# ref 引用形参

M62 已支持 [const ref 只读引用](const-ref.md)，固定数组形参见 [M61](array-arguments.md)；后文相关未支持描述是历史边界，以新文档为准。

M61 已增加[固定数组整体形参](array-arguments.md)，支持多维数组及动态前缀子数组。后文数组整体形参未支持的描述为 M60 历史边界，以新文档为准。

automatic task/function 支持可写 `ref` 形参。形参与实际变量共享存储，写入立即可见；多个形参可以指向同一变量。支持命名/default 实参、嵌套转传、整数、logic/bit、enum、packed struct 及宽值。RTL parser 单独增强，门级 parser 保持独立。

```systemverilog
integer value=1;
task automatic update(ref integer target, input integer amount);
  target+=amount; // 调用者立即看到变化
  #2;
  target+=amount;
endtask
initial update(value,3);
```

实参可以是完整变量或固定 unpacked 数组的单个完整元素，包括多维数组的完整下标。动态下标在调用入口求值一次，挂起后不会重新选择元素。actual 与 formal 必须类型等价，不进行 input/inout 的值转换；net、packed bit/part selection、聚合成员、数组整体形参和静态子程序 ref 明确拒绝。动态元素下标含 X/Z 或越界时终止并诊断，该诊断策略不称作与 VCS 完全相同。

实现沿用编译进程状态机。入口捕获实际物理信号 ID，激活帧保存别名；别名不进入自动变量所有权池。父帧由共享引用保活，任务等待时按实际存储订阅事件。函数使用 C++ 作用域守卫恢复调用者帧，包括异常退出。引用实际变量的潜在读写进入依赖分析和分区；可写 ref 函数不作为无副作用事件回调。取消、槽复用、检查点与失败预测沿用既有运行时。

尚缺 `const ref`、数组整体形参、递归、动态数组/队列/关联数组和更完整的类型等价规则；packed bit/part/member actual 本批不接通。NBA 写 ref 仍按 automatic 目标拒绝。直接在 join_none/join_any 分支访问外层 ref 的标准限制未完整实现，不能据现有父帧保活宣称该构造标准兼容；远端 VCS 对该探针仅发 warning，并未拒绝编译。

验收入口：`ctest --test-dir build -R '^rtl_ref_arguments$' --output-on-failure`，运行时直接检查为 `ref_arguments_kernel/wheel/compact`。六组同源模型与远端真实 VCS 对照，数组元素使用 wrapper 中只读观察线补充 VCS 默认 dump 的省略项，映射逐项列出且不排除位。详细证据见 [M60](../validation/m60-ref-arguments/README.md)。本批没有新的性能测量，不能视为全部功能或性能与 VCS 对齐。
