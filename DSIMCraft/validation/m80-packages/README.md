# M80：报告 B2 package/import

用户报告仍为 `../dsim-test/rtl-tests/REPORT.md` v2，SHA256 `1e64d6f8fb92cd505b175919eee986e0ecca20f13df883f6387e4be842ca77a0`。原始 `/tmp/dsim_regress/t03_package.sv` 逐字节保存在 `tests/packages/report.sv`，SHA256 `e96512440e36856021b7e9e7eace9eacb6b6c5499b2f59e934a129052291705e`；执行结果 `T03_PACKAGE PASS`。

新增独立共享 package 符号表、显式/通配 import、qualified 类型/常量/调用；原用例所需的内置类型首组 ANSI 隐式 input 也补齐。包内 subroutine 按包的词法作用域绑定；跨模块静态局部共享、automatic 激活分开，使用既有数据依赖与 checkpoint。包时标参与 task 延迟和最低全局精度，125ps 的包延迟不再使用默认 1s 时标。运行时头文件没有修改；RTL/gate parser 继续分离。完整边界见 [packages.md](../../docs/packages.md)。

## 功能证据

- `native/results.json`：8 模型，27 份三后端完整 ordered VCD、3 次强制失败预测，14 类拒绝；多文件、Verilog 模式 package/import/endpackage 普通标识符检查。`parallel` 实际两分区；`functions` 中共享包静态状态强制留在同一分区。
- `sanitized/results.json`：sanitized compiler 生成完整 C++ 与原生一致；8 个实际程序、3 个失败预测程序、1 个实际双分区程序通过 ASan/UBSan，完整输出和 ordered VCD 一致。14 类拒绝也由 sanitized compiler 检查。关闭 leak detection。
- `parser-{native,sanitized}.stdout/stderr`：完整 parser 语义测试，包括同一 package 被两个实例导入、共享 type/parameter 指针身份及三轮重新解析/克隆/清理。语法错误 stderr 来自原有负例；sanitizer 无非法访问报告。
- `vcs/results.json`、各目录 `input.sv`/`compile.log`/`run.log`/`vcs.vcd`：真实远端 VCS W-2024.09_Full64 的 8 份相同源，使用 `-full64 -sverilog -debug_access+all -timescale=1s/1s`，源码 timescale 覆盖默认值。远端 source `/apps/EDAs/syn.bash`；`-full64` 必需。仿真不仅检查退出码，也检查 Fatal/Error 和期望输出。
- `vcs-verified.json`：8 例输出相同；7 个有时间模型共 661 个公开物理位完整时间线一致，无公开位排除。原始 report 在零时刻 finish，明确仅作输出比较。包 subroutine 局部不在 VCS `$dumpvars(0,top)` 范围；未比较的包局部名称和位数逐例列出，静态共享状态另由同源自检覆盖。

`related-ctest.log` 保留首轮既有回归日志。preprocessing 旧的“二维数组不支持”负例已在 M79 稳定版成功编译，见 `preprocess-baseline.log`；这不是本批引入的回归。将源位置诊断探针改为非法缺失赋值 RHS，独立完整重跑 preprocessing 通过，见 `preprocessing-final.log`。其余受影响回归及发布状态在最终记录中追加。

本批未测试全量 CTest、Linux 本地工具构建或新的性能比例。不修改 DWF，不修改或提交用户 `experiments/matvec16/`。

## 最终回归和稳定发布

`related-final.json`：11 项不同受影响检查最终通过（named types、automatic subroutine、ref、const ref、frontend、type signatures、packed aggregates、enum、subroutine、semantic memory 与修正后的 preprocessing）。首轮 preprocessing 过时预期的失败日志保留，其他十项首轮通过；不把首轮称为全部通过。

实现提交 `5d6bdfa5b13817a3607a8e8c03e907c975028c06`；59 项稳定发布检查全部 PASS，包括六组用户 case、六原始完整设计和报告定向检查、随机函数、package 与门级/SDF 入口。稳定入口已指向 `~/vibe-coding/dsim-test/releases/20261024T075707280245Z-ee133c7cf4d4/dsim`。

- source SHA256：`ee133c7cf4d412d9e51791d440d40538c056dd2468ff602c575251a3ea67e9ff`
- binary SHA256：`168309ccd37c67563f3617165072da7a2ffdce7844fcd3888a5569cac0bac8a3`
- `stable-identity.json`：53 个旧根模型完整 C++/输出/ordered 波形一致；31 个旧随机程序及 4 个旧 v2 程序完整 C++/输出一致，31 个随机程序完整 ordered VCD 一致；27 个新 package 程序完整 C++/输出/ordered VCD 与本批原生验收一致。八运行时头文件未改，source/runtime/binary hash 全部验证。
- `stable-{release,packages,reported-cases,rtl-report,random-functions,report-v2}.json` 与 `publish.log` 保存不可变发布清单和分组结果。发布后再次读取用户报告，SHA256 未变化。源码仍缺并发 SVA、string/enum.name、完整层次路径和文档中列出的 package 子功能。

## 复现

```sh
python3 tests/packages/regression.py build/dsim validation/m80-packages/native
python3 validation/m80-packages/run-sanitizers.py validation/m80-packages/sanitized
python3 validation/m80-packages/verify.py
```
