# M50 非阻塞赋值内部事件控制

接通 `q <= @(event) rhs` 和 `q <= repeat(count) @(event) rhs`，发起进程立即继续。每笔更新分别保存取样值、目标地址、剩余次数和表达式基线，支持同一赋值点多笔挂起与不同次数。源变化驱动 Active 判断，条件满足后进入 NBA；不通过挂起发起进程冒充非阻塞，不在运行中注册进程，不轮询。按需启用 DSIM_EVENT_NBA_ENABLED，未使用该功能的模型不增加相应运行时表/分支。功能说明见 [event-nba.md](../../docs/event-nba.md)。

支持普通信号、表达式/选择、边沿、混合列表、静态命名事件、iff、原有无外部副作用 automatic 事件函数；覆盖 130 位 signed/四态转 bit/enum、动态 packed 目标/拼接、数组字目标、automatic task 返回后交付、分区及实际失败预测。次数/右值可来自 automatic task，取样后与调用槽脱离；事件源/iff 和非阻塞目标中的 automatic 变量依据 IEEE 1800-2017 §13.3.1 明确拒绝，VCS 的 auto_guard 原始诊断同样拒绝。RTL/gate parser 仍分开；本批只扩展 parser 绑定/清理单测，grammar/lexer/生成文件未改。

真实 VCS W-2024.09（10.131.254.103，`source /apps/EDAs/syn.bash`）先核对取样顺序：**非阻塞重复事件赋值先 RHS、再次数**，不同于 M49 阻塞形式。目标地址在发起时求值；零/负/X 次数直接排 NBA，晚于 Active 与 `#0`。新源码五个共同模型 sample/targets/repetition/expressions/parallel 字节相同，全部 TRACE、自检与 **1345 条物理位 settled 时间线**一致，未使用名称别名或位排除。M49 的非阻塞赋值负例已升级为本批正例，M49 历史报告不改。

十个原始探针保存原源、编译/运行退出码、日志和 TRACE。automatic/burst/capture/expressions/order/same_site/zero 七项接受/输出对齐；auto_guard 两端拒绝。**两项不算对齐**：concat 的动态拼接目标调用静态索引函数，native d=32、VCS d=0（整数索引两端均 b=32）；evaluation 的索引函数与重复事件组合由 native 接受，但 VCS 在 GenLHS_NBA/gate.c 内部断言退出255。保留完整原始输出，不将编译器内部错误当语法不支持。共同 targets 模型使用整数拼接索引，并保留单目标函数索引；未掩盖原始 concat 差异。verify.py 严格核对全部 probe 身份/状态/输出及例外分类。

编译器复用普通事件/iff 的源生成与读写依赖收集；运行时固定订阅与各笔通知标记隔离晚发起记录，避免重放较早已排队发生。普通复合表达式缓存继续随依赖变化更新，需入口取样的源由各实例持有新基线。每轮最多消费一次合并发生，计数未满则重挂；交付后释放记录拥有的值和目标容器。Active/NBA、待交付记录、计数、缓存与通知标记随 Sim 快照复制。批量门求值遇新类型任务必须返回主调度器，compact 信号也有对应通知分支。

三个直接内核（kernel/wheel/compact）验证千笔同点挂起、释放与稳定交付、晚订阅隔离、同刻合并/iff Active 取样、复合缓存与两源相消、triggered 查询、队列中检查点、失败预测及门级 batch ID 隔离。三后端 × 两格式 × 两模式的五模型共60捕获；前三模型在1ns实际失败预测/恢复另加3捕获，共 **63捕获、3回滚**，全部 ordered 逐信号流和 stdout 一致。七类拒绝通过；另核对独立计算的宽结果/目标写入/任务交付时间线和真实 partitions=2。--threads8 emit-only 仍分两个域，仅为依赖分区检查，不称八线程实跑。

本地 **37 项定向 CTest** 全通过，264.4秒；新内核修改后的三配置另行重建/验证通过。macOS ASan/UBSan parser 语义单测、五语料各三轮清理、五份实际最终程序及完整 ordered 流、三直接内核通过，包含实际双线程，leak检测关闭。六份完整实际CPP（五串行、一双线程）重新生成字节一致，五个 sanitizer CPP hash 对应最终实际程序，不使用删头片段比较。

Linux 同源干净构建 **37 项 CTest** 全通过，541.53秒，退出0；六完整CPP及五模型完整 ordered 逐信号事件/stdout跨平台一致，再次核对相同VCS的1345条位时间线。十个原始探针分类使用保存的本地/VCS记录复核，未在Linux重新运行该组原始探针。冻结 1074 源文件，源包SHA256 `57d5700db93ff83b23c1cd87f7edc6ec6f13a737f2d2402ca7382db58517c0e5`；source-manifest.json 所列文件未改，plan1017.md和验收输出不在清单。证据 local/linux/vcs/probes/sanitizers 保存源码、实际CPP、IR、日志/退出码和波形，不保存二进制。

复跑：`ctest --test-dir build -R '^(rtl_event_nba|event_nba_kernel|event_nba_wheel|event_nba_compact)$' --output-on-failure`；`python3 validation/m50-event-nba/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py保存对应流程。

仍缺整unpacked数组/隐式内部事件控制、复合赋值时间控制、fork/join与动态进程、完整事件句柄/数组/形参、package/interface/class、动态容器、完整事件区域/SVA/UVM等；static/外部副作用事件函数及其他历史差异保留。本批未做全量CTest、Linux sanitizer或新的性能测试，不称全部SV/VCS功能或速度对齐。
