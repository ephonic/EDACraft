# SDF 单元模型准备

当可用的功能模型只有占位 specify 声明时，可显式生成一份与 SDF 事件身份一致的测试模型：

```sh
build/dsim_sdf_models --sdf design.sdf --models functional.v \
  --liberty cells.lib -o prepared.v --report coverage.json
build/dsim --gate-netlist design.v --gate-top dut --liberty cells.lib \
  --gate-models prepared.v --sdf-annotate design.sdf tb.v -o simv
```

`--models`、`--liberty` 可重复，支持 `-I dir`、`-D name=value`、`--timescale unit/precision`。输出文件必须不存在。工具先读完输入并验证，再创建新文件；失败会移除本次创建的输出，不覆盖旧输入、软链接或既有结果。

工具复用独立流式 SDF parser，按 CELLTYPE 汇总并去重 IOPATH 与九类常用检查的声明。SETUP/HOLD/SETUPHOLD 等按各自的 Verilog 事件顺序生成，保留数据/时钟的精确边沿、条件和物理转换。INTERCONNECT 属于连接，不生成单元 specify 声明，但计入完整覆盖统计。报告保存每个声明的来源行、原始项数、替换的占位声明数和新增条件别名。原始网表、Liberty、SDF 不改，仿真入口继续严格匹配。

生成文件复制词法预处理后的功能代码，仅替换参与注解单元的 specify 块，并在需要时补充条件别名。所有新路径和检查初值为零，实际数值由原始 SDF 注解；原模型里不属于这份 SDF 的其他时序声明不会被继承。因此这是专门为该 SDF 准备的测试模型，不能替代完整厂商时序库或用于签核。

Liberty 中命名的 `sdf_cond` 可以通过同一个 timing 组的 `when` 查明定义。当前接入直接标量端口别名，例如 `D_SDFCHK → D`、`CDN_SDFCHK → CDN`；已在功能源中的单驱动直接别名也可读取。严格注解仍比较原条件身份，只有执行条件才解析端口别名。布尔逻辑别名、循环、多驱动或缺失定义明确拒绝，不能把有 delta 行为的内部组合逻辑直接替换为即时表达式。

该工具能表示条件/ifnone 路径元数据，但当前运行时仍明确拒绝其执行；RETAIN、pulse threshold、PORT/DEVICE、未实现的检查模板也会失败。负检查值仍按默认非负模式夹零，未实现 `+neg_tchk` 的延迟 reference/data、notifier/UDP 行为。

统一流程清单可设置 `prepare_sdf_models: true`。流程增加独立模型准备阶段，再让 native 与 VCS 使用同一份生成文件，记录工具/模型 SHA256 及覆盖报告。它要求 VCS sources 中列出全部原 `gate_models`，以便明确替换。完整真实设计结果与限制见[验收记录](../validation/m4-sdf-model-preparation/README.md)。
