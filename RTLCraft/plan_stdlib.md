# Plan Stdlib: Verilog Readability + Protocol / Component / VIP Standard Library

## 1. 背景

当前 `rtlgen_x` 已经具备：

1. DSL authoring
2. lowering 到 executable model
3. Python / C++ 仿真
4. emitted Verilog / SystemVerilog
5. Python-UVM / SV-UVM collateral
6. PPA / CDC / cosim 分析能力

但还有两个非常实际的问题没有被系统性收口：

1. **DSL 生成的 Verilog 是否足够可读，是否像人写的 RTL，而不是“机器拼出来的文本”**
2. **基础协议、基础组件、协议验证 VIP 是否已经形成可复用、可分级声明状态的标准库**

这两个问题本质上是同一件事的两面：

1. 如果 DSL 只能生成“语义对但文本难读”的 RTL，那么 agent 和人都很难 review、debug、handoff
2. 如果协议 / 组件 / VIP 只是零散 helper，而不是统一标准库，那么 DSL 的复用和验证闭环就很难稳定

但除此之外，前面 DSL 主线里还有几类**尚未完全收口**的工作，不能因为进入 stdlib 阶段就被遗忘：

1. multi-clock / reset / storage 语义仍有 `partial` 边界
2. 类型系统还缺 enum / struct / fixed-point / lane-vector
3. protocol/channel 还没有完全 first-class 化
4. finding / hint schema 还未在 CDC / PPA / verify 间完全统一
5. agent-friendly API 虽已有 hierarchy / connectivity query 起步，但 symbol/query/hint 体系仍未全部完成
6. stdlib 的很多对象还没有形成统一 support matrix 和 regression contract

因此，本计划不是替代前面的 DSL 计划，而是把：

1. **前面尚未完成但与 stdlib 直接相关的基础工作**
2. **Verilog 可读性**
3. **协议 / 组件 / VIP 标准库**

放到同一张执行图里统一推进。

---

## 2. 总体目标

本计划的目标不是单纯“再加几个协议类”，而是把 `rtlgen_x` 补强成一个：

1. **默认产出 review-grade RTL** 的 DSL / emitter 系统
2. **自带基础协议 / 基础组件 / 基础 VIP 标准库** 的硬件构造系统
3. **完成前面未闭环的 DSL 基础语义收口** 的工程框架
4. **对 agent 友好、对人工 review 友好、对验证闭环友好** 的工程框架

一句话目标：

**让 `rtlgen_x` 既能生成好读的 RTL，又能把常用协议/组件/VIP 变成可直接使用、可直接验证、可直接扩展的标准库。**

---

## 3. 与前面计划的关系

本计划吸收并继续推进以下尚未完成的主线工作：

### 3.1 来自 `plan0622.md` 的未完项

1. multi-clock 支持边界继续明确
2. reset-release / CDC pattern 识别继续增强
3. area/power PPA 与协议/组件对象之间的可解释性继续增强

### 3.2 来自 `plan_dsl_0623.md` 的未完项

1. 时钟 / 复位 / 存储语义一等公民化尚未全部完成
2. 类型系统增强尚未开始系统推进
3. protocol/channel first-class abstraction 仍是主任务
4. source-mapped diagnostics 与统一 finding/hint schema 仍未全部完成
5. stdlib 仍缺统一支持矩阵和统一 public surface contract

### 3.3 本计划的角色

本计划将上面这些未完项按照“可读 RTL + stdlib + VIP”主线重新组织，并继续执行。

---

## 4. 当前基线

### 3.1 已有能力

当前代码里已经有一些 stdlib 雏形，但还没有完成“产品化收口”：

1. `rtlgen_x/dsl/codegen.py`
   - 已有模块头注释、端口表、`always_comb` / `always_ff` / `always_latch`
   - 已有 source-map 能力
   - 已有一部分表达式拆分和安全 emit 逻辑

2. `rtlgen_x/dsl/protocols.py`
   - 已有 `Bundle`
   - 已有 `AXI4Stream` / `APB` / `AXI4Lite` / `AXI4` / `AHBLite` / `Wishbone`
   - 但大多还停留在“信号集合定义”层

3. `rtlgen_x/dsl/lib.py`
   - 已有 `FSM` / `SyncFIFO` / `AsyncFIFO` / pipeline / handshake 相关结构
   - 但成熟度不均匀，部分能力仍偏 placeholder 或 partial

4. `rtlgen_x/verify/protocols.py`
   - 已有 APB / AXI-Lite / AXI4 / AXI-Stream / Wishbone / CSR / interrupt 的
     sequence builders 和 reference model helpers
   - 但和 DSL 协议对象之间的统一程度还不够

5. `rtlgen_x/verify/python_uvm.py` 与 `rtlgen_x/verify/uvm.py`
   - 已有 Python-UVM
   - 已有 generated SV/UVM runtime bundle
   - 但还不是“协议 VIP 标准库”的形态

### 4.2 主要问题

#### A. Verilog 可读性问题还没有成为正式 contract

当前 emitter 更多是在保证：

1. 语义正确
2. 语法安全
3. 可仿真 / 可综合

但还没有正式定义：

1. 什么叫 **review-grade readable RTL**
2. 哪些命名 / 分块 / 排版 / 注释 / 结构保持是必须保证的
3. emitter 应该如何在“语义正确”和“人工可读”之间做结构化取舍

#### B. 协议 / 组件 / VIP 还没有被收成一套标准库

当前已有不少材料，但还存在：

1. DSL protocol object、verify helper、UVM collateral 分散在不同层
2. 没有一份统一的 stdlib taxonomy / support matrix
3. 没有明确哪些是 `stable`，哪些只是 `partial`
4. 缺少一组面向 agent 的统一命名和统一配置接口

#### C. DDR 等复杂协议没有明确 scope

像 DDR 这类对象非常容易“做得很大但不可闭环”。如果 scope 不先收住，就会变成：

1. 只做端口 bundle，没有行为语义
2. 只做 VIP 名字，没有可运行模型
3. 想做 full PHY / training / JEDEC 细节，结果工程过重

因此 DDR 必须先明确阶段目标。

#### D. 前面未完成的基础语义问题仍会直接影响 stdlib

如果下面这些基础项不继续推进，stdlib 会很难真正稳定：

1. multi-clock object 在 verify / generated collateral 上仍有 `partial`
2. reset / reset-release policy 还没有对所有 stdlib 组件形成统一 contract
3. storage policy 在 emitted RTL 侧仍有部分未闭环项
4. finding / hint schema 还没有统一到足以支撑 stdlib 级 triage
5. 类型系统不足会直接拖累协议/组件的可读性和结构化分析

---

## 5. 核心原则

### 4.1 可读性不是 cosmetic，而是输出质量 contract

Verilog 可读性不是“生成完以后再格式化一下”，而应该是 emitter 的一等目标。

要明确保证：

1. 命名稳定
2. 层次尽量保留
3. 结构分块清晰
4. 大表达式可拆解
5. 端口和协议相关逻辑能按语义分组
6. 文档和源位置可以回指

### 4.2 review RTL 和 compact RTL 分开

不要只保留一种“尽量短”的 emitted RTL。

至少应有两类 profile：

1. **review profile**
   - 优先人工可读
   - 更稳定的中间信号命名
   - 更清晰的分块和注释

2. **compact profile**
   - 优先简洁
   - 适合最小文本输出、快速导出

默认对 agent / review / debug 应优先使用 review profile。

### 4.3 标准库必须 DSL-first，而不是文本模板-first

协议 / 组件 / VIP 的标准库对象首先应是 DSL 语义对象，而不是一堆：

1. Verilog 模板
2. UVM 模板
3. ad hoc helper

正确顺序应是：

```text
DSL protocol/component object
  -> executable semantics
  -> readable emitted RTL
  -> Python verify adapter
  -> SV/UVM collateral / VIP
```

### 4.4 每个 stdlib 条目都必须有 closure 定义

一个协议、组件或 VIP 只有在满足下面条件后，才能称为 `stable`：

1. 有 DSL authoring object
2. 有 lowering / simulator closure
3. 有 emitted RTL closure
4. 有至少一种 verify closure
5. 有文档和 regression lock

### 5.5 DDR 先做 controller-side functional/timing scope

本轮不追求 full PHY / calibration / analog training 级别 DDR。

优先做：

1. controller-facing interface
2. behavioral memory model
3. command / data / refresh / timing rule checker
4. Python VIP
5. SV/UVM VIP 骨架

---

### 5.6 stdlib 建设不能绕过基础语义收口

对于 ready-valid / AXI / DDR / FIFO / CSR / AsyncFIFO 这类对象，如果：

1. clock/reset semantics 不清楚
2. storage semantics 不清楚
3. finding/hint/schema 不清楚

那么它们就只能停留在“能写对象定义”，无法成为真正的 stable stdlib。

因此本计划把这些基础语义项视为 stdlib 建设的前置和并行工作，而不是可跳过事项。

---

## 6. 交付物

本计划最终希望交付以下几类能力：

1. **Readable Verilog contract**
2. **Emitter readability profiles**
3. **Clock / reset / storage semantic closure for stdlib-facing features**
4. **Protocol / channel standard library**
5. **Component standard library**
6. **Verification VIP standard library**
7. **Type-system upgrades needed by stdlib**
8. **Unified finding/hint schema for stdlib users and agents**
9. **Stdlib support matrix + tutorials + examples**

---

## 7. Workstream A: Verilog 可读性收口

### A1. 定义 readable RTL contract

先把“什么叫好读”写成明确规则，而不是感受性描述。

建议 contract 至少包括：

1. 尽量保留 authored module / signal / instance naming
2. declaration ordering 稳定
3. params / localparams / ports / memories / state / wires / instances / logic 分区清晰
4. `always_comb` / `always_ff` / `always_latch` 语义明确
5. 长表达式和深 mux chain 不直接糊成一行
6. protocol / bundle 相关信号尽量成组出现
7. review 输出默认带模块头文档和必要结构注释
8. 同一设计重复 emit 时文本 diff 稳定

### A2. 增加 emitter profile

建议在 emitter 层明确支持：

1. `review`
2. `default`
3. `compact`

建议行为：

#### `review`

1. 更保守地拆分大表达式
2. 优先保留中间信号
3. 对 protocol / state / memory / pipeline logic 分段留白
4. 允许自动注入少量结构化注释
5. 可选 source-map 注释，但默认不要让它污染主阅读面

#### `default`

1. 兼顾可读性和简洁性
2. 作为日常默认输出

#### `compact`

1. 文本最少
2. 减少注释和中间命名
3. 不作为主要 review 输出

### A3. 做“readability pass”，而不是只在 emit 时即时拼接

建议在 codegen 层明确拆出一层 review-oriented normalization / formatting pass。

这层负责：

1. 稳定声明顺序
2. 长表达式拆分
3. 命名规范化
4. port / bundle grouping
5. 状态机输出的可读 localparam / state naming
6. memory / array block 的结构化注释

### A4. 命名与结构保持策略

为避免“机器味”，建议默认策略是：

1. 保留 authored signal 名
2. 临时信号命名尽量从目标语义派生，而不是 `_tmp17` 这类匿名形式
3. 复杂表达式拆分时优先命名为：
   - `<target>_next`
   - `<target>_sum`
   - `<target>_addr`
   - `<target>_sel`
   - `<instance>_<port>`
4. flatten 后也尽量保持层次前缀可读，而不是哈希式名字

### A5. 注释与文档传播

建议增强：

1. `ModuleDoc`
2. block description
3. timing / protocol note
4. interface / bundle 文档

让 emitted RTL 天然带上：

1. 模块用途
2. 关键时序 / 协议说明
3. 端口表
4. pipeline / state / memory 的必要说明

### A6. Readability lint / regression gate

为避免“看起来好像更可读，但没有稳定标准”，应加入 readable-RTL gate。

建议检查：

1. 最大行长
2. 深层嵌套 ternary / mux chain 数量
3. 匿名临时信号比例
4. 过长 assign 语句数量
5. bundle/port 分组是否被打散
6. 多次 emit 的 diff 稳定性

建议为代表性模块建立 golden-output regression：

1. `sfu`
2. `rv32`
3. `sram256k`
4. `gpu_sm` 中的一个代表模块
5. 一个带 AXI/APB 的控制器

### A7. 验收标准

1. review profile 输出可直接用于人工 review
2. repeated emit 结果稳定
3. 不需要人工大改命名和排版才能阅读
4. golden-output regression 锁定关键模块文本结构

---

## 8. Workstream B0: 前置基础语义收口

这一部分是把前面未完成、但会直接影响 stdlib 的基础工作显式并入本计划。

### B0.1 multi-clock / reset / reset-release

继续推进：

1. stdlib 组件的 clock domain API 统一
2. stdlib 组件的 reset semantics contract 统一
3. reset-release CDC rule 对 stdlib primitive 全覆盖
4. generated UVM / local verification 中对 multi-clock stdlib 对象的支持边界继续清晰化

优先对象：

1. `AsyncFIFO`
2. CDC synchronizer primitives
3. ready-valid / req-rsp channel crossing helper
4. memory wrapper with cross-domain control/status

### B0.2 storage semantics closure

继续推进：

1. stdlib memory wrapper 对 read/write/read-during-write/byte-enable/latency 的统一 contract
2. emitted RTL 侧剩余 storage `partial` 项逐步收口
3. protocol-facing memory component 与 storage metadata 对齐

优先对象：

1. `SinglePortRAM`
2. `SimpleDualPortRAM`
3. regfile / SRAM wrapper
4. FIFO internal storage contract

### B0.3 DSL-only API 收口继续强化

继续坚持：

1. public verify / PPA / UVM / stdlib-facing helper 只接受 DSL `Module` 或 `LoweredDslModule`
2. raw `SimModule` 仅留给低层执行对象
3. 新 stdlib / VIP API 不引入旁路入口

### B0.4 finding / hint schema 统一

把前面未完成的 P3 主线并入本计划：

1. CDC
2. PPA
3. verify
4. protocol checker
5. readability gate

应尽量统一输出：

1. target kind
2. target name
3. module / hierarchy path
4. source file / line
5. rationale
6. suggested action

### B0.5 验收标准

1. stdlib 关键对象不再依赖模糊的 clock/reset/storage 语义
2. stdlib 相关 finding 能统一回指 DSL 位置
3. public API 边界不再因为 stdlib 扩张而变乱

---

## 9. Workstream B: Protocol / Channel 标准库

### B1. 先统一 taxonomy

建议把 stdlib protocol/channel 分成五类：

1. **基础 channel**
   - ready-valid
   - request-response
   - packet / framed stream
   - memory request / response

2. **片上低复杂度总线**
   - APB
   - AXI4-Lite
   - Wishbone
   - AHB-Lite

3. **高吞吐流协议**
   - AXI4-Stream
   - generic packet stream

4. **高复杂度事务总线**
   - AXI4 full

5. **外部 memory/controller 协议**
   - DDR controller-side interface

### B2. 基础 channel first-class 化

优先把下面对象做成真正的一等公民：

1. `ReadyValidChannel`
2. `ReqRspChannel`
3. `PacketStream`
4. `MemoryReqRspChannel`

它们应自带：

1. connect / flip / auto-wire helper
2. protocol lint
3. tracing / naming convention
4. CDC recommendation hook
5. Python-UVM / SV-UVM adapter 基础

### B3. 优先收口已有协议

现有 `rtlgen_x/dsl/protocols.py` 中已经存在的协议，应优先从“signal bundle”收口成“semantic protocol object”：

1. `APB`
2. `AXI4Lite`
3. `AXI4Stream`
4. `Wishbone`
5. `AHBLite`
6. `AXI4`

建议推进顺序：

1. `APB`
2. `AXI4Lite`
3. `AXI4Stream`
4. `Wishbone`
5. `AHBLite`
6. `AXI4`

原因：

1. 前四项更容易先完成 DSL + verify + VIP 闭环
2. `AXI4 full` 最复杂，应放到后期

### B4. DDR 的分阶段目标

DDR 不建议一开始就做 full PHY 级 scope。

建议分三阶段：

#### Phase D1: controller-side DSL object

1. DDR 命令 / 地址 / 数据 interface object
2. 初始化、读写、刷新等基本事务抽象
3. 明确只覆盖 controller-facing semantics

#### Phase D2: behavioral model + timing checker

1. Python behavioral memory model
2. 基本时序约束检查
3. refresh / activate / precharge / burst 的功能级验证

#### Phase D3: VIP / UVM adapter

1. Python VIP
2. SV/UVM VIP 骨架
3. directed / constrained-random 事务支持

### B5. 验收标准

1. 每个 `stable` 协议对象都有 DSL + sim + emit + verify coverage
2. protocol sequence helper 和 DSL protocol object 命名统一
3. protocol/channel 可直接被 CDC / verify / UVM 消费

---

## 10. Workstream C: Component 标准库

### C1. 标准组件范围

建议把组件库标准化为以下核心集合：

1. skid buffer
2. pipeline register / pipeline stage
3. SyncFIFO
4. AsyncFIFO
5. regfile
6. SRAM wrapper / simple dual-port RAM helper
7. arbiter
8. stream width adapter
9. CSR bank
10. request/response queue
11. CDC synchronizer primitives

### C2. 组件必须和 channel / protocol 配套

不要只做“裸组件”。

例如：

1. FIFO 要知道自己是给 ready-valid / packet stream / AXI-Stream 用的
2. CSR bank 要和 APB / AXI-Lite / Wishbone 适配
3. AsyncFIFO 要和 CDC checker / reset-release 规则协同

### C3. 组件交付标准

每个组件至少需要：

1. DSL authoring object
2. executable behavior
3. emitted RTL
4. directed verification
5. 至少一类 protocol-aware verification path
6. 文档与例子

### C4. 现有组件的处理策略

现有 `rtlgen_x/dsl/lib.py` 不应整体推倒重来，而应：

1. 盘点已有条目
2. 给每个条目标 `stable / partial / experimental`
3. 对成熟条目收口
4. 对 placeholder 条目明确 scope 或下线

### C5. 验收标准

1. 核心组件集有清晰 support matrix
2. ready-valid / register-bank / memory-wrapper 类组件可直接复用
3. AsyncFIFO / CDC primitive 与 CDC 分析协同

---

## 11. Workstream D: VIP 标准库

### 当前进展补充

本轮已经新增统一 protocol VIP registry 入口，作为 Python VIP / protocol
helper 的公共查找面：

1. `rtlgen_x.verify.get_protocol_vip_kit(...)`
2. `rtlgen_x.verify.list_protocol_vip_kits()`
3. `rtlgen_x.verify.PROTOCOL_VIP_KITS`

当前已纳入统一 kit 的协议包括：

1. `ReadyValid`
2. `ReqRsp`
3. `APB`
4. `AXI4Lite`
5. `AXI4Stream`
6. `Wishbone`
7. `WishboneClocked`
8. `AHBLite`

每个 `ProtocolVipKit` 当前统一暴露：

1. transaction type
2. sequence builder
3. reference-model builder
4. trace checker

同时，这轮已经补上第一条 generated-UVM bridge：

1. `rtlgen_x.verify.protocol_transfers_to_uvm_sequence_steps(...)`

这意味着 APB / AXI4-Lite / WishboneClocked 控制面事务，以及轻量
AXI4-Stream 流式事务，现在都可以只写一份 protocol transfer，然后同时复用于：

1. local Python-UVM sequence generation
2. generated SV/UVM directed smoke sequence generation

当前 bridge 的边界是刻意收住的：它只复用 stimulus 形状，generated UVM 的
scoreboard 闭环仍然依赖 emitted DUT/reference-model 路径，而不是直接搬运
Python-UVM `expected` 字典。

同时补齐了 `AXI4Stream` 对称的 `axistream_reference_model(...)` 入口，后续可
继续沿这套 registry 扩展 generated SV/UVM VIP。

### D1. VIP 分层

建议把 VIP 分成三层：

1. **Python VIP**
   - 事务类型
   - sequence builders
   - reference models
   - protocol checkers
   - coverage helper

2. **Generated SV/UVM VIP**
   - transaction
   - driver
   - monitor
   - scoreboard adapter
   - env / test / sequence template

3. **Cross-runtime closure**
   - local Python simulator
   - compiled simulator
   - emitted RTL + iverilog smoke
   - remote VCS/UVM

### D2. 优先顺序

建议 VIP 标准库推进顺序：

1. APB VIP
2. AXI4-Lite VIP
3. AXI4-Stream VIP
4. Wishbone VIP
5. AXI4 full VIP
6. DDR controller-side VIP

### D3. Python VIP 和 SV/UVM VIP 统一命名

协议 VIP 不应出现 DSL / Python / UVM 三套完全不同的话语体系。

应统一：

1. transaction naming
2. field naming
3. config naming
4. protocol state naming
5. error / finding naming

### D4. protocol checker 与 scoreboard adapter

每类 VIP 除 sequence 外，还要有：

1. protocol checker
2. reference model / scoreboard adapter
3. failure triage 格式
4. coverage summary

### D5. 验收标准

1. 至少 APB / AXI4-Lite / AXI4-Stream / Wishbone 有完整 Python VIP
2. 至少 APB / AXI4-Lite / AXI4-Stream 有 generated SV/UVM VIP 闭环
3. DDR 至少完成 controller-side Python VIP + behavioral memory model

---

## 12. Workstream E: 类型系统与 stdlib 结合推进

这部分来自前面 `plan_dsl_0623.md` 的未完成项，但这里仅保留**直接服务 stdlib 与 readable RTL 的部分**。

### E1. 优先类型项

建议优先引入：

1. enum 状态类型
2. packed struct / field access
3. fixed-point 类型
4. lane-vector / SIMD-friendly 类型

### E2. 为什么这部分必须并入 stdlib 计划

因为下面这些能力都强依赖类型系统：

1. readable RTL 的字段级命名与结构保持
2. protocol bundle 的结构化表达
3. CSR / request / response / packet 的字段级语义
4. VIP transaction 与 DSL object 的统一映射

### E3. 推进原则

1. 不做只存在于 authoring 层、不能闭环的类型
2. 新类型必须尽快进入 lowering / Python sim / C++ sim / emitted RTL
3. 至少 enum / struct 应优先用于 protocol/channel/component/VIP 对象

### E4. 验收标准

1. 至少一套 enum / struct 稳定进入 stdlib 核心对象
2. emitted RTL 能保留足够好的字段级可读性
3. verify / VIP 能消费结构化字段语义

---

## 13. Workstream F: 文档、矩阵、样例

### E1. 新文档

建议新增：

1. `rtlgen_x/STDLIB_SUPPORT_MATRIX.md`
2. `rtlgen_x/TUTORIAL_STDLIB.md`
3. `rtlgen_x/TUTORIAL_READABLE_VERILOG.md`

### E2. Support matrix

对每个协议 / 组件 / VIP 条目，至少标：

1. authoring
2. lowering
3. Python sim
4. C++ sim
5. emitted RTL
6. Python verify
7. SV/UVM
8. CDC / PPA consumption
9. status: `stable / partial / experimental`

### E3. Worked examples

建议至少做以下样例：

1. ready-valid + skid buffer + FIFO
2. APB CSR bank
3. AXI4-Lite register slave
4. AXI-Stream packet datapath
5. Wishbone SRAM wrapper
6. DDR controller-side behavioral example

---

## 14. 建议的代码触点

本计划预计主要涉及：

1. `rtlgen_x/dsl/codegen.py`
2. `rtlgen_x/dsl/core.py`
3. `rtlgen_x/dsl/protocols.py`
4. `rtlgen_x/dsl/lib.py`
5. `rtlgen_x/verify/protocols.py`
6. `rtlgen_x/verify/python_uvm.py`
7. `rtlgen_x/verify/uvm.py`
8. `rtlgen_x/verify/cdc.py`
9. `rtlgen_x/verify/*` 中 finding/report helpers
10. `rtlgen_x/ppa/*`
11. `rtlgen_x/tests/test_dsl_import.py`
12. `rtlgen_x/tests/test_verify_uvm.py`
13. `rtlgen_x/tests/test_python_uvm.py`
14. `rtlgen_x/tests/test_cdc.py`
15. `rtlgen_x/tests/test_ppa.py`
16. `rtlgen_x/tests/` 中新增 readable RTL / stdlib regression

---

## 15. 执行顺序

建议按下面顺序推进：

### M0. 盘点与 contract

1. 盘点当前协议 / 组件 / VIP / emitter 能力
2. 写出 readable RTL contract
3. 写出 stdlib taxonomy
4. 确定 support levels

### M1. 基础语义前置收口

1. multi-clock / reset / reset-release 面向 stdlib 的 contract
2. storage semantics 面向 stdlib 的 contract
3. DSL-only public API 边界继续收紧
4. finding/hint schema 打底统一

### M2. Readable Verilog first

1. emitter profiles
2. readability pass
3. golden RTL regression
4. readability lint / metrics

### M3. Channel / protocol core

1. ready-valid
2. req-rsp
3. APB
4. AXI4-Lite
5. AXI4-Stream
6. Wishbone

### M4. Component stdlib

1. FIFO / skid / pipeline / regfile / CSR / SRAM wrappers
2. CDC-related primitives
3. protocol-aware adapters

### M5. VIP stdlib

1. Python VIP 收口
2. SV/UVM VIP 收口
3. local / remote closure

### M6. 类型系统与 stdlib 结合

1. enum
2. packed struct
3. fixed-point / lane-vector 评估与首轮落地

### M7. AXI4 full + DDR

1. AXI4 full transaction semantics
2. DDR controller-side interface
3. DDR behavioral model
4. DDR VIP phase-1 closure

---

## 16. 当前阶段不做的事

本计划当前不做：

1. full DDR PHY / analog / training 建模
2. 一次性覆盖所有长尾协议
3. 只靠文本模板堆 protocol/VIP
4. 只优化 emitted RTL 的“表面格式”，而不处理命名和结构问题
5. 引入新的重型控制面

---

## 17. 最终验收口径

当下面条件同时满足时，可以认为这轮 stdlib / readable RTL 计划达到阶段性目标：

1. DSL emitted RTL 默认已经是 review-grade，而不是明显的机器拼接文本
2. review profile 和 compact profile 边界清晰
3. 与 stdlib 直接相关的 multi-clock / reset / storage 基础语义已继续收口
4. 基础 channel / APB / AXI4-Lite / AXI4-Stream / Wishbone 形成标准库
5. 核心组件库形成 stable/partial 支持矩阵
6. Python VIP 与 generated SV/UVM VIP 至少在核心协议上闭环
7. DDR 至少有 controller-side DSL object + behavioral model + 初级 VIP 路线
8. enum / struct 等关键类型开始服务 stdlib 主线
9. finding/hint/schema 对 stdlib 相关问题有统一输出
10. 所有这些能力都有 regression lock 和明确文档

---

## 18. 建议的第一轮落地动作

如果按价值 / 风险排序，建议第一轮实际执行顺序是：

1. **先把 stdlib 相关的基础语义缺口继续收口**
2. **再做 readable RTL contract + emitter review profile**
3. **然后收口 ready-valid / APB / AXI4-Lite / AXI4-Stream / Wishbone**
4. **再把 verify.protocols / Python-UVM / generated UVM 收成 protocol VIP**
5. **最后进入 AXI4 full、DDR、以及更强类型系统**

原因：

1. 如果 clock/reset/storage/finding 这些基础项不继续收口，后面 stdlib 会出现“对象有了、闭环不稳”的问题
2. 如果 emitted RTL 不够可读，后面标准库即使功能上可用，review 和 adoption 也会受阻
3. 基础协议先标准化，能最快拉动组件库和 VIP 一起收口
4. AXI4 full 和 DDR 都是高复杂度条目，应该建立在前面的统一接口和统一方法之上
