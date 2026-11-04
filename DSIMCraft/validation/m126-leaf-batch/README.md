# M126：FIFO 批次与 Clang / Intel 编译配置联合优化

已完成代码、功能差分、完整负载复测和两端稳定发布。实现冻结为 `6cc95a7f5a5ce9aac48f9f37132cb50faa3fce23`；1708 个源码包成员逐个核对该 Git 提交。后续报告提交不改变这一实现身份。

M125 的纯三指令连续过程注册共享生成处理器，只执行 Active 队首连续属于该处理器的过程。行为过程、其他处理器、wake、区域令牌和预算边界结束批次。每次中间信号发布、Ready 事件、FIFO 次序及逻辑预算保留；部分预算激活永久交回拥有 PC 的原闭包，回退状态和共享处理器上下文参与检查点。这里减少外层调度和闭包调用，没有实现通用 DAG 融合、中间发布消除或固定 NBA 分组。

103 的前端及模型均使用 Intel oneAPI C++ 2026.1.1。模型默认 `-O3 -fp-model=strict -xHost -ipo`；Mac 使用 SDK 入口 `/usr/bin/clang++ -O2`。构建支持 `DSIM_MODEL_CXX`、`DSIM_MODEL_OPTIMIZATION`、`DSIM_MODEL_CXX_FLAGS`；实际默认参数显示在 `--help`，也可通过 `--cxx` / `--cxx-flag` 覆盖。配置与语义边界见 [编译选项](../../docs/compiler-options.md)。

最终运行是 Xeon Platinum 8358 的同一逻辑核心 CPU25，一次预热、三轮换序，编译全部完成后计时。四个原始完整工作量及计数均保留，输出逐次检查。下表是进程 CPU 时间中位数（秒），编译耗时不计入。旧版为冻结 M125/GCC O2；“Intel 原调度”使用同一最终 C++ 和选定 Intel 参数，仅定义 `DSIM_REFERENCE_LEAF_BATCH`。

| 负载 | M125 GCC O2 | Intel 原调度 | Intel 新调度 | VCS | 总耗时降低 | 合批单独降低 |
|---|---:|---:|---:|---:|---:|---:|
| CPU | 9.58 | 9.47 | 9.32 | 5.75 | 2.71% | 1.58% |
| CRC | 3.89 | 3.22 | 3.07 | 4.00 | 21.08% | 4.66% |
| 乘除法 | 8.43 | 7.33 | 7.30 | 6.90 | 13.40% | 0.41% |

编译配置与调度贡献按成对控制分别计算，不能把总收益全算给合批。CPU/CRC/乘除法的新版本 CPU 耗时分别为同批 VCS 的约 1.62/0.77/1.06 倍；CPU 的差距仍明显。AXI4 全输出通过，0.22→0.17 秒的样本较短，作为正确性和短负载对照保留，不作吞吐结论。VCS 墙钟含启动等待，全部 CPU/墙钟样本都在 [linux-full.json](linux-full.json)。Mac 测量期间存在明显的其他主机负载，保留全部数据和输出，但不据此给出可推广的 Mac 加速百分比。

编译器初筛保留 Intel O2/O3/IPO、Clang O2/O3、GCC O3 及第二轮 Intel 本机指令集组合，分别对原/新调度检查：见 [compiler-matrix.json](compiler-matrix.json)、[compiler-host.json](compiler-host.json)。IPO 的编译耗时、二进制体积及每次运行均记录在这些文件里。选择结果说明需要联合调整生成代码与编译配置，编译器名称本身不能保证收益。

GCC O2 的初版公共求值器使 CPU 退化约21.3%，机器码中有54处静态 get() 外部调用点。拆分小函数和局部强制内联候选也未达到采用标准，全部撤回；对应完整负载记录和源码保留在原始归档。GCC 默认保留 M125 路径，`DSIM_EXPERIMENTAL_LEAF_BATCH` 才显式启用；Clang 系列采用新批次。`DSIM_REFERENCE_LEAF_BATCH` 可关闭该批次，保留 M125 的过程内直线执行。

固定前缀独立统计：CPU 的385605次叶过程执行进入184276次批次，少201329次外层处理器调用；CRC 为64688/59447，乘除法为38836/20408。两端的逻辑步、历史全信号哈希、Ready 出入及叶过程数精确一致，物理队列事件没有减少。统计版本与性能计时分开，见 [linux-prefix.json](linux-prefix.json) 和 [mac-prefix.json](mac-prefix.json)。选定 `-xHost` 程序在 Valgrind 下未能通过 Intel 启动指令集检查，本次最终配置没有可用的 Callgrind Ir 测量；原失败输出和归类依据保留在归档及 [profile.json](profile.json)，正常原生运行全部通过。

两端八模型差分各覆盖80份完整有序/稳定 VCD、2104组预算比较和16次预测；576组中断恢复比较中107组匹配既有参考错误，不是576组均成功恢复。新增批次内核各比较1248个 FIFO/预算/检查点/预测状态，包括夹在叶过程之间的行为观察器及无关编译处理器。Mac 三个程序 ASan/UBSan 通过；Linux 额外完整组合区域回归、13项 Intel 内核 CTest、独立 RTL/门级/格式 parser 和原生 DB 检查通过。既有预算异常丢失已弹出过程的限制仍未解决。

macOS 发布时发现直接调用 Xcode 底层编译器缺失 SDK 头文件；改用系统 Clang SDK 入口，新增省略 `--cxx` 的实际编译回归。失败发布没有激活，原错误及候选二进制保留在归档。最终两端安装入口重新生成并完整运行四个负载，C++ 哈希和八份运行时头文件跨平台一致，实际安装验证见 [mac-installed.json](mac-installed.json)、[linux-installed.json](linux-installed.json)。

- Mac 稳定入口：`~/vibe-coding/dsim-test/bin/dsim`；发布 `20261027T081923533580Z-174bb8e00fe9`，二进制 SHA256 `816d655fef42bf78fbfbf74f718c7e4c1bd69c247fb61adb1ac22a6d9ed06735`。
- 103 稳定入口：`/apps/EDAs/own/dsim/bin/dsim`、`/apps/EDAs/own/dsim/dsim`；两者解析到发布 `20261027T082003Z-6cc95a7` 的同一二进制，SHA256 `60f5ee8bdcb23d8ff301436b15da4b0627b482ea05bf859f6eaf9789c139a3a2`。

最终源码包 SHA256 为 `66fc815de932cf93fa7eea9066dfb2359487fd3a44e99e40cafabca8afb8a2b9`。`pre-sdk-source-proof.json` 是被 SDK 修复取代的历史核对记录。源码及两端逐成员验真的原始归档镜像于本地 `~/vibe-coding/dsim-test/evidence/m126-leaf-batch` 和远端 `/apps/EDAs/own/dsim/evidence/m126-leaf-batch`，身份及交叉核对见 [audit.json](audit.json)、[mirrors.json](mirrors.json)。归档不包含 VCS 代码或程序；冻结的 M125 参考程序身份及来源另见 [M125](../m125-comb-leaves/README.md)。
