# SystemVerilog 整数与尺寸转换

支持普通整数静态 cast：`bit/logic/reg/byte/shortint/int/longint/integer/time`，`signed'(expr)` / `unsigned'(expr)`，以及正整数常量尺寸 `N'(expr)` / `(WIDTH+1)'(expr)`。内建类型采用其默认位宽、符号与两态/四态属性；尺寸 cast 保留内部表达式的符号与四态属性。支持 1..1,048,576 位，宽度表达式当前支持整数字面量、参数/genvar、整数运算及条件、已有 sign cast；不含常量用户函数或系统函数宽度查询。

```systemverilog
localparam longint LIMIT = longint'(32'hffffffff + 1);
localparam TRUNC = 8'(16'h12ff);  // 8'hff
logic [63:0] sample;
initial sample = 64'(byte'(counter++));
```

目标尺寸在内部上下文运算前生效，至少保留表达式的自然运算宽度，然后截断为 cast 尺寸；外层赋值/运算先获得转换结果，再按结果符号扩展。比如 `longint'(32'hffffffff+1)` 得到 64'h0000000100000000，而 `64'(byte'(255))` 得到 64'hffffffffffffffff。两态类型逐位将 X/Z 转 0；integer/time、尺寸及 sign cast 保留四态，logic/reg cast 为一位。

cast 是明确的 AST 运算，参与名称绑定、参数/实例/generate 克隆、常量求值和直接 C++ 代码生成。操作数只求值一次；复用短路/三目副作用、静态函数/任务、delay/NBA、波形、检查点和并行依赖；仅使用两态运行时转换的模型启用对应支持。cast 计算不新增仿真事件。RTL/SV 与门级紧凑 parser 保持独立；门级结构表达式仍拒绝 cast。

CLI 原来对所有 cast 提前拒绝；旧 grammar 的占位分支还会丢弃 cast。当前移除全局拒绝并替换占位节点，非法/零/负/未知/超限/运行时宽度明确报错。enum/struct 类型 cast、直接 packed 类型 cast、动态 `$cast`、real/string/void cast 及 qualified type cast（如 `int unsigned'(...)`）未接入，不作恒等表达式处理。整数 typedef 与其命名 cast 已接通，见 [命名整数类型](named-types.md)；enum/packed struct、package/interface 和并发 SVA 仍在 [计划](../plan1017.md) 中。

验收范围与限制见 [M22](../validation/m22-explicit-casts/README.md)。
