# M53 分支提前继续与过程收尾

接通 `join_any`、`join_none`、`wait fork` 和 `disable fork` 的静态激活子集。join_any 首个直接子进程完成后恢复父进程，其余继续且不重复恢复；join_none 父进程继续，子进程在父进程阻塞或结束后才执行。wait fork 等待当前进程所有未完成的直接子进程，覆盖多个 fork 位置；子进程已结束但孙进程仍活跃时不等待孙进程。disable fork 取消所有后代，包括这种存活孙进程，保留当前进程和同行分支。详见[功能范围](../../docs/fork-control.md)。

仍使用编译期注册的进程槽，只有前一轮后代全部结束或被取消才可复用。重叠复用在运行入口明确报错，automatic 父存储中的 join_any/join_none 保守编译拒绝，提示需要动态激活帧。分支调用阻塞 automatic 子任务已支持。这是可执行子集，不是完整动态进程能力；VCS 能接受的 overlap/escape 两项差距保留，未包装成对齐。

ForkGroup 增加类型和首次恢复状态，完成计数记录直接子进程，wait fork 集合记录父进程等待。start_fork 的 Active 排队配合编译闭包执行到阻塞/结束，保证 join_none 分支不提前读取父进程后续写入。取消遍历编译父子图，复用 M52 控制 epoch 隔离旧队列/定时器/事件，保留已发起 NBA、延迟 NBA、内部事件 NBA 及独立驱动。父子控制边保持同组分区，等待集合、计数、首次恢复状态、PC 和队列随 Sim 快照复制；未增加轮询或运行时 AST 解释。

RTL grammar 新增 wait/disable fork 两语句，复用动作 AST 的绑定/克隆/清理，新增两个 detail tag；参数化模块两实例及三轮清理纳入单测。Bison 生成文件同步、47项 shift/reduce 冲突未增加；lexer 和门级专用 parser 未改。M51/M52/automatic 子程序的旧 join_any/join_none 负例升级为尚缺的 automatic 父帧逃逸负例；level wait 的旧 wait fork 拒绝用例改为函数内非法控制拒绝。初次回归因旧预期失败的日志保留于 ctest-initial.log 和 linux/initial，更新测试后，本地重新执行完整49项定向集合；Linux 保留其余48项通过结果，只复测修改过的 level wait 用例。历史验收记录保留。

真实 VCS W-2024.09（10.131.254.103，source /apps/EDAs/syn.bash）8个字节相同共同源 any/none/cancel/nested/scopes/events/parallel/empty 的 TRACE、自检和 **865条物理位 settled 时间线**全部一致，无别名和位排除。独立预期核对双 lane 的1/2/3倍周期输出、取消后5/6/7ns的 NBA 保留；其他用例覆盖零/空控制、父进程结束、多个 fork 直接子进程等待、孙进程和同行区别、事件取消及 automatic 子任务交付。

8原始探针保存双方源码、编译/运行日志、退出码及 TRACE：cancel/defer/empty/peer/wait/join_any 六项对齐，包含 M51 当时拒绝的原始 join_any 源；escape 由 VCS 接受/native 编译拒绝，overlap 由 VCS 接受/native 编译后在运行入口明确拒绝。verify.py 区分编译边界和运行边界，原始探针只在 macOS/VCS 执行，Linux 复核保存记录，未在 Linux 重跑该组。

8模型 × 串行/时间轮/双线程 × VCD/DWF × ordered/settled 共96捕获；any 在3ns已进入 wait fork 后、cancel/scopes 在1ns挂起时，各做一次实际失败预测恢复，再加3捕获，共 **99捕获、3回滚、6类编译拒绝和2类重叠运行拒绝**。完整 ordered 逐信号事件/stdout 相同，真实双线程 partitions=2；threads8仅作emit-only分区核对。三个直接内核 kernel/wheel/compact 覆盖首完成恢复、无多余父唤醒、直接子等待、存活孙进程取消/死计时器清理、重叠拒绝和取消复用，以及 wait fork 集合挂起时的实际检查点/失败预测。

最终 macOS **49项定向 CTest** 全通过，324.11秒；ASan/UBSan parser全部语义单测、8语料各三轮清理、8个实际最终生成程序/完整 ordered 流、3种直接内核通过，含真实双线程，leak检测关闭。9份完整 CPP（8串行、1双线程）重生成字节相同，sanitizer CPP hash 与最终程序匹配。

Linux 同源构建初轮49项中48项通过，仅旧 wait fork 拒绝预期失败（835.35秒）；更新该测试并核对最终全部源文件 hash 后，**rtl_level_wait 单项复测通过**（84.89秒、退出0）。49项定向检查在这两次执行中均取得通过结果，未重复执行其余48项；9份完整 CPP、8个模型完整 ordered 逐信号流及 stdout 跨平台一致，再次核对同样 VCS 的865条位时间线。冻结1142文件，源包SHA256 `e2f1aa742d6c0000eb72072577080e00fdb6c6ae8422bdd33b7262c63bec71f3`；source-manifest.json 所列文件未改，plan1017.md和验收输出不在清单。local/linux/vcs/probes/sanitizers 保存实际代码、IR、日志/退出码及波形，不保存仿真可执行文件。

仍缺重叠动态激活、automatic 父帧逃逸、process对象、递归/完整生命周期、外部/层次/任务名 disable，以及既有完整事件区域、接口/对象/随机化/SVA/UVM和精确时序等。用户要求继续功能优先，本批未新测速、未跑全量CTest或Linux sanitizer，不称完整 SV/VCS 功能或性能对齐。

复跑：`ctest --test-dir build -R '^(rtl_fork_control|fork_control_kernel|fork_control_wheel|fork_control_compact|rtl_semantic_memory)$' --output-on-failure`；`python3 validation/m53-fork-control/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py 保存各流程。
