# SystemVerilog 枚举类型

支持 `typedef enum`：省略基类型时为两态 signed int；可指定已有整数基类型、signed/unsigned 与单个下降 packed 范围，或使用已有非 enum 整数别名作为基类型。成员在声明所在作用域成为展开常量。支持模块、generate、过程块和静态函数/任务局部定义；每个参数实例和 generate 克隆分别重建类型及成员。

```systemverilog
typedef enum logic [2:0] {IDLE, BUSY=3, DONE} state_t;
typedef state_t alias_t;
state_t state;
initial begin
  state=IDLE;
  #1 state<=BUSY;
  #1 state=alias_t'(7);
end
```

成员可显式赋整数展开常量，或从零/前一个值自动递增。支持跨机器字的成员值、负数、四态基类型的显式 X/Z 成员。检查同作用域名称冲突、重复位值、超出基类型值域、过宽显式尺寸表达式、两态基类型的 X/Z、从 X/Z 自动递增及自动递增溢出。类型和成员只占编译期符号，不成为运行时信号。

enum 保留独立类型身份，普通别名不会创建另一个 enum 类型。变量声明初始化、packed 成员单独赋值、阻塞/非阻塞赋值（含内部 delay）及一维数组字赋值要求同一 enum 类型或显式 enum cast。无类型参数和同类型两臂的条件表达式保留 enum 身份；显式整数参数、算术、整数/尺寸 cast、packed 位/部分选择不保留 enum 身份。enum 可以转换为普通整数。显式 enum cast 允许得到成员集合以外的值，按基类型截断/扩展及两态转换。支持前置/后置和语句 `++/--`；`+=` 等复合赋值明确拒绝。

接入既有直接 C++、delay/NBA、VCD/DWF、检查点回放和独立域并行，类型检查在编译阶段完成，不新增运行时类型分派。RTL/SV parser 与紧凑门级 parser 继续独立。

范围限制：本批是整数 enum typedef 子集。尚不支持内联匿名 enum、成员范围展开（如 `A[3]`）、`.name`、enum 模块端口、类型参数、package/import、类型查询和动态 `$cast`。枚举强类型赋值的已验收路径及常量尺寸规则见回归，不推广为完整 IEEE 1800 合规性。现有子程序端口仍使用已支持的内建类型。

用例、实际 VCS 探针、已列明的 VCS 生成临时量及两平台结果见 [M24 验收记录](../validation/m24-enums/README.md)。

M25 支持 enum 作为 [packed struct/union 成员](packed-aggregates.md)。整体位向量赋值允许重写 enum 成员位；成员的单独赋值保持强类型。该安装 VCS 对成员 `++` 的拒绝差异单列在 M25，未计入共同模型对照。

M28 已接通[命名类型参数和子程序签名](type-signatures.md)，enum 参数、形参、函数结果/return 和任务复制保持同一类型或显式 cast 检查。

M36 已接通 [first/last/next/prev/num 数值遍历方法](enum-methods.md)，包括常量求值、类型身份、宽/四态值和延迟/并行/回滚。未类型化方法返回值参数的 VCS 类型推断差异单列保留。

M80 已接入基础 [package/import](packages.md)；M81 补入 [enum.name 与动态字符串](strings.md)。前述历史批次限制不代表这些功能仍全部缺失，完整范围以新功能文档为准。
