# 连续 delay 的 VCS 差异修正

初版冻结 425 源 `909f7d2…` 的 Linux 完整 71/71 通过（456.39s），随后新 VCS 对照在 `vector` 失败，原任务 `/tmp/dsim-continuous-delay-1018-MMiuc1OK` 正常以错误状态终止；未将其作为功能验收通过。初版源码、macOS 捕获及终止记录保留于相邻 `m4-continuous-delay`。

定向探针实测 VCS W-2024.09：多值连续 delay 按 RHS 最低位的 0/1/X/Z 选择，再整体交付向量。16 种标量和 64 种向量转换、声明/whole/part/concat/一位 packed 等形式共 960 条输出，三次完全一致。Icarus 在部分向量例上也与 VCS 不同，不能用它代替该版本 VCS 参考。原始证据与新矩阵期望逐条核对 PASS，见 `../m4-continuous-delay/vcs-vector-probe`；探针初次声明语法写错的源和日志另行保留。

修正版默认 `--continuous-delay-mode vcs`，提供显式 `ieee` 保留 IEEE 1800-2017 10.3.3 的向量选择，IR 记录模式；不把实测 VCS 行为说成 IEEE 文本规则。补入 RTL parser 的 `range delay3` 声明分支，Bison 仍为原 33 shift/reduce、69 reduce/reduce，gate/SDF parser 未改。

最终冻结 425 源 SHA256 `d862b9173684475f0a352fe02ed1d9665b66f37016fc65cee31733d0d61361a2`，相对初版仅修改 10 项，见 `changes.json`。本地五项定向测试已通过：12 组源码/84 原生捕获/实际预测重放、两组显式 IEEE 对照和四种内核。四个实际内核及实际生成回放的本地 ASan/UBSan 通过，含 12 组并行全局结束配置；feature-off 的实际完整 SDF runtime 替换后同一 Clang 预处理逐字相同。本地完整 **72/72** 通过（345.94s），381 份捕获文件及源码/全部事件流/IEEE 模式/17 条手算时间线/sanitizer/完整 CPP 替换与预处理身份的独立核对 PASS，见 `local-validation.json`。Linux 干净构建、新VCS、72项及实际全SDF生成身份的最终验收结果见下文；本批不声明性能收益。

Linux 新目录 `/tmp/dsim-continuous-vcs-1018-LEurnsnX`，原会话17520已正常退出0。完整 **72/72** 通过（468.38s）；12组新native/VCS各三次，以及六例公共流程581个位时间线、四例定向流程562个位时间线通过。936个原始证据文件归档 SHA256 为 `c3324718cfb6a90ba70f4e0d32f71449ca58e50cfcdc19ba377c017d759ef0ff`。`verify.py --source-root /tmp/dsim-continuous-vcs-frozen-1018` 已逐项核对原始文件身份、两平台84份完整事件流/17条独立时间线、新VCS、实际默认/标量完整SDF生成等式及同GCC预处理身份，结果 `verification.json PASS`；本批功能验收完成，没有性能收益声明。

工作区已继续接入实验性时间轮，不能将当前427源称为本批425源；复查仍使用上述冻结根目录。本批整项终止并验收后，已启动标量独立性能复测，见相邻 `m5-scalar-timing/replication-inflight.json`。普通 Verilog 自动并行、自动预测器和完整 SDF 功能目标仍未完成。
