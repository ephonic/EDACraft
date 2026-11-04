# 有序命名事件等待

M59 支持静态标量命名事件的 `wait_order`，包括模块、generate、静态局部 event 和 automatic task 对外部静态 event 的引用。

```systemverilog
event request, accepted, completed;
initial wait_order(request, accepted, completed)
  $display("transaction completed");
else
  $error("out of order");
```

成功与失败 action 均可为普通过程语句，支持省略成功 action、空 action、单事件、重复名称及内层 if/else。没有显式 failure action 时，乱序会终止仿真，不再执行后续语句。只有进入等待之后发生的事件才有效，`triggered` 查询不代替新的事件发生。

每次触发只消费一个期望事件；同一 tick 内连续阻塞触发或同批 NBA 触发保留发生顺序。序列之外的事件及不再出现在剩余序列中的旧事件不影响等待；剩余序列中的其他事件提前到来则立即失败。重复名称仍需要独立的发生次数，例如 `wait_order(a,a,b)` 需要两次 a；`wait_order(a,b,a)` 等待 b 时再次触发 a 会失败。

编译器生成等待和分支 PC，运行时按事件索引只查找相关站点，在实际触发时推进顺序。完成只唤醒一次，后续触发不能改写已选 action。固定站点参与动态 fork 克隆/复用，取消沿用进程代际，顺序位置和结果随 Sim 检查点保存；支持已有失败预测重放、时间轮、VCD/DWF 及保守并行分区。未使用本功能的程序不启用相关运行时字段。

目前只支持现有静态标量 event 对象。event handle 赋值/形参、event 数组和 automatic 局部 event 尚缺；函数与 always_comb/always_latch/always_ff 中的 wait_order 会被拒绝。真实 VCS 在一个多调用静态 task 探针中编译崩溃，在多个词法等待共享事件的 fork 探针中结果与单站点探针不同；原始输入/日志单列，不计作对齐。共同支持模型、实测范围和剩余差距见 [M59 验收记录](../validation/m59-wait-order/README.md)。

运行检查：`ctest --test-dir build -R '^(rtl_wait_order|wait_order_(kernel|wheel|compact)|rtl_semantic_memory)$' --output-on-failure`。
