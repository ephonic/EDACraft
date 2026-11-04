# 阻塞赋值内部事件控制

M49 支持 `q = @(event) value` 和 `q = repeat(count) @(event) value`。右值在入口按目标上下文宽度取样，进程挂起，等待结束后计算动态目标并写入，再继续后面的语句。它与 `@(event) q = value` 的区别是后者在等待结束后才读取右值。

```systemverilog
q = @(posedge clk iff enable) data;
word[address()] = @ready sample();
q = repeat(3) @(posedge clk) data;
```

重复次数在右值之前求值，二者各执行一次；后续 count/data 改变不影响已开始的等待。零、负的 signed 次数和含 X/Z 的次数按现有 repeat 规则不等待，仍求值并赋入右值。带 iff 的控制只计通过条件的发生。支持普通整信号、表达式、受支持 automatic 函数事件、静态命名事件及混合列表，沿用各类入口/Active 条件取样规则。

动态目标索引和函数调用在恢复后求值一次。支持 packed 位/固定宽度 indexed part select、拼接目标、数组字和已支持 packed 成员；宽值/符号扩展、四态与两态转换、enum 类型检查沿用原赋值路径。ordinary initial/always 和非递归 automatic task 均可用，函数和 always_comb/latch/ff 中拒绝内部时间控制。

RTL grammar 修复阻塞赋值事件控制被 assignment expression 归约遮挡的问题；新增仅用于赋值的 repeated event control，复用已有 REPEAT 循环及 timing-control AST。绑定、模块克隆、清理继续走通用节点路径。门级 parser 保持独立，Bison 原有 47 个 shift/reduce 冲突未增加。生成解析文件同步提交。

编译器复用普通显式事件等待生成器、进程保存值和 repeat 计数；没有新增运行时表、动态进程或 AST 解释器。取样值、计数、PC 和等待状态随已有检查点恢复；读取、函数副作用与动态目标进入分区依赖。本批未改 runtime/parallel，未测量速度收益。

仍拒绝非阻塞内部事件赋值 `q <= @(event) value`（包括 repeat 形式）：它需要立即继续发起进程并维护多个独立待交付实例，不能用阻塞等待冒充。VCS 接受的原始 NBA 探针保留为缺口。整 unpacked 数组内部事件赋值由 native 与该 VCS 安装共同拒绝；`@*`/`@(*)` 内部赋值控制暂不支持。既有函数事件、event 对象、fork/动态进程、完整事件区域/SVA/UVM 等边界继续保留。

验证入口为 `rtl_intra_event_assignments`。四共同源覆盖入口 RHS 和恢复后目标、130 位/signed/bit/enum、拼接与未知索引、重复次数求值顺序/零/负/X、automatic task、真实双分区、三次实际失败预测恢复及完整 ordered VCD/DWF。原始数组字目标探针独立核对索引时机。实际 VCS 位时间线、sanitizer、跨平台与未支持项见 [M49](../validation/m49-intra-event-assignments/README.md)。
