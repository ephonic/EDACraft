# M35：限定选择语句与 VCS 功能对照

已实现 unique/unique0/priority if/else-if、case/casez/casex/case inside，包括首次匹配选择、重叠/漏匹配诊断、同一 case item 的多标签去重、四态与宽/符号上下文、else/default、函数/task、参数实例化、delay、并行和回滚。RTL parser 克隆保留限定信息；紧凑门级 parser 不变，Bison 仍为 47SR/0RR。具体范围见 docs/selection-checks.md。

检查在执行语句时取样，按实际调用过程排队（函数/task 继承调用过程）；当前支持的 Active/Inactive/NBA 集合稳定后确认。event/wait 恢复、always_comb/latch 重触发会清除该过程尚未成熟的报告，delay/#0 不清除。循环每次违规独立排队；Sim 快照拥有队列，打印使用已有推测事务，失败回放不重复报告。功能未使用时预处理宏关闭新增状态和调度分支；可能报告的过程按现有副作用规则保守合并。parallel 用例实际为两个独立分区。

六组共同源、72次后端/格式/模式捕获，另有2次1ns检查点的实际失败预测回滚，共74次。八类非法/未支持形式明确拒绝，12次独立预期报告通过。最终新功能/parser/集合匹配三项 CTest 85.76秒通过；此前 automatic/多维数组/循环/编译总回归/门级及 parser 也通过，合计八项不同测试。初次集合匹配负例期待旧语法错误，现已变成更具体的 inside requires case 拒绝，更新相应诊断后重跑；原失败日志保留，不把初次整组计为全部通过。

实际远端 10.131.254.103、source /apps/EDAs/syn.bash、VCS W-2024.09，六组共同源 TRACE/自检及全部756条直接导出物理位时间线相同，无名称映射、信号/位排除。VCS 输入、dump wrapper、编译/执行状态及原始波形见 vcs/；verify.py 严格比较每一位，diagnostic differences 单独核验，未将差异报告计入一致数。

**诊断尚未全部与 VCS 对齐：native 12次、VCS 15次。** branches/cases/glitches/parallel 的报告位置/种类/次数/时间均相同；events 的 0ns initial 入口等待/声明初始化事件及 1ns 重唤醒，VCS各多一次，functions 在同时间步重唤醒的调用过程 VCS多一次。native 按延后确认/逐过程清理预期处理。这三个差异的源、双方完整报告和逐项记录均保留，vcs-results.json 状态为 PASS_WITH_KNOWN_DIFFERENCES。报告文本与同刻相对打印顺序也不宣称与 VCS 相同；当前机制不等于完整 Observed/Reactive 区域或全部 assertion control。

原始 probes/basic.sv 包含在 unique 条件中调用的函数。VCS 发 IUC 编译告警、忽略检查，实际调用一次；native 按 IEEE 1800-2017 12.4.2 继续求值三个条件，实际调用三次；VCS 还未报告该探针后续的 unique-if 违规。源和双方原始输出均在 probes/，results.json 标为 KNOWN_DIFFERENCE，不计入共同源波形一致结果。probes/glitch.sv 的双方 TRACE 相同且都无误报。

本地负例发现 Flex 返回 MY_EOF 时提前销毁扫描器，导致 Bison 在截断输入报错时访问失效 yytext，诊断包含随机字节。移除词法动作中的提前销毁，扫描器仍在下一次 init 时释放/重置；加入三轮截断失败后重新解析回归。初次测试脚本生成 endcaseendmodule 的无效输入触发该问题，日志保留；修正空格后继续检查真正要拒绝的 casez inside。

macOS ASan/UBSan parser单测、六组语料各三轮清理、六个实际生成程序（含真实双线程）、完整 ordered 波形和12次诊断检查通过，关闭 leak 检测，证据在 sanitizers/。当前编译器重跑此前 M34/M32 的实际波形，分别1544直接位+660数组观察位、968直接位+96数组独立预期保持通过。

774文件冻结源包记录在 source-archive.json，逐文件哈希在 source-manifest.json，七份完整实际生成程序身份在 final-identity.json。Linux 同源干净构建及六项定向 CTest 223.43秒通过、退出0；774文件逐项哈希和源包SHA-256一致，七份完整实际C++跨平台字节一致，Linux实际756位波形及12/15次诊断和三个已知差异再次核验。完整结果为 results.json（PASS_WITH_KNOWN_DIFFERENCES），证据在 linux/、platform-identity.json 和 linux-vcs-results.json。

仍缺完整 assertion control、case matches/pattern、完整 SVA/UVM 及事件区域，以及数组端口/动态数组、ref/递归/常量函数、package/interface/class 等既有缺口。本批未运行全量 CTest、Linux sanitizers或新速度测量，未宣称完整RTL/门级/VCS功能或性能对齐。
