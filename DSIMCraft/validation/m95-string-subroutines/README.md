# M95 — 标量字符串子程序

支持范围和剩余边界见 [字符串](../../docs/strings.md)。RTL parser 独立增加字符串函数调用的类型传播及 typedef 签名；编译器将形参/返回变量声明为真实字符串槽，按形参选择转换并保留字符串表达式标记，ref 额外检查字符串类型身份。运行时复用原有不可变 V、自动激活帧和检查点，无新全局字符串状态。门级 parser 和 DWF 未修改。

`tests/string_subroutines` 七份源分别覆盖 ANSI/经典声明、命名/default/空实参、input/output/inout、ref/const ref 的延迟别名、自动调用重叠与延迟 RHS、static/automatic 返回生命周期、直接递归、方法 receiver、字符串函数表达式事件和实际双分区。正例有独立值检查；双分区模型通过每域错误计数和导出数值时间线检查，不在域内执行会合并分区的诊断任务。

- `baseline.json`：原稳定版对字符串形参和返回值明确拒绝，保留真实诊断。
- `native-check.json`：三后端 46 份标准文本 VCD、4 次失败预测回滚、11 个精确诊断拒绝案例，实际双分区。
- `vcs-check.json`：七份源逐字节相同，全部输出与 513 个共同物理位完整 settled 时间线相同，无额外未比较位。字符串不伪造为 packed 波形，由输出、自检和数值观测验证。
- `sanitizer-check.json`：sanitized/release 编译器的七份完整 C++ 相同；九次实际生成程序 ASan/UBSan 执行，包括重叠任务、ref、递归、事件、双分区和两次回滚。已有 parser 泄漏未在本批处理，leak detection disabled。
- `related-tests.json`：八组既有字符串、命名类型与数值子程序/引用/automatic/REPORT3 回归通过。

调试中保留两次新测试的分区失败记录：测试在各 lane 执行 `$fatal`，会按既有副作用顺序约束合并为单域；改为各域计数并由波形检查后得到两个真实分区。另将空 task 负例补为 `begin/end`，使错误来自目标类型检查而非空 body 的语法错误。VCS 产物导出使用源码/日志/波形归档，避免其重编译后遗留的 csrc 失效链接；未删除或改写仿真失败结果。

函数中的系统任务语句仍按既有范围拒绝。输出参数的默认空串检查通过返回哨兵并在调用方断言完成，未将函数内 `$fatal` 宣称为已支持。此前调试日志保留在原始归档。

复现：

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target dsim -j4
ctest --test-dir build -R '^rtl_string_subroutines$' --output-on-failure
python3 validation/m95-string-subroutines/verify-vcs.py --native build/rtl-string-subroutines --vcs /path/to/vcs-evidence --output /tmp/m95-vcs.json
```

VCS 运行复用 `validation/m94-report4/run-vcs.py`，将七份原始 SV 复制到输入目录，加载 `/apps/EDAs/syn.bash` 后使用 `--inputs INPUT --output OUTPUT`。它只附加独立 dump wrapper，不改写设计。

稳定发布增加显式 `--check-group` 模式，默认全量行为保留；选择模式仍执行 parser/format 检查、冻结八份运行时、验证发布输入哈希并在所有选定检查通过后原子切换入口。范围保存在 manifest，不把选择检查声明为全库回归。原有默认全量分支的 77 条 Python 检查语句按 AST 核对保持相同，另增加新字符串组的两条语句，见 `publisher-review.json`。

## 发布与跨平台验证

实现提交 `4db41acb9c5cbe0629987244ec5e6be520c67b1d`。源码包全部 1489 个文件与该提交逐字节核对，见 `source-package.json`。原始 C++、SV、标准文本 VCD 和各阶段日志（含调试失败）保存在测试目录 `evidence/m95-string-subroutines/raw-evidence.tar.gz`；源码包另存，哈希见 `archives-check.json`。

macOS 稳定入口已更新至 `20261025T091832076424Z-792c86153134`。发布范围为 parser、format_parsers、string_subroutines、strings 四组；535 个发布输入和八份运行时快照与实现提交匹配。实际安装入口重新编译七模型，完整 C++、输出和整文件 VCD 与原生验收一致，见 `release-local-check.json`、`installed-local-check.json`。

Linux 新增模型组的 46 捕获、4 回滚和11拒绝已通过，且与同源 VCS 的 513 位完整时间线一致，见 `vcs-check-linux.json`。两端全部25份C++、46份输出、46份整文件VCD逐字节相同，见 `cross-platform-check.json`。

Linux 两个稳定入口 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 已切换至 `20261025T091854Z-4db41ac`。发布范围为 parser、format_parsers、string_subroutines、strings、ref_arguments 五组，其中原有引用组含77捕获、5次失败预测及实际双分区。加载 VCS 环境后从安装入口再编译七模型，完整 C++、输出和整文件 VCD 与 Linux 基准相同；1489 个源码文件、八份运行时和二进制哈希复核通过。见 `release-linux-check.json`、`installed-linux-check.json`。

macOS binary SHA256：`6d6ce7697faeb10a1c80903d89f2121ec63ddbf2750eccfc1fbbe50bb7319834`；Linux binary SHA256：`40a5bbb593619f25464a8cbebd9b3f1335e4b5933c140ba9897879e0c0b4e6a6`。源码包 SHA256：`ea89967eac69048b9475b57a3beeb837fec0a3cc475345b2b4599a9c02922127`。没有新增性能测量或完整 SV/VCS 兼容结论。
