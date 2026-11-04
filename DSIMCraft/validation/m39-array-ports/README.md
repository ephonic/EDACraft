# M39 静态变量数组端口与 VCS 对齐

本批接通模块input/output的静态unpacked变量数组，支持整数组及常量下标前缀的子数组、多维/非零下界/相反方向、受支持的integral/bit/logic元素和同宽两态转换。秩、每维大小和元素位宽在编译时检查，按每维声明顺序对应，输出展开为具体变量字驱动并检查冲突。逐元素生成静态C++适配过程，没有运行时数组类型分派；RTL/紧凑门级parser保持分离，runtime/parallel和词法/语法生成文件未改。

RTL parser的模块类型引用检查改为计算下标消耗后的剩余unpacked维度，支持子数组端口，并保留完整元素及packed选择的已有语义。新增公开入口三轮清理和秩错误单测。IR的数组端口signal_id为null、binding为array_adapter，array_elements列出formal/actual信号对应，避免数组端口沿用标量信号ID时map::at崩溃。另修复完整宽数组元素带delay时被误作标量、导致runtime报错的问题。

共同源在tests/array_ports：basic覆盖signed/XZ/NBA和相反方向，matrix覆盖三级层次/三维存储器的静态子数组以及逐维映射，types覆盖130位和两态输出delay，timing覆盖两态输入/传输式延迟NBA与惯性连续赋值，parallel使用两个真实独立分区及错误标志。五例×三后端×两模式×VCD/DWF共60次捕获；types/timing在1ns建立检查点、执行实际失败预测回放，再核对完整ordered波形，共62次。14类拒绝和一个独立输出子数组/不相交过程写入自检通过；并行输出时间线另按数学预期核对。

实际VCS为10.131.254.103的W-2024.09，source /apps/EDAs/syn.bash。共同源使用-full64 -sverilog -debug_access+all -top top -top dump，运行simv -no_save。五组共同源字节相同、TRACE/自检相同，全部2076条直接导出位时间线一致，无路径映射或位排除。其中包括packed观察信号；VCS未直接导出的全部2008个数组位（含父级存储器、各层输入/输出和子数组以外的字）经这些同源观察信号逐位逐时刻核验，不将两个数字相加当作独立VCS导出位。完整覆盖映射在tests/array_ports/observers.json，verify.py会拒绝未列出的数组字。原始源码/日志/状态/VCD在vcs，逐模型范围见vcs-results.json。

六组未改原始探针验证方向、同宽四态到两态、未连接数组输入和独立输出子数组，以及元素位宽/数组大小错误双方拒绝。命令、hash、实际退出状态和日志在probes/native、probes/vcs，run-probes.py可重跑。最初未连接四态数组错误地沿用了标量输入的Z适配，VCS实测为X；现改为保留变量默认值，四态X、两态0。双方最终输出TRACE open xx 00；修复前日志保留local/initial-vcs-open.log及initial-native-open.log，不隐藏这一实际差异及修正。M35/M36/M38历史差异未声称解决。

macOS ASan/UBSan parser单测、五语料各三轮清理、五个实际生成模型及完整ordered波形通过，包含实际双线程，leak检测关闭。日志、完整程序和hash在sanitizers，入口run-sanitizers.py。之前M38七份完整实际C++使用当前编译器重生成字节一致，证据m38-identity.json；这项身份核验不替代本批新增功能差分。原有array_port负例改为仍不支持的变量inout，原有net数组负例仍保留；对应旧回归纳入重跑。

最终本地/干净Linux构建和测试结果见results.json及local、linux。850文件冻结包身份见source-manifest.json/source-archive.json，包不含验收输出及plan进度记录；冻结后所列源码不再修改。六份完整实际生成程序（五串行、一实际双分区）在final-identity.json和platform-identity.json间核验；Linux实际波形再与同一原始VCS核验，结果linux-vcs-results.json。

复跑入口：ctest --test-dir build -R '^rtl_array_ports$' --output-on-failure；python3 validation/m39-array-ports/verify.py；远端run-vcs.py与run-probes.py接受输入和输出目录。

范围见[数组端口](../../docs/array-ports.md)：一般net数组、变量inout/ref、动态子数组、数组slice/拼接/默认值/赋值模式、整数组复制、enum/packed复合数组端口及数组形参仍缺；沿用非负unpacked下界限制，没有增加反向驱动net数组连接语义。本轮未跑全量CTest、Linux sanitizers或新性能测量，不称完整SV/VCS功能或速度已对齐。

最终验收：本地七项定向CTest 143.84 秒、Linux同源干净构建六项 262.27 秒全部通过、退出0；六份完整实际C++跨平台字节一致，Linux2076导出位及2008数组观察位再次匹配VCS（两项不相加）。850文件冻结源包SHA256 b821e73bc01cd3b63f0cd41206ff4b5bf9b028ed7bbde0ed68727da2b4e91161，冻结后所列源码未改变。
