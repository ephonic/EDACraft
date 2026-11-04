# M104：格式化输入扫描与 VCS 对齐

接入 `$sscanf/$fscanf` 的整数、进制、字符串/字符、宽度、转换抑制及字面量/空白匹配。扫描目标沿用原生写回路径，覆盖宽四态、二态、片选/拼接、automatic/ref 和 final。文件游标/EOF/回推复用现有预测事务；sscanf 单独使用不启用文件缓存。完整范围及明确拒绝见 [功能文档](../../docs/formatted-scan.md)。

开发验收：六份相同源文件与103 VCS W-2024.09_Full64的43行TRACE、四份文件字节和1336个数值位完整settled时间线一致。192个VCS不dump数组位明确排除，仅TRACE中出现的元素另核对。新组48份VCD、六次拒绝回放/六次接受提交、真实双分区、七项编译拒绝/七项运行拒绝通过；六份实际生成程序及内核ASan/UBSan通过，代码SHA另记。旧文件I/O九模型72份VCD及各九次接受/拒绝通过。

六份同源模型覆盖转换计数、部分匹配、空输入、符号/溢出/XZ、无赋值转换、动态源/格式、目标两次求值、文件保留未匹配字符、NUL 字节、跨时刻子程序和真实双分区。原始 VCS 输入、日志、波形及输出文件保留到私有 evidence。`verify-vcs.py` 检查输入SHA、完整TRACE、全部可比数值位的完整 settled 时间线及文件字节。VCS不dump的未打包数组位单独列出，不能用若干TRACE值声称其完整波形对齐。

`regression.py` 验证 serial/time-wheel/two-thread 的 ordered/settled 流，另外执行接受/拒绝预测；推测结束且提交前直接检查OS文件存在性/内容。内核测试额外验证已打开文件的游标、EOF、回推恢复和非法格式不消费输入。`sanitize.py` 对实际生成程序及内核执行 ASan/UBSan（关闭泄漏检测，UBSan立即失败），保留代码SHA。

发布前冻结实现，源码包逐文件对照Git。两端稳定入口通过所选回归后才切换；`verify-installed-linux.py`/`verify-release.py` 对照实际入口重生成代码、运行automatic/ref/final模型、核对不可变运行时与跨平台文件。最终身份和验收数字记录于本目录JSON，不声称完整VCS兼容。本轮没有新增性能测量。

M104 已发布：实现75c10a7，macOS/Linux各九项针对性检查通过，两端实际入口各重生成12份C++并运行automatic/ref/final文件用例，全部输出/整文件VCD及auto.txt字节一致。653项本地输入和1616份源码包文件与Git逐字节核对，各端八份运行时快照校验；六份sanitizer生成代码哈希与实际入口相同。跨平台160份C++、218份整文件VCD、259份运行输出和135份文件字节JSON完全相同；安装版各重新通过VCS全部1336位和四份文件对照。身份见release-summary.json，15份报告/原始档案逐SHA保存于两端私有evidence并核验，见evidence-receipt.json。
