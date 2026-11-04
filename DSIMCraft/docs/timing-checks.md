# 编译式时序检查

`--sdf-annotate`在原有模块路径和逐接收输入延迟之外执行标准单元时序检查；`--gate-models`提供specify声明、常量和模型精度。结构网表仍由独立gate parser处理，RTL parser只解析测试平台和端口桩。`--no-timingchecks`显式关闭检查，默认开启。

支持SETUP、HOLD、SETUPHOLD、RECOVERY、REMOVAL、RECREM、WIDTH、PERIOD与SKEW。编译器将事件规范化为数据/异步控制与参考时钟，保留独立上升/下降/显式转换、事件条件、初始limit和WIDTH threshold。SDF按模型声明的事件、边沿和条件匹配后替换limit；未注解声明保持初值。时序检查要求精确边沿身份，不能套用IOPATH的省略边沿匹配规则：VCS对“模型未限定数据边沿、SDF限定数据边沿”的检查报告无法匹配，本工具严格拒绝并保留已有输出。

事件条件可用标量端口/常量位选、0/1/X/Z、括号、逻辑非/位反、逻辑与或、位与或异或及普通/四态相等运算。事件条件只有确定为1才启用；X/Z条件不启用。未限定边沿的时序事件不把X↔Z视作有效转换。事件支持posedge/negedge，以及Verilog `edge [01,10,...]` 与对应SDF显式转换。未覆盖表达式明确报错。

每次解析后的引脚变化直接送入检查通道，同一Active/NBA时刻的多次变化不在此通道合并。检查读的是实际接收引脚：已启用INTERCONNECT时使用MIPD私有输入，输出检查使用带路径延迟的可见输出。默认零延迟程序不启用检查宏，不增加这部分分派。上下文拥有窗口历史，检查点同时恢复历史和队列；诊断通过已有打印事务提交，拒绝预测不会留下投机违例输出。

违例以`TIMING kind=... time=... limit=... cell=... model=... declaration=...`输出；组合检查的诊断按实际SETUP/HOLD或RECOVERY/REMOVAL阶段报告。time/limit为IR所列global_precision_fs的tick，不冒充VCS原始诊断文字。违例本身不终止仿真。没有notifier时不擅自把输出置X；notifier/扩展参数要求功能Verilog模型支持，目前明确拒绝。NOCHANGE、TIMESKEW/FULLSKEW/BIDIRECTSKEW、完整事件条件语言和负检查的延迟参考/数据模式仍未实现。

当前为非负检查模式：先按目标模型精度精确换算，再转成全局tick；负limit夹为零，编译日志与IR统计该转换。它对应本批VCS默认模式对照（VCS对负值报SDFCOM_NNTC，注解统计1错误并以0运行；本工具显式提示夹零并在IR计数），不支持`+neg_tchk`的延迟信号语义，也不把负时序检查当作负IOPATH处理。

验证脚本在[tests/timing_checks](../tests/timing_checks)；实际差分、回滚及全量真实SDF的当前结果见[验收记录](../validation/m4-timing-checks/README.md)。标准单元模型的行为体仍不由specify reader编译，真实全量SDF能否运行取决于完整模型身份和其他已记录的时序边界，不能由若干检查微例通过推断。

## 回调查找

检查观察者使用普通信号/紧凑信号各自的稠密编号查表，再进入仅为有观察者的信号分配的回调组。信号无检查观察者时立即返回，避免每次变化都查询红黑树。组内保持注册顺序；信号ID合法性和上下文仍在登记时检查，检查窗口和诊断事务沿用原状态。拓扑在检查点后禁止改变，因此索引表本身不需要复制进每个检查点。
