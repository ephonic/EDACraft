# SDF 标量交付实验

当前实现为显式 `--gate-scalar-timing`，默认关闭；上一批验收的 compact 接收端仍为默认。新增标量通道/事件存储、通用宽值的独立池、IC/IOPATH 标量 handler 和保持原 FIFO 的直接 compact 发布。两个 parser、SDF parser 和 DWF 编解码器未改，未减少中间进程数量或提前计算路径延迟。

冻结 416 文件源包 `/tmp/dsim-scalar-timing-source.tar.gz`，SHA256 `2942f76c2d03bfd0f01ba1e6960126bfd41492909a06a22237e417a8ef619e6d`。相对上一批只修改 runtime、三个编译器实现/头文件、CLI 和 CMake，新增两个测试入口；逐项见 `source.json`、`changes.json`。

macOS 完整 **64/64** 通过（249.65s）。新增测试复用原 delayed-driver 的全部四态/64 位/取消/alias/FIFO/预测场景，另以独立明确时间线覆盖混合标量与 257 位向量、值池重用、无效请求、路径戳和 1/2/4 worker 全局结束。实际生成 generic/scalar/scalar+batch 三后端的五组完整 stdout 及 ordered/settled × VCD/raw DWF/Zstd DWF 共 90 捕获一致，另有实际生成 IC/IOPATH/HOLD 程序的四份边界/回滚捕获一致。

实际标量 driver、混合向量/结束内核及实际生成 scalar IC/IOPATH/check 回滚程序均通过 macOS ASan/UBSan，原生 ordered/settled 波形与独立边界运行一致；不是 Linux sanitizer 结论。关闭实验宏时，对上一批真实 121MB 完整 SDF 程序替换整个 runtime 后预处理逐字相同，SHA256 `3250ef4253fdf27b7cb208bfa7f1e64162f102721ae1d8a5ac2e86bbe667cb40`。

Linux 隔离干净构建/完整 **64/64** 已在原会话 78417 正常退出 0，远端目录 `/tmp/dsim-scalar-timing-1018-zfozDNNq`。701 个证据文件已归档并下载核对，归档 SHA256 为 `f855eee1838711a193978aa816e9d3641b90045b70cf608308c3ef898a614e64`；`verify_functional.py` 对两平台源码身份、每平台 94 份捕获、完整日志及本地 sanitizer 独立核对 PASS，见 `local-validation.json`。后续 `prepare_full.py` 用最终 Linux 编译器重读原始完整网表/Liberty/SDF，核对关闭选项的完整生成身份、开启选项只差宏和两个 handler，构建实际程序并逐笔核对 128 输出。`measure.py` 要求两端功能验收和真实程序验证通过后才开始五对同核交替计时；首轮性能初筛及独立复测结果见下文。

首次定向 flow 测试将含层次引用的 VCS 激励直接送入 RTL parser，在 generic 对照即语法失败；记录保留于 `targeted-initial-fixture-error.log`。已沿用既有 compact 对照的 native 激励生成方式，仅使用可编译的顶层观察，同时完整原生波形仍覆盖门级内部信号。最终冻结测试增加实际生成回滚验证，之前的初始源包/清单另存 `source-initial.json`，未发生性能样本重启或筛选。

实际完整 SDF 验证现已完成：最终 Linux 编译器重读原始输入生成 default/scalar 两版，覆盖 790,222 INTERCONNECT、867,982 IOPATH 和 86,496 未关闭检查，23,051 个负 limit 仍按默认夹零。default 完整程序仅替换整个 runtime 后与已采用版本相同；scalar 整个程序只再差宏和两个 handler。使用相同 `c++ -std=c++17 -O2` 构建后，scalar 的 128 笔输出逐笔匹配同模型的既有 VCS 参考。30 个原始证据文件已归档，SHA256 `debefe94f2af34183027d78c76df56afc5297d8bebba321d16ba0150c59dee82`，`verify_full.py` 独立核对 PASS，见 `full-verification.json`。后继 NBA 与流式波形的远端任务全部终止并验收后，固定 CPU0 的五对交替初筛已在原 session93826 正常退出 0；各预热一次，未因观察超时重启。见 performance-inflight.json。完整性能结果见下文。

首轮性能初筛现已结束并独立核对 PASS。固定 CPU0、各一次预热后五对交替，完整原始 SDF、无波形、默认非负检查，每次核对全部 128 笔输出。五对 CPU 耗时下降分别为 **15.61%/10.86%/14.05%/10.52%/17.45%**，配对中位数 **14.05%**；CPU 中位数 compact **116.49s**、scalar **102.71s**，RSS 中位数 **636,348→532,252 KiB**。共享主机且未锁频率，尚待独立复测及后继版本接入验收，候选仍默认关闭。没有本轮 VCS 计时，不将旧 VCS 分母与新时间相除。

56 个原始证据文件归档 SHA256 `b590ff7b26554ce4ba750db815ab15475c7485e450feb1be6d6bc6a8f245a8f3`；`verify_performance.py` 从原始 GNU time、逐笔 stdout、源/二进制身份、执行顺序及逐次环境记录重算结果，见 `performance-verification.json`。本次只有首轮收益，尚不构成默认采用结论。

工作区随后推进 RTL 延时 NBA。需要复查本批 416 文件源时，使用 `python3 validation/m5-scalar-timing/verify_functional.py --source-root /tmp/dsim-scalar-timing-frozen-1018`；不可将后继源码称为本次冻结候选。

修正RTL连续向量delay的425源已完成两平台/新VCS/实际全SDF默认及标量身份独立核对后，启动唯一一次独立五对复测，原会话48011、同远端根目录。已确认 `replicate.py` PID1228838及固定CPU0的基线预热仿真PID1229010实际存活；各预热一次，五对交替顺序相对初筛反转，保持源和二进制身份不变。见 `replication-inflight.json`。测量期间不在远端启动本会话的构建/回归/剖析；下一步只观察同一进程，正常终止后才抓取/独立核对。尚无复测收益或新的VCS比例，候选默认仍关闭。

独立复测已在原会话48011正常退出0，58个原始证据文件经`verify_replication.py`独立核对PASS，见[replication-verification.json](replication-verification.json)。固定CPU0、每程序一次预热，五对执行顺序相对首轮反转，12次运行各128笔输出均匹配，源及二进制前后身份未变。五对CPU耗时下降为14.63%/20.55%/9.58%/11.86%/17.36%，配对中位数**14.63%**；CPU中位数compact **111.15s**、scalar **94.89s**，RSS中位数**634,088→529,536 KiB（下降16.49%）**。归档SHA256为`4785530a365ec89506b9f5758fba19ac42f4c2140d2ea0650703b4858436edd5`。共享主机未锁频率，两轮收益均已复现；满足初筛与复测门槛，当前组合源码接入验收尚待完成，选项仍默认关闭。本轮没有VCS计时，不计算新的VCS速度比。上述“尚无复测收益”为此前启动时的历史状态，以本段最终核对为准。
