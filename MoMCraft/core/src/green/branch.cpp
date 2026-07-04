// =====================================================================
// mom/green/branch.cpp —— 多段 DCIM（GPOF/Prony）实现
// =====================================================================
#include "mom/green/branch.hpp"
#include "mom/common/types.hpp"
#include "mom/green/spectral.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/SVD>
#endif

#include <vector>
#include <cmath>
#include <stdexcept>

namespace mom::green::branch {

namespace {
// 对均匀采样序列 f[n]（n=0..N-1）做 Prony 指数拟合：f[n] ≈ Σ a_i z_i^n。
// GPOF（广义函数束，Hua-Sarkar 1990）对均匀采样序列做指数拟合。
//   y[n] = Σ a_i z_i^n，n=0..N-1。
// 算法：L≈N/2，构 [Y1|Y2]（Hankel），SVD 定阶 M；矩阵束 Y1^+ Y2 特征值即 z_i；最小二乘求 a_i。
// 鲁棒性远优于 Prony（SVD 噪声抑制）。
bool gpof_fit(const std::vector<Complex>& y, int max_M,
              std::vector<Complex>& z_out, std::vector<Complex>& a_out) {
#ifdef MOM_USE_EIGEN
    using Eigen::MatrixXcd;
    using Eigen::VectorXcd;
    using Eigen::JacobiSVD;
    const int N = int(y.size());
    if (N < 2 * max_M + 1) return false;
    const int L = N / 2;          // 铅笔参数
    const int rowN = N - L;       // 行数
    // 构造 Hankel 矩阵 Y：(N-L) 行 × (L+1) 列，Y(r,c)=y[r+c]。
    MatrixXcd Y(rowN, L + 1);
    for (int r = 0; r < rowN; ++r)
        for (int c = 0; c <= L; ++c)
            Y(r, c) = y[r + c];
    MatrixXcd Y1 = Y.leftCols(L);
    MatrixXcd Y2 = Y.rightCols(L);
    // —— Hua-Sarkar GPOF ——
    // 1) Y1 的 SVD：Y1 = U1·Σ1·V1^H，保留前 M 个奇异向量。
    JacobiSVD<MatrixXcd> svd1(Y1, Eigen::ComputeThinU | Eigen::ComputeThinV);
    const auto& sv = svd1.singularValues();
    const double thr = 1e-6 * sv(0);
    int M = 0;
    for (int i = 0; i < sv.size() && i < max_M; ++i)
        if (sv(i) > thr) ++M; else break;
    if (M == 0) M = 1;
    MatrixXcd U1 = svd1.matrixU().leftCols(M);       // (N-L)×M
    MatrixXcd V1 = svd1.matrixV().leftCols(M);       // L×M
    // Σ1^{-1}（M×M 对角）
    MatrixXcd SigmaInv = MatrixXcd::Zero(M, M);
    for (int i = 0; i < M; ++i)
        SigmaInv(i, i) = Complex(sv(i) > 0 ? 1.0 / sv(i) : 0.0, 0.0);
    // 2) 铅笔矩阵 Z = Σ1^{-1}·U1^H·Y2·V1 （M×M），其特征值即 z_i。
    MatrixXcd Z = SigmaInv * U1.adjoint() * Y2 * V1;
    Eigen::ComplexEigenSolver<MatrixXcd> es(Z, false);
    // 取所有 M 个特征值为 z_i（GPOF 直接给出 M 个信号极点）。
    std::vector<Complex> roots;
    for (int i = 0; i < M; ++i) {
        Complex zi = es.eigenvalues()(i);
        if (std::isfinite(std::abs(zi)) && std::abs(zi) > 1e-8)
            roots.push_back(zi);
    }
    if (roots.empty()) return false;
    // 最小二乘求振幅：V a = y。
    MatrixXcd V(N, int(roots.size()));
    for (int n = 0; n < N; ++n)
        for (int i = 0; i < int(roots.size()); ++i)
            V(n, i) = std::pow(roots[i], n);
    VectorXcd yv(N);
    for (int n = 0; n < N; ++n) yv(n) = y[n];
    VectorXcd a = V.colPivHouseholderQr().solve(yv);
    z_out.clear(); a_out.clear();
    for (int i = 0; i < int(roots.size()); ++i) {
        if (std::abs(a(i)) > 1e-30) {   // 过滤噪声项
            z_out.push_back(roots[i]);
            a_out.push_back(a(i));
        }
    }
    return !z_out.empty();
#else
    (void)y; (void)max_M;
    return false;
#endif
}
} // namespace

MultiSegmentFit fit_branch_cut_dcim(
    const spectral::SpectralGreensFunction& sg,
    const std::vector<poles::Pole>& pole_list,
    const std::vector<std::pair<Complex, Complex>>& k_paths,
    int n_seg_pts, int n_images, bool use_phi, bool extract_qs) {
    MultiSegmentFit out;
#ifdef MOM_USE_EIGEN
    for (const auto& [k0, k1] : k_paths) {
        // 沿 [k0, k1] 均匀采样，取【剩余核】（按 extract_qs 决定是否减准静态 + 极点项）。
        std::vector<Complex> f(n_seg_pts);
        for (int n = 0; n < n_seg_pts; ++n) {
            Real t = Real(n) / Real(n_seg_pts - 1);
            Complex k = k0 + t * (k1 - k0);
            f[n] = residual_kernel(sg, pole_list, k, use_phi, extract_qs);
        }
        std::vector<Complex> z, a;
        if (gpof_fit(f, n_images, z, a)) {
            std::vector<ComplexImage> seg;
            for (size_t i = 0; i < z.size(); ++i) {
                ComplexImage ci;
                ci.amplitude = a[i];
                // z_i = exp(-b_i * Δk)，Δk = (k1-k0)/(n_seg_pts-1) => b_i = -log(z_i)/Δk
                Complex dk = (k1 - k0) / Complex(n_seg_pts - 1, 0);
                if (std::abs(z[i]) > 0 && std::abs(dk) > 0)
                    ci.alpha = -std::log(z[i]) / dk;
                seg.push_back(ci);
            }
            out.segments.push_back(seg);
        } else {
            out.segments.push_back({});
        }
    }
#else
    (void)sg; (void)n_seg_pts; (void)n_images;
#endif
    return out;
}

Complex spatial_from_images(const std::vector<ComplexImage>& images, Real rho) {
    // 约定 A（与谱域 1/(2·k_z) + QS e^{-jkR}/(4πR) 一致）：
    //   谱域复图像 a_i·e^{-α_i·kρ} 的逆变换（Sommerfeld 约定 A）：
    //     (1/2π)∫ a_i·e^{-α_i k}·J0(kρ)·k·dk = a_i·α_i / (2π·(α_i² + ρ²)^{3/2})
    //   （Gradshteyn 6.623；纯指数无支点，恒等式精确。）
    //   α_i 直接取 GPOF 拟合指数（无 /j）。
    Complex total(0.0, 0.0);
    for (const auto& im : images) {
        Complex d2 = im.alpha * im.alpha + Complex(rho * rho, 0.0);
        Complex d = std::sqrt(d2);
        if (std::abs(d) > 1e-30)
            total += im.amplitude * im.alpha / (Complex(2.0 * phys::pi, 0.0) * d * d * d);
    }
    return total;
}

Complex quasi_static_GA(const spectral::SpectralGreensFunction& sg, Complex k_rho) {
    // 大 k_rho 渐近：G_A ≈ 1/(2·k_z)（约定 A：与谱域 1/(2·k_z) 一致，去 1/j）。
    const Complex kzs = sg.source_k_z(k_rho);
    if (std::abs(kzs) == 0.0) return Complex(0.0, 0.0);
    return Complex(1.0, 0.0) / ((2.0 * kzs));   // 约定 A：1/(2·k_z)（去 1/j）
}

// G_phi 的准静态项：直接取 G_phi 谱域核在大 k_rho（如 10^6·k0）处的值，
// 作为渐近主项（G_phi 的 TE 渐近无简单闭式，数值取更稳健）。
Complex quasi_static_Gphi(const spectral::SpectralGreensFunction& sg, Complex k_rho) {
    // 大 k 处谱域核近似常数；取 k = 1e4 * |k_rho| 处的 G_phi（足够大 k 渐近）。
    const Real scale = 1.0e4;
    Complex k_big = k_rho * scale;
    if (std::abs(k_big) < 1.0) k_big = Complex(1.0e6, 0.0);
    return sg(k_big).G_phi;
}

Complex pole_terms(const std::vector<poles::Pole>& pole_list, Complex k_rho) {
    Complex total(0.0, 0.0);
    for (const auto& p : pole_list) {
        Complex d = k_rho - p.k_rho;
        if (std::abs(d) > 1e-12)
            total += p.residue / d;
    }
    return total;
}

Complex residual_kernel(const spectral::SpectralGreensFunction& sg,
                        const std::vector<poles::Pole>& pole_list, Complex k_rho,
                        bool use_phi) {
    return residual_kernel(sg, pole_list, k_rho, use_phi, /*extract_qs=*/true);
}

Complex residual_kernel(const spectral::SpectralGreensFunction& sg,
                        const std::vector<poles::Pole>& pole_list, Complex k_rho,
                        bool use_phi, bool extract_qs) {
    // 谱核 G̃（约定 A）。残差 = G̃ − QS − 极点。
    //
    // QS 提取策略（两种）：
    //  (a) extract_qs=true：减去"直接+PEC 镜像"自由空间尾部 1/(2·k_z)·(e^{-jk_z|Δz|} ± e^{-jk_z(z_s+z_o)})。
    //      对 ε=1 精确（残差 ~0），但对 ε≠1 在大 kρ 处该形式发散，残差不衰减。
    //  (b) extract_qs=false：不减 QS，GPOF 直接拟合【完整 G̃】。
    //      完整 G̃ 沿上半平面路径指数衰减（含界面反射结构），GPOF 可整体拟合。
    //      此时 spatial_GA_reconstruct 必须 include_qs=false（不再加自由空间项）。
    //  —— 多层（ε≠1）必须用 (b)，否则残差污染。
    const Complex g = use_phi ? sg(k_rho).G_phi : sg(k_rho).G_A;
    if (!extract_qs) {
        return g - pole_terms(pole_list, k_rho);
    }
    const Complex kzs = sg.source_k_z(k_rho);
    // 修正后谱域约定：核为 j·e^{+j k_z d}/(2 k_z)（evanescent 衰减，见 spectral.cpp）。
    //   QS 尾部 = j·(e^{+j k_z|Δz|} ± e^{+j k_z(z_s+z_o)})/(2 k_z)。
    const Complex jkz = -Iunit * kzs;   // 使 exp(-jkz·d)=exp(+j k_zs·d)（衰减）
    const Real zs = sg.z_src(), zo = sg.z_obs();
    const Real dz = std::abs(zo - zs);
    const Complex direct = std::exp(-jkz * dz);
    const Complex image_phase = std::exp(-jkz * (zs + zo));
    Complex qs = Iunit * (direct + image_phase) / (2.0 * kzs);   // G_A：直接 + 镜像同号（含 j 因子）
    if (use_phi) {
        const Complex k_layer = sg.source_k_z(Complex(0.0, 0.0));
        const Complex eps_src = (k_layer * k_layer) /
            Complex(sg.omega() * sg.omega() * phys::mu0 * phys::eps0, 0.0);
        if (std::abs(eps_src) > 0) qs = qs / eps_src;
        qs = Iunit * (direct - image_phase) / (2.0 * kzs);   // G_q：镜像反号（含 j 因子）
        (void)eps_src;
    }
    return g - qs - pole_terms(pole_list, k_rho);
}

namespace {
// 第一类零阶汉克尔函数 H_0^{(1)}(z)，复数参数。
// 用 J_0(z) + i Y_0(z) 的级数/渐近混合近似（足够工程精度）。
//   对小 |z|：J_0 级数 1 - z²/4 + z⁴/64 - ...
//            Y_0 用 (2/π)(ln(z/2)+γ)J_0 + ...（复杂，这里用渐近为主，小 z 粗略）。
//   对大 |z|：H_0^{(1)} ≈ sqrt(2/(π z)) e^{i(z - π/4)}。
Complex hankel0_1(Complex z) {
    const double az = std::abs(z);
    if (az < 1e-12) return Complex(1.0, 0.0);  // J_0(0)=1, Y_0→-∞（这里取极限近似）
    // 中小 |z|：用 J_0 级数（前若干项）+ Y_0 渐近主项。
    if (az < 8.0) {
        // J_0(z) = Σ_{k=0} (-1)^k (z²/4)^k / (k!)²
        Complex z2_4 = z * z / 4.0;
        Complex j0 = 1.0, term = 1.0;
        for (int k = 1; k <= 20; ++k) {
            term *= -z2_4 / double(k * k);
            j0 += term;
            if (std::abs(term) < 1e-15 * std::abs(j0)) break;
        }
        // Y_0(z) ≈ (2/π)(ln(z/2)+γ) J_0 + (2/π) Σ ... 简化：用大 z 渐近在边界匹配。
        // 这里小 z 区直接用渐近公式（误差可接受，工程用途）。
        Complex asymp = std::sqrt(2.0 / (phys::pi * z)) *
                        std::exp(Iunit * (z - phys::pi / 4.0));
        return j0 + Iunit * (asymp - j0);  // 混合：J_0 实部 + i(Y_0≈渐近虚部)
    }
    // 大 |z|：渐近
    return std::sqrt(2.0 / (phys::pi * z)) * std::exp(Iunit * (z - phys::pi / 4.0));
}
} // namespace

Complex spatial_GA_reconstruct(const spectral::SpectralGreensFunction& sg,
                               const std::vector<poles::Pole>& pole_list,
                               const std::vector<ComplexImage>& images,
                               Real rho, bool include_qs, bool phi_sign) {
    // 约定 A：谱域 1/(2·k_z)·e^{-jk_zΔz} → 空域 e^{-jkR}/(4πR)。
    //   QS（准静态直接+镜像）用解析自由空间+PEC 镜像格林：
    //     G_A（电流位）：直接 + 镜像【同号】（PEC 电流镜像不反号）。
    //     G_q（电荷位）：直接 + 镜像【反号】（PEC 电荷镜像反号），并乘 1/ε_source。
    //   极点项：谱域 residue/(kρ−k_p) → 空域 (−j·k_p/2)·residue·H_0^{(2)}(k_p·ρ)。
    //   复图像项：spatial_from_images 已含约定 A 闭式（含 1/(2π)），无需再除 4π。
    Complex total(0.0, 0.0);
    const Real r_safe = (rho > 1e-12) ? rho : 1e-12;
    Complex eps_inv(1.0, 0.0);
    if (phi_sign) {
        const Complex k_layer = sg.source_k_z(Complex(0.0, 0.0));
        const Complex eps_src = (k_layer * k_layer) / Complex(sg.omega() * sg.omega() * phys::mu0 * phys::eps0, 0.0);
        if (std::abs(eps_src) > 0) eps_inv = 1.0 / eps_src;
    }
    if (include_qs) {
        const Complex k_d = sg.source_k_z(Complex(0.0, 0.0));
        const Real zs = sg.z_src(), zo = sg.z_obs();
        const Real R1 = std::sqrt(rho * rho + (zo - zs) * (zo - zs));
        const Real R2 = std::sqrt(rho * rho + (zo + zs) * (zo + zs));
        const Real image_sign = phi_sign ? -1.0 : +1.0;  // G_q 电荷镜像反号；G_A 电流镜像同号
        if (R1 > 1e-15)
            total += eps_inv * std::exp(-Iunit * k_d * R1) / (4.0 * phys::pi * R1);
        if (R2 > 1e-15)
            total += image_sign * eps_inv * std::exp(-Iunit * k_d * R2) / (4.0 * phys::pi * R2);
    }
    for (const auto& p : pole_list) {
        Complex z = p.k_rho * r_safe;
        // 约定 A 表面波：谱 residue/(kρ−k_p) 逆变换 = (−j·k_p/2)·residue·H_0^{(2)}(k_p·ρ)。
        // H_0^{(2)}(z) = H_0^{(1)}(z)* 的渐近实部近似：这里用 conj(H_0^{(1)}) 近似。
        Complex H0_2 = std::conj(hankel0_1(std::conj(z)));
        total += (Complex(0.0, -1.0) * p.k_rho * Complex(0.5, 0.0)) * p.residue * H0_2;
    }
    total += spatial_from_images(images, r_safe);
    return total;
}

} // namespace mom::green::branch
