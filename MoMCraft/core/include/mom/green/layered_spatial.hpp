// =====================================================================
// mom/green/layered_spatial.hpp —— 多层介质【空域】格林函数
//
// 阶段 3.1：通过对谱域核做数值 Sommerfeld 积分得到空域格林函数：
//   G(ρ) = (1/2π) ∫_0^∞ G̃(k_ρ) J_0(k_ρ ρ) k_ρ dk_ρ
// 这是【精确但慢】的空域格林函数，用于阶段 3 端到端验证。
// 后续可切换为阶段 2 的 DCIM 闭式（快）。
//
// 提供给 MoM 装配的「单核」接口（不区分 direct/image，直接给 G_A、G_phi）。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/green/spectral.hpp"
#include <functional>

namespace mom::green {

// 多层介质空域格林函数（数值 Sommerfeld 积分版）。
class LayeredSpatialGreen {
public:
    // 构造：给定谱域求值器、积分上界（k_rho_max，如 30*k0）、积分点数。
    LayeredSpatialGreen(spectral::SpectralGreensFunction sg,
                        Real k_rho_max_factor = 30.0, int n_points = 400);

    // 矢量位 G_A(ρ)：水平距离 ρ 处（z_src、z_obs 已在谱域求值器内固定）。
    Complex G_A(Real rho) const;
    // 标量势 G_phi(ρ)。
    Complex G_phi(Real rho) const;

private:
    // Sommerfeld 积分：(1/2π) ∫_0^∞ G̃(k_ρ) J0(k_ρ ρ) k_ρ dk_ρ
    Complex sommerfeld(std::function<Complex(Complex)> kernel, Real rho) const;

    spectral::SpectralGreensFunction sg_;
    Real k_rho_max_;
    int n_points_;
};

} // namespace mom::green
