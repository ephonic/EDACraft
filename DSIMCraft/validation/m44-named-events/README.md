# M44 静态命名事件同步

接通静态标量 `event`、`@e` / `@(e or signal)`、阻塞 `->`、NBA `->>` 和带常量/动态 delay 的 NBA 触发、`e.triggered` 及其变化/边沿等待。支持模块克隆、静态块/子程序、automatic task 对外部静态事件的挂起和函数触发。语法、绑定/克隆、编译进程与运行时分别接入，门级 parser 保持独立。接口与边界见 [named-events.md](../../docs/named-events.md)。

隐藏信号 ID 只表示发生，时间戳表示当前 tick 的持续查询；固定 wait-site 保存查询取样基线。事件依赖参与自动分区合并，NBA/定时池、触发状态、waiting 与订阅基线随现有 Sim 检查点恢复。新状态与 NBA 分支只在 `DSIM_NAMED_EVENTS_ENABLED` 时启用；运行期不遍历 AST 或轮询。本批修改 runtime.hpp，历史完整生成 C++ 因嵌入头而变化，不宣称旧模型 C++ 字节不变；既有运行行为通过定向回归核验。

真实 VCS W-2024.09（10.131.254.103，`source /apps/EDAs/syn.bash`）运行五个字节相同公共源。全部 **1102 条直接导出物理位 settled 时间线**、TRACE 和自检一致。全部 14 个静态事件对象按 IR 清单逐项核验，双方均未将对象导出为整数波形。VCS 未导出的 tick 函数返回槽和 input 槽共 64 位，通过共同源的 packed call_values 观察值逐位比较，同时独立检查 X 初态和 1ns 的值 4；观察位已包含在 1102 中，不相加作独立 VCS 位。verify.py 严查其他信号名称/位身份，没有任意位丢弃、名称重写或 VCS 位排除。

八个原始探针保存输入、原始接受状态、诊断与 TRACE：delayed、late、ordering、query、query_edges、sampling、function_nba 七个均接受/输出一致，parentheses 双方拒绝 `e.triggered()`。确认同刻持续查询、早发生丢失、NBA 发送者继续、delay 单次求值、函数中 NBA/延迟 NBA、查询隐式过期不通知、真基线跨 tick 不更新，以及新进入的假基线等待能接住后续触发。本批没有以 VCS 的某种先验假设代替实际运行。

五模型 handshake/triggered/nba_delay/tasks/parallel，三后端 × ordered/settled × VCD/DWF 共 60 份波形；另在 1ns 挂起期间对 handshake/nba_delay 实际执行失败预测、恢复并比较完整 ordered 逐信号事件及 stdout，合计 **62 捕获、2 回滚**。18 类拒绝检查、独立交付时间线和实际 partitions=2 同时通过。三个内核配置 kernel/wheel/compact 另核对重复发生、查询基线、时间过期、延迟队列、NBA 批次和排队检查点恢复。native 后端/格式及跨平台完整 ordered 比较保留同刻变化；VCS 比较为 settled 位时间线，不宣称所有事件区/瞬态顺序相同。

Parser 新增三轮错误恢复、事件查询和两实例克隆清理单测；同步再生词法/语法文件，仍为原有 47 个 shift/reduce conflicts。最终 macOS ASan/UBSan parser 单测、五语料各三轮清理、五个实际最终生成程序及完整 ordered 事件比较通过，包含双线程；三个事件内核也分别通过 ASan/UBSan。leak 检测关闭，见 parser-unit-final.log、sanitizers/results.json 与 sanitizers/kernel/results.json。六份最终实际 C++ 重生成字节核验，sanitizer 消费文件的 hash 与最终输出逐项一致。

本地 15 项定向 CTest 全部通过 121.16 秒（包含三个新增事件内核及 12 项既有检查）；新增五模型回归另行通过。Linux 同源干净构建 16 项 CTest 全部通过 216.77 秒，退出 0；六份完整实际 C++、五模型完整 ordered 逐信号事件及 stdout 跨平台一致，Linux 再次核对相同 VCS 1102 直接位时间线通过。见 results.json、platform-identity.json、platform-waveforms.json 与 linux-vcs-results.json。

冻结清单包含 960 个文件，压缩包 SHA256 为 2f9f6d9abc366852df1db4c8987deb4e77565085ce2e1f85a1e76319a1bdd6cf，见 source-manifest.json/source-archive.json。所列文件冻结后未改；plan1017.md 和本批验收结果不在冻结清单。local/、linux/、vcs/、probes/、sanitizers/ 保存选定实际 C++、输入、日志、波形与结果，不包含模型二进制。

复跑：`ctest --test-dir build -R '^(rtl_named_events|named_events_kernel|named_events_wheel|named_events_compact)$' --output-on-failure`；`python3 validation/m44-named-events/verify.py` 使用默认 build 捕获，传入 `validation/m44-named-events/local` 可核验归档。run-vcs.py/run-probes.py 接受输入和输出目录；run-sanitizers.py 在生成文件稳定后运行；run-linux.py 从带清单的冻结包干净构建。

仍缺事件句柄别名/null/数组/ref/形参、automatic 局部事件、一般层次事件引用、event-control 形式的非阻塞触发、wait_order/wait fork、fork/join 和动态进程。查询结果直接位选择明确拒绝；一般表达式事件控制如 @(a+b) 仍缺，本轮改为显式错误，避免静默空等待。完整 SV 事件区域、package/interface/class、动态容器、完整 SVA/UVM 及历史数组/诊断差异继续保留。未跑全量 CTest、Linux sanitizers 或新性能测试，不称全部 SV/VCS 功能或速度对齐。
