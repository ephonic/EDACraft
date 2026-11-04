# 包与子程序生命周期

支持 `package automatic p;`、`package static p;` 和默认静态的 `package p;`。生命周期限定只决定该包内未限定 task/function 的默认生命周期，包变量仍为唯一共享静态存储。显式 `task static` / `function static` 或 `automatic` 覆盖包默认值；显式 static 同样适用于现有模块/interface 子程序声明路径。

```systemverilog
package automatic p;
  integer shared = 0;
  function integer fresh(input integer x);
    integer n = 3;
    n += x; shared++; return n;
  endfunction
  function static integer kept(input integer x);
    integer n = 3;
    n += x; return n;
  endfunction
endpackage
```

连续两次 `p::fresh(2)` 都返回 5，而 `p::kept(2)` 依次返回 5、7；`shared` 最终为 2。automatic task 可重叠挂起，局部初始化读取本次实参，每次调用保存独立局部状态。static 局部按原有规则初始化一次。默认值在包结束及 parser 重置时清除，不影响后续包、模块或重新解析。

沿用现有子程序类型/参数/延时能力和限制：NBA 不可写 automatic 存储，ref 子程序须为 automatic，函数须为零时间。M146 另外支持 `module/interface automatic/static` 头部，见 [设计单元生命周期](unit-lifetimes.md)。编译单元导入、class、virtual interface 和完整 clocking/SVA 仍有缺口。

同时将 71 个尚无语法实现的 SystemVerilog 关键字保留，包括 `before`、`soft`、`class`、`clocking` 等，拒绝其用作未转义标识符，包括单级限定名称；Verilog 模式、转义名称、注释和字符串保持相应用法。保留关键字并不表示相应语言能力已经实现。原始 RAM case 的 `before` 为非法输入；归档保持不变。

回归覆盖四个同源模型、三种执行配置、预测提交/回滚、挂起检查点恢复、共享状态和独立分区，以及非法生命周期、automatic 存储限制和两种关键字路径。验收记录见 [M145](../validation/m145-package-lifetimes/README.md)。没有新增性能测量。
