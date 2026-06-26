# Plan DSL 0623: `rtlgen_x` DSL 演化计划

## 1. 目标

基于 [audit_dsl_0623.md](/Users/yangfan/release/EDACraft-main/RTLCraft/audit_dsl_0623.md)，`rtlgen_x` 的 DSL 演化目标不是“再造一个更像 Verilog 的 Python 语法”，而是把它收敛成一个：

1. **唯一主 authoring surface** 的硬件描述语言
2. **executable-first** 的设计语言
3. **对 CDC / UVM / PPA / agent 友好** 的结构化语言
4. **在多时钟、存储、协议、类型语义上更强** 的工程语言

一句话目标：

**让 `rtlgen_x.dsl` 成为一个比 Verilog 更适合“生成、执行、分析、反馈、再修改”的硬件构造语言。**

---

## 2. 当前基线

结合审计结论和当前代码状态，先明确现状：

### 2.1 已完成收口

1. `native DSL` 已从 `rtlgen_x` 代码与文档中移除
2. 原 `legacy DSL` 已收口为唯一公开 DSL
3. `rtlgen_x/dsl/legacy/*` 已折叠到 `rtlgen_x/dsl/*`
4. `sim / verify / ppa / cdc / uvm` 的公开叙事已经围绕 DSL 展开

### 2.2 仍然存在的主要问题

1. **还缺明确 support matrix**  
   用户还不够容易判断哪些 DSL construct 是 synthesis-grade stable、哪些只是 partial。

2. **语义收敛还不够显式**  
   当前 lowering / emitter / analyzer 虽然已经共用大量路径，但“canonical semantics contract” 还没有被正式定义出来。

3. **时钟 / 复位 / 存储语义还不够一等公民**  
   multi-clock 可以执行，但 authoring 层对 domain / reset-release / memory policy 的表达还偏弱。

4. **类型系统不够强**  
   目前还缺 enum / packed struct / fixed-point / lane-vector 等更适合真实 datapath 和协议设计的类型。

5. **协议 / channel 抽象还可以再前进一步**  
   已有 Bundle / Interface / 协议库，但还缺更统一的 first-class channel 语义与 lint / adapter。

6. **agent 可操作性还不够强**  
   还缺 hierarchy query、connectivity query、structured symbol table、统一 rewrite hint 格式等能力。

### 2.3 当前定位

本计划保持以下边界不变：

1. `archsim` 只输出分析报告，不向 DSL 显式传递 IR
2. `ppa` 只输出分析和建议，不自动改 DSL
3. 不引入新的 control plane / contract 系统
4. 不再引入第二套平行 DSL front-end

---

## 3. 演化原则

### 3.1 一个主 DSL，零平行前端

后续只维护一个 synthesis-grade 主 authoring surface：`rtlgen_x.dsl`。

### 3.2 不新增重型用户可见 IR

可以补“内部 canonical semantics / normalization layer”，但不再对用户暴露一套新的多层 IR 体系。

### 3.3 所有稳定特性都必须走同一闭环

一个 DSL 特性只有在同时满足以下条件后，才能标记为 stable：

1. 能 lowering
2. 能 Python 仿真
3. 能 C++ backend 仿真
4. 能 emitted RTL
5. 能被相关分析器正确消费

### 3.4 优先放大 DSL 相对 Verilog 的优势

优先做强：

1. 参数化生成
2. executable semantics
3. 协议 / 结构抽象
4. source-mapped diagnostics
5. agent 结构化修改能力

而不是优先追求“更像手写 Verilog 文本”。

---

## 4. 总体路线

本轮演化分四个阶段推进。

---

## 5. Phase P0: 语义收敛与边界明确

### 5.1 目标

把“当前其实已经存在的主 DSL + executable backend 路径”正式定义清楚，避免再次出现多入口、多语义世界。

### 5.2 主要工作

1. 补一份 DSL support matrix 文档  
   建议新增：
   - `rtlgen_x/DSL_SUPPORT_MATRIX.md`

2. 补一份 DSL semantic contract 文档  
   建议新增：
   - `rtlgen_x/DSL_SEMANTICS.md`

3. 明确公开 API 边界  
   高层接口文档统一约定：
   - 用户输入是 DSL `Module`
   - `LoweredDslModule` 仅作为调试/中间观察对象
   - `SimModule` 是内部执行对象，不作为主 authoring surface 宣传

4. 给每个主要 DSL construct 标注状态：
   - `stable`
   - `partial`
   - `experimental`
   - `unsupported`

5. 清理剩余“能写但不能稳定闭环”的模糊表述

### 5.3 主要代码触点

1. `rtlgen_x/README.md`
2. `rtlgen_x/TUTORIAL_UVM.md`
3. `rtlgen_x/TUTORIAL_ARCH_PPA.md`
4. `rtlgen_x/dsl/adapter.py`
5. `rtlgen_x/verify/module_adapter.py`
6. `rtlgen_x/ppa/advisor.py`

### 5.4 验收标准

1. 所有公开文档只描述一个 DSL front-end
2. 每个主 construct 在文档里都能看到支持级别
3. 对外示例只走 `rtlgen_x.dsl` 路径
4. `rtlgen_x/tests/` 全绿

---

## 6. Phase P1: 时钟 / 复位 / 存储语义一等公民化

### 6.1 目标

让多时钟设计、reset-release、memory 行为不只是“后端能跑”，而是在 authoring 层就能明确表达和检查。

### 6.2 主要工作

#### A. 时钟 / 复位域语义

引入或增强以下 authoring-level 能力：

1. `ClockDomain` 规格对象
2. `ResetDomain` 规格对象
3. reset polarity / sync / async / release policy 显式声明
4. process 与 domain 的显式绑定
5. CDC-safe crossing primitive 的统一标注

#### B. reset-release 专项能力

1. reset builder / functional block 的语义区分
2. hand-written synchronizer pattern 识别继续增强
3. reset-release rule 的 source-mapped 诊断标准化

#### C. storage 语义

Memory/Array 声明增强为可描述：

1. 读端口数 / 写端口数
2. sync read / async read
3. read-during-write policy
4. byte-enable
5. latency
6. initialization contract

### 6.3 主要代码触点

1. `rtlgen_x/dsl/core.py`
2. `rtlgen_x/dsl/logic.py`
3. `rtlgen_x/dsl/ram.py`
4. `rtlgen_x/dsl/adapter.py`
5. `rtlgen_x/verify/cdc.py`
6. `rtlgen_x/sim/python_runtime.py`
7. `rtlgen_x/sim/cpp_backend.py`
8. `rtlgen_x/verify/uvm.py`
9. `rtlgen_x/ppa/advisor.py`

### 6.4 验收标准

1. multi-clock / reset DSL authoring 有明确 API
2. reset-release 规则能稳定回指到 DSL 源位置
3. memory policy 在 lowering / simulation / emitter 中语义一致
4. 新增覆盖：
   - 单时钟 / 多时钟
   - sync / async / async-assert-sync-release
   - single-port / dual-port memory
   - read-during-write policy

---

## 7. Phase P2: 类型系统与协议/通道增强

### 7.1 目标

让 DSL 更适合真实控制器、互连、SIMD/NPU datapath，而不是只靠位宽和 operator overloading 硬撑。

### 7.2 主要工作

#### A. 类型系统

优先引入：

1. enum 状态类型
2. packed struct / field access
3. fixed-point 类型
4. lane-vector / SIMD-friendly 类型

可延后但要预留设计空间：

1. packed union
2. 参数化 interface type

#### B. protocol / channel

把以下对象做成更统一的一等公民：

1. ready-valid channel
2. request-response channel
3. CSR / register-bank interface
4. streaming packet / framed stream channel

并为其配套：

1. protocol lint
2. auto-connect helper
3. Python-UVM adapter
4. SV/UVM collateral adapter
5. CDC recommendation hook

### 7.3 主要代码触点

1. `rtlgen_x/dsl/core.py`
2. `rtlgen_x/dsl/protocols.py`
3. `rtlgen_x/dsl/pipeline.py`
4. `rtlgen_x/verify/python_uvm.py`
5. `rtlgen_x/verify/uvm.py`
6. `rtlgen_x/verify/directed.py`
7. `rtlgen_x/verify/ref_runtime.py`

### 7.4 验收标准

1. 至少有一套 enum / struct / fixed-point 的稳定 authoring + lowering + emit 覆盖
2. 至少有一套 ready-valid / req-rsp channel 的 stable 支持
3. 新类型和新协议都能进入：
   - Python simulator
   - C++ backend
   - Python-UVM
   - emitted SV/UVM

---

## 8. Phase P3: source-mapped diagnostics 与 agent API

### 8.1 目标

把 DSL 从“能写、能跑”进一步提升为“能被工具精确诊断、能被 agent 稳定修改”。

### 8.2 主要工作

1. 统一 symbol table / hierarchy query API
2. 增加 connectivity query API：
   - 谁驱动某信号
   - 某寄存器在哪些 process 中被写
   - 某 memory 被哪些路径读写

3. 统一 finding / hint schema，至少覆盖：
   - CDC
   - PPA
   - verification
   - lowering diagnostics

4. 所有 finding 尽量回指：
   - module
   - signal / memory / field
   - source file
   - source line
   - 建议动作

5. trace / mismatch / hotspot 与 DSL 源位置建立稳定映射

### 8.3 主要代码触点

1. `rtlgen_x/dsl/core.py`
2. `rtlgen_x/dsl/adapter.py`
3. `rtlgen_x/verify/cdc.py`
4. `rtlgen_x/verify/uvm.py`
5. `rtlgen_x/ppa/advisor.py`
6. `rtlgen_x/sim/trace.py`

### 8.4 验收标准

1. CDC / PPA / verify 报告都能稳定回指 DSL 位置
2. agent 能通过结构化 API 查询模块层次和连接关系
3. rewrite hints 至少包含：
   - target kind
   - target name
   - source location
   - rationale
   - suggested action

---

## 9. 持续工作：标准库与工程体验

这部分不阻塞 P0-P3，但应持续推进。

### 9.1 标准库

逐步标准化：

1. pipeline primitives
2. regfile
3. arbiter
4. FIFO
5. CSR bank
6. stream adapter
7. CDC helper library

### 9.2 工程体验

逐步补齐：

1. formatting / style normalization
2. 更清晰的错误信息
3. 更完整的 example/tutorial
4. support matrix 与 tutorial 联动

---

## 10. 明确不做的事

本计划当前**不**做以下事项：

1. 不恢复第二套 DSL front-end
2. 不重新引入文档驱动多层 IR 控制面
3. 不让 `archsim` 向 DSL 显式传递结构化 IR
4. 不让 `ppa` 自动改写 DSL 代码
5. 不优先做 IDE/LSP/图形浏览器
6. 不追求“完全替代整个 Verilog 工具生态”

---

## 11. 里程碑建议

### M0: 现状收口完成

1. 单一 DSL front-end 已成立
2. native DSL 已移除
3. 文档已完成第一轮收口

### M1: 语义合同与 support matrix

完成 P0。

### M2: domain / reset / storage 一等公民

完成 P1。

### M3: 类型与协议增强

完成 P2。

### M4: agent 友好型诊断与查询

完成 P3。

---

## 12. 最终验收口径

当以下条件同时满足时，可以认为 `rtlgen_x.dsl` 的主线演化达到了阶段性目标：

1. 用户只需要理解一套 DSL front-end
2. 主 DSL construct 都有明确的 stable / partial 状态
3. 稳定特性能统一进入：
   - lowering
   - Python simulator
   - C++ simulator
   - emitted RTL
   - CDC / UVM / PPA
4. multi-clock / reset / memory / protocol 不再只是“后端补救”，而是 authoring 语义的一部分
5. 主要分析结果都能 source-map 回 DSL
6. agent 能基于结构化语义而不是纯文本猜测来修改设计

---

## 13. 建议的下一步执行顺序

按收益和风险排序，建议后续实际执行顺序如下：

1. **先做 P0**
2. **再做 P1**
3. **然后做 P3**
4. **最后补 P2**

原因是：

1. 先把语义边界和支持级别说清楚，避免继续乱长
2. 时钟 / 复位 / 存储是当前最影响真实设计可信度的基础问题
3. diagnostics / agent API 能直接提高后续迭代效率
4. 类型系统和协议增强很重要，但建立在前面三项更稳

这会让 DSL 的演化更像“收紧主线并做强闭环”，而不是“继续往语言里堆特性”。
