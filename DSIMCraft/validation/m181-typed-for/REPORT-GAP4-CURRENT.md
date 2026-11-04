# REPORT-GAP4 复核（实现 7c1e2525）

原报告测试的是 20261030T0445 入口。当前以修正后的 M181 稳定入口复查其目录中的 **35 个原始 SV 文件**，22 个生成 C++、13 个拒绝；这不是 22 个原生执行通过。原文件按字节保存在 `probes/`，结果与来源哈希见 `gap4-full-native.json`。

报告列为缺失的标量 `randc`、队列 `$` 下标与空队列字面量、合法 mailbox `peek` task 已具备；专项执行、回滚、波形与 VCS 对照见本目录和 M180 记录。组合随机化探针仍首先被 `dist` 阻塞，不能据此判断 `randc` 未实现。

| 报告项目 | 当前 dsim | 本次 VCS 对照与测试边界 |
| --- | --- | --- |
| clocking | 仍缺 | 原 q06 缺少 default clocking，VCS 同样拒绝。仅补 default 后，原检查输出 `BAD q=00`；等待两拍再读取采样值的独立合法变体输出 `ok`。 |
| covergroup | 仍缺 | 原 q03 实际执行，VCS 返回覆盖率 100%；尚非 cross、illegal bins 或完整覆盖率测试。 |
| program | 仍缺 | 原 q12 在 VCS 启动执行；它不检查 Reactive/Re-NBA 调度顺序。实现时需要相应调度语义。 |
| let | 仍缺 | 原 q09 在 VCS 输出 `ok`；dsim 在 let 声明处拒绝。 |
| specify 时序 | 仍缺 | 原 q10 在 VCS 输出 `q=1`，不足以验证时序检查；dsim 明确拒绝 specify timing。 |
| 断言控制 | 仍缺 | 全局及指定断言的原 q14 探针在 VCS 编译执行；dsim 分别缺少 `$assertoff` 与断言目标绑定。完成提示本身不能证明全部控制语义。 |
| dist | 仍缺 | 原 r11 在 VCS 的 400 次中有 46 次取高区间；该权重的期望为约 50 次。dsim 在 dist 处拒绝。 |
| solve before | 仍缺 | 原 r12 在 VCS 编译执行；只检查蕴含成立，不能检测忽略 solve-before 后的分布偏差。 |

这八类是本报告确认的功能缺口，并非与 VCS 的全部差距。公开、未修改的 UVM 2020.3.1 当前仍在 `uvm_mem_mam.svh:495` 的约束 foreach 处解析失败，尚未完整编译、展开和运行。报告中“仅剩 clocking 与 covergroup”的结论不成立。

`r14_mbox_deep` 和 `r14d_peek` 都把 `mailbox.peek` task 用作表达式，两端均拒绝；合法自动 task 中的阻塞 peek 已单独执行通过，并检查消息保留及后续 get。`r03_randpart` 仅检查类内 urandom，不是 randc 循环测试。

后续优先补约束 foreach 与随机复合类型，同时推进 clocking 的采样、驱动和周期等待基础，再接通 program 调度区域；随后补 dist/solve-before、断言控制与 let，继续覆盖率能力。约束 foreach 要在每次 randomize 建题时遍历当前容器；clocking 要保留输入采样与输出驱动的时序；solve-before 要影响求解选择顺序，均不能仅消除语法错误。

复现前端矩阵：

```sh
python3 validation/m181-typed-for/report-matrix.py BUILD/dsim \
  validation/m181-typed-for/probes OUTPUT
```

VCS 九个原始缺口探针的编译与执行记录在 `gap4-gaps-vcs.json`；两个 clocking 变体在 `gap4-clocking-vcs.json`。`gap4-summary.py` 校验源文件哈希、实际入口身份和观测输出后生成 `gap4-current.json`。原生发射、VCS 执行及完整功能验证分别记录。
