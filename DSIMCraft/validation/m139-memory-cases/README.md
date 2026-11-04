# M139：新增 cases 修复验收

M139 已修复 cases 下两组新问题：标量 `[0]`/零边界宽度一选择被误报，以及大型展开式一次性 TB 的生成 C++ 编译超时。原始输入和 180 秒预算保持不变；SRAM 全部 4480 阶段、memory 全部 3840 阶段通过，同源 VCS 重新运行通过。Mac 编译分别 56.896/60.101 秒，103 Intel 分别 160.761/168.430 秒。双端各三组发布回归及 parser/格式/原生 DB 检查通过，每端 26 捕获、18 次预算恢复、22 次检查点恢复、预测提交/回滚各一次及 5 个拒绝例通过。稳定入口已更新。六个旧模型生成 C++ 和八个 runtime 头文件保持一致；103 原生编译选项由 `-O3 -xHost -ipo` 改为 `-O2 -xHost`，保留 strict FP，未重新测运行速度，生成代码一致不代表相同原生性能。实现范围见[专题](../../docs/memory-case-fixes.md)。

## 冻结与发布

实现提交 `a9ae10d9041c78bb42292c7e3b72a5c15a51cc25`；源码包 1775 个成员逐项与 Git blob 一致，SHA256 `ed33092da45801655c7b5a40440b051c205aad5ed4798d9480c10eaadb8f512d`。原始归档只读，11 个输入 SHA 固定到 `tests/memory_cases/origins.json`，未执行归档 Python。

| 平台 | 不可变 release | binary SHA256 |
| --- | --- | --- |
| Mac | `/Users/yangfan/vibe-coding/dsim-test/releases/20261028T063355781536Z-0acf383a3694` | `144beb0752ade17af3d18439183211c818cd3d8d23ab1119135f55d0d3dc3953` |
| 103 Intel | `/apps/EDAs/own/dsim/releases/20261028T064659Z-a9ae10d` | `4031d99345c9cab94a2619c05c7cddef409f853513afd20af76523a1fb9f2c33` |

Mac `~/vibe-coding/dsim-test/bin/dsim`、103 `/apps/EDAs/own/dsim/bin/dsim` 及 `/apps/EDAs/own/dsim/dsim` 已切换。入口实际编译标量测试的 C++ SHA 均为 `7d84854b38124495c17edf4291e9a08166a06b8b9005d5c8e0a5afec73287b32`，输出和完整有序波形与各自发布回归相同。Mac 发布输入 SHA 清单、两端源码包身份、实际二进制及 runtime 头 SHA 均在激活前核验。

## 原始用例与边界

| 用例 | Mac 完整编译秒 | 103 完整编译秒 | 独立预期 |
| --- | ---: | ---: | --- |
| SRAM | 56.896 | 160.761 | 4480 阶段、76160 端口比较、4480 macro_q 比较 |
| 展开 memory | 60.101 | 168.430 | 3840 阶段、38400 端口比较 |

三种执行配置包括 serial、time wheel 和 threads=2，后者对大有限过程为真实两个分区。完整分步有序波形对照为 DSIM 三配置及预算/预测运行间对照；直接 checkpoint 不携带活动波形输出，独立检查最终值及精确步骤。每端 26 份捕获、18 次预算恢复、22 次 checkpoint 恢复、1 次预测提交/1 次回滚、5 个拒绝例，循环/always 继续原生成路径。实际生成程序的三次 sanitizer 执行为 scalar、large checkpoint、large prediction rollback，ASan/UBSan 通过，leak detection 关闭。

VCS W-2024.09_Full64 重新运行同一 SRAM、memory、scalar 源码：两个完整独立自检输出与 scalar 全部 TRACE 对齐。本批没有宣称与 VCS 完整波形对齐。VCS 生成代码和二进制仅在私有临时目录，不入 Git 或导出；持久证据只有自有输入/生成程序、运行输出及派生报告。动态或非零标量选择仍明确拒绝，VCS 对其语义与向量越界不同，范围见专题。

## 编译策略与失败记录

仅对至少 16384 指令、无回跳且满足控制流限制的一次性 initial 按 256 指令分块，并在 Clang/Intel Clang 限制该回调的词法优化。反复运行的 RTL 与普通循环保持原路径，可用 `--cxx-flag -DDSIM_OPTIMIZE_LARGE_INITIAL` 恢复优化。这是通用编译资源控制，会影响巨大一次性 TB 的执行成本，不是 runtime 加速。

开发版原 M138、仅分块、仅优化限制以及只给外层 lambda optnone 的候选均超 180 秒；组合候选通过，完整结果保留在 development JSON/归档。首次 Linux `-O3 -xHost -ipo` 候选 SRAM 超时，未激活；`linux-ipo-failed-stage.json` 保留失败。随后同一冻结源码改用 Intel `-O2 -xHost`、strict FP、无 IPO，完整重跑通过。`intel-o2-pilot.json` 只是筛选结果，正式通过取自 linux-memory_cases。不能把联合选项变化归因于 IPO 单因素，也不能从此推断 GCC 编译预算或 runtime 性能。

## 证据位置与重放

两端 `evidence/m139-memory-cases/` 含源码包、自有 C++/输入/日志/波形、生成代码保持检查、sanitizer、实际稳定入口和失败/筛选记录；文件哈希见 `evidence-index.json`，归档与完整 validation 报告镜像到 Mac test 前缀和 103 own/dsim 前缀。归档不含可执行文件或 vendor 生成物。

`tests/memory_cases/regression.py DSIM OUTPUT CMakeCache.txt` 重放完整新组。`publish-linux.py` 在同一冻结源码包上使用 Intel 构建并执行三组回归；`compare-vcs.py` 对照同源 VCS 报告；`generation.py` 检查六个旧模型 CPP 和八个 runtime 头；`activate.py` 检查全部身份后切换；`check-entry.py` 测真实入口。Mac publisher API 选组 memory_cases/memory/ascending_packed，CLI 原有 ascending_packed choice 缺失通过 API 调用解决，未修改原生产接口。
