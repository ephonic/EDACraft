# M36：枚举数值遍历及 VCS 对照

已实现 first/last/next/prev/num 的表达式路径，包括省略无参括号、声明顺序、回绕、原枚举类型身份/宽度/符号、无效当前值默认结果、显式 X/Z 成员、32 位无符号步数截断以及别名/参数/generate 克隆。first/last 的复杂接收者及 next/prev 的接收者/步数各求值一次，普通变量的类型查询可折叠，num 不执行接收者。未知步数采用本次实测 VCS 的低 32 位 aval（X 作 1、Z 作 0），不是泛化的未知整数规则。范围见 docs/enum-methods.md。

有序成员表只存编译期；常量折叠，常见不超过 32 位的枚举生成四态键 switch，宽值生成精确比较和结果分派，步数取模而非逐步循环。RTL 与门级 parser 保持分离，runtime/parallel 头文件未改。上一轮 M35 的七份完整生成 C++ 字节保持一致，哈希在 m35-identity.json；不把本次功能实现描述为已测得的性能提升。

六组模型 traversal/edges/constants/effects/types/parallel，共 72 次后端/格式/模式捕获和 2 次 1ns 挂起期间失败预测回放，合计 74 次；14 类非法/未支持表达式明确拒绝。涵盖四态/两态、130 位有符号值、动态多维数组和 packed 成员、函数/task、delay/NBA、真实两个独立分区。初轮九项定向 CTest 通过（154.04秒）；完成接收者求值修正后，最终新功能和 parser 两项再次通过（51.91秒）。日志在 local/，最终统计以 results.json 为准。

实际使用 10.131.254.103、source /apps/EDAs/syn.bash、VCS W-2024.09。六组共同输入的 TRACE/自检和全部 933 条导出位时间线一致；其中 VCS 把两个 generate 变量写成转义的展平名称，通过 tests/enum_methods/vcs-aliases.json 两项显式路径规范化七个位，检查无碰撞及完整集合。VCS 未导出的全部四个数组字（12 位）通过同源 packed image 逐位核验。原始 VCD、共同输入、dump wrapper、命令和退出状态在 vcs/；没有将未核验位计入匹配数。

**仍有四类原始探针差异，不宣称全面枚举/VCS 对齐。** probes/ 保存原始源、双方命令/编译及执行状态、输出及 JSON。六个探针配置中：

- expressions 无 debug 标志时，VCS 省略静态函数接收者的调用（0 次），native 的 first/last 各执行一次（2 次）。expressions-debug 加共同对照使用的 -debug_access+all 后双方均为 2 次，num 均不执行接收者。保留编译标志变化，避免把单一形式推广为通用规则。
- untyped-parameter 中，VCS 不保留方法返回值初始化的无类型 parameter 的枚举身份，后续 P.prev() 报 FNLD；native 保留并支持。共同模型显式声明枚举类型参数。
- constant-width 中，VCS 对参数化实例的 $bits(FIRST.next()) 两次均返回首例宽度 4，native 为 4/9。共同模型使用 $bits(E)，变量接收者的方法宽度由 130 位模型另行检查。原始宽度差异继续单列。
- runtime-label 把同样的枚举标签方法查询放在运行时 $display 中，VCS 报 XMRE，native 支持。没有删除原始探针中的查询来制造一致。

最初步数预期将 32'bx1 误当作只有一位 X，实际按首位 X 扩展全部高位；双方均触发该错误预期。共同测试改用显式零前缀 32'b0x1，原始 edges 探针及初次失败日志保留。这是测试预期修正，不计为仿真器功能修复。

macOS ASan/UBSan parser 单测、六组语料各三轮清理、六个实际生成程序（含真实双线程）及完整 ordered 波形通过，关闭 leak 检测，证据在 sanitizers/。runtime-results.json 中每份完整 C++ 哈希与最终实际程序再次核对。六个原始探针配置另以普通构建执行，不计入 sanitizer 程序数量。

Linux 从 793 文件源包开始干净构建/测试。离线波形对照识别出上述 VCD 名称表示后，仅更新 verifier/说明及新增路径映射，形成最终 794 文件清单；编译器、runtime、parser、CMake、CTest 脚本和全部 SV 语料字节未变。两个源包哈希、精确三个元数据变化及清单在 source-transition.json 和 initial-source-*/source-* 文件，平台最终校验及结果见 results.json。这里不声称两版压缩包字节相同。 Linux 六项定向 CTest 最终 184.66 秒通过、退出 0；最终 794 文件逐项哈希与源包 SHA-256 核验通过，七份完整实际生成 C++ 跨平台字节相同，Linux 波形再次通过 933 导出位及 12 数组观察位核验。平台日志、身份及波形见 linux/、platform-identity.json、linux-vcs-results.json。

仍缺 name()/字符串、匿名/范围展开枚举、方法结果 packed 选择和完整方法调用语法，以及动态数组、数组端口/ref/递归/常量函数、package/interface/class、完整 SVA/UVM/事件区域等既有功能。本批未运行全量 CTest、Linux sanitizers 或新速度测量，M35 的告警/IUC 差异保持未解决。
