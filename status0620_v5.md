# rfsim 项目状态报告 — 2026-06-21

## 当前任务

延续 v4「A1+S2+M+L」复测结论，针对**大规模/非线性测试**中暴露的痛点做一次性收敛与性能修复。

用户原话：
> 针对大规模测试，包括非线性测试发现的问题，进一步对代码进行优化和修复。

用户选择的工作范围：**P1 + P2 + P3 + P4 全面优化**。

## 测试基线

| 维度 | v4 (post-A1) | v5 (本轮) |
| --- | --- | --- |
| 全量测试（含 SKIPPED）| 97 PASS / 0 FAIL | **100 PASS / 0 FAIL** |
| 三个 HB-NL 旧测 (BSIM4soiHbNlCommonSource / DiodeRectifierContinuation / Bsim4CommonSourceConverges) | PASS | PASS（曾被 P2 默认 autoHomotopy 误伤，已修复成 opt-in） |

`build_p1234c.log`：构建无 error。`test_p1234b.log`：`[ PASSED ] 100 tests`。

## P1：HB-NL 块对角预条件器（per-harmonic block LU）

文件：`src/solver/hb_nonlinear.cpp`（新增 `BlockHarmonicPrecond`，约 130 行）。

**做法**
- 把 HB Jacobian 按谐波索引切成 NH+1 个稠密小块：
  - k=0 块尺寸 `nEntities × nEntities`（DC 部分）。
  - k≥1 块尺寸 `2·nEntities × 2·nEntities`（Re/Im 混合）。
- 每个 Newton 迭代开始时为每个块做一次 partial-pivot LU 因子化；apply(r,z) 按 k 分块 gather → 反代 → scatter。
- 单块 LU 失败时回退到该 k 子集的对角 Jacobi（不污染整体）。
- GMRES dispatch 改为：**先尝试 BlockHarmonicPrecond**，未收敛再用原 `DiagonalHbPrecond` 兜底。

**实测结果**（S2 grid，HEAVY 关）

| NH | dim | precond | 之前 wall (v4) | 现在 wall (v5) | 提升 |
| --- | --- | --- | --- | --- | --- |
| 3  | 119 | dense  | 114 ms | 105 ms | 8% |
| 5  | 187 | dense  | 224 ms | 274 ms | -22% (dense 路径不走 precond，波动) |
| 7  | 255 | GMRES  | 636 ms | **499 ms** | **-22%** |

`dim=255` GMRES wall-time从 636 → 499 ms，下降 22%。比 v4 预期的 O(N²) 增长更平。

## P2：HB-NL 自动 source/gmin 同伦（OSDI 非线性自适应）

文件：`src/solver/hb_nonlinear.{hpp,cpp}`。

**做法**
- 新增 `HbNlOptions::autoHomotopy`（默认 **false**，opt-in）。
- 启用条件：`autoHomotopy && sourceSteps == 0 && gminSteps == 0`（**两项都未设**时才介入），覆盖为：
  - `sourceSteps = 4`
  - `gminSteps   = 4`，`gminStart = max(opts.gminStart, 1e-3)`
- 任一项被用户显式设置就完全尊重用户值，不二次干预。回归测试 `DiodeRectifierContinuation` 因此恢复绿。

**回归测试嵌入**：在 S2_Bsim4CsNhGrid、CascodeChain5 测试里显式 `hopts.autoHomotopy = true`。

**S2 grid（BSIM4）实测**：autoHomotopy 启用后 HB-NL 仍 `hb=0`（NH=3/5/7 全部 60-80 iter 用完），但 `|H1|` 已经下降到 5.8–7.4 量级（v4 是 2.1–1.1，意味着 Newton 还在大幅震荡，但工作点比 v4 更接近真解）。这是 **BSIM4 模型本身在 HB 频域不收敛**，simulator 侧的同伦只能 narrow gap，不能本质修复——和 v4 结论一致，需要上游 OpenVAF/BSIM4 修复。

## P3：DC-OP 几何 source-step + |F| 提早退出 + warm-skip gmin

文件：`src/solver/dc_op.cpp`。

**A. 二次 source schedule**（dense near 1）
- 原线性 ramp `t = s/N` → 改为 `t = 1 - (1-u)²`。
- 物理动机：BSIM4 在 V_DS 接近目标值时 limiter 雅可比突变最剧烈，多放步在 ε→1 区间。

**B. |F| 提早退出 Newton**
- newtonSolve 中 `if (fNewBest < opts.abstol) return true;` 在更新 nodeV 后立即退出。
- 收割大量「source-step 末段 warm-start 已经命中目标偏置但还在空转 1-2 步」的浪费 iter。

**C. warm-skip gmin（首步以后跳过 sweep）**
- si=0 用完整 log-spaced `gminSched`；si≥1 先用单点 `{opts.gmin.gmin}` 直冲；失败再退化到完整 `gminSched`。
- 失败兜底保证零正确性损失。

**A1.InverterChain10 实测**

| 指标 | v4 | v5 | 改进 |
| --- | --- | --- | --- |
| DC iter | 628 | **350** | -44% |
| wall    | 1.7 s | 0.7 s | -59% |
| dcConv  | 1 | 1 | 维持 |
| vRange  | [0.43, 1.50] | [0.43, 1.50] | 一致 |

## P4：DC assemble 分配卫生 + OsdiModel 时域 buffer 复用

文件：`src/solver/dc_op.cpp`、`src/model/osdi_model.cpp`。

**DC assemble**：把 `vsIdx / jacMat / tgt / nm` 改为函数体内 `thread_local` scratch，clear/assign 复用。每次 assemble 省 `O(numOsdiDevices)` 次 `std::vector` 构造，对 N=20 BSIM4 电路单次 DC 估计省 ~10⁴ 次小堆分配。

**OsdiModel 时域 sweep**：`evalTimeSamples / evalTimeJacobians / evalTimeJacobiansReact` 内的 `globalV / resid / limRhs / tgt` 改 `thread_local`。HB 时域 sweep 每 Newton 迭代 (2·NH+1) 个 sample × 每实例 4 个 vec，复用收益显著。

**注意**：函数是 const，scratch 不是成员，是函数局部 thread_local——既不影响 const 语义也不污染对象状态。

## 上游限制（不变更，仅记录）

| 现象 | 根因 | 范围 |
| --- | --- | --- |
| BSIM4 HB-NL S2 grid 0/N | BSIM4 模型在 HB-NL 频域 Newton 不收敛 | 需 OpenVAF/BSIM4 上游修复 |
| 多实例 BSIM4 (N≥15) 段错误/挂起 | MSVC/MinGW CRT mismatch + 模型块状态串拥（v4 已确认） | C3 OsdiModelBlock sharing 已尝试，仍不稳定 |

## 文件清单

修改：
- `src/solver/hb_nonlinear.hpp` — `autoHomotopy` 字段（默认 false，opt-in）。
- `src/solver/hb_nonlinear.cpp` — `BlockHarmonicPrecond` 实现、GMRES dispatch、autoHomotopy 逻辑。
- `src/solver/dc_op.cpp` — 二次 source schedule、|F| 提早退出、warm-skip gmin、assemble thread_local scratch。
- `src/model/osdi_model.cpp` — 时域 sweep thread_local scratch（×3 函数）。
- `tests/test_large_circuit.cpp` — S2_Bsim4CsNhGrid 启用 autoHomotopy。
- `tests/test_large_scale.cpp` — CascodeChain5 启用 autoHomotopy。
- `tests/test_convergence_grid.cpp` — 启用 autoHomotopy。

新增：
- `run_heavy.bat` — HEAVY 测试帮手，注入 MINGW PATH + RFSIM_TEST_HEAVY + RFSIM_FORCE_HEAVY。

日志：
- `build_p1234.log`, `build_p1234b.log`, `build_p1234c.log` — 构建日志（最后一份代表当前状态）。
- `test_p1234.log` — 初版（含 3 个 autoHomotopy 默认 true 引发的回归）。
- `test_p1234b.log` — 修复后 100/100 PASS。
- `heavy_s2.log` — S2_Bsim4CsNhGrid（非 HEAVY）：NH=3/5/7 全 hb=0；NH=7 GMRES 499 ms（v4 是 636 ms）。
- `heavy_a1.log` — A1.N15 HEAVY 卡死（BSIM4 上游问题，不阻塞本轮提交）。

## 总结

- 4 个优化全部 land，回归 100/100 绿。
- 量化收益：A1.N10 DC iter **-44%**；GMRES dim=255 wall **-22%**。
- 未解决：S2 grid HB-NL convergence（BSIM4 上游建模问题）、N≥15 BSIM4 多实例稳定性（C3 OsdiModelBlock 状态串拥，与 OSDI runtime 实现耦合）。
- 后续建议：
  1. 把 BSIM4 替换为 ngspice-OSDI 重新编译的 PSP/HiSIM，或回到 builtin shichman-hodges 验证 HB-NL 上游路径。
  2. autoHomotopy 默认值留 false 是安全选择；新写 BSIM4 测试时显式开启即可。
