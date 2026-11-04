# M52 命名块退出与并发取消

接通词法包围的 `disable name`，目标可为命名 begin 或 fork；同进程跳出块，从并发分支退出包含块则取消所有后代并恢复目标块后的语句。支持循环重启、函数局部退出、automatic task，以及 `end : name` / `join : name` 关闭标签和一致性诊断。详见 [功能范围](../../docs/named-disable.md)。

真实 VCS 发现同一 automatic task 内的命名块是共享词法目标：disable 必须退出所有活跃调用。实现按模块/generate 作用域、task 名和块遍历编号建立稳定身份，避免 parser 调用体克隆造成身份分裂；各调用槽的 PC 范围判断活跃状态。共同 scopes 语料并发 work(1)/work(3) 时在1ns一起退出，输出12/4；5ns才开始的 work(2) 正常到7ns输出13；已经返回的旧调用也不重新恢复。控制身份参与分区依赖。

进程取消使用独立 control epoch，旧 Active/Inactive 项不能清除新激活 queued 状态，旧定时器不唤醒新分支，命名/信号/表达式等待沿用等待代际。失效普通计时器与失效惯性驱动交替清理，避免只剩死事件仍推进时间。已经发起的普通/延迟/内部事件 NBA 与独立连续驱动交付保留。Sim 快照复制控制字段、PC、等待、队列和调用存储，DWF/VCD 回滚复用已有事务。只有需要过程取消的模型启用 DSIM_PROCESS_CONTROL_ENABLED，未增加运行时 AST 解释或轮询。

RTL grammar 新增关闭标签，Bison 生成文件同步，47项 shift/reduce 冲突未增加。函数含 disable 暴露旧 parser 克隆时推入空 `_break_stmt` 的崩溃，本批修正 replacement/dot 遍历空节点；参数模块两实例、函数/任务、命名 fork、坏标签恢复及三轮清理纳入单测。lexer 和门级 parser 未改。

实际 VCS W-2024.09（10.131.254.103，source /apps/EDAs/syn.bash）8个共同源 lexical/nested/outer/nba/labels/scopes/events/parallel 的 TRACE、自检和 **866条物理位 settled 时间线**全部一致，无别名或位排除。6个原始探针保存源码、编译/运行日志、退出码：5项接受及 TRACE 对齐；external 由 VCS 接受、native 明确拒绝，保留为缺口。原始探针只在 macOS/VCS 执行，Linux 复核保存记录，未在 Linux 重跑这组探针。

8模型 × 串行/时间轮/双线程 × VCD/DWF × ordered/settled 共96捕获；nested/scopes/nba 在1ns挂起时各做一次实际失败预测恢复，再加3捕获，共 **99捕获、3回滚、8类拒绝**。完整 ordered 逐信号事件/stdout 一致，实际双线程 partitions=2；threads8仅作emit-only分区检查。独立数学检查核对双 lane 更新时刻及取消后 NBA 在3/5ns的交付。三个直接内核 kernel/wheel/compact 覆盖旧 Active/Inactive/信号等待/定时器隔离、重新启动、检查点/回滚、独立 NBA/驱动保留和无效事件不推进时间。

macOS 最终重建头文件消费者后 **45项定向 CTest** 全通过，352.61秒。ASan/UBSan parser全部语义单测、8语料各三轮清理、8个实际最终生成程序/完整 ordered 流和3个直接内核通过，含实际双线程；leak检测关闭。9份实际完整 CPP（8串行、1双线程）重新生成字节一致，8份 sanitizer CPP hash 对应最终程序。

Linux 同源干净构建 **45项定向 CTest** 全通过，551.61秒、退出0；9份完整 CPP、8模型完整 ordered 逐信号事件及 stdout 跨平台一致，再次核对同样 VCS 的866条位时间线。冻结1117文件，源包SHA256 `d32eeb2b51f7a51b5f96980bb97ee7ece05641f5e8e8590e439d72485e299116`；source-manifest.json 所列文件未改，plan1017.md及验收输出不在清单。local/linux/vcs/probes/sanitizers 保存实际生成代码、IR、源码、日志/退出码和波形，不保存仿真可执行文件。

首轮发现函数 disable 的旧 parser 空节点崩溃、坏标签异常未走错误恢复，以及 native 将命名块误作每次 task 调用私有目标；修正后才冻结源码并重新验收。VCS 零时间 finish 早于 dump 初始化的 lexical 语料增加1ns观察延迟，双方共同源同步，不改功能结果。

仍缺外部/层次/任务名 disable、disable/wait fork、join_any/join_none 执行、process对象和动态/脱离/递归生命周期，以及既有完整事件区域、接口/对象/随机化/SVA/UVM及精确时序等。无完整 SV/VCS 支持或性能对齐声明；未跑全量CTest、Linux sanitizer或新性能测试。

复跑：`ctest --test-dir build -R '^(rtl_named_disable|named_disable_kernel|named_disable_wheel|named_disable_compact|rtl_semantic_memory)$' --output-on-failure`；`python3 validation/m52-named-disable/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py 保存各流程。
