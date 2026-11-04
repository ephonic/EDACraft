# M2 第一批：RTL 层次与端口验证

最终 macOS / Linux CTest 均 4/4 通过。端到端回归包含 15 个正例、18 个拒绝用例、空模块层次与 IR 输出路径保护、2 个零延迟循环保护用例。

新增 5 个正例：`hierarchy`（多层、位置/命名参数、独立实例与依赖 localparam）、`hierarchy_nets`（inout、多驱动冲突/释放、output net 读回、不同 packed 下标范围）、`hierarchy_ports`（非 ANSI、output reg、宽度适配、输入表达式/选择/拼接、空端口）、`hierarchy_events`（多层时钟传播、不同参数的状态与 NBA）、`hierarchy_defaults`（连接/省略/显式空连接的输入默认值和顶层输入）。

## VCS 与最终源码

服务器：`10.131.254.103` / `mn02`；环境：`source /apps/EDAs/syn.bash`；VCS：`W-2024.09_Full64`，参数 `-full64 -sverilog -top top`。工作目录：`/tmp/dsim-m2-1017-seckXp`，最终源码和完整回归位于其 `final/` 子目录。

- `vcs-existing/results.json` 和对应日志：10 个基线用例 + 4 个新增层次用例，每工具各运行 3 次，全部通过；这里记录的是输入默认值补充实现之前的编译器时间快照。
- `vcs-defaults/results.json` 和对应日志：最终代码上的默认端口用例，每工具各运行 3 次，通过。
- `local-ctest.log` / `remote-ctest.log`：最终完整 CTest。
- `local-results.json` / `remote-results.json`：最终代码重新编译和执行全部 15 个正例的输出。
- `local-final-native-recheck.json` / `remote-final-native-recheck.json`：重新核对全部 15 个最终 native 输出与上述 VCS golden，同时检查输入 SHA256、固定预期与 PASS 状态；包含自研源码、测试、脚本和 parser 补丁校验。两台机器的实现校验和行为结果完全一致。
- `source-snapshots.json`：首次时间快照与最终源码归档的 SHA256，以及关键文件校验。早期时间不用于描述最终编译器性能。
- `elaboration-example.json`：真实层次展开输出，包含实例路径、参数位串、信号别名和端口类别。

这些微型用例验证行为，尚不代表大规模门级网表的解析或仿真性能；也不代表完整 IEEE 语义覆盖。

## 已记录的工具差异

`hierarchy_defaults` 的参考行为按 VCS W-2024.09：省略 `.a` 时使用默认值，显式 `.a()` 保持 Z，顶层 net 输入保持 Z、顶层变量输入保持 X。该用例中 Icarus 对显式空连接使用默认值，顶层变量输入为 Z。`icarus-defaults.log` 保存其输出，`tests/regression.py` 明确记录两组预期。其余 14 个正例在本机与 Icarus 的 trace 相同；没有将这一已知差异统计为两工具完全相同。

## 复核命令

```sh
ctest --test-dir build --output-on-failure
python3 scripts/compare_vcs.py --repeat 3
# 或仅运行一个新用例
python3 scripts/compare_vcs.py --case hierarchy_defaults --repeat 3
# 检查最终 native 回归与本次已存 VCS 证据
python3 scripts/recheck_vcs.py --native-results build/regression/results.json \
  --reference validation/m2-hierarchy/vcs-existing/results.json \
  --reference validation/m2-hierarchy/vcs-defaults/results.json \
  --output build/final-vcs-recheck.json
```

门级网表专用 parser 与 RTL parser 的分工见 `docs/frontend-design.md`；本批没有接入门级 Network 仿真适配。
