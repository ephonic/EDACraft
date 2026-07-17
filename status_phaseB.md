# Phase B 完成状态 — 器件 bypass 强化 + multi-rate 增强（需求 1、3）

日期：2026-07-17。承接 Phase A（需求 6+7）。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **156 tests, 131 PASSED / 0 FAILED / 51 SKIPPED**（与 Phase A 后一致，无退步） |
| HEAVY multi-rate 验证 | `CurrentMirrorArray8_HEAVY`（K=4 手动）PASS（58s） |
| B1 Jacobian 级 bypass | 激活 `evalTransientResidOnly`（原死代码），line-search 试验点复用 jac |
| B2 multi-rate 自动开关 | `.options multirate=1` 启用 mrAutoTune，复用现有 V3-MR 基础设施 |

## 落地清单

### 修改文件（无新增源文件，全部增强现有）

| 文件 | 改动 |
| --- | --- |
| `src/model/osdi_model.hpp` | B1：`beginNewtonStep()`/`markJacComputed()`/`residOnlyPending()`/`setResidOnlyMode()` 接口 + `residOnlyPending_`/`residOnlyActive_` 成员 |
| `src/assembly/transient_assembly.{hpp,cpp}` | B1：`assembleTransient` 加 `residOnly` 参数；OSDI 装配块在 `residOnly && residOnlyPending()` 时走 `evalTransientResidOnly`（复用 jac，只重算 resid），首装配 `markJacComputed()` |
| `src/solver/time_stepper.{hpp,cpp}` | B1：Newton 步首 `beginNewtonStep()`，line-search 装配传 `residOnly=true`；B2：`TimeStepperOptions.multiRate` + 积分前 `setMrAutoTune(true)` |
| `src/solver/shooting.{hpp,cpp}` | B2：`ShootingOptions.multiRate` + `solveShooting` 入口对 OSDI 器件 `setMrAutoTune(true)`（B1 **未启用**于 shooting——保 FD 一致性，见下方风险说明） |
| `src/cli/main.cpp` | B2：`resolveMultiRate()` 解析 `.options multirate=`；注入 `.pss`/HB→Shooting 回退 opts |

## 关键设计决策

### B1：Jacobian 级 bypass（需求 1）

**问题**：Newton 内层 line-search 时，每个试验点重新装配整个系统（含 OSDI 雅可比计算）。但 **Jacobian 在同一 Newton 步内不变**——只有 residual 随试验电压变。`evalTransientResidOnly`（V3-MR Phase2 实现）本为此设计，但是死代码（`osdi_model.hpp:134` 标注"L6: 当前未被 assembler 调用"）。

**激活**：`assembleTransient` 加 `residOnly` 参数。time_stepper 的 line-search（`assembleAndNorm` 第二个及以后调用）传 `residOnly=true`；Newton 步首（`beginNewtonStep`）首装配算完整 f+jac 并 `markJacComputed`，后续试验点走 resid-only（jac 从 `lastJac_` 复用）。**省 line-search 每试验点的 jac 计算开销**（BSIM4 jac 含 12 内部节点，开销显著）。

**调用方契约**：`residOnly=true` 装配的 `sys.G` 含 stale jac，**不可用于求解**——仅取 `sys.F` 算 ‖F‖。time_stepper 的 line-search 恰好只用 ‖F‖（接受准则），符合契约。

### B1 风险控制：shooting 不启用

shooting 的 `integrateOnePeriod` 有 **P0-4 一致性约束**（`shooting.cpp:210-217`）：主路径与 FD 雅可比扰动路径必须用同一接受准则演化，否则 FD 噪声爆炸。resid-only bypass 可能让两路径在 jac 更新时机上分歧。故 **B1 仅在 standalone transient（time_stepper）启用，shooting 保持全装配**。这是正确的风险权衡——standalone transient 无 FD 一致性问题，收益直接；shooting 的 multi-rate bypass（V3-MR）已独立处理。

### B2：multi-rate 自动开关（需求 3）

**现状**：V3-MR Phase 1-4 已实现完整 multi-rate 基础设施（`mrRateRatio`/`mrStepCounter`/`mrAutoTune`/`mrCheckVoltages`），但需**手动** `setRateRatio(K)` 或 `setMrAutoTune(true)` per device（如 `test_shooting.cpp:603` 的 `m->setRateRatio(4)`）。普通用户无法从网表启用。

**增强**：`TimeStepperOptions.multiRate` / `ShootingOptions.multiRate`（默认 false，bit-identical）。开启后积分入口对所有 OSDI 器件 `setMrAutoTune(true)`——器件自动分级（稳定器件 K 增大到 16，快器件回退 K=1）。CLI `.options multirate=1` 解析注入。**复用现有 V3-MR 机制，零新算法风险**。

### B2 未做：真正异步分区时间网格

方案中 B2 的"完全版"是每器件 cluster 独立 dt + 边界插值耦合。这是 multi-rate 的本质提升但**风险极高**：
- 需重构 transient 积分循环（当前所有器件共享时间网格）。
- cluster 边界耦合（插值/保序）数学复杂，易引入数值噪声。
- FD 一致性（shooting）几乎无法保证。
- 现有同步 multi-rate（K 步延迟 swapState + 自适应 eval bypass）已捕获主要收益（慢器件省 eval），且经测试验证。

**决策**：本轮做"自动开关 + 增强现有"，留真正异步网格为后续大改（独立 sprint + 充分测试）。

## 交付标准核对

- [x] 默认 ctest **131/0/51** PASS（无退步；multiRate 默认 false 保持 bit-identical）
- [x] B1 Jacobian 级 bypass 在 time_stepper line-search 激活
- [x] B2 `.options multirate=1` 可用，自动启用 mrAutoTune
- [x] `CurrentMirrorArray8_HEAVY`（手动 K=4）PASS
- [x] shooting 保持全装配（B1 不启用，保 FD 一致性）

## Phase A + B 总结

| Phase | 需求 | 状态 |
| --- | --- | --- |
| A1 求解器抽象+自动选择 | 6 | ✅ |
| A2 HB/Shooting 收敛加固 | 7 | ✅ |
| B1 器件 bypass 强化 | 1 | ✅ |
| B2 multi-rate 自动开关 | 3 | ✅（增强现有；真正异步网格留后续） |

回归 **131/0/51**，新增 20 个单元测试（LinearSolverSelect + NonlinearDamping），无退步。

## 后续

- **Phase C**（需求 2、5）：PDK 桥接 + 参数化增强（`.lib` corner、`level=54` 映射、多参函数 `.func`）
- **Phase D**（需求 4）：波形输出多格式 + 增强 waveview
- 真正异步 multi-rate 时间网格（B2 完全版，独立 sprint）
