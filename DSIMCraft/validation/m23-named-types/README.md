# M23：命名整数类型与静态子程序语句体

实现整数 typedef、已有别名再命名、signed/两态与单个 packed 范围；模块、generate、过程块及静态函数/任务局部作用域分别绑定，实例/generate 克隆保留类型身份并按本实例重新求宽度。类型节点 vtTYPE 不分配运行时存储，不可作普通值、左值或尺寸表达式。变量/一维数组声明及命名 cast 接入原编译执行、delay/NBA、波形、检查点与独立域并行。标量与显式 [0:0] packed 属性分别保留。门级紧凑 parser、runtime 布局不变。范围和限制见 [说明](../../docs/named-types.md)。

同时支持静态函数/任务省略 begin/end 的多语句体。修复旧常量 ===/!== 在 X/Z 存储模式下读取普通整数空指针的崩溃；新增 224 组单/多字四态 case equality 真值检查，以及命名类型三轮清理、两种参数实例和标量/packed 身份检查。

五例 values/scopes/effects/hierarchy/parallel 通过 62 次捕获、2 次实际失败预测回放、23 类明确拒绝。三后端、ordered/settled、VCD/DWF 完整捕获互相一致；另有 9 项参数宽度/符号/位值、9 项信号类型属性、4 个 generate 内部输出及两个并行输出的独立预期。类型定义没有成为仿真信号。parallel 是真实两分区，数组两个字由自检检查。

实际 VCS W-2024.09 五例共同输入的 TRACE 与 **1828 条可观察物理位时间线**一致；严格核对全部普通信号，仅枚举 effects 的两个未导出数组字，不排除普通信号。正式输入逐字节与 VCS 输入相同，SHA256/名单见 vcs-results.json，原始记录在 vcs/。Mac/Linux 六份完整 C++ 与最终重新发射身份的结果在 final-identity.json、platform-identity.json。

保留的 VCS 差异：原 hierarchy 的 generate 局部 typedef 常量 `word_t'('1)`，VCS 在 W=8/13 两例中 `$bits(C)` 都为 8；dsim 按实例为 8/13，造成内部十个物理位不一致。三个 VCS 诊断探针确认，等值的 `word_t'((W+g)*0-1)` 和显式尺寸 `(W+g)'(-1)` 得到 8/13。原输入/原始两边波形/完整 CPP 和诊断输入、日志、波形保留在 probes/generate-constant，不回写为原例通过。正式共同输入采用显式参数依赖的命名 cast，新增四个 generate 值的独立数学预期；不宣称任意命名常量 cast 全面兼容，也不将原因认定为已证明的 VCS 内部机制。

最后一轮审计发现 typedef 范围接受运行时变量、X/Z 或超出整数索引的高位后截断值，已增加展开常量/已知值/非负与 0..2147483647 边界检查；实数和单界范围也明确拒绝。五种非法范围加入 parser 重复异常清理检查，正式拒绝项增至 23。修复后重新运行本地两项、五组 parser/runtime sanitizer，并核对六份完整 CPP 与实际运行版本相同。

首轮还暴露了标量 typedef 被误标记为 packed [0:0] 的波形身份差异，已修正类型属性传递后重新验收。并行测试最初包含打印/诊断，按现有全局副作用依赖规则合成单分区；正式用例只在各域记录错误标志，由脚本核对波形，以验证两个独立域。初轮失败、错误标量身份、原始 generate 差异及 case equality 崩溃记录全部保留。

既有七项相关 CTest 全部通过（144.69 秒，整数参数/两态/子程序/整数 cast/总回归/门级/parser bundle）；标量修正后和最终共同输入再跑新用例/parser 两项通过（最终增加范围检查后 46.79 秒）。Bison 保持 M22 的 46 个 shift/reduce conflicts，无 reduce/reduce。parser 单测/五组正式输入各三次清理、五个实际生成程序（parallel 双线程）通过 macOS ASan/UBSan，关闭 leak 检测；正式 hierarchy 的等值输入改动后，parser/runtime 再次验证，并核对完整生成 CPP 身份。

Linux 同源干净构建后，最终范围检查修正版重建并通过四项定向 CTest（93.73 秒，退出 0）：named types、parser 单测、静态子程序和 parser bundle。606 文件清单逐项匹配工作区，两平台六份完整 CPP 字节一致，Linux 实际波形再次与同五组 VCS 的 1828 条位时间线匹配。初轮、中间轮和最终日志均保留在 linux/。606 文件冻结源包身份见 source-archive.json，生产代码和正式输入以 source-manifest.json 为准；初轮和标量修正版清单分别保留。没有完整 CTest、Linux sanitizer 或新性能测量。本批是功能补齐，不代表 SV/VCS 功能已完整；命名类型参数/端口、enum/struct/union、package/interface、automatic/复杂数组、并发 SVA、class/随机化/UVM、完整时序等仍未齐。
