# 紧凑内部单比特网候选

**未采用，已恢复已验收生产后端。** 不宣称真实设计的新加速。前两版标量表达式没有稳定收益，见 [被拒候选](../m5-scalar-logic/README.md)。本版保持旧 V 表达式、ff/latch capture、输出算法和全部模型过程安装不变，改变符合条件的内部 net 表示。

编译器按完整门级 IR 逐叶输出统计驱动数，选择非端口、非常量且恰有一个叶驱动的 net。门级生成模型单独开启 `DSIM_COMPACT_GATES`；普通 RTL 不开启。`CompactSignal` 48 字节、原 Signal 96 字节，不将这个对象大小比当作整机内存或速度结论。每槽保存当前和自有驱动的两个位平面、驱动身份、原顺序 watch、逻辑创建序号与可选通用回退。首次 Z 驱动、直接 set 和驱动值分别保留；额外身份驱动/alias 转入完整 DriverValues，没有值事件。slot 深复制可选状态，检查点包括它们和所有元数据。

负 ID 区分紧凑槽；原来对正整数的排序不足以保留创建顺序。结构 copy、alias settle 和 assign_parts 均先读取/解析全部值，再按逻辑创建顺序发布。波形注册/初始值与通知、延时通道、保守并行输入端点接入两种槽，不过滤内部观察。波形编码格式不变。延时注册可将该槽转到通用表示，尚未优化时序热路径。SDF parser/绑定边界仍不变，实际自动回标和自动分区尚未实现。

源冻结 `/tmp/dsim-compact-nets-source.tar.gz`，SHA256 `197bed7720b01cab682b7776969cdece64acb6f3cca2a4f7b87b6b1b188fbb7b`；160 工程、108 parser、3 个不变原型依赖及 7 个驱动/参考文件。已验收基线仍为生产源 `7d50442262e323b6b421a17abbe215e9b8e3c1f8a7f35378ba619f4f5426d6c3`，远端 `/tmp/dsim-scalar-baseline-1018-HrfyrU`。候选 `/tmp/dsim-compact-nets-1018-fjVtmi`。两种 parser 保持分离。

`gate-mask.py` 独立从原版生成模型的全部 cell/pin 数组、输出函数/copy、常量与端口连接重建 eligibility，并逐项核对候选表；去除 runtime/macro 和 net 创建语句后，完整生成代码须逐字相同。真实 128 组完整黄金值、100k ff 和三类普通 RTL 同输入重新生成/编译，同核串行旋转原版/候选/VCS，再用同二进制做五次配对复测。原始库/网表不简化。共享主机不独占/锁频，各轮分母不混用。

当前初步通过：完整四态/额外有符号身份、直接 set 修复、独立边沿表、混合槽创建顺序与原子 copy/parts、alias 前后 watch、深复制/预测事务、延时与 1/2/4 worker×5 quanta 端点。关闭宏时，全部 8 种 wave/timing/parallel 组合的预处理代码与优化汇编逐字相同。18 条完整 ordered/internal 波形与已验收版本一致。完整两平台回归、实际生成模型 sanitizer 和性能测量继续中；最终结论见随后 analysis/decision。

本地完整 CTest 28/28（263.87s），最终核心 fixture 重建复核 1/1；19 个实际 ASan/UBSan 程序（11 核心、8 个生成 baseline/replay）以及 1 个实际紧凑/并行 TSan 程序通过。所有生成 ordered/settled 回放完整一致，19 个程序的符号与 SHA 由 `local-verify.py` 复算。macOS 使用 detect_leaks=0，不声明 LSAN。`local-analysis.json` 状态 PASS；Linux/性能流水线仍在运行，未作采用决定。

Linux 完整 28/28（495.74s）、15 门级和 3 延时组的新 native 三次对既有 VCS 三次、新编译 256 组表达式 native/Icarus/VCS 三次通过。独立审计 24 个本地生成回归模型的 compact eligibility 与完整代码边界（其中包括额外边界 fixture，不是 24 个 VCS 组）；丢弃紧凑条件分支后三份完整 runtime/waveform/parallel header 逐字相同。首轮真实性能已测到，仍待全部主轮和五次配对完成后决定采用，不从首轮较小 CPU 改善作结论。

## 最终决定

原始证据独立复算全部通过；真实性能门槛未达到，决定 `NOT_ADOPTED`。主轮同核 CPU 中位数：

| 负载 | 原版 | 紧凑候选 | VCS |
|---|---:|---:|---:|
| 真实 300,909 单元 | 18.86 | 18.39 | 13.88 |
| 100k ff 反馈 | 8.26 | 5.93 | 8.11 |
| RTL clocked | 2.77 | 2.83 | 2.94 |
| RTL fanout | 2.77 | 2.96 | 3.41 |
| RTL arithmetic | 0.39 | 0.39 | 0.46 |

同二进制五次交替配对：真实 CPU 14.48→14.37s（仅减少 0.76%，3/5 对改善），RSS 86,192→71,224 KiB（减少 17.37%）；反馈 6.81→6.14s（减少 9.84%，4/5 对改善）；RTL fanout 2.70→2.74s。内存收益保留，但不将其代替真实 CPU 收益。复测未运行 VCS，不能混算主轮 VCS 分母。三类普通 RTL 的实际 `.text` 与 `.rodata` 逐字一致。

已按 SHA 恢复 159 个工程文件、108 parser 与 3 个原型依赖；默认构建重建，9 核心回归和四条 CLI counter 输出通过。候选 fixture 仅保留冻结源及 `candidate-compact_nets.cpp`。这是恢复确认，不是恢复版本重跑 28 项；后续 SDF 接口变更另批记录。

证据归档 `/tmp/dsim-compact-nets-evidence.tar.gz`，SHA `68caf7f0f7949d67c8681736a73f3f779f3247e3038b86ebfd61cb255e8080d5`，1,472 文件。`analyze.py` 从原始日志复算；`verify.py` 用冻结审计源复核，不依赖当前工作区保留候选后端。

下一步独立筛选 [合并紧凑驱动写入路径](../m5-compact-drive/README.md)，减少同一槽的重复查找和 V 转换。完整真实网表性能及后续全回归仍是采用前提。
