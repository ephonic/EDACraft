# 并发过程 fork/join

RTL 前端支持 `fork statement … statement join`。每条直接子语句是一个并发分支；父进程到达 fork 后启动分支，等待全部完成，再执行 join 后的语句。分支中的 begin/end 保持顺序执行，可以使用已有 delay、显式事件、iff、命名事件、wait、循环、任务和非阻塞赋值。

支持空块、单分支、嵌套、命名 `fork : name`、块内声明、重复执行和 automatic task。块声明在父进程启动分支前建立；automatic 任务的存储保持到所有分支完成，来自不同并发分支的任务调用使用不同调用槽。子进程之间不得通过 break/continue/return 跳出 fork；子进程内部自己的循环及调用的任务仍可使用相应控制语句。

每个分支编译成固定 PC 的独立进程，编译期建立父子组，运行时仅启动已注册进程并计数完成。子进程在到达 fork 前不执行；最后一个分支结束后把父进程放回 Active 队列，所以 join 不等待尚未交付的 NBA。没有定时轮询或运行中注册拓扑。父子控制边参与分区，同组必须位于同一内核，互不依赖的模块仍可并行。

`DSIM_FORK_JOIN_ENABLED` 按模型启用。Sim 检查点保存完成位、剩余分支数、队列、各进程 PC 和现有等待状态；失败预测恢复到同一父子等待状态。现有四态值、DWF/VCD 波形、时间轮、并行机制继续复用。RTL parser 保存独立的块类型标记并参与模块克隆/绑定/清理；门级专用 parser 不变。

`join_any/join_none`、`disable fork` 和 `wait fork` 的静态激活子集已由 M53 接通，详见[分支提前继续与过程收尾](fork-control.md)。尚缺重叠动态激活、automatic 父帧逃逸和 process 对象。函数和 always_comb/always_latch/always_ff 中的 fork 明确拒绝。共享变量同刻写入的竞争不承诺与 VCS 任意调度顺序一致。

测试：`ctest --test-dir build -R '^(rtl_fork_join|fork_join_kernel|fork_join_wheel|fork_join_compact)$' --output-on-failure`。实际 VCS、逐位 settled 时间线、完整 ordered 流、挂起检查点/失败预测、双分区与 sanitizer 证据见 [M51](../validation/m51-fork-join/README.md)。不以小型功能测试声明性能或全部 SV/VCS 对齐。

M52 已补充 `join : name` / `end : name` 关闭标签及词法命名块 disable，详见[命名块退出与并发取消](named-disable.md)。
