修正 M150 引入的关键字模式兼容性问题：普通函数名 `new` 被全局名称检查误当成构造器。现在只由 `function new` 的构造器语法入口校验 class 上下文，普通 Verilog 函数名及 SystemVerilog 转义函数名 `\new` 可使用；类外真实构造器仍明确拒绝。实现冻结 `ad05efc4c90a8436f20770b2338938eec595fd93`，1864 源码成员匹配 Git。

Mac/103 Intel 各重跑 class_objects + frontend_compat，两组 298 捕获（139 + 159）及 parser/格式/原生 DB 检查通过；原构造器拒绝例保持，增加普通函数名的三个调度配置和转义函数覆盖。完整 parser 与 legacy/escaped/class 三个完整 frontend 用例通过 ASan/UBSan，关闭 LeakSanitizer。两个新增关键词用例与 VCS 的相同源文件/对应语言模式输出一致。

两端 66 份生成 C++ 和 298 份解码捕获逐一对齐；各 24 份 class 生成 C++ 及八个 runtime 头与 M150 原验收逐字节相同，因此保留 [M150 的六组、VCS 和生成程序 sanitizer 验收](../m150-class-objects/README.md)，没有声称新运行过那一轮 VCS class 或全部六组。新构建仍重新执行 class/前端回归。原始 q01 仍缺 extends/super/virtual，完整 UVM 目标继续；SDF time0 monitor 已知差异不变，不增加性能结论。

最终 Mac 稳定入口指向 `20261028T184508970716Z-26abd20a3f92`，103 两入口指向 `20261028T184757Z-ad05efc`。三个实际入口重新编译、TRACE、完整有序异步 DWF 和所选 2..6 tick 波形复核通过，旧版保留，见 stable-entry JSON。

源快照和原始日志/程序/捕获归档位于本机 `../dsim-test/evidence/m150-constructor-keywords/archives` 及 103 `/apps/EDAs/own/dsim/evidence/m150-constructor-keywords/archives`。沿用 M150 的逐成员校验器，索引为本目录 evidence-index.json；VCS 只保留文本结果，没有导出其生成代码或程序。压缩波形接口见 [文档](../../docs/waveform-format.md)。
