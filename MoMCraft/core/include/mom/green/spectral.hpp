// =====================================================================
// mom/green/spectral/spectral.hpp —— 谱域格林函数（S-matrix 递推）
//
// 阶段 2.1：对平面分层介质，用广义反射系数（S-matrix）递推计算谱域并矢
// 格林函数 G_tilde(k_rho)，供空域 Sommerfeld 积分使用。
//
// 复平面结构（先验）：支割线在第二象限，极点（surface-wave）在第四象限。
// 谱域核在 k_rho 复平面解析（除支点 k_rho=±k_i 各层波数外）。
//
// 实现 Michalski-Zheng Formulation C 的递推（稳定）：
//   每层波数 k_i = omega*sqrt(mu0*eps0*eps_r_i*(1 - j*tand_i))
//   垂直波数 k_zi = sqrt(k_i^2 - k_rho^2)（支点选取 Im(k_zi)>=0）
//   界面广义反射系数自底向上/自顶向下递推。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/green/medium.hpp"   // DielectricLayer, Stackup（避免与 green.hpp 循环）
#include <vector>
#include <complex>
#include <limits>

namespace mom::green::spectral {

// Fresnel 反射系数（TM=true / TE=false）。自由函数。
Complex fresnel(Complex kz_a, Complex kz_b, Complex eps_a, Complex eps_b, bool TM);

// 谱域并矢格林函数分量（层状介质，点源在 z_src、场点在 z_obs）。
// 仅返回 MPIE 所需的标量核：矢量位 G_A（z 方向）、标量势 G_phi。
// 这是 k_rho 的函数；空域格林函数需对其做 Sommerfeld 积分。
struct SpectralKernel {
    Complex G_A{0.0, 0.0};     // 矢量位（水平分量）谱域核
    Complex G_phi{0.0, 0.0};   // 标量势谱域核
    Complex G_Azz{0.0, 0.0};   // 矢量位（z 分量 / TM 电压 TLGF）谱域核
    Complex G_Axz{0.0, 0.0};   // 矢量位（x-z 交叉耦合）谱域核
};

// 分层介质描述（自底向上）：底层可为半空间或 PEC 接地，顶层可为开放或 PEC 封闭。
struct LayeredMedium {
    std::vector<DielectricLayer> layers;   // 自底向上
    Real ground_z = 0.0;                    // 底面 z（PEC 接地）；NaN=无接地（底半空间）
    Real cover_z  = std::numeric_limits<Real>::quiet_NaN();  // 顶面 z（PEC 封闭）；NaN=开放（上侧半空间）
    // 源/场点 z 由调用方传入。
};

// 计算给定频率下，谱域核作为 k_rho 的函数（返回求值器）。
//   medium : 分层介质
//   freq   : 频率（Hz）
//   z_src  : 源点 z
//   z_obs  : 场点 z
// 返回一个可调用对象：给定复 k_rho 返回 SpectralKernel。
class SpectralGreensFunction {
public:
    SpectralGreensFunction(const LayeredMedium& medium, Real freq,
                           Real z_src, Real z_obs);

    // 在复 k_rho 处求值。自动处理支点选择（Im(k_zi)>=0）。
    SpectralKernel operator()(Complex k_rho) const;

    // 调试：返回 TM 极化的广义反射系数 (Rup_TM, Rdn_TM)。
    // 用于核对待数（surface-wave 极点出现在 1 - Rup*Rdn*phase = 0）。
    std::pair<Complex, Complex> debug_R_TM(Complex k_rho) const;

    // 源层垂直波数 k_z（供项提取/DCIM 使用）。
    Complex source_k_z(Complex k_rho) const;

    // 各层波数 k_i（复）。
    const std::vector<Complex>& layer_wave_numbers() const { return k_layers_; }
    Real omega() const { return omega_; }
    Real k0() const { return omega_ / phys::c0; }   // 真空波数
    Real z_src() const { return z_src_; }
    Real z_obs() const { return z_obs_; }
    const LayeredMedium& medium() const { return medium_; }

private:
    void compute_recursion();

    // 第 i 层垂直波数 k_zi（支点选择使衰减波 Im>=0）。
    Complex k_z(Index i, Complex k_rho) const;

    // 广义反射系数：Rup_TM（向上看，累积到顶空气）、Rdn_TM（向下看，到底 PEC）。
    // 公开供 debug_R_TM 复用。
    Complex generalized_refl_up_TM(Complex k_rho) const;
    Complex generalized_refl_dn_TM(Complex k_rho) const;
    // TE 极化（用于 G_phi 标量势）。
    Complex generalized_refl_up_TE(Complex k_rho) const;
    Complex generalized_refl_dn_TE(Complex k_rho) const;
    Complex generalized_refl_up_polar(Complex k_rho, bool TM) const;
    Complex generalized_refl_dn_polar(Complex k_rho, bool TM, bool pec_positive) const;

    LayeredMedium medium_;  // 改为值存储（避免引用悬挂）
    Real omega_;
    Real z_src_, z_obs_;
    std::vector<Complex> k_layers_;   // 每层波数
    std::vector<Real> z_interface_;   // 界面 z 坐标（自底向上，含顶/底半空间边界）
};

} // namespace mom::green::spectral
