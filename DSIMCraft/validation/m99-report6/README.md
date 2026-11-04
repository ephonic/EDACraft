# M99 REPORT6

原始报告及源身份保留。原 p21/p27 与既有 VCS 对照输入字节一致，问题来自测试预期；修正后的模型不再错误地把独立 signed 运算当作 unsigned 三元上下文的oracle。

三同源模型、18份标准VCD、全部914物理位与VCS settled时间线/功能输出相同。用户 probes2 12项用原稳定入口全部通过。报告和原始探针/脚本备份保留；详细修改见 ../../docs/report6-review.md。当前候选编译器的10个复杂设计回归全部通过，详见complex-designs.txt。

run-vcs.py/verify-vcs.py复核同源输入及全部比特。原始生成程序、VCD、日志归档保存在用户测试目录和103的 evidence/m99-report6 下；仓库仅保留摘要，最终发布身份在M98 release-summary.json。

M98两端发布后，各7项发布检查通过。两端REPORT6各18份VCD及输出/全部914位重新与VCS核对通过，九份生成C++与十八份整文件VCD跨平台相同。源实现10f0bb0，最终身份见../m98-integral-string/release-summary.json。
