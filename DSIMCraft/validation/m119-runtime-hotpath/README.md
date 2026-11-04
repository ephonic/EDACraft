# M119：标量信号边沿通知热路径

实现冻结：`4d56bbcd092e871301591012e2739410988d9592`。基线是含 M117 runtime 的 M118 稳定版。采用四态边沿查表，撤回没有稳定收益的驱动历史冷存储候选。

## 完整负载实测

103 服务器、GCC 11.5 `-std=c++17 -O2 -pthread`、固定 CPU 0。每个程序预热一次，再按轮次换序测三次；所有程序编译完才开始计时。原始 RTL、TB、输入和工作量不变。没有 PGO、缩短循环或修改事件预算。表中为完整仿真的用户加系统 CPU 秒中位数。

| 原始负载 | M117/M118 参考 | M119 | 下降 | 同批 VCS | M119/VCS CPU 耗时 |
|---|---:|---:|---:|---:|---:|
| CPU | 13.16 | 12.30 | 6.5% | 5.73 | 2.15 |
| CRC | 4.32 | 4.29 | 基本持平 | 3.91 | 1.10 |
| muldiv | 9.86 | 9.49 | 3.8% | 6.89 | 1.38 |
| AXI4 短控制 | 0.23 | 0.23 | 持平 | 0.57 | 不作吞吐比较 |

[measurement.json](measurement.json) 保留每次 CPU 和墙钟样本，包括不利样本。共享主机仍有抢占和频率变化；VCS 墙钟包含较明显的启动/等待，本报告不把 CPU 比例当作墙钟比例。AXI4 太短，不据此宣称优于 VCS。48 组完整 stdout/计时日志、12 个执行文件身份和四个 M117 参考代码段均独立复核，见 [measurement-audit.json](measurement-audit.json)。

## 实现与因果边界

`set_planes` 在值确实改变且存在订阅后，用新旧 `a/b` 位平面最低位形成四位索引，读取 16 字节常量表。X/Z 的正负边沿规则相同；向量高位变化而最低位不变时仍保留 change 事件。原值规范化、观察、等待代次检查、FIFO 去重和唤醒顺序全部沿用。宽值、字符串和门级构建保留原判断；`DSIM_REFERENCE_EDGE_MASKS=1` 恢复参考分支。

固定 200000000 tick 前缀的步数、时间及全部信号状态哈希相同。Callgrind 指令分别下降 CPU 2.45%、CRC 0.28%、muldiv 2.63%，见 [profile.json](profile.json)。它们是指令测量，不能当作耗时比例。没有减少逻辑执行步、组合过程执行数或队列事件数，也没有完成组合区域融合。

正式测量最初使用相互隔离的候选宏；归并为默认实现后，另外重新生成四个最终模型、编译默认和参考共八个程序。每个 `.text`、`.rodata`、`.data` 逐字节等于实测对应版本，见 [final-machine-code.json](final-machine-code.json)。四个参考 `.text` 也逐字节等于冻结 M117。当前模型源码身份见 [final-models.json](final-models.json)；最初实测源码身份仍原样保留，不混为同一个哈希。

## 功能验证

- 新增独立四态/向量边沿内核，每个默认/参考变体穷举 96 个场景，涵盖 1/7/64 位及仅高位变化。
- 四组模型（穷举 RTL、网络/别名/反馈、force、多驱动和宽值回退），默认/参考/时间轮/并行对照：40 份完整 ordered/settled 波形、1052 组精确预算及完整状态、8 次预测接受/拒绝均一致。ordered 比较也核对跨信号事件顺序，见 [regression.json](regression.json)。
- 条件事件 38 份捕获及实际双分区、并发断言 41 份捕获和回滚/拒绝检查通过，见对应 JSON。七项本地内核通过；三份真实生成程序和一份边沿内核 ASan+UBSan 通过，见 [kernels.json](kernels.json)、[sanitizers.json](sanitizers.json)。
- 发布时重新运行 scalar_edges、nba_storage、runtime_windows、wait_rearm、原始 AXI4 层次数组和 gate_source 六组回归，以及 parser/格式/native DB 检查。安装入口另外重新生成并完整运行四个原始性能负载，要求最终 CPP 字节相同和完整 stdout 相同。

## 已撤回的布局候选

先试验将普通标量 Signal 的驱动历史移到独立的深拷贝存储，Signal 从 96 缩到 64 字节。功能对照通过，但完整 CPU 仅 13.06→12.95 秒，CRC 4.48→5.05 秒，muldiv 10.00→10.40 秒，没有稳定整体收益，未发布。主机干扰同时存在，不把退化归因于未经测量的缓存因素。

[rejected-layout.patch](rejected-layout.patch)、[rejected-layout-measurement.json](rejected-layout-measurement.json) 和功能结果保留。重现这个被否决的独立实验应从 `387a02c` 检出后应用补丁；它早于本轮边沿查表，不能直接混用当前默认表路径解释数据。

## 源码、发布与证据

1687 个打包源码文件逐个对应冻结 Git 树，见 [source-proof.json](source-proof.json)。包 SHA-256：`100810540b63c81ee0c6ad6849a146b4475a9da6f5a4bbed0c70243527a410ed`。打包和证据均排除了用户 `experiments/matvec16/`，该目录保持原样。

发布身份和两端安装验收记录保存在本目录的 release/installed JSON。原始自有生成源码、全部计时日志、波形及 Callgrind 文件使用逐成员 SHA-256 清单归档；不包含 VCS 私有生成代码或执行文件。稳定目录 evidence/m119-runtime-hotpath 保存 `source.tar.gz`、`mac-raw.tar.gz`、`linux-raw.tar.gz`，分别位于本地 `~/vibe-coding/dsim-test` 和 103 `/apps/EDAs/own/dsim` 下。

`measure.py` 与 `profile.py` 适用于冻结的最终默认实现，参考开关为 DSIM_REFERENCE_EDGE_MASKS；原始阶段脚本也保存在原始归档内。重新测量时先由该冻结版本生成四份完整 CPP 到新测量目录，再运行 measure.py --root 指向该目录（默认 /tmp/dsim-m119-remeasure），并提供所需的冻结 M117/VCS 对照；不要把被否决布局阶段的 CPP 当作最终模型。profile.py 从 /tmp/dsim-m119-final-models 读取最终源码，写入独立的 /tmp/dsim-m119-reprofile。`final-proof.py` 保留阶段到最终版本的机器码核对方法。`verify-installed.py` 使用 final-models.json 核对安装入口源码，运行输出逐字节对照实测版本。

最终验收已完成：同源 VCS 四组模型共 48 行 TRACE、1118 个静态数值位的完整 settled 时间线一致，见 [vcs.json](vcs.json)。两端安装入口四个完整负载全部通过，生成 CPP 与最终冻结模型逐字节相同；Linux 两个入口解析到同一不可变版本。

- 本地稳定版本：`20261026T145801444712Z-dca59a1d80bb`。
- 103 稳定版本：`20261026T150711Z-4d56bbc`，二进制 SHA-256 `a20a2673e9f481660c07d28efd01c9714a8401dbb3bc87b12997b6795c5506e4`。
- 两端各六组发布回归及 parser/格式/native DB 检查通过；Linux 另八项内核通过。源包与两个原始归档已在两端保存并核对 SHA-256，见 mirror/ raw JSON。
