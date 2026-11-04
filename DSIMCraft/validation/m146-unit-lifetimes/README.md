# M146：设计单元生命周期与 banking 编译预算

实现冻结 `b4c61dfd9fe7ff5ba9648b9ca9ca4c78a8529de4`，源码归档 SHA256 `494c89c000365ccefa9a8df222ff3275056a289391b5845d8335210af014e7d6`；1821 个源码成员逐项匹配 Git。

补齐 module/interface automatic/static 默认 task/function 生命周期，显式限定覆盖默认。解析 header 前确定默认值，每个设计单元及失败重解析隔离；子程序 AST 保存已解析生命周期。模块/interface 变量继续按每实例静态存储，包变量继续唯一共享，沿用现有 activation、ref、延时、checkpoint 和预测回滚。RTL/门级 parser 保持分开。

优先复核用户新增 banking case：原稳定版编译超过原始 180 秒预算，未启动仿真。生成 initial 为 5528 条指令，旧 16384 门槛未覆盖；将已有只执行一次、无回跳 initial 的通用分块门槛降至 4096，保持 256 指令分块和所有保守条件，不按设计名选择路径。原始 DUT/TB 逐字节加入 tests/memory_cases/banking，仍用 180 秒预算；开发候选编译约 44.260 秒，640 阶段/23040 次独立比较通过。同源 VCS 重新运行输出相同。这是编译预算修复，本批没有 runtime 性能测量。

新组四个模型分别覆盖默认/显式生命周期、实际 modport 原型调用与重叠 ref task、header import/参数/generate 双分区、带类型返回值与每实例静态局部。开发新组 20 捕获、4 次预测提交、4 次回滚、2 次 checkpoint 恢复、17 个拒绝例及实际双分区通过。四个 VCS 模型所有 TRACE 与独立预期一致，2724 个共同声明位 settled 时间线一致；signatures 中 VCS 未导出两份 count.n 静态局部（64 位）及两份 scalar_f 静态方法（6 位），精确 70 位遗漏另列，任何其他遗漏均失败。

完整 parser 和 8 份实际生成程序通过 ASan/UBSan（关闭 leak detection）。额外 banking 生成程序的首个 O1/debug sanitizer 编译超过独立的 180 秒检查预算，没有运行；保留失败记录，另外用 O0/no-debug 编译执行 sanitizer。该额外预算与原案例 release 编译验收分开。O0/no-debug 版本编译并运行通过，输入 C++ 与最终 release 的 banking/model.cpp 逐字节相同；最终结果见 banking-sanitizer.json。

诊断对照区分两个已有 static ref 接收差异，以及 VCS 默认 .v 接收 module automatic、dsim 显式 Verilog 模式拒绝的模式差异。首次探针把后一项误期望为 VCS 拒绝，失败后原输入不变，将真实接收差异单列；最终对照不是全部负例兼容的声明。生产代码不因探针调整而改动。

开发期 parser 测试误查未 elaboration 的模块模板并崩溃，改查实际实例 hive 后完整重跑通过；首次 parallel fixture 含全局输出/停止副作用，正确退回单分区，删除观察副作用后由独立波形预期检查输出，并确认实际双分区。这两项均为验收脚本修正，生产实现未因此改变。

Mac 五组正式回归全部通过（181 捕获、240 拒绝、18 预算恢复、22 checkpoint 恢复），三个原始 case 编译分别为 59.684/64.065/48.997 秒，均低于原 180 秒预算。Mac 稳定入口已激活并实跑 overlap，C++/stdout/完整有序波形匹配验收。103 曾尝试将最后 modport/memory 两组并行，但实际到达时 modport 已结束，前置检查阻止了任何进程变更和重复启动；继续原来的顺序检查。所有组均须完整 PASS 后才完成发布。103 五组也已全部完整通过（181 捕获、240 拒绝），三个原始 case 编译分别为 154.881/154.386/89.194 秒，原预算不变。Linux Intel 稳定版 `20261028T140929Z-b4c61df` 的两个入口均已实跑 overlap，核对 C++/stdout/完整有序波形；Mac 稳定版为 `20261028T140923485410Z-a728c06f81ca`。两端 20 份新组捕获的生成代码/输出/完整有序波形相同，六个旧模型 C++ 与八个 runtime 头与 M145 完全相同，本批不重测 runtime。原始证据及逐成员清单已镜像到 `~/vibe-coding/dsim-test/evidence/m146-unit-lifetimes/` 和 103 `/apps/EDAs/own/dsim/evidence/m146-unit-lifetimes/`；大小/SHA 索引见 evidence-index.json，最终审计见 audit.json。编译单元 import、class/UVM、virtual interface、完整 clocking/SVA、完整门级时序等仍有缺口，不声明全面 VCS 对齐。
