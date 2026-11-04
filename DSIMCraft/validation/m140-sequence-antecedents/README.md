# M140：有限序列作为蕴含前件

已支持单时钟 `a ##N b |->/|=> c`，连接已有命名 sequence、固定重复、分组、采样和异步取消。前件未匹配为空成功；后件从前件匹配终点或下一拍开始。实现范围与明确限制见[专题](../../docs/sequence-antecedents.md)。

实现提交 `d8e7b3ddd4705fd5aa86d0c9846a99d256056c01`，源码归档 1785 个文件逐项与 Git blob 一致，SHA256 `d209ebdccd9b7c3fc3b64d463d5f580b2c057ba2cea8e72855d07bc1e856927a`。

| 平台 | 不可变 release | binary SHA256 |
| --- | --- | --- |
| Mac | `/Users/yangfan/vibe-coding/dsim-test/releases/20261028T075231833140Z-16d77bedb367` | `52df6cb5500fe6ba2f44fee33a791f54f81020d942f698e9dbba5e557b18b8ec` |
| 103 Intel | `/apps/EDAs/own/dsim/releases/20261028T075238Z-d8e7b3d` | `51e268cc2780eeb23e32a29af544e88b9e6396fb22ccb5e0283adf40c3205c03` |

两端均已激活，并通过稳定入口重新编译 basic；生成 CPP SHA `cb22554cbf2d349db8ecaa5a5361d0c0029ff8a13e098bdc073e559bc7a2dd27`，完整输出与逐信号有序波形与各自发布回归相同。103 继续使用 Intel O2/xHost/strict FP，无 IPO，未改变 M139 的发布选项。

双端各五组回归为 sequence_antecedents、named_sequences、concurrent_assertions、sampled_values、budget_resume，另必跑 RTL parser/多格式 parser/原生 DB 单元。新组每端 29 份逐信号有序捕获，5 次提交、5 次回滚、4 次预算续跑、2 次 checkpoint 重复恢复及 15 个拒绝例，parallel 模型为实际两分区。基本模型预期按固定激励直接计算每个起点的匹配终点，算法不复用运行时尝试队列；边界和双分区另有独立最终计数。完整 parser 和 11 份实际生成程序 ASan/UBSan 通过，leak detection 关闭。

VCS W-2024.09_Full64 同源模型 basic/sampled/clones/boundary/parallel 全部 TRACE 对齐，逐一比对层次归一化后的全部 1503 个声明位 settled 时间线。归一化只拆分自有输入中点号层次组件，拒绝碰撞；原始未配对声明另列 JSON。没有声称跨工具内部事件顺序完全一致。VCS 生成代码/二进制留在私有临时目录，导出只有自有源、observer、输出及 VCD。

运行时只在多阶段前件模型启用新宏，阶段分界及尝试队列由 Sim 保存，checkpoint/预测沿用值复制。`runtime.hpp` 变更，其他七个头文件与 M139 相同。六个旧 CPU/CRC/muldiv/AXI4/chain/history 模型在替换整个嵌入 runtime 后，其余 CPP 完全一致；保存原始与归一化后 SHA，不把它表述成整体代码或二进制性能不变。没有速度测量。

开发阶段前四个模型通过，最初两版 parallel fixture 的跨域观察器及默认失败 I/O 造成保守单分区；已改为有限独立时钟和局部显式失败计数，正式完整组重新通过。旧套件的四条“拒绝序列前件”检查改由本组正例接替；旧组其他正反例保留。Bison 3.8.2 的 shift/reduce 冲突数仍为原有 76，RTL/gate parser 保持分离。

证据在两端 `evidence/m140-sequence-antecedents/`，包括冻结源码、VCS 自有证明、完整回归 CPP/日志/波形、生成保持检查、sanitizer、入口及开发记录。`evidence-index.json` 记录每个归档的 SHA；报告归档与单独的 index/mirror proof 避免递归身份，所有归档镜像逐字节校验。

重放：`python3 tests/sequence_antecedents/regression.py DSIM OUTPUT CMakeCache.txt`。`compare-vcs.py` 使用同源 VCS 自有证明验证发布候选；`generation.py` 只归一化整个嵌入 runtime；`activate.py` 在源码/二进制/全部回归与波形证明一致后切换入口；`check-entry.py` 实测入口。
