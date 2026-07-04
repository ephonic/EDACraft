// =====================================================================
// mom/green/branch/branch.hpp —— 支线积分（多段 DCIM，第二象限）
//
// 阶段 2.5 实现：
//   将谱域格林函数（减去准静态项与表面波极点后）沿采样路径用 GPOF/Prony
//   在多个区间分别拟合为复镜像指数项之和：G̃_res(k) ≈ Σ a_i e^{-b_i k}。
//   空域复镜像项：Σ a_i / (2 sqrt(ρ² + (b_i/j)²))。
//   多段（分段拟合）扩大有效 ρ 范围，克服单段 DCIM 在大 ρ 误差增长。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/poles.hpp"
#include <vector>

namespace mom::green::branch {

// 单个复镜像项：a * exp(-b * k)，由 GPOF/Prony 拟合得到。
struct ComplexImage {
    Complex amplitude{0.0, 0.0};  // a
    Complex alpha{0.0, 0.0};      // b（指数衰减/振荡系数）
};

// 多段 DCIM 拟合结果：每个采样区间给出其复镜像项集合。
struct MultiSegmentFit {
    std::vector<std::vector<ComplexImage>> segments; // 分段，每段若干指数项
};

// 对谱域核（已减极点贡献）做多段 DCIM 拟合。
//   sg       : 谱域求值器（返回减极点后的剩余核；调用方负责极点分离）
//   k_paths  : 每段的采样 k_rho 区间 [k_start, k_end]（复平面，Sommerfeld 路径）
//   n_seg_pts: 每段采样点数
//   n_images : 每段拟合的指数项数（模型阶数）
// 返回多段拟合。
MultiSegmentFit fit_branch_cut_dcim(
    const spectral::SpectralGreensFunction& sg,
    const std::vector<poles::Pole>& pole_list,
    const std::vector<std::pair<Complex, Complex>>& k_paths,
    int n_seg_pts, int n_images, bool use_phi = false, bool extract_qs = true);

// 由复镜像项计算空域格林函数（支线贡献部分）。
//   images : 复镜像集合
//   rho    : 横向距离
// 返回 Σ a_i / (2 sqrt(ρ² + α_i²))（α_i = b_i/j，复镜像深度）。
Complex spatial_from_images(const std::vector<ComplexImage>& images, Real rho);

// 谱域核的【准静态项】（大 k_rho 渐近）。对 z_src=z_obs 的同层源场：
//   G_A^{qs} ≈ 1/(2j k_z)，其中 k_z 为源层垂直波数。
// 减去它使剩余核平滑，便于 GPOF 指数拟合。
Complex quasi_static_GA(const spectral::SpectralGreensFunction& sg, Complex k_rho);

// 谱域核的【表面波极点项】之和：Σ_i R_i / (k_rho - k_{p,i})。
Complex pole_terms(const std::vector<poles::Pole>& pole_list, Complex k_rho);

// 提取后的剩余核：G_A - G_A^{qs} - Σ极点项。
//   use_phi : 若为真，用 G_phi 分量（标量势）；否则 G_A（矢量位）。
//   extract_qs : 是否提取准静态尾部。
//      true（默认）：减"直接+PEC镜像"自由空间尾部（ε=1 精确，ε≠1 大 kρ 失效）。
//      false：不减 QS，GPOF 拟合完整 G̃；此时 spatial_GA_reconstruct 须 include_qs=false。
//      多层（ε≠1）必须 false。
Complex residual_kernel(const spectral::SpectralGreensFunction& sg,
                        const std::vector<poles::Pole>& pole_list, Complex k_rho,
                        bool use_phi = false, bool extract_qs = true);

// —— 空域格林函数重构（三项闭式之和）——
// G_spatial(ρ) = 准静态项 + 极点留数项（汉克尔）+ DCIM 复镜像项。
// 每项的空域形式：
//   准静态：源层均匀介质自由空间格林 = 1/(4π) · 1/ρ（z_src=z_obs 时）。含 1/(4π)。
//   极点 i：(1/(4j)) · R_i · H_0^{(1)}(k_{p,i} ρ)   （surface-wave 圆柱波）
//   DCIM：  Σ a_i / (2·4π · sqrt(ρ² + (α_i/j)²))   （复镜像）
//
//   sg         : 谱域求值器（提供源层信息）
//   pole_list  : 表面波极点（含留数）
//   images     : DCIM 复镜像项
//   rho        : 横向距离
//   include_qs : 是否含准静态项（默认是）
//   phi_sign   : true 时为标量势（G_phi）镜像反号、极点反号（Dirichlet）
Complex spatial_GA_reconstruct(const spectral::SpectralGreensFunction& sg,
                               const std::vector<poles::Pole>& pole_list,
                               const std::vector<ComplexImage>& images,
                               Real rho, bool include_qs = true,
                               bool phi_sign = false);

} // namespace mom::green::branch
