# 可选近时间队列

`dsim --time-wheel top.v -o simv` 在实际生成的程序中启用近时间队列；默认仍使用稳定二叉堆。可与 RTL 过程 delay、延迟 NBA、连续赋值 delay，以及门级 SDF 的通用或 `--gate-scalar-timing` 后端组合。它只影响定时事件的存储，Active、Inactive、NBA 的执行规则和调度预算保持原有定义。

近时间窗口为 256 tick，每个时间桶保持投递 FIFO，位图定位下一非空桶，节点池复用已释放存储。窗口外事件进入按 `(time, order)` 排序的堆，在仿真时间实际前进时迁入近时间桶。空闲时间跨度很大时直接跳到下一事件，不逐 tick 扫描；接近 `uint64_t` 上界时使用时间差判定，避免窗口上界加法溢出。

清理已取消的未来事件不会推进窗口时间。队列、节点池、空闲链、位图、远时间堆及稳定顺序均属于 `Sim` 的拥有状态，随检查点复制和恢复。待交付载荷仍由现有延迟槽管理，不改变取消代际、路径选择或检查器观察点。

生成 C++ 的开头包含 `DSIM_TIME_WHEEL_ENABLED`，IR 的根对象包含 `"time_queue":"near-far"`。不开启选项时不生成该宏或 IR 字段。预处理、仅检查网表/SDF/时序模型的命令不接受该选项。

生产源码已接入该实验选项，新增百万次标准堆混合对照和十项实际运行时组合测试。实际 CLI 测试分别编译 heap/wheel：五种 RTL 延迟场景及四种 SDF 场景，逐项比较 stdout、stderr、ordered/settled 的 VCD、原始 DWF 和 Zstandard DWF，共 108 份波形；另有四份带待交付 SDF 定时器的检查点/拒绝预测重放捕获。原型与本次生产接入证据分别保存在 `validation/m5-time-wheel` 和 `validation/m5-time-wheel-integration`。

两平台各83项、六类新VCS流程及两个实际新编译器完整SDF程序各128笔已独立核对通过，见[验收结果](../validation/m5-time-wheel-integration/verification.json)。这项改动尚无 Linux 性能结论。完整 SDF 的现有计数表明该工作负载正延迟交付集中在 2–255 tick，但不能据此保证其他设计的收益。时间轮也不会消除单元求值、接收端进程或路径进程；后续仍需减少 SDF 中间调度。独立计时通过前保持默认关闭，验证进度以接入目录的原始日志和核对结果为准。


## 稳定堆后端

默认定时队列保留二叉堆，可选候选为四叉/八叉堆，比较键均为 `(time, order)`。同一时间按投递顺序进入既有 Active/NBA 队列，取消和延迟载荷仍沿用原槽及代际。堆的拥有存储仍为同一个 vector，检查点直接复制/恢复；时间轮选项保持独立。

`DSIM_TIMER_HEAP_ARITY` 可在编译生成 C++ 时定义为 2、4 或 8。2 使用原 `std::push_heap/pop_heap`，4/8 使用逐层选择子节点、移动空洞的实现。该配置供候选复测使用；不改变 HDL、时间单位或波形模式。每种堆都检查同刻 FIFO、稀疏大时刻、UINT64_MAX、实时插入和重复检查点恢复，以及 NBA、连续延迟和 SDF 路径。实际性能及最终采用记录见 [本批证据](../validation/m9-timers-selects/README.md)。
