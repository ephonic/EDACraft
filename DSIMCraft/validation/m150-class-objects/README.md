M150 接通基础 class 执行，继续 REPORT-GAP 的 UVM 依赖链。实现冻结于 `0a342f104ca19b6b2a328a9f35c74dca14a21a2a`；1864 个源码成员逐文件与该提交核对。具体能力和边界见 [class 文档](../../docs/class-objects.md)。没有进行性能基准测试。

这是 M150 原批次的验收记录；随后构造器关键字兼容性修订的稳定入口和检查见 [关键词修订](../m150-constructor-keywords/README.md)。

- 支持 module/package 内 class、null/new/this/构造器、句柄别名及形参/返回/ref、integral/string/对象字段、宽四态选择及整数更新、automatic 方法及延时 task、克隆、字段事件和 checkpoint/预测事务。
- Mac/103 Intel 各六组相关回归、parser/格式/原生 DB 检查通过，每端 483 捕获。新组 11 模型、23 个普通调度配置及一份事务重放程序，139 捕获、1 回滚/1 提交、16 编译拒绝和 2 空句柄运行时拒绝；包含真正的双分区与独立数值预期。Mac/Intel 的 24 份 C++ 和全部 139 份解码捕获相同。
- VCS W-2024.09 对照相同 SV：11 模型输出对齐；其中 6 模型所有 356 个 native 导出声明位（含别名）物理时间线一致。其余 5 模型在 time 0 finish，使独立 VCS dump initial 未执行，没有 VCD，只计输出对照。没有改动 SV 输入延后 finish，也没有把缺失波形计为通过。无 TRACE 的 parallel 模型使用已验收 native 全量波形直接与 VCS 对照；原 run_flow 要求 TRACE 的失败记录保留。
- 完整 parser（含多次失败后重解析及参数化类克隆检查）、11 新组正例/16 编译拒绝经过 ASan/UBSan；七份逐字节核对后的生成程序、窄/宽堆内核经过 ASan/UBSan，双分区 + 独立压缩线程程序经过 TSan，完整 DWF 与普通程序逐字节相同。不声明 LeakSanitizer 通过。
- Mac 稳定入口指向 `20261028T181549272293Z-d70355b006b2`；103 两入口指向 `20261028T181722Z-0a342f1`。实际入口重新编译、输出、有序异步 DWF 和范围筛选复核通过；旧版本保留。SHA 和先前入口见两端 release/stable-entry JSON。

未将基础类支持表述为 UVM 完成：原始 q01 的 virtual/extends/super 仍明确拒绝，见 original-q01.json；继承/virtual、参数化类、对象容器、约束求解、mailbox/semaphore、virtual interface/clocking/coverage 等继续待补。M149 的旧 SDF root-buffer time0 额外 X monitor 差异仍单列，没有修改旧 oracle 或将完整 waveform_dump 组计作通过。早期候选曾因形参逗号识别影响 modport，被原 parser/旧回归拦截；修正后冻结，并在两端重新完成全部相关回归。

异步压缩波形仍使用 DWF，独立线程负责接收、差分编码、Zstd、CRC、写盘与索引收尾；支持有界积压/背压和用户范围筛选。本轮在对象模型、预测事务及实际稳定入口再次验证；没有新增 FSDB 二进制兼容或速度提升声明。波形不直接导出整个对象堆，验证通过 SV 观察变量。

`audit.py` 核对本批验收陈述；`verify-evidence.py <archives目录>` 核对五份归档及所有成员。原始归档位于本机 `../dsim-test/evidence/m150-class-objects/archives` 和 103 `/apps/EDAs/own/dsim/evidence/m150-class-objects/archives`，索引见 evidence-index.json。VCS 仅导出自有 SV 捕获器、文本日志、元数据和 VCD/DWF，未导出其生成代码或二进制。最终验收脚本随本目录保存，源码归档保留实现冻结时的脚本版本；采集限制和两次 harness 失败均明确保留，不计作功能或波形全等证明。
