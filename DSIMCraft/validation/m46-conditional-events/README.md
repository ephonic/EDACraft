# M46 条件事件控制

接通 `@(expression iff condition)`、posedge/negedge 和各分支分别带条件的 or/逗号列表。支持现有整数/130 位四态表达式、动态 packed 选择、模块克隆和 automatic task。RTL lexer/grammar、事件节点绑定/克隆/清理及编译器同步扩展，门级 parser 保持独立。完整接口及边界见 [conditional-events.md](../../docs/conditional-events.md)。

源操作数编译为依赖表和 C++ 值求值器，复用 M45 的 Active FIFO 合并求值；实际源变化/最低位边沿成立、过程仍等待当前位置后，才读可选 iff 条件。条件单独改变不触发求值，但其读集合参与分区合并。四态条件有已知 1 才算真。带 iff 的所有源在挂起入口重取样，过滤等待前写入；无 iff 的 M45 静态复合表达式保持原缓存规则。条件回调、缓存、排队标志、FIFO 和 generation 随现有 Sim 检查点恢复，不新增轮询或 AST 解释路径。本批没有速度测量。

三共同源 truth/mixed/parallel 已由真实 VCS W-2024.09（10.131.254.103，source /apps/EDAs/syn.bash）运行。全部 **733 条直接物理位 settled 时间线**、TRACE 和自检相同，零名称别名、零位排除。guard 130 位、含 X/Z 的真/假/unknown、源缓存更新、多个分支、动态位和 130 位操作数均覆盖。VCS 比较为 settled 位，native 多后端/格式及跨平台比较完整 ordered 逐信号事件，不声称 VCS 同刻全部瞬态顺序对齐。

五个原始探针保存共同输入、原始诊断、编译/运行状态和 TRACE。entry 核对整信号、复合及选择操作数入口；guard_only 核对条件独立变化及分支优先级；sampling 核对同过程写入与 #0 前后条件取样。上述三个接受/输出一致。short_circuit（条件用户函数、副作用）和 named（命名事件直接加 iff）由 VCS 接受、native 明确拒绝，作为两个缺口保留，不计作已支持或对齐。拒绝诊断也由 verify.py 核验。

三后端 × 两波形格式 × ordered/settled 共 36 捕获；truth/mixed 在 1ns 悬挂期间实际失败预测并恢复，共 **38 捕获、2 回滚**，完整 ordered 逐信号事件和 stdout 一致。六类拒绝通过。parallel 有两个实际独立分区、任务重复激活/入口局部条件；时钟与条件分别由不同过程写入。另以 --threads 8 仅编译检查仍为两个分区，核对 guard-only 依赖合并，不把这次 emit-only 算作八线程实跑。独立数学时间线核对计数变化及任务交付。

最终 macOS ASan/UBSan parser 全部语义单测、三语料各三轮解析/清理、三个实际最终生成程序和完整 ordered 事件通过，parallel 使用实际双线程程序；三个 kernel/wheel/compact 配置均通过，含 guard-only 通知、Active 取样、四态真假、待求值任务检查点和实际失败预测。leak 检测关闭。四份实际 C++（三串行及一个双线程）重生成字节核对，三个 sanitizer 消费 CPP 的 hash 与对应最终程序相同。

本地 23 项定向 CTest 全部通过，247.59 秒；新增三模型回归另行通过。头文件消费者重新构建后，15 项最终内核检查全部通过，1.96 秒，见 units-final.log。M45 原 iff 负例转为本批正例，现有 M45 回归负例为五类；历史六类报告不改写。Linux 同源干净构建 24 项 CTest 全部通过，302.94 秒，退出 0；四份实际完整 CPP 字节一致，三模型完整 ordered 逐信号事件和 stdout 跨平台一致，Linux 再次核对相同 VCS 733 条位时间线及原始探针通过。见 linux/tests.log、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。

冻结 999 文件源包 SHA256 `b9a0fe62c8d5d956cdb6521c5460cc01a3bd6a8ad7ef5fa06cfa416c2036fd80`，清单见 source-manifest.json；冻结后所列源文件未改。plan1017.md 和本批验收输出不在冻结清单。local/linux/vcs/probes/sanitizers 保存实际输入、CPP、IR、日志和波形，不保存模型二进制。未跑全量 CTest、Linux sanitizers 或新性能测试。

RTL grammar 与配套生成文件同时提交，用 Bison 3.8.2 / Flex 2.6.4 重生成。Bison 原有与当前均为 47 个 shift/reduce 冲突，没有增加冲突；原有 empty-rule 警告保留。命令为 `bison -p verilog --defines=PATH/verilog_yacc.hpp -o PATH/verilog_yacc.cpp PATH/verilog.y` 及 `flex -Pverilog --nounistd -o PATH/verilog_lex.cpp PATH/verilog.l`，PATH 为 third_party/edacraft_parsers_20261017/verilog_parser/src/parser/verilog；根构建仍使用已提交生成文件，不要求安装生成器。

复跑：`ctest --test-dir build -R '^(rtl_conditional_events|conditional_events_kernel|conditional_events_wheel|conditional_events_compact)$' --output-on-failure`；`python3 validation/m46-conditional-events/verify.py`；其余 run-vcs/run-probes/run-sanitizers/run-linux 脚本保留完整流程。

仍缺事件源/条件中的用户函数和副作用、命名事件直接加 iff、完整层次/动态对象及容器事件、fork/join、动态进程、完整事件区域和 SVA/UVM。历史差异保留，不声称全部 SystemVerilog/VCS 功能或速度对齐。
