# REPORT6 修复与复核

REPORT6 测的是稳定入口 `20261025T101432479554Z-d2ccf6538643`。103 的指定 REPORT6 路径不存在，读取本地同名测试目录。原文保留在 `validation/m99-report6/REPORT6-original.md`。

唯一标为 P0 的 p21/p27 并非 dsim 与 VCS 的语义差异。两份探针字节与上一轮 VCS 验证的原始模型相同；`32'd0` 或无符号移位另一分支会使三元表达式中的这些算术运算采用 unsigned 上下文。括号不改变上下文。原 p27 输出的 `BUG got=...` 是探针的 `$display`；VCS 也输出这些文字。类型规则与具体数值见 [REPORT5 复核](report5-review.md)。

本轮修复测试本身（原稳定版本也会通过修正后的oracle）：

- p21 同时检查独立 signed 路径为 `ffffffff`、无符号三元路径为 `003fffff`（移位10位）；不再把两种上下文视为同一预期。
- p27 分别检查独立 signed 结果 `ffffffff,00000000,fffffffe` 与 unsigned 三元结果 `7fffffff,55555554,00000002`，失败调用 `$fatal`。
- 加入 p29 对 `32'd0` 与 `32'sd0` 两种上下文的独立字面量自检。
- 用户 `probes2/run.sh` 不再以出现 `BUG got` 作为 PASS：同时检查命令退出码及明确成功标记；任意 CHECK 返回非零。波形探针使用本次进程的唯一文件名，保留已有 `out.vcd`，避免重复运行触发防覆盖错误。

用户目录的 p21/p27/run.sh 已同步修正，原文件备份在 `complex/evidence/report6-original/`；REPORT6 原文保留。修正后的12项 probes2 检查已用原稳定入口全部通过；三份修正/上下文模型与 VCS 同源输出及全部914物理位 settled 时间线一致。dsim 三后端18份标准VCD通过。归档、源身份和复核脚本见 [M99](../validation/m99-report6/README.md)。

同时进行的整数循环优化和字符串能力补齐属于编译器实际改进，单列在 [M98](../validation/m98-integral-string/README.md)。不能把 REPORT6 的测试误报当作编译器已经修复的符号性缺陷，也不能据这些用例宣称完整 VCS 兼容。

实现源10f0bb0已推送并发布到本地及103稳定入口。两端各7项发布检查通过，REPORT6在两端各18份标准VCD与VCS全部914位重新核对相同；当前实现的10个复杂设计回归通过。
