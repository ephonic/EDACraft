# 自动分区 API 与统一工具流程

本批把手工保守并行推进到图规划和实际内核安装，并给编译器、统一流程和源码分发提供入口。RTL 和结构 gate parser 保持独立。

- `PartitionGraph` 合并零延迟域，用确定性的最大负载优先分配返回节点归属、负载、切边和 lookahead。十万节点测试通过。
- `AutoConservativeSim` 自动安装各分区 Sim，连接零延迟 net alias 和正延迟通道。实际四态输出时间线按独立固定预期验证，覆盖 1/2/4 worker 和五种窗口。
- `--gate-partition-report N` 在功能 gate IR 上分析 net/单元图，报告单元分区映射。接收引脚所有转换均为正的 INTERCONNECT 才允许切边；IOPATH 不切，常量可复制。普通生成程序仍串行，报告明确 `scope: gate-only, execution: serial`。
- 清单的 `partition_report` 接入 `scripts/run_flow.py`，编译、三种波形模式、完整 native VCD/DWF 流核对和可选 VCS 差分在同一流程执行。`scripts/package_source.py` 分发完整工具依赖和逐文件 SHA256 清单。

原始 300,909 单元网表及 1.2GB Liberty 的哈希与此前严格 SDF 入口一致；本批只做零延迟功能网表分区分析。请求四分区得到一个有工作量的域，没有正延迟切边。此结果不代表完整 SDF 只能一个分区，也不是仿真加速实验；它说明该零延迟基准还需组合锥静态编译、批量调度和等价变换。没有新的 VCS 性能比例。

macOS 完整 51/51 通过；实际 ASan/UBSan、TSan 程序执行通过。本地 RTL/gate/SDF 统一流程通过；Linux 同三例新编译 VCS 差分通过，SDF 首次注解零错误、零警告，完整 native VCD/DWF 流一致。分区分析随编译执行，未把报告视作多线程程序。

Linux 初次分发遇到两个打包问题：macOS tar 资源元数据被 CMake glob 当作 C++ 源码；随后包漏带独立波形解码器，使 13 个相关测试无法启动。现在用完整打包脚本排除元数据并包含工具依赖；编译核心不变，已通过的 38 项保留，13 项按原测试入口重跑全部通过，累计覆盖 51 项。`verify.py` 已从完整原始测试行集合和采用源码哈希核对通过，不把空结果当作成功。首次失败记录保留。

Linux ASan 的系统共享库目标缺失，静态库也不可用，两个链接失败没有运行 sanitizer 程序；见 `linux-sanitizer.json`。本批 sanitizer 通过的结论限实际 macOS 程序，Linux 使用正常 CTest 内核。

`complete-source.json` 是最终编译器、测试、脚本和独立解码器的采用源码清单；源码包 `/tmp/dsim-auto-partition-complete-source.tar.gz` 自带相同逐文件清单。`source*.json` 和 `tools-source.json` 保留首次分发及修正记录。`flow-runner.json` 指向本地实际结果，`linux-flow-results.json` 保存新 VCS 结果，`real-analysis.json` 保存真实输入哈希和分区结果。

普通 Verilog 的自动分区代码生成、testbench 边界、全局 finish、跨内核波形汇合和自动预测器仍未完成。下一实现按两个执行入口推进：零延迟基准的静态组合锥/批量调度，以及 SDF 正延迟分区与真实模型生成；避免继续调分区算法企图切开零延迟依赖。

验证入口：`python3 validation/m5-auto-partition/verify.py`。
