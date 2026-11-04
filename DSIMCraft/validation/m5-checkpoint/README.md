# 内核检查点与保守并行验证

本批总记录和冻结清单见 [SDF/并行基础批次](../m4-sdf/README.md)，实现边界见 [设计文档](../../docs/parallel-and-rollback.md)。

- `local-ctest.log`：完整 15/15；`final-core-tests.log`：最后的并行输入边界、输出时间戳和完整时间 oracle 变更后复核 4/4。
- `sanitized-ctest.log`：完整 ASan/UBSan 15/15；`final-sanitized-core.log`：最终 checkpoint/parallel 2/2。
- `final-parallel/asan-run.log` / `tsan-run.log`：最终并行代码的 ASan/UBSan 与 ThreadSanitizer，无错误报告。
- `sanitized-generated-wave.log`：全部 18 个生成波形模型的 ASan/UBSan；`sanitized-replay.log`：额外 4 个实际生成的 checkpoint / 错误预测重放程序，两份 baseline/replay 可执行文件均经过 ASan/UBSan 编译，核对 stdout 和 ordered/settled DWF。
- `asan-cxx/c++` 是最后一项验证所用包装器，实际调用 `/usr/bin/c++` 并附加 sanitizer，不修改项目生成代码。对应数据目录 `build-control-sanitized/asan-checkpoint-regression`。

早期 `parallel-core-tests.log` 的反馈断言失败是测试错误地假定未知值会永久保持；最终改用明确的已知初态与独立反馈递推预期，并把打印时间从默认一位 `V` 改为完整 64 位以避免只比较奇偶。早期失败日志保留。

实际修复包括：sized decimal 高位越界（第三方最小补丁）、事务回放 settled 波形时误读最终内核值、并行输入的初始时间边界，以及延迟提交输出必须保存原时间戳。先前未提交波形工作的重复标量声明修复与失败证据保留在 `../m6-native-waveform/`。

这些测试不证明任意用户闭包可自动回滚，也不证明一般 Verilog 网表可以并行运行。共享模型状态须注册；外部输出须走提交协议；当前并行由 API 手工划分正延迟分区。
