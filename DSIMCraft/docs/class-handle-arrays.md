# 类句柄数组、容器查询与随机队列

M209 接通类属性的一维类句柄动态数组。支持默认空数组、new[N] 分配后的 null 元素、new[N](source)、整体值复制、拼接、foreach、元素赋值、size/delete 和通过元素调用虚方法。数组赋值复制容器，元素仍指向同一个对象；修改目标数组的槽位不会修改源槽位，修改共享对象会从两边可见。存储与对象身份随 checkpoint 恢复。

支持类标量/一维数组、已有队列的 rand 类句柄声明、初始化和模式设置。randomize(null) 将其作为状态检查，randomize(scalar_property) 可继续求解指定整数属性并读取句柄指向对象的当前属性。

对象整体 randomize() 涉及随机句柄时仍明确编译拒绝，包括运行时禁用句柄字段的情形。联合求解尚未实现，不能把句柄编码当成随机整数，也不能用分别调用子对象 randomize 替代跨对象约束。这一边界参考 [Accellera 对随机句柄的说明](https://www.accellera.org/images/eda/sv-ec/att-3413/Section889.pdf)。randc 句柄/容器、对象图联合约束仍不支持。

类动态整数/packed 数组和队列支持 $size、$bits、$dimensions、$unpacked_dimensions、$left、$right、$low、$high、$increment。维度参数和接收者按运行时值求值，接收者只求值一次。类句柄容器的 $bits 仍明确拒绝。随机数组约束内请用 size()，尚未接入符号求解的系统数组查询会拒绝。

整数/枚举 rand 队列复用两阶段长度/元素求解，支持有界队列、多个容器和标量关联、foreach、模式切换、具名普通队列属性和回调。没有活跃长度约束时保持当前长度；有界队列容量作为求解约束，过大长度导致 UNSAT 并保持原内容，不先求值后截断。支持空队列和预测回滚。既有随机数组 reduction/locator、混合长度与元素约束原子的限制仍适用。

新增类内隐式属性 rand_mode 设置及标量查询。数组整体 rand_mode() 查询按 VCS 实测明确拒绝；设置形式仍可用。

公开未修改 Accellera UVM 2020.3.1 保持 166 依赖和相同预处理 SHA，通过随机类句柄及 uvm_reg_fifo 随机队列声明，当前首错进入 uvm_globals.svh:76 的函数互递归代码生成。这里不代表整个库已展开或运行通过，完整原版 UVM 仍未完成。

六个同源模型覆盖句柄存储、查询、状态约束、随机队列、容量原子性和回滚；见 [M209 验收](../validation/m209-class-handle-arrays/README.md)。
