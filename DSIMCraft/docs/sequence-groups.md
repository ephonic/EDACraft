M140 已支持有限序列作为蕴含前件，见[当前范围](sequence-antecedents.md)。下文关于前件仅限布尔表达式的描述是历史边界。

# 有限括号序列与子序列重复（M137）

支持把单时钟固定周期序列作为括号组，继续串接或按固定正数重复，包含嵌套组合。例如：

```systemverilog
assert property (@(posedge clk) disable iff (reset)
  request |-> (ready ##2 done)[*3] ##0 accepted)
  passed++; else failed++;
```

每个子序列内部保留原有周期距离；相邻重复之间隔一拍。上例在偏移 0/2、3/5、6/8 检查 ready/done，并在第 8 拍检查 accepted。`##0` 可以连接组内部或外部的条件。普通布尔括号继续由表达式语法处理；只含布尔表达式的固定重复仍遵循 M136。解析器为组体和后续序列保留独立所有权，避免把括号后的串接错误地重复。

编译器在参数展开后生成有限阶段列表，每个词法采样函数只降低一次，随后共享不可变表达式；重复不会多推进 `$past` 等采样历史。运行时复用原有独立尝试、Reactive 动作、异步取消、检查点和预测提交/回滚。RTL 与门级 parser 保持分离，没有改动 runtime 头文件。

计数须为已知整数常量 1..256；整体展开最多 256 个条件、总跨度最多 65536 拍、括号 temporal 组嵌套最多 128 层。表达式须为受支持的纯 integral 子集。不支持空/范围/无界重复、goto/nonconsecutive 重复、sequence antecedent、局部变量、多时钟或完整 SVA；这些输入仍明确拒绝。弱的未完成尝试在自然结束时不额外报错。

验收与稳定版发布记录见 [M137](../validation/m137-sequence-groups/README.md)。本批优先功能，没有速度测量或完整 VCS 兼容声明。

M138 已补齐[命名有限 sequence](named-sequences.md)，包含嵌套/前向引用和词法作用域绑定；形参、局部变量和完整 SVA 仍未支持。
