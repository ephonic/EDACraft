# M19：两态整数和 bit 存储语义

已接入 bit/byte/shortint/int/longint 的默认零值、固定宽度及符号属性、逐位 X/Z 转 0、无效读取、模块端口、静态子程序、一维数组和类型化循环。integer/time 保留四态；RTL 与门级 parser 继续独立。类型信息参与参数化克隆，elaboration JSON 输出 `two_state`。范围与剩余限制见 [类型说明](../../docs/two-state-types.md)。

含两态声明的模型启用 `DSIM_TWO_STATE_ENABLED`。转换在中央存储入口、变化判断和事件唤醒之前执行，覆盖 NBA/delay、子程序复制和 readmem；默认存储为 0。动态数组与 packed 选择的无效读取单独转换，读改写仍只执行一次地址副作用。普通四态/门级模型不启用此标记和分支。两态暂用现有数值容器，本批没有新的整体速度测量。

七组正式用例：values/ports/subroutines/memory/control/generate/parallel。本地四项新增 CTest 通过 74.84 秒；语言回归包含 serial/time-wheel/双线程、ordered/settled、VCD/DWF 共 **87 次捕获**、**3 次失败预测回放**和 **8 类拒绝**。数组七字、两域输出另有独立数值与时刻预期；并行用例实际两分区七窗口。通用/compact 两个内核单测检查逐位转换、跨字、默认值、NBA、恢复后再次写入和不产生虚假变化事件。

实际 VCS W-2024.09 七组 TRACE 与 **2709 条可观察物理位时间线**一致，核对信号身份、物理位及 1ps 时间轴，包含其导出的全部子程序静态变量。仅逐项排除六个不导出的 inline 计数器和七个数组字，完整名单见 `vcs-results.json`。没有排除其他普通信号。generate 的 VCD scope 分段不同，比较器统一按完整层次名称核对，不重命名信号。

```sh
ctest --test-dir build -R '^(rtl_two_state|two_state_kernel|two_state_compact|rtl_semantic_memory)$' --output-on-failure
python3 validation/m19-two-state/verify.py
```

`probes/semantics.sv` 与 VCS 确认未知/越界两态读取返回 0，越界前置增减返回 1、忽略存储。`probes/operators.sv` 的实际 VCS/native TRACE 确认除零、取模零和未知移位仍传播 X；不对算术表达式一律做两态转换。正式数据含 130 位 bit、typed input/output、signed/unsigned、函数/任务复制、延迟 NBA、readmemh、参数化克隆和真双域执行。

12 项既有定向 CTest 全部通过，230.81 秒，包括四态 integer/time、旧循环/子程序/复合赋值/增减、运行时/驱动/检查点、自然并行、编译回归和门级 CLI；没有运行完整 CTest 集。记录见 `local-affected.log`。

五个实际生成程序（values/memory/ports/subroutines 串行和 parallel 双线程）、parser 单测及七组输入各三次解析/清理、通用/compact 两个内核通过 macOS ASan/UBSan，关闭 leak 检测。最终代码身份见 `sanitizer-runtimes.json`；没有运行 Linux sanitizer。新 bit 函数结果暴露了历史 parser 断言，已改为按类型检查 packed/atom range 并保护错误清理空指针；原失败与最终通过日志分别保留为 `parser-san-unit-initial.log` 和 `parser-san-unit.log`。Bison 29 个 shift/reduce conflicts，上批 32，见 `parser-generation.log`。

```sh
python3 validation/m19-two-state/run-sanitizers.py
```

初轮用例使用了 SV 保留字 small/large/local，VCS 拒绝后改成普通变量名，原始失败日志保留在 `vcs/`。初轮并行用例打印两个域，使分区器按共享观察过程合并；改为用独立波形预期检查两域。原始串行退化检查失败见 `local-new-initial.log` 和 `sanitizers-initial.log`，最终新功能/并行 sanitizer 均通过。首次构建命令在 CMake 自动更新后未找到新 kernel target，随后补建再完整运行，原日志没有删除。

冻结源码/测试 **564 文件**，源包 SHA256 `5c10120e969419bcc17d322561599eaef554419e646c5bd5c599bc5c1b7ac97b`。`source-manifest.json` 已逐项核对工作区，七份完整 serial CPP 与最终本地编译器重新发射结果逐字相同，见 `final-identity.json`。Linux 原任务 `/tmp/dsim-m19-linux-d2n1O0` 退出 0，相同 manifest 的干净构建及九项定向 CTest 全部通过，220.97 秒。七份完整生成 CPP 与 macOS 逐字相同，Linux 实际 TRACE/2709 条位时间线另行与同七组 VCS 对照通过。日志/捕获见 `linux/`，结果见 `linux-vcs-results.json`、`platform-identity.json` 和 `results.json`。

```sh
python3 validation/m19-two-state/verify.py validation/m19-two-state/linux/source/build/rtl-two-state validation/m19-two-state/linux-vcs-results.json
```

`int` 与 `integer` 已分开词法身份。`parameter int`/`localparam int` 的历史兼容入口尚未迁移到新的两态参数语义，当前会拒绝；本批只覆盖变量、端口、子程序和循环类型，不能将它当作完整类型系统支持。
