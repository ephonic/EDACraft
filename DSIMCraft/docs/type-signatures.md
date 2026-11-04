# 命名类型参数与静态子程序签名

本页记录 M28 的原始范围；后续 M95 已支持标量 `string`/`typedef string` 子程序形参和返回值，当前规则与验收见 [字符串支持范围](strings.md)。

已有 integral、enum、packed struct/union typedef 及别名可以用于值参数、函数返回值和函数/task 形参。支持经典与 ANSI 子程序声明；命名类型必须已在当前词法作用域中可见。模块体、generate、静态子程序及过程局部参数可以组合使用；实例/generate 克隆分别重新绑定类型和范围。

```systemverilog
typedef logic signed[7:0] byte_t;
typedef enum logic[1:0] {IDLE, BUSY, DONE} state_t;
typedef struct packed {state_t state; byte_t data;} packet_t;
localparam packet_t INIT=10'h101;
localparam byte_t START=INIT.data;

function byte_t add(input byte_t a, input byte_t b);
  begin return a+b; end
endfunction

task change(input byte_t delta, output packet_t result);
  begin #2 result=INIT; result.data=add(START,delta); end
endtask
```

参数默认值和受支持的实例覆盖使用目标宽度求值，保留声明 signed 和 packed 边界。命名 aggregate 参数保留成员布局，可用于常量成员访问、后续参数和 `$bits`/范围查询。直接常量拼接初始化参数也已接通。模块采用参数头时，覆盖列表仍按头部参数处理；本批体内命名类型参数的覆盖用例使用传统体内参数声明。

函数实参先按各自表达式求值，再转换到形参宽度；函数结果按声明符号参与外层扩展。任务 input/inout 入口复制，output/inout 返回时复制，延迟和提前 return 沿用现有语义。enum 形参、结果赋值、`return`、任务复制和 enum 参数要求同一 enum 身份或显式 cast；普通别名保持身份。整体 packed 聚合赋值采用位向量转换，不逐成员检查 enum。

全部两态的类型在存储/复制边界清除 X/Z；混合聚合的底层位保留 X/Z，读取 bit 成员才转换，沿用 [packed 聚合规则](packed-aggregates.md)。声明位宽/范围和身份只用于编译展开，运行时沿用现有字级向量、静态信号和 PC 指令，没有运行时类型分派。RTL 与紧凑门级 parser 保持独立。

本批四例覆盖 signed/非零下界、130 位两态值、混合/全两态聚合、别名与 enum、嵌套调用、经典/ANSI 形参、任务 delay、NBA 取样、实例/generate/局部绑定、回放和真实双分区。

仍未支持：`parameter type`、模块命名类型端口、package/import/编译单元 typedef、追加 packed 维度、数组参数/形参、参数的位/部分选择、函数形参默认值/省略方向/ref、automatic/递归/常量函数和完整并发激活。参数声明目前要求初始化值；未提供默认值而仅由实例覆盖的参数也未接通。匿名/非 packed 聚合、赋值模式及完整层次引用仍缺。

VCS 差分中保留四个 generate 函数返回变量的精确名称对应，全部位均比较，没有信号排除。原始未调用的全两态 packed-struct 形参初始 dump 在 VCS 中为 X、dsim 中为 0；原输入与波形保留，不能宣称其初始波形相同。共同并行用例在零时刻执行一次初始化调用；未据该 dump 差异推断内部原因或改变类型转换规则。详细证据见 [M28 验收](../validation/m28-type-signatures/README.md)。本批没有新的速度测量。
