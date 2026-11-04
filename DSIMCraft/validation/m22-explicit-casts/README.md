# M22：SystemVerilog 整数与常量尺寸 cast

接通内建整数类型 bit/logic/reg/byte/shortint/int/longint/integer/time、signed/unsigned 与正整数常量尺寸 cast。CLI 原先拒绝全部 cast，grammar 的占位分支会丢弃转换；本批移除旧全局拒绝并保留显式 AST 身份，接通参数常量上下文、绑定/实例/generate 克隆及直接 C++ 代码生成。RTL/SV 行为 parser 与门级紧凑 parser 保持独立，门级仍明确拒绝结构 cast，未改 runtime 布局。范围见 [功能说明](../../docs/explicit-casts.md)。

先按目标上下文执行内部运算，再截断为 cast 宽度，然后按结果符号参与外部扩展。两态类型逐位将 X/Z 转 0；尺寸/sign cast 保留内部表达式属性。操作数只求值一次，接入短路/三目、静态函数/任务、delay/NBA、波形、失败预测回放和现有并行依赖。仅需要两态转换的模型启用对应支持；不新增仿真事件。宽度必须是 1..1,048,576 的整数常量，拒绝零/负/未知/超限/运行时尺寸，包括一位 signed -1 和高 32 位非零的宽常量。

values/constants/effects/hierarchy/parallel 五例通过 **62 次捕获、2 次实际失败预测回放、11 类拒绝**。三后端、ordered/settled、VCD/DWF 逐项一致；参数 IR 的 15 项宽度/符号/值有独立预期，两个并行域有独立时刻/值预期，实际两分区九窗口。覆盖 130 位转换、嵌套截断/扩展、条件副作用、静态函数/任务、generate 克隆及延时 NBA；两个数组字由自检断言核对。原首轮十类拒绝之后增加一位 signed 负尺寸边界，最终为十一类；生产实现增加对应负值检查。最终运行日志 local-regression.log，初轮保留 local-regression-initial.log。

实际 VCS W-2024.09 五例 TRACE 和 **2214 条可观察物理位时间线**一致，按层次身份、位号、1ps 时间轴严格核对。仅列出两个未导出的 inline 计数器和两个数组字，不排除普通信号；名单/输入 SHA256 见 vcs-results.json，原始记录在 vcs/。VCS 拒绝 longint unsigned'(expr) 的初始探针；正式用例使用 unsigned'(longint'(expr))，qualified type cast 目前明确拒绝。

parser 单测新增三次解析清理、两个参数实例、常量转换宽度/符号/位值。Bison 当前 46 个 shift/reduce conflicts（M21 为 40），无 reduce/reduce conflict，日志保留。五组原始输入各三次解析清理、parser 单测及四个实际生成程序（values/effects/hierarchy 串行、parallel 双线程）通过 macOS ASan/UBSan，关闭 leak 检测；运行波形核对正式基线，见 sanitizer-runtimes.json 与 sanitizers/。最终本地编译器重新发射五份完整 C++，与实跑版本字节相同，见 final-identity.json。

既有 13 项本地定向 CTest 首轮 12 通过、1 失败；失败是旧总回归要求合法 4'(8'hff) 被拒绝。已把该项改为非法零宽 cast 的拒绝检查，生产代码和正式 SV 输入未改；原失败保留 local-existing-ctest-initial.log。更正后的第一次重跑因初轮遗留的 negative_cast 生成程序而失败；删除该生成文件后，单项通过 66.09 秒，合计 13 项唯一既有检查通过。两次失败和最终通过日志均保留，未改变生产代码或放宽拒绝断言。

最终 595 文件源包 SHA256 为 67d9641cdcabae7174fed6410179235a5c2fd04e4e70c4793906061872e924ef，逐项与工作区一致。Linux /tmp/dsim-m22-linux-J713Xq 同源干净构建，11 项定向 CTest 首轮 10 通过、1 项相同旧预期失败（217.35 秒）；更正后也清理初轮遗留生成文件，最终 compiled_regression 通过 67.63 秒，11 项唯一检查通过，任务退出 0。原始失败/重跑日志在 linux/。六份完整 C++（五份串行及一份双线程）与 macOS 字节相同；Linux 实际 TRACE/2214 条物理位时间线另行与同五组 VCS 对照通过，见 linux-vcs-results.json 和 platform-identity.json。

```sh
ctest --test-dir build -R '^(rtl_explicit_casts|rtl_semantic_memory)$' --output-on-failure
python3 validation/m22-explicit-casts/verify.py
python3 validation/m22-explicit-casts/run-sanitizers.py
```

typedef/enum/struct 命名类型、packed 类型转换、qualified type、dynamic $cast、real/string/void 转换与完整常量函数仍未实现；并发 SVA、完整验证环境/事件区和整体性能目标继续推进。本批未跑完整 CTest 或 Linux sanitizer。性能重测单独记录在 ../current-vcs-comparison/，不把功能正确性对照当成加速结果。
