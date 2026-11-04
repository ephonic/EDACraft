# REPORT-GAP5 当前复核

报告文件：`~/vibe-coding/dsim-test/rtl-tests/complex/REPORT-GAP5.md`，原报告使用 M188；本轮源码为 M190。

原目录实际有 36 个 SV，原文发射检查得到 23 发射 / 13 拒绝，逐文件哈希与诊断在 report-gap5.json。发射结果不表示实际执行通过。

- **仍缺**：clocking block（采样、输出 skew、默认 clocking、##N/#1step）、covergroup/功能覆盖率、let、program、specify 时序检查、$assertoff、dist、solve-before。
- **peek 要修正测试写法**：r14_mbox_deep/r14d_peek 把标准阻塞 task 当作表达式；合法 `mb.peek(value);` 保留队首并与随后 get 配合的探针，在 dsim 和 VCS 均执行通过。
- **randc 已有实现**：本轮使用合法二位 randc，检查一轮四个值不重复且域完整；dsim 和 VCS 均执行通过，不代表全部随机对象/数组约束已支持。
- **clocking 测试也需校正**：原 q06 缺少 default clocking，VCS 也拒绝。仅加 default 后再等待两个采样周期的合法探针在 VCS 通过，dsim 仍缺此功能。保留原文与合法变体，不通过删除采样语义接收原测试。
- **covergroup 是真实缺口**：原 q03 在 VCS 执行输出 100% 覆盖率，dsim 在 covergroup 语法处拒绝。

本批补齐的是另一个真实 UVM 阻塞：class 句柄关联键、泛型 KEY 索引及遍历/复制/快照。本轮完整 UVM 仍未编译运行。后续优先接入 clocking 调度，再接入真实 covergroup 采样、bins 计数与查询；其余报告项继续分批实现，保持明确诊断。
