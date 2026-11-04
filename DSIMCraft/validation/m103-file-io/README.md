# M103：通用文本文件 I/O 与 VCS 对齐

新增12个系统函数/任务：fopen、fclose、fwrite、fdisplay、fflush、fgetc、ungetc、fgets、feof、ftell、fseek、rewind。支持 FD/MCD、常用打开模式、宽 packed/string、automatic/ref、final 和文件位置/内容的预测事务。完整边界见 [功能文档](../../docs/file-io.md)。

开发验证：103 VCS W-2024.09_Full64，九份相同源文件的全部45行 TRACE、12份最终文件字节及1816个数值波形位的完整 settled 时间线一致；不排除 FD 位。VCS不dump的280个未打包数组位明确排除，TRACE 中出现的数组元素值另行核对，不宣称这280位也具备完整VCS波形。既有 writememh 的 export.txt 注释格式不纳入通用文本文件逐字节对照。

新回归72份标准VCD、九次拒绝预测回放、九次接受提交、实际双分区、11项编译拒绝及五项运行拒绝通过。每个预测用例在推测结束但提交前直接检查OS文件内容/存在性；内核另测已打开文件游标恢复、读己写、内存文件互通与提交失败不重放。旧testbench_io为49份VCD/七次回放；memory为50份捕获/两次回放/五项编译及五项运行拒绝。两项早已支持的数组声明从旧memory负例改为编译接受，已用上轮稳定入口确认不是本轮语义变化。

`run-vcs.py` 保存真实编译/运行日志、输入SHA和文件字节；`verify-vcs.py` 检查同源、完整TRACE、全部其余数值位和文件内容。没有只挑采样点或按FD掩蔽差异。`sanitize.py` 检查实际生成程序及文件事务内核，保留源码SHA；ASan关闭泄漏检测，UBSan错误立即退出；九份生成程序和事务内核共十份程序通过，哈希与最终回归相同。

实现 `3e6fcbb` 已推送。macOS/Linux各九项针对性发布检查通过，稳定入口为 `~/vibe-coding/dsim-test/bin/dsim` 和103的 `/apps/EDAs/own/dsim/bin/dsim`（兼容入口 `/apps/EDAs/own/dsim/dsim`）。652项本地发布输入、1605份源码包文件与实现Git逐字节核对，各端八份运行时快照校验；实际安装入口各重生成18份C++并编译运行automatic/ref/final文件用例。跨平台123份C++、170份整文件VCD、204份运行输出和81份文件字节JSON相同，九份sanitizer源码哈希与稳定版相同；两端安装版回归均再次通过全部1816位与12份文件的VCS对照。

发布身份与完整校验见 `release-summary.json`、`source-package.json`、`vcs-alignment-*-release.json`。原始日志/波形保留在本地 reference 及两端私有 evidence，不将模拟器产物提交到源码库。本轮没有性能重测；不能据此宣称完整 VCS 兼容。
