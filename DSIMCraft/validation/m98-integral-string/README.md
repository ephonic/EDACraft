# M98 整数循环与字符串能力

无挂起、直线标量赋值循环可生成uint64_t本机代码，支持受验收的加减乘、位操作、比较及逻辑操作，保留位宽截断和signed上下文。不是针对LCG常数的代数特化。X/Z、net/别名、订阅、force、混合状态、动态激活或特殊观察状态回退原PC路径；波形构建仍回退原路径。整轮预算预留，不能完整执行时交还原PC，保持失败步骤和状态；本机局部值在边界提交，均由Sim检查点保存。

补齐string精确case（含unique/priority）、字符索引读及无时序阻塞写，覆盖typedef/ref/const ref、未知/越界/零字节处理及索引副作用；修复字符串声明初始化多唤醒一次always事件的问题。字符串casez/casex、字符NBA/复合更新、字符串数组等仍有明确边界。

6个整数/4个字符串同源模型与VCS全部输出及866物理位settled时间线一致，无单边未比较位。三后端60份标准VCD、10次预测失败回滚；98组有限循环精确预算/状态对照，加20组无限循环边界。10份实际生成程序ASan/UBSan通过；被测C++哈希与本机回归程序相同。原有strings、string_subroutines、increment_expressions、comb_sensitivity、function_effects及REPORT5受影响回归通过。旧increment_expressions的局部更新负例已过时：原稳定版本也接受该合法输入，因此移除其错误拒绝预期；不收紧编译器合法语义。

103同机CPU0，无波形/覆盖/调试，单线程，预热一次再三工具交替三轮。CPU中位数：

| 工作负载 | 原稳定版 | 候选版 | VCS | 候选/VCS |
|---|---:|---:|---:|---:|
| 十亿次整数LCG |20.24s|1.52s|1.67s|0.910|
| 三千万时钟/NBA |4.29s|4.27s|3.90s|1.095|
| 64路扇出三百万周期 |8.14s|7.99s|7.86s|1.017|

整数模型比原版加速13.32倍，只代表该合成负载。共享主机未锁频；CPU包含初始化；编译另计；没有本轮大型RTL、门级SDF或波形性能结论。候选是实际生成自包含C++在同一主机以GCC -O2编译；两端安装入口重生成C++哈希已核对一致，Linux实际入口另复跑十亿次整数校验。候选GCC时间不能当作RTL编译时间。

performance-results.json保留所有重复值、版本/源/二进制哈希；verify-performance.py独立重算36份TRACE、GNU time CPU、中位数与比值。原始生成代码、计时、VCD、sanitizer日志在用户测试目录及103的 evidence/m98-integral-string；两端最终发布记录见release-summary.json。REPORT6测试误报修复单列在../m99-report6。

发布完成：实现10f0bb0，macOS/Linux各7项针对性发布检查通过。macOS566项发布输入与Git源码包相同，Linux1524源码文件、两端各8份头快照和二进制身份核对；两端89份完整C++、78份整文件VCD及354份运行输出逐字节相同，13模型重新与VCS按866/914全部位核对。新组每端118组预算边界、10次回滚、6项明确拒绝均通过。实际稳定入口、哈希和检查范围见release-summary.json。原始记录见两个evidence目录；历史性能基线与当前结果明确区分。
