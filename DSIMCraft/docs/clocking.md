# Clocking block

支持命名 clocking、默认 clocking、采样输入、带常量 skew 的输出以及按时钟周期等待。RTL parser 为 clocking 保留独立节点和成员绑定，门级网表 parser 不变。

```systemverilog
clocking cb @(posedge clk);
  default input #1step output #1ns;
  input response;
  output request;
endclocking
default clocking cb;

initial begin
  ##2;
  cb.request <= 1;
  @(cb);
  $display("response=%0d", cb.response);
end
```

输入默认使用 `#1step`，读取当前时隙开始之前的值；显式 `#0` 在设计的 NBA 更新后采样。等待 `@(cb)` 恢复时可以读取本次样本。支持 input/output 别名、层次 `@(bus.cb)`、多个 interface 实例，以及单维 packed 输入的位选和部分选择（含升序范围）。`##N` 使用词法作用域内的默认 clocking，当前 N 须为正整数常量。

输出使用 `<=`，右侧在执行语句时求值并保存。时钟事件之后的零 skew 驱动进入 Re-NBA，正 skew 按时间推迟并保留该区域语义；时钟之外发出的驱动等到下一次 clocking 事件。采样、等待和待驱动值支持预测回滚及指令预算续跑。

当前不支持正输入 skew、modport clocking、部分输出驱动、net 输出、动态周期数、复合 clocking 事件和同一时隙多个 clocking 边沿。含 clocking 的多线程请求退回串行执行。本功能不代表完整 SVA 或 UVM 支持；同源 VCS 对照与发布收据见 [M191](../validation/m191-clocking/README.md)。
