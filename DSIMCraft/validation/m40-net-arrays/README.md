# M40 静态 net 数组与 VCS 对齐

接通 RTL wire/tri 静态 unpacked 数组、多维/非零非负下界和宽 packed 元素，以及模块 input/output/inout 的整数组和常量前缀子数组连接。按每维声明顺序映射元素；两端为 net 时在生成代码前合并为同一信号槽，input 内部驱动可反向传播，inout 共享多驱动解析。没有引入双向赋值循环或每个端口额外的运行时电气适配过程；变量边界仍使用逐元素单向适配并执行两态转换。RTL/紧凑门级 parser 保持分离，runtime/parallel 和 parser 词法语法生成文件未改。

生产修改在 src/rtl_compiler.cpp：允许 net 数组信号声明；先建立数组端口元素映射，再与标量 net 一起规范化 ID，最后生成变量边界适配。IR 的 collapsed_net 数组元素两端 ID 相同，回归逐一断言。变量 inout/变量接 net inout、动态连续目标、过程写 net 及 net readmem 明确拒绝；避免直接改写 net 解析后的存储。parser 单测新增 net 数组端口及子数组三轮清理。原有两个“net 数组不支持”负例换为仍非法的变量接 inout/过程写 net，旧回归重跑。

五组共同源位于 tests/net_arrays。inout 覆盖多驱动冲突、撤销驱动、动态读取/越界及 buf 原语；matrix 覆盖三级层次、三维存储器的静态子数组、逐维相反方向、input 反向驱动、部分 X 与未连接字；types 覆盖 130 位、变量到 net 输入、net 输出到变量和两态输入转换；timing 覆盖惯性 net 延迟和 NBA 激励；parallel 为两个独立分区，每个输出时间线另按数学预期核验。五例×三后端×两模式×VCD/DWF 共60次捕获，types/timing 在1ns建立检查点并实际失败预测回放后核对完整 ordered 波形，共62次。19类拒绝诊断及真实两分区核验通过。

实际 VCS 为 10.131.254.103 的 W-2024.09，执行 source /apps/EDAs/syn.bash，使用 -full64 -sverilog -debug_access+all -top top -top dump，运行 simv -no_save。五组共同源字节相同，自检/TRACE一致，1691条 VCS 直接导出位时间线全部一致，无路径映射或位排除。全部1376个 native 数组位通过同源 packed 观察信号逐位逐时刻核验；1691已包含这些观察信号，不把1376再加作独立 VCS 导出位。observers.json覆盖每个层级的所有数组字，verify.py拒绝未列出的数组字。完整源码、原始日志/状态、VCD及命令/hash在 vcs 和 vcs-results.json。

四组原始探针核验 inout 多驱动/X/Z、input 反向驱动、悬空 net 输入/inout 为 Z，以及变量接 inout 双方拒绝。日志、退出状态、命令及源码 hash 在 probes/native 和 probes/vcs。部分位冲突 8'h11 与8'hff 的结果为8'bxxx1xxx1，十六进制显示大写 XX；延迟连续驱动在首次交付前为 X，与无驱动 net 的 Z 区别开。初轮测试预期已据双方实际输出修正，未以格式化显示替代位级核验。层次数组表达式仍缺，types 经普通标量输出核验转换，并明确保留该限制。

macOS ASan/UBSan parser 单测、五语料各三轮清理、五实际生成程序及完整 ordered 波形通过，包含真实双线程；leak检测关闭。证据在 sanitizers，入口 run-sanitizers.py。M39 六份完整实际生成程序重生成字节一致，见 m39-identity.json。最终源包869文件，所列源码冻结后不再修改；身份见 source-manifest.json/source-archive.json，包不含本批结果及 plan1017.md。source-changes.json 的 added 表示相对前次冻结清单新增条目。

本地八项定向 CTest 分两次执行：原有七项149.92秒、新增 net 数组一项50.45秒，均通过。这些是回归耗时，不是仿真速度对比。Linux 同源干净构建七项 CTest 220.39 秒全部通过，退出0；六份完整实际生成 C++ 跨平台字节一致，Linux 实际波形再次匹配同一原始 VCS，详见 results.json 和 linux-vcs-results.json。

复跑：ctest --test-dir build -R '^rtl_net_arrays$' --output-on-failure；python3 validation/m40-net-arrays/verify.py。run-vcs.py/run-probes.py接受输入与输出目录。功能范围见 [net 数组](../../docs/net-arrays.md)。变量 inout/ref、动态/关联数组和队列、动态连续目标、数组 slice/整体复制/赋值模式、负下界、enum/复合数组端口、数组形参和多维 readmem 仍缺。M35/M36/M38历史差异保留，package/interface/class、完整 SVA/UVM/事件区域等缺口未解决。未跑全量CTest、Linux sanitizers或新性能测量，不宣称全部SV/VCS功能或速度已对齐。

最终身份：869文件冻结源包SHA256 5a509b495e7db46b289bf9403301f7f9c0faa5fc41e0eb5661be00bf05e57e9a，所列源码与本地及Linux清单一致。ASan完整ordered事件另由 sanitizers/verify-ordered.py 核对（保留同一时刻的全部变化），结果 ordered-results.json；sanitizer生成程序hash与最终实际程序一致。
