# M3 首批：独立 Network 组合门级仿真

最终实现版本 0.5.0。`--gate-netlist` / `--gate-top` 经专用 GateNetlistParser → Network → 拥有数据的 GateDesign IR，绑定 Liberty 组合 function/three_state；RTL 测试平台只解析 DUT 端口桩。每种单元编译一份 C++ 求值函数，各实例保存整数连接表，多个 DUT 独立安装到同一四态事件运行时。

## 功能与边界

支持 ANSI/非 ANSI 结构模块、标量模块层次、具名叶单元引脚、已声明端口顺序的标量位置连接、结构 assign、标量四态常量及明确位选；顶层端口可为降序 1–64 位 packed bus。输出 pin 的驱动 ID 独立分配，不依赖时序 Network 的单 driver 字段或 blackbox 推测方向；缺省/空引脚使用独立的未连接 net。Liberty 支持组合多输出、前/后缀反相、XOR、显式/隐式 AND、OR、括号、常量及 three_state，理想供电、零延迟。

专用 parser 的原时序模式会略去过程块或将运算近似为一个网络引用。新增显式仿真 grammar 检查按 token 流拒绝这些输入，不创建 RTL/表达式 AST。读取一次文件，metadata/建网复用 source view。绑定后释放 Network 名称、metadata 与查找表，IR 只保留 net 常量状态、每种模型、每实例的模型 ID/pin 起点和连续连接表。

本批尚不支持 Verilog 单元行为模型、Liberty ff/latch、inout cell pin、层次向量端口、一般 bus/拼接/部分选连接、结构表达式、参数实例、过程块、门延迟、SDF、specify/timing checks、Liberty 时序表或 SPEF RC。含方括号/单引号的转义标量名及文字常量同名的标量明确拒绝，避免现有 Network 文本命名的歧义。Liberty 三态禁用条件未知时保守驱动 X，数据为 Z 也如此；这与通用表达式 mux 的逐位合并分开实现。

## 正确性与回放

- `four_state`：64 对三输入四态组合，两份 DUT 的位序、状态隔离、多输出、缺省/空 pin，以及三态 bus 与测试平台驱动冲突，共 64 行独立预期。每份设计 9 个叶实例/assign，仅 7 种模型；RTL IR 只有 testbench 与两份端口桩共 3 个 scope。
- `hierarchy`：标量多层位置/具名连接、内部 net、常量及未驱动输出；4 行独立预期。DUT 内部层次不进入 RTL AST。
- `connections`：同一单元两个输出接同一 net、未连接但内部驱动的层次 port、层次 X/Z 常量、缺省输入、非零下标的一位 packed port、转义内部网/实例名；16 行独立预期。

以上三例共 84 行预期由 `tests/gate/generate_cases.py` 的独立标量真值/解析模型给出。另有 33 个门级结构/库拒绝用例、输入覆盖保护，单个单元自反馈的预算保护，以及 3 个含奇/偶链长和周期数的 benchmark checksum smoke（native 与 Icarus）。前批 RTL 的 27 个正例、26 个拒绝用例、空层次/IR 路径保护和 8 个预算保护继续保留。

新增运行时测试穷举 16 对三态禁用/数据状态。Liberty three_state 字段经 FTLib v13 尾部追加保存，`liberty_model_roundtrip` 覆盖 plain/gzip、字符串 ID 重映射与 v12 字段缺省；原 v5–v12 读取分支保持。运行时、Liberty 字段回放及三组门级的前端/生成模型另有 ASan/UBSan 记录。

最终本地 AppleClang 21 / 远程 GCC 11.5 的 CTest 均 **7/7**。最终 native 的 27 个 RTL + 3 个门级用例共 30 例均复核同输入 VCS 参考，其中 29 例默认配置、1 例为前批明确记录的 debug 配置；本批新增 3 个门级用例在默认 VCS 与 native 各运行 3 次。VCS 读取相同网表/测试平台及独立 Verilog cell model，不读取 Liberty；dsim 由 Liberty 生成模型。三组门级新增 84 行 trace 比对，尚非全信号波形等价证明。

`final-native-recheck.json` 汇总这 30 例的 trace、输入校验、参考路径及 VCS 选项。`local-ctest.log` / `remote-ctest.log` 是最终完整 CTest；`local-test-details.log` 和 `local-gate/` 保留本地逐例日志及生成的负例/IR。`local-rtl-results.json` / `remote-rtl-results.json`、`local-gate-results.json` / `remote-gate-results.json` 保存最终 native trace；旧 RTL 的最终 VCS golden 复核见 `local-final-rtl-recheck.json` / `remote-final-rtl-recheck.json`，计时仍归各自历史快照，不用于描述本版性能。

## 三态差异：保留失败与修复依据

初版门级 three_state 使用通用 mux 合并；数据为 Z 且使能 X/Z 时得到 Z，与 Icarus 条件表达式模型一致。默认 VCS 在本例 64 行中有 11 行不同：它保守驱动 X，可能进一步与测试平台驱动形成冲突。初次差分按失败保存在 `vcs-tristate-difference/initial/`，包含初版 63 文件源码清单、失败 JSON、编译/运行日志和预期；原条件模型也单独保存为 `cells-conditional.v`。没有将该失败计为通过。

最小 `tri-probe.v` 分别观测直接条件连续驱动、反向条件写法及 cell 输出。VCS 默认和 `-debug_access+all` 两种配置各执行 3 次，数据为 Z、使能 X/Z 时均为 X；dsim 的 RTL mux 和 Icarus 为 Z。`tri-explicit.v` 用显式四态 truth function 建模同样输出，默认 VCS 的 cell 输出可得到 Z；该探针也重复 3 次。原始日志及独立断言结果见 `vcs-tristate-difference/probes/` 和 `probe-analysis.json`。

最终门级实现用独立 `tristate()` 驱动规则跟随 VCS 的未知禁用条件 X 行为，不更改 RTL 通用 mux。`four_state.expected.json` 与 `four_state.icarus.json` 分别保留 VCS/native 与 Icarus 的预期。这增加一项明确的 Icarus 差异；原 RTL 的 5 项差异继续保留。RTL 同形条件连续三态驱动仍存在上述已测差异，是待完善的兼容边界，不能宣称通用 RTL 三态条件已经全部匹配 VCS。

前批 `control_loops` 的默认 VCS q=2 / debug q=59 差异也继续保留，见[前批控制语句记录](../m2-control/README.md)；该例的最终 RTL 复核仍明确引用 debug 配置，不计作默认通过。

## 单元自反馈的 delta 保护

门级组合驱动与 RTL 连续驱动一样，需要在输出写入前 arm 输入等待。收尾探针先把 `Y=A*~Y` 的 A 置 0，待 Y 稳定为 0 后再将 A 置 1；旧顺序在写完 Y 后才登记等待，漏掉自身引发的输入变化，并错误结束于 Y=1（`feedback-before.log`）。现改为先 arm 再求值/驱动，后续 delta 重新求值，达到预算后明确报错；CTest 增加这个门级预算保护，见 `feedback-after.log`。RTL 原有连续驱动本来已经先 arm，没有更改过程 always 的敏感语义。

`pre-feedback-source-snapshot.json` 和 `pre-feedback/` 保留三态修复后、自反馈修复前的实现及测量，不能作为最终性能。最终源码与测量单独保存。

## 源码与测量目录

初版差分目录 `10.131.254.103:/tmp/dsim-m3-gate-1017-bLx0Ua` 保留原始失败及探针。三态修复快照目录 `/tmp/dsim-m3-gate-final-1017-JH17S6` 保留中间测量；最终隔离目录 `/tmp/dsim-m3-gate-verified-1017-VsWcDA` 另修复自反馈敏感登记。环境入口 `source /apps/EDAs/syn.bash`；VCS `W-2024.09_Full64`，native 编译为 C++17 / O2。

`source-snapshot.json` 保存最终上传归档 SHA256 和 64 个自研实现/测试/脚本/补丁文件的清单，说明文档可晚于实现归档。`source-provenance.json` 记录原 ZIP；`parser-replay-sha256.json` / `parser-patch-replay.log` 验证当前补丁可在干净 ZIP 上重放，共 16 个第三方修改文件（前批 11 个 RTL 文件保持，新增 5 个 gate/Liberty 文件）。本轮未修改 RTL grammar，也未重新生成 Flex/Bison 文件。

`--gate-check` 的计时不含 RTL、C++ 生成/编译或仿真：parse 包含源读取、metadata、严格 grammar 和 Network 构建；bind 包含 Liberty 读取/解析及模型/引脚绑定。解析/绑定每规模串行执行 3 次，无单独预热；输入刚由脚本写入，不属于冷盘读取基准。JSON 的 `warmup_runs_per_tool` 只用于后面的仿真测量。`/usr/bin/time -v` 的峰值 RSS 是整个 check 进程的峰值，包含 Network 与 IR 共存及释放的过程，不冒称为各阶段独立峰值。

端到端基准用可重复生成的 INV 链，分别记录 dsim 生成（含 parse/bind/RTL）、独立 C++ 编译、VCS 总编译和仿真。每工具每例预热 1 次，轮换顺序各执行 3 次，所有自身性能负载串行；闭合形式计算输出、计数和时间。INV 链高度规则，VCS 可以折叠，不能代表真实门级设计；启动/许可证等待也会影响墙钟。主机为共享环境，未固定 CPU affinity/frequency。

## 最终规模与性能基线

以下各项取三次测量中位数；峰值 RSS 一栏为各次峰值的中位数。解析/绑定仅测 dsim，尚无同口径 VCS parser 单独基线。

| INV 实例数 | 输入大小（字节） | parse（s） | bind（s） | check 进程墙钟（s） | 峰值 RSS（MiB） |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100,000 | 4,755,577 | 0.56745 | 0.01620 | 0.64418 | 76.69 |
| 1,000,000 | 51,555,574 | 6.58628 | 0.15549 | 7.66307 | 704.91 |

百万规模的 parse 吞吐约 15.18 万实例/s；它包含严格检查与 Network 构建。当前峰值内存仍有明显优化空间，不能把紧凑最终 IR 的逻辑表大小当成解析进程的 RSS。

下表为 200 周期 INV 链的运行测量；所有规模的 native/VCS 输出均为独立计算的 `sum=100 y=0 time=201`。CPU 是 user+system，GNU time 精度为 0.01s。

| 实例数 | dsim 墙钟（s） | VCS 墙钟（s） | dsim CPU（s） | VCS CPU（s） | dsim / VCS RSS（KiB） |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.01958 | 3.27301 | 0.01 | 0.48 | 3,072 / 105,036 |
| 10,000 | 0.11614 | 3.26808 | 0.10 | 0.48 | 6,144 / 109,632 |
| 100,000 | 1.04930 | 3.26200 | 1.03 | 0.48 | 41,848 / 109,628 |

VCS 在此规则链上的 CPU 基本不随实例数增加，符合链折叠优化的特征；dsim 仍逐单元事件执行，运行成本随规模增加。VCS 墙钟含较大的启动/许可证等待，不能从墙钟推断 dsim 更快，也不能用接近零的 VCS CPU 增量估算稳定速度比。此处已有明确的门级优化缺口，真实设计性能尚未测量。

以下编译阶段各测量一次，墙钟包含工具启动，不能作为稳定吞吐比：

| 实例数 | dsim 生成（s） | 独立 C++ 编译（s） | VCS 总编译（s） | 生成 C++ 大小（字节） |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.01589 | 1.74424 | 9.73332 | 43,896 |
| 10,000 | 0.07204 | 1.77550 | 8.07346 | 246,906 |
| 100,000 | 0.66758 | 2.66624 | 11.94411 | 2,546,916 |

三个规模均只有一份共享 INV 求值函数；增加的是连接表。`large-elaboration.json` 的 100,000 实例仍只有 testbench 与端口桩两个 RTL scope，`gate_design` 单独记录 100,000 个门级实例。顶层 `signal_count` / `process_count` 仅统计 RTL 部分，不是整个运行时的总数。测量后重新生成的 C++ SHA256 与实际测量的模型相同，见 `generated-structure.json` / `post-benchmark-verification.log`。

原始结果及输入、逐次日志、GNU time 文件位于 `vcs/`、`benchmark/`、`remote-gate/`；环境见 `environment.json`。`benchmark-analysis.json` 保存上述计算，`analyze.py` 可重查 64 个实现文件、16 个 parser 文件、30 例最终 trace、所有规模输入/预期和逐次运行日志。最终远程源码/第三方校验分别见 `remote-code-sha256.json` / `remote-parser-sha256.json`。远程证据归档的路径及 SHA256 另存 `evidence-archive-sha256.json`；本地已展开保存，复核不依赖归档仍在临时目录。

## 复现

```sh
ctest --test-dir build --output-on-failure
python3 tests/gate/generate_cases.py --check
# 在本批 0.5.0 源码归档中执行（后续版本的实现校验会不同）
python3 validation/m3-gate/analyze.py
# source /apps/EDAs/syn.bash 后
python3 scripts/compare_gate_vcs.py --repeat 3 --output build/vcs-gate
python3 scripts/benchmark_gate_vcs.py --parse-sizes 100000 1000000 \
  --sizes 1000 10000 100000 --cycles 200 --repeat 3 --output build/benchmark-gate
# 不依赖 VCS 的解析/绑定测量
python3 scripts/benchmark_gate_vcs.py --parse-only --parse-sizes 100000 1000000
```

这是一批组合门级接入，完整 M2/M3/M4 和真实设计性能目标仍未完成，继续按 `plan1017.md` 推进。
