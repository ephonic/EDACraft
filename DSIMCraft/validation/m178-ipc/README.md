# M178：本地原生 mailbox / semaphore

继续 REPORT-GAP3 的功能补齐。仅本地开发，未推送、未操作103、未激活稳定入口。实现及最终结果以本目录 JSON 中的输入/生成程序哈希为准；`work/` 和首轮日志保留开发过程，最终输入使用 `final3/`。

本批接通独立于用户类的规范 IPC 类型身份、`mailbox` / `mailbox #(T)` / `semaphore`、类型别名、构造边界/初始键数，以及 mailbox 的 put/get/peek/try_put/try_get/try_peek/num 和 semaphore 的 put/get/try_get。阻塞操作编译为过程状态机的挂起/恢复，运行时使用 FIFO 等待队列，不使用 #0 轮询。接收者、输入和 ref 目标选择在调用时捕获一次；完成后恢复原目标。支持整数/packed 向量、enum、string、real 和类句柄消息；普通 mailbox 保存每条消息的类型，try_get/try_peek 类型不符返回负数且保留消息。

对象、消息、等待请求和待写回数据全部由 Sim 持有，checkpoint 复制这些状态；取消进程时移除等待请求；整批disable的全部子进程清理完成后，再检查后续可运行的等待者，避免把资源交给同批将被取消的进程。IPC 的 heap 依赖把通信进程归入同一运行分区，独立进程仍可进入其他分区。没有同一 IPC 对象跨工作线程并发访问的声明。

## 验收

最终结果见 `progress.json`、`ipc.json`、`sanitizer.json`、`guards.json` 和 `bindings.json`。新9模型164捕获、27编译拒绝/9运行时诊断，实际回滚/提交各一次及真实双分区；最终前端、9模型/9运行时诊断及回放经ASan/UBSan验证（未启用LSan，无新TSan结论）。旧五组35模型559捕获和mandatory复验，105份执行CPP与最终源重新发射相符。新输入在 `tests/ipc/`，包含有界写阻塞、FIFO、多 peek、取消队首后唤醒、取消读写、automatic task 及 ref 形参、一次性输入/接收者/固定数组与类属性目标捕获、128位值/enum/real/string/对象别名、预测恢复及真实双分区。正常运行比较文本 VCD / 同步 DWF / 独立线程压缩 DWF，ordered/settled 两种模式均检查；回滚另比较恢复后的完整波形和用户指定范围。

复现：

```sh
cmake --build build-m176 --target dsim test_verilog_semantic_memory parser_bundle_smoke liberty_db_test -j 6
python3 tests/ipc/regression.py build-m176/dsim validation/m178-ipc/final3 build-m176/CMakeCache.txt
python3 validation/m178-ipc/sanitize.py build-m150-asan/dsim validation/m178-ipc/final3 validation/m178-ipc/sanitized-final3
```

报告原始 `probes3/q07_mailbox.sv` 原样编译/执行输出 `PROBE_MAILBOX: ok`。公开 Accellera 2020.3.1 库保持原内容，166个依赖、1888084字节的预处理输出维持原SHA；原生编译首错仍为 `uvm_sequence_library.svh:191` 的 `randc`。**完整公开 UVM 仍不能编译运行**，不能将 IPC 局部回归或首错位置视为完整方法学通过。没有本轮 VCS/Intel、性能或新 TSan 结论。

## 边界与后续

- 暂不支持 unpacked 数组/struct 消息、packed struct 消息，以及动态容器元素或部分 packed 选择作为 mailbox ref 目标；编译期拒绝。
- 无类型 mailbox 的整型表达式类型推导目前只接变量、数字 primary 及变量的 packed 选择等已明确类型路径；复杂表达式须先存入变量或使用 typed mailbox。不能把这一范围写成全部 dynamic_singular_type 已支持。
- typed mailbox 的输入使用已有形参转换，ref 输出要求等价类型；继承现有数值/二态四态类型模型。本轮没有重做整体 SystemVerilog 类型系统。
- 原有用户 task 的 class property ref 绑定（当前开发版及未变更 M175 均已复现，见 `known-gap.json`）仍存在运行时 `invalid reference argument binding` 缺口；开发 payload 首版触发并保留在工作日志。本批 native mailbox 直接传入类属性目标已通过，普通 ref 标量任务也通过，不把它们计为修复该旧缺口。
- 后续继续 randc 循环状态、dist、solve-before、virtual interface/clocking、coverage、program/let/specify/assert 控制，并以未修改公开库的实际 component/phase/objection/sequence 执行验收。
