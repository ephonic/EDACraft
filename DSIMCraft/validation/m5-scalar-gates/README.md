# 门级标量四态求值

状态：**第一版未采用**。正确性通过，但真实收益未复现，反馈负载两轮均略慢。后续在 `../m5-scalar-logic/` 继续优化，保留本版全部源和数据。总体 VCS 功能/性能目标继续进行。

Liberty 标量 function/three_state、ff/latch 的控制及 next_state 使用 0/1/X/Z 字节中间值，输出转换回 V 后走原驱动路径。没有新增缓存或状态字段，不融合/重排事件。通用 RTL 向量表达式、门级安装器、敏感列表、驱动/alias/set/调度、SDF 与波形编码器保持。证明条件和接口见 [说明](../../docs/scalar-gates.md)。

变更范围为 `include/dsim/runtime.hpp` 的标量 helper/采样入口、`src/gate_compiler.cpp` 的模型表达式生成、CMake 新测试及 `tests/scalar_gate.cpp`。原 capture 在逻辑归一化后的完整算法逐字不变，通用 V 入口继续原归一化；新标量入口将 X/Z 归一化为存储 X。全四态真值表、三态未知控制及 state q/qn 独立性保持，未使用二态代数消除。

本地 CTest 分为首批 5/5（66.11s）与其余 23/23（199.42s），覆盖全部 28 个不同测试；Linux 单次完整 28/28（470.81s）。18 条完整有序波形与已验收延时驱动版本一致。15 门级用例的新 native 各三次对相同输入既有 VCS 三次，三个显式延时驱动微例同样复核既有 VCS；不声称这 18 组重新编译了 VCS。新增表达式集在本轮新编译 native/Icarus/VCS，256 组四态/11 输出，VCS 连续三次通过。

ASan/UBSan 使用 19 个实际二进制：11 个核心/适配目标和四类实际生成 checkpoint 模型各 baseline/replay 两个；核心 CTest 10/10，另运行适配器的三个模式。生成模型的 ordered/settled 完整波形与普通构建及回滚前后一致。两个实际并行 TSan 二进制通过，没有新增共享缓存。macOS 使用 `detect_leaks=0`，不声明 LSAN 通过。二进制和符号/源 SHA 见 `sanitizer-provenance.json`、`generated-sanitizer-records.json`。旧 sanitizer 与证据文件均未覆盖。

性能使用原 300,909 cell、111 种模型、内部 256/257 位连接、完整 1.2GB Liberty 和原 128 组黄金输出（不是精确 a*b%p）。两个版本重新生成并采用同 C++17/O2 编译，生成/编译与仿真计时分离。先结束所有本轮远端正确性/编译准备任务，再固定 CPU 0、串行预热和三次旋转 native 原版/候选/VCS。真实/反馈 VCS 使用既有 SHA 固定的二进制，本轮重新运行，三类 RTL 的 VCS 本轮新编译。随后对同一批 native 二进制做五次交替顺序配对；不将无 VCS 复测的分母与主实验混算。共享主机未独占或锁频，保留全部样本，不以单次计时决定采用。

最终候选源 `/tmp/dsim-scalar-gates-v3-source.tar.gz`，SHA256 `3b103b734716e44ac9e2cbaa01f77f741c1f9a4da62ed233a206ac28ed5a47b9`。160 个工程文件、108 个 parser 文件和 3 个不变原型依赖，Linux `/tmp/dsim-scalar-candidate-1018-qCBoSe`；独立原版构建 `/tmp/dsim-scalar-baseline-1018-HrfyrU` 来自上一批生产源包 `7d50442262e323b6b421a17abbe215e9b8e3c1f8a7f35378ba619f4f5426d6c3`。

初包沿用了运行时单点候选的计时说明，最终包修正说明和复现脚本归档路径；三份包中的生产/测试/parser 文件 SHA 完全相同，无需重跑相同 C++。初包与 v2 包均保留，证明见 `refresh-proof.json`。主流水线起始提取初包，执行性能前更新了上述驱动元数据；所有原始日志及初始清单保留。

实际 SDF 自动回标、逐接收 pin INTERCONNECT、条件/脉冲与 timing checks、自动分区和压缩格式扩展仍未实现；本候选是零延迟求值专用化，不降低这些功能的验收范围。

## 最终结果

| 首轮 CPU 中位数 / 秒 | 原版 | 候选 | VCS |
|---|---:|---:|---:|
| 真实设计 | 13.47 | 12.61 | 10.52 |
| 100k ff | 5.44 | 5.63 | 5.08 |
| RTL clock | 2.74 | 2.75 | 2.83 |
| RTL fanout | 2.70 | 2.69 | 2.97 |
| RTL arithmetic | 0.39 | 0.39 | 0.46 |

首轮真实约减少 6.38%，但独立五次配对复测为原版/候选 14.54/14.55s，未复现收益；反馈为 6.70/6.84s，候选五对均慢，fanout 为 2.70/2.70s。完整原始样本全部保留，包括 real/VCS 波动及 fanout 原版的一次 3.10s，不删异常值，不混算不同轮次分母。不将首轮候选约 1.20 倍 VCS CPU 计为已采用版本成绩。

主流水线与复测均 terminal 0。证据包 `/tmp/dsim-scalar-gates-evidence.tar.gz`，SHA256 `849a45c88a9617ba2b1440b7da062903a4c7b3e9e11eff0dcf00b4ba977b5494`，1459 文件。原始数据逐项核验并安全提取到 `remote-verified/`，独立 [analyze.py](analyze.py) 以冻结源 `/tmp/dsim-scalar-a-audit-source` 复核全部输入、完整事件、sanitizer 符号、原始 user+sys/RSS 和中位数，见 [analysis.json](analysis.json)；[decision.json](decision.json) 记录不采用决定。当前工作树正在验证后继候选，不宣称本版是默认生产实现。
