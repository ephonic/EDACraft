M209：类句柄动态数组、容器查询与随机队列。

接通类句柄数组的默认 null、分配、复制、拼接、foreach、虚方法访问和 checkpoint。支持 rand 句柄声明与状态检查/显式标量随机化；整体 randomize 涉及随机句柄仍拒绝，未把句柄作为整数随机化，也未宣称对象图联合求解完成。

补类内隐式 rand_mode 属性控制和动态容器系统查询，并将两阶段求解扩展到整数/枚举随机队列。 bounded 容量进入求解器，过大长度 UNSAT 保持内容。VCS 同源检查六模型，queue_limits 一次预期 CNST-CIF；state 用返回值检查 randomize(null) 失败，VCS 不发 CNST-CIF；完整 TRACE、任何 Fatal 和非预期错误均检查。数组整体 rand_mode 查询经 VCS 拒绝后，已加入明确诊断和负例。

六模型执行串行、时间轮、双线程及 VCD/DWF/异步波形完整解码对照；rollback 覆盖共享对象身份和随机队列 RNG 恢复。十一项拒绝检查。公开原版 UVM 首错进入 uvm_globals.svh:76 的互递归代码生成；完整库尚未运行。功能范围见 docs/class-handle-arrays.md。

M209 Mac 稳定完成：生产 6943e8e2，1482 输入，源 SHA cf2a8f4d140ffd6d7116143c886441abc5954b3b122c10d01c7d3386389c0061。四组 34 模型/624 捕获、74 编译拒绝/1 运行拒绝及 mandatory 通过；112 CPP/624 完整解码参考建立。六个同源 VCS、前端/生成模型 ASan+UBSan、十一项消毒拒绝与 parser 重复清理通过。VCS 对 randomize(null) 失败不发 CNST-CIF，验收脚本已按实际诊断修正，queue_limits 的一次预期 CNST-CIF 单列。Mac 稳定 20261101T054228245227Z-cf2a8f4d140f 已激活，六实际入口 CPP 与冻结结果一致，复跑对应已验收原生模型的 TRACE/完整波形并记录二进制 SHA。原版 UVM 当前首错为 uvm_globals.svh:76 的函数互递归代码生成；对象图联合随机化仍明确不支持。103 在 M208 最终验收之后串行 Intel+Z3 发布，未记为 Linux 完成。
