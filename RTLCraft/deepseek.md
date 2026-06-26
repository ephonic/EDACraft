# DeepSeek: Spec-to-RTL Gap Analysis & Modification Plan

## 问题诊断

当前 pipeline 存在一个 **串行化断层**：从 ArchDefinition → GenerationContext → spec markdown 的过程中，大量架构/行为信息丢失。导致了：

```
原文行为层                   骨架层                    spec.md                     DSL生成
──────────────────────────────────────────────────────────────────────────────
behaviors.py (实时模拟)  →  Callable 函数        →  "处理流水线数据"          ← 无法指导
dsl_modules.py (手写RTL) →  ReferenceSummary     →  截断的代码片段            ← 参考不足
_fill_*_logic (完整逻辑)  →  skeleton_hints计数   →  "有3个comb块"           ← 无实质内容
_SUBMODULE_DEFS (连线图)  →  SubmoduleInst创建    →  子模块名列表             ← 无连接细节
arch_templates (信号级)   →  抽象为up/downstream  →  无信号映射              ← 无法生成互联
golden测试向量            →  _gen_golden_tests()  →  未包含进spec             ← 无验证依据
```

## 具体断点

### 断点1: 行为代码从不串行化
`pe.behavior` 是 `Callable[[CycleContext], None]` — Python闭包，无法被 spec_markdown 读取。虽然 behaviors.py 有：
- `rv64_core_template()`: PC更新、retire计数、ISS集成
- `l1_cache_template()`: tag检查、hit/miss、coherence请求  
- `coherence_dir_template()`: sharers bitmask、M→S downgrade
- `noc_router_template()`: XY routing决策

但这些内容在 spec 中完全消失，仅剩模板字符串 "process pipeline stage data"。

### 断点2: ReferenceSummary 信息截断
`ReferenceSummary.code_patterns` 包含 `fsm_summary`、`state_vars`、`ports`，但：
- code_snippets 只保存0-4个片段（dsl_modules.py 有300+行完整RTL）
- `design_intent` 只保存前4条（实际有10+条）
- `state_pattern` 只保存前4条
- code_patterns 是由 ReferenceExtractor 从 skills_index.yaml 提取的，而不是从实际 dsl_modules.py 源码提取

### 断点3: FSM 信息丢失
`_fill_*_logic()` 创建了完整的FSM：
- cache_fsm: IDLE→CHECK→REFILL (+ coherence states)
- dir_fsm: IDLE→LOOKUP→PROBE→UPDATE→WB
- l2_fsm: 类似 cache_fsm

但 `skeleton_logic_hints` 只记录"有3个comb块"，不提取状态名、转移条件、输出逻辑。

### 断点4: 子模块连接图不输出
`_SUBMODULE_DEFS` 含有详细的跨子模块连接：
- IFU.fetch_valid → IDU.fetch_valid
- IDU.dec_ra → ALU.dec_ra
- ALU.branch_taken → IFU.branch_taken
- ...

这些在 spec 中完全看不到。子模块只有输入/输出信号名列表（且只显示前4个），没有连接拓扑。

### 断点5: 互联架构被抽象
arch_templates 定义了精确的信号级连接（`Core_0.icache_req → L1I_0.req`），但 spec 只得到 "upstream/downstream" 列表，没有信号映射。

## 修改方案

### 方案A: 在 spec_ir 层增加结构化信息提取

创建 `rtlgen/spec_enhancer.py`，在 GenerationContext → markdown 之间增加增强层：

```
GenerationContext → SpecEnhancer → SpecIR (增强版) → spec_markdown (v2)
```

增强器从以下来源提取额外信息：

#### A1: 从 Module 对象提取 FSM 信息
`_fill_skeleton_logic()` 之后，introspect Module 的 seq/comb 块：
```python
def extract_fsms(module):
    fsms = []
    for seq in module._seq_blocks:
        # 查找 state_reg 模式: reg <<= STATE_ID 的赋值
        for assignment in seq.assignments:
            if is_state_transition(assignment):
                fsm = {
                    "reg": reg_name,
                    "states": extract_state_names(seq),
                    "transitions": extract_transitions(seq),
                    "width": reg_width,
                }
                fsms.append(fsm)
    # 从 comb 块提取输出/状态依赖
    return fsms
```

#### A2: 从 ProcessingElement 提取行为伪代码
将 `pe.behavior` 函数做静态分析（或对已知模板做 text extraction）：
```python
def extract_behavior_psuedocode(pe_type):
    # 预定义的行为伪代码（存储在 behaviors.py 的 docstring 中）
    behavior_map = {
        "rv64_core": """
            每个周期:
              stall = input.stall
              if stall: output.retire_valid = 0; return
              pc = state.pc (default 0x1000)
              iss_service = model.isa_step()
              if iss_service.done:
                pc = model.get_pc()
                output.retire_valid = 1
              else:
                pc = pc + 4
                output.retire_valid = 1
              state.pc = pc
        """,
        ...
    }
    return behavior_map.get(pe_type, "")
```

#### A3: 从 ArchDefinition 提取互连拓扑
```python
def extract_interconnect_map(arch, pe_name):
    """生成该 PE 的输入/输出信号→互联 PE 的映射"""
    conns = []
    for ic in arch.interconnects:
        if ic.src_pe == pe_name:
            for sig in ic.signals:
                conns.append(f"{ic.src_pe}.{sig.name} → {ic.dst_pe}.{sig.name}")
    return conns
```

### 方案B: 增强 spec_markdown.py 输出

#### B1: 新增"架构描述"章节 (Section 2 → Section 4)
从 PE 的 description 和 pe_type 生成结构化架构描述：

| rv64_core | 5-stage RISC-V pipeline (Fetch/Decode/Execute/Memory/Writeback) |
|-----------|---------------------------------------------------------------|
| l1_cache  | Direct-mapped cache with MSI coherence, tag+data RAM + refill FSM |
| noc_router | 5-port XY routing, input FIFO buffers, crossbar switch, priority arbitration |
| coherence_dir | MSI directory with sharers bitmask, snoop generation, response arbitration |

#### B2: 新增"FSM 状态转移表"章节
生成表格格式的状态机描述：

| Current State | Condition | Next State | Outputs |
|---|---|---|---|
| IDLE | req == 1 | CHECK | ready = 1 |
| CHECK | hit == 1 | IDLE | valid = 1, rdata = data_ram[...] |
| CHECK | hit == 0 | REFILL | miss = 1, miss_addr = addr |
| REFILL | fill_valid == 1 | IDLE | valid = 1 |

#### B3: 新增"子模块内部连接"章节
从 `_SUBMODULE_DEFS.connections` 生成连线表：

| From | To | Signal |
|---|---|---|
| ifu.fetch_valid | idu.fetch_valid | Wire fetch_valid |
| idu.dec_ra | alu.dec_ra | Wire dec_ra[63:0] |
| alu.branch_taken | ifu.branch_taken | Wire branch_taken |

#### B4: 新增"接口协议描述"章节
从 ArchDefinition 的 InterconnectSpec.handshake 信息生成：

- Core_0 → L1I_0: valid/ready handshake, icache_req/icache_valid/icache_ready
- Core_0 → L1D_0: valid/ready handshake, dcache_req/dcache_valid/dcache_wen/dcache_ready

#### B5: 新增"Golden 测试向量"章节
将 `_gen_golden_tests()` 生成的测试向量包含进来：

| Test | Input | Expected Output | Description |
|---|---|---|---|
| 1 | icache_valid=1, icache_rdata=0x00000013 | icache_req=0, retire_valid=1 | NOP execution |
| 2 | icache_valid=0 | icache_req=1, fetch_valid=0 | I-cache stall |
| 3 | req=1, addr=0x1000 | miss=1 (第一次), hit=1 (第二次) | Cache fill |

### 方案C: 在 spec_gen 阶段引入更丰富的数据源

修改 `skill_ppa.py:_run_spec_gen()` 和 `_build_gen_ctx_from_package()`:

#### C1: 传入 ArchDefinition 完整引用
当前 `_build_gen_ctx_from_package()` 只使用 `pkg.pe`，应该同时传入 `arch` 来提取互连信息。

#### C2: 包含 pe.behavior 的 text/docstring 提取
在创建 GenerationContext 时，如果 pe.behavior 有 `__doc__` 或来自已知模板，提取其 docstring 作为额外的行为描述。

#### C3: 从 dsl_modules.py 提取完整的 reference code
在 `_run_spec_gen()` 中，如果能找到对应的 hand-written DSL 文件（`dsl_modules.py`），提取完整的类定义作为 reference。

### 方案D: 修改 GenerationContext.to_dict() 包含所有字段

当前 `GenerationContext.to_dict()` 省略了：
- `skeleton_state_vars`
- `skeleton_logic_hints`
- `sub_modules`
- `implementation_steps`

这些字段需要在 serialization 中包含，以便下游使用。

## 执行优先级

### P0 (立即修复，spec质量根本提升)
1. **D**: `GenerationContext.to_dict()` 包含所有字段
2. **C1**: `_build_gen_ctx_from_package()` 传入 `arch` 参数提取互联拓扑
3. **B2**: spec 增加 FSM 状态转移表（从 Module seq/comb 块提取）

### P1 (显著改善指导性)
4. **A1**: 创建 `extract_fsms()` 函数，从 Module 提取 FSM 细节
5. **B1**: 增加架构描述章节（从 pe_type 映射）
6. **B3**: 子模块内部连接表（从 _SUBMODULE_DEFS.connections 生成）

### P2 (补充性增强)
7. **A2**: 提取行为伪代码
8. **B4**: 接口协议描述
9. **B5**: Golden 测试向量

## 预期效果

修改后，Core_0_spec.md 将从当前的 ~96行（仅端口+状态变量名）扩展到 ~300+行，包含：

| 内容 | 当前 | 修改后 |
|---|---|---|
| 端口列表 | ✅ 15行 | ✅ 15行 |
| 行为描述 | ❌ 只有 "process pipeline stage data" | ✅ 5-stage pipeline + PC/ALO/转发细节 |
| FSM | ❌ 无 | ✅ cache_fsm 状态转移表 |
| 子模块连接 | ❌ 无 | ✅ IFU→IDU→ALU→LSU→WB 连线表 |
| 架构描述 | ❌ 无 | ✅ 5-stage pipeline block diagram |
| 接口协议 | ❌ 无 | ✅ icache/dcache handshake 描述 |
| 参考代码 | ❌ 截断片段 | ✅ 完整参考代码链接 |
| 测试向量 | ❌ 无 | ✅ 3-5个 golden test cases |
