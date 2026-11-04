# 固定 unpacked 数组形参

M63 新增[无尺寸数组 input/inout 值形参](open-arrays.md)，支持固定数组实参；动态分配与动态数组引用仍未接通。

M62 已支持 [const ref 只读引用](const-ref.md)，固定数组形参见 [M61](array-arguments.md)；后文相关未支持描述是历史边界，以新文档为准。

任务和函数支持固定大小 unpacked 数组的 `input/output/inout/ref` 形参，包括多维数组、固定数组的完整或动态前缀子数组、ANSI/经典声明、命名调用和默认实参。RTL parser 独立维护，门级 parser 不经过这条路径。

```systemverilog
task automatic update(input integer source[2],
                      output integer result[7:6],
                      ref integer shared[0:1]);
  #2;
  result[7]=source[0];
  result[6]=source[1];
  shared[0]++;
endtask
```

数组按各维的声明顺序匹配元素，允许上下界和方向不同，要求维数、各维大小匹配。M70新增[值形参的等位宽两态/四态转换](array-state-conversion.md)；ref/const-ref仍要求严格类型等价。当前检查还涵盖宽度、符号、内建整数类型、enum 和 packed 聚合身份；任意元素类型转换仍未实现。维度须为非负的固定范围，总元素数至多 1048576。声明 `[N]` 按标准解释为 `[0:N-1]`，N 必须为正数；这一修正也适用于普通变量数组声明。

`input/inout` 在入口求值实际子数组地址并复制全部元素，任务挂起后保持取样值。`output/inout` 在返回时重新求值实际子数组地址，并复制元素；每次传输的动态前缀只求值一次。output 自动变量默认四态 X、两态 0。函数先捕获返回值，再复制输出。

`ref` 必须属于 automatic 子程序，在入口捕获每个实际元素的存储地址，挂起后保持别名；多个形参可以引用同一数组，嵌套转传和引用调用者 automatic 局部数组均保留共享语义。沿用已有不可变激活帧、事件订阅、取消/复用、分区和快照。动态引用前缀含 X/Z 或越界时显式运行诊断；这项诊断策略未称作与 VCS 相同。值传递的无效源前缀填 X/0，无效输出前缀忽略写入。

数组形参可在受支持的 foreach、查询、整体数组赋值、成员选择和事件表达式中使用。无外部副作用的 automatic 函数可以按既有规则以数组值参数用于事件回调，可写 ref 函数仍保守拒绝作为此类回调。input 可读 net 数组；output/inout/ref 必须写变量存储，automatic 目标仍禁止 NBA。

仍缺开放数组 `[]`、动态数组/队列/关联数组、const ref、递归、数组返回值、数组字面量/assignment pattern 实参及更完整的类型转换和 SV 验证体系。join_any/join_none 中直接访问外层 ref 的标准限制沿用 M60 已记录边界，不因支持数组而宣称补齐。

测试：`ctest --test-dir build -R '^rtl_array_arguments$' --output-on-failure`。真实 VCS 对照和证据见 [M61](../validation/m61-array-arguments/README.md)。本批以功能为先，没有新增性能测量。
