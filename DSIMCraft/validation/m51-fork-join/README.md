# M51 并发过程 fork/join

接通 `fork … join`：各直接子语句编译为独立可挂起进程，父进程等待全部分支完成后继续。支持空/单分支、嵌套、命名块/声明、循环和 always 复用、automatic task 并发调用、既有 delay/事件/iff/命名事件/NBA。详细范围见 [fork-join.md](../../docs/fork-join.md)。

分支静态注册，在父进程到达 fork 前保持 dormant。启动时设置父进程等待代际并排入分支，最后一个分支结束后把父进程放回 Active，因此 join 不等尚未交付的 NBA。无需运行时注册拓扑或轮询；DSIM_FORK_JOIN_ENABLED 按需启用。父子控制边参加分区，整组留在一个内核，独立模块继续双分区执行。所有完成位/剩余数与已有队列、PC、自动存储随 Sim 快照复制。并发调用的 automatic task 依调用点与子进程分配调用槽，join 之前父调用帧不退出。

RTL lexer/grammar 新增 fork/join/join_any/join_none，并行块复用块作用域/遍历/克隆机制，增加块类型标记。Bison/Flex 生成文件同步，实际基线/新版本均47项 shift/reduce 冲突；parser 单测验证参数化模块两实例克隆后嵌套块类型、绑定/错误恢复和三轮清理。门级专用 parser 未改。旧 automatic task 回归把 fork 负例升级为仍缺少生命周期支持的 join_any；新语料覆盖原 fork 正向行为，历史验收记录不改。

真实 VCS W-2024.09（10.131.254.103，`source /apps/EDAs/syn.bash`）六个同源模型 nested/scopes/events/nba/parallel/always 的 TRACE/自检和 **642 条物理位 settled 时间线**全部一致。共同源字节相同，无别名、无位排除。独立时间线检查验证两个 lane 的1/3/5倍周期更新、条件边沿、命名事件计数及 NBA 交付。并发分支间共享变量的同刻竞争不承诺任意 VCS 顺序一致。

五个原始探针保留原始源码、编译/运行日志、退出码和 TRACE：empty/nba/nested/reuse 四项对齐；**join_any 由 VCS 接受、native 明确拒绝，仍是缺口**。join_any/join_none 的语法识别不算执行支持。verify.py 严格检查上述差距，未把负例混算为对齐。

六模型三后端（串行/时间轮/双线程）×两格式（VCD/DWF）×两模式（ordered/settled）共72捕获；nested/scopes/events 在1ns分支未完成时各做一次实际失败预测/恢复，另加3捕获，共 **75捕获、3回滚**。完整 ordered 逐信号事件/stdout 一致。七类拒绝通过；真实 --threads2 的 partitions=2，--threads8 emit-only 也保持两个域，仅检查分区。三个直接内核（kernel/wheel/compact）覆盖 dormant、重复启动、部分完成检查点/恢复、实际失败预测、NBA、信号边沿及非法拓扑/重复完成检查。

本地 **41 项定向 CTest** 全通过，297.99秒。macOS ASan/UBSan parser 全部语义单测、六语料各三轮清理、六份实际最终程序及完整 ordered 流、三个直接内核通过，包含真实双线程；leak 检测关闭。七份完整实际CPP（六串行、一双线程）重新生成字节一致，六个 sanitizer CPP hash 对应实际最终程序。

Linux 同源干净构建 **41 项定向 CTest** 全通过，513.06秒，退出0；七份完整CPP及六模型完整 ordered 逐信号事件/stdout跨平台一致，再次核对同样VCS的642条位时间线。五原始探针只复核保存的macOS/VCS记录，未在Linux重跑该组探针。冻结 1094 文件，源包SHA256 `e235efcc2ad590a7a5d0e69e735cdc64b430acb219bb31ae88025c93942ef1b3`；source-manifest.json 中所有文件未改，plan1017.md和验收输出不在清单。首轮发现旧 fork 负例预期已过期，最终源码升级后重新冻结并重新进行本地/远端验收；首轮结果不计为通过。证据 local/linux/vcs/probes/sanitizers 保存实际CPP、IR、源码、日志/退出码及波形，不保存二进制。

复跑：`ctest --test-dir build -R '^(rtl_fork_join|fork_join_kernel|fork_join_wheel|fork_join_compact)$' --output-on-failure`；`python3 validation/m51-fork-join/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py 保存相应流程。

仍缺 join_any/join_none 执行、disable fork/wait fork、process 对象、脱离父进程的动态生命周期、join 关闭标签，以及既有完整对象/事件区域、SVA/UVM、历史差异等。函数和 specialized always 中 fork 明确拒绝。本批未跑全量CTest、Linux sanitizer或新性能测量，不称全部 SV/VCS 功能或速度对齐。
