# 多端口、复杂三维结构 S 参数提取扩展计划

> 基于 Method of Moments (MoM) 多层介质格林函数的互连线 S 参数提取工具
> 当前状态：1D 单导体微带线，1-64 GHz，Touchstone 输出
> 目标：支持任意三维导体结构（多根耦合线、过孔、三维互连）+ 多端口 S 参数

---

## 1. 现状评估

### ✅ 已完成（可直接复用）

| 组件 | 状态 | 3D 复用性 |
|------|------|----------|
| 谱域格林函数（TM/TE 反射 + S 矩阵递归） | 精确（所有 ε）| 需扩展为并矢 |
| QWE 空域积分（J1 零点 + Shanks 外推） | 验证 1-64 GHz | 核心算法复用 |
| 两级 Aksun 尾部提取 | 32GHz 物理正确 | 需按并矢分量复制 |
| 表面波极点提取（Chew 搜索 + Hankel 空域） | 64GHz 验证 | 复用 |
| Schur N-端口降阶 | 4-端口验证 | **完全复用** |
| Z→S 变换 | 通用 | **完全复用** |
| 密集 LU 求解 | 通用 | **签名复用**（需 pFFT 加速）|
| Stackup/DielectricLayer | 层状介质定义 | **完全复用** |
| Touchstone .sNp 读写 | RI/MA/DB | **完全复用** |

### ❌ 关键瓶颈（需重写）

1. **网格**：仅 `RectMesh`（单根矩形带，1D rooftop 基函数）
2. **格林函数 API**：`SpatialGreenFn = function<Complex(Real rho)>`（标量径向）
3. **装配**：硬编码 x-segment + y-width 积分循环
4. **A-EFIE Z_Λ**：硬编码三对角（1D rooftop 散度）
5. **端口模型**：`port.hpp` 仅有 stub

---

## 2. 分阶段实施计划

### 阶段 M1：三角网格 + RWG 基函数（核心基础设施）

**目标**：用三角形网格替代矩形网格，支持任意平面/三维导体表面。

**新增组件**：

```
core/include/mom/mesh/trimesh.hpp
core/src/mesh/trimesh.cpp
```

**数据结构**：

```cpp
struct Vertex { Real x, y, z; };
struct Triangle {
    Index v[3];        // 顶点索引
    Index layer_idx;   // 所在介质层
    Real area;
    Vec3 normal;
    Vec3 centroid;
};
struct RWGBasis {
    Index edge;         // 内边索引
    Index t_plus;       // 正三角形
    Index t_minus;      // 负三角形
    Index v_free_plus;  // 正三角形自由顶点
    Index v_free_minus; // 负三角形自由顶点
    Real edge_length;
    // RWG 形函数：f(r) = ±(l/(2A))(r - v_free) on t±
};
struct TriMesh {
    std::vector<Vertex> vertices;
    std::vector<Triangle> triangles;
    std::vector<RWGBasis> bases;  // 内边 → RWG 基函数

    // 从外部网格导入（gmsh JSON / STL / 自定义）
    static TriMesh from_gmsh(const std::string& filename);
    static TriMesh from_stl(const std::string& filename);
    // 矩形带快捷构造（兼容旧 RectMesh 用法）
    static TriMesh rectangle_strip(Real x0, Real x1, Real y0, Real y1,
                                    Real z, int nx, int ny);
    // 多根平行线
    static TriMesh multi_strip(const std::vector<Rect>& strips, int nx, int ny);
};
```

**RWG 基函数**：
- `rwg_shape(basis, r) -> Vec3`：三角形上线性矢量函数
- `rwg_div(basis) -> Real`：面散度（每三角形常数 ±l/A）
- 自适应数值积分（三角形上的 Gauss 规则）
- 奇异处理：Duffy 变换 / Khayat-Wilton 三角形对 1/R 积分

**工作量**：~800 行 C++

**验证**：单根微带线（`rectangle_strip`）结果与现有 `RectMesh` 对比。

---

### 阶段 M2：并矢格林函数（3D 电流方向）

**目标**：从标量 G_A(ρ) 扩展到并矢 Ḡ_A(r,r')，支持任意方向电流。

**原理**：Michalski-Zheng Formulation III（全并矢）：

```
谱域核（并矢）：
  G̃_Axx(kρ) = G̃_A  (水平 x 电流 → x 矢量位)
  G̃_Ayy(kρ) = G̃_A  (水平 y 电流 → y 矢量位，同 G̃_Axx 因各向同性)
  G̃_Azz(kρ) = G̃_P  (垂直 z 电流 → z 矢量位)
  G̃_phi(kρ) = G̃_phi (标量势)
  交叉项 G̃_Axz, G̃_Azx（水平-垂直耦合，过孔场景需要）
```

**新增**：

```cpp
// core/include/mom/green/dyadic.hpp
struct SpectralDyadic {
    Complex G_Axx, G_Ayy, G_Azz;  // 对角并矢
    Complex G_Axz, G_Azx;          // 交叉项（z≠z' 时非零）
    Complex G_phi;                  // 标量势
};

class DyadicGreensFunction {
    const LayeredMedium& medium;
    Real freq;
    Complex z_src, z_obs;
    SpectralDyadic operator()(Complex k_rho) const;
};

// 空域并矢格林（QWE 每个分量分别积分）
struct SpatialDyadic {
    Complex G_Axx(Real rho), G_Ayy(Real rho), G_Azz(Real rho);
    Complex G_Axz(Real rho), G_phi(Real rho);
    // 每个分量用 QWE + 尾部提取（复用现有逻辑）
};
```

**关键**：
- 同层（z_src = z_obs）：G_Axx = G_Ayy = 标量 G_A（现有），G_Azz = G_P（垂直），G_Axz = 0。
- 跨层（过孔）：G_Axz ≠ 0，需要 Michalski Formulation III 的完整 5 核公式。
- QWE 核心算法（J1 零点 + Shanks）完全复用，仅新增分量。

**工作量**：~600 行 C++（谱域并矢 300 + 空域 QWE 包装 300）

**验证**：水平电流（z_src=z_obs）退化到现有标量结果。

---

### 阶段 M3：RWG MPIE 装配（核心装配重写）

**目标**：用三角形对积分替代矩形对积分，装配 RWG 基函数的 MPIE 矩阵。

**接口**：

```cpp
// core/include/mom/mom/rwg_assembly.hpp
MPIEBlocks assemble_rwg(
    const TriMesh& mesh,
    const SpatialDyadic& green,   // 并矢空域格林
    int gauss_order               // 三角形 Gauss 积分阶
);
```

**关键实现**：

1. **三角形对 Gauss 积分**：
   - 远场对（不相邻）：标准三角形 Gauss 规则（Dunavant 点）。
   - 近场对（共享边/顶点）：Duffy 变换消除 1/R 奇异。
   - 自场对（同一三角形对）：解析 + Duffy。

2. **奇异提取**：
   - `G(ρ) ≈ 1/(4πρ) + [G(ρ) - 1/(4πρ)]`
   - 1/(4πρ) 部分：三角形对解析积分（已发表闭式，如 Sieber et al.）。
   - 平滑残差：Gauss 数值积分。

3. **并矢积分**：
   - 每个基函数对 (m,n)：计算 `∫∫ f̄_m·Ḡ_A·f̄_n dS dS'` 和 `∫∫ (∇·f_m)·G_phi·(∇·f_n) dS dS'`。
   - f̄ 是矢量（RWG），Ḡ_A 是并矢 → 点积后标量。

**工作量**：~1000 行 C++（积分框架 400 + 奇异处理 400 + 并矢装配 200）

**验证**：单根微带线 RWG vs RectMesh Z 矩阵对比。

---

### 阶段 M4：多端口定义 + delta-gap 激励

**目标**：支持任意位置/方向的端口（不仅限于传输线两端）。

**新增**：

```cpp
// core/include/mom/port/port.hpp（扩展现有 stub）
struct Port {
    std::string name;
    Real z0;                      // 参考阻抗
    std::vector<Index> edge_set;  // RWG 内边集合（定义端口截面）
    Vec3 direction;               // 端口参考方向（delta-gap 法向）
    Real position[3];             // 端口位置（参考面）
};

// 多端口 delta-gap 激励 → S 参数
std::vector<Complex> extract_sparams_multiport(
    const MPIEBlocks& blk,
    const std::vector<Port>& ports,
    Real omega
);
```

**实现**：
- 每个端口：在 edge_set 上的 RWG 基函数施加 delta-gap 电压。
- Schur N-端口降阶（复用现有 `schur_nport_export`）。
- 端口阻抗矩阵 → S 参数（复用 `zport_n_to_sparam`）。

**工作量**：~300 行 C++

---

### 阶段 M5：A-EFIE RWG 扩展（低频稳定性）

**目标**：将 A-EFIE 的 Z_Λ 从硬编码三对角扩展为 RWG 散度的数值积分。

**修改**：

```cpp
// build_aefie 中 Z_Λ 块：
// 旧：hardcoded ±1/2（1D rooftop 散度）
// 新：Z_Λ[m,n] = ∫ f̄_m · (∇_s · f̄_n) dS  （RWG 面散度）
//   对 RWG，∇·f_n 在每三角形上是常数 ±l_n/A_n
//   Z_Λ[m,n] = Σ_{t∈T_m∩T_n} ±l_n/A_n · ∫_{t} f̄_m dS
```

**工作量**：~200 行 C++（数值 Z_Λ 装配）

---

### 阶段 M6：pFFT 加速（大规模求解）

**目标**：从 O(N³) 密集 LU 加速到 O(N log N) 迭代求解，支持 N > 3000。

**新增**：

```
core/include/mom/solver/pfft.hpp  （扩展现有 stub）
core/src/solver/pfft.cpp
```

**原理**：
- RWG 基函数 + 多层格林 → Toeplitz 块结构。
- 预校正 FFT：在均匀网格上插值，FFT 卷积，预校正近场。
- 迭代求解器（GMRES）+ pFFT 矩阵向量乘。

**工作量**：~1500 行 C++（pFFT 核心 800 + 近场校正 400 + GMRES 300）

**验证**：N=500 单根线，pFFT vs 密集 LU 结果对比。

---

### 阶段 M7： gmsh 网格导入 + Python API

**目标**：从 gmsh 导入任意几何，提供高层 Python API。

**新增**：

```python
# py/mom/structure.py
class Structure:
    def __init__(self, mesh_file: str, medium: Stackup):
        """从 gmsh .msh 文件导入几何"""
        ...

    def add_port(self, name: str, edges: list[int], z0: float = 50.0):
        """添加端口（RWG 内边集合）"""
        ...

    def solve(self, freq: float) -> np.ndarray:
        """单频求解 → S 参数"""
        ...

    def sweep(self, freqs: np.ndarray) -> np.ndarray:
        """扫频 → S 参数序列"""
        ...

    def to_touchstone(self, filename: str, freqs: np.ndarray):
        """扫频 + Touchstone 输出"""
        ...
```

**工作量**：~500 行 C++ + 300 行 Python

---

## 3. 依赖关系

```
M1 (三角网格+RWG) ──► M3 (RWG 装配) ──► M5 (A-EFIE RWG)
                   │                    │
                   │                    ├──► M4 (多端口)
                   │                    │
M2 (并矢格林) ─────┘                    ├──► M6 (pFFT)
                                        │
                                        └──► M7 (gmsh + Python API)
```

- M1 和 M2 可并行开发。
- M3 依赖 M1 + M2。
- M4、M5、M6、M7 依赖 M3。

---

## 4. 总工作量估计

| 阶段 | 内容 | C++ 行数 | Python 行数 | 预计工时 |
|------|------|---------|------------|---------|
| M1 | 三角网格 + RWG | 800 | 0 | 2-3 周 |
| M2 | 并矢格林函数 | 600 | 0 | 1-2 周 |
| M3 | RWG MPIE 装配 | 1000 | 0 | 3-4 周 |
| M4 | 多端口定义 | 300 | 0 | 1 周 |
| M5 | A-EFIE RWG | 200 | 0 | 0.5 周 |
| M6 | pFFT 加速 | 1500 | 0 | 4-6 周 |
| M7 | gmsh + Python | 500 | 300 | 1-2 周 |
| **合计** | | **~4900** | **~300** | **13-19 周** |

---

## 5. 里程碑验证标准

| 里程碑 | 验证标准 |
|--------|---------|
| M1 完成 | `rectangle_strip` 构造的 RWG 网格，基函数数 = 2·nx·ny（对比 1D nx-1）|
| M2 完成 | 同层水平电流退化到现有标量 G_A（relerr < 1e-6）|
| M3 完成 | 单根微带线 RWG vs RectMesh Z[0,0] 对比（relerr < 1%）|
| M4 完成 | 2 端口 S 参数 vs 现有 solve_qwe_sparam_fast（relerr < 5%）|
| M5 完成 | A-EFIE 低频（1 MHz）条件数 vs 标准 EFIE 改善 > 10× |
| M6 完成 | N=500 pFFT vs dense LU（relerr < 1%，速度 10×+）|
| M7 完成 | gmsh 导入任意 L 形/V 形导体 → S 参数 → Touchstone |

---

## 6. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 三角网格格式 | gmsh `.msh` 4.1 | 行业标准，开源，Python/C++ API |
| RWG 奇异积分 | Duffy 变换 | 标准方法，数值稳定 |
| pFFT | Anderson 级数 pFFT | 成熟方法，原计划已包含 |
| 并矢格林 | Michalski Formulation III | 支持 z 电流（过孔）|
| 迭代求解 | GMRES + ILU 预条件 | 通用，鲁棒 |
| gmsh 接口 | gmsh C++ API / 文件解析 | 灵活 |

---

## 7. 与现有代码的兼容性

- **保留** `RectMesh` + `assemble_mpie_single`（阶段 1 验证用，向后兼容）。
- **保留** 标量 `SpectralGreensFunction`（水平电流专用，快速路径）。
- **新增** `TriMesh` + `assemble_rwg` + `DyadicGreensFunction`（3D 通用路径）。
- Python API 同时支持两种模式（`Microstrip` 旧接口 + `Structure` 新接口）。

---

## 8. 应用场景

扩展后可处理的结构：

1. **多根耦合微带线**：差分对、共面波导、耦合线滤波器。
2. **过孔（via）**：多层 PCB 通孔、盲孔、埋孔（需 z 方向电流 = 并矢 G_Azz）。
3. **三维互连**：键合线、倒装焊凸点、TSV。
4. **任意平面天线**：微带贴片、缝隙天线（需辐射模式）。
5. **电磁兼容**：PCB 走线耦合、屏蔽腔体谐振。

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| RWG 奇异积分实现复杂 | 先用数值积分（高阶 Gauss），后优化解析 |
| 并矢格林 5 核公式复杂 | 先实现水平电流 2 核（G_Axx + G_phi），后加垂直 |
| pFFT 大规模工程 | 先密集 LU 验证正确性，后加 pFFT 加速 |
| gmsh 依赖 | 先自定义网格，后接 gmsh |
| 性能瓶颈 | 分阶段优化，先正确后快速 |
