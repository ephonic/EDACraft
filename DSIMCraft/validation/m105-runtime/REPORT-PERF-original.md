# dsim vs VCS 性能对比（同机 mn02，simv 运行时间）

- 日期: 2026-10-25
- 主机: mn02（10.131.254.103，Intel Xeon Platinum 8358 @ 2.60GHz，CentOS Stream 9）
- 绑核: `taskset -c 0`；计时: `/usr/bin/time -v`，warmup + 3 次取最优（wall clock）
- 工具: VCS W-2024.09_Full64；dsim = 服务器 `/apps/EDAs/own/dsim`（20261025T1230~1346 系列，测试期间服务器自身有更新）
- **只比较 simv 运行时间**（编译一次性完成，不计时）
- 工作负载跨工具逐位一致：确定性 xorshift32 激励，双方输出 PASS + 相同校验和

## 一、真实设计基准（本套件，perf-kit）

| 基准 | 工作量 | dsim | VCS | 相对 |
|------|--------|------|-----|------|
| bench_cpu | 5 级流水 RV32I，4.5M 指令 / 7.5M 周期 | 32.39s | **7.53s** | **VCS 快 4.3x** |
| bench_axi4 | AXI4 突发，30k 突发 / 205k 拍 | **0.36s** | 2.36s | **dsim 快 6.6x** |
| bench_crc | CRC-32 流引擎，160k 帧 × 64B | 12.43s | **6.10s** | **VCS 快 2.0x** |
| bench_muldiv | Booth 乘 + 恢复余数除，1.2M 向量 | 19.06s | **10.22s** | **VCS 快 1.9x** |
| bench_cache | 2 路写回 Cache，1.2M 次访存 | 15.51s | 见下注¹ | — |

¹ bench_cache 的 VCS 出现**非确定性挂死**：同一二进制 3 次计时段全部 600s 超时（无 STUCK 看门狗触发），此前一次手动运行却在 4.29s CPU 完整跑完 1.2M ops 且校验和与 dsim 一致。dsim 侧 12 次运行全部确定性通过。属 VCS 对该 TB 轮询形态的调度异常（详见下文），故此项不给 VCS 定值。

**所有完成的运行双方校验和逐位一致**（如 cpu=0x0044aa1f、crc=0xfab30761、muldiv=0x9e4be39a、axi4=0x000000ff）。

## 二、微基准（团队 m98 证据，同机同方法论，供参照）

| 基准 | dsim | VCS | 相对 |
|------|------|-----|------|
| arithmetic-1G（纯组合运算 10 亿次） | **1.53s** | 4.47s | dsim 快 2.9x |
| clocked-30M（时钟翻转 3 千万次） | **4.29s** | 5.70s | dsim 快 1.3x |
| fanout-3M（高扇出网络） | **7.96s** | 10.65s | dsim 快 1.3x |

## 三、结果解读

1. **两种负载画像分明**：
   - DUT 事件密集、TB 轻（微基准、axi4 突发流）→ **dsim 显著更快**（1.3~6.6x）
   - TB 过程代码密集（任务调用/等待循环主导：cpu、crc、muldiv 的逐操作 task 握手）→ **VCS 快 1.9~4.3x**
2. dsim 的 wall≈user（计算饱和）；VCS wall > user 约 25-60%（启动/IO 开销约 2s）
3. 结论：dsim 的事件引擎效率高（每事件成本低）；过程级 TB 执行调度是当前相对 VCS 的主要差距点

## 四、过程中发现的工具问题（记录）

1. **VCS up-to-date 误判**：源文件改动后 `vcs -o simv` 报 "up to date" 复用旧二进制，多次产生假数据（本测试全部改用唯一输出名+强制重编译规避）——注意这是 VCS 侧行为
2. **VCS 对 `while(cond) @(posedge clk); #1;` 轮询形态非确定性死锁**（cache/crc 初版 TB 在 VCS 下卡死、加打印即恢复）；改为 negedge 轮询 + 看门狗后 crc/muldiv/axi4 稳定，cache 仍有 3/4 概率挂死。dsim 对两种形态均稳定
3. 连续赋值读未打包数组内容（`wire h0 = v_arr[...] && ...`）按 LRM 对内容不敏感，VCS 严格执行导致语义偏差——cache DUT 已改 always_comb（两工具行为一致，跨工具可移植性修复）

## 五、复现

```
# 远端（mn02，需 VCS license）
cd ~/dsim-perf-kit && ./compare_remote.sh     # 全流程：构建+warmup+3 次
# 本地（仅 dsim 侧）
cd rtl-tests/perf-kit && ./run_dsim.sh
```
注：本文件早前版本中的 Apple M2 本地计时仅作 dsim 侧参考（跨机器不可与 VCS 比较），已被本同机数据取代。
