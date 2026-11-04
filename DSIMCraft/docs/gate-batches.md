# 组合单元批量执行

`--gate-batch` 是显式开启的单线程编译模式，适用于现有门级功能、SDF 路径/检查和波形入口。RTL 激励仍由独立 RTL parser 编译，门级图仍来自结构 parser。

```sh
build/dsim --gate-netlist net.v --gate-top dut --liberty cells.lib \
  --gate-batch tb.v -o simv
```

编译器给组合 handler 生成原生模型 switch，并在 handler 内消费同一 handler/context 的 Active FIFO 连续前缀。每次求值仍读取实际输入、重新装载 fixed wait，并按原单元输出顺序调用相同的四态驱动函数。队首一旦是另一个 handler、RTL 进程、wake 或延迟交付，就返回通用调度器；没有挑选后面的任务或提前求值未就绪门。

逐事件的 `step()`、清 queued、延迟失效清理和并行输入到达保留原顺序；预算超限发生在弹出相应事件之前。Inactive/NBA、时间推进与波形 tick 使用原运行循环。顺序模型的 sample/commit 处理没有合并。检查点没有跨越半个 batch 暂停；窗口边界仍由原调度器在该时间的事件排空后返回，预测失败恢复原状态和未提交效果。

这项变换减少的是调度入口与上下文加载，以及模型函数的间接分派；没有消除内部信号/驱动，没有改变多输入门、反馈或毛刺的可观察事件，也没有把设计变成稳态电路求值器。它不启用多线程。生成 IR 的 `batch_execution: true` 表示编译模式，不能替代实际收益测量。

未开启选项时，runtime 的批量方法和队首读取均被编译条件排除，原调度循环不增加批量分支。`DSIM_BATCH_PROFILE` 仅供另行编译的诊断程序统计进入次数与实际求值数；性能程序不启用该计数。

验收覆盖独立内核混合事件/到达/延迟取消/回滚和 89 个预算边界；八组实际生成程序核对完整 stdout 及 ordered/settled VCD/DWF，包含组合四态、多驱动与 alias、宽原子 copy、时序反馈、SDF INTERCONNECT/IOPATH/HOLD。两个生成程序执行了实际失败预测回放；本地内核和实际 SDF 回放程序另经 ASan/UBSan。范围和真实设计测量见[本批记录](../validation/m5-fifo-batch/README.md)。默认不启用该选项。
