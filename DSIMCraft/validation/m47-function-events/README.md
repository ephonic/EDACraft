# M47 自动函数事件表达式

补齐事件源与 iff 条件中的无外部副作用 automatic 函数，含嵌套调用、私有局部变量/数组、signed/130 位四态、automatic task 挂起等待。编译器传递安全标志和完整读写依赖，复用已有函数 C++ 生成及表达式事件回调。RTL/门级 parser 继续分开；本批没有改 runtime/parallel、lexer/grammar 或生成解析文件，只增加 parser 清理/克隆单测。接口和限制见 [function-events.md](../../docs/function-events.md)。

源敏感集合取实参读取；函数体单独读取的全局变量不唤醒事件，仍加入分区依赖。无参数函数没有信号唤醒源。含调用的源表达式，包括外包复合运算，进入等待时重取样。iff 函数仅在源事件成立且过程仍等待时执行，条件变化本身不触发。私有函数存储也加入拥有者依赖，避免独立分区共享访问；已有快照恢复函数存储、等待缓存和排队求值任务。本批没有增加自动预测器或测量速度。

三个字节相同的共同源 value/guard/parallel，由 10.131.254.103 上实际 VCS W-2024.09（source /apps/EDAs/syn.bash）运行。全部 **533 条物理位 settled 时间线**、TRACE 和自检一致，无名称映射、无位排除。VCS 对照为 settled 位；native 后端/格式及跨平台比较完整 ordered 逐信号事件，保留同刻变化，不称 VCS 完整瞬态顺序对齐。

六个原始探针保存输入、编译/运行状态、诊断与 TRACE。entry 核对调用、posedge/iff 及调用外包运算的重新取样；sensitivity 核对函数体全局读取与实参唤醒；guard 核对无参数条件函数；noargs 核对无参数源函数。上述四项一致。side_effect 写全局计数、static 使用静态函数，均为 VCS 接受、native 明确拒绝的两项功能差距，不计入支持数量。原 M45/M46 带副作用函数差距仍保留。

三后端 × 两格式 × 两模式共 36 捕获；value/guard 在 1ns 挂起期间执行实际失败预测并恢复，共 **38 捕获、2 回滚**，ordered 逐信号事件及 stdout 一致。独立时间线核对变化/边沿计数和任务交付，九类拒绝检查通过。parallel 实际运行两个独立分区；另以 --threads 8 编译检查仍为两个分区，核对函数体/guard-only 依赖合并，不将这次 emit-only 算作八线程实跑。

macOS ASan/UBSan parser 全部语义单测、三语料各三轮清理及三个实际最终生成程序通过，含实际双线程和完整 ordered 波形比较；leak 检测关闭。四份实际完整 C++（三串行、一双线程）重生成字节一致，三个 sanitizer 程序的 CPP hash 与对应最终程序一致。本批未改内核，未新增内核实现或宣称新的内核 sanitizer 覆盖。

本地 **24 项既有定向 CTest** 全通过，228.06 秒；新增 38 捕获回归另行通过。Linux 同源干净构建 **25 项 CTest** 全通过，338.78 秒、退出 0；四份实际完整 CPP、三模型完整 ordered 逐信号事件和 stdout 跨平台一致，Linux 再次对照同样 VCS 533 条位时间线及六个探针通过。见 linux/tests.log、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。

冻结 1016 个文件，源包 SHA256 `76efecd3ef1956f3c3074efb1bbb4c353623f652b341bef0fe325e16f67ec637`，清单见 source-manifest.json，冻结后所列文件未改。plan1017.md 与验收输出不在冻结清单；local/linux/vcs/probes/sanitizers 保留实际源码、CPP、IR、日志和波形，不保留模型二进制。未跑全量 CTest、Linux sanitizers 或新速度测试。

复跑：`ctest --test-dir build -R '^rtl_function_events$' --output-on-failure`；`python3 validation/m47-function-events/verify.py`。run-vcs/run-probes/run-sanitizers/run-linux.py 保存对应运行流程；verify.py 需要本批实际 VCS 证据。

仍缺 static/外部副作用函数事件、output/inout/诊断副作用、递归、命名事件直接加 iff、fork/join、动态进程、完整事件区域及 SVA/UVM。递归负例由 parser 既有语义阶段拒绝，其诊断仍通用。历史语言/数组/诊断差异保留，不称全部 SystemVerilog/VCS 功能或速度对齐。
