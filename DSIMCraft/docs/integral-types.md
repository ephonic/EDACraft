# 四态 integer、time 与类型化端口

支持 32 位四态 `integer` 的默认 signed、显式 `signed/unsigned`，以及默认 unsigned 的 64 位四态 `time`。这些类型可用于模块/generate/静态过程局部变量、一维 unpacked 数组、类型化循环计数器、模块 input/output、函数形参/返回值和任务 input/output/inout。

```verilog
module stamp(input integer signed value, input time ticks,
             output integer unsigned quotient, output time next_tick);
  always @* begin
    quotient = value;
    next_tick = ticks + 1;
  end
endmodule

function time next_stamp(input time value);
  begin return value + 64'h100000000; end
endfunction

integer unsigned total = 0;
initial begin
  for (integer unsigned i = 0; i < 4; i++) begin
    #1;
    total += i;
  end
end
```

`integer unsigned` 的除余、比较、算术右移、十进制打印和向更宽表达式转换使用 unsigned 规则；`integer signed` 使用 signed 规则。选择后的值仍为 unsigned。`time` 的值保留完整 64 位；表达式、普通/延迟 NBA、任务值复制、位/部分选择、数组读改写和现有回滚/独立域并行共同接入。

模块类型化端口支持 ANSI 形式及 `input integer x; output time q;` 这样的非 ANSI 声明；固定宽度分别为 32/64 位，integer 默认 signed，time 默认 unsigned。类型化 input 使用方向性复制，首次复制安排在子模块事件控制就绪之后，让 `always @*` 能响应端口的初值变化。output 实参仍要求父模块 net；不支持整数/time variable inout 模块端口或带 packed range 的整数/time 声明。

子程序形参保留声明的符号属性，不再把所有整数形参强制设为 signed；`function integer unsigned` 和 `function time` 按结果类型转换。parser 只绑定子程序运行时变量，不用其初值缓存折叠表达式，避免将合法的宽位运行时除法错误送入有限的常量求值路径。新增类型保持直接 C++ 生成，运行时状态布局不变，门级 parser 不变。

`int` 已在后继 M19 改为标准两态存储；`bit/byte/shortint/longint` 也已接入，见[两态类型说明](two-state-types.md)。M18 的四态对照使用 `integer`，历史验收记录保留。`time signed/unsigned` 修饰语不在支持范围；实际 VCS 参考版本拒绝这些形式中的 `time signed`。VCS 也拒绝 time 输出端口的声明初始化，共同用例使用过程初始化；不宣称该扩展形式与 VCS 一致。automatic/递归/常量函数、完整声明初始化、整数类型参数、完整 cast、数组端口和变量输出实参仍待补齐。

```sh
ctest --test-dir build -R '^rtl_integral_types$' --output-on-failure
python3 validation/m18-integral-types/verify.py
```

验证范围和原始证据见 [M18](../validation/m18-integral-types/README.md)。本批没有新的速度测量。
