# M14：过程循环控制

生产实现新增 inline `for(int/integer ...)` 计数器、多初始化/迭代语句和空头部、语句位置的前后置 `++/--`、`break/continue`。嵌套循环就近处理跳转，`continue` 保留 for 迭代、repeat 计数消耗和 do-while 尾部判断。连接现有 delay、NBA、并行依赖、VCD/DWF 和真实失败预测回放。支持范围见 [loop-control.md](../../docs/loop-control.md)，总体计划见 [plan1017.md](../../plan1017.md)。

独立 RTL parser 新增明确的跳转/更新 AST 身份、词法作用域及参数化实例克隆处理，生成 lexer/parser 已更新；33 个 shift/reduce conflicts 与前批一致。门级 parser 保持独立。编译器把控制流降低为已有过程 PC 跳转，不增加运行时循环解释器，也不改变值/信号/事件布局。

本地验证：

- 五例 **62 次捕获**：serial/time-wheel/双线程、VCD/DWF、ordered/settled，完整有序流和 settled 流跨后端/格式一致，另含两个真实失败预测回放。见 `local-loop-control.log`、`local-results.json`。
- `control` 覆盖五种循环、空 for、case 内 break、continue 后续处理及 delay；`scoped` 覆盖运行时初始化、同名遮蔽、嵌套最近循环及两次重入；`updates` 覆盖 130 位 signed、80 位数组字、packed 部分选择、X/Z、越界和延迟 NBA；`generate` 覆盖参数化克隆后的更新/跳转。
- 双独立域确为两分区、八窗口，两个输出轨迹由 Python 整数规则独立检查；两个数组字的值和时间另有独立预期。见 `parallel-stats.log` 和回归脚本。
- 八类非法/未支持用法明确拒绝：循环外 break/continue、计数器逃逸、net/常量更新、增减表达式返回值、头部 NBA、unsigned inline 计数器。负返回码被视为崩溃，不算诊断通过。
- 10 项既有定向 CTest 通过，共 136.29 秒：integer、signed、generate、memory、always SV、动态 delay、普通编译 RTL、门级源流程、preprocessing、parser 语义单测。见 `local-affected.log`；没有运行完整 CTest 集。
- 四个实际生成程序（control/scoped/updates 串行，parallel 真双线程）通过 macOS ASan/UBSan，全部 settled 信号时间线与普通 ordered 捕获一致。独立 parser 语义单测及五组源码各三次实际解析/清理通过 ASan/UBSan，关闭 leak 检测。具体配置及输入参数见 `sanitizer-config.json`，日志为 `*-runtime-san.log` 和 `*-parser-san.log`；未运行 Linux sanitizer。

实际 VCS W-2024.09 五例 TRACE 和 **1082 条可观察物理位时间线**一致。`verify.py` 双向检查全部参与比较的信号名字/位索引及完整时间线，timescale 必须为 1ps。VCS 不导出六个 inline 循环局部变量及三个 unpacked 数组字，名单在 `vcs-results.json` 中逐项保留；没有忽略整个作用域或其他普通信号。数组值另由 packed 观察量及独立预期检查，循环计数行为由 TRACE/输出轨迹检查，不宣称这些 native 独有导出的 VCS 本体全名对齐。

VCS 差分发现无显式初值的 inline 计数器每次进入时为 0，生产实现据此修正，并用连续两次重入检查；普通静态四态整数仍默认 X。五组最终源、VCS 编译/运行日志及波形在 `vcs/`，真实 VCS 任务退出 0，执行命令保存在 `vcs-command.sh`。

最终源码包包含 **522 文件**，SHA256 为 `5da1d5d2aaa4346494edc7d981fd0fb8bbd97e7abc7a847d8258a166e8486cf4`，工作区与 `source-manifest.json` 逐项一致。Linux 原任务 **122684 退出 0**，manifest 校验、从源码构建及四项 CTest（loop control、普通 RTL、门级源流程、parser）通过，共 **84.24 秒**。五个完整 serial CPP 与 macOS 字节相同，Linux 实际运行的 TRACE/1082 可观察位另行对照同五组 VCS 通过。Linux 日志、生成 CPP 和波形在 `linux/`，命令在 `linux-command.sh`，总结果见 `results.json`。生产编译器已重建，最终再次生成五个完整 serial CPP 与回归程序相同。

复查：

```sh
python3 tests/loop_control/regression.py build/dsim build/rtl-loop-control
python3 validation/m14-loop-control/verify.py
python3 validation/m14-loop-control/verify.py validation/m14-loop-control/linux/source/build/rtl-loop-control
```

仍缺增减表达式返回值、复合赋值、完整整数类型与 automatic/并发激活、用户函数/任务、完整层次/时序/SV 能力。本批没有新的整体 VCS 速度测量。
