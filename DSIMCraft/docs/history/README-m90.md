> 历史快照：整理前的 README（截至 M90，2026-10-25）。保留当时的功能叙述和使用示例；当前入口见 [项目首页](../../README.md) 和 [文档导航](../README.md)。历史原始运行产物的取回方法见 [验证归档说明](../../validation/README.md)。

# dsim

M90 将 RTL、门级 Verilog、Liberty、SPEF 整理为仓库内独立组件，见 [parser 目录](../../parsers/README.md)；同时补齐 [升序 packed 范围](../ascending-packed.md)。

M87 新增 [固定周期断言序列](../sequence-delays.md)：`##N`、同拍 `##0`、多阶段后件、重叠尝试及异步取消，接通分区、采样和预测回滚。范围延迟、重复、多时钟和完整验证平台仍缺。

M86 修复 [complex RTL 报告缺陷](../complex-report-fixes.md)：automatic 函数直接递归、受限纯整数常量函数、过程块采样函数、整信号 force/release、固定整数成员 unpacked struct、写内存文件及参数/genvar 位选；同时改进重声明和执行预算诊断。支持范围与 VCS 边界差异在文档中单独列明。

本轮 M85 接入单时钟并发断言采样值函数 `$past/$rose/$fell/$stable/$changed/$sampled`，包括定深度/门控历史、嵌套表达式及动作块 `$sampled`；范围与限制见 [并发断言说明](../concurrent-assertions.md)。

M84 新增 [interface/modport](../interfaces.md)：参数化实例、类型与视图绑定、跨模块共享存储、端口转发及读写方向检查；支持范围和验证结果见文档。

M83 修复 [v3 报告组合缺陷](../report-v3.md)：层次固定数组元素/动态索引读取、层次 enum 方法和 packed struct 成员、包内共享可变状态，以及 `.vcd` 文件名自动选择标准文本波形。interface/modport 由 M84 继续接通，完整 SVA 仍未齐全。

M82 新增 [单时钟并发 property/SVA](../concurrent-assertions.md)：原报告 B3、命名/直接 assert/assume/cover、`|->`/`|=>` 与 `disable iff`，接通采样、Observed/Reactive/Re-NBA、分区和预测回滚。11 同源模型与 VCS 的输出及 964 个公开物理位时间线一致；完整 sequence、多时钟仍缺；采样函数由 M85 接通，验收见 [M82](../../validation/m82-concurrent-assertions/README.md)。

M81 新增 [动态字符串与 enum.name](../strings.md)：原始报告 B9、字符串复制/拼接/比较和基本方法，接通延迟快照、automatic 激活、分区及预测回滚。支持边界与 VCS 隐式敏感性差异明确列出。

M75 新增 [SystemVerilog 流式拼接](../streaming-concatenation.md)：位序/字节序转换、宽四态与固定数组打包、静态目标拆包，接通初始化、延迟/NBA、自动调用与常量求值。

M74 新增 [SystemVerilog 赋值模式](../assignment-patterns.md)：固定数组、packed 多维数据与 struct 的按位置、default、索引/成员键和嵌套重复，接通声明初始化、过程赋值与延迟 NBA。

M73 补入 [RTL 模块和原语实例数组](../instance-arrays.md)：宽端口切分/广播、独立时序状态、三态 net 连接、参数化 generate 与波形索引层次。

M72 补齐 [多维 packed 端口、genvar 自增/自减、顶层自动选择与 Verilog 关键字模式](../frontend-compatibility.md)，真实 VCS 对照和验收见 [M72](../../validation/m72-frontend-compat/README.md)。

M71 新增 [固定数组声明复制初始化](../fixed-initializers.md)，并将用户报告目录中的六组问题用例纳入回归和稳定发布检查。

M66 新增 [动态数组元素非阻塞赋值](../dynamic-nba.md)：即时/延迟/事件 NBA、分配和调用身份、自动存储复用、取消与回滚。

M65 新增 [动态数组形参与引用](../dynamic-arguments.md)：动态实参到 automatic task/function 的 input/output/inout/ref/const ref、变长复制、挂起别名、取消与回滚。

M64 新增 [动态数组运行期存储](../dynamic-arrays.md)：new[]、扩缩容、size/delete、元素更新、查询与 foreach。

M63 新增 [无尺寸数组值形参](../open-arrays.md)：固定数组到 input/inout `[]`、多维与混合维度、查询、嵌套调用和挂起复制。

M62 新增 [const ref 只读引用](../const-ref.md)：标量和固定数组实时别名、嵌套转传与写保护，接通挂起、取消和回滚。

M61 新增 [固定 unpacked 数组形参](../array-arguments.md)：task/function 的 input/output/inout/ref、动态子数组、入口/返回复制与引用别名，接通事件、取消、分区和回滚。

M60 新增 [ref 引用形参](../ref-arguments.md)：automatic task/function 即时别名写入、嵌套转传、固定数组元素地址捕获，接通挂起事件、取消、分区和回滚。

M59 新增 [wait_order 有序事件等待](../wait-order.md)：成功/失败分支、重复事件、NBA 顺序、automatic task、fork 取消/复用及预测回滚。

M58 支持 [显式 static 局部声明](../explicit-static.md)：automatic 子程序跨调用共享持久变量、数组和静态 event，接通一次初始化、NBA、波形、分区和回滚。

M57 新增 [显式 automatic 局部声明](../explicit-automatic.md)：支持 fork 逐轮捕获、混合静态/自动存储、静态任务重叠调用及挂起/退出后的生命周期。验收见 [M57](../../validation/m57-explicit-automatic/README.md)。

M56 新增 [foreach 动态循环帧](../foreach-fork.md)：补齐重叠循环、分支共享索引和父任务返回后的保活，覆盖控制流、等待及回滚。验收见 [M56](../../validation/m56-foreach-fork/README.md)。

M55 新增 [automatic fork 变量帧](../automatic-fork.md)：支持重叠调用隔离、同级共享父变量及父任务返回后的存活分支，包含局部事件订阅、取消和回滚；功能核验见 [M55](../../validation/m55-automatic-fork/README.md)。

新增[重叠 fork 激活](../dynamic-fork.md)：支持静态存储分支的循环批量启动、嵌套后代及事件等待，动态变量帧边界见 [M54](../../validation/m54-dynamic-fork/README.md)。

新增[join_any/join_none 与 fork 收尾控制](../fork-control.md)：支持提前继续、直接子进程等待、后代取消和取消后复用；静态调用槽边界及 VCS 对照见 [M53](../../validation/m53-fork-control/README.md)。

新增[命名块 disable 与并发取消](../named-disable.md)：支持后代取消、automatic task 多次活跃调用、重复启动及关闭标签；VCS 对照和明确边界见 [M52](../../validation/m52-named-disable/README.md)。

新增[并发过程 fork/join](../fork-join.md)：各分支独立挂起，全部完成后恢复父进程，支持嵌套、循环复用、automatic task、分区和回滚；真实 VCS 对照及 join_any/join_none 等边界见 [M51](../../validation/m51-fork-join/README.md)。

新增[非阻塞内部事件赋值](../event-nba.md)：每笔更新独立取样 RHS/目标/次数，支持 repeat、表达式/iff/命名事件、任务返回后交付、并行与回滚；证据及动态拼接函数索引差异见 [M50](../../validation/m50-event-nba/README.md)。

新增[阻塞赋值内部事件控制](../intra-event-assignments.md)：入口保存右值、恢复后计算动态目标，支持 repeat/iff/命名事件、automatic task、并行与回滚；VCS 同源对照和非阻塞形式边界见 [M49](../../validation/m49-intra-event-assignments/README.md)。

新增[条件命名事件](../qualified-named-events.md)：`@(event iff condition)`、混合列表、automatic 条件函数及 NBA/延迟触发，接入并行与回滚；真实 VCS 对照和边界见 [M48](../../validation/m48-qualified-named-events/README.md)。

新增[自动函数事件表达式](../function-events.md)：无外部副作用 automatic 函数可用于事件源和 iff 条件，支持嵌套/局部数组、敏感依赖、分区与回滚；真实 VCS 对照和保留差距见 [M47](../../validation/m47-function-events/README.md)。

新增[条件事件控制](../conditional-events.md)：iff 四态条件、表达式边沿、混合列表、automatic task、分区依赖与回滚；真实 VCS 同源对照和边界见 [M46](../../validation/m46-conditional-events/README.md)。

新增[表达式事件控制](../event-expressions.md)：算术/逻辑/拼接、动态位与数组字选择、四态边沿及混合事件，接入 automatic task、并行与回滚；实际 VCS 对照及函数调用边界见 [M45](../../validation/m45-event-expressions/README.md)。

新增[静态命名事件](../named-events.md)：event 声明、发生等待、阻塞/NBA/延迟触发和 triggered 查询，接入串行、时间轮、并行及回滚；实际 VCS 对照与边界见 [M44](../../validation/m44-named-events/README.md)。

新增[电平条件等待](../level-wait.md)：wait 条件重查、函数实参敏感性、automatic 任务及回滚；同时补齐 function logic/reg 返回类型。实际 VCS 对照见 [M43](../../validation/m43-level-wait/README.md)。

新增[动态索引子数组复制](../array-copy.md)：动态读写、延迟NBA地址取样、完整位宽/四态边界检查，含真实VCS对照与副作用差异，见 [M42](../../validation/m42-dynamic-array-copy/README.md)。
新增[静态数组整体过程赋值](../array-copy.md)：多维/常量子数组、阻塞/NBA复制、宽字和类型检查，含实际 VCS 对照及阻塞赋值内 delay 差异，见 [M41](../../validation/m41-array-copy/README.md)。


新增[静态 net 数组](../net-arrays.md)：wire/tri、多维子数组端口、input 反向驱动与 inout 电气合并、多驱动及悬空 Z；VCS 对齐证据见 [M40](../../validation/m40-net-arrays/README.md)。
新增[静态变量数组端口](../array-ports.md)：input/output、多维与静态子数组、声明顺序映射及目标转换；实际 VCS 差分见 [M39](../../validation/m39-array-ports/README.md)。

新增[显式变量连续赋值](../variable-assign.md)：静态选择、宽/两态/枚举、混合拼接和惯性 delay，接入时间轮、并行与回滚；实际 VCS 对照及保留差异见 [M38](../../validation/m38-variable-assign/README.md)。

新增[模块输出连接变量](../variable-ports.md)：父级 logic/bit/整数、静态位段/数组字/成员、混合拼接、写入冲突检查及延迟传播；实际 VCS 对照见 [M37](../../validation/m37-variable-ports/README.md)。

新增[枚举数值遍历方法](../enum-methods.md)：first/last/next/prev/num、常量查询、宽四态成员和回绕；实际 VCS 对照及类型推断差异见 [M36](../../validation/m36-enum-methods/README.md)。

新增[动态数组混合拼接目标](../dynamic-concat.md)：元素、位段、普通变量和固定数组混合阻塞/NBA更新，目标重叠顺序、非法阻塞项跳过、延迟/事件控制及整组回滚；索引函数和特定扩容序列的VCS差异单列，详见 [M68](../../validation/m68-dynamic-concat/README.md)。
新增[动态数组声明初始化](../dynamic-initializers.md)：new[]、带源分配和深复制，静态启动与自动局部初始化顺序、宽/四态/两态存储、取消与回滚、初始化分区依赖；[稳定版发布](../stable-release.md)持续更新到 `~/vibe-coding/dsim-test/bin/dsim`。

新增[动态数组元素位选与部分选择](../dynamic-selects.md)：阻塞读写、复合更新、等待后目标取样，以及即时/延迟/事件 NBA 位段合并。VCS W-2024.09 的动态部分 NBA NYI 和负下界写入差异单列，详见 [M67](../../validation/m67-dynamic-selects/README.md)。

新增[限定选择语句及检查](../selection-checks.md)：unique/unique0/priority if/case、逐过程报告清理、毛刺抑制和回滚；实际 VCS 波形及保留的告警差异见 [M35](../../validation/m35-selection-checks/README.md)。

新增[静态多维数组](../multidim-arrays.md)：多维下标、foreach、packed 元素/成员、delay/NBA 和 automatic 局部存储，接通并行和回滚；同源实际 VCS 比较见 [M34](../../validation/m34-multidim-arrays/README.md)。

新增 [foreach 静态数组遍历](../foreach.md)：声明方向、多索引/跳过维度、只读自动索引、函数/任务、延时及回滚，保持 RTL 与门级 parser 分开；实际 VCS 验收见 [M33](../../validation/m33-foreach/README.md)。

新增 [SystemVerilog 集合匹配](../set-membership.md)：inside、case inside、==?/!=?，接通四态/范围/数组、参数与 generate、立即断言、延时取样、敏感依赖及回放。实际VCS同源验收见 [M32](../../validation/m32-set-membership/README.md)；未导出的数组字单独核验，不计入VCS位数。

新增[静态子程序默认与命名实参](../call-arguments.md)，支持空位默认、词法绑定、函数/任务复制及启动事件对齐；同源 VCS 验收见 [M30](../../validation/m30-call-arguments/README.md)。

编译式 Verilog 仿真器的工程版本（0.13.0）。复用提供的 EDACraft RTL parser，将 AST 降为独立的表达式和进程控制 IR，再生成 C++17 并编译成本机 `simv`。运行期执行生成的进程状态机，不调用 VCS/Icarus，不遍历 parser AST。二元运算符以模板参数固定在编译期，避免生成模型中的字符串运算符分派。固定等待位置在仿真前登记，运行期以值类型事件队列、NBA 记录和稳定时间堆调度。

RTL 与门级网表使用独立 parser，门级大网表不经过行为 RTL AST。设计边界见 [docs/frontend-design.md](../frontend-design.md)；专用门级 Network 已接入 Liberty 组合及 ff/latch 零延迟仿真，按单元类型复用生成的 C++ 函数，每个时序实例保存独立状态。RTL 测试平台只加载 DUT 端口桩，不解析整份网表。

总体路线、里程碑和验收标准见 [plan1017.md](../../plan1017.md)。当前覆盖 M0、M1 与 M2 的层次、左值片段与过程控制功能，预处理与文件输入，以及 M3 的组合门级、结构宽连接和 Liberty ff/latch；完整 VCS 功能/性能对标仍需后续阶段。

当前功能边界与分场景性能对照见 [dsim/VCS 比较](../../validation/current-vcs-comparison/README.md)。下列性能记录保留各批次配置与结果，历史未实现项以最新功能表及比较报告为准。

此前补入[函数输出形参与副作用](../function-effects.md)：output/inout 复制、外部变量写入、void/语句/丢弃调用，接通 delay/NBA、波形、回滚和并行；验收见 [M29](../../validation/m29-function-effects/README.md)。

此前补入[命名类型值参数与子程序签名](../type-signatures.md)：typedef/enum/packed 聚合的 parameter/localparam、函数返回及函数/task 形参，保持范围、符号和 enum 检查；验收见 [M28](../../validation/m28-type-signatures/README.md)。

此前补入[静态数组查询和多控制位计数](../array-queries.md)：`$dimensions/$unpacked_dimensions/$left/$right/$low/$high/$increment/$size/$countbits`，接通参数展开、动态维度及四态计数；验收见 [M27](../../validation/m27-array-queries/README.md)。此前补入[整数/位向量系统函数](../system-functions.md)：`$bits/$clog2/$isunknown/$countones/$onehot/$onehot0`，接通常量展开、宽向量与运行时检查；验收见 [M26](../../validation/m26-system-functions/README.md)。此前补入 [packed struct/union](../packed-aggregates.md)：真实成员布局、别名嵌套、两态/符号/enum 成员、数组字及动态成员读写，接通 delay/NBA、波形/回放和并行；验收见 [M25](../../validation/m25-packed-aggregates/README.md)。此前补入 [整数 enum](../enums.md)：显式/自动编号、名义类型身份、别名与作用域、强类型赋值和 cast、增减/数组/delay/NBA；验收见 [M24](../../validation/m24-enums/README.md)。此前补入 [命名整数类型](../named-types.md)：typedef、别名链、作用域遮蔽、参数化/generate 绑定及命名 cast；同时补齐静态函数/任务的多语句体并修复四态常量 case equality。验收与已知 VCS 常量转换差异见 [M23](../../validation/m23-named-types/README.md)。

此前补入 [SystemVerilog 整数与尺寸 cast](../explicit-casts.md)：内建整数类型、signed/unsigned 和常量尺寸转换，接通参数常量上下文、截断/扩展及四态/两态转换，保留运行时副作用。验收见 [M22](../../validation/m22-explicit-casts/README.md)。

此前补入 [SystemVerilog 立即断言与诊断](../systemverilog-verification.md)：assert/assume/cover 的条件、标签及动作，四态与单次求值，$fatal/$error/$warning/$info，参数化克隆及现有 delay/NBA、回滚/并行；并发 SVA 和完整覆盖率继续分阶段实现。验收见 [M21](../../validation/m21-immediate-assertions/README.md)。

此前补入 [类型化值参数与常量上下文](../typed-parameters.md)：修复 parameter int/localparam int 入口，整数/bit/logic/reg 参数按目标宽度、符号与两态属性处理默认值和实例覆盖；接通常量宽除余、零除及移位边界。验收范围见 [M20](../../validation/m20-typed-parameters/README.md)。

此前补入 [两态整数与 bit](../two-state-types.md)：bit/byte/shortint/int/longint 的默认零值、X/Z 转 0、端口/子程序/数组及延迟 NBA，七例 87 捕获、3 次失败回放及实际 VCS 2709 条可观察位时间线通过，见 [M19](../../validation/m19-two-state/README.md)。

此前补入 [四态整数类型及端口](../integral-types.md)：显式 integer signed/unsigned、64 位 time、模块 input/output、子程序形参/返回值和类型化循环。七例 87 捕获、3 次失败回放及实际 VCS 3792 条可观察位时间线通过，见 [M18](../../validation/m18-integral-types/README.md)。

此前补入 [前置/后置增减表达式](../increment-expressions.md)：结果按目标位宽/符号返回，支持短路条件、实参、动态索引及 delay/NBA 取样。六例 75 捕获、3 次失败回放及实际 VCS 2166 条可观察位时间线通过；范围见 [M17](../../validation/m17-increment-expressions/README.md)。

此前补入 [复合赋值与子程序 return](../procedural-actions.md)：十二种复合运算、动态目标单次求值、循环/嵌套调用中的提前返回及任务出口复制，接通 delay/event/NBA、波形、回滚和独立域并行。验证范围见 [M16](../../validation/m16-procedural-actions/README.md)。

此前补入 [静态用户函数与任务](../subroutines.md)：signed/整数/宽四态形参与返回值、静态局部变量、嵌套调用、任务 output/inout 及 delay/event/NBA，接通回滚与独立域并行。五例 62 捕获、2 次失败预测回放、10 类拒绝和实际 VCS 2187 条可观察位时间线通过；边界及证据见 [M15](../../validation/m15-subroutines/README.md)。

此前补入 [RTL 过程循环控制](../loop-control.md)：inline for 计数器、多赋值/空头部、语句 `++/--` 和 `break/continue`，接通 delay、NBA、波形及回滚。五例实际 VCS 的 TRACE/1082 条可观察位时间线一致，验证范围见 [M14](../../validation/m14-loop-control/README.md)。

当前新增 [RTL 动态位/固定宽度部分选择](../indexed-selects.md)，支持过程赋值、延迟 NBA、模块输入表达式、宽四态数据和越界裁剪，并接入检查点、回滚与独立域并行。普通 `[msb:lsb]` 仍要求常量；超宽索引高位非零的已知 VCS 差异单独记录。 本批本地定向/回放及Linux三类实际流程通过，558条VCS物理位时间线匹配；四个macOS ASan/UBSan程序通过。速度候选两轮组合首轮改善6.09%、第二轮回退2.10%，默认保留二叉堆，不宣称稳定提速。最终二叉查表配置本轮完整SDF约为VCS CPU的7.67倍（短筛选、共享主机），详见[功能与测量记录](../../validation/m9-timers-selects/README.md)。

当前新增 [SystemVerilog always_comb/latch/ff](../always-procedures.md)：时刻 0 启动、隐式敏感列表、单写者检查和既有 NBA/回滚/独立域并行接入。无波形 SDF 默认采用标量时序存储及处理器，可用 `--no-gate-scalar-timing` 回退。本轮原始全量用例单轮 CPU 旧默认 74.37s、新默认后端 57.69s、VCS 8.89s，减少 22.43%，仍约为 VCS 的 6.49 倍；每次128笔匹配，完整条件与验收见 [本批记录](../../validation/m8-speed-sv/README.md)。不能将单次筛选推广为跨负载稳定收益。

0.13.0 继续性能主线：每 DUT 共享门级回调、紧凑进程记录与 alias 缓存，沿用 0.12.0 的单驱动内联及状态输出消除。10 万触发器非规则反馈基准同轮 CPU 中位数从 0.12.0 的 9.14 降至 6.51 秒，减少约 28.8%；同轮 VCS 为 5.31 秒，该合成负载约 1.23 倍。仅共享回调版本为 6.16 秒，单项收益不完全叠加；实验条件、复测及范围见 [本批记录](../../validation/m5-compiled-process/README.md)。SDF 已有真实大网表严格绑定，新增 11 组实际延迟 VCS 参考，实际时序回标仍待实现。

当前开发版新增 RTL 运行时整数表达式延迟（普通过程、阻塞内部和 NBA），本地8项/Linux4项定向回归及新VCS两例145物理位对照通过。无波形 SDF 默认折叠全零 IC/PORT 通道，可用 `--no-gate-fold-zero-inputs` 关闭。原始30万单元完整SDF单轮CPU旧默认112.06s、新默认81.54s（−27.2%）、VCS10.13s（新默认约8.05倍），三者各128笔输出匹配；单轮无预热，不能替代多轮结论。见[本批实现与结果](../../validation/m7-feature-speed/README.md)。

新增真实 barr_modmult 验证：原始 300,909 单元、111 种模型，内部 256/257 位连接通过结构端口分段接入，128 组 RTL 黄金向量在 native/VCS 全部一致。同输入串行三次 CPU 中位数为 **13.78/6.14 秒，约 2.24 倍差距**。本轮直接模型回调候选没有稳定收益，已撤回，当前仍为 0.13.0；完整条件、原始数据与下一热点见 [真实设计记录](../../validation/m5-model-handlers/README.md)。

新增固定 Liberty 反相专用化：保留 1 位归一化和 X/Z，省去运行时字符串分派。完整真实设计固定 CPU 五次交替复测，原版/优化 CPU 中位数 **17.29/14.82 秒，降低约 14.3%**；另一轮原版/优化/VCS 为 17.31/13.71/7.12 秒，优化后约为 VCS 的 **1.93 倍 CPU**，两轮不混算。全部 128 组 golden、本地/Linux 23/23 回归、有序波形和 sanitizer 通过，已纳入当前代码；条件及证据见 [固定反相优化](../../validation/m5-unary-specialization/README.md)。完整 SDF 时序和自动并行分区仍待补齐。

新增固定门级敏感列表：只绑定一个终生固定列表的编译进程，重新等待时只恢复 waiting，保留原唤醒判断与事件顺序。以上一批固定反相为基线，同核三次交替测量，真实设计 CPU **18.90→14.57s（减少 22.9%）**、运行峰值 RSS **108,320→87,404 KiB（减少 19.3%）**；同轮 VCS **9.10s**，约为其 **1.60 倍 CPU**。10 万 ff 反馈减少约 12.8%，三类长周期普通 RTL 基本持平；本地/Linux 24 项、完整有序流、实际生成回滚、ASan/UBSan/TSan 通过。不同轮次不混算；[结果与边界](../../validation/m5-fixed-wait/README.md)、[等价条件](../fixed-sensitivity.md)。

新增可选的[延时驱动内核](../delayed-drivers.md)：独立驱动事件、显式替换/保留策略、取消与槽复用，支持检查点/预测事务及保守并行 worker。普通模型关闭开关；SDF 文件到驱动通道已接入有限的无条件 IOPATH，见 [支持边界](../sdf-runtime.md)。该批不替换上面的零延迟性能测量。

重复单驱动写入候选已完成评估并撤回：首轮真实 CPU 14.32→13.67s，五次配对复测却为 13.25→14.41s，五对均慢。运行时恢复原版，只保留独立四态/多驱动/回滚行为测试。首轮恢复版本/VCS 为 **14.32/10.29s，约 1.39 倍 CPU**，属于原版重新测量，不能把与上轮 1.60 倍的差异当作优化收益。详见[原始结果与撤回决定](../../validation/m5-redundant-drive/README.md)。

门级标量表达式两版候选已评估并撤回：第二版首轮真实 CPU 17.84→11.77s，但五次配对复测为 **13.20→14.48s**，100k ff 为 **5.37→6.90s**，没有可复现收益。生产文件已逐字恢复，不能把首轮结果当作已达到 VCS 性能。两平台候选 28/28、完整有序流和 sanitizer 通过；[完整证据](../../validation/m5-scalar-logic/README.md)。下一项转向[内部信号与驱动的紧凑存储](../compact-gate-storage-plan.md)，第一版两平台正确性通过，但真实五次配对 CPU 仅改善 0.76%，已恢复原后端；内存约降 17% 不等于解决速度差距。后继合并写入版本已验收采用，见下文。实际 SDF 回标、自动分区及波形扩展继续按原计划补齐。

本轮已采用**内部单比特网紧凑存储与合并驱动写入后端**。真实 300,909 单元/128 完整 golden 的独立五次配对 CPU **13.59→11.33s（减少 16.63%，五对均改善）**，RSS **88,976→73,696 KiB（减少 17.17%）**；100k ff 反馈 CPU **6.60→5.09s（减少 22.88%，五对均改善）**。同轮四方主实验真实原版/紧凑 A/合并 B/VCS 为 14.01/13.28/11.90/9.15s，B 约为该轮 VCS CPU 的 1.30 倍。独立配对未运行 VCS，不混用分母；这些是无波形、无 SDF、单核运行结果，不代表总体 VCS 对齐。

本地与 Linux 后端各 28 项、最终默认构建与 SDF 更新的组合 28 项通过；9 个实际 ASan/UBSan +1 个 TSan、24 个完整生成模型边界、18 条完整有序流、15 门级+3 延时组 native/VCS 参考各三次通过。默认编译器已重建，生成门级主体与实测冻结候选逐字一致。SDF 原始数值绑定另经两平台各 4 项和实际 ASan/UBSan 验证，实际路径回标尚未实现。完整[本批证据](../../validation/m5-compact-drive/README.md)。

新增[小型组合输出四态查找表](../gate-four-state-lut.md)。真实设计独立七对 CPU 配对收益中位数 **3.86%，六对改善**；反馈独立复测慢 1.23%，并非所有负载均提速。实际编译器的新同轮原版/优化/VCS CPU 中位数 **10.11/9.64/7.76s**，约为 VCS 的 **1.24 倍**；无 SDF/波形、单核。两平台各 30 项回归、179,648 组四态/别名有序对照及实际 sanitizer 通过，已纳入默认编译器。

新增[SDF 路径数值层](../sdf-path-delays.md)，按 VCS 新微例纠正逐项模型精度舍入与路径夹零顺序。文件到编译缓冲器延时驱动的 54 组受支持微例逐项匹配，另 4 组尚未明确的部分覆盖/零延迟增量组合明确拒绝。该探针验证数值接入；生产 CLI 的一般路径、条件/脉冲、INTERCONNECT 与 timing checks 回标继续开发。

新增 [Verilog specify 模型提取与路径表匹配](../timing-models.md)：从实际 111 种标准单元模型读取时间精度、322 条路径及 12 条时序检查声明。`--sdf-bind-check` 配合 `--gate-models` 可建立模型匹配的 IOPATH 数值表，完整 flattened SDF 的 867,982 条路径已走通；模型初始 corner 与 SDF corner 分开选择。报告明确列出互连和 timing checks 的待处理数量，尚未生成一般 SDF 仿真程序。


新增有限的[编译式 SDF IOPATH](../sdf-runtime.md)：`--sdf-annotate` 实际生成带延时的门级程序，支持无条件路径、完整四态转换、增量和独立 corner，并恢复路径状态及待交付事件。11 组新 VCS 每组三次输出/波形匹配，54 组既有参考通过实际 CLI；Linux 37/37，本地分组 32+5 项和九个实际 ASan/UBSan 程序通过。条件、INTERCONNECT 与 timing checks 等仍不支持，见 [验收证据](../../validation/m4-sdf-runtime/README.md)。

性能继续优先。紧凑网直接编码读取试验在真实设计上五对配对收益中位数 0%，未采用；不发布新的提速比例。下一步按当前后端的新 profile 评估通知/队列成本和可证明的等价变换，见 [执行顺序](../performance-next.md) 与 [试验原始数据](../../validation/m5-scalar-read/README.md)。


新增[多字四态值后端](../multiword-values.md)：RTL运算、常量、端口、部分更新、门级宽接口及DWF、检查点、并行消息共同支持宽值，保持RTL与门级parser分离。窄模型仍使用原24字节值结构；验证和真实设计结果见[本批记录](../../validation/m4-wide-values/README.md)。本批是功能扩展，无新的VCS性能比例。

新增[编译式时序检查](../timing-checks.md)：SDF入口默认执行SETUP/HOLD/SETUPHOLD、RECOVERY/REMOVAL/RECREM、WIDTH/PERIOD/SKEW，逐解析变化检查、模型精度转换、诊断和窗口历史接入检查点。支持范围、负值模式、notifier及真实模型限制见[验收记录](../../validation/m4-timing-checks/README.md)。

新增[图自动分区 API 与编译器分析](../parallel-and-rollback.md)：零延迟域合并、按负载分配与正延迟通道实际执行；`--gate-partition-report N` 和统一清单的 `partition_report` 输出 gate-only 分析，单独使用时生成程序仍串行。后继实验选项 [--threads](../automatic-parallel.md) 已接入普通 RTL 独立域自动代码生成、全局结束与压缩波形，两平台51程序/三类新VCS对照及原始全量关闭选项身份通过；gate scope内部切分及实际收益待完成。真实300,909单元零延迟设计仍需静态组合锥和批量调度，不宣称多线程加速。

新增显式[组合单元批量执行](../gate-batches.md) `--gate-batch`：保持逐事件FIFO和完整有序波形，支持现有SDF/回滚入口。真实设计五对配对CPU收益中位数2.26%，反馈3.41%；未达真实设计默认采用门槛，默认关闭，见[本批测量与范围](../../validation/m5-fifo-batch/README.md)。

普通RTL自动并行继续消减开销：实际仅一个分区时直接生成原串行代码，多分区无`$finish`时省去全局结束快照。本地54程序/306捕获、21份串行回退完整代码身份和新增两例sanitizer通过；Linux定向验证进行中，尚无新的速度比。见[验证与限制](../../validation/m6-parallel-fallback/README.md)。

## 构建与运行

新增[SDF 模型准备工具](../sdf-model-preparation.md)，可从原始 SDF 和功能模型生成严格身份匹配的测试模型；真实300,909单元全量SDF已实际运行，128输出匹配本轮新编译VCS，默认非负检查模式仍有明确限制。RTL新增[阻塞赋值内部延时](../time-semantics.md)及待采样值回滚，统一清单接入 `sdf-prepared`、`rtl-delays`。证据见[本批记录](../../validation/m4-sdf-model-preparation/README.md)。

需要 CMake ≥3.19、C++17 编译器、zlib、Threads、Tcl 开发头文件/库，测试需要 Python 3。普通构建不需要 Flex/Bison。已在 macOS AppleClang 21 和 Linux GCC 11.5 上验证。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 6
ctest --test-dir build --output-on-failure
./build/dsim --top top tests/cases/counter.v -o build/counter_simv
./build/counter_simv
```

输出示例：

```text
TRACE q=1 plus=2
TRACE q=3 plus=4
TRACE q=5 plus=6
TRACE q=7 plus=8
```

默认保留 `<输出文件>.dsim.cpp`，它包含完整运行时，可单独用 `c++ -std=c++17 -O2` 编译。生成的可执行文件无需 parser、Tcl 或 dsim 本体。编译驱动通过 `posix_spawnp` 调用编译器，路径不经过 shell；可用 `--cxx /path/to/c++`、`--emit-cpp model.cpp` 和 `--emit-only` 控制输出。`--emit-ir elaboration.json` 可导出层次、参数位串、信号 ID、端口片段和按位 net 连接信息。`dsim` 驱动本身目前需在源码树中使用。

`simv --max-events N` 设置调度/生成指令预算（默认 10000000），用于终止零延迟循环；预算不是仿真时间。时间按实际实例的最小精度计 tick，支持模块 timescale、常量小数延迟及物理单位的 VCD/DWF，详见 [时间语义](../time-semantics.md)。遇到同一 Active region 的测试平台竞争时，不保证与其他仿真器选择相同执行顺序。

## 当前支持边界

| 能力 | 当前状态 |
| --- | --- |
| 顶层 | 显式 `--top`，多输入文件合并；多层模块实例展开，空模块及同模块多个实例 |
| 参数与端口 | 位置/命名参数覆盖及依赖参数；ANSI/非 ANSI 端口，命名/位置/未连接端口及省略输入的默认值；输入表达式与 signed/unsigned 宽度适配；输出接父层 net 的完整/常量选择/拼接左值；同宽直接 net 与选择连接可共享驱动解析，inout 支持选择/拼接 |
| 值 | 1–1,048,576 位 unsigned/[signed](../signed.md) 四态 packed reg / logic / wire / tri；降序范围；宽表达式自动使用多字后端；[32 位四态 integer 与静态局部变量](../integer-and-locals.md)；[bit/byte/shortint/int/longint 两态类型](../two-state-types.md) |
| 存储器 | [一维 unpacked reg/logic 数组](../memory.md)，动态地址、字内选择、延迟读写、敏感依赖、波形和回滚；`$readmemh/$readmemb` 文件初始化 |
| 初始化 | 常量变量声明初始化；net 声明赋值按连续驱动处理；`'0` / `'1` / `'x` / `'z` |
| 表达式 | 常见算术、按位、归约、逻辑、比较、逻辑移位、三目、拼接、常量位选/部分选；赋值上下文位宽传播 |
| 进程 | initial、传统 always、begin/end、if/else、完整信号、常量位选/部分选、嵌套拼接的阻塞赋值与 NBA；部分 NBA 在提交时合并未写位；for/while/do-while/repeat/forever、case/casez/casex，循环与分支可挂起恢复 |
| 用户子程序 | [automatic 函数/任务](../automatic-subroutines.md)及[静态函数/任务](../subroutines.md)，整数/signed/packed 宽形参与函数返回值、静态局部变量、嵌套调用；任务 output/inout、delay/event/NBA，支持 [return](../procedural-actions.md) |
| 调度 | Active、Inactive（`#0`）、NBA 批次、常量/参数/运行时整数表达式过程 delay 与延迟 NBA、信号变化及 posedge/negedge、`@*` 读集合；实验性 [`--time-wheel`](../time-queue.md) 默认关闭 |
| RTL 连续赋值/primitive | assign、带赋值的 net 声明及标量 and/nand/or/nor/xor/xnor/buf/not/bufif/notif 的常量 delay；部分/拼接左值、同强度多驱动与 Z 解析；[支持边界及 VCS/IEEE 延迟模式](../continuous-delays.md) |
| 输出 | 格式化 `$display` / `$write`，`%b/%d/%h/%x/%o/%t`；`$finish`、模块单位 `$time`、受限 `$timeformat`；CLI 原生 VCD/DWF 压缩波形 |
| 独立门级 | `--gate-netlist` + `--gate-top`，结构 Network → 紧凑拥有数据的 IR；Liberty 组合 function/three_state、ff/latch、异步 clear/preset、多输出、同强度驱动解析、总线/部分选/拼接/复制连接、宽度适配、结构层次展开、RTL 测试平台及多 DUT 隔离 |
| 预处理/文件输入 | RTL 的 object/function 宏、默认实参、续行、token 拼接、基本宏字符串、ifdef/ifndef/elsif/else/endif、include/undef/undefineall、`__FILE__`/`__LINE__`；-I/-D/-U、+incdir+/+define+、-f/-F、-E、源位置/依赖导出 |
| SDF | 独立流式 parser；按需实例名称索引、层次/转义/通配绑定、pin/方向/互连可达检查、corner 数值预览；编译式IOPATH/逐接收输入INTERCONNECT回标；有限[条件路径执行](../conditional-paths.md)通过两平台及九类新VCS验收；PORT/DEVICE的多驱动、交错更新与[同定义模块通配](../../validation/m4-sdf-model-alias/README.md)差异已修正并定向验证，一般模型等价及primitive DEVICE仍待完成 |
| 预测与并行 | 可恢复检查点、预测事务和失败重放；保守并行/图分区 API；gate-only分析；实验性普通RTL独立域自动并行代码生成；内部切分、自动预测器和收益待完成 |
| 格式 parser | FTLib v14 plain/gzip 保存 Liberty three_state 及完整 ff/latch 字段，读取兼容 v5–v13（缺失信息不推断）；SPEF 等仍只有格式解析，尚无时序模型 |

支持常量条件/循环的 [RTL generate 子集](../generate.md)，包含逐迭代局部作用域、子模块、delay、波形和现有回滚。

尚未支持：完整 generate 语法与隐式命名消歧、实例数组、层次表达式引用、变量输出实际连接、非同宽 inout、完整类型参数/整数端口、命名及复合类型 cast、完整常量表达式与负下界索引、多维 unpacked 数组/数组端口/整数组赋值、动态连续赋值/输出适配的 select、复合赋值表达式返回值、ref/递归/常量函数及完整子程序语义、UDP、strength、动态连续赋值/门延迟、无赋值 net delay、完整 SDF 回标、完整 timing checks/notifier、Liberty bank/statetable、双时钟/双使能与延迟仿真、SPEF RC 仿真等。已识别的未支持结构会明确报错；原 parser 仍存在历史语法覆盖限制，当前测试不构成完整 IEEE 兼容保证。算术的 signed/unsigned 共同类型及上下文规则见 [signed 支持边界](../signed.md)。

过程赋值支持 [十二种复合赋值](../procedural-actions.md)。过程循环支持 [inline for 计数器、多赋值/空头部、语句增减及 break/continue](../loop-control.md)，按运行时控制流执行；repeat 入口捕获一次次数（X/Z 次数跳过），计数可跨 delay/event 挂起保留；计数器可使用 packed reg/logic 或默认 signed 的 32 位 integer/int；支持过程静态局部变量及词法遮蔽，见 [整数和局部变量](../integer-and-locals.md)。case 按所有标签和选择表达式的共同位宽比较，首个匹配分支生效，支持逗号标签、拼接标签及四态通配。

同一赋值的 RHS 只求值一次；按 VCS 实测，重叠的变量拼接左值以右侧项为最终值（Icarus 不同）。连续赋值各片段使用独立驱动，未写位驱动 Z，并批量解析，避免一次拼接赋值内部产生中间值事件。按 VCS 验证的端口语义：同宽 net 的直接引用/选择可按位连接，input/inout 的 net 拼接也可按位连接。RTL 前端当前对 output 拼接使用方向性适配器，覆盖前批常量专例；新门级动态连接探针显示更广的逐位 net 折叠行为，RTL 这部分覆盖仍需继续完善，详见本批门级连接记录。

## 独立门级入口

```sh
./build/dsim --gate-netlist tests/gate/four_state.net.v --gate-top dut \
  --liberty tests/gate/cells.lib tests/gate/four_state.tb.v -o build/gate_simv
./build/gate_simv
# 单独解析/绑定，避免混入 RTL、C++ 编译和仿真时间
./build/dsim --gate-check --gate-netlist tests/gate/four_state.net.v \
  --gate-top dut --liberty tests/gate/cells.lib --emit-ir build/gate.json
```

目前一次接入一份结构网表，文件内可有多个结构模块；`--liberty` 可重复。支持具名叶单元连接；已有 Verilog 端口声明时也支持叶单元位置连接。结构模块支持 ANSI/非 ANSI、可选 wire/tri net 类型、标量/packed 层次端口、裸 bus、常量位选/部分选、嵌套拼接和 RHS 常量复制，结构 assign 按位宽对齐、扩展/截断。内部 net/连接可超过 64 位（1024 位已有测试），索引与单次连接宽度限制为 1,000,000；连接展开不创建 RTL AST。

RTL 测试平台的门级 DUT 顶层端口支持降序宽向量（仍受结构reader单次连接1,000,000位上限约束）；内部结构范围可升序或降序，索引为非负十进制常量。net 端口按位共享连接，宽度不同时保留公共低位；常量输入与补齐位使用局部驱动，输出宽连接的额外高位驱动 0。inout 要求同宽；省略/空引脚保留未连接 net。宽 assign 作为共享复制模型一次读 RHS、批量提交驱动，重复目标也有独立驱动身份。数值常量支持 sized binary/octal/decimal/hex、signed literal 的扩展、非负 unsized decimal/based literal，以及上下文填充的 `'0/'1/'x/'z`；无尺寸十进制整数按已测 VCS 的 signed 32 位规则截断/扩展，基数字面量可具有更宽的自身宽度；signed 信号和一般运算表达式尚未支持。

叶单元支持 Liberty 标量 pin 的组合 function/three_state、多输出及单状态对 ff/latch；Verilog 单元行为模型、Liberty bank/statetable、双时钟/双使能、库 bus pin、结构运算/参数实例、一般门延迟、完整 SDF/Liberty/SPEF 时序尚未接入。含方括号/单引号的转义标量名及 `__dsim_` 前缀保留名明确拒绝。原时序 parser 的表达式近似模式不用于仿真。Liberty 三态未知禁用条件按 VCS 实测驱动 X；一般 RTL 条件三态的工具差异继续保留。常量输入接重复输出时，VCS 默认优化与 debug 配置又出现读回差异，本批保留独立探针，不将其列入默认通过数。


Liberty ff/latch 保存两个独立状态变量，初始 X，支持正/负沿或 Boolean 时钟函数、透明/保持、反馈 next_state/data_in、异步清零/置位及 L/H/N/T/X 冲突属性。状态采样后经 NBA 提交，纯输入相关的输出函数/三态控制继续在 Active 响应；未知边沿/使能/异步控制采用理想四态共识模型，Z 不作为存储值。与独立 UDP/行为参考的 VCS 对照不等于所有 foundry 模型、UDP 或 notifier 的四态行为完全一致，常用时序检查通过SDF入口接入，见[说明](../timing-checks.md)；完整notifier功能模型仍待支持。触发器只监测控制和输出的实际依赖，锁存器还监测 data_in；同沿级联、零时间脉冲及多个 DUT 的状态保持独立。字段/事件阶段与证据见[时序单元验证](../../validation/m3-sequential/README.md)。

## 验证与 VCS 对标

```sh
# 在 10.131.254.103 上，项目目录中运行
source /apps/EDAs/syn.bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DTCL_INCLUDE_PATH=/apps/anaconda3/include \
  -DTCL_LIBRARY=/usr/lib64/libtcl8.6.so
cmake --build build -j 6
ctest --test-dir build --output-on-failure
python3 scripts/compare_vcs.py --case control_case --repeat 3
```

远端 VCS 需使用 `-full64`；脚本已包含该选项。`--case` 可重复指定用例；省略时检查全部用例。当前 `control_loops` 的 X/Z repeat 常量赋值在 VCS 默认优化与 `-debug_access+all` 下结果不同，dsim/Icarus 与后者一致；单独复核该例使用 `--case control_loops --vcs-flag=-debug_access+all`，默认配置的失败也保存在验证记录中。对比脚本在同一主机分别编译 dsim/VCS，并对照相同 Verilog 输入及独立固定预期。每个用例重复执行，记录版本、输入 SHA256、选项、编译/运行时间、RSS、原始日志与 JSON。测试输入在设计上避开 Active region 的观测竞争，NBA 用例在 `#0` 和后续时刻分别检查提交前/后行为。

CTest 包含运行时真值表与调度测试、预热后的基本调度分配计数、Liberty 功能字段二进制回放、独立门级与 RTL 端到端正负例、原包 RTL 语义和格式 parser smoke。有 Icarus 时本地回归额外做 Icarus 差分。输入默认端口存在工具差异：VCS 对显式空连接保留 Z、只对省略端口应用默认值，顶层变量输入保持 X；Icarus 在该专门用例上的输出不同。部分输出 net 的内部读回、重叠变量拼接的写入顺序也存在 VCS/Icarus 差异；回归分别记录两组预期，dsim 按 VCS 行为实现。小型正确性用例不用于得出速度领先的结论。`python3 scripts/benchmark_vcs.py --iterations 100000 1000000 10000000 --repeat 3` 提供同机算术循环与时钟/NBA 的初始性能基线，输出实际差距；规则门级规模基线已建立，实际 RTL/门级设计和带时序性能仍需后续 M3/M5。

## 代码入口

- `src/gate_compiler.cpp`：独立 Network 解析、Liberty 功能编译、紧凑门级 IR 与共享模型生成。
- `src/rtl_compiler.cpp`：AST 适配、信号表、拥有数据的表达式/进程 IR、C++ 生成。
- `include/dsim/runtime.hpp`：四态运算、强驱动解析、敏感集合、事件调度。
- `src/main.cpp`：CLI、前端边界检查、生成文件与本机编译器调用。
- `tests/cases/`、`tests/regression.py`：行为基线、负例和可执行文件验证。
- `scripts/compare_gate_vcs.py` / `scripts/benchmark_gate_vcs.py`：独立门级 VCS 差分、parser/绑定规模与编译/仿真测量。
- `scripts/benchmark_sequential_vcs.py`：非规则 XOR/触发器反馈网络，独立状态递推预期，分别测量生成、编译和运行成本。
- `scripts/compare_vcs.py`：同机 VCS 差分与测量。
- `scripts/benchmark_vcs.py`：算术循环、时钟/边沿/NBA、共享时钟多进程扇出的规模基准；支持 `--baseline-dsim` 同时测量旧版，独立核对结果。
- `patches/`：对原 parser 的修复说明与可重放补丁。

原始 parser 的版权与许可说明保留在 `third_party/`。本项目没有为原包代码额外授予许可。

本次实测结果与原始证据见 [validation/README.md](../../validation/README.md)：M1 基线的 10 个用例通过 VCS 差分；M2 第一批的 15 个用例及历史证据见 [层次验证记录](../../validation/m2-hierarchy/README.md)；第二批 20 个用例的最终 native/VCS 复核见 [左值与按位连接验证记录](../../validation/m2-lvalues/README.md)；控制语句增量与前批性能基线见 [控制语句验证记录](../../validation/m2-control/README.md)；事件运行时优化见 [调度器验证记录](../../validation/m5-scheduler/README.md)。

独立门级接入和规模测量见 [门级验证记录](../../validation/m3-gate/README.md)：0.5.0 两平台 CTest 均 7/7，新增 3 组默认 VCS 对照；最终 native 30 例复核通过（29 个默认参考、1 个前批 debug 参考）。百万实例 parse 中位数 6.586s、bind 0.155s，进程峰值 RSS 中位数 704.91 MiB。规则链仿真仍需组合锥优化；真实设计性能与时序能力尚未完成。RTL 条件连续三态驱动的已测 VCS 差异也在该记录中保留。

结构宽连接、1024 位内部网、端口别名/原子提交及最终 0.6.0 的复核见 [门级连接记录](../../validation/m3-connections/README.md)。前批 0.5.0 的计时和校验清单保持为历史快照，不用于描述新版本性能。

0.7.0 的 Liberty ff/latch、NBA 状态阶段及最终规模基准见 [时序单元记录](../../validation/m3-sequential/README.md)：两平台 CTest 7/7，42 例最终复核（41 默认参考、1 前批 debug 参考）。10 万触发器反馈网络的 native/VCS CPU 中位数为 13.44/6.03s，仍有约 2.23 倍差距。0.7.0 原 RTL lexer 的同一行多字符串缺陷另有[历史失败复现](../../validation/m3-sequential/known-rtl-string-lexer/README.md)，已在 0.8.0 修复。


## RTL 预处理与文件列表（0.8.0）

```sh
./build/dsim -I rtl/include -D WIDTH=32 -F sources.f --top top -o build/design_simv
./build/dsim +incdir+rtl/include +define+FAST_MODE -f sources.f -E
./build/dsim -F sources.f --emit-preprocessed build/expanded.v --emit-deps build/deps.json -o build/simv
```

`-f` 的相对路径以当前工作目录为准，`-F` 以该文件列表的目录为准，可嵌套；列表允许空白、引号分组和 #/行/块注释，参数不经 shell 执行。include 先查当前工作目录，再按 `-I` / `+incdir+` 顺序搜索，不隐式搜索源文件所在目录；宏在本次调用的 RTL 文件间按顺序保留。`-D` 缺省值为 1，`-U` 与定义按选项顺序处理；Verilog 源码里的宏定义在用到时展开，支持嵌套参数与 ()/[]/{} 内逗号。

`-E` 输出 RTL 预处理文本并跳过 AST/编译。`--emit-deps` 保存读取文件的规范路径和输出行对应的原始文件/行号；include、文件列表及符号/硬链接输入均受输出覆盖保护。解析错误保留首个错误行，编译后端的行号也映射回原始源文件。门级结构文件仍直接交给独立 parser，以上预处理用于 RTL/测试平台，不为百万门网表建立 RTL token/AST。

当前有显式限制：最多 64 层 include/文件列表、100 层宏展开、100 万次宏调用、256 MiB 输入/输出和 800 万 token；递归、未定义宏、缺失文件及不支持的 directive 都报错。default_nettype、宏生成 directive、复杂宏转义字符串、文件列表环境变量替换和自动库搜索等继续按计划扩展。当前字符串输出支持引号、反斜杠、换行和制表符转义，其他转义仍明确拒绝。

VCS 参考、独立预期及前批功能复核见 [预处理验证记录](../../validation/m2-preprocessor/README.md)。运行时和门级求值代码相较 0.7.0 保持不变；前批性能仍是其原始版本的数据。

## 压缩波形实验原型

波形压缩已列为正式 M6 范围。`experiments/waveform/dwf.py` 提供数字 VCD → DWF → VCD 的可解码原型和按时间窗口查询，使用时间差、四态位平面、XOR、独立 Zstandard/DEFLATE 压缩块、检查点与索引。这是前批独立转换原型；当前开发版另有原生 C++ 后端（见下文），testbench 的 `$dumpfile/$dumpvars/$dumpoff/$dumpon/$dumpall` 已接通，支持边界及 VCS 对照范围见[任务控制波形](../wave-dump-tasks.md)。

```sh
# Zstandard 使用 Python 3.14 compression.zstd；也可 --codec zlib
python3 experiments/waveform/dwf.py pack input.vcd output.dwf --codec zstd
python3 experiments/waveform/dwf.py unpack output.dwf restored.vcd
python3 experiments/waveform/dwf.py window output.dwf 100 110
python3 experiments/waveform/verify.py
```

现有四态门级用例及两组生成 RTL 波形均通过三种 codec 的完整事件回放和 VCD 往返，共 270 个窗口查询通过。压缩比与 Python 吞吐见 [原型验证](../../validation/m6-waveform/README.md)，格式、原生 writer 接入和百万信号扩展见 [设计](../waveform-format.md)。格式仍可变，不将 Python 转换速度当作原生写波形性能。

## 当前开发版：SDF、回滚与并行基础

性能主线新增实验性 [`--time-wheel`](../time-queue.md)，支持 RTL 各类定时事件与现有 SDF 后端，默认关闭。近时间采用 256 个稳定 FIFO 桶，远时间保持稳定堆，全部队列状态支持检查点恢复。当前接入的正确性验证见 [本批记录](../../validation/m5-time-wheel-integration/README.md)，尚无 Linux 性能收益结论。

```sh
./build/dsim --sdf-check timing.sdf --emit-ir build/sdf-summary.json
./build/dsim --wave-support testbench.v -o build/simv
./build/simv --waveform build/run.dwf --wave-mode ordered --wave-codec zstd
```

SDF 采用独立流式前端，支持常用路径、条件、min/typ/max 与 timing check 数据；已有模型路径匹配与有限的[编译式IOPATH回标](../sdf-runtime.md)，逐接收输入INTERCONNECT及九类常用时序检查已接入实际运行。开发版新增有限条件路径/ifnone执行，新VCS发现的边沿fallback差异已修正，432组合源两平台各92项、九类新VCS各三次及全量SDF两作业后端各128笔已验收；一般条件表达式和完整notifier仍待补齐。原生 VCD/DWF 已接入，0.10.0 增加 RTL timescale、常量分数延迟和实际精度波形；参见[时间语义](../time-semantics.md)。

`Sim` 新增内核检查点、预测验证/失败重放与提交输出；`include/dsim/parallel.hpp` 提供保守并行内核和图自动分区 API。`--gate-partition-report N` 单独使用时仅分析 gate IR。实验性 [--threads](../automatic-parallel.md) 可自动生成普通RTL独立域的多内核程序，gate scope内部仍不切分。并行 [单文件全局 VCD/DWF](../parallel-and-rollback.md#单文件全局压缩波形)在窗口提交后归并各分区波形，支持全局结束回滚前缀；CLI 尚无自动预测器。支持范围、待完成项和验证入口见 [功能矩阵](../vcs-feature-status.md)、[SDF 设计](../sdf-parser.md)、[并行/回滚设计](../parallel-and-rollback.md)。

编译时可使用 `` `timescale 1ns/1ps `` 或 `dsim --timescale 1ns/1ps top.v -o simv`。源文件声明优先；未声明时默认 1s/1s。常量小数及运行时整数表达式过程延迟、`$time` / `%t` 与受限 `$timeformat` 已接入；`$realtime` / real 运算仍不支持。开启 `--wave-support` 后波形自动采用实际仿真精度，无需设置波形单位。


0.11.0 的 SDF 端点绑定入口与边界见 [SDF 绑定](../sdf-binding.md)。当前 `--sdf-bind-check` 只校验拓扑并选择数值，不施加延迟；独立 gate parser 在绑定检查与 `--sdf-annotate` 模式保留时序名称；后者支持有限的无条件 IOPATH 运行时，见 [支持边界](../sdf-runtime.md)。预测/回滚与并行现状见 [设计与限制](../parallel-and-rollback.md)，压缩波形见 [格式](../waveform-format.md)。

0.12.0 加入单驱动内联和状态输出的重复求值消除；适用条件、四态/事件边界及测量见 [仿真性能优化](../simulation-optimization.md)。

实验性性能后端新增 [`--gate-sdf-jobs`](../sdf-jobs.md)，将IC/IOPATH的通用进程替换为保持原FIFO位置的专用作业；要求标量SDF选项，默认关闭，尚无性能收益结论。

完整原始SDF最新[五程序消融](../../validation/m5-sdf-ablation/README.md)已审计PASS：实验组合CPU中位数80.31s、同轮VCS7.47s（约10.75倍），相对scalar的配对改善中位数10.73%待独立复测；单独wheel回退6.30%、jobs改善0.22%，选项均默认关闭。新[路径延迟表去重](../../validation/m5-path-dictionary/README.md)候选已接入CLI并验证完整表128笔，但未参与本轮计时，尚无其性能结论。

M31 新增 [automatic 函数/任务](../automatic-subroutines.md)：非递归调用的入口初始化、局部数组/循环块生命周期、跨 delay/event 的激活隔离、默认/命名实参与类型、波形和挂起期间回滚。实际 VCS 六例全部 1272 条导出物理位时间线一致；递归/ref/fork、完整常量函数、package/interface/class/UVM 等仍未齐备。验收见 [M31](../../validation/m31-automatic-subroutines/README.md)，本批没有新的性能测量。
