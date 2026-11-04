# SystemVerilog 验证构造

M45 补齐[表达式事件控制](event-expressions.md)，覆盖动态选择、数组字、四态边沿和混合事件列表；事件表达式中的用户函数、iff、动态进程和完整验证环境仍待实现。

M44 新增[静态命名事件同步](named-events.md)，支持发生等待、triggered 条件以及阻塞/NBA/延迟触发，已做实际 VCS 功能对照；完整事件对象模型、wait_order/fork 和动态验证环境仍缺。

以 [IEEE 1800-2023](https://standards.ieee.org/ieee/1800/7743/) 作为语言路线基线，逐项接入语法、AST、展开及运行时语义，当前实现仍是明确列出的子集。RTL/SV 行为前端与门级紧凑前端保持独立。

现已支持普通过程立即断言 `assert`、`assume` 和 `cover` 的条件及动作，包括标签、空动作、成功/失败动作、嵌套 if/case/循环、静态函数/任务、参数化模块和 generate 克隆。

```systemverilog
int failures, hits;
initial begin
  checked: assert (count == expected)
    hits++;
  else begin
    failures++;
    $error("count=%0d expected=%0d", count, expected);
  end
  assume (ready) else $fatal(1, "ready is required");
  cover (count > 0) hits++;
end
```

条件只求值一次，保留增减、函数调用及短路副作用。按普通四态布尔规则判断：确定为真执行成功动作，0/X/Z 执行失败动作；多位条件存在已知 1 时仍可为真。无成功动作可写 `assert(cond) else statement;`；无动作可写 `assert(cond);`；`assert(cond); else ...` 不合法。cover 没有失败动作。

立即 assert/assume 缺省失败时输出带类别、层次/标签及源码行号的 error 诊断，继续仿真；显式空 else 会抑制缺省诊断。普通仿真中的立即 assume 按检查条件执行。cover 当前接通条件与成功动作，可由动作记录命中；**尚无自动 cover 计数、覆盖数据库或报告**。断言类别与标签保存在 AST，并参与实例/generate 克隆；没有把并发 SVA 降成普通 if 来执行。

新增 `$fatal/$error/$warning/$info`，支持现有常量格式串及整数/四态参数、`%b/%d/%h/%x/%o/%t` 和字段宽度。severity 消息带层次及源码行；输出格式采用 dsim 自身格式，不承诺与 VCS 文本逐字一致。`$error/$warning/$info` 输出后继续；`$fatal;` 或 `$fatal(0/1/2[, format, args...]);` 输出后以非零退出码终止，不能执行后续语句。finish number 目前要求常量 0/1/2，复杂消息参数及运行时字符串仍未支持。

动作复用已有控制流与事件调度，支持 delay/event/NBA。普通诊断使用已有输出事务：失败预测丢弃推测输出，正确回放仅输出一次；fatal 异常在预测中恢复检查点后向外传播。带输出的过程参与现有副作用分区约束；无输出的自检动作可以在独立域双线程执行。覆盖动作的用户计数器走普通状态/检查点，不引入额外全局统计状态。

以下继续明确拒绝：deferred `assert #0`/`assert final`、concurrent `assert property`/`cover property`、property/sequence、clocking block、并发采样/Observed/Reactive 调度、class/randomization 和 covergroup。完整类型端口/类型参数及 cast、package/import/interface/modport、动态数组/queue/string、automatic/递归、DPI/VPI 和 UVM 仍按 [计划](../plan1017.md) 分阶段推进，不能把当前子集当成完整 IEEE 1800-2023 支持。

```sh
ctest --test-dir build -R '^(rtl_immediate_assertions|rtl_semantic_memory)$' --output-on-failure
python3 validation/m21-immediate-assertions/verify.py
```

范围和实际验收见 [M21](../validation/m21-immediate-assertions/README.md)。

M26 接入[整数/位向量系统函数](system-functions.md)，可在上述立即断言中检查 X/Z、已知 1 的数量和 one-hot 条件；尚无并发采样语义。

M43 新增[wait(condition)](level-wait.md)，含函数实参敏感集合、automatic task 挂起/重入、NBA 唤醒及失败预测回滚；同时接通 function logic/reg 默认/显式 signed/unsigned 与 packed 返回范围。wait fork/wait_order 及完整事件区域仍缺，验收见 [M43](../validation/m43-level-wait/README.md)。
