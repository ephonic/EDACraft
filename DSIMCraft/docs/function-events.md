# 自动函数事件表达式

M47 支持事件源和 iff 条件中的无外部副作用 automatic 函数，包括嵌套调用、函数局部数组、signed/宽字/四态返回值，以及 automatic task 内的等待。复用已有函数 C++ 代码生成和表达式事件回调，运行时不解释 AST，不增加新的内核结构。RTL 与紧凑门级 parser 继续独立，本批只增强 RTL 编译器的安全检查与依赖分析。

```systemverilog
function automatic logic odd(input logic [7:0] value);
  return ^value;
endfunction
always @(odd(data)) changes++;
always @(posedge odd(data) iff allowed(enable)) edges++;
```

事件源只订阅函数实参的读取依赖。函数体读取的全局变量参与分区依赖，但单独变化不会唤醒事件；无参数函数因此没有信号唤醒源。源依赖变化时重新调用函数并比较结果，结果未变就继续等待。含函数调用的源表达式在进入等待时重新取样，包括调用外包一层运算的情况；这些规则通过真实 VCS 原始探针核对。

iff 中的函数只在源事件满足且等待仍有效时求值；条件本身及函数体全局读取都不增加源事件订阅。条件/函数体依赖与共享函数存储加入分区图，避免独立内核跨域访问。已有等待缓存、进程状态和信号快照负责失败预测恢复；没有新增预测器。

允许写入当前 automatic 函数及其 automatic 被调用函数的私有参数、返回槽和局部变量。编译期传递安全标志、读写集合并检查调用链；外部写入、output/inout 复制、事件/诊断副作用、参数中的自增等明确拒绝。static 函数即使看似纯函数也暂不接受，避免持久局部/返回槽状态破坏事件求值。递归和 void 值仍拒绝，递归可能由现有 parser 语义阶段报告通用错误。

这不是全部用户函数事件支持。真实 VCS 接受的 static 函数和写全局变量的函数仍是明确差距；M48 已接通[静态命名事件 iff](qualified-named-events.md)；动态进程、fork/join、完整事件区域、SVA/UVM 等仍未实现。

验收入口为 `rtl_function_events`。三模型比较串行、时间轮、双线程的 ordered/settled VCD/DWF；独立计算值变化/边沿及任务输出时间线，验证两次实际失败预测回滚、两个真实分区和九类拒绝。真实 VCS 同源逐位 settled 时间线、六个原始探针、跨平台及 sanitizer 记录见 [M47](../validation/m47-function-events/README.md)。本批没有新速度测量。
