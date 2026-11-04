# 字符串转换与常量参数

RTL parser 与编译执行链路支持 `string'(expr)` 和 `typedef string` 的类型转换。
整数按完整宽度转换为字节，不足八位的高位补零，X/Z 位转换为零，移除所有零字节。
字符串操作数保持原值；实数、类句柄和数组不能用这个转换进入字符串域。

显式 string 参数及其类型别名支持默认值、命名覆盖、包内声明和实例独立特化；
未指定类型的参数可从 string 转换表达式推导类型。常量字符串比较采用字典序，
拼接与条件表达式保留字符串类别，`$bits` 在运行时返回实际字符数乘八，包括空串的零；
动态字符串的 `$bits` 不能用于常量参数。未知条件下，相同字符串分支保留该字符串，
不同字符串分支返回空串。
字符串常量的复制、重新解析与 parser 清理会保留或复位相应类型标志。

```systemverilog
typedef string text_t;
localparam text_t LABEL = string'(32'h410042); // "AB"
localparam JOINED = {LABEL, ":suffix"};
// Dynamic string $bits is a runtime query.
initial $display("bits=%0d", $bits(JOINED));   // 72
```

同时支持 `function unsigned f(...)` 的隐式一位无符号返回类型，
以及 `function unsigned [8:0] f(...)` 的显式范围和匹配的 extern 类方法定义。

`tests/string_casts/regression.py` 执行五个模型，检查三种调度请求、
VCD/同步与异步压缩 DWF、预测回滚和用户选定的信号及时间范围。
波形检查针对数值观测信号，当前格式不记录动态字符串内容。
请求双线程不表示每个测试都实际分为两个执行分区。

字符串到整数的显式转换、动态字符串复制表达式及字符串数组仍有缺口。
后续数组定位功能见 [数组定位方法](array-locators.md)；原始公开 UVM 仍有编译阻塞。
这些增量不代表完整 UVM 或全部 SystemVerilog 已支持。
