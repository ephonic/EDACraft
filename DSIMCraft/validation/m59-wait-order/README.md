# M59：wait_order 有序事件等待

已实现静态标量命名事件的 wait_order，包括成功/失败 action、缺省失败终止、单事件/重复名称、同 tick 阻塞和 NBA 顺序、automatic task、动态 fork 克隆/取消/重用、分区及预测回滚。RTL parser 独立增强，门级 parser 未修改。

每次实际触发推进相关等待站点，固定订阅按事件索引；完成结果锁定，进程恢复后执行编译的 action PC。站点状态由 Sim 保存，取消用既有 generation 排除旧订阅，动态 fork 克隆独立站点。没有轮询或 AST 解释。未使用本功能的模型不启用新字段。补齐工厂验证前设置 AST 标识、逗号事件列表验证和参数化实例克隆/三轮清理；修复 unique if 的 else wait_order 被误收进条件分支链的情况。Bison 仍为既有 47 个 shift/reduce 冲突。

- 六个共同支持模型：顺序/提前/重复/无关事件、重复名称和 action 绑定、NBA 批次、自动任务、12 次启动与 12 次取消、两个独立分区。串行/时间轮/双线程，VCD/DWF、ordered/settled 共 72 捕获；四个等待中的失败预测和一次分配前失败预测再增加 5 捕获，总计 77。断言每次预测确实 rollback；比较完整 ordered 流和 stdout。8 类拒绝和缺省 failure 终止另测。实际双分区数为 2。
- 真实 VCS W-2024.09：六份 SV 与 native 完全相同，TRACE/自检及全部 992 条物理位 settled 时间线一致，名称映射 0、排除位 0。VCS 探针确认已消费事件可以忽略，但重复名称仍出现在剩余序列时再次提前触发会失败。缺省失败终止只核对终止语义，不宣称双方退出码相同。完整 ordered 同 tick 流只在 native 多后端/格式和跨平台之间比较。
- macOS：最终 18 项不同定向 CTest 均有通过记录。`final-tests.log` 的首轮为 17/18，通过外新增旧 named_events 测试仍把合法 wait_order 当作不支持而失败；更新为空列表语法错误后，`named-events-final.log` 单项 40.89 秒通过。其余 17 项在 431.64 秒批次内通过，含新增回归 63.89 秒。初轮三个内核在 checkpoint 后注册新站点的测试错误、parser 工厂先验证再设标识的问题均已修复，原始失败日志保留。
- ASan/UBSan：六个最终实际生成程序（含实际双分区）与完整 ordered 波形一致，六语料各三轮 parser 清理、完整语义单测及三种直接内核通过。leak detection 关闭。见 `sanitizers/`、`sanitizers.log`、`parser-sanitizer.log`。
- Linux：最终冻结 1245 文件，另目录干净构建；parser/三内核检查及六串行/一实际双分区程序、14 波形捕获通过，全部退出 0。七份完整 C++、六份完整 ordered 流和 stdout 与 macOS 一致，再核对相同 992 条 VCS 位时间线通过。未运行 Linux sanitizer 或全量 CTest。冻结包 SHA256：`58be1569c37d47618b80ee7ee08e2cf88dc8ffdf37acaf80f835a4f4f587ec31`。

独立探针未混入共同支持通过数：`probes/order.sv` 在无 debug_access 的 VCS 编译中 SIGSEGV；`probes/direct.sv` 的多个词法等待共享同一组事件时，VCS 对重复/无关/过去事件及重复名称的结果与独立单站点探针、native 不同。保留原始输入、VCS 编译/运行日志和 native 输出，不修改预期或删位掩盖。`nonconsecutive.sv` 的失败 TRACE 双方一致。

当前边界：event 句柄赋值/别名/形参、数组和 automatic 局部 event 仍缺；函数与 specialized always 不允许 wait_order。递归/ref、动态容器、完整 class/随机约束/SVA/覆盖率/UVM/DPI/VPI、完整 SV 调度区域及全部门级时序支持仍未具备。M47 事件函数限制和 M55 逃逸直接事件差异继续保留；本轮没有新的性能测量，不宣称全面对齐 VCS。

复跑：

```sh
cmake --build build -j4 --target dsim test_verilog_semantic_memory wait_order_kernel_test wait_order_wheel_test wait_order_compact_test
ctest --test-dir build -R '^(rtl_wait_order|wait_order_(kernel|wheel|compact)|rtl_semantic_memory)$' --output-on-failure
python3 validation/m59-wait-order/verify.py
python3 validation/m59-wait-order/run-sanitizers.py
```

`run-vcs.py` 需在已 source `/apps/EDAs/syn.bash` 的远端执行，参数为同源 fixtures 目录和输出目录。`linux/driver.py`、源 hash 清单和各原始输出记录实际冻结构建；`final-identity.json` 对应最终生成物。
