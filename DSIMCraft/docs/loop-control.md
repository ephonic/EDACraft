# RTL 过程循环控制

支持过程 `for/while/do-while/repeat/forever` 中的 `break`、`continue`，以及语句位置的前置/后置 `++/--`。`for` 支持逗号分隔的阻塞初始化/迭代语句、空初始化/条件/迭代，以及 `for(int ...)` 或 `for(integer ...)` 的一个或多个计数器声明。

```verilog
integer total = 0;
initial begin
  for (int i = 0, j = 9; i < 8; i++, --j) begin
    #1;
    if (i == 2) continue;
    if (i == 6) break;
    total = total + i + j;
  end
end
```

`break` 退出最近一层过程循环；`case` 不构成循环边界。`continue` 在 `for` 中执行迭代列表后重新判断条件，在 `repeat` 中消耗本次次数，在 `do-while` 中跳到尾部条件。`while/forever` 按各自循环入口继续。跳转可跨越本轮剩余的赋值、delay 和分支，已排定的延迟 NBA 继续交付。

inline 计数器属于循环的独立词法作用域，可以遮蔽外部同名变量，循环结束后不可直接访问。初始化在每次进入循环时执行，支持读取运行时变量及前面已初始化的计数器。无显式初始化的 inline 整数计数器按当前 VCS 对照结果在每次进入时设为 0；普通模块/静态块中未初始化的四态整数仍为 X。底层使用固定 Signal 存储，本批没有实现多次并发激活时的 automatic 存储栈。

`++/--` 更新沿用普通四态加减和目标截断，支持 packed 变量、位/部分选择、宽字和运行时地址的存储器元素。未知输入产生四态算术结果；非法数组地址保持现有不写入规则。语句及循环头部可使用这些操作，后继批次也已接入 `j=i++` 等[表达式结果](increment-expressions.md)。

独立 RTL parser 负责 AST 类型、作用域和参数化实例克隆，门级紧凑 parser 保持独立。编译器将更新/跳转降低为已有过程指令及固定 PC，连接现有 delay、NBA、依赖、独立域并行、VCD/DWF 和失败预测回放；不增加运行时的循环解释器。

仍未支持：循环头部 NBA/时间控制、复合赋值表达式返回值、带标签跳转、`disable`、automatic/并发激活、完整子程序语义。无限零时间循环依旧受现有执行预算保护。本批不是完整 SystemVerilog 过程语法实现，也没有新的 VCS 速度测量。

回归入口：

```sh
ctest --test-dir build -R '^rtl_loop_control$' --output-on-failure
python3 validation/m14-loop-control/verify.py
```

实际验收和 VCS 导出范围见 [M14](../validation/m14-loop-control/README.md)。

静态用户函数/任务已在后继批次接入，支持范围及剩余 automatic/递归等限制见 [子程序说明](subroutines.md)。

循环初始化/迭代已支持十二种 [复合赋值](procedural-actions.md)，静态子程序内的 return 可直接退出调用。

循环头部也已接入显式 `integer signed/unsigned` 和 `time` 计数器，见[类型与端口说明](integral-types.md)。

inline for 的 byte/shortint/int/longint 两态计数器已接入，默认值和类型边界见[两态类型说明](two-state-types.md)。

后继批次已接通 [foreach 静态遍历](foreach.md)，支持现有静态数组/packed 位维度、多索引与跳过维度、只读自动索引及跨延时回放。
