# VCS 路径数值语义与编译缓冲器集成

本批新增 `src/sdf_delay.*` 与文件→严格绑定→模型精度→编译缓冲器→延时驱动探针。生产 CLI 仍无一般 SDF 回标。RTL/gate parser 分离、已采用紧凑/合并驱动 runtime 不变。

58 组新 VCS W-2024.09 参考各三份一致 trace：54 组受支持场景的 native 各三次完整匹配，4 组部分 ABSOLUTE 出零后再 INCREMENT 的读回行为尚未解释，当前明确拒绝且无仿真输出。相隔 100ps 的缓冲器激励覆盖全部四态转换，验证数值接入；没有验证一般脉冲/COND/RETAIN/INTERCONNECT/timing checks。

VCS 证据纠正了旧精确数学暂存层的合并假设：逐项按目标模型精度舍入再相加，路径负结果逐次夹零；ABSOLUTE 负值先夹零再展开。完整六项以内路径更新基本项后推导 X 转换，显式十二项的 X 延迟独立累加；NULL 与零不同，负增量与 NULL 的 min/max 边界单独补测。原型五文件/归档保持原样，说明见 `experiments/sdf_annotation/VCS_COMPATIBILITY.md`。

初始 `updates/` 多个同体模块在 VCS 合并后出现 CELLTYPE 不匹配，原流水线只检查 trace 数量而误写 PASS。其 root-level `results.json` **不是有效数值参考**；日志完整保留。权威参考改为 `updates/separate/` 每例独立编译、检查全部注解报告；`prepare_native.py` 只从该目录收集。所有有效报告仅允许预期负延迟警告 SDFCOM_NDI，拒绝目标丢失等警告。

冻结源 `69f3a4f22ffc5c5b588c511e368243652441a803ed2b76efe0b8936c24ac2ac8`：227 工程文件、108 parser、3 个未修改波形原型依赖，见 `source-snapshot.json`。原始 VCS 证据 SHA `68e8d05140471e256ebd41867fb65a8581cdb542450660829ae49360daad1212`，追加零更新证据见 `zero-updates/evidence-archive.json`；58 组输入/三份 trace/注解报告均有逐文件 SHA。

本地 29+1=30 项通过（72.19s +60.66s），Linux 29+1=30 项通过（119.28s +126.46s）。3 个实际 ASan/UBSan 程序为绑定、数值和文件集成探针，CTest 3/3；macOS 关闭 LSan，检查实际 sanitizer 符号及完整成功日志。`verify.py` 从冻结源、原始 VCS 日志和实际 native 输出重新核对，保留 4 项拒绝边界，不将它们计为数值兼容通过。

复核：`python3 validation/m4-sdf-merge-semantics/verify.py`。实现接口、依赖和待完成项见 [路径数值层](../../docs/sdf-path-delays.md)。整体 SDF/并行/波形目标继续。
