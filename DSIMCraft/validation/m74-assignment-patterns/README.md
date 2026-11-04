# M74：SystemVerilog 赋值模式

补入 RTL `'{...}` 的上下文类型展开，支持固定 unpacked 数组、packed 数组和 packed struct 的按位置、default、数字索引/成员名、嵌套及常量重复。接通声明初始化、automatic 局部初始化、阻塞/NBA、延迟赋值及 packed continuous RHS。RTL/gate parser 保持分离；复用现有数组快照、存储转换、依赖、调度与回滚。

- [native-results.json](native-results.json)：5 模型 × 3 后端 × ordered/settled × VCD/DWF，加 3 次失败预测回滚，共 63 份完整波形；21 个拒绝测试；实际双分区。所有 TRACE 与固定期望一致。
- [vcs/results.json](vcs/results.json)：10.131.254.103，source /apps/EDAs/syn.bash，VCS W-2024.09_Full64。5 组共享源逐字节一致，保留编译日志、执行日志和 VCD；[verify.py](verify.py) 比较全部 975 条公开物理位的 settled 时间线，无排除位。23 根只读 observer 暴露 VCS 默认不导出的固定数组元素。
- [sanitizer-results.json](sanitizer-results.json)：5 模型的 ASan/UBSan 编译器生成和实际 C++ 程序执行，完整生成 C++、stdout、ordered 波形与普通构建一致。[最终编译器复核](final-compiler-sanitized.json) 另验证 5 个生成 C++ 身份和全部 21 个拒绝分支。关闭泄漏检测；parser 重复解析/克隆/清理的 instrumented 可执行程序也通过。
- [regressions.log](regressions.log)：9 项已有回归通过，覆盖 parser 内存、packed aggregate、固定初始化、实例数组、前端兼容、数组复制/形参、generate 与 gate CLI。加新功能回归，共 10 个不同检查组。
- [lexer-probe.json](lexer-probe.json)：跨行 apostrophe/brace 正确解析，拒绝诊断保持正确行号。

对齐中修正：混合 bit/logic packed struct 的整体模式赋值保留原始 X/Z，读取 bit 成员时才转零；整个两态聚合仍在存储时转换。双分区模型通过波形检查输出，避免跨两个独立 lane 的测试显示语句合并依赖域。

边界：typed pattern、类型键、表达式/参数索引键、直接模式调用参数/return 表达式、动态/关联容器、重叠 union 与持久副作用值表达式仍缺。unpacked 每维需显式嵌套模式，沿用非负 unpacked 下标等现有限制。索引键/重复数限已知 32 位常量；不代表完整 SV/VCS 支持。本批未做性能对标。

运行：`python3 tests/assignment_patterns/regression.py build/dsim build/rtl-assignment-patterns`，再执行 `python3 validation/m74-assignment-patterns/verify.py`。稳定版发布见 [stable-release.json](stable-release.json)，37 项发布检查通过，含 6 组用户问题 case 及 gate CLI/SDF。35 个生成模型与已验收版本完整 C++、stdout 和波形流一致（5 个 M74 + 30 个上一稳定版），见 [stable-identity.json](stable-identity.json)。

稳定入口：`~/vibe-coding/dsim-test/bin/dsim`。实现提交 `b6b72bb32454e797470a93c738ccaa21cecfbe1e`；binary SHA256 `59752789f912fdb450833a7983df3bfe7123cdc75e70dcdbfba45d90bf00e7b2`。
