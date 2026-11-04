# M78：用户 RTL 报告缺陷修复

阅读并冻结用户 [原始报告](REPORT-original.md)，按后续指示跳过 DWF 格式修改。逐项状态与边界见 [处理表](../../docs/rtl-report-fixes.md)。

修复无括号 task 调用空指针、常量表达式复制次数、always_ff 声明初始化、显式 var 模块端口，新增向下已展开实例的内部标量/packed/参数观测，改善指定错误码文本。具名 packed struct 形参及 assert 失败动作 NBA 已可用，本批加入检查而不冒称新实现。层次读取目前要求实例先在源中声明；其他限制及尚缺 package、并发 SVA、随机函数、enum 字符串返回均明确保留。

- tests/rtl_report 的六个完整设计及三个原始任务探针以 origin.json 的 SHA256 核对；不修改用户外部报告和用例。
- [原生检查](native-results.json)：11个定向模型 × 串行/时间轮/`--threads 2` 配置（单分区可回退），共33份完整 ordered VCD 流比较；6个原始应用 golden 自检；7类拒绝；Verilog var 标识符检查。
- [VCS](vcs/results.json)：同源十一模型在 10.131.254.103 / `source /apps/EDAs/syn.bash` / W-2024.09_Full64 实际编译运行；固定无 timescale 源的默认值为 1s/1s（与 dsim CLI 默认值一致，源内 timescale 优先）。两个含 always_ff 声明初值的模型使用 `-ignore initializer_driver_checks`，其他模型不用该选项。[默认拒绝日志](vcs/ff-initializer-default-rejected.log) 原样保留，不宣称默认配置也接受。十一模型 TRACE 相同；[逐位核验](vcs-verified.json) 比较十个有波形模型的194条物理位，九例完整时间线相同。hierarchy_timing 在10ns同刻 finish/时钟翻转时，四条输入端口时钟尾波不同，保留全部原始差异，仅比较到9.5ns。p1 零时刻 finish 阻止 VCS dump 初始过程，无 VCS 波形，单列为 TRACE 检查，不计入波形对齐。
- [sanitizer](sanitizer-results.json)：实际 ASan/UBSan 编译器生成、全部17个实际 C++ 程序编译执行；完整 C++/stdout 与原生一致，定向十一模型再比完整 ordered 波形；七个错误分支也检查，关闭泄漏检测。[parser](parser-sanitized.log) 含三轮参数实例、var/task/层次读取清理。
- [既有回归](regressions.log)：frontend、子程序、named type signatures、立即断言、enum、parser 六组通过；另一个 specialized always 检查组通过（26捕获、12拒绝）。旧 always_ff 初值拒绝用例改为 always_comb 初值冲突，保留其独占写者检查用途。M77 七个最终完整生成 C++ 及15个拒绝分支在本批最终 sanitizer 编译器下再次核对；M77 的完整 ASan/UBSan 程序证据随原代码身份保留。

未跑全量 CTest/Linux 原生构建；未对完整应用另外声称与 VCS 逐位对照或重测性能。稳定入口已更新至 releases/20261024T040222070894Z-bdce241a045f/dsim；[发布记录](release.json) 56项通过，含全部本报告用例、原有六组用户问题 case 和 gate CLI/SDF。冻结8份运行时头文件。实现提交 `2bafbcab4657f8b2f3df925110afc15479beadb3`，binary SHA256 `43212ce76ba0872860d40afbb23a8f7e5acacf9ffddf4bf5d838ac584a576325`。发布版[39个报告程序](stable-identity.json)的完整 C++/stdout 与原生一致，33份完整 ordered VCD 流一致；另[53个根目录模型](../m77-reduction-with/stable-identity.json)核对生成代码/输出/波形身份（47旧稳定版＋6本批归约模型）。
