# M169：字符串转换、参数和跨平台 DPI 链接

实现见 [字符串转换](../../docs/string-casts.md)，不改变 RTL/gate parser 分离。
开发五模型三种调度请求、VCD/同步与异步 DWF 共92捕获、一次预测回滚/一次提交、
用户指定信号及时间范围通过，十个拒绝边界通过。未声称全部模型实际双分区。
旧字符串子程序46捕获/四回滚通过；原 typedef string 参数拒绝项被本批执行正例替代。
DPI六模型110捕获、二回滚/一提交、23编译拒绝与五运行时拒绝通过。
完整parser、格式parser、原生DB通过。最终ASan/UBSan覆盖完整parser、五前端/十拒绝、
五生成程序及预测回放，程序和异步波形与正常证据相同；不作LSan声明。
旧字符串组31捕获/四回滚/25拒绝最终重跑通过。发布仍待冻结候选验收。

最终五个原样执行fixture与VCS输出一致。十个拒绝边界中五个VCS拒绝，
另五个VCS接受而DSIM尚拒绝：类句柄字符串转换、字符串到数值参数、隐式整数字符串参数、
混合字符串/整数比较及条件表达式；需要继续判断标准边界并补齐实际合法能力。
首次VCS发现动态字符串$bits不能用于常量参数，已修正并重新对照；
未知条件下字符串相同分支保留该值，不同分支返回空串。

公开Accellera UVM 2020.3.1 未修改，预处理1888084字节/166依赖/原SHA，
native首错推进到callback:1141的unique(...) with(...)。完整UVM仍不能编译运行；
约束随机、IPC、virtual interface/clocking、coverage等原目标继续。

M168在103的冻结Intel候选五组通过，但DPI测试依次暴露GNU C特性宏缺失、
CLI错误使用Darwin链接选项：GNU ld把-export_dynamic解析为-e xport_dynamic，
没有进入main，首个signal分配处SIGSEGV。旧候选未激活；本批生产CLI、
测试C库和原生回放命令均按平台修正。Mac验证不能代替Linux验证，需新候选验收。

历史失败日志保留：最初缺类型别名参数支持、测试调用不支持的模块层次函数、
仅含字符串的fixture没有数值波形信号、动态$bits常量假设和字符串旧诊断。
对应修正与重跑分开保留；第一次sanitizer-final在依赖回归尚未PASS时触发前置断言，
未执行sanitizer程序，不能据此声明验收通过。无本批速度或完整SV/UVM声明。

M169已冻结0c1dfd68并推送：2156源码成员/1107发布输入，七组916捕获和mandatory全部通过。
Mac稳定20261029T110437789351Z-d0156ae37d64已激活，16CPP/92新增捕获逐字节绑定，
实际入口五模型、所选异步波形、原始r02省略--top和公开UVM首错复核通过。
103的新Intel候选20261029T110700Z-0c1dfd6已编译，mandatory通过，七组回归仍在运行，尚未激活。

103最终Intel验收完成：七组916捕获、parser/格式parser/原生DB以及timing通过。五个模型经实际bin入口重编译与完整/所选异步波形复核通过，根目录dsim入口统一指向bin/dsim；两者解析到20261029T110700Z-0c1dfd6/dsim，SHA 43f3517b39ee7cae900ff71bbaa5310b511d9e70d727d3d496fad8d55ceb80f6。旧M168两次失败候选仍未激活。linux-stage/activation/entry收据保留分阶段状态。
