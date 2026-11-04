# 静态命名事件

M59 新增 [wait_order 有序事件等待](wait-order.md)：成功/失败分支、重复事件、NBA 顺序、automatic task、fork 取消/复用及预测回滚。

M44 接通模块、generate 和静态过程块/子程序中的标量 `event`。支持 `@e`、`@(e or signal)`、`->e`、`->>e`、`->> #delay e`、`e.triggered` 与 `@(e.triggered)`，以及查询的 posedge/negedge。普通和 automatic task 可以等待或触发词法外部静态事件；函数可以发出阻塞/NBA/延迟 NBA 事件触发，调用立即返回。RTL lexer/parser、绑定、克隆和编译器分别接入，门级紧凑 parser 保持独立。

```systemverilog
`timescale 1ns/1ps
module top;
  event request, reply;
  initial begin
    ->> request;
    @reply;
    $finish;
  end
  initial begin
    @request;
    #1 ->reply;
  end
endmodule
```

`->` 当场触发；已经挂起的接收过程进入 Active 队列，发送者继续执行。早于 `@e` 的触发不会被保存供以后消费。`->>` 在 NBA 阶段触发，发送者立即继续；同一 NBA 批次的重复触发可合并对尚未恢复的等待者的唤醒。带 delay 的触发在入口求值一次、按所在模块时间单位转换并排队，到期进入 NBA；复用已有动态整数延迟、常量小数舍入和溢出检查。

`e.triggered` 为一位两态查询，事件在当前 tick 曾经触发就返回 1，否则返回 0。`wait(e.triggered)` 在当前 tick 已触发时立即继续，因此能接住晚进入的等待；`@e` 则不能。查询不是可写变量，也不支持带括号的 `e.triggered()`；后者与本轮 VCS 一样拒绝。

实际 VCS 探针确认：时间推进造成查询隐式变回 0，不产生一次表达式变化通知，也不更新已挂起 `@(e.triggered)` 的采样基线。查询为假时进入的等待可被下一次触发唤醒；在查询为真时重新进入的等待，即使跨 tick 再触发也不会因此看到值变化。`negedge e.triggered` 不因时间推进被唤醒；`wait(!e.triggered)` 也不会仅靠时间推进重查。普通 `@e` 每次重新挂起后仍可接收后续触发。

运行时用一个隐藏信号 ID 表示事件发生，用触发时间戳表示持续查询；固定 wait-site 区分发生订阅与查询订阅。事件依赖参与分区合并，多个触发者不作为普通变量的重复写者。NBA、定时池、时间戳和订阅采样基线随现有 Sim 快照复制，支持失败预测回滚。串行、时间轮、紧凑内核与自动分区复用原调度框架，不轮询，不引入另一套调度器。只有实际声明事件的模型才定义 `DSIM_NAMED_EVENTS_ENABLED`，未使用时无事件表或额外 NBA 分支。

事件对象不是整数信号。IR 将其标记为 `named_event: true`，VCD/DWF 不导出隐藏翻转值；本轮 VCS `$dumpvars` 也不导出这些 event 对象。通过普通计数器、握手结果和 query 观察其语义。全部导出物理位和对象清单均有独立核验；VCS 未导出的两个静态函数变量另经同源 packed 观察值核对，没有将额外观察位相加作独立 VCS 位数。

尚不支持事件句柄赋值/别名/null、事件数组、event/ref 形参、automatic 局部事件、一般层次事件引用、event-control 形式的非阻塞触发及 process 对象。查询结果的直接位选择明确拒绝；一般 `@(a+b)` 等表达式事件控制已于 [M45](event-expressions.md) 接通，无外部副作用 automatic 函数由 [M47](function-events.md) 接通，静态命名事件 iff 由 [M48](qualified-named-events.md) 接通；外部副作用函数等边界仍缺。完整 SV 事件区域、并发 SVA、class/package/interface、动态容器和 UVM 仍不具备。本批未重新测量性能。

验证入口：`ctest --test-dir build -R '^(rtl_named_events|named_events_kernel|named_events_wheel|named_events_compact)$' --output-on-failure`。覆盖五个公共模型、串行/时间轮/threads2、VCD/DWF 两模式、两次实际失败预测回滚、动态 delay 单次求值、static/automatic 子程序与模块克隆。三个内核测试另核对延迟事件、查询基线和排队状态恢复；实际 VCS 证据与边界探针见 [M44](../validation/m44-named-events/README.md)。

M48 新增[条件命名事件](qualified-named-events.md)：`@(event iff condition)`、混合分支、Active 条件取样、连续触发与晚进入隔离，支持 automatic 条件函数、NBA/延迟触发、并行及回滚。事件对象/数组/形参边界继续保留；wait_order 的后继支持范围见页首 M59。
