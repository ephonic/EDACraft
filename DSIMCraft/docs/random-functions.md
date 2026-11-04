# 随机系统函数

RTL 编译器支持 `$random`、`$random(seed)`、`$urandom`、`$urandom(seed)` 和 `$urandom_range(max [, min])`。支持省略无参函数的括号；返回值必须用于表达式或通过 `void'(call)` 显式丢弃。`$random` 可用于 Verilog 模式，其余要求 SystemVerilog。

`$random` 返回 signed 32 位值。显式种子要求至少 32 位的完整可写整型变量或数组元素，按 inout 读入和回写，同时更新无参调用使用的全局序列。回写时重新求值 actual，因此 `seed[i++]` 会推进两次索引；该行为已用 VCS W-2024.09 实测。生成代码记录全部读写依赖和 const ref 限制。实现用无溢出的整数形式计算传统均匀转换，处理精确负整数边界和上端饱和；共享用例检查 104 组返回值/种子对，而非只检查是否能编译。

`$urandom` 返回 unsigned 32 位值；显式种子是输入表达式，不回写 actual。每个仿真过程拥有独立的 SplitMix64 状态并取高 32 位。相同种子重新产生相同序列，函数/task 使用调用线程的状态；fork 创建时依次从真实父线程取得子线程种子，重用和重叠的 automatic 激活均重新播种。静态声明初始化使用独立启动状态，自动初始化使用调用线程状态。静态初始化仍受既有非恒定读写限制。静态过程的默认种子采用逻辑过程编号，避免 worker 注册顺序改变结果；这不等于完整 SystemVerilog 实例级随机稳定性。

`$urandom_range` 使用 unsigned 32 位闭区间，缺省 min 为 0，max 小于 min 时交换上下界，覆盖单点及完整 0..2^32-1。用 rejection sampling 避免直接取模的偏差。

所有 RNG 状态归 Sim/Process 所有，随 checkpoint、失败预测和并行事务一起恢复；没有进程外的宿主随机状态。表达式保留随机副作用和短路求值。连续赋值、事件回调和 reduction with 等已有纯表达式上下文明确拒绝 RNG 调用。含随机副作用的过程和相关启动初始化保守地合入同一分区；其他独立电路仍可并行。未使用随机函数的设计不启用运行时随机字段/执行保护分支。

这是基本随机函数支持，尚不包括 class/constraint/randomize、std::randomize、进程 srandom/get_randstate/set_randstate、分布系统函数、全设计运行种子 CLI 或完整对象/实例随机稳定性。`$urandom`/`$urandom_range` 的具体随机数序列不与 VCS 一致；对照验证重播、类型、范围、线程稳定及副作用语义。另保留 VCS 忽略零 urandom 种子并警告的探针；dsim 接受零种子并可重复播种，不将该行为计为已对齐。seed 的四态转换和宽 actual 的探针另存验收目录，不据此宣称完整参数类型兼容。

线程独立和层次播种的语义参考 [Accellera 随机稳定性提案](https://www.accellera.org/images/eda/sv-ec/att-0248/01-Random-Constraints_Proposal.pdf)，实际对照与边界见 [M79 验收](../validation/m79-random-functions/README.md)。未修改门级 parser 或 DWF 格式；本批没有新增性能结论。
