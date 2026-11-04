# 类外 function/task 定义

M165 为独立 RTL parser 增加模块/包中的 class 内 `extern` 原型及同一作用域内、类声明之后的 `Class::method` 定义。类外函数体在实例和参数化类克隆前移回原方法，调用继续使用原型的访问权限、virtual/static 属性、automatic 生命周期及默认实参。构造器 `Class::new`、void/命名/宽 packed/数组返回、ANSI 和非 ANSI 形参以及 `endfunction : name` / `endtask : name` 均走原有执行路径；没有运行时字符串查找。

```systemverilog
class Counter;
  local int value;
  extern function new(int n=0);
  extern virtual function int next(int delta=1);
endclass
function Counter::new(int n); value=n; endfunction:new
function int Counter::next(int delta); value+=delta; return value; endfunction:next
```

定义中的默认实参可以省略；重复提供时须与原型的表达式语法一致。绑定检查形参个数、名称、方向、ref/const ref、类型身份、符号性、packed/unpacked 形状及返回类型。形参头在完成的类作用域中解析；返回类型及其 packed 范围按类外词法作用域解析，类内类型/常量须写 C::T/C::W。该前缀在参数化类及其类外定义中指当前特化，不能绑定到默认特化。原型保留声明位置的类型绑定，因此后续 typedef 遮蔽不能悄悄改变原型。普通类的头部即使方法未被调用也检查；泛型类按实际特化检查。

缺失/重复实现、没有 extern 原型、先定义后声明类、不同作用域、function/task 不一致及不兼容的签名会拒绝。类限定符写在原型；类外定义不可重复 static/virtual/local/protected，且不可指定 static 生命周期。构造器不能显式指定返回类型。

范围仍有限：方法体沿用按调用绑定的机制，未调用体内错误可能延后发现；编译单元 class、嵌套类、约束随机、更多类容器、完整 SystemVerilog 及完整 UVM 尚未完成。原始公开 UVM 的解析越过 extern 后停在连续类型参数的省略 type 写法；语法首错推进不等于语义或运行通过。RTL/门级 parser 继续分开，本批不改变运行时调度或声称提速。

测试见 [extern_methods](../tests/extern_methods)，证据见 [M165](../validation/m165-extern-methods/README.md)。声明与定义规则依据 IEEE 1800-2017 §8.24，见[标准文本](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)。
