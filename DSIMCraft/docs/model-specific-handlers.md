# 未采用候选：模型专用门级回调

本候选已完成正确性与多负载 A/B，未获得稳定收益，未合入当前 0.13.0。候选把 0.13.0 的三个共享 DUT handler 改为按已绑定模型注册 handler。组合模型一个 eval handler；ff/latch 各有 commit、sample 两个。每个实例仍只携带 handler ID 与 cell 索引，不创建逐实例函数或闭包。模型数量决定代码体积，实例数量决定不可变 cell 表与可变状态大小。

安装时依据 cell.model 选择 handler；运行时 handler 直接调用对应 gate_sample_i / gate_eval_i，C++ 编译器可内联模型函数，消除模型函数表的间接调用，并常量化输入依赖和 latch 分支。没有要求编译器一定内联；实际收益由同输入、同 O2 的未插桩运行决定，同时保留生成字节数与编译成本。

实例原顺序创建 commit/sample/eval 进程，进程 ID、等待位置、Active/Inactive/NBA、调度预算和初始化均保持。sample 前登记 wait，ff 的数据变化仍按既有控制依赖处理；初次输出和 DFFOUT 的输入/三态依赖回退保持；latch 状态变化仍重新排队 sample。GateState 的 q/qn 保留独立语义。此变换不做组合锥融合、时钟推断、二态代数或脉冲近似。

handler 的无捕获函数与 DUT context 配对，多个 DUT 各有独立状态；安装中的 HandlerIds 临时表只交付整数 ID，回调不引用该临时表。context 生命周期、检查点、预测事务和通用 RTL Action 表沿用 0.13.0。本批运行时和所有 parser 保持原样。

证据在 [本批记录](../validation/m5-model-handlers/README.md)。性能必须同时说明工作负载与共享主机波动，SDF 实际回标、自动分区和压缩格式另按原计划推进。
