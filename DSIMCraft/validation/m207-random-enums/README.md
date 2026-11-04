M207：原版 UVM 的随机枚举阻塞。

让类 rand/randc、具名 randomize(enum_property) 和 std::randomize(enum_variable)
进入已有约束求解器，并按声明的枚举成员生成有限合法值域。保留 enum 类型身份，
覆盖稀疏负值、宽于 64 位的枚举、继承与实际派生类型约束、内联约束、回调、
变量列表、rand_mode/constraint_mode、UNSAT 原子性与 randc 周期/预测回滚。
关闭随机化的字段只约束为当前状态，不强加活跃随机字段的枚举值域。

四个新增执行模型加入 constraint_randomization 的完整回归；分别跑串行、时间轮、
双线程与完整解码波形对照。VCS 使用相同原始源文件与断言，不比较不同 RNG 算法的
具体抽样序列。UNSAT 用例检查 randomize 返回值，VCS 的预期 CNST-CIF 单独计数，
其他错误与任何 Fatal 均不允许。前端和生成模型另跑 ASan/UBSan。

带 X/Z 枚举成员的随机化仍明确拒绝。本次不宣称支持随机数组或完整原版 UVM：
未修改的公开 UVM 首错已经从 m_command 随机枚举推进到
uvm_tlm2_generic_payload.svh:194 的 rand byte unsigned m_data[]。
