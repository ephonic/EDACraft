# M55：automatic fork 动态变量帧

本批范围验收通过；不代表完整 SystemVerilog/VCS 功能或速度对齐。

- automatic task/过程块的形参、局部标量、宽 packed/two-state 值和固定局部数组按激活隔离。fork 同级分支共享本次父帧；join_any/join_none 后父任务返回，分支仍持有变量。
- 等待按实际帧绑定，表达式回调使用等待进程的变量上下文。return/break/词法 disable 按编译 PC 的作用域深度收尾；完成/取消后复用无存活引用的同布局存储。快照持有的帧不会提前复用，值由 Sim 独立复制。
- 补齐逃逸命名块的取消：不重启已经返回的父任务，取消计数收尾后可恢复外部 wait fork。原失败探针及 VCS 输出见 probes/escaped-disable，最终 control 同源模型同时核对延迟等待和 wait fork。
- 修复混合门级模块晚于 fork 配置注册信号时的波形边界，三种直接内核检查晚注册静态信号仍可导出、私有槽不会导出。变量查找沿持有的不可变帧借用指针，避免每次读取增减 shared_ptr 引用。

RTL 与门级 parser 均未改动，继续独立维护。旧 automatic 父帧/子任务负例升级为实际执行；foreach 隐式索引的重叠仍明确拒绝。

## 验证

| 项目 | 实际结果 |
| --- | --- |
| 本地模型 | 6 模型、76 个捕获；串行/时间轮/双线程，VCD/DWF 与 ordered/settled；3 个挂起期间及 1 个分配前的真实失败预测恢复 |
| 生命周期/复用 | 75 次任务调用、提前返回、嵌套块、取消、两次父任务已返回后的命名取消；直接内核再检查存储池与前/后检查点 |
| VCS W-2024.09 | 6 份字节相同设计，TRACE/自检及全部 928 条导出物理位 settled 时间线一致；无别名、无位排除；M53 原始 escape 源由拒绝升级为对齐 |
| macOS CTest | 先前 12 项定向检查 288.64 秒通过；最终受影响 10 项 139.17 秒通过，合计 18 个不同检查通过 |
| ASan/UBSan | 6 个实际最终程序（含双分区）、6 个 parser 语料各三轮清理、完整 parser 语义单测及 3 种直接内核通过；leak 关闭 |
| Linux 最终范围 | 最终清单核对、内核重建及 3 项内核检查通过；6 串行程序及 1 个真实双分区程序、14 个 VCD 捕获通过 |
| 跨平台 | 7 份完整 C++ 字节一致，6 份完整 ordered 逐信号流及 stdout 一致；Linux 再核对同样 928 条 VCS 位时间线通过 |

Linux 初始 13 项大回归自然完成，12 项通过、gate_regression 一项因生成的 seq_edges C++ 编译超过既有 90 秒限制失败（exit 1）。范围切换命令发出时已无该测试进程，实际中断进程为 0；历史命名的 linux/initial-interruption.json 已按真实完成状态更正。未把该失败计为通过，也不宣称 Linux 全量回归通过。随后同步最终 7 个变更文件、核对清单并完成上表的最终范围（exit 0）；详见 linux/final-source-changes.json、final-tests.log、final-models.log 与保留的原始 tests.log。

初轮共享帧语料用顶层数组作观测量，VCS 默认 VCD 不导出数组字，显式 dumpvars 也给出警告；相应原始 VCS 证据保留在 initial-sharing-vcs。最终语料用四个具名结果字段，局部数组仍由 overlap 同源模型独立自检。临时语料的一处 endcase 拼接笔误已修复，失败日志保留在 input-typo.log，最终语料全部重新执行。

## 保留差异与范围

父任务已返回时，VCS W-2024.09 对原始 probes/escaped-direct-event.sv 的直接 `@(posedge local_clock)` 没有唤醒；dsim 会唤醒。表达式事件、父任务仍存活时的直接事件在主模型对齐。原始探针保留为 KNOWN_DIFFERENCE，不计入 6 份对齐模型。

仍缺 foreach 索引动态帧、递归/process 对象、automatic 局部 event、NBA 写 automatic 变量，以及完整 SV 验证与时序能力。本批不修改这些边界，不宣称完整标准、完整 VCS 对齐或新速度结果；没有全量 CTest、Linux sanitizer 或新性能测量。

## 证据与复现

- results.json：本批实际范围；source-manifest.json/source-changes.json/source-archive.json：冻结源码及变更。
- local、sanitizers、linux、vcs：实际程序文本、波形和日志，不含可执行文件或 vendor 生成的构建目录。
- verify.py：对全部可观测身份及位时间线严格比较；run-vcs.py：真实 VCS；run-sanitizers.py：实际最终 C++ 的 sanitizer；run-linux.py：初始大回归；linux/smoke-runner.py：最终聚焦范围。
- `ctest --test-dir build -R '^(rtl_automatic_fork|automatic_fork_(kernel|wheel|compact))$' --output-on-failure`
- `python3 validation/m55-automatic-fork/verify.py`

冻结源码 1174 文件，归档 SHA256 `659fc03c3ed91baca89a3d88c5651f5e363a232500ff07f1b942395194c44d27`；最终清单文件未再改动。
