# RTLCraft 当前合同化方案的泛化性复盘

日期：2026-06-11

## 1. 背景

我们已经在 `riscv_ooo_4core` 和 `riscv64_soc` 上完成了一轮较完整的落地：

- 单 master CPU 生成
- 分层 DSL / hierarchy emission
- `ModuleContract`
- 局部 `FunctionalObjective`
- 局部 `PerformanceObjective`
- `PerfCheck`
- `contract_emit`
- `verify` 中的局部性能验证
- `rtl -> lint` 闭环

因此现在已经具备一个足够具体的样本，可以回头审视：

1. 这套方案是否有泛化性
2. 哪些能力已经是领域无关的
3. 哪些能力仍然带有明显 CPU 偏置
4. 要推广到其他设计，还需要补哪些框架能力


## 2. 结论先行

结论是：

**有泛化性，但现在的泛化性主要体现在“框架骨架”层面，而不是“领域能力完备”层面。**

更具体地说：

### 已经具备泛化性的部分

- 多层建模思想
- 合同化模块边界
- 每模块功能/性能目标
- 合同导出与追踪
- verify 中的局部静态/动态检查
- “失败定位到局部模块 + 推荐局部 knob”的闭环

这些并不依赖 CPU，本质上可以用于：

- NoC
- cache/memory
- DSP pipeline
- FFT
- NPU tile / MAC array
- GPGPU scheduler / warp datapath
- 图像 ISP chain

### 还不具备充分泛化性的部分

- 性能 check 类型还偏少
- 激励模型还很原始
- 合同语言还偏 DSL/L3 层
- verify 主要还是模块局部，不太支持跨模块事务级验证
- diagnosis 仍然偏“数值失败”，缺少更抽象的瓶颈分类
- 技能库还没有沉淀成“可复用 lowering recipe + perf recipe + verification recipe”

所以现在更准确的表述不是：

- “这套系统已经完全泛化”

而是：

- “这套系统已经形成了可泛化的框架原型，但还需要补一批中层能力，才能稳定迁移到其他设计域”


## 3. 已经证明有泛化性的机制

### 3.1 多层合同化建模

当前实践已经证明：

- L0/L1 可以表达产品和架构目标
- L3 可以承载具体模块 DSL
- `ModuleContract` 可以作为 lowering 过程中的局部边界

这一点不是 CPU 专属的。

对其他设计也成立：

- DSP: FIR / MAC / buffer / controller
- NPU: PE array / local SRAM / DMA / scheduler
- NoC: router / VC allocator / switch allocator / buffer
- FFT: butterfly / twiddle / reorder / stream control

### 3.2 局部性能驱动

我们已经把性能驱动从“后期参考目标”推进成：

- 合同的一部分
- verify 的一部分
- 局部优化的驱动

这种模式本身非常通用。

例如可以自然映射成：

- DSP: stage latency / sample throughput / buffer occupancy
- NPU: tile utilization / SRAM conflict ratio / DMA overlap
- NoC: flit latency / injection throughput / HOL blocking ratio
- GPU: warp issue rate / scoreboard stall ratio / memory divergence ratio

### 3.3 失败局部化

这点非常重要。

当前 CPU 试点里，失败已经不再表现为：

- “顶层 RTL 看起来不对”

而是：

- `L1Cache` 某个 perf check fail
- `OoOCore` 某个 structural check fail

这种失败局部化机制，正是复杂系统泛化所必需的。

没有局部化，领域越复杂，系统越不可扩展。

### 3.4 单 master + 多实例分离

我们已经修正了：

- module master 定义
- instance 命名
- hierarchy emission

这对泛化尤其关键。

因为无论是：

- 4-core CPU
- 64-tile NPU
- 16-router NoC
- 128-lane SIMD

都要求：

- 一个 master
- 多个实例
- 独立 instance map
- 独立局部配置

这是强泛化性能力。


## 4. 当前仍然偏 CPU 的地方

### 4.1 PerfCheck 语义还不够丰富

目前的 `PerfCheck.kind` 主要覆盖：

- `latency`
- `throughput`
- `duty_cycle`
- `stall_ratio`
- `structural_budget`

这对 CPU 前后端、cache、NoC 小模块已经够用了。

但对其他领域还不够。

缺少的典型类型包括：

- `occupancy`
- `utilization`
- `overlap_ratio`
- `burst_efficiency`
- `bank_conflict_ratio`
- `queue_age_bound`
- `replay_ratio`
- `fairness`
- `ordering_preserved`
- `transaction_completion_bound`

这些在 NPU / NoC / memory / GPU 场景里很重要。

### 4.2 刺激模型太原始

现在动态 perf check 里的 stimulus 主要还是：

- 固定拉高某输入
- 常量驱动
- 简单 sample cycle

这对：

- FIFO
- 小 cache
- wrapper
- 简化 backend

还勉强够用。

但对以下场景明显不够：

- burst traffic
- 多请求者竞争
- producer/consumer 失配
- DMA + compute overlap
- warp divergence
- cache probe/replay sequence

所以必须补：

- `PerfScenario`
- 可组合事务激励
- ready/valid stream driver
- request/response traffic templates

### 4.3 合同还偏 L3，不够覆盖 L1/L2/L4

现在 `ModuleContract` 主要挂在 DSL module 上。

这已经很好，但还不够。

为了真正泛化，应该让合同存在于每个 lowering 边：

- L1: architecture contract
- L2: executable behavior contract
- L3: structured DSL contract
- L4: implementation skeleton contract
- L5: RTL acceptance contract

尤其是对非 CPU 设计，很多关键错误发生在：

- L2 行为模型与 L3 DSL 不一致
- L3 到 L4 pipeline cut 不合理
- L4 到 RTL 时局部 timing 偏离

如果合同只存在于 L3，会损失很多约束力。

### 4.4 verify 还不支持跨模块事务级检查

当前 verify 的核心仍然是模块级。

这对 CPU 局部模块已经有价值。

但对很多系统级设计来说，不够：

- NoC 的端到端包传递
- DMA 请求到完成
- coherence probe 到 invalidate ack
- GPU scoreboard/stall/replay sequence
- NPU tile load/compute/store overlap

也就是说，我们还缺：

- 事务级 scenario
- 跨模块观测点绑定
- transaction trace verification
- path-level performance checks

### 4.5 diagnosis 还不够“设计师友好”

当前 diagnosis 更像：

- 一个数值没达标
- 推荐 knobs

下一阶段应该补成更接近设计分析语言：

- front-end starvation
- ROB backpressure
- arbitration hotspot
- bank conflict dominated
- refill limited
- compute under-fed
- response path over-serialized

这一步对泛化很重要，因为不同领域的设计师不一定用同一套信号语言，但会用同一类瓶颈语言。


## 5. 为了推广到其他设计，还需要补什么框架能力

下面这些能力，我认为是当前最值得补的。

### 5.1 Contract Schema 继续升级

建议新增：

- `PerfScenario`
- `ProtocolContract`
- `TransactionContract`
- `ResourceContract`
- `DiagnosisTag`

#### ProtocolContract

用于描述：

- ready/valid
- req/resp
- credit-based flow control
- cache probe/ack
- DMA descriptor / completion

如果没有协议层合同，很多领域设计只能退化为“裸信号检查”。

#### TransactionContract

用于描述：

- 请求发起
- 中间状态
- 完成条件
- 最大完成时延
- 允许乱序/不允许乱序

这对 NoC / memory / DMA / GPU / NPU 都很关键。

#### ResourceContract

用于描述局部共享资源：

- queue
- bank
- FU
- SRAM port
- crossbar output

否则性能优化永远只能靠信号占空比，表达能力不够。

### 5.2 通用激励/观测框架

建议新增一个独立层：

- `rtlgen/perf_scenarios.py`
- `rtlgen/perf_drivers.py`
- `rtlgen/perf_monitors.py`

让动态 verify 不再由单个 check 临时拼刺激。

需要支持：

- ready/valid stream source
- burst requester
- multi-initiator contention template
- memory miss / refill template
- producer-consumer mismatch template
- pipeline warmup / drain template

### 5.3 跨模块 path-level verify

建议新增：

- `PathPerfCheck`
- `TransactionPerfCheck`

用于表达：

- `ClusterTop.req -> L2.valid`
- `DMA.start -> SRAM.write_done`
- `warp_issue -> writeback_complete`
- `ingress_flit -> egress_flit`

这会大大增强 NoC / NPU / GPU 的泛化能力。

### 5.4 Lowering Recipe Library

当前很多“专业性”其实还写在 agent 或 skill 模块里，缺少统一 recipe 层。

建议引入：

- canonical lowering recipes
- perf recipes
- verification recipes

例如：

- `queue + arbiter + backpressure`
- `pipeline stage with valid/ready`
- `banked SRAM + conflict arbitration`
- `router input buffer + switch allocation`
- `tile load/compute/store overlap`

这样 agent 就不是从零生成，而是在 recipe 约束里选择和细化。

### 5.5 领域无关的 diagnosis taxonomy

建议建立统一失败标签体系：

- `underutilized`
- `backpressured`
- `serialization_limited`
- `conflict_limited`
- `latency_bounded`
- `protocol_violation`
- `ordering_violation`
- `resource_oversubscribed`

然后不同领域再映射到更具体语义。

这会让报告、自动修复、agent 约束都更统一。


## 6. 对其他设计域的直接影响

### 6.1 NoC

是最容易直接泛化的方向之一。

原因：

- 已经有 router / buffer / topology
- 很适合模块合同
- 很适合局部 perf checks
- 很需要跨模块 transaction checks

下一步只要补：

- end-to-end packet scenario
- fairness / starvation checks
- multi-router path checks

就会很自然。

### 6.2 NPU

中等偏强的泛化性。

已有框架适合：

- PE array
- local SRAM
- DMA
- scheduler

但还缺：

- overlap-oriented perf scenario
- bank conflict checks
- utilization metrics
- tile transaction model

### 6.3 DSP / FFT

非常适合泛化。

原因：

- pipeline清晰
- 吞吐/延迟目标明确
- 模块边界稳定

需要的新增能力不多，主要是：

- stream scenario
- pipeline fill/drain checks
- fixed-point precision / saturation checks

### 6.4 GPGPU / Thor 类 GPU

泛化潜力有，但需要更多中层能力。

关键缺口：

- scoreboard / replay / divergence 的事务模型
- 多 warp / 多 lane 的 scenario
- utilization / stall breakdown
- path-level completion checks

也就是说，框架方向是对的，但现有抽象还不够高。


## 7. 推荐的下一阶段路线

建议不要立刻全面铺开所有 design domain，而是按以下顺序推进。

### Phase A. 把合同体系从 CPU 样本提升为领域中立框架

优先做：

1. `PerfScenario`
2. `ProtocolContract`
3. `TransactionContract`
4. `ResourceContract`
5. diagnosis taxonomy

这是最有杠杆的基础建设。

### Phase B. 选一个 CPU 之外但结构清晰的领域试点

我建议优先选：

- `skills/noc`
  或
- `skills/dsp`

原因：

- 比 GPU/NPU 简单
- 比纯 CPU 更能检验泛化
- 能比较快看出框架设计是否真通用

### Phase C. 建立 recipe 层

在 skill 之外建立：

- lowering recipe
- perf recipe
- verify recipe

把“专业性知识”从个别模块实现中抽出来。

### Phase D. 最后再挑战 NPU / GPGPU

那时我们会更有把握，而不是一上来就在高复杂度领域里找不到边界。


## 8. 最终判断

当前方案已经证明：

- 它不是只能服务 CPU 的一次性脚手架
- 它具备成为通用专业生成框架的核心骨架

但要真正泛化，必须继续补：

- richer contract language
- scenario/driver/monitor framework
- transaction/path-level verification
- reusable lowering/perf/verify recipes
- unified diagnosis taxonomy

所以最准确的结论是：

**我们已经跨过了“有没有方向”的阶段，进入了“如何把这套方向从 CPU 样本提炼成领域通用框架”的阶段。**

这一步的核心任务，不再只是继续堆模块，而是把：

- 已经在 CPU 上证明有效的方法

抽象成：

- 其他设计域也能复用的能力和框架。
