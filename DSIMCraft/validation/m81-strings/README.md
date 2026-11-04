# M81 动态字符串与 enum.name 验收

实现提交 `2c0bb432358d578c6ffe3dc6ca432851e6b4f753`。用户报告 SHA256 仍为 `1e64d6f8fb92cd505b175919eee986e0ecca20f13df883f6387e4be842ca77a0`；B9 原始 t11 逐字节保存在 `tests/strings/report.sv`，源 SHA256 `b3f34effc5cfa7a64343e45d8667806eaddd955a59f0097f735f089409ce8d55`。功能范围和未支持项见 [strings.md](../../docs/strings.md)。用户 cases/FOLLOWUP 仍记录原始 unrolled TB 已在后续冻结版本通过，未据旧超时另作性能结论。

`native-frozen/results.json`：9 个模型、三后端共 27 份及 4 次实际失败预测，共 31 份完整 ordered VCD 流对照通过；30 类拒绝、Verilog `string` 标识符、实际两个分区通过。原始报告无括号 name、83 字节枚举名称、130 位四态匹配、2048 字节动态增长、复制、ASCII 方法、大小写/前缀/字符差、窄 signed 实参和宽 signed 返回值、延迟 RHS、字符串敏感性、package/packed enum 字段和重叠 automatic 局部均覆盖。最终额外类型检查后，27 份生成 C++ 与已验收程序逐字节相同，另有字符串误作 packed 写索引、数组写索引和整数端口实参的 3 个拒绝探针；见 `final-codegen.json` 和 `probes/string-*`。

实际 VCS W-2024.09_Full64 使用 `source /apps/EDAs/syn.bash`、`-full64 -sverilog -debug_access+all -timescale=1s/1s`。`vcs/` 保存 8 个完整原始输入、独立 dump wrapper、编译/运行日志和有时间模型的波形；文件源 SHA256 严格等同当前测试。8 份输出一致，7 个有时间模型的全部 **737 个公开数值物理位**完整 settled 时间线一致，没有删除差异位。原始 t11 零时刻 finish 未生成 VCS 波形，仅比较输出。动态字符串本身双方都不在这些数值波形中，字符串内容另由同源自检和输出验证，不能把数值位对齐表述为字符串波形对齐。自动局部不导出波形；额外 VCS 观测项和未观测项逐例列在 `vcs-verified.json`。

两类原始记录保留：`comparison-initial/` 的测试过度约束 compare 负值为 -1，实际 VCS 返回首个不同字节之差。随后用 `probes/compare*.sv` 确认字符差、前缀、getc 的 X/Z 清零和 substr 的 X/Z 拒绝，再修正实现及测试。`implicit-vcs/` 是原始隐式敏感性模型：VCS 中 source 改变后 `always_comb length=source.len()` 留为零，延迟快照仍正确；dsim 长度重新求值。该源逐字节对应 `implicit.sv`，作为原生三后端/回滚用例，不计入共享对齐；共享 `timing.sv` 使用显式 `@(source)`。`probes/timing-debug*` 给出实际 `[first] [second] 0 2` 输出，区分敏感性与 RHS 快照。

`sanitized-frozen/results.json`：14 份实际 ASan/UBSan 程序通过，包含 9 serial、4 次失败预测和真实双分区；其完整 C++/stdout/ordered VCD 与原生相同。sanitizer 编译器还运行 30 类拒绝及额外 3 个类型探针。parser 新增两实例克隆的 enum 名称/string 元数据检查并重复清理，原生和 sanitizer 全部既有检查通过，leak 检测关闭。第一次 sanitizer 校验脚本在并行阶段误引用旧 `native/parallel`，保留 `sanitized-initial.log`；修正为 `native-frozen/parallel` 后，resume 对已执行且 CPP hash 相同的 13 个 ASan 程序重新执行，并实际编译执行第 14 个程序，再完成全部拒绝检查；`sanitized-final.log` 和最终结果记录通过，不把首次运行说成全部成功。

11 项不同的既有检查最终通过：automatic subroutines、package、random、type signatures、system functions、packed aggregates、enums、expression/conditional/function events 和 checkpoint。原 event regression 将此前未支持的常量字符串事件当负例，本批已可生成；替换为明确拒绝的 `posedge string`，独立完整复测通过，初始失败日志和旧源保留。checkpoint 在当前 runtime 头文件下重新构建并复测。参见 `related.log`、`events-initial.log`、`events-final.log` 和 `checkpoint-*.log`。

复现：

```sh
python3 tests/strings/regression.py build/dsim validation/m81-strings/native-frozen
python3 validation/m81-strings/run-sanitizers.py validation/m81-strings/sanitized-frozen
python3 validation/m81-strings/verify.py
```

稳定发布及上一版本行为、最终生成代码身份核对完成后，记录在 `stable-*.json`。没有修改 DWF，没有新的性能对标、全量 CTest 或 Linux 本地构建结论。并发 SVA、完整 string/package/层次引用与验证能力仍待补齐。

稳定发布完成：60 项检查全通过，入口为 `~/vibe-coding/dsim-test/bin/dsim` → `20261024T104159778536Z-e55af7d0b056/dsim`。source SHA256 `e55af7d0b05611c0bb3e1687a8728625160b9d99b9444ff70ce3b8bca05b7d62`；binary SHA256 `524e3f6dde6884149a496fb992aeabd59641b20759b28ccba96dacb870578aab`。53 个先前根模型、31 个随机和 27 个 package 程序完整输出/ordered 波形一致，4 个先前 v2 程序输出一致；31 个新程序完整生成 C++/输出/ordered VCD 与 `native-frozen` 一致。运行时头文件已扩展，不把旧程序与旧版 C++ 说成相同；最终 source/runtime/binary 输入全部复核。见 `stable-release.json`、`stable-identity.json`、`stable-audit.json`。
