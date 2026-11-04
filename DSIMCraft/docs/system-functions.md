# 整数与位向量系统函数

支持 `$bits`、`$clog2`、`$isunknown`、`$countones`、`$onehot`、`$onehot0`，贯通参数/范围/generate 展开和生成模型执行。支持现有整数、enum、packed struct/union、别名、数组字、位/范围/固定宽度动态选择及宽向量。RTL 与大规模门级 parser 保持独立。

```systemverilog
parameter DEPTH=17;
localparam ADDR_W=$clog2(DEPTH);
typedef struct packed {bit valid;logic[ADDR_W-1:0] addr;} request_t;
request_t request;
logic[ADDR_W-1:0] index;
initial begin
  if($bits(request_t)!=ADDR_W+1)$fatal(1,"layout");
  request=0;index=3;
  assert(!$isunknown(index))else $fatal(1,"unknown address");
  if($countones(index)!=2)$fatal(1,"population");
end
```

`$bits` 返回 signed 32 位 int，在编译期查询自决定类型，不执行实参或记录其运行时读写。支持内建 bit/logic/reg、byte/shortint/int/integer/longint/time 数据类型、单个 bit/logic/reg packed 范围、命名类型、静态数组整体和已支持表达式，包括静态函数返回类型及含增减的数组字地址。类型名字在其他函数中仍不是普通值。packed 数据类型范围支持升序/降序，边界必须为已知、可用 signed int 表示的展开常量；范围宽度最多 1,048,576，查询总位数必须在正 int 范围内。

`$clog2` 返回 signed 32 位 int，按实参自决定宽度的无符号位模式计算向上取整的二进制对数；0/1 返回 0，任意 X/Z 返回 32 位 X。负整数按对应宽度的位模式处理，例如 `$clog2(-1)` 为 32。

`$countones` 返回 signed 32 位 int，只计数已知 1，X/Z 不计入。`$onehot`、`$onehot0`、`$isunknown` 返回 unsigned 单位两态值；前两者分别检查已知 1 的数量是否等于 1、至多 1，后者检查任意 X/Z。全部函数恰好接收一个实参；除 `$bits` 外，实参只求值一次，外围赋值或运算宽度不向实参传播。

常量函数结果用于参数、范围、实例和 generate 克隆时重新求值；运行时使用内联 C++ 模板和 64 位字的 popcount/最高位操作，无额外事件或状态布局。接入现有 delay/NBA、立即断言、VCD/DWF、检查点回放及独立域并行。另补齐子程序 `logic` / `logic signed/unsigned` 形参语法。

当前不支持 `$typename`、动态 `$cast`、real/string 查询、动态数组/queue 及当前类型系统以外的复合类型；不等于完整 SV 系统函数库。命名类型后追加 packed 维度和多维数组仍受现有类型/数组限制。

实际 VCS W-2024.09 的额外 130 位 `$clog2` 探针使用四态 `integer` 接收结果时，与 dsim 的已知值及 X 返回一致。原先使用两态 `int` 接收的输入，高字含 X 时 VCS 输出 130、dsim 输出 0；原输入和输出分别保留，未把它推广为宽 `$clog2` 整体不兼容。原探针对两态接收变量直接期待 X 的自检也已修正，不能把该自检失败解释为四态返回失败。没有据此判断供应商内部根因或完整标准合规性。VCS fatal 的退出码仍可为 0，验收同时检查 Fatal 和完成 TRACE。详见 [M26](../validation/m26-system-functions/README.md)。

语义参考：[Accellera 位向量系统函数参数讨论](https://www.accellera.org/images/eda/sv-bc/10802.html)；具体实现边界由本页及实际用例限定。

M27 已继续补入 [$countbits 和静态数组维度/边界查询](array-queries.md)，包含动态控制位/维度选择与常量展开。
