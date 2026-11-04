# 电平条件等待

M59 新增 [wait_order 有序事件等待](wait-order.md)：成功/失败分支、重复事件、NBA 顺序、automatic task、fork 取消/复用及预测回滚。

M43 支持 `wait (condition) statement` 和 `wait (condition);`，可用于普通 initial/always 过程及 task，包含 automatic task、模块克隆、循环和 break/continue。RTL lexer/parser、语义绑定、节点克隆和编译器均已接通，门级网表仍使用独立 parser。

```systemverilog
function automatic logic ready(input logic req, input logic ack);
  ready = req && ack;
endfunction
initial begin
  wait (ready(req, ack));
  #1 data = next_data;
  wait (!ack);
end
```

条件入口求值一次，为真立即执行后续语句，不额外插入 delta；为假或未知则挂起。任意已知 1 位使向量逻辑值为真；全 0 为假，只有 0/X/Z 且含未知位时继续等待。支持现有表达式体系，包括 130 位宽值、packed 选择、动态数组字、比较和函数调用。相关信号变化时恢复并重新求值；同一执行块内先拉高又拉低，恢复时为假则重新等待，不能把变化事件直接当成条件成立。

与本轮实际 VCS 探针一致，函数调用的实参表达式参与唤醒敏感集合，函数体单独读取的全局变量不参与。因此 `wait (f(a))` 会随 a 改变重查，若 `f()` 只读取全局 b，单独改变 b 不唤醒。函数体的外部读写仍保留在自动分区依赖图中，避免丢失跨过程依赖。固定假条件、无敏感信号条件不会轮询；`wait(0)` 永久挂起，`wait($time>10)` 也不会自动安排未来时间唤醒。

编译器生成一个条件检查 PC 和既有固定等待点。假值保存同一 PC 并调用现有 wait-site 机制，真值直接继续；运行期不遍历 AST，不增加条件轮询队列或独立调度器。PC、waiting、信号订阅及 automatic 调用状态沿用原检查点/预测回滚，适用于串行、时间轮和自动分区。此批没有修改 runtime.hpp/parallel.hpp，也没有重新测量仿真速度。

同时补齐 `function logic` / `function reg` 的返回类型语法，包括默认 unsigned、显式 signed/unsigned、packed 范围及 automatic 声明；返回转换沿用现有四态、宽度和符号处理。重名 task 与已有函数冲突时返回语义错误，修复原先空指针崩溃，并加入三轮解析/清理检查。

函数仍禁止 wait 等耗时语句；always_comb/always_latch/always_ff 中的 wait 明确拒绝。命名 event 的静态子集已于 [M44](named-events.md) 接入；fork/join、wait fork、动态 fork 和 wait_order 已由后继批次接入，范围分别见 [fork 控制](fork-control.md)、[动态 fork](dynamic-fork.md) 和 [有序等待](wait-order.md)；完整 SystemVerilog 事件区域仍未实现。

验证入口：`ctest --test-dir build -R '^rtl_level_wait$' --output-on-failure`。五模型覆盖三次握手/NBA、宽值/X/Z/动态数组条件、函数实参敏感性、automatic task 重入/输出复制、模块克隆、循环控制和真实双分区；三后端、两种波形格式/模式共 60 捕获，另两次实际失败预测回滚。独立数学时间线及七类拒绝用例同时核验。实际 VCS 五个同源模型的 TRACE/自检与全部 1120 条直接导出位 settled 时间线一致；16 个数组位经同源 packed 观察信号核验，已包含于 1120 中，不相加作独立位。四原始边界探针均接受/TRACE 一致。完整 ordered 同刻变化仅在 native 多后端/格式及跨平台之间比较，未声称与 VCS 的全部瞬态顺序一致。证据见 [M43](../validation/m43-level-wait/README.md)。
