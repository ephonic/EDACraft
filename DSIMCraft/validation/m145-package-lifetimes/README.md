# M145：包与子程序生命周期、关键字接收修正

最终实现冻结为 `06fbb2d211a0d4b71101e9b9309f167c45bd3747`；1812 个源码归档成员逐字节匹配 Git，归档 SHA256 `20c75789bc8e3190af89a5d1059384c10dff098236bf553a7c413c7d1a2abb01`。RTL 与门级 parser 继续分开维护；runtime 头没有修改。

支持 package automatic/static 默认子程序生命周期和显式 task/function static 覆盖，包含 ANSI/经典参数、命名/packed/隐式返回类型、包静态变量、默认初始化、重叠挂起、独立实例与既有 ref 调用。包变量仍为共享静态对象。71 个尚无对应语法的 SV 关键字在普通/单级限定标识符路径上拒绝，Verilog 模式及转义名称通过。

开发新组四模型通过 20 份逐信号有序波形、4 次预测提交、4 次回滚、2 次挂起检查点恢复、150 个拒绝例和真实双分区。完整 parser 与 8 个生成程序 ASan/UBSan 通过（关闭 leak detection）。原始 RAM case 编译因 before 关键字被拒绝、原归档哈希未变；它属于非法输入接收差异，归档原报告明确称更名后的原设计双方均通过，不重新归为合法 RTL 误仿真。

四个最终同源模型 VCS W-2024.09 的 TRACE 与预期一致；Mac/103 已各自直接核对全部共同的 2066 个声明位 settled 时间线。使用无参数 `$dumpvars` 保留包变量/静态方法；signatures 模型的 types_pkg 中 171 位仍未被 VCS 导出，精确缺失集合进入检查，任何其他缺失都会失败，不声称这些位完成参考比对。

VCS 探针另测现有 automatic NBA 限制、非法限定符及保留字、Verilog/escaped 模式。原始第一轮 static_ref 被 VCS 接收，检查预期因此失败并保留日志；后续将其单独标为既有接收差异，未修改原输入：dsim 仍要求 ref 子程序为 automatic。最终按显式 1800-2012 关键字模式（包装文件 include 不改原输入）复核，19 个拒绝例和 2 个合法模式通过，只保留 static_ref 接收差异。默认 VCS 模式对 soft/nettype 的接收由独立 begin_keywords 2009/2012 探针解释，不能归为 dsim 新误拒绝；该 VCS 对 1800-2017 指令值拒绝，未当作相应变量探针通过。dsim 本轮不新增 begin_keywords 指令支持。两端发布及稳定入口复核均完成；原始证据按大小/SHA256/归档成员清单镜像到两端。

module/interface 头部生命周期、compilation-unit import、class/UVM、clocking 和完整 SVA 等仍缺；本批没有性能测量，也不以六个旧模型生成代码一致推断所有设计性能不变。

首次发布候选两端均被 automatic_subroutines 的 duplicate_automatic 历史诊断要求拦截，未激活；修正编译器诊断，不修改旧回归预期，重新冻结并重跑发布检查。最终完整 parser 再次通过 sanitizer；8 个实际生成程序与已执行 sanitizer 的输入 C++ 全部逐字节相同，复用有明确输入哈希证明，未声称重复执行这 8 个程序的 sanitizer。

Mac 五组正式发布回归均已通过，共 309 次捕获和 239 个拒绝例（新组为 20/150），mandatory parser/格式/原生 DB 检查通过。Mac 稳定入口已激活 `20261028T131547596117Z-82b4ccad2603`，二进制 SHA256 `1b97db0706f31e12dd8b2841ffd33da0a6c88f8f6d82ac6b1d69c47a80eb0f91`；由实际安装入口重新编译/运行的 overlap C++、stdout 和完整有序波形匹配候选验收，RAM 原输入安装入口负例也再次通过。

Linux Intel 稳定版 `/apps/EDAs/own/dsim/releases/20261028T131552Z-06fbb2d` 二进制 SHA256 `36c350aa900d8ed306d71ac4215e3de1655397cac57ccb024d49b673c419d4d7` 已与 VCS 直接对照，20 份新组捕获的 C++、stdout 和完整有序流与 Mac 完全相同；五组发布回归共 309 次捕获、239 个拒绝例及 mandatory units 均通过，两处稳定入口已激活；真实入口各重新编译/运行 overlap 并核对 C++、stdout 和完整有序波形通过。

最终证据索引见 `evidence-index.json`，两份原始归档保存在本地 `~/vibe-coding/dsim-test/evidence/m145-package-lifetimes/` 与 103 `/apps/EDAs/own/dsim/evidence/m145-package-lifetimes/`。`audit.json` 绑定最终冻结源码、两端验收与镜像复核；本轮没有性能重测。
