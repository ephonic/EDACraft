# 实数执行与波形

RTL 前端区分 `real`（64 位）和 `shortreal`（32 位）；`realtime` 是 `real` 的别名。
类型信息贯通常量、参数、typedef、普通变量/端口、固定数组、类属性和函数/task 调用。
支持算术、幂、关系和逻辑运算、类型转换、赋值/NBA、浮点 DPI import、
`$itor`、`$rtoi`、`$realtobits`、`$bitstoreal`、`$shortrealtobits`、
`$bitstoshortreal`、`$realtime` 和浮点格式输出。

实数赋给整数时取最近整数，半整数向远离零的方向舍入；`$rtoi` 向零截断。
整数转换为实数时逐位将 X/Z 置零，保留源整数的有符号性。
`shortreal` 与整数混合时按单精度转换；存在 `real` 操作数时采用双精度。
分数延迟按模块 timeunit/timeprecision 转换到仿真 tick。

固定实数数组已经有层次读取执行回归。动态实数容器仍明确拒绝；实数 `inside`、
数组规约、格式化输入和常量函数等尚未完整验证。这批实现不表示所有实数语义、
完整 SystemVerilog 或完整 UVM 已支持。

## 指定波形范围

先编译带波形支持的模型，再由用户选择运行时输出范围：

```sh
dsim tb.sv --wave-support -o simv
./simv --waveform selected.dwf --wave-async \
  --wave-scope top.dut --wave-include '*result*' \
  --wave-start 100 --wave-end 200
```

范围参数沿用现有波形选择规则，时间以模型 tick 为单位。独立线程接收事件，
进行块编码、Zstd 压缩、校验及写盘。同步和异步编码结果逐字节一致；
预测回滚撤回尚未提交的事件，范围起点保留所选信号的当前值。

含实数的 DWF 元数据使用 `dsim.wave.prototype.v2`，每个实数信号声明
`"type":"real"` 和 32/64 位宽；纯数字文件保持 v1。压缩事件保存 IEEE 原始位，
保留 NaN 载荷、无穷与负零。仓库的 Python decoder 同时读取 v1/v2。
这是 DSIM 自有格式，不是 FSDB 二进制格式。

`--wave-format vcd` 输出标准文本实数值；文本 NaN 无法保存其载荷，
因此 VCD 数值一致性和 DWF 原始位一致性分别验证。

## 验证范围

`tests/real_values/regression.py` 执行九个模型的串行、时间轮和双线程请求，
覆盖 ordered/settled、VCD、同步和异步 DWF；检查真实双分区时间线、
预测回滚/提交、用户范围选择与非法类型用法。
这组测试不构成完整 UVM、全部实数边界或 VCS 性能对齐证明。
