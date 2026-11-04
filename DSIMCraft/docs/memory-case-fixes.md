# 新增 memory/SRAM cases 修复（M139）

复核 `dsim-test/cases` 的两个新归档，保留原始 DUT、TB、向量和 180 秒编译预算，没有运行归档内 Python。原始文件 SHA 与原归档的对应关系记录在 `tests/memory_cases/origins.json`。

SRAM 原用例报 `too many packed indices`：选择对象是没有显式 packed 维度的标量，TB 对它使用 `[0]` 和 `[0:0]`。VCS 接受这种写法并给出 INAV 警告。现在兼容常量 `[0]`、`[0:0]`、`[0+:1]`、`[0-:1]`，包括标量 unpacked 元素、层次读取、阻塞/NBA 写入和二态转换；不改变数组查询的声明维度。动态/非零标量选择仍明确拒绝，其 VCS 行为与普通向量越界选择不同，不能直接套用向量裁剪。本批没有宣称标量查询与 VCS 全面对齐，VCS 拒绝 `$dimensions(scalar)`。

另一原始 memory TB 把全部输入与预期展开为语句，生成一个约 43523 条 PC 指令的过程及约 13 MB C++。M138 默认编译在 180 秒被终止，尚未运行仿真，属于编译预算问题。单独做 PC 分块或单独限制优化的开发候选仍超时；同时分块和限制这些块内部表达式的优化才通过开发筛选。

编译器现在对至少 16384 条指令、没有回跳的一次性 initial 程序按 256 条指令生成独立 noinline 块。Clang/Intel Clang 在该回调的词法范围内关闭优化，包含其表达式 lambda；后续代码恢复正常编译选项。每次块间转移不新增事件或指令计数，原 PC、挂起、默认终止步和 checkpoint 所有权保持原结构。反复触发的 RTL、循环、子程序及带复杂过程控制的设计保持原编译路径。仅在 Clang 上限制优化，其他编译器仍分块；不能推断 GCC 也已通过相同预算。可用 `--cxx-flag -DDSIM_OPTIMIZE_LARGE_INITIAL` 保留这些大 initial 块的正常优化。

这是处理编译规模的通用策略，没有匹配设计名称、端口或向量内容，也没有把原始 TB 改为文件驱动。有限一次性过程可能执行更慢，本批不做 runtime 加速声明。解析器和八个 runtime 头文件未改。

新增回归包含两个原始完整 case、VCS 标量兼容对照、前向分支/延迟/真正双分区大过程，以及分块边界的预算中断和 checkpoint 恢复。源码冻结、双端发布和实际测量见 [M139](../validation/m139-memory-cases/README.md)。
