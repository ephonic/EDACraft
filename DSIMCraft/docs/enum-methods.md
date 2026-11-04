# 枚举数值遍历方法

支持 `first/last/next/prev/num`，可省略无实参调用的括号。前四者返回原枚举类型，保持宽度及符号，`num` 返回 signed 32 位整数。`first/last/num` 查询声明元数据，普通变量/枚举常量查询折叠，可以用于 parameter/localparam；`first/last` 的复杂运行时接收者（函数、动态下标等）求值一次，保留副作用，`num` 为类型查询，不执行接收者。`next/prev` 求值接收者一次、显式步数一次，按成员**声明顺序**迭代，默认一步，零步保持当前成员，超过成员数回绕。

```systemverilog
typedef enum logic signed [7:0] {LOW=-4, HIGH=9, MIDDLE=2} State;
parameter State LAST = LOW.next(2);
State state;
initial begin
  state = LOW;
  #1 state = state.next(); // HIGH，按声明顺序
  #1 state <= state.prev(2);
end
```

当前值不在成员表时，`next/prev` 返回基类型默认值：两态全零、四态全 X，零步也遵循此规则。成员允许显式 X/Z，使用四态精确匹配。步数转为 32 位无符号，负数按截断后的值处理；为对齐本次实测 VCS，X/Z 步数采用低 32 位 aval（X 位作 1，Z 位作 0）。此项是明确记录的兼容行为，不推广为所有未知整数参数的语言规则。常量求值与运行时使用相同规则。

支持别名、参数实例/generate 克隆、宽枚举、packed 成员、静态多维数组元素，以及已有函数/task、delay/NBA、线程、波形和检查点回放路径。类型和有序成员表只在编译期保存；查询及常量调用折叠，常见不超过 32 位的枚举迭代生成四态键 switch，步数取模，不按步数循环。宽枚举生成精确比较及结果分派。runtime 和门级 parser 不变。

VCS 差异：本次安装 W-2024.09 不保留由枚举方法初始化的无类型 parameter 的枚举身份，`parameter P=A.next(2); parameter R=P.prev();` 报 FNLD。dsim 保留枚举身份并接受后续方法调用；共同模型显式声明 `parameter E P=...`，原始未修改的失败源、日志及 native 检查单列保存。这不是完全类型推断对齐。

函数接收者另有差异：共同 automatic 函数模型中双方均执行接收者副作用；原始静态函数 `get().first()/last()/num()` 探针中，VCS 无 debug 标志时省略全部调用（0 次），带共同对照使用的 `-debug_access+all` 时执行 first/last（2 次）；dsim 执行 first/last（2 次），num 不执行。两套实际命令及输出均保留，不推广某组编译标志的行为为所有查询的规则。

另两个原始探针保留：参数化模块的 `localparam BITS=$bits(FIRST.next())` 在 VCS 中两实例均得到首例宽度 4，dsim 分别为 4/9；同一标签方法置于运行时 `$display` 的 `$bits` 中，VCS 报 XMRE。共同模型使用 `$bits(E)`，宽方法结果另由变量接收者 `$bits(w.next())` 检查。原始标签查询源和双方结果均单列，未计入共同模型一致位数。

VCD 路径表示差异：VCS 把两个 generate 枚举变量导出为转义的 `gen[0].e`/`gen[1].e` 名称，native 导出为 generate scope 下的 `e`。验收仅按显式两项路径表规范化这七个位，保留原始 VCD，严格检查无冲突、完整路径集合及每一位时间线；不删除信号或差异位。VCS 未导出的十二个数组字位另用同源 packed 观察信号完整核验。

限制：`.name()`/字符串、匿名 enum、枚举成员范围展开、类型参数、package/interface/class、方法结果再做 packed 选择及完整方法调用语法仍未补齐。已有 enum 端口及复杂类型限制延续。仅承诺上述五种方法的已测表达式路径，不宣称完整 SystemVerilog/VCS 支持。用例、实际 VCS 对照与平台验收见 [M36](../validation/m36-enum-methods/README.md)。

M81 已补入 [name/name() 与动态字符串](strings.md)，保留四态精确成员匹配及声明名称；前述限制中的 name 项已解除，其他未支持项以对应最新功能文档为准。package/import 的新范围见 [packages.md](packages.md)。
