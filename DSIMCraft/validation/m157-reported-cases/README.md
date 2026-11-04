# M157：新增问题 case 与层次写入

实现冻结 `8a6e63fe6dac59fc1de3b538d2f3e7d19764c6f5`。普通模块层次变量/内存赋值和 ref 实参复用现有存储、packed 选择、动态下标、延迟 NBA、唤醒及事务路径；net/parameter、packed ref、不等价类型仍拒绝，modport 输入权限保持。块、函数/task、fork 列表内的独立空语句接入已有 DummyStmt。RTL/gate parser 分开；Bison 仍 78 shift/reduce、无 reduce/reduce。

七份新增原始 DUT/TB/刺激字节和 archive 哈希不变，在原有每步 180 秒预算内完成 25470 个完整四态观测；独立冻结 oracle、原归档 VCS 与新鲜 VCS 复跑完全一致。四份通用模型验证窄/129位、升序 packed 二维、索引只求值一次、NBA 地址冻结、多实例隔离、连续读者、真双分区和空语句执行；VCS 同源输出及断言通过。共十一份新鲜 VCS 正例通过。旧五种输入/十二份归档及三个原始内存 case 本机复验通过；SV 保留字 before 已拒绝，原竞争 TB 不作为有效数值误仿真。

Mac 与 103 Intel 各九组817捕获及 mandatory RTL parser、格式 parser、原生 DB 通过。新通用组各73捕获、六编译拒绝、1回滚1提交；十三份生成 C++ 和73完整捕获跨平台一致。完整 parser、新四正例/六反例前端、四实际生成程序和预测 replay ASan/UBSan、实际双分区与独立异步 writer TSan 通过，未启用 leak detection，未宣称运行速度/压缩率提升。Mac 所有发布输入与冻结 Git 字节绑定；103 源码清单在构建和验收前后逐哈希检查。

Mac `~/vibe-coding/dsim-test/bin/dsim` 已更新至 `20261029T004223935490Z-385b2669bcae`；103 两入口 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 更新至 `20261029T004524Z-8a6e63f`。三个实际入口重编译、执行、完整异步 DWF 字节和范围选择复核通过。五个自有源码/结果归档逐成员哈希在两端验证；VCS 仅导出自有输入关联记录和文本输出，无 vendor C/C++、csrc、daidir 或可执行文件。

首次 Linux 候选缺失独立 decoder 的 Python 源码依赖，验收 import 失败，未激活。补入同一冻结 Git 提交的 experiments/waveform/dwf.py 后重新打包并完成全部九组，原失败收据和原源包保留。全量 all-target 构建仍在未变更的 masked_kernel.cpp 的旧 Ready 尺寸断言失败；本批只报告上述明确目标和回归通过，不报告全量构建通过。

已读 REPORT-GAP2，并在 plan1017 更新依赖/优先级。Mac 实际稳定入口重测未修改公开 UVM，预处理保持1888084字节/166依赖，native仍在uvm_misc.svh:96 string键关联数组拒绝；完整 UVM 不能编译运行。本批没有重新执行完整 UVM 参考仿真。

目录复核期间又新增 retained_memory_codec（15418观测、编译timeout），属于下一批正在处理的问题，不计入本批七正例通过，不声称目录所有问题已关闭。见 case-inventory.json。本批稳定发布与该后续问题修复分别绑定，避免把尚未完成的验证计为成功。
