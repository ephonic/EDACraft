后续核心目标：打通原版 UVM + REPORT-GAP9 虚接口，不把支持语法等同于运行语义支持。

1. 先补 uvm_resource_base.svh:212 的 unpacked struct 关联数组。沿 AggregateType 描述符保留 time/int/bit/logic/string 默认值、类型身份、按键读写、复制、迭代、字段切片、inout/ref 和快照恢复。next-blocker.sv 是 VCS 成功复现，不能删除 access 或修改 UVM 来绕过。
2. 虚接口需要与 interface port 的静态绑定区分：保留接口声明/参数实例/可选 modport 的类型；实例类属性、局部和形参存真实可空句柄，支持赋值、复制与类型兼容检查。编译后的动态成员读写按句柄选择真实已展开实例；不能把多个接口固定为同一个端点。
3. 接入 posedge/negedge、clocking 读样本与非阻塞驱动、clocking/event 等待、任务/函数和 modport 权限。先验收报告 u04_vif.sv，再加两个接口运行中重绑、多对象相互独立、null 诊断、input 禁写、参数类型不匹配、继承和预测回滚。每项与 VCS 同源核对。
4. $monitor/$strobe 要在 Active/Inactive/NBA/Reactive/Re-NBA 稳定后执行；$monitor 只保留最后登记的一组参数，忽略 $time 作为独立触发源，支持 monitoron/off 和瞬态变化；$strobe 读取时间槽末值，不能简单替换为 $display。自动变量生存期和有副作用函数需按 VCS 明确处理。输出及登记状态要参加预测回滚。
5. 模块 type 参数、范围 sequence、字符串字面量接收者、$typename，再与 legacy assign/deassign、线网/强度、expect/checker/SDF任务等按影响逐项补齐。官方UVM每批保持输入SHA并记录真实下一首错。

GAP9 原探针目录现有38份 u*.sv，报告列30项。已对当前编译器逐份 emit-only 并保留 SHA/诊断，20份可生成代码、18份拒绝；拒绝中包含报告试验的中间/无效语料，未与 VCS 确认前不能直接计18个产品缺陷。编译通过也不算仿真对齐通过。VCS原始探针复查单列。

类内非法覆盖参数两个拒绝项：VCS W-2024.09发出AOUP后忽略不存在于类头的N，dsim直接报unknown class parameter，属于显式诊断策略差异；不记为VCS也拒绝。直接对类字符串参数调用len在VCS遇到NYI，正例改为先将同一常量赋给string变量再查询；保留此边界记录。

GAP9 VCS复查最终为20两端可编译、11仅VCS可编译、7两端均拒绝。7份分别含未声明code、VCS可变数组比较NYI、字面量方法和checker形参语法拒绝、未声明u、packed union内未打包成员或位宽不等；不能把这些统称为非法语法，也不能据此宣称相关功能已具备。
