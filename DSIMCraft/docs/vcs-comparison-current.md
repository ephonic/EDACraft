M235 当前功能进展：未修改的 Accellera UVM 2020.3.1 已通过基本 run_test、sequence/driver/factory/config_db/analysis、field 工具与 clone/copy/compare/event、virtual interface 驱动真实 DUT 后独立 monitor/scoreboard、8192 位字段 pack/unpack。后两条同源 VCS 分别输出 3/303 与 8196/8196；真实 DUT 集成亦通过完整前端/原生 ASan/UBSan。条件是 UVM_NO_DPI 和原生 -O0 功能验证，发布及新打包 sanitizer 收据见 [M235](../validation/m235-stream-enums/README.md)。

这不代表完整 UVM/VCS 支持。联合对象图随机化、DPI open array、带参数 covergroup.sample、完整 SVA/VPI 与 virtual interface 子程序/clocking/数组等仍有缺口。VCS 接受而 dsim 拒绝的隐式 stream→enum 和部分 stream 左值边界也单列。以下功能表与速度数字为各历史批次记录，不能当作 M235 完成度或当前速度；本轮没有新的性能对照。

# dsim 与 VCS 当前对照（2026-11-02）

最新功能状态以 [M215 验收](../validation/m215-uvm-reflection/README.md) 和 [功能状态](vcs-feature-status.md) 顶部为准：原版 UVM 已越过 `$typename(T)`、字符串条件分支和字符串队列流操作，当前停在寄存器序列字段宏的数组语义，仍未完整运行；C910 原始源文件已完成通用分片原生构建，最小 RV64 镜像实际 TEST PASS；完整 ISA 和效率仍未对齐。新增共享函数模式及调用语义修复不构成 VCS runtime 对比。下面 M163 等“当前”描述是相应历史批次状态。

按 REPORT-GAP2 推进后的最新功能记录见 [功能状态](vcs-feature-status.md)：class/继承/虚拟派发、参数化类、static 类成员、int/string 键容器、数组值调用已有原生执行子集；M163 补 [local/protected 成员权限](class-access.md)。原始 r01/r02 已纳入运行回归。**未修改公开 UVM 仍不能原生编译运行**，当前语法首错是 `uvm_globals.svh:124` 的 DPI-C export。约束随机、mailbox/semaphore、虚拟接口/clocking、功能覆盖和 DPI 等仍缺；首错推进不等于完整 UVM 支持。M163 Mac 最终五组778捕获、parser/格式/原生DB、实际入口和 sanitizer 复核通过，稳定版已更新；103 无响应，无本批新 VCS/Intel 或速度结论。下列历史测量仅适用于其冻结版本。

M140 接通[有限序列作为蕴含前件](sequence-antecedents.md)：`a ##N b |->/|=> c`、命名序列、分组与固定连续重复，区分前件空成功和后件失败，并接通采样、异步取消及事务恢复。双端五组发布回归通过，新组各 29 份逐信号有序捕获、5 次预测提交/5 次回滚、4 次预算续跑、2 次 checkpoint 恢复和 15 个拒绝例通过，实际并行为两分区。五模型全部 TRACE 及层次归一化后的全部 1503 个声明位 settled 时间线与 VCS 一致。完整 parser 和 11 份生成程序 ASan/UBSan 通过；Mac 与 103 Intel 稳定入口已更新。六个旧模型仅在替换嵌入 runtime 文本后生成 C++ 相同，不能表述为全部原始 CPP/运行时不变；七个其他 runtime 头相同。范围/无界重复、序列形参、多时钟和完整 SVA/class/UVM 仍缺，本批没有速度测量。详见 [M140 验收](../validation/m140-sequence-antecedents/README.md)。

M139 已修复 cases 下两组新问题：标量 `[0]`/零边界宽度一选择被误报，以及大型展开式一次性 TB 的生成 C++ 编译超时。原始输入和 180 秒预算保持不变；SRAM 全部 4480 阶段、memory 全部 3840 阶段通过，同源 VCS 重新运行通过。Mac 编译分别 56.896/60.101 秒，103 Intel 分别 160.761/168.430 秒。双端各三组发布回归及 parser/格式/原生 DB 检查通过，每端 26 捕获、18 次预算恢复、22 次检查点恢复、预测提交/回滚各一次及 5 个拒绝例通过。稳定入口已更新。六个旧模型生成 C++ 和八个 runtime 头文件保持一致；103 原生编译选项由 `-O3 -xHost -ipo` 改为 `-O2 -xHost`，保留 strict FP，未重新测运行速度，生成代码一致不代表相同原生性能。详见 [M139 验收](../validation/m139-memory-cases/README.md)及[实现范围](memory-case-fixes.md)。

前一发布为 [M138](../validation/m138-named-sequences/README.md)，新增[命名有限 sequence](named-sequences.md)：前向/嵌套引用、空括号调用、词法作用域和 generate 克隆。两端各六组回归通过，新组各 25 份有序波形、5 次预测提交、5 次回滚及 53 个拒绝例通过；五个同源模型的 1275 个直接同名声明位与 VCS 完整 settled 时间线一致，另以无歧义的点号层次归一化覆盖全部 1504 位，包括作用域遮蔽计数。Mac 和 103 Intel 稳定入口已更新；完整 parser 与九个生成程序 ASan/UBSan 通过。六个旧模型生成代码及八个 runtime 头文件与 M137 相同，没有新的性能测量。序列形参、范围/无界重复、sequence antecedent、多时钟及完整 SVA/UVM 等仍缺。

前一发布为 [M137](../validation/m137-sequence-groups/README.md)，新增[有限括号序列及子序列重复](sequence-groups.md)，支持 `(a ##N b)[*M]`、嵌套串接、实例参数和采样函数。两端各八组回归通过，新组各 25 份逐信号有序波形、5 次预测提交、5 次回滚及 30 个反例通过；五个同源模型在两端分别与 VCS 的 1275 个共同声明位完整 settled 时间线一致，scope 拼写不同的未配对声明另列。Mac 和 103 Intel 稳定入口已更新；空/范围/无界重复、命名 sequence、sequence antecedent 和完整 SVA/UVM 仍缺。六个旧模型生成代码及八个 runtime 头文件与 M136 相同，没有新的性能测量。

前一发布为 [M136](../validation/m136-sequence-repetition/README.md)，新增 SVA 固定正数连续重复 `expr[*N]`，贯通实例参数、固定周期串接、采样函数、异步取消和事务回放。计数限 1..256，整个序列仍限 256 阶段/65536 拍；空/范围/无界重复和完整 SVA 尚未补齐。没有新的性能测量；旧负载与既有 SVA 模型生成代码及八个 runtime 头文件保持不变。

前一批 [M135](../validation/m135-budget-resume/README.md)，补充生成过程 PC 指令边界的预算中断恢复，保留队列顺序并支持该中断状态的 checkpoint；函数内部和任意 callback 的部分执行仍不能自动续跑。当前未重新测速。

前一批 [M134](../validation/m134-package-exports/README.md) 新增 package 显式/通配 export、多层与菱形重新导出，保留类型属性、词法函数及共享变量身份。四组同源模型的 TRACE 和 258 个共同声明位完整 settled 时间线与 VCS 一致；两端新组各 16 份有序波形、2 次预测提交、2 次回滚及 17 个负例通过。13 个边界探针中有 2 个明确的 VCS 宽松接受差异，未计作全部兼容。上一批 [M133](../validation/m133-header-imports/README.md) 的头部 import/typedef 端口和 [M132](../validation/m132-region-transport/README.md) 的三目四态修复继续保留。功能优先，速度优化后置；M134 的生成代码/runtime 保持性结论不适用于 M135 的恢复机制改动。最近正式性能数据仍为 [M130](../validation/m130-native-cases/README.md)。

以下保留历史对照。M111 发布身份见 [M111 验收](../validation/m111-scalar-dispatch/README.md)，VCS 对照版本为 103 上的 W-2024.09_Full64。当前仍不能替代完整 VCS，没有完整标准覆盖矩阵，因此不给出功能兼容百分比。

M111减少标量set/drive调用的栈参数传递，并将已知常量标签的精确case编译成原生switch。完整原始负载、同核轮换三轮：CPU16.77→14.89s（11.2%），CRC5.25→4.42s（15.8%），muldiv11.90→11.07s（7.0%）；相应VCS CPU为5.72/3.92/6.90s，目前耗时比为2.60/1.13/1.60。短AXI4不作吞吐结论。固定活动前缀执行步数/全信号状态哈希相同，指令减少5.9%/5.4%/2.9%。调度器未改用批处理，候选没有稳定收益；同源对照另修复了动态case逗号标签的副作用短路差异。详见[机制与边界](scalar-dispatch.md)。

M110在无观察需求时缓存automatic标量函数局部四态值，保留执行预算及异常时的精确状态。原始完整负载、同核轮换三轮：CRC CPU 6.30→5.24s（改善16.8%），VCS为3.89s，差距缩小到1.35倍；CPU和muldiv没有稳定收益。CPU两份可执行文件哈希相同。当前CPU/CRC/muldiv耗时为VCS的2.93/1.35/1.70倍；这批是单核比较，DSIM单执行分区不能解释该差距。机制、回退条件及验证见[单核优化](function-locals.md)。

M109减少复杂纯谓词的中间值计算，修复自然并行run逐事件同步而不能利用窗口的问题，并将检查点恢复从两次全量复制减为一次复制后移动。原始完整RTL负载、GCC O2、CPU0、预热及三轮轮换的CPU中位数：CPU17.05→16.75s、CRC6.34→6.33s、muldiv11.97→11.77s、AXI4不变；仍为VCS的2.94/1.62/1.68倍CPU耗时，串行改善有限。四个原始负载仍是一个执行分区。另测同步为主的四独立域，25万次同步降至246次，2.867→0.022s；重复恢复大检查点0.557→0.303s，这些专项收益不能外推原始RTL或VCS速度。新组44份VCD、261组精确预算/状态及六次预测接受/拒绝通过，同源VCS的70行TRACE与573位完整settled时间线一致。详见[M109方法与边界](runtime-windows.md)及[完整测量](../validation/m109-runtime-windows/README.md)。此前等待重挂优化见[M108](../validation/m108-wait-rearm/README.md)。

新增 [$fread](binary-io.md) 的 packed 及固定一维数组输入，覆盖 byte order、短读、EOF、地址副作用、automatic/ref 和回滚。五个同源 VCS 模型有明确的输入、输出和波形验收；零字节 EOF 的 VCS 漏记 VCD 更新单列。`$ferror`、完整实数输入和完整验证语言仍未补齐。

| 范围 | 已实现并在相应子集验收 | 主要缺口 |
| --- | --- | --- |
| RTL | 编译式四态/宽值、层次/generate、常用控制流、数组/聚合/枚举、package、interface/modport、task/function/ref、部分递归/常量函数、字符串、精确case、字符索引及整数转换方法 | 完整动态容器/类型组合、访问控制、完整类类型语义及复杂对象验证环境 |
| 验证 | 立即断言、单时钟并发 property、固定周期序列与正数连续重复、部分采样/随机函数 | 完整类验证语义、约束 randomize、mailbox/semaphore、完整 UVM、covergroup/覆盖数据库、完整 SVA、DPI/VPI |
| 接口与时钟 | 参数化 interface/modport、接口传递及共享状态、子程序按名称/原型 import | interface 实例数组、modport export、虚拟接口、clocking blocks |
| 门级/时序 | 独立网表 parser、Liberty 逻辑/时序单元、SDF IOPATH/INTERCONNECT 与受支持检查/条件路径 | 任意厂商 Verilog/UDP、完整 specify/强度/脉冲、notifier 和负检查模式等 |
| 并行/预测 | 独立域线程、检查点及失败预测回放 API | 通用自动预测器、增量日志、复杂时序域自动安全切分；函数内部、任意 callback 及复杂多分区预算耗尽的续跑仍未完整支持 |
| 原生 DB | 不调用工具的 cells/pins/tables/CCS 对象读取与覆盖报告 | 完整对象归属、逻辑/时序函数和单位装配；不能直接生成完整仿真库 |

功能范围以各专题文档的最新限制为准。[M135](budget-resume.md) 专门验证安全 PC 边界的中断恢复；[M132](../validation/m132-region-transport/README.md) 历史上 reference 同样报错的 142 组仍不能追记为恢复成功，函数内部中断等缺口继续保留。REPORT5 的 p21/p27 是测试预期误判：四份同源模型与 VCS 全部输出和 954 位时间线相同，详见 [复核](report5-review.md)。这不能证明完整语言覆盖。

M104 接入 [格式化输入扫描](formatted-scan.md)：$sscanf/$fscanf 的整数/进制、string/packed、字符、字段宽度、转换抑制、字面量与空白，连接 automatic/ref、final、分区依赖及预测回滚。完整浮点/原始二进制扫描格式、ferror 和完整验证语言仍待实现；fread 已在 M107 接入上述子集。验收范围及发布证据见 [M104](../validation/m104-formatted-scan/README.md)，不据此推断完整兼容或速度。

M103 新增 [通用文本文件 I/O](file-io.md)，覆盖 FD/MCD、读行/字符、定位、格式化输出及预测期间文件副作用隔离。完整错误接口和交互输入仍待补齐，九个同源模型的45行输出、12份文件字节及1816个数值波形位与VCS一致；两端各9项发布检查通过，新组72份VCD/9次拒绝回放/9次接受提交、九个生成程序及事务内核sanitizer通过。验收见 [M103](../validation/m103-file-io/README.md)。REPORT7已撤销三元运算误报，其已测基线通过；这不等于完整语言覆盖。

M102 新增 [plusargs 与动态格式化](testbench-io.md)。七个同源模型的完整输出、1553个数值波形位及三组额外运行参数与VCS一致；每端新组覆盖49份VCD、7次失败预测回滚和真实两分区。实数/浮点及完整格式族仍有缺口，未重新测速。

M101 修复 cases 中传输观察器所需的 final、文件作用域模块类型 bind 和 %m。11 个顶层归档及 carry follow-up 对应五组不同输入；全部2759次独立采样及3754行完整输出通过新一轮VCS对照，详见[用例复核](cases-review-20261025.md)。原始竞争测试仍保留无效harness分类；完整bind、final异常退出及动态调用栈格式仍有边界。本批没有性能重测。

M100 新增 putc、四种整数解析和四种整数格式化方法，连接 automatic/ref 与预测回滚。两端各七项针对性发布检查通过；每端三个字符串组共119份VCD、14次回滚及46项明确拒绝。五个同源新模型全部输出及608物理位与VCS一致；宽putc实参和数值格式化事件通知的差异单列，见 [方法范围](string-integer.md) 和 [M100验收](../validation/m100-string-integer/README.md)。本批未重新测速，下面是M98实测结果。

M98实现与原稳定入口2a914d3、VCS重新进行同机测量。整数循环已加入受保护的本机代码，补齐字符串case及字符索引读/阻塞写，并修复声明初始化多触发字符串事件。功能验证为10同源模型全部输出及866物理位，三后端60份VCD、10次回滚、118组预算边界对照；10份实际生成程序sanitizer通过。明确的保护/回退及语言边界见 [M98](../validation/m98-integral-string/README.md)。

同机固定CPU0，单线程无波形/覆盖/调试，预热一次再交替三轮；运行CPU中位数如下。共享机器未锁频，初始化计入CPU，编译另计。

| RTL负载 | 原稳定版 | M98稳定版 | VCS | M98/VCS耗时比 |
|---|---:|---:|---:|---:|
| 整数LCG十亿次 |20.24s|1.52s|1.67s|0.910×|
| 时钟/NBA三千万周期 |4.29s|4.27s|3.90s|1.095×|
| 64过程扇出三百万周期 |8.14s|7.99s|7.86s|1.017×|

整数合成模型加速13.32倍，不能外推到所有整数RTL或大设计。M98实际生成C++在103上GCC -O2编译，两端发布入口重生成的三个C++哈希与实测版本一致，并已复跑十亿次整数校验；GCC编译时间不能当作完整RTL编译时间。36份预热/运行TRACE、GNU time CPU、中位数与比值独立复核通过。M97旧基线12.09/1.10/1.04倍保留为历史记录，不与本轮混算。

REPORT6的p21/p27继续为错误oracle，修正后的探针/脚本与VCS全部914位对齐，用户12项probes2通过，见 [REPORT6](report6-review.md)。

M100/M101/M102/M103/M104没有重测RTL、门级/SDF或波形性能；上表仅为M98测量版本。历史完整 SDF 69.415/9.055 秒（7.67×）只保留为历史证据，不能当作当前版本结果，也不能与本轮 RTL 数字混算。

M105 targets the original REPORT-PERF CPU/CRC/muldiv workloads with generated unary specialization, scalar replication, ready-queue inlining and guarded native function loops. Method, actual repeated results and remaining VCS gap: [runtime evidence](../validation/m105-runtime/README.md). The original report's timings used changing dsim releases and best wall time; they are not mixed with the fixed-binary medians in this measurement.

M145 补齐 [包默认及显式子程序生命周期](package-lifetimes.md)，并修正 SystemVerilog before 等尚未实现语法的保留字被当作标识符接收的问题；这不表示 class/clocking 等语法已实现。新增 RAM 原始 case 为非法输入接收差异，更名后的设计参考已通过，不列为合法设计误仿真。本批不测速。

M215：先补齐 UVM 功能，再优化性能。编译耗时是否偏慢须在同设计、同条件下与 VCS 比较；当前分片编译记录和超时仅作为本工具验收记录，不据此给出相对编译速度结论。
