# SDF 端点绑定（0.11.0，合并验收见 0.12.0）

独立门级 parser 的按需名称索引与流式 SDF binder 已实现。支持层次、转义 divider、通配 CELLTYPE、pin 方向及有向结构连接检查，保留原始条件、边沿、模式和数值；提供显式精度下的 min/typ/max 数值预览。接口和限制见 [SDF 绑定](../../docs/sdf-binding.md)。当前 `binding:true, annotation:false`，不施加延迟或执行 timing checks。

0.11.0 本地 CTest 19/19，核心 ASan/UBSan 8/8。首次远端完整回归 19/19、时间/预处理/波形差分通过，但真实 SDF 驱动错误地断言只有一个层次 scope，导致流水线退出；[原始失败](real-driver-failure.log) 保留。独立网表遍历得到 17 个 scope，见 [层次 census](hierarchy-census.json)。这不是 SDF 解析失败。内部 Liberty pin 被误当作外部端点的问题随后修复，原始误接受日志见 [internal-before-fix.log](internal-before-fix.log)，增加独立拒绝测试。

最终 0.11.0 源码包 `/tmp/dsim-sdf-binding-source.tar.gz` SHA256 为 `62a21347f4d970c8b0a15694b023a6d525c083ccbabb5d728f03fa69c9ca1d98`，用于下一批固定性能基线；其真实输入验证驱动仍含旧 scope 断言。修正的驱动与全部绑定实现一起纳入 [0.12.0 合并验收](../m5-driver-inline/README.md)，该记录提供真实输入、两份完整 SDF、回归和最终证据，不将两次源码快照混为一次成功运行。

[固定真实输入](real-inputs.json) 包含 300,909 个具名单元、111 种 cell，使用完整约 1.2 GB Liberty。flat SDF 有 1,744,700 条记录，原 SDF 有 3,633,232 条记录，两者各含 790,222 条 INTERCONNECT。最终验证逐项对照前批独立 SDF census，运行前后核对网表、完整库及两份 SDF 的 SHA256。该规模只验收端点绑定；完整 256 位 RTL、foundry 单元行为与带时序仿真尚需后续接入。

0.12.0 合并验证中，包含完整 Liberty 读取、门级拓扑和 SDF 绑定的单次墙钟分别为 34.16/47.68 秒，峰值 RSS 1,970,532/1,969,768 KiB。它们不是单独 SDF parser 时间，也不是仿真时间；尚未与 VCS 的相同阶段对照。完整 Liberty 的大对象仍是内存优化候选，不能把紧凑名称池大小当作整个绑定进程内存。
