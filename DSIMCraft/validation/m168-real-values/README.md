# M168：实数值链路与异步范围波形

参考 REPORT-GAP/GAP2，继续消除未修改公开 UVM 的实际语言阻塞。
实现范围与用户用法见 [实数执行](../../docs/real-values.md)。
RTL 与 gate parser 保持独立，修改涉及 RTL 类型/常量、IR/运行时、浮点 DPI 和波形。

开发最终 `dev/final3` 九模型164捕获、16非法用法拒绝通过。
包含实际双分区、一次预测回滚/一次提交、范围过滤、NaN载荷/无穷/负零、
单精度与整数比较、宽有符号转换及常量/运行时四态逻辑。
`dev/final2-ctest.log` 的 timing、intra-assignment、完整parser、集成parser和原生DB五项通过。
旧延迟NBA和动态延迟回归也通过。

ASan/UBSan 覆盖完整parser、九前端、16拒绝例、九生成程序和实际预测replay，
全部异步输出与正常执行一致；DPI C库也被instrument，生成程序只有该库路径替换。
TSan 覆盖实际双分区实数程序与独立writer，输出和正常程序逐字节一致。
不作LSan、全部RTL回归或性能声明。

开发失败收据保留：最初负例诊断预期陈旧、DPI header include路径遗漏、
把有全局打印/finish的串行回退例误当两分区；均修正测试预期并重新执行。
新增实数时间fixture最初缺少end/endmodule分隔符，修正后执行通过。
旧 intra-assignment 事件控制拒绝项在M167已经被接受，改为实际验证等待前采样RHS。
位拼接的直接未定宽整数常量现按通用表达式路径拒绝，显式定宽拼接延迟执行通过。
不把这些测试修正算作新增语义。

原始公开 Accellera UVM 2020.3.1 预处理1888084字节/166依赖/原SHA；
普通与ASan native编译均仍在printer:1773的 `string'(...)` 转换处拒绝。
完整UVM仍未编译运行，字符串转换、约束随机、IPC、virtual interface/clocking、
coverage等目标继续。后续发布和VCS/Intel结果必须以相应收据为准。

首次VCS对照八模型通过，arithmetic因错误使用 `$bits(real/shortreal)` 被拒绝；
修正DSIM的非bit-stream实数查询检查，改正正例并补四个拒绝例，完整九模型和16拒绝边界重新验证。

本地最终版已冻结为 b2eed7ec 并推送，稳定入口激活到
`20261029T101646273860Z-97b7c2e80cc7`；六组824捕获、mandatory checks、
原始 r02 省略 --top 执行和实际入口完整/所选波形复核通过。
源码2113成员、1099发布输入、28生成程序及164捕获的绑定见相应收据。
九模型VCS执行一致；13拒绝边界一致，另3例VCS接受而DSIM仍拒绝，
其中动态实数数组为有效但未实现功能。六模型导出的16个实数声明、38次采样匹配；
另三模型零时刻结束未产生VCS波形，不能据此推断波形已验证。

103 Intel 首次六组中五组实际通过，DPI C fixture 因缺少 GNU 特性宏失败；
补宏重试后，模型运行暴露Linux错误使用macOS链接选项的问题：
链接器把 `-export_dynamic` 当作 `-e xport_dynamic`，入口错误，GDB在首个signal分配处捕获SIGSEGV。
失败候选未激活，原始冻结源码未改；两次失败收据保留。
M169在生产CLI和原生回放编译中按平台区分导出选项，修复后需要新候选重新验收。
