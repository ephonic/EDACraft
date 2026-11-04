# fork 中的 foreach 循环帧

M56 为 foreach 隐式只读索引增加循环激活帧。每次进入循环分配独立索引存储，重叠的静态/automatic 任务及克隆 fork 分支不串扰。循环体中原本 static 的局部变量保持共享。复用现有 automatic 变量帧、编译 PC 和固定步长计数器，没有按数组元素展开代码或运行时解释 AST。

同一次循环生成的分支共享索引，索引并非每轮复制。自然结束时从内向外推进到右边界之外（左右边界相等时按下降方向推进）；break/return 保留退出时的索引。存活分支持有循环帧，因此父循环/任务结束后仍可读取。比如 ascending unpacked 数组范围 1:3 中，每轮启动 `fork begin #1; q+=i; end join_none`，父循环不让出，三个分支最终都读到 4。需要每轮捕获时仍应使用独立 automatic 局部变量；显式逐声明 automatic 捕获已由 [M57](explicit-automatic.md) 接通。

支持现有静态多维 unpacked 数组、packed 位维度、多个/省略索引、方向和 singleton 范围。嵌套控制流通过 PC 深度清理帧；continue 进入内到外的索引推进，break/return/disable 清理退出的帧，取消释放当前进程引用并隔离旧等待。索引事件等待绑定实际帧信号，失败预测恢复索引、计数器、PC、订阅及共享关系。VCD/DWF 不导出隐式索引和 private 存储。

仅存在 join 时仍可使用原有固定进程槽；有 join_any/join_none 时启用动态帧与克隆。没有 detached 子进程时省略不可观察的额外索引推进，保留原有扁平循环执行路径。

边界：数组范围仍受现有非负 unpacked/下降 packed 限制；动态/关联数组、队列、递归、process 对象和完整 SV 验证能力未接通。M55 保存的逃逸局部直接事件等待 VCS 差异仍保留，本批不能据此宣称全部 automatic 事件语义对齐。RTL 与门级 parser 继续独立，本批不修改 grammar/lexer。

验证入口：`ctest --test-dir build -R '^rtl_foreach_fork$' --output-on-failure`。实际范围、VCS 和其他验证结果见 [M56](../validation/m56-foreach-fork/README.md)。本批没有新的性能测量。
