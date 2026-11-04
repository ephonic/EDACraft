# integer/int 与过程局部变量

RTL 编译器支持默认 signed 的 32 位四态 `integer`，以及默认 signed 的 32 位两态 `int`（[M19 类型扩展](two-state-types.md)），包括模块/generate 变量、过程循环计数器、一维 unpacked 数组，以及命名/匿名 `begin/end` 块中的局部声明。使用现有信号和事件状态，未引入逐次执行的动态符号查找；RTL 和门级 parser 继续独立。

```verilog
integer total = 0;
initial begin : worker
  integer i;
  integer temporary = -2;
  for (i = 0; i < 4; i = i + 1) begin
    #1;
    temporary = temporary - 1;
    total = total + temporary;
  end
end
```

整数沿用 signed 运算的上下文、扩展、比较、除余、移位、打印和 packed 选择规则。溢出按 32 位截断；未初始化的 `integer` 为 X，`int` 为 0。整数数组支持动态地址、字内 packed 选择、阻塞/NBA/内部 delay，以及现有 `$readmemh/$readmemb` 路径，数组的其他边界沿用 [memory.md](memory.md)。

过程块中的 packed `reg/logic`、整数及一维变量数组按词法作用域解析，支持嵌套同名遮蔽。局部变量有静态生命周期，跨循环重入及 delay/event 挂起保持值。支持的常量声明初始化在启动时执行一次，包括未进入分支中的声明；不会在每次进入块时重置。显式过程赋值仍按控制流执行。局部信号接入 NBA、敏感依赖、波形、独立域并行和 checkpoint/predict 失败回放。

命名块的波形路径使用声明标签；匿名声明块使用每个父作用域内的 `$unm_blk_N` 名称。这与 VCS 的 `unnamed$$_N` 拼写不同；验证脚本显式列出名称映射，不省略其物理位和时间点。

编译期常量折叠检查表达式的符号来源：仅参数、genvar 和字面量参与的表达式可以使用 parser 的常量结果。整数的历史求值缓存不会替代运行时读取，包括数组地址、packed 索引及 generate 内部的运算。

当前限制：尚不支持 `automatic`/显式 `static` 声明、非恒定声明初始化、块外层次引用、完整子程序语义及多维/端口/整体数组操作。局部 net、事件变量等也不在支持范围。本批不代表完整 SV 整数/生命周期语义。

循环内声明计数器、语句 `++/--`、`break/continue` 已接入，初始化和生命周期边界见 [loop-control.md](loop-control.md)。

回归入口：

```sh
ctest --test-dir build -R '^rtl_integer$' --output-on-failure
```

验收见 [M13](../validation/m13-integer/README.md)。没有本批整体 VCS 速度测量。

静态用户函数/任务已在后继批次接入，支持范围及剩余 automatic/递归等限制见 [子程序说明](subroutines.md)。

前置/后置 `++/--` 的[表达式结果](increment-expressions.md)已在后继批次接入。

显式 `integer signed/unsigned`、64 位 `time`、模块类型化端口和子程序形参/结果已在后继批次接入，见[类型与端口说明](integral-types.md)。`int` 已改为两态，新增 `bit/byte/shortint/longint`，见[两态类型说明](two-state-types.md)。
