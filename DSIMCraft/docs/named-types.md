# SystemVerilog 命名整数类型

支持 `typedef` 的内建整数类型 bit/logic/reg/byte/shortint/int/longint/integer/time、signed/unsigned 属性、单个 descending packed 范围和已有别名的再命名。支持模块、generate 和过程块、静态函数/任务局部作用域。标量与显式 packed 范围（包括 [0:0]）的属性分别保留。类型名与值有不同 AST 符号身份（vtTYPE），不分配运行时信号；名称在当前作用域和每个参数化实例中重新绑定。类型名不能作为普通值、左值或尺寸表达式使用。

```systemverilog
parameter int W=13;
typedef logic signed [W-1:0] word_t;
typedef word_t sample_t;
sample_t a, mem[0:3];
localparam LIMIT=word_t'(-2);
initial begin
  a=sample_t'(255);
  mem[1] <= #2 word_t'(a+1);
end
```

命名变量声明覆盖标量和既有一维 unpacked 数组、声明常量初始化，以及局部变量的词法遮蔽。命名 cast 保留宽度、符号与两态/四态属性，使用 [整数 cast](explicit-casts.md) 的上下文运算、截断与外部扩展规则，操作数只求值一次。参数值可由命名 cast 计算；参数化 generate 克隆保留定义，并按本实例参数重新计算范围。可接入 delay/NBA、VCD/DWF、检查点回放和现有独立 RTL 域并行。

同时补齐静态函数/任务不写 begin/end 的多语句体。修复常量 `===/!==` 在 X/Z 存储模式下误读已释放的普通整数存储所引起的崩溃；按对齐后的逐位四态比较生成已知的一位结果。

当前边界：M23 的整数别名范围：packed 范围必须下降、边界非负、宽度 1..1,048,576。不支持编译单元/package typedef、forward typedef、别名后追加 packed 维度、typedef unpacked 数组、模块命名类型端口、类型参数、非 packed 聚合、动态 $cast、除 `$bits` 外的类型查询及 real/string/void。普通局部变量、别名 cast 及使用内建端口类型的子程序可以组合使用；不把上述限制下的通过推广为完整 SV 类型系统支持。

M24 在此基础上补入 [整数枚举 typedef](enums.md)，枚举方法仍缺；M25 补入 [packed struct/union](packed-aggregates.md)，非 packed 聚合与完整复合类型仍缺。

RTL/SV parser 与紧凑门级 parser 保持分离，门级结构语法未扩大。验收见 [M23](../validation/m23-named-types/README.md)。

实际 VCS W-2024.09 配置存在一项保留的差异：两个不同 W 实例的 generate 局部 typedef 中，localparam C=word_t'('1) 被求成相同的首实例宽度；$bits(C) 在 W=8/W=13 两例均为 8，dsim 为 8/13。将常量操作数显式依赖 W/g（等值的 word_t'((W+g)*0-1)）后，该 VCS 得到 8/13。原始输入、原始波形和诊断探针保留在 M23 probes/generate-constant，正式共同用例采用后者并独立核对每个 generate 值。未据此宣称任意命名常量 cast 与 VCS 全面兼容，也未把该差异归因为已经证实的 VCS 内部实现。

M26 补入[整数/位向量系统函数](system-functions.md)，`$bits` 可以查询命名类型和已支持表达式。

M28 已接通[命名类型值参数与子程序签名](type-signatures.md)，包括 enum/packed 聚合身份及转换。
