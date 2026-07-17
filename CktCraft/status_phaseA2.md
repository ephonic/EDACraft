# Phase A2 完成状态 — HB / Shooting 收敛加固（需求 7）

日期：2026-07-17。承接 Phase A1（求解器抽象）。对应总体增强方案 Phase A 的 A2 子项。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **156 tests, 131 PASSED / 0 FAILED / 51 SKIPPED**（A1 后 121 + 新增 10 个 NonlinearDamping 测试） |
| 新增测试 | `tests/test_nonlinear_damping.cpp` — 10/10 PASS |
| A1 基线保持 | A1 的 121 测试全 PASS（无退步） |
| KI-1 改进 | HB 卷积 FFT 过采样（N=2(NH+1)→4(NH+1)）+ LM 阻尼器，降低混叠+改善强非线性收敛 |

## 落地清单

### 新增文件

| 文件 | 作用 |
| --- | --- |
| `src/solver/nonlinear_damping.{hpp,cpp}` | `DampingController`：Backtracking / LevenbergMarquardt / TrustRegion 三策略；LM 自适应 λ（Marquardt scale 正则） |
| `tests/test_nonlinear_damping.cpp` | 10 个单元测试（LM 正则/λ 自适应/上下界/Backtracking Armijo/TR 步长限幅/reset） |

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/solver/hb_solver.hpp` | `HbConfig.oversample`（默认 2，FFT 卷积采样 N=2·os·(NH+1)） |
| `src/assembly/hb_jacobian.cpp` | `ifftWaveform` 接收 N 参数；`assembleHarmonicBalanceReal` 用 `config.oversample` 计算采样数（A2-1，消除卷积混叠） |
| `src/solver/shooting.cpp` | 外层收敛判据 `fNorm < abstol` → `fNorm < abstol + reltol·‖y‖`（A2-2，激活声明但未用的 reltol） |
| `src/solver/hb_nonlinear.{hpp,cpp}` | 集成 `DampingController`：LM 自适应 λ 替代固定 Tikhonov；失败升 λ 重解，成功降 λ 加速（A2-4）；GMRES 参数可配 `gmresRestart/MaxIter/Reltol`（A2-5）；`HbNlOptions.damping` 策略字段 |
| `src/cli/main.cpp` | HB→Shooting 回退加固：完整同伦（gminSteps=4 + maxIter=30）+ NH 减半粗收敛重试（A2-3） |
| `src/CMakeLists.txt` + `tests/CMakeLists.txt` | 注册 nonlinear_damping 源/测试 |

## 关键设计决策

### A2-1：HB FFT 过采样（KI-1 根因之二）

**问题**：HB 非线性卷积（IFFT→eval→FFT）原用最低采样 `N=2(NH+1)`——这是提取 0..NH 谐波的 Nyquist 下限，高次谐波（>NH）折叠回低次 → 卷积混叠噪声，强非线性下 HB-NL 收敛失败（KI-1 根因之二，`status0621-v3.md` Sprint S3 待办）。

**修复**：`N = 2·oversample·(NH+1)`，`oversample` 默认 2（即 4(NH+1)）。过采样的高次谐波被 DFT 丢弃（吸收混叠），保留的 0..NH 谐波更纯净。`ifftWaveform`/`currentFft`/`conductanceFft` 均按 N 参数化（后两者已用 `t.size()`，仅 ifftWaveform 需改签名）。线性器件频域 stamp 不受影响（直接在频域）。

### A2-2：Shooting 外层收敛用上 reltol

**问题**：`shooting.cpp` 外层 Newton 收敛判据 `fNorm < opts.abstol`（纯绝对），`opts.reltol` 声明但未用。大信号 PSS（‖y‖~1V，abstol=1e-9）要求 1e-9 相对精度过严，不可达。

**修复**：`fNorm < abstol + reltol·‖y‖`（相对+绝对，与 DC/transient 一致语义）。

### A2-3：HB→Shooting 回退加固

**问题**：`main.cpp` 的 HB-NL 失败回退是单次 `maxIter=15` 无同伦 Shooting，失败即终。

**修复**：回退 Shooting 用完整同伦（`gminSteps=4, gminStart=1e-2, maxIter=30`）。失败再试 NH 减半的粗收敛（`shootingToHarmonics` 仍提取原 NH，粗采样更易收敛）。

### A2-4：Levenberg-Marquardt 阻尼器（最广泛收益）

**问题**：HB-NL 原用固定 Tikhonov 正则（`opts.lambda=1e-6`）+ Armijo backtracking。固定 λ 无法适应收敛过程中雅可比条件数的变化——冷启动需大 λ 稳定，接近收敛需小 λ 加速。

**修复**：`DampingController`（LM 策略）自适应 λ：
- 正则：`J_reg[i,i] += λ·max_k|J[i,k]|`（Marquardt scale，避免 O(dim³) 的 JᵀJ）。
- 自适应：步接受（残差下降）→ λ/=2（向纯 Newton 靠拢，加速）；步拒绝 → λ*=4（更保守，近梯度下降），下轮用新 λ 重解 J·dx=-F。
- λ 上下界 [1e-12, 1e6]，防止数值病态。
- Backtracking 策略保留（与原行为等价）；TrustRegion 接口预留（当前退化为 LM+步长限幅）。
- HB-NL 默认走 LM；DC/Shooting 可选（通过 opts.damping 字段，当前未接入以控制风险）。

### A2-5：GMRES 参数可配

**问题**：HB-NL 的 GMRES 配置硬编码 `restart=min(50,dim)`、`maxIter=dim*2`、`reltol=1e-8`。

**修复**：`HbNlOptions.gmresRestart/MaxIter/Reltol`，0 表示用默认。大规模 HB 可调优。

## 交付标准核对

- [x] 默认 ctest **131/0/51** PASS（A1 后 121 + 新增 10，不退步）
- [x] HB FFT 过采样（oversample=2）激活，HB/Shooting 测试全 PASS
- [x] Shooting 用上 reltol（相对+绝对收敛）
- [x] HB→Shooting 回退加固（完整同伦 + NH 减半重试）
- [x] LM 阻尼器在 HB-NL 路径生效（默认策略）
- [x] GMRES 参数可配
- [x] NonlinearDamping 单元测试 10/10 PASS
- [x] `ConvergenceGrid.Bsim4CommonSource` PASS（KI-1 触发器之一）

## 未做（控制风险，留后续）

- **Shooting 外层 source-stepping 同伦**：P0-4 一致性约束（main↔FD 路径）使外层同伦改动风险高，推迟。A2-3 的 HB→Shooting 回退已在回退路径启用 gmin 同伦（一致性约束更宽松）。
- **DC/Shooting 接入 LM 阻尼器**：HB-NL 已接入（收益最大）；DC/Shooting 现有 backtracking+gmin 同伦已稳，接入 LM 需更多测试，留后续。
- **HB BlockHarmonicPrecond 的 DC 块 ILU**：A2-5 已让 GMRES 可调，预条件 ILU 改进留后续（需复用 A1 的 ILU0Preconditioner，但 HB J 是稠密的，需稠密 ILU）。

## Phase A 总结（A1 + A2）

| 子项 | 需求 | 状态 |
| --- | --- | --- |
| A1 求解器抽象+符号复用+自动选择+BiCGSTAB+KLU 可选 | 6 | ✅ |
| A2-1 HB FFT 过采样 | 7 | ✅ |
| A2-2 Shooting reltol 收敛 | 7 | ✅ |
| A2-3 HB→Shooting 回退加固 | 7 | ✅ |
| A2-4 LM 阻尼器 | 7 | ✅ |
| A2-5 GMRES 可配 | 7 | ✅ |

Phase A（需求 6 + 7）完整交付。回归 **131/0/51**，新增 20 个单元测试（LinearSolverSelect + NonlinearDamping），无退步。

## 后续 Phase

- **Phase B**（需求 1、3）：器件 bypass 强化 + 异步 multi-rate
- **Phase C**（需求 2、5）：PDK 桥接 + 参数化增强
- **Phase D**（需求 4）：波形输出多格式 + 增强 waveview
