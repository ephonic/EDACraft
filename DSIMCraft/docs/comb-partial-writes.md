# 组合过程的整字与局部写混用

`always_comb` / `always_latch` 现在接受同一过程内对变量整字赋值、局部改写、随后读取，例如：

```systemverilog
always_comb begin
  flags = in_a;
  flags[AW-1] = in_b[0];
  next_word = out_word;
  if (flags) next_word = in_data;
end
```

支持静态位/片选、动态 indexed part-select、宽 packed 值、固定数组整表复制后元素修改，以及嵌套函数的全字写副作用。整字写按语法依赖处理，允许位于条件分支中；不要求每次执行都写入。写入变量不加入本块的隐式自触发，外部读和函数读依赖仍参与调度与分区。没有增加运行时状态，已有 checkpoint/rollback 按现有信号和过程状态恢复。

动态目标用于“多个写过程是否冲突”的保守范围与真正的整字写分开记录。否则 `q[i]=q[0]` 会被误认为写入整个 q，丢失 q 的未写位敏感性。

静态局部写且读取同一变量的形式，现已由[位区间敏感性](comb-bit-sensitivity.md)支持，包括多个部分写覆盖整字。动态写目标若缺少整字写，仍保留明确诊断。其他过程对同一位的写入、非法 timing control 等检查继续生效。

另修复有符号负下标 indexed part-select 的裁剪读写。`q[-2 +: 4]` 的动态等价形式会写入仍在范围内的位；不可读位为 X，使用正确 RHS 偏移。128 位下标仍有已知 VCS 差异：VCS 在部分探针中对超宽位置作有效窄化/范围处理，而 dsim 检查整个位置值；共享边界探针保留双方原始输出和全部差异，不宣称这部分已对齐。见 [indexed-selects](indexed-selects.md)。

永久回归：`tests/comb_partial`。包含用户原始 193 事件用例，两原始源 SHA256 保留在 `reported/provenance.json`。
