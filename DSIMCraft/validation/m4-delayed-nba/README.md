# RTL 常量延时 NBA

`q <= #常量 expr` 已接入编译和运行时，过程不暂停，右值立即采样，到期后进入 NBA；`#0`、同一过程多次更新、部分选/拼接/重复目标、257 位四态值、模块精度和时钟重复触发均有实际编译用例。动态 delay 和 event/repeat 赋值控制仍拒绝。RTL/gate parser 分开；仅改 RTL grammar、语义校验、RTL lowering、受宏保护的 runtime 和 CMake，新增三个测试文件。

最终冻结 419 文件源码 SHA256 `3d125f704b56ce50fb204db0613420767a59124dfa5d250bbab39cb7a8b6e6a8`，源包 `/tmp/dsim-delayed-nba-source.tar.gz`。默认不启用 `DSIM_DELAYED_NBA_ENABLED`，无此语句的程序保持原 Timer 布局/调度；完整真实 SDF 的新编译器生成身份正在远端验证。

修正后的独立编译器已通过原 RTL 回归及九个 NBA 用例；ordered/settled × VCD/raw DWF/Zstd DWF 共 66 份捕获逐事件比较，包含真实生成程序的待交付事件预测回滚。回滚对照采用相同的 `run_until(500/6500)` 边界，保留所有空时间标记，而不删除它们后比较。混合延时驱动/标量/257 位事件、重复检查点/池复用、非法时间、12 组全局结束及实际生成回滚程序已通过 macOS ASan/UBSan；不宣称 Linux sanitizer。

最终冻结源的 macOS 完整 **66/66**（324.16s）、Linux 干净构建完整 **66/66**（441.72s）均已通过。九组同源 native/新编译 VCS 各三次输出一致；统一流程 transport/clock/wide/precision 四例的无波形/VCD/DWF 通过，Linux 另与 VCS 比较完整 TRACE 和全部 555 个顶层稳态位。实际新 Linux 编译器重读原始完整网表/Liberty/SDF，关闭延时 NBA 宏时整个生成 C++ 仅差 runtime，GCC 预处理逐字相同，未关闭检查。610 个远端原始证据文件归档 SHA256 `8a1a906423d9c72cd9f8895da1ca49fa04d813a4f57e033336329dbb89f05f1c`；源码、两端捕获、新 VCS、实际 sanitizer 与完整 C++ 身份已独立复算，`verification.json` PASS。目前无本功能的性能收益声明。

工作区后继仅推进流式波形比较工具。复查本批最终源码时使用 `python3 validation/m4-delayed-nba/verify.py --source-root /tmp/dsim-delayed-nba-frozen-1018`，不能把后继工具脚本更改称为本次 419 文件源。

初版 grammar 只把延时分支改为 unary-expression 前缀，完整回归发现普通 `q <= d` 被错误解析，macOS 初版 7/66 失败；保留初始源码 `source-initial.json`、`initial-failure.json` 和 `macos-ctest-initial.log`。单改为 expression 前缀则拒绝 `<= #`，探针日志亦保留。最终三类 NBA 共用 unary-expression 前缀，普通/延时回归均通过；Bison 的既有 33 shift/reduce、69 reduce/reduce 冲突及两条既有无效规则数量不变。初版远端任务正常结束后另做最终冻结源的干净验证，不因观察超时重启进程。

首个生成回滚探针错误使用窄值后端不存在的 `V::ones`，随后修为通用 `V::x`；首个完整波形比较遗漏手工运行边界新增的空 tick，已改为实际边界参考运行。这两次测试夹具失败保留在 `targeted-flow.log`、`targeted-flow-corrected.log`，不归为仿真语义修复或性能实验。
