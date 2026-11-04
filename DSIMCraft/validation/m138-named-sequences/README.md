# M138：命名有限 sequence

补齐模块/generate 中无形参、无显式时钟的 sequence 声明、名称/空括号调用、前向/嵌套引用与词法作用域绑定。复用有限阶段、采样和事务机制；范围及剩余限制见 [专题](../../docs/named-sequences.md)。RTL/门级 parser 保持分离，runtime 头文件没有改动。

五个 VCS 同源模型覆盖 assert/assume/cover、嵌套引用和重复、四态/采样历史、异步取消、参数化/generate 克隆和名称遮蔽、256 阶段及真实双分区。期望 TRACE 来自 VCS 原始执行。发布检查三种配置逐信号完整有序波形和在途预测提交/回滚；53 个反例包含递归、重名、非法上下文、形参/实参、展开边界与声明标签错误，并检查既有输出保护。

发布前运行六组受影响功能（named_sequences、sequence_groups、sequence_repetition、sequence_delays、sampled_values、concurrent_assertions）及 RTL/格式 parser、原生 DB 检查，比较六个旧模型生成代码和八个 runtime 头文件。完整 parser 与九个实际生成程序运行 ASan/UBSan（不启用 LeakSanitizer）。双端直接对照 VCS 的 1275 个共同声明位完整 settled 时间线，原始 scope 拼写不同的 229 位单列。另将本批无转义点号标识符的五个自有 fixture 做逐工具无碰撞层次名归一化，覆盖全部 1504 位，并检查四个名称遮蔽/外层引用计数实际触发。

源码冻结、发布、入口及差分结果将记录在本目录 JSON。VCS 生成代码/二进制只留在远端私有临时目录，不进入仓库或证据归档。本批没有性能测量。

Mac 六组回归及 parser/格式/原生 DB 检查通过；完整 parser 与九个生成程序 ASan/UBSan 通过。稳定版 `20261028T054048463052Z-c8f6c14754a2` 已激活，经入口重编译后的生成代码 SHA、输出及完整有序波形与验收相同。103 Intel 六组发布回归及 parser/格式/原生 DB 检查通过，稳定版 `20261028T054053Z-cb672f9` 两个入口已激活。同源 VCS、全部声明位归一化及旧代码生成检查通过。开发阶段模型和反例分开运行，正式发布组重新运行完整合并检查；`development.json` 明确记录该区别。

冻结实现 `cb672f9cda623c1e196b5d54018168ff325980e8`，1758 个归档成员逐项匹配 Git；Mac 发布器的 759 个输入均匹配源码清单。源码包和原始证据持久保留在两端 `evidence/m138-named-sequences`；实际编译模型与全部回归日志/波形保留在各自不可变 release 目录。源码归档记录实现时文档，仓库中的后续发布说明与验收 JSON 属于元数据更新。

两端稳定入口重编译/执行采样命名序列模型通过，生成代码 SHA、stdout 和逐信号完整有序波形与各自 release 验收一致，见 `mac-entry.json` / `linux-entry.json`。
