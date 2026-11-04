# M173：foreach 的 this / super 目标

支持范围见 [显式接收者](../../docs/foreach-receivers.md)。三个模型56捕获、
三拒绝、一次预测回滚/一次提交通过，包含同步/异步压缩波形和用户指定范围。
完整parser、格式parser、原生DB通过；ASan/UBSan完整parser、三前端/三拒绝、
三生成程序及预测回放通过，生成CPP及异步波形与正常证据相同。
VCS三个原样源码执行输出一致，三个非法接收者同样拒绝；源码SHA绑定在vcs.json。
没有LSan/TSan、全部实际双分区或性能结论。

普通和ASan未修改的公开Accellera UVM 2020.3.1预处理仍1888084字节/166依赖/原SHA，
使用已有UVM_NO_DPI选项，native首错到phase:1551的数组元素接收者路径。
公开库仍不能编译运行，类句柄键关联数组等底层能力也未完成。

重新检查REPORT-GAP/GAP2原目录中的19个q/r源码：9个能生成C++、10个拒绝，
结果和源码SHA记录在report-probes.json。该批只检查前端，不能称9个全部原生运行；
DPI原始探针需要实际C库。rand/constraint、clocking、mailbox、covergroup、let、
program、specify及部分assert控制仍被拒绝，不能因公开库首错后移而宣称这些已完成。
下一主功能推进受约束随机化执行链路及IPC，公开UVM编译继续作为真实库检查。
当前稳定本地M171、103 M169，本批未发布稳定入口。
