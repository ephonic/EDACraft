M140 已支持有限序列作为蕴含前件，见[当前范围](sequence-antecedents.md)。下文关于前件仅限布尔表达式的描述是历史边界。

# 固定周期并发断言序列（M87）

M136 增加布尔表达式的固定正数连续重复 `expr[*N]`，见 [当前重复范围](sequence-repetition.md)。下文的重复缺口限于空/范围/无界重复。

单时钟 `assert/assume/cover property` 新增固定周期串接：

```systemverilog
property p;
  @(posedge clk) disable iff (reset)
    request |-> ##2 grant ##0 ready ##1 done;
endproperty
check_p: assert property (p) passed++; else failed++;
```

支持直接 `a ##N b` 序列、`|->` / `|=>` 的多阶段后件及后件的前导 `##N`。`|=>` 在首阶段的延迟上额外加一拍。`##0` 在同一时钟的采样值上连续检查。周期数可为数字、参数名或括号中的整数常量表达式，包含参数/generate 克隆；总跨度最多 65536 拍，最多 256 个条件。时钟仍须为一个静态整数信号的显式 posedge/negedge。

每个时钟建立独立尝试；前一尝试未结束时，可以继续触发后续尝试。任一条件为假或 X/Z 时，该尝试立即失败，全部条件通过才执行通过动作；cover 忽略失败尝试。蕴含的假 antecedent 不执行通过动作。异步 `disable iff` 脉冲清除全部在途尝试，采样函数历史仍按时钟前进。进程、所有阶段读依赖及采样依赖进入分区；待检查阶段、剩余拍数、结果和采样历史归 Sim 所有，随 checkpoint 一起恢复。无序列的简单断言继续使用原有路径。

仍缺：延迟范围/无界等待、空/范围/无界重复、序列 antecedent、序列/属性组合运算、first_match、property 形参/局部变量、多时钟、default clocking、bind、程序内并发断言及完整覆盖率。未据此宣称支持完整 SVA 或 UVM；沿用既有 property 表达式、动作块和时钟的限制。DWF 编码未改，本批没有性能对标结论。

验收与 VCS 差分见 [M87](../validation/m87-sequence-delays/README.md)。测试故意触发失败尝试以检查失败动作，VCS 自带的失败位置诊断与 dsim 不作文字一致性声明；逐拍 TRACE 计数和共同信号的完整 settled 时间线作为语义对齐依据。

固定重复、括号组和命名有限 sequence 已由 [M136](sequence-repetition.md)、[M137](sequence-groups.md)、[M138](named-sequences.md) 接通；完整 SVA 仍未实现。
