# M67：动态数组元素位选与部分选择

补齐一维整型动态元素的位选、常量和固定宽度可变部分选择读写、增减/复合更新、阻塞延迟/事件控制，以及即时/延迟/事件 NBA 位段更新。NBA 在提交时合并当前元素，保留其他位的更新；沿用分配代次、描述符调用身份、自动帧、检查点和原有队列。完整元素阻塞保留直接写路径。RTL/gate parser 保持分离，grammar 未修改。

最终验收结果：

| 检查 | 结果 |
| --- | --- |
| 本地定向 CTest | 13 项全部通过，234.04 秒；新功能 67.58 秒 |
| 新功能模型 | 4 个共享模型 + 2 个原生 NBA 模型，三后端、ordered/settled、VCD/DWF，共 78 捕获 |
| 预测/并行 | 6 次实际失败预测回放一致，实际两分区通过 |
| VCS W-2024.09 | 4 份同源模型，498 条全部导出物理位 settled 时间线及 TRACE 一致；无位排除、无 wrapper 别名 |
| 编译诊断 | 5 类原生拒绝；VCS 也拒绝 4 类，接受拼接目标，属于尚未补齐能力 |
| ASan/UBSan | 7 份实际生成程序及完整 ordered 流/stdout、7 次 sanitized compiler 生成、3 种 NBA 内核通过；leak 关闭 |
| Linux | 冻结源干净构建，6 种动态内核 + parser 语义单测通过；6 串行 + 1 实际并行程序、14 捕获、5 类诊断通过 |
| 跨平台 | 7 份完整 C++、6 串行 + 1 并行完整 ordered 流及 stdout 一致；Linux 再核对 498 条 VCS 位时间线 |

功能边界与独立探针：

- VCS 对本批动态元素 packed NBA 报 `NYI: Non-blocking assignment with bit/part select on dynamic type`。两份原生模型不计作动态 VCS 对齐；`values.sv` 的 `FIXED_REFERENCE` 配置将存储改为固定数组，单独核对常见 NBA 位段行为，TRACE 一致。分配替换、空数组发出后再分配、等待后目标重算由原生 timing 模型和内核验证。
- 跨过负下界的写入：VCS 对探针中的固定/动态数组均忽略，dsim 对非负起点按原有策略裁剪写入；负索引读取也保留既有限制。`probes/clipping.sv`、`vcs-probes/clipping`、`native-probes` 保留全部原始输入与输出，不能称这条探针对齐。
- 动态元素仍通过同源 scalar 读取与 TRACE 观察；本批没有导出动态元素波形声明，498 条不是所有动态存储位。
- M66 的 NBA 索引函数一次/两次求值差异、ref-port NBA NYI，以及先前记录的其他兼容边界继续保留。
- 尚缺拼接动态目标、元素 scalar-ref、packed aggregate member 选择、整体数组 timed/NBA、多维动态容器、数组返回/声明初始化/assignment pattern、完整数组转换及完整 SV 验证体系。

首轮诊断夹具拼接遗漏空格、内核夹具在 checkpoint 后注册事件站点已修正，错误日志保留在 `logs/first-*`，不计为最终通过结果。实现完成后的最终 CTest、sanitizer 和 Linux 均使用冻结源；`final-identity.json` 再次从最终编译器生成 7 份 C++，与实际执行输入一致。

1480 个冻结输入，源包 SHA256：
`aa4022e9652394d415214cf1d07a6a47ca73112568460dff5848d3b288e45f35`。
`source-manifest.json`、`source-changes.json`、`source-archive.json` 保存来源；汇总见 `results.json`。未新增性能测量、全量 CTest 或 Linux sanitizer，不宣称完整 IEEE/VCS 兼容。

复现入口：`tests/dynamic_selects/regression.py`、`run-vcs.py`、`verify.py`、`run-probes.py`、`run-vcs-negatives.py`、`run-linux.py`、`run-sanitizers.py`；远端干净构建驱动保存为 `linux/driver.py`。
