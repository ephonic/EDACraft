# foreach 的下标接收者与子数组

RTL parser 支持 `foreach (objects[s].values[key])`、多层成员链和多次下标选择。
前面的方括号解析为接收者选择，最后一组解析为循环变量列表；后者只能是标识符或省略位置。
省略维度继续支持，例如 `foreach (matrix[row][,col])`。
RTL/门级 parser 仍独立，生成 parser 保持86个 shift/reduce 冲突，没有新增 reduce/reduce 冲突。

```systemverilog
foreach (successors[s])
  foreach (successors[s].values[pred])
    total += successors[s].values[pred];
```

支持已有数组/容器与类成员的组合：固定数组、动态数组或队列中的类句柄，
整数和字符串键关联属性，固定子数组的剩余维度、参数化克隆、automatic函数/延时task。
循环变量只读、按原有索引类型绑定，break/continue 与 checkpoint/预测恢复继续生效。
省略循环变量和只读规则可参见 [Accellera foreach 提案](https://www.accellera.org/images/eda/sv-ec/att-1406/01-foreach.pdf)。

关联目标在每次 first/next 操作中重新求值。循环体修改接收者或它的下标后，
下一次 cursor 操作会作用于新的对象；带副作用的下标函数也在各次操作中执行。
此行为由本批同源 VCS 用例确认，不能把入口对象缓存到循环结束。
首轮测试曾假定只求值一次，与 VCS 失败；保留原始失败和诊断探针，修正编译器与测试预期。

用户所选层次/信号和时间范围的压缩波形随功能一起验证；VCD、同步/独立线程DWF
以及预测回滚后的完整时间线都参与对照。

本批不增加类属性底层数组类型，也没有实现类句柄键关联数组、嵌套容器等完整能力。
未修改公开 UVM 2020.3.1 的语法首错已越过 phase:1551 的 foreach，
下一处为 phase_hopper:562 的 `9200s` 时间常量；预处理字节与依赖仍完全相同。
这不是完整库通过，完整 UVM 仍不能原生编译运行。
验收见 [M175](../validation/m175-foreach-selections/README.md)。
