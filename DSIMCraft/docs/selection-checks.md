# unique / unique0 / priority 选择检查

RTL 支持 `unique`、`unique0`、`priority` 修饰 if/else-if，以及 case/casez/casex/case inside。限定信息在参数化/generate 克隆时保留；门级紧凑 parser 不变。

- 三种限定都执行源代码中第一个匹配分支。
- unique/unique0 继续检查其他条件或 case item，多个 item 命中报告 overlap；同一 item 内多个标签命中不算重叠。
- unique/priority 在没有 else/default 且没有匹配时报告 no-match；unique0 允许无匹配。
- priority 按顺序检查，命中后不再求值后续条件。unique/unique0 当前按源顺序求值所有条件/item，符合 IEEE 允许的顺序选择。
- X/Z 条件沿用现有四态逻辑，只有真值 1 才命中。case 的全局位宽/符号上下文、casez/casex/inside 规则保持现有实现。

```systemverilog
always_comb begin
  unique case (state)
    IDLE: next = BUSY;
    BUSY: next = IDLE;
    default: next = IDLE;
  endcase
end
```

按 IEEE 1800-2017 12.4.2/12.5.3，检查在语句执行时取样，报告属于调用过程（包括函数/task 内的检查）。当前 Active/Inactive/NBA 集合稳定后确认报告；event/wait 恢复或 always_comb/latch 重触发时，清除该过程尚未确认的报告。delay/#0 恢复不会清除；一次循环的多个违规分别排队。报告队列归 Sim 所有，检查点自动复制，推测打印沿用事务缓冲，失败回放不重复输出。只对使用限定语句的程序启用运行时宏，其他输入不增加队列或调度分支。可能报告的过程仍按现有可观察副作用规则保守合并分区。

不允许在裸 else 后重新加限定符；嵌套独立限定 if 应使用 begin/end。尚不支持完整 assertion control、case matches/pattern、完整 Observed/Reactive 等事件区域或完整 SVA。

与本机安装 VCS W-2024.09 的比较保留以下差异，不能称为全部诊断已对齐：

1. 六组共同源的全部 756 条导出物理位时间线及 TRACE 相同，但报告为 native 12 / VCS 15。events 输入在 0ns 的 initial 入口等待/声明初始化事件，以及 1ns 重新唤醒，VCS 各多报一次；functions 输入在同一时间步重唤醒的调用过程，VCS 多报一次。native 按上述延后确认/逐过程清理规则处理，原输入和完整双方报告保留。
2. 原始 basic 探针含在 unique 条件中调用的函数：VCS 发 IUC 编译告警并忽略检查，实际调用一次；native 继续检查三个条件，实际调用三次。VCS 还抑制同一探针中的后续 unique-if 报告。这个差异不计入共同源一致结果。
3. 报告文本、同刻相对打印顺序由工具决定，本批只核验明确的报告位置、类型、次数及时间，并记录差异。

输入、独立预期和检查脚本见 tests/selection_checks/；证据见 validation/m35-selection-checks/。此外修复了 Flex 在返回 MY_EOF 时提前释放 yytext 的问题，使截断输入的 Bison 错误诊断保持有效；新增三轮错误后重新解析回归。
