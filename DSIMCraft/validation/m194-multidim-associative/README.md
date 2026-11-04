# M194 多维关联数组

生产实现 **96239d15522f756fe6590775396d2ae389e4b485**，1328 冻结输入，源摘要 `d66627c01071cd59577cd61e7ed58eaf0ee5a625ba84814988560357b038ed4f`。实现及边界见[功能文档](../../docs/multidimensional-associative-arrays.md)。

Mac 稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 已激活 `20261031T044506687582Z-d66627c01071`，九个新模型经实际入口编译执行，CPP 与候选一致、异步波形与候选一致。冻结源码 `/private/tmp/dsim-m194-src`，构建 `/private/tmp/dsim-m194-build`。

| 验收 | 结果 |
| --- | --- |
| 新功能 | 9 模型、164 捕获、13 编译拒绝、1 回滚/1 提交、原生树存储测试 PASS |
| 整数索引 + 旧类型容器 | 21 模型、384 捕获、35 编译拒绝、2 运行时诊断、3 回滚/3 提交 PASS |
| mandatory | RTL parser 重复解析/清理、格式 parser、Liberty 原生 DB PASS |
| ASan/UBSan | 新 9 模型、1 回放、13 拒绝、原生存储及 parser PASS；关闭 leak 检查 |
| 额外开发回归 | constraint_foreach 6 模型/110 捕获，foreach_receivers 3 模型/56 捕获 PASS |
| VCS W-2024.09 | 6 同源执行正例、5 共同类型拒绝 PASS；3 项差异独立记录 |
| 跨端参考 | 96 CPP、548 解码捕获摘要；Linux 比对待执行 |

新增语料覆盖公开 UVM 的 class/class/enum 三维形状、整数/字符串轴、65/129 位索引、子数组 cursor/locator/复制/删除、foreach 控制流、接收者和下标单次求值、packed/复合/自增更新、两态转换、package/层次访问、automatic 递归隔离与预测回滚。原生存储另验证内层 signed 覆盖外层 unsigned 和复制覆盖祖先。

原版 Accellera 2020.3.1 预处理仍为 1,888,084 字节/166 依赖，展开哈希不变。三维容器 parser 阻塞已越过；当前首错为 `uvm_transaction.svh:38` 的 `forward class has no definition in the same scope: uvm_event_pool`。完整 UVM 未通过。

VCS 差异均保留源哈希和日志：`constraints` 与 `sparse_constraints` 报 `CNST-NAE`，填齐行并未消除此语料的错误，不推断所有多维约束均不支持。`storage` 在 logic→bit 二维复制断言失败；独立探针显示源 `x1z1`、目标 `1010`，dsim 目标为 `0101`。普通/增加观测的 debug 探针还出现递归求和最终观测差异（13/26），未将该程序计作 VCS 一致；具体日志保留，未归因为某个尚未证明的供应商实现原因。其余六同源正例覆盖核心容器及有副作用对象接收者。

103 上 M192/M193 验收仍在执行/排队，当前入口保持 M190。M194 阶段任务 **35003**、最终验收任务 **36369** 已排队，先等待已知旧最终验收进程退出，再进行 Intel 构建、三组测试及跨端 CPP/波形比对；继承或补测 clocking，九个实际入口复验通过后才激活。当前为 **QUEUED_NOT_PUBLISHED**，见 [linux-pending.json](linux-pending.json)。不将排队计为发布或 Linux 通过。

脚本 `public-uvm.py`、`sanitize.py`、`vcs.py`、`activate.py`、`release-check.py` 和 `finalize-remote.py` 提供复验入口。`vcs.py --resume` 仅复用输入哈希与原始 TRACE 均匹配的成功执行语料。初次开发中的原生测试键宽默认值和负例诊断预期已纠正；发布采用最终冻结输入，旧失败未计入通过。

完整可审查证据保存在 `~/vibe-coding/dsim-test/evidence/m194-multidim-associative/mac`，归档清单另见 `archive-catalog.json`。没有性能结论。
