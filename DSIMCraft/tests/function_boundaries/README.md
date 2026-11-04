# SV 函数编译边界和长仿真默认预算

retained_memory_codec 的原始 DUT/TB/刺激逐字节复制，archive 哈希保持，15418 阶段使用损失为零的 H4 传输。完整四态逐周期期望来自原始已验证 VCS 轨迹；原 producer 另验证数值事务和 retained memory 历史，但该周期 oracle 并非独立软件周期模型，不能称独立周期签核。

回归保持每步180秒预算，核对每个观测的序号、20个输出和全部四态位，含冷态X/Z；显式 --max-events 仍须中断。semantics 用独立 Python 位编码期望验证128位函数返回、输入副作用只执行一次、函数体副作用、同步/异步波形；budget 的两个独立有限过程各超过旧默认指令预算，验证串行/真双分区、带/不带波形的默认长运行与显式限额。

生成器按展开后的函数体长度设置 native noinline 边界，不识别 DUT 名称、函数名或测试数据。小函数继续正常内联。未新增 RTL/gate parser 耦合，不代表 runtime 速度已经达到 VCS。
