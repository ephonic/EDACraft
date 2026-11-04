# M210 函数互递归

本批支持标量 input 参数的模块/包/类函数互递归、多对象与虚方法分派、静态及自动生命周期、初始化中的递归。源码和功能边界见 [说明](../../docs/recursive-functions.md)。

验证入口：`tests/recursive_functions/regression.py`；七模型预期 128 次完整波形捕获、一次预测回滚及一次提交、四类编译拒绝和一次递归深度错误。VCS 使用完全相同的七份 SV，不以 RNG 归一化或修改库源码绕过问题。选定既有回归为 automatic_subroutines、class_inheritance、extern_methods；发布仍要求 mandatory RTL parser、格式 parser、原生 Liberty DB 检查。无性能结论、无全量回归或完整 UVM 声明。

`public-uvm.py` 验证未修改的 Accellera UVM 2020.3.1，保留 166 依赖、1888084 预处理字节及既定 SHA。当前首错已从函数互递归推进到 uvm_component.svh:1753 的字符串转义。`sanitize.py` 对前端及实际生成程序运行 ASan/UBSan，并核对 C++ 和完整解码波形；关闭 leak 检测。

`activate.py` 先验证冻结源码及全部发布输入，实际稳定入口重新生成七份 C++，逐字节对照已通过 native 编译与运行的冻结程序，再复用对应 native 二进制复跑 TRACE 和完整波形；复用已测试 native 程序在收据中显式标明。失败自动恢复旧 symlink。默认远端 Intel 发布串行等待 M209 验收。用户本轮明确要求将修正版发布到 103，因此使用 `--supersede-older`：仅终止 M204–M209 的发布脚本及其子进程，保留旧版入口和证据；写入核对 PID、冻结提交及旧入口的审计后，才允许 M210 越过旧队列。实际部署仍以 Intel 检查、跨平台对照和入口验收为准。

双平台验收和发布完成：冻结实现 `1f3a9e72`，1501 项发布输入 SHA `368ffb1f8d16e9697ecfd4de5131134bacd4f6d0c762dd7134021c5128834332`。每端四组共 32 模型、530 捕获、72 编译拒绝、3 运行时拒绝及 mandatory 检查通过；103 份完整生成 C++ 和 530 份完整解码捕获跨平台一致。31 份压缩编码字节差异另列，完整解码记录仍相同，不宣称所有压缩文件逐字节一致。Mac 稳定版本 `20261101T061759832969Z-368ffb1f8d16`、103 Intel 稳定版本 `20261101T061924173757Z-368ffb1f8d16` 均已激活并通过实际入口七模型复验；103 根入口 `/apps/EDAs/own/dsim/dsim` 已核对。两端实际入口的 `-f/-F`、嵌套列表、include/define、含空格路径及本机 TRACE 验证通过。首次阶段失败、旧稳定版相同 CPP 及修正后的实际双分区证据保留；103 实际为两分区、9 窗口、0 消息。最终状态与完整收据见 progress.json 和本目录 JSON，外置原始证据及校验清单见 archive-catalog.json / linux-archive-catalog.json。

103 的共享用户 CPU 配额导致旧脚本固定的 180 秒编译超时触发，虽然发布配置为 14400 秒。当前源码中的四个脚本已接通 `DSIM_TEST_COMMAND_TIMEOUT`，默认仍为 180 秒。冻结候选不改输入：`recover-timeouts.py` 保留初次失败收据和全部已有原始结果，核验失败仅为固定超时，等待遗留编译器退出，再通过 `configured-timeout.py` 在内存 AST 中只替换对应的 subprocess 超时常量。编译选项、断言、输入与候选二进制不变；完整重跑失败组，重新核验全部冻结输入及运行时后才恢复最终验收。该时间预算用于功能验收，不构成性能测量。
