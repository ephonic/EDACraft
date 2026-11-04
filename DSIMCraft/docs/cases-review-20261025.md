# 2026-10-25 cases 复核与修复（M101）

检查 `~/vibe-coding/dsim-test/cases/` 中的 11 个顶层归档及 carry 的一次 follow-up。输入和独立 oracle 哈希证明其中有 5 组不同的仿真输入；永久回归保留原 RTL、原 TB、原 stimulus，不删除绑定观察器、不改写测试平台。

| 原始组 | 归档数（含 follow-up） | 采样次数 | 结论 |
|---|---:|---:|---|
| carry_baseline | 2 | 290 | 当前版本通过；旧编译预算超时不能认定数值缺陷 |
| blocking | 1 | 193 | 先前的 always_comb 部分写入限制已解除，本轮原样复跑通过 |
| overlap48_hand | 1 | 196 | 同上，48 位重叠写入通过 |
| u13_s2 与对应 replay | 4 | 1040 | 补齐 final、模块类型 bind、%m 后通过 |
| u256_s8 与对应 replay | 4 | 1040 | 同上，256 位数据通过 |

5 组共 2759 次独立采样、423384 个输出位观察值均符合归档 oracle。103 上 VCS W-2024.09 对原始输入重新编译运行，全部 3754 行采样、完成和传输输出与 dsim 一致，包含 `%m` 实例路径和 final 的 event=E。重复归档按 RTL/TB/stimulus/oracle 的完整 SHA256 识别。`harness-rejected/` 下同区输入与时钟竞争的旧 TB 仍保留其无效测试分类，不能据此改变调度语义。

修复采用原生实现：RTL parser 记录文件作用域的模块类型绑定，待所有模块声明完成后，把实例接入目标模块的符号解析、实例图和参数化展开流程；实际端口表达式在目标作用域解析。门级 parser 保持独立。`final` 是独立的结束过程，首次运行不入 Active 队列，在自然结束或 `$finish` 后执行一次；阻塞写入不会继续调度普通过程。并行执行在全局结束栅栏提交后统一执行，并提交最后的波形。检查点保存结束状态和过程状态，失败预测丢弃结束日志和波形，再回放。

专项回归包含 8 个模型，串行、时间轮、线程后端共 49 份完整 VCD、8 次拒绝预测回放、9 项明确拒绝；两个模型要求实际分配两个分区，并检查提前结束和 final 变量波形。独立调度器测试验证双分区自然结束、结束栅栏回放及结束输出只出现一次。参数化/前置 bind、重复 parser 清理和 final 标志克隆加入 parser 单测；5 份实际生成程序通过 ASan/UBSan。

当前边界：支持文件作用域 `bind module_type observer ...`，暂不支持指定单实例/实例列表的 bind、interface/checker bind。final 支持零时间阻塞语句和已支持函数，拒绝定时控制、NBA、并行 fork、事件调度、用户 task 及 final 内 `$finish`。尚不保证运行时异常或 `$fatal` 路径执行 final；`%m` 本轮验收模块实例和 generate 层次，不代表所有动态调用栈格式均与 VCS 相同。本轮没有性能重测。

永久原始输入、oracle 与来源：[cases_archive](../tests/cases_archive/inventory.json)；专项回归：[final_bind](../tests/final_bind/regression.py)；VCS 与发布证据：[M101](../validation/m101-cases/README.md)。
