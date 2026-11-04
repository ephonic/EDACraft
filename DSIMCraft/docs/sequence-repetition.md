M140 已支持有限序列作为蕴含前件，见[当前范围](sequence-antecedents.md)。下文关于前件仅限布尔表达式的描述是历史边界。

# 固定次数连续重复（M136）

支持单时钟 SVA 中布尔表达式的固定正数连续重复 `expr[*N]`，可用于直接序列或 `|->`、`|=>` 后件，与前导/中间/尾部 `##N`、`##0` 组合。括号包裹的布尔表达式、静态 packed 位选、参数和 generate 实例均可使用；计数在实例展开后绑定，允许整数常量表达式。

```systemverilog
property response;
  @(posedge clk) disable iff (reset)
    request |-> acknowledge[*3] ##1 done;
endproperty
check_response: assert property(response) passed++; else failed++;
```

按 [Accellera 附录 H.2.3.2](https://www.eda-twiki.org/sv/AnnexH_draft4.1.pdf) 的固定正数规则，三次连续重复在三个相邻采样时钟检查该表达式。编译器在展开后转换为既有阶段表示；没有增加运行时字段或另设调度路径。`[*1]` 在一个采样时钟检查，后续重复之间为一拍。相邻 `##0` 仍在当前采样时间槽检查后继条件，不能把重复全部压成同一拍。

计数必须为 1..256 的已知整数常量；包含重复展开后的整个序列最多 256 个条件，总跨度最多 65536 拍。阶段表达式仍须纯 integral；X/Z 条件按原有失败语义处理，采样函数历史每个时钟推进。独立尝试、Reactive 动作、异步 `disable iff` 取消、检查点、预测提交/回滚和独立分区复用已有机制。结束时未完成的弱尝试不自动失败。

尚不支持 `[*0]` 的空序列语义、范围/无界重复、`[+]`、`[->N]`、`[=N]`、序列 antecedent 或完整 SVA。它们会明确拒绝，不能因固定重复成功而推断完整标准支持。完整 class/UVM、clocking、虚拟接口、覆盖率和 DPI/VPI 仍在后续计划中。

验收见 [M136](../validation/m136-sequence-repetition/README.md)。同源 VCS 对照同时检查输出和共同声明位的全部 settled 时间线；三种执行配置、真实双分区以及事务回放另作回归。RTL 与门级 parser 保持独立；本批不进行性能测量。

M137 已接入[括号 temporal 子序列及固定重复](sequence-groups.md)，原 M136 验收范围保持不变。

括号组和命名有限 sequence 已分别由 [M137](sequence-groups.md) 与 [M138](named-sequences.md) 接通，仍受有限阶段/跨度上限约束。
