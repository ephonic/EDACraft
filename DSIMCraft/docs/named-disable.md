# 命名块退出与并发取消

RTL 前端支持从词法内部执行 `disable name;`，目标为包围该语句的命名 `begin : name … end` 或 `fork : name … join`。退出顺序块时跳到块后；从 fork 分支退出命名 fork 或外层命名 begin 时，取消块内所有分支及后代，恢复到目标块后的语句。支持循环重复启动、automatic task 和零时间函数中的命名块退出。

同一 task 内的命名块是一个词法目标。对它执行 disable 会退出该块所有活跃调用，包括 automatic task；未开始和已返回的调用不受影响。编译期为各静态调用槽记录目标身份及 PC 范围，运行时据此选择活跃调用，相关控制边参与分区。函数不挂起，其 disable 编译为局部 PC 跳转。暂不支持递归或脱离父进程的动态调用生命周期。

取消使旧 Active、Inactive、延迟和事件等待失效，并重置被取消分支的执行位置。重复启动不会被旧定时事件误唤醒；只剩已取消事件时不会推进仿真时间。已经发起的 NBA、延迟 NBA、内部事件 NBA 以及独立连续驱动交付继续执行。取消状态、PC、等待代际和队列随 Sim 检查点保存与恢复，波形继续使用既有事务机制。

`DSIM_PROCESS_CONTROL_ENABLED` 只对需要过程取消的模型启用，普通模型不增加取消字段或调度检查。分支仍为编译时注册的静态进程，未增加轮询或运行时 AST 解释。RTL grammar 支持 `end : name` 和 `join : name`，要求与起始标签一致；绑定、克隆和错误恢复参与 parser 清理单测。门级 parser 保持独立。

当前只接受词法包围的命名块；从其他 initial/task 访问目标、层次目标、任务名 disable 均明确拒绝。`disable/wait fork` 与 `join_any/join_none` 的静态子集见 [M53](fork-control.md)；重叠动态激活、automatic 父帧逃逸、process 对象和完整 SV 事件区域/SVA/UVM 仍缺。并发分支同刻写共享变量的竞争不承诺与 VCS 任意顺序相同。

复跑：`ctest --test-dir build -R '^(rtl_named_disable|named_disable_kernel|named_disable_wheel|named_disable_compact|rtl_semantic_memory)$' --output-on-failure`。实际 VCS 对照与验证记录见 [M52](../validation/m52-named-disable/README.md)。
