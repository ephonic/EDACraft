# 射频仿真器开发计划（plan.md）

> 版本：v0.2 | 最近更新：2026-06-18
> 目标：构建面向射频（RF）电路的频域非线性仿真器，支持 Verilog-A 器件模型（OpenVAF/OSDI）、Harmonic Balance 求解、预条件 GMRES 与 Krylov 子空间重用、SPICE 网表解析与 HSPICE 兼容输出。

---

## 1. 项目概述

### 1.1 定位
一款**频域非线性电路仿真器**，核心能力是对强非线性射频电路（功率放大器、混频器、振荡器、倍频器等）进行稳态谐波平衡分析。

### 1.2 核心需求
| 编号 | 需求 | 说明 |
|------|------|------|
| R1 | 器件模型由 **OpenVAF** 支持（Verilog-A） | OpenVAF 编译 Verilog-A 为符合 **OSDI** 标准的共享库，运行时动态加载并调用其残差/雅可比评估接口；内置线性器件（R/L/C/V/I）与之共享同一装配入口 |
| R2 | 求解器采用 **Harmonic Balance** | 频域求解非线性代数方程 F(X)=0，X 为各节点各谐波复幅度 |
| R3 | 线性求解用**预条件 GMRES** | Newton 步内 J·ΔX = −F 用右预条件 GMRES |
| R4 | **重用子空间降低复杂度** | GCROT/GMRES-DR 思想，连续 Newton 迭代间重用 Krylov 子空间 |
| R5 | 支持 **SPICE 解析器** | 标准网表（元件/模型/子电路/控制卡） |
| R6 | 波形输出采用**标准 HSPICE 输出格式** | .lis/.tr0/.ac0/.measure |

### 1.3 非目标（v1 不做）
- 瞬态时域求解
- **多音（≥3 音）HB**（v1 只做单音 + 双音）
- 布局后寄生提取、蒙特卡洛、电磁场协同

---

## 2. 开发语言：C++

C++（C++17+），MSVC/GCC/Clang 三编译器，CMake 构建，vcpkg/Conan 依赖，OpenMP 并行，RAII 资源管理，`std::expected` 错误处理。

---

## 3. 技术选型

| 维度 | 选择 |
|------|------|
| 语言 | C++17+ |
| 构建 | CMake + Ninja |
| 器件模型 | OpenVAF（Verilog-A → OSDI 共享库） |
| 线性代数 | 自研稀疏矩阵 + BLAS/LAPACK |
| 并行 | OpenMP |
| 解析器 | 手写递归下降 |
| 测试 | GoogleTest |
| 日志 | spdlog |

---

## 4. 模块设计

### 4.1 SPICE 解析器（R5）
行导向递归下降：元件卡/模型卡/子电路嵌套/`.include`/控制卡/`.param` 表达式/续行/注释/单位后缀。

### 4.2 电路表示
节点表（地别名归一）+ 器件实例 + 模型表 + 层次化子电路展开。

### 4.3 器件模型层（OpenVAF/OSDI，R1）
- **OSDI ABI**（已验证）：共享库导出 `OSDI_DESCRIPTORS` 描述符数组（非指针的指针）、`OSDI_NUM_DESCRIPTORS`、`OSDI_VERSION_MAJOR/MINOR`。`OsdiDescriptor` 含全部函数指针与元数据。
- **node_mapping**：仿真器在实例块 `node_mapping_offset` 处设 `uint32[num_nodes]`（本地节点→全局位置）。
- **雅可比加载**（关键发现）：`jacobian_ptr_resist_offset` 处存 `[double*; num_entries]` **指针数组**，每指针指向矩阵位置，`load_jacobian_resist` 做 `*ptr += val`。
- **C++ 封装**：`DeviceModel` 抽象基类；`OsdiModel` 适配 OSDI；内置 `Resistor`/`Capacitor`/`Inductor`/`VoltageSource`/`CurrentSource`。

### 4.4 频域装配（HB 推广）
线性器件频域导纳 stamp；非线性器件 IFFT→eval→FFT 卷积。

### 4.5 Harmonic Balance 求解器（R2）
阻尼 Newton 外迭代 + GMRES 内迭代 + 子空间重用。

---

## 5. 数据结构（C++ 草案）

```cpp
using Complex = std::complex<double>;
class DeviceModel { virtual void eval(...); virtual bool is_linear(); };
class OsdiModel : public DeviceModel;
struct HbConfig { double fundamental; uint32_t numHarmonics; };
```

---

## 6. 开发阶段

### M1 — 骨架与解析器（✅ 完成）
### M2 — OpenVAF/OSDI 集成与线性 DC（进行中）
### M3 — Harmonic Balance 核心（进行中，线性已完成）

---

## 实现进度（滚动更新）

### 环境（2026-06-17）
- msys2 mingw64：GCC 15.2.0 + CMake 4.2.3 + Ninja 1.13.2。
- **关键环境问题**：用户 TEMP 含中文字符导致 mingw 汇编器失败，`build.bat` 重定向 TMP/TEMP 到 ASCII 路径绕过。
- OSDI 模型编译：MSVC Build Tools (VS2022) + OpenVAF 23.5.0，`build_model.bat` 在 MSVC 环境编译 `.va` → `.dll`。
- 构建：`build.bat configure | build | test`。

### M1 — 完成 ✅（2026-06-17）
词法器、`.param` 表达式求值、AST、行导向解析器、节点表、扁平化、CLI。22 测试通过，`inverter.sp` 端到端解析正确。

### M2 — OSDI 集成与 DC（OSDI 非线性 DC 已打通 ✅）
- **器件模型层**：`DeviceModel` 基类 + 内置线性器件（R/L/C/V/I，含 AC 频域导纳）+ 工厂。
- **OSDI 集成层**（`src/model/osdi/`）：`osdi_0_3.h`、`OsdiLibrary`（dlopen）、`OsdiClient`（setup/eval/雅可比）、`OsdiModel`。修复指针间接 bug。验证：库加载、descriptor、setup、node_mapping、eval（与 Shockley 吻合）、雅可比加载（per-entry 指针数组）。
- **装配与求解**：稀疏矩阵(CSR)、稠密 LU（实+复）、MNA 装配、DC 工作点、DC 扫描、AC 小信号、**非线性 Newton（gmin stepping + 回溯线搜索）**。
- **关键突破（OSDI 非线性 DC）**：① 符号——OSDI 残差/雅可比与 F=流出-注入 约定相反，stamp 取负；② 收敛——gmin stepping（1e-2→1e-12 递减并联电导）+ 回溯线搜索（残差下降判据）。**验收：二极管（5V,1k,D）v(anode)=0.717V，收敛成功**。
- **验收**：62 测试通过。DC/AC/扫描/HB 与理论吻合，二极管非线性 DC 已打通。

### M3 — Harmonic Balance（线性 + 非线性框架完成 ✅）
- **线性 HB**（`hb_solver.{hpp,cpp}`）：单音，谐波集 K={0..NH}，每谐波独立频域 MNA，复 LU。R/L/C 频域导纳，V 源 DC+AC 分谐波激励，波形 IFFT。与 AC 吻合到 1e-6。
- **非线性 HB**（`hb_nonlinear.{hpp,cpp}`）：Newton 迭代，IFFT→OSDI eval→FFT 频域残差装配。OsdiModel 加 `evalTimeSamples`/`evalTimeJacobians`（时域批量评估）。对角雅可比近似 + 自适应阻尼 + NaN 保护。纯线性电路自动路由到线性 HB。
- **完整频域卷积雅可比 + 稠密 LU Newton**（2026-06-18 新增）：
  - 新增 `src/assembly/hb_jacobian.{hpp,cpp}`，将线性器件频域 stamp 与非线性 OSDI 时域雅可比卷积统一装配为实数稠密 Jacobian。
  - 修复 `OsdiModel::evalTimeSamples`/`evalTimeJacobians` 的电压向量索引 bug：原来传递本地索引向量给 `evalDC`，导致 OSDI 模型读到错误节点电压；现在构造全局节点编号索引的电压向量。
  - `hb_nonlinear.cpp` 改用完整 Jacobian + 稠密 LU + 裁剪/回溯阻尼 Newton。纯线性电路仍一步收敛；二极管整流测试通过。
- **Phase 3 — 右预条件 GMRES(m)**（2026-06-18 新增）：
  - 新增 `src/assembly/gmres.{hpp,cpp}`，实现 restarted GMRES(m)，支持抽象 `LinearOperator` 与 `Preconditioner`。
  - 新增 `tests/test_gmres.cpp`：单位矩阵、随机对角占优矩阵、对角预条件器三类测试通过。
  - `hb_nonlinear.cpp` 中当实数化 Jacobian 维数 >200 时自动切换为 GMRES + 对角预条件器；小规模仍用稠密 LU。
- **Phase 4 — 简单子空间重用 / 热启动**（2026-06-18 新增）：
  - Newton 迭代间保存上一轮的修正量 `prevDx`，作为下一轮 GMRES 的初始猜测，实现最简形式的 Krylov 子空间信息复用。
- **验收**：53 个测试中的 51 个通过；2 个 MOSFET 测试因缺少 EKV 库文件预失败，与本改动无关。线性 HB 一致性保持；二极管整流产生谐波产物；GMRES 单元测试通过。
- **待完成**：
  - 强非线性 HB 收敛精度仍需提升（gmin stepping / source stepping / 更优初值/连续法）。
  - 更系统的子空间重用：GMRES-DR/GCROT 风格，保存并正交化多轮 Krylov 基。
  - 更优预条件器：块对角（每谐波一个块）或 ILU 预条件。

---

## 7. 测试策略
单元测试（解析/装配/FFT/GMRES）+ 集成测试（RLC→二极管→PA→混频器）+ 对照基线（Ngspice/Qucs/ADS/HSPICE）。当前 57 单元测试通过。

## 8. 风险
- OSDI 接口语义对接（DC 符号调试中）
- HB 强非线性收敛（阻尼 Newton + continuation）
- 子空间重用正交性漂移
- HSPICE 二进制格式无公开规范

## 9. 交付物
源码、可执行仿真器、OpenVAF 模型编译文档、用户手册、验证报告、plan.md。

## 10. 术语
HB、MNA、GMRES、GCROT/GMRES-DR、Verilog-A、OpenVAF、OSDI（Open Source Device Interface，SemiMod 标准，ngspice 有桥接实现）。
