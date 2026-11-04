# 普通模块层次变量写入与独立空语句

允许 `u.word = ...`、`u.mem[i] <= #N ...` 等普通层次变量目标，沿用既有 storage_part/selected_storage 解析和运行时赋值路径。支持多实例存储隔离、动态下标、packed 位/片选择、拼接、复合赋值、整变量/未打包数组元素 ref 实参；net、parameter、packed ref 和不等价类型仍拒绝，interface modport 输入权限仍检查。

块内、子程序内与 fork 分支的独立空语句由 stmt_or_null 统一产生已有 DummyStmt，不生成额外行为。未增加 RTL/gate parser 耦合。

四模型验证窄/129位、升序 packed 二维、动态下标只求值一次、延迟 NBA 地址冻结、连续读者唤醒、多实例、真实双分区和空语句执行；serial/time-wheel/parallel 下的 VCD、同步/异步 DWF 全流对照，预测失败回滚/成功提交与六负例一起回归。具体结果见 validation/m157-reported-cases；未实现层次数组整体赋值、动态容器 ref 或完整类静态成员。
