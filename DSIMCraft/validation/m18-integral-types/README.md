# M18：四态整数符号属性、time 与类型化端口

补入显式 `integer signed/unsigned`、64 位 unsigned `time`，以及模块 input/output、函数形参/返回值、任务 input/output/inout 和类型化循环计数器。普通变量/局部静态变量、一维数组、delay/NBA、波形、失败回滚和独立域并行沿用现有执行路径。RTL 与门级 parser 保持独立，运行时状态布局不变。支持边界见 [integral-types.md](../../docs/integral-types.md)。

七组正式用例在 [tests/integral_types](../../tests/integral_types)：

- `values`：integer 默认/显式符号、unsigned 除法/右移/打印、80 位转换、64 位 time 溢出及 X/Z。
- `ports`：ANSI/非 ANSI 类型化端口、启动时 input 复制、signed/unsigned 转换和 X/Z 传播。
- `subroutines`：unsigned 形参/返回值、64 位 time 形参/返回值/局部变量、宽 signed 运行时除法及任务延迟返回复制。
- `memory`：三个 64 位 time 字和两个 unsigned integer 字、动态索引/字内选择、读改写和延迟 NBA；五个数组字有独立值/时间预期。
- `control`：显式 unsigned/signed integer 及 time 循环计数器，跨 delay 保持与动态 delay。
- `parallel`：time 输出、unsigned 形参/循环变量、64 位函数/任务与延迟 NBA；真实两分区七窗口，两个输出有独立时间/值预期。
- `generate`：参数化模块/generate 多实例、time 静态状态和返回值、类型化循环及延迟 NBA。

新回归通过 **87 次捕获**：七例 × serial/time-wheel/双线程 × ordered/settled × VCD/DWF，加 ports/memory/subroutines 三组实际失败预测回放。同一模式下完整事件流跨后端/格式一致，8 类错误均明确拒绝，崩溃不算通过。见 `local-results.json`、`local-integral-types.log` 和 `parallel-stats.log`。

实际 VCS W-2024.09 七组 TRACE 和 **3792 条可观察物理位时间线**一致，完整核对信号身份、物理位索引及 1ps 时间轴，包括所有 VCS 导出的静态子程序变量。只逐项排除 VCS 不导出的七个 inline 循环计数器和五个 unpacked 数组字，名单见 `vcs-results.json`；数组字和双域输出另有独立预期。没有排除普通信号或使用名称映射。输入/编译日志/运行日志/波形保存在 `vcs/`；远程原任务 `/tmp/dsim-m18-vcs` 的最终七例均退出 0。

```sh
python3 validation/m18-integral-types/verify.py
```

初版 VCS 探针的 `time signed` 和 time output 声明初始化被参考版本拒绝，保留在 `initial-vcs-inputs/`。正式共同用例使用默认 unsigned time、显式 packed signed 64 位值及过程初始化，不把扩展语法冒充 VCS 一致。parser 的 time signed/unsigned 修饰语保持拒绝。当前 `int` 仍是历史四态兼容实现，两态整数语义未补齐，本批四态对照使用 `integer`。

此次还修正类型化 input 的启动复制顺序：先让子模块事件监听就绪，再执行首次复制，ports 用例验证 `always @*` 能收到初值变化。子程序运行时形参/返回变量不再用初值缓存做常量折叠，避免宽位运行时除法在 parser 中被错误拒绝。新增节点/元数据支持参数化克隆，单测核对固定宽度、符号、方向和函数结果类型。整数修饰语解析显式选择移入，Bison 为 32 个 shift/reduce conflicts（上批 33），见 `parser-generation.log`。

四个实际生成程序（values/ports/subroutines 串行、parallel 真双线程）和 parser 单测、七组输入各三次解析/清理通过 macOS ASan/UBSan。全部 sanitizer settled 时间线与普通 ordered 捕获一致，sanitized CPP SHA 与普通实跑文件相同；关闭 leak 检测，没有运行 Linux sanitizer。配置和日志见 `sanitizer-config.json`、`*-san.log`，入口：

```sh
python3 validation/m18-integral-types/run-sanitizers.py
```

另有 `probes/typed-parallel.sv` 验证类型化 input 的首次复制在真实双分区下执行正确。`probes/run.log` 记录两分区七窗口；`typed-parallel.dwf` 的两条输出对照独立值/时间预期通过。该补充探针不计入七组 VCS 的数量。

十三项既有定向 CTest 首轮十二项通过，195.39 秒；唯一失败是旧 loop_control 仍要求拒绝新支持的 unsigned 计数器。将其改为仍未支持的 automatic 计数器后，该项单独重跑通过，41.16 秒。其余通过项未重复运行。原始首轮日志与最终单项日志分别为 `local-affected-initial.log` 和 `local-loop-final.log`；不是完整 CTest 集。

最终冻结生产源码/测试 **553 文件**，源包 SHA256 为 `4f1e5628b9b77cfca8d09968a08b6ba41c6471c045f413fb613d3aa99f673b93`，见 `source-manifest.json`。初版冻结后只更正上述一条测试脚本；生产代码和正式输入不变，记录见 `source-refresh.json`。最终本地编译器重新发射七例完整 serial CPP，与实跑版本逐字相同，见 `final-identity.json`。

仍缺两态整数、完整整数参数/cast/端口连接、automatic/递归/常量函数、完整层次/事件区/SystemVerilog 及完整时序；本批没有新的速度测量。

Linux 原任务 455469（`/tmp/dsim-m18-linux-N36d2A`）退出 0：相同生产源码从干净目录构建，八项定向 CTest（integral_types/increment_expressions/procedural_actions/subroutines/loop_control/semantic_memory/compiled_regression/gate_source_cli）通过，302.89 秒。上述唯一测试脚本和 manifest 在 Linux loop_control 开始前更新；最终 553 文件及源包 SHA 再次核对通过，见 `linux/final-source.log`。生产代码和正式模型输入在构建后没有改变。七例完整 CPP 与 macOS 字节相同，Linux 实际 TRACE/3792 条可观察位时间线另行与同七组 VCS 对照通过。日志、完整 CPP 和捕获见 `linux/`，结果见 `linux-vcs-results.json`、`platform-identity.json` 和 `results.json`。

```sh
python3 validation/m18-integral-types/verify.py validation/m18-integral-types/linux/source/build/rtl-integral-types validation/m18-integral-types/linux-vcs-results.json
```
