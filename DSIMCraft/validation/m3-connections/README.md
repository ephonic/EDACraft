# M3 第二批：结构宽连接（0.6.0）

本批扩展独立 GateNetlistParser → Network → GateDesign 路线；网表仍不进入 RTL AST。支持 packed bus、部分选、嵌套拼接、RHS 常量复制、结构 assign、层次 net 端口及宽度对齐。内部结构向量可超过 64 位，测试覆盖 1024 位；RTL 测试平台的 DUT 顶层端口仍限降序 1–64 位。常量和结构索引的上限及未支持项见根 README。

## 实现与正确性

- 当前连接在 token 流上直接展开为 MSB 优先的位列表，使用后释放，不建立表达式 AST。升序/降序及非零下标按声明方向处理。
- net 端口逐位共享驱动，宽度不同保留公共低位；输入常量/补齐位使用局部驱动，输出额外高位独立补 0，inout 要求同宽。Liberty 为叶单元提供真实 pin 方向。空结构模块保留独立未驱动 net。
- 每种宽度复用一份结构复制函数；`drive_copies` 读取旧 RHS，先提交所有独立驱动再统一解析和唤醒，重复目标不暴露中间状态。原组合门等待仍先 arm 后驱动。
- 六组新增用例：`wide_connections`（256 行，位序/部分选/嵌套层次/复制/内部升序）、`wide_ports`（16 行，宽度变化/读回/冲突/inout/标量叶输出/转义名称）、`wide_constants`（1 行，1024 位内部网/数值基数/符号扩展/未知填充/空模块）、`wide_inputs`（16 行，内部写 input/宽度变化/升序及单 bit packed port/空输入）、`wide_aliases`（256 行，置换/重复/跨 net 输出的驱动读回）、`wide_atomic`（6 行，重复目标交换后 X 保持时事件计数）。共 551 行新增独立预期，原三组 84 行保留。
- 门级现有 9 个语义用例、35 个结构拒绝/5 个库拒绝、输入保护、1 个组合自反馈预算保护及 3 个 benchmark checksum smoke；前批 RTL 27 个正例、26 个拒绝与 8 个预算保护保留。RTL parser/grammar 未修改。

`generate_wide_cases.py` 用独立字符串位模型生成预期；不调用 dsim 解析或连接实现。Icarus 的端口读回/补齐、重复目标事件差异单独写入 `.icarus.json`，不混入 VCS/native 预期。

## 差分发现及保留证据

首次宽端口 VCS 对照有 12 行读回差异，见 `wide_ports.initial-diff.json`；旧 native C++/IR/trace 见 `pre-alias/`。最小端口探针 `port-probes/ports.v` 与 `ports-v2.v` 覆盖完整/选择/拼接/重复/置换连接，默认与 debug 配置各运行 3 次，原始日志和配置保留。随后修正了按位共享和宽度对齐，不以修改 VCS 模型来消除失败。

重复目标 `assign {y,y}=a` 在 a=01→10 时最终仍为 X。默认 VCS 与 native 无变化事件，Icarus 多触发一次；该差异单独保留。常量驱动的重复**端口**还有配置差异：`constant-port-probe/` 中默认 VCS 把固定输入实例的 readback 折叠为 10，而 debug/native 为 XX；动态输入实例的结果则一致。两种 VCS 配置各重复 3 次，`analysis.json` 明确标记默认差异。这一探针不计入默认通过的用例数，前批 RTL 的 repeat 配置差异与条件三态差异也继续保留。

`wide_ports` 加入名为 `g/__dsim_pin_Y` 的转义标量，检出标量叶输出扩展时的临时名称碰撞，4 行失败见 `name-collision-before.log` / `name-collision-diff.json`。最终直接连接输出低位、只给额外高位补零，删除了该临时 net 和转发过程；最终回归覆盖此名称。`pre-name-fix/` 保存修改前的 87 文件源码清单，远程初次目录 `/tmp/dsim-m3-connections-1017-tXpGaP` 的完整对照在大整数字面量处失败，未执行规模基准；失败证据见 `initial-vcs-failure/`，不用于最终性能。

## 数值字面量的 VCS/Icarus 宽度差异

首次远程完整对照在 `wide_constants` 失败：裸十进制 `4294967296`，VCS 为 0，旧 native/Icarus 为第 33 位为 1。默认与 debug 的边界值探针各运行 3 次，确认裸十进制遵循 VCS signed 32 位语义：`2147483648` 扩展为 `ffffffff80000000`，`4294967296` 截断为 0。无尺寸基数字面量则可保留更宽的自身宽度，且显式 signed 决定扩展，例如 `'d4294967296` 为 `0000000100000000`，`'sd4294967296` 为 `ffffffff00000000`。不能将所有无尺寸形式一概截到 32 位。

已修正十进制转换及扩展，并在常量主用例加入相应边界。`literal-probe/` 保存两组共 20 个探针、默认/debug 各 3 次的原始日志、Icarus 输出及最终 native 复核。native 探针将同宽 wire 声明初始化改写为等价的结构 assign，改写的文件和源 SHA 单独保存；最终常量主用例另用完全相同网表/TB 对照 VCS。`pre-literal-fix/` 保存修复前的源码清单。

## 最终复核与规模测量

最终版本 **0.6.0** 在本地 AppleClang 21 与远端 GCC 11.5 构建通过，两平台 CTest 均 **7/7**。最终 27 个 RTL 与 9 个门级 native 用例逐项复核同输入 VCS 参考，共 **36 例：35 个默认配置、1 个前批已记录的 debug 配置**。本批 9 个门级用例均在默认 VCS/native 上各运行 3 次，共 635 行独立预期；旧 RTL 参考计时不用于描述当前性能。运行时、Liberty 回放、门级前端与生成的全部 9 个模型通过 ASan/UBSan，见 `gate-sanitized.log`。

最终远程目录：`10.131.254.103:/tmp/dsim-m3-connections-verified-1017-wztvbi`；源码归档 `/tmp/dsim-connections-verified-source.tar.gz`。`source-snapshot.json` 保存归档 SHA256 及 88 个实现/测试/脚本/补丁文件；测量前后均逐项校验本地/远端源码与 16 个第三方修改文件，见 `remote-code-sha256.json` / `remote-parser-sha256.json`、`source-verification.log` / `post-benchmark-verification.log`。干净原 ZIP 上补丁重放通过；相较 0.5.0，仅 gate parser 的两个第三方文件更新，其余 14 个保持，RTL grammar 未改动。文档可晚于冻结实现归档。

所有自身性能负载串行运行，check 每规模 3 次、没有单独预热，输入刚生成，不属于冷盘基准。`parse_seconds` 包含源读取、metadata、宽连接展开和 Network 构建；`bind_seconds` 包含提前进行的 Liberty 读取/方向收集及后续模型/引脚绑定。RSS 是整进程峰值，不是 IR 或分阶段独立内存。

| INV 实例数 | 输入字节 | parse（s） | bind（s） | check 墙钟（s） | 峰值 RSS（MiB） |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100,000 | 4,755,577 | 0.60189 | 0.01473 | 0.66547 | 76.84 |
| 1,000,000 | 51,555,574 | 7.24866 | 0.15554 | 8.27325 | 706.44 |

百万实例吞吐约 13.80 万实例/s。前批历史 parse 为 6.58628s、RSS 为 704.91 MiB，本次为 7.24866s、706.44 MiB；本批增加连接语义，未宣称解析提速。共享主机未固定 affinity/frequency，两次快照未做旧/新版交替对照，不能将全部时间差直接归因于代码。百万规模名称/metadata/Network 峰值存储仍需优化。

下表为 200 周期 INV 链，每工具预热一次、轮换顺序各测 3 次的中位数；所有输出均核对 `sum=100 y=0 time=201`。CPU 为 user+system，GNU time 精度 0.01s。

| 实例数 | dsim 墙钟（s） | VCS 墙钟（s） | dsim CPU（s） | VCS CPU（s） | dsim / VCS RSS（KiB） |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.01875 | 5.26813 | 0.01 | 0.48 | 3,072 / 100,352 |
| 10,000 | 0.11482 | 3.25742 | 0.10 | 0.48 | 6,144 / 102,532 |
| 100,000 | 1.05965 | 4.28473 | 1.05 | 0.49 | 40,032 / 107,604 |

规则 INV 链可被 VCS 折叠，其 CPU 基本不随规模增加；dsim 仍逐门调度。VCS 墙钟含启动/许可证等待，不能据墙钟宣称更快或整体性能接近。实际网表与组合锥优化尚未验证。以下编译阶段每规模仅测一次，墙钟含工具启动：

| 实例数 | dsim 生成（s） | 独立 C++ 编译（s） | VCS 总编译（s） | 生成 C++ 字节 |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.01664 | 1.69744 | 11.54789 | 44,555 |
| 10,000 | 0.07832 | 1.78769 | 8.01927 | 247,565 |
| 100,000 | 0.70335 | 2.59302 | 12.87580 | 2,547,575 |

三个规模都只有一份共享 INV 求值函数；10 万门 IR 只有测试平台与端口桩两个 RTL scope，未将门实例送入 RTL AST。`large-elaboration.json` / `generated-structure.json` 保存结构和模型 SHA256；远端测量后重新生成的 C++ 与实测模型完全一致。顶层 RTL signal/process 数量不包含门级运行时对象。

`final-native-recheck.json` 保存最终 36 例复核；`vcs/`、`benchmark/`、`remote-gate/` 保存输入、逐次日志与 GNU time，`environment.json` 保存共享主机信息。远程流水线退出后收集 431 份原始文件，归档路径与 SHA256 见 `evidence-archive-sha256.json`，展开后的复核不依赖临时归档。`analyze.py` 复查 88/16 个源码校验、36 例输出、20 个字面量探针和单独的默认配置差异，重新核验规模输入/逐次日志并生成 `benchmark-analysis.json`；不重新运行计时。

## 复现

```sh
ctest --test-dir build --output-on-failure
python3 tests/gate/generate_wide_cases.py --check
# 在 0.6.0 冻结源码归档中执行（后续版本的实现校验不同）
python3 validation/m3-connections/analyze.py
# source /apps/EDAs/syn.bash 后
python3 scripts/compare_gate_vcs.py --repeat 3 --output build/vcs-gate
python3 scripts/benchmark_gate_vcs.py --parse-sizes 100000 1000000 \
  --sizes 1000 10000 100000 --cycles 200 --repeat 3 --output build/benchmark-gate
```

本批仍不支持 Verilog 行为单元模型、Liberty ff/latch、库 bus pin、结构运算/参数实例、SDF、specify/timing checks 或 Liberty/SPEF 时序。RTL signed/任意位宽、generate、存储器、函数/任务、预处理和波形继续按总计划推进。真实设计和整体 VCS 性能目标尚未完成。
