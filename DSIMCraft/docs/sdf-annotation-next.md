# 下一批：SDF 回标与并行编译接入

此文件记录下一批实施依赖，不代表已经实现。当前可运行接口见 `sdf-parser.md` 与 `parallel-and-rollback.md`。

2026-10-18 已补 [specify 模型与路径表](timing-models.md)：读取标准单元 Verilog 的 timescale、原始路径、条件/边沿、specparam 及 timing-check/pulse 声明，严格检查 Liberty 端口后建立 IOPATH 更新表。完整 flattened 输入已建立 867,982 张路径表；原始条件 SDF 与不带条件路径的模型不匹配时明确拒绝。任一方省略输入边沿的匹配，以及独立的模型/SDF corner，已用新 VCS 微例确认。仍须将这些表编译成实际路径因果、条件、脉冲和逐接收 pin 互连状态，不能把路径表检查当作完成一般回标。

## 统一时间精度：0.10.0 已接入 RTL

RTL 过程延迟、`$time` / `%t` 与 VCD/DWF 已接入模块 timescale 和实际实例的全局精度；默认 1s/1s、CLI 可覆盖，独立小数 literal 按模块精度舍入。实现与验证边界见 [时间语义](time-semantics.md)。SDF 十进制换算已复用，0.11.0 已加入端点绑定与 corner 数值预览，接下来仍需实现实际回标后的路径/脉冲语义。

后续 SDF 回标验收包含不同模块 1ns/1ps 与 10ps/1ps、SDF 1ns 下 0.125、舍入边界、空 corner/min/typ/max 选择、负 INCREMENT 合并及时间溢出。RTL 默认策略已明确；回标需继续区分 SDF TIMESCALE、模块时间精度与仿真 tick。

已新增 [实际延迟 VCS 参考](../validation/m4-sdf-delay-probes/README.md)：corner、目标 10ps 精度的 0.125→130ps、负 INCREMENT 合并、12 种四态 transition、两个接收 pin 的独立 INTERCONNECT 与脉冲选项。它们是下一实现的独立 oracle，尚非 native 时序仿真通过。微例中仅 transport 名称的选项仍拒绝窄模块路径脉冲，而 pulse_r/e=0 保留两个沿；实际模式须按明确对象和阈值实现，不能照选项名称猜测。

## 门级保留按需名称与 pin 绑定

0.11.0 已在独立 gate parser 生命周期内按需导出名称池、实例路径索引、层次端口和 pin 方向。普通零延迟仿真不建立时序索引。绑定检查可只使用 Liberty 的 pin 信息，允许大于 64 位的顶层端口；此拓扑模型禁止生成可执行代码。实现边界见 [SDF 绑定](sdf-binding.md)。

绑定顺序：选定 DUT scope → 规范化 SDF divider/转义但保持路径组件 → INSTANCE / CELLTYPE 校验 → 标量/位选 pin 解析 → 具体 timing arc 匹配。精确匹配、通配 INSTANCE、空顶层 INSTANCE 分别统计；未知实例、类型不符、错 pin、歧义已有严格诊断；重复/覆盖仍需在实际 arc 数据库中加入明确策略。失败时不提交部分回标，输出匹配/未匹配摘要。

IOPATH 与 INTERCONNECT 需要不同的存储。IOPATH 绑定 cell 内输入到输出驱动；INTERCONNECT 绑定源 pin 到接收 pin，不能把一个 net 的所有扇出统一改成相同延迟。接收 pin 应分配自己的延迟信号，保留其余驱动/别名与无延迟连接的区别。

## 延时驱动与取消

新增可快照的延迟赋值/驱动事件，保存 payload、稳定顺序、驱动身份和取消 generation；检查点须恢复全部待发生事件及代数状态。路径按输入边沿、条件和目标 transition 选择延迟，先限定明确支持的组合条件语法，不能把当前 parser 中保留的 opaque COND 默认视为真。

惰性取消和脉冲 reject/xlimit 需要独立微例；先选明确定义的受限模式，再扩完整语义。不可先丢弃 RETAIN、COND、timing checks 后声称完成 SDF 对齐。Liberty/SPEF 计算延迟是另一路线，不替代标准 SDF 回标。

timing checks 单独跟踪参考/数据事件、setup/hold 窗口、复合检查和 notifier，违例打印/波形等效果同样参加预测提交。先做无竞争参考激励，以 VCS 默认选项和同一 cell model 比对。

## 从手工并行到编译器接入

当前 `ConservativeSim` 要求每分区独立 Sim、明确正延迟通道。门级编译器需先生成读写集合与依赖图，将零延迟强连通分量、别名、多驱动和共享存储边界保留在同一区域；对可跨分区的正延迟边生成消息适配与名称映射。

自动划分必须同时约束跨区消息量、负载均衡与 lookahead；极短延迟/大共享时钟可能使同步成本超过收益。全局 finish/错误传播、单一有序波形出口、可复制随机状态、DPI/VPI/文件提交协议是一般模型并行运行前的依赖。当前并行 API 遇分区内 finish 直接失败，不做不完整的全局终止近似。

预测事务先只用于可隔离边界的局部窗口。跨分区乐观推进还需要因果错误检测、已发送消息撤销/反消息、提交安全界限和旧状态回收，不能直接把多个 `predict_until` 放进线程池就宣称实现。优先测保守路线，只有实际设计的 profile 证明值得时再实现这些成本。

每次性能验收保留输入与库/SDF SHA、线程数/分区、时间精度、波形范围、编译选项、预热与轮换多次运行、CPU/墙钟/RSS/消息量。先核对完整事件或明确选择的 settled 观测边界，再解释加速比。

原始数值绑定已补齐：设置 `numeric_preview=false` 可跳过 tick 预览，回调明确给出 `unit_fs` 与 `corner`。没有自动建立 arc 数据库或施加延迟。新 VCS 微例纠正了原先数学暂存层的合并策略：须逐项按 model precision 量化、合并并对负路径结果夹零，而非全部累加后舍入；负 timing checks 必须单独处理。详见[兼容性更正](../experiments/sdf_annotation/VCS_COMPATIBILITY.md)。后续接入逐接收 pin 信号和有状态路径选择；不能将空的预览向量误作缺失原始值。
