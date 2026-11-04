# 仿真检查点、预测与并行基础

本批加入同进程检查点、预测事务与实验性保守并行 API。它们不是 VCS 功能对齐完成，也没有测得加速收益。参考 `vcs1017.md` 未披露预测/回滚算法，因此这里是 dsim 的独立设计。

## 检查点与预测事务

`Sim::checkpoint()` / `restore(cp)` 必须在调度器调用之外使用，检查点属于创建它的 Sim，可重复恢复。创建后冻结信号、进程、静态等待站点和连接结构。保存的内容包括：

- 信号四态值、驱动、多驱动/别名解析结构、watch generation 与动态等待表。
- Active/Inactive FIFO、NBA 及其批次、定时堆与稳定顺序号、时间、finish、指令预算计数。
- `std::function` 值语义复制的进程 PC / repeat 局部计数器。
- 显式注册的外部模型状态；生成的门级模型注册自己的共享 State，因此 ff/latch 的当前/待提交值、采样状态会恢复。

共享指针指向的数据不会仅因复制闭包自动恢复。自定义模型必须用 `register_state(shared_ptr<T>)` 注册可复制状态，例如随机数生成器；裸引用、外部全局数据和直接文件 I/O 不能被自动回滚。

```cpp
auto cp = sim.checkpoint();
sim.run_until(100);  // 包含 tick 100，并排空其 Active/Inactive/NBA
sim.restore(cp);

bool accepted = sim.predict_until(100,
    [](dsim::Sim& s) { /* 在窗口起点施加预测输入 */ },
    [](const dsim::Sim& s) { return /* 与已知真实输入/结果核对 */ true; },
    [](dsim::Sim& s) { /* 失败时在恢复的起点施加真实输入 */ });
```

预测正确时提交，错误时恢复窗口起点、施加真实输入并重放到相同 horizon。预测/验证异常恢复状态并丢弃未提交效果；外部效果开始提交后若 sink 失败则直接报错，避免重复提交。`prediction_stats` 记录尝试/提交/回滚、推测及重放步数。

生成的 `$display/$write` 改走 `Sim::print`；预测中的打印和波形 change/tick 顺序进入事务日志，提交后才输出。settled 波形使用接收到的 change 值维护自身状态，避免延迟回放 tick 时错误读取内核的最终值。附着波形时禁止手动检查点恢复，必须走预测事务，避免倒写已提交文件。波形检查点不是内核检查点。

当前是整状态复制，并未实现增量日志、自动预测器或跨进程恢复。预测回调和实际输入由 API 调用方提供，CLI 尚无自动预测开关；不能据此宣称预测可提高仿真速度。

## 保守并行 API

`#include <dsim/parallel.hpp>` 必须先于 `runtime.hpp`，使用 C++17 / `-pthread`。`ConservativeSim(workers, window_ticks)` 创建常驻线程池，`partition()` 分配独立 Sim，`kernel(id)` 用于安装该分区的模型，`connect(from,source,to,destination,positive_delay,driver)` 声明有向边。

每个分区的零延迟域由一个 worker 顺序执行。跨分区边必须有至少一个整数 tick 的延迟；最小边延迟形成 lookahead，各线程执行不超过该 lookahead 的窗口，barrier 后按源分区与源内顺序把消息放入接收方的定时输入堆。带时间戳输入先于该时间本地定时唤醒入队；并发打印按时间、分区、源内顺序提交。同一时刻竞争应按此边界规则设计模型，不能把任意共享变量放入不同线程。

```cpp
dsim::ConservativeSim engine(4, 100);
auto left = engine.partition(), right = engine.partition();
// 安装各自 kernel 的信号、进程与等待站点……
engine.connect(left, source_id, right, input_id, 10, input_driver_id);
engine.run_until(1000);
```

当前限制：明确正延迟、统一整数 tick、有限 horizon；跨分区零延迟边拒绝。net 输入必须提供驱动身份，variable 输入 driver 为 -1。各分区不得共享可变模型状态，也不得自行运行其 kernel。默认模式拒绝分区内 finish；需要结束协议时，在首次执行前调用 `enable_global_finish()`。未被结束边界排除的 worker 异常使 engine 失败，不能继续运行。正常源变化、输出和输入堆各自由所属 worker/协调线程访问；同一内核不会被多个线程同时执行。

这是可运行的保守并行内核。后继 [--threads](automatic-parallel.md) 已接入普通 RTL 独立域自动编译，gate scope内部的切分仍待实现；尚无乐观时间推进、反消息或跨分区回滚。预测事务是后续乐观算法的局部基础，不能把两者组合存在视为已经实现 Time Warp。零延迟大组合锥还需静态分区/层级并行求值与严格观测语义。

## 全局结束协议

`ConservativeSim` 和 `AutoConservativeSim` 均提供显式开启的全局结束模式：

```cpp
engine.enable_global_finish();  // 在 run_until 之前调用
engine.run_until(1000);
if (engine.finished()) {
    auto tick = engine.finish_time();
    auto partition = engine.finish_partition();
}
```

开启后，每个推进窗口先保存所有内核的事务检查点。worker 私下执行，打印、解析值通知和波形回调缓冲至协调器提交。若分区请求结束，协调器选最早的 `(tick, partition ID)`，恢复该窗口并重放到结束边界：较小 ID 执行完整结束 tick，请求结束的内核执行到自身 finish，较大 ID 只执行到前一 tick；tick 0 时较大 ID 不执行。只提交这个前缀的外部效果，结束后的有限 `run_until` 不再执行。`stats.window_replays` 记录结束窗口重放次数。

窗口内的异常也按同一边界判断。发生在结束之后的推测异常不提交；结束前或同刻较小 ID 的异常仍报错，并回滚未提交的事务。提交外部 sink 后若其抛异常，engine 终止且不重复提交。该边界沿用 API 的物理分区 ID 顺序；有竞争的模型改变分区映射后可能改变同刻结果，不能视为任意 Verilog/VCS 调度等价。

协调器使用的 `Sim::begin_transaction()`、`transaction_pending(cp)`、`commit_transaction(cp)`、`rollback_transaction(cp)` 仅在并行宏下提供。token 属于单个内核且只能结算一次；旧 token 不能控制新事务。模型共享状态仍须 `register_state`，直接文件 I/O 等外部操作无法自动撤销。全局结束模式每窗口复制完整状态且可能重放，没有加速收益声明；默认模式不付出该检查点成本。

验证包含 360 种 worker/窗口/结束时刻/分区/通道/分段运行组合，以及宽四态、NBA、注册状态、异常先后和过期 token。实际原生 ordered/settled VCD、raw/Zstd DWF 共 96 份捕获，与独立串行内核按明确结束边界执行的完整事件流一致。这批是每分区文件；后继全局文件接入见下节。普通 Verilog 编译器尚未自动生成这些 API 调用。证据入口见 [全局结束验证](../validation/m5-global-finish/README.md)。

## 单文件全局压缩波形

`#include <dsim/parallel_waveform.hpp>` 放在 runtime 之前，启用并行和波形运行时。`ParallelWaveCapture` 接受 `ConservativeSim` 或 `AutoConservativeSim`，使用与串行 `WaveCapture` 相同的运行参数、scope/depth 过滤、ordered/settled 策略和 VCD/raw DWF/Zstd DWF 编码器。声明必须携带物理分区 ID；自动图的节点使用 `engine.plan().owner[node]` 查找。内核中的相同整数 signal ID 在不同分区拥有独立波形 ID，同一分区同一 signal 的多个声明共享 ID。

```cpp
// 配置所有内核、信号、通道和进程，统一其 time_precision_fs……
dsim::ParallelWaveCapture wave(engine, argc, argv, "1ps");
wave.declare(left_partition, left_signal, {"top", "left"}, "data", 256, 0, false, true);
wave.declare(right_partition, right_signal, {"top", "right"}, "data", 256, 0, false, true);
wave.start();
engine.run_until(1000);
wave.close();
// 运行参数例：--waveform run.dwf --wave-mode ordered --wave-codec zstd
```

每个 worker 只追加自身分区的值变化缓冲；所有内核提交事务之后，协调线程以 `(tick, physical partition ID, local order)` 做多路归并，调用共享编码器。提交 hook 使用弱所有权，关闭波形后继续仿真不会访问已释放对象。全局结束窗口的试运行不输出波形，回滚后只归并重放所得的有效前缀；未提交异常窗口的部分变化在关闭时丢弃。sink 提交失败使 engine 失败，不自动重放已写部分。

文件保留初始 tick、实际选中信号发生变化的 tick 和最终已提交 horizon，不为每个保守窗口添加时间记录。settled 在合并完同刻所有分区后取值；ordered 保留同刻中间变化。窗口大小变化不应引入不同的时间标记。使用不同物理分区映射时，同刻跨分区顺序仍依赖分区编号，并不保证任意 Verilog 竞争的 VCS 顺序。`--max-events` 是每个内核的预算，不是全局共享预算。

支持普通网、紧凑网、257位四态、别名、多驱动和 NBA。缓冲覆盖一个推进窗口，归并复杂度为 `O(events * log(partitions))`；百万信号分组检查点尚未实现，也不改变普通 RTL/网表自动并行代码生成的接入状态。最终435源已通过本地完整94项（405.80s），252份常规及252份ASan/UBSan捕获独立核对PASS。后继442冻结源的相同runtime/wave头及相同测试，在Linux单独构建generic/compact两项也已通过：252份完整捕获按独立模型重算，并与435源macOS归档逐事件一致，含部分挂接清理；见[Linux定向核对](../validation/m6-parallel-wave/targeted-linux/verification.json)。这不是435/442完整Linux套件或Linux sanitizer验收。本批源码和验收入口见 [全局波形验证](../validation/m6-parallel-wave/README.md)，功能验收不作并行或压缩吞吐收益声明。

后继456源增加共享编码器的有界异步Zstd块压缩，使用相同的`--wave-compression-jobs`选项；只有全局窗口提交后归并出的字节进入压缩队列。压缩线程不访问分区内核，压缩完成顺序不影响文件提交顺序。两种后端各五场景的ordered/settled文件与同步压缩逐字节相同，完整本地105项通过，Linux集成仍在进行。线程预算、异常与验收范围见[波形格式](waveform-format.md#有界异步块压缩2026-10-18)及[本批记录](../validation/m6-async-wave/README.md)。

## 自动分区 API 与编译器分析

`PartitionGraph` 描述拥有独立状态的节点、估计计算权重和有向延迟依赖。规划先用并查集合并所有零延迟边的两端，再按域权重从大到小分配给当前总权重最小的分区。相同输入产生相同分配；分区数不超过有工作量的域数。零权重节点用于连接拓扑，不单独占用 worker。权重只是静态估计，不是测量的 CPU 时间；算法不保证最小化切边。

`AutoConservativeSim` 接收完整图，按规划自动创建内核。调用方仍负责在 `kernel(node)` 安装模型和进程，并将每条图边绑定到实际信号；缺失或重复连接会报错。

```cpp
dsim::PartitionGraph graph;
auto producer = graph.node(100), consumer = graph.node(80);
auto channel = graph.edge(producer, consumer, 10);
dsim::AutoConservativeSim machine(graph, 4);
auto& left = machine.kernel(producer);
auto& right = machine.kernel(consumer);
int source = left.signal(1, false), input = right.signal(1, false);
// 安装模型、设置时间精度并 enqueue 初始进程。
machine.connect(channel, source, input);
machine.run_until(1000);
```

零延迟图边只接受等宽 net alias，driver 参数必须为 -1；两端必在同一内核。正延迟边保留每次解析变化，net 目的端仍需显式 driver。即使两端被分到同一内核，正延迟边也经过协调器消息队列，因而其最小延迟同样限制当前实现的窗口。`plan().lookahead` 只描述跨分区边，实际窗口可能更短。相同时刻有竞争或来自不同节点的打印时，应遵守分区边界的确定性顺序，不能假定任意模型改变 worker 数后都保持 Verilog 调度顺序。

编译器提供 `--gate-partition-report N`：

```sh
build/dsim --gate-check --gate-netlist net.v --gate-top dut --liberty cells.lib \
  --gate-partition-report 4 --emit-ir partition.json
# 也可附加在普通 --sdf-annotate 编译命令中，必须指定 --emit-ir。
```

报告包含分区数、零延迟域数、估计负载、切边数、最小切边延迟（fs）、每分区单元/net 数和单元的分区映射。输入为独立 gate IR，未调用 RTL parser 解析网表。常量作为不可变值可在各分区复制；单元内部保持原子性，IOPATH 暂不切分。仅当接收引脚 INTERCONNECT 的 rise/fall/turnoff 三个最终延迟都严格为正时，才允许沿该输入边切分；任一转换为零就合并。共享输入和多驱动 net 保持其零延迟依赖。

这是 **gate-only 分析**；单独使用 `--gate-partition-report` 不改变执行方式，分析报告标记 `execution: serial`。后继 [--threads](automatic-parallel.md) 用另一份全程序依赖图接入 testbench、层次端口 alias、全局 finish、波形汇合及独立域代码生成，实际计划位于顶层 `parallel` 字段；它仍把每个 gate scope保持原子化。两种报告的分区数不可互相替代，都不能据此推断加速比。

原始完整 SDF 的 8 分区请求目前只得到一个有单元负载的域，无法直接并行。IOPATH 不能仅凭名义正延迟就切分：`module_path_delay` 根据输入变化戳返回剩余延迟，可为 0。后续需证明真实因果下界，并实现初始化、同刻交付和取消消息协议。

`tests/parallel_test.cpp` 用独立递推预期核对多级四态传输、正延迟反馈、1/2/4 线程与不同窗口大小；同步屏障探针确认两个 OS 线程确实重叠执行，并验证 worker 异常能够退出。测试通过只说明这些范围的正确性，性能结论须另测真实设计、分区成本、同步成本与串行基线。
