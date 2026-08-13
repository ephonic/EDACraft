# TCADCraft 0.2.0 发布说明

> 2026-08-08 中间审计（已由下方 2026-08-09 结果取代）：已显式冻结 Sentaurus W-2024.09 Silicon DOS 质量与
> QuantumPotentialParameters，加入 DOS 质量+gamma 公共映射、严格量子残差门和
> 固定界面闭合 API，并移除按膜厚切换的 DG 经验项。3/5/8/10 nm 厚度族仍为
> `partial_not_passed`；现已加入 opt-in 式 (248) 势形式 PDE，并与式 (250)
> 材料阶跃边界在同一 Gummel 固定点中求解。5 nm 完整连续路径量子残差为
> 7.37e-7、电流幅值误差为 0.663%，但片电荷仍差 7.85%；下一闭环项已转为
> 重合材料侧界面/切割控制体电荷映射，而不是继续增加厚度经验项。

> 2026-08-09 界面续修：厚度回放已改用完整材料侧节点与几何控制体占比；通用
> cut-cell 修复了界面位于边端点时的介电常数侧别，并开始使用真实器件 region
> shape。式 (250) 的 gamma 也已按手册改取未求解势垒侧 `0+`，不再误用硅侧
> 式 (248) 的 gamma。修复后 5 nm 的电流幅值/片电荷误差为 2.456%/0.637%，
> 密度 log-RMSE 为 0.0386 decade，量子势 RMSE 为 3.38 mV，最终量子残差
> `6.15e-8`，全部通过；跨偏压量子状态延续也消除了每级回退密度形式的重启。

> 2026-08-09 最终审计：原 3 nm Sentaurus golden 被网格审计判定未收敛，现已
> 由 fine→ultrafine 收敛的 29 节点剖面替换。TCADCraft 3 nm 完整回放通过，
> classical/DG 电流 RMSE 为 0.0766/0.0501 decade，Vt 误差 3.21 mV，量子势
> RMSE 3.95 mV，classical/DG 片电荷误差 0.155%/0.628%。同时修复了 continuity
> 失败后 NaN 状态仍可能被标记 converged 的发布阻断项，并加入 portable 窄带 LU。

> 2026-08-11 发布候选审计：8 nm 已用同一公共路径完成正式重放，最大量子残差
> `9.932e-6`、最大截面 KCL 相对误差 `1.054e-4`。3/5/8/10 nm canonical
> 合并后的量子 Vt 位移与片电荷比趋势相关系数分别为 `0.999891/0.995574`，
> 均通过 `0.90` 门限，厚度族状态更新为 `passed`。量子审计新增事务回滚、
> 平台专用 Q-only 提交和一次性终端 Q 混合重启；所有原方程验收门限保持不变。

发布日期：2026-08-11

TCADCraft 0.2.0 是首个以 Sentaurus W-2024.09 标定门禁为核心的发布版本。
本版本重点闭环量子修正、Newton/Gummel 耦合稳定性、接触与隧穿、可靠性，
以及雪崩击穿和自热仿真。

## 发布门禁

- HfO2 铁电主回线：通过。
- Si 陷阱 stress/recovery：通过。
- GaN Schottky + 非局域隧穿：通过。
- GaN 接触精化：热发射/总电流 log-RMSE 0.0155/0.0226 decade，开启电压
  误差 0.927 mV，NLM 峰值幅度误差 4.12%。
- 8 nm 双栅 MOS 密度梯度量子修正：通过。
- 3 nm 双栅 MOS 超细网格密度梯度量子修正：通过。
- 3/5/8/10 nm 厚度族及跨厚度趋势：通过；Vt 位移/片电荷比趋势相关系数
  0.999891/0.995574。
- 8 nm 非平面双栅 FinFET：通过；classical/DG 电流 log-RMSE
  0.03475/0.02584 decade，最大相对误差 12.35%/14.28%，DG/classical 比值
  RMSE 0.03332，最大量子残差 9.349e-5。
- 2-D 平面长沟道 nMOS：五条 Id–Vg/Id–Vd 分支通过；log(Id) RMSE
  0.0140–0.0371 decade，Vt 误差 2.32–3.12 mV，最大 SS 误差
  0.0695 mV/dec，Id–Vd 最大抽样误差 4.70%，导通区最大 KCL 偏差 5.27e-7。
- 3-D 四面栅 GAA nanosheet：60 个 classical/DG 点全部通过；六分支
  log(Id) RMSE 0.01735–0.07821 decade，Vt 误差 1.87–6.06 mV，最大 Ion
  误差 7.68%，强反型 DG/classical 比值 RMSE 0.08533，最大量子残差
  9.457e-5。
- 电热雪崩击穿：通过；热失控外电压误差 3.72%，峰值温度误差
  0.193%，端电流 KCL 相对散度 6.10e-9。
- 本轮相关数值回归：128 passed；其中 35,937 节点 3-D MMS 独立慢门禁
  `1 passed in 837.98s`，四点高层 MOS sweep `1 passed in 4.41s`。
- nMOS 非均匀 Poisson/材料界面连续性定向回归：`30 passed`；另有 50 个正式
  nMOS 偏置点全部收敛并通过自动指标验收。
- 干净环境构建/安装快速门禁：42 passed（24.65 s）。
- IGZO/WSe2 mixed material dashboard：通过发布口径门禁。IGZO full-DD tail selector
  已通过 6 个 Sentaurus synthetic 分支；WSe2 当前按 Sentaurus response replay 发布，
  compact/contact/full-DD 替代仍保持 diagnostic-only，不能标记为物理模型通过。

## 重要行为变化

Newton-primary 模式不再继承跳过的 Gummel 预热结果；Newton 收敛后也不再
执行会破坏载流子一致性的 Poisson-only 重解。Auger 及其解析 Jacobian 已进入
全耦合 Newton，非收敛安全钳位、KCL 判据、延续步长和热终止点细化也已加固。
所有 Gummel 接受出口现在要求 continuity polish 成功且状态有限；Newton 对
NaN/Inf 输入、残差、Jacobian、步长和写回逐层拒绝。无 PETSc/LAPACK 时，窄带
结构网格使用内部 banded LU，宽带问题使用 GMRES+ILU0。

高动态范围 3-D 连续性矩阵现在可用上一有限载流子状态作物理列尺度，再做仅行
均衡与混合精度精修；接受判定始终回到未缩放 float128 原方程。强单极量子状态
允许严格受限的少子块暂缓，但每 8 步和最终审计都强制双载流子求解。Python
结果字典新增 `poisson_residual`。共享材料侧节点的半导体电荷控制体可与输运
裁剪保持一致，改善 FinFET/GAA 的非平面界面泛化。

非均匀网格 Newton Poisson 现在使用 `edge×cell` 控制体离散；Newton 电子/空穴
连续性也在零迁移率材料邻点处裁剪绝缘体侧半控制体，与 Gummel 和端口电流积分
采用同一几何。由此消除了旧平面 nMOS 的 38 mV Vt 偏移和约 45% 电流倍率误差，
没有引入经验电流或迁移率倍率。

高漏压 GAA DG 路径现在使用冻结的吸引域续接节点、最佳真实残差保留和原子状态
检查点。正式偏置点同时检查 Poisson、DG 与 KCL；高场 Poisson 门为 2.5e-3，
明显拒绝约 1.2e-2 的污染状态，且失败 polish 不再覆盖更优解。

## 已知边界

本版本可用于已通过门禁的参考器件与相邻参数空间，但不能把 Sentaurus synthetic
golden 当作材料实验真值。3/5/8/10 nm 公共路径和跨厚度趋势现已通过；
IGZO、WSe2 仍需实验/文献/第一性原理约束
材料参数。当前 IGZO/WSe2 mixed dashboard 的发布口径是：IGZO full-DD selector
已通过 synthetic Sentaurus 对标；WSe2 只声明 response replay 对齐，compact/full-DD
替代仍未闭环。电热击穿当前以 0.07 标定缩放等效缺失的原生高场速度饱和模型，加入
该模型后必须重新标定。

## 构建与验证

```bash
TCAD_USE_PETSC=0 TCAD_USE_LAPACK=0 python setup.py build_ext --inplace
python scripts/release_check.py \
  --calibration-root ../.. \
  --mixed-material-dashboard ../../bench/results/calibration/tcadcraft_mixed_material_calibration_dashboard.json
python -m pytest -q
```

本版本仅发布 `EDACraft/TCADCraft/` 中的代码，不附带 tar.gz 或 wheel。默认构建
采用内部直接求解器，不依赖系统 LAPACK/BLAS，从而避免与 SciPy 自带线性代数库
发生符号冲突。经过平台级验证后，源码构建可显式设置
`TCAD_USE_LAPACK=1` 启用系统 LAPACK 加速。

支持 GCC/Clang 的 Linux 和 macOS 源码构建；原生 Windows/MSVC 不支持，Windows
用户应使用 WSL2。
