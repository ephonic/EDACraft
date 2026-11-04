# 整数与枚举类型的关联数组索引

M193 将命名关联索引从 class/string/32 位整数扩展到有符号或无符号的 packed 整数和枚举类型。索引按声明的位宽进行扩展或截断，存储与比较保留全部位，支持 65/129 位及更宽的现有整数值表示。负数在非负数之前，unsigned 按完整无符号数值排序，避免高位不同的索引发生碰撞。

`first/last/next/prev`、`foreach`、`find_index` 等索引队列、`exists/delete`、关联数组复制、类内属性、包类型、类型参数和模块特化共用该类型信息。枚举游标及枚举索引队列保留规范枚举身份；其他枚举不能冒充同一索引类型。复制检查索引的位宽、符号及枚举/类身份；同宽同符号整数索引允许两态/四态类型之间复制，与 VCS 对照保持一致。constraint foreach 的隐式索引同样保留枚举和高位，存储与游标变化继续纳入 checkpoint / 预测恢复。

VCS 对照的窄索引会诊断 X/Z，dsim 对全部索引位执行相同检查。转换到索引位宽后仍包含 X/Z 的直接读写报运行时错误；`exists` 返回 0。显式两态 cast 先产生确定值则可以使用。合法但不存在的索引仍返回元素类型的默认值。非零高位不会被强行截成旧的 32 位索引。

边界：此批通过命名类型/类型参数声明 packed 整数索引，未增加全部内联索引类型语法。packed struct、unpacked 类型、real/chandle 索引仍拒绝；string 索引 locator 队列、关联数组形参、多维运行期容器及其混合维度尚未实现。原版 Accellera UVM 2020.3.1 的枚举索引检查已越过，但同一处 `uvm_copier.svh:70` 的 `m_recur_states[uvm_object][uvm_object][uvm_recursion_policy_enum]` 仍因多维容器拒绝，完整 UVM 未编译执行。

另有实测差异：VCS W-2024.09 接受这批 129 位索引最高位含 X 的读写，dsim 仍拒绝，单列保留，不声称这条路径与 VCS 对齐。

测试另保留 VCS W-2024.09 的已知边界：其约束关联索引超过 64 位时报告 NYI-CSTR-AAKTNS，dsim 的 129 位约束用例单列为自身正确性测试，不计为 VCS 运行对齐。

实现不改变 RTL/门级 parser 的分工，不据这些功能用例作速度结论。测试、发布与未完成项见 [M193 验收记录](../validation/m193-integral-keys/README.md)。
