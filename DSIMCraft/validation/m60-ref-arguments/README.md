# M60：automatic 子程序的可写 ref

这批补齐 automatic task/function 引用形参的编译执行路径：即时别名写入、多形参共用实际变量、嵌套转传、等待中的外部变化、固定数组元素动态地址只取一次、宽四态/两态、enum/packed 聚合、默认与命名参数、取消/复用和预测回滚。RTL grammar/lexer、绑定克隆和清理同步增强；门级 parser 保持独立，Bison 冲突维持 47。

运行时扩展不可变激活帧的逻辑信号到实际存储映射，引用不进入 owned 变量池。自动父帧保活，函数作用域守卫在返回或异常时恢复调用上下文。潜在实际读写参与依赖和分区分析，任务仍编译成 PC 状态机，运行时不遍历 AST。

## 原生和真实 VCS

- `tests/ref_arguments/regression.py`：六模型、serial/time-wheel/parallel 三后端、ordered/settled 两模式和 VCD/DWF 两格式，共 77 次捕获；5 次强制预测失败后回滚重放，含分配前恢复；24 次正常/取消调用存储有界，实际两个分区；11 类编译拒绝和 2 类非法动态索引运行诊断。
- `vcs/` 保存真实远端 VCS W-2024.09 的六份相同 SV、wrapper、编译/执行日志和波形。六组 TRACE/自检和 963 条物理位 settled 时间线一致，无排除位。
- VCS 默认 dump 即便指定数组元素也省略它们。`observers.json` 明列四条只读 wrapper 观察线，将 324 位还原到 native 数组元素身份；没有修改设计源。`verify.py` 严格检查双方完整身份集合和值时间线。
- `probes/reference.sv` 即时可见、共享别名及动态地址探针对齐；`probes/detached.sv` 在 join_none 直接访问外层 ref，VCS 仅警告且编译成功。该构造的标准限制尚未完整实现，不计入对齐模型。

## 回归、sanitizer 和跨平台

本地 10 项不同定向 CTest 最终通过，涵盖三个新内核、parser 语义、call arguments、automatic subroutines/fork、function events、wait_order 和 explicit static；主批次 9/10，旧 automatic ref 拒绝预期失效，改查 static ref 边界后复测通过。新增功能回归直接执行成功，命令等同注册的 `rtl_ref_arguments`。初始三个新内核断言误认为预测失败停在检查点；已按既有“恢复后重放到 horizon”契约修正预期，运行时未为此更改。失败原始日志保留。

macOS ASan/UBSan：六个最终实际生成程序（parallel 模型实际两个分区）/完整 ordered 流、六语料每份三轮 parser 清理、完整 parser 语义单测及三种新直接内核通过。leak 检测关闭。

Linux 从 1262 文件冻结源包干净构建；四项 parser/内核检查、六串行模型及一个真实双分区程序验证 14 次捕获。完整 C++、ordered 流/stdout 和 VCS 位核对结果见 `linux/`；最终状态以 `results.json` 为准。未跑全量 CTest 或 Linux sanitizer。

源包 SHA256：`6d41c80687a71ed7d940b8a05d8847499114804c2c845fc40d96e78c3288e459`。`source-manifest.json` 固定输入文件及哈希；`source-changes.json` 列出相对 M59 的变化；`final-identity.json` 绑定七份完整生成代码与 sanitizer 输入。源包不含商业工具二进制或 csrc。

## 当前边界

仍缺 const ref、数组整体形参、packed bit/part/member 实参、递归、动态数组/队列/关联数组和完整类型等价/验证体系。静态子程序的 ref、net/type 不匹配、NBA 写 ref 等明确拒绝。未知/越界动态元素引用采用显式运行诊断，未宣称这项诊断策略与 VCS 一致。直接 join_any/join_none 访问外层 ref 的标准限制尚未完整执行。此前 M47 事件函数和 M55 逃逸直接事件等已记录差异仍保留。

功能优先；本轮没有新性能测量，不称作全部功能或性能与 VCS 对齐。
