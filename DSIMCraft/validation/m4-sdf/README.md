# SDF、回滚、保守并行与原生波形：本批记录

本批落地独立 SDF 流式前端、内核检查点/预测事务、手工分区保守并行 API，并完成此前原生 C++ VCD/DWF 的功能接入。SDF 回标、普通网表自动并行和完整 VCS 功能对齐尚未完成，也未证明预测/并行具有净加速收益。

冻结实现为 137 个文件、3 个不变的 Python 波形原型依赖、4 个验证驱动；最终清单见 `source-snapshot.json`。源码归档 `/tmp/dsim-sdf-parallel-source.tar.gz` SHA256 为 `eedf15f64f1d6c6fad41401e16402cb2b9390b85f84bf35b76fb0c9972f088b3`。相对原始 parser ZIP 有 17 个修改文件；新增的 `veri_num.cpp` 修复 ASan 发现的 sized decimal 高 words 越界，原有 16 文件与 0.8.0 相同。干净原包补丁重放通过，原始失败和早期测试日志保留。

## 实现与功能边界

- [SDF](../../docs/sdf-parser.md)：逐 entry 回调，保留条件、边沿、RETAIN、脉冲值、min/typ/max/空值及常见 checks；统计 CLI 不建立整文件或整个 CELL AST。条件暂存为 token 表达式文本，不做求值/specify 匹配，JSON 明确 `annotation:false`。
- [回滚](../../docs/parallel-and-rollback.md)：恢复进程 PC/局部闭包、信号/驱动/别名/watch、各调度队列、时间/finish/预算，以及注册的门级共享 State。预测正确提交打印/波形，错误恢复并按真实输入重放。整状态复制；没有自动预测器、跨进程 checkpoint 或跨分区 Time Warp。
- 保守并行：常驻线程池、独立 Sim、正延迟通道、lookahead/barrier，输出按时间/分区/源内顺序提交。1/2/4 线程与窗口大小、反馈、实际重叠、错误退出通过独立预期。要求手工分区、统一整数 tick、有限 horizon；零延迟跨区、全局 finish、共享可变模型状态不支持。
- 原生波形：`--wave-support` 编译，运行时选择 VCD/DWF、settled/ordered、raw/Zstd、scope/depth。全事件往返、四态/范围/别名/glitch、窗口查询与生成模型预测失败不泄漏波形均有回归。tick 标签没有实现 RTL timescale 换算，dump 系统任务与百万信号分页/恢复仍待做。

## 真实 SDF 输入与测量

读取 `10.131.254.103:/home/yangfan/vcs/vcs1017.md`，其当前 SHA256 与已有快照一致。只读取用户原工程中的 SDF，在独立 `/tmp/dsim-sdf-1017-zrUJuE` 构建 standalone parser。固定输入先后串行测 3 次，GCC 11.5、`-O3`；统计和 SHA256 由独立逐行 census 核对。

| 输入 | 字节 | CELL | IOPATH | INTERCONNECT | 全条目 | 解析秒中位数 | 进程 RSS 中位数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| sdf_sim/barr_modmult_flat.sdf | 162,466,853 | 300,910 | 867,982 | 790,222 | 1,744,700 | 7.130 | 3.0 MiB |
| sdf_gen/barr_modmult.sdf | 405,954,748 | 300,910 | 2,756,514 | 790,222 | 3,633,232 | 19.720 | 3.0 MiB |

两文件还有 SETUP 40,394、HOLD 43,248、RECOVERY 2,854；条件条目分别 17,124 和 2,435,340。条件条目数与条件表达式出现次数不是同一指标。当前固定输入的 IOPATH / SETUP 数与参考报告文字不同；保存报告原文，以本次输入 SHA256、独立 census 和实际 parser 结果为准，不通过修改输入迎合报告数字。

`real-sdf-measurements.json`、`remote-final/` 保存三次原始计时/结果、源码与独立计数。这里的 RSS 属于仅链接 SDF parser 的 standalone 检查进程，不是整个 dsim 仿真器或时序数据库的内存；文件系统为 warm，未测冷盘，不是 VCS 解析速度对比。

## 验证入口

- `tests/sdf/parser_test.cpp`：接口字段独立断言、非法结构/值/深度、10 万条单 CELL、十进制量化/舍入/溢出。
- `tests/sdf/cli.py`：独立 CLI、JSON、错误文件/行、源文件/符号链接/硬链接保护。
- `tests/checkpoint_test.cpp`：重复恢复、PC/计时器/watch/别名/驱动/NBA/#0、ff/随机数、预测提交/拒绝/异常、波形输出隔离。
- `tests/checkpoint/generated.py`：实际生成的 RTL、ff 反馈、latch、宽连接模型，错误分支 stdout 与 ordered/settled DWF 逐事件对照正常执行。
- `tests/parallel_test.cpp`：独立完整时间/四态预期，1/2/4 线程、不同窗口与恢复运行、正延迟反馈、真实并发和异常退出；另外验证推测提交时输出保持原时间戳。
- 本地完整常规与 ASan/UBSan CTest 各 15/15；最后仅修改并行宏分支和测试的时间戳部分，最终 core tests 与 ASan/UBSan/ThreadSanitizer 单独复核。另有全部 18 组生成波形模型，以及 4 组 baseline/replay 实际生成回滚模型的 ASan/UBSan 运行记录。详见 `../m5-checkpoint/`。
- 远端冻结源码复核、完整 CTest、历史同输入 RTL/门级 VCS 参考复核、13 组预处理和 3 组新波形默认 VCS 三次差分、同份真实 SDF 的 CLI/census 核对，由 `run-remote.sh` 执行。最终原始文件已收集到 `remote-verified/`；`python3 validation/m4-sdf/analyze.py` 总复核 PASS。

本批没有运行新增的原生波形 overhead benchmark；Python 原型的强相关输入压缩率与吞吐仍是前批历史结果，不能用于当前原生后端或并行引擎的性能结论。下一步优先补时间单位、SDF 实例/引脚绑定、真实路径延迟与脉冲/checks；并行需自动分区/编译接入和串行基线测量。

最终远端流程退出码 0，完整 CTest 15/15；既有 27 RTL /15 gate 参考核对，13 组预处理与 3 组波形默认 VCS 各三次通过。合计 58 个正例参考（57 默认，1 历史 debug）；不将这些小例推广为完整语言/时序兼容。最终 CLI 同份真实 SDF 单次核对约 7.14s /20.78s、RSS 均 4 MiB，区别于上表 standalone 三次中位数。

证据包 `/tmp/dsim-sdf-parallel-final-evidence.tar.gz`，1327 个文件、3,619,390 字节，SHA256 `e7e71caf838f1660b0e6cf794be6fe1da11a6736bbcbddcfac8a3ca88be77198`；远端独立目录 `/tmp/dsim-sdf-parallel-final-1017-0cKmaZ`。所有实现与驱动冻结 hash 再核对相同，文档/分析器可晚于归档。
