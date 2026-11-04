# M158：新增大模型编译与默认运行预算

实现冻结 `9a7132cd6b71246aa99acf64457ca7cf5fd38958`。按 SV 函数展开体大小给非平凡调用设置原生 noinline 边界，避免在单一巨大过程内重复内联数百个 PC 解释器；不根据 HDL 名称、case 或刺激选择优化。Intel LLVM在这些边界内另加minsize，限制helper展开，其他代码保留配置优化级别；Clang/GCC保持noinline。默认指令限额由1000万改为 uint64 最大值，显式 --max-events/API 预算及既有预算恢复路径保留。

新增 retained_memory_codec 使用原始三文件、刺激及每步180秒预算，15418个完整有序四态观测、20个输出（包括全部保留内存字）与原归档及新鲜VCS一致。H4按每源位两位编码解码，检查所有位、序号和完成标记。周期参考来自合格VCS轨迹，并非独立周期oracle；原producer另有独立数值/保留内存检查，不能将二者混称。旧模型本机原生 -O2 编译复现180秒超时；正式开发路径编译48.880秒、运行4.147秒，仅说明该输入/主机测量，不代表普遍速度比或签核。

新组另含128位四态函数、实参副作用一次求值、串行/时间轮/并行，以及两个超过旧默认限额的进程；新组20份完整VCD/DWF/异步捕获，明确检查真双分区及显式预算中断。跨格式比较全部声明与事件，sync/async DWF逐字节一致。新鲜VCS原始模型和两份通用模型通过。Mac六组发布检查及mandatory RTL parser/格式parser/原生DB已通过，实际稳定入口重编译、完整及范围异步波形验证通过。

Mac新前端和两份实际生成程序 ASan/UBSan通过（detect_leaks=0）；首次验证脚本以默认settled模式运行却与ordered参考比较而失败，修正为显式ordered，确认生成C++身份并复用相同已编译二进制重跑通过。修订轮首次使用emit-only参考目录，缺少运行输出，比较脚本失败；改用实际发布回归目录，并核对相同生成C++后复用相同二进制重跑通过。两个脚本失败均保留，不计为通过。没有新增TSan或LSan结论。

远端Intel首次候选在并发验收时原始模型仍超过180秒，未激活；隔离同样超时，失败收据保留为 linux-first-stage.json 与 intel-isolated-rejection.json。minsize自有CPP试验78.379秒编译并匹配完整参考后，正式修订源版重新冻结并完成双端六组及mandatory检查。正式原始模型编译/运行：Mac 82.011/6.322秒，103 Intel 89.745/8.165秒，仍保持原180秒预算；仅为该主机/输入/当时负载测量。

REPORT-GAP2 已纳入 plan1017 的优先级。完整公开UVM仍卡在 uvm_misc.svh:96 的string键关联数组，不能原生编译运行；本批未改进该语言能力；Mac修订版稳定入口重新确认预处理1888084字节/166依赖及上述native拒绝。约束随机、IPC、static、clocking、coverage、DPI等继续补齐。全量all-target构建仍存在未变更的masked_kernel.cpp Ready尺寸断言失败，本批不报告全量构建通过。

最终跨平台8份生成C++、20份新捕获的全部声明/事件完全相同，六组均PASS。Mac发布978项输入与冻结Git字节绑定；103构建前后逐文件核对1802源码清单。五个源码/自有原生结果/sanitizer/VCS文本归档双端逐成员校验，共10065个成员；VCS不导出vendor C/C++、csrc、daidir或可执行文件。

Mac稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 指向 `20261029T011923507157Z-a0157e7c31dc`；103两个入口 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 指向 `20261029T011926Z-9a7132c`。三个实际入口各自重编译/执行、完整异步DWF逐字节及用户所选范围验证通过。首轮候选与两个sanitizer脚本失败的收据保留。最终audit.json为PASS；源输入、参考来源、未完成UVM及全量构建限制见上文。目录24项复核无新增，历史项保留原始判定，不把竞争TB算作合法DUT误仿真。
