# 函数、任务与构造器结束标签

RTL parser 支持 `endfunction : name`、`endtask : name` 和构造器 `endfunction : new`。标签必须与声明名称精确匹配，区分大小写并支持转义标识符。标签属于声明的校验信息，不产生新作用域，不改变静态/automatic 生命周期、虚拟派发或仿真调度。ANSI/非 ANSI 端口、隐式/packed/命名返回类型、显式生命周期、包、static/virtual 方法及参数化类均沿同一校验路径。门级 parser 保持独立。

不匹配、缺少标识符的标签是编译错误，不输出部分生成程序。重复“错误源→合法源”解析验证 parser 清理和参数化克隆；四个执行模型覆盖多种函数/任务声明分支、包/类派发、延时任务、真正两个并行分区，以及预测回滚和用户指定时间/信号范围的异步波形。去掉结束标签但保持行号后，生成代码应完全相同。

未修改的公开 Accellera UVM 2020.3.1 可越过 `uvm_misc.svh:377` 的结束标签，下一处语法错误为 `:611` 的 `typedef TYPE types_t[$]`。完整 UVM 仍不能原生编译执行。该队列别名需要保留 unpacked shape，并贯穿类特化、存储、实参和返回值，不能将只通过语法当成功能完成。原 REPORT-GAP/GAP2 中约束随机、mailbox/semaphore、clocking、覆盖率/DPI 等目标继续。
