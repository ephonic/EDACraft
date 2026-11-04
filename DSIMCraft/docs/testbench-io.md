# 运行参数与动态格式化

M102 为生成的本机仿真程序接入 `$test$plusargs`、`$value$plusargs`、`$sformatf` 与 `$sformat`。

```systemverilog
string path="input.hex", message;
int seed=1;
initial begin
  void'($value$plusargs("seed=%d",seed));
  void'($value$plusargs("input=%s",path));
  message=$sformatf("%m seed=%0d file=%s",seed,path);
  $display("%s",message);
end
```

```sh
dsim test.sv -o test_sim
./test_sim +seed=123 +input=memory.hex
```

参数在生成程序运行时读取，可以与 `--waveform`、`--wave-mode` 等原生参数交错。前缀查询返回32位整数；空查询返回0。值查询按命令行顺序使用第一个匹配项，无匹配时返回0且保持目标值。`%s` 保留参数值中的空格；写 packed 变量时按低位字节截断。空 `%s` 值写动态字符串为空串，写 packed 目标为字符 `0`，匹配实测 VCS。数值格式使用完整后缀，非法字符产生 X，再由目标类型执行二态转换；空数值后缀写0。支持 `%d/%h/%x/%o/%b/%s`，格式要求恰好一个末尾转换项。目标接入普通变量、数组元素、动态下标、切片、拼接及 automatic/ref 写回；net、enum直接写入、const ref 写入明确拒绝。

字符串格式化支持动态格式字符串，转换项 `%b/%d/%h/%x/%o/%t/%s/%c/%m`、`%%` 与十进制字段宽度。整数保留符号与四态宽值；`%t` 使用现有 `$timeformat`，`%m` 使用静态层次和子程序作用域。`$sformatf` 返回动态字符串，`$sformat` 可写字符串或 packed 目标。packed `%s` 将零字节和未知字节显示为空格，`%0s` 跳过这些字节。

本批接入运行时表达式，不支持将这些调用用于参数常量求值；`%m` 仅支持无字段宽度形式。本批仍不支持实数/浮点格式、`%p/%u/%z/%v/%l`、左对齐/精度及动态字段宽度、完整动态调用栈格式。未实现格式、实参与格式数量不符以及字段宽度超过1048576在运行时明确报错；不支持自动把任意格式解释为有效输出。`$value$plusargs` 的格式后缀、字段宽度以及对字符串目标做数字转换也明确拒绝。额外未知 `+` 参数被接受，未知 `--` 原生选项继续拒绝。

验收覆盖同源 VCS 输出和数值波形、普通队列/时间轮/线程后端、无波形程序、真实两分区、失败预测后的状态/波形/输出恢复以及实际生成程序 sanitizer。范围和发布证据见 [M102](../validation/m102-testbench-io/README.md)。本批没有性能重测。
