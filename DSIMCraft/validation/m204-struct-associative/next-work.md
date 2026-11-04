后续仍以未经修改的公开 UVM 和 REPORT-GAP9 为主线。

1. 先接通 uvm_config_db_implementation.svh:38 的实例 event 属性。当前模块命名事件已有独立运行时身份，但类事件不能仅在类定义上分配一个静态 signal。需要每个实例独立身份，成员访问和方法中的 this 均引用同一事件；动态等待在进入等待时捕获事件身份，支持触发、NBA 触发、triggered 的时间槽语义和预测回滚。验证两对象隔离、别名、继承、等待后对象变量改绑、同时等待者及 null 事件。next-blocker.sv 在 VCS 上成功运行；这不代表 dsim 已支持。
2. 随后完成真正的 virtual interface：保留接口/参数/modport 类型，可空句柄、局部/类属性/形参传递、运行时重绑、动态成员端点、clocking 事件和 modport 权限一起验收。优先 u04_vif.sv，再以两个真实接口和两个对象验证隔离与重绑，不静态绑定为单一实例。
3. 结构体容器仍缺整张关联数组参数和返回值、关联元素 ref、结构体关联末维队列和 NBA；本批只完成普通/自动局部、类属性关联存储和按值结构体元素传递。string-key 的索引 locator 仍需 parser 队列元素类型扩展。
4. GAP9 的 $monitor/$strobe 仍需时间槽末观察；模块 type 参数、范围 sequence 等按既有 next-work.md 继续。每批保存公开 UVM 的 166 依赖和预处理 SHA，记录真实下一首错，不修改 UVM 源码绕过。
