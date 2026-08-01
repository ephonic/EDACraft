# rfsim

一个面向 RF / 模拟电路的小型 SPICE 风格仿真器，主打**非线性谐波平衡 (HB-NL)**
与**大信号 MOSFET 周期稳态**（Shooting-Newton + FFT 提取谐波）。
半导体器件统一走 **Verilog-A 生成模型**路径：仓库内置 vaParser 代码生成器
（`tools/vaparser`），把 `.va` 紧凑模型编译为 C++ DeviceModel 并静态链接，
覆盖 BSIM4 / BSIM-SOI / BSIM-CMG / BSIM3 / EKV / BJT / 二极管等。
（历史 OSDI/OpenVAF DLL 路径已于 v0.2 移除。）

当前版本 **v0.2.0**。全量 gtest：`155 passed, 0 failed`（25 个由 `RFSIM_FORCE_HEAVY=1`
门控的 HEAVY case 与 15 个 `RFSIM_FORCE_*` 诊断 case 默认 skip）。

---

## 工具能力

### 已支持的分析

| 控制卡    | 含义                  | 后端                                                                             |
|--------|---------------------|--------------------------------------------------------------------------------|
| `.op`  | DC 工作点               | Newton + gmin homotopy + 源步进 (source-stepping) + 中轨种子 (resistor + nonlinear-device BFS) |
| `.dc`  | DC 扫描               | 上面 DC OP 的连续扫描包装                                                                |
| `.ac`  | 小信号 AC              | 复数线性化系统直接求解                                                                     |
| `.hb`  | 谐波平衡 (Harmonic Balance) | 线性电路：复频解析；非线性电路：**全非线性 HB-NL**（IFFT→eval→FFT 时域采样装配 + 精确 2NH 卷积雅可比 + LM 阻尼 + source/gmin 续延 + stall 接受；dim>200 走 GMRES+块预条件），不收敛时自动回退到 **Shooting-PSS → FFT** |
| `.pss` | 周期稳态 (Shooting-Newton) | 时间步进 (Backward Euler / 梯形) + Newton-shooting；末尾 DFT 提取谐波                          |
| `.tran` | 瞬态分析 | BE / 梯形积分 + Newton，输出 CSV 波形 |

### 数值核心

- **稀疏直接求解器**：SuiteSparse-KLU（BTF + AMD + 部分选主元）。DC / 瞬态 / shooting 的核心步全部走 KLU。
- **HB 求解器**：GMRES + Jacobi/块预条件子 + Krylov 子空间复用（HB 雅可比块结构非 KLU 友好）。
- **DC 收敛同伦**：
  - log-spaced gmin 调度
  - 源步进 (`vsScale=ε..1` linear schedule)
  - 中轨种子传播：VS 锚定 → 电阻图 BFS（`V_neigh = 0.5·V_anchor`）→ 非线性器件均值传播
  - `gmin floor accept`：到达 gmin 下限仍未收敛时返回"最佳已收敛"工作点
- **限幅 (limiting)**：生成模型内建 VA 限幅（pnjlim/fetlim 风格，`resetLimiting()` 跨 Newton 重置），并配合中轨种子 + 同伦避开 hostile 工作点。
- **内部节点**：生成模型按 mod 参数动态折叠（如 BSIM4 rdsmod/rgatemod/rbodymod=0 时 di/si/gi/gm/bi 等 alias 到外部节点），`allocateInternalNodes()` 在器件构造后统一分配。

### 设备模型

- 内建：`V`（电压源，DC + SIN/PULSE/AC）、`I`（电流源）、`R` / `C` / `L`、子电路 `.subckt` / `X`。
- Verilog-A 生成模型：`.model name kind ...` 直接路由到静态链接的生成模型
  （`file="*.dll"` 属性兼容解析但忽略）。`models/` 附 `.va` 源：
  - `bsim4.va`（bsim4va，PTM 130 nm 参数集）、`bsimsoi.va`、`bsimcmg.va`、`bsim3.va`
  - `ekv.va`、`bjt505.va`、`diode.va`/`diode_vt.va`、`simple_diode.va`
  - `nmos_sh.va`（Shichman-Hodges level-1 替身）
- 新增模型流程：`vaParser <model>.va src/model/generated/<name> --format=rfsim`
  产出 `_gen.cpp/.h + _reg.inc`，再跑 `tools/regen_registry.sh` 汇总注册表。
- 含非线性器件时，HB-NL 失败会自动尝试 PSS；纯线性走解析 HB。

### 解析器 (Parser)

- SPICE 风格 token + AST + 扁平化 (flatten)。
- 支持：`.param`、`.subckt`/`.ends`、`.model`、`.options`、表达式（含 SPICE 单位后缀 `1k`/`1u`/`1meg`）、`.print`、`.measure`（部分）。
- 错误恢复型 parser：诊断收集后仍尽可能继续解析，便于调试。

---

## 仓库布局

```
src/
  cli/main.cpp           ← rfsim 命令行入口
  parser/                ← SPICE 词法 / 语法 / 表达式 / 扁平化
  circuit/               ← Circuit + 节点表 + 分析卡识别
  model/                 ← 内建器件 + device_factory（生成模型路由）
  model/generated/       ← vaParser 产出的生成模型 (*_gen.cpp/.h + 注册表)
  assembly/              ← 雅可比 stamp + KLU 包装 + HB 雅可比块
  solver/                ← dc_op / dc_sweep / ac_analysis / hb_solver / hb_nonlinear / shooting / time_stepper
  output/                ← HSpice 风格输出格式化
tests/
  netlists/              ← SPICE 示例：rc_lowpass.sp / divider.sp / inverter.sp / bsim4_cs_pss.sp ...
  test_*.cpp             ← 26 个测试源（DC / AC / HB / PSS / 多 MOSFET）
models/                  ← 紧凑模型 Verilog-A 源 (*.va)
tools/
  vaparser/              ← Verilog-A → C++ 代码生成器（vaParser，含 lex/yacc 产出物）
  regen_registry.sh      ← 生成模型注册表汇总脚本
cmake/SuiteSparseKLU.cmake
build.bat / runtest.bat
```

---

## 构建

### 依赖
- MSVC 2022 (cl.exe)、CMake ≥ 3.22、Ninja。
- SuiteSparse-KLU / GoogleTest 通过 `FetchContent` 拉取（离线环境用
  `FETCHCONTENT_SOURCE_DIR_*` 指向本地源码包）。
- vaParser 随主构建一起产出（`RFSIM_BUILD_VAPARSER=ON` 默认）；
  lex/yacc 产出物已入库，无需 flex/bison。

### Windows 一键构建

```cmd
build.bat configure   :: 首次：用 mingw64 cmake/ninja 生成 build/
build.bat build       :: 编译 rfsim_cli + rfsim_tests
build.bat test        :: 编译 + 跑全部 gtest
build.bat clean
```

`build.bat` 会自动把 `G:\msys64\mingw64\bin` 注入 PATH，并把 TMP/TEMP 改成 ASCII 路径（避开中文用户名的汇编器路径 bug）。

### 手动 (POSIX shell)

```bash
export PATH="/g/msys64/mingw64/bin:$PATH"
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target rfsim_cli rfsim_tests -j
```

### 从 Verilog-A 新增 / 更新器件模型

```cmd
build\bin\vaParser.exe models\bsim4.va src\model\generated\bsim4va --format=rfsim
tools\regen_registry.sh
```

> 生成产物（`*_gen.cpp/.h` + `*_reg.inc`）入库并静态编译进 rfsim_core；
> 修改 `.va` 模型后需重新生成并全量构建。

---

## CLI 用法

```
rfsim <netlist.sp>
```

- `-L <dir>`：历史 OSDI 库搜索目录参数，已 deprecated（兼容保留、无实际作用）。
- 输出走 stdout（节点电压 / 频域 / 谐波），错误与进度走 stderr。

### Windows 跑测试时的 DLL 注入

`runtest.bat` 是个无脑封装：

```cmd
runtest.bat                                :: 跑全部 gtest
runtest.bat MultiDevice.*                  :: 只跑 MultiDevice.*
runtest.bat "NewtonDiag.*:Shooting.*"      :: GTest filter 表达式
```

它会把 `G:\msys64\mingw64\bin` 加到 PATH（让测试找到 mingw 运行时 DLL），然后执行 `build/bin/rfsim_tests.exe [--gtest_filter=...]`。

---

## 示例网表

### 1. 电阻分压器 + 电流源（纯线性 DC OP，不需要 OSDI）

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

跑法：
```cmd
build\bin\rfsim_cli.exe tests\netlists\divider.sp
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
VG  g   0 0.7 SIN(0.7 0.1 1MEG)
M1 d g 0 0 nmos w=1u l=130n
.model nmos bsim4va file="models/bsim4.dll"
+ vth0=0.5 u0=0.045 vsat=1.5e5 ...   (完整参数见仓库)
.op
.pss freq=1MEG nh=3 pts=32
.hb  freq=1MEG nh=3
.end
```

```cmd
build\bin\rfsim_cli.exe -L models tests\netlists\bsim4_cs_pss.sp
```

- `.pss` 走 Shooting-Newton → FFT，输出 drain 节点的 DC、基频幅相与高次谐波。
- `.hb` 检测到 BSIM4 是非线性设备 → 先走全非线性 HB-NL；不收敛时 stderr 提示 `"nonlinear HB did not converge; falling back to Shooting-PSS"`，再走与 `.pss` 同一路径。

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
auto c   = rfsim::flatten(pr.ast);
auto fac = rfsim::buildDeviceModels(c, env);              // env.libSearchDir 指向 *.dll
auto dc  = rfsim::solveDcOp(fac.totalNodes, fac.devices); // dc.nodeVoltages[i]
auto pss = rfsim::solveShooting(fac.totalNodes, fac.devices,
                                {.fundamental=1e6, .numTimePoints=64},
                                &dc.nodeVoltages);
auto hb  = rfsim::shootingToHarmonics(pss, fac.totalNodes, /*NH=*/5, /*f0=*/1e6);
```

`time_stepper` 还暴露独立的 BDF / 梯形瞬态求解器，可单独跑 `.tran` 风格分析（CLI 暂未连线，但 gtest 里有完整用例：`Shooting.Bsim4TransientSwitch` 等）。

---

## 测试

```cmd
build.bat test                                       :: 全量 (~85 s, 含 BSIM4 PSS)
runtest.bat "MultiDevice.*:NewtonDiag.*"             :: 焦点 suite
runtest.bat "Shooting.*"                              :: 周期稳态
runtest.bat "LargeScaleBsim4.*"                       :: 大规模 BSIM4 收敛
```

测试覆盖：

- **DC / Newton**：`NewtonDiag.*`、`GminFloor.*`（gmin 同伦边界 + 强敌对工作点）
- **多 MOSFET DC + PSS**：`MultiDevice.DiffPair / CascodeAmp / CurrentMirror / InverterChain / ...`
- **大规模 BSIM4**：`LargeScaleBsim4.CascodeChain5` 等
- **Shooting / HB**：`Shooting.RcSineSteadyState / DiodeRectifierRuns / Bsim4CommonSourcePssConverges / Bsim4LcTank1GHz`
- **解析器 / 表达式 / 扁平化**：`Lexer.*`、`Parser.*`、`Expression.*`、`Flatten.*`
- **设备建模 / 生成模型**：`GeneratedModels.*`、`MultiDevice.*`、`LargeCircuitBsim4.*`

`C3bis_*` / `EightFingerBalanced` / `SelfBiasedCascodeStack5` 等 15 个用例默认 `GTEST_SKIP`，需要设环境变量 `RFSIM_FORCE_C3BIS=1` 才会跑——它们是 V2-γ 在持续推进的多 finger / 自偏置 cascode 收敛诊断。

---

## 当前状态与限制

- DC：BSIM4 多 MOSFET 网表（DiffPair / Cascode / 反相器链 / 电流镜）全部收敛。
- HB-NL：全非线性路径（生成模型通用时域采样装配）。生成模型目前为**纯阻性**
  HB（无电荷/电抗卷积项），中低频下与 Shooting-PSS 一致；高频强动态场景建议
  用 `.pss` 交叉验证。极端强非线性（如硬整流）下 Newton 可能停滞在小残差窄谷，
  此时按 `stallAcceptRel`（默认 3e-2）放宽接受并在结果中标记 `relaxedConvergence`。
- PSS：`Bsim4CommonSourcePssConverges` / `Bsim4LcTank1GHz` 稳定通过。
- 噪声分析、HB Krylov 复用的二次开发**仍在 backlog**。

## 许可

未声明（本仓库目前为研究 / 内部使用）。SuiteSparse 子项目按 LGPL / BSD（详见 `build/_deps/suitesparse-src/LICENSE.txt`）。
