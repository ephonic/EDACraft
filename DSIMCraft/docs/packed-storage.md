# Packed 成员的存储与两态视图

混合 packed struct/union 共享底层四态位向量。成员声明为 `bit` 时，成员读取将 X/Z 转为零，但成员写入保留底层向量的原始 X/Z。独立 `bit` 变量、全两态 packed 存储和 unpacked struct 的独立 `bit` 成员仍在存储时转换。

```systemverilog
typedef struct packed {bit [3:0] b;logic [3:0] l;} mixed_t;
mixed_t s;
initial begin
  s='x;
  s.b=4'bx1z0;
  // 整体为 x1z0xxxx，成员 s.b 的读取结果为 0100。
end
```

M86 为 unpacked struct 添加的成员写入转换没有区分 packed 容器，导致 `s.b` 提前存成 `0100`，破坏整体及 union 其他视图的可见值。M91 将该转换限制为直接所属的 unpacked struct，packed 成员继续由底层信号的存储类型决定。只在编译期选择转换路径，没有增加运行时类型查询或额外存储。

`tests/packed_aggregates` 保留既有 `values` 原始断言，新增 `storage_views`：直接与嵌套成员、固定数组动态地址、RHS/地址一次求值、延迟 NBA、拼接与部分选择、130 位 union，以及独立两态存储和 unpacked 成员。完整聚合组还包含时间轮、分区执行、预测失败回滚、完整 ordered/settled 波形比较和负例诊断。

本批验收见 [M91](../validation/m91-packed-storage/README.md)。早期 [M90](../validation/m90-ascending-packed/README.md) 和[仓库整理记录](history/repository-cleanup-20261025.md)中的失败描述属于当时版本，保留作为回归证据。

完整聚合类型、层次写入、类型参数和完整验证平台仍有缺口；packed enum 自增及部分越界动态选择等已记录 VCS 差异不在本次修复范围。
