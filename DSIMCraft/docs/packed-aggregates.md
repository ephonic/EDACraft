# Packed struct / union

M91 修复后续 unpacked struct 支持引入的 packed 成员写入回归：混合存储中的 bit 视图写入保留原始 X/Z，读取时转换。原 `values` 断言恢复通过；具体范围见[存储与视图](packed-storage.md)。下文是最初功能范围，后续扩充以相关专题为准。

支持 `typedef struct packed`、等宽 `typedef union packed` 和别名。成员使用已支持的整数类型、单个下降 packed 范围或先前定义的 enum/packed 类型；嵌套通过命名类型组合。struct 先声明的成员占高位，union 成员共享全部位。整体默认 unsigned，可显式声明 signed。模块、generate、过程和静态子程序局部定义均在实例/克隆中重新绑定。

```systemverilog
typedef enum logic[1:0] {IDLE, BUSY, DONE} state_t;
typedef struct packed {
  state_t state;
  logic signed[7:0] data;
} packet_t;
packet_t q, words[0:3];
initial begin
  q=0;
  q.state=BUSY;
  q.data=-3;
  words[1]=q;
  words[1].data <= #2 q.data+1;
end
```

成员支持读写、嵌套访问、位/范围/固定宽度动态选择、拼接目标、复合赋值和增减，支持数组字的动态索引。读改写的字地址与位地址只求值一次。连接现有 delay/NBA、VCD/DWF、检查点回放和独立域并行；成员可作为内建类型端口/子程序的输入实参。整体赋值与命名 cast 使用 packed 位向量，enum 成员单独赋值仍要求同类型或显式 enum cast；整体赋值不逐成员施加 enum 检查。

全部成员为两态时，整体默认 0，存储时 X/Z 转 0；含任意四态成员时，整体默认 X。混合类型的底层位保留 X/Z，读取 bit 成员才转成 0；给 bit 成员写入 X/Z 不提前清除混合整体的底层位。这一行为已用实际 VCS 探针核对。signed 成员读取独立保留符号，其 packed 选择结果为 unsigned。

布局只在编译期存在，执行程序使用现有字级向量与切片，没有运行时结构对象或类型分派。动态成员写入限制在成员范围内，越界读取补 X（两态成员转 0），无效数组字写入忽略，右值及地址副作用仍执行。宽度限制 1..1,048,576 位；packed 范围边界必须是已知非负展开常量。

当前边界：没有匿名内联聚合、内联匿名嵌套定义、非 packed struct/union、tagged union、成员 unpacked 数组/初始化、赋值模式（`'{...}`）、整体数组操作、类型参数和模块命名类型端口、package/import、除 `$bits` 外的类型查询或完整层次引用。声明后追加 packed 维度仍缺。未声明类型的参数不保留聚合成员身份。输出端口现已支持父级 variable、静态成员/选择及混合拼接，范围与驱动检查见 [模块变量端口](variable-ports.md)；显式事件控制仍要求整体信号，直接成员边沿/变化控制尚缺。同一聚合整体的读与部分写仍受 always_comb/always_latch 的既有限制。

保留的实际 VCS W-2024.09 差异：该安装将 packed enum 成员的 `++` 诊断为 enum 复合赋值并拒绝，dsim 可以执行；部分越界成员动态选择的写入结果也不同。原始用例和诊断保留在 [M25 探针](../validation/m25-packed-aggregates/probes)，这两项不计入共同用例差分通过。未声明类型的聚合参数成员访问两者均拒绝，不推广为标准合规性结论。

实现与验收见 [M25](../validation/m25-packed-aggregates/README.md)。RTL/SV parser 与紧凑门级 parser 保持独立。

M26 新增[系统函数](system-functions.md)，可对整体/成员查询 `$bits` 并进行四态、位计数和 one-hot 检查。

M28 已接通[命名类型值参数与子程序签名](type-signatures.md)，typed 聚合参数保留成员身份。

M74 新增上下文决定类型的[赋值模式](assignment-patterns.md)，包括成员键、default、嵌套及重复；typed pattern 和类型键仍缺。
