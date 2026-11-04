# 类、句柄与对象执行

M150/M151 接通 module/package 内非参数化 class 的 RTL AST、生成代码、运行时堆及单继承多态。门级 parser 保持独立。它是 UVM 的基础，完整 UVM package 仍不能编译运行。

支持类类型/typedef、`null`、`new`/`new()`、构造器及默认/命名实参、`this`、句柄赋值/别名和同类句柄比较。构造器实参先求值一次。对每一层继承，先执行直接基类构造器（显式 `super.new` 或隐式默认调用），再执行本层属性初始化及构造器体；无显式构造器时也保留这一顺序。对象默认值为：二态整数零、四态 integral X、string 空串、对象句柄 null。

支持 integral（含 signed、宽 packed 四态）、string 和其他类句柄属性；字段读写、packed 选择、整数更新、嵌套对象；automatic function/task 方法、隐式或显式 this、嵌套方法、句柄参数/返回和完整句柄变量 ref。带延时方法复用独立 activation；字段存于对象堆，不因方法返回而清除。参数化 module 的类分别克隆和解析。

字段变化接入事件/等待依赖，堆解引用事件在进入等待时采样，避免在创建对象之前读取字段。普通 checkpoint 和预测事务复制对象堆；恢复后别名仍指向相同对象，失败预测内的分配和字段修改撤销。单个内核中堆相关过程保守归入同一调度分区，独立普通 RTL 仍可并行。

运行时检查空句柄、越界句柄和类身份。每个 Sim 最多保留 1,048,576 个已分配对象；当前没有垃圾回收，置 null 不回收对象。句柄身份是内部实现，不允许把句柄当整数使用。

支持 `extends` 单继承、继承属性及同名字段遮蔽、`super` 成员/构造器调用、派生句柄向基类赋值/值参数/返回及相容句柄比较。`virtual function/task` 按对象实际类型分派，派生 override 可省略 virtual；非虚调用及 super 调用保持静态绑定。接收者与实参只求值一次，默认值来自静态声明；支持延时虚任务、标量 ref/output、固定数组输入、宽四态/字符串/协变类返回。override 签名不相容、隐式向下赋值、类外 virtual、虚构造器及非首条 super.new 会拒绝；ref 句柄仍要求精确类型。与 VCS 一致拒绝在 event/wait 控制中直接调用虚函数。原 REPORT-GAP 的 q01 已接通，仍不能据此声称 UVM 完成。

M152 进一步补入 [virtual class、纯虚方法与动态 $cast](abstract-casts.md)，支持抽象合同检查及转换后的虚方法执行，并明确记录与 VCS 的副作用目标、枚举和无实现 super 调用差异。

M154 加入 `typedef class C;`：前向声明绑定到同一词法列表内的真实 class 定义；类型别名、循环句柄、方法形参/返回/ref、未来基类、同名内层类和参数化 module/generate 的克隆使用对应的类身份。重复前向声明及定义之后的同类前向声明可用；缺少同作用域定义、重复完整定义、非法类型赋值/ref 和循环继承会报错。声明前使用类型仍需前向声明。静态句柄初始化可在完整定义之前调用 `new`，构造器及嵌套 automatic 调用使用启动期独立 activation；构造器读取模块常量初值之前，先完成常量存储初始化。相关初始化依赖也纳入并行分区约束。详见 [M154 验收](../validation/m154-class-forward/README.md)。

M155 补独立 class 句柄的固定数组、queue、动态数组及 int-key 关联数组；元素读取/pop 保留静态类身份，可继续调用字段和虚方法。容器复制是浅复制，派生到基类容器转换保持实际对象类型；不隐式向下转换。详见[容器边界](uvm-containers.md)。

后续 M156/M159/M160/M162 已补编译单元/参数化类、static 成员、关联数组实例属性和部分数组值调用；M163 补入 [local/protected 访问检查](class-access.md)。当前边界仍包括 extern 方法、递归对象构造、实例 queue/动态/固定数组属性、类属性 ref、属性 NBA/延时赋值/拼接写目标、new 的拷贝构造，以及部分 new 类型推断。各特性的细节以对应专题文档为准。支持范围之外应明确拒绝；接受这些基础用例不表示支持 UVM factory 或 sequence。

VCD/DWF 不导出对象句柄和全部动态堆字段。可以把感兴趣的属性映射到 SV 观察变量，再使用既有范围筛选和独立压缩线程输出；普通变量输出仍是标准文本 VCD 或自有 DWF。

后续仍按 [计划](../plan1017.md) 补编译单元类/类型参数、约束随机、mailbox/semaphore/virtual interface、clocking/coverage，再以真实 UVM component/sequence/driver/scoreboard 流程验收。
