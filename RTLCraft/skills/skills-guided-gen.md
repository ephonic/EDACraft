下面给你一个**整体方案**，把前面两个想法合在一起：

1. **从系统级/行为级需求生成 RTL**
2. **智能体从现有 skills 中检索有参考价值的模块/片段**
3. **不直接复用旧代码，而是参考已有设计模式生成新实现**
4. **框架保持尽量简单，不引入过多层级**

我建议这个框架可以叫：

# Skill-Guided RTL Generation Flow

中文可以叫：

# 基于技能检索引导的 RTL 生成流程

核心思想是：

> 行为级模型负责说明“要做什么”；
> skills 负责提供“类似设计怎么做过”；
> 生成器负责根据当前需求重新生成 RTL/DSL；
> verifier 负责验证并驱动修复。

---

# 1. 总体架构

建议整体只保留五个核心模块：

```text
BehaviorSpec
    ↓
ArchSkeletonGenerator
    ↓
SkillRetriever
    ↓
LogicGenerator
    ↓
Verifier / Repair Loop
```

不要设计太复杂的 provider、adapter、contract graph、capability graph。

最小架构如下：

```text
系统级行为模型
        ↓
行为仿真通过
        ↓
行为需求/模块需求提取
        ↓
架构骨架生成
        ↓
针对每个模块检索 skills
        ↓
生成 reference cards
        ↓
根据当前需求重新生成 DSL/RTL
        ↓
语法/仿真/综合检查
        ↓
失败则自动修复
        ↓
输出可综合 RTL
```

---

# 2. 关键定位

你的系统不要把 `skills/` 看成 IP 库。

而应该看成：

```text
设计经验库
+ 模块参考库
+ 控制模式库
+ 接口协议库
+ 子模块组织方式库
+ 局部代码片段库
```

也就是说：

```text
不要：ArchSkeletonGenerator 直接实例化 skills.gpgpu.SMWrapper

而是：

ArchSkeletonGenerator 发现要生成 sm_wrapper
    ↓
SkillRetriever 找到 SMWrapper / WarpScheduler / Scoreboard 等参考
    ↓
抽取这些模块的结构、协议、状态、行为模式
    ↓
LogicGenerator 根据当前需求生成新的 sm_wrapper
```

---

# 3. 推荐目录结构

保持简单：

```text
rtlgen/
├── arch_skel.py             # 原有骨架生成器，稍作修改
├── skill_retriever.py       # 新增：检索 skills
├── logic_generator.py       # 新增：根据需求+参考生成逻辑
├── verifier.py              # 新增：语法/仿真/修复闭环
├── skill_index.py           # 可选：构建/加载 skills_index
└── prompts/
    ├── module_generate.md
    └── module_repair.md

skills/
├── gpgpu/
│   ├── dsl_modules.py
│   └── skills_index.yaml
├── cpu/
│   └── skills_index.yaml
└── common/
    └── patterns.yaml
```

其中最重要的是：

```text
skills_index.yaml
```

它不是代码，而是已有模块的“可检索摘要”。

---

# 4. 完整流程分解

## Phase 0：已有 skills 建索引

先对 `skills/` 下的已有模块建立索引。

第一版建议手工/半自动维护，不要一开始就做复杂向量数据库。

例如：

```yaml
- id: module:gpgpu:WarpScheduler
  source:
    file: skills/gpgpu/dsl_modules.py
    class: WarpScheduler
  kind: module
  domain: gpgpu

  behavior_tags:
    - warp_scheduling
    - arbitration
    - valid_ready
    - fairness

  interface_patterns:
    - multi_request_valid
    - single_grant
    - valid_ready

  control_patterns:
    - round_robin
    - priority_scan
    - stall_control

  datapath_patterns:
    - mux_select
    - index_encode

  useful_for:
    - warp_issue
    - request_selection
    - arbitration
    - scheduler_generation

  state_patterns:
    - rr_ptr

  summary: >
    Selects one ready warp from multiple active warps using a scheduling policy.
    Useful as a reference for arbitration, warp scheduling, and issue selection.

  maturity:
    syntax_checked: true
    sim_tested: false
    synthesizable_likely: true
```

再比如：

```yaml
- id: module:gpgpu:Scoreboard
  source:
    file: skills/gpgpu/dsl_modules.py
    class: Scoreboard
  kind: module
  domain: gpgpu

  behavior_tags:
    - hazard_check
    - dependency_tracking
    - register_busy_tracking

  interface_patterns:
    - query_response
    - update_event

  control_patterns:
    - busy_bit_table
    - dependency_blocking

  useful_for:
    - issue_hazard_check
    - operand_ready_check
    - pipeline_stall_generation

  summary: >
    Tracks register dependencies and blocks issue when operands or destination
    registers are not ready.
```

这样后续检索不是靠“模块名完全一致”，而是靠行为、接口、控制模式、数据通路模式的相似性。

---

## Phase 1：系统级行为模型仿真

你现有思路是：

```text
系统级行为模型
→ 仿真通过
→ 骨架生成
→ RTL 生成
```

这里建议在行为仿真通过后，额外生成一个结构化的 **Behavior Requirement**。

例如对于 GPGPU SM：

```yaml
module: sm_wrapper
type: gpgpu_sm

behavior:
  - receive CTA dispatch
  - allocate warp entries
  - fetch instruction by warp PC
  - decode instruction
  - buffer decoded instruction
  - select ready warp
  - check scoreboard hazards
  - collect operands
  - issue to execution units
  - write back results
  - update scoreboard

interfaces:
  - dispatch_valid_ready
  - instruction_fetch_request_response
  - global_memory_request_response
  - pipeline_valid_ready

state:
  - warp_valid
  - warp_pc
  - warp_active_mask
  - scoreboard_busy
  - issue_queue_valid

control_patterns:
  - valid_ready_handshake
  - pipeline_stall
  - round_robin_scheduler
  - scoreboard_hazard_check

datapath_patterns:
  - instruction_decode
  - operand_mux
  - alu_execute
  - load_store_request
```

这个文件非常关键，因为它是后面检索和生成的共同输入。

---

## Phase 2：架构骨架生成

`ArchSkeletonGenerator` 仍然负责生成模块边界：

```text
module name
ports
parameters
state variables
submodule placeholders
interface channels
```

但它不再只靠硬编码 `_fill_sm_wrapper_logic`。

原来的流程：

```python
module = _create_base_module(pe)
_declare_state_vars(module, pe.state)
_fill_skeleton_logic(module, pe.pe_type, pe)
```

改成：

```python
module = _create_base_module(pe)
_declare_state_vars(module, pe.state)

logic = generate_logic_with_skill_reference(pe, arch, module)

if logic.success:
    module.merge(logic)
else:
    _fill_skeleton_logic_fallback(module, pe.pe_type, pe)
```

这样你保留原有框架，同时增加智能生成能力。

---

# 5. 检索与生成如何结合

这是核心。

对于每个待生成模块，流程如下：

```text
当前模块需求
    ↓
构造 Retrieval Query
    ↓
从 skills_index 检索参考模块/模式/片段
    ↓
生成 reference cards
    ↓
把 reference cards + 当前需求交给 LogicGenerator
    ↓
生成当前专用 RTL/DSL
```

---

## 5.1 构造 Retrieval Query

不要只用：

```text
pe_type = sm_wrapper
```

而要构造多维查询：

```yaml
retrieval_query:
  target_module: sm_wrapper
  pe_type: gpgpu_sm

  behavior:
    - receive CTA dispatch
    - allocate warps
    - schedule ready warp
    - check scoreboard hazards
    - issue instruction
    - collect operands
    - execute and writeback

  interface_patterns:
    - dispatch_valid_ready
    - memory_request_response
    - pipeline_valid_ready

  control_patterns:
    - valid_ready_handshake
    - round_robin_scheduler
    - scoreboard_hazard_check
    - pipeline_stall
    - fifo_buffer

  datapath_patterns:
    - instruction_decode
    - operand_select
    - alu_execute
    - load_store

  generation_goal:
    - generate synthesizable RTL
    - reference existing skills but do not copy
    - satisfy current module ports
```

---

## 5.2 SkillRetriever 多路打分

对每个 skill 计算综合相关性：

```text
score =
  0.25 * behavior_similarity
+ 0.20 * interface_similarity
+ 0.20 * control_pattern_similarity
+ 0.15 * datapath_similarity
+ 0.10 * keyword_similarity
+ 0.10 * maturity_score
```

第一版可以用集合重合度：

```python
def overlap_score(query_items, skill_items):
    if not query_items:
        return 0.0
    return len(set(query_items) & set(skill_items)) / len(set(query_items))
```

整体伪代码：

```python
def retrieve_references(query, skill_index, top_k=6):
    candidates = []

    for skill in skill_index:
        score = 0.0
        score += 0.25 * overlap_score(query.behavior_tags, skill.behavior_tags)
        score += 0.20 * overlap_score(query.interface_patterns, skill.interface_patterns)
        score += 0.20 * overlap_score(query.control_patterns, skill.control_patterns)
        score += 0.15 * overlap_score(query.datapath_patterns, skill.datapath_patterns)
        score += 0.10 * keyword_score(query, skill)
        score += 0.10 * maturity_score(skill)

        if score > 0.2:
            candidates.append((score, skill))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [make_reference_card(skill, score, query) for score, skill in candidates[:top_k]]
```

---

## 5.3 Reference Card

检索结果不要直接返回代码全文，而是返回“参考卡片”。

例如：

```yaml
reference_card:
  name: WarpScheduler
  relevance: 0.87
  source: skills/gpgpu/dsl_modules.py:WarpScheduler

  why_relevant:
    - target module needs ready warp selection
    - this skill implements multi-request single-grant scheduling
    - contains round-robin pointer update pattern

  useful_ideas:
    - maintain rr_ptr
    - scan candidate warps from rr_ptr
    - issue first valid and dependency-ready warp
    - update rr_ptr after successful issue

  reusable_patterns:
    - round_robin_select
    - valid_ready_fire
    - stall_when_no_candidate

  suggested_adaptation:
    - adapt warp_valid to current warp_active_mask
    - adapt scoreboard_ready to dependency_clear
    - expose issue_packet rather than only warp_id

  caution:
    - existing implementation may assume fixed NUM_WARP
    - do not copy code directly
```

这样智能体获得的是“设计方法”，不是一段旧代码。

---

# 6. LogicGenerator 如何使用 reference cards

生成器输入应该固定为：

```yaml
generation_context:
  target_module:
    name: sm_wrapper
    ports: ...
    parameters: ...
    state: ...

  behavior_requirement:
    - receive CTA dispatch
    - allocate warps
    - schedule ready warp
    - check scoreboard hazards
    - issue instruction
    - writeback result

  template_tasks:
    - cta2warp
    - fetch_decode
    - ibuffer
    - warp_schedule
    - scoreboard_check
    - issue_execute
    - writeback

  reference_cards:
    - WarpScheduler
    - Scoreboard
    - IBuffer
    - Issue
    - SMWrapper

  generation_policy:
    copy_existing_code: false
    use_reference_as_guidance: true
    synthesizable_only: true
    prefer_simple_logic: true
    preserve_current_ports: true
```

生成器的任务是：

```text
根据当前端口、状态和行为要求，参考已有模块的设计模式，生成一个新的模块实现。
```

不是：

```text
导入旧 SMWrapper。
```

---

# 7. 生成策略：按任务逐步生成，而不是一次生成整个模块

对于复杂模块，例如 `sm_wrapper`，不要一次性让智能体生成完整 RTL。

建议按 `_TEMPLATE_STEPS` 分阶段生成：

```text
1. CTA dispatch / warp allocation
2. instruction fetch interface
3. decode / ibuffer
4. warp scheduler
5. scoreboard hazard check
6. issue logic
7. operand collect
8. execute dispatch
9. writeback
10. top-level stall/flush/control
```

每一步：

```text
task requirement
    ↓
检索相关 skills
    ↓
生成该部分逻辑
    ↓
局部检查
    ↓
合并到模块
```

例如：

```python
for task in template_tasks:
    query = build_task_query(pe, task)
    refs = skill_retriever.retrieve(query)
    logic_piece = logic_generator.generate_task_logic(pe, task, refs)
    module.merge(logic_piece)
    verifier.check_partial(module)
```

这样比一次性生成更稳定，也更容易修复。

---

# 8. `_TEMPLATE_STEPS` 建议结构化

你现在的 `_TEMPLATE_STEPS` 是字符串。建议改为轻量结构化。

例如：

```python
_TEMPLATE_STEPS = {
    "sm_wrapper": [
        {
            "name": "cta2warp",
            "goal": "receive CTA dispatch and allocate warp entries",
            "behavior_tags": ["dispatch", "warp_allocation"],
            "interface_patterns": ["valid_ready"],
            "control_patterns": ["allocator", "free_list"],
            "datapath_patterns": ["payload_decode"]
        },
        {
            "name": "warp_schedule",
            "goal": "select one ready warp for issue",
            "behavior_tags": ["warp_scheduling", "arbitration"],
            "interface_patterns": ["multi_request_valid", "single_grant"],
            "control_patterns": ["round_robin", "stall_control"],
            "datapath_patterns": ["index_encode"]
        },
        {
            "name": "scoreboard_check",
            "goal": "block issue when operands or destination registers are busy",
            "behavior_tags": ["hazard_check", "dependency_tracking"],
            "control_patterns": ["busy_bit_table", "pipeline_stall"]
        }
    ]
}
```

这不是复杂层级，只是把已有提示变成可检索、可生成的任务描述。

---

# 9. Verifier / Repair Loop

因为生成器是“参考后生成”，一定要有验证闭环。

最小验证分四层：

```text
Level 1: 语法检查
Level 2: 静态检查
Level 3: 简单行为 testbench
Level 4: 与行为级模型对比
```

## 9.1 语法检查

```text
iverilog / verilator / 自己的 parser
```

检查：

```text
是否有未声明信号
是否有语法错误
是否端口重复
是否 always_comb 有 latch
```

## 9.2 静态检查

检查：

```text
重复驱动
未驱动输出
valid-ready 成对
reset 是否覆盖状态寄存器
时序逻辑是否用 always_ff
组合逻辑是否用 always_comb
```

## 9.3 简单行为测试

自动生成 smoke test：

```text
reset
输入 valid
观察 ready
发一条简单 dispatch
检查 issue_valid 是否出现
检查 scoreboard 是否更新
```

## 9.4 行为模型对比

如果系统级行为模型能产生 trace，则做：

```text
behavior trace
    vs
RTL simulation trace
```

例如：

```yaml
expected_trace:
  cycle 0: dispatch_valid=1
  cycle 1: warp_valid[0]=1
  cycle 3: issue_valid=1, issue_warp_id=0
```

如果不匹配，进入 repair prompt。

---

# 10. 生成失败后的修复流程

生成失败时不要重新从头生成，而是把错误、当前代码、参考卡片一起给 repair agent。

```text
generated module
    ↓
verifier error
    ↓
repair prompt
    ↓
patch
    ↓
re-run verifier
```

修复上下文：

```yaml
repair_context:
  module: sm_wrapper
  failed_check: syntax
  error:
    - signal issue_valid is assigned but not declared
  current_code: ...
  behavior_requirement: ...
  reference_cards:
    - WarpScheduler
    - Scoreboard
  repair_policy:
    preserve_existing_structure: true
    minimal_change: true
```

---

# 11. 最小可实现主流程伪代码

```python
def generate_rtl_from_behavior(behavior_model, arch_def, skills_index):
    # 1. 行为模型仿真
    sim_result = run_behavior_sim(behavior_model)
    if not sim_result.pass_:
        raise RuntimeError("Behavior model simulation failed")

    # 2. 从行为模型提取模块需求
    behavior_reqs = extract_behavior_requirements(behavior_model, arch_def)

    generated_modules = []

    # 3. 对每个 PE / module 生成骨架
    for pe in arch_def.processing_elements:
        module = create_base_module(pe)

        # 4. 获取结构化生成任务
        tasks = get_template_tasks(pe.pe_type)

        # 5. 按任务生成逻辑
        for task in tasks:
            query = build_retrieval_query(
                pe=pe,
                task=task,
                behavior_req=behavior_reqs.get(pe.name)
            )

            refs = retrieve_references(
                query=query,
                skill_index=skills_index,
                top_k=5
            )

            logic_piece = generate_logic_piece(
                pe=pe,
                task=task,
                behavior_req=behavior_reqs.get(pe.name),
                reference_cards=refs,
                policy={
                    "copy_existing_code": False,
                    "synthesizable_only": True
                }
            )

            module.merge(logic_piece)

            check = verify_partial_module(module)
            if not check.pass_:
                module = repair_module(module, check, refs)

        # 6. 整模块验证
        final_check = verify_module(module)
        if not final_check.pass_:
            module = repair_module(module, final_check, refs)

        generated_modules.append(module)

    # 7. 顶层集成
    top = integrate_modules(generated_modules, arch_def)

    # 8. 系统级 RTL 仿真
    rtl_check = verify_against_behavior(top, behavior_model)

    if not rtl_check.pass_:
        top = repair_top_level(top, rtl_check, behavior_model)

    return top
```

---

# 12. 数据在系统中的流动

整体数据流可以设计为：

```text
behavior_model.py
    ↓
behavior_trace.json
    ↓
behavior_requirements.yaml
    ↓
arch_definition.yaml
    ↓
module_generation_context.yaml
    ↓
skills_index.yaml
    ↓
reference_cards.yaml
    ↓
generated_dsl.py / generated_rtl.sv
    ↓
simulation_report.json
    ↓
repair_patch
```

这样每一步都有中间产物，便于 debug。

---

# 13. 一个具体例子：生成 WarpScheduler

## 输入行为需求

```yaml
target_module: warp_scheduler

behavior:
  - choose one ready warp each cycle
  - do not issue warp with dependency hazard
  - use round-robin priority
  - update pointer after successful issue

ports:
  warp_valid: input [NUM_WARP-1:0]
  dependency_clear: input [NUM_WARP-1:0]
  issue_ready: input
  issue_valid: output
  issue_warp_id: output [$clog2(NUM_WARP)-1:0]
```

## 检索 query

```yaml
behavior_tags:
  - warp_scheduling
  - arbitration
  - fairness

interface_patterns:
  - multi_request_valid
  - single_grant
  - valid_ready

control_patterns:
  - round_robin
  - stall_control
```

## 检索结果

```yaml
reference_cards:
  - WarpScheduler
  - round_robin_select_pattern
  - Issue
```

## 生成结果

生成器根据当前端口生成新的 RTL：

```verilog
always_comb begin
  issue_valid = 1'b0;
  issue_warp_id = '0;
  for (int i = 0; i < NUM_WARP; i++) begin
    idx = rr_ptr + i;
    if (!issue_valid && warp_valid[idx] && dependency_clear[idx]) begin
      issue_valid = 1'b1;
      issue_warp_id = idx;
    end
  end
end

always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n)
    rr_ptr <= '0;
  else if (issue_valid && issue_ready)
    rr_ptr <= issue_warp_id + 1'b1;
end
```

注意这里它参考了已有 `WarpScheduler`，但不是直接复制。

---

# 14. 如何避免框架复杂化

你的担心很重要。建议明确“不做”的东西：

## 第一版不要做

```text
不要做复杂 provider registry
不要做完整旧 API 到新 API 的 adapter
不要做 capability graph
不要做大型知识图谱
不要做向量数据库依赖
不要一上来自动 AST 深度理解所有 skills
不要直接复用旧代码作为 IP
```

## 第一版只做

```text
skills_index.yaml
SkillRetriever
ReferenceCard
LogicGenerator
Verifier
```

这个复杂度可控。

---

# 15. 与现有 `arch_skel.py` 的最小改动点

你只需要改三个地方。

## 15.1 在 generator 初始化时加载 skills

```python
class ArchSkeletonGenerator:
    def __init__(self, ..., skills_index_path=None):
        self.skill_index = load_skill_index(skills_index_path)
        self.skill_retriever = SkillRetriever(self.skill_index)
        self.logic_generator = LogicGenerator()
        self.verifier = Verifier()
```

## 15.2 修改 `_fill_skeleton_logic`

```python
def _fill_skeleton_logic(self, module, pe_type, pe, arch):
    if self.skill_retriever is not None:
        result = self._fill_with_skill_guidance(module, pe_type, pe, arch)
        if result.success:
            return

    self._fill_skeleton_logic_fallback(module, pe_type, pe)
```

## 15.3 增加 `_fill_with_skill_guidance`

```python
def _fill_with_skill_guidance(self, module, pe_type, pe, arch):
    tasks = get_template_tasks(pe_type)

    for task in tasks:
        query = build_retrieval_query(pe, arch, task)
        refs = self.skill_retriever.retrieve(query, top_k=5)

        piece = self.logic_generator.generate(
            module=module,
            pe=pe,
            task=task,
            references=refs
        )

        module.merge(piece)

        check = self.verifier.check_partial(module)
        if not check.pass_:
            patch = self.logic_generator.repair(module, check, refs)
            module.apply_patch(patch)

    return Success()
```

这样整体框架仍然很轻。

---

# 16. 最终建议的系统闭环

最终工作流：

```text
1. 编写/获得系统级行为模型
2. 行为级仿真通过
3. 自动提取 Behavior Requirements
4. ArchSkeletonGenerator 生成模块外壳
5. 对每个模块/任务构造 Retrieval Query
6. SkillRetriever 从 skills_index 中找参考模块/片段
7. 生成 Reference Cards
8. LogicGenerator 根据当前需求生成新逻辑
9. Verifier 做语法/静态/仿真检查
10. Repair Loop 修复
11. 顶层集成
12. 与行为模型做 trace 对齐
13. 输出 RTL
```

---

# 17. 这个方案的优点

## 17.1 不依赖精确匹配

因为检索的是：

```text
行为模式
接口协议
控制结构
数据通路模式
```

不是模块名。

所以即使没有完全相同模块，也可以找到有参考价值的模块。

---

## 17.2 不直接复制旧代码

通过 reference cards 只提供：

```text
有用设计思路
适配建议
注意事项
```

让生成器重新生成当前专用实现。

---

## 17.3 框架不复杂

只增加：

```text
SkillRetriever
LogicGenerator
Verifier
```

没有引入大型注册系统或复杂图数据库。

---

## 17.4 可逐步演进

第一版：

```text
手工 skills_index + 规则检索
```

第二版：

```text
自动索引 + 模式识别
```

第三版：

```text
embedding 语义检索 + 结构 rerank
```

第四版：

```text
根据验证成功率更新 skill relevance
```

---

# 18. 一句话总结

我建议你的 RTL 生成框架改成：

> **行为模型驱动骨架生成，skills 检索提供参考模式，智能体根据当前需求重新生成逻辑，verifier 负责闭环修复。**

最简结构是：

```text
BehaviorSpec
→ ArchSkeletonGenerator
→ SkillRetriever
→ Reference Cards
→ LogicGenerator
→ Verifier/Repair
→ RTL
```

其中 skills 的角色不是“可直接实例化的 IP”，而是：

> **可检索、可参考、可迁移的设计经验库。**
