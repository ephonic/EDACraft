# 紧凑写入路径合并：独立性能筛选

**后继 B 已验收采用并合入默认构建。** 此处保留构造代码、原始筛选与完整复测。前一版紧凑存储的真实 CPU 收益不足，完整 [撤回证据](../m5-compact-nets/README.md) 保留。

`prepare.py` 从冻结的紧凑候选构造 `include/dsim/runtime.hpp`，差异见 `runtime.diff`。仅在连接已定型、槽尚未转为通用解析且驱动身份相同或首次写入时，一次查找同时写自有驱动值、比较解析值并发布变化。直接 set 后仍能修复；首次 Z 仍登记驱动身份。初始连接、额外身份及 alias 走原解析路径。波形和并行观察按同一顺序通知，四态边沿只区分 0、1、未知，不区分 X/Z 的编码顺序。

本地普通与实际 ASan/UBSan 核心程序通过；Linux 普通核心程序通过。使用前一版冻结的完整四态、驱动、混合 ID 原子操作、别名、检查点/预测、延时及多 worker 测试。未完成本候选两平台完整回归，不作采用决定。

`screen.py` 用完整真实网表的 128 组完整 golden 和 100k ff 反馈比较已验收原版、紧凑 A、合并写入 B 与 VCS。所有既有二进制核对 SHA，B 只替换 A 生成代码中的 runtime，完整模型主体逐字相同；使用相同 C++17/O2。先完成全部编译，再同核串行预热与旋转计时，真实五次、反馈三次。共享主机未独占/锁频。筛选收益通过后才运行完整候选回归；未通过则保留实验并继续下一热点。

远端目录 `/tmp/dsim-compact-drive-1018-im30mgm0`。源归档与 SHA 见 `archive.json`；状态以进程和实际结果为准。

## 筛选与本地回归

完整真实网表五次旋转的 CPU 中位数：已验收原版 14.01s、紧凑 A 13.28s、合并 B 11.90s、VCS 9.15s；B 比原版减少 15.06%，五轮均快，约为同轮 VCS CPU 的 1.30 倍。真实 RSS 88,360→73,412 KiB。100k ff 三次旋转 CPU 原版/A/B/VCS 为 6.44/6.01/4.87/6.54s。原始计时、完整输出、生成 C++ 与独立复算见 `screen-verified` 和 `screen-analysis.json`。此时仍待独立配对和 Linux 全回归，不能作为采用结论。

冻结完整候选 `/tmp/dsim-compact-drive-full-source.tar.gz`，SHA `407e8620ad6e4580c4a98c0b7cc95e89173268af9deb24caa1658984115e6fa1`；160 工程/108 parser/3 原型依赖，单独包含 B runtime。同期 SDF 原始绑定更新不在这份候选中，另批冻结。本地 28/28、24 个生成模型边界、18 完整 ordered/internal 流、9 个实际 ASan/UBSan 程序（8 个真实生成 baseline/replay +核心）与 1 个实际 TSan 通过；15 门级+3 延时组的新 native 三次对既有同输入 VCS 三次通过。关闭 compact 时，3 份完整 header、8 种宏配置的预处理/汇编与已验收后端一致。

Linux 后续包装脚本第一次因外部 EDA setup 在 nounset 下读取未定义 LD_LIBRARY_PATH 而在启动测量前退出，原日志保存 `linux-full-environment-error.log`；改为 setup 后才启用 nounset。当前唯一流水线先做五次配对，再结束全部计时后构建和测试。waveform 测试依赖 gate_regression 产物，因此先并发运行其余 27 项，再单独运行它，总计 28 项；不是同时运行多个计时任务。

## 最终采用

独立五次交替配对真实 CPU 13.59→11.33s（减少 16.63%，五对均改善），RSS 88,976→73,696 KiB（减少 17.17%）；反馈 CPU 6.60→5.09s（减少 22.88%，五对均改善）。本轮无 VCS，不能混用筛选轮分母。原始计时、完整输出与复算见 `full-verified` / `full-analysis.json`。Linux 27+1=28 项通过（前 27 项 124.41s、波形 132.45s）；本地候选完整 28 项 262.68s，最终默认构建合并独立 SDF 更新后再次 27+1=28 项通过。

决定 `ACCEPTED`；最终生产源共 161 工程/108 parser/4 原型依赖（精确 SDF header 仅作测试依赖），见 `production-snapshot.json`。默认编译器与完整组合已重建验证，门级 C++ 与实测冻结候选逐字一致。SDF 原始绑定独立两平台 4/4 和 ASan/UBSan 通过；没有实际路径注解或 VCS 功能持平的声明。

筛选证据 SHA `49ec0a929a9f4b69d6bedfdcbf7729b4910765bd9b353e35e100eea78d038dee`；复测/全回归证据 SHA `5208c1a98a05655ec4fad09f886d4453367025f8b450590f602585653cd20762`。`verify.py` 从冻结源和原始日志重算，后续性能候选不覆盖本批源、证据或实际 sanitizer 二进制。
