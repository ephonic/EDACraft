# M79：随机函数与 RTL 报告 v2

输入为用户 RTL 报告的 B4 和工作中更新的 [v2 报告](REPORT-v2.md)，SHA256 `1e64d6f8fb92cd505b175919eee986e0ecca20f13df883f6387e4be842ca77a0`。原始 t05/t06/t08 源与 hash 在 tests/rtl_report/v2/origin.json；未改用户报告、原设计、问题目录或 experiments/matvec16。DWF 按要求不作修改。

## 实现与边界

- 接通 `$random`/`$urandom`/`$urandom_range`：32 位 signed/unsigned、输入/回写种子、全局/过程 RNG、范围和边界、短路表达式、声明初值、自动函数/任务、延迟/NBA。传统 random 采用明确无溢出的整数转换；urandom 采用固定 SplitMix64 序列及无偏范围采样。
- RNG 状态归 Sim/Process 所有，随 checkpoint/transaction 复制恢复。fork 从真实父线程依次播种，覆盖分支重用与重叠 automatic 调用；逻辑过程种子避免 worker 注册序号改变结果。保守合并含随机副作用的分区，另有实际双分区检查。
- v2 的原始 struct function 形参失败根因为 ANSI 首组 named typedef 形参没有显式 input。接通该缺省方向、同类型续写、task 和 enum typedef；后续组仍使用既有显式方向规则，不声称所有省略形式/完整 struct 支持。
- 缺失 `--top` 现报告 `top module not found 'nonexistent_top'`，退出 1，不生成 C++。
- RTL/gate parser 分开；bison/flex 重新生成。继承的 shift/reduce 数由 M78 的 56 变为 57（随机无括号/括号调用）；新增 implicit formal 不增加该计数。
- `$urandom` 具体序列不同于 VCS；VCS 忽略零种子并警告，dsim 允许重复用零播种。保留实际探针，不将此列为对齐。未实现 class/constraint/randomize、process RNG 管理、完整实例/对象随机稳定性或运行种子 CLI。package/import、并发 SVA、enum.name/string、完整层次与匿名/nonpacked/package struct 仍缺。无新性能结论。

## 本机与 sanitizer

[native-results.json](native-results.json)：9 模型，serial/time-wheel/threads=2 共 27 捕获，加 4 次实际失败预测回放，共 31 份完整 ordered VCD 流；每个后端重复运行检查确定性；12 类拒绝。parallel 模型实际使用 2 个分区。VCD 比较包含所有导出的信号/位/事件，不只比较 TRACE。

[sanitizer-results.json](sanitizer-results.json)：实际编译执行 14 个 ASan/UBSan 生成程序（9 serial、4 失败预测、1 双 worker），每份完整 ordered 流/输出与 native 一致，11 类拒绝。关闭 leak detection，未声称 leak 检查。

[v2-native-results.json](v2-native-results.json)：原始 t05 random、t06 urandom、t08 struct 三源不变通过，额外首组类型缺省方向 function/task/enum 测试通过，缺失 top 拒绝通过。[v2-sanitizer-results.json](v2-sanitizer-results.json) 保存额外 4 个实际 ASan/UBSan 程序；最终含新 grammar 的 sanitized compiler 对前面 9 个模型重生成，完整 C++ 与已执行版本相同。parser 全部 semantic_memory 原生/ASan/UBSan 检查通过。

受影响旧检查：首批 11 项 CTest 中 10 项通过，system_functions 仅因历史 `$bits(string)` 拒绝文本期望陈旧而失败，原日志 [regressions-initial.log](regressions-initial.log) 保留。将期望改为现有明确文本后单独完整回归通过：49 捕获、1 回滚、28 拒绝和 256 四态向量，见 [system-functions-final.log](system-functions-final.log)。typed formals 补入后额外 5 项子程序/类型/ref 检查另记录 formal-regressions.log。没有跑全量 CTest、Linux 构建或性能基准。

## 实际 VCS

远端 `yangfan@10.131.254.103`，source `/apps/EDAs/syn.bash`，实际 W-2024.09。9 个共享源逐字节及 TRACE/自检通过，raw source/compile/run/VCD 全存 vcs；[verify.py](verify.py) 复核源码 SHA256、预期输出和明确选定观察信号的完整时间线。共 960 个观察位通过：legacy 的全部信号/位，其他模型只比较确定性的控制、传统序列或单点区间结果。所有未选信号名单与原因在 [vcs-verified.json](vcs-verified.json)，不冒称 urandom 随机数本身或所有位对齐。legacy 的 104 个返回值/更新种子对含 0/1/负种子、精确负整数、零后继及饱和边界。

另 4 个 v2 源实际 VCS 自检通过，保存在 vcs-v2；其中 3 例完整结果行相同，t06 的随机数只验证自检与范围，不比较具体数字。没有声称该组 VCS 波形对齐。

probes 保留实际发现与边界：直接 `$urandom();` 被 VCS 拒绝，dsim 同步要求使用结果或 void 丢弃；`$random(seed[i++])` 实测 copy-in/out 分别求值、index=2，原先按单次地址捕获断言的失败源/日志完整保留；整数边界与宽/四态种子、urandom 零种子差异均保留。额外宽/四态 legacy 5 个输出对与 VCS 相同，不据此推广为完整参数兼容。

## 复跑与发布

```
cmake --build build --target dsim test_verilog_semantic_memory -j 4
python3 tests/random_functions/regression.py build/dsim build/rtl-random-functions
python3 tests/rtl_report/v2/regression.py build/dsim build/rtl-report-v2
python3 validation/m79-random-functions/verify.py
python3 validation/m79-random-functions/run-sanitizers.py /tmp/dsim-m79-sanitizers
python3 validation/m79-random-functions/run-v2-sanitizers.py /tmp/dsim-m79-v2-sanitizers
```

sanitize 脚本要求 build-control-sanitized/dsim 已配置构建；VCS raw 由 run-vcs.py/run-v2-vcs.py 在已加载环境的远端生成。稳定发布已完成：58 项检查全部通过。入口 ~/vibe-coding/dsim-test/bin/dsim 指向 releases/20261024T045736305228Z-e171323582c0/dsim，实现提交 `0b370183da3437e1da911bf3f825f66d3116ed92`。53 个此前稳定模型的完整 stdout/ordered 波形相同；新测试共 35 份完整生成 C++/stdout 身份相同，其中含随机模型全部 31 份完整 ordered 流。源、8 份冻结运行时头和二进制 SHA256 均复核，见 [release.json](release.json)、[stable-identity.json](stable-identity.json)。

source SHA256 `e171323582c00609e292f28a929c9096a959260aa9d3149e32a261e699fe2a9f`；binary SHA256 `f6307540cf8ba7bb3b0946d24ca7769dc13af83fc9a5de52e01d28d7daea15f6`。运行时仅 runtime.hpp 有本批 RNG 条件代码，其他七份头未改；没有 DWF 格式修改。
