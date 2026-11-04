# M43 条件等待与函数返回类型

新增 `wait(condition)` / `wait(condition) statement`：真值立即继续，假/X/Z 挂起，相关信号变化后重查；支持宽值、动态数组字、函数实参、普通过程、循环控制和 automatic task。编译为条件 PC 与原有固定等待点，无轮询；沿用时间轮、自动分区与预测回滚，没有修改 runtime.hpp/parallel.hpp。RTL lexer/parser、语义检查与克隆单独扩展，紧凑门级 parser 未改。同时补齐 function logic/reg 默认/显式 signed/unsigned、packed 范围与 automatic 返回声明。接口与限制见 [level-wait.md](../../docs/level-wait.md)。

真实 VCS W-2024.09（10.131.254.103，`source /apps/EDAs/syn.bash`）运行五个字节相同的公共源。双方自检/TRACE、全部 **1120 条直接物理位 settled 时间线**一致，无名称别名或位排除；全部 16 个 native 数组位通过同源 packed 观察信号逐位核对，1120 已包含观察信号，不相加作独立 VCS 位数。verify.py 严查其余信号身份及未列出的数组字。四个原始探针 calls/fourstate/function/pulse 的接受状态与 TRACE 全部一致：函数实参决定唤醒集合，函数体单独读取的全局变量不唤醒；同一执行块内高低脉冲恢复后仍重查，不直接视为成功。

五模型为 handshake、conditions、functions、controls、parallel，覆盖多次握手/NBA、立即继续/常假、130 位与 X/Z、动态数组条件、函数副作用计数、无参全局读取、返回符号/宽度、automatic task 反复调用与输出复制、双实例克隆、循环 break/continue、同刻短脉冲及两个实际独立分区。串行/时间轮/threads2 × ordered/settled × VCD/DWF 共 60 捕获；handshake/controls 在 1ns 挂起期间实际失败预测并恢复，再比较完整 ordered 逐信号事件与 stdout，共 **62 捕获、2 回滚**。另核对独立数学输出/条件交付时间线、实际 partitions=2 和七类拒绝。native 多后端/格式及跨平台比较保留同刻变化；未宣称与 VCS 全部瞬态顺序一致。

Parser 三轮错误恢复、两实例克隆及新返回声明检查通过；语法再生前后均为原有 47 个 shift/reduce conflicts，没有新增冲突。Sanitizer 最初重名输入暴露 task 符号注册的空指针，现修复为 vTASK_REDEFINE 并加入三轮负例，原始失败日志 parser-unit.log 保留。最终 macOS ASan/UBSan parser 单测、五语料各三轮清理和五个实际生成程序（含双线程）的完整 ordered 事件全部通过，leak 检测关闭；parser-unit-final.log 与 sanitizers/results.json 记录终态。六份实际 C++ 经最终编译器再次生成字节核对，sanitizer 消费程序的 hash 与最终生成文件逐项一致。

本地原有八项 CTest 全部通过 251.59 秒，新增五模型 62 捕获回归另行通过；M42 七份完整实际 C++ 重生成字节不变，见 m42-identity.json。Linux 同源干净构建九项 CTest 全部通过 335.60 秒，退出 0；六份完整实际 C++、五模型完整 ordered 逐信号事件及 stdout 跨平台一致，Linux 五共同源再次核对相同 VCS 1120 直接位/16 数组观察位通过，见 results.json、platform-identity.json、platform-waveforms.json 和 linux-vcs-results.json。937 文件源清单与压缩包 hash 见 source-manifest.json/source-archive.json，所列文件冻结后未改；plan1017.md 和本批验收输出不在冻结清单。local/、linux/、vcs/、probes/、sanitizers/ 保存选定实际生成 C++、输入、日志、波形和结果；不包含编译二进制。

复跑：`ctest --test-dir build -R '^rtl_level_wait$' --output-on-failure`；`python3 validation/m43-level-wait/verify.py` 使用默认 build 捕获；`python3 validation/m43-level-wait/verify.py validation/m43-level-wait/local` 校验随仓库保存的捕获。run-vcs.py/run-probes.py 分别接受语料目录与输出目录；run-sanitizers.py 在回归生成文件稳定后运行；run-linux.py 从带 dsim-source-manifest.json 的冻结包解压源干净构建。

wait fork/wait_order、命名 event、fork/join、动态进程、package/interface/class、动态容器、完整 SVA/UVM/事件区域仍缺，先前数组赋值、选择告警等 VCS 差异继续保留。未跑全量 CTest、Linux sanitizers 或新性能测试，不宣称全部 SystemVerilog/VCS 功能或速度对齐。
