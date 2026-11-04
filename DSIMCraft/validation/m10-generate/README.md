# M10：RTL generate 功能接入

生产 `build/dsim` 已重建，RTL lowering 和独立 RTL parser 已接通 generate。门级 parser 和事件 runtime 未修改；本批没有新性能测量。

覆盖显式/隐式 generate、if/else-if/case、多标签/default、嵌套循环、inline/external genvar、逐迭代局部声明/参数/子模块、delay、原语、宽四态值、隐式敏感依赖、自动独立域、波形与失败回放。范围见 [generate 说明](../../docs/generate.md)。修正常量比较和零的 signed 属性，不代表运行时完整 signed 已实现。

- 本地 9 项受影响 CTest 通过：generate、parser、既有 RTL、动态 packed 选择、专用 always、动态/连续 delay、原语分组及门级输入 CLI。两批原始日志为 `local-main.log` 和 `local-affected.log`；并非完整 129 项。
- 新功能每个平台三模型、38 波形、6 类拒绝、2 回放。嵌套宽四态输出有独立预期；双线程例确认两个分区。Linux 对应结果为 `linux/build/rtl-generate/results.json`。
- 真实 VCS W-2024.09 三例全部 907 条物理位时间线及 TRACE 相同：design 347、branches 152、nested 408。双向名字集合相等，不丢弃额外信号。VCS 将 generate 前缀写进名称，比较器对本批没有转义标识符的设计连接层次组件；不将其当通用层次比较方案。
- 同源 Linux 任务 `/tmp/dsim-m10-generate-GiaCoU`、PID 1358638 已退出 0，编译器及 parser 单测重建；generate、parser、既有 RTL 和 gate_source_cli 四项通过，68.51s。原日志在 `linux/ctest.log`；三个完整 serial CPP 与本地逐字相同，Linux 实际生成程序的 907 物理位也与 VCS 相同。
- macOS parser 单测及三组新源码各三次重复解析/清理通过 ASan/UBSan（关闭 leak 检测），四份 `*-san.log`。普通 parser 入口不处理 timescale，重复解析输入先删除单独的 timescale 行；实际编译器的 timescale 由正常预处理保留验证。不是 Linux sanitizer，也不是全量 RTL/SDF sanitizer。

本批冻结的可构建源码/测试共 500 文件，`source-manifest.json` 逐文件 SHA 与工作区一致。上传包 `/tmp/dsim-m10-source.tar.gz` SHA256 为 `6c5972c1a3290d2b4cf0d3127f2132d1e1407a5a0b7d0bb43f2ab2e46fd17fc6`；不包含后续说明文档/验收目录。VCS 原始文件在 `vcs/`；Linux 提取包仅保存三组 serial CPP/IR/波形和日志，不声称保存了全部 Linux 38 捕获。

复算（默认本地执行产物仍在 `build/rtl-generate`）：

```sh
python3 validation/m10-generate/verify.py
python3 validation/m10-generate/verify.py validation/m10-generate/linux/build/rtl-generate
ctest --test-dir build -R '^(rtl_generate|rtl_semantic_memory|compiled_regression)$' --output-on-failure
```

开发中 VCS 首次因环境脚本不接受 shell nounset 退出，修正作业脚本后继续；随后发现测试中 inline genvar 和另一个块同名，VCS 拒绝，已将块改名再重新编译全部三例。它们不是功能通过证据。早期原生测试也帮助定位默认 case/匿名块作用域与倒序循环常量比较问题，均修改生产实现后再验收。

当前仍是语言/时序子集，不是完整 VCS 替代品。特别是 signed、unpacked 存储器、用户函数/任务、完整 timing checks/notifier/脉冲、复杂标准单元模型，以及自动预测/内部自动并行仍待补齐。最近完整 SDF 7.67 倍的同轮耗时比属于 M9，本批没有新速度结论。
