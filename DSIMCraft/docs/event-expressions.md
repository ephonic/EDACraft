# 表达式事件控制

M45 支持 `@(expression)`、`@(posedge expression)`、`@(negedge expression)`，以及用 `or` / 逗号连接的混合列表。表达式沿用现有整数/四态/宽字体系，包括算术、比较、逻辑、拼接、常量和动态 packed 选择、packed 成员、静态 unpacked 数组字及受支持系统函数。普通 initial/always、循环、模块克隆、静态块和 automatic task 均可使用；RTL parser 与紧凑门级 parser 保持独立。

```systemverilog
initial begin
  @(data[index]);
  @(posedge (clk && enable));
  @(memory[address] or done_event);
end
```

无边沿限定时比较完整表达式值，包含 X/Z；posedge/negedge 只根据结果最低位判断四态边沿，其他位改变不形成边沿。数组索引改变时重查所选值，其他数组字变化也可能触发求值，但所选值不变就继续等待。相同数值的不同索引不会被当成值变化；无效索引沿用既有 X 结果规则。`@({a,b})` 保留一个拼接表达式，不再错误拆成两个独立事件项。

表达式编译成 C++ 值求值器和静态依赖 ID 表。依赖变化将求值任务排入 Active FIFO，同一任务在恢复前的多次通知合并；不逐次写入即执行边沿判断，不轮询或运行 AST。例如 a/b 在同一过程执行段从 0/0 变为 1/1，`@(a^b)` 不捕获中间瞬态；插入 `#0` 后的两次变化则可分别唤醒。VCS 原始探针已确认这一行为。

一般静态复合表达式监视器在等待者暂未挂起时仍更新缓存；依赖变化已排队、随后才进入该表达式等待，也可能在求值任务执行时被唤醒。选择表达式以及 automatic 作用域表达式在进入等待时重新取样，避免把任务形参初始化或等待前的选中位写入当成后来的事件。两类入口行为分别由 entry、selected、automatic、automatic_entry 和 automatic_expression 的真实 VCS 探针核验，不能将所有表达式当成普通整信号，也不能统一用一种取样时机代替。

等待点的 generation 区分不同挂起位置；求值更新缓存后，仅唤醒仍等待该位置的过程。混合命名事件/整信号可以先唤醒过程，已排队表达式任务随后仍更新缓存，避免下次进入时使用旧值。缓存四态值、待求值标志、FIFO 中的任务和 generation 均随现有 Sim 检查点复制，支持失败预测回放。求值器接收当前 Sim，串行直接使用静态 ID，自动分区共享 main 中的最终 ID 映射，避免每个求值器复制整表；依赖读集合参与分区合并。

简单整信号、直接命名事件及直接 `.triggered` 等待沿用原有路径。只有使用复合表达式等待的程序才定义 `DSIM_EXPRESSION_EVENTS_ENABLED`；没有使用时不增加表达式表或求值任务分支。新任务复用原 Active FIFO，门级批量求值在遇到表达式任务时停止批次，保留其队列位置；不是完整 SystemVerilog 事件区域实现。本批未重新测量速度或宣称性能收益。

M47 接通[无外部副作用 automatic 函数调用](function-events.md)，含函数的表达式在进入等待时重新取样。static/外部副作用函数及变更表达式（如 `@(counter++)`）仍明确拒绝；M45 原始 functions 探针写入全局计数，VCS 接受、dsim 拒绝的差距继续保留。M46 已接入[整数表达式的 iff 条件](conditional-events.md)；一般层次引用、动态容器、字符串/对象事件、fork/join、动态进程、完整 SVA/UVM 和事件区域仍缺。支持集合受现有表达式/类型系统限制，不能据此称完整 SystemVerilog 支持。

验证入口：`ctest --test-dir build -R '^(rtl_event_expressions|event_expressions_kernel|event_expressions_wheel|event_expressions_compact)$' --output-on-failure`。五个公共模型覆盖 130 位、四态边沿、同值过滤、动态数组字和越界、任务激活、混合事件、双实例及两个实际独立线程分区；三后端/两格式/两模式和两次实际失败预测回滚比较完整 ordered 逐信号事件。实际 VCS settled 位时间线、原始探针和已知差距见 [M45](../validation/m45-event-expressions/README.md)。
