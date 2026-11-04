# 静态数组查询和多控制位计数

M34 已扩展到[静态多维 unpacked 变量数组](multidim-arrays.md)。下文原有单维示例继续适用；当前多维范围和限制以该文档为准。

M27 在独立 RTL/SystemVerilog parser 中接入八项数组查询与 `$countbits`，继续使用直接 C++ 代码生成。门级紧凑 parser 保持独立。

| 函数 | 已实现行为 |
| --- | --- |
| `$dimensions/$unpacked_dimensions` | 返回现有静态类型/对象的总维数与 unpacked 维数 |
| `$left/$right/$low/$high/$increment/$size` | 缺省第一维，支持常量或动态维度实参；先 unpacked 后 packed；保留原声明边界与方向 |
| `$countbits(value, control, ...)` | 自决定操作数宽度，每个控制实参取 LSB，0/1/X/Z 匹配，重复控制去重；结果 signed int |

查询支持现有整数、bit/logic/reg、typedef/enum/packed struct/union、成员和静态数组字；内建类型可附一个 bit/logic/reg packed 范围。静态查询可用于参数、类型范围和 generate；查询结果为 signed 四态 integer，无效或未知维度返回 32 位 X。正负边界及升序类型范围可以查询，实际信号/存储器声明仍受既有布局限制。整体数组不参与运行时取值。

查询对象、数组索引和函数调用实参只用于绑定类型，不执行副作用；动态维度实参执行一次，完整位宽参与选择，高位非零/含 X/Z 不会被截断为合法维度。动态查询仅将维度表达式的读写依赖带入调度。`$countbits` 的每个实参执行一次，控制实参可在运行时变化；宽值按 64 位字扫描并使用原生 popcount，末字掩码避免把填充位算进去。上述能力接入已有 delay/NBA、静态子程序、立即断言、VCD/DWF、预测失败回放与独立域并行。

```systemverilog
logic [7:3] mem [2:6];
localparam D = $dimensions(mem);       // 2
localparam W = $size(mem, 2);          // 5
// $left(mem)=2; $right(mem)=6; $increment(mem)=-1
// $left(mem,2)=7; $right(mem,2)=3
integer d, q;
initial begin
  d=2; q=$size(mem,d++);               // q=5, d=3
  q=$countbits(4'b01xz,1'bx,1'bz);    // 2
end
```

测试包含参数实例/generate 重绑定、signed 返回、原边界/成员/数组字、动态及未知超宽维度、130 位计数、256 种四位四态值与动态控制位。范围依据 IEEE 1800 的数组查询和 bit vector 系统函数条款（[1800-2017，20.7/20.9](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)）；这不表示实现完整标准。

实际安装的 VCS W-2024.09 对部分输入存在限制/差异：拒绝参数常量中的 `$countbits`、超 32 位越界维度参数的求值，以及某些标量对象/函数返回表达式查询；`$countbits(source++,ctl++)` 探针使用了递增后的控制位，dsim 使用后置表达式原值。保留原源/诊断/输出，相关输入作为独立原生检查，不混入共同支持模型差分通过数。详见 [验收记录](../validation/m27-array-queries/README.md)。

尚不支持：完整多维 packed/unpacked 存储与数组端口、整体数组 bit-stream 计数、动态/关联数组及 queue、字符串查询、`$typename`。package/interface、完整类型参数/端口、automatic/递归、并发 SVA、class/randomization/UVM 及完整事件区/时序仍待补齐。本批不提供新的性能对标数字。
