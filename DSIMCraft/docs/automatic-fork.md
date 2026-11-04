# fork 中的 automatic 变量帧

M58 支持 [显式 static 局部声明](explicit-static.md)：automatic 子程序跨调用共享持久变量、数组和静态 event，接通一次初始化、NBA、波形、分区和回滚。

M57 支持 [显式 automatic 局部声明](explicit-automatic.md)：默认静态任务/函数和过程块可指定自动局部变量；混合静态存储、fork 捕获及生命周期范围以新文档为准。

M55 接通 automatic task 与其过程块在重叠 fork 激活中的动态存储。形参、局部标量、packed 值和固定局部数组按调用分配；fork 子进程继承同一次父调用的存储。兄弟分支共享父变量，后续调用使用新帧。join_none/join_any 后任务可以返回，存活分支继续持有父帧。

```systemverilog
task automatic launch(input integer n);
  integer saved=n;
  fork begin #2; q+=saved; end join_none
  saved+=10;
endtask
// 同一个调用点连续 launch(1)..launch(4)，随后 wait fork：q 增加 50。
```

任务实参先在调用者上下文取样，再进入新帧写入 input/inout，按顺序初始化其他局部变量。output/inout 在返回复制完成后离开任务帧。每条编译 PC 保存所需作用域深度，return、break、continue 和词法 disable 跳转会清理退出的帧。fork 结束/取消释放自己的引用，保留仍存活后代的引用。

变量映射不可变，值与订阅保存在 Sim，检查点复制值而保留帧共享关系。局部事件控制在 arm 时绑定实际变量字；表达式回调在等待进程的帧上下文求值。失效等待通过代际隔离。存储池只复用没有存活引用的同布局帧；检查点持有的帧不会提前复用。private 存储不导出为静态 VCD/DWF 信号。模块/门级连接仍为编译时结构，未合并 RTL 和门级 parser。

当前仍不支持递归、process 对象、automatic 局部 event、NBA 写 automatic 变量、ref/复杂动态容器。foreach 隐式索引的动态帧已由 M56 接通，见 [foreach fork](foreach-fork.md)。automatic function 保持原有零时间编译调用槽；本批增加的是可挂起任务/过程块帧。

真实 VCS W-2024.09 的一个已保存差异：父任务已返回时，直接 `@(posedge local_clock)` 没有唤醒，而表达式事件与父任务仍存活时的直接事件能唤醒。dsim 在原始复现中会唤醒；该复现单独列为差异，不计为 VCS 对齐通过。证据见 [M55](../validation/m55-automatic-fork/README.md)。

验证入口：`ctest --test-dir build -R '^(rtl_automatic_fork|automatic_fork_(kernel|wheel|compact))$' --output-on-failure`。
