# 前置/后置增减表达式

支持 `++a`、`--a`、`a++`、`a--` 的表达式结果，可用于赋值右侧、函数/任务实参、条件、短路逻辑、三目表达式、数组/packed 索引和动态 delay。前置返回更新后的值，后置返回更新前的值；更新先按目标自身位宽截断，再按目标 signed 属性参与外层上下文转换。

```verilog
reg [7:0] a = 8'hff;
reg [15:0] q;
integer index = 0;
reg [79:0] words [0:2];
initial begin
  q = ++a;                 // a=0, q=0
  q = a++;                 // q=0, a=1
  q = words[index++]++;    // index 只更新一次
end
```

目标支持 packed 变量、常量/动态位选、固定宽度部分选择及一维数组字/字内选择。动态地址先保存，读和写使用同一地址。未知值沿用四态算术；无效数组地址返回 X 且不存储，右侧副作用仍执行；越界 packed 选择按现有规则局部裁剪。表达式操作数按生成代码规定的顺序求值；对同一变量存在未规定顺序的多个副作用，不提供跨仿真器一致性保证。

`&&`、`||` 和已知条件的三目表达式只执行被选择的分支；未知条件按四态规则求值。延迟阻塞/NBA 赋值在取样右值时执行自增，交付时不再次执行。任务 input 仍按值复制，形参自增不修改调用者变量。

RTL parser 保存四种运算身份并支持参数化模块/generate 克隆，语义遍历不执行运行时副作用。编译器生成直接 C++ 读改写代码，并记录读写及部分更新依赖，接入现有波形、失败回滚和独立域并行。门级 parser 和运行时状态布局不变。

仍缺复合赋值的表达式返回值、非恒定选择宽度、整数组操作、automatic/递归/常量函数和完整 SystemVerilog 子程序语义。只读常量、net 和非左值增减明确拒绝；不能将本批视为完整 SystemVerilog 兼容。

```sh
ctest --test-dir build -R '^rtl_increment_expressions$' --output-on-failure
python3 validation/m17-increment-expressions/verify.py
```

范围和实际验证证据见 [M17](../validation/m17-increment-expressions/README.md)。本批没有新的速度测量。
