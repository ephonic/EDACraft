# S 参数仿真工具实现计划 (Sparam.md)

## 1. 目标

实现 N-port S 参数器件，支持：
- Touchstone .sNp 文件解析
- S→Y 参数转换（按频率插值）
- Vector Fitting 有理逼近（Y(s) = Σ d_k/(s-p_k) + d∞）
- 无源性修正（极点实部翻转）
- AC 分析（频域直接 stamp Y 矩阵）
- DC 分析（Y(ω=0) 实部 stamp）
- 瞬态分析（VF 极点-留数 companion model）

## 2. 架构设计

### 2.1 新增文件

```
src/sparam/touchstone.hpp/cpp     — Touchstone .sNp 文件解析
src/sparam/vector_fit.hpp/cpp     — Vector Fitting 算法
src/sparam/passivity.hpp/cpp      — 无源性检测与修正
src/model/sparam_device.hpp/cpp   — SParamDevice 器件模型
tools/sparam_fit.py                — VF 调试/可视化工具
```

### 2.2 Touchstone 解析 (touchstone.hpp)

```cpp
struct TouchstoneData {
    uint32_t numPorts;
    std::vector<double> freqs;           // Hz
    std::vector<std::vector<Complex>> S;  // S[freq][port_i*N + port_j]
    double refImpedance;                  // 通常 50Ω
    std::string format;                   // "RI" / "MA" / "DB"
};

TouchstoneData parseTouchstone(const std::string& path);
```

- 支持格式：RI（实虚部）、MA（幅度角度°）、DB（dB 角度°）
- 自动检测端口数（.s1p/.s2p/.s3p.../.sNp）
- 频率单位解析（Hz/kHz/MHz/GHz）

### 2.3 S→Y 参数转换

```cpp
// S → Y 转换（每频率点）
// Y = (Z0^{-1}) * (I - S)^{-1} * (I + S) * Z0^{-1}
// 对角 Z0 矩阵（所有端口同 refImpedance）
std::vector<Complex> sToY(const std::vector<Complex>& S, uint32_t N, double Z0);
```

### 2.4 Vector Fitting (vector_fit.hpp)

```cpp
struct VFResult {
    std::vector<Complex> poles;    // p_k（实部 ≤0 保证因果性）
    std::vector<Complex> residues; // d_k（NxN 矩阵的留数）
    std::vector<Complex> constant; // d∞（NxN 矩阵）
    double rmsError;
};

// 对 Y(f) 做 VF 拟合
// Y(s) ≈ Σ_k d_k/(s - p_k) + d∞
VFResult vectorFit(const TouchstoneData& ts, uint32_t numPoles = 10);
```

**VF 算法步骤**：
1. 初始极点：在对数频率轴上均匀分布（虚部覆盖频段，实部为负小值）
2. 迭代求解线性方程组（留数 + 极点）
3. 极点重定位（Sk sanity check）
4. 收敛后输出极点-留数模型

**无源性修正**：
- 检查所有极点实部：若 Re(p_k) > 0，翻转 Re(p_k) → -Re(p_k)
- 重新计算留数使 Y(s) 保持无源：Y_passive = (Y + Y†)/2（Hermitian 部分取正定）

### 2.5 SParamDevice (sparam_device.hpp)

```cpp
class SParamDevice : public DeviceModel {
    std::vector<NodeId> nodes_;     // N 个端口节点
    uint32_t numPorts_;
    TouchstoneData sData_;           // 原始 S 参数数据
    VFResult vfResult_;              // VF 拟合结果
    // 瞬态状态（每极点一个状态变量 × N 端口）
    std::vector<double> poleStates_; // numPoles * numPorts

public:
    SParamDevice(name, nodes, touchstoneData);

    // AC: 按频率插值 S→Y
    std::vector<Complex> admittanceMatrix(double omega) const;

    // DC: Y(ω→0) 实部
    // eval() stamp Y_dc

    // Transient: VF companion model
    void evalTransient(op, out) override;
    bool hasTransientState() override { return true; }
    uint32_t transientStateSize() override { return numPoles * numPorts; }

    bool is_linear() override { return true; }
};
```

### 2.6 网表语法

新增器件字母 `'k'`（SPICE 中 K 通常用于耦合电感，但本仿真器未实现）：

```
* 2-port S-parameter element
K1 port1 port2 file="device.s2p" z0=50

* 3-port S-parameter element
K2 in out iso file="coupler.s3p" z0=50
```

- `file=` : Touchstone 文件路径
- `z0=` : 参考阻抗（默认 50Ω）
- 端口数 = 节点数（自动从 .sNp 文件检测）

### 2.7 集成点

| 模块 | 改动 |
|------|------|
| parser.cpp | `parseDevice`: 加 `'k'` 字母，变长节点收集（读到 `file=` 前都是节点）|
| device_factory.cpp | `buildDevice`: 加 `'k'` 分支，解析 file=，加载 Touchstone，做 VF |
| ac_analysis.cpp | 加 `SParamDevice*` 分支，调 `admittanceMatrix(omega)` stamp N×N Y 矩阵 |
| mna.cpp (DC) | 加 `SParamDevice*` 分支，stamp `Re(Y(ω→0))` |
| transient_assembly.cpp | 加 `SParamDevice*` 到 C/L 分支，调 `evalTransient` |

### 2.8 VF 瞬态 companion model

VF 结果：`Y(s) = Σ_k d_k/(s - p_k) + d∞`

每个极点 k 对应一个一阶 ODE：
```
s·x_k = p_k·x_k + d_k·V
I = Σ_k x_k + d∞·V
```

Backward Euler companion：
```
x_k[n] = (x_k[n-1] + dt·d_k·V[n]) / (1 - dt·p_k)
I[n] = Σ_k x_k[n] + d∞·V[n]
     = (Σ_k d_k/(1-dt·p_k)) · V[n]  +  Σ_k x_k[n-1]/(1-dt·p_k)  +  d∞·V[n]
```

等效导纳 `g_eq = Σ_k d_k/(1-dt·p_k) + d∞`，历史电流 `i_hist = Σ_k x_k[n-1]/(1-dt·p_k)`。

N 端口版：`d_k` 是 N×N 矩阵，`x_k` 是 N 维向量，`g_eq` 是 N×N 矩阵。

## 3. 实施步骤

### Phase 1: Touchstone 解析 + S→Y 转换 + AC 分析
1. `touchstone.hpp/cpp`: 解析 .sNp 文件
2. S→Y 转换函数
3. `sparam_device.hpp/cpp`: 基础器件 + `admittanceMatrix(omega)`
4. `parser.cpp` + `device_factory.cpp`: 加 `'k'` 字母
5. `ac_analysis.cpp`: 加 SParamDevice AC stamp
6. 测试: 2-port S2p 电路 AC 分析

### Phase 2: DC 分析
1. `sparam_device.cpp`: DC Y 矩阵（ω→0 外推）
2. `mna.cpp`: 加 SParamDevice DC stamp
3. 测试: S 参数器件 DC OP

### Phase 3: Vector Fitting
1. `vector_fit.hpp/cpp`: VF 算法实现
2. `passivity.hpp/cpp`: 无源性修正
3. `sparam_device.cpp`: VF 结果存储
4. 测试: VF 拟合精度验证

### Phase 4: 瞬态分析
1. `sparam_device.cpp`: VF companion model + 状态管理
2. `transient_assembly.cpp`: 加 SParamDevice 分支
3. 测试: S 参数器件 transient

### Phase 5: 集成测试
1. 混合电路：S 参数 + BSIM4 放大器
2. RF 电路：S 参数匹配网络 + LNA
3. 性能基准

## 4. 验证标准
- AC: S 参数器件的 Y 矩阵与 Touchstone 数据吻合（相对误差 < 1e-6）
- DC: Y(ω→0) 正确外推
- VF: 拟合 RMS 误差 < 1e-3
- 无源性: 所有极点 Re(p) ≤ 0
- 瞬态: companion model 正确（与 AC 在单频正弦激励下一致）
- 全量回归 104 PASS 不回归

## 5. 不做
- 多端口 Z0 不等（所有端口同 Z0）
- 噪声参数分析
- 温度依赖 S 参数
- 频域 HB 中的 S 参数（HB 走非线性路径，S 参数在 HB 中需要特殊处理）
