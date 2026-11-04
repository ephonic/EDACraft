补齐公开 UVM access[string] 所需的 unpacked struct 关联元素，支持普通变量和类属性、多层关联键、string/宽整数/类句柄键、混合两态四态与嵌套 string/class 字段默认值、字段选择、整图/子图复制、游标/foreach、mapped reduction、locator 值复制与预测回滚。

类型描述跟随自动任务私有存储分配，包含同时存活的调用及后续槽复用。八个模型与九份拒绝语料覆盖存储和类型边界，前端及生成模型用 ASan/UBSan 验证。

整图关联数组参数/返回值、关联元素 ref、关联末维结构体队列、结构体容器 NBA 仍不支持。string-key locator 的索引队列仍有独立 parser 限制。本批不宣称这些能力已完成。

未修改的公开 UVM 越过 uvm_resource_base.svh:212；新首阻塞是 uvm_config_db_implementation.svh:38 的类内 event trigger。next-blocker.sv 为独立事件属性复现。完整 UVM、virtual interface 及其他 GAP9 欠缺仍未完成。

groups.json 是冻结验收范围；发布前检查同源 VCS、前端/生成模型消毒器、七组回归和 mandatory parser/Liberty DB。入口复验要求生成 C++ 与冻结阶段完全一致，复用对应已原生编译通过的模型再验证输出和完整波形，记录可执行文件 SHA。最终状态以 progress.json 和各项收据为准。
