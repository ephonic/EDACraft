# M102：运行参数与动态格式化

实现 `$test$plusargs/$value$plusargs`、`$sformatf/$sformat`，接入生成程序的真实 argv、依赖/写入分析、automatic/ref、线程分区、检查点及回滚。另修复 packed `%s/%0s` 的零字节/未知字节显示，增加 `%c`。RTL 与门级 parser 继续分开。

七个同源模型在103的 VCS W-2024.09_Full64 上重新编译运行：27行完整用户TRACE、1553个数值物理位的全部 settled 时间线一致，另有三组缺失/非法/空值/溢出参数输出一致。VCS不dump的128个数组位单独记明，数组写回由stdout及本机全流回放观察，不算入VCS位覆盖。原始输入sha256、逐模型argv、完整输出和位数见 `vcs-alignment.json`，重放工具为 `run-vcs.py`、`verify-vcs.py`；`boundary-probes.json` 保存补充探针观察，不把额外探针全都算作永久对齐覆盖。

新回归组每端检查49份完整VCD，普通队列/时间轮/线程后端、无波形程序、真实两分区、7次失败预测回滚、8项编译拒绝、6项动态运行拒绝。额外三组argv在四种生成程序上运行，原生波形选项与plusargs交错传入。旧字符串、整数方法、字符串子程序及final/bind定向回归见对应JSON。实际生成程序 ASan/UBSan、冻结运行时与源码Git身份、两端发布及入口重生成证明见下文。

支持范围与明确拒绝的格式见 [功能文档](../../docs/testbench-io.md)。本批没有重测性能，不把测试模型通过解释成完整SystemVerilog或VCS功能覆盖。

原始完整VCS编译/运行日志及VCD保存在忽略的 `reference/vcs/`，可由脚本和固定输入重新产生。这些不可变证据已归档至本地和103的稳定安装目录。

实现源提交为 `511594bb8e8662bd43c83f1f60091e82e35be176`，两端各八项针对性发布检查通过（parser、格式parser、原生DB、新功能组、strings、final/bind、cases_archive、gate_source）。七份实际生成的无波形程序通过 ASan/UBSan，代码哈希与两端稳定版相同。629份macOS输入、1590份源码包文件与Git相符，两端各八份冻结头文件核对；实际安装入口各重生成14份C++，并编译运行带运行参数、automatic/ref、格式化和final的组合模型。跨平台100份C++、129份VCD、179份运行输出逐字节相同。见 `release-summary.json`、`release-macos.json`、`release-linux.json`、两个 `vcs-alignment-*-release.json`。

稳定入口为 `~/vibe-coding/dsim-test/bin/dsim` 和103的 `/apps/EDAs/own/dsim/bin/dsim`（别名 `/apps/EDAs/own/dsim/dsim`）。macOS发布目录 `20261025T134626704467Z-5fdcad06e86e`，二进制SHA256 `3e886cc167cea07d1e426f8cf0b85bbee6d92b1eba42f24122c948ab0c4ad36d`；Linux发布目录 `20261025T134633Z-511594b`，二进制SHA256 `f6ebe1ea49b344d06ccad1004de4ef428bbe864e04807f3c257c9b13fa41e6bb`。

原始VCS输出/波形和sanitizer日志归档的SHA256分别见 `vcs-artifact.json` 与 `sanitizer-artifact.json`；源码归档身份见 `source-package.json`。完整证据存入两端稳定安装根目录的 `evidence/m102-testbench-io/`，不把生成物或用户未跟踪的实验目录加入Git。
