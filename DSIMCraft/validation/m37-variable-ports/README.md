# M37 模块输出连接变量与 VCS 对齐

本批接通子模块 output 到父级变量，覆盖 logic/reg/bit/整数、宽 signed/两态转换、静态选择/数组字/packed 成员、多层模块和混合拼接。重复目标出现在同一输出拼接时，按右侧项覆盖；两个端口的重叠驱动以及过程写/声明初始化冲突会明确拒绝，静态不相交位可分别写入。函数副作用携带静态写范围。没有把变量转换为可多驱动解析的 net，也没有新增运行时 AST；RTL 与紧凑门级 parser 继续分开。

修改还修复 RTL parser 将“已取完下标的静态数组元素”误当作数组端口的不匹配判断，并避免将 packed 成员选择的 receiver 错误强转为 primary。parser 单测增加数组字/成员选择连接的三轮清理。runtime/parallel 头文件及词法/语法生成文件未变；M36 七份完整 C++ 重生成字节一致，见 `m36-identity.json`。

验证输入为 `tests/variable_ports/` 的 basic、parts、hierarchy、types、timing、parallel，独立 TRACE 预期在 `expected.json`，SV 内也有自检；parallel 使用两个独立域和错误标志，不以打印把分区合并。六例 × serial/time-wheel/threads=2 × ordered/settled × VCD/DWF 共72次捕获；types/timing 另外在1ns建立检查点并执行实际失败预测回放，再完整比较 ordered 波形，共74次RTL捕获、两次回放。17类拒绝覆盖重叠端口、声明初始化、blocking/NBA/复合写、动态最长静态前缀、函数副作用、task写回、数组字冲突及未接通的动态输出/变量inout/数组端口/显式变量assign。实际分区统计为2。

另将既有 four_state 和 seq_pipeline 网表测试台中的父级输出改为变量，以原有独立预期核验 Liberty 组合/三态及触发器门级模拟；新增两次 settled DWF 捕获。测试脚本的文件名为 native.vcd，但未指定 --wave-format，实际内容为默认 DWF；验收复制为 native.dwf 并核对原始字节未变后读取，不进行波形转换。最初按扩展名误读的验收脚本失败日志在 local/initial-hybrid-wave-reader.log。这两例走独立紧凑门级 parser，未计入六组RTL的VCS逐位数或74次捕获。

远端实际 VCS 为 10.131.254.103 的 W-2024.09，环境 `source /apps/EDAs/syn.bash`。共同源使用 `-full64 -sverilog -debug_access+all -top top -top dump`，运行 `simv -no_save`。六例共同源字节相同，TRACE/自检相同，**全部1623条直接导出物理位时间线一致**，不做名称映射或位排除。VCS未导出的全部4个数组字、16位，经同源packed观察信号逐时刻逐位核验，单列且不算直接导出位。完整覆盖关系在 `tests/variable_ports/observers.json`，离线核验见 `verify.py` / `vcs-results.json`。

原始探针在 `probes/*.sv`，双方命令、源码hash、原始退出状态和日志在 `probes/native` 与 `probes/vcs`。repeated 双方接受，输出6/b；overlap、initialization、procedural 双方编译拒绝，VCS分别为ICSD/ICPSD，native为编译期端口驱动冲突诊断。不要求两工具的错误文案或数值退出码相同，不把拒绝算作仿真结果一致。

本地最终新增功能、automatic、function-effects 三项70.33秒通过；two-state和always_sv两项69.68秒通过。初轮既有 integral-types、packed-aggregates、gate、parser及compiled-regression也通过；初轮不是全部最终源码的统一重跑。初次失败与重跑日志均在 `local/`：新增模型曾使用 parser 尚不接受的无参旧式 function 头，改成 `()`；two_state 旧负例仍期待非递归 automatic 函数被拒绝，与M31已实现功能冲突，替换为仍不支持的递归边界；负例实际诊断为既有 semantic analysis failed。最初 packed mixed bit 成员的整体四态存储预期写错，双方原始输出均为xz01xz01；修正自检为整体保留四态、bit成员读取转两态，原始VCS失败日志保留在 `local/initial-vcs-smoke.log`，不把预期修正说成模拟器语义修复。

macOS ASan/UBSan parser单测、六语料各三轮清理、六个实际生成程序及完整ordered波形通过；parallel使用实际双线程，leak检测关闭。日志、程序源码及hash在 `sanitizers/`，`run-sanitizers.py`可复跑。

最终源包清单、hash和两端验证见 `source-manifest.json`、`source-archive.json`、`final-identity.json`、`platform-identity.json`；Linux干净构建/CTest和真实波形在 `linux/`，与VCS再次比对见 `linux-vcs-results.json`。Linux最终812文件源包干净构建及六项CTest225.64秒通过，退出0；七份完整实际C++跨平台字节一致，Linux实际1623直接位和16数组观察位再次匹配VCS，两组门级完整波形与本地一致。最终源包SHA256为 `1e0d677b09933eaa2ebaed49b25a5a4d61f8d46240d75f2273c3499083931c9d`，未在Linux构建后修改冻结文件。汇总见 `results.json`，本批已完成所列范围验收。

范围边界见 [模块变量端口](../../docs/variable-ports.md)。仍缺一般显式连续赋值到变量、动态输出选择、变量inout、数组端口/ref及完整端口类型体系；根/断开输入的历史差异不在本批宣称解决。动态过程写的冲突分析沿用现有编译器的保守写范围，在某些复杂packed选择/函数表达式中可能拒绝合法但尚未证明不相交的组合。M35告警/IUC、M36枚举探针差异继续保留；未跑全量CTest、Linux sanitizers或新性能测量，不宣称全部SV/VCS功能已齐全。
