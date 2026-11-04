# SDF 流式前端

`dsim --sdf-check timing.sdf [--emit-ir summary.json]` 独立于 RTL 和门级前端，检查文件并输出统计 JSON。当前 summary 明确标记 `annotation:false`；本批尚未把这些延迟施加到仿真器，不支持 `$sdf_annotate`。

`src/sdf.hpp` 的 `parse_sdf(istream, filename, callbacks)` 提供 header、CELL 与 entry 回调。每个 IOPATH、INTERCONNECT 或 timing check 读完即回调；即使顶层 CELL 内包含几十万条互连，也不把整个 CELL 收集成树。只保留当前条目的小型语法树与统计，不保存整文件字符串；需要绑定的消费者自行选择所需数据。

支持的结构：

- 常见 SDF 头、`.`/`/` 层次分隔符、1/10/100 倍 fs–s 单位；单位缺省时返回空值，交给后续 annotator 明确处理。
- CELLTYPE、空/具体/通配 INSTANCE，ABSOLUTE / INCREMENT。
- IOPATH、INTERCONNECT、PORT、DEVICE，边沿限定；1/2/3/6/12 项 transition delay。
- COND（可选字符串标签）/CONDELSE，IOPATH 的 RETAIN；普通 delay、嵌套的 delay/reject/xlimit。
- SETUP/HOLD/SETUPHOLD、RECOVERY/REMOVAL/RECREM、SKEW/BIDIRECTSKEW、WIDTH/PERIOD、NOCHANGE；timing port 的 COND。
- 十进制、小数、科学计数、负数、min:typ:max 与缺省 corner；`()` 与零延迟区分。

数字保留原始十进制文本。`sdf_ticks` 在回标前提供精确的非负十进制到整数 tick 转换，采用半入舍入，检查单位、负值和 uint64 溢出。INCREMENT 与负 timing check 的合并须由后续有符号时序层处理，不能先转成 unsigned。

条件目前保留为括号与 token 规范化后的表达式文本，**不做布尔语义解析、求值或与 specify 的匹配**；名称保留转义与分隔符，不提前猜测实例路径。语法识别不意味着条件路径已经能回标。

未支持的扩展（例如 PATHPULSE、TIMINGENV、LABEL、部分 timing-check 可选条件/扩展）明确报错。单条目限制为 128 层嵌套、65536 节点、8 MiB atom 文本；单 token 1 MiB。这些是条目级限制，不是文件或 CELL 大小限制。回调可能在后续语法错误前被调用，调用方应在文件解析成功后提交绑定结果。

CLI 对原输入及文件列表实施路径/符号链接/硬链接覆盖保护，解析成功后才创建 summary。`--emit-ir` 在此模式保存统计信息，不是完整延迟数据库；接口测试直接核对完整回调数据。

语法依据 SDF 格式及 [OpenSTA 的公开 SDF grammar](https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/sdf/SdfParse.yy) 交叉核对；本实现没有复制其 parser 源码，也没有链接 OpenSTA。真实设计和边界测试见 [验证记录](../validation/m4-sdf/README.md)。0.11.0 已加入独立的[端点绑定与 corner 预览](sdf-binding.md)，RTL 已使用物理时间轴；下一步是实际  IOPATH/INTERCONNECT 延迟、脉冲和 timing checks 的 VCS 差分。
