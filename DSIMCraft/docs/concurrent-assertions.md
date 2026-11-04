M140 已支持有限序列作为蕴含前件，见[当前范围](sequence-antecedents.md)。下文关于前件仅限布尔表达式的描述是历史边界。

M136 已接通固定正数布尔重复 `expr[*N]`，见 [当前重复范围](sequence-repetition.md)；下文历史批次关于完全不支持重复的描述不适用于当前版本。

M87 更新：固定 `##N`、多阶段后件和直接串接序列已接通，见 [当前范围](sequence-delays.md)。下文 M82/M85 的“完全不支持 ##”属于历史边界；延迟范围、重复和完整 SVA 仍缺。

# 单时钟并发 property/SVA

M82 为 RTL parser 和编译运行时增加有界并发断言；门级 parser 保持独立。原报告 `t04_property.sv` 可以直接编译执行。以下范围是本批支持声明，不代表完整 IEEE 1800 或 VCS 验证功能。

```systemverilog
property request_ack;
  @(posedge clk) disable iff (reset) request |=> acknowledge;
endproperty
check_ack: assert property (request_ack) else failures = failures + 1;
cover_ack: cover property (@(posedge clk) request |-> acknowledge) hits = hits + 1;
```

支持模块或已展开 generate 局部作用域中的无形参 property、同一作用域内的前向命名引用、直接时钟 property，以及 assert/assume/cover。`assume` 在仿真中同 assert 检查，不约束激励。单个静态 integral 信号的 posedge/negedge 为时钟；布尔表达式、`|->` 和 `|=>` 的 antecedent/consequent 必须是无副作用的 integral 表达式。可读取 packed 变量、参数、位/片选和可静态展开的 unpacked 元素。除下述采样值函数外的函数调用、动态数组、运行时 unpacked 下标和字符串 property 表达式拒绝。命名定义按实例克隆，不共享尝试状态。

每个时间槽只为实际读取的信号按需保留第一次写入前的值。静态声明初始化先完成，时间零的过程执行也使用该采样起点。Active/Inactive/NBA 稳定后在 Observed 求值；同一轮 Observed 之前的重复时钟脉冲合并。非重叠蕴含保留一个到下一时钟的尝试，每一时钟仍可开始新尝试。结束时未完成的弱尝试不自动失败。

`disable iff` 使用 Observed 时刻的未采样值；在两个时钟之间出现的有效脉冲取消已有尝试，同沿 NBA 撤销复位可以使新尝试生效。编译器登记复位表达式依赖，只在相关信号变化时检查取消；不在每次任意信号变化时遍历所有断言。

动作在独立 Reactive 队列执行；动作中的非阻塞赋值进入 Re-NBA，在返回被动作唤醒的设计 Active 过程前提交。动作支持阻塞/非阻塞赋值、条件、循环和打印，其他语句受现有 lowering 和动作检查的限制。含 delay、event wait、wait、fork，以及直接 `$finish` 的动作暂时拒绝；cover 不接受 else。默认 assert/assume 失败输出 DSIM 诊断并继续仿真，有 `$fatal` 动作则按已有规则终止。竞态动作的跨断言先后顺序不保证与 VCS 一致。

与本批实际 VCS W-2024.09_Full64 对照一致，空成功不执行 pass 或 cover 动作，X/Z antecedent 不产生非空成功；X/Z consequent 使已触发尝试失败。没有实现 `$assertvacuouson/off` 等运行时控制，不将这一默认选择表述为全部工具/全部控制模式的行为。

采样、尝试、Observed/Reactive/Re-NBA 队列和结果均归 Sim 所有，随 checkpoint 保存、回滚；回滚期间打印和波形沿用已有事务机制。表达式、时钟、复位和动作读写加入过程依赖图，独立设计可分区。仅在使用并发 property 的生成模型中启用这些额外状态，不使用 SVA 的模型不增加这些字段。

尚缺完整 sequence、`##` 延迟/范围、重复、嵌套 temporal property、多时钟、默认 clocking、property 形参/局部变量、别名、跨作用域命名引用、程序内并发断言、bind、完整采样函数的显式时钟与省略中间实参形式、assert 控制任务和完整覆盖率数据库。错误恢复、所有标准调度区和完整验证工具链也没有据此宣称补齐。DWF 未修改，没有新增性能对标结论。

验证记录位于 [validation/m82-concurrent-assertions](../validation/m82-concurrent-assertions/README.md)。

M85 增加单时钟采样值函数：`$sampled(expr)`、`$past(expr[, ticks[, gate]])`、`$rose(expr)`、`$fell(expr)`、`$stable(expr)`、`$changed(expr)`。表达式保持原有静态 integral 限制，支持固定元素、层次/接口信号和宽四态值；`$past` 保留自定宽度/符号，深度必须为 1..65536 的已知正整数常量。gate 只在采样值为真时计入历史，当前拍的返回值读取当前拍之前的有效历史。rose/fell 只检查最低位，stable/changed 比较全部位并区分 X/Z。

每个函数出现位置在每次断言时钟都更新，独立于蕴含 antecedent、逻辑短路和 disable iff；嵌套函数按依赖顺序求值。历史不足时使用静态声明初始化完成后、时间零 initial 赋值前的表达式采样初值。值队列按实际需要增长，容量不超过所需深度；初始化值、队列游标和结果均随 Sim checkpoint 保存/恢复。动作块和 disable iff 支持 `$sampled`，因此同沿 NBA 后动作仍可读取该时钟的采样值。动作不能让采样表达式依赖 automatic 局部存储。

本批尚不支持采样函数中的显式时钟、`$past(x,,gate)` 的空中间实参、default clocking 或独立过程中的时钟推断；动作块及 disable iff 中的历史函数暂明确拒绝，仅接通 `$sampled`。sequence、重复及多时钟限制仍适用。验证见 [validation/m85-sampled-values](../validation/m85-sampled-values/README.md)。
