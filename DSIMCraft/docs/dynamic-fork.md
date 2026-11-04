# 重叠 fork 激活

M55 增加 [automatic 动态变量帧](automatic-fork.md)：重叠调用隔离、父帧共享及任务返回后的存活分支已接通；M56 又增加 [foreach 循环帧](foreach-fork.md)。下文 M54 验收范围保留为历史记录。

M54 在生成 C++ 的执行路径上支持静态存储分支的重叠 `join_any/join_none`，包括循环批量启动、嵌套 fork、直接子进程等待和仍活跃的孙进程。前一轮未完成时，不再复用其 PC 或等待记录，而是从编译模板创建独立激活；旧激活及其后代都结束或取消后，进程槽可供下一轮复用。

每个激活拥有独立闭包状态、进程/分组/等待点/命名控制目标映射。静态变量仍按 SystemVerilog 规则共享；例如模块级循环变量在 `join_none` 父进程结束循环后被各分支读取，不能擅自复制为每轮的值。普通事件、命名事件、表达式及 iff 等待在激活之间隔离，`wait fork` 等待所有活跃的直接子进程，`disable fork` 和词法命名块 disable 覆盖对应后代。已发起的 NBA 继续交付。表达式等待在分支实际进入等待时重新取样，父进程在分支启动前的变化不能通过旧求值任务误唤醒新等待。

分配发生在运行时，执行体仍为编译闭包。可增长的闭包表保持正在运行的函数地址稳定，避免启动嵌套分支时容器重分配导致失效。激活映射构造完成后保持只读；进程、队列、订阅、池及 PC 都由 Sim 快照保存，支持在分配之前或已有多个活跃分支时做失败预测恢复。信号和门级模型拓扑保持固定。只在设计含 `join_any/join_none` 时启用动态激活，普通 RTL/门级路径保留原闭包表。

本轮没有实现动态变量帧：automatic 父存储中的 detached fork 仍在编译时拒绝；重叠分支访问 automatic 局部存储或 foreach 临时槽时，在创建重叠激活前明确报错。非重叠分支调用阻塞 automatic 子任务继续支持。完整 automatic 帧共享/逃逸、递归、process 对象、外部/层次任务 disable 和完整 SV 验证能力仍缺。

回归包含批量启动、join_any 尾部分支、存活孙进程、命名/条件事件、命名块取消、延迟 NBA 保留、独立实例双分区、槽复用，以及 M53 当时拒绝的原始 overlap 探针。详见 [M54 验收](../validation/m54-dynamic-fork/README.md)。

复跑：`ctest --test-dir build -R '^(rtl_dynamic_fork|dynamic_fork_kernel|dynamic_fork_wheel|dynamic_fork_compact)$' --output-on-failure`。
