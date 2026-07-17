# UMFPACK 集成状态

日期：2026-07-17。作为经验性求解器选择（empirical solver selection）的第一个外部求解器插件。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| UMFPACK wrapper 代码 | ✅ 完成（`src/assembly/umfpack_solver.{hpp,cpp}`，`LinearSolver` 子类，symbolic/numeric 分离 + 结构指纹复用） |
| CMake 集成 | ✅ 完成（`option(RFSIM_USE_UMFPACK OFF)`，UMFPACK 子项目启用 + BLAS 链接 + 宏门控） |
| Factory + 候选注册 | ✅ 完成（`.options method=umfpack` + `EmpiricalSolverSelector` 候选池自动注册） |
| 编译验证 | ✅ 通过（`-DRFSIM_USE_UMFPACK=ON -DRFSIM_BLAS_LIB=...`，`rfsim_core.lib` 13.8MB 含 UMFPACK_static 全部源） |
| **运行时验证** | **受阻**：MSVC host + mingw OpenBLAS DLL = CRT 不匹配（KI-2 同类问题），需 MSVC 兼容 BLAS |
| 默认构建（UMFPACK-OFF） | ✅ 154/0/51 PASS（无影响，代码在 `#ifdef RFSIM_USE_UMFPACK` 守卫内） |

## 代码交付（已完成，可编译）

### 新增文件

| 文件 | 作用 |
| --- | --- |
| `src/assembly/umfpack_solver.{hpp,cpp}` | `UmfpackSolver : public LinearSolver`：UMFPACK di（double,int32）API；CSR→CSC；`umfpack_di_symbolic`/`numeric`/`solve`；结构指纹复用 Symbolic（同 KluSolver 模式） |
| `_build_umfpack.ps1` + `_genblas.bat` + `_build_umfpack2.bat` | 从 mingw OpenBLAS DLL 生成 MSVC import lib 的辅助脚本（带 no-underscore BLAS 别名） |

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `cmake/SuiteSparseKLU.cmake` | UMFPACK 子项目门控（`RFSIM_USE_UMFPACK`）；`UMFPACK_USE_CHOLMOD=OFF`；BLAS 占位/真实切换（`RFSIM_BLAS_LIB`）；`SuiteSparse::UMFPACK` 目标别名；MSVC 降噪 |
| `CMakeLists.txt` | `option(RFSIM_USE_UMFPACK OFF)` |
| `src/CMakeLists.txt` | `umfpack_solver.cpp` 门控编译；UMFPACK + BLAS PUBLIC 链接；`RFSIM_USE_UMFPACK` 宏 |
| `src/assembly/linear_solver_factory.{hpp,cpp}` | `SolverMethod::Umfpack` 枚举；`parseSolverMethod`/`solverMethodName`/factory switch 处理 `umfpack`/`umf` |
| `src/assembly/solver_benchmark.cpp` | `RFSIM_USE_UMFPACK` 时自动注册 `umfpack` 到经验选择候选池 |
| `tests/test_solver_selection.cpp` | 门控的 UMFPACK 单元测试（`RFSIM_USE_UMFPACK` 时启用） |

## 运行时受阻：MSVC/mingw CRT 不匹配

### 问题

本项目用 **MSVC（cl.exe /MD UCRT）** 构建（为与 `bsim4.dll` 的 UCRT 对齐，见 README KI-2）。UMFPACK 需 BLAS-3（dgemm/dgemv/dtrsm）。环境中唯一的 BLAS 是 **mingw64 的 `libopenblas.dll`**（msvcrt CRT）。

链接成功（生成 `openblas.lib` import lib + no-underscore 别名），但运行时崩溃：MSVC host 进程加载 mingw OpenBLAS DLL → 跨 CRT 堆（UCRT vs msvcrt）→ 堆腐败/崩溃。这与 KI-2（bsim4.dll）是同类问题。

### 解决方案（需用户环境提供）

UMFPACK 运行时验证需 **MSVC 兼容的 BLAS**：
- **vcpkg OpenBLAS**：`vcpkg install openblas:x64-windows`，提供 MSVC 兼容的 `openblas.lib` + DLL。
- **Intel MKL**：`mkl_rt.lib`（闭源但 MSVC 兼容，性能最优）。
- **MSVC 自编 OpenBLAS**：从源码用 MSVC 编译（复杂）。
- **conda OpenBLAS**：`conda install openblas`，Library/lib 下的 MSVC 兼容库。

### 构建命令（MSVC 兼容 BLAS 就绪后）

```bat
:: 1. 配置（提供 RFSIM_BLAS_LIB 指向 MSVC 兼容 BLAS import lib）
cmake -S . -B build -G Ninja ^
    -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL ^
    -DRFSIM_USE_KLU=ON ^
    -DRFSIM_USE_UMFPACK=ON ^
    -DRFSIM_BLAS_LIB="C:/path/to/openblas.lib"

:: 2. 构建（UMFPACK_static + BLAS 链接进 rfsim_core）
cmake --build build --target rfsim_core
cmake --build build --target rfsim_tests

:: 3. 运行（BLAS DLL 需在 PATH 或 exe 旁）
build\bin\rfsim_tests.exe --gtest_filter=LinearSolverSelect.Umfpack*
```

## 为什么仍交付代码

1. **代码完整且可编译**：wrapper、CMake、factory、注册全部就绪，`#ifdef RFSIM_USE_UMFPACK` 守卫，默认 OFF 不影响任何现有构建。
2. **MSVC 兼容 BLAS 是环境问题，非代码问题**：用户环境装了 vcpkg/MKL 即可激活。
3. **经验选择机制已验证**：`EmpiricalSolverSelector` 的候选池/基准/缓存机制（9 测试 PASS）——UMFPACK 只是多一个候选，机制不变。
4. **后续外部求解器（PARDISO/MUMPS/SuperLU）模板**：UMFPACK wrapper 是插件式集成的参考实现。

## 当前状态总结

- 默认构建（UMFPACK-OFF）：**154/0/51 PASS**（无影响）。
- UMFPACK-ON：编译链接通过，运行时待 MSVC 兼容 BLAS。
- 经验选择机制：完整可用（KLU/DenseLu/BiCGSTAB 候选；UMFPACK 在 MSVC-BLAS 就绪后自动加入）。
- `.options method=umfpack`：解析就绪（UMFPACK-ON 时生效）。

## 后续

- 用户提供 MSVC 兼容 BLAS（vcpkg/MKL）后，UMFPACK 即可运行时验证 + 进入经验选择候选池。
- PARDISO（MKL）/MUMPS（Fortran）/SuperLU 插件：按 UMFPACK 模板接入。
