# 连续赋值/原语常量 delay

此目录保留初版验证历史。后续 Linux 71/71 通过，但新 VCS 的 vector 用例失败，初版未通过 VCS 验收；修正版默认 VCS/显式 IEEE 模式及 packed 声明支持见 [m4-continuous-vcs](../m4-continuous-vcs/README.md)。

最终冻结 425 文件，SHA256 `909f7d2ac17f64ad5849fa5a5fe869c31c2236c58347493fb7ea0dcbfcf1512e`。实现和边界见 [continuous-delays.md](../../docs/continuous-delays.md)。RTL grammar 的逗号延迟列表在 AST 构造时解包，一/二/三值 delay 使用同一入口；修正旧第三项缓存误读第二项。保持既有 33 SR / 69 RR 冲突及两条无效规则，门级和 SDF parser 均未改。

本地新增 11 组源码/78 捕获和实际生成待交付事件的预测重放，ordered/settled × VCD/raw DWF/Zstd 完整比较通过。`check_oracle.py` 另按手算整数 tick 核对 17 条完整有序变化流，保留所有变化，不筛稳定点。普通/紧凑/标量内核的 32 种四态转换、取消/去重、目标片段/别名/多驱动、257 位、混合 timing、检查点复用与溢出通过。普通及 scalar+compact 内核、实际生成重放、12 个显式并行全局结束配置的 macOS ASan/UBSan 通过，不是 Linux sanitizer 结论。

公共六例流程及额外四例向量/packed/宽拼接/三态流程通过。新增公共例串接 delayed NBA、continuous、bufif 和 SDF INTERCONNECT/IOPATH；没有关闭时序检查。

首次 71 项完整本地回归有 70 项通过，唯一失败是原测试仍要求 `assign #1` 被拒绝。本批保留该语法为执行式正例，重跑修改的 `compiled_regression` 通过（50.22s）；其余 70 项的生产代码逐字不变，不重跑整套。最初 425 源包 `858af1466aba2e770a94034bd2e01adbee4b44a60923e1a2f94ea7cfdd4260f0`、完整日志及新正例重跑日志分别保留，最终源码仅比该包多一处测试更新。`local-validation.json` 明确区分聚合覆盖与单次全套通过。

初次 Bison 命令漏传 `-p verilog` 的构建失败及显式三值 grammar 冲突探查保留；最终生成带正确前缀，冲突未增加。生成文件相对路径和 include guard 的变化来自在 grammar 目录运行 Bison。

Icarus 13 的九组结果一致，两组向量多值延迟行为不同，差异保留于 `icarus/`，尚不以此宣称 VCS 验收。Linux 干净构建、71 项、11 组新 VCS ×3、全部公共流程/选定顶层位时间线和真实完整 SDF 重新生成身份，由 `launch_linux.py` 在现有标量五对测量终止并独立核对后启动；当前尚未启动。实际旧全量程序替换整个 runtime 的本地预处理已相同；不替代新编译器真实生成证明。

复查最终源码用 `/tmp/dsim-continuous-delay-frozen-1018`；初始源码另存 `/tmp/dsim-continuous-delay-initial-frozen-1018`。本批无性能收益声明，未接入普通 RTL 自动并行或自动预测器。
