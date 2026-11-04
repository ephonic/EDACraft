# M49 阻塞赋值内部事件控制

接通 `q = @(event) value` 和 `q = repeat(count) @(event) value`：次数先于右值求值，右值按目标上下文宽度在入口取样，进程挂起，恢复后求动态目标并写入。支持整信号/表达式/受支持 automatic 函数事件、iff/静态命名事件和混合列表；包含 130 位/signed/bit/enum、动态 packed 选择/拼接、数组字目标及 automatic task、分区和失败预测恢复。功能说明见 [intra-event-assignments.md](../../docs/intra-event-assignments.md)。

修复阻塞事件赋值被普通 assignment expression 归约遮挡的 parser 路径；赋值专用 repeated-event grammar 复用 REPEAT 循环及 timing-control AST，补齐阻塞/非阻塞控制节点的语义检查、三轮错误恢复和参数化模块克隆单测。门级 parser 保持独立。Bison 3.8.2 同步重生成 verilog_yacc.cpp/header，header 因内容不变没有 diff；原有与当前均为 47 个 shift/reduce 冲突，lexer/生成 lexer 未改。命令与日志见 bison.log 和 bison-baseline.log。

编译器抽出与普通显式事件控制共用的等待生成器。保存值、repeat 计数、PC 与已有等待状态随进程快照恢复；动态次数只存一个计数器，循环使用同一固定等待点，不按次数展开。读写、副作用、条件/函数体全局依赖加入原分区图；未新增 runtime/parallel 表、动态进程、轮询或运行时 AST。M48 四份完整实际生成 C++ 重生成字节不变，见 baseline-identity.json。本批没有新速度测量。

四个字节相同共同源 sample/targets/repetition/parallel，由 10.131.254.103 的实际 VCS W-2024.09（source /apps/EDAs/syn.bash）运行。全部 **1260 条物理位 settled 时间线**、TRACE 与自检一致，无名称映射、无位排除。sample 核对 RHS 单次/入口取样、130 位 signed 扩展、四态转 bit 和 enum；targets 核对恢复后索引/拼接和未知目标不写；repetition 核对次数先于 RHS、后续 count 改变无效、零/负/X 次数不等但仍取 RHS、条件命名事件与函数表达式；parallel 核对任务保存值与计数隔离。VCS 比较为 settled 位；native 后端/格式与跨平台比较完整 ordered 逐信号事件，保留同刻变化，不称 VCS 完整瞬态顺序对齐。

五个原始探针：blocking/target/repeat 的接受及 TRACE 对齐，单独验证数组字目标函数在恢复后才执行一次、次数/RHS顺序为12；array 两端均拒绝，VCS 原始诊断为 unpacked array 内部控制不支持；nba 由 VCS 接受、native 明确拒绝，作为功能缺口保留。非阻塞内部事件赋值必须让发起进程立即继续并支持多个待交付实例，本批没有用阻塞挂起冒充。verify.py 核对全部源 hash、编译/运行状态、TRACE 及拒绝诊断。

三后端 × 两格式 × 两模式共 48 捕获，前三模型在 1ns 挂起期间实际失败预测并恢复，共 **51 捕获、3 回滚**，ordered 逐信号事件及 stdout 一致。九类拒绝通过。独立计算宽结果、目标写入/索引调用、次数求值顺序与任务交付的 settled 时间线。parallel 实际两个独立分区；另以 --threads 8 编译检查仍为两个分区，核对 guard-only/函数体依赖合并，不将 emit-only 算作八线程实跑。

macOS ASan/UBSan parser 全部语义单测、四语料各三轮清理、四个实际最终生成程序及完整 ordered 波形通过，含实际双线程；leak 检测关闭。五份实际完整 C++（四串行、一双线程）重生成字节一致，四个 sanitizer CPP hash 与相应最终程序相同。未改运行时，不声称新的内核 sanitizer 覆盖。

本地 **32 项既有定向 CTest** 全通过，255.51 秒，包含动态 delay、过程循环/return、数组复制及 M43–M48 控制回归；新增 51 捕获回归另行通过。Linux 同源干净构建 **33 项 CTest** 全通过，486.61 秒、退出 0；五份完整实际 CPP、四模型完整 ordered 逐信号事件和 stdout 跨平台一致，Linux 再次核对相同 VCS 1260 条位时间线及五个探针通过。见 linux/tests.log、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。

冻结 1050 文件，源包 SHA256 `3923f45304a47c8a507f01602e375cf679a329dff68da84d1fe0e948a836b6ba`；source-manifest.json 所列文件冻结后未改。plan1017.md 与验收输出不在冻结清单。local/linux/vcs/probes/sanitizers 保存实际输入、CPP、IR、日志和波形，不保存模型二进制。未跑全量 CTest、Linux sanitizers 或新性能测试。

复跑：`ctest --test-dir build -R '^rtl_intra_event_assignments$' --output-on-failure`；`python3 validation/m49-intra-event-assignments/verify.py`。其余 run-vcs/run-probes/run-sanitizers/run-linux.py 保存对应流程。parser 重生成使用 `bison -p verilog --defines=PATH/verilog_yacc.hpp -o PATH/verilog_yacc.cpp PATH/verilog.y`，PATH 为 third_party/edacraft_parsers_20261017/verilog_parser/src/parser/verilog；根构建继续使用已提交生成文件。

仍缺非阻塞内部事件/repeat 赋值、整 unpacked 数组内部事件赋值、隐式内部事件敏感控制、复合赋值时间控制、fork/动态进程、完整事件对象/事件区域、SVA/UVM 等。M47 static/外部副作用函数事件及其他历史差异继续保留，不称全部 SystemVerilog/VCS 功能或速度对齐。
