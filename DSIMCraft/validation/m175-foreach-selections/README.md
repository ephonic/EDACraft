# M175：foreach 下标接收者、子数组与 cursor 求值

实现范围与边界见 [foreach 下标接收者](../../docs/foreach-selections.md)。
语法通过保留待判定的最后一组方括号区分接收者选择与迭代变量，
保持86个 shift/reduce 冲突，没有新增 reduce/reduce 冲突。
最终迭代变量严格检查为标识符或省略位置；先前下标要求一个表达式。
独立RTL parser贯通绑定、类/模块参数化克隆和清理，不改门级parser。

六个原生执行模型覆盖固定/动态/队列中的类句柄、嵌套foreach与多层成员、
整数/字符串关联属性、剩余子数组维度和省略维度、parameterized/automatic调用，
以及break/continue、带延时的接收者变更和预测回滚。
110捕获、8拒绝、一次预测回滚/一次提交通过；VCD/同步和异步DWF，
ordered/settled与三个后端请求的观测相同，异步字节相同。
用户范围限定top.observed和时间2到3得到3/9，恢复后的完整时间线相符。
后端请求通过不代表每个模型实际被划为多个分区。
旧foreach-receivers组三模型56捕获/3拒绝/一次回滚一次提交也通过。

首轮selected模型假设接收者仅在入口求值，VCS实际运行失败，保留vcs-initial.json。
额外VCS探针receiver-evaluation.sv显示first/next三次求值，
接收者下标状态变化会把后续cursor切换到新对象。
修复原有生成器缓存入口对象的逻辑；最终selected应为calls=3/observed=14，
带延时的suspended模型为calls=4/observed=14/time=3。
诊断探针中的function内$display仅在VCS运行，dsim仍拒绝此类系统任务；
正常六模型不依赖此打印探针，直接断言副作用次数、遍历结果与时间。

VCS六个完全相同的最终源码实际运行、完成TRACE一致，八个负例同样拒绝；见vcs.json。
完整parser含六轮新参数化绑定/清理检查通过。
未修改公开Accellera UVM 2020.3.1的正常/ASan预处理仍为1888084字节/166依赖及原SHA，
语法首错从phase:1551推进到phase_hopper:562的9200s；完整UVM尚未编译运行。
该结果不证明尚未进入的整个库语义检查已通过。
时间常量、类句柄关联键、完整随机化、IPC、virtual interface/clocking、coverage等继续。

ASan/UBSan覆盖完整parser、六前端/八拒绝、六生成模型及预测回放，通过；
生成CPP和完整异步波形与正常构建逐字节相同，不包含LSan或新TSan验收。
本地M175冻结2d99736e，七组818捕获与mandatory检查通过，1157发布输入绑定相符。
新增19CPP/110捕获与开发证据逐字节一致，已更新稳定入口。
实际入口六模型CPP/完整异步波形、所选范围3/9及原始q02/q13自动top复验通过，
公开UVM实际入口仍在上述时间常量拒绝。103 Intel同样通过七组818捕获与mandatory，
1157输入绑定相符，新19CPP/110捕获与Mac发布结果逐字节一致。
root/bin稳定入口已更新，实际入口六模型的CPP/完整异步波形与候选相符，所选范围3/9复验通过。
冻结源码及输入、实际入口结果见mac-stage/source-binding/activation/entry.json、linux-activation.json。
没有本批性能结论，没有用编译接收性代替VCS实际运行。
