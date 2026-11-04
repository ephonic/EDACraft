# PORT / DEVICE 实际仿真接入

本批扩展实际 `--sdf-annotate` 入口，RTL parser 与大网表 gate parser 继续分离；没有改动运行时、路径选择、波形或并行头文件。

- PORT 使用逐接收叶输入的独立延迟通道，按目标模型精度量化；与 INTERCONNECT 共享同一接收 pin，不增加额外传播阶段。437源对多驱动PORT采用最后一次ABS更新的策略，经后继VCS对照证实错误，已由[443源修正](../m4-sdf-port-policy/README.md)为MAXIMUM合并。
- DEVICE 更新指定外部输出的所有 module paths；不指定输出时覆盖所有外部输出。保留每条路径的条件、边沿、ifnone 和输入变化时间来源，与 IOPATH 更新共享表状态。没有 module path 的 primitive body 尚不能注解，明确拒绝。
- 输入限制沿用已执行的 MIPD 范围，DEVICE 沿用路径表的 12 转换、ABS/INC/corner 量化。scope/inout、pulse threshold/RETAIN 等未实现语义继续报错。
- 新的 origin 标记仅用于编译期统计；旧 INTERCONNECT 报告只统计对应来源，PORT 增加独立计数。

`tests/sdf_port_device/regression.py` 通过实际 CLI 编译 generic/scalar/jobs/jobs-wheel，比较 equivalent.sdf 的完整生成 C++、完整 stdout/stderr、ordered/settled × VCD/raw/Zstd 的全部事件。可选 `--baseline` 指向已验收435源的旧编译器，直接验证旧版 INTERCONNECT/IOPATH 与新版 PORT/DEVICE 的完整 C++ 身份。冻结 VCS 的旧 IC/IOPATH 参考仅用于等价输入的物理波形控制，不能称为新的 PORT/DEVICE VCS 对照。

另有实际生成程序的 pending timer、拒绝预测回滚及接受提交对照；`--sanitize` 会对 boundary/replay 生成程序启用 ASan/UBSan。普通 Verilog 自动预测器不因这个 API 验证而成为已实现。

437文件源`c36bc6b6d7c38050507e64ab49d8dfa2fa1c812784cdd47c5f722f5ff9e2765d`已冻结。当前本地独立核对PASS，见[local-validation.json](local-validation.json)：

- 既有94项回归全部通过（650.96s）；新增流程单独运行28个场景、32个corner配置、四后端，共768常规捕获和24生成回放。
- 独立sanitizer批次另有72份准备捕获和24份实际ASan/UBSan生成回放，12个插桩二进制。合计840份常规捕获、48份回放；不能把840份全部称为sanitizer捕获。
- 140次完整生成C++身份比较（主批128次、sanitizer准备12次）与旧435编译器的等价INTERCONNECT/IOPATH输入一致；既有VCS oracle另按输出及私有接收位复核。
- 测试清单查询`ctest -N`覆盖了运行中的详细`LastTest.log`，覆盖后的文件及说明原样保留。完整控制台日志的94个唯一Passed测试名与两个生成CTest清单逐项匹配，不能声称该详细日志仍保留了94项内容。新增流程的每次命令、stdout/stderr、完整C++和波形均已归档并逐文件校验。

本批新VCS任务已实际结束1，795个原始文件归档`25d1b65dea144ab00bd3b913dad701183b24aa638bf2687152a5b0ca0df245e0`已下载并独立重算全部波形差异：32组中26组各三次通过，6组第一次即不一致，总84次实际运行；全部注解日志零错误/警告，见[vcs-verification.json](vcs-verification.json)。失败保持FAIL，没有用本地等价输入覆盖vendor参考。

差异为通配PORT的三个corner、多驱动PORT重复更新、DEVICE/IOPATH混合更新、以及PORT+通配DEVICE。额外13个PORT探针已归档173文件`3e54d37b223be8c035bdda95089bc9880ce1b2e1aa95f600189cd2cdfb66bc5a`。编译日志显示相同定义的S/D合并后只生成S，通配PORT D也影响S；不同时间精度阻止该合并时S不受影响。不存在CELLTYPE会产生NIWF警告并不注解；不是无条件忽略CELLTYPE。DEVICE补充探针另保留，混合状态的修正尚未实现。

Linux完整集成和完整vendor兼容仍未通过，没有提速声明。没有module path的primitive DEVICE仍明确拒绝。原437源的`launch_linux.py`保留但不应继续把已知语义差异当通过；后继集成使用修正源，并同时覆盖435全局波形，避免重复构建。
