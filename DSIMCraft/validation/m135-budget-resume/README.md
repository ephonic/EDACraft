# M135：过程预算中断恢复

本批补充生成过程 PC 指令边界的安全恢复；普通函数内部或自定义 callback 的部分执行不属于该保证。范围及计步语义见 [budget-resume.md](../../docs/budget-resume.md)。没有性能测量或完整 VCS 对齐声明。

新增 `rtl_budget_resume` 回归，四个模型对照同源不间断运行的完整输出、有序波形和计步：552 个恢复场景（含 12 个多次分块场景），另有 164 个无波形 checkpoint 恢复场景。函数负例单独检查不可恢复异常不会被安全重入逻辑捕获。

稳定发布同时检查 `typed_stores` 的历史预算/恢复/预测差分、`package_exports` 和 `gate_source`，以及 RTL/格式 parser、原生 DB 单元测试。最终的平台结果、内核检查及安装入口检查写入同目录 JSON；原始运行产物保留在对应不可变 release 目录。

预算暂停/恢复是 DSIM 的 C++ 运行时 API，没有直接对应的 VCS CLI 操作；这里以同源不间断运行作为恢复语义的 oracle，不能把两个 DSIM 后端一致当作新的 VCS 兼容性证明。

实现冻结提交 `22800c2ed65c6a743f38426d20f90439dded6ac3`；源码归档 1734 个成员逐个匹配 Git。`source-proof.json` 保存归档 SHA 与提交身份。生成过程正常执行结果另用五组 VCS TRACE 对照，未将其记作 VCS 预算恢复测试。

macOS 另通过 13 项内核检查，以及实际生成的四个恢复程序共 48 次 ASan/UBSan 运行；未启用 LeakSanitizer。函数负例的 63 次不可恢复中断属于明确限制，不记作恢复成功。

Mac 稳定入口已通过真实重新编译和有序波形核验；`mac-entry.json` 绑定二进制和生成代码 SHA。完整 release 内保留各回归原始产物，Mac 额外 sanitizer/内核日志归档位于 `~/vibe-coding/dsim-test/evidence/m135-budget-resume`。

Linux 初次构建命令的完整提交标签误填；激活前再次逐项核验冻结源码和 Git 归档，将身份纠正为上述实现提交，原标签保留在 `original_unverified_commit_label`，二进制及源码没有因此修改。发布 helper 后续直接读取已核验的 source proof，避免手填完整提交。

双端四组发布回归均通过并已激活：Mac `20261028T023731217921Z-79b2b47d5974`，103 Intel `20261028T023755Z-22800c2`。每端旧调度组 90 个波形、2367 个预算边界、648 个恢复和 18 次预测检查通过，当前组 reference 恢复错误为 0；这不能外推到函数内部等未实现路径。两端安装入口实跑及生成代码核验见 `mac-entry.json`、`linux-entry.json`。
