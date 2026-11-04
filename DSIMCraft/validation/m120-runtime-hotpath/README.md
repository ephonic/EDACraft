# M120：延后诊断清理移出信号通知热路径

实现冻结 `d779a7146ed3e028cbb851958db4aba0252e7c9f`，基线为 M119。默认采用非空报告清理的冷函数；没有修改 RTL、输入、仿真工作量和事件预算。

## 完整运行时间

103 服务器，GCC 11.5，`-std=c++17 -O2 -pthread`，固定 CPU 0。四个程序的默认和参考版本先全部编译，再每个程序预热一次，三轮换序运行；VCS 同机同核作为对照。表中为完整仿真的用户加系统 CPU 秒中位数。

| 原始负载 | M119 参考 | M120 | CPU 时间下降 | 同批 VCS | M120/VCS CPU 时间 |
|---|---:|---:|---:|---:|---:|
| CPU | 12.17 | 12.02 | 1.2% | 5.80 | 2.07 |
| CRC | 4.29 | 4.29 | 持平 | 3.96 | 1.08 |
| muldiv | 9.46 | 8.87 | 6.2% | 6.89 | 1.29 |
| AXI4 短控制 | 0.23 | 0.22 | 不作吞吐结论 | 0.58 | 不作吞吐比较 |

CPU 的三轮候选为 12.02/12.03/12.01，参考为 12.17/12.16/12.48 秒；muldiv 候选 8.83/8.88/8.87，参考 9.45/9.46/9.50 秒。共享服务器存在波动，保留全部样本，包括 CPU 的一次 VCS 8.23 秒。CRC 没有启用选择诊断，默认和参考的机器码逐字节相同。AXI4 墙钟中位数均为 0.23 秒。

[measurement.json](measurement.json) 包含 CPU、墙钟、预热及所有正式样本。48 组完整输出/时间日志、12 个执行文件身份和四份参考 `.text` 均独立复核，见 [measurement-audit.json](measurement-audit.json)。参考机器码逐字节等于冻结 M119；VCS 比较核对完整 PERF 行，dsim 输出逐字节核对原始完整基准。CPU 比例不能解释成墙钟比例，前缀指令数不能解释成完整耗时比例。

## 热点和实现

原 `flush_selection_reports` 内联了 vector 中字符串的移动、释放和压缩。即使报告队列为空，这些冷代码仍影响热通知函数的寄存器分配和布局。现在保留原地空队列检查，仅对非空队列调用 `noinline,cold` 的清理函数；删除谓词、报告归属、保留顺序和成熟时刻保持原样。`DSIM_REFERENCE_SELECTION_FLUSH=1` 恢复参考实现。

实测程序的 `set_planes` 从 934 字节缩为 445 字节，清理函数独立为 660 字节，见 [code-size.json](code-size.json)。这没有宣称整个程序代码体积变小。

固定 200000000 tick 前缀、执行步数和全信号状态哈希完全相同，Callgrind 指令数如下，见 [profile.json](profile.json)：

| 原始负载 | 参考指令数 | 默认指令数 | 减少 |
|---|---:|---:|---:|
| CPU | 365955153 | 357422352 | 2.33% |
| CRC | 80181921 | 80181921 | 0 |
| muldiv | 81792119 | 80072568 | 2.10% |

本次改善通知路径代码布局和开销，没有减少进程执行或调度事件。组合区域融合和结构性事件消减仍未完成，不能把这项收益当作已解决与 VCS 的主要差距。

## 功能验证和发布

- 新增默认/参考精确差分：16 份完整 ordered/settled 波形，比较跨信号事件顺序及全部 stdout；408 组预算边界完整信号状态一致。
- 新内核默认/参考共 60 项检查：跨过程报告顺序、短字符串/堆字符串、队列中段删除、预算中断后的待报告快照、重复恢复和预测接受/拒绝。另四项 runtime/驱动/编译过程/固定等待内核通过。见 [regression.json](regression.json)、[kernels.json](kernels.json)。
- 两个内核变体和真实 events 生成程序 ASan+UBSan 通过，见 [sanitizers.json](sanitizers.json)。
- 两端稳定发布检查 selection_flush、selection_checks，另包含 RTL/格式 parser 和原生 DB 检查；Linux 另运行七项内核。既有 selection_checks 覆盖六模型、串行/时间轮/实际双分区、74 份波形、两次回滚及八项拒绝检查。具体结果以 release JSON 和原始归档内 results.json 为准。

1689 个源码包成员逐个与冻结 Git 树及清单一致；SHA-256 `ddc9d3f419367e9f387948243c0ac18d1aa8ed4614fb022584bf3abc76bf65e2`，见 [source-proof.json](source-proof.json)。未包含用户实验目录。

`measure.py` 从指定目录读取四份冻结版本生成的完整 CPP，使用参考宏并核对 M119 `.text`；默认目录 `/tmp/dsim-m120-full`。`audit.py` 独立核对原始记录；`profile.py` 对这些源生成固定时间前缀。脚本依赖冻结 M119/VCS 对照和原始输入目录，所有测量相关自有源和日志另存原始归档。

发布和安装验收身份见 release/installed JSON。稳定目录的 `evidence/m120-runtime-hotpath/` 保存源码包及两端带逐成员 SHA-256 清单的原始归档，排除执行文件和 VCS 私有生成代码。

发布已完成：

- 本地稳定版本 `20261027T011209688351Z-d79eff25c1bc`，入口 `~/vibe-coding/dsim-test/bin/dsim`。
- 103 稳定版本 `20261027T011246Z-d779a71`，两个入口 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 指向同一二进制，SHA-256 `25986521d1a042e624b3721b77ebb1138608f0081ddf19db1e8c6e88bbd90610`。
- 两端安装入口各自重新生成四个原始模型，CPP 逐字节等于实测源码，完整运行输出相同，八份 runtime 头文件与冻结实现一致。见 [installed-mac.json](installed-mac.json)、[installed-linux.json](installed-linux.json)。
- 两端均已保存并核对三个归档。Mac 原始归档逐成员验真 3850 个文件，Linux 2280 个，见 raw/mirror JSON。记录后的测试源码仅整理了一处循环缩进，运行时实现和归档仍对应上述冻结提交。
