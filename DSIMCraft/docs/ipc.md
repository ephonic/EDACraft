# Mailbox 与 semaphore

`mailbox`、`mailbox #(T)` 与 `semaphore` 使用原生编译及运行时对象，RTL parser 负责类型/调用绑定，调度内核负责 FIFO 和挂起恢复。门级 parser 不受这一语法扩展影响。

```systemverilog
mailbox #(int) messages = new(1);
semaphore ready = new(0);
int received;
initial begin
  messages.put(42);
  ready.put();
end
initial begin
  ready.get();
  messages.get(received);
end
```

| 对象 | 任务（可能阻塞） | 函数 |
| --- | --- | --- |
| mailbox | `put(message)`、`get(ref message)`、`peek(ref message)` | `try_put(message)`、`try_get(ref message)`、`try_peek(ref message)`、`num()` |
| semaphore | `get(keyCount=1)` | `put(keyCount=1)`（void）、`try_get(keyCount=1)` |

`new()` 默认 mailbox 无界、semaphore 初始0键。支持有界 mailbox、别名与类属性中的 IPC 句柄、整数/packed 向量/enum/string/real/类句柄消息。消息、阻塞输入及 ref 目标在调用时保留；整批取消等待者后再检查后续请求。`peek` 不消费消息，可唤醒多个等待者。非参数化 mailbox 保留每条消息的类型；`try_get/try_peek` 发现类型不符返回负数并保留队首及目标变量，空队列返回0，成功返回正数。

mailbox 按 FIFO 传递消息。semaphore 按到达顺序检查可满足请求：一个大请求等待时，键数足够的小请求仍可成功；键数相同的等待者保持到达顺序。这包括新调用的 `get()`，也包括 `put()` 后已挂起的请求，与103上 VCS W-2024.09 的实测一致。M178 的严格队首阻塞假设已在 M179 修正。

整型消息按位宽、符号和二态/四态判断等价，不再要求内建类型名字相同，例如 `int` 与 `bit signed [31:0]` 可互传。enum 仍保留类型身份。M179 的 VCS 对齐另外记录了工具行为差异：VCS 对无类型 mailbox 的整数符号检查较宽松，并可能在类型不符时修改 string 目标；dsim 保留等价类型检查和失败不写回。负初始 semaphore 键数按 IEEE 1800-2023 的有符号计数实现，该 VCS 版本的实测不同。

阻塞调用降低为过程状态机中的等待/恢复步骤，不使用 #0 轮询。checkpoint 包括对象、消息、请求及待写回值。共享 IPC 对象的进程保守地归入同一分区，其他独立进程可在其他线程运行。

边界：目前拒绝数组/struct 消息，动态容器元素和 packed 部分选择作为 ref 输出；typed mailbox 输出要求等价类型。无类型 mailbox 的复杂表达式类型推导仍有缺口，可先存入变量或使用 typed mailbox；变量、数字 primary 和变量的 packed 选择已有执行检查。数值类型沿用现有类型系统，不能据此宣称完整 IEEE 类型等价规则已实现。原有用户 task 的 class property ref 绑定仍缺，native mailbox 直接类属性目标和普通 ref 标量任务分别有通过用例。

验收、复现脚本、公开 UVM 阻塞和未支持范围见 [M178](../validation/m178-ipc/README.md)，后续远端对齐和发布状态见 [M179](../validation/m179-remote-alignment/README.md)。完整公开 UVM 仍不能编译运行，IPC 局部通过不代表 UVM 功能完备。
