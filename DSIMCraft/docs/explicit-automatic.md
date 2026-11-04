# 显式 automatic 局部变量

M57 支持 begin/fork、静态与 automatic task/function 局部声明中的显式 `automatic`，包括 integer、现有内建整数/logic/bit、命名整数/enum/packed 类型以及固定局部数组。RTL parser 在声明节点保存限定，并在模块参数化克隆中保留；门级 parser 不受影响。

```systemverilog
integer i=0,q=0;
initial begin
  for(i=1;i<=4;i++)fork
    automatic integer saved=i;
    begin #1; q+=saved; end
  join_none
  wait fork; // q=10
end
```

fork 的声明在父进程进入时初始化，先于 deferred 子进程执行。每次进入分配新的 saved，分支继承并共享这次块的存储；父块/任务退出后存活分支继续持有。`begin ... automatic integer saved=i; ... end` 位于分支内部时在该分支启动时初始化，不能据此推断同样捕获了父进程每一轮的值。

同一个块可混合默认静态与显式自动声明，只有自动变量进入帧。静态任务的形参和普通局部继续共享，显式自动局部按调用隔离，即使没有 fork 也使用过程激活帧。函数保持现有零时间非递归执行，自动局部在每次入口重置，默认静态状态保留。四态/两态默认值分别为 X/0，显式初始化按声明顺序执行。现有 integer 同声明列表的绑定范围不变，其他类型前序声明项引用仍有限制。

变量/数组字、部分选择、订阅绑定、PC深度清理和检查点复用 M55 机制。return/break/continue/命名取消离开相应帧；失败预测恢复私有值与共享关系。VCD/DWF 只导出静态变量，混合块中的自动变量和物理私有槽不导出。含自动变量的事件表达式入场重新取样，避免声明初始化排入的旧求值误唤醒。

范围：仅过程局部变量的 automatic 限定；显式 static 覆盖由 [M58](explicit-static.md) 补齐；仍不支持 module/for 头部 lifetime 语法、递归、ref 和动态容器。automatic 局部 event、NBA 写 automatic 变量仍明确拒绝。static/default-static 函数作为事件源的 M47 限制及 M55 逃逸局部直接事件等待差异保留。

验证入口：`ctest --test-dir build -R '^rtl_explicit_automatic$' --output-on-failure`。同源 VCS、回滚、sanitizer 和跨平台实际范围见 [M57](../validation/m57-explicit-automatic/README.md)。没有新的性能测量。
