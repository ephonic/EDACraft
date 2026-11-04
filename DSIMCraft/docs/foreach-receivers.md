# foreach 的 this / super 接收者

`foreach (this.values[key])` 和 `foreach (super.values[key])` 现在使用与普通成员目标相同的
数组/类成员解析链路。目标路径可以有多级成员，保留继承权限、实际对象和索引类型。
整数/字符串键关联属性沿已有运行时遍历，函数内累加、task 延时、continue 和预测恢复均可使用。
RTL 与门级 parser 保持独立，生成 parser 的冲突数仍为86。

三个执行模型涵盖继承的 protected 数组、字符串索引自动推导、带延时的自动 task 及
对象内容在预测回滚后的遍历，VCD/同步与异步 DWF、用户所选信号和时间范围共56次捕获。
类外 this/super 和无基类的 super 仍拒绝。

M175 已补[数组元素接收者和子数组](foreach-selections.md)，如 `foreach (objects[i].values[key])`。
本批没有扩大类属性底层支持的数组类型，也没有实现类句柄键关联数组。
M173 的公开 UVM 语法首错 phase:1551 已在 M175 越过；最新首错见上述文档，完整 UVM 仍未编译运行。
