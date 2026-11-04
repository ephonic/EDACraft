# M15：静态用户函数与任务

本批新增静态 function/task 的编译执行：整数、signed、宽四态形参与函数返回变量、静态局部变量、嵌套调用，任务 output/inout、delay/event/NBA。函数编译成固定 PC 的 C++ 表达式，任务内联进调用进程；不使用运行时 parser AST。RTL 与门级 parser 继续分离，门级 parser 和运行时布局未改。功能边界见 [subroutines.md](../../docs/subroutines.md)，总体进度见 [plan1017.md](../../plan1017.md)。

RTL parser 修正函数体在解析时计算/裁剪控制流的问题、整数形参与默认函数返回类型、经典 task 声明分号、零形参任务及调用参数的运行时绑定，并增加递归展开保护。if/case/三目/逻辑表达式的所有分支保留语义绑定。函数运行时执行，常量函数 elaboration 尚未接入。重生成后的 Bison 仍有既有 33 个 shift/reduce conflicts，见 `parser-generation.log`。

五组用例：

- `functions`：整数循环/continue/break/case、嵌套函数、80 位 signed 返回值、归约、X 输入；外部 bias 变化区分连续赋值和 always_comb 的函数依赖。
- `state`：多个调用点共享静态局部和返回变量、条件未赋值时保留结果、赋值上下文、已知/未知三目分支的调用及副作用。
- `tasks`：入口采样 input/inout、局部静态计数、delay、事件等待、经典和零形参任务；动态数组 output 目标在返回时取地址。
- `parallel`：两个独立参数化实例的函数和延时任务、延迟 NBA；真实执行两分区、七窗口，两条输出轨迹有独立 Python 预期。
- `generate`：8/80 位参数化 generate 子程序、任务内函数调用及 delay/NBA。

本地最终回归五例 **62 次捕获**通过：serial/time-wheel/双线程 × ordered/settled × VCD/DWF，以及 `state`/`tasks` 两个真实失败预测回放。完整事件流按同一模式跨后端/格式比较；两个数组字及两条并行输出另有独立值/时间预期。10 类非法/未支持用法明确拒绝，进程崩溃不算诊断通过。见 `local-subroutines.log`、`local-results.json`、`parallel-stats.log` 和 [回归脚本](../../tests/subroutines/regression.py)。

11 项受影响 CTest 全部通过，183.57 秒：loop_control、integer、signed、generate、memory、always_sv、dynamic_delay、compiled_regression、gate_source_cli、preprocessing、semantic_memory。见 `local-affected.log`；本批没有运行完整 CTest 集。

四个实际生成程序（functions/state/tasks 串行，parallel 真双线程）通过 macOS ASan/UBSan；全部 settled 信号时间线与普通 ordered 捕获一致，sanitized CPP 与最终实跑 CPP SHA 相同。独立 parser 单测及五组源码各三次解析/清理也通过。初次 sanitizer 发现旧 `VeriNum::uxor()` 的越界读取，已修复 xor/xnor 归约，并新增跨 1/8/31/32/33/65/80/130 位、已知/X/Z 的独立计数检查。初始失败单独保留在 `initial-parser-parity-asan-failure.log`；最终通过日志为 `*-parser-san.log` / `*-runtime-san.log`。配置见 `sanitizer-config.json`，关闭 leak 检测，未运行 Linux sanitizer。

实际 VCS W-2024.09 五例的 TRACE 和 **2187 条可观察物理位时间线**全部一致。比较包含 VCS 实际导出的子程序形参、局部变量和返回变量，双向检查信号身份/位索引及完整时间线，要求 1ps timescale。VCS 未导出的三个 inline 循环局部变量和两个 unpacked 数组字在 `vcs-results.json` 逐项列出；没有忽略整个函数/任务作用域。数组另有独立预期。连续赋值只跟踪函数调用实参，always_comb 还跟踪函数体外部读取，依据此次 VCS 差分修正。

VCS 原任务 `/tmp/dsim-m15-subroutines-zBysqJ` 最终退出 0，命令见 `vcs-command.sh`，原始输入/编译日志/运行日志/波形保留在 `vcs/`。最初 state 探针的 `1'bx?sticky` 被词法器作为非法数字读入，两种工具均拒绝；加空格为 `1'bx ? sticky` 后实际重新编译运行，原始失败记录保留，不记作通过。

529 文件最终同源包 SHA256 为 `26aee0b933feb78deaa3097e4b664798de720717494e3d5f06c1cee5c4794b85`，逐文件清单见 `source-manifest.json`，已与工作区核对。Linux 原任务 224796（`/tmp/dsim-m15-linux-d0WRQA`）退出 0：manifest 校验、干净构建和四项 CTest（subroutines/semantic_memory/compiled_regression/gate_source_cli）通过，95.19 秒。日志、五份完整生成 CPP、实际 TRACE/VCD 在 `linux/`；五份 CPP 与 macOS 字节相同，Linux 实际结果另行对照 VCS 的 2187 条时间线通过，见 `linux-vcs-results.json`。最终本地编译器重新发射五份完整 serial CPP，与被验证版本逐字相同。

复核命令：

```sh
python3 validation/m15-subroutines/verify.py
python3 validation/m15-subroutines/verify.py validation/m15-subroutines/linux/source/build/rtl-subroutines
```

尚缺 automatic/递归/常量函数展开、完整并发激活、return/void、函数 output/inout/global write、层次调用及完整 SV 子程序语义。本批没有新的速度测量；既有 SDF 性能比例不能代替本批 RTL 子程序性能。
