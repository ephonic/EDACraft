# 仿真器对标进度 (2026-07-30)

## HSPICE W-2024.09 黄金参考 — BSIM4 直驱 DC

| VG (V) | HSPICE Id (µA) | rfsim OSDI Id (µA) | rfsim Gen Id (µA) |
|--------|----------------|---------------------|--------------------|
| 0.70   | 2.65           | 80.5 (30x)          | NOT CONV           |
| 0.80   | 24.1           | 131  (5x)           | NOT CONV           |
| 0.90   | 85.1           | 181  (2x)           | NOT CONV           |
| 1.00   | 169.3          | 231  (1.4x)         | **166.6 ✓ (1.6%)** |

## 关键发现

### OSDI 模型 (bsim4.dll)
- 所有偏置点误差巨大 (1.4x ~ 30x)
- **根因**: OpenVAF 把 W/L/NF 等几何参数编译为 MODEL-kind（不是 INST-kind）
- rfsim 把网表 M1 的 w=1u l=130n 当作 instance params 传递 → `setInstanceParam` 找不到 → 静默丢弃
- BSIM4 使用默认 W=5µm, L=5µm（而非 1µm/130nm）→ W/L = 1（应为 7.7）

### Generated 模型 (bsim4va_gen.cpp)
- VG=1.0 已精确到 1.6% ✓
- VG=0.7-0.9 **不收敛** — Newton 残差 stuck 在 |F|=2.9e-3
- 诊断: gmin stepping 到 gmin=1e-3 时，残差停止下降，node 4 电压变化 ~1e-4/iter
- 可能原因: generated model 的 Jacobian 部分导数未初始化（编译有大量 C4701 警告）

## 下一步
1. 修复 generated model 的 Jacobian — 检查所有 `d*` 变量的初始化
2. 增强 DC 收敛 — 更小的 dvmax 或更多 gmin 步
3. 扩展到 diode/bsimcmg 对标
