# 延时驱动内核接口

这层接口接收已选择的整数 tick 延迟，尚未接入 CLI 的 SDF 回标。RTL/gate parser、SDF parser/绑定及零延迟门级代码生成保持原有边界。模块路径精度舍入、ABSOLUTE/INCREMENT 合并、COND/边沿路径选择、RETAIN、脉冲阈值、timing checks/notifier 仍需在注解层实现。

在包含 `runtime.hpp` 前定义 `DSIM_TIMING_ENABLED`。普通生成模型不定义它，不增加通道、事件槽或分支。底层事件使用现有时间堆，以时间与插入序号排序；负的内部 Ready/Timer 编号标识驱动事件，不占用用户进程 ID。`Process`、`Watch` 和 `Timer` 的布局不变。

```cpp
#define DSIM_TIMING_ENABLED 1
#include <dsim/runtime.hpp>
using namespace dsim;
Sim s;
int output = s.signal(1, true);
auto ch = s.delayed_driver(output, 17, Sim::DelayPolicy::ReplacePending);
s.drive_after(ch, V(0), 0);
s.run_until(0);                  // 提交初始驱动
s.drive_after(ch, V(1), 5);      // 不阻塞采样进程
s.run_until(2);
s.drive_after(ch, V(0), 5);      // 回到已提交值，取消尚未提交的脉冲
s.run();                        // 没有存活事件，时间保持 2
```

`delayed_driver(signal, driver, policy)` 在拓扑冻结前登记，只允许 net；同一 signal/driver 不能重复登记。调用方须独占这个驱动身份，后续使用 `drive_after`，不能混入直接 `drive`，也不能绕过 API 改写 `signals`。不同驱动仍按既有强驱动规则解析，alias 保持按位连接。延时取消比较该驱动自己的已提交值，不比较可能被其他驱动遮蔽的 net 解析值。

两种策略的定义为：

| 策略 | 请求行为 |
|---|---|
| `ReplacePending` | 输入请求发生变化时，取消此前未提交请求；若新值等于本驱动已提交值，不创建事件 |
| `PreserveTransitions` | 保留每次输入变化的请求，按各自到达时刻及插入序号提交；允许可变延迟导致的到达顺序变化 |

相同的连续输入请求不会推迟已有事件。`cancel_delayed(ch)` 取消该通道全部未提交请求、保留已提交输出并清除输入去重状态，因此下一次同值请求可以重新提交。这些是明确的内核策略，不等同于 Verilog 中任意延迟对象的 inertial/transport 语义，也不能仅凭某个 VCS transport 选项映射策略。

`drive_after(ch, value, 0)` 追加 Active 事件，调用时不立即改变输出；现有 Active 工作先执行，当前 NBA 批次仍在 Active 清空后提交。正延时与进程 timer 共享时间堆。timer 被取出时，驱动事件直接进入 Active，进程 timer 先追加 wake，再由 wake 追加进程体，沿用既有协议。这个内部确定顺序不承诺消除设计/TB 的同刻竞争，完整路径模式仍需额外差分。

取消使用通道代次标记。失效的堆顶驱动事件会被清除，不推进时间；已进入 Active 的失效事件按其 FIFO 位置消耗但不写值。事件槽在提交/清除后复用，内存取决于尚未取出的堆/Active 事件高水位；大量远期取消事件仍可能暂时占用内存，并非增量状态日志。

检查点按值复制通道输入/输出、代次、所有事件槽与空闲槽、Active/时间队列及 timer 序号。已提交 net/驱动存储沿用既有深复制。预测事务恢复它们，并通过既有事务缓冲隔离打印/波形/并行观察输出；不支持跨分区回滚或边运行边外部写入。固定敏感进程只调用 `drive_after`，不执行进程 `delay`，所以可以继续采样。

验证见 [本批记录](../validation/m5-delayed-drivers/README.md)。微例使用显式整数延迟适配 VCS 已有 SDF trace，不把适配程序当作自动回标。完整回标必须继续通过文件到编译 IR、接收 pin 网络与单元输出驱动的集成测试。
