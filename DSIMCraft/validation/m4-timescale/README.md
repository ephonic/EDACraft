# 0.10.0：统一物理时间与 SDF 回标前置条件

本批完成模块 timescale、常量分数过程延迟、`$time` / `%t` 与受限 `$timeformat`，让生成模型的 VCD/DWF 自动采用实际仿真精度。时间格式参加检查点/预测事务，保守并行拒绝物理精度不一致的分区。SDF 的精确十进制换算已复用；**实际实例/引脚绑定、SDF 延迟回标和自动网表并行仍未完成**。

实现说明见 [时间语义](../../docs/time-semantics.md)，后续依赖见 [SDF 回标计划](../../docs/sdf-annotation-next.md)。RTL 与门级前端继续独立，门级网表没有转入 RTL AST。

最终源码冻结 143 个实现/测试/脚本文件、3 个不变的波形原型依赖与 2 个验证驱动。`source-snapshot.json` 对应 `/tmp/dsim-time-source.tar.gz`，SHA256 `5392dcd93d702a249ca8d0cf5f66df03ae4c4e6b57d03a04ff0350c0a19a341c`；文档和证据分析器可晚于归档。原始 parser ZIP 上重放 `patches/edacraft-parser.patch` 通过，17 个修改文件的 hash 见 `parser-replay-sha256.json`。

本地最终完整 CTest **17/17**，248.03s，日志 `ctest-accepted.log`。ASan/UBSan 核心 **6/6**，并执行全部七组时间用例：波形模型、预处理 roundtrip 模型、跨文件/include/CLI 默认值，共 17 次生成模型构建并逐一运行；12 个拒绝用例须正常退出，禁止把崩溃或 sanitizer 输出当成预期失败。现存 15 个生成可执行文件均核对 ASan/UBSan 符号（3 次预处理验证复用同一文件名），见 `sanitize-provenance.json`。ThreadSanitizer 并行回归通过，见 `tsan-accepted.log`。

远端最终源码在 `/tmp/dsim-time-accepted-1017-Ddkd3z` 独立编译，运行完整 CTest、七组时间差分、十三组既有预处理差分、三组原生波形差分，并核对既有 27 RTL /15 gate 参考。每组新 VCS 差分执行三次；时间用例中六组使用默认命令，`resetall` 一组明确加入 `-timescale=1s/1s`，保留逐用例 flags 和源码 SHA。最终流程退出码 0；远端 CTest **17/17**、418.74s，所有上述差分及既有参考核对通过。`final-analysis.log` 再次核对源码/输入/原始 TRACE/证据 hash，并独立解码三组 VCS/原生波形，确认均为 10ps 及相同 settled 轨迹。证据包 `/tmp/dsim-time-accepted-evidence.tar.gz`，1613 个文件、4,123,159 字节，SHA256 `fd0dd57280eda541ab4bc7c98282ff40982d5db0e6c7f236cc9b601556170b95`；详情见 `evidence-archive.json`。

七组时间用例包括混合模块尺度、局部精度舍入、小数/指数/下划线、格式化、参数化实例、未实例化模块和默认/resetall。独立固定预期先由原始 VCS 探针确认；分数用例还核对原生波形在全局 tick 1、2、15、25 的变化，不能仅比较已取整的 `$time`。预处理测试覆盖跨文件继承、include、关闭分支、CLI 默认、重新编译输出和波形单位误标拒绝。大 uint64 格式化、换算溢出及预测后格式恢复有独立内核用例。

保留的失败与修复：

- 原 lexer 将 `1.25` 截为 `1`；现在保留原文，在延迟上下文精确换算，其他 real 上下文明确拒绝。
- 初始测试用了非法 `#-1`，改为合法表达式 `#(-1)` 后暴露 parser 的空指针。旧 `gen_delay_exp` 只枚举部分表达式，未命中返回 null；现在统一保留单个表达式形状，取消把拼接误当延迟列表的分支，并正确诊断暂不支持的操作数。初始 ASan 崩溃原始日志与输入保存在 `failures/`，对应修复前源码清单 `source-snapshot-before-null-fix.json`；该源码归档另存 `/tmp/dsim-time-before-null-fix-source.tar.gz`，清单的 archive 字段保留原始产物名。
- 原负例只要求非零退出，曾将崩溃记为通过；现要求正常的非零退出并扫描 sanitizer 标记。原始失败运行日志保留，最终依据 `*-accepted.log` 和最终远端证据。
- VCS 对 `resetall` 后混合“有声明/未声明”时间单位报 NTSFM。默认命令失败保留于 `/tmp/dsim-time-final-1017-3hD4ZM/build/time-vcs/resetall/vcs-compile.log`，随后单独使用显式默认单位验证，最终批次也记录该配置。该项不伪装为默认命令通过。

这些是功能正确性验证；本批没有进行原生波形运行开销、并行净加速或 SDF 回标性能验收，不将小例结果推广为完整 VCS 兼容。
