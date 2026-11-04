# M57 显式 automatic 局部声明验收

状态：**PASS_SCOPED**。补齐过程 begin/fork、默认静态及 automatic task/function 局部变量的显式 `automatic` 限定，支持现有整数/logic/bit、命名/enum/packed 类型和固定局部数组。混合块只为自动变量分配激活存储；静态任务形参仍共享，自动局部按调用隔离，无 fork 时也成立。fork 声明在父进程入场初始化，分支内声明在分支启动时初始化。父块返回后，存活分支持有帧。

RTL 声明 AST、克隆/清理、grammar 与 Bison 生成文件同步；冲突仍为 47 个，lexer/门级 parser 不变。复用 M55 帧、PC、订阅和快照，未改 runtime。编译作用域独立记录实际声明的帧成员，避免把 foreach 隐式索引误当普通局部声明重置。功能边界见 [说明](../../docs/explicit-automatic.md)。

## 验证范围

- [六组同源模型](../../tests/explicit_automatic)：逐轮捕获、静态任务形参共享/自动局部隔离、静态函数状态与自动默认值、130 位/四态/两态/enum/局部数组、取消和嵌套控制转移、局部表达式/iff/电平等待、实际双分区。
- 串行/时间轮/双线程及 VCD/DWF ordered/settled，**76 次捕获**完整逐信号流一致；三个挂起期间及一个分配前的实际失败预测，共 **4 次恢复**。48 次调用后检查进程不超过 16、信号槽不超过 100；8 类非法或未支持语法/生命周期明确拒绝。
- 实际 VCS W-2024.09：六份 SV 字节相同，TRACE/自检及 **928 条物理位 settled 时间线一致**，没有位排除。仅一个隐式 for 作用域命名映射：`top.unnamed$$_vcs_0.body.calls` → `top.body.calls`，其全部 32 位仍参与比较。见 [原始 VCS 日志](vcs)、[比较结果](vcs-results.json) 和 [verify.py](verify.py)。
- 修正后本地 **15 项不同定向 CTest** 全部通过：13 项既有测试 266.22 秒，foreach 与新增功能两项 68.42 秒。不是全量 CTest。
- macOS ASan/UBSan：六个最终实际生成程序（含双线程）与完整 ordered 流、六语料各三轮 parser 清理、完整 parser 语义单测、kernel/wheel/compact 三内核通过；leak 检查关闭。程序哈希见 [sanitizers/results.json](sanitizers/results.json)。
- Linux 从冻结 **1206 文件**干净构建，parser 语义单测与三个帧内核共 4 项 CTest 通过（1.20 秒），六串行加一个实际双分区程序、14 个波形捕获通过。**7 份完整 C++ 字节相同，六个完整 ordered 流和 stdout 跨平台一致**，Linux 再核对相同 928 条 VCS 位时间线通过。见 [Linux 结果](linux/results.json) 和 [跨平台比较](linux/cross-platform.json)。未跑 Linux 全量回归或 sanitizer。

## 发现并修复的问题

初轮 14 项既有回归中 12 通过、2 失败（275.33 秒），原始 [日志](regressions.log) 保留：integer 仍预期拒绝 automatic，已升级为重复进入自动局部的正向断言；foreach 重叠任务暴露隐式索引在后续入口被重置为 X 的实际错误，已用独立的声明帧成员集合修复。最终上述 15 项全部在修正后运行通过。

初次 Linux 构建在发现该编译器错误后中断自己运行的 5 个进程，记录为 [INTERRUPTED_FOR_COMPILER_FIX](linux/initial/stop.json)，不计通过。最终另建干净目录，按修正后的源清单完整构建和核验。

## 原始探针与边界

[父进程捕获](probes/capture.sv) 得到 `TRACE capture 10 4`；[无 fork 的静态任务](probes/task.sv) 得到 `TRACE task 6 8 6`；[分支内初始化](probes/branch.sv) 得到 `TRACE branch 20`，均与真实 VCS TRACE 相同。第三项确认循环结束后启动的分支读取最终 i=5，不能将分支内声明误作父进程逐轮捕获。见 [探针结果](probes/results.json)。

显式 static 覆盖、module/for 头部 lifetime 语法、递归/ref/动态容器、automatic 局部 event 及 NBA 写 automatic 变量仍未支持。M47 默认静态函数事件限制、M55 逃逸局部直接事件等待差异保留。未进行新性能测速，不宣称完整 SystemVerilog 或与 VCS 全功能/性能对齐。

## 证据与复现

入口：`ctest --test-dir build -R '^rtl_explicit_automatic$' --output-on-failure`。同源 [VCS](run-vcs.py)、[sanitizer](run-sanitizers.py)、[Linux 模型](run-linux.py) 运行器和 [Linux 构建驱动](linux/driver.py) 均保留。

[results.json](results.json) 汇总结果，[final-identity.json](final-identity.json) 保存七份最终 C++ 哈希；[source-manifest.json](source-manifest.json)、[source-changes.json](source-changes.json) 记录冻结源，1206 个文件在归档后再次核对一致。源包 SHA256：`660bff9b2e9b18a2a55af721f6f1c17fb13766b002810f761d45c557a58e7d25`。原始日志保留工具产生的空白。
