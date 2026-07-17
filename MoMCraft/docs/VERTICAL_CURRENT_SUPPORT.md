# 垂直电流支持实现说明

## 概述

本次更新为 RWG 装配添加了垂直电流支持，使求解器能够处理过孔（via）、硅通孔（TSV）等三维结构。

## 关键变更

### 1. 网格系统 (trimesh.hpp/cpp)

**新增字段：**
```cpp
struct RwgBasis {
    // ... 现有字段 ...
    bool is_vertical = false;  // 标记是否为垂直边
};
```

**垂直边检测逻辑：**
```cpp
// 在 build_rwg_bases() 中
Real dz = std::abs(ep1.z - ep0.z);
Real dxy = std::sqrt((ep1.x - ep0.x)*(ep1.x - ep0.x) + 
                     (ep1.y - ep0.y)*(ep1.y - ep0.y));
basis.is_vertical = (dz > 0.5 * basis.edge_length);  // z 分量占主导
```

### 2. 并矢格林函数 (dyadic.hpp/cpp)

**新增方法：**
```cpp
struct SpatialDyadic {
    Complex GA(Real rho) const;    // 水平分量
    Complex GAzz(Real rho) const;  // 垂直分量（z 方向）
    Complex Gphi(Real rho) const;  // 标量势
    
    // 并矢点积
    Complex vector_dot(Real rho, 
                      Real fx, Real fy, Real fz,      // 源电流
                      Real fxp, Real fyp, Real fzp) const {  // 场电流
        return GA(rho) * (fx*fxp + fy*fyp) + GAzz(rho) * fz*fzp;
    }
};
```

**GAzz 实现：**
```cpp
Complex SpatialDyadic::GAzz(Real rho) const {
    // 当前简化实现：使用与 GA 相同的函数
    // TODO: 实现完整的 TM 电压 TLGF（G_P）
    return qwe::spatial_GA_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}
```

### 3. RWG 装配 (rwg_assembly.cpp)

**并矢格林函数使用：**
```cpp
// 矢量位贡献
Complex gA_val = green.GA(rho);
Complex gAzz_val = green.GAzz(rho);
if (is_singular) {
    gA_val -= singular_1_over_4pi_r(rho);
    gAzz_val -= singular_1_over_4pi_r(rho);
}

// 并矢点积：J̄·Ḡ_A·J̄' = G_A(ρ)·(fx·fx' + fy·fy') + G_Azz(ρ)·fz·fz'
Complex vec_contrib = gA_val * (fm.x*fn.x + fm.y*fn.y) +
                      gAzz_val * fm.z*fn.z;
sumA += vec_contrib * wm * wn;
```

## 物理意义

### 并矢格林函数

对于三维结构，电流可以有三个分量（x, y, z），因此需要完整的并矢格林函数：

```
Ḡ_A = [G_Axx  G_Axy  G_Axz]
      [G_Ayx  G_Ayy  G_Ayz]
      [G_Azx  G_Azy  G_Azz]
```

对于水平分层介质，非对角项为零，简化为：

```
Ḡ_A = [G_A    0    0  ]
      [0      G_A  0  ]
      [0      0    G_P]
```

其中：
- `G_A`：水平分量（现有实现）
- `G_P`：垂直分量（TM 电压 TLGF，待完整实现）

### 应用场景

1. **过孔（Via）**：连接不同层的垂直导体
2. **硅通孔（TSV）**：3D 封装中的垂直互连
3. **键合线（Bond Wire）**：芯片封装中的垂直连接
4. **垂直天线**：单极子天线等

## 当前限制

### GAzz 简化实现

当前 `GAzz` 使用与 `GA` 相同的函数，这是一个简化近似。完整的实现需要：

1. **TM 电压传输线格林函数（G_P）**
   - 考虑不同层之间的耦合
   - 处理垂直电流的边界条件

2. **层间耦合**
   - 当源和场在不同层时，需要计算层间耦合系数
   - 涉及多层反射和透射

### 后续工作

1. **实现完整的 G_P**
   - 参考 Michalski-Mosig 1997 论文
   - 实现 TM 电压 TLGF

2. **层间耦合计算**
   - 添加层索引到 RWG 基函数
   - 计算跨层耦合系数

3. **奇异积分**
   - 垂直边的奇异积分需要特殊处理
   - 可能需要 Duffy 变换或其他技术

## 测试用例

### 简单过孔结构

```python
# 创建过孔网格
mesh = TriMesh()

# 底部层（z=0）
mesh.add_vertex(0.0, 0.0, 0.0)
mesh.add_vertex(1.0, 0.0, 0.0)
mesh.add_vertex(0.5, 1.0, 0.0)

# 顶部层（z=1）
mesh.add_vertex(0.0, 0.0, 1.0)
mesh.add_vertex(1.0, 0.0, 1.0)
mesh.add_vertex(0.5, 1.0, 1.0)

# 添加三角形
mesh.add_triangle(0, 1, 2)  # 底部
mesh.add_triangle(3, 4, 5)  # 顶部

# 构建 RWG 基函数
mesh.build_rwg_bases()

# 检查垂直边
for i in range(mesh.num_bases()):
    if mesh.get_basis(i).is_vertical:
        print(f"基函数 {i} 是垂直的")
```

## 参考文献

1. Michalski, K. A., & Mosig, J. R. (1997). Multilayered media Green's functions in integral equation formulations. IEEE Transactions on Antennas and Propagation, 45(3), 508-519.

2. Rao, S. M., Wilton, D. R., & Glisson, A. W. (1982). Electromagnetic scattering by surfaces of arbitrary shape. IEEE Transactions on antennas and propagation, 30(3), 409-418.

3. Aksun, M. I. (1996). A robust approach for the derivation of closed-form Green's functions. IEEE Transactions on Microwave Theory and Techniques, 44(5), 651-658.
