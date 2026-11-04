# M2 第二批：左值片段与按位端口连接

版本 0.3.0。本地 macOS / AppleClang 21 与远端 Linux / GCC 11.5 的最终 CTest 均为 4/4。端到端回归包含 20 个正例、23 个拒绝用例、空层次与 IR 路径保护，以及 3 个循环预算保护。运行时另通过 ASan/UBSan 检查。

新增功能覆盖常量位选、部分选、嵌套拼接的阻塞赋值与 NBA、部分连续驱动、带实例名的标量 primitive 选择输出、选择/拼接端口，以及稀疏 net 位等价组。部分 NBA 在提交时保留最新的未写位；连续驱动各片段保留独立驱动身份。RTL 与专用门级 parser 仍独立，门级 Network 仿真适配尚未接入。

## 用例与独立预期

| 用例 | 主要检查 |
| --- | --- |
| `lvalue_blocking` | RHS 一次求值、重叠/嵌套拼接、四态、非零下标、赋值位宽、64 位边界 |
| `lvalue_nba` | 提交前后观测、部分/完整 NBA 顺序、保留其间的阻塞写入、重叠目标 |
| `lvalue_nets` | 部分驱动、冲突与释放 Z、重复 net 目标、标量门输出位选 |
| `port_parts` | 多层 inout、选择/拼接端口、冲突/释放、输出读回、方向性宽度适配、重复输出拼接 |
| `lvalue_matrix` | seed 1017，48 次四态赋值，12 次观测，含重叠片段与 64 位目标 |

生成语料的参考模型是独立 Python 位列表实现，不调用 dsim 的表达式或写入代码；分别生成 VCS 与 Icarus 的预期。`python3 scripts/generate_lvalue_matrix.py --check` 在两平台通过，确认固定输入与预期可重现。生成用例首次 VCS 差分检出了重叠拼接顺序错误；修复前日志单独保存为 `vcs-matrix-before-fix.log`，不作为通过证据。

## VCS 和最终实现复核

主机 `10.131.254.103` / `mn02`，独立目录 `/tmp/dsim-m2-parts-1017-UsKayI`；环境 `source /apps/EDAs/syn.bash`；VCS `W-2024.09_Full64`，选项 `-full64 -sverilog -top top`。

- `vcs/results.json` 及逐例日志：最终实现的 5 个新增用例，每工具各执行 3 次，全部通过。
- `local-ctest.log` / `remote-ctest.log`、`local-results.json` / `remote-results.json`：最终完整构建回归与 20 个用例的 trace。
- `local-final-native-recheck.json` / `remote-final-native-recheck.json`：重新编译执行的全部 20 例，与前批 15 例的原有 VCS golden 和本批 5 例逐项核对；同时校验输入 SHA256、固定预期和 PASS 状态。本地与远端的全部实现文件校验及结果一致。
- `source-snapshot.json`：最终上传源码归档的 SHA256 和 34 个实现/测试/脚本/补丁文件校验；对应上述最终复核。`pre-vcs-fix-source-snapshot.json` 是修复前快照，仅保留追溯用途。
- `runtime-sanitized.log`、`corpus-check.log`、`remote-corpus-check.log`：运行时 ASan/UBSan 与确定性语料检查。
- `elaboration-example.json`：真实 `port_parts` 展开结果，含左值片段、端口类别、按位连接。

旧 15 例的 Verilog 输入未变化，复用 [前批 VCS 记录](../m2-hierarchy/README.md)，未将旧时间记录归给当前实现。这里验证的是固定 trace，不是全信号波形；这些小用例不能用于宣称大规模性能或完整 IEEE 兼容性。

## 已确认的工具差异和边界

重叠变量拼接在本次 VCS 中从左向右写入，右侧重复项最终生效；Icarus 的结果相反。`lvalue_blocking`、`lvalue_nba`、`lvalue_matrix` 分别保存两套预期。net 的重复拼接仍是多驱动解析，不能应用变量覆盖规则。

VCS 的同宽 net 直接引用/选择连接支持父层驱动的内部读回；`port_parts` 中父层驱动 `external[7:4]=4'hb`，子模块内部读回 VCS 为 `b`、Icarus 为 `z`。input/inout 的 net 拼接建立按位连接；output 拼接采用方向性适配，重复连接父层 net 可以产生 X，但不反向污染子模块输出内部值。前批 `hierarchy_defaults` 的默认端口差异继续保留。合计 5 个专例记录了工具差异，其余 15 例的本地 Icarus trace 与 dsim 相同。原始 Icarus 输出见 `icarus/`，默认端口日志见前批目录。

本批未修改第三方 parser。发现原 parser 会丢弃一种无实例名的门语句，编译适配层现明确拒绝该已知形式并提示使用带实例名的 primitive，避免静默生成错误模型。动态 select、索引部分选、超过 64 位目标、signed、generate、变量输出实际连接及非同宽 inout 等仍不支持，详见项目 README。

## 复现

```sh
ctest --test-dir build --output-on-failure
python3 scripts/generate_lvalue_matrix.py --check
# 加载 VCS 环境后运行新增用例；省略 --case 可运行全部 20 例
python3 scripts/compare_vcs.py --repeat 3 \
  --case lvalue_matrix --case lvalue_blocking --case lvalue_nba \
  --case lvalue_nets --case port_parts
python3 scripts/recheck_vcs.py --native-results build/regression/results.json \
  --reference validation/m2-hierarchy/vcs-existing/results.json \
  --reference validation/m2-hierarchy/vcs-defaults/results.json \
  --reference validation/m2-lvalues/vcs/results.json \
  --output build/final-vcs-recheck.json
```
