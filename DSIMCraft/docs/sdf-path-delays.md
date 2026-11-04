# SDF 路径数值层与编译缓冲器验证

`src/sdf_delay.*` 将绑定后的原始 corner 值换为目标 cell model 的路径延迟表。调用者必须明确提供模型 timescale 和原始 specify 延迟；不能用 Liberty time_unit 代替模型精度，也不能默认模型延迟为零。当前生产 CLI 仍只提供 SDF 解析/绑定检查，尚未自动回标一般门级模型。

现已增加 [Verilog specify 元数据与模型匹配检查](timing-models.md)，可从模型文件获得上述初始值/精度，并应用到文件绑定的 IOPATH 表。模型初始 corner 与 SDF corner 分开指定。此接口仍是路径表构建，不改变本文关于一般门级运行时尚未完成的边界。

新 VCS W-2024.09 参考纠正了旧数学暂存原型的策略：每项更新先按模型精度半入量化，再合并 INCREMENT；每次负的路径结果夹零。10ps 精度的 `.004ns+.004ns` 为 0ps，`.005ns+.005ns` 为 20ps。最终才将模型精度的整数换为全局 tick，并检查加法/乘法溢出。负 timing checks 不走这个路径接口。旧原型保持冻结，见[兼容性更正](../experiments/sdf_annotation/VCS_COMPATIBILITY.md)。

列表接受 1/2/3/6/12 个值，转换顺序为 01、10、0Z、Z1、1Z、Z0、0X、X1、1X、X0、XZ、ZX。两值路径的基本六项是 rise、fall、rise、rise、fall、fall。完整的六项以内路径在基本转换更新后推导 X 转换；显式十二项路径的 X 延迟独立累加。部分更新保留原来的推导/独立表示，空 corner 与显式零不同。ABSOLUTE 的负值先夹零再展开；INCREMENT 的负值保留到与旧路径相加。失败不修改旧表。

仍有一个明确限制：部分 ABSOLUTE 覆盖使路径包含零延迟后，再执行 INCREMENT，VCS 的延迟读回在已测四组组合中不同于普通逐槽加法。该接口明确拒绝这个组合，等待进一步确认；不输出近似结果。已有 VCS 参考保留这些反例，回归单独核对拒绝诊断与无仿真输出。

`tests/sdf_path/probe.cpp` 是数值集成探针：从真实 SDF 文件经独立门级 parser 和严格端点绑定建立表，再交给编译缓冲器与已验收延时驱动，比较实际输出时间。模型精度/原始延迟与 VCS 输入一致；54 个受支持微例逐项匹配，另 4 个组合明确拒绝。每组 native 三次，并保留三份一致的 VCS trace、完整输入和注解报告。覆盖跨单位、舍入/负增量、缺失 corner、1/2/3/6/12 转换和独立 X 表示。

探针仅接受无条件 A→Z IOPATH，激励之间充分分隔。COND/边沿/RETAIN/阈值和未知端点明确拒绝；整个文件成功后才建立运行器。它不验证一般路径因果选择、重叠脉冲、逐接收 pin INTERCONNECT 或 timing checks，不等于 CLI 完成 SDF 回标。原始证据与复现脚本在 `validation/m4-sdf-merge-semantics/`。
