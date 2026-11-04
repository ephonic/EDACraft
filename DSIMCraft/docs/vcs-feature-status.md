M236 开发实现[virtual interface task/function 调用](virtual-interface-calls.md)，原版 UVM driver 经接口任务驱动 DUT、monitor 经接口函数采样，3笔/303与同源VCS一致；接入参数/ref、延时重入、实例static局部和纯automatic函数事件/wait。带副作用实参改绑的绑定时机、带副作用事件函数、空接口函数三个探针仍有差异，单列不计为对齐通过。验收/发布见 [M236](../validation/m236-interface-calls/README.md)。

M235 修复运行期 stream cast 丢失枚举身份，原版 UVM 8192 位 pack/unpack 已通过并与 VCS 输出8196/8196一致。M234 的真实 DUT/virtual interface 集成也通过完整前端和原生 ASan/UBSan。联合对象图随机化、DPI open array、带参数覆盖率采样及完整 SVA/VPI 仍有缺口；当前发布进度见 [M235](../validation/m235-stream-enums/README.md)。以下批次为历史状态。

M233/M234 接通[virtual interface](virtual-interfaces.md)及动态 stream 左值：原版 UVM 的 config_db→driver→真实 DUT→monitor→scoreboard 与 field 工具用例通过（UVM_NO_DPI、原生 -O0）。仍缺联合对象图随机化、DPI open array、带参数覆盖率采样及完整 SVA/VPI；8192 位 UVM pack/unpack 尚有枚举类型阻塞，未算通过。当前验收/发布见 [M234](../validation/m234-virtual-interfaces/README.md)。以下批次为历史记录。

M232 双端稳定版接通 [类属性 ref](object-scalar-references.md)，完整原版 UVM 的 hello 和 sequence/driver/factory/config_db/analysis/scoreboard 用例在 UVM_NO_DPI、原生 -O0 下通过，集成的前端/原生 ASan/UBSan 也通过。uvm_field_* 工具用例仍缺动态数组左值流式赋值，完整 UVM/DPI/VPI 尚有缺口；详见 [M232](../validation/m232-scalar-refs/README.md)。

M231 双端稳定版新增 [关联数组值形参与回写](associative-values.md)，十个同源 VCS 模型、29 次原生捕获及完整波形通过，并修复后续类特化的虚分派表缺项。完整未修改 UVM 已编译为本机程序，运行仍卡类标量字段 ref，未通过 run_test；见 [M231](../validation/m231-associative-values/README.md)。下列批次为历史记录。

M226 生产源码 297d8a7a 已推送并双端发布，每端两组 105 捕获及实际入口验收通过。补齐[函数终止与暂停控制](function-termination.md)：函数/递归/虚方法/构造器中的 `$finish`、基本 `$stop` 恢复及初始化/final 边界。十二同源 VCS 模型二十执行路径通过；开发八十次原生执行、五十六捕获、十二模型 ASan/UBSan、四次强制失败预测和三次暂停屏障回放通过。未修改完整 UVM 当前首错推进为 uvm_resource_pool.svh:178 关联数组函数实参，仍未生成完整原生模型或跑通 run_test。参数及交互调试仍有明确边界，见 [M226](../validation/m226-function-termination/README.md)。

M230 双端稳定版新增 [运行期数组 stream/cast 与固定字符串数组](array-streams.md)，十二同源 VCS 输出一致、两项差异单列；完整 UVM 继续推进至 uvm_phase.svh:2092 的关联数组按值/output 传参，尚无原生 run_test 成功结论。见 [验收](../validation/m230-array-streams/README.md)。


M229 双端稳定版新增 [可恢复共享自动任务](shared-tasks.md)，十二同源 VCS 输出对齐，完整 UVM 的任务重入阻塞已越过，当前仍卡 uvm_reg_map.svh:2160 的动态队列流式转换。原生完整 UVM/run_test 仍未通过，验收见 [M229](../validation/m229-shared-tasks/README.md)。


M228 双端稳定版新增 [process::status/kill/await](process-lifecycle.md) 与生命周期回滚。原始完整 UVM 同源 smoke 在 VCS 编译运行通过，dsim 当前仍卡 uvm_reg_sequence.svh:570 的 start 任务重入；未生成完整 UVM 原生程序。验收见 [M228](../validation/m228-process-lifetime/README.md)。


M225 生产源码 `1bd413af` 已推送并双端发布，每端三组 113 捕获及实际入口检查通过。新增[运行期字符串重复](string-replication.md)及字符串到 packed 转换。9 个同源 VCS 模型、36 捕获、9 个前端/原生 ASan/UBSan 和四个强制失败预测回放通过。未修改完整 UVM 默认/共享/消毒前端均越过 printer，下一阻塞为 `uvm_root.svh:183` 函数内 `$finish`，尚未生成完整模型或跑通 `run_test`。运行期数值 packed 重复、动态重复的 `$bits`、带全局副作用的计数函数检查仍有边界；见 [M225 验收](../validation/m225-string-replication/README.md)。

M224 已双端发布（生产 78c8698a）：补 [类成员/自动局部事件复制](event-aliases.md)，保留旧等待与延迟触发身份，接通局部 fresh event、模块来源通知和空事件语义。十同源 VCS 与四模式 40 捕获通过；未修改完整公开 UVM 默认/共享/消毒均推进至 uvm_printer.svh:1501 运行期字符串重复，完整 UVM 仍未跑通，process::await 等仍缺。边界与发布见 [M224](../validation/m224-event-aliases/README.md)。

M223 已双端发布（生产 17986884）：补 [函数内 join_none](function-background-forks.md)，支持后台延时/等待、活跃自动帧、按实际父进程等待/取消及启动调用。九同源 VCS 模型与四模式 36 捕获通过，函数 fork 的线程请求明确回退单内核。REPORT-GAP13 打桩库下一项为 process_guard:152 `process::await`；未修改公开库仍先卡 event 句柄赋值，完整 UVM 未跑通。验收与发布见 [M223](../validation/m223-function-forks/README.md)。

M222 开发实现：新增[类成员动态数组/队列 ref 引用](object-array-references.md)，支持真实别名、重分配、嵌套转发、延时调用、等待唤醒；有界到无界引用保留实际容量，普通队列同样接入。十个同源 VCS 用例与一个单列差异探针完成三模式原生检查。未修改完整 UVM 已越过 reg_item 数组引用，默认/共享/消毒均到达 uvm_event.svh:268 事件句柄赋值；**完整 UVM 仍未跑通**。发布与边界以 [M222 验收](../validation/m222-object-array-refs/README.md) 为准，下面较早批次为历史状态。

最新 M215（生产 c10bf303 已双端发布）：补 `$typename(T)` 及已支持类型元数据、带副作用的字符串条件分支、UVM 字符串队列右向流拼接。原版公开 UVM 首错已推进到寄存器序列 `uvm_field_queue_string` 的 `do_execute_op` 数组语义，完整 UVM 仍未运行。本轮优先功能；没有新的性能对齐结论，编译快慢须以同条件 VCS 对照判定。验收与发布见 [M215](../validation/m215-uvm-reflection/README.md)。

历史 M200：修复 class/null 常量折叠边界与纯读三目分支惰性求值；共享按声明/词法作用域绑定的子程序语义体，运行时激活仍独立；符号作用域按负载扩容。公开未修改 UVM 当时已越过静态单例错误和重复展开内存增长，阻塞为 `uvm_phase_hopper.svh:763` 的 `sort() with`。验收范围和收据见 `validation/m200-integral-folding/`。

# 功能状态与优先级

最新 M214（生产 3ca118ba 已双端发布）：补字符串转义、null 实参、递归 input/ref 数组、class 条件表达式、多层 type_id 工厂别名及省略括号函数调用；新增可选 [共享函数体](shared-functions.md) 和写范围元数据去重。七个同源微例已与 103 VCS 全部 TRACE 对齐，三种串行模式完整有序波形与失败预测回放通过；真实 DPI 调用/回调另验。未修改公开 UVM 当前首错推进到 `uvm_resource.svh:80` 的 `$typename(T)`，**完整 UVM 仍不能原生编译运行**。C910 原始 RTL/TB 的最小 RV64 镜像已通过分片原生构建并实际得到 TEST PASS；完整 ISA/性能仍未对齐。发布与消毒边界见 [M214](../validation/m214-uvm-functions/README.md)。以下 M210 及更早段落是历史记录。

最新 M210：[函数互递归与类方法递归](recursive-functions.md) 已接通标量 input 参数的调用环、自动/静态生命周期、接收对象、虚分派和预测恢复，并修复自动任务之间共享函数临时变量导致的单分区退化。Mac 与 103 Intel 已发布冻结实现 `1f3a9e72`；每端选定四组 32 模型/530 捕获、mandatory 检查及实际入口通过，跨端 103 份 C++ 与 530 份完整解码捕获一致，31 份压缩编码差异单列。七同源 VCS 和 Mac 前端/生成程序 ASan/UBSan 通过；没有新的速度对齐结论。未修改公开 UVM 当前首错为 `uvm_component.svh:1753` 的字符串转义，完整 UVM 尚未编译运行。递归非 input/数组参数、递归任务和完整对象图随机化仍有边界；收据见 [M210](../validation/m210-recursive-functions/README.md)。以下为历史批次记录。

M199 新增[功能覆盖率](functional-coverage.md)：covergroup 实际采样、bins/cross 计数、实例/覆盖点查询和 checkpoint。REPORT-GAP6 原始 q03 纳入回归；带参数采样、复杂 bins、自定义 cross 和数据库仍缺。未修改公开 UVM 的首个实际阻塞仍为单例 handle/null 常量函数求值，不能视为完整 UVM 已通过。

当前实现 M199：新增[功能覆盖率](functional-coverage.md)，保留 M198 string 队列与 M197 packed 关联键能力。未修改公开 UVM 的首个实际阻塞仍在静态单例 handle/null 常量函数求值；完整库不能运行。复杂覆盖率、virtual interface、dist/soft/solve-before 和完整 SVA/DPI/VPI 仍需补齐。

历史稳定批次 M181（7c1e2525，已推送）补齐类/参数化类型 for 局部声明、automatic 循环生命周期、函数步进、空队列字面量与拼接类型校验。Mac与103 Intel每端完整九组891份捕获与17个实际入口模型复验通过；220份生成CPP与896份解码波形跨端一致，30份压缩编码字节差异单列。验收结果见 [M181记录](../validation/m181-typed-for/README.md)，最新报告复核见 [GAP4当前对照](../validation/m183-compilation-types/REPORT-GAP4-CURRENT.md)。

上一双端稳定批次M182（生产实现de430e17）：Mac与103 Intel均已更新，1236输入相同；每端三组422捕获、mandatory及五个实际入口模型复验通过，77份CPP与422份解码波形跨端一致。新增状态容器约束foreach和类内队列，完整边界及证据见[M182记录](../validation/m182-constraint-foreach/README.md)。

M180已补原生randc、randomize(property,...)及randomize(null)，随机历史随checkpoint恢复。M179已对齐mailbox整型等价规则与semaphore可满足请求调度。M182已补[状态容器约束foreach与类内队列](constraint-foreach.md)，生产实现de430e17。M183已补[编译单元class与typedef](compilation-types.md)，生产实现32c524c1，Mac与103 Intel稳定入口均已更新，1245输入一致；每端三组选定回归227捕获、mandatory及六个实际入口模型通过，69份CPP与227份解码波形跨端相同。远端日志断管失败与同候选恢复核验均保留在[M183记录](../validation/m183-compilation-types/README.md)。六新模型110捕获、16拒绝、真实双分区、回滚/提交及sanitizer、六同源VCS正例通过；VCS另确认四项文件级语法能力仍缺。未修改公开UVM smoke当前首错进入chandle语义分析，完整库仍未展开运行。接下来优先chandle与编译单元类型剩余能力、随机复合数据，再推进dist/soft/solve-before、virtual interface/clocking及coverage。

以下M178及更早条目是当时的历史记录，安装与功能状态以上述记录为准。

M178本地：[mailbox/semaphore](ipc.md) 已接通原生对象、阻塞与非阻塞方法、FIFO、取消及checkpoint。
新9模型164捕获、27编译拒绝/9运行时诊断，覆盖无类型mailbox的packed选择类型检查和整批取消后的资源保留；验收及ASan/UBSan结果见
[M178记录](../validation/m178-ipc/README.md)。当前未修改公开UVM仍首错于 `uvm_sequence_library.svh:191` 的 `randc`，完整库仍不能运行。
仅本地开发，未推送/操作103/激活稳定入口。后续优先randc/dist/solve-before与clocking/coverage。

M177本地：按REPORT-GAP3补齐队列末下标及unsigned关联键，详细实现、复测与边界见
[M177记录](../validation/m177-gap3/README.md)。公开UVM原生首个语法错误推进到
`uvm_sequence_library.svh:191`的`randc`，完整UVM仍不能编译运行。
本轮仅本地开发，稳定入口仍为M175；以下M176首错记录是历史结果。

M176开发进度：原生时间语义、匿名enum、动态数组/队列赋值模式与非类const已接入，
17模型310捕获/32拒绝、两次预测回滚/提交和ASan/UBSan通过。
公开UVM仍不能编译运行，当前首错为sequencer_base:426的`int unsigned`关联索引。
VCS时间模型及低于1fs精度仍有已知差异，新增用例待远端复验，未发布。
详见[M176开发记录](../validation/m176-time-literals/README.md)；下面稳定版状态仍为M175。

M175历史进度：重新检查 REPORT-GAP/GAP2
的19个原始探针，11个能生成C++、8个仍拒绝；这是前端结果，未计为11个全部原生运行。
结果与源码SHA见 [原始探针复查](../validation/m174-constraint-randomization/report-probes.json)。

| 范围 | 当前证据与剩余工作 |
| --- | --- |
| OOP / 子程序 | 已接通参数化类、继承/虚派发、权限、extern；新增[无括号函数体](nonansi-bodies.md)、[const 属性](const-properties.md)，支持范围内有实际执行/VCS对照；完整OOP仍有边界。 |
| 容器与数组 | 已有动态/队列/整数及字符串关联数组，新增[定位与去重](array-locators.md)、[foreach接收者](foreach-receivers.md)、[下标接收者与子数组](foreach-selections.md)；已支持 class 键和纯关联多维数组；混合 runtime 容器、关联形参及部分实例数组仍缺。 |
| 数值 / DPI | 已补实数值链路、浮点DPI和[字符串转换](string-casts.md)；完整DPI/VPI、动态实数/字符串容器仍缺。 |
| 真实公开 UVM | 未修改2020.3.1库仍不能编译运行；M224 当前 smoke 首错为 uvm_printer.svh:1501 运行期字符串重复。首错推进不代表完整方法学可用。 |
| 验证运行时 | 新增[实例整数约束随机化](constraint-randomization.md)，原始q02/q13实际运行通过；已补randc与本次变量列表/null控制；已补当前状态容器的约束foreach；分布/soft/solve-before及随机复合数据仍缺。原生mailbox/semaphore已接通，部分消息/ref类型仍有限制；virtual interface/clocking、covergroup及完整program/let/specify/assert控制仍有缺口。 |
| 用户范围压缩波形 | 独立线程接收、编码/Zstd压缩及写盘，支持scope/include/exclude和start/end；VCD/同步与异步DWF及预测恢复持续检查，动态字符串内容等仍有限制。 |

M174 冻结91cc686e，Mac与103 Intel各七组728捕获、mandatory和实际入口六模型复验通过，
两端稳定入口已更新，覆盖M172 const与M173 foreach基础支持。
M174六模型110捕获/28拒绝/1运行时错误及ASan/UBSan通过，VCS六个相同正例运行通过；
失败不写回、对象随机状态/模式及回调的预测恢复也已验证。
M175新增下标接收者、子数组及关联cursor重新求值，六同源VCS模型执行及八拒绝一致，
ASan/UBSan通过；本地冻结2d99736e七组818捕获及mandatory通过，已更新稳定入口。
1157发布输入、19新增CPP/110捕获绑定相符，实际入口六模型与所选范围复验通过。
103 Intel同样通过七组818捕获与mandatory，1157输入及新增19CPP/110捕获跨平台逐字节一致，
root/bin稳定入口已更新，实际入口六模型与所选范围复验通过。
没有新的性能对比结论。以下为历史批次原始记录。

M167 补齐[逗号后的嵌套参数化类形参](parameterized-formals.md)，保留泛型身份、方向继承、默认值和extern语义；跨Flex缓冲、长注释、字符串/转义名与错误恢复另验。Mac六组781捕获和mandatory检查通过，新八模型146捕获/8拒绝、回滚/提交及真实双分区通过；25CPP与开发证据相同，ASan/UBSan和独立writer TSan通过。本地稳定入口已更新；未修改公开UVM首错推进至printer:176的real，完整UVM仍不可运行。real值语义、约束随机、IPC、clocking/coverage等继续补齐。接口组陈旧“层次写只读”拒绝改为执行正例，首候选未激活；103连接超时未更新，无新VCS/性能结论。详见[M167](../validation/m167-parameterized-formals/README.md)。

M166 根据 REPORT-GAP2 补齐[连续类参数声明与必填值参数](class-parameter-lists.md)，以及逗号后的作用域限定类型形参。Mac四组742份捕获与mandatory检查通过，新增八模型146捕获/16拒绝、回滚与真实双分区通过；ASan/UBSan、异步writer TSan通过，稳定入口已更新。报告原始19探针中9个可生成C++，这不代表全部已原生运行。未修改公开UVM首错推进到config_db_implementation:119的参数化类形参，完整UVM仍不可运行；约束随机、IPC、virtual interface/clocking、coverage、program/let和assert控制等仍有缺口。103连接超时未更新，无新VCS/性能结论。详见[M166验收](../validation/m166-class-parameter-lists/README.md)。

M165 已补 [extern 类外方法定义](extern-methods.md)，覆盖构造器、void/命名/数组返回、参数化特化、虚派发、static、默认实参、ref 和延迟 task；返回类型/形参的作用域及命名类型绑定分别检查。冻结73a3a7cc，Mac八组1162捕获与mandatory检查通过，新增十一模型200捕获/31拒绝/1回滚1提交；34CPP与开发证据相同，ASan/UBSan和实际双分区异步writer TSan通过。Mac稳定入口已更新，实际入口新类型返回/句柄别名、原始q11/r02及完整/所选异步波形复验通过。首两个候选的作用域问题及撤回记录保留。未修改公开UVM仍在pool:49的连续类型参数处正常拒绝，完整UVM/约束随机/IPC/clocking/coverage仍未完成；103未更新，无本批VCS/Intel或速度结论。详见 [M165](../validation/m165-extern-methods/README.md)。下列首错与状态为历史批次记录。

M164 已补 [DPI-C function 真实调用与回调](dpi.md)：C ABI 参数、宽四态 packed/output/inout、string、context 作用域和普通 C 调用的预测屏障。冻结 f3e10bc9，Mac六组615捕获及mandatory检查通过，稳定入口已更新；新增六模型110捕获、23编译拒绝、5运行时拒绝、2回退/1提交、ASan/UBSan与TSan通过。22份新生成程序在开发/发布之间仅默认C库路径不同。实际入口原始q11提供真实C动态库后输出6，原始r02、C回调和用户范围异步波形复验通过。未修改公开 UVM 的首错为 `uvm_object.svh:70` extern，完整 UVM 仍不能原生编译运行；本批没有 VCS/Intel 对照或性能结论，103未更新。详见[M164](../validation/m164-dpi/README.md)。下文 M163 及更早段落是历史状态，当前边界以本段和 DPI 文档为准。

M163 已读取原始 REPORT-GAP2 并复跑现存探针，继续补 [local/protected 类访问](class-access.md)：词法权限、继承/同类其他实例、工厂构造、参数化/static 成员和虚覆盖权限合同。冻结 b7d58d56，Mac 最终五组778捕获、24个新拒绝与 mandatory 检查通过，稳定入口已更新；31份新生成程序与 sanitizer/development 字节相符，ASan/UBSan、真双分区异步 writer TSan 和实际入口范围波形复验通过。开发另十组分批执行通过，最终五组使用冻结源重跑。公开 UVM 语法首错推进至 `uvm_globals.svh:124` 的 DPI-C 导出，**完整 UVM 仍不能原生编译运行**；约束随机、IPC、clocking/virtual interface、coverage/DPI 等仍未完成。详见 [M163](../validation/m163-class-access/README.md)。以下保留历史批次的原始状态，当前首错以本段为准。

M162 实现 [未打包类型别名、数组值返回与队列形参](array-aliases.md)，贯通类型形状/实例克隆/参数化特化、automatic 返回快照、引用与值传递、虚方法签名和队列拼接。原始 REPORT-GAP2 r02 已运行通过，新11模型开发验证200捕获及14拒绝边界通过；最终冻结2ff24ad7，Mac七组1005捕获与实际入口复验通过，稳定版已更新；新前端/生成程序/预测回放的ASan/UBSan和双分区异步writer的TSan通过。补充回归13组执行通过，三组诊断预期修正后在正式组重跑通过，328份相关正常生成程序与探测入口修正前逐字节相同。未修改公开 UVM 首错推进至 `uvm_coreservice.svh:165` 的 `local`，**完整 UVM 仍不能编译运行**。103 无响应，本批暂无新 VCS/Intel 对照，远端入口保持原版；不作速度结论。详见 [M162](../validation/m162-array-aliases/README.md)。下列历史首错和未完成项以本批当前记录为准。

M161 补充 [函数/任务/构造器结束标签](subroutine-labels.md)，并精确验证标签名称。四个同源模型覆盖多种声明形式、参数化克隆、虚拟派发、延时任务、双分区、预测恢复和用户选择范围波形；开发回归74捕获通过，标签移除后的生成代码相同。VCS三个非空TRACE模型一致，四模型1007共同可见位时间线一致，96个native合成类静态位单列。九个错误标签均与VCS同样拒绝。公开UVM首错已由 `uvm_misc.svh:377` 推进到 `:611` 的队列类型别名；**完整UVM仍不能原生编译执行**。Mac八组737捕获及实际入口复验通过并已发布；103额外 automatic_subroutines/types.sv 并行编译超时，未发布，原因待查。验收见 [M161](../validation/m161-subroutine-labels/README.md)，未以语法推进替代完整UVM验收。

M160 已补齐 [static 类存储、方法与类作用域](class-static.md)，原始 REPORT-GAP2 r01 无改写通过；Mac/103 Intel 各九组1102捕获通过，新十模型31份C++/182捕获跨平台一致，三个稳定入口已更新。VCS 八个非空输出模型对齐，双分区无输出模型128位波形对齐；ref 实参的一例保留两条调用计数差异；两个接收性边界也仍比 VCS 严格。实际公开 UVM 首错推进到 uvm_misc.svh:377 子程序结束标签，**完整 UVM 仍不能原生编译运行**。详见 [M160 验收](../validation/m160-class-static/README.md)。本批无性能结论；后续继续子程序/类限定符、约束随机与 IPC 等依赖。

M159 已按 REPORT-GAP2 补齐 [string 键和类关联数组](string-associative.md)，包括方法、foreach、复制、两态转换及 checkpoint/预测恢复。Mac/103 Intel 各七组904捕获通过，九同源VCS输出及三个模型256个可见声明位时间线一致；三个稳定入口已更新。完整 UVM 的语法首错已推进至 static function，**仍不能原生编译运行**；原始r02还缺队列拼接初始化。验收和首轮回归记录见 [M159](../validation/m159-string-associative/README.md)，后续优先 static、约束随机与 IPC；下列历史 UVM 阻塞描述以本项为准。本批不作性能结论。

M158 已修复新增 retained_memory_codec 的大函数重复内联编译超时及默认指令预算误终止。原始15418完整四态观测与VCS一致，Mac/103各六组通过，新组8份C++与20捕获跨平台相同，三个实际稳定入口已更新。原周期参考来自合格VCS轨迹，未宣称独立周期oracle或一般runtime加速。验收、首轮失败和限制见[M158记录](../validation/m158-function-boundaries/README.md)。REPORT-GAP2 已更新规划，完整公开UVM仍在string键关联数组处拒绝。

M157 已修复新增七个问题 case 的层次变量/内存写入和独立空语句：原始25470完整观测与新鲜VCS一致，Mac/103各九组817捕获通过，稳定入口已更新。详见[验收与边界](../validation/m157-reported-cases/README.md)。期间新增的 retained_memory_codec 已在M158单独修复验收。REPORT-GAP2 已纳入规划，完整 UVM 仍不支持。

稳定版 M156 已补原生参数化类、类型/整数参数绑定与规范特化、参数化继承及函数签名应用。Mac/103 Intel 各十二组1726捕获通过，新九模型全部1184导出位与VCS一致；四项无效参数覆盖的编译接收差异保留。详见[本批验收](../validation/m156-parameterized-classes/README.md)。公开 UVM 预处理通过，native 语法首错已移到 uvm_misc.svh:96 的字符串键关联数组，**完整 UVM 仍不能编译运行**。独立波形线程及用户范围选择持续验收；下列历史阻塞描述以本项为准。

M153 根据公开 UVM 实际阻塞补通 [宏续行、展开中的条件编译与字符串替换](uvm-preprocessing.md)，并修复 RTL 语法恢复崩溃。公开 UVM 包+component 已完整通过 dsim 预处理，其展开源码在 VCS 运行通过；native 仍在类前向声明正常拒绝，**完整 UVM 尚不可运行**。CRLF 续行及普通替换字符串嵌套宏的参考差异保留。Mac/103 发布验收见 [M153](../validation/m153-uvm-preprocessing/README.md)，历史 UVM 预处理阻塞描述以本项为准。


M152 新增 [抽象类、纯虚方法与动态 `$cast`](abstract-casts.md)，Mac/103 稳定入口已更新，各七组 879 捕获通过。六个 VCS 对照模型中四个输出/波形完整一致，两个仍有明确差异，详见 [M152 验收](../validation/m152-abstract-casts/README.md)。独立波形线程支持范围选择、差分编码、Zstd 与索引写出；采用自有 DWF，未兼容 FSDB 二进制。实际未修改的 Accellera UVM 2020.3.1 component smoke 在 VCS 通过，dsim 仍卡在宏续行预处理；完整 UVM 尚不可运行，参数化/编译单元类、对象容器、约束随机、IPC、虚拟接口等仍待补齐。


M151 补齐 [class 单继承与虚方法](class-objects.md)：`extends`、`super.new`、隐式构造链、派生到基类值传递、协变返回、虚函数及带延时虚任务分派。原始 REPORT-GAP q01 已通过，同源 VCS 八模型输出及十三个拒绝例对齐。异步压缩波形和用户指定范围继续纳入发布检查。抽象/参数化类、对象容器、约束随机及完整 UVM 仍缺，完整验收与边界见 [M151 记录](../validation/m151-class-inheritance/README.md)。

M148 根据 REPORT-GAP 补入 [UVM integral 容器基础](uvm-containers.md)：queue 与 int-key associative array 的原生存储/方法/克隆/automatic/事务链路；动态数组原先已支持，不能将报告 q05 的失败归为三种容器均缺。另新增 [独立波形接收线程](waveform-format.md)，可将 DWF 编码、压缩和文件写出一起移出仿真线程。最终验收见 `validation/m148-uvm-containers-wave`。完整 class/约束随机/UVM 仍未实现，报告中“RTL/门级全面可替代、性能全面领先”的结论超出已有测试范围，本轮不采纳为产品保证。


M144 补齐 [modport task/function 原型 import](modport-prototypes.md)，支持按视图默认参数、前向声明、参数化实例克隆及签名检查。命名实参按实际实现的形参名绑定，默认值按所选 modport 的原型绑定；这一行为以 VCS 同源用例验证。modport export、virtual interface、clocking、类型参数、类/约束随机和完整 SVA 仍有缺口。本轮功能优先，不新增性能结论。

M140 接通[有限序列作为蕴含前件](sequence-antecedents.md)：`a ##N b |->/|=> c`、命名序列、分组与固定连续重复，区分前件空成功和后件失败，并接通采样、异步取消及事务恢复。双端五组发布回归通过，新组各 29 份逐信号有序捕获、5 次预测提交/5 次回滚、4 次预算续跑、2 次 checkpoint 恢复和 15 个拒绝例通过，实际并行为两分区。五模型全部 TRACE 及层次归一化后的全部 1503 个声明位 settled 时间线与 VCS 一致。完整 parser 和 11 份生成程序 ASan/UBSan 通过；Mac 与 103 Intel 稳定入口已更新。六个旧模型仅在替换嵌入 runtime 文本后生成 C++ 相同，不能表述为全部原始 CPP/运行时不变；七个其他 runtime 头相同。范围/无界重复、序列形参、多时钟和完整 SVA/class/UVM 仍缺，本批没有速度测量。详见 [M140 验收](../validation/m140-sequence-antecedents/README.md)。

M139 已修复 cases 下两组新问题：标量 `[0]`/零边界宽度一选择被误报，以及大型展开式一次性 TB 的生成 C++ 编译超时。原始输入和 180 秒预算保持不变；SRAM 全部 4480 阶段、memory 全部 3840 阶段通过，同源 VCS 重新运行通过。Mac 编译分别 56.896/60.101 秒，103 Intel 分别 160.761/168.430 秒。双端各三组发布回归及 parser/格式/原生 DB 检查通过，每端 26 捕获、18 次预算恢复、22 次检查点恢复、预测提交/回滚各一次及 5 个拒绝例通过。稳定入口已更新。六个旧模型生成 C++ 和八个 runtime 头文件保持一致；103 原生编译选项由 `-O3 -xHost -ipo` 改为 `-O2 -xHost`，保留 strict FP，未重新测运行速度，生成代码一致不代表相同原生性能。详见 [M139 验收](../validation/m139-memory-cases/README.md)及[实现范围](memory-case-fixes.md)。

M138 接入[命名有限 sequence](named-sequences.md)：前向/嵌套引用、空括号调用、词法作用域和 generate 克隆绑定，复用有限阶段及既有采样/事务机制。五模型 VCS 对照和双端六组回归通过，Mac/103 Intel 稳定入口已更新；完整 SVA 与 class/UVM 等仍缺。

M137 接入[有限括号序列](sequence-groups.md)及整个子序列的固定连续重复，支持嵌套串接、参数计数和既有采样/取消/事务机制。整体仍限 256 阶段/65536 拍，双端八组回归和五模型 VCS 对照通过，稳定入口已更新；完整 SVA 等功能继续补齐。

M136 新增 [固定连续重复](sequence-repetition.md) `expr[*N]`，贯通单时钟 SVA 的直接序列/蕴含后件、参数化实例、采样和事务状态。零次/范围/无界重复仍明确拒绝；完整 SVA、clocking、class/UVM 等缺口继续补齐。

M135 修复生成过程 PC 指令边界预算耗尽后的过程丢失，支持继续运行及该边界状态的 checkpoint 恢复；函数内部和 callback 部分执行仍需先前有效 checkpoint。范围和检查见 [预算恢复](budget-resume.md)。继续补齐功能，不据此宣称完整恢复或完整 VCS 兼容。

M134 补齐 [package export](packages.md)：显式/两种通配形式、前置声明、多层/菱形转出与共享符号身份；四组 VCS 正例、258 个共同声明位及双端发布回归通过。显式 export 缺 import 的两类输入仍比 VCS 严格，边界详见 [验收](../validation/m134-package-exports/README.md)。继续以功能补齐为主，完整能力缺口见 [当前对照](vcs-comparison-current.md)。

M133 补齐[模块/interface 头部 package import](packages.md)，供参数默认值和 typedef 端口使用；普通模块 typed 端口保留 signed、二态、enum 和 packed aggregate 属性。覆盖参数覆盖、重复/generate 实例、共享包变量及 interface/modport，继续功能优先、速度优化后置；未宣称完整 SystemVerilog/VCS 兼容。

M132 修正[三目运算的四态合并](conditional-expressions.md)：未知条件下相同 Z 分支应合并为 X，标量与宽向量统一修复。当前按用户要求优先补齐功能，进一步速度优化后置；本批不发布新的 VCS 性能比。完整 SV/UVM、SVA、clocking/虚拟接口及门级时序等缺口仍以专题文档列出的范围为准。

M107 增加 [$fread 二进制输入](binary-io.md)，涵盖 packed、固定一维数组、切片、automatic/ref 和回滚；仍有明确语言子集及 VCS 波形差异。runtime 新增保留驱动状态的单驱动网直接发布路径。原始 perf-kit 完整工作量、默认 GCC O2 的固定基线/新版/VCS 重复测量及发布证据见 [M107](../validation/m107-runtime-binary-io/README.md)。

2026-10-26 最新对照见[当前摘要](vcs-comparison-current.md)。完整 SystemVerilog/UVM、时序和原生 DB 模型仍有缺口，不声称已经完整兼容 VCS。

M101 补入[final、模块类型bind及%m](cases-review-20261025.md)，修复原始cases中的传输观察器。支持自然结束/finish、结束波形和回滚，保留明确的语言子集边界。

M100 补齐 [字符串整数方法](string-integer.md)：四种整数解析、四种格式化和 putc，包含 automatic/ref、事件与回滚。两类 VCS 实测差异在文档中明确列出，尚不视为完全对齐。

M95 补齐[标量字符串子程序](strings.md)：字符串形参/返回值、默认与命名实参、output/inout 复制、automatic ref/const ref、重叠延迟、直接递归及函数表达式事件。七个同源模型与 VCS 的全部输出和 513 个共同物理位一致，三后端 46 份 VCD、4 次回滚和 11 个拒绝用例通过；完整 string/class/UVM 等仍有缺口。M93/M94 的报告复核见 [REPORT3](report3-review.md) 和 [REPORT4](report4-review.md)。

M92 统一未打包 struct 的二态成员存储转换，补齐切片/拼接/复合赋值、事件 NBA、赋值模式和子程序传参的组合行为，并修正信号重排后的聚合默认值。4 个同源模型与 VCS 的 TRACE 和 728 个共同物理位 settled 波形一致，见[unpacked 存储](unpacked-state.md)。这仍是固定整数成员子集，未声明完整 SV 支持或新增性能提升。

M91 修复混合 packed struct/union 成员写入的 X/Z 丢失，恢复原有聚合回归并新增嵌套、数组、宽向量、延迟 NBA 等组合检查，见[存储与视图](packed-storage.md)。不代表完整聚合类型或 SystemVerilog 兼容。

M87 新增 [固定周期 SVA 序列](sequence-delays.md)。当前仍不能替代完整 VCS：class/继承/多态、约束随机和完整 UVM、covergroup/覆盖率数据库、完整 SVA、虚拟接口/clocking、DPI/VPI 与交互调试等仍有较大缺口；常用 RTL、接口、类型、子程序和门级时序能力也仅在各功能文档列出的范围内验收。尚无覆盖完整语言标准的功能矩阵，不给出没有依据的“兼容百分比”。下文为逐批历史，当前边界以最新对应文档为准。

最新 M86 支持范围以 [complex 报告修复](complex-report-fixes.md) 为准：受限直接 automatic 递归/纯整数常量函数、过程块采样、整信号 force/release、整数成员 unpacked struct、写内存文件和参数/genvar 位选。M84 interface/modport 和 M85 断言采样函数也已接通；下方历史限制不代表这些能力仍完全缺失。完整 SV/VCS 功能仍未齐全。

M83 修复[v3 报告组合缺口](report-v3.md)：层次固定数组元素/动态索引及 enum/aggregate 读取、包内共享可变变量、`.vcd` 文件名自动选择文本输出。M82 已接通[单时钟并发 property](concurrent-assertions.md)，M81 已接通[基本动态字符串](strings.md)。interface/modport 由 M84 接通，完整 SVA 仍未完成；下方历史条目以最新功能文档为准。

M79 补入[基本随机系统函数](random-functions.md)、v2 报告中省略 input 的 named typedef ANSI 首组形参，以及缺失 top 的明确诊断；仍不等同完整随机约束/struct/SV 支持。

M78 优先修复[用户 RTL 报告问题](rtl-report-fixes.md)：无括号任务调用、常量次数复制、always_ff 初值、var 端口及受限层次读取；未完成项逐项列明。M77 新增[数组归约 with 映射](reduction-with.md)，支持默认/命名词法迭代变量、嵌套、固定/动态存储与延迟/NBA。验收见对应批次，均无新性能结论。

M74 接通 [SystemVerilog 赋值模式](assignment-patterns.md)：固定数组、packed 数组/struct、嵌套/default/常量重复、初始化及延迟 NBA；验收见 [M74](../validation/m74-assignment-patterns/README.md)。typed pattern、类型键、动态容器和完整 SV 验证环境仍缺，本批未测速。

M73 新增 [RTL 实例数组](instance-arrays.md)，包含模块及逻辑/三态原语数组、端口切分/广播和独立状态。前端 packed 多维、genvar 更新和顶层推断见 [M72](frontend-compatibility.md)。

M58 支持 [显式 static 局部声明](explicit-static.md)：automatic 子程序跨调用共享持久变量、数组和静态 event，接通一次初始化、NBA、波形、分区和回滚。

M57 增加 [显式 automatic 局部声明](explicit-automatic.md)，覆盖混合块、fork 入场捕获、静态任务的自动局部隔离、类型/数组默认值、事件等待和回滚；显式 static 覆盖后由 M58 补齐。

M56 增加 foreach 动态循环帧：重叠执行隔离、同次循环分支共享索引、任务返回后保活、末端索引推进和回滚。范围及验收见 [foreach fork](foreach-fork.md)。

M55 功能更新：[automatic 动态变量帧](automatic-fork.md) 接通重叠任务/过程块隔离、fork 共享父帧与返回后逃逸、订阅重绑定和回滚。保留一项 VCS W-2024.09 逃逸局部直接事件等待差异；不计为对齐。完整验证能力仍有缺口，未新增速度测量。

M54 补齐[静态存储 fork 分支的重叠激活](dynamic-fork.md)，含嵌套后代、事件等待、命名目标取消、进程槽复用和分配期间的回滚。M53 的 overlap 拒绝缺口已接通；automatic 动态变量帧与父帧逃逸仍缺。本批继续功能优先，未新测速。

M53 接通[join_any/join_none、wait/disable fork 的静态子集](fork-control.md)：首分支恢复、延后启动、直接子进程等待及后代取消。重叠激活和 automatic 父帧逃逸仍明确限制，详见 [M53](../validation/m53-fork-control/README.md)。下文早期批次缺口以最新对应功能文档为准，本批未测速。

M52 补入[命名块 disable 与并发取消](named-disable.md)，含 automatic task 多个活跃调用、旧唤醒隔离、关闭标签及回滚；范围和验收见 [M52](../validation/m52-named-disable/README.md)。M51 已支持 fork/join，M50 已支持非阻塞内部事件赋值。下文逐批说明保留历史边界，当前行为以对应最新批次为准。仍缺 join_any/join_none、disable/wait fork、动态进程及完整验证语言；近期功能批次未重新测速。

M49 接通[阻塞赋值内部事件控制](intra-event-assignments.md)：入口 RHS 取样、恢复后动态目标、repeat 次数、iff/表达式/命名事件、automatic task、并行与回滚；VCS 对照见 [M49](../validation/m49-intra-event-assignments/README.md)。非阻塞内部事件赋值、整体 unpacked 数组和隐式敏感控制仍拒绝，本批未测速。

M48 接通[条件命名事件](qualified-named-events.md)：静态 event 的 iff、混合列表、Active 条件取样、连续发生、晚进入等待隔离、NBA/延迟触发、并行与回滚；实际 VCS 对照见 [M48](../validation/m48-qualified-named-events/README.md)。事件对象/数组/ref、wait_order/fork、动态进程和完整事件区域仍缺，本批未测速。

M47 接通[自动函数事件表达式](function-events.md)：事件源/iff 中的无外部副作用 automatic 调用、嵌套私有局部写入、函数体全局依赖和入口取样；真实 VCS 对照见 [M47](../validation/m47-function-events/README.md)。static/外部副作用函数仍缺；静态命名事件 iff 后由 M48 接通，本批未测速。

M46 接通[条件事件控制](conditional-events.md)：iff 条件、分支优先级、四态真假、入口取样、guard 依赖分区与回滚，真实 VCS 对照见 [M46](../validation/m46-conditional-events/README.md)。M46 当时用户函数/副作用及命名事件直接加 iff 仍缺；automatic 函数子集后由 M47 接通，本批未测速。

M45 接通[表达式事件控制](event-expressions.md)：一般值变化、四态边沿、宽值、静态/动态选择、数组字与混合列表，覆盖子程序、线程和回滚。实际 VCS 五个共同源及原始入口/毛刺探针对照见 [M45](../validation/m45-event-expressions/README.md)；M45 当时尚缺事件表达式中的用户函数/副作用和 iff；后者的整数表达式子集由 M46 接通，本批未测速。

M44 接通[静态命名事件](named-events.md)：@event、->/->>、延迟 NBA 触发与 triggered 查询，包含子程序、分区依赖和回滚；真实 VCS 同源比较及查询基线探针见 [M44](../validation/m44-named-events/README.md)。事件句柄/数组/ref、wait_order/fork、动态进程和完整事件区域仍缺，本批未测速。

M43 接通[wait(condition)](level-wait.md) 和 function logic/reg 返回类型，覆盖立即继续、四态/宽字/数组条件、函数实参敏感性、automatic task、并行和回滚。实际 VCS 五个共同源全部 1120 直接位时间线及四原始探针对齐，见 [M43](../validation/m43-level-wait/README.md)。wait fork/wait_order、动态进程和完整事件区域仍缺，本批未测速。

M42接通[动态前缀子数组过程复制](array-copy.md)，支持动态多维读写、NBA源/目标地址取样、宽/越界/未知索引及两态默认值，并修复delay函数调用的parser误拒绝。普通用例与副作用原始边界分开核对，见 [M42](../validation/m42-dynamic-array-copy/README.md)。仍缺slice/数组模式/整体初始化/连续数组赋值/形参及动态容器，本批未测速。

M41 接通[静态数组整体过程赋值](array-copy.md)：逐维方向映射、常量子数组、阻塞/NBA、宽字、net 源、两态目标、函数/automatic任务与敏感依赖。整数组阻塞赋值内delay保留已观测的VCS差异，动态子数组/模式/连续数组赋值仍缺；验收见 [M41](../validation/m41-array-copy/README.md)，本批未测速。

M40 接通[静态 net 数组](net-arrays.md)，支持 wire/tri 多维数组、整数组/静态子数组 input/output/inout 及编译期电气合并。input 内部反向驱动、多驱动解析、悬空 Z、变量边界转换、延迟与回滚纳入实际 VCS 对照，证据见 [M40](../validation/m40-net-arrays/README.md)。变量 inout/ref、动态数组和数组形参仍缺，本批未测速。

M39 接通[静态变量数组端口](array-ports.md)，支持多维input/output、静态子数组、声明方向映射、同宽两态转换、delay/NBA和回滚，并修复宽数组元素延迟分类。一般net/复合类型数组端口、ref和数组形参仍缺；实际VCS范围见 [M39](../validation/m39-array-ports/README.md)，本轮未测速。

M38 接通[显式变量连续赋值](variable-assign.md)，覆盖静态目标、混合 net/变量拼接及单值惯性 delay；变量写入冲突改为区间扫描。实际 VCS 对照与无延迟重复左值差异见 [M38](../validation/m38-variable-assign/README.md)。动态连续左值、数组端口等仍缺，本轮未测速。

M37 接通 [模块输出到变量](variable-ports.md)，覆盖父级 logic/bit/整数、静态位段/数组字/成员、多层连接、混合/重复拼接、位区间驱动冲突、延迟 NBA 传播、线程及失败预测回放。实际 VCS 同源差分及边界探针见 [M37](../validation/m37-variable-ports/README.md)。M37 当时尚缺显式变量连续赋值/数组端口；前者已于 M38 接入，本批未测速。

M36 接通 [first/last/next/prev/num 枚举方法](enum-methods.md)，含常量查询、四态成员、步数回绕及数组/函数/delay/NBA/并行/回放；实际 VCS 验收及无类型 parameter、标签方法宽度查询和无 debug 函数接收者差异见 [M36](../validation/m36-enum-methods/README.md)。本批未测速。

M35 接通 [unique/unique0/priority 选择检查](selection-checks.md)，含报告排队、逐过程清理和推测回滚。六组实际 VCS 输入的 756 位时间线相同，但告警为 native 12 / VCS 15，三个差异及函数条件 IUC 探针另行保留，见 [M35](../validation/m35-selection-checks/README.md)。不宣称全部诊断或完整事件区域对齐；本批未测速。

M34 新增静态多维 unpacked 变量数组：逐维完整位宽/四态检查、固定步长寻址、多维 foreach/查询/inside、delay/NBA、automatic 局部数组及 packed 成员；六组同源实际 VCS 对照通过，1544 位直接导出时间线与 660 位数组观察时间线一致。范围见 [静态多维数组](multidim-arrays.md)，证据见 [M34](../validation/m34-multidim-arrays/README.md)。仍不支持动态数组、子数组值、数组端口/形参及多维 readmem。本批未重新测量速度。

截至 2026-10-21，dsim 尚未覆盖 VCS 主要功能，也未达到整体性能接近 VCS 的目标。以下记录项目自身实现范围，不是 VCS 产品功能或内部算法的完整描述。M22 冻结源码的同机 RTL 测量（M23–M42 功能更新后未重测）与历史门级/SDF数据分列于 [对照报告](../validation/current-vcs-comparison/README.md)。

当前可运行受支持子集的 RTL 功能仿真、带 delay 的 RTL 及 Liberty 门级/SDF 仿真，**不能当作 VCS 的完整替代品**。最新补入[foreach 静态数组遍历](foreach.md)，包括声明方向、多索引/跳过维度、只读自动索引、重叠任务隔离及回放，见 [M33](../validation/m33-foreach/README.md)。此前补入[集合匹配与通配相等](set-membership.md)，支持 inside、case inside、==?/!=?、四态范围/数组和常量展开，见 [M32](../validation/m32-set-membership/README.md)。此前补入[非递归 automatic 函数/任务](automatic-subroutines.md)，含每次入口初始化、跨 delay/event 的激活隔离、循环块生命周期、类型及挂起期间回滚，六例实际 VCS 全部1272条导出位时间线一致，见 [M31](../validation/m31-automatic-subroutines/README.md)。此前补入[默认与命名实参](call-arguments.md)，含空位默认、词法作用域、延时任务取样和 always 入口初始化事件对齐，验收见 [M30](../validation/m30-call-arguments/README.md)。此前补入[函数输出形参与副作用](function-effects.md)，支持 output/inout、void、语句及丢弃调用与外部阻塞写入，验收见 [M29](../validation/m29-function-effects/README.md)。此前补入[命名类型值参数和子程序签名](type-signatures.md)，支持 typedef/enum/packed 聚合的参数、函数返回和函数/task 形参；范围、名称对应及初始 dump 差异见 [M28](../validation/m28-type-signatures/README.md)。此前补入[静态数组查询与多控制位计数](array-queries.md)，覆盖动态维度、四态计数及参数展开，实际 VCS 边界与验收见 [M27](../validation/m27-array-queries/README.md)。此前补入[整数/位向量系统函数](system-functions.md)，支持位宽/地址计算、四态和 one-hot 检查；范围及保留的 VCS 差异见 [M26](../validation/m26-system-functions/README.md)。此前补入 [packed struct/union](packed-aggregates.md)，含成员/嵌套/数组字、符号/两态与 delay/NBA，范围和保留的 VCS 差异见 [M25](../validation/m25-packed-aggregates/README.md)。此前补入 [整数 enum](enums.md)，支持成员编号、名义类型身份、强类型赋值/cast、作用域/实例克隆及增减；尚缺枚举方法和类型端口，验收见 [M24](../validation/m24-enums/README.md)。此前补入 [命名整数类型](named-types.md)：typedef/别名链、作用域、参数化/generate 和命名 cast，静态子程序多语句体；已知 VCS 跨实例常量 cast 差异见 [M23](../validation/m23-named-types/README.md)。此前补入 [整数与尺寸 cast](explicit-casts.md)，接通内建整数转换、常量尺寸、参数与运行时语义，见 [M22](../validation/m22-explicit-casts/README.md)。此前补入 [SystemVerilog 立即断言与诊断](systemverilog-verification.md)：assert/assume/cover 条件及动作、标签、四态与单次求值、severity 系统任务，见 [M21](../validation/m21-immediate-assertions/README.md)。此前补入 [类型化值参数与常量上下文](typed-parameters.md)：整数/bit/logic/reg 参数默认值和实例覆盖、上下文宽度及符号/两态转换、常量宽除余和移位边界，修复 M19 的 parameter int/localparam int 入口退化；验收见 [M20](../validation/m20-typed-parameters/README.md)。此前补入 [两态整数与 bit](two-state-types.md)，含默认零值、逐位 X/Z 转 0、端口/静态子程序/数组/延迟 NBA，七例 87 捕获、3 次失败回放及实际 VCS 2709 条可观察位时间线通过，见 [M19](../validation/m19-two-state/README.md)。此前补入 [四态整数类型及端口](integral-types.md)，显式 integer signed/unsigned、64 位 time、模块端口和子程序结果/形参，七例 87 捕获、3 次失败回放及实际 VCS 3792 条可观察位时间线通过，见 [M18](../validation/m18-integral-types/README.md)。此前补入 [前置/后置增减表达式](increment-expressions.md)，支持短路、动态索引和 delay/NBA 取样，六例 75 捕获、3 次失败回放及实际 VCS 2166 条可观察位时间线通过，见 [M17](../validation/m17-increment-expressions/README.md)。此前补入 [十二种复合赋值与子程序 return](procedural-actions.md)，动态目标单次求值，任务提前返回仍复制 output/inout；五例 62 捕获、2 次失败预测回放和实际 VCS 2451 条可观察位时间线通过，见 [M16](../validation/m16-procedural-actions/README.md)。此前补入 [静态用户函数与任务](subroutines.md)：整数/signed/宽四态形参和函数返回值、静态状态、任务 output/inout、delay/event/NBA、嵌套调用，五例 62 捕获、2 次失败预测回放和实际 VCS 2187 条可观察位时间线通过，见 [M15](../validation/m15-subroutines/README.md)。此前补入 [过程循环控制](loop-control.md)：inline for 计数器、多赋值/空头部、语句增减及 break/continue，五例 62 捕获、2 次失败预测回放及实际 VCS 1082 可观察位对照通过，验收见 [M14](../validation/m14-loop-control/README.md)。此前补入 [integer/int 与过程静态局部变量](integer-and-locals.md)：32 位四态整数、命名/匿名词法作用域、局部变量/一维数组、同名遮蔽与跨 delay 保持；验收见 [M13](../validation/m13-integer/README.md)。此前补入 [signed packed 类型及常见运算](signed.md)：符号扩展、混合类型传播、signed 比较/除余、算术移位、`$signed/$unsigned`、负常量和十进制打印。六例本地 75 捕获、3 失败预测回放和独立 256 组算术穷举通过；实际 VCS 六例 3378 条可观察位时间线及 TRACE 相同，验收见 [M12](../validation/m12-signed/README.md)。此前已接通[一维存储器/文件初始化](memory.md)、[generate](generate.md)、[专用 always](always-procedures.md)、[动态 packed 选择](indexed-selects.md)。

尚缺能力可按使用场景判断：普通 RTL 仍受完整类型参数/整数端口、复合赋值表达式返回值、完整常量求值/命名及复合类型 cast、子数组/端口/整体数组操作、递归/常量函数/完整子程序和层次引用限制；RTL testbench 还缺通用文件操作、完整运行时字符串操作、丰富系统任务、完整并发 SVA/覆盖数据库、DPI/VPI；标准单元 Verilog 模型还缺 UDP/完整 specify/强度；精确时序仿真还缺完整 SDF/timing checks/notifier、负检查延迟信号及完整脉冲语义。完整 SystemVerilog 的接口/class/随机化/UVM 和完整事件区调度未实现。SPEF 只有解析，没有 RC 仿真。

| 范围 | 当前状态 | 下一步验收 |
|---|---|---|
| 编译执行 | RTL/门级分别解析，共同生成本机 C++ 可执行模型 | 实际 RTL/门级设计 |
| RTL | [阻塞内部事件赋值](intra-event-assignments.md)；[条件命名事件](qualified-named-events.md)；[自动函数事件表达式](function-events.md)；[条件事件控制](conditional-events.md)；[表达式事件控制](event-expressions.md)；[静态命名事件](named-events.md)；[电平条件等待](level-wait.md)；[静态多维数组](multidim-arrays.md)；[foreach](foreach.md)；[集合匹配](set-membership.md)；[automatic 子程序](automatic-subroutines.md)；[静态数组查询/countbits](array-queries.md)；[整数/位向量系统函数](system-functions.md)；[packed struct/union](packed-aggregates.md)；[整数 enum](enums.md)；[命名整数 typedef](named-types.md)；[整数/尺寸 cast](explicit-casts.md)；[立即断言/诊断](systemverilog-verification.md)；[类型化值参数](typed-parameters.md)；[两态整数/bit](two-state-types.md)；[integer/time 类型及端口](integral-types.md)；[复合赋值/子程序 return](procedural-actions.md)；[静态用户函数/任务](subroutines.md)；[过程循环控制](loop-control.md)；[integer/int 与过程静态局部变量](integer-and-locals.md)；[signed packed 类型/运算](signed.md)；[一维存储器/文件初始化](memory.md)；[generate](generate.md) 的条件/循环展开及局部作用域；动态 packed 位/固定宽度部分选择；1–1,048,576 位无符号多字四态、层次/参数、常见控制流、端口/选择/拼接、预处理/文件列表；常量及运行时整数表达式过程 delay、采样式阻塞内部 delay、表达式延时 NBA、连续赋值/标量原语 delay、三态原语及事件回滚；运行时表达式延迟本批通过本地及Linux定向回归、新VCS两例145物理位对照；[原语有名/无名/混合实例分组](../validation/m4-primitive-groups/README.md)已通过本地及Linux六项定向/新VCS验收 | 无赋值 net delay、动态连续赋值/原语 delay、完整类型参数/整数端口、完整常量求值/命名及复合类型 cast、子数组/端口/整体数组操作、递归/常量函数/完整子程序、完整层次引用 |
| 门级 | 独立紧凑结构前端；门级预处理/结构scope时间；原始宽端口与内部宽连接；Liberty 组合、三态、理想 ff/latch；有限编译式 IOPATH | 标准单元 Verilog/UDP 功能体、完整时序 |
| 事件内核 | 确定性的 Active/Inactive/NBA、稳定定时队列、边沿/多驱动、模块 timescale；可选可回滚延时驱动通道；实验性近时间队列接入实际 CLI、两平台各83项/六类VCS流程/全量SDF通过，默认关闭 | 近时间队列/SDF专用作业性能验证、完整脉冲/取消语义 |
| SDF | 独立流式 parser、严格端点/事件身份绑定；独立模型准备工具与条件直接别名；原始完整真实 SDF 的 IOPATH/INTERCONNECT/常用检查已实际执行，128笔输出匹配新VCS，默认非负检查模式；有限条件路径/ifnone执行已接入，432源两平台各92项/九类新VCS各三次及回滚验收通过 | 一般条件表达式、完整脉冲语义、一般模型等价与primitive DEVICE、完整 timing checks/notifier、负检查延迟数据；部分零覆盖增量读回与复杂模型常量表达式 |
| 预测/回滚 | 检查点、PC/队列/驱动/ff 状态恢复、预测失败重放、打印/波形事务已实现 | 自动预测器、增量状态日志、跨分区回滚与成本测量 |
| 并行仿真 | 常驻线程池、正延迟通道/保守 lookahead；图自动分区与内核安装 API；gate-only 分析；全局结束回滚和单文件波形；实验性 [--threads 普通 RTL 独立域代码生成](automatic-parallel.md)，472两平台51程序/新VCS三例通过；473单分区串行回退和无finish快照消减本地54程序/306捕获通过、Linux三项及原始全量代码身份已通过 | gate scope内部与IOPATH安全切边、dump tasks并行接入、真实收益 |
| 波形 | 原生 C++ VCD/DWF，含多字 plane/XOR 编码、块 Zstd 压缩、checkpoint/索引/CRC 和中断后的完整前缀恢复；native 完整事件流式比较接入统一流程；并行API窗口提交后全局VCD/DWF归并，两平台定向流验证通过；有界异步压缩及统一清单控制，两平台各105项及新流程验证通过；[dump任务](wave-dump-tasks.md)自动启用后端，148份本地捕获/54份事务捕获及219个VCS物理位对照通过 | dump任务Linux完整回归及更广控制排列/同刻瞬态对照、异步压缩性能验收、百万信号分组检查点/索引、VCS 位比较流式化 |
| 调试/验证接口 | 立即断言/severity 诊断、单时钟并发 property 子集、可检查 C++/IR、VCS 差分脚本 | 完整 SVA/覆盖数据库、DPI/VPI、通用文件激励，分批实现 |
| SV/UVM | 未实现完整支持 | 依赖语言/对象模型/随机化等单独规划 |
| 性能 | 单驱动内联、状态输出消除、alias 缓存、共享编译进程、固定反相/敏感列表、内部网紧凑/合并驱动及小型输出四态查找表；真实基准逐轮保留，尚无整体 VCS 对齐结论 | 表达式复杂度筛选、常量传播、通知/队列与完整 Liberty 成本，再评估并行 |

最新无波形 SDF 默认启用全零输入通道折叠和标量时序后端，二叉定时堆保持默认。完整原始 SDF 已执行 128 输出对照，但这不是任意 SDF/单元模型的兼容证明。最近同轮完整 SDF 短测 native/VCS CPU 中位数为 69.415/9.055s，约 **7.67 倍**；不是 RTL 速度比，也不是本轮语言功能补全的新测速。内部自动并行、自动预测与增量回滚仍不完整；已有手工 API 不代表自动加速已实现。

当前多字后端的支持与验证见[多字值说明](multiword-values.md)及[验收记录](../validation/m4-wide-values/README.md)。手工并行通道支持宽值，不代表已实现自动分区；宽值回滚支持不代表已实现自动预测器。

最新常量延时 NBA 的范围与最终验收状态见[时间语义](time-semantics.md)及[独立记录](../validation/m4-delayed-nba/README.md)。连续 delay 新增默认 VCS/显式 IEEE 选择模式及 packed 声明延时，修正版两平台各72项、12组新VCS各三次和完整流程已验收。SDF 紧凑接收端已默认采用；后继标量交付选项通过两平台各64项及真实完整SDF的128输出核对，首轮五对 CPU 配对耗时下降中位数14.05%，独立五对复测也已核对PASS（配对中位数14.63%），组合源码接入验收尚待完成、默认仍关闭，见[标量交付](../validation/m5-scalar-timing/README.md)。[近时间队列](time-queue.md)已接入实际CLI，427源本地完整83项/原始全SDF运行128笔通过；Linux完整83项、六类VCS流程及两个全量新生成程序各128笔已独立核对PASS，无队列性能结论。新增默认关闭的[SDF专用作业](sdf-jobs.md)及边沿/ifnone修正已通过432组合源本地完整92项及实际生成回放sanitizer，Linux同源92项、新VCS九类各三次/选择时刻探针、六公共流程及实际新编译器全SDF两作业后端各128笔已正常结束并独立核对PASS，见[组合验收](../validation/m5-sdf-jobs/verification.json)。

[全局波形归并](parallel-and-rollback.md#单文件全局压缩波形)最终435源通过本地完整94项和两种实际后端ASan/UBSan；252常规+252 sanitizer捕获独立核对PASS，包含部分挂接异常清理。后继442相同runtime/wave头及测试在Linux通过两项定向验证，252份完整捕获按独立模型及435源macOS记录重算一致。再后继446的Linux完整100项也已结束并独立核对PASS，252份全局流与上述Linux捕获完整一致，见[集成核对](../validation/m4-sdf-device-state/linux-verification.json)；不代表Linux sanitizer或普通网表自动并行接入。

[PORT/DEVICE实际回标](../validation/m4-sdf-port-device/README.md)：437源新VCS共32组，26组各三次通过，6组有差异，原始证据保留。443修正多驱动PORT的MAXIMUM，446修正DEVICE/IOPATH交错读改，分别通过六组新VCS各三次和18组新VCS各三次及native完整流。[450模型身份修正](../validation/m4-sdf-model-alias/README.md)进一步扩展相同token定义、相同时间单位/精度的叶模型通配范围，21组新VCS各三次、三native后端378捕获及绑定边界检查通过。原32配置重新对照84份原始VCS波形全部通过；112个未变程序以450整个CPP身份复用446实跑捕获，16个改变程序实际由450编译执行。原六项失败不回写为旧源PASS。一般模型等价、没有module path的primitive DEVICE及完整脉冲等仍未支持，450 Linux六项受影响CTest、522份跨平台捕获及原始全量SDF两版完整代码身份已独立核对通过，不代表完整102项。

以下为逐批历史记录，较新批次覆盖早期功能边界。

0.7.0 的 10 万 ff 反馈网络 CPU 中位数为 native 13.44s、VCS 6.03s；这不能代表总体性能。历史数据见 [时序单元验证](../validation/m3-sequential/README.md)。

仿真检查点与波形块检查点不同：后者只保存记录值，不能恢复进程 PC、事件队列或门级内部状态。预测/回滚的设计是待验证的 dsim 方案；[VCS 实验报告快照](../validation/m2-preprocessor/vcs1017-reference.md) 没有提供 VCS 使用该算法的证据。

0.10.0 的 RTL delay、`$time` / `%t` 与生成模型的 VCD/DWF 已使用共同物理时间轴，详见 [时间语义](time-semantics.md)。SDF parser 的换算函数已复用，但实际回标仍未实现。

0.11.0 的绑定不会执行条件、合并重复路径或施加延迟，数值预览使用显式指定的统一精度；未来回标还须按 cell model 的精度舍入。接口见 [SDF 绑定](sdf-binding.md)。

0.12.0 优化当前零延迟模型，未改变 SDF 仍无实际回标的边界。证明条件与数据见 [性能优化](simulation-optimization.md)。

0.13.0 的真实设计测量与边界见 [固定敏感列表验收](../validation/m5-fixed-wait/README.md)，不与历史不同轮次的 VCS 分母混算。新增[延时驱动通道](delayed-drivers.md)只完成可回滚事件基础；`--sdf-bind-check` 仍不施加延迟，尚无 native `--sdf` 自动注解入口。

最新重复驱动候选已撤回，生产运行时与上一批相同。原版/VCS 14.32/10.29s 的约 1.39 倍是重测结果，不能把与上轮 1.60 倍的变化归因于优化；候选五次复测反而变慢，详见[完整数据](../validation/m5-redundant-drive/README.md)。正确性新增一项行为回归，完整功能目标仍在进行。

标量两版候选的正确性均通过，但配对收益未复现；第二版真实 CPU 13.20→14.48s、反馈 5.37→6.90s，已逐字恢复生产源。首轮看似接近 VCS 的数据不作为采用结论，见 [完整证据](../validation/m5-scalar-logic/README.md)。后继 [紧凑信号/驱动存储](compact-gate-storage-plan.md) 第一版两平台正确性通过，但真实配对 CPU 仅减少 0.76%，已恢复已验收后端；内存下降约 17%，不能作为已解决性能差距的结论。后继合并写入版本已验收采用。

最新已采用后端的真实五次配对 CPU 13.59→11.33s（-16.63%），同轮主实验 B/VCS 为 11.90/9.15s，约 1.30 倍；无 SDF/波形/并行，仍无总体接近 VCS 的结论。完整 [验收](../validation/m5-compact-drive/README.md)。SDF 原始数值绑定与精确暂存层的对接测试通过两平台，仍未施加实际路径延迟。

最新四态查找表版本：真实设计独立七对CPU配对收益中位数3.86%，6/7改善；反馈慢1.23%。实际编译器新同轮原版/LUT/VCS CPU为10.11/9.64/7.76s，约1.24倍（无SDF/波形、单核），两平台各30项通过。详见[查找表边界](gate-four-state-lut.md)。SDF已按新VCS参考更正目标精度舍入/夹零策略；54组受支持文件集成微例通过、4组明确拒绝，仍无一般CLI回标。

最新编译式 SDF 入口为 [`--sdf-annotate`](sdf-runtime.md)，无条件路径的输入沿历史、输出驱动和待交付事件已接入检查点；并非完整 SDF/时序检查实现。紧凑网直接编码读取试验真实配对收益中位数 0%，未采用，见 [原始证据](../validation/m5-scalar-read/README.md)。性能主线继续，不能将该试验或功能新增称为提速。

门级预处理新增独立快速扫描与宏/include后备，保持RTL/gate parser分开；本地/Linux各39项、4组新VCS时间参考与实际ASan/UBSan联合SDF/回放通过。完整真实模型和11份SDF程序生成C++相同，runtime未改，无新提速声明。13原始互连网表已从网表头失败推进到明确的INTERCONNECT运行时拒绝，仍未支持该运行时。见[门级预处理](gate-preprocessing.md)。

最新功能批次已把逐接收输入INTERCONNECT编译进实际程序，与IOPATH、VCD/DWF及已有检查点联合使用；本地/Linux各41项、29组VCS参考及4组实际回滚/提交检查通过，两个生成程序ASan/UBSan通过。原13+16参考研究的“尚未支持”描述属于历史状态。具体范围见[sdf-runtime.md](sdf-runtime.md)；真实全量SDF仍有缺口，手工预测API不等于自动预测器。统一[工具流程](tool-flow.md)新增同一清单的RTL/门级/SDF编译、三种波形模式、阶段CPU/RSS和可选VCS差分，不据单次小例时长更新VCS性能比例。

最新多字后端已通过原始256/257位接口的真实128笔新VCS对照；全量SDF严格入口首个实际阻塞为HOLD运行时检查，未关闭检查。下一整体时序里程碑以SETUP/HOLD等检查和条件路径为主，不把零延迟兼容当全量时序成功。详见[宽接口验收](../validation/m4-wide-values/README.md)。

最新九类编译式时序检查通过两平台各49项、21组完整VCS警告流及联合互连/路径/回滚检查；真实原始SDF当前停在占位模型HOLD事件身份不匹配。负值默认夹零、完整notifier/负检查延迟信号和条件路径边界详见[timing-checks.md](timing-checks.md)。本批没有新性能比或自动并行收益声明。

后续[模型准备与 RTL delay 批次](../validation/m4-sdf-model-preparation/README.md)已解除上述真实模型身份阻塞：原始300,909单元全量SDF实际编译运行，128输出匹配同一生成模型的新VCS。覆盖867,982 IOPATH、790,222 INTERCONNECT、86,496检查；17,124条条件项属于检查事件。23,051次负limit更新在默认模式夹零，VCS亦报告相同数量的NNTC注解错误，不能称零错误注解或负检查模式成功。原始SDF未删项，检查未关闭；一般条件IOPATH等仍待补齐。

默认关闭的[零输入延迟通道折叠](../validation/m5-zero-input-fold/README.md)已接入实际CLI；九场景/三后端162份完整捕获、192次VCS物理位对照及24普通+24本地sanitizer回滚捕获通过。原始全量SDF两后端各128输出已通过；scalar/jobs候选六轮配对CPU改善中位数35.39%，同轮51.935s/VCS7.01s（7.41倍），默认仍关闭且独立复测待做。默认通用后端六轮测速已审计PASS：128.49/79.70s，同轮VCS10.875s，默认/折叠耗时比分别11.82/7.33，配对改善38.62%；仍默认关闭，独立复测及采用验收待做。ABS写零保留既有MIPD已修正；顶层input非零重复ABS使用MAXIMUM的新修正通过12例本地216捕获，Linux五项定向CTest及248跨平台捕获已独立验收，见[新增范围](../validation/m4-sdf-root-input/README.md)。

## 动态 packed 选择（2026-10-18）

RTL 编译器支持运行时位选择以及固定宽度 `+:`/`-:` 的读取、过程目标和模块输入表达式；索引进入敏感列表/自动并行依赖。NBA及延迟NBA在入口采样目标，阻塞内部延迟在恢复时计算目标；宽四态和部分越界处理接入现有回滚。输出/inout动态适配和连续动态左值仍明确拒绝，普通范围两端仍须常量。超宽索引高位非零的VCS差异单独保留，不宣称全部兼容。见[功能边界](indexed-selects.md)。

最终二叉版本的Linux动态选择/时序检查/普通RTL三类流程通过；新功能三个用例共558物理位时间线与实际VCS一致，本地50捕获/7拒绝/2回放通过。超宽高位索引和同Active立即读取组合wire的探针差异均保留。4/8叉堆候选两轮收益不稳定，默认继续二叉；直接检查查表不宣称整体稳定收益。完整SDF同轮二叉查表/VCS CPU中位数69.415/9.055s，约7.67倍；这不是RTL速度或完整功能等价结论。完整代码及GCC预处理身份复用两次实际128笔执行，见[最终记录](../validation/m9-timers-selects/README.md)。

M79：报告 B4 的基本 `$random`/`$urandom`/`$urandom_range` 已接入编译、过程 RNG、fork 层次播种与 checkpoint；支持范围、实际对照和未对齐的零种子/具体序列见 [随机函数](random-functions.md)。不包含 class constraint/randomize 或完整随机稳定性。

M80：报告 B2 原始 package/enum/function 用例已接通。新增独立包符号表、显式/通配导入、qualified 类型/常量/调用、包内 subroutine 词法绑定与共享静态局部、包时标/精度；当时[支持范围](packages.md)排除 mutable 包全局（M83 已接通）、export/class、header/compilation-unit import 等。运行时不变，不据功能微例更新 VCS 速度比例。

M103 新增 [通用文本文件 I/O](file-io.md)，包括 fopen/fclose、fwrite/fdisplay/fflush、fgetc/ungetc/fgets/feof/ftell/fseek/rewind。扫描格式、fread/ferror、交互输入和完整格式族仍有缺口；普通文件的字节内容、游标和外部写入纳入预测事务。
