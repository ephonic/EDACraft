# 模块与 interface 的默认生命周期

支持 `module automatic`、`module static`、`interface automatic` 和 `interface static`。未指定限定符时默认 static。限定符在解析名称后的 header import、参数、端口和正文之前生效，决定该单元中未显式限定的 task/function 生命周期；显式 `automatic` / `static` 覆盖默认值。已有属性、参数化实例、generate 克隆和 modport 子程序原型路径继续适用。

```systemverilog
module automatic worker;
  integer shared = 0;
  function integer fresh(input integer x);
    integer n = 3;
    n += x; shared++; return n;
  endfunction
  function static integer kept(input integer x);
    integer n = 3;
    n += x; return n;
  endfunction
endmodule
```

同一实例连续调用 `fresh(2)` 都返回 5，而 `kept(2)` 返回 5、7。模块/interface 自身变量仍为每实例静态对象；显式静态子程序或 automatic 子程序内显式 static 局部跨调用保留，但不同实例不共享这些存储。包存储仍唯一共享。

automatic task 的挂起调用保存各自局部/数组、实参和输出状态，复用已有 ref、延时、checkpoint 和预测回滚。automatic 存储不能成为 NBA 目标。当前仍要求 ref 子程序为 automatic；VCS 接收部分 static ref 声明，该既有接收差异未在本批消除。Verilog 模式拒绝模块生命周期扩展，仍允许 automatic task 和名为 static 的模块。

本批不新增嵌套模块、编译单元 import、virtual interface、class/UVM 或完整 clocking/SVA。生命周期模型的独立预期、同源 VCS、串行/time-wheel/实际双分区及回放结果见 [M146 验收](../validation/m146-unit-lifetimes/README.md)。
