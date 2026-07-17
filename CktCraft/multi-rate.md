# Multi-Rate 仿真架构计划

## 1. 背景与动机

### 1.1 当前瓶颈

V3 优化后，Shooting 的剩余瓶颈是 `integrateOnePeriod` 内的器件 eval：
- 每个时间步对所有 OSDI 器件调 `evalTransient`（含 `desc_->eval`）
- BSIM4 有 12 个内部 charge 节点，Newton 每步都在变化
- V3-L1 eval bypass 在统一步长下命中率仅 1.8-9.6%（tol 1e-9~1e-3）
- 根因：每步末 `swapState` 清缓存，cache 只在单步内有效

### 1.2 Multi-rate 的核心价值

不同器件的动态特性差异大：
- **快器件**（强非线性、高 dV/dt）：需要小步长 dt_fast
- **慢器件**（静态偏置、弱变化）：可用大步长 dt_slow = K × dt_fast

慢器件在 K 个快步长内**只 eval 一次**，其余 K-1 步复用缓存 → 命中率 = (K-1)/K

若 K=10（慢器件步长是快器件的 10 倍），命中率 = 90%，器件 eval 减少 90%。

### 1.3 适用场景

- 大规模电路（100+ 器件）中大部分器件在静态偏置
- 电流镜阵列、差分对、偏置网络等"慢"器件
- Shooting PSS（周期积分中慢器件贡献几乎不变）
- Transient 分析（慢器件不需要每步更新状态）

## 2. 架构设计

### 2.1 核心数据结构

#### MultiRateDeviceState（每个 OSDI 器件一个）

```cpp
struct MultiRateDeviceState {
    uint32_t rateRatio = 1;      // K = dt_slow / dt_fast（1=统一步长）
    uint32_t stepCounter = 0;    // 当前在 K 步周期中的位置 [0..K-1]
    bool needsEval = true;       // 本步是否需要重新 eval
    // eval bypass cache（复用 V3-L1 已有的 lastTermV_/lastF_/lastJac_）
};
```

#### 在 OsdiModel 中集成

```cpp
class OsdiModel {
    // ... 已有成员 ...
    // V3-MR: multi-rate 状态
    uint32_t mrRateRatio_ = 1;     // K
    uint32_t mrStepCounter_ = 0;   // [0..K-1]
    bool mrNeedsEval_ = true;     // 本步是否需 eval
public:
    void setRateRatio(uint32_t K) { mrRateRatio_ = K > 0 ? K : 1; mrStepCounter_ = 0; mrNeedsEval_ = true; }
    uint32_t rateRatio() const { return mrRateRatio_; }
    // assembleTransient 调用前检查：若 mrStepCounter_ > 0 && mrStepCounter_ < K，跳过 eval
};
```

### 2.2 积分循环改动

#### 当前（统一步长）

```
for step in [1, numSteps]:
    t = step * dt
    for each device:
        evalTransient(t, dt)        // 每步都 eval
    Newton solve → trialNodeV
    updateDeviceStates → swapState   // 每步末 swapState
    prevNodeV = nodeV
```

#### Multi-rate

```
for step in [1, numSteps]:
    t = step * dt
    for each device:
        if device.mrNeedsEval:
            evalTransient(t, dt)     // 快器件每步 eval，慢器件每 K 步 eval
            device.mrNeedsEval = false
        else:
            // bypass: 复用上次 f/jac（V3-L1 cache 机制）
    Newton solve → trialNodeV
    for each device:
        device.mrStepCounter++
        if device.mrStepCounter >= device.mrRateRatio:
            updateDeviceStates → swapState  // 慢器件每 K 步 swap
            device.mrStepCounter = 0
            device.mrNeedsEval = true       // 下一步需重新 eval
    // 快器件每步 swap（rateRatio=1）
    prevNodeV = nodeV
```

### 2.3 assembleTransient 改动

`assembleTransient` 遍历器件时，对 OSDI 器件检查 `mrNeedsEval`：

```cpp
if (auto* osdi = dynamic_cast<OsdiModel*>(dev.get())) {
    if (!osdi->ready()) continue;
    if (osdi->mrNeedsEval()) {
        osdi->evalTransient(op, dc);  // 正常 eval + 更新 nextState_
    } else {
        // bypass: 复用上次 f/jac（不更新 nextState_）
        osdi->evalTransientBypass(dc);
    }
    // stamp f/jac 到 G/F（不变）
}
```

`evalTransientBypass` 复用 V3-L1 的 `lastF_`/`lastJac_`，不调 `desc_->eval`。

### 2.4 FD Jacobian 一致性

Shooting 的 FD 扰动需要主路径和扰动路径使用相同的 eval 决策：
- **主路径**：step N 的器件 eval 决策由 mrStepCounter_ 决定
- **FD 扰动路径**：`restoreDeviceStates` 后 mrStepCounter_ 重置

**解决方案**：FD 扰动时**强制所有器件 needsEval=true**（绕过 multi-rate），确保扰动路径和主路径的器件状态一致。这是保守做法——FD 扰动路径的 eval 次数不变，但主路径的 eval 次数大幅减少。

### 2.5 自动速率分级

初始 K=1（统一步长）。在积分过程中自动检测慢器件：

```
每 N_check 步（如 10 步），检查每个器件的端电压变化：
  maxDeltaV = max|termV[step] - termV[step-N_check]|
  if maxDeltaV < threshold_slow (如 1e-4):
      K *= 2  (加倍该器件的步长)
  if maxDeltaV > threshold_fast (如 1e-1):
      K = 1  (该器件回退到快步长)
```

也可手动设置（`setRateRatio`）——测试时先手动验证。

## 3. 实施步骤

### Phase 1: 手动 multi-rate（验证机制）

1. **OsdiModel 加 multi-rate 成员**：mrRateRatio_/mrStepCounter_/mrNeedsEval_ + setRateRatio/mrNeedsEval
2. **assembleTransient 加 bypass 路径**：mrNeedsEval=false 时复用 lastF_/lastJac_
3. **evalTransientBypass 方法**：不调 desc_->eval，直接从 cache 输出
4. **integrateOnePeriod 改步长循环**：每步检查 mrNeedsEval，步末按 rateRatio 决定 swapState 时机
5. **FD 扰动路径强制 needsEval=true**：保持 FD 一致性
6. **手动设置 K 的测试**：CurrentMirrorArray8 中镜像管设 K=4，看命中率和 wall
7. **全量回归 102/0/14**

### Phase 2: 自动速率分级

1. **电压变化检测器**：每 N_check 步统计 maxDeltaV per device
2. **K 自适应逻辑**：根据 threshold_slow/fast 调整 K
3. **收敛性守卫**：K 过大导致精度损失时自动回退
4. **测试**：大电路自动分级 + wall 对比

### Phase 3: 与 Shooting PSS 集成

1. **Shooting 外层 Newton**：FD 扰动路径不受 multi-rate 影响（强制 needsEval）
2. **最终波形积分**（integrateTransient）：启用 multi-rate 加速
3. **PSS 收敛性验证**：multi-rate 不影响周期稳态收敛点

## 4. 验证标准

- 全量回归 102/0/14 PASS
- CurrentMirrorArray8: 镜像管 K=4 时命中率 > 75%，wall 降 40%+
- CommonSourcePssConverges: 无慢器件（单 BSIM4），K=1 无变化
- tol=0 / K=1 时 bit-identical

## 5. 风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| Multi-rate 导致 PSS 不收敛 | 中 | K 限制 ≤ 16；自动回退 K=1 |
| FD 噪声（主路径省 eval 但扰动路径全 eval） | 低 | 扰动路径强制 needsEval=true |
| 线性器件 companion model 与慢器件状态不同步 | 中 | 线性器件不走 multi-rate（仅 OSDI） |
| BSIM4 内部节点状态滞后 | 中 | swapState 时强制完整 eval + INIT_LIM |

## 6. 时间线

- Phase 1（手动 multi-rate）：1-2 个 session
- Phase 2（自动分级）：1 个 session
- Phase 3（Shooting 集成）：1 个 session

## 7. 与 V3 的关系

V3 已完成的基础设施直接支持 multi-rate：

| V3 组件 | multi-rate 中的角色 |
|---------|-------------------|
| eval cache (V3-L1 lastF_/lastJac_) | 慢器件的 K-1 步复用 |
| invalidateEvalCache | 改为按 mrStepCounter_ 调度 |
| stampPtrs (V3-L0) | 快速 stamp 复用值 |
| FD 列 bypass (V3-L2) | 线性节点已跳过，与 multi-rate 正交 |
| boundG_ 检查 | 不变（慢器件仍用同一 sysShared） |
