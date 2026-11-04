# M172：const 类属性与构造器赋值状态

范围见 [const 类属性](../../docs/const-properties.md)，保持独立 RTL/gate parser。
最终四模型74捕获、11编译拒绝、一个运行时重复赋值拒绝、一次回滚一次提交通过。
三调度请求、VCD/同步和异步DWF、ordered/settled、用户指定范围均检查。
完整parser/格式parser/原生DB通过；旧class_static和class_access各182捕获、
一次回滚一次提交通过。请求双线程不代表每个模型实际双分区。
最终ASan/UBSan覆盖完整parser、四前端/11拒绝、四生成程序/回放及运行时重复赋值拒绝；
CPP及异步波形与正常执行相同。无LSan/TSan或本批速度结论。

VCS四个相同正例执行输出一致，源码SHA记录在vcs.json。
11个拒绝中八个VCS同样拒绝，已初始化属性位选写、静态常量可写ref、
派生构造器赋值继承常量三项VCS接受而原生拒绝；不称全部const语义对齐。运行时循环重复赋值探针在VCS中未被拦截、到达兜底fatal（进程退出码仍为0），原生则在第二次赋值报错；不以退出码称VCS通过该拒绝检查。

开发首次泛型模型失败：静态常量编号未随信号压缩重排，误把普通句柄标为只读。
随后运行时拒绝模型暴露循环子块丢失构造器上下文；修订元数据重排和词法块继承，
最终dev/verified-final与asan-final重新通过。dev/verified、dev/final的失败保留。

未修改公开Accellera UVM 2020.3.1普通与ASan预处理仍1888084字节/166依赖/原SHA，
使用已有UVM_NO_DPI选项，native首错从transaction:443推进到phase:953的foreach(this...)。
完整库仍未编译运行，约束随机、IPC、virtual interface/clocking、coverage等总目标继续。
稳定本地M171、103 M169；本批尚未发布到稳定入口。
