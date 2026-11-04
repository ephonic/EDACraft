# 2026-10-24 RTL 测试报告处理

v1 输入报告冻结于 [REPORT-original.md](../validation/m78-rtl-report/REPORT-original.md)。原始六设计和三个任务崩溃探针逐字节保存在 tests/rtl_report，origin.json 记录 SHA256。按用户后续要求，DWF 输出格式不作修改。

| 报告项 | 当前处理与范围 |
| --- | --- |
| A1 task 崩溃 | 修复无括号调用 `incr;` 的空语句节点；经典/ANSI、静态/automatic 任务继续使用既有编译路径。原始 incr/delay/edge 三探针加入回归。任务定义自身和 `incr()` 原本可用。非法裸表达式语句明确报错。 |
| B7 常量表达式复制 | 复制次数读取 parser 的 elaboration 常量值，支持 `(W-1)`、`2*W` 等。仍要求正整数，最终宽度不超过 1,048,576；运行时次数拒绝。 |
| B8 always_ff 声明初值 | 接受既有静态声明初始化，不把它计作另一个过程写者。真实 initial/其他 always 写入仍拒绝；always_comb/latch 的原有独占检查保留。VCS W-2024.09 默认也拒绝该初值，必须加 `-ignore initializer_driver_checks`；对照记录明确保留该选项及默认拒绝日志。 |
| B5 层次观测 | 新增向下模块实例路径读取：标量/packed 变量、参数、多层子实例、单维 packed 位/片选、外部组合依赖和事件表达式。读取关联实际 elaborated 实例的信号身份，参与既有依赖、分区及波形。限已在源中声明并展开的实例；暂不支持向上/绝对路径、generate 名、实例数组索引、层次写入/force、层次调用；M83 新增层次 unpacked 元素、packed aggregate 成员和 enum 方法组合，见 [v3 修复](report-v3.md)。 |
| B11 input var logic | 模块 ANSI/非 ANSI 端口接受 `var` 加既有显式变量数据类型及 packed 范围；不接受 var wire/tri。仍不支持省略数据类型的 var 端口和完整变量端口兼容性。Verilog 模式保留 var 作为普通标识符。 |
| B6 struct 形参 | M79 按 v2 原始 t08 探针补上 ANSI 首组 named typedef 形参省略 input 的入口，同时支持同类型续写形参、task 和 enum typedef。M80 增加 package 类型与内置类型首组隐式 input。原始 packed struct 形参可执行；完整匿名/non-packed struct 和所有省略方向组合仍不包含在支持声明内。 |
| B10 assert 动作 NBA | `assert(0) else x <= 1;` 当前可执行，追加延后观测及 VCS 对照；不将其表述为本批新增实现。 |
| C12 空诊断 | 为 6110/6115、6400/6402/6702 增加明确文本；未知普通标识符和调用报告名称。其余历史空诊断尚未全部清理。 |
| C13 级联语法位置 | 继续使用已有首个语法错误行；本批新增用例覆盖根因。未声称所有错误恢复/多文件位置映射均已解决。 |
| B4 随机函数 | M79 接通 random/urandom/urandom_range 基本函数、种子、线程状态、fork 播种和回滚；具体范围与 VCS 差异见 [random-functions.md](random-functions.md)。不是完整随机约束验证支持。 |
| B2 | M80 补齐独立 package 作用域、import、qualified 类型/常量和包内 task/function；原始 t03 同源对照通过。完整边界见 [packages.md](packages.md)，M83 增加 mutable package 全局；export 和 class 等仍缺。 |
| B9 | M81 接通动态 string 与 enum.name/name()，原始 t11 通过；复制、拼接、比较、基本方法和自动局部支持范围见 [strings.md](strings.md)。完整字符串验证能力仍未补齐。 |
| B3 | M82 接通单时钟并发 property、命名/直接 assert/assume/cover、重叠/非重叠蕴含、disable iff 和采样/动作调度；原始 t04 加入同源对照。完整 sequence、采样函数和多时钟等仍缺，范围见 [concurrent-assertions.md](concurrent-assertions.md)。 |
| D14 DWF / VCD | 早期按用户要求不改 DWF；M83 根据新增清单修复 .vcd 文件名默认选择文本 writer，保留显式格式优先和 DWF 编码。 |

验收见 [M78](../validation/m78-rtl-report/README.md)。新增读取沿用现有运行时状态与调度器，不修改运行时头文件，RTL/gate parser 保持分离。本批没有新性能结论，也不等同于完整 SV/VCS 对齐。

v2 复测报告冻结于 [REPORT-v2.md](../validation/m79-random-functions/REPORT-v2.md)。M79 同时修复不存在的 --top 模块诊断，显示 top module not found 和请求的名称；原始 t05/t06/t08 源逐字节纳入 tests/rtl_report/v2。

v3 新增清单逐项状态见 [report-v3.md](report-v3.md)。interface/modport 和完整 SVA 仍有缺口。
