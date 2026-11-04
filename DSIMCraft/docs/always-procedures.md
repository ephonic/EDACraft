# SystemVerilog always 过程

RTL 编译器支持已有无符号四态语言子集中的 `always_comb`、`always_latch` 和 `always_ff`；门级 parser 保持独立。

`always_comb` / `always_latch` 在时刻 0 执行，并根据块内读取的变量建立隐式敏感列表。块内写入的变量从列表排除，因此 `c=b; b=a;` 不会因为自己的 `b` 更新而再次执行。无读依赖的常量块也会启动。`always_latch` 条件未满足时保留变量值。当前尚不分析组合赋值是否完备、锁存是否有意义。

`always_ff` 当前要求语句以显式事件控制开头，例如 `@(posedge clk or negedge rst_n)`。等待在仿真启动前注册，能捕获时刻 0 的复位变化。赋值沿用阻塞/NBA 和四态值语义。三个过程都拒绝内部 delay；comb/latch 拒绝所有显式事件控制，ff 拒绝额外事件控制和 `@*`。

写变量与其他过程的写入冲突会在编译时拒绝；M78 允许 always_ff 变量的静态声明初值，comb/latch 的声明初值冲突仍拒绝（见[用户 RTL 报告处理](rtl-report-fixes.md)，VCS 对应需 initializer_driver_checks 放宽选项）；静态位区间不重叠时允许分别驱动。由于现有事件敏感度按整个变量表示，同一 comb/latch 块同时读取并部分写入一个变量暂时明确拒绝。函数/任务、数组、signed 等仍受现有 RTL 子集限制。不同过程在同一时刻读写共享变量的竞争尚不保证与 VCS 完全相同的瞬态排序。

隐式等待、启动事件、PC、NBA 和输出沿用可回滚内核及自动独立域分区。定向回归入口：`ctest --test-dir build-speed-sv -R rtl_always_sv --output-on-failure`。
