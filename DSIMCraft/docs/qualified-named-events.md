# 条件命名事件

M48 支持静态标量命名事件的 `@(event iff condition)`，包括混合 or/逗号列表、宽字四态条件及无外部副作用 automatic 条件函数；普通 initial/always 和 automatic task 均可使用。支持已有阻塞 `->`、NBA `->>` 与延迟 NBA 触发，接入分区和失败预测恢复。RTL/门级 parser 继续分开，复用现有事件 AST，本批不改 lexer/grammar。

```systemverilog
event ready;
logic enable;
always @(ready iff enable) accepted++;
initial @(ready iff permit(valid) or posedge clk iff enable);
```

每次命名事件发生都可以安排一个 Active 求值任务；同一求值前的多次触发合并。条件在任务执行时读取，有已知 1 才为真。因而 `->ready; enable=1;` 可以放行，`enable=1; ->ready; enable=0;` 会过滤。连续两次触发不能因内部发生位回到原值而丢失。条件独立变化不产生求值任务，不会重放之前被过滤的发生。

只有已挂起且代际匹配的等待才能接收发生。触发后才进入等待、或混合列表的其他分支已经唤醒过程时，该次发生不能再用于后一次等待。队列记录发生所属的等待代际；新发生可以替换同一待求值任务中的旧代际。条件/函数体全局读取参与分区合并，条件本身不加入发生订阅。

编译器为这类事件生成发生模式的表达式等待，复用 Active FIFO、固定依赖表和条件回调；发生模式不比较隐藏位的最终数值。普通命名事件仍走原直接等待路径。发生代际、待求值任务和条件依赖存储随已有 Sim 快照恢复；没有轮询、运行时 AST 或新的预测器。额外发生代际字段与检查只在同时启用命名事件和表达式事件时编入；没有新速度测量。

这仍是静态标量 event 子集。事件句柄赋值/别名/null、event 数组/形参、automatic 局部 event、wait_order/fork、动态进程、完整事件区域未实现。命名事件不允许 posedge/negedge。条件中的 static 函数、外部写入、output/inout、诊断或变更表达式仍按 [M47 边界](function-events.md)拒绝。

验证入口为 `rtl_qualified_named_events`、`qualified_named_events_kernel/wheel/compact`。三共同源覆盖 130 位/X/Z 条件、偶数次触发、混合分支、NBA/延迟交付、晚进入等待、automatic 条件函数、task 及真实双分区。比较三后端/两格式/两模式和两次实际失败预测回滚；内核检查旧代际、新发生替换、待求值检查点、延迟回放和 compact 普通信号混合分支。真实 VCS、跨平台与 sanitizer 证据见 [M48](../validation/m48-qualified-named-events/README.md)。
