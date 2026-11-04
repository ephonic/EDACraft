# M3 第三批：Liberty ff/latch（0.7.0）

独立门级 GateNetlistParser / Network 与 RTL AST parser 继续分开；此批只更新 Liberty 的三个第三方文件，保持上一批 gate parser 和全部 RTL parser 文件。Liberty 的 ff/latch 状态表达式编译为共享 C++ 采样/输出函数，每个实例的状态独立，网表实例不进入 RTL AST。

## 状态模型与差分

保留两个状态名、ff/latch 类型、clocked_on/next_state、enable/data_in、clear/preset 及 clear_preset_var1/2。支持正负沿、Boolean 控制、反馈、透明/保持和 L/H/N/T/X 冲突动作；两个状态变量可能非互补。初始状态为 X，存储 Z 归一化为 X；模糊边沿/使能/控制采用可能结果的共识合并。这是理想功耗、零延迟模型，不能推断所有 foundry 的 UDP/notifier 未知传播或时序等价。

首次按 Active 提交时，`seq_edges` 在第 17 行与默认 VCS 不同；原始失败和当时完全相同输入保存在 `initial-vcs-failure/`，其源码早于最终版本。`phase-probe/` 的最小 UDP 触发器/锁存器探针在 VCS 默认/debug 各执行 3 次，连续两次 #0 仍观察到旧值，而 Icarus 已更新。最终改为采样后经 NBA 唤醒提交进程，同时纯输入相关的组合输出保持 Active 响应。主用例保留 #0 与随后时刻的双阶段预期，并单独记录 Icarus 的 UDP 阶段差异；未将观测全部推迟以规避差分。

重复的下降沿/保持事件不能覆盖同刻待提交的捕获；零时间脉冲与 NBA 时钟另有用例。双异步未知控制与 N 动作的合并还检出待提交值被枚举分支意外覆盖的问题，修复前源码和输出见 `pending-conflict-before/`；所有分支现在使用同一旧值快照。

运行时以三个值类型 NBA 记录种类保留原来的赋值/部分写入行为，并支持 NBA 唤醒；不分配热路径回调闭包。每实例存储从首版 208 字节降为 20 字节（sizeof，非整进程 RSS）；ff 只监测实际控制/输出依赖，latch 另监测数据依赖。包含派生时钟依赖和锁存反馈预算保护。

## 缓存与支持边界

FTLib v14 在 v13 尾部追加完整顺序字段，并保留 v5–v13 读取。旧缓存未保存的状态名/类型不伪造为完整顺序模型。plain/gzip、ID 重映射、多库和 v12/v13 缺省已验证；新增多库测试检出旧 loader 在库容器扩容后持有悬空指针，修复前崩溃栈见 `binary-multilib-before.log`，修复后在收集完目录后重新取得指针。

本批拒绝 bank、statetable、双时钟/双使能、多个状态组、混合/缺失字段、无效冲突属性与状态名。Verilog 标准单元行为模型、库 bus pin、SDF/specify/timing checks、Liberty/SPEF 时序尚未接入。RTL 的 signed/任意位宽、generate、存储器、预处理与波形等仍按总计划推进。

另记录原 RTL lexer 的同一行多字符串缺陷：Flex 的 `\".*?\"` 采用最长匹配，将两个 `$display` 合并为一个字符串，可能静默输出源码片段。`known-rtl-string-lexer/` 保存同一行与分行输入的 native/Icarus 差分；不计入通过用例。本批保持 RTL parser 字节不变，后续 M2 需修复并加入 VCS 对照。

首次冻结后的远端流水线在性能驱动的 IR 数量断言停止：N 个 DFF、N 个 XOR 加采样复制单元实际为 `2N+1`，原断言漏计复制单元。修正仅涉及基准断言、元数据与验证驱动，三档生成网表、测试平台和预期不变，仿真器实现不变。该次失败在任何性能 warmup/run 之前发生，保存于 `initial-scale-failure/`，归档校验见 `count-failure-archive-sha256.json`；最终测量使用重新冻结的独立目录，不借用该次性能数据。

## 最终验证

本地 CTest 7/7；新增 6 组共 2623 行独立预期，在默认 VCS 各运行 3 次通过。最终 native 与本批 6 组及前批 9 组同输入 VCS 参考逐项复核，共 15 组/3258 行。42 个 RTL/门级正例中仅前批 control_loops 使用已记录的 debug 参考，其余 41 个为默认参考；前批其他已知差异仍单独保留。

本地及远端最终 CTest 均 7/7。ASan/UBSan 覆盖全部 15 组门级的前端及生成运行时；运行时和 Liberty 缓存回放也通过。包括 60 个门级/库拒绝用例、两个反馈预算保护和六个基准 checksum smoke。最终组合/时序网表规模测量和证据复核已完成。参考与性能归档分开，正确性参考的计时不作为最终性能。原始 ZIP 补丁干净重放通过，16 个第三方修改文件清单见 `parser-replay-sha256.json`。

## 最终规模与性能

远端独立目录：`10.131.254.103:/tmp/dsim-m3-sequential-final-1017-SjbjpX`，GCC 11.5 / VCS W-2024.09。`source-snapshot.json` 冻结 114 个实现/测试/脚本文件及 3 个验证驱动；测量前后逐项核对，16 个第三方文件另作校验。冻结源码包 `/tmp/dsim-sequential-source.tar.gz` 的 SHA256 为 `62e22bb08ec8f804fb9be353dfe5ef1f25afe09f4b81d62fda5c0d91f2219984`；原始证据包 `/tmp/dsim-sequential-final-evidence.tar.gz` 共 512 文件，SHA256 为 `cdd766d67a2f8d2732115db3bf330285b93ae904d3ef872adb30c92a7188a902`。归档记录见 `evidence-archive-sha256.json`，原始日志已解出到本目录。文档与分析脚本可晚于源码归档。

自有负载串行执行；parser 各 3 次，无单独预热，不能视为冷盘测量。仿真每工具预热 1 次，再轮换顺序测量 3 次，表内为中位数；CPU 为 user+system，原始精度 0.01s。共享主机未固定 CPU affinity/频率，墙钟含启动和许可证等待；编译阶段只执行 1 次。

### 独立 parser / 绑定

| INV 实例 | parse 秒 | bind 秒 | check 峰值 RSS MiB |
| ---: | ---: | ---: | ---: |
| 100,000 | 0.65968 | 0.015934 | 76.93 |
| 1,000,000 | 7.56039 | 0.155371 | 705.28 |

parse 包含读取、metadata、严格 grammar、宽连接展开和 Network 构建；bind 包含 Liberty 读取及 IR 绑定，RSS 为完整 check 进程。百万实例约 13.23 万实例/秒；本批未改 gate parser，不据共享主机的批次时间差声称 parser 优化。

### 非规则 XOR / 触发器反馈（200 周期）

每 N 个触发器对应 N 个 XOR 和 1 个采样复制单元，共 `2N+1` 个 GateDesign 实例。异步复位后按确定性非规则反馈演化，独立 bytearray 递推给出最多 64 个采样节点的末值及累加校验；这不是全信号波形比较，也不包含时序/功耗模型。

| 触发器 N | native CPU 秒 | VCS CPU 秒 | native RSS MiB | VCS RSS MiB |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.06 | 0.56 | 4.00 | 101.14 |
| 10,000 | 0.64 | 0.85 | 15.04 | 110.70 |
| 100,000 | 13.44 | 6.03 | 134.85 | 156.34 |

10 万触发器 / 200,001 个门级实例：native 墙钟 13.55s、VCS 10.72s；native CPU 为 VCS 的 2.23 倍，运行吞吐尚未接近目标。较小规模的启动开销占比较大，不能据此宣称普遍优于 VCS。

| 触发器 N | dsim 生成秒 | C++ 编译秒 | VCS 编译秒 | 生成 C++ MiB |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.036 | 2.130 | 9.892 | 0.097 |
| 10,000 | 0.196 | 2.361 | 12.507 | 0.741 |
| 100,000 | 2.141 | 5.139 | 48.502 | 8.042 |

各档均只有两个 RTL scope、三个共享输出求值函数和一个共享状态采样函数；状态只按时序实例数分配。编译表描述本基准的不同工具路线及选项，不代表等功能商业工具的编译优势。

### 组合规则链回归（200 周期）

| INV 实例 | native CPU 秒 | VCS CPU 秒 |
| ---: | ---: | ---: |
| 1,000 | 0.01 | 0.47 |
| 10,000 | 0.11 | 0.47 |
| 100,000 | 1.04 | 0.48 |

VCS 可折叠此规则链，CPU 几乎不随规模增长；dsim 仍逐门调度。原始生成/编译/运行墙钟和 RSS 保存在 `benchmark-analysis.json`，不可推广为实际设计性能。整体 VCS 目标仍需实际语料、RTL 功能覆盖及 M4 时序层。

### 下一批

- M5 先 profile 时序采样、纯状态输出重复求值、未连接 QN 驱动与 net/watcher 存储；保留此版本交替基线，新增非规则组合逻辑和实际网表。
- M3 接入标准单元 Verilog 行为模型，连接继续走独立 gate parser；支持边界与四态/事件阶段单独验收。
- M2 修复已记录的字符串 lexer 问题，继续 signed/任意位宽、存储器、generate、预处理与波形；M4 的 SDF/specify/timing checks 与 SPEF 仍为独立未完成项。

## 证据复核

`final-native-recheck.json` 保存最终 42 例复核；`local-native-repeat/`、`remote-native-repeat/` 保存 15 组最终二进制各 3 次运行；`benchmark/`、`benchmark-sequential/` 保存输入、生成 C++、IR、编译和运行原始日志。`remote-test-details.log` 包含 60 个门级/库拒绝、两个反馈预算及六个 checksum smoke。超时工具的真实父/子进程组终止探针见 `timing-timeout-check/`，派生时钟默认 VCS 三次对照见 `gated-clock-vcs.json`。

在当前最终源码运行 `python3 validation/m3-sequential/analyze.py`，可逐项验证 114/16/3 个哈希、同输入 VCS 参考、重复输出和全部 8 档原始测量，并重建 JSON 统计；结果见 `analysis.log`。旧批次时间与本批正确性参考计时均不作为本批最终性能。

## 复现

```sh
ctest --test-dir build --output-on-failure
python3 tests/gate/generate_sequential_cases.py --check
# source /apps/EDAs/syn.bash 后
python3 scripts/compare_gate_vcs.py --case seq_edges --case seq_latches \
  --case seq_async --case seq_feedback --case seq_pipeline --case seq_regions --repeat 3
python3 scripts/benchmark_sequential_vcs.py --sizes 1000 10000 100000 --cycles 200 --repeat 3
```

整体 VCS 功能与实际设计性能目标仍未完成，继续见 `plan1017.md`。
