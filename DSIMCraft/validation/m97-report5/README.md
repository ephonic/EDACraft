# M97 REPORT5 复核及当前性能

当前实现源2a914d3。REPORT5原文保留；p21/p27的unsigned三元分支预期错误，保持与VCS一致的行为。新增p29自检。两端实际稳定入口四模型、各24份VCD通过；与103 VCS W-2024.09_Full64输出及全部954物理位settled时间线相同，无单边位。四个实际生成程序ASan/UBSan通过。

同机固定CPU0、无波形/覆盖/调试、编译另计；预热一次、交替三轮。整数十亿次20.31/1.68秒（12.09倍）、时钟/NBA三千万4.58/4.16秒（1.10倍）、64路扇出三百万8.29/7.99秒（1.04倍），均CPU中位数。全部24份计时TRACE和CPU独立复算通过；共享主机未锁频，只代表三类合成RTL。详见performance-results.json与performance-verification.json。

验证脚本、源哈希和比较结果在本目录。原始生成代码/波形/计时归档位于用户测试目录及103安装目录的evidence/m97-report5。功能/性能摘要见../../docs/vcs-comparison-current.md。此轮无编译器行为改动，无需重新发布相同实现；当前稳定二进制身份沿用M96 release-summary.json。
