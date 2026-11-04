# 固定门级敏感列表优化（已采用）

从已采用的固定反相版本开始，删除终生固定列表的重复 generation 写入和 gate 的 WaitSite/WaitRef 表。`set()` 唤醒谓词保持逐字不变，门级进程/输入/watch 顺序不变。模式防护拒绝通用 RTL 闭包、多个列表、动态/延时等待混用；普通 RTL 继续使用原逻辑。证明及适用边界见 [设计说明](../../docs/fixed-sensitivity.md)。已通过独立性能与正确性验收并采用，见 [decision.json](decision.json) / [analysis.json](analysis.json)。

## 冻结与复现

- 基线是固定反相已采用源包 `/tmp/dsim-unary-source.tar.gz`，SHA256 `8d67a3682a728bc4791e5c4ac9a5223b88be4086b18af44e933c8eac645aec71`，不是已经撤回的模型专用 handler。
- 候选源包 `/tmp/dsim-fixed-wait-source.tar.gz`，SHA256 `2ccc47523dd9e051a3aec2f3964a0822769d4471e9d941c2bf2965116f8fc1a0`；[清单](source-snapshot.json) 固定 155 个项目文件、全部 parser 和原型依赖。生产差异在 [candidate.patch](candidate.patch)。
- `freeze.py` 拒绝覆盖旧源包，只允许 runtime、gate emitter、CMake、parallel 测试及新增 fixed_wait 测试的变化。RTL 编译器、两个 parser、SDF/binder 和波形 codec 未修改。
- `run.sh` 在独立目录构建，完整 Linux CTest 完成后才串行准备和计时；`recheck.py` 将新 native 每用例三次输出与既有同输入 VCS 三次 trace 核对，明确没有重新编译/运行这 15 个 VCS 用例。它们的输入和库逐文件 SHA 相同，原始 VCS log 一并封存。

## 验收范围

新 fixed_wait 核心测试覆盖 0/1/X/Z 全部 16 个转换的 any/posedge/negedge/复合掩码、重复敏感项、禁止重新等待后保持禁用、空列表、非法模式切换、两个模型 context 与 net 别名、可复用检查点、预测失败回放及提交。Process/Watch 在 macOS/Linux 必须维持 24/16 字节。并行测试增加 fixed relay，与 generic 和 compiled dynamic 三种模式在 1/2/4 worker、多个 quantum 下使用同一独立 oracle。

本地采用核心 6 项加其余 18 项，另在扩充 parallel 用例后复验该项；不把两次调用说成一次完整 CTest。18 条完整有序流与固定反相基线逐事件比较。ASan/UBSan 覆盖编译器、4 个核心程序、4 对实际生成基线/回滚程序和 256-pattern 反相程序，共 14 个二进制；新增 TSan 为包含 fixed relay 的并行程序。各二进制/符号由 `sanitizer-provenance.json` 固定，不复用旧 binary 冒充新源码。

性能矩阵为完整原 barr_modmult（300,909 单元、111 模型、完整 Liberty、128 组原 RTL golden）、100k ff 非规则反馈，以及 20M 周期普通 RTL clock、1M 周期 fanout64、20M arithmetic。真实设计内部 256/257 位完整保留，TB 采用前批同一 64-bit limb 适配。每次预热/计时都核对全部 oracle，均无 SDF/波形。所有生成/编译结束后才计时；每工具固定同一允许逻辑 CPU、各预热一次，再旋转顺序三次。共享主机未独占或锁频，CPU 与墙钟分开报告，不推广为所有设计或 VCS 并行能力。

初次新增测试使用了不存在的 `connect_bit` 名称，构建拒绝后修正为现有 `connect_net`；初始编译日志已保留。局部有序流核对初次把归档内 settled/raw 等文件也计入固定的 18 条 ordered 数量，实际已读事件均一致；按 ordered.dwf/internal.dwf 筛选后 18 条一致。两项均属于验证器修正。

实际 SDF 延时/脉冲与回标、自动分区、压缩编码扩展仍按总计划推进，整体目标未完成。

## 同轮性能结果

所有工具固定 CPU 0；每工具一次预热后旋转顺序三次。下表为 CPU 中位数（秒），基线包含上一批固定反相；真实设计均为原始完整 Liberty 与网表、原 RTL 128 组 golden，无 SDF/波形。

| 负载 | 原版 | 固定敏感列表 | VCS |
|---|---:|---:|---:|
| 300,909 单元真实设计 | 18.90 | 14.57 | 9.10 |
| 100k ff 非规则反馈 /200 周期 | 7.72 | 6.73 | 6.50 |
| 普通 RTL clock /20M 周期 | 2.73 | 2.75 | 2.86 |
| 普通 RTL fanout64 /1M 周期 | 2.80 | 2.79 | 2.96 |
| 普通 RTL arithmetic /20M 次 | 0.38 | 0.39 | 0.45 |

真实设计 CPU 减少 **22.91%**，约为同轮 VCS 的 **1.60 倍**；RSS 中位数从 **108,320 降到 87,404 KiB（减少 19.31%）**，VCS 为 194,568 KiB。墙钟分别为 18.974/14.637/13.488s。运行时不再分配 gate 的 WaitSite/WaitRef 向量，与约 20MiB 的 RSS 减少相符；没有修改 parser 或全 Liberty 处理。反馈 CPU 减少 **12.82%**，RSS 89,124→79,836 KiB；墙钟 7.753/6.768/9.952s。普通 RTL 三个负载本轮基本持平，CPU 记录粒度为 0.01s，不将 0.38→0.39s 宣称为严格无开销。

共享主机有明显波动：真实原版 CPU 15.54/18.90/22.78s、候选 11.55/14.65/14.57s、VCS 8.62/9.10/10.88s；反馈原版 9.15/7.72/7.05s、候选 7.16/6.73/5.17s、VCS 6.50/7.13/4.86s。两组各迭代的候选均比对应原版快。fanout 候选有一次 3.66s，其他两次 2.71/2.79s，原样保留，不删除异常点。没有独占/锁频，不能与上一轮未绑核的 VCS 7.12s 混算收益，也不将合成网络近似持平推广为真实设计/VCS 全功能同等。

真实候选生成/编译墙钟分别 **27.216/16.776s**，峰值 RSS 1,974,572/1,638,668 KiB；这些与运行阶段分开，原版未同轮重测对应生成/编译成本，不能据此声称解析/编译提速。

## 验收结论与原始证据

本地核心 6/6 +其余 18/18（3.24/266.27s），扩充后的并行 1/1 复验；Linux 完整 **24/24（490.37s）**。15 组新 native 各三次与已封存的同输入 VCS 三次 trace 核对，保留原始日志，不称为新 VCS 门级重跑。性能矩阵中的 VCS 则均在本轮预热加三次运行；普通 RTL 三个 VCS 程序本轮新编译，真实/反馈复用 SHA 固定的原程序。全部预热及计时都重新核对各自完整 oracle。

18 条完整 ordered 流、4 对实际生成模型的回滚/波形、256-pattern 四态、ASan/UBSan **14 个实际二进制**及含 fixed relay 的 **1 个 TSan 程序**通过。`set()`/普通 `arm_wait()` 的源码逐字不变；实际生成的门级模型函数逐字不变，install 部分只有三个 API 名称替换；普通 RTL main 逐字不变。全部源码、parser、原型依赖与 frozen 清单一致。

[原始证据包](evidence-archive.json) `/tmp/dsim-fixed-wait-evidence.tar.gz`：**1,339 个文件、21,891,680 字节**，SHA256 `ac05641024caa53a3072a9c007babc7691059b9298bd6364b958631b380abc6b`。`remote-verified/` 含 CPU/墙钟/RSS 原始计时、全部输出、源和生成 C++、IR、参照 VCS 原始 trace、输入/golden/模型及 manifest。完整 1.2GB Liberty 保留原路径和前后 SHA，没有复制进包。

`python3 validation/m5-fixed-wait/analyze.py` 独立重算原始结果、模式边界、所有 oracle 和 sanitizer 符号/二进制 SHA。后续源树变更后，可先解本批源包到独立目录，再把该目录作为脚本可选参数；本地 waveform/sanitizer 专用路径仍取本工作区。默认 build 已按采用源码重建。

下一批功能重点为可回滚延时驱动事件及 native SDF 实际回标，继续满足固定输入列表约束；性能后续检查值传递/驱动路径与完整 Liberty 的功能建模成本，自动分区和压缩扩展继续保留独立验收。
