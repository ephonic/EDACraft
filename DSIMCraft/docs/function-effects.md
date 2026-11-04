# 函数输出形参与副作用

模块/generate 词法静态函数支持 `input/output/inout` 形参、阻塞写外部变量、`function void`、函数语句调用以及 `void'(f(...));`。函数和任务均支持空 ANSI 形参表。支持已有整数、enum、typedef 和 packed 聚合类型；不是完整 SystemVerilog 子程序实现。

```systemverilog
integer total=0, copied, result;
function integer add(input integer x, output integer y);
  begin total+=x; y=total; return total; end
endfunction
initial begin
  result=add(3,copied);
  void'(add(4,copied));
end
```

input/inout 在入口取样，output 不读取实参值。单个嵌套函数或条件表达式作为实参时保留整条表达式和副作用。函数体结束或提前 return 后，将 output/inout 按声明顺序复制到实际目标；目标动态下标在返回时求值。例如函数体把 `i` 改为 2，实际输出目标 `a[i++]` 随后写入 `a[2]` 并令 i 变为 3。返回值在复制前保存，实参按形参宽度、符号及两态属性转换；enum 保持名义类型检查。静态输出形参未赋值时保留已有存储值。

函数体外部读取进入 `always_comb/always_latch` 隐式敏感集合，传统 `@*` 只追踪实参表达式和复制目标地址的读取。函数写入参与单写进程检查、共享状态分区和回滚；共享状态使进程合并，独立实例仍可分区执行。外部部分写入也记录依赖。延迟 NBA 在调度时执行函数并保存结果，提交时不重复执行函数；阻塞内部 delay 先执行函数再等待。

函数继续编译为原生 C++ 中的固定指令控制流，不在运行时遍历 AST。void 函数没有运行时返回信号，值上下文和 `$bits/$dimensions` 等查询拒绝 void。非 void 语句调用给出丢弃返回值警告，显式 void 丢弃调用不告警。

按 IEEE 1800-2017 13.4，具有 output/inout 形参的函数禁止用于连续赋值、模块实参等非过程表达式。继续拒绝 automatic、递归、ref、数组形参、完整并发激活、层次调用及函数中的时间控制、NBA、任务调用和系统任务。`void'(...)` 当前只接收函数调用；保留已有非 void `return;` 扩展。仍不支持完整常量函数求值。

验收命令：`ctest --test-dir build -R '^rtl_function_effects$' --output-on-failure`；实际 VCS 同源对照和已知差异见 [M29](../validation/m29-function-effects/README.md)。本批没有新的速度测量。

后续 [M30](call-arguments.md) 已接通默认/命名/空实参，并修正 always 入口事件等待与声明初始化的顺序；原始启动差异证据保留。该修正不代表完整事件区兼容。
