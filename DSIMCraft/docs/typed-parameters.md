# 类型化值参数与常量上下文

RTL 前端支持 `parameter`/`localparam` 的 `bit`、`byte`、`shortint`、`int`、`longint`、`integer`、`time`、`logic` 和 `reg` 值类型。整数 atom 固定位宽（8/16/32/64 位），默认符号与变量类型一致；bit/logic/reg 可使用现有降序 packed 范围。支持类型允许的显式 signed/unsigned、同声明继承类型、模块头部及体内声明、静态局部和 generate 参数。M19 分离 int/integer 后遗留的 `parameter int`/`localparam int` 兼容退化已修复。

```verilog
module counter #(
  parameter int COUNT = 4,
  parameter longint LIMIT = 32'hffffffff + 1,
  parameter byte signed START = -2,
  parameter bit [79:0] MASK = '1
)(output reg [63:0] q);
  localparam int NEXT = COUNT + 1;
  initial begin
    q = START;
    repeat (NEXT) begin #1; q += LIMIT; end
  end
endmodule
```

默认值、命名覆盖和位置覆盖均在目标声明上下文中求值，然后按目标位宽截断、确定声明符号，并对两态参数逐位把 X/Z 转为 0。后续参数、端口宽度、generate 条件/循环及 delay 使用的是转换后的值。未指定类型或范围的旧参数继续从表达式推断宽度与符号。参数实例克隆保留各自结果，elaboration JSON 输出 `width`、`signed`、`two_state` 和完整位串。

固定宽目标把上下文传入普通一元/二元运算和条件表达式，再执行运算。因此上述 LIMIT 为 64'h0000000100000000；命名覆盖 `.LIMIT(32'hffffffff + 2)` 为 64'h0000000100000001。比较/逻辑、移位量及拼接遵循自身尺寸边界。未知条件的常量三目表达式逐位合并，未知结果仍保留到两态目标转换阶段。无基数填充值 `'0`、`'1`、`'x`、`'z` 在目标上下文展开。

归约 AND/OR 及其取反、逻辑非返回 1 位 unsigned，X/Z 按四态控制值规则处理；位反转把 Z 转 X。常量 `/`、`%` 采用多字整数求值，覆盖 signed 向零截断及余数符号；零除或未知操作数产生 X。常量移位不再对位宽取模，超过位宽时按逻辑/算术移位填充，未知移位量产生 X。带尺寸的二/八/十/十六进制字面量允许丢弃高位，不再把非整字十六进制宽度误判为越界。所有操作在编译展开期完成，不增加仿真事件的运行时分支；RTL 与门级 parser 继续独立。

这仍是值参数与既有整数表达式的子集，不包含类型参数、参数数组、完整类型/尺寸 cast、real/string 参数、常量用户函数、完整 mintypmax/幂运算与层次引用。固定宽 atom 的额外 packed 范围、重复/未知/localparam 覆盖、运行时变量初始化参数等明确拒绝。没有宣称完整 SystemVerilog 常量求值，也没有本批速度对比。

验收命令：

```sh
ctest --test-dir build -R '^(rtl_typed_parameters|rtl_semantic_memory)$' --output-on-failure
python3 validation/m20-typed-parameters/verify.py
```

测试范围与实际结果见 [M20](../validation/m20-typed-parameters/README.md)。

M28 增加 [typedef/enum/packed 聚合值参数](type-signatures.md)，包含常量成员访问、别名、实例重新绑定与 enum 检查。
