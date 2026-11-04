# M17：前置/后置增减表达式

补入 `++a`、`--a`、`a++`、`a--` 的表达式结果，包括赋值右侧、短路条件、三目表达式、函数/任务实参、动态索引及 delay/NBA 采样。动态目标只计算一次地址，按目标自身位宽/符号返回结果；门级紧凑 parser 和运行时布局不变。支持边界见 [increment-expressions.md](../../docs/increment-expressions.md)。

六组正式输入在 [tests/increment_expressions](../../tests/increment_expressions)：

- `values`：8/16/130 位、signed 扩展、前置截断/后置旧值、函数实参及 X/Z。
- `control`：短路、已知/未知三目、条件/while/repeat/for 中的副作用。
- `targets`：80 位数组、动态字内选择和 packed 选择，地址仅更新一次，越界数组 RHS 副作用、部分越界裁剪。
- `delays`：动态 delay、阻塞延迟取样、事件等待、任务 input 复制与普通/延迟 NBA。
- `parallel`：函数/任务形参自增、延迟 NBA、真实两分区七窗口；两条输出轨迹另有独立时间/数值预期。
- `generate`：8/80 位参数化模块、generate 多实例、静态局部状态及子程序返回。

本地新回归通过 **75 次捕获**：六例 × serial/time-wheel/双线程 × ordered/settled × VCD/DWF，加 control/targets/delays 三组实际失败预测回放；同一模式的完整事件流跨后端/格式一致。三个数组字有独立值/时间预期。8 类非法用法均明确拒绝，崩溃不算通过；包括 net/常量/非左值/嵌套增减、动态选择宽度、整数组更新、复合赋值表达式及 always_comb 部分读改写。见 `local-results.json`、`local-increment-expressions.log` 和 `parallel-stats.log`。

实际 VCS W-2024.09 六组 **2166 条可观察物理位时间线**和全部 TRACE 一致，逐项比较信号身份、物理位索引及 1ps 时间轴，包含 VCS 导出的所有静态形参/局部/返回变量。不排除任何普通信号，也不需要名称映射；只有三个 VCS 不导出的 unpacked 数组字由独立预期检查，名称在 `vcs-results.json` 中列出。原始输入、编译/运行日志及波形保存在 `vcs/`，远程原任务为 `/tmp/dsim-m17-vcs`，六例退出码均为 0。

```sh
python3 validation/m17-increment-expressions/verify.py
```

独立 VCS 位宽探针保留在 `probes/`。首次 native 探针发现 `q=++a` 在 8 位 a 溢出后错误返回未截断的 16 位结果（0100）；修复为先截断更新结果，再进入外层上下文。正式 values 回归覆盖该边界。targets 覆盖无效数组写入时 RHS 自增仍执行，compiler 把 RHS 放在受保护存储操作之前。

四个实际生成程序（values/targets/delays 串行、parallel 真双线程）通过 macOS ASan/UBSan，全部 settled 信号时间线与普通 ordered 捕获一致，sanitized CPP SHA 与普通实跑 CPP 一致。独立 parser 单测检查四种运算的参数化克隆、父子关系及符号绑定；另有六组输入各三次解析/清理通过。关闭 leak 检测，配置和日志见 `sanitizer-config.json`、`*-san.log`。没有运行 Linux sanitizer。

```sh
python3 validation/m17-increment-expressions/run-sanitizers.py
```

生成 Bison 仍为既有 33 个 shift/reduce conflicts，见 `parser-generation.log`。未支持的复合赋值表达式、automatic/递归/常量函数及完整整数/层次/事件区/SystemVerilog/时序仍须后续补齐；本批没有新的速度测量。

本地另有十二项既有定向 CTest 全部通过，220.30 秒：procedural_actions/subroutines/loop_control/integer/signed/memory/generate/always_sv/dynamic_delay/semantic_memory/compiled_regression/gate_source_cli，见 `local-affected.log`；没有运行完整 CTest 集。

冻结生产源码/测试 544 文件，源包 SHA256 为 `02a148f7d38714d3537e37939b310fe96999b77248e0045bccee77b5b1e524d9`。逐文件清单见 `source-manifest.json`；最终编译器重新发射六例完整 serial CPP 与实跑版本相同，见 `final-identity.json`。

同源 Linux 原任务 315370（`/tmp/dsim-m17-linux-YPWHyG`）退出 0：544 文件 manifest 校验、干净构建及七项定向 CTest（increment_expressions/procedural_actions/subroutines/loop_control/semantic_memory/compiled_regression/gate_source_cli）通过，256.00 秒。六例完整 CPP 与 macOS 字节相同，Linux 实际 TRACE/2166 条可观察位时间线另行与同六组 VCS 对照通过。日志、完整 CPP 和捕获见 `linux/`，结果见 `linux-vcs-results.json`、`platform-identity.json` 和 `results.json`。

```sh
python3 validation/m17-increment-expressions/verify.py validation/m17-increment-expressions/linux/source/build/rtl-increment-expressions validation/m17-increment-expressions/linux-vcs-results.json
```
