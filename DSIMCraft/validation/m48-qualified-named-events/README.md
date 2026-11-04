# M48 条件命名事件

补齐 `@(event iff condition)`、or/逗号混合列表、宽四态条件和无外部副作用 automatic 条件函数，支持 automatic task、阻塞/NBA/延迟触发、分区和实际失败预测回放。复用现有事件 AST，RTL/门级 parser 继续独立，lexer/grammar 和生成解析文件未改；增加三轮错误恢复/模块克隆清理单测。接口及边界见 [qualified-named-events.md](../../docs/qualified-named-events.md)。

发生模式复用表达式事件表和 Active FIFO，条件在任务执行时读取。相同过程段中触发后改真可以放行，改假会过滤；连续偶数次触发仍算发生，不依赖隐藏位最终变化。条件独立变化不触发重试。仅已挂起且代际匹配的等待接收发生，旧任务不能重放到新等待；同一排队任务可被新代际的真实发生更新。普通命名事件保持直接等待路径。新发生代际状态/检查仅在同时启用命名事件及表达式事件时编入；与队列一起随已有 Sim 快照恢复，没有轮询、AST 解释或新预测器。本批未测速。

三个字节相同共同源 occurrence/timed/parallel，由 10.131.254.103 的实际 VCS W-2024.09（source /apps/EDAs/syn.bash）运行。全部 **486 条物理位 settled 时间线**、TRACE 与自检一致，无别名、无位排除。覆盖 130 位/X/Z 真假、混合分支、NBA/延迟交付、晚进入等待、persistent triggered 查询、automatic 条件函数及 task。VCS 比较为 settled 位；native 后端/格式及跨平台比较完整 ordered 逐信号事件，不称 VCS 完整同刻瞬态顺序对齐。

五个原始探针全部接受/TRACE 对齐：basic 直接复用 M46 原 named 拒绝探针，关闭该缺口；entry 核对早触发丢失；generation 核对混合分支已唤醒后不把发生重放到后一次等待；mixed 核对各分支独立条件；sampling 核对同段条件取样、偶数触发及条件变化不回放。保存原始输入、编译/运行状态与诊断，verify.py 核对源 hash 和实际 TRACE。M46 历史拒绝记录保持原样，当前 conditional_events 回归移除这一负例，现有拒绝为五类。

三后端 × 两格式 × ordered/settled 共 36 捕获，occurrence/timed 在 1ns 挂起期间实际失败预测并恢复，共 **38 捕获、2 回滚**，ordered 逐信号事件及 stdout 一致。独立时间线核对发生计数、NBA交付、晚进入者和任务输出；八类拒绝检查通过。parallel 实际两个独立分区；另以 --threads 8 编译检查仍为两个分区，验证条件/函数体全局依赖合并，不将 emit-only 算作八线程实跑。

三个直接内核配置 kernel/wheel/compact 检查 Active 取样、未知真假、偶数触发、等待代际替换/拒绝、可重用待求值检查点、延迟发生失败预测恢复及 compact 普通信号混合分支。macOS ASan/UBSan parser 全部语义单测、三语料各三轮清理、三个实际最终生成程序及完整 ordered 波形通过，含实际双线程；三个内核配置也通过 sanitizer，leak 检测关闭。四份实际完整 C++（三串行、一双线程）重生成字节一致，三个 sanitizer CPP hash 与对应最终程序一致。

本地受影响头文件消费者全部重新构建后，**28 项定向 CTest** 全通过，194.32 秒；新增 38 捕获回归另行通过。Linux 同源干净构建 **29 项 CTest** 全通过，363.68 秒、退出 0；四份实际完整 CPP、三模型完整 ordered 逐信号事件和 stdout 跨平台一致，Linux 再次对照相同 VCS 486 条位时间线及五个探针通过。见 linux/tests.log、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。

冻结 1033 个文件，源包 SHA256 `c22a3de2443413e42c8af731936874776bed5479482d16dc4ef6823247f6105a`；source-manifest.json 所列文件冻结后未改。plan1017.md 与验收输出不在冻结清单。local/linux/vcs/probes/sanitizers 保存实际输入、CPP、IR、日志和波形，不保存模型二进制。未跑全量 CTest、Linux sanitizers 或新性能测试。

复跑：`ctest --test-dir build -R '^(rtl_qualified_named_events|qualified_named_events_kernel|qualified_named_events_wheel|qualified_named_events_compact)$' --output-on-failure`；`python3 validation/m48-qualified-named-events/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py 保存相应流程。

仍缺事件句柄/别名/null、event 数组/形参、automatic 局部 event、wait_order/fork、动态进程、完整事件区域、SVA/UVM 等；条件中的 static/外部副作用函数仍拒绝，保留 M47 已知差距。历史语言/数组/诊断差异不改写，不称全部 SystemVerilog/VCS 功能或速度对齐。
