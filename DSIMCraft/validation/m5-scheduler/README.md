# 事件运行时优化：0.4.2

本批优化 RTL 生成模型的等待登记与事件调度。RTL parser 和门级网表 parser 继续独立；门级 Network 接入、规模基准及 SDF/Liberty/SPEF 时序仿真仍未完成。

## 实现与语义

固定等待位置在模型初始化时登记稳定 watcher 槽位，运行时只更新进程代次及当前槽位；动态 wait API 使用独立槽位，允许与固定位置混用。向量任意变化与最低位 posedge/negedge 分开处理。同一信号转换只计算一次边沿掩码。

Active/Inactive 使用保留容量的值类型环形队列，全量 NBA 使用拥有值的记录，时间队列使用按时间及插入序号排序的最小堆。延迟唤醒仍先入队再执行，保留去重、同刻 FIFO 和指令预算行为；Inactive 耗尽后才提交 NBA，当前 NBA 批次全部提交后再执行其唤起的 Active 进程。部分 NBA 保留提交时合并未写位的语义。

## 正确性证据

本地 AppleClang 21 与远端 GCC 11.5 的最终 CTest 均通过 5/5。包含 27 个端到端正例、26 个拒绝用例、空层次/IR 路径保护及 8 个预算保护。运行时、分配计数和 5 个输入的前端生成另通过 ASan/UBSan。27 个 native 模型在两平台输出完全相同。

- `scheduler_wait_sites`：跨两轮切换等待位置、过期 watcher、向量高位变化、同信号多边沿及恢复。
- `scheduler_regions`：多次 #0 时 NBA 仍待提交，全量/部分 NBA 的完整批次及再次提交。
- 运行时测试另覆盖全部 16 对标量四态转换、动态/固定等待混用、120 进程队列增长与环绕 FIFO、256 个跨时刻计时器、重复唤醒去重及时间溢出。

新增两例使用默认 VCS 配置，每工具执行 3 次。最终 0.4.2 的全部 27 个 native 输出与同输入 VCS 参考重新核对：26 例默认配置，1 例沿用已明确记录的 `-debug_access+all` 参考。`control_loops` 在默认 VCS 优化下的 q=2 与 debug/dsim/Icarus 的 q=59 差异仍保留在[前批记录](../m2-control/README.md)，不计作默认配置通过。前批 5 个 VCS/Icarus 差异仍保留，其余 22 例与 Icarus 相同。

- `local-ctest.log` / `remote-ctest.log`、`local-test-details.log`：完整检查及用例详情。
- `local-results.json` / `remote-results.json`：最终 native 输出。
- `vcs/`：新增两例的 VCS/dsim 配置、输入校验、编译/运行日志及计时。
- `local-final-native-recheck.json` / `remote-final-native-recheck.json`：全部 27 例的最终 VCS 参考复核；前批不变输入参考仍保存在原目录。
- `runtime-sanitized.log`、`allocations-sanitized.log`、`frontend-sanitized.log`：ASan/UBSan 结果。
- `icarus/`、`benchmark-smoke.log`：新增语义例及小规模多扇出输入的 Icarus 辅助差分。

## 堆分配核对

`tests/scheduler_allocation_test.cpp` 在预热 32 个时钟周期后，对另外 10,000 个 clock/posedge/全量 NBA 周期计数。相同内核分别编译到不变的 0.4.1 runtime（动态 wait）及 0.4.2 runtime（预登记等待）。

| 平台 | 0.4.1 C++ 堆调用次数 | 0.4.2 C++ 堆调用次数 |
| --- | ---: | ---: |
| macOS / AppleClang | 89,998 | 0 |
| Linux / GCC | 93,122 | 0 |

原始数据为 `allocations-before.log` / `allocations-after.log` 及对应的 `remote-` 文件。测试统计替换的 C++ new/new[]，并非全部 libc 分配；结论只覆盖上述预热内核。部分 NBA 的片段复制/合并、net 解析、初始化或队列首次增长仍可能分配，不能由此宣称全部仿真路径零分配。

## 源码对应关系

远端隔离目录为 `10.131.254.103:/tmp/dsim-m5-scheduler-1017-tSqRnp`，环境入口 `source /apps/EDAs/syn.bash`，VCS `W-2024.09_Full64`。`source-snapshot.json` 保存本轮上传归档 SHA256 和 45 个实现/测试/脚本/补丁文件的清单；`remote-code-sha256.json` 逐项相同。说明文档可晚于实现归档。

0.4.1 基线使用 `/tmp/dsim-m2-control-1017-4FOZrl/build/dsim`，对应 `baseline-source-snapshot.json` 的 42 个文件。`baseline-verification.log` 保存测量前的完整校验；`post-benchmark-verification.log` 记录全部测量结束后旧版 42 个文件及新版 45 个文件仍匹配。旧目录保持不变，本轮全部生成物写入新目录。

本批没有修改第三方 parser。`remote-parser-sha256.json` 的 11 个文件与[前批干净重放补丁所得清单](../m2-control/parser-replay-sha256.json)及本地工作树一致；补丁重放、生成器冲突数和原始来源证据沿用前批记录。

## 性能测量方法

相同主机上分别用 0.4.1、0.4.2 和默认优化 VCS 编译同一输入。每工具每例预热一次，随后轮换工具顺序各执行 3 次；全部自身负载串行执行。算术循环、clock/edge/NBA 各测 10 万、100 万、1000 万次；64 个独立 NBA 进程共享时钟的扇出负载测 1 万、10 万、100 万次，另有连续 checksum 进程。结果以 Python 仿射变换快速幂或封闭形式校验，编译与运行分开计时，关闭波形输出。

本轮 clocked 输入增加初始 #0，以避开 X→0 negedge 的注册竞争。因此使用本轮同输入重新测得的 0.4.1 数据，不将前批 clocked 时间用作本轮的优化前对照。`benchmark-core/`、`benchmark-fanout/` 保存源输入、SHA256、版本、全部命令、原始日志、墙钟、CPU 和 RSS；`environment.json` 保存主机信息。共享主机未固定 CPU affinity/frequency，CPU 时间有量化误差；VCS 启动包含数秒等待，墙钟比值不能证明核心性能达到 VCS。

全部 9 个输入、三个工具的预热及各 3 次执行均通过独立结果核对。墙钟和总 CPU 均为各自的样本中位数，计算结果保存在 `benchmark-analysis.json`。

| 负载 / 次数 | 0.4.1 墙钟 s | 0.4.2 墙钟 s | VCS 墙钟 s | 0.4.1 / 0.4.2 / VCS 总 CPU s |
| --- | ---: | ---: | ---: | ---: |
| arithmetic / 100,000 | 0.0061 | 0.0073 | 3.2696 | 0.00 / 0.00 / 0.47 |
| arithmetic / 1,000,000 | 0.0292 | 0.0290 | 5.2577 | 0.02 / 0.02 / 0.49 |
| arithmetic / 10,000,000 | 0.2123 | 0.2073 | 3.2869 | 0.20 / 0.20 / 0.52 |
| clocked / 100,000 | 0.0411 | 0.0221 | 5.2930 | 0.03 / 0.01 / 0.52 |
| clocked / 1,000,000 | 0.3746 | 0.1403 | 3.4056 | 0.37 / 0.13 / 0.71 |
| clocked / 10,000,000 | 3.6843 | 1.2971 | 4.4558 | 3.67 / 1.29 / 1.77 |
| fanout64 / 10,000 | 0.1135 | 0.0404 | 4.3131 | 0.10 / 0.03 / 0.58 |
| fanout64 / 100,000 | 1.0394 | 0.2903 | 3.5275 | 1.03 / 0.28 / 0.83 |
| fanout64 / 1,000,000 | 10.2238 | 2.8641 | 7.7286 | 10.19 / 2.85 / 3.06 |

最大规模的时钟负载墙钟改善约 2.84 倍，64 进程扇出约 3.57 倍，算术循环基本持平。以最后两个规模的 CPU 中位数作差，clocked 的 0.4.2/VCS 为 1.16/1.06≈1.09，fanout64 为 2.57/2.23≈1.15；对应旧版约为 3.11 和 4.11。这说明本批减少了这些调度内核的开销，不能推断完整 VCS 或真实设计的性能。

算术 CPU 增量仍为 0.18s，VCS 本轮增量仅 0.03s，粗算比值约 6.00；前批约为 3.00。VCS 增量接近 0.01s 计时精度，固定开销和主机噪声对其比例影响很大，不能据此推断本轮算术实现退化或得到稳定速度比。两版 dsim 本轮的 CPU 增量相同，且没有修改算术路径。更长算术负载及真实设计覆盖仍需后续测量。

## 复现

```sh
ctest --test-dir build --output-on-failure
# 远端 source /apps/EDAs/syn.bash 后
python3 scripts/compare_vcs.py --case scheduler_wait_sites --case scheduler_regions --repeat 3
python3 scripts/benchmark_vcs.py \
  --baseline-dsim /tmp/dsim-m2-control-1017-4FOZrl/build/dsim \
  --iterations 100000 1000000 10000000 --repeat 3 --output build/benchmark-core
python3 scripts/benchmark_vcs.py \
  --baseline-dsim /tmp/dsim-m2-control-1017-4FOZrl/build/dsim \
  --workload fanout --fanout 64 --iterations 10000 100000 1000000 \
  --repeat 3 --output build/benchmark-fanout
```

当前工作没有完成整体 VCS 功能和性能目标。signed/任意位宽、存储器、generate、函数/任务、预处理和波形等 RTL 能力，以及独立门级 Network 仿真和时序能力，继续按 `plan1017.md` 推进。
