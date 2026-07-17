# Phase A1 完成状态 — 求解器抽象 + 符号复用 + 自动选择 + 新迭代求解器

日期：2026-07-17。对应总体增强方案（7 需求）Phase A 的 A1 子项（需求 6）。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **146 tests, 121 PASSED / 0 FAILED / 51 SKIPPED**（基线 111/0/51 + 新增 10 个 LinearSolverSelect 测试） |
| 新增测试 | `tests/test_solver_selection.cpp` — 10/10 PASS |
| KLU-OFF 构建 | ✅ 可行（`-DRFSIM_USE_KLU=OFF`，Auto 回退 DenseLu） |
| 性能改进 | KLU 符号分解复用激活（dc_op / shooting / time_stepper 求解器提到 Newton 循环外） |
| 关键 bug 修复 | KLU `num_`/`sym_` 结构变化时不同步释放 → 堆腐败（0xC0000374），根治 |

## 落地清单

### 新增文件

| 文件 | 作用 |
| --- | --- |
| `src/assembly/linear_solver.hpp` | `LinearSolver` 抽象基类（factorize/solve/dim + supportsRefactor/name） |
| `src/assembly/linear_solver_factory.{hpp,cpp}` | `makeLinearSolver(SolverMethod, SolverHints)` 工厂 + Auto 选择 + `parseSolverMethod` |
| `src/assembly/iterative_solver.{hpp,cpp}` | `BiCgStabSolver`：BiCGSTAB + ILU(0) 预条件迭代求解器 |
| `tests/test_solver_selection.cpp` | 10 个单元测试（接口/工厂/Auto/解析/refactor 复用/结构变化） |

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/assembly/klu_solver.{hpp,cpp}` | `KluSolver` 继承 `LinearSolver`；新增结构指纹 `prevAp_/prevAi_` 安全复用 `sym_`；**结构变化时同步释放 `num_`（堆腐败修复）**；移动语义迁移新成员 |
| `src/assembly/lu_solver.hpp` | `LuSolver` 继承 `LinearSolver`（原死代码现激活） |
| `src/solver/dc_op.{hpp,cpp}` | Newton 循环外持有求解器（复用 KLU 符号分解）；`DcOpOptions.solver` 字段；polish 步也走工厂 |
| `src/solver/time_stepper.{hpp,cpp}` | 时间步循环外持有求解器（跨步 + 跨内层 Newton 复用）；`TimeStepperOptions.solver` |
| `src/solver/shooting.{hpp,cpp}` | `integrateOnePeriod` 接收持久 `innerSolver`（跨 nominal/FD/trial 路径复用）；外层 monodromy 用持久 `outerSolver`；`ShootingOptions.solver` |
| `src/solver/hb_nonlinear.hpp` | `HbNlOptions.solver` + GMRES 可配参数（gmresRestart/MaxIter/Reltol）预留 |
| `src/solver/ac_analysis.cpp` | `#ifdef RFSIM_USE_KLU` 守卫；OFF 时返回 `ok=false` 诊断（KLU 可选化） |
| `src/cli/main.cpp` | `.options method=` 解析 → `SolverMethod` 注入各分析 opts（.op/.hb/.pss） |
| `CMakeLists.txt` + `src/CMakeLists.txt` + `cmake/SuiteSparseKLU.cmake` | `option(RFSIM_USE_KLU ON)`；KLU 源/链接/宏门控 |

## 关键设计决策

### 1. 求解器抽象接口（`LinearSolver`）

三方法接口 `factorize(SparseMatrix) + solve(Vector,Vector) + dim()`，与现有 `KluSolver`/`LuSolver` 字节级对齐——两者仅需 `override`。`KluZSolver`（复数 + in-place + raw CSC）API 不兼容，暂不纳入（AC 分析仍直用），留待未来 `ComplexLinearSolver`。

### 2. Auto 选择策略

```
dim < 64 且 density > 0.30  →  DenseLu（小稠密，常数因子优）
否则                         →  Klu（稀疏不对称，电路 MNA 最优）
无 KLU 编译时                 →  Auto 始终回退 DenseLu
显式 BiCgStab                 →  迭代求解器（ILU(0) 预条件）
```

### 3. 性能核心：求解器提到 Newton 循环外

原代码 `KluSolver solver;` 在 Newton/时间步循环内构造 → 类内已有的 `analyzed_`/`klu_refactor` 复用路径完全失效（死代码）。改为循环外持有 `std::unique_ptr<LinearSolver>`，连续 `factorize` 同结构矩阵时复用 `sym_` 只做数值 `klu_refactor`，省 `klu_analyze`（AMD/BTF 排序）开销。

### 4. 关键 bug 修复：KLU 结构变化的堆腐败

**症状**：`OsdiMatrix.BsimcmgHbNlCommonSource` 与 `Shooting.Bsim4LcTank1GHz` 在 hoisting 后崩溃 `0xC0000374 (STATUS_HEAP_CORRUPTION)`。

**根因**：连续 `factorize` 间矩阵结构变化时（如 OSDI 内部节点折叠、gmin 步改变对角），原 refactor 逻辑只 `klu_free_symbolic(&sym_)` 重新 analyze，但保留旧 `num_`（数值因子绑定在旧 `sym_` 的内存布局）。后续 `klu_factor`/`klu_refactor` 用不匹配的 `sym_`/`num_` 组合 → 越界写 → 堆腐败。

**修复**：
- 结构指纹：`prevAp_`/`prevAi_`（完整 `memcmp`，O(nnz)）判断结构是否变化。
- 结构变化时**同时** `klu_free_numeric(&num_)` 与 `klu_free_symbolic(&sym_)`，强制下节重新 `klu_factor`。
- 回归保护：`LinearSolverSelect.KluReanalyzesOnStructureChange`（n=10→20 切换不崩溃）。

### 5. KLU 可选化

`option(RFSIM_USE_KLU ON)`（默认 ON，保持现有构建）。OFF 时：KLU cmake 不 include，`klu_solver.cpp`/`klu_z_solver.cpp` 不编译，`rfsim_core` 不定义 `RFSIM_USE_KLU`，工厂 Auto/Klu 都回退 DenseLu，AC 分析返回 `ok=false`。已验证 OFF 构建通过。

## 交付标准核对

- [x] 默认 ctest **121/0/51** PASS（基线 111 + 新增 10，不退步）
- [x] `.options method=klu|dense|bicgstab|auto` 可用，Auto 选择正确
- [x] KLU-OFF 构建可行（`-DRFSIM_USE_KLU=OFF`）
- [x] 3 个具体求解器 + 工厂 + Auto 全部单测覆盖
- [x] KLU refactor 复用 + 结构变化安全重建回归保护
- [x] KLU 堆腐败根治（bsimcmg / LcTank 恢复 PASS）
- [~] KLU 复用 wall 下降：CascodeChain5=111ms / SelfBiasedCascodeStack5=142ms（基线未单独计时，需 RFSIM_BENCH_JSON 对比；正确性已验证）

## 后续（Phase A2 — 需求 7：HB/Shooting 收敛加固）

A1 已为 A2 铺路：
- `LinearSolver` 抽象 + refactor 复用 → A2 的 LM/TR 阻尼器可统一用 `makeLinearSolver`。
- `HbNlOptions` 的 GMRES 可配参数 → A2-5 预条件改进。
- KLU 结构变化安全重建 → A2 的 HB FFT 过采样改采样数不会触发堆腐败。

A2 待办：HB 卷积 FFT 过采样（N=2(NH+1)→4(NH+1)）、Shooting 外层 reltol+同伦、HB→Shooting 回退加固、Trust-Region/LM 阻尼器、HB 预条件 ILU。
