# 函数终止与暂停控制

M226 支持从普通函数、类方法、虚方法、递归调用和构造器调用 `$finish`。
终止越过整条调用链，跳过后续赋值、return 和 output 复制；ref 已写入的状态保留，
自动帧和引用绑定通过原有 RAII 清理。参数仍限省略或常量 0、1、2；其他部分
VCS 已接受的参数形态尚未对齐。

正常仿真期间终止后执行 final；声明初始化阶段退出则跳过后续初始化、initial
和 final。已进入 final 的 `$finish` 是空操作，该块继续执行，包括 final 调用的函数。
final 的调度控制限制仍保留。

`$stop` 暂停当前执行栈。原生程序从标准输入接受 run（或 continue）恢复，
quit（或 exit）退出。正常仿真期间 quit 执行 final，输入结束退出则不执行 final。
初始化阶段退出不执行 final。在 final 中 `$stop` 仍暂停，恢复后继续该块。
这里只提供基本执行控制，不是完整 VCS UCLI 调试器。

暂停输入属于外部 I/O，预测路径在读取前触发屏障，恢复 checkpoint 后在提交路径
读取，避免重复消费命令。终止前的写入、final 状态沿用已有快照恢复。
含这类终止/暂停的设计目前保守使用单一调度内核，确保初始化和终止边界一致；
已有普通过程级 finish 和双分区路径保留。本轮没有新性能结论。

未修改 Accellera UVM 2020.3.1 越过 uvm_root.svh:183，下一实际阻塞是
uvm_resource_pool.svh:178 的关联数组函数实参。完整 UVM 仍未生成原生模型或
跑通 run_test，process::await 等后续缺口仍在。
