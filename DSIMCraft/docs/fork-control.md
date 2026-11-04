# 分支提前继续与过程收尾

M55 增加 [automatic 动态变量帧](automatic-fork.md)，join_any/join_none 不再一概拒绝 automatic 父任务；父帧可由存活分支持有。下文 M53 限制以此更新为准。

M54 已补充[静态存储分支的重叠激活](dynamic-fork.md)，下文 M53 的“一律拒绝重叠”边界由该范围更新；automatic 动态变量帧仍缺。

RTL 前端支持 `join_any`、`join_none`、`wait fork;` 和 `disable fork;` 的静态激活子集。它们可用于常见的超时竞争、等待多个并发任务收尾，以及取消后重复启动；完整动态进程生命周期尚未实现。

`join_any` 在第一个直接子进程结束时恢复父进程，其余分支继续执行；后续分支完成不重复唤醒父进程。`join_none` 让父进程继续，子进程在父进程阻塞或结束后才开始。空 fork 不等待。`wait fork` 等待当前进程所有尚未完成的直接子进程，包含来自多个 fork 位置的分支；直接子进程结束后仍存活的孙进程不在它的等待范围内。

`disable fork` 取消当前进程的全部后代，包括父进程已经结束的孙进程；当前进程及它的同行分支继续执行。从一个子分支调用 disable fork 不会取消其他同行分支。已经发起的 NBA、延迟 NBA、内部事件 NBA 和独立连续驱动继续交付。取消复用命名块 disable 的控制代际，旧 Active/Inactive、定时器和事件等待不会唤醒下一轮分支。

每个 fork 位置仍使用编译时注册的进程槽。只有前一轮所有后代完成或被取消后，才可重新启动该位置；有重叠激活时，运行入口明确报 `overlapping fork activations are not supported yet`。automatic 父任务/块中的非空 join_any/join_none 目前保守拒绝，提示需要 dynamic activation frames；分支调用普通阻塞的 automatic 子任务已支持。递归、process 对象、动态分配帧和任意脱离生命周期仍缺。

分支类型、首次恢复状态、直接子进程计数及 wait fork 等待集合随 Sim 检查点保存。现有父子控制边保证整组留在同一分区，独立实例继续并行。执行仍为生成的 C++，没有轮询或运行时 AST 解释。RTL grammar 新增两个 fork 控制语句，复用可克隆/清理的动作节点；门级 parser、lexer 不变。

本轮对照、真实失败预测回滚、串行/时间轮/双分区及 sanitizer 记录见 [M53](../validation/m53-fork-control/README.md)。复跑：`ctest --test-dir build -R '^(rtl_fork_control|fork_control_kernel|fork_control_wheel|fork_control_compact|rtl_semantic_memory)$' --output-on-failure`。
