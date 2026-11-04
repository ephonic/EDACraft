# automatic 函数与任务

M145 支持 [包默认生命周期与显式 static 子程序](package-lifetimes.md)。包 automatic 只改变未限定 task/function 的默认值，包变量继续静态共享。

M63 新增[无尺寸数组 input/inout 值形参](open-arrays.md)，支持固定数组实参；动态分配与动态数组引用仍未接通。

M62 已支持 [const ref 只读引用](const-ref.md)，固定数组形参见 [M61](array-arguments.md)；后文相关未支持描述是历史边界，以新文档为准。

M61 支持[固定 unpacked 数组形参](array-arguments.md)，覆盖 input/output/inout/ref、多维及子数组、默认/命名调用；下文历史数组形参限制以新文档为准。

M60 支持 [ref 引用形参](ref-arguments.md)：完整变量与固定数组元素共享实际存储，即时写入、挂起、嵌套、取消和回滚；后文 ref 限制为历史范围，当前边界以新文档为准。

M59 新增 [wait_order 有序事件等待](wait-order.md)：成功/失败分支、重复事件、NBA 顺序、automatic task、fork 取消/复用及预测回滚。

M58 支持 [显式 static 局部声明](explicit-static.md)：automatic 子程序跨调用共享持久变量、数组和静态 event，接通一次初始化、NBA、波形、分区和回滚。

M57 支持 [显式 automatic 局部声明](explicit-automatic.md)：默认静态任务/函数和过程块可指定自动局部变量；混合静态存储、fork 捕获及生命周期范围以新文档为准。

M55 增加 [automatic 动态变量帧](automatic-fork.md)，支持重叠 fork 调用、父帧共享及任务返回后的存活分支。下文固定调用槽的限制保留为 M31/M54 历史范围；当前 foreach 隐式索引/递归等限制见新文档。

M54 支持[静态存储 fork 分支的重叠激活](dynamic-fork.md)。automatic 父帧逃逸及重叠分支的动态变量帧仍未实现；非重叠分支调用阻塞 automatic 子任务已支持。

M46 新增[条件事件控制](conditional-events.md)，条件读参与分区合并，源取样与待求值任务随快照恢复；真实 VCS 范围见 [M46](../validation/m46-conditional-events/README.md)。

M45 支持 automatic task 内的[表达式事件控制](event-expressions.md)，挂起入口重取样，避免把形参初始化当成事件；缓存、队列和等待位置随既有激活状态回滚。

M44 接通 automatic task/function 对词法外部[静态命名事件](named-events.md)的等待/触发；事件触发不把对象变为 automatic 存储，automatic 局部 event 仍拒绝。

模块和 generate 词法作用域内支持非递归 `function automatic` / `task automatic`。ANSI、经典形参、隐式一位返回类型、内建整数/packed 返回类型、命名 typedef/enum/packed 聚合返回类型与形参、默认及命名实参均接入编译路径。RTL parser 与紧凑门级 parser 分开维护。

每次调用先取样 input/inout，再初始化 output、返回变量和局部变量：四态为 X，两态为 0，随后按声明顺序执行局部初始化表达式。初始化可以读取实参、前面声明的整数变量，或调用受支持函数并产生外部副作用；同一 integer 声明的各声明项按顺序解析和绑定。未写的 output/返回值不保留上次调用值。嵌套过程块的 automatic 变量在每次块入口重新初始化，包括循环迭代。单维局部数组逐字初始化；whole-array 初值和数组形参仍不支持。

```systemverilog
task automatic wait_copy(input integer x, input integer ticks,
                         output integer y);
  integer saved=x+3;
  begin #ticks; y=saved+x; end
endtask
integer a,b;
initial wait_copy(2,5,a);
initial begin #1; wait_copy(7,2,b); end
```

上述两个挂起调用分别保存局部状态，3ns 时 b=17，5ns 时 a=7。output/inout 仍在返回时复制，动态输出地址也在返回时求值；函数结果在输出复制前捕获。函数保持零时间阻塞执行，外部目标上的 delay/NBA 取样可以调用 automatic 函数，调用只执行一次。

实现为调用点与任务调用进程专用的编译激活存储，任务体内联到调用进程，函数生成固定 PC C++ 代码。M55 起变量激活帧支持重叠 fork/动态后代及父任务返回后的局部存储保活，见页首后继说明；递归和通用调用栈仍未接通。状态继续进入现有依赖分析、检查点及回放，不在运行时遍历 AST；automatic 临时状态不导出为静态 VCD/DWF 层次信号，保持与本批 VCS dump 行为一致。

禁止 NBA 写 automatic 变量，包括局部变量、形参、局部数组和部分选择；任务可以使用阻塞延时/事件控制。函数继续拒绝时间控制、NBA、任务调用和系统任务。递归、const ref/数组整体形参、常量函数展开、复杂数组、层次调用及完整 SystemVerilog 生命周期/事件区域仍未补齐。普通 int/logic/命名类型的同一声明内对前序声明项的引用绑定尚未像 integer 一样扩展；本批不宣称所有声明形式完整兼容。

验证入口：`ctest --test-dir build -R '^rtl_automatic_subroutines$' --output-on-failure`。六组用例覆盖重复入口、未写输出/返回值、初始化副作用、局部数组、循环块、重叠 delay/event、类型、默认目标、延时取样、双线程和挂起期间回滚；实际 VCS 同源 TRACE 和全部 1272 条导出物理位时间线一致，无名称映射或位排除。完整验收见 [M31](../validation/m31-automatic-subroutines/README.md)。没有新的性能测量。

M41 范围更新：静态变量数组及常量前缀子数组的整体过程复制已接通，覆盖阻塞/NBA、net 源、宽字和 automatic 局部数组；当前类型规则、赋值内 delay 的实际 VCS 差异及仍缺范围见 [数组整体赋值](array-copy.md)。此前文中“整体复制仍缺”的描述以此范围更新，整体声明初始化、数组形参及动态数组仍缺。

M42范围更新：静态数组的动态前缀子数组过程读写/NBA已接通，含越界/未知索引与取样时点，见[数组复制](array-copy.md)；模块端口连接仍要求静态前缀，数组形参及动态容器尚缺。

M43 新增[wait(condition)](level-wait.md)，含函数实参敏感集合、automatic task 挂起/重入、NBA 唤醒及失败预测回滚；同时接通 function logic/reg 默认/显式 signed/unsigned 与 packed 返回范围。该批验收见 [M43](../validation/m43-level-wait/README.md)。
