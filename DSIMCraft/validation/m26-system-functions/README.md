# M26：整数与位向量系统函数

已接通 `$bits`、`$clog2`、`$isunknown`、`$countones`、`$onehot`、`$onehot0` 的 parser、常量/参数/范围/generate 展开和实际 C++ 执行。`$bits` 查询自决定类型，不执行实参；其他函数实参只求值一次，外围宽度不传播进去。支持现有整数、命名类型/enum/packed 聚合、数组字、成员/选择及宽向量，另补齐子程序 logic/signed/unsigned 形参入口。边界见 [说明](../../docs/system-functions.md)。

查询与类型元数据只在编译期存在；位函数使用有条件启用的内联 C++ 模板，按 64 位字做 popcount/最高位操作。运行时状态、事件队列和 RTL/门级 parser 的分工未改。新宏关闭时不产生执行分派。五份 M25 完整 CPP 严格移除新增 guarded helper 后与旧冻结结果逐字节一致；不是原始 CPP 完全不变，记录见 legacy-identity.json。

四个共同模型 constants/vectors/effects/parallel，经 serial/time-wheel/双线程 × ordered/settled × VCD/DWF 共 **49 次捕获**，含一次真实失败预测回放；28 类拒绝和额外 130 位原生探针通过。独立检查全部 **256 种四位四态组合**、两组参数实例和 generate 布局、自决定宽度、地址/增减单次求值、delay/NBA 取样和两个独立域输出时间线。parallel 实际为两个分区，错误信号均为 0。

实际 VCS W-2024.09 对逐字节相同的四组输入执行成功，TRACE 与 **1577 条可观察物理位时间线**一致。仅列明 VCS 没有导出的八个数组字（两个实例各三个 mem 字、effects 的两个 mem 字）；无普通信号、函数局部量或临时量排除，也无名称映射。这八个字的内容不包含在上述位时间线比较中；共同源另检查数组查询宽度和地址副作用。VCS 源、编译/运行状态、日志和实际 VCD 保留在 vcs/，verify.py 检查身份和逐位时间线。

额外语义探针保留于 semantics.sv、wide-clog2.sv、probes/：

- 窄向量探针核对 `$clog2` 的 0/1/负位模式/X/Z、六个函数的返回位宽、计数/one-hot 对 X/Z 的处理及 `$bits(i++)` 不执行实参。
- 四态 integer 接收的 130 位 `$clog2` 对 2^100、2^100+1、2^129、全 1 和高字含 X 均与 VCS 一致，VCS/原生完成 TRACE 和独立预期通过。
- 初始探针使用两态 int 接收高字含 X 的结果，VCS 输出 130、dsim 输出 0，源和两份输出保留于 probes/int-receiver。这个原始探针却对两态接收变量期待 X，因此双方自检均失败；不把该无效自检视作四态函数返回失败。仅保留实际输出差别，未判断内部根因或完整标准合规性，也未把该探针算作共同模型差分通过。VCS fatal 可返回 0，探针同时检查 Fatal 和完成 TRACE。

本地十项既有定向 CTest 通过 **151.57 秒**：枚举、命名类型、packed 聚合、子程序、类型参数、cast、编译/门级总回归、parser 单测及门级 parser smoke。最终新增功能/parser 两项 CTest 通过 **95.18 秒**。首轮常量拼接缺少求值结果、查询静态函数返回类型、logic 形参入口已修正；探针中 int packed 范围非法、%t 预期单位、空实参诊断预期、VCD 去除重复不变值和额外宽探针接收类型也已修正，初轮日志保留，不冒充首次即通过。

parser 单测（三轮清理/两参数实例）及五组输入各三轮清理通过 macOS ASan/UBSan；五个实际生成程序亦通过，含真双线程。四个共同程序按正式完整 CPP 编译并核对实际 DWF 时间线；额外 wide 程序核对独立 TRACE。关闭 leak 检测，见 sanitizer-runtimes.json、wide-sanitizer.json 与日志。Bison 仍为 46 个 shift/reduce conflicts，无 reduce/reduce。

Linux 最终同源干净构建及新功能/parser/编译总回归三项 CTest 通过 **172.60 秒**、退出 0；**六份完整 CPP** 与 macOS 字节相同（四组串行、parallel 双线程和 wide 探针），Linux 实际 TRACE/1577 条位时间线再次匹配 VCS。源身份、构建/测试和生成证据保留在 linux/。早先辅助远端启动脚本的引号问题已修正，未产生构建结果，也未算作成功。

最终 **646 文件**源包 SHA256 `1bbcfbf1a568955d6c4cf5b4a69683b68c91becb4b9dea29f544d82d9ee8bb85`，工作区与远端按 source-manifest.json 逐项一致；source-archive.json 记录归档身份。本报告、plan 和汇总结果不放入源清单，避免相互引用改变源身份。

尚缺多参数 `$countbits`、数组维度/边界查询、`$typename`、real/string 查询、类型参数/完整类型端口、package/interface、automatic/动态数组、并发 SVA、class/随机化/UVM 和完整时序/事件区。本批未跑完整 CTest 集或 Linux sanitizer，没有新的性能测量，历史 M22 数字不当作本批新测。
