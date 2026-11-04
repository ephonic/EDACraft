# 0.8.0 RTL 预处理与文件输入验证

2026-10-17，新增独立 token 预处理器和 `-f/-F` 文件列表入口；修复原 RTL lexer 在同一物理行上多个字符串被最长匹配合并的问题。门级结构网表保持独立 parser，运行时与门级编译器相较 0.7.0 字节不变。

本批支持 include、跨 RTL 文件宏状态、object/function 宏、默认实参、嵌套展开、token paste、基本宏引号、续行、ifdef/ifndef/elsif/else/endif、undef/undefineall、`__FILE__`/`__LINE__` 生成，以及 include/define/undef CLI 参数。记录展开文本、依赖和源位置，并保护源文件、头文件、文件列表及其符号/硬链接免于输出覆盖。精确边界见 [项目用法](../../README.md#rtl-预处理与文件列表080)。

结果：

- 本地及远端 CTest **8/8**，包含原有 27 RTL 和 15 门级正例；新增 13 组预处理正例、26 个拒绝，以及文件列表/源定位/输出覆盖保护矩阵。最终共 55 个正例，54 个使用默认 VCS 参考，1 个沿用已记录的历史 debug 参考。原有已知差异继续保留，不算作默认通过。
- 新增 13 组在同一远端分别由 native 和默认 VCS 各执行三次，全部匹配独立常量预期；VCS 编译原始文件列表/源码，不使用 dsim 预展开结果。VCS flags `-full64 -sverilog -top top`，无 debug。flags 用例对 `-D/-U` 使用已记录的等效最终 VCS define，其他使用相同输入参数。原始输入 hash、命令、编译与运行日志见 [vcs/results.json](vcs/results.json)。
- 12 组新增例通过 Icarus trace，另 1 组转义标识符中包含反引号：native/VCS 接受，Icarus 错当宏展开后编译失败；回归明确核对并保存这一差异，不称作 13 组 Icarus 成功。源文件中的条件块跨 include 继续能正确关闭。
- 全部 13 组新前端与生成 C++ 运行时通过 ASan/UBSan；同一 sanitizer 前端也运行全部新拒绝/保护矩阵。见 [sanitized.log](sanitized.log)。
- 冻结 **119 个实现/测试/脚本文件、16 个第三方修改文件、3 个驱动**，远端构建前后逐一校验。与 0.7.0 比仅六个第三方 RTL 文件变化（lexer/grammar/错误行记录及生成物），两个 gate parser 和三个 Liberty 文件不变。补丁在原 ZIP 干净解压目录重放一致；Bison 仍是原有 33 SR、69 RR 和两条无效 generate 规则。

远端独立目录：`10.131.254.103:/tmp/dsim-m2-preprocessor-1017-VSKGYM`；VCS W-2024.09，GCC 11.5，环境 `source /apps/EDAs/syn.bash`。所有进程均等待终态成功后归档，未把观测超时当作失败或重复启动。归档包含 874 文件，校验见 [evidence-archive-sha256.json](evidence-archive-sha256.json)，原始展开内容在 `remote-raw/`，便捷 VCS 副本在 `vcs/`。

源码压缩包 `/tmp/dsim-preprocessor-source.tar.gz` SHA256 为 `2bc21dd98f470ca6e17c9eeee5462a20fd4b1b5b0c444c0a79a1b90832de1383`；[source-snapshot.json](source-snapshot.json) 保存完整清单。原始 ZIP、第三方改动和重放验证分别见 `source-provenance.json`、`parser-replay-sha256.json`、`parser-patch-replay.log`。本批 tiny fixture 的时间用于追溯，**不作为 VCS 性能比较**，0.7.0 的性能数据仍仅描述原始版本。

前期 VCS 搜索顺序、跨文件作用域、-f/-F、宏引号、默认参数、转义标识符和零形参失败探针的原始输入/日志见 `vcs-probes/`；初始失败也保留。参考报告 `/home/yangfan/vcs/vcs1017.md` 已读并快照为 [vcs1017-reference.md](vcs1017-reference.md)，据此在计划中细化字级算术、事件块、时间轮适用条件、增量编译和实际设计验收。

已知限制：timescale/default_nettype 等 directive 明确拒绝；宏生成 directive、复杂宏字符串转义、环境变量文件列表和自动库搜索尚未实现。`__LINE__` 有同输入运行验证；`__FILE__` 当前只有实现，没有直接的路径字符串差分用例。门级结构文件尚不走本 RTL 预处理入口。55 例 trace 不等于全信号波形验证，也不构成完整 IEEE/VCS 覆盖。

复核：

```sh
python3 validation/m2-preprocessor/analyze.py
ctest --test-dir build --output-on-failure
# 在已加载 VCS 环境的远端，使用独立新输出目录重跑：
python3 scripts/compare_preprocess_vcs.py --repeat 3 --output /tmp/dsim-preprocess-repeat
```

[analysis.log](analysis.log) 和 [summary.json](summary.json) 核对冻结清单、两平台最终结果、全部新 VCS 原始日志及原有功能参考。原生压缩波形是后续独立功能，其实验原型不计入本批冻结仿真器的支持数。
