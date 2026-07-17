# 经验性求解器选择（empirical solver selection）状态

日期：2026-07-17。用户需求升级：不只是静态规则选求解器，而是对候选求解器实际跑 N 次基准，选最快的。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **179 tests, 154 PASSED / 0 FAILED / 51 SKIPPED**（D 后 145 + 新增 9 个 EmpiricalSolverSelect 测试） |
| 经验选择机制 | ✅ `EmpiricalSolverSelector`：候选池 + N 次基准 + 指纹缓存 + 阈值触发 |
| 插件式架构 | ✅ `registerCandidate`/`setUnavailable` 动态注册外部求解器 |
| 触发策略 | dim > 10万 才基准（用户决策）；小矩阵默认 KLU；`RFSIM_EMPIRICAL_SOLVER=1` 强制启用 |
| UMFPACK/PARDISO/MUMPS/SuperLU 集成 | **推迟**（插件接口已就绪，外部求解器按需接入） |

## 落地清单

### 新增文件

| 文件 | 作用 |
| --- | --- |
| `src/assembly/solver_benchmark.{hpp,cpp}` | `EmpiricalSolverSelector` 单例：候选池 + `benchmark`(N 次 factorize+solve 中位数) + `select`(指纹缓存最优) + `matrixFingerprint`(FNV-1a over 结构) + `enabledForDim`(阈值/环境变量) |
| `tests/test_solver_benchmark.cpp` | 9 测试（候选注册/基准排序/指纹/小矩阵跳过/强制触发/缓存/失效/插件注册） |

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/assembly/linear_solver_factory.{hpp,cpp}` | `makeAutoSolver(A)` 重载：dim>阈值时先 `EmpiricalSolverSelector::select`，否则静态规则 |
| `src/solver/dc_op.cpp` / `time_stepper.cpp` / `shooting.cpp` | method==Auto 时用 `makeAutoSolver(A)`（触发经验选择），否则 `makeLinearSolver(method, hints)` |
| `src/CMakeLists.txt` + `tests/CMakeLists.txt` | 注册 solver_benchmark 源/测试 |

## 关键设计决策

### 经验选择触发策略（用户决策）

```
dim > 100000  →  对所有候选求解器各跑 10 次 factorize+solve，取中位数，选最快
dim ≤ 100000  →  默认 KLU（静态规则，不基准——开销不值得）
RFSIM_EMPIRICAL_SOLVER=1  →  强制启用（任意 dim 都基准，用于调试/对比）
```

用户明确：小稀疏矩阵默认 KLU；仅大规模（>10万）才值得基准选择的开销。

### 候选池与插件式架构

`EmpiricalSolverSelector` 维护候选池 `vector<SolverCandidate{name, factory, available}>`：
- **默认注册**（构造时）：KLU（BTF+AMD）、DenseLu、BiCGSTAB+ILU(0)。
- **外部求解器插件**：`registerCandidate(name, factory)` 动态注册。UMFPACK/PARDISO/MUMPS/SuperLU 各自的 wrapper 初始化时调用此接口注入——未注入则不在候选池。
- **运行时不可用**：`setUnavailable(name)` 标记（如 UMFPACK 编译但运行时 DLL 加载失败）。

这使外部求解器集成是**增量**的：每接入一个只需写 wrapper + 注册，不影响核心。

### 基准与缓存

- **benchmark(A, runs)**：对每个可用候选构造实例，跑 `runs` 次 factorize+solve，用 `SteadyTimer` 测耗时，取中位数。按 totalMs 升序排序返回。
- **指纹缓存**：`matrixFingerprint` = FNV-1a over (dim + rowPtr + colIdx)。同结构矩阵同指纹（值不影响）。`select` 结果按指纹缓存，本会话内同结构矩阵直接用最优求解器，不重复基准——开销摊到首步。
- **失效**：`invalidate(A)` / `clearCache()` 强制重基准。

### 调用方集成

dc_op / time_stepper / shooting 的求解器构造改为：
```cpp
solver = (method == SolverMethod::Auto) ? makeAutoSolver(A)   // 大矩阵走经验选择
                                        : makeLinearSolver(method, hints);  // 显式方法/小矩阵
```
显式 `.options method=klu|dense|bicgstab` 仍走静态构造（不基准）；`.options method=auto`（默认）在大矩阵时触发经验选择。

## UMFPACK / PARDISO / MUMPS / SuperLU 集成（推迟）

插件接口已就绪。外部求解器接入步骤（每个）：
1. 写 `LinearSolver` 子类 wrapper（factorize/solve/dim/name）。
2. CMake 可选编译（`option(RFSIM_USE_UMFPACK ON)` 等）。
3. wrapper 初始化时 `EmpiricalSolverSelector::instance().registerCandidate(name, factory)`。

**UMFPACK**（SuiteSparse 自带，多列前沿，电路业界常用）：需 `cmake/SuiteSparseKLU.cmake` 启用 UMFPACK 子项目 + `UMFPACK_USE_CHOLMOD=OFF`（避 BLAS）+ BLAS 占位（现有 KLU-only 构建已用 `BLA_VENDOR="Generic"` 占位，可复用）。

**PARDISO**（Intel MKL，闭源）：需 MKL 安装 + runtime 检测。

**MUMPS**（Fortran）：需 Fortran 编译器。

**SuperLU**：SuiteSparse 中的版本是 SuperLU-MT demo 源，需单独取上游。

这些是独立集成工作（各需构建调试 + 平台可用性验证），本轮交付**机制 + 接口**，外部求解器按需接入。

## 交付标准核对

- [x] 默认 ctest **154/0/51** PASS（无退步）
- [x] `EmpiricalSolverSelector` 经验基准 + 指纹缓存 + 阈值触发
- [x] 插件式 `registerCandidate`/`setUnavailable`
- [x] dim > 10万 触发基准，小矩阵默认 KLU，`RFSIM_EMPIRICAL_SOLVER=1` 强制
- [x] dc_op/time_stepper/shooting Auto 路径接入
- [x] EmpiricalSolverSelect 单元测试 9/9 PASS
- [~] UMFPACK/PARDISO/MUMPS/SuperLU 插件（接口就绪，集成推迟）

## 全部工作总览（含本轮）

| 项 | 需求 | 状态 |
| --- | --- | --- |
| A1 求解器抽象+自动选择 | 6 | ✅ |
| A2 HB/Shooting 收敛加固 | 7 | ✅ |
| B1 器件 bypass 强化 | 1 | ✅ |
| B2 multi-rate 增强 | 3 | ✅ |
| C2 表达式/参数化增强 | 5 | ✅ |
| C1 `.lib` corner 选择 | 2 | ✅（基础）；level=54 映射推迟 |
| D 波形输出 + waveview | 4 | ✅ |
| **经验性求解器选择（升级）** | 6 | ✅ 机制；外部求解器插件推迟 |

回归 **154/0/51**，累计新增 43 个单元测试，全程无退步。

## 后续

- **UMFPACK 集成**：改 CMake 启用 UMFPACK 子项目（UMFPACK_USE_CHOLMOD=OFF）+ 写 UmfpackSolver wrapper + 注册。
- **PARDISO/MUMPS/SuperLU 插件**：按需接入。
- **C1 level=54 映射** / **异步 multi-rate 完全版** / **二进制 rawfile**（其他推迟项）。
