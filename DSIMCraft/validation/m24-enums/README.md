# M24：整数枚举类型

新增 enum typedef 的真实名义类型身份，支持缺省两态 signed int、整数基类型/packed 范围/非 enum 整数别名基类型、成员显式值和自动递增、负数及宽四态成员。成员作为同作用域展开常量，类型/成员不分配运行时信号。别名保留同一 enum 身份，模块/过程/静态函数任务/generate 和参数实例各自绑定、克隆并求值。范围见 [说明](../../docs/enums.md)。

阻塞/非阻塞及带内部 delay 的赋值、声明初始化、一维数组字要求同一 enum 或显式 enum cast。无类型参数和同 enum 条件表达式保留类型身份；算术、数值类型/尺寸 cast、显式整数参数和 packed 选择不保留。enum 可转普通整数，显式 enum cast 可产生标签集合外的值；前置/后置和语句增减接入旧单次地址/RHS 求值路径，enum 复合赋值拒绝。所有身份检查在编译时完成，无运行时类型分派，RTL 与紧凑门级 parser 继续独立。

检查成员名称/值重复、值域溢出、过宽显式尺寸表达式、两态 X/Z、X/Z 后隐式值及自动递增溢出。实际 VCS W-2024.09 的 21 个语义探针接受/拒绝均与 dsim 一致（probes/ 原始输入与双方日志）；包括宽但可表示的参数、窄 sized 值、填充值、同宽 signed 位模式、负 unsigned、跨界递增、增减与复合赋值。探针不是完整标准认证。

四个正式用例 values/scopes/hierarchy/parallel：本地 50 次捕获、2 次实际失败预测回放、37 类拒绝通过。serial/time-wheel/双线程 × ordered/settled × VCD/DWF 全部捕获逐信号一致；另有两个参数、六项信号类型属性、四个 generate 值和两域输出的独立预期。数组两个字另有自检，parallel 为真实两个分区。

实际 VCS 同四组逐字节输入 TRACE 和 **1248 条可观察物理位时间线**一致。VCS 不导出 values 的两个数组字；VCS 为 enum 更新额外生成六个临时量：values 的 8/130 位、scopes 的 13/8 位，以及 parallel 两域各 8 位。验证脚本精确枚举这些名字和宽度，并确认它们不在设计信号中；无普通设计信号排除或名称映射。原始波形/编译运行日志保留在 vcs/，首次未枚举临时量时的身份失败保留在 vcs-initial-identity-failure.log。

本地新增 enum/parser 两项 CTest 通过 41.94 秒，八项既有相关 CTest 通过 222.59 秒（命名类型/整数 cast/类型化参数/两态/子程序/编译总回归/门级/parser bundle）。旧 named_types 对合法 enum 的拒绝用例更新为尚未支持的成员范围展开。首轮新回归在负用例拼接时缺空格形成非法 endendmodule，触发非 UTF-8 错误输出解码失败；更正用例边界后 37 类检查通过，原始失败日志保留。Bison 保持 46 个 shift/reduce conflicts，无 reduce/reduce。

parser 单测新增三轮清理 × 两参数实例，核对 enum/别名/成员/变量/无类型参数的身份及整数参数身份消除、宽值跨字递增、X/Z 成员和异常后清理。parser 单测和四组正式输入各三次清理、四个实际生成程序（含真实双线程）通过 macOS ASan/UBSan，关闭 leak 检测。五份最终完整 CPP 与实际捕获版本相同；六份 M23 旧用例完整 CPP 字节不变（legacy-identity.json）。

Linux 同源干净构建后五项定向 CTest（enum、命名类型、静态子程序、parser 单测和 parser bundle）通过 96.45 秒、退出 0。两平台五份完整 CPP 逐字节一致，Linux 实际 TRACE 和同 1248 条位时间线再次匹配 VCS。616 文件远端/工作区/归档逐项校验一致，记录见 linux/、platform-identity.json、linux-vcs-results.json 和 results.json。616 文件冻结源包见 source-archive.json/source-manifest.json，生产代码及正式输入以清单为准；不包含本报告、汇总结果和 plan，避免结果文档相互引用影响源身份。

尚缺内联匿名 enum、成员范围展开、枚举方法和名称字符串、类型化端口/子程序参数/返回值、enum 类型参数声明、package/interface、struct/union、类型查询、automatic/动态数组、并发 SVA、class/随机化/UVM 和完整时序/事件区。本批未跑完整 CTest 集或 Linux sanitizer，没有新的速度测试；M22 的性能记录不当作 M24 新测。
