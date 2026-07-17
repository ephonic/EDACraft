// =====================================================================
// mom/green/qwe.hpp —— Quadrature-with-Extrapolation (QWE) Sommerfeld 积分
//
// 参考：Key (2011) "Is the fast Hankel transform faster than quadrature?"
//   geo2011-0237.  算法：J1 零点分段 + 固定阶 Gauss-Legendre + Shanks/Wynn
//   ε 外推。可处理慢收敛/轻度发散积分。
//
// 对屏蔽微带，配合【尾部提取】使用：
//   - ε=1：减去 direct + PEC image（解析空域闭式），残差~0。
//   - ε≠1：减去大 kρ 渐近 C_tail/(2kz)，C_tail=-(1+R∞)/R∞，R∞=(ε-1)/(ε+1)。
//   残差在实轴有界衰减，QWE 可靠收敛。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/poles.hpp"
#include <functional>
#include <complex>
#include <memory>
#include <vector>

namespace mom::green::qwe {

// QWE 求积：F(r) = ∫₀^∞ f(λ)·J0(λr)·λ dλ。
//   f        : 谱域核（残差，实轴+j·微小偏置求值）
//   r        : 横向距离
//   n_intervals : J1 零点分段数
//   gauss_order : 每段 Gauss-Legendre 点数
//   rtol/atol   : Shanks 外推收敛容差
//   branch_points: 额外的分段边界（谱域支点 k0、k1 等），用于在 cusp 处细分 Gauss 段。
// 返回 F(r)（复数）。
Complex qwe_hankel(const std::function<Complex(Real)>& f, Real r,
                   int n_intervals = 60, int gauss_order = 7,
                   Real rtol = 1e-9, Real atol = 1e-14,
                   const std::vector<Real>& branch_points = {});

// 表面波极点项空域贡献：residue·(-j·k_p/2)·H_0^{(2)}(k_p·ρ)
//   用于从 QWE 残差积分中提取的极点，解析加上其空域贡献。
Complex surface_wave_spatial(Complex residue, Complex k_pole, Real rho);

// 完整空域格林 G_A(ρ)：尾部解析 + QWE 残差。
//   自动按 ε 选择尾部提取形式（ε=1：direct+PEC image；ε≠1：C_tail/(2kz)）。
Complex spatial_GA_qwe(const spectral::SpectralGreensFunction& sg,
                       Real rho, Real eps_r,
                       int n_intervals = 60, int gauss_order = 7);

// 带表面波极点提取的 QWE 空域格林（高频厚介质必需）。
Complex spatial_GA_qwe_poles(const spectral::SpectralGreensFunction& sg,
                              Real rho, Real eps_r,
                              const std::vector<poles::Pole>& pole_list,
                              int n_intervals = 60, int gauss_order = 7);

// 完整空域标量势 G_phi(ρ)：尾部解析 + QWE 残差（G_phi 用 TE 反射 + 1/ε）。
Complex spatial_Gphi_qwe(const spectral::SpectralGreensFunction& sg,
                         Real rho, Real eps_r,
                         int n_intervals = 60, int gauss_order = 7);

// —— 加速版：谱核缓存 + 插值（empymod 风格）——
//
// 预计算：在密集 log-λ 网格上采样谱核残差 G̃(λ) - tail(λ)，构造样条。
// 对每个 ρ，QWE 断点处用样条插值取值（避免重复谱核求值）。
// 适合装配中 N² 次 Green 调用（只需 1 次网格采样）。
class CachedQWE {
public:
    CachedQWE(const spectral::SpectralGreensFunction& sg, Real eps_r,
              Real lambda_min, Real lambda_max, int n_grid = 2000,
              int n_intervals = 60, int gauss_order = 7);
    // G_A(ρ)（尾部解析 + 残差 QWE，残差用缓存样条）
    Complex GA(Real rho) const;
    // G_phi(ρ)
    Complex Gphi(Real rho) const;
private:
    struct Impl;
    std::shared_ptr<Impl> impl_;
};

} // namespace mom::green::qwe
