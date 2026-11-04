# 编译单元 package import

M147 支持设计单元外的 `import p::*;`、`import p::name;` 和逗号列表。一次 dsim 调用按命令行及 filelist 展开后的顺序组成一个编译单元，include 文件参与同一顺序；不新增独立编译/链接模式。RTL 和门级 parser 仍分开。

```systemverilog
package types_pkg;
  parameter W=8;
  typedef logic[W-1:0] word_t;
endpackage
import types_pkg::*;
module lane #(parameter N=W)(input word_t value, output word_t result);
  assign result=value+1;
endmodule
```

模块和 interface 的参数、端口、正文、generate 和子程序使用定义位置可见的外层导入。后面的 import 不会追溯影响前面的模块；包必须先声明，package 内不能捕获编译单元名称。本地参数、变量、typedef 和子程序可以遮蔽外层导入，包括显式导入。本地/header import 仍按原有规则绑定，不写入父模块、兄弟实例或编译单元。

编译单元作用域独立于实例层次。导入的原声明、枚举/aggregate 类型身份、包函数词法作用域和可变存储保持不变；包变量/数组不会按实例复制。`instance.name` 不把外层文件级导入当成实例成员。预测、回滚、checkpoint 和分区使用既有机制，没有新增运行时对象。

每个导入位置保存一个可见视图。已经在更早视图中实际绑定的通配名称继续可见；未绑定的不同通配候选发生冲突时拒绝。展开顺序可能与源码顺序不同，因此冲突候选只暂存用于语义分析的引用，完成展开后必须由更早的真实绑定验证；暂存引用不能互相消除歧义。后续显式导入与更早使用的通配绑定冲突也会拒绝，失败时不输出 C++。

M183 已补[编译单元级 class 与普通 typedef](compilation-types.md)，保留原始类型身份和声明顺序。范围仍受现有 package/type/subroutine 能力约束；`$unit::name`、编译单元变量/task/function、前向类声明、完整 UVM 及独立编译/库链接仍未实现。隐式通配绑定只收集实际展开的设计单元；未实例化模块中的引用对后续文件级导入产生绑定影响的情况仍有缺口，不宣称完整 SystemVerilog 支持。

回归见 [compilation_imports](../tests/compilation_imports/regression.py)，本轮 VCS 对照和发布结果见 [M147](../validation/m147-compilation-imports/README.md)。本轮没有 runtime 性能测量。
