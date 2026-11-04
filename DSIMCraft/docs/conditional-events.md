# 条件事件控制

M46 支持 `@(expression iff condition)`、posedge/negedge 限定，以及各分支分别带条件的 or / 逗号列表。RTL lexer/grammar 新增 iff，AST 事件节点保存独立条件，作用域绑定、模块克隆与清理同时处理两棵表达式；紧凑门级 parser 保持独立。

```systemverilog
always @(posedge clk iff enable) count++;
initial @(data[index] iff valid);
always @(posedge a iff ready or negedge b iff reset_ok) sample();
```

iff 的绑定优先于 or/逗号，各条件只约束所在事件项。条件沿用整数/宽字四态真假：有已知 1 则真，全零为假，只有 0 和 X/Z 则不算真。源事件无边沿限定时比较全部四态值，有 posedge/negedge 时只检查最低位。false/unknown 条件过滤本次事件，更新后的源值仍成为后续比较基线。

源依赖变化在原 Active FIFO 合并求值，实际值变化/边沿成立且当前过程仍等待该位置时，才读条件。只将源表达式的读集合登记为事件依赖；条件本身变化不会触发或再次求值。条件的读集合参与分区合并，避免在其他独立内核读取远端状态。相同过程段中源变化后修改条件，会被该 Active 求值看见；#0 之后的修改不改变此前已经作出的判定。这些行为与 IEEE 1800-2017 §9.4.2.3 及真实 VCS 探针分别核验。

所有带 iff 的等待在进入时重新取样源值，包括静态复合表达式，避免等待前的写入误唤醒；无 iff 的 M45 普通静态复合表达式缓存规则保持原样。缓存、排队标志、等待位置和 FIFO 随已有检查点恢复。求值器复用 M45 编译式表达式接口，不在运行期遍历 AST，也不轮询；未使用表达式事件的程序不增加新表。条件求值器是可选字段，本批未测量速度收益。

支持普通过程和非递归 automatic task 的已支持整数表达式、动态 packed 选择、宽值和混合列表。M47 接通事件源或条件中的[无外部副作用 automatic 函数](function-events.md)。static/外部副作用函数、变更表达式仍拒绝；M48 接通[静态命名事件 iff](qualified-named-events.md)，原 M46 named 探针升为本批正例。M46 原始副作用函数差距继续保留。完整层次引用、动态对象/容器事件、fork/join、完整事件区域、SVA/UVM 等历史边界继续保留。

验证入口为 `rtl_conditional_events` 和 `conditional_events_kernel/wheel/compact`。三模型覆盖 130 位/四态真假、源缓存更新、动态位、分支优先级、任务隔离、真实双分区、八 worker 请求下 guard 依赖合并、完整 ordered VCD/DWF、两次实际失败预测回放；实际 VCS 位时间线及原始探针见 [M46](../validation/m46-conditional-events/README.md)。
