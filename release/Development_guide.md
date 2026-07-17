# rfsim 开发指南

本文档面向 rfsim 的二次开发者，涵盖架构、数值核心、OSDI 集成、S 参数实现、
扩展指南、构建系统、以及 **OpenVAF Linux 支持方案**。

---

## 目录

1. [项目架构](#1-项目架构)
2. [数值核心](#2-数值核心)
3. [OSDI 集成](#3-osdi-集成)
4. [S 参数实现](#4-s-参数实现)
5. [新增器件模型](#5-新增器件模型)
6. [新增分析卡](#6-新增分析卡)
7. [测试体系](#7-测试体系)
8. [构建系统](#8-构建系统)
9. [OpenVAF Linux 支持方案](#openvaf-linux-支持方案)
10. [调试](#10-调试)
11. [已知问题与回归基线](#11-已知问题与回归基线)

---

## 1. 项目架构

rfsim 采用经典 SPICE 流水线分层，每层一个子目录：

```
src/
  parser/    词法 → 语法 → AST → 表达式求值 → 扁平化(flatten)
     ↓ Netlist
  circuit/   Circuit + NodeTable + ControlCard 识别
     ↓ Circuit (FlatDevice / FlatModel / controls)
  model/     DeviceModel 基类 + 内建器件(R/L/C/V/I) + OsdiModel + SParamDevice + DeviceFactory
     ↓ vector<unique_ptr<DeviceModel>>
  assembly/  MNA stamp + SparseMatrix + KLU/KLU-Z 求解器 + HB 雅可比块 + 瞬态装配
     ↓ (G, F) 线性化系统
  solver/    dc_op / dc_sweep / ac_analysis / hb_solver / hb_nonlinear / shooting / time_stepper
     ↓ 结果 (DcOpResult / AcResult / HbResult / ShootingResult / TimeDomainResult)
  output/    HSpice 风格格式化
  sparam/    Touchstone .sNp 解析 + Vector Fitting
  cli/       main.cpp — 命令行入口，接线各分析
```

### 关键数据流

```
源码文本 ──parseNetlist──▶ Netlist(AST) ──flatten──▶ Circuit(扁平)
  └─ Diagnostics (错误恢复型，收集后继续解析)
Circuit ──buildDeviceModels──▶ FactoryResult{devices, totalNodes}
  └─ DeviceFactory 按 firstLetter 分发到 Resistor/Capacitor/.../OsdiModel/SParamDevice
FactoryResult ──solveDcOp/solveAc/solveShooting/...──▶ 结果
```

### 核心类型（`src/rfsim.hpp`）

```cpp
using Complex = std::complex<double>;
using NodeId  = uint32_t;        // 0=地，1..N 为非地节点
struct Diagnostics { vector<Error> errors, warnings; };  // 不抛异常，累积诊断
```

---

## 2. 数值核心

### 2.1 稀疏直接求解器：KLU

- **用途**：DC / 瞬态 / Shooting 的 Newton 内层与外层 monodromy 雅可比都是稀疏不对称矩阵，用 KLU（BTF + AMD + 部分选主元）拿到接近最优的稀疏直接因子化复杂度。
- **集成**：`cmake/SuiteSparseKLU.cmake` 通过 FetchContent 拉取 SuiteSparse（仅启用 `suitesparse_config + amd + colamd + btf + klu`，关闭 Fortran/OpenMP/CUDA/CHOLMOD，纯 C 无外部 BLAS）。
- **复数版**：`assembly/klu_z_solver.{hpp,cpp}` 用于 AC 分析的复数线性化系统。
- **封装**：`assembly/klu_solver.hpp` 暴露 `factorize(SparseMatrix)` + `solve(b, x)`。

### 2.2 HB 求解器：GMRES + 预条件子

- HB 雅可比块结构非 KLU 友好（频域耦合稠密块），走 `assembly/gmres.{hpp,cpp}` 的 GMRES + Jacobi/块预条件子 + Krylov 子空间复用。
- 弱非线性快路径 `solver/hb_nonlinear.cpp`（AC warm-start + Armijo 线搜索）；强非线性自动回退 Shooting-PSS。

### 2.3 DC 收敛同伦（`solver/dc_op.cpp`）

DC OP 收敛靠三段式策略，应对 hostile 工作点（BSIM4 大摆幅、浮空节点）：

1. **log-spaced gmin 调度**：`GminOptions{gminStart=1e-2, gmin=1e-12, steps=10}`，逐步降低并联电导。
2. **源步进**：`vsScale = ε..1` linear schedule，逐步恢复源到全幅。
3. **中轨种子传播**：VS 锚定 → 电阻图 BFS（`V_neigh = 0.5·V_anchor`）→ 非线性器件均值传播，给 Newton 一个合理初值。
4. **gmin floor accept**：到达 gmin 下限仍未收敛时返回"最佳已收敛"工作点（`floorAcceptOuter`）。
5. **限幅**：OSDI `CALC_RESIST_LIM_RHS | ENABLE_LIM` 全程启用。

### 2.4 Shooting-Newton（`solver/shooting.cpp`）

- 时间步进 Backward Euler / 梯形积分一个周期 → 外层 Newton 迭代 monodromy 方程。
- 内层每步 Newton + dvmax 限幅 + Armijo 回溯线搜索。
- 末尾 DFT 提取谐波（`shootingToHarmonics`）。

### 2.5 Pattern 固化（V3 优化）

- `SparseMatrix::commitPattern()` 首次建 pattern 后固化，后续频率点/Newton 迭代走 `zeroCommitted` + `addCommitted` 直接写 CSR values_ 指针（O(1)）。
- 器件通过 `bindStampPtrs` 预存自己的 jacobian entry 指针，`stampValuesViaPtrs` 直写。

---

## 3. OSDI 集成

### 3.1 OSDI 0.3 / 0.4 双 ABI 兼容

`src/model/osdi/osdi.h` 是 host 端头文件，**前向兼容 0.3 与 0.4**：
- OSDI 0.4 在 `OsdiDescriptor` 末尾追加字段，但前半段与 0.3 同 offset（offsetof 逐项验证，sizeof 两边一致）。
- dll 自报 `OSDI_DESCRIPTOR_SIZE` 的尾部 padding 差异 host 不访问。
- 预编译 dll 状态：
  - `bsim4` / `diode` / `ekv` / `nmos_sh` / `simple_diode`：**0.4**（OpenVAF-Reloaded 重编）
  - `bsim4soi` / `bsimcmg` / `bsimsoi`：**0.3**（无 `.va` 源，预编译产物，存于 `models/orig_dlls_v0_3/`）

### 3.2 跨 CRT 对齐（Windows 关键）

OpenVAF 编译的 `bsim4.dll` 链 **UCRT**（ucrtbase + VCRUNTIME140，即 MSVC `/MD`）。
host 必须也用 MSVC `/MD`，与 dll 共享同一 ucrtbase 堆。若 host 用 MinGW（msvcrt.dll，
NT4 时代 CRT），两套独立堆 → `osdi_log` 的 msg free 等场景触发跨 CRT 堆腐败。

**修复**：`CMakeLists.txt` MSVC 分支强制 `CMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL`，
`build.bat` 重写为 MSVC 工具链。`osdi_library.cpp` 已删除 msg leak workaround，恢复
OSDI spec 规定的 `std::free(msg)`。

### 3.3 isReadableCString 守护

OSDI spec 要求仿真器对 `param_opvar[]` 表尾做 NULL 检查。0.4 dll 在表尾接续
非 NULL 但非指针的小整数（`0x500000004`），host 直接 deref 触发 SEGV。

`src/model/osdi/osdi_client.cpp` 新增 `isReadableCString()`：双重检查 `p.name`（别名数组
指针）和 `p.name[0]`（第一个别名字符串）都在合法用户态可读范围内才 deref。

```cpp
static bool isReadableCString(const char* p) {
    if (!p) return false;
    auto addr = reinterpret_cast<uintptr_t>(p);
    if (addr < 0x10000) return false;        // 排除小整数伪装指针
    if (addr > 0x7FFFFFFFFFFFull) return false;
#ifdef _WIN32
    MEMORY_BASIC_INFORMATION mbi;
    if (VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return false;
    if (mbi.State != MEM_COMMIT) return false;
    if (mbi.Protect & PAGE_NOACCESS) return false;
    if (mbi.Protect & PAGE_GUARD) return false;
    return true;
#else
    return true;  // POSIX 路径保守允许
#endif
}
```

### 3.4 跨平台库加载

`src/model/osdi/osdi_library.cpp` 跨平台：
```cpp
#ifdef _WIN32
  LibHandle openLib(const char* path) { return LoadLibraryA(path); }
  void* sym(LibHandle h, const char* name) { return (void*)GetProcAddress(h, name); }
#else
  LibHandle openLib(const char* path) { return dlopen(path, RTLD_NOW | RTLD_LOCAL); }
  void* sym(LibHandle h, const char* name) { return dlsym(h, name); }
#endif
```

`src/model/device_factory.cpp` 候选路径按平台生成：
```cpp
#ifdef _WIN32
  candidates.push_back(env.libSearchDir + "\\" + modelName + ".dll");
#else
  candidates.push_back(env.libSearchDir + "/lib" + modelName + ".so");
#endif
```

### 3.5 内部节点折叠

OSDI `collapsed[i]==1` 的内部节点（如 BSIM4 在 RS/RD=0 时的 SP/DP）直接
alias-remap 到外部节点，残差 gather 去重 + 雅可比 4-entry 求和保证合并梯度数学正确。

**边界守护**（KI-3 根治）：`dc_op.cpp` 的 `assemble` 对 `NodeId > numNodes` 的
内部节点跳过外部 MNA 残差/stamp（OSDI spec：内部隐式节点 KCL 由 dll 自洽求解）：

```cpp
for (uint32_t k = 0; k < nNodes && k < nds.size() && k < dc.f.size(); ++k) {
    NodeId nk = nds[k];
    if (nk == 0 || nk > numNodes) continue;   // 内部节点不进外部 MNA
    F[nk - 1] += dc.f[k];
}
```

---

## 4. S 参数实现

### 4.1 Touchstone 解析（`src/sparam/touchstone.cpp`）

- 支持 `.s1p` / `.s2p` / `.sNp`，格式 RI / MA / DB，频率单位 Hz/kHz/MHz/GHz。
- 2 端口 Touchstone 文件顺序 `S11 S21 S12 S22` 重排为矩阵行优先 `S11 S12 S21 S22`。
- `sToY`：`Y = (1/Z0)·(I-S)^{-1}·(I+S)`，Gauss-Jordan 复数消元。
- `interpolateS`：频率二分查找 + 线性插值。

### 4.2 SParamDevice（`src/model/sparam_device.cpp`）

`K` 器件，`is_linear()=true`：

| 分析 | 实现 |
|------|------|
| AC | `admittanceMatrix(omega)` → 插值 S→Y → stamp N×N 复数 Y |
| DC | `dcAdmittanceMatrix()` → Y(ω→0) 外推（最低两频率点线性外推）→ 实部 stamp |
| 瞬态 | Vector Fitting companion model |

### 4.3 Vector Fitting（`src/sparam/vector_fit.cpp`）

两阶段 VF（Gustavsen 1999），拟合 `H(s) = Σ_k r_k/(s-p_k) + d + s·e`：

**阶段 1 — 极点重定位（迭代）**：
- 同伦方程 `σ(s)·H(s) = f(s)`，固定 `ẽ=1` 消去齐次不定性。
- 未知数 `[r̃_k, d̃, r_k, d, e]`，最小二乘（A^H·A + Tikhonov 正则化，解秩亏）。
- 新极点 = `σ(s)` 的零点 = `σ·Π(s-p_k)` 多项式求根（Durand-Kerner）。
- 不稳定极点（Re>0）翻转到左半平面。

**阶段 2 — 最终留数求解**：
- 极点固定，直接最小二乘解留数。

**N×N 矩阵版**：`initVectorFitting()` 对 Y_00 拟合得公共极点 → `vectorFitFixedPoles()`
对所有 Y_ij 用固定极点解留数，保证 companion model 极点一致。

### 4.4 N×N BE companion model

VF 模型 `Y(s) = Σ_k R_k/(s-p_k) + D`（R_k 是 N×N 留数矩阵，D 是 N×N 常数矩阵）：

- 状态方程 `s·x_k = p_k·x_k + R_k·V`（x_k 是 N 维）
- Backward-Euler：`x_k[n] = (x_k[n-1] + dt·R_k·V) / (1-dt·p_k)`
- 等效电导 `G_eq = Σ_k R_k/(1-dt·p_k) + D`
- 历史电流 `I_hist = Σ_k x_k[n-1]/(1-dt·p_k)`
- `evalTransient` stamp `jac = Re(G_eq)`，`f = G_eq·V + I_hist`
- 复数极点对状态取实部合并存储（`state_` 为实数 vector）

**状态更新时机**：`evalTransient`（Newton 迭代中，只读不改状态），
`updateTransientState`（time_stepper 在 Newton 收敛后调用，推进状态）。

---

## 5. 新增器件模型

### 5.1 实现 DeviceModel 子类

参考 `src/model/builtin_devices.hpp` 的 `Resistor`：

```cpp
class MyDevice : public DeviceModel {
public:
    MyDevice(std::string name, NodeId n1, NodeId n2, double param);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;  // 预声明非零位置
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;  // DC: jac=导纳, f=电流
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }
    // 动态器件(C/L)还需重载:
    // void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    // bool hasTransientState() const override;
    // void updateTransientState(const TransientOpPoint& op) override;
private:
    std::string name_;
    std::vector<NodeId> nodes_;
};
```

### 5.2 在 DeviceFactory 注册

`src/model/device_factory.cpp` 的 `buildDevice` 按 `firstLetter` 分发。加一个分支：

```cpp
if (c == 'y') {  // 你的新器件字母
    // 解析参数，构造 MyDevice
    return std::make_unique<MyDevice>(fd.name, fd.nodes[0], fd.nodes[1], param);
}
```

### 5.3 在 Parser 注册首字母

`src/parser/parser.cpp` 的 `parseDevice`：若新器件是变长节点（如 S 参数 `K`），
设 `expectedNodes = 999` 让它收集到 `file=` 等命名参数前。

### 5.4 加源文件到 CMakeLists

`src/CMakeLists.txt` 的 `RFSIM_MODEL_SOURCES` 加 `model/my_device.cpp`。

### 5.5 加测试

`tests/test_my_device.cpp`，仿照 `test_model.cpp` / `test_sparam.cpp`：
直接构造 wrapper + `OperatingPoint` 调 `eval`，或 parse 网表文本走完整管线。
加入 `tests/CMakeLists.txt` 的 `RFSIM_TEST_SOURCES`。

---

## 6. 新增分析卡

1. **Parser 识别**：`src/circuit/circuit.cpp` 的 `isAnalysisCard` 加命令名。
2. **CLI 接线**：`src/cli/main.cpp` 检测 control card，调你的 solver。
3. **Solver 实现**：`src/solver/my_analysis.{hpp,cpp}`，返回结果结构体。
4. 加到 `src/CMakeLists.txt` 的 `RFSIM_SOLVER_SOURCES`。

---

## 7. 测试体系

### 7.1 GoogleTest 组织

- `tests/CMakeLists.txt` FetchContent 拉 GoogleTest v1.14.0，`gtest_discover_tests` 注册。
- 纯 `TEST(Suite, Case)`，无 fixture（部分 BSIM4 套件用 `TEST_F` 管理 OSDI 库生命周期）。
- `RFSIM_TEST_DATA_DIR` 宏指向 `tests/netlists`，测试用它定位网表 fixture。

### 7.2 HEAVY / FORCE_* 门控

大规模 / 多 finger / 收敛诊断用例默认 `GTEST_SKIP`，需环境变量打开：
- `RFSIM_FORCE_HEAVY=1`：N≥15 BSIM4 大摆幅用例
- `RFSIM_FORCE_C3BIS=1`：C3-bis 多 finger 收敛诊断

### 7.3 两种构造模式

1. **直接 wrapper**：`std::make_unique<Resistor>("r1", 1, 2, 1000.0)` → `solveAc/solveDcOp`（如 `test_analysis.cpp`）
2. **网表文本管线**：`parseNetlist("...")` → `flatten` → `buildDeviceModels` → solver（如 `test_model.cpp`）

### 7.4 bench JSON

`RFSIM_BENCH_JSON=1` 下 `rfsim_tests` 生成 `bench_<ts>.json`，
`tools/bench_summary.py` 转 markdown 表格（wall_ms / newton_iter / klu_factor_ms / peak_rss）。

---

## 8. 构建系统

### 8.1 CMake 顶层结构

```
CMakeLists.txt              ← 项目级配置 + add_subdirectory(src/tests)
cmake/SuiteSparseKLU.cmake  ← FetchContent 拉 KLU（仅 5 个子项目，纯 C）
cmake/rfsim_config.h.in     ← 版本号配置头模板
src/CMakeLists.txt          ← rfsim_core 静态库 + rfsim_cli 可执行
tests/CMakeLists.txt        ← GoogleTest + rfsim_tests
```

### 8.2 第三方依赖（均 FetchContent 自动拉取）

| 依赖 | 用途 | 来源 |
|------|------|------|
| SuiteSparse KLU | 稀疏直接求解器 | 本地 `../SuiteSparse.zip` 或 GitHub Release v7.7.0 |
| GoogleTest | 单元测试 | GitHub v1.14.0 |

### 8.3 MSVC `/MD` 对齐

`CMakeLists.txt` MSVC 分支：
```cmake
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
```
保证 host 与 OpenVAF dll 共享 UCRT 堆（见 §3.2）。

### 8.4 跨平台编译选项

- GCC/Clang：`-Wall -Wextra -Wpedantic -Wconversion -Wshadow`
- MSVC：`/W4 /permissive- /utf-8 /Zc:__cplusplus`，C 子项目（KLU/AMD）走 `/W1` 降噪

---

## OpenVAF Linux 支持方案

### 背景

rfsim 的 host 源码**本身已跨平台**，无需改动：
- `osdi_library.cpp` 用 `#ifdef _WIN32` 区分 `LoadLibrary`/`dlopen`
- `device_factory.cpp` 候选路径按平台生成 `.dll` / `lib*.so`
- `isReadableCString()` POSIX 分支 `return true`

唯一障碍：**预编译的 `models/*.dll` 是 Windows PE 格式，Linux 下 `dlopen` 无法加载**。
需用 OpenVAF-Reloaded 从 `.va` 源重编为 `.so`。

### 步骤 1：构建 OpenVAF-Reloaded（Linux）

OpenVAF-Reloaded 是 IHP 维护的 OpenVAF 分支（原 OpenVAF 23.5.0 已停维护）。

**前置依赖**：
- Rust / cargo ≥ 1.64（用 [rustup](https://rustup.rs) 安装）
- LLVM-15 开发库 + clang-15（版本须匹配；新版亦可）

**安装系统依赖**：

```bash
# Debian/Ubuntu (用 LLVM 官方源)
sudo bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"
sudo apt install llvm-15-dev clang-15

# Fedora 37+
sudo dnf install clang llvm-devel
```

**构建 OpenVAF-Reloaded**：

```bash
git clone https://github.com/pascalkuthe/openvaf-reloaded.git
cd openvaf-reloaded
# 若有多个 LLVM 版本，指定正确版本:
# export LLVM_LINK_SHARED=1 LLVM_CONFIG="llvm-config-15"
cargo build --release --bin openvaf
# 产物: target/release/openvaf
sudo cp target/release/openvaf /usr/local/bin/
```

> 也可用官方 Docker 镜像：
> ```bash
> docker pull ghcr.io/pascalkuthe/ferris_ci_build_x86_64-unknown-linux-gnu:latest
> docker run -ti -v $(pwd):/io ghcr.io/pascalkuthe/ferris_ci_build_x86_64-unknown-linux-gnu:latest
> # 容器内: cd /io && cargo build --release --bin openvaf
> ```

### 步骤 2：编译 `.va` → `.so`

OpenVAF CLI 用法（与 Windows 相同，仅产物扩展名不同）：

```bash
cd <release_root>
openvaf models/bsim4.va       -o models/libbsim4.so
openvaf models/diode.va       -o models/libdiode.so
openvaf models/ekv.va         -o models/libekv.so
openvaf models/nmos_sh.va     -o models/libnmos_sh.so
openvaf models/simple_diode.va -o models/libsimple_diode.so
```

> **注意**：Linux 下 host 的 `device_factory.cpp` 候选路径是
> `<dir>/lib<name>.so`（加 `lib` 前缀）。因此输出文件须命名为 `lib<name>.so`。

### 步骤 3：构建 rfsim（Linux）

```bash
cd <release_root>
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target rfsim_cli rfsim_tests -j
```

SuiteSparse 依赖：`cmake/SuiteSparseKLU.cmake` 优先找本地 `../SuiteSparse.zip`，
找不到则从 GitHub 下载 v7.7.0。离线环境请提前放置 zip 或设内网镜像 URL。

### 步骤 4：运行测试

```bash
# 网表内用绝对路径或 -L 指定模型目录
./build/bin/rfsim -L models tests/netlists/bsim4_cs_pss.sp

# 跑测试
./build/bin/rfsim_tests --gtest_filter="SParam.*"
./build/bin/rfsim_tests   # 全量
```

### 不可用模型

| 模型 | 原因 | Linux 替代 |
|------|------|-----------|
| `bsim4soi` | 无 `.va` 源，仅 0.3 预编译 dll | 无（需上游 `.va` 源） |
| `bsimcmg` | 同上 | 无 |
| `bsimsoi` | 同上 | 无 |

`bsim4` / `diode` / `ekv` / `nmos_sh` / `simple_diode` 有 `.va` 源，Linux 下可重编。

### 网表路径约定

Linux 下有两种指定 OSDI 模型路径的方式：

1. **网表内绝对路径**：
   ```spice
   .model nmos bsim4va file="/path/to/models/libbsim4.so"
   ```
2. **`-L` 搜索目录**（相对路径时生效）：
   ```bash
   rfsim -L models circuit.sp
   ```
   网表内写 `file="libbsim4.so"`（bare 名），host 会到 `-L` 目录找 `lib<name>.so`。

---

## 10. 调试

### MSVC AddressSanitizer

release 未附 `build_asan.bat`，手动配置 ASAN 构建：

```cmd
:: 配置 ASAN 构建 (Debug + /fsanitize=address)
call vcvars64.bat
cmake -S . -B build_asan -G Ninja ^
    -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl ^
    -DCMAKE_BUILD_TYPE=Debug ^
    -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL ^
    -DCMAKE_CXX_FLAGS="/fsanitize=address /Zi /Od /MDd" ^
    -DCMAKE_C_FLAGS="/fsanitize=address /Zi /Od /MDd"
cmake --build build_asan --target rfsim_tests
:: 跑测试（含 HEAVY）
set RFSIM_FORCE_HEAVY=1 & set RFSIM_FORCE_C3BIS=1
build_asan\bin\rfsim_tests.exe
```

ASAN 在首个越界/UAF 指令处报完整栈。注意 ASAN 不能 instrument 动态加载的 dll
（OpenVAF 产物），但 host 侧崩溃（solveDcOp/assemble/OsdiClient::evalDC）能抓到。

### HB-NL 诊断

```cmd
set RFSIM_HBNL_VERBOSE=1    :: 每外层 Newton 一行 ‖F‖ 轨迹 + AC warm-start 状态
set RFSIM_HBNL_VERBOSE=2    :: 加 source/gmin schedule + α/dxMax + safestep 触发点
```

### PageHeap（Windows）

```cmd
gflags /p /full rfsim_tests.exe   :: 启用 Full PageHeap，抓 dll 内部越界
```

---

## 11. 已知问题与回归基线

所有历史 KI（Known Issue）均已 **close 或在可控范围**：

| KI | 内容 | 状态 |
|----|------|------|
| KI-1 | HB-NL 高 NH × 强非线性频域 Newton 不收敛 | 已部署 AC warm-start + Armijo 修正；路径 B（4× FFT oversampling）backlog |
| KI-2 | N≥15 BSIM4 跨 CRT 堆腐败 | **根治**（MSVC /MD + 删除 msg leak） |
| KI-3 | DC assemble 内部节点越界 | **根治**（`nk > numNodes` 边界守护 + fullDim 修正） |

### 回归基线

- 默认全量：**111 PASS / 0 FAIL**（51 个 HEAVY/FORCE_* 用例默认 skip）
- `RFSIM_FORCE_HEAVY=1`：除 KI-1 明示用例外其余必须 PASS
- 任何 PR 增删 KI 条目时同步更新本文件

### 测试矩阵覆盖

| 模块 | 测试 suite |
|------|-----------|
| DC / Newton | `NewtonDiag.*`、`GminFloor.*` |
| 多 MOSFET | `MultiDevice.*`、`LargeScaleBsim4.*`、`LargeCircuitBsim4.*` |
| Shooting / HB | `Shooting.*`、`Hb.*`、`HbNl.*` |
| S 参数 | `SParam.*`（7 个：解析/S→Y/AC/DC/VF 固定极点/VF 重定位/瞬态） |
| 解析器 | `Lexer.*`、`Parser.*`、`Expression.*`、`Flatten.*` |
| OSDI | `Bsim4.*`、`Osdi.*`、`OsdiModels.*` |
| 装配 | `Assembly.*`、`Gmres.*` |
