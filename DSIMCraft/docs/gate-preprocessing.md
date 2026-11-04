# 独立门级预处理与时间精度

门级结构文件通过 `GateSource` 处理，再交给 `GateNetlistParser` / Network；不经过行为 RTL parser。RTL 与门级文件各有独立的宏/编译单元状态，命令行 `-D`、`-U`、`-I` 和 `--timescale` 同时作为各自的初始选项。

普通结构网表，以及只含模块外 `timescale`、`resetall`、`celldefine` / `endcelldefine` 的文件，使用一次词法扫描。它跳过注释、字符串和转义名称，保留模块的声明行和时间单位；不建立逐 token、逐行映射或 RTL AST。文本在原位去指令后，通过新增的 `parse_source(std::string, …)` 所有权接口交给结构 parser，不写临时文件、不再次读取网表。此路径没有公共宏预处理器的 256 MiB / 800 万 token 限制，仍受内存和结构 parser 自身限制；尚未以超过 256 MiB 的网表实测。

宏、include、条件编译或复杂时间指令转入已有词法预处理器，再交给相同的结构 parser。该分支保留公共预处理器的资源上限。`default_nettype` 等当前未支持的指令继续报错，不默默丢弃。include 依赖写入 `--emit-deps`，并参与同路径、符号链接和硬链接输出覆盖保护；结构语法诊断映射回原 include 文件及行号。

每个结构模块保留 `TimeScale`。实际展开的层级 scope 记录所属模块时间，门级顶层 stub 使用原模块时间，包含转义模块名。只有 DUT 被 RTL 顶层实际实例化时，其实际结构层级精度才参与全局 tick；源中未实例化的模块不降低精度。已有 SDF 模型精度仍参加实际门级实例的精度选择。`--sdf-bind-check` 接受门级预处理选项，但数值预览仍要求显式 `--sdf-tick`。

IR 的 `gate_design.gate_preprocessing` 与依赖报告列出快速路径标记、处理字节数、时间、依赖以及各模块原始位置与时间单位；`structural_precision_fs` 是实际门级层级的最细精度。`parse_seconds` 现在不含此前单独完成的预处理，比较前端成本应同时查看预处理、解析和绑定，不能只比较解析一项。

本地和 Linux 各 39 项通过。4 组新 VCS 测试各运行三次，native 对应三次完整 trace 一致，覆盖顶层精度、实际嵌套精度、未使用模块与宏/include。3 组宏/include/时间头与有限 IOPATH 联合测试经实际 ASan/UBSan 编译器和 6 个实际生成的普通/回放程序验证；有序/稳定波形和预测回滚通过。11 份完整 SDF 生成程序与已验收基线逐字一致。

完整真实网表保留为原始字节前缀，沿用既有 64 位结构封装及独立 RTL 激励：300,909 单元、335,872 网、111 模型。31,597,253 字节结构输入走快速路径，单次预处理约 0.252s，旧/新实际编译器生成的完整 C++ 相同。这是前端观察，不是配对性能筛选或新的 VCS 仿真比值。默认 runtime、模型求值、波形和并行 header 均未改。

13 份原始 VCS 互连输入现已通过合法网表头，全部到达明确的 INTERCONNECT 运行时拒绝，并保留已有输出。INTERCONNECT 数值合并、私有接收 pin 和运行时仍待实现，不能把本项称为互连仿真支持。源码、原始日志、独立检查、VCS/Linux 归档见 [验证记录](../validation/m4-gate-source/README.md)。
