# 保持 FIFO 的组合单元批量执行

本批实现显式 `--gate-batch`，默认关闭。编译器生成原生模型 switch，运行时连续执行同一 handler/context 的队首前缀，逐门保持输出驱动、重新等待、queued 和 step 语义。其他进程、wake、延迟交付、Inactive/NBA 和时间推进仍由原调度循环处理。支持边界和命令见[执行模式](../../docs/gate-batches.md)。没有实现任意组合锥融合或多线程执行。

原始真实网表与 1.2GB Liberty、原 256/257-bit 接口及测试平台未改。Linux GCC 11.5/C++17/O2，同一 CPU、每工具一次 warmup 后五对交替运行，所有编译和功能回归先结束。真实设计各次完整 128 笔输出匹配此前已编译且本轮重跑的 VCS W-2024.09；VCS 没有重新编译。反馈负载为独立 Boolean recurrence 预期的 100k FF/100k XOR、200 周期。

| 负载 | 默认 CPU 中位数 | batch CPU 中位数 | 配对收益中位数 |
| --- | ---: | ---: | ---: |
| 原始 300,909 单元设计 | 12.38 s | 12.15 s | 2.26% |
| 100k FF 反馈 | 5.00 s | 4.85 s | 3.41% |

真实设计 batch 五对均更快，但未达到既定 3% 门槛，`screen_qualifies=false`，不做默认采用或独立复测。反馈有一个明显慢的默认样本 5.95s，原样保留，使用配对中位数而不是最好一轮。VCS 真实设计 CPU 中位数 10.48s，batch/VCS 约 1.16；单次 VCS 为 10.16–12.41s，主机共享且频率未锁定。上述仅是本配置的单核零延迟、无波形比较，不能外推 RTL/SDF/波形/并行或与旧 64-bit 包装测试混算。

两平台各通过两个定向 CTest 入口：独立内核覆盖四态、混合动作、固定等待、Active wake/Inactive/NBA、延迟取消、到达、实际回滚及 89 个预算边界；实际编译器覆盖八组完整 stdout 和 ordered/settled VCD/DWF，包含多驱动/alias、宽原子复制、反馈、时序事件区域及 SDF INTERCONNECT/IOPATH/HOLD。两个生成程序实际执行失败预测/回放。一个实际生成程序的计数为 5 次入口处理 11 个事件，性能程序不开启该统计。没有把这两个定向入口称作累计 53 项完整回归。

本地内核和实际生成的 SDF 回放程序均经 ASan/UBSan 执行通过，后者核对完整 ordered DWF/stdout。Linux sanitizer 库缺失在前一批已确认，本批没有重复安装或尝试，不作该平台 sanitizer 结论。

首轮回放测试多插入了空 tick 1，而 SDF 普通执行下一 tick 为 3；修正检查点边界后完整流相同。随后重跑遇到已有波形文件保护，测试现先清理自身指定输出。两次测试工具问题日志保留，未放宽波形比较、事件调度或 SDF 规则。

`source.json` 标识最终源码包及逐文件 SHA256；相对上一批仅改六个编译器/运行时/构建文件并增两个测试文件，RTL/gate/parser、SDF parser 和波形解码器未改。`linux/performance` 保存实际生成 C++、IR、编译命令/成本、各次 stdout/stderr 和 GNU time 原始记录；`linux/build/gate-batch` 保存完整八组生成程序/波形与回放。`verify.py` 重新核对源码、完整流和原始 CPU 数据。

默认后端保持原执行方式。本轮停止调批量循环的局部参数，后续转向原始全量 SDF 的模型生成/身份匹配和条件路径，以及普通网表分区执行与波形汇合。
