# rfsim 代码审计报告 — 2026-06-23

## 审计范围

对 stamp 机制、稀疏 LU 求解器、HB 求解器、AC 分析、DC 收敛性、器件 eval 六个模块进行系统性代码审查。

---

## 高严重度问题（需立即修复）

### H1 — DC OP polish step line search 接受更差的步
**文件**: `src/solver/dc_op.cpp:184, 572`
**问题**: line search 的接受条件 `fNew <= fOld * (1.0 + 1e-6)` 允许残差增大的步被接受。在 polish step 中（无后续迭代），更差的步被提交为最终解。
**影响**: 允许非下降步被提交为收敛解——这正是 C3-bis 修复的 polish step 应该防止的。
**修复**: 改为严格下降 `fNew <= fOld`（或 `fNew <= fOld * (1.0 - 1e-6)`）。

### H2 — DC OP bestGmin 初始化为 gminStart 而非 target
**文件**: `src/solver/dc_op.cpp:413`
**问题**: `bestGmin = opts.gmin.gminStart`。若所有 gmin 步都不收敛，polish 和分支电流提取在 gmin=gminStart（如 1e-2）下运行——大电导淹没真实器件电流。
**影响**: 全局非收敛时返回的 nodeVoltages/branchCurrents 对应错误 gmin，下游 HB warm-start 从严重扭曲点开始。
**修复**: 初始化 `bestGmin = opts.gmin.gmin`（target）。

### H3 — DC OP floor-accept 的解被报告为 converged=true
**文件**: `src/solver/dc_op.cpp:466, 507`
**问题**: floor-accept（残差停滞接受）返回 `stepConverged=true`，`lastConvergedScale` 被设为当前 scale。最终 `reachedTarget` 检查 `lastConvergedScale == 1.0`——floor-accept 的非收敛解被误报为收敛。
**影响**: 非收敛的 DC OP 被误报为收敛，下游分析从错误工作点开始。
**修复**: floor-accept 不应设 `lastConvergedScale`；或 `reachedTarget` 应区分真收敛和 floor-accept。

### H4 — HB loadResidualReact stub 清零电荷 Q
**文件**: `src/model/osdi_model.cpp:247-260`
**问题**: V3 C3-bis 修复时 `loadResidualReact` 被 API 漂移移除，改为 `reactResid.clear()`。导致 HB 残差中 `jω·Q` 项消失，但 Jacobian 仍含 `jω·∂Q/∂V`——F/J 不一致。
**影响**: 含电容的 OSDI 器件（BSIM4 的 Cgs/Cgd 等）HB 结果不正确。Newton 无法收敛到正确解。
**修复**: 恢复 reactive residual 路径——重新实现 `loadResidualReact` 或通过其他 OSDI API 获取 Q。

### H5 — AC 分析静默跳过非线性器件
**文件**: `src/solver/ac_analysis.cpp:110-127`
**问题**: AC 分析只处理 R/C/L/CS/VS，`OsdiModel` 被 `dynamic_cast` 链跳过——非线性器件在 AC 中表现为开路。无 DC OP 线性化。
**影响**: 含 BSIM4/diode 的电路 AC 结果错误（器件被忽略）。
**修复**: 至少检测 OsdiModel 并发出警告；理想方案是先做 DC OP，提取器件小信号 (G, C) 矩阵。

### H6 — AC 分析 Inductor admittance(omega=0) 除零
**文件**: `src/model/builtin_devices.hpp:153`
**问题**: `Complex(0.0, -1.0 / (omega * l_))`——omega=0 时产生 -inf。
**影响**: Lin 扫频从 0Hz 开始时矩阵含 inf，结果 NaN。
**修复**: omega=0 时返回大电导（如 `Complex(1e6, 0)`），与 HB 的处理一致。

### H7 — OSDI eval alpha=1.0 硬编码，Trapezoidal 退化为 BE
**文件**: `src/model/osdi_model.cpp:472, 518`; `src/model/osdi/osdi_client.cpp:368`
**问题**: `alpha=1.0` 硬编码，`op.method` 和 `op.dt` 被丢弃。Trapezoidal 积分被静默退化为 Backward Euler。
**影响**: 电荷精度损失 `(1-alpha)·Q` 每步累积。
**修复**: alpha 应根据 `op.method` 计算——BE: alpha=1.0，Trapezoidal: alpha=0.5。

### H8 — DC 和 transient 的 out.f 符号相反
**文件**: `src/model/osdi_model.cpp:419-422` (DC: `out.f[i] = resid[i] + limRhs[i]`, 无翻转) vs `483` (transient: `out.f[i] = -rhs[i]`, 翻转)
**问题**: DC `eval()` 的 `out.f` 不翻转，transient `evalTransient()` 的 `out.f` 翻转。assembler 对两者都用 `sys.F += dc.f[k]`——符号不一致。`loadSpiceRhsTran` 的 fallback 路径（调 `load_residual_resist`）会双重翻转。
**影响**: 残差符号错误导致 Newton 方向错误。
**修复**: 统一符号约定——确认 OSDI 的 "RHS" vs "residual" 语义。

### H9 — KLU symbolic factorization 仅按 (n, nnz) 复用
**文件**: `src/assembly/klu_solver.cpp:128`
**问题**: `sym_` 复用条件是 `cached_n_ == n && cached_nnz_ == nnz`——仅检查维度和非零数，不检查实际 sparsity pattern。结构不同但同 size 的矩阵会错误复用。
**影响**: 若 KluSolver 被复用（如跨 Newton 迭代），不同 sparsity 的矩阵会用错误的 elimination tree。
**修复**: 改为 pattern hash 或强制每次重建（当前每次新建 solver，未触发）。

### H10 — Stamp zeroCommitted 不清 data_ map
**文件**: `src/assembly/matrix.hpp:68-72`
**问题**: `zeroCommitted()` 只清 `values_`（CSR 值数组），不清 `data_`（构建期 map）。committed 后 `data_` 残留旧值。若 `finalized_` 被翻回 false，`get()` 会读 stale data_。
**影响**: 潜在数据残留——当前不触发（committed 后不读 data_），但为维护隐患。
**修复**: `commitPattern()` 时 `data_.clear()`。

---

## 中严重度问题

### M1 — DC OP eval cache 跨 gmin 步返回 stale Jacobian
**文件**: `src/solver/dc_op.cpp` + `src/model/osdi_model.cpp:372-436`
**问题**: gmin 步之间不调 `resetLimiting()`，V3-L1 bypass cache 可能跨 gmin 步返回 stale Jacobian（f 重新算但 jac 用旧的）。
**修复**: gmin 步间 invalidate eval cache。

### M2 — HB 收敛仅检查 ‖F‖ 无 ‖dx‖ 检查
**文件**: `src/solver/hb_nonlinear.cpp:495`
**问题**: `fNorm < reltol * f0Norm + abstol`——若 f0Norm 很大（冷启动），reltol·f0Norm 是宽松阈值，可能 ‖dx‖ 仍大时声明收敛。
**修复**: 增加 `‖dx‖ < reltol·‖X‖` 检查。

### M3 — HB Jacobian (k=0, m≥1) block 可能缺 2× 因子
**文件**: `src/assembly/hb_jacobian.cpp:190-193`
**问题**: `(k≥1, m=0)` block 用 `2.0 * gp.real()`，但 `(k=0, m≥1)` block 不乘 2——不对称。对实信号 g(t)，两者应对称。
**修复**: 验证并补充 2× 因子。

### M4 — Stamp commitPattern() 在 finalized_=false 时静默 no-op
**文件**: `src/assembly/matrix.hpp:65`
**问题**: `patternCommitted_ = finalized_`——若未 finalize，commit 静默失败，无断言。
**修复**: 加 assert 或返回 bool。

### M5 — Stamp ptrFor 指针在 resize/finalize 后悬空
**文件**: `src/assembly/matrix.hpp:67`
**问题**: `ptrFor` 返回 `&values_[k]`。`finalize()`/`resize()` 重建 values_ vector，指针失效。当前靠调用顺序保证安全，无机制检测。
**修复**: `boundG_` 检查已部分缓解；考虑加 "pointers outstanding" 标志。

### M6 — Device eval L1 bypass 用绝对容差
**文件**: `src/model/osdi_model.cpp:385, 453`
**问题**: `bypassTol_` 是绝对值（1e-9），近零电压时相对变化可能很大但 < 1e-9 → 误 bypass。multi-rate 的 `mrCheckVoltages` 用相对容差，L1 不用——不一致。
**修复**: L1 bypass 也用相对容差 `bypassTol_ * max(|v|, 1.0)`。

### M7 — evalTransientResidOnly 不清 cache
**文件**: `src/model/osdi_model.cpp:508-533`
**问题**: `evalTransientResidOnly` 推进 `next_state` 但不清 `evalCached_`——后续 bypass 可能用 stale cache。
**修复**: 调 `invalidateEvalCache()`。

---

## 低严重度问题

### L1 — KLU move 构造/赋值丢失 bench 计时器
**文件**: `src/assembly/klu_solver.cpp:46-73`
**问题**: move 操作不转移 `factorMs_`/`solveMs_`。

### L2 — KLU solveMs_ mutable 导致线程安全隐患
**文件**: `src/assembly/klu_solver.hpp:71`
**问题**: `const` solve 方法修改 `mutable` 成员——多线程共享时有数据竞争。

### L3 — Stamp addCommitted 不检查 j 越界
**文件**: `src/assembly/matrix.hpp:74-75`
**问题**: 只检查 `i >= n_`，不检查 `j >= n_`——越界 j 静默丢弃。

### L4 — Device eval mrCheckVoltages scale=1.0V 对低压节点不合适
**文件**: `src/model/osdi_model.hpp:87`
**问题**: `max(|v|, 1.0)` 对 10mV 信号路径过宽。

### L5 — mrAdvance auto-tune 阈值注释与逻辑不符
**文件**: `src/model/osdi_model.hpp:108`
**问题**: 注释说"超半数步"，但 `(K+1)/2` 对 K=16 允许恰好半数触发回退。

### L6 — evalTransientResidOnly 是死代码
**文件**: `src/model/osdi_model.cpp:508`
**问题**: 声明并实现但从未被 assembler 调用。

### L7 — NaN/Inf 检查不覆盖 state 向量
**文件**: `src/model/osdi/osdi_client.cpp:320-321`
**问题**: 只检查 `prevSolve`，不检查 `prevState_`/`nextState_`。

### L8 — Stamp V3 fast path 零测试覆盖
**问题**: `commitPattern`/`zeroCommitted`/`ptrFor`/`bindStampPtrs` 无任何单元测试。

### L9 — AC 电流源用 DC 值作 AC 幅度
**文件**: `src/solver/ac_analysis.cpp:123`
**问题**: `CurrentSource` 的 AC 幅度被忽略，用 DC 值替代。

### L10 — DC OP branchIndex fallback 返回有效 branch index
**文件**: `src/assembly/transient_assembly.cpp:54`
**问题**: `return numNodes` 是有效 branch index——非 VS 器件误入会踩第一个 VS 的行。当前不可达。

---

## 修复优先级

1. **H1-H3** (DC OP 收敛性) — 直接影响仿真正确性
2. **H4** (HB Q 清零) — 含电容器件的 HB 结果错误
3. **H7-H8** (eval alpha/符号) — Trapezoidal 精度和符号约定
4. **H5-H6** (AC 分析) — 非线性器件跳过 + 除零
5. **H9-H10** (KLU/Stamp) — 潜在但未触发
6. **M1-M7** — 中等风险
7. **L1-L10** — 低风险/维护性
