# M2 第三批：过程控制与性能基线

最终版本 0.4.1（控制语句基线为 0.4.0）。新增 for/while/do-while/repeat/forever、case/casez/casex，以及整数 tick 的 `$time`；循环与分支内可以使用 delay、event、NBA。RTL 与门级 parser 保持独立；门级 Network 仿真适配和大规模网表性能仍未完成。

## 功能和正确性证据

最终 macOS / AppleClang 21 与 Linux / GCC 11.5 的 CTest 均为 4/4。端到端包含 25 个正例、26 个拒绝用例、空层次与 IR 路径保护、8 个循环预算保护。运行时及 5 个新增输入的完整前端处理另通过 ASan/UBSan。

| 新用例 | 检查内容 |
| --- | --- |
| `control_loops` | 嵌套 for/repeat、动态 while、do 首次执行、未知条件、repeat 一次捕获、零/未知次数、空体、if/else 结合 |
| `control_timing` | forever 时钟、循环内 posedge/negedge 等待、#0、NBA 提交前后、delay 后恢复、独立的嵌套 repeat 计数、$time |
| `control_case` | X/Z 精确/通配匹配、首个匹配、default、不匹配保留、逗号/拼接/变量标签、共同位宽、填充常量、嵌套和挂起 |
| `control_comb` | 子模块中循环/分支、@* 对标签和分支数据的依赖 |
| `control_case_matrix` | 256 对两位四态操作数，逐对观测 case/casez/casex 的 768 个匹配结果 |

穷举预期由独立 Python 字符比较生成，不调用运行时匹配代码；`scripts/generate_case_matrix.py --check` 在两平台通过。5 个新增输入在本机与 Icarus 的 trace 相同；此前 5 个 Icarus 差异专例继续保留，因此全部 25 例中有 20 例与 Icarus 相同。

原 parser 会在语义阶段尝试展开过程循环，while/forever 的空头部可触发崩溃，动态 for 被拒绝；case 标签还可能在未设置作用域时查找变量。现将过程 loop/case/if 改为绑定全部表达式及分支，执行交给生成的控制流。generate 使用独立节点，未改成运行时循环。原 ZIP 上干净重放补丁后，11 个修改文件全部与工作树一致；Bison 冲突仍为 33 个 shift/reduce、69 个 reduce/reduce。

- `local-ctest.log` / `remote-ctest.log`：最终完整 CTest；`local-test-details.log` 保存本地正负例及预算检查详情。
- `local-results.json` / `remote-results.json`：最终 25 个 native 模型的输出。
- `runtime-sanitized.log` / `frontend-sanitized.log`：运行时及前端的 ASan/UBSan。
- `source-provenance.json`、`parser-patch-replay.log`、`parser-replay-sha256.json`、`parser-generation.log`：本批第三方修改、重放及生成器证据。
- `corpus-check.log` / `remote-corpus-check.log`、`icarus/`：确定性语料检查及新增输入的 Icarus 原始输出。

## VCS 配置差异：明确保留默认失败

主机 `10.131.254.103` / `mn02`，工作目录 `/tmp/dsim-m2-control-1017-4FOZrl`，环境 `source /apps/EDAs/syn.bash`，VCS `W-2024.09_Full64`。默认编译选项为 `-full64 -sverilog -top top`。

控制语句基线 0.4.0 的新增 4 例在默认 VCS 配置下每工具各执行 3 次，通过，见 `vcs-normal/results.json`。`control_loops` 默认 VCS 的最终 q 为 2，dsim/Icarus 为 59；同一输入加 `-debug_access+all` 后 VCS 为 59，重复 3 次通过，见 `vcs-repeat-debug/results.json`。因此不能声称默认 VCS 配置下全部 25 例一致：24 例默认配置一致，另 1 例使用明确记录的 debug 配置。

分离探针定位到 X/Z repeat 次数与常量赋值组合：默认配置下 `repeat(4'b0x01) q=0;` 将 q 从 57 改为 0；加入 debug 选项后保持 57。独立加一计数探针中，默认 VCS 对同类未知次数也跳过。代码保留未知次数跳过的规则，没有将这个与 VCS 优化配置相关的行为写入语言实现。失败报告、完整输入和默认/debug 原始日志保存在 `vcs-optimized-difference/`，该失败不计作通过。辅助 Icarus 动态 X repeat 探针在 2 秒预算内未完成，也按超时保存，不列为通过用例。

优化后的 0.4.1 重新编译执行全部用例；`local-final-native-recheck.json` / `remote-final-native-recheck.json` 将最终 25 个 native 输出与同输入 VCS 参考逐项核对，包括输入 SHA256、预期和 PASS 状态；其中该 repeat 例引用 debug 配置。上述差分中的 dsim 计时属于 0.4.0，最终性能以单独的 0.4.1 benchmark 为准。前 20 例复用 [层次](../m2-hierarchy/README.md) 和 [左值](../m2-lvalues/README.md) 的不变输入参考。两平台的最终实现校验一致，`source-snapshot.json` 保存最终 0.4.1 归档和 42 个实现/测试/脚本/补丁文件的 SHA256；`pre-specialization-source-snapshot.json` 记录性能优化前的 0.4.0 实现；`initial-source-snapshot.json` 是增加比较脚本的显式 VCS 参数选项之前的快照。

## 性能测量范围

`scripts/benchmark_vcs.py` 生成两类逐级增大的相同输入：32 位 LCG 算术循环、时钟/边沿/NBA 调度。算术结果用仿射变换快速幂独立计算，时钟结果用次数和仿真时间核对。每例每工具预热一次，再交替次序各运行 3 次；所有工作负载串行执行。编译和运行分开计时，不开启波形，VCS 使用默认优化配置。记录版本、输入 SHA256、命令、墙钟时间、CPU 用户/系统时间及峰值 RSS。

0.4.0 基线见 `benchmark-before/`，0.4.1 最终数据和原始日志见 `benchmark/`。二元运算符现以编译期模板参数生成，去掉运行模型中的字符串分派；算术模型的符号检查见 `arithmetic-symbols.log` / `arithmetic-specialized-symbols.log`。启动开销会影响小负载，不能仅依据墙钟比值声称核心执行速度或整体性能接近 VCS；本批仍不覆盖大规模门级、真实 RTL 语料、SDF/Liberty/SPEF 时序或完整 VCS 功能。初步并发探索的计时未作为最终数据，最终记录来自随后串行重测。


| 负载 / 次数 | dsim 优化前墙钟 s | 优化后墙钟 s | VCS 墙钟 s | dsim / VCS 总 CPU s |
| --- | ---: | ---: | ---: | ---: |
| arithmetic / 100,000 | 0.0522 | 0.0084 | 5.2574 | 0.00 / 0.48 |
| arithmetic / 1,000,000 | 0.4223 | 0.0304 | 3.2798 | 0.02 / 0.47 |
| arithmetic / 10,000,000 | 4.1026 | 0.2102 | 5.2893 | 0.20 / 0.53 |
| clocked / 100,000 | 0.0534 | 0.0490 | 5.2736 | 0.04 / 0.52 |
| clocked / 1,000,000 | 0.4849 | 0.3794 | 3.4120 | 0.37 / 0.72 |
| clocked / 10,000,000 | 4.7460 | 3.6864 | 4.4711 | 3.67 / 1.78 |

1000 万次算术循环的墙钟改善约 19.5 倍；时钟/NBA 改善约 1.29 倍。VCS 的启动等待约为数秒，不能把墙钟比值当作核心速度。以 100 万到 1000 万次的 CPU 中位数增量粗略扣除固定开销，dsim/VCS 比值为算术约 3.00、时钟/NBA 约 3.11；仍有差距。该估算受 CPU 时间量化、共享主机负载和样本数影响，不是严格的核心耗时测量。原始数据及计算结果见 `benchmark-analysis.json`；主机配置与未固定 affinity/frequency 的限制见 `benchmark-environment.json`。

## 复现

```sh
ctest --test-dir build --output-on-failure
python3 scripts/generate_case_matrix.py --check
# source /apps/EDAs/syn.bash 后
python3 scripts/compare_vcs.py --repeat 3 \
  --case control_timing --case control_case --case control_comb --case control_case_matrix
python3 scripts/compare_vcs.py --repeat 3 --case control_loops \
  --vcs-flag=-debug_access+all
# 去掉上述 debug 选项可重现已记录的默认配置差异
python3 scripts/benchmark_vcs.py --iterations 100000 1000000 10000000 --repeat 3
python3 scripts/recheck_vcs.py --native-results build/regression/results.json \
  --reference validation/m2-hierarchy/vcs-existing/results.json \
  --reference validation/m2-hierarchy/vcs-defaults/results.json \
  --reference validation/m2-lvalues/vcs/results.json \
  --reference validation/m2-control/vcs-normal/results.json \
  --reference validation/m2-control/vcs-repeat-debug/results.json \
  --output build/control-final-vcs-recheck.json
```
