# M156：原生参数化类验收

实现冻结 `e085348af23002e6127875ba5f12704446ec2e41`。新增类型/整数类参数、规范特化缓存、声明作用域默认绑定和调用作用域实参绑定、参数化继承、递归句柄、函数返回与值/ref 形参；对象在生成程序中真实执行。enum 类属性读取保留类型身份。详细边界见 [参数化类](../../docs/uvm-parameterized-classes.md)。

Mac 与 103 Intel 各十二组、1726 捕获及完整 RTL parser、格式 parser、原生 DB 检查通过。新组各九模型、164 捕获、17 native 编译拒绝、1 回滚/1 提交，含实际双分区。28 份生成 C++、stdout 和 164 完整解码捕获跨平台一致。VCS 九正例输出及全部 1184 导出声明位 settled 时间线一致；17 负例中 VCS 拒绝 13 项，另外四项以警告接受或忽略覆盖（未知参数、重复命名覆盖、超量实参、普通类参数覆盖），native 更严格拒绝，不能称完全对齐。

完整 parser、九正例/17 反例前端、九实际生成程序及公开 UVM 预处理/失败编译通过 ASan/UBSan；实际预测 replay 与双分区程序及独立异步 writer 分别通过 ASan/UBSan 与 TSan。诊断修正前后的 28 份生成程序相同，相关 replay/TSan 证据按该身份复用。未启用 leak detection，不作性能或压缩率声明。七组前端负例预检共 108 项通过。

Mac 稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 指向 `20261029T000919293994Z-ad7adb861bec`；103 的 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 指向 `20261029T000949Z-e085348`。三个真实入口均重新编译、运行，并验证完整及用户范围异步 DWF 字节相同。Mac 940 个发布输入、Linux 1766 个源码文件及各八个 runtime 头与冻结源码一致；工作区仍含无关 untracked 实验，不声称 Git 工作区全净。各端波形管线 72 捕获/36 对、范围选择 232 捕获/62 对通过。

未修改的 Accellera UVM 2020.3.1 固定提交 `78c06547a2a0a29b3dc9dcafae62b75b2ff61544`，326 源文件保持，预处理为 1888084 字节/166 依赖。native 正常退出并报告 `uvm_misc.svh:96` 的 string 键关联数组语法缺口，尚未完成整个包的语义分析，**完整 UVM 仍不能编译运行**。共享隐式 type 参数、部分空位置参数、静态/类外泛型方法、类容器属性、约束随机、IPC、virtual interface/clocking/coverage/DPI 等仍待补齐。

首次冻结候选 `68c8d0fc` 因旧继承负例的诊断文本回归失败，未激活；对应 Linux 候选同步中止，不计未完成检查。修复基类类别预检后，重新冻结并完成上述双端验收。失败和停止收据保留。原始证据位于两端 `evidence/m156-parameterized-classes/archives`；六归档逐成员校验结果、来源绑定、实际入口收据和总审计均在本目录。公开 UVM 参考归档复用不变的固定来源，不声称本批重新运行完整 UVM 参考仿真。
