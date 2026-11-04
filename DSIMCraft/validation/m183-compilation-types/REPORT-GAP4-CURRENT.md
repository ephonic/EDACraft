# REPORT-GAP4 复核（M183）

以生产实现 `32c524c1` 的本地稳定入口重新检查 35 个原始探针：22 个生成 C++、13 个拒绝，本次数量只代表前端接收性，不代表 22 个均执行通过。当前用户目录 `rtl-tests/complex/probes3`、M181 保存的原始文件与本轮输入的 35 份 SHA256 全部相同，见 [源码绑定](report-source-binding.json) 和 [前端结果](gap4-native.json)。

原报告测试旧 `20261030T0445` 入口。标量 randc、队列 `$` 下标、空队列字面量和合法 mailbox.peek task 已有专项执行验收；原 peek 表达式探针把阻塞 task 当成有返回值的函数，VCS 同样拒绝。约束 foreach 和文件级 class/typedef 已分别在 M182、M183 补入，这些能力并不表示完整 UVM 已支持。

| 报告中的能力 | M183 状态与剩余工作 |
| --- | --- |
| clocking | 未支持；需要输入采样、输出驱动和周期等待语义。原 q06 缺 default clocking，VCS 也拒绝；合法变体的既有 VCS 对照另存。 |
| covergroup | 未支持；sample、bins、cross、覆盖率统计仍需实现。 |
| program | 未支持；需要 Reactive/Re-NBA 等调度语义。 |
| let | 未支持；需要参数绑定和使用处词法上下文。 |
| specify 时序检查 | 报告所用形式仍拒绝；不能据已有 SDF/延时功能视作完整 specify。 |
| 断言控制 | 报告所用 `$assertoff` 及指定目标绑定仍缺。 |
| dist | 未支持；需要真正按权重选择，不能只忽略关键字。 |
| solve before | 未支持；需要影响求解选择顺序和分布。 |

以上八类仍为真实缺口。VCS 对照和 clocking 修正变体沿用 [M181 原始记录](../m181-typed-for/REPORT-GAP4-CURRENT.md)，本次未重新运行这些 VCS 探针；M183 的六个新增模型另有新鲜同源 VCS 验收，见 [本轮结果](README.md)。

未修改的 Accellera UVM 2020.3.1 smoke 当前首个语义错误为 `unknown integral type chandle`。预处理成功及首错推进均不能证明整库语义分析、展开或运行成功。下一阶段优先 chandle/DPI 类型边界、编译单元剩余能力及随机复合类型，继续 dist/soft/solve-before、virtual interface/clocking 和覆盖率。
