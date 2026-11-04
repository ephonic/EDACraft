# M174：实例整数约束随机化执行

支持范围与未完成项见[约束随机化](../../docs/constraint-randomization.md)。
RTL parser 保留 rand 元数据和独立的命名约束 AST，特化克隆及前向属性绑定检查通过；
生成模型使用真正的 Z3 位向量 SAT/UNSAT 求解，不使用有次数上限的随机试探代替无解判断。

六模型110捕获、28个前端拒绝、一个 X/Z 状态运行时错误、一次预测回滚/一次提交通过。
覆盖多变量与64位稀有精确解、signed/96位、继承/同名约束替换、基类句柄动态调用、
内联约束/调用作用域、参数化、pre/post回调、无解不写回、独立对象种子、
整体/个别rand_mode和constraint_mode、automatic作用域随机化及无参数约束检查。
`randomize` 在 Verilog 模式保留为用户函数名，生成程序不链接求解器。
VCD/同步与异步DWF、ordered/settled、三个后端请求的观测一致，异步字节相同；
所选波形限定top.observed及时间2到3，回滚后保留完整随机输出时间线。
不据此声称所有约束模型均实际并行执行。

完整 RTL parser（含六轮约束特化/绑定/清理）、格式parser及原生Liberty DB通过。
ASan/UBSan覆盖完整parser、六前端/28拒绝、Verilog前端、六生成程序、回放及运行时拒绝；
正常与sanitizer生成CPP/异步波形相符。不包含LSan、新TSan或第三方Z3库内部插桩。
旧const组74捕获/11拒绝/1运行时拒绝、random-functions组31捕获/4回滚/12拒绝通过。

VCS六个相同正例源码均实际运行并到达相同完成TRACE，源码SHA与当前fixture相符。
比较合法解和失败行为，不比较随机数序列，也没有均匀分布或性能声明。
27项编译接收性对照中17项同样拒绝，10项VCS能编译而原生拒绝；
包括尚缺的randc/数组/对象/static/soft/dist，以及const、重复实参、只读实参、
非rand属性模式等接收差异。VCS能编译不证明其运行行为或该写法的标准合法性。
新增四态等式拒绝有原生证据，尚未包含在这27项VCS对照中。
首轮VCS测试发现fixture错误地把pre/post声明为virtual；修正为普通函数后重跑通过，
原始失败摘要保留为vcs-initial.json，原生也新增拒绝错误回调声明的检查。

原始REPORT-GAP2的q02/q13没有改写，已编译执行通过，见original.json。
19个同源探针重新前端检查为11生成/8拒绝；不能计作11个全部原生运行。
未修改公开Accellera UVM 2020.3.1普通/ASan预处理仍1888084字节/166依赖/原SHA，
native仍在phase:1551的数组元素foreach路径拒绝，完整UVM不能编译运行。
randc/分布与优先约束、随机复合数据、IPC、virtual interface/clocking、coverage等仍待补齐。

本地稳定入口已更新为冻结91cc686e的M174，七组选定回归728捕获及mandatory检查通过。
1148个发布输入与冻结源码相符，21份新增CPP和110个新捕获与开发证据逐字节一致。
实际稳定入口六个模型的CPP和完整异步波形再次与发布候选相符，所选范围波形正确，
原始q02/q13不指定top也编译执行成功；见mac-stage/source-binding/activation/entry.json。
公开UVM实际稳定入口仍在phase:1551拒绝。
103已构建静态Z3 4.15.4，M174 Intel七组728捕获与mandatory通过，
1148发布输入与冻结源相符，root/bin两个实际入口已更新，六模型CPP/完整异步波形和所选范围复验通过，
见linux-dependency.json与linux-activation.json。
整个REPORT/UVM目标继续。
