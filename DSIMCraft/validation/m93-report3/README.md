# M93 — REPORT3 修复

问题分类、修复范围及语言边界见 [REPORT3 复核](../../docs/report3-review.md)。

- `baseline.json`：上一稳定版对 arithmetic、mixed concat 和 `$bits` 字面量用例明确拒绝；保留真实诊断。
- `tests/report3`：四份带独立值检查的模型，含 136 位字面量、常量求值、函数参数、混合表达式、四态条件选择、断言多语句动作、两个实际并行分区；另保留原始 p27 源码。三后端共 31 份标准文本 VCD，四次失败预测回滚，其中零时刻检查点不先运行进程。
- 原有 strings 的字面量 X 条件期望修正为 VCS 的 packed 合并后转换；numeric-to-string 和 `$bits` 字面量从过时的拒绝清单删除，新增正例验证。
- `vcs-check.json`：四份新模型和原始 p27 源码逐字节相同，全部输出与 980 个共同物理位的完整 settled 时间线一致；无 VCS-only 位。动态 string 不作为 packed 波形，另由输出检查。
- `strings-vcs-check.json`：原有 strings/values 用例与 VCS 的全部 TRACE 相同，包含 X 字面量选择得到 `dfe` 的更正。
- `related-tests.json`：九组相关 CTest、parser 重复清理及其 ASan/UBSan 执行通过。
- `sanitizer-check.json`：16 个实际 ASan/UBSan 仿真执行，含三个后端及四次回滚；sanitized compiler 的 12 份完整 C++ 与 release compiler 相同。Leak detection disabled。
- `original-designs-check.json`：报告原测试目录中的 10 个复杂设计及 6 个旧设计均复制到隔离输出目录重新编译运行，保留源文件 hash 与完整日志。
- `linux-cross-check.json`：四份新模型在 macOS/Linux 的全部 85 项产物身份一致：16 份完整生成 C++、41 份输出、28 份 VCD 的完整逐信号流及整文件字节；未抽样。原始 p27 的三个捕获另计入 native/VCS 验收。
- `source-package.json`：1474 个包内文件与实现提交逐字节相同。
- `archives-check.json`：原始报告、VCS 同源日志/波形、原生/sanitizer C++、用户设计日志及源码包保存在测试目录的 evidence/m93-report3，未将编译产物写入 Git。

实现提交 `b457afb768342f4d6c180648eec0b0ec0990897f`（含前序 `9947952` 和 `436ad6d`）。发布前检查修复了 veSTR 内部 dump 层次路径与真实文字的区分，以及系统函数回归读取显式构建缓存；检查失败期间保留旧稳定入口。两端实际稳定入口复编均已通过。

复现：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target dsim -j4
ctest --test-dir build -R '^rtl_report3$' --output-on-failure
python3 validation/m93-report3/verify-vcs.py --native build/rtl-report3 --vcs /path/to/vcs-evidence --output /tmp/m93-vcs.json
```

远端 VCS 复现：将 `tests/report3/*.sv` 和 `tests/strings/values.sv`（重命名为 `string-values.sv`）放到 `/tmp/dsim-m93-vcs-inputs`，执行 `source /apps/EDAs/syn.bash` 后运行 `run-vcs.py`。源码不作功能性改写，dump wrapper 独立添加。VCS 有意失败的断言会打印失败诊断，动作执行次数由用例的数值检查确认。

## 稳定版本

Linux：`/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim`，release `20261025T081336Z-b457afb`。验收范围为 parser 重复清理、格式 parser、REPORT3、strings、system_functions 五组，均通过。1474 个源文件与八份 runtime 快照已核对；在 VCS 环境下从实际安装入口重编译四模型，完整 C++ 和整份 VCD 字节与 Linux 基准一致。原有其余功能由本地完整发布回归覆盖。元数据见 `release-linux-check.json` 和 `installed-linux-check.json`。

macOS：`~/vibe-coding/dsim-test/bin/dsim`，release `20261025T081316933578Z-a9da8a173a9d`。全部 76 项发布检查通过；521 个发布输入与实现提交相同，八份 runtime 快照匹配。实际入口重编译四模型，完整 C++ 与整份 VCD 字节相同。元数据见 `release-local-check.json` 和 `installed-local-check.json`。

发布源码包 SHA256：`5b714864e50738cd2d507f93b40a62df24c469d38eda48236e605cb0ff1438f9`。macOS binary SHA256：`d5109b13a6f627410e4b05532e1f66bbe02308793e0e10c8541a0eab5b72e20d`；Linux binary SHA256：`9a1bfa571f493de4e53270a8a2fb8630d6b387dcae32d4b737c838871b23b022`。
