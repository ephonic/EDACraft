M151 继续 REPORT-GAP 的 UVM 基础能力：class 单继承、super、虚函数及带延时虚任务、派生到基类的值传递、override 签名校验和协变返回。原始 q01 保持源文件字节不变，新增构造顺序、字段遮蔽、默认构造器链、非虚调用、多层多态、接收者/实参单次求值、数组/ref/output/宽四态、package、参数化 module 克隆和回滚用例。完整 UVM 仍未完成；抽象类、参数化类、动态转换、约束随机、mailbox/virtual interface/clocking/coverage 等继续。

构造器修正为每层先执行基类构造，再执行本层属性初始化和构造器体；隐式默认构造器同样执行完整链。派生对象保留基类字段前缀布局及对象实际类型，checkpoint 包含祖先类型信息。parser 和门级 parser 保持分离，生成程序无 parser 指针。virtual 分派的接收者/输入实参仅计算一次，默认实参按静态声明绑定；super 与非虚调用静态绑定。

本目录保存该批次的构建、同源 VCS、波形、sanitizer 及安装入口检查记录。VCS 输出只导出文本日志和自有捕获波形，不导出 vendor 生成代码/程序。没有性能或压缩率结论。异步 DWF 与范围选择继续验证；对象堆字段仍经 SV 观察变量导出。

实现冻结为 `92b475849767dd7b0f60f67ab741ef635c358732`，源码包包含 1879 个成员。虚方法调用的命名实参和默认值按静态声明绑定，override 允许使用不同形参名；分派目标按稳定 class ID 排序，避免 AST 地址影响跨平台代码生成。

验收口径：

- Mac 和 103 Intel 各通过七组发布检查，共 674 份捕获；另外通过完整 RTL parser、格式 parser 和原生 DB 检查。继承组包含八模型、127 份捕获、十三个编译拒绝、两个空句柄运行时拒绝和一次预测提交/回滚。
- class_objects 与 class_inheritance 两组共 47 份生成 C++ 跨平台逐字节一致，266 份完整解码波形一致；此数字不表示七组的全部生成程序均做了跨平台身份对照。
- 八模型实际 VCS 输出一致，十三个非法输入双方均拒绝。六个模型全部导出声明位时间线一致，signatures 模型仅对共同捕获的位比较：共比较 819 位，VCS 默认捕获漏掉 `xs[0]`、`xs[1]` 共 64 位，未将缺失位算作通过。原始 q01 在 time0 结束，仅计输出对照，不计 VCS 波形通过。
- 完整 parser、八个前端正例、十三个前端反例、七份生成程序与窄/宽堆内核通过 ASan/UBSan；实际双分区旧模型及新虚任务模型带异步 writer 通过 TSan。未启用 LSan；新对象堆模型可能合并为单分区，不将配置 parallel 等同于实际双分区。
- 三个实际稳定入口重新编译 rollback 模型，生成代码、完整 ordered 异步 DWF 与验收样本相同；按 `top.*observed`、深度及 tick 2..6 选择的输出也复核通过。同步/异步字节身份、背压、错误传播和波形恢复另由 waveform_pipeline 检查。

稳定入口为 `~/vibe-coding/dsim-test/bin/dsim`，103 上为 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim`。发布身份及实际入口收据见 `mac-release.json`、`linux-release.json` 和两份 `*-stable-entry.json`。

`evidence-index.json` 索引源码、Mac、Linux、sanitizer 和 VCS 五个独立证据包；`verify-evidence.py` 逐个核验包及成员哈希，`mirror-local.json` 与 `mirror-remote.json` 保存两端校验结果。`audit.py` 核对本目录的最终验收口径。旧 SDF root-buffer time0 X monitor 差异仍保留，未将完整 waveform_dump 回归计为通过。完整 UVM 缺口见 `remaining-gaps.json`。
