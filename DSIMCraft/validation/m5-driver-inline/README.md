# 0.12.0 性能优化与 SDF 绑定验收

本轮响应“优先优化仿真效率，同时补全功能”：将单驱动值直接放在 net 内，第二个及后续驱动按需建立独立存储并在检查点中深复制；编译 Liberty 时证明输出不依赖输入后，消除状态未变时的重复输出求值。首次初始化、输入相关输出、三态依赖、时钟采样和 NBA 提交位置保留。证明与适用范围见 [优化说明](../../docs/simulation-optimization.md)。RTL 与大规模结构网表仍使用两个独立 parser。

## 同轮性能

主机 `10.131.254.103`（mn02），GCC 11.5、VCS W-2024.09，native `-std=c++17 -O2`、VCS 默认优化。非规则 XOR/DFF 反馈、200 周期、`2N+1` 个门级实例；每工具预热一次，再轮换顺序各测三次，自己的计时任务串行。原版/单项/组合使用相同输入、库和独立递推预期，复用的旧二进制在运行前后检查 SHA256。共享主机未固定亲和性和频率。

10 万触发器同轮中位数：

| 版本 | CPU 秒 | 墙钟秒 | 峰值 RSS KiB |
| --- | ---: | ---: | ---: |
| 0.11.0 原版 | 13.32 | 13.376 | 140232 |
| 仅单驱动内联 | 10.46 | 10.494 | 113948 |
| 仅消除重复输出 | 11.23 | 11.274 | 139824 |
| 0.12.0 组合优化 | **9.66** | **9.691** | **113500** |
| VCS | **5.28** | **7.998** | **161156** |

组合优化 CPU 减少 **27.48%**，RSS 减少 **19.06%**。CPU 差距由同轮 2.52 倍缩至 **1.83 倍**，仍需继续优化。墙钟受 VCS 启动/许可及共享主机影响，单独列出。1 万档 CPU 依次为 0.64/0.57/0.47/0.41/0.89 秒，启动成本较高，不能据此声称普遍快于 VCS。

第一阶段只有单驱动候选，10 万档 11.47→9.73 秒，同轮 VCS 4.91 秒；保留为独立实验。不要将该批 11.47 秒与最终批 9.66 秒相减。原始 Callgrind 的约 47% drive 相关指令、约 13% set 指令是采样对象的指令归因，不是实际 CPU 时间百分比。

Callgrind 总指令为原版 5,224,238,018、组合版 2,565,506,331；两次均输出正确 checksum 并退出 0，同时报告 `brk segment overflow` 分配回退。该工具结果仅用于定位候选；性能表来自未插桩的正常执行，不使用 Valgrind 时间或 RSS。

大基准仅用最多 64 个采样节点与 checksum 检查独立递推结果；全事件等价由额外的小型四态/反馈/门级回归验证。以上是理想零延迟库的特定负载，不代表真实 30 万 cell 设计或 SDF 仿真速度。

## 原生波形开销

同一批 1 万触发器、200 周期，包含 20,073 个信号与 1,921,765 条值变化：

| 模式 | CPU 中位数秒 | 墙钟中位数秒 | 波形字节 |
| --- | ---: | ---: | ---: |
| 未编入捕获 | 0.41 | 0.423 | — |
| 编入但关闭 | 0.43 | 0.445 | — |
| 全网 VCD | 0.64 | 0.663 | 9317158 |
| 全网 DWF/Zstd | 0.66 | 0.678 | 5646864 |
| native 顶层 VCD | 0.47 | 0.486 | 39356 |
| VCS 关闭捕获 | 0.90 | 5.631 | — |
| VCS 顶层 VCD | 0.91 | 5.605 | 45872 |

相同全网范围 DWF 压缩约 **1.65 倍**，CPU 比全网 VCD 高约 3%；相比同一带捕获程序关闭时，DWF CPU 高约 53%。VCS 仅捕获顶层，不能用其文件大小与 native 全网相比。文件系统为普通缓冲写入，未 fsync，不是持久化带宽测量。

原始计时运行全部完成后，旧比较器拒绝 VCS 将 `y[63:0]` 拆成同名 indexed scalar 的合法声明，导致流水线退出。保留 [原始失败](wave-cost-failure.log) 和远端 `build/wave-cost/results.json`。修复仅涉及验证器与 CMake 新测试，所有 `src/`、`include/` 字节与计时版本一致。新 `bit_timeline` 保留各位范围及四态值，拒绝重叠声明，覆盖升序范围和同 tick 最终值；三轮完整 native VCD/DWF 及顶层 VCS 位流均从原始文件重新核验，另写 `wave-cost-accepted.json`，不重写失败报告或重新计时。

## 源码与复核

- 计时实现冻结包 `/tmp/dsim-optimization-before-wave-reader-source.tar.gz`，SHA256 `b07176cf68463385d82fdca29845c040346938f1089aed6c2bf9647dd5d6251e`；对应 [原快照](source-snapshot-before-wave-reader.json)。
- 修正验证器后的包 `/tmp/dsim-optimization-source.tar.gz`，SHA256 `f3a889d8f29357e25c1644d9c1167ef9bd765cce3c99fe3f9d06093143891e56`；[最终快照](source-snapshot.json) 包含 152 个实现/测试/脚本文件、3 个不变原型依赖和 8 个驱动。两个包的全部 `src/`、`include/` 哈希相同。
- 本地完整 CTest 20/20；随后验证器测试与 writer 测试 2/2。ASan/UBSan 核心 9/9、18 个实际生成波形模型、4 个实际生成模型的正常/失败预测重放通过，34 个二进制的哈希和 sanitizer 符号见 [sanitizer 清单](sanitizer-provenance.json)。并行 API 经 ThreadSanitizer。
- 远端最后一轮运行目录记录在 [final-path.txt](final-path.txt)。Linux CTest **21/21**，433.62s；15 组门级、7 组时间与 3 组波形在 native/VCS 各跑三次通过，另复核既有 27 RTL/15 gate 参考。18 条完整有序波形与优化前逐事件相同，真实两份 SDF 绑定通过，最终流水线退出 0。确切状态见 `post-verification.log` 和 [分析结果](analysis.json)。原始证据目录为 `remote-verified/`，归档摘要在 [evidence-archive.json](evidence-archive.json)。

复核命令：`python3 validation/m5-driver-inline/analyze.py`。测量脚本 [measure-final.py](measure-final.py)，保留波形复核 [verify-wave-cost.py](verify-wave-cost.py)，收尾驱动 [resume-final.sh](resume-final.sh)，证据收集 [collect.py](collect.py)。源包保存计时/验证精确版本；文档可在归档后补充实测结论。

证据包 `/tmp/dsim-optimization-evidence.tar.gz` 含 **1989** 个文件，61,231,398 字节，SHA256 `0e8da8fee8a23799c6464bcc95f2bedeb83707f1d936b95e7f58731d1f0bed85`。本地逐文件重算 manifest，并从原始 `.time`、trace、VCD/DWF 重算中位数与等价性，不只采信汇总中的 PASS。

功能补全包含 SDF 实例/pin/有向互连严格绑定与 corner 数值预览。完整 Liberty 和真实 SDF 的输入 SHA、独立统计与解析后绑定报告单独保存；尚无实际延迟回标、COND 求值或 timing checks。下一轮按 profile 推进 [alias 缓存、不可观察输出和共享 handler](../../docs/optimization-next.md)，同时继续可回滚延时事件与受限 IOPATH/INTERCONNECT。
