# M25：packed struct / union

补入 packed struct、等宽 packed union typedef、别名嵌套、编译期成员布局及直接 C++ 读写。支持 signed 整体/成员、混合两态/四态、enum 成员的强类型赋值、数组字的动态索引、成员位/范围/固定宽度动态选择、拼接目标、复合赋值/增减、delay/NBA 和内建类型端口/子程序的输入实参。模块/过程/静态子程序、参数实例及 generate 克隆分别重建布局与类型身份；成员作用域独立，不把字段注册为外围信号。范围见 [说明](../../docs/packed-aggregates.md)。

运行时只使用已有 packed 位向量和切片；无结构对象或类型分派，RTL/SV 与紧凑门级 parser 继续独立。新增一个有边界的 indexed-part helper，不改变状态布局或事件队列。五份 M24 完整 CPP 在严格移除这一段新增 helper 后与旧冻结结果逐字节一致；不是宣称原始 CPP 文件完全不变，记录见 legacy-identity.json。波形按整体 packed 位向量导出，成员类型/枚举名称元数据尚未导出。

四个共同模型 values/effects/hierarchy/parallel：serial/time-wheel/双线程 × ordered/settled × VCD/DWF，共 **50 次捕获**（含两次真实失败预测回放），22 类非法输入、两个独立原生边界模型及隐式端口顺序交换回归通过。独立核对六项信号类型/宽度、四个 generate 布局值、两个域的输出时间/值，parallel 为真实两个分区；两个数组字有自检。动态字/位地址在读改写中只求值一次。额外覆盖小结构上的 65 位越界成员读取，独立预期为高 61 位 X 与低 4 位有效值，确保没有其他宽变量时仍启用宽向量代码生成。

实际 VCS W-2024.09 使用同四组逐字节输入，TRACE 和 **996 条可观察物理位时间线**一致；仅列明 VCS 未导出的两个数组字，无普通设计信号、临时量排除或名称映射。原始源、编译/运行状态与日志、实际 VCD 保留于 vcs/，verify.py 逐位核对身份及时间线。另有五个实际探针（probes/、probe-evidence/、probe-results.json）：

- 隐式端口连接：移除旧点号吞并规则后，在 grammar 中生成真实同名连接；交换 `.y,.a` 顺序仍按端口名绑定，dsim 与 VCS 实跑通过。
- 混合两态/四态默认值和 X/Z：整体底层保持 X/Z，读 bit 成员才转换为 0，写入 bit 成员不提前清除混合整体的底层位；与 VCS 探针一致。
- 未声明类型的参数成员访问，两者均拒绝。本批没有命名类型 parameter/localparam 声明，不把未类型化参数强行当作 aggregate。
- packed enum 成员 `++`：该安装 VCS 报 ERRORENUMBOP，dsim 独立预期执行通过。共同模型使用显式同类型赋值，原拒绝输入保留。
- 部分越界成员动态选择：VCS 在 lower clipping 自检处触发 fatal，dsim 按成员边界裁剪并通过独立预期。原始差异输入保留，不计入共同模型差分通过。

后两项是保留的兼容差异，未据此作完整标准合规性或供应商内部根因判断。VCS 对 fatal 返回 0，因此探针显式检查 Fatal 标记和未出现完成 TRACE，不把进程退出码 0 当作功能通过。

本地九项既有定向 CTest 通过 177.29 秒，最终类型/子程序/新功能/parser 五项通过 98.06 秒；末次宽选择修复后新功能单项再次通过 42.06 秒，五份共同模型完整 CPP 身份不变，只有新增边界检查启用宽向量路径。首轮负用例格式串拼接、旧单测使用新增关键字 packed 作变量名，以及单成员函数实参被旧 factory 遗漏的问题均已修正，初轮日志保留。末次隐式端口回归修复后，新功能/parser/编译总回归三项通过 54.93 秒，实际 VCS 及原生顺序交换检查通过。Bison 仍为 46 个 shift/reduce conflicts，无新增 reduce/reduce。

parser 单测（三轮清理 × 两参数实例）、七组输入各三轮清理、七个实际生成程序通过 macOS ASan/UBSan（含真双线程），关闭 leak 检测。程序与正式捕获/独立原生检查的完整 CPP 身份逐项核对，见 sanitizer-runtimes.json、native-sanitizers.json 和日志。

Linux 初始同源干净构建及六项定向 CTest 通过 143.29 秒；随后同步宽选择修复和独立边界检查、重建，两项相关回归通过 85.73 秒。最后同步隐式端口修复、重建，新功能/parser/编译总回归三项通过 90.97 秒，退出 0。最终两平台 **八份完整 CPP** 字节相同（四组串行、一个双线程和三个补充模型），Linux 实际 TRACE/996 条位时间线再次匹配 VCS。初始、宽选择及最终构建/测试、三份源清单保留于 linux/，不把初始构建冒充最终冻结源码的干净构建。

最终 632 文件源包 SHA256 为 `543189a464b31f3c61e5ab23af488bd3c1a1d6fee7c78bcabbedaaf505896f96`，工作区/远端逐项匹配 source-manifest.json。归档信息 source-archive.json，不包含本报告、汇总结果及 plan，避免结果相互引用改变源身份。已实际读完远端 `/home/yangfan/vcs/vcs1017.md` 的 217 行，采用 RTL 字级编译展开与门级独立专用化的分工，SDF 路径事件热点留作后续优化依据。

尚缺匿名/非 packed 聚合、赋值模式、命名类型参数/端口/子程序类型、完整成员事件控制及 always_comb 读写粒度、package/interface、automatic/递归/动态数组、并发 SVA、class/随机化/UVM 和完整时序/事件区。本批未跑完整 CTest 集或 Linux sanitizer，也没有新的速度测量；历史 M22 性能数字不当作本批新测。
