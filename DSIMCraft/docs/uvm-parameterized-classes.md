# 参数化类

RTL 前端对每个类声明按参数绑定结果建立规范特化。每个特化包含真实的属性、构造器与方法，生成原生仿真代码；并不跳过方法体或在编译器中解释对象行为。门级 parser 保持独立。

支持带默认值或必填的 `type` 参数、integral 数值参数、按位置/按名传参、空命名实参采用默认值、依赖前序参数的默认值，以及嵌套类类型实参。类模板的默认值在声明作用域求值，显式实参在调用作用域求值。规范键保留 integral 类型、符号、scalar/vector、各 packed 维度、enum/aggregate/class 身份及完整数值位。

```systemverilog
class Box #(type T=int, parameter int W=8);
  T value;
  logic [W-1:0] lane;
  function new(T v); value=v; lane='1; endfunction
  function T get(); return value; endfunction
endclass
typedef Box#(logic[64:0],65) Wide;
Wide a;
Box#(.W(65),.T(logic[64:0])) b; // 与 Wide 是同一特化
```

支持参数化基类、继承与虚分派、直接声明与 typedef、函数返回及值/ref 形参中的显式类类型应用、递归句柄和模块克隆后的独立模板。类体中裸模板名表示默认特化；要表示当前特化须显式写 `C#(T)`。native 前端拒绝对普通类和 typedef 别名重新应用参数。VCS 对普通类的多余覆盖等部分写法会警告后忽略；这些接受性差异仍保留。读取 enum 类型的类属性会保留其身份，packed select 则取得普通位向量。

本批不构成完整 UVM 支持。尚待补充的形式包括连续省略类型的参数声明、部分空位置实参、带参数的静态/外部类作用域方法、string 参数，以及编译单元类和类属性容器等后续依赖。当前 integral 原子类型的既有四态语义边界也未在本批扩展。完整 Accellera UVM 仍不能编译/运行。

压缩波形仍使用独立接收线程；接口和用户指定的层次、深度、信号过滤、时间窗口见[波形接口](waveform-format.md)。验收结果在 [M156](../validation/m156-parameterized-classes/README.md) 更新。

M186：前向声明的参数化类允许在完整类定义之前建立 typedef 特化。此时先规范化类型身份，将类体放入既有延迟语义队列，等外围声明完成后展开；同参数的早期/后期别名保持同一类型，模块克隆各自绑定自己的参数和类。缺失或非类基类、循环继承、必填参数缺失及不兼容句柄仍拒绝。parser clear 同时清除失败分析残留的待处理节点。

原版 UVM 2020.3.1 已越过 `uvm_resource_db` 的继承错误，新的首个阻塞是 `uvm_report` 中默认实参引用前序形参 `severity`；本批未补此能力，也未完成整个 UVM 的编译或运行。证据见 [M186](../validation/m186-forward-specializations/README.md)。
