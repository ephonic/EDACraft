# M16：复合赋值与子程序提前返回

本批补入十二种复合赋值及静态用户函数/任务 `return`。动态读改写目标只计算一次地址，函数返回按声明转换，任务提前退出仍复制 output/inout；已有 delay/event/NBA、波形、失败预测回放和独立域并行共同接入。支持边界见 [procedural-actions.md](../../docs/procedural-actions.md)，计划见 [plan1017.md](../../plan1017.md)。RTL parser 新增独立节点身份、语义绑定及参数化克隆，门级紧凑 parser 与运行时布局不变。

编译器在现有 PC 指令上生成提前跳转：函数出口位于结果读取之前，任务出口位于形参返回复制之前，嵌套调用各自保存退出目标。复合赋值的动态数组/packed 目标在入口保存索引，再读、算、写；语句 `++/--` 也使用这一单次求值路径。RTL parser 同时补入 packed 子程序形参/返回变量的选择绑定。生成 Bison 仍为既有 33 个 shift/reduce conflicts，见 `parser-generation.log`。

五组正式用例：

- `operators`：全部十二种运算，16/80/130 位、signed 除余/算术右移、混合位宽、截断、未知位和除零。
- `targets`：动态数组与字内 indexed part-select、拼接目标、边界裁剪；索引函数带静态状态，验证复合赋值与语句增减只调用一次；越界目标仍计算带状态的 RHS。
- `returns`：循环内提前返回、80 位 signed 结果、任务即时/延时/事件后退出、output/inout 复制、嵌套任务及退出后已排定的延迟 NBA。
- `parallel`：参数化实例中的函数循环提前退出和任务延时返回、延迟 NBA；真实两分区七窗口，两个输出轨迹另有独立 Python 值/时间预期。
- `generate`：8/80 位参数、generate 局部子程序、形参位选、复合赋值、条件提前返回及延迟 NBA。

最终本地新增回归 **62 次捕获**通过：serial/time-wheel/双线程 × ordered/settled × VCD/DWF，加 targets/returns 两个实际失败预测回放。完整事件流按同一模式跨后端/格式一致，三个数组字有独立值/时间预期。8 类错误明确拒绝：initial/普通循环中 return、任务返回值、net/常量复合目标、复合赋值表达式返回值、内部 delay 及动态选择宽度。崩溃不算诊断通过。见 `local-procedural-actions.log`、`local-results.json`、`parallel-stats.log` 和 [回归脚本](../../tests/procedural_actions/regression.py)。

最终 12 项既有定向 CTest 通过，166.02 秒：subroutines、loop_control、integer、signed、generate、memory、always_sv、dynamic_delay、compiled_regression、gate_source_cli、preprocessing、semantic_memory。见 `local-affected.log`；没有运行完整 CTest 集。

实际 VCS W-2024.09 五组 TRACE 和 **2451 条可观察物理位时间线**一致，完整检查双方信号身份/位索引和 1ps 时间轴，包含所有 VCS 导出的子程序静态变量。六个 VCS 未导出的 inline 循环计数器和三个 unpacked 数组字逐项列于 `vcs-results.json`；数组另由独立预期检查。generate 内四个函数返回变量使用明确的名字映射（VCS 名字含 generate 前缀），没有跳过整个作用域或普通信号。复核入口：

```sh
python3 validation/m16-procedural-actions/verify.py
```

VCS 原始输入/编译日志/运行日志/波形保留于 `vcs/`，原任务 `/tmp/dsim-m16-actions` 及最终 targets 重跑均退出 0。初版 targets 没有覆盖越界目标的 RHS 副作用，其输入和通过捕获单独留在 `targets-before-invalid-rhs*`；单独探针发现 VCS 即使目标越界也会调用 RHS 函数，据此把 RHS 放到受保护的存储操作之前，再重跑最终 targets。探针记录见 `probes/`。裸函数 return 的 VCS 警告亦保留，不宣称编译无警告。

四个实际生成程序（operators/targets/returns 串行，parallel 真双线程）通过最终 macOS ASan/UBSan，全部 settled 信号时间线与普通 ordered 捕获一致，sanitized CPP SHA 与最终实跑 CPP 一致。独立 parser 单测包含新节点的参数化克隆/父子关系/符号绑定，另有五组源码各三次实际解析/清理，全部通过。配置见 `sanitizer-config.json`，日志见 `*-runtime-san.log` / `*-parser-san.log`，关闭 leak 检测，未运行 Linux sanitizer。可从仓库根目录执行 `python3 validation/m16-procedural-actions/run-sanitizers.py` 复跑五组 parser 和四个生成程序。

最终源码 536 文件，包 SHA256 为 `6e6af8229807decb8d026ddeab8bb1e062fe375bcd5e73b404f9c5da3a101b75`，逐文件清单见 `source-manifest.json`。已与工作区逐项核对，最终本地编译器重新发射五例完整 serial CPP，与实跑版本逐字相同。

最终同源 Linux 原任务 272148（`/tmp/dsim-m16-final-linux-o7Q4UG`）退出 0：536 文件 manifest 校验、干净构建和六项 CTest（procedural_actions/subroutines/loop_control/semantic_memory/compiled_regression/gate_source_cli）全部通过，185.46 秒。日志、五份完整生成 CPP、实际 TRACE/VCD 在 `linux/`；五份 CPP 与 macOS 字节相同，Linux 实际运行结果另行对照同五组 VCS 的 2451 条时间线通过，见 `linux-vcs-results.json`。

```sh
python3 validation/m16-procedural-actions/verify.py validation/m16-procedural-actions/linux/source/build/rtl-procedural-actions
```

尚缺增减/复合赋值表达式返回值、automatic/递归/常量函数、完整子程序/层次/事件区/SV 及完整时序语义；本批没有新的速度测量。
