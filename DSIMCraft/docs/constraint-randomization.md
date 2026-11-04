# 约束随机化

已接通 RTL parser、类特化/继承、C++ 生成及 Z3 位向量求解执行，
不是仅接受关键字。门级 parser 保持独立。

支持实例标量整数/packed `rand` 与 `randc` 属性、命名 `constraint` 块、分号约束、
`inside` 集合/范围、if/else、蕴含 `->`，以及支持的整数算术、比较、逻辑、
位运算、移位、拼接、常量 packed 选择和整数 cast。
保留 SystemVerilog 的位宽、截断、符号/无符号上下文；有 96 位实际求解用例。
不同变量组成同一个求解问题，64 位稀有精确解不依赖随机试探命中。

```systemverilog
class Packet;
  rand int unsigned address, length;
  constraint legal {
    address inside {[16:255]};
    address % 4 == 0;
    length == address + 8;
  }
endclass
```

M180 已补循环随机化：每个对象/字段独立保存已用值，循环变量先于普通随机变量求解，历史随 checkpoint 恢复。支持 `object.randomize(property,...)` 临时指定完整标量属性，也支持 `object.randomize(null)` 只检查约束；未列出的属性保留为状态值。字段列表与 rand_mode 的关系、失败后的循环历史行为见 [M180 验收](../validation/m180-cyclic-randomization/README.md)。

`object.randomize()` 支持内联 `with { ... }`；对象成员优先查找，未命中的名字
继续从调用作用域查找。继承中同名约束替换基类约束，其他约束合并，
经基类句柄调用时使用对象实际类型的随机属性与约束。
`pre_randomize/post_randomize` 为不带形参的普通 void 实例函数，不能声明 virtual；
求解前调用最派生的前处理，成功后调用后处理，基类处理由显式 super 调用控制。

`std::randomize(a,b) with { ... }` 支持当前作用域的完整标量变量，含 automatic 函数局部变量。
无实参形式只检查约束，返回 int；无约束、无实参形式成功且不修改变量。
求解器返回 SAT 后先提取全部结果再写回；UNSAT 返回 0、不写任何随机变量、
不执行 post_randomize。pre_randomize 已执行的普通副作用保留。
求解器 unknown/异常明确报错，不作为已证明无解。

支持对象整体及单个属性 `rand_mode(0/1)`、对象整体及命名约束
`constraint_mode(0/1)`，单个目标可不带参数查询模式。
禁用的随机属性作为当前状态参与求解；禁用的约束不加入求解问题。
对象 `srandom(seed)` 重置独立随机流；作用域随机化使用当前进程随机流。
对象随机流、模式和回调修改均随 Sim checkpoint 恢复。
普通 RTL 不使用约束随机化时不链接 Z3。

构建时 CMake 自动寻找 `z3++.h` 与 libz3，也可指定
`-DDSIM_Z3_INCLUDE=/prefix/include -DDSIM_Z3_LIBRARY=/prefix/lib/libz3.so`。
生成的约束模型需用相同头文件/库编译；稳定版快照包含 dsim 求解运行时头文件，
不包含第三方 Z3 安装。本机验证使用 Homebrew Z3 4.15.4；103 已从官方源码
构建静态 Z3 4.15.4，安装于 `/apps/EDAs/own/dsim/deps/z3-4.15.4`。

M182 已支持对当前状态容器的[约束 foreach](constraint-foreach.md)，包含非 rand 类内对象队列、嵌套索引作用域与空容器真值。M208 进一步接通一维类整数动态数组的长度/元素求解，见[类动态数组](class-dynamic-arrays.md)。

边界：const rand、dist/solve-before/soft、static rand、随机对象图、randc/固定/多维随机数组、
local:: 名称限定、约束 unique、
约束中的通用函数调用等仍待补齐。M207 已支持标量随机枚举合法域。
X/Z 状态在约束求值时明确报错，不能作为普通无解返回；四态相等运算符拒绝。
完整未知状态诊断与约束内建方法仍待扩展。
随机位偏好会产生不同合法解，不承诺均匀分布或与 VCS 相同的随机序列；
完整约束随机化/UVM 功能尚未完成。

用户指定信号/层次与时间范围的异步压缩波形继续纳入回归，
随机状态回滚后对照顺序波形。本批验收见
[M174 记录](../validation/m174-constraint-randomization/README.md)及 [M180 更新](../validation/m180-cyclic-randomization/README.md)。

M209 支持一维整数/枚举随机队列，含容量约束与模式控制。类 rand 句柄可声明并在 randomize(null)/指定整数属性时作为状态，但涉及它们的整体 randomize 仍拒绝；联合对象图求解尚未实现。详见[类句柄数组与随机队列](class-handle-arrays.md)。
