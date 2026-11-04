# M134：package export

补齐包作用域的显式 `export p::name`、通配 `export p::*` 和 `export *::*`。支持逗号列表、重复导出、export 先于 import、多层/菱形转出，以及导出类型用于模块头部端口。保持原始声明身份；包函数使用原词法环境，变量、固定数组、task 延时和 NBA 共享原存储。RTL 与门级 parser 继续分开，运行时未改。

通配 export 仅转出实际导入的名称；未使用候选不会因下游查询而导入。显式 export 从指定候选包按直接 import 规则绑定名称，不与其他未用通配候选混淆。包内私有 import 不自动泄漏。Verilog 模式保留 `export` 标识符。

四个原始 fixture 位于 `tests/package_exports`。Mac/103 两端各通过 16 份完整有序 VCD、2 次预测提交、2 次拒绝回放、17 个负例和旧语言关键字检查。新组及原 header_imports/packages/interfaces/named_types/frontend_compat/gate_source 共七组均通过；parser 重复克隆/失败清理、格式 parser 和原生 DB 检查通过。Mac parser ASan/UBSan 完整语义套件通过，含五次导出身份和失败后重置检查；Apple ASan 不支持 leak detection，本次未声称 LSan 通过。

103 新跑 VCS W-2024.09 的四组输入与最终 DSIM 输入哈希相同。全部 TRACE、258 个共同声明位的完整 settled 时间线一致（types/chains/shared/wildcards 为 29/133/64/32 位）。这些数目包含各层次声明/别名，并非去重后的物理位数。包存储未被 VCS top dump 全部覆盖，未匹配集合保留在 `vcs.json`，共享状态另由源内断言和 TRACE 核对。双线程模式不意味着共享状态模型实际切成多个独立分区。

13 个额外边界探针中，接受/拒绝有 11 个一致；VCS 接受缺少 import 的显式 export，以及只从另一包路径导入后对原包显式 export。DSIM 按文档保留来源检查，拒绝这两个输入。`boundaries.json`、`linux-boundaries.json` 和 `vcs-boundaries.json` 明确记录差异。未宣称完整 SV/UVM、compilation-unit import、类型参数或全部 VCS 兼容；其他缺口见 [当前对照](../../docs/vcs-comparison-current.md)。

冻结实现 `5b7f9b84116eda8a7a3290cee065196927a646e2`；源码包 1731 个成员逐个匹配 Git blob 和 SHA256。Mac 稳定版 `20261028T015345690716Z-7e20214b8191`，103 Intel 稳定版 `20261028T015403Z-5b7f9b8`，三个稳定入口已核验。两端安装入口均重新生成并执行 typed-export 模型，有序波形与发布回归一致，CPP SHA256 同为 `be8c076da8956c0ba07409cb2686c793c2f4c6d6279b871a107f08a9daa36d0d`。

两端 CPU/CRC/muldiv/AXI4 的生成 C++ 与上一稳定版完全一致，八个 runtime 头文件也相同。本批功能优先，未开展性能测量或发布新的加速结论。Mac/Linux 原始证据分别逐成员核验 1962/2005 个文件；源码和证据归档保留在两端前缀 `evidence/m134-package-exports`。VCS 二进制、生成代码和私有构建目录没有导出。

`source-proof.json`、两端 release/group/entry/generation 报告、`sanitizers.json`、`audit.json` 和 `mirrors.json` 记录输入、验证与发布身份。`vcs.py` 可在 103 重做同源对照；`check-boundaries.py` 对保留的 VCS 接受结果重测 DSIM；`check-entry.py` 复验安装入口。源和原始证据归档不放入 Git。
