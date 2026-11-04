# M96 原生 DB 读取接入

本轮导入用户指定的 `db_api.h/cc` 原生实现，删除工具调用路径，增加一次扫描的结构化对象读取、覆盖 JSON 和严格模型检查。完整图装配尚未完成，不宣称 DB 可以直接用于门级仿真。

实现和限制见 [docs/liberty-db.md](../../docs/liberty-db.md)。来源 hash 见 [IMPORT.json](../../docs/parser-origin/db-api/IMPORT.json)。PDK 原始文件、摘取的 Liberty 和生成的 cell 数据不进入仓库。

已验证：

- 合成容器命名/紧凑 NLDM、准确 float32 数组及 CCS 时间/电流样本；失败保持数据库、字符串池和文档不变。
- 按内容识别（含大于 64KB 的注释），损坏 CRC 的片段恢复和后续 ROOT 搜索；七类畸形文件拒绝；截断和 1,024 组固定种子随机字节。
- 文本库门级四态实际执行、既有 gate_regression 全组、gate_source 单元/CLI、Liberty binary roundtrip、格式 smoke；SDF model preparation。
- 同一 C++ 原生读取测试通过 ASan/UBSan，`detect_leaks=0`。未修改 RTL parser 或 DWF。

真实数据结果见 [real-data-summary.json](real-data-summary.json)：213MB 样本恢复 1,139/1,143 个 cell，已恢复 cell 面积全部与对应文本库按 float32 一致；6,870 张表，996,594 CCS 向量，20,865,765 时间/电流样本对。本机读取约 9.16 秒，不是 VCS 性能对比。

严格真实数据对照**未全部通过**：选定两个 cell 的 20 张 NLDM 表仅 8 张整数组完全存在于恢复结果，640 个 CCS 波形有 636 个全坐标/全样本匹配。`compare_real.cpp` 故意在缺失时退出 1，不通过删除缺失项或容差来伪造通过。该检查只验证原始数据存在性，不验证图归属。对象图、库单位、逻辑与 sequential 函数、部分紧凑/共享数据仍需原生实现。

复核脚本：`extract_reference.py` 在验证主机上流式读取用户库并只生成本机临时文件；`compare_real.cpp` 对全 float32 数组与 CCS 样本作精确匹配。临时原始证据在本机 `/tmp/dsim-m96-evidence` 及远端 `/tmp/dsim-m96-reference`；稳定发布身份另写 release-summary.json。
