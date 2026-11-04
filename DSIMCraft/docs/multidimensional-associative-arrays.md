# 多维关联数组（M194）

支持每一维均为关联数组的声明、typedef 叠加和类型特化，例如公开 UVM copier 使用的 `state_t states[uvm_object][uvm_object][policy_t]`。每一维分别保留整数位宽/符号、枚举身份、字符串或 class 类型，内层键不会继承外层的 unsigned/class 标记。

已接入完整元素读写、packed 选择、复合赋值及前后自增；完整数组和子数组复制；子数组 `num/size/exists/delete/first/last/next/prev`；剩余一维子数组的 locator（沿用现有方法支持边界）；多维及子数组 foreach、break/continue；当前存储上的约束 foreach。对象接收者和每个地址下标在单次读写或复合更新中只求值一次。

存储以拥有子数组的树保存，读空路径不创建外层元素；清空一个已有子数组保留其父键，删除父键移除整个分支。复制先取源快照，再解析写入目标，子数组独立拥有；checkpoint 同时保存全局/automatic 容器与对象堆内的分支。两态目标按叶元素转换，保留源数组的 X/Z。原生存储测试另覆盖复制覆盖祖先和有符号内层键。

当前边界：混合 fixed/dynamic/queue 与 associative 的多维容器、关联数组形参、字符串/real/aggregate 元素、遗漏维度的多维 associative foreach、子数组 reduction、string 键索引结果队列仍未补齐；元素的 timed/NBA 写仍拒绝。并非完整 SystemVerilog 容器或完整 UVM 支持。

公开 Accellera 2020.3.1 原版预处理保持 1,888,084 字节/166 依赖；原生首错已越过 `uvm_copier` 的三维关联数组，进入 `uvm_event_pool` 前置类与后续类型别名绑定。编译并运行整个公开 UVM 库尚未通过。

九个执行语料及负例见 `tests/multidim_associative`；[验收记录](../validation/m194-multidim-associative/README.md)区分开发测试、稳定入口与远端状态。两份带枚举内层键/负数外层键的约束语料在 VCS W-2024.09 报 `CNST-NAE`，单列供应商差异，不计作同源通过。二维 logic→bit 复制也有实测差异：源 `x1z1` 的目标在 dsim 为 `0101`，VCS 为 `1010`，独立 debug 探针重现；该语料未计入一致。没有性能结论。
