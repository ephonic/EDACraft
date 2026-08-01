# issues0719 修复报告（2026-07-28）

依据 `issues0719.md` 的 P0 清单与 `test_results-5.docx` 的诊断，本轮完成了
"阶段 A：可信度止血" 的核心修复，并在修复过程中新发现了若干深层求解器问题。
所有改动均已同步到 `release/` 镜像。

## 1. P0-1：铁电驱动方向与器件几何方向不一致 —— 已修复

**修复内容**

- C++ 侧的 `fe_axis_` 支持（`e_field_component`）此前已存在但**从 Python 完全不可达**
  （`set_ferroelectric_polar_axis` 绑定无任何调用点）。本轮在
  `Simulator.set_ferroelectric(..., polar_axis=...)` 中完成接线，并新增
  `Simulator.set_ferroelectric_polar_axis()`。
- `polar_axis=None`（默认）自动检测：极轴 = FE 区域填充比例
  （`FE_span / mesh_span`）最小的轴——薄膜法向启发式。z 堆叠 MFIS 模板
  正确得到 z 轴，1D 单板得到唯一非退化轴，准 2D 退化 y 轴不会被误判。
- `tcad/postprocess/discovery.py` 的存储指标不再固定读 `Px`，改为读取
  主极化分量（均值最大的分量）。
- 端到端实测（内置 `Device.alscn_mos2_fefet()` 模板，z 向栅扫）：
  **Px = Py = 0 恒成立，Pz 在收敛点上随栅压响应**（±5V 内 Pz 范围
  ≈ [-9.4e-3, +3.2e-3] C/m²，为部分翻转——20nm AlScN 矫顽电压 ~7V，
  这是 issues0719 §4.1 的串联电容物理，不是 bug）。

**新增回归测试**（`tests/test_fefet_validation.py`）

- `TestPolarAxis`：z 膜/1D 板自动检测、显式轴向、非法轴向 fail-fast、
  未知模型名 fail-fast（§5.4）。
- `TestFeFETPolarAxisEndToEnd::test_z_gate_sweep_drives_pz`：z 向栅扫
  驱动 Pz、Px≈Py≈0、每个偏置点必须真实收敛、`valid` 标志存在。

## 2. P0-3：收敛判据与伪收敛 —— 系统性修复

- **`Simulator.run()`**：结果增加 `valid` 标志；不收敛时发 `RuntimeWarning`
  （此前完全静默）。
- **Gummel 极限环重试**：2 → 8 次（阻尼可达 1/256），并且重试时
  **同时减半连续性阻尼**（观测到 PN 结与 FeFET 的环由 n/p 映射主导，
  rel_dN 摆幅 0.3–4，仅阻尼 phi 无法打破）。
- **LK 模型禁用冻结/重试**：准静态 LK 每次迭代都重播种 P，其 phi 振荡
  可能是真实的畴翻转过程，钉住 phi 会消灭翻转（回归：
  `test_p_switches_when_drive_exceeds_coercive_field`）。
- **补齐构建断裂**：工作树 `gummel_solver.cpp` 引用了头文件中不存在的
  `frozen_residual_gate`——即审查所述"源码树无法干净构建、旧 .so 被复用"
  的实锤。已补入 `GummelOptions::frozen_residual_gate = 1e-3`。
- **Newton 收敛判据**：删除全局 `|F|/(|x|+1)` 判据（|x| 被 n~1e25 主导，
  曾在 Poisson 残差 0.158 时假收敛）；改为**分块（phi/n/p）判据**：
  每块必须满足 `|F_b| < abs_tol`、`|F_b| < tol·|F_b0|`、或
  `|F_b| < tol·(|x_b|+1)` 之一。分块后 Poisson 块以电压尺度检验，
  载流子块以载流子尺度检验，任何块都无法被其他块掩盖。
- **Gummel→Newton 级联重构**：
  - Newton 打磨**总是尝试**（此前要求 Gummel 完全收敛才启动，而极限环
    正是 Newton 的用武之地）；若预热已收敛则跳过 Newton（Newton 停滞
    时的写回只会破坏已收敛状态）；
  - 预热在**首次检测到极限环时即退出**交予 Newton（正常收缩不被打断；
    环上反复阻尼重试只会污染初值）。预热退出路径**不做连续性抛光**——
    抛光扰动移交状态（实测：PN 结 Newton 从未抛光状态收敛、从抛光后
    状态停滞）；
  - 收敛判定 `converged = gummel_ok || newton_ok`，两者皆败则诚实报告
    不收敛；不做第二次 Gummel 回退（会重复推进 NLS 记忆状态，违背
    P0-2 的每偏置点一次推进语义）；
  - Newton 增加线搜索停滞看门狗（alpha=0 连续 10 次提前失败，不再磨
    满 1000 次迭代）。
- **Gummel max_iter 出口的残差终裁**：迭代停滞但更新量未达 tol 时，
  以抛光后真 Poisson 残差门禁（1e-3）裁决——满足离散方程的状态诚实
  接受（如 2D PN 结在 1.1e-4 残差处停滞），O(1) 残差的真实发散仍拒绝。
- **log-space Newton 公开 API**：`Simulator.set_newton_log_space()`。
  强反型区线性空间 Newton 停滞，log-space 后 FeFET 全偏置点在诚实
  分块判据下收敛。

**诚实化的代价（预期内）**：一批此前经"冻结后 rel_dPhi=0"或 conv_step
假收敛通过的测试现在诚实失败。处理如下（均附详细 xfail 原因）：

- `test_newton_gummel_agreement_{equilibrium,biased}`：纯 Gummel 在
  Na=1e24/Nd=1e22 结上极限环（网格无关、阻尼 1/256 仍不稳）——
  **新发现的求解器开放问题**，xfail(strict=False)。
- `test_per_node_nc_nv_affects_result`（DSFET）：同类，xfail。
- 6 个正偏/高注入电流与 NDR 测试：其中 **4 个 contact_current_2d 测试
  已于 2026-07-29 恢复为诚实通过**（0.1V 偏置延续 + Gummel→log-space
  Newton 级联 + Bank-Rose 钳位，真残差 ~1e-12）；剩余 2 个
  （mosfet sweep、tunnel_diode_converges）维持 xfail(strict=False)，
  归因开放问题 #1（全局化）。

## 3. P0-4：真实端电流与代理量 —— 生产路径止血

- `examples/alscn_mos2_fefet.py`：删除 `n.max()*1e-15` 代理回退与裸
  `except Exception`；不收敛偏置点直接 `RuntimeError`；纵轴标注修正为
  电流密度 A/m²（`contact_current_1d` 是单位截面积 SG 边通量，不是 A）。
- 示例陷阱密度从人为 `D_it=1e13`（材料值 100 倍，审查 P0-6 点名的
  "数值校准冒充界面物理"）改为材料库值（1e11 cm^-2 eV^-1）。
- `extract_transfer_characteristics` 的 `n.max()` 代理改为**显式选择加入**：
  默认 `RuntimeError` 并指向 `extract_transfer_characteristics_current`；
  `allow_density_proxy=True` 时才可用且结果带
  `current_kind="density_proxy"` 元数据。真实电流版本带
  `current_kind="current_density_a_per_m2"`，杜绝共用 `Ion` 名称混淆。
  调用方示例已更新。
- 示例最终结果（0→+3→-3→0 双向扫描，nls_dt=1e-2 = 10ms/点驻留）：
  **全部偏置点诚实收敛**，个别极限环点由 Newton 以真残差 ~6e-9 救回；
  Pz 在负向分支部分翻转到 +7.3e-3 C/m² 并在回程保持剩余极化，
  Px=Py=0 恒成立。

## 4. P0-5：被弱化的测试 —— 基于实测恢复/重写

- `tests/test_fe_validation.py`
  - imprint 测试恢复为**矫顽电压偏移**断言：E_bi=1e8 V/m 跨 40nm 应
    移动 Vc ≈ 4V，实测 3.79V，断言 >2V（正确 div(P) 下回线极值饱和，
    原"极值不对称度"断言在物理上不可见，故换可观测量）。
  - 漏电测试恢复为 **0V 末态改变**断言（实测 -1.066 vs +1.066 C/m²）。
  - NLS 测试恢复：开关响应（P.max > 0.1·Ps，实测 0.22·Ps）、
    **0V 剩余极化符号翻转**（+0.309 vs -0.068）、有限斜率
    （无单步跳变）、|P|≤Ps 有界。
- `tests/test_fe_coupling_and_ionization.py` 自旋极化重播种测试：原断言
  "中点均匀翻转到 -Ps"在正确 div(P) 下不是物理结果（接触附近成核 +
  体内畴结构，无梯度能模型里 180° 畴是正确响应）。重写为畴成核断言
  （min(P) < -0.9Ps、平均极化崩塌、翻转体积分数 >20%）——旧 bug
  （无重播种、无一节点离开旧阱）仍会被杀死。
- `tests/test_numerical_validation.py` 两个 LK 测试：
  - 回滞扫描：±1V 驱动下穿极化场锁定（实测中点 P 全程冻结）——
    Vmax 改为 8V（超过 Edep≈5.9V）后完整真值链成立
    （+Ps→+Pr→-Ps→-Pr→+Ps）。
  - 2D 矢量解耦：保留 |Px|,|Py|>0.5Ps、Pz=0 断言；符号断言改为
    "P 与**自洽总场**同号"（原断言忽略了退极化场，且注释中
    `-a/dx` 本身算错）。
- HEAD 基线对照（git worktree 干净构建）：`test_log_space_solver` 7 失败、
  `test_devsim_srh_optical` 4 失败、`test_grammar` 2 失败、
  `test_dsfet_basic_convergence` 1 失败均为 **HEAD 即存在的既有失败**，
  非本轮回归。

## 5. 构建与工程

- 编译器：`g++-15` 已不存在，使用 `CXX=g++-16 CC=gcc-16 python3 setup.py
  build_ext --inplace`。
- 所有 src/tcad/tests/examples 改动已同步 `release/`。

## 6. 测试结果汇总（当前工作树，最终构建）

| 测试集 | 结果（2026-08-01 最终） |
|---|---|
| 快速核心+求解器+数值+DSFET 11 文件 | **128 passed**（仅 1 个 HEAD 既有 dsfet_basic 失败 + 1 个既有 xfail） |
| contact_current + contact_current_2d + ndr + trust_gate | **45 passed，0 xfail，0 failed**（trust_gate 12 项全绿，含 2 个 HEAD 既有失败已修复） |
| bands/bindings/coordinate/geometry*/mechanism/mesh*/mutation/evolution 等 | 全部 passed |
| devsim_srh_optical(4) / grammar(2) / dsfet_basic(1) | HEAD 既有失败（未修复，非回归） |
| discovery_metrics / laws / simulator / tfet | 慢速套件（HEAD 同样 >10min，见第 7 节） |
| examples/alscn_mos2_fefet.py 端到端 | **16s 全部偏置点收敛**（修复前 50 迭代不收敛、P=0） |

**xfail 清零**：本轮全部 9 个因工作而设的 xfail 均已随根治移除——
2 个 Newton-Gummel 一致性 + 1 个 DSFET（半隐式 Gummel，§7.1）、
4 个 contact_current_2d（偏置延续+级联，§7.2）、
1 个 MOSFET sweep + 1 个 tunnel diode（半隐式 Gummel）。
**顺带修复**：trust_gate 的 2 个 HEAD 既有失败——`kcl_residual_1d`
优先使用求解器 __float128 边通量（原 double 重算在平衡态产生超过
1e-6 门禁的灾难性抵消噪声）；收敛解的 KCL 相对散布现为 ~1e-16。

## 7. 新发现的开放问题（处理状态更新于 2026-08-01）

1. ~~Gummel 在极端掺杂 PN 结上的网格无关极限环~~ **已根治
   （2026-08-01）**：逐节点诊断将振荡定位于结旁耗尽边缘节点——
   Boltzmann 超调（p ~ 1e6×Na）经滞后电荷驱动下一次 Poisson 求解
   ~26V，形成非光滑极限环；标量阻尼（1/256）、Anderson(1)、载流子
   对数阻尼均无效。修复：Poisson 装配加入 **Boltzmann 线性化的
   半隐式 Gummel**（(A−D)φ_new = rhs − D·φ_old，D=(q/VT)(n+p)，
   不动点不变仅改变迭代路径）。效果：该结平衡 28 次迭代收敛
   （真残差 8.4e-11），此前 5 个 xfail 全部恢复通过（2 个
   Newton-Gummel 一致性、DSFET per-node Nc/Nv、MOSFET sweep、
   tunnel diode），全部 xfail 标记已移除。
2. ~~Newton 停滞（疑似 Jacobian/残差装配不一致）~~ **已查明并修复**
   （2026-07-29）：新增有限差分 Jacobian 校验器
   （`tools/fd_jac_check.cpp`、`tools/fd_jac_fefet.cpp`，后者可直接加载
   Python 导出的真实器件状态），在 4 个代表性状态（1D PN、FeFET 平衡、
   正偏 2D PN 远态、2D PN 移交态）上 verify **assemble_jacobian 与
   assemble_residual 完全一致（0 个失配项）**。停滞的真正根源：
   (a) 预热出口抛光扰动移交态（已修：预热模式不抛光）；
   (b) log 空间远离解时 Newton 方向需要 α~1e-8 的步长，回溯范围
   [0.01, 1] 内残差反而上升（exp 非线性爆炸）——已通过
   **Bank-Rose log 空间步长钳位**（|du|≤5）修复；
   (c) 个别高注入器件（MOSFET sweep、tunnel diode）即使在钳位+延续下
   仍难以在合理时间收敛——归入开放问题 #1（全局化）。
   配套改进：`simulate_sweep` 新增 `use_newton`/`newton_log_space`
   参数；4 个 contact_current_2d 测试经 0.1V 偏置延续 + 级联恢复为
   诚实通过（真残差 ~1e-12）；剩余 2 个（mosfet sweep、tunnel diode）
   维持 xfail。
3. **高驱动下 LK 纯板的 P↔-div(P) 代数循环**：±8V 时 64/125 偏置点
   不收敛（低驱动正常）。铁电-静电强耦合需要专用阻尼或全耦合装配。
4. 慢速套件（discovery_metrics/evolution/laws/simulator）单文件运行
   >3–10 分钟，主要消耗在非收敛点的诚实重试上；需要按第 1 项根治后
   再评估。

## 8. 未覆盖的 P0 项（建议后续）

- P0-2（NLS 时间绑定迭代）：工作树此前已修复（每次 solve() 仅在
  iter==0 推进一次），本轮补充了不变性覆盖于 e2e 测试。
- P0-6（界面陷阱面元化）、P0-7（泄漏/击穿守恒装配）：量纲与网格
  不变性此前已部分修复，面元化与守恒装配属阶段 B，未动。
- IGZO/WSe₂ 材料机制（test_results-5 的"过于理想"问题）：属阶段 C，
  在 P0 可信度门禁建立前不应继续堆功能。
