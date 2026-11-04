# 异步压缩接入统一编译/仿真流程

457文件冻结源SHA256 `f33ca27dd77fcf31499de4c6504d5701fe65423ba353ea8990868e1edf5bacbe`，见[source.json](source.json)。相对456仅修改`run_flow.py`与CMake新增测试，增加`tests/flow/async.py`；全部native编译源/运行头不变。清单每例可设置整数`wave_compression_jobs`（1–16）和`wave_block_events`（1–1,000,000），仅DWF运行接收这两项，配置错误在编译前拒绝。

隔离副本验证后合入工作树，实际新增正式CTest`tool_flow_async`于现工程通过（48.96秒）。六类RTL/gate/SDF/模型准备/delay组合，各以jobs1/4/16、block1执行一次实际编译和三种运行：18次编译、54次运行、18组完整VCD/DWF流、12对DWF文件逐字节相同；10个非法类型/范围在编译前失败。记录保留实际参数、runner/编译器/输入/模型哈希及所有原始日志/文件，见[独立审计](local-validation.json)。先前隔离副本另有同范围PASS，不混计为新增正式CTest。

原456完整105项通过并有独立不可变快照。本批审计逐一核对457的原105项CTest命令及属性相同，且native源完全相同，复用其结果；没有声称457一次完整106项执行。新测试使用相同已验收native编译器，该二进制哈希在全部18次流程报告中核对。

Linux脚本原任务`/tmp/dsim-async-flow-linux-1018-Ah3EzHwG`（PID2281055）已正常退出0且原PID消失，389份证据归档SHA256 `fd6d95cc2907b958f6855540a11b4a3ab6956b419782e63ff452504a9111f40b`已下载并[独立审计PASS](linux-verification.json)：18次实际编译、54次模式运行、12对DWF字节身份、10种非法配置拒绝；36份VCD/DWF与本地完整流逐条一致。复用456实际构建的native编译器及模型准备工具，二进制和两份源逐文件运行前后核对；没有重新构建457 native或运行完整106项。原456 Linux完整105项仍在独立原任务中运行。没有新增VCS实跑、异步吞吐或RSS收益结论。
