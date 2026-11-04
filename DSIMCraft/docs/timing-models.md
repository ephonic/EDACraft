# Verilog specify 模型与 SDF 路径表

`--timing-model-check models.v... --emit-ir models.json` 独立提取标准单元 Verilog 的时序声明。功能体保持 opaque，不作为已验证的功能模型；门级功能仍由独立结构 parser 与 Liberty 编译，RTL parser 不接收大规模网表。

模型 reader 复用宏、include、filelist 和 timescale 预处理，另在此模式接受 `celldefine/endcelldefine` 分类指令。普通 RTL 对这些指令的处理不变。记录模块自己的时间单位/精度、标量或常量位选端口、specparam 原文、路径条件/ifnone、posedge/negedge、路径极性和输出 data 表达式、1/2/3/6/12 延迟列表、标准系统 timing-check 参数及 pulse 声明。报告保留文件/行号；条件、notifier、pulse 信息均不丢弃，也不隐含执行。

结合已有检查模式可建立模型匹配的数值路径表：

```sh
build/dsim --sdf-bind-check timing.sdf \
  --gate-netlist design.v --gate-top dut --liberty cells.lib \
  --gate-models cells.v --sdf-tick 1ps --sdf-corner typ \
  --emit-ir path-tables.json
```

匹配前检查 Verilog/Liberty 外部端口集合与方向。每条 IOPATH 必须匹配输入、输出、条件 token 和 ifnone；保留 `==`/`===` 的差别，只忽略空白及包围整个表达式的括号，不做四态不安全的逻辑简化。新 VCS 独立微例确认：输入边沿在 SDF 或模型任一方省略时可匹配，双方都明确且不同则不匹配。一个条目匹配到多条路径时分别更新；full path 的不同输入输出端点对分别保存延迟状态。原始路径值先按 corner 解析，再用目标模型精度执行已验证的逐次 ABSOLUTE/INCREMENT 量化与夹零，最后换算显式报告 tick。

整个路径表在局部暂存，文件末尾任一解析、绑定、匹配、数值或输出 tick 换算失败都不提交报告。模型初始值不能猜为零：当前求值支持十进制 literal、正负号、括号、min:typ:max、specparam 引用和循环诊断。算术表达式、based delay literal、参数化/generate 模型和未展开的向量路径需要进一步 elaboration，当前明确拒绝，不进行中间舍入近似。条件只匹配词法身份，不声称任意语义等价条件均可互换。

模型初始 min/typ/max 由独立 `--gate-model-corner` 选择（默认 typ）；SDF 更新仍由 `--sdf-corner` 选择。两者不能共用一个选项，否则只有 INCREMENT 的路径会从错误模型基值开始。

报告 `runtime_annotation:false`，`paths` 只列出实际匹配更新的端点对，未更新路径的模型基值仍在模型库中。INTERCONNECT/PORT/DEVICE/timing-check 等条目仍仅做已有端点绑定，计入显式 `deferred_entries`，不称已施加延迟。RETAIN、路径脉冲阈值和条件 terminal 更新明确拒绝。此命令不生成带 SDF 的可执行仿真器。

本批打通真实 specify 元数据与数值表，后续运行时接入仍需路径因果选择、条件求值、脉冲/取消、每个接收 pin 的互连状态及 timing checks/notifier；继而才能在正延迟边界上自动分区。已有数值兼容边界见 [SDF 路径数值层](sdf-path-delays.md)。验证原始记录见 [本批证据](../validation/m4-timing-model/README.md)。
