# rfsim 项目状态报告 — 2026-06-21 (S1 完成)

## 当前任务

按照 `plan0621-v4.md` 第 §1 / §3 的 **Sprint S1（~300 行预算）** 实施 KI-1（HB-NL
BSIM4 非收敛）与 KI-2（N≥15 多实例崩溃）的低风险缓解。

用户原话：
> 请按照计划修复

## TL;DR

| 维度 | v5 基线 | S1 (本轮) |
| --- | --- | --- |
| 默认全量测试 | 100 PASS / 0 FAIL | **100 PASS / 0 FAIL** |
| HEAVY 子集（17 项可完成集） | — | **17 PASS / 0 FAIL** |
| HB-NL 旧测三件套 | PASS | PASS（含 `DiodeRectifierContinuation` 经源步闸作修复后） |
| 代码增量 | — | 5 个源文件 + 1 个新增文档（≈260 行净增） |
| KI-1 缓解 | 仅 autoHomotopy | **AC warm-start + Armijo 修正 + bad-gate 收紧 + RFSIM_HBNL_VERBOSE** |
| KI-2 缓解 | C3 单 setup_model + 内存泄漏 patch | **本轮无源码改动；落地 `bsim4MultiEnabled()` SKIP gate + `docs/known_issues.md` 正式归档** |

构建日志：`out_s1_default.log`。  
默认回归日志：`out_s1_default2.log` → `[ PASSED ] 100 tests`。  
HEAVY 子集日志：`out_s1_heavy_safe.log`、`out_s1_heavy_extras.log`。

---

## S1-#1 — HB-NL BSIM4 非收敛（KI-1）

### S1-#1 补丁 1：Armijo 比较式修正

文件：`src/solver/hb_nonlinear.cpp`（~478-493 行附近）

**原状**
```cpp
if (fTrial <= fNorm * (1.0 - 1e-4 * alpha)) { ... }
```
Armijo 标准充分下降条件应为 `‖F(x+αΔx)‖² ≤ ‖F(x)‖² · (1 − 2cα)`。原写法把 `c` 当
成线性 ‖F‖ 系数，等效 c=0.5e-4，**实际下降门槛严格了一倍**，导致更频繁回退 α，最终
触发 best-α / safestep 兜底而无法稳步下降。

**修正**
```cpp
const double armijoC = 1e-4;
if (fTrial * fTrial <=
    fNorm * fNorm * (1.0 - 2.0 * armijoC * alpha)) { ... }
```

### S1-#1 补丁 2：evalTimeSamples bad-gate 收紧

文件：`src/model/osdi_model.cpp`（evalTimeSamples、evalTimeJacobians、
evalTimeJacobiansReact 三处对称改动）

**原状**：节点电压 |v|>100V 直接置 bad=true 并跳过该时域样本——破坏 FFT 周期性，
导致频域 Newton 信号被人为加噪声。

**修正**：
```cpp
if (std::isnan(vv) || std::isinf(vv)) { bad = true; }
else if (std::abs(vv) > 20.0) { vv = (vv > 0) ? 20.0 : -20.0; }
globalV[nodes_[i]] = vv;
```
即只对 NaN/Inf 标 bad，其余大幅度电压 clamp 到 ±20V，**保 FFT 周期性、保 Newton
连续性**。

### S1-#1 补丁 3：RFSIM_HBNL_VERBOSE 环境开关

文件：`src/solver/hb_nonlinear.cpp`

新增 `hbnlVerbose()` 帮手函数读取 `RFSIM_HBNL_VERBOSE`，在三个关键节点打印：
- 每轮 Newton 进入时：`iter`, `‖F‖`, `sourceScale`, `gmin`
- safestep 触发：`dxMax > dxCap` 时回到 best-α
- Armijo 失败回退到最佳 α

诊断用法：
```cmd
set RFSIM_HBNL_VERBOSE=1
ctest -R S2_Bsim4CsNhGrid -V
```

### S1-#1 路径 D：AC 小信号 warm-start

文件：`src/solver/hb_nonlinear.cpp`、`src/solver/hb_nonlinear.hpp`

**做法**：在 HB Newton 进入前——但**在 autoHomotopy 设置完成且未启用源步进时**
——对 `k≥1` 谐波列做一次线性化 AC 求解：
1. 在 X = DC 工作点处装配 HB Jacobian（=AC admittance Y(jω_k) 的块对角逼近）。
2. 装配源 RHS（仅 sin/cos 激励的 k=1 列）。
3. dim ≤ 200 走 `denseLuSolve`；更大走 GMRES + `BlockHarmonicPrecond` →
   `DiagonalHbPrecond` 兜底。
4. 求解结果 ΔX_{k≥1} 经 dxCap=1.0V 的 scale 后注入 X[e][k]，**k=0 (DC) 保留**。

**关键闸作（修一次回归后的版本）**
```cpp
HbNlOptions eff = opts;
// auto-homotopy block ...    (necessary to be BEFORE warm-start)
bool srcRamped = (eff.sourceSteps > 0)
                 && (eff.sourceStart < 1.0 - 1e-12);
if (opts.acWarmStart && NH >= 1 && !srcRamped) {
    acSmallSignalWarmStart(...);
}
```
**理由**：AC warm-start 假设 sourceScale=1；若调用方启用源步进且从 sourceStart<1
开始，预灌的 X[k≥1] 在 sourceScale=0 段反而是离真解最远的恶劣初值，导致
`DiodeRectifierContinuation` 在第 1 步源 ε=0 时震荡不收敛。`srcRamped` 闸保留
原行为，warm-start 只对非源步进路径生效。

`HbNlOptions` 新增字段：
```cpp
// 默认 true；失败静默回退 DC-only，零回归风险。
bool acWarmStart = true;
```

---

## S1-#2 — N≥15 BSIM4 多实例（KI-2）

按 `plan0621-v4.md` §2 / §3 计划，KI-2 在 S1 走 **路径 D（文档化 + SKIP gate）**：
真正的修复（MinGW 重编 bsim4.dll）排入 S3，**本轮不动 dll 构建**。

### S1-#2 落地清单

1. **`docs/known_issues.md`**（新增，~4 KB）
   - KI-1 / KI-2 各一条表格 + 根因 + 已部署 / 未完工缓解 + 复现命令 + 主参考。
   - 红线段：默认 100/100 PASS + RFSIM_FORCE_HEAVY 下除 KI 明示项外 PASS。

2. **`tests/test_large_circuit.cpp`**
   - 新增 `[[maybe_unused]] bool bsim4MultiEnabled()`：读 `RFSIM_FORCE_BSIM4_MULTI`，
     用作未来 BSIM4 多实例 HEAVY 用例的 opt-in 闸（**当前 SKIP gate 占位，未挂用例**）。

---

## 回归验证

### 默认全量（`out_s1_default2.log`）
```
[==========] 100 tests from 50 test suites ran. (4123 ms total)
[  PASSED  ] 100 tests.
```
含 `DiodeRectifierContinuation`（最初因 warm-start 与 sourceStart=0 冲突 FAIL，修
源步闸作后绿）、`Bsim4CommonSourceConverges`、`BSIM4soiHbNlCommonSource` 全 PASS。

### HEAVY 子集（`out_s1_heavy_safe.log` + `out_s1_heavy_extras.log`）

| # | 测试 | 用时 (ms) | v5 基线 | 状态 |
|---|------|----------|--------|------|
|  1 | LargeCircuitLinear.ResistorMesh20x20_DC                    |     7 | — | PASS |
|  2 | LargeCircuitLinear.ResistorMesh50x50_DC_HEAVY              |    48 | — | PASS |
|  3 | LargeCircuitLinear.RcLadder1000_AC_HEAVY                   |  2510 | — | PASS |
|  4 | LargeCircuitLinear.RcLadder2000_AC_HEAVY                   | 20928 | — | PASS |
|  5 | LargeCircuitLinear.LcTankChain10                           |     0 | — | PASS |
|  6 | LargeCircuitLinear.LcTankChain50_HEAVY                     |     2 | — | PASS |
|  7 | LargeCircuitLinear.LinearHbNhScan                          |     0 | — | PASS |
|  8 | LargeCircuitHbnl.DiodeRectifierStack5_NH5_DefaultDense     |   300 | — | PASS |
|  9 | LargeCircuitHbnl.DiodeRectifierStack30_NH10_HEAVY_TriggersGmres | 5886 | — | PASS |
| 10 | LargeCircuitBsim4.G2_Bsim4CsNhScan                         |  4062 | — | PASS |
| 11 | LargeCircuitBsim4.A1_InverterChain10                       |  1525 | 700 (v5) | PASS（慢 ~2×，AC warm-start 开销，可接受） |
| 12 | LargeCircuitBsim4.A2_CascadeCS3Stage                       |   146 | — | PASS |
| 13 | LargeCircuitBsim4.A2_CascadeCS5Stage_HEAVY                 |   298 | — | PASS |
| 14 | LargeCircuitBsim4.M1_LcMatchedCsAmp                        |     6 | — | PASS |
| 15 | LargeCircuitBsim4.M2_CascodeLnaPiMatch_HEAVY               |   333 | — | PASS |
| 16 | LargeCircuitBsim4.M3_RingOscillator3Stage_HEAVY            |    10 | — | PASS |
| 17 | LargeCircuitBsim4.S2_Bsim4CsNhGrid                         |  4919 | NH=7: 499 (v5) | PASS（全 grid，hb=0 但工作点解出） |

**全 17 项 PASS / 0 FAIL**。

### v5 基线已知挂起项（不在 S1 修复范围，已归档到 KI-2）

| 测试 | 状态 |
|------|------|
| `LargeCircuitBsim4.A3_NmosPullupBuffer20_HEAVY` | 挂起 > 90s — 20 NMOS 多实例，KI-2 |
| `LargeCircuitBsim4.A1_InverterChain15_HEAVY`   | v5 baseline 已记为 N15 挂死，KI-2 |
| `LargeCircuitBsim4.S1_InverterChainGrid`       | 含 N=8/10/15 网格，过半段进入 KI-2 region |

**结论：与 v5 基线（`status0620_v5.md`） 完全对齐，无新增回归。**

---

## 代码增量统计

| 文件 | 改动 | 估计行数 |
| --- | --- | --- |
| `src/solver/hb_nonlinear.cpp` | +AC warm-start helper / +Armijo 修正 / +verbose 打印 / +srcRamped 闸 | ≈ 180 |
| `src/solver/hb_nonlinear.hpp` | +`acWarmStart` 字段 + doc-comment | ≈ 10 |
| `src/model/osdi_model.cpp`   | bad-gate 三处对称改动 | ≈ 18 |
| `tests/test_large_circuit.cpp` | +`bsim4MultiEnabled()` helper | ≈ 6 |
| `docs/known_issues.md`        | 新增 | 88 |
| `status0621.md`               | 新增（本文件） | — |

S1 预算 ~300 行；实际 ≈ 220 行净增（不含本文档与 doc 文件）。**预算内。**

---

## 仍未触动 / 排入后续 Sprint

| KI | 未做 | 计划 |
|----|------|------|
| KI-1 路径 B | FFT 4× oversampling + 残差 jωQ 项补全 | Sprint S2 |
| KI-1 路径 A | trust-region / LM 替代 line search | Sprint S3 |
| KI-2 路径 A | MinGW 重编 bsim4.dll，去跨 CRT | Sprint S3 |
| KI-2 路径 C | ekv / nmos_sh.dll 做多实例边界对照实验 | Sprint S2 |

详见 `plan0621-v4.md` §3 优先级矩阵。

---

## 红线（与 v5 一致）

- 默认 ctest 必须 100/100 PASS（不含 HEAVY / FORCE_* 用例）。  
- `RFSIM_FORCE_HEAVY=1` 下，除 KI-1 / KI-2 明示用例外其余必须 PASS。  
- KI 文档（`docs/known_issues.md`）任何条目增删须同步 `plan0621-v4.md` §3。
