// =====================================================================
// mom/mom/rwg_assembly.hpp —— RWG 基函数 MPIE 装配（M3 阶段）
//
// 三角对积分：对每对 RWG 基函数 (m,n)：
//   ZA[m,n] = ∫∫ f̄_m(r) · Ḡ_A(r,r') · f̄_n(r') dS dS'
//           = Σ_{(t_m,t_n)} ∫_{t_m} ∫_{t_n} f̄_m · Ḡ_A · f̄_n dS dS'
//   ZPhi[m,n] = ∫∫ (∇·f_m)(r) · G_phi(r,r') · (∇·f_n)(r') dS dS'
//
// 对水平并矢（同层 z=z'）：Ḡ_A 退化为 G_A·I_2x2（水平），
//   G_A(r,r') = G_A(ρ)，ρ = |r_xy - r'_xy|（水平距离）。
//
// 积分策略：
//   远场对（不相邻）：标准三角形 Gauss 规则。
//   近场/自场对：1/(4πρ) 解析提取 + 平滑残差数值积分。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/mesh/trimesh.hpp"
#include "mom/green/dyadic.hpp"
#include "mom/mom/efie.hpp"   // MPIEBlocks
#include <vector>
#include <functional>

namespace mom::mom {

// RWG 装配结果（同 MPIEBlocks 结构，兼容 build_impedance/build_aefie）
struct RwgMPIEBlocks {
    std::vector<Complex> ZA;     // nb × nb 行主序
    std::vector<Complex> ZPhi;   // nb × nb 行主序
};

// 装配 RWG MPIE 矩阵
//   mesh     : 三角网格（含 RWG 基函数）
//   green    : 空域并矢格林函数（水平电流版本）
//   gauss_order : 三角形 Gauss 积分阶（3-7）
RwgMPIEBlocks assemble_rwg(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5
);

// 加速版：用格林函数查找表替代每次精确求值（M6）
RwgMPIEBlocks assemble_rwg_fast(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5,
    Size n_lookup = 2000
);

/**
 * @brief pFFT 加速版 RWG 装配（O(N log N) 复杂度）
 * 
 * 使用预校正快速傅里叶变换 (pFFT) 加速远场计算，
 * 近场使用直接积分。适合大规模问题（N > 5000）。
 * 
 * @param mesh 三角形网格
 * @param green 并矢格林函数
 * @param gauss_order 高斯积分阶数
 * @param n_grid FFT 网格分辨率（0=自动）
 * @return RwgMPIEBlocks 包含 ZA 和 ZPhi 的阻抗块
 */
RwgMPIEBlocks assemble_rwg_pfft(
    const mesh::TriMesh& mesh,
    const green::dyadic::SpatialDyadic& green,
    int gauss_order = 5,
    Size n_grid = 0
);

// RwgMPIEBlocks → MPIEBlocks 转换（复用 build_impedance/schur）
inline MPIEBlocks to_mpie_blocks(const RwgMPIEBlocks& rwg) {
    MPIEBlocks blk;
    blk.ZA = rwg.ZA;
    blk.ZPhi = rwg.ZPhi;
    return blk;
}

// 专门为 RWG 基函数设计的阻抗构建函数。
//
// 标准 RWG-MPIE 中，ZA 和 ZPhi 的量纲不同：
//   ZA 量纲: m³  （f 无量纲，G_A 为 1/m，dS² 为 m⁴）
//   ZPhi 量纲: m （∇·f 为 1/m，G_phi 为 1/m，dS² 为 m⁴）
//
// 直接用 build_impedance 会因量纲不匹配导致 ZPhi 贡献过大。
// 本函数对每个基函数对 (m,n) 用边长归一化使两者量纲一致。
//
// Z[m,n] = jωμ₀·ZA[m,n]/(l_m·l_n) + (1/jωε₀)·ZPhi[m,n]/(l_m·l_n)
std::vector<Complex> build_rwg_impedance(const RwgMPIEBlocks& rwg,
                                          const mesh::TriMesh& mesh,
                                          Real omega);

// —— M5: A-EFIE for RWG ——
// 构建 RWG 的 Z_Λ 连续性约束矩阵。
// Z_Λ[m,n] = Σ_{t∈T_m∩T_n} div_m(t) · div_n(t) · ∫_t f̄_m dS
//   对 RWG，散度在每三角形常数 ±l/A，∫_t f̄_m dS 有闭式。
// 返回 nb×nb 行主序矩阵。
std::vector<Complex> build_rwg_lambda(const mesh::TriMesh& mesh);

// 构建 RWG A-EFIE 系统（复用 build_aefie 结构，但 Z_Λ 用 build_rwg_lambda）。
// 返回 AEFIESystem（2nb×2nb）。
AEFIESystem build_rwg_aefie(const RwgMPIEBlocks& blk, Real omega, Real eps_r,
                             const mesh::TriMesh& mesh);

} // namespace mom::mom
