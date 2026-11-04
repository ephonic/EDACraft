# 静态 net 数组

RTL 编译器支持 wire/tri 的静态 unpacked 数组，包括多维、非零非负下界、不同声明方向和宽 packed 元素。每个元素使用现有 net 信号槽，未驱动值为 Z；连续赋值和门原语按元素驱动，多个驱动逐位解析。支持动态下标读取、已有数组查询及固定下标的位段选择。RTL 与紧凑门级 parser 继续分开。

模块 input/output/inout net 数组可以连接整数组或常量下标前缀选择的子数组，剩余秩、各维大小及元素位宽必须相同。元素按每维声明顺序对应。两端均为 net 时，编译期将对应元素合并为一个 net，不生成往返赋值过程；因此 input 内部驱动能够反向传播，inout 能正确解析多驱动并在撤销驱动后回到 Z。IR 的 binding 为 collapsed_net，array_elements 中两端为同一规范信号 ID。

```systemverilog
module pad(inout wire[3:0] p[3:2], input logic en);
  assign p[3]=en?4'ha:4'hz, p[2]=en?4'h5:4'hz;
endmodule
module top;
  tri[3:0] p[0:1];
  logic en, host;
  pad u(p,en); // p[0] 与 u.p[3] 为同一 net
  assign p[0]=host?4'h5:4'hz;
endmodule
```

net 与变量之间的 input/output 沿用单向逐元素适配；变量目标执行两态转换和单驱动检查。inout 实参必须为 net 数组。悬空 net 元素默认 Z，悬空变量数组仍为四态 X/两态 0。过程赋值及 readmem 对 net 数组明确报错，不能绕过 net 解析直接改写存储。

延迟使用已有惯性 net 驱动事件，NBA 可作为激励；没有引入新的调度内核。串行、时间轮、双线程、VCD/DWF、检查点及失败预测回放由 tests/net_arrays 回归核验；同源 VCS 比较逐位时间线，并以 packed 观察信号核对未直接导出的每个数组字。证据见 [M40](../validation/m40-net-arrays/README.md)。

仍不支持变量 inout/ref、动态数组/队列/关联数组、动态连续驱动目标、数组 slice/拼接/赋值模式/整体复制、负 unpacked 边界、enum/聚合数组端口、命名复合模块类型、数组形参及一般层次数组表达式。多维 readmem 和 net 整体声明初始化仍缺。保持既有 packed 范围和强度限制。M35/M36/M38 历史差异未在本批解决；本批没有新的仿真速度测量。

M41 范围更新：静态变量数组及常量前缀子数组的整体过程复制已接通，覆盖阻塞/NBA、net 源、宽字和 automatic 局部数组；当前类型规则、赋值内 delay 的实际 VCS 差异及仍缺范围见 [数组整体赋值](array-copy.md)。此前文中“整体复制仍缺”的描述以此范围更新，整体声明初始化、数组形参及动态数组仍缺。

M42范围更新：静态数组的动态前缀子数组过程读写/NBA已接通，含越界/未知索引与取样时点，见[数组复制](array-copy.md)；模块端口连接仍要求静态前缀，数组形参及动态容器尚缺。
