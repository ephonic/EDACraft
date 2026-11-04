# RTL signed 运算

支持当前 packed `reg/logic/wire/tri` 类型的 signed 声明，包括模块端口、一维存储器元素及参数。位宽继续为 1–1,048,576；packed 范围保持降序限制。RTL 与结构门级前端仍分开，结构门级 parser 的 signed 语法没有扩展。

```verilog
reg signed [7:0] a, b;
wire signed [15:0] sum = a + b;
wire signed [15:0] quotient = a / b;
wire signed [15:0] shifted = a >>> 2;
initial begin a = -7; b = 3; end
```

已接通：

- 赋值/端口的符号扩展；一维存储器整字保持元素类型，packed 位选/部分选择结果为 unsigned。
- 一元负号、带负号和 X/Z 的 signed 常量；共同类型/上下文位宽传播；混合 signed/unsigned 运算使用共同 unsigned 类型。
- 两个 signed 操作数的关系比较、除法与余数；除法向零截断，余数符号随被除数。未知数据/除零沿用四态 X 结果。
- `>>>` 算术右移和 `<<<`；算术右移的类型取左操作数及其上下文，位移量自定宽。保留 `>>` 逻辑右移。
- `$signed/$unsigned` 类型转换、signed 三目分支、signed 拼接/复制项（拼接结果 unsigned）、case 的共同类型。
- signed `%d/%0d`；VCS 默认 signed 十进制字段按至少 32 位计算。打印元数据只传给输出函数，没有扩大 V/信号/事件状态布局。
- signed 负 repeat 次数跳过；延迟赋值、组合依赖、波形、线程分区及已有 checkpoint/predict 回放。

常量正数的隐含高位现已在 RTL parser 分配实际存储，保证 65 位等常量取负/取反时处理整个声明位宽；带未知位的常量取负得到全 X。生成模型仍直接调用原有无符号算术模板，只有需要符号扩展、signed 比较/除余、算术右移时才选择新辅助函数。没有本批整体速度测量。

限制：这不是完整 IEEE/SystemVerilog signed 支持。显式 unsigned 整数/整数端口/automatic、类型/尺寸 cast（例如 `16'(x)`）、完整常量表达式求值、负下界 packed 索引等仍有缺口；负地址 unpacked 数组仍拒绝。常量负延迟仍拒绝，运行时负 signed delay 转为无符号时间后可能超过可表示范围并报错；没有完成跨厂商负延迟兼容。通用字符串/real、用户函数/任务、数组端口及完整时序语义也未因此补齐。默认 signed 的 `integer/int` 与过程静态局部声明已在后继 [M13](integer-and-locals.md) 接通。

回归入口：`ctest --test-dir build -R '^rtl_signed$' --output-on-failure`。六例覆盖 75 次波形捕获、3 次失败预测回放、256 组独立 Python 穷举，VCS 比较范围详见 [M12 验收](../validation/m12-signed/README.md)。
