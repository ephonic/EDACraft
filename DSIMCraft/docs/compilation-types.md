# 编译单元级类与 typedef

一次 dsim 调用中的源文件、filelist 和 include 按顺序组成一个编译单元。设计单元外可声明类和普通 typedef；继承、虚派发、参数化类、类类型别名、enum、packed aggregate 和数组 typedef 沿用已有类型系统。

```systemverilog
typedef bit[7:0] Word;
class Counter;
  static int count=0;
  Word value;
  function new(Word n);value=n;count++;endfunction
endclass
module lane;
  Counter c;
  initial c=new(7);
endmodule
module top;
  lane a(),b();
  initial begin #1;$display("%0d",Counter::count);end // 2
endmodule
```

每个声明位置拥有独立可见视图，导入和此前定义的类型保持原始身份，后面的声明不追溯进入前面的模块。文件级类不随模块实例克隆，同一参数化特化的静态字段和方法上下文也共享；不同对象的实例字段仍独立。模块内同名类可以遮蔽外层类。包不能捕获编译单元类型，层次实例引用也不把文件级类型当作实例成员。

AST 由私有的编译单元声明 owner 持有，作用域视图仅借用规范类型符号，不生成可导入的用户 package。编译时先建立这些共享声明的词法存储位置，再收集使用它们的模块；没有文件级类型声明的设计保持原有收集顺序。静态字段、堆对象和队列继续使用原有调度、checkpoint、预测回滚和波形链路。

当前不支持编译单元级 `typedef class` 前向声明、类外 extern 定义、变量/task/function、显式 `$unit::`，以及独立编译/链接；类内部仍受既有 OOP、容器和随机化能力的限制。`chandle` 尚未接通，不能据此宣称完整 SystemVerilog 或 UVM 支持。

未修改公开 UVM 2020.3.1 smoke 已越过编译单元 `class` 的语法阻塞，当前首个语义错误为 `unknown integral type chandle`。整库语义分析、展开与运行尚未完成。

复现及验证边界见 [M183](../validation/m183-compilation-types/README.md)。
