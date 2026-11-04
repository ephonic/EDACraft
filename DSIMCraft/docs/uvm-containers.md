# UVM 基础容器与当前边界

M159 新增 [string 键及类关联数组](string-associative.md)，扩展下列历史 M148/M155 的 int 键和独立变量范围；其它键类型、string 元素及类 queue/动态数组仍有缺口。参数化类已于 M156 接通，完整 UVM 仍未完成。

M148 根据用户的 `rtl-tests/complex/REPORT-GAP.md` 增加一维 integral queue 和 int 索引关联数组。原始 `probes3/q05_queues.sv` 已纳入仓库回归。报告中的动态数组 `new[]` 并非全新能力，既有实现及限制见 [动态数组](dynamic-arrays.md)。

M155 扩展命名 integral/enum/class 类型：`typedef T Alias; Alias q[$]`、`E a[int]`、`C d[]` 等均保留元素类型身份。enum pop 后可直接调用 name/next，class pop 后可直接调用字段/虚方法；固定 class 数组也已接通。class 容器浅复制保留共享对象，派生类元素可整体赋给基类容器。包与 automatic 调用的局部存储、预测提交/回滚共用既有运行时。

支持 `int q[$]`、`logic signed [95:0] q[$:N]`、`integer aa[int]` 等独立变量。声明进入 RTL AST，实例克隆分别解析参数化边界；门级 parser 不受影响。

- 队列：`size()`、push_back/front、pop_back/front、insert、delete()/delete(index)、元素及 packed select 阻塞读写、整数更新、`q[q.size()]=value` 追加、foreach、sum/product/and/or/xor 及 reduction with。
- 关联数组：有符号 int 键（表达式截成32位）、size()/num()、exists、first/last/next/prev、delete()/delete(key)、阻塞元素及 packed select 更新、按键排序 foreach 和 reduction。游标参数目前需要完整32位 integral变量；失败时保持原值。
- 整体值复制：队列接收兼容固定数组、队列与兼容动态数组互拷；关联数组同类复制。复制后的内容独立。有界队列整体赋值保留前 N+1 个元素；push_back 满时忽略，push_front/insert 满时丢尾。
- 二/四态、signed 及宽 packed integral 元素；默认空队列 pop/缺失键读取返回元素默认值。关联数组未知键写入报 runtime 错误，对齐本轮 VCS 探针；其他未知键操作不能据此推断全面对齐。
- automatic 子程序/块和重叠延时调用的独立存储、返回/取消清理、依赖分析与实际双分区、普通 checkpoint 和预测回滚。队列 push_back/pop_back 原位修改，避免每次复制整个容器。

边界：不支持 string/aggregate 元素、类属性中的 unpacked 容器、其他键类型/通配键、多维 runtime 容器、容器形参/返回值/typedef、队列 `$` 末元素下标和切片/拼接初始化、关联数组系统维度查询、容器元素 ref 或 timed/NBA 赋值、含此类元素的 concatenation 写目标。未支持路径应明确拒绝。仍保留已有动态数组的形参与 NBA 能力。

动态内容暂不作为可变 VCD 声明导出；验证使用实际 SV 标量观察、TRACE、原生内核检查及已声明物理位波形，不声称 dump 全部堆元素。

完整 UVM 仍不能运行。M150–M152 已接通 [class/堆对象、继承和虚方法执行](class-objects.md)，M155 已补独立对象容器，但参数化/编译单元类、约束求解、mailbox/semaphore、virtual interface/clocking、covergroup 等仍需补齐，不能用一个 q05 成功代表 UVM 完成。后续顺序见 [计划 M148](../plan1017.md)。

M155 同源执行与当前边界见 [验收记录](../validation/m155-typed-containers/README.md)。VCS 接受若干 enum 容器隐式转换及 queue-of-fixed-array 声明，native 仍拒绝；这五个接收差异保留，不能表述为完全对齐。
