# 参数化类形参

M167 补齐逗号后的参数化类类型识别，例如公开 UVM 的
`function void set(int depth, uvm_pool#(string,uvm_resource#(T)) pool)`。
既有语法和特化系统负责建立实际类型，新增词法前瞻负责区分新的形参声明与前一声明的变量列表。

前瞻支持括号、方括号、花括号的配对与嵌套，跳过注释、字符串和转义标识符，
在完整类型后找到形参名才给出声明分隔符。`C#(...)::method()` 等表达式保留普通逗号。
该过程只读取 parser 当前输入，不消耗 Flex 字符、不改变行列状态，没有新增参数列表长度上限。
Flex 缓冲区换页后，按当前尚存字符数将 token 映射回输入位置；不依赖固定缓冲区大小。

类型/方向/默认实参仍由既有函数和任务语义处理。省略方向的下一形参继承前项方向；
带 ref 形参的模块函数/任务须声明 automatic。依据
[IEEE 1800-2017 §13.4、§13.5 与 Annex A](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)。
泛型实参身份、克隆、extern 原型和 ref 类型检查继续生效。

`tests/parameterized_formals` 包含八执行模型：普通/三层嵌套、默认/null、ref及const ref、
extern、package与8/129位克隆、转义名和含括号字符串、预测恢复及实际双分区。
三种后端请求结合有序/settled、VCD/同步压缩/独立writer波形；用户指定范围另验。
八拒绝用例检查不兼容的类句柄、继承ref方向、错误类型/实参数、畸形分隔符与截断输入。
完整 parser 还直接测试不同缓冲位置、66KB注释、未闭合注释/字符串和错误后的重新解析，
避免 CLI 预处理清除注释而漏测 lexer。

本批仍使用当前支持的 integral/class 类型；`C#(...)::member_type`、完整类型参数语法
和所有验证运行时能力尚未完备。未修改的公开 UVM native 首错推进到
`uvm_printer.svh:176` 的 real 形参。real 型及值运算、约束随机、IPC、virtual interface/clocking、
coverage 等仍待补齐，完整 UVM 尚不可运行。独立 gate parser 与 runtime 未修改。
