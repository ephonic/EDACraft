# M160：static 类成员

实现冻结 `746b7993290813d5ec69e6e91dc59ab005bd9553`；远端源包冻结 `fa4f2f218d7a01735f140dbe0cf38544b2147124` 仅修正归档辅助脚本路径，两者987个发布输入相同，源包1822文件逐哈希验证。按 REPORT-GAP2 r01 和真实公开 UVM 阻塞补齐 static 属性、无 this 的 automatic 静态 function/task、类作用域与参数化特化身份。原始 r01 字节不改，在三个后端与 VCS 输出一致；RTL/门级 parser 保持独立。范围见 [功能说明](../../docs/class-static.md)。

Mac 和 103 Intel 各九组1102捕获及 mandatory RTL parser/格式/原生 DB 检查通过。新十模型、31份C++/182完整捕获跨平台一致，10 native拒绝、1预测回滚/1提交，真正双分区通过。覆盖继承共享、空句柄静态访问、包/模块克隆、静态初始化与单例、automatic及显式static局部、交叠延时task、宽四态/两态、string/容器与接收表达式副作用。全量有序/settled VCD/DWF/异步DWF跨后端比较，同模式sync/async字节一致，另核验用户选择范围。

十份相同SV在VCS编译运行：八个非空输出模型完整一致，parallel无输出但128个共同可见位时间线一致；receiver模型有两条ref调用计数差异，保留而不计完全对齐。共897个共同声明位896一致/1不同；834个native类静态位使用合成路径，没有参考同名导出，单列且不计匹配。initializers无共同导出位、原始r01在time0结束，仅计输出；不宣称完整类堆波形匹配。八个拒绝例与VCS相符，模块static函数前缀/显式static方法局部生命周期两例VCS接受、native拒绝，详见 [接收性记录](negative-comparison.json)。

完整parser/新前端十正十拒绝、八个普通生成程序与实际预测回放通过ASan/UBSan；真正双分区和独立异步writer通过TSan，公开UVM正常失败路径也经过ASan/UBSan。LeakSanitizer关闭，无泄漏/性能结论，没有声称全量all-target构建通过；既有masked_kernel限制保留。31份正式生成程序与开发验收版相同，sanitizer证据按具体程序身份绑定。

Mac `~/vibe-coding/dsim-test/bin/dsim` 更新到 `20261029T031517555716Z-10b1a92b3a30`；103 `/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim` 更新到 `20261029T031610Z-fa4f2f2`。三个实际入口重新编译与完整/所选范围异步波形复验通过。首轮发现静态波形元数据未随信号重排更新，已修复后冻结重测；归档/入口辅助脚本路径错误保留，入口验证失败自动恢复旧链接后才重试，没有将失败计通过。

实际稳定入口的公开 Accellera UVM 2020.3.1 预处理两端仍1888084字节、166依赖与原SHA一致，native语法首错从static function推进到 `uvm_misc.svh:377` 子程序结束标签。**完整UVM仍不能原生编译执行，完整REPORT-GAP2目标继续。** 原始r02队列拼接初始化等缺口未宣称修复；后续继续结束标签/类限定符、约束随机、mailbox/semaphore、virtual interface/clocking、coverage/DPI等依赖。

源码、自有Mac/Linux结果、sanitizer及VCS文本五归档存于两端dsim-test/evidence/m160-class-static，逐成员哈希双端核验；VCS生成C/C++、csrc、daidir及二进制不导出，公开UVM展开源码不进入结果归档。结构化验收见 [audit.json](audit.json)，它只表示本增量通过，完整UVM标志仍为false。
