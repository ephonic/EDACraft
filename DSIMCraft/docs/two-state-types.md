# 两态整数与 bit

RTL 编译器支持两态 `bit`、8 位 `byte`、16 位 `shortint`、32 位 `int` 和 64 位 `longint`。`bit` 默认 unsigned，其余四种默认 signed，均可显式 signed/unsigned。`bit` 可带现有降序 packed 范围（最多 1,048,576 位）；固定宽度整数不能再带 packed 范围。`integer` 仍是 32 位四态 signed，`time` 仍是 64 位四态 unsigned。

```verilog
bit [79:0] mask;
byte signed delta;
int unsigned count;
longint total;
initial begin
  delta = 8'b1xz001zx; // 8'h84，signed 值 -124
  count = 32'hxz123456; // 32'h00123456
  for (shortint i = 0; i < 4; i++) begin
    #1; total += delta;
  end
end
```

两态存储在启动时默认为 0，写入时逐位把 X/Z 转成 0，保留已知 0/1。转换发生在变化检测与事件唤醒之前；将 X 写入已经为 0 的两态变量不会凭空产生变化事件。阻塞赋值、位/部分选择、拼接目标、复合赋值、NBA/延迟 NBA、`readmemh/readmemb`、端口及子程序复制共用此路径。大于 64 位的 `bit` 跨字转换同样保留已知位。

支持模块/generate/静态过程局部声明、一维 unpacked 数组、模块 ANSI/非 ANSI input/output、函数形参与返回值、任务 input/output/inout，以及 byte/shortint/int/longint inline for 计数器。两态数组未知/越界读取和 `bit` 未知/越界位选择返回 0；无效写入忽略存储，保留原有地址与 RHS 副作用规则。前置/后置增减复用读取、截断和单次地址求值。实际 VCS 探针还确认：除零等表达式仍可产生 X，赋给两态目标时才转成 0，不能对所有算术表达式一律清除未知位。

子程序沿用静态生命周期。实参写入两态形参时转换，函数返回变量按返回类型存储，任务返回时再按实际目标类型复制。类型化 input 的首次复制在事件监听就绪后执行。模块 output 实参仍要求 net，模块 variable inout、数组端口、多维/整体数组、类型参数、类型/尺寸 cast、automatic/递归/常量函数和完整 SV 类型系统仍未支持。`for(bit …)` 声明式循环头部不在本批范围，已有 bit 变量可作为循环计数器使用。

RTL parser 保留独立的 `int`/`integer` 类型，类型信息和函数结果类型参与参数化克隆。门级 parser 保持独立。编译器仅为含两态声明的模型启用 `DSIM_TWO_STATE_ENABLED`；普通四态/门级模型不会加入两态标记或转换分支。两态仍使用现有值容器，这一批没有将其压缩成专用二态数值布局，也没有新的速度测量。

```sh
ctest --test-dir build -R '^(rtl_two_state|two_state_kernel|two_state_compact)$' --output-on-failure
python3 validation/m19-two-state/verify.py
```

验收范围及原始证据见 [M19](../validation/m19-two-state/README.md)。

兼容变化：`int` 不再是 `integer` 的四态别名。M19 曾遗留 `parameter int`/`localparam int` 入口退化，已由 [M20 类型化值参数](typed-parameters.md)修复，并接入默认值/覆盖时的目标宽度、符号与两态转换。
