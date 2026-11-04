# 共享编译进程（0.13.0）

门级编译器按 DUT 安装拥有状态的 context，每个 DUT 登记 commit、sample、组合求值三个无捕获回调。每个进程只保存 handler ID、cell payload、queued/waiting 和 generation；cell 表保存顺序状态索引。回调以运行中的 `Sim&` 及相应 context 求值，避免逐实例分配捕获 State/i/driver 的 `std::function`。

RTL 的一般闭包仍由 `Sim::process` 注册，放在独立的 Action 表中。它们保持可复制，检查点复制 Action 表以保存可变 PC/局部计数。编译回调的 context 由 `compiled_context(shared_ptr<T>)` 登记，内核同时拥有生命周期并注册状态快照；多个 handler 共用同一份模型状态，检查点不为每个 handler 重复捕获。context 的值类型复制须拥有全部可变状态；若它含指向外部可变对象的指针，调用者仍需为该对象提供独立快照参与者。

`compiled_handler(context, function)` 保存 `void(Sim&, void*, uint32_t)` 函数指针；`compiled_process(handler, payload)` 创建进程。payload 是模型自行解释的 32 位索引，生成代码保证其范围。空 context、空函数、不存在的 context/handler、超限进程及冻结后的注册均报错。低层函数的 context 类型必须与注册模型匹配。

这些修改不融合或重排进程。门级 commit/sample 仍按旧顺序创建，sample 仍在 Active 采样、commit 仍经 NBA 调度；等待位置、去重、generation 与事件预算不变。状态输出消除沿用 0.12.0 的依赖证明。context 及闭包表一起参加可重复检查点恢复，错误预测仍丢弃未提交波形和输出。

连接定型时还为参与 alias 组的信号设置缓存标志，`drive` 对未连接信号直接解析本地驱动；组内冲突解析保持原算法。第一次 drive 可惰性完成连接定型，之后新建的独立信号初始不属于组。缓存和信号一起复制，无单独指针失效问题。

专用测试覆盖混合通用/编译回调、多个模型、10 万 payload 校验、Active/Inactive/NBA/定时/等待、可变 RTL PC、可复用检查点、预测提交与失败重放、模型生命周期及拒绝条件。保守并行回归在 1/2/4 worker 上分别运行通用和编译 context，使用同一独立预期。生成 RTL/门级模型仍须完整波形和 VCS 差分验证。

此接口本身没有实现自动网表分区、SDF 延迟或跨分区回滚。性能结果与源码/证据见 [验证记录](../validation/m5-compiled-process/README.md)，继续依赖 [时序与并行接入计划](sdf-annotation-next.md)。
