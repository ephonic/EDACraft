# rfsim 项目状态报告 — 2026-06-22（V2-γ 收尾 + C4 perf 报告）

本报告承接 status0620_v2.md，覆盖 plan0620_v2.md 的 V2-γ 阶段（C1-C4）完整闭环。

## 1. 本轮核心成果

### V2-γ C3-bis：3rd-instance 串拥 bug 根因定位 + 修复

**现象**：高对称 N≥3 BSIM4 阵列（EightFingerBalanced / SelfBiasedCascodeStack5）DC OP 求解后，
某个 drain 节点电压非物理跳变（drain > VDD）。C1.4 / C2.b 因此被 GTEST_SKIP 封存。

**根因调查链**（C3-bis Step1-4）：

| Step | 假设 | 实验 | 结论 |
|------|------|------|------|
| C3 | setup_model N× 重复初始化 | OsdiModelBlock 共享 + BIT-IDENTICAL 复跑 | 证伪：与 modelData 无关 |
| 1 | instData init-time 互写 | N=3 fwd vs rev 构造 | 证伪：drain=4 一致坏 |
| 1 | BSIM4 VA setup_instance 计数 | 同上 | 证伪 |
| 2 | add-order / MNA stamp 序累积 | revDrain={4,3,2} | 证伪：drain=4 在 addPos=0 仍坏 |
| 2 | max-ID-of-drain-set | N4.2345 / skipMaxFirst | 证伪：drain=5 永远健康 |
| 3 | BSIM4 内部节点相邻 | 234.baseFar (base=100) | 证伪：drain=4 仍坏 |
| 3 | node ID = 4 specifically | N3.345 (drain=4 在中间) | 确认：是 drain=4 坏 |
| **4** | **DCOP_VERBOSE=2 跟踪** | gmin step 4 Newton n4 反复 bt 退避 → residual floor 卡 V[n4]~0.8V → **末段 polish step 裸 Newton 跳 0.8→1.249V** | **锁定真因** |

**真因**：`dc_op.cpp` 末段 polish step（`nodeV + dx`）是一步**裸 Newton**，既无 dvmax 限幅也无下降检查。
在 Newton 多解陷阱拓扑下，homotopy 末段残差地板接受的 V[n4]~0.8V 经这一步被推到 1.249V（drain > VDD，非物理）。
node 4 被选中是 AMD 重排序 + sparsity pattern 的确定性产物——同一拓扑下永远输出相同值（bit-identical 验证）。

**修复**（dc_op.cpp polish step）：

```cpp
// 加 dvmax clamp + 简化 backtracking line search
for (int bt = 0; bt < 12; ++bt) {
    // 1. dvmax 限幅（与 Newton 主循环同款）
    // 2. 重 assemble 评估 |F|
    // 3. 接受若 |F_new| <= |F_old|*(1+1e-6)；否则 alpha *= 0.5
}
// 若完全失败：保留 bestNodeV，不强行推进
```

**验证**：
- C3-bis 13 个诊断测试 spread=0（修复前 N=3 spread=0.996）
- EightFingerBalanced：V_drain=0.537V 对称，max|ΔV|=0.00e+00（修复前 1.12V / 0.636V）
- SelfBiasedCascodeStack5：v[2]=0.072V 物理（修复前 3.386V > vdd）
- 全量回归：102 PASSED / 0 FAILED / 14 SKIPPED（HEAVY/gated）

### V2-γ C3：OsdiModelBlock 共享框架（性能优化保留）

同 modelcard 多实例共享 modelData，setup_model 由 N× 压缩为 1×。
功能正确但不修复 3rd-instance bug（C3-bis 已证伪）。作为纯性能优化保留。

### V2-γ C3：bench JSON 落库

新增 `RFSIM_BENCH_JSON=1` 开关，在 dc_op / hb_nonlinear / shooting 三个 solver 填充 BenchCounters
（wall_ms / newton_iter / klu_factor_ms / klu_solve_ms / peak_rss_mb）。
GoogleTest 通过 `tests/bench_recorder.hpp` 在 solve 后追加 JSON 行到 `build/bench_<timestamp>.json`，
`tools/bench_summary.py` 汇总为 markdown。

首份 baseline：`build/bench_20260622-195603.json`（4 代表用例）。

### V2-γ C4：perf 采样 + 瓶颈定位

基于 C3 bench JSON，对前 3 wall-time 主导项做代码内 chrono 分段计时。
完整报告见 `build/bench_summary.md`。

**核心结论**：

| 用例 | wall_ms | 瓶颈 | 占比 |
|------|---------|------|------|
| Shooting.Bsim4CommonSourcePssConverges | 35284 | integrateOnePeriod（FD Jacobian 构造） | 99.98% |
| Shooting.Bsim4LcTank1GHz | 11679 | 同上 | 99.98% |
| LargeScaleBsim4.SelfBiasedCascodeStack5 | 58 | DC Newton（325 iter） | KLU 6% |

**Shooting 瓶颈**：前向有限差分构造 monodromy Jacobian——每 outer Newton 迭代对每个未知数做一次
完整周期积分。dim≈16 时每 iter 做 17 次积分（1 标称 + 16 FD），8 iter = 136 次。
tFDJacobian 占 tIntegrate 的 86-88%，tKluOuter 仅 0.0003%。

**优化路径**（记入 v3，不在本轮实施）：
- A. OpenMP 并行 FD（推荐，4-8x，低风险）
- B. 解析 Jacobian（OSDI 灵敏度，10-50x，高风险）
- C. GMRES + matrix-free（5-10x，收敛风险）
- D. 截断 FD（仅强非线性节点，2-4x，精度风险）

## 2. 附带修复：预存 API 漂移编译错误

session 间隔产生的两个 pre-existing 编译错误（阻塞 build）：
- `osdi_model.cpp:186` — `loadResidualReact` 被新 OSDI API 移除，改为 stub（电荷 Q 走 `loadLimitRhsReact` 路径）
- `hb_jacobian.cpp:414-415` — `contrib.re/.im` 改为 `contrib.real()/.imag()`（MSVC `/permissive-` 标准合规）

## 3. V2-γ 退出条件检查（plan0620_v2.md §7）

| # | 条件 | 状态 |
|---|------|------|
| 1 | OSDI 模型矩阵 24/24 用例状态明确 | ✅ 8 模型 × 3 phase（DC/HB/Shooting），A1-A5 全绿 |
| 2 | bsim4 bias 扫描收敛率 ≥ 95% | ✅ B1 harness（G2_Bsim4CsNhScan）通过 |
| 3 | ≥ 3 类中等规模 RF 拓扑端到端通过 | ✅ C1.1 RC ladder / C1.2 cascode chain / C1.3 LC tank |
| 4 | ≥ 1 张 perf 基线 JSON 落库 | ✅ bench_20260622-195603.json |
| 5 | 全量 ctest 100% 通过 | ✅ 102 PASSED / 0 FAILED / 14 SKIPPED |

**V2-γ 全部退出条件满足。**

## 4. 环境

- 构建：MSVC 19.42 (VS 2022) + CMake 3.31 + Ninja，`/MD` 与 bsim4.dll UCRT 对齐
- OSDI 模型库：`models/bsim4.dll`（MSVC + OpenVAF 23.5）
- 测试运行：`build\bin\rfsim_tests.exe`（直接执行，102 用例 ~80s wall）
- bench 模式：`set RFSIM_BENCH_JSON=1 && run_bench.bat`

## 5. 残留事项（移交 v3）

- **Shooting FD Jacobian 性能**：35s/11s wall，OpenMP 并行 FD 是首选优化（4-8x）
- **DC OP Newton 迭代数**：SelfBiasedCascodeStack5 325 iter 偏高，可探索 source stepping 收敛策略调优
- **C3-bis 诊断测试**：13 个 C3bis_* 仍 gated by `RFSIM_FORCE_C3BIS=1`，可作为回归守卫保留
- **Phase C short-stamping**：plan0620_v2.md 沉淀的可选扩展，未启用
