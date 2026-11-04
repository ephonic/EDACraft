# M88：组合过程、负下标与 Complex REPORT2

实现提交 `06125fde8f9b84df7787cadba9c69a0ff9873346`。范围见 [组合过程](../../docs/comb-partial-writes.md)、[REPORT2 复核](../../docs/report2-review.md)。原始 REPORT2 冻结于本目录；外部报告追加更正及独立 `REPORT2-REVIEW.md`，不覆盖原结论历史。

- 原始 case `rtlagent-dual-20261025T020420-68e90d9f-blocking` 的两个源字节不变，193 事件的两个输出与原 VCS 记录及本次重跑相同。新增单独的 whole-write 元数据，区分静态整变量写与动态选择的保守冲突范围，贯穿表达式、函数效果和数组复制。没有静态整字写的部分反馈仍明确拒绝，不能简单移除保护。
- 修复 signed negative indexed part-select 丢弃全部目标的问题，传递 signed_index，保留裁剪的 RHS 偏移，并在减法前做边界判断。宽位置按符号扩展校验，保留完整数值边界。
- 8 组合模型 serial/time-wheel/parallel 三入口及 7 失败预测，共 31 份完整 ordered 捕获相同；实际 `partitions:2`；7 类拒绝且不生成 C++。宽值、X/Z、静态/动态选择、锁存、嵌套函数效果、数组整表复制及原始 DUT 均覆盖。
- REPORT2 原始 4 复杂设计及 9 项 probes2 通过，新增 p21/shift_context/reproducible 三模型共 12 捕获、3 回滚。RNG 同源不同路径/重复编译、三入口、显式播种与回滚一致；不宣称修改设计后的完整实例随机稳定性。
- 实际 VCS W-2024.09_Full64 对原 p21 同样给 `tern=003fffff`，报告 P0 分类更正；未将合法语义改成报告的错误预期。p21 与带 `$fatal` 自检的扩展移位模型全部 428 共同位完整 settled 时间线一致。
- 原始 SDF model 无时标，默认 1s/1s 将纳秒延迟舍入为零。保留原命令功能回归；新增显式默认时标，VCS 使用实际 `$sdf_annotate`，双方 11 共同位完整时间线相同，y 为 X@0、0@5ns、1@12ns。11 个 VCS-only 单元端口别名逐项列明，不宣称全部 dump 位相同。
- 组合 7 个模型（不含已知超宽下标边界）713 共同位、上述 REPORT2/SDF 439 位，共 **1152 共同位完整时间线相同**，无尾部裁剪。原 case 的 4053 个 native-only 数组位、array 模型的 32 个 native-only 位逐项记录。VCS 4 复杂设计同源自检通过；AXI/Cache 的具体 urandom 激励不同，不能据自检声称随机流/全部内部波形一致。
- `wide_indices` 另有 494 共同位，其中 12 位完整时间线与 VCS 不同：部分 128 位下标的有效窄化/范围处理有差异，延续已有 `tests/indexed_selects/large_index.sv` 的已知边界。native golden 根据独立 bit 位置算出；所有差异双方完整时间线在 `vcs-check.json` 中保留，不计入已对齐的 1152 位。
- 17 个实际 ASan/UBSan 程序（含回滚、真正两分区、SDF、流水 CPU）与原生完整输出及对应模式波形一致；8 个 sanitizer 编译器完整生成 C++ 身份、7 类拒绝通过，leak 检测关闭。第一轮 SDF 验收把 native 默认 settled 与 sanitizer ordered 混比而停止；保留初始日志，统一模式后重新运行全部程序通过，没有 sanitizer 故障。
- 受影响旧 CTest：always_sv/indexed_selects/increment_expressions/function_effects 四组，以及 runtime/runtime_drivers/time_runtime 三组，均通过。永久新增两组接入 CTest 及稳定发布，不修改 RTL/gate parser 分离或 DWF 编码。

复核：

```sh
python3 validation/m88-comb-partial/verify.py
python3 validation/m88-comb-partial/run-sanitizer.py
```

`generated-sha256.json` 保存验收 C++ 哈希；原生/ASan 可执行文件与生成 C++ 不入库。VCS 保留实际输入、命令脚本、原始日志与波形，不修整商业工具日志的空格。稳定发布及 Linux 安装记录在完成验收后追加。不新增性能结论。

Linux 已完成发布：GCC 原生构建，parser/comb_partial/complex_report2/always_sv/indexed_selects/function_effects/complex_report/gate_source 八组通过。入口 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 指向 `/apps/EDAs/own/dsim/releases/20261025T030213Z-06125fd/bin/dsim`，binary SHA256 `37194d455797e35bb3e239e1bd92b8fa119cfd795966a25a993c51f384fc427e`。全部源包文件 SHA256、55 份完整生成 C++、43 ordered + 3 报告波形以及全部输出与 macOS 原生一致；加载 syn.bash 后三个实际安装入口用例重新编译/运行通过，完整 VCD 与验收版本逐字节相同。复核命令：`python3 validation/m88-comb-partial/verify-linux.py`。

macOS 稳定发布完成：68 组检查全部 PASS，入口 `~/vibe-coding/dsim-test/bin/dsim` 更新为 `20261025T030148000058Z-bfa2aba2bf5c`；source SHA256 `bfa2aba2bf5cbda5f10b002297a436bd74a76be55ed76e7d79dc4d7970b8f57f`，binary SHA256 `b6c2f1e34cc6024271e391c48e9c1eaecf7237921f2363fde725ee4a24f3fcda`。源输入、八个 runtime 快照和二进制 hash 全部核验；55 份完整生成 C++、43 ordered 捕获及额外三份 VCD/全部输出与原生相同。实际入口重新编译 reported/p21/SDF，完整 C++、输出及整份 VCD 逐字节相同。`git_dirty` 包含无关用户实验与验收文件；所有受跟踪编译输入对应实现提交 06125fd，本地指纹也记录不参与编译的既有 `.DS_Store` 元数据。

复核：`verify-release.py <macOS release>`、`check-installed-local.py <macOS release>`、`verify-linux.py`。GitHub 实现与最终记录均推送；用户 experiments/matvec16 未触碰，不新增性能结论。
