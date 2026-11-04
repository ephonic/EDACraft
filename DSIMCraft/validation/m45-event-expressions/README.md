# M45 表达式事件控制

接通 `@(expression)`、posedge/negedge 表达式及混合列表，支持算术/逻辑/比较/拼接、130 位四态、静态/动态 packed 选择、静态数组字、模块克隆和 automatic task。原有 grammar 已能接收表达式，本批扩展 parser 事件节点构造、绑定/克隆清理单测及编译器；拼接保留为一个表达式，不能拆成 OR 列表。词法/语法生成文件和紧凑门级 parser 未改。接口、取样规则和边界见 [event-expressions.md](../../docs/event-expressions.md)。

新求值器与静态依赖表只在 `DSIM_EXPRESSION_EVENTS_ENABLED` 时编入模型，依赖通知在原 Active FIFO 合并求值，不轮询、不遍历 AST。缓存包含完整四态值；一般静态复合表达式在过程暂未等待时也更新，选择/automatic 表达式则在挂起入口重新取样。generation 防止旧等待点误唤醒，缓存、待求值标志、队列和等待位置共同回滚。简单整信号和 M44 直接 event/triggered 保留原路径。runtime.hpp 已改变，不宣称历史完整生成 C++ 字节不变，也没有新速度结论。

真实 VCS W-2024.09（10.131.254.103，`source /apps/EDAs/syn.bash`）运行五个字节相同公共源：全部 **1078 条直接导出物理位 settled 时间线**、TRACE 和自检一致，无名称别名或 VCS 位排除。native 全部 16 个数组位另经共同源 packed observed 观察信号逐位核验，观察位已包含于 1078，不相加作独立 VCS 位。verify.py 严查未列出的数组字和其余信号身份。

七个原始探针保留输入、原始诊断/接受状态和 TRACE。automatic、automatic_entry、automatic_expression、entry、glitch、selected 六个接受/输出一致，分别核对任务形参初始化不形成早触发、选择等待前的写入丢失、automatic 复合表达式入口、一般静态复合表达式的待求值任务、同刻合并/跨 #0 变化，以及所选位同刻脉冲过滤。functions 探针 VCS 接受而 dsim 明确拒绝，功能差距保留在 vcs-results.json；本批不把它计作对齐或通过的支持功能。

五模型 expressions/selections/edges/tasks/parallel 覆盖同值过滤、128 位以上变化、X/Z 区分、最低位四态边沿、门控时钟、动态位/数组字和越界、任务实参与多个激活、混合 named event、双实例及两个实际独立线程分区。三后端 × ordered/settled × VCD/DWF 共 60 捕获；expressions/selections 在 1ns 实际失败预测、恢复后完整比较 ordered 逐信号事件及 stdout，共 **62 捕获、2 回滚**。独立数学交付时间线、六类拒绝和 partitions=2 同时通过。VCS 比较为 settled 位；native 多后端/格式及跨平台比较完整 ordered 逐信号事件，保留同刻变化，未宣称 VCS 全部瞬态顺序一致。

三个事件内核 kernel/wheel/compact 核对缓存值、合并求值、最低位边沿、混合等待、含待求值任务的检查点与实际失败预测；compact 另覆盖负 ID 紧凑网通知；三个配置均验证门级批次遇到表达式任务时停止，避免将表达式任务 ID 误当成门级进程 ID。最终 macOS ASan/UBSan parser 单测、五语料各三轮清理、五个实际最终生成程序及完整 ordered 事件通过，包含真实双线程；三个内核也分别通过，leak 检测关闭。六份最终实际 C++ 重生成字节核验，sanitizer 消费文件 hash 与最终输出逐项相同。

本地 19 项定向 CTest 全部通过 115.95 秒（16 项既有检查及三个新增内核），新增五模型回归另行通过。M44 曾拒绝的 @(a+b) 已由本批正例接替，M44 回归负例从 18 减为 17，历史验收报告不回写。Linux 同源干净构建 20 项 CTest 全部通过 269.17 秒，退出 0；六份完整实际 C++、五模型完整 ordered 逐信号事件及 stdout 跨平台一致，Linux 再次核对相同 VCS 1078 直接位时间线与 16 数组观察位通过。见 results.json、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。

982 文件冻结源包 SHA256 为 27636c59dd06ffc022605fd84776305932590568ab2e901f41bb25c0c541144a，见 source-manifest.json/source-archive.json，所列文件冻结后未改；plan1017.md 和本批验收输出不在冻结清单。local/、linux/、vcs/、probes/、sanitizers/ 保存实际 C++、输入、日志、波形和结果，不保存模型二进制。

复跑：`ctest --test-dir build -R '^(rtl_event_expressions|event_expressions_kernel|event_expressions_wheel|event_expressions_compact)$' --output-on-failure`；`python3 validation/m45-event-expressions/verify.py` 核验默认 build 捕获，传入 `validation/m45-event-expressions/local` 可核验归档。run-vcs.py/run-probes.py 接受输入/输出目录；run-sanitizers.py 在生成程序稳定后运行；run-linux.py 从带清单的冻结包干净构建。

仍缺事件表达式中的用户函数调用/副作用、iff、一般层次引用、动态容器/对象/字符串事件；事件句柄/数组/ref、fork/join、动态进程、完整 SV 事件区域和完整 SVA/UVM 等差距继续保留。未跑全量 CTest、Linux sanitizers 或新性能测试，不称全部 SystemVerilog/VCS 功能或速度对齐。
