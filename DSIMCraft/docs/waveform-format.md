# 压缩波形设计与 DWF1 原型

当前状态（2026-10-29）：格式为 `DWF1P001`，原生数字后端已接入 RTL 和门级/SDF 生成运行时，独立接收线程及用户指定输出范围均已发布。原生 writer 位于 `include/dsim/waveform.hpp`，Python reader/转换工具位于 `experiments/waveform/`。DWF 为自有格式，不兼容 FSDB 二进制；仍不承诺跨未来格式版本的二进制兼容。

## 当前稳定版入口

```sh
~/vibe-coding/dsim-test/bin/dsim tb.sv --wave-support -o sim
./sim --waveform run.dwf --wave-async --wave-buffer-bytes 8388608 \
  --wave-mode ordered --wave-stats
python3 experiments/waveform/dwf.py unpack run.dwf run.vcd
```

`--wave-support` 是编译参数，其他波形选项传给生成的仿真程序。输出路径必须不存在。省略 `--wave-async` 时使用同步路径；默认采集模式为 `settled`，需要保留同 tick 的有序变化时显式选择 `ordered`。

独立线程的数据流为：

```text
仿真器已提交变化 → 不可变四态快照 → 有界 FIFO → 单独接收线程
  → 时间差/信号 ID/四态 XOR 编码 → 独立 Zstd 块 → CRC/写盘/时间索引
```

接收线程创建、持有并销毁 writer，编码和文件 I/O 都在该线程执行。队列满时仿真线程背压等待；关闭时排空并 join，后台错误传回调用者。预测回滚的数据不进入输出队列。预算只约束待处理 batch，包含正在消费的 batch，不是进程 RSS 上限；具体计费见下文[独立接收线程](#独立接收线程编码压缩与写盘m148)。

输出层次、信号和时间窗口由用户选择，见[范围参数](#用户指定输出范围m149)。完整块检查点和常驻时间索引仍有规模限制，百万信号长期仿真、分组跳读和增量索引尚未验收。以下各日期小节记录实现过程，其中的“下一批”属于当时计划；当前可用接口以本节及 M148/M149 小节为准。

M83 格式选择：生成程序使用 `--waveform output.vcd` 时自动输出标准文本 VCD，`.dwf` 选择压缩容器；显式 `--wave-format vcd|dwf` 覆盖后缀。其他后缀与 `$dumpfile/$dumpvars` 保留既有默认。DWF 编码没有变化；本轮验收及已知历史差异见 [v3 修复](report-v3.md)。

## 数据路径

目标是 RTL 和门级共用一个波形写出后端：编译期生成稳定的信号 ID、层次/范围/别名字典，运行时在已解析的信号值变化处写入二进制记录。门级名称需要在释放 Network 名称之前按所选 dump 范围导出；同一个 resolved net 的多个层次名称共享一份值流。禁用波形时不创建字典和压缩器，默认性能基准继续关闭波形。

不能只把 VCD 文本送给熵编码器。先去掉时间和信号名称的文本冗余，再处理四态数值与变化分布，最后做熵压缩。Zstandard 采用 Huffman 和 FSE 等编码，但它的普通压缩流不提供波形按时间定位能力，所以索引、检查点和独立压缩帧属于容器层设计。参考 [Zstandard 格式规范](https://github.com/facebook/zstd/blob/dev/doc/zstd_compression_format.md)。FST 是后续比较和互操作的候选，当前没有测量 FST，也不声称优于它；参见 [GTKWave FST 文档](https://gtkwave.github.io/gtkwave/internals/fst-file-format.html)。

## 已实现的实验格式

| 层次 | 原型编码 |
| --- | --- |
| 文件 | 8 字节版本魔数、META、BLK1 块、INDX、16 字节尾部 |
| 信号字典 | UTF-8 信息以 JSON 的 ASCII 转义保存；VCD header 指令、层次分量、原声明、范围、同 ID 别名；每个独立值流一个整数 ID |
| 时间 | uint64 tick，ULEB128 时间差；保留每一个原始时间标记，包括相同时间的重复标记与无变化标记；精度保存于原 timescale 声明 |
| 数值 | 任意 1–1,048,576 位四态；`aval/bval` 两平面，0/1/X/Z 整向量专用码，普通二态单平面、四态双平面，或与前值 XOR 后去掉高零字节 |
| 变化 | 时间 opcode、值 opcode + ULEB128 信号 ID、控制 opcode；保持输入记录顺序，不合并同 tick 的多次变化 |
| 检查点 | 每块之前的绝对时间和全部值流状态；首次未赋值与全 X 区别保存；检查点不依赖前块 |
| 块 | 默认实验测量每 4096 事件一块；每块独立 raw / DEFLATE(level 3) / Zstandard(level 3)，压缩后更大则回退 raw |
| 校验与索引 | 每记录 tag/codec/原始长度/存储长度/CRC32；索引保存块起止时间、文件范围、事件数；尾部保存索引偏移和结束魔数 |

`aval=0,bval=0` 为 0，`1,0` 为 1，`1,1` 为 X，`0,1` 为 Z。没有将 X/Z 降成二态；不同别名不重复写值。按原始 VCD 声明和标准缩写规则归一化数值，不保留 VCD 空白、大小写与向量前导零的字节表现，因此“无损”指 header token 与有序四态事件等价，不是 VCD 文本逐字节相同。

压缩块之外的记录头采用 little-endian `<4sB3xIII>`：tag、codec(0/1/2)、三字节保留零、原始字节数、存储字节数、CRC32。尾部 `<Q8s>` 为索引记录偏移和 `DWFEND01`。解码器按长度限制展开数据，拒绝未知 codec、非法宽度/ID/varint、截断、校验失败和越界索引；完整扫描同时检查相邻检查点的状态一致。原型还不是经过不可信输入模糊测试的生产读取库。

每个 BLK1 解压后为：检查点绝对时间、信号数、依次排列的完整状态、事件数、事件流。整数使用最多十字节的规范 ULEB128。opcode 0 后为时间差；opcode 1 后为 ID 和值编码；opcode 2 后为 JSON 控制 token 数组的字节长度和内容。值 mode 0/1/2/3 为全 0/1/X/Z；4 为固定 `ceil(width/8)` 字节 aval；5 为同样长度的 aval 和 bval；6 为两个“字节数 + trimmed XOR 平面”，只用于变化值；8 为未赋值，仅用于检查点。所有数值字节低位在前，末字节超出 width 的位必须为零。INDX 是上述五字段数组的 JSON 列表。

## 定位、回放和限制

时间查询二分找到首个结束时间不小于 start 的块，读取检查点并回放块内 start 之前的记录，返回 start 之前的状态和 `[start,end]` 的全部事件。若一个 tick 被分到多个块，会继续读取这些块，保留同时间的全部变化。原型索引常驻内存，写入保留当前信号状态、单块编码和随块数增长的索引，不保留整个历史；读取窗口仍需解码相关块中的全部信号，尚无按信号分组跳读。

VCD 导入/导出支持数字 scalar/vector、层次、范围、别名、dumpvars/dumpon/dumpoff/dumpall 和 comment。real/string/event 变量及扩展 VCD 暂时拒绝；这是格式原型边界，不影响未来以独立 typed stream 扩展。VCD 未记录的事件区、delta 编号或被源仿真器省略的毛刺无法恢复。原生接口将明确提供 settled-tick 与 ordered-change 两种采集语义，事件区/序号是否持久化需以调度测试和性能测量确定，不能声称仅凭 VCD 具备这项能力。

正常读取要求最终索引；异常退出的文件可通过下述独立恢复命令重建索引。增量索引、目录压缩与百万信号下的检查点分组仍待实现，否则全状态检查点会产生很大的稀疏波形开销。原型每记录限制 64 MiB，检查点限制 32 MiB，不宣称能覆盖百万信号和长期仿真。CRC32 用于检测意外损坏。

## 中断文件恢复

```sh
python3 experiments/waveform/dwf.py recover interrupted.dwf recovered.dwf
python3 experiments/waveform/dwf.py unpack recovered.dwf recovered.vcd
```

恢复扫描 META 后连续的完整 BLK1，逐块核对长度、压缩帧、CRC、四态值及检查点连续性。末块未写完时保留它之前的完整块；缺失、截断或可识别但损坏的最终索引可重建。完整数据块或 META 损坏会失败，不跳过坏块继续拼接。正常 Reader 仍要求合法结束索引，不会隐式截断数据。

输出必须是新文件，输入保持原样。META 和保留的数据块逐字复制，只重新写索引及尾部；不重新压缩事件。命令返回恢复的块数、事件数、最后完整时间、复制字节数和移除的尾部字节数。尾部字节数包含被替换的旧索引，不能当作丢失事件数；尚在 writer 内存或未完整落盘的块无法恢复。读取期间检测输入大小及修改时间变化，处理中断文件时应使用已停止写入的文件或副本。

Python 3.14 优先使用 `compression.zstd`；旧版 Python 可使用系统 `libzstd`，raw/DEFLATE 使用标准库。两个 Zstd 路径都限制单帧和解压长度。C++ 原生 writer 和文件版本在此次恢复功能中保持一致，不产生新的波形采集开销。实际原生 RTL/SDF 的 ordered/settled、raw/Zstd 与完整 VCD 对照、截断恢复和时间窗口验证见 [恢复验收](../validation/m6-wave-recovery/README.md)。

## 验收与接入顺序

1. 已实现 Python writer/reader、VCD 双向转换、时间窗口读取；以手写四态/别名/控制记录、跨块同时间变化、随机 1–1024 位独立整数 oracle、损坏/截断和解压长度限制验证。三种 codec 都需通过。
2. 捕获现有四态门级 fixture 和生成 RTL 的宽总线/稀疏变化 VCD；固定输入记录 SHA256，保存三次写入、VCD 全文件压缩基线、270 次窗口查询和完整回放证据。数据见 [验证记录](../validation/m6-waveform/README.md)。Python 吞吐包括 VCD 解析，没有代表 C++ 热路径性能。
3. 下一批用 C++/libzstd 实现后端，先提供显式 dump 范围、VCD 与 DWF 两个 writer，以及编译生成的 RTL/门级信号表；不因采集波形改变 Active/Inactive/NBA 调度和驱动解析。关闭/开启波形在相同原生程序上交替测量。
4. 根据百万信号/稀疏变化 profile 引入分组流、差分检查点/周期全检查点、选择信号跳读、异步压缩与增量索引；使用有界队列和背压，不丢事件。块大小按压缩率、RSS 和跳转延迟共同选择。
5. 以相同信号选择、时间精度和采集语义比较 dsim VCD/DWF、VCS 可用波形及 FST 转换；单独测无波形运行时间、开启波形增加的 CPU/RSS、写入带宽、文件大小、完整读取、单信号/时间窗口查询和损坏恢复。压缩率不能预先给出通用保证。

## 原生接入进展（2026-10-17）

2026-10-18 新增完整事件流式比较：`python3 scripts/compare_waveforms.py left.vcd right.dwf`。比较规范化后的层次、范围、别名组和完整有序记录，保留重复时间标记、同刻变化、X/Z 及控制记录；允许编码 ID、声明顺序及等价时间单位不同。比较期间检查输入身份变化，报告拒绝覆盖已有文件。该工具与统一流程已经接通，不将完整事件历史载入列表，但仍保存字典、索引和当前解码块/VCD 行。两平台新增测试、各 104 对真实捕获及五种统一流程通过；没有修改文件格式、原生采集或压缩算法，也没有新增仿真提速结论。详见[验收记录](../validation/m6-wave-streaming/README.md)。

当前开发版已加入 `include/dsim/waveform.hpp`，经 `--wave-support` 编译后可用运行时 CLI 捕获 RTL/门级信号到 VCD 或 DWF，支持作用域/深度、settled/ordered、raw/Zstd。编码复用原型格式；原生 META 省略冗余 aliases JSON，以 header 为准。已增加四态/范围/别名/同 tick glitch 和完整 VCD/DWF 比对，以及预测错误分支不泄漏输出的回归。此前 Python 原型测量保持为历史数据，不代表原生吞吐或 overhead。

0.10.0 生成模型使用模块 timescale 推导的 uint64 全局 tick，波形单位自动匹配实际精度，运行时拒绝不匹配的单位标签；`$dumpfile/$dumpvars`、百万信号分页检查点、增量索引尚未实现。截断恢复现已通过独立扫描命令接入。原生 writer 使用独占创建保护已有文件。settled 采集维护 change 值副本，使事务提交时的延迟 tick 回放不会读取未来内核状态。

0.12.0 原生同程序交替测量见 [性能记录](../validation/m5-driver-inline/README.md)。1 万触发器、200 周期的相同全网范围，VCD 9,317,158 字节、DWF/Zstd 5,646,864 字节，约 1.65 倍；CPU 中位数 0.64/0.66s，同一捕获程序关闭时 0.43s。三次完整解码一致。该结果说明高活动标量网并未重现历史宽总线原型的高压缩率；继续按块大小、ID 编码、检查点与分组实测改进，不能只提高熵压缩级别。

## 有界异步块压缩（2026-10-18）

已编译 `--wave-support` 的模型可使用运行时参数：

```sh
./sim --waveform run.dwf --wave-codec zstd --wave-compression-jobs 4
```

`--wave-compression-jobs` 范围1–16，默认1保留同步路径；大于1要求DWF/Zstd，非法组合在创建输出前拒绝。生成波形程序的编译命令自动链接线程库。线程数用于压缩，与仿真分区或worker数分别设置。

仿真线程完成信号采集、四态/XOR编码及块检查点，再将独立BLK1原始字节交给后台线程。每个线程有独立Zstd上下文，计算压缩及CRC；文件写入、索引、计数与按序提交仍归调用线程。结果按原块顺序提交，线程完成顺序不改变文件。META/INDX仍同步处理，格式保持`DWF1P001`。预测分支只有事务提交后才进入采集；并行流仍在全局窗口提交后归并，然后进入压缩队列。

未提交块最多`2 × jobs`份，同时原始长度计费上限为64MiB；已压缩完成但尚未提交的块继续占用其原始长度额度。达到任一上限时等待并提交最早的块，不丢事件。该上限只约束待提交块的原始长度总和，不是整个进程RSS上限：当前编码块、全状态检查点、Zstd工作区及线程栈另占内存。嵌入式Dwf构造接口允许降低预算，CLI当前固定64MiB。超预算单块明确失败；关闭时排空、顺序写出并join线程，后台异常通过future返回调用者。异常后只能恢复已经完整写出的前缀。

本地定向验证包含114份完整捕获、69对逐字节身份、1024位独立整数oracle、64KiB预算背压、错误预测回滚、全局并行窗口、后台异常与截断/损坏恢复。另12对与旧454默认writer逐字节一致；macOS ASan/UBSan及TSan内核测试通过。456完整本地/Linux各105项均已通过并独立审计，Linux114+4跨平台捕获及三份完整代码身份也通过，见[异步压缩记录](../validation/m6-async-wave/README.md)。后继457将线程/块大小控制接入统一JSON清单，六类流程18次编译/54次运行、12对文件身份和10非法配置通过，见[工具流程](tool-flow.md)。尚无异步压缩吞吐、CPU/RSS收益结论；百万信号分组检查点及增量索引仍待实现。

## 独立接收线程：编码、压缩与写盘（M148）

```sh
dsim tb.sv --wave-support -o sim
./sim --waveform run.dwf --wave-async --wave-buffer-bytes 8388608 --wave-stats
```

`--wave-async` 使用一个专用接收/写出线程。仿真线程采集已提交的时间、信号ID、不可变四态值快照及 dump 控制记录，按批提交 FIFO；该线程独占 DWF writer，完成变化量编码、块检查点、Zstd、CRC、文件写入和索引收尾。宽值共享不可变存储，后续仿真写入不会改变已提交快照。并行仿真仍先在全局提交处合并再进入单 producer 队列，错误预测不会进入输出链路。

格式保持 DWF1P001，包含信号字典、时间差/数值 XOR、独立压缩块、检查点和时间索引；可由现有 reader/window/recover 工具读取。这里借鉴压缩波形的通用架构，不声明 FSDB 文件兼容或更好的压缩率。

`--wave-buffer-bytes` 范围1024–67108864，默认8MiB，仅与 `--wave-async` 一起使用。预算计费包括队列中和正在编码的 batch；满时背压等待，不丢事件。调用线程另有至多256记录/64KiB的 staging（单条更大时独立成批，仍不能超过预算）。字典、当前/前值、编码块/全状态检查点、索引、Zstd工作区、容器/线程开销另计，因此预算不是 RSS 上限。已提交 batch 的 value charge 保守计入完整宽值数据，即使其底层共享。

关闭时排空、写索引并 join；初始化/编码/压缩/写入/关闭错误传回调用者，析构也会 join，已有文件保护保持。`WAVE_ASYNC` 统计报告 writer_threads、预算、峰值 pending 计费量、峰值排队批次和背压等待次数；普通 WAVE 字段保持。

该模式要求 DWF/Zstd 和 `--wave-compression-jobs 1`；旧 `--wave-compression-jobs 2..16` 是另一种后台块压缩策略。未开启新选项时保留原路径；VCD 仍是标准文本。统一 JSON 流程可设置 `"wave_async":true,"wave_buffer_bytes":8388608`，只对 DWF 运行生效。

当前仍有全量块检查点/索引增长等规模边界，未宣称百万信号长期仿真已经验收；本批不由功能验证推断吞吐或仿真速度提升。

## 用户指定输出范围（M149）

```sh
dsim tb.sv --wave-support -o sim
./sim --waveform selected.dwf --wave-async \
  --wave-scope top.cpu --wave-scope top.bus --wave-depth 2 \
  --wave-include '*data*' --wave-include '*valid' --wave-exclude '*debug*' \
  --wave-start 1000 --wave-end 8000
```

`--wave-scope` 可以重复，取多个层次子树的并集，按完整层次边界匹配；`top.u` 不会选中 `top.u2`。`--wave-depth 1` 仅选择各根层次直接声明的信号，2再包含下一层，0（默认）不限深度。没有指定根时，从顶层计算深度；重叠根各自计算，所以可同时选择某个模块及其特定子模块。

`--wave-include`、`--wave-exclude` 均可重复，匹配点号连接的完整声明名。包含规则取并集，再减去排除规则；未指定包含规则时保留范围内全部声明。`*` 匹配任意长度字符（含层次点），`?` 匹配一个字符，其他字符均按字面值匹配。数组名如 `'top.u.mem[3]'` 中的方括号不是字符集合；转义标识符去掉前导反斜杠。请用shell引号保护模式。选择按声明而非内部信号ID应用，选中一个别名不会把被排除的其他别名写入字典。若最终没有信号，在创建文件前报错。

`--wave-start`、`--wave-end` 是编译精度下的非负整数tick，闭区间；默认0和UINT64_MAX。窗口仅限制输出，不改变调度或提前结束仿真。进入窗口时先写入此前已观测的信号状态，然后保留窗口内的四态变化、同时间事件顺序及dump控制。窗口起点没有事件时仍能获得准确的初始状态。已有 `$dumpvars` 晚于起点时，捕获从实际首次采样开始，不伪造此前历史；窗口不与采集时间相交时，输出带有效字典且没有事件的文件。

VCD、同步/异步DWF、串行/时间轮/并行合并及SDF共享这些选择规则；异步模式的时间窗口处理也归专用writer线程。时间窗口需要保留一份所选信号的进入窗口前状态，这部分内存另计。默认不指定时间窗口时不构造此适配器。源代码 `$dumpvars` 的选择与CLI选择取交集，dump开关仍有效；已有dump范围不能由CLI扩大，需同时调整测试平台中的 `$dumpvars`。

统一流程支持 `wave_scopes`、`wave_include`、`wave_exclude` 字符串列表及 `wave_depth`、`wave_start`、`wave_end` 整数。范围只传给VCD和DWF，不影响无波形基线。异步/压缩配置仍只传给DWF。与VCS比较时，将参考时间线投影到同一物理时间区间；未显式指定 `wave_bits` 时，验证全部已选择声明位，不静默取字典交集。
