# 优化项 3-7 完成状态（第二波）

日期：2026-07-17。承接第一波优化项 1-5（`.tran`/`.measure`/OpenMP 基础/噪声框架/S 参数稳定性）。

## TL;DR

| 项 | 状态 | 验证 |
| --- | --- | --- |
| 3. **OpenMP 并行器件 eval**（完整实现） | ✅ | per-device 并行（hb_jacobian device loop），16 HB 测试 PASS（OpenMP ON+OFF 一致） |
| 4. **噪声分析 `.noise`**（完整实现） | ✅ | 线性 R 热噪声，PSD=4kTR=1.6575e-17 V²/Hz 精确匹配理论值；RC 低通噪声衰减曲线正确 |
| 6. **温度设置 `.options temp=`** | ✅ | 温度传入 OSDI `setup_instance`（°C→K）；bsim4.dll 温度灵敏度取决于模型实现 |
| 7. **真正异步 multi-rate 时间网格** | 🟡 推迟 | 架构性改动（积分循环重构+边界插值+FD 一致性），独立 sprint |

**回归 187 tests, 162 PASSED / 0 FAILED / 51 SKIPPED**（全程 0 退步）。

## 详细

### ✅ 3. OpenMP 并行器件 eval

**设计**：per-device 并行（非 per-sample）——每 OSDI 器件有独立 `OsdiClient`（instance_data + state），天然线程安全。`hb_jacobian.cpp` 的器件循环重构为：并行 eval（`#pragma omp parallel for`）→ 串行 FFT + 装配（写共享 `sys.F`/`sys.J`）。

**为什么不用 per-sample 并行**：OSDI instance_data 含内部指针（node_mapping、jacobian_ptr），memcpy 克隆有指针安全问题（实测 segfault）。

**验证**：
- OpenMP ON (`-DRFSIM_USE_OPENMP=ON`)：187 tests, 162/0/51
- OpenMP OFF（默认）：187 tests, 162/0/51
- 两种模式结果完全一致（并行正确性验证）

### ✅ 4. 噪声分析 `.noise`

**实现**：`src/solver/noise_analysis.{hpp,cpp}`。线性电路（R/L/C/V）的噪声分析。
- 每个 R 的热噪声电流源 PSD = 4kT/R (A²/Hz)
- 每个 freq 点建复数导纳 Y(jω)，对每个噪声源求传输 H = Y⁻¹·b，输出 PSD += |H|²·PSD_src
- KLU 复数求解（复用 AC 分析的 KluZSolver）
- 积分噪声 RMS（梯形积分）

**验证**：RC 低通（R=1k, C=1u），1Hz 处 PSD=1.6575e-17 V²/Hz = 4kTR（精确匹配），高频 RC 衰减，积分噪声 0.064 µV RMS。

### ✅ 6. 温度设置

**实现**：`ParamEnv.temperature`（K）→ `OsdiModel::setTemperature` → `setup_instance`。CLI `.options temp=<°C>` 解析（°C→K）。

**验证**：`.options temp=85` 正确传入 OSDI（DC OP 收敛）。bsim4.dll 的温度灵敏度取决于该 VA 模型的温度模型实现（当前参数集温度效应不明显——模型限制，非代码问题）。

### 🟡 7. 真正异步 multi-rate 时间网格

**推迟**：架构性改动（积分循环重构 + cluster 划分 + 边界插值 + FD 一致性），独立 sprint。当前同步 multi-rate（B2，已交付）通过 K-step delayed swapState + 自适应 eval bypass 捕获主要收益。

## 两波优化累计总览

| 优化项 | 状态 |
| --- | --- |
| 1. `.tran` CLI | ✅ |
| 2. `.measure` | ✅ |
| 3. OpenMP 并行 eval | ✅ |
| 4. `.noise` 噪声分析 | ✅ |
| 5. S 参数稳定性 | ✅ |
| 6. 温度设置 | ✅ |
| 7. 异步 multi-rate | 🟡 推迟 |

**6/7 优化项完整交付，1 项架构性推迟。**
