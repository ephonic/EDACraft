# SDF 端点绑定（0.11.0）

```sh
./build/dsim --sdf-bind-check tests/sdf_binding/timing.sdf \
  --gate-netlist tests/sdf_binding/net.v --gate-top dut \
  --liberty tests/gate/cells.lib --sdf-tick 1ps \
  --sdf-corner typ --emit-ir build/sdf-binding.json
```

此入口使用独立 gate parser，完成实例、引脚、方向和结构互连校验，输出统计；不生成仿真程序。JSON 明确给出 `binding:true`、`annotation:false`。`--emit-ir` 保存统计摘要，不是完整 arc 数据库。

支持空 INSTANCE 对应所选网表顶层、具体层次路径、`INSTANCE *` 按 CELLTYPE 展开；严格校验 CELLTYPE。名称按组件编码，SDF 的 `.` / `/` divider 与反斜杠转义独立处理，转义的字面分隔符不会误拆成层次。Liberty internal pin 不能作为外部时序端点，明确拒绝。IOPATH 限本 cell 输入到输出，PORT 校验输入，DEVICE 校验指定输出或展开本 cell 全部输出。INTERCONNECT 按发送和接收 pin 分别绑定，检查方向及 net/结构 assign 的有向可达关系；不会跨功能门推断连通，也不会将所有扇出合成一个接收端。

`--sdf-corner min|typ|max` 默认为 typ，只选择对应值，空 corner 保持为空。`--sdf-tick` 必须显式提供合法 1/10/100 fs–s 单位，作为**数值预览精度**。SDF TIMESCALE 优先；无头部单位时可用 `--sdf-unit` 指定后备单位。十进制换算精确、半入舍入，保留 uint64 范围的符号/幅值，拒绝溢出。负 ABSOLUTE、INCREMENT 和检查值均保留，不提前夹到零。将来实际回标仍须区分 SDF 单位、目标 cell model 时间精度及全局 tick；当前统一精度预览不证明混合 cell 精度的 VCS 舍入等价。

`src/sdf_binding.hpp` 提供逐条 `SdfBoundEntry` 回调，包含目标 ID、pin/net/方向、所选数值及原始语法引用。条件、边沿、标签、模式、RETAIN、reject/xlimit 不丢弃。原始语法引用只在本次回调有效，需要持久化的消费者须复制或 intern 所需信息，且必须等整文件解析成功才提交效果。CLI 在成功后写摘要，失败不覆盖已有摘要文件。

为控制大网表开销，时序名称仅按需保存：长度编码的路径字节池、两个 uint32 索引及层次端口；普通功能仿真不建立此索引。网表不经过 RTL AST。绑定专用 topology 模式只要求 Liberty pin，不要求可执行 function/ff/latch 支持，可校验升序和超过 64 位的顶层端口；禁止该模型进入代码生成。完整 Liberty 解析仍可能占主要内存，名称池大小不能代表进程 RSS。

尚未实现 specify arc 匹配、COND 求值、CONDELSE 优先级、重复路径诊断/覆盖、ABSOLUTE/INCREMENT 合并、transition 延迟应用、取消/脉冲、notifier 和 timing checks 执行。回调按源顺序交付，包括重复记录；“绑定成功”只说明这些端点在拓扑中存在且符合上述约束。缺省/负数计数按原始数值槽位统计，bound_entries 按通配展开后计数。

测试包含独立已知的 min/typ/max tick 断言、转义/层次/通配、RETAIN/条件保留、有向连接、空值、最大负幅值、溢出及失败输出保护。真实输入验证及原始记录见 [0.11.0 验证](../validation/m4-sdf-binding/README.md)。下一步是 [可回滚延时事件与实际回标](sdf-annotation-next.md)。

## 原始数值绑定接口

实际回标消费者可以设置 `SdfBindOptions.numeric_preview=false`，此时 `tick_fs` 可为零。端点、方向、连通性、语法和单位校验照常执行，但不转换数值。回调通过 `unit_fs`、`corner` 与 `syntax` 读取原始十进制；`numeric_preview=false` 明确表示 `values` / `retain` 预览向量为空，并非原语法缺值。语法引用仍只在回调内有效，消费者须暂存自己的数据并在整个绑定成功后提交。

缺失 corner 计数仍按原数值槽位统计，不受通配展开影响；原始模式不计算舍入后的负值数量，报告 `negative_selected_values:null`。默认模式与 CLI 继续数值预览，报告新增 `numeric_preview:true`，原计数语义不变。不能把预览结果作为 INCREMENT 的求和输入。

原始接口测试覆盖不同 SDF 单位、缺失 typ、回退单位、条件/RETAIN、全部 corner、大数原文保留及错误保护。原先连接的“全部合并后舍入”数学原型不能作为 VCS 注解策略：新 VCS 微例中，目标精度 10ps 的 `.004+.004ns` 得到 0ps，`.005+.005ns` 得到 20ps；每个更新须按目标模型精度量化，再合并并处理负的路径结果。全局 tick 预览同样不能代替目标模型精度。详见[兼容性更正](../experiments/sdf_annotation/VCS_COMPATIBILITY.md)。该接口没有施加路径延时，未完成自动 SDF 回标。
