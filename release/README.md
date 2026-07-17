# rfsim

一个面向 RF / 模拟电路的小型 SPICE 风格仿真器，主打**大信号 MOSFET 周期稳态**
（Shooting-Newton + FFT 提取谐波）和 **OSDI 紧凑模型集成**（BSIM4 / BSIM-SOI / EKV / 二极管等），
支持 **S 参数器件**（Touchstone + Vector Fitting 瞬态 companion model）。

当前版本 **v0.2.0**。全量测试：`111 tests passed, 0 failed`（51 个 HEAVY/诊断 case 默认 skip）。

---

## 功能矩阵

### 已支持的分析

| 控制卡  | 含义                 | 后端                                                                                       |
|---------|----------------------|--------------------------------------------------------------------------------------------|
| `.op`   | DC 工作点             | Newton + gmin homotopy + 源步进 + 中轨种子 (resistor BFS + 非线性器件均值传播)              |
| `.dc`   | DC 扫描               | DC OP 的连续扫描包装                                                                        |
| `.ac`   | 小信号 AC              | 复数线性化系统直接求解（KLU 复数求解器 + pattern 固化复用）                                  |
| `.hb`   | 谐波平衡 (Harmonic Balance) | 线性电路：复频解析；非线性：弱非线性 HB-NL（GMRES + 续延），不收敛时自动回退 Shooting-PSS    |
| `.pss`  | 周期稳态 (Shooting-Newton) | 时间步进 (Backward Euler / 梯形) + Newton-shooting；末尾 DFT 提取谐波                       |
| `.tran` | 瞬态分析（库内可编程访问） | BDF / 梯形积分器 + companion model；CLI 暂未连线（gtest 内有完整用例）                        |

### 器件模型

| 类别     | 器件                                                                 |
|----------|----------------------------------------------------------------------|
| 内建线性 | `V`（DC + SIN/PULSE/AC）、`I`、`R` / `C` / `L`、子电路 `.subckt` / `X` |
| OSDI 紧凑模型 | `.model name kind file="*.dll"` 加载 OpenVAF 编译的模型：`bsim4`、`bsim4soi`、`bsimcmg`、`bsimsoi`、`ekv`、`diode`、`simple_diode`、`nmos_sh`（Shichman-Hodges level-1 替身） |
| S 参数   | `K` 器件：N-port Touchstone `.sNp` 文件 + Vector Fitting 瞬态 companion model |

---

## 系统要求

### Windows（主要支持平台）
- Visual Studio 2022（MSVC，`/MD` 与 OpenVAF 编译的 `.dll` 对齐 UCRT）
- CMake ≥ 3.22 + Ninja（VS 自带，或独立安装）
- 预编译 OSDI 模型 `.dll` 已随仓库分发（`models/`）

### Linux
- GCC ≥ 13（或 Clang ≥ 15）、CMake ≥ 3.22、Ninja
- host 源码本身跨平台（`dlopen` 加载 `.so`），但**预编译的 `.dll` 不可用**，
  需用 OpenVAF-Reloaded 从 `.va` 源重编为 `.so`。详见
  [Development_guide.md — OpenVAF Linux 支持方案](Development_guide.md#openvaf-linux-支持方案)。
- `bsim4soi` / `bsimcmg` / `bsimsoi` 无 `.va` 源（仅 0.3 预编译 dll），Linux 下不可用。

---

## 快速开始（Windows）

```cmd
build.bat configure   :: 首次：MSVC + Ninja 生成 build/
build.bat build       :: 编译 rfsim.exe + rfsim_tests.exe
build\bin\rfsim.exe tests\netlists\divider.sp
```

预期输出片段：
```
=== DC Operating Point ===
converged in 1 iteration(s)
--- Node Voltages ---
  v(in)  = 5.000000 V
  v(mid) = 2.400000 V
  i(v1)  = 1.300000e-03 A
```

---

## 构建

### Windows 一键构建（推荐）

```cmd
build.bat configure   :: 首次配置（MSVC + Ninja）
build.bat build       :: 编译
build.bat test        :: 编译 + 跑全部 gtest
build.bat clean
```

`build.bat` 自动探测 VS2022（Community/Professional/Enterprise）并调用 `vcvars64.bat`，
把 TMP/TEMP 改成 ASCII 路径（避开中文用户名的汇编器路径 bug）。
SuiteSparse-KLU 通过 CMake `FetchContent` 自动拉取（优先本地 `../SuiteSparse.zip`，否则从 GitHub 下载）。

### 手动构建（POSIX shell / Linux）

```bash
# Windows (MSVC via Developer Command Prompt)
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release ^
      -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL
cmake --build build --target rfsim_cli rfsim_tests -j

# Linux / macOS (GCC / Clang)
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target rfsim_cli rfsim_tests -j
```

---

## CLI 用法

```
rfsim [-L <osdi_lib_dir>] <netlist.sp>
```

- `-L` 指定 OSDI 库 (`*.dll` / `*.so`) 搜索目录；当 `.model ... file="bare.dll"` 是相对路径时生效。
  网表内写绝对路径（如 `file="models/bsim4.dll"`）则可省略。
- **输出**：
  - stdout：结构化电路描述 + 分析结果（节点电压 / 频域 / 谐波）
  - stderr：错误与进度
  - `<netlist>.lis`：HSpice 风格节点表列表文件
  - `<netlist>_pss.csv`：PSS 波形（供 `tools/waveview.py` 查看）

### `--help`

```
rfsim --help
usage: rfsim [-L <osdi_lib_dir>] <netlist.sp>
```

---

## 示例网表

### 1. 电阻分压器 + 电流源（纯线性 DC OP，不需 OSDI）

`tests/netlists/divider.sp`：
```spice
* rfsim DC 工作点验证: 电阻分压器 + 电流源
V1 in 0 5.0
R1 in mid 2k
R2 mid 0 3k
I1 mid 0 1m
.op
.print v(in) v(mid) i(v1)
.end
```

```cmd
build\bin\rfsim.exe tests\netlists\divider.sp
```

### 2. RC 低通滤波器（AC 扫描）

`tests/netlists/rc_lowpass.sp`：
```spice
Vin in 0 0 AC 1
R1 in out 1k
C1 out 0 1u
.ac dec 10 1 100k
.end
```

输出：fc≈159.15 Hz 处 |V(out)|≈0.707。

### 3. BSIM4 共源放大器 + PSS / HB（端到端）

`tests/netlists/bsim4_cs_pss.sp`：
```spice
VDD vdd 0 1.0
RD  vdd d  1k
VG  g   0  0.7 SIN(0.7 0.1 1MEG)
M1 d g 0 0 nmos w=1u l=130n
.model nmos bsim4va file="models/bsim4.dll"
+ vth0=0.5 u0=0.045 vsat=1.5e5 ...
.op
.pss freq=1MEG nh=3 pts=32
.hb  freq=1MEG nh=3
.end
```

```cmd
build\bin\rfsim.exe -L models tests\netlists\bsim4_cs_pss.sp
```

- `.pss` 走 Shooting-Newton → FFT，输出 drain 节点的 DC、基频幅相与高次谐波。
- `.hb` 检测到 BSIM4 是非线性 OSDI 器件 → 先试弱非线性 HB-NL；不收敛时 stderr 提示
  `nonlinear HB did not converge; falling back to Shooting-PSS`，再走与 `.pss` 同一路径。

---

## S 参数器件

`K` 器件从 Touchstone `.sNp` 文件加载 N-port S 参数，支持 AC / DC / 瞬态分析。

### 语法

```spice
* 2-port S-parameter element
K1 port1 port2 file="device.s2p" z0=50

* 1-port S-parameter element
K2 port1 file="match.s1p" z0=50
```

- `file=`：Touchstone 文件路径（`.s1p` / `.s2p` / `.sNp`）
- `z0=`：参考阻抗（默认 50Ω）
- 端口数 = 节点数（自动从 `.sNp` 文件检测）

### 分析能力

| 分析 | 实现 |
|------|------|
| `.ac`  | 按频率插值 S→Y，stamp N×N 复数 Y 矩阵 |
| `.op`  | Y(ω→0) 实部外推 + stamp 电导 |
| 瞬态   | Vector Fitting 有理逼近 `Y(s)=Σ R_k/(s-p_k)+D` + Backward-Euler companion model |

### 示例

`netlists/sparam_dc_test.sp`：
```spice
* 2-port S-parameter device in DC circuit
VDD vdd 0 1.2
VIN in 0 0.6
K1 in out file="netlists/test.s2p" z0=50
Rload out 0 50
.op
.print v(in) v(out)
.end
```

```cmd
build\bin\rfsim.exe netlists\sparam_dc_test.sp
```

---

## OSDI 模型编译

### Windows

```cmd
build_model.bat models\bsim4.va  models\bsim4.dll
build_model.bat models\diode.va  models\diode.dll
```

`build_model.bat` 进入 MSVC `vcvars64` 环境（让 MSVC `link.exe` 优先），调用
`tools/openvaf-reloaded.exe`（OpenVAF-Reloaded，OSDI 0.4 ABI）。
旧版 `tools/openvaf.exe`（OpenVAF 23.5.0，OSDI 0.3）保留作 rollback。

### Linux

需从源码构建 OpenVAF-Reloaded 并重编所有 `.va` 为 `.so`。详见
[Development_guide.md — OpenVAF Linux 支持方案](Development_guide.md#openvaf-linux-支持方案)。

---

## 测试

```cmd
build.bat test                              :: 全量构建 + 跑全部 gtest
runtest.bat                                :: 只跑测试（已构建）
runtest.bat "MultiDevice.*:NewtonDiag.*"   :: GTest filter
runtest.bat "SParam.*"                      :: S 参数子集
runtest.bat "Shooting.*"                    :: 周期稳态
```

测试覆盖：
- **DC / Newton**：`NewtonDiag.*`、`GminFloor.*`（gmin 同伦边界 + 强敌对工作点）
- **多 MOSFET DC + PSS**：`MultiDevice.DiffPair / CascodeAmp / CurrentMirror / InverterChain`
- **大规模 BSIM4**：`LargeScaleBsim4.*`、`LargeCircuitBsim4.*`
- **Shooting / HB**：`Shooting.RcSineSteadyState / Bsim4CommonSourcePssConverges / Bsim4LcTank1GHz`
- **S 参数**：`SParam.TouchstoneParse / SToYConversion / AcAnalysis / DcOp / VectorFitFixedPoles / Transient`
- **解析器 / 表达式 / 扁平化**：`Lexer.*`、`Parser.*`、`Expression.*`、`Flatten.*`
- **器件建模 / OSDI**：`Bsim4.*`、`Osdi.*`、`OsdiModels.*`

51 个 HEAVY / C3-bis 用例默认 `GTEST_SKIP`，需设环境变量
`RFSIM_FORCE_HEAVY=1` / `RFSIM_FORCE_C3BIS=1` 才会跑（大规模 / 多 finger 收敛诊断）。

### 波形查看

```cmd
python tools\waveview.py build\<netlist>_pss.csv
python tools\waveview.py build\<netlist>_pss.csv v1 v3    :: 指定节点
```

---

## 已知限制

| 项 | 说明 |
|----|------|
| 噪声分析 | 未实现（`.noise`） |
| `.tran` CLI | 瞬态求解器在库内可编程访问，CLI 暂未连线（gtest 内有完整用例） |
| HB-NL 强非线性 | 弱非线性快路径；强非线性下自动回退 Shooting-PSS |
| Vector Fitting 极点重定位 | 对纯实数极点收敛较慢（VF 算法固有，适合共轭复数对）；`vectorFitFixedPoles` 固定极点求解留数精度高 |
| `bsim4soi` / `bsimcmg` / `bsimsoi` | 仅 0.3 预编译 dll，无 `.va` 源；Linux 下不可用 |

---

## 编程接口（库使用）

`rfsim_core` 是 static lib，链接它就能在 C++ 里用：

```cpp
#include "parser/parser.hpp"
#include "circuit/flatten.hpp"
#include "model/device_factory.hpp"
#include "solver/dc_op.hpp"
#include "solver/shooting.hpp"

auto pr  = rfsim::parseNetlist(text, "in-memory");
auto c   = rfsim::flatten(pr.netlist);
rfsim::ParamEnv env;
env.libSearchDir = "models";                  // OSDI *.dll/*.so 搜索目录
auto fac = rfsim::buildDeviceModels(c, env);  // fac.totalNodes, fac.devices
auto dc  = rfsim::solveDcOp(fac.totalNodes, fac.devices); // dc.nodeVoltages[i]
auto pss = rfsim::solveShooting(fac.totalNodes, fac.devices,
                                {.fundamental=1e6, .numTimePoints=64},
                                &dc.nodeVoltages);
auto hb  = rfsim::shootingToHarmonics(pss, fac.totalNodes, /*NH=*/5, /*f0=*/1e6);
```

详见 [Development_guide.md](Development_guide.md)。

---

## 仓库布局

```
src/
  cli/main.cpp              ← rfsim 命令行入口
  parser/                   ← SPICE 词法 / 语法 / 表达式 / 扁平化
  circuit/                  ← Circuit + 节点表 + 分析卡识别
  model/                    ← 内建器件 + OSDI 加载器 + S 参数器件
  assembly/                 ← 雅可比 stamp + KLU/KLU-Z 包装 + HB 雅可比块 + 瞬态装配
  solver/                   ← dc_op / dc_sweep / ac_analysis / hb / shooting / time_stepper
  sparam/                   ← Touchstone 解析 + Vector Fitting
  output/                   ← HSpice 风格输出格式化
tests/
  netlists/                 ← SPICE 测试网表
  test_*.cpp                ← 22 个测试源（含 test_sparam.cpp）
models/                     ← 预编译 OSDI 模型 (*.dll + *.va 源)
tools/                      ← openvaf-reloaded.exe / waveview.py / bench_summary.py
cmake/                      ← SuiteSparseKLU.cmake + rfsim_config.h.in
build.bat / build_model.bat / runtest.bat
```

---

## 许可

未声明（本仓库目前为研究 / 内部使用）。SuiteSparse 子项目按 LGPL / BSD
（详见 `build/_deps/suitesparse-src/LICENSE.txt`）。
