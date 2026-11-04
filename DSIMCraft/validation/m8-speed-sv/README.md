# 默认 SDF 标量后端与 SV always 过程

生产变更为 `src/main.cpp`、`src/rtl_compiler.cpp`、`include/dsim/runtime.hpp`：无波形 SDF 默认标量时序存储/处理器，显式 `--no-gate-scalar-timing` 回退；接入受支持语言子集中的 always_comb/latch/ff。RTL/门级 parser 继续分离，二者 parser 源码本批均未修改。

480 文件源码包 `/tmp/dsim-m8-speed-sv.tar.gz`，SHA256 `67826c083105c939513be83108487e0d44235d2c9e069d4aaf3a1936ed07af8f`。工作区逐文件对照通过；常用 `build/dsim` 已重新构建，实际 SV 冒烟输出与测试构建相同。详细边界见 [always 过程](../../docs/always-procedures.md)。

原始 300,909 单元、完整 SDF、128 笔输出，CPU0、无波形、默认非负检查、无预热、单轮顺序筛选：

| 后端 | CPU 秒 | RSS KiB | 正确输出 |
|---|---:|---:|---:|
| 上批默认（含全零输入折叠） | 74.37 | 346692 | 128 |
| 标量时序（本批默认策略） | 57.69 | 314140 | 128 |
| 仅共享路径表 | 69.93 | 275144 | 128 |
| 标量及共享路径表 | 62.84 | 233852 | 128 |
| VCS W-2024.09 | 8.89 | 210996 | 128 |

标量耗时下降22.43%、RSS下降9.39%，本轮仍为VCS耗时的6.49倍。共享表组合比仅标量慢，因此没有默认启用；不能把单轮筛选推广为跨负载稳定提速，也不混用上一批VCS分母。这里测量的是此前已支持的真实生产标量 lowering；本批新编译器的默认命令另做完整代码身份及实际执行验收，不把功能验收当作另一次计时。

原测速 `/tmp/dsim-m8-candidates-OFtnL1` 退出0。全部五份CPU和128条输出已本地从原始记录重算：[performance.json](performance.json)。原始日志在 `linux/candidates/`。

本地13项受影响CTest通过：新SV过程、运行时/阻塞内部/NBA延迟、自动并行编译、共享路径表流程/检查点、默认策略与五项标量/作业/路径内核；不是完整115项。新SV回归包含26波形捕获、两个真实失败预测重放、12类拒绝和实际双线程独立域。另将SV三类过程接入带SDF的设计，普通always对照/通用后端/专用作业三个模型两份完整ordered波形比较通过，覆盖启动时跳过已预注册过程的作业初始化接口。[本地结果](local-results.json)、[组合结果](mixed-local.json)。

Linux实际VCS两例共283物理位时间线与TRACE匹配，8个Mac生成程序经GCC重新编译执行，对照全部通过。重放允许预测horizon添加空时间边界，保留所有其他事件的时间和全局顺序；独立分区只比较各信号有序历史及物理位。首轮验证器把空边界误判为差异；首次继续又触发已有波形保护。修正验证器后重用原二进制全部重跑通过，生产源码未变，原失败日志和报告保留。原任务`/tmp/dsim-m8-sv-linux-ufwVLv`首次退出1，继续运行`resume.exit=0`；[结果](sv-linux-results.json)，不将首次状态写成成功。

新源码Linux编译器重建、三项CTest及全量默认命令验收已在`/tmp/dsim-m8-default-linux-m9aFdm`退出0：新默认完整CPP与实测标量候选替换内嵌runtime后逐字一致，新默认程序实际重新编译并执行，128笔全部匹配。源码前后逐文件SHA保持。该批等待上述测速终态后启动，不与本会话测速并行；功能执行没有被当作另一次计时。[最终结果](default-linux-results.json)。

原始归档 `evidence.tar.gz` SHA256 `b563760af875c08fff4f7824d9bc296af5b0e5ccc244200ec1a53669ff8224d0`，含本轮筛选、VCS探针和SV/GCC日志。原始全量网络/SDF/Liberty与上一批相同；动态声明初始化、同刻竞争排序、完整SV/时序和自动预测仍有未完成边界。
