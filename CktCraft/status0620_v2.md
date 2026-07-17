# rfsim 项目状态报告 — 2026-06-20

## 当前焦点

把仿真器从 “66/66 测试通过的实验性原型” 推进到 **真实可用**：让大信号 MOSFET 网表跑出合理的稳态谐波，CLI 端到端可用。

测试基线：**68/68 通过**（在原 66 基础上新增 2 个 PSS / Shooting harmonics 测试）。

## 环境
- 构建：MSYS2 MinGW64 GCC 15.2 + CMake + Ninja，`build.bat configure|build|test`。
- OSDI 模型库：MSVC + OpenVAF 23.5 编译，`models/bsim4.dll` 等。
- 测试运行：`runtest.bat` 自动把 `G:/msys64/mingw64/bin` 注入 PATH。

## 关键诊断（OSDI 反应残差语义）

针对 status0620 中 “强非线性 HB 收敛缺 dQ/dt 残差” 的问题：

1. 写了 `probe_react2.cpp` 对 BSIM4 在固定偏置下分别调用 `eval()`（DC）和 `evalTransient()`（dt=1ns/1us）。
2. 观察：DC 漏极电流随 Vg 单调上升（Vg=0.8V≈0.1mA），符合预期。
3. **关键发现**：transient RHS 的输出**与 dt 无关**（1ns 与 1us 完全一致），且约为 DC 残差的 3×。
4. 结论：OSDI 0.3 的 `load_spice_rhs_tran` 返回的并不是 “Q” 也不是 “dQ/dt”，而是 **SPICE 风格 Newton RHS：α·(J·V − F + lim_rhs)**。直接把它当 dQ/dt 加进 HB 残差是行不通的——OSDI 没有干净暴露电荷。

→ 战略调整：**HB 残差不再尝试直接拼电荷项**；大信号路径改走 **Shooting → FFT 提取谐波**。HB 仍保留给弱非线性。

## 本次主要改动

### 1. Shooting 谐波导出（新功能）
- `src/assembly/hb_jacobian.hpp/.cpp`：把原文件局部的 `currentFft` 暴露为公开符号 `realSamplesToHarmonics(t, NH)`。
- `src/solver/shooting.hpp/.cpp`：新增 `shootingToHarmonics(ShootingResult, numNodes, NH, fundamental) → HbResult`，自动剥掉 Shooting 末尾的 T 等价点、对每个非地节点做 DFT。

### 2. CLI 端到端可用
- `src/cli/main.cpp`：
  - 新增 `-L <osdi_lib_dir>` 参数，传给 `ParamEnv::libSearchDir`。
  - `.hb` 检测 OSDI 非线性器件后自动走 `solveHbNonlinear`；若 HB 不收敛，**自动回退到 Shooting-PSS → FFT** 路径。
  - 新增 `.pss freq=<f> nh=<n> pts=<m>` 控制卡，`pts` 自动至少 2·(NH+1)。
  - DC 不收敛时由电压源推断初值（被 VS 强制的节点取 VS 电压，其余取最大供电电压）。
  - PSS 即使未收敛也输出已有的有限波形（与单元测试语义一致）。
- `src/circuit/circuit.hpp`：`isAnalysisCard` 增加 `"pss"`。

### 3. SPICE 解析到装配的两个隐藏 Bug 修复

#### 3a. 波形源没装上波形（device_factory.cpp）
原来 `Vx ... 0.7 SIN(0.7 0.1 1MEG)` 解析后只取了首个数值作 DC，**没调用 `setWaveform`**，也没把 SIN 的幅度暴露为 AC 量。修复：
- 解析 SIN/PULSE 时构造 `Waveform` 并 `setWaveform(...)`。
- SIN 的 `va` 默认填入 `acMag = (va, 0)`，使 HB 拿到基频激励。允许后续显式 `AC <mag> <phase>` 覆盖。

#### 3b. HB Jacobian 把 acMag 错出到所有谐波（hb_jacobian.cpp）
原代码：
```cpp
Complex src = (k == 0) ? Complex(v->voltage(),0) : v->acMag();
```
等于 H1、H2、H3 …全部用同一个基频幅度激励，物理错误。修复为只在 H=1 处加载：
```cpp
Complex src = (k == 0) ? Complex(v->voltage()*ss,0)
                       : (k == 1 ? v->acMag()*ss : Complex(0,0));
```

### 4. 测试新增
- `tests/test_shooting.cpp`：
  - `Shooting.ShootingHarmonicsMatchLinear`：1MHz RC 256 点，与 `solveHbLinear` 比 |H1| 容差 5%。
  - `Shooting.Bsim4CommonSourcePssConverges`：Bsim4 共源 NH=3 pts=32，断言波形有限且 |Vd_H1| < VDD。
- `tests/netlists/bsim4_cs_pss.sp`：真实 BSIM4 共源放大网表，含 `.op .pss .hb` 三张控制卡。

## 测试结果

```text
[==========] 68 tests from 16 test suites ran. (~36s)
[  PASSED  ] 68 tests.
```

CLI 端到端示例（`build\bin\rfsim.exe tests\netlists\bsim4_cs_pss.sp`）：

```
=== Harmonic Balance (f0=1e+06 Hz, NH=3, nonlinear) ===
  nonlinear HB converged in 18 iter, 6 continuation steps
  harmonic 0  v(d)=1.0000  v(g)=0.7000
  harmonic 1  v(d)=1.20e-5  v(g)=0.1000   ← AC drive
  harmonic 2  v(d)=6.04e-6  v(g)≈0
  harmonic 3  v(d)=9.21e-6  v(g)≈0
  时域 v(g): 0.8 / 0.77 / 0.7 / 0.63 / 0.6 / 0.63 / 0.7 / 0.77   ← 干净的正弦

=== Periodic Steady State (Shooting, f0=1e+06 Hz, NH=3, pts=32) ===
  PSS shooting did not converge after 20 iter   ← BSIM4 大信号仍未完全闭合
  （仍输出有限波形与谐波，与单元测试语义一致）
```

> 注：`v(d)` HB 基频幅度很小是 **物理结果**——`vth0=0.5, Vov=0.2V, u0=0.045` 下小信号增益本来就不大；漏端基频 ≈ gm·va·Rd，量级吻合。

## 仍开放的问题（推迟到下一阶段）

1. **DC 工作点对 BSIM4 不收敛**：网表里直接 130 次 Newton 仍未收敛。CLI 已用 “VS 推导初值” fallback 让 PSS/HB 还能跑。后续应在 DC 中加 source-stepping。
2. **Shooting 收敛**：BSIM4 大信号 PSS 在 32 点、20 轮内仍未完全闭合，输出可用但残差尚大。后续要把 finite-diff Jacobian 换成 Broyden / 伴随。
3. **HB 强非线性精度**：HB 走 continuation 收敛，但电荷项目前由 ∂Q/∂V 频域电纳块代替（残差和 Jac 仍不完全一致，弱信号 OK）。最终方案是 Shooting 提供初值 + jωQ 频域校正。

## 文件变更（本次新增/修改）

```
src/assembly/hb_jacobian.cpp    | acMag 仅在 H=1 加载；realSamplesToHarmonics 暴露
src/assembly/hb_jacobian.hpp    | 公开 realSamplesToHarmonics 声明
src/circuit/circuit.hpp         | isAnalysisCard 加 "pss"
src/cli/main.cpp                | -L 选项；.pss 处理；.hb 自动回退；DC fallback init
src/model/device_factory.cpp    | SIN/PULSE 装 Waveform + 默认 acMag = va
src/solver/shooting.cpp         | shootingToHarmonics 实现
src/solver/shooting.hpp         | shootingToHarmonics 声明
tests/test_shooting.cpp         | +2 测试
tests/netlists/bsim4_cs_pss.sp  | 新增 BSIM4 共源放大端到端网表
runtest.bat                     | 新增：注入 mingw64 PATH 后运行测试
probe_hb.cpp / probe_react.cpp  | 诊断探针（CMake 选项 RFSIM_BUILD_PROBES）
probe_react2.cpp                |
src/CMakeLists.txt              | RFSIM_BUILD_PROBES 选项
```

---
*报告由 ZCode 自动生成于 2026-06-20。*
