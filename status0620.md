# rfsim 项目状态报告 — 2025-06-18

## 当前焦点

Stage 1 收尾：为 BSIM4 单音 HB 强非线性收敛实现 **电荷项 HB Jacobian** 与 **limiting RHS 装配**。
已提交 commit `3fa19f1`，测试基线 **66/66 通过**。

## 环境

- 项目：`rfsim`，C++17 RF 电路仿真器，路径 `G:/vibe-codeing/simulator`。
- 构建：MSYS2 MinGW64 GCC 15.2，CMake + Ninja，`./build.bat configure|build|test`。
- OSDI 模型库：`models/bsim4.dll`（OpenVAF 23.5.0）。
- 运行测试需把 `/mingw64/bin` 加入 `PATH`。
- 当前基线：**66/66 测试通过**（已本地 git commit：`3fa19f1`）。

## 已完成（Stage 1 后续）

### 1. OSDI 客户端接口扩展
- 新增 `loadLimitRhsResist()` / `loadLimitRhsReact()`。
- 新增 `loadJacobianReactWith()`：正确写入电荷 Jacobian 目标指针。
  - 优先调用 `load_jacobian_react(alpha)`。
  - 使用每个 `OsdiJacobianEntry::react_ptr_off` 作为指针槽（之前错误地写到了电阻性指针数组）。
  - 回退方案：`load_jacobian_tran - load_jacobian_resist` 近似电荷 Jacobian。
- 新增 `resetLimiting()`：控制 `INIT_LIM` 标志，避免跨 Newton/continuation 的 limiting 状态污染。

### 2. OSDI 模型层
- `OsdiModel::resetLimiting()`：暴露给求解器。
- `OsdiModel::evalTimeJacobiansReact()`：沿电压波形采样 ∂Q/∂V（alpha=1.0）。

### 3. HB 频域装配 `src/assembly/hb_jacobian.cpp`
- `evalTimeSamples` 已把 `lim_rhs` 合并进电阻性电流残差。
- 新增 `addSusceptanceBlock()`：
  - 对 `G_Q(t) = ∂Q/∂V` 做 FFT 得到 `G_Q[k]`。
  - 乘以 `j k ω₀` 得到频域电纳 `Y_Q[k]`。
  - 按 `sign=-1.0` 加入 HB Jacobian（仿真器约定 `F = -I`）。
- 非线性 OSDI 器件现在同时组装：
  - 电阻性电导卷积块（`evalTimeJacobians`）。
  - 电荷电纳卷积块（`evalTimeJacobiansReact`）。

### 4. 求解器
- `solveDcOp` 与 `solveHbNonlinear` 在非线性求解前统一调用所有 `OsdiModel::resetLimiting()`。

### 5. 测试与提交
- 全部 66 个测试通过。
- 已本地提交：`3fa19f1 Stage 1 后续：OSDI limiting 重置、电荷 Jacobian 与 HB 电纳块`。

## 活跃问题

### 1. 强非线性 HB 仍发散
- 栅压明显高于阈值时，HB Newton 停滞或发散。
- 已尝试：
  - 抬高栅压、加 source/gmin continuation、收紧 `dvmax`、增加 `maxIter`。
  - 调整 BSIM4 测试偏置/尺寸。
- 根因：
  - **缺少精确的周期瞬态电容电流残差**。当前 HB 残差仍只使用阻性电流，Jacobian 已包含电纳块，残差-Jacobian 不完全一致。
  - 测试用模型参数 `k1=0.5` 使有效阈值被抬得很高（约 0.9–1.2 V），常见偏置容易落在截止或深导通区，continuation 容易跑飞。

### 2. Shooting 仍是 smoke test
- `Bsim4CommonSourceSine` 目前只跑 1 次 Shooting 迭代、15 个时间点，仅验证不崩溃。
- 尝试改成真实收敛测试（`maxIter=10`、`numTimePoints=50`、栅压 DC 1.0V）后， Shooting 有限差分 Jacobian 每轮需要积分 `dim` 次，单次测试运行约 70 秒仍未收敛。
- 周期闭合误差约 0.55 V，未满足放宽后的 0.5 V 容差。

### 3. 跨 Newton 迭代 limiting 状态
- 已在 DC/HB 入口重置，但 Shooting 内部每个时间步的局部 Newton 未统一处理 limiting 收敛历史。

## 下一步候选方案

1. **实现周期瞬态残差 `evalTimeSamplesTran`**
   - 沿一个周期做 Backward Euler 积分，得到含 dQ/dt 的总电流。
   - 替换当前仅用电阻性电流的 HB 残差。
   - 这是强非线性 HB 收敛最可能的路径，但需处理状态轨迹闭合性与时间离散精度。

2. **优化 Shooting 求解器**
   - 用伴随法（adjoint）或 Broyden 更新替代有限差分 Jacobian。
   - 大幅减少每轮 Shooting 迭代成本后，再改成真实收敛测试。

3. **调整/隔离 BSIM4 测试参数**
   - 为强非线性 HB/Shooting 测试单独准备模型参数（如降低 `k1`、选取合适 Vg/Rd/W）。
   - 先把收敛路径跑通，再回推到通用模型。

## 文件变更（相对 commit `6d6804a`）

```
src/assembly/hb_jacobian.cpp    |  +47  电荷电纳块、lim_rhs 合并
src/model/osdi/osdi_client.cpp  |  +62  limiting RHS、reactive Jacobian 加载
src/model/osdi/osdi_client.hpp  |   +9  新增接口声明
src/model/osdi_model.cpp        |  +54  resetLimiting、evalTimeJacobiansReact
src/model/osdi_model.hpp        |   +8  新增接口声明
src/solver/dc_op.cpp            |   +5  resetLimiting
src/solver/hb_nonlinear.cpp     |   +5  resetLimiting
tests/test_hb_nl.cpp            |   +5  注释/测试说明
```

## 测试状态

```text
[==========] 66 tests from 16 test suites ran.
[  PASSED  ] 66 tests.
```

---
*报告由 Kimi Code CLI 自动生成于 2026-06-18T21:37+08:00。*
