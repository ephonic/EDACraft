# 普通层次变量写入

RTL 编译支持向已经 elaboration 的普通模块实例内变量写值：

```systemverilog
initial begin
  dut.words[0] = 32'h12345678;
  dut.words[index++][15:8] <= #2 8'hff;
  dut.status[3:0] += 4'd1;
end
```

层次目标解析到实例自己的信号/内存存储；复用现有 packed/未打包下标、宽四态、调度依赖和 NBA 路径。下标副作用、延迟 NBA 地址冻结及 ref 变量别名规则不变。普通 net 和 parameter 不能作为过程赋值目标，interface/modport 输入权限仍生效。层次未打包数组整体赋值、动态容器 ref 和层次事件仍有限制。

独立空语句 `;` 及带属性的空语句现在也可出现在顺序块、函数/task 和 fork 语句列表中，与 if/loop 分支已有的空语句使用同一 AST。

回归包括七份原始问题输入/25470 个完整观测及通用实例、选择、事务、并行与压缩波形用例；结果见 [M157](../validation/m157-reported-cases/README.md)。这不是完整 UVM 或全部层次语言能力声明。
