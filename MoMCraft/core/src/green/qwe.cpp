// =====================================================================
// mom/green/qwe.cpp —— QWE (Quadrature-with-Extrapolation) Sommerfeld 积分
//
// Key (2011) geo2011-0237: J1 零点分段 + Gauss-Legendre + Shanks/Wynn ε 算法。
// =====================================================================
#include "mom/green/qwe.hpp"
#include "mom/common/quadrature.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/branch.hpp"   // pole_terms

#include <cmath>
#include <vector>
#include <stdexcept>
#include <algorithm>

namespace mom::green::qwe {

namespace {

// 零阶贝塞尔 J0(x)（级数，足够精度）。
double bessel_J0(double x) {
    double x2_4 = (x * x) / 4.0;
    double j0 = 1.0, term = 1.0;
    for (int k = 1; k <= 40; ++k) {
        term *= -x2_4 / double(k * k);
        j0 += term;
        if (std::abs(term) < 1e-17 * std::abs(j0)) break;
    }
    return j0;
}

// 复参数 J0（级数，用于表面波极点的 H0^(2) 计算）
Complex bessel_J0_complex(Complex z) {
    Complex z2_4 = (z * z) / 4.0;
    Complex j0(1.0, 0.0), term(1.0, 0.0);
    for (int k = 1; k <= 60; ++k) {
        term *= -z2_4 / Complex(double(k * k), 0);
        j0 += term;
        if (std::abs(term) < 1e-16 * std::abs(j0)) break;
    }
    return j0;
}

// 复参数 Y0（Neumann 函数）。
//   Y0(z) = (2/π)(ln(z/2)+γ)J0(z) + (2/π)·Σ_{k≥1} (-1)^{k+1}·H_k·(z/2)^{2k}/(k!)²
//   其中 H_k 是第 k 调和数，γ=0.5772。
Complex bessel_Y0_complex(Complex z) {
    const double gamma = 0.5772156649015329;
    Complex z2_4 = (z * z) / 4.0;
    Complex J0 = bessel_J0_complex(z);
    Complex sum(0, 0);
    Complex term(1, 0);   // (z/2)^{2k} / (k!)² 的第 k 项，从 k=0
    double Hk = 0;         // 调和数
    for (int k = 1; k <= 60; ++k) {
        term *= -z2_4 / Complex(double(k * k), 0);
        Hk += 1.0 / double(k);
        Complex tk = term * Complex(Hk, 0) * Complex((k % 2 == 1) ? 1.0 : -1.0, 0);
        sum += tk;
        if (std::abs(tk) < 1e-16 * (std::abs(sum) + 1e-30)) break;
    }
    Complex ln = std::log(z / 2.0);
    return (Complex(2.0 / phys::pi, 0)) * ((ln + Complex(gamma, 0)) * J0 + sum);
}

// H0^(2)(z) = J0(z) - j·Y0(z)
Complex hankel0_2(Complex z) {
    return bessel_J0_complex(z) - Iunit * bessel_Y0_complex(z);
}

// 一阶贝塞尔 J1(x)（级数）。
double bessel_J1(double x) {
    // J1(x) = Σ (-1)^k (x/2)^{2k+1} / (k!(k+1)!)
    double x2_4 = (x * x) / 4.0;
    double j1 = 0.5 * x, term = 0.5 * x;   // k=0
    for (int k = 1; k <= 40; ++k) {
        term *= -x2_4 / (double(k) * double(k + 1));
        j1 += term;
        if (std::abs(term) < 1e-17 * std::abs(j1)) break;
    }
    return j1;
}

// J1 的第 n 个正零点（n≥1）。用 asymptotic 初值 + Newton-Raphson。
// empymod 用此法（transform.py L200-218）。
// 【缓存】J1 零点对所有调用相同，缓存避免重复 Newton-Raphson。
std::vector<double> j1_zeros(int n) {
    static std::vector<double> cached;
    if (int(cached.size()) >= n) {
        return std::vector<double>(cached.begin(), cached.begin() + n);
    }
    // 扩展缓存到 n
    for (int i = int(cached.size()); i < n; ++i) {
        double a = (double(i) + 1.25) * phys::pi;
        double zi = a;
        // Newton-Raphson: z_{k+1} = z_k - J1(z)/J1'(z), J1'=J0-J1/z·... 用 J1'/ = J0 - J1/z
        // 简化用 Jv(2,z) 关系：J1'(z) = J0(z) - J1(z)/z
        for (int iter = 0; iter < 20; ++iter) {
            double j1 = bessel_J1(zi);
            double j0 = bessel_J0(zi);
            double jp = j0 - j1 / zi;          // J1'(z)
            double step = j1 / jp;
            zi -= step;
            if (std::abs(step) < 1e-14 * zi) break;
        }
        cached.push_back(zi);
    }
    return std::vector<double>(cached.begin(), cached.begin() + n);
}

// Shanks/Wynn ε 算法：返回最佳外推（最深偶数列首元素）。
Complex shanks_wynn(const std::vector<Complex>& S) {
    const int n = int(S.size());
    if (n == 0) return Complex(0, 0);
    if (n == 1) return S[0];
    // ε 表：ε[0]=S, ε[1]=1/差分, ε[k]=ε[k-2][i+1]+1/(ε[k-1][i+1]-ε[k-1][i])
    // 用 vector<vector>，外层 k，内层 i。
    std::vector<std::vector<Complex>> eps;
    eps.push_back(S);                                          // ε[0]
    {
        std::vector<Complex> col;
        for (int i = 0; i + 1 < n; ++i) {
            Complex d = S[i + 1] - S[i];
            col.push_back(std::abs(d) > 1e-300 ? Complex(1.0, 0) / d : Complex(1e300, 0));
        }
        eps.push_back(col);                                    // ε[1]
    }
    int k = 2;
    while (int(eps[k - 1].size()) >= 2) {
        const auto& p1 = eps[k - 1];
        const auto& p2 = eps[k - 2];
        std::vector<Complex> col;
        for (int i = 0; i + 1 < int(p1.size()); ++i) {
            Complex d = p1[i + 1] - p1[i];
            col.push_back(p2[i + 1] + (std::abs(d) > 1e-300 ? Complex(1.0, 0) / d : Complex(0, 0)));
        }
        eps.push_back(col);
        ++k;
        if (k > n + 2) break;
    }
    // 最深偶数列首元素
    for (int kk = int(eps.size()) - 1; kk >= 0; --kk) {
        if ((kk % 2 == 0) && !eps[kk].empty()) {
            Complex v = eps[kk][0];
            if (std::isfinite(v.real()) && std::isfinite(v.imag())) return v;
        }
    }
    return S.back();
}

} // namespace

// 表面波极点空域贡献（匿名 namespace 外，供 spatial_GA_qwe_poles 用）
Complex surface_wave_spatial(Complex residue, Complex k_pole, Real rho) {
    Complex z = k_pole * rho;
    if (std::abs(z) < 1e-10) return Complex(0, 0);
    Complex H0 = hankel0_2(z);
    return Complex(0, -0.5) * residue * k_pole * H0;
}

Complex qwe_hankel(const std::function<Complex(Real)>& f, Real r,
                   int n_intervals, int gauss_order,
                   Real rtol, Real atol,
                   const std::vector<Real>& branch_points) {
    // rho 过小时 J1 零点/r 发散，积分数值病态。用 floor 保护
    // （装配中 rho→0 由解析奇异提取处理，QWE 残差在 rho=0 极限有限）。
    // floor 取 ~0.1·dx 量级（dx≈0.5mm → floor≈5e-5）。
    if (r < 1e-4) r = 1e-4;
    // J1 零点分段：breakpoints = [0, j_{1,1}/r, j_{1,2}/r, ...]
    auto zeros = j1_zeros(n_intervals + 1);
    // Gauss-Legendre 节点/权重
    const GaussRule g = gauss_legendre(gauss_order);

    std::vector<Complex> partial_sums;
    partial_sums.reserve(n_intervals + 1);
    Complex S(0, 0);
    Complex prev_extrap(0, 0);
    bool have_prev = false;

    Real a = 0.0;
    for (int i = 0; i <= n_intervals; ++i) {
        Real b = zeros[i] / r;
        // 在每个 J1 段内，若段跨越了给定的支点/极点，细分以保证每段在单一解析叶上。
        // （支点处谱函数有 cusp/不连续，单一 Gauss 段无法捕捉。）
        std::vector<Real> sub;
        sub.push_back(a);
        for (Real bp : branch_points) {
            if (bp > a + 1e-9 && bp < b - 1e-9) sub.push_back(bp);
        }
        sub.push_back(b);
        Complex Fi(0, 0);
        for (size_t s = 0; s + 1 < sub.size(); ++s) {
            Real sa = sub[s], sb = sub[s+1];
            Real half = 0.5 * (sb - sa);
            for (Size j = 0; j < g.nodes.size(); ++j) {
                Real lam = 0.5 * (sa + sb) + half * g.nodes[j];
                Complex fv = f(lam);
                Fi += fv * bessel_J0(lam * r) * lam * (g.weights[j] * half);
            }
        }
        S += Fi;
        partial_sums.push_back(S);
        a = b;

        // 每 few 步检查 Shanks 收敛
        if (i >= 8) {
            Complex extrap = shanks_wynn(partial_sums);
            if (have_prev) {
                Real delta = std::abs(extrap - prev_extrap);
                if (delta <= rtol * std::abs(extrap) + atol) {
                    return extrap;
                }
            }
            prev_extrap = extrap;
            have_prev = true;
        }
    }
    return shanks_wynn(partial_sums);
}

Complex spatial_GA_qwe(const spectral::SpectralGreensFunction& sg,
                       Real rho, Real eps_r,
                       int n_intervals, int gauss_order) {
    const Real k0 = sg.k0();
    const Real k1 = k0 * std::sqrt(eps_r);
    const Real h = sg.z_src();   // 层厚（源在微带表面 z=h，底 z=0）
    const Real tiny = 1e-8 * k0;              // 实轴上方微小偏置（避免支点奇异）
    // rho 过小（装配近场奇异区，含 rho=0 与 rho~1e-13）：
    //   必须返回【完整尾部含 1/(4πρ) 奇异】，与装配 singular_at(rho)=1/(4πρ) 抵消。
    //   （DCIM spatial_GA_reconstruct 也是返回含奇异的完整格林，rho→0 时 ~1/(4πρ)。）
    //   rho=0 时 1/0=inf，但装配极少传 rho=0（dxr=0→rho=0 同点，singular_at(0)=0，
    //   此时 inf-0=inf 会导致问题）→ 用 r_safe 防 inf，但 singular_at 也对 rho<1e-15 返回 0，
    //   故对 rho<1e-15 返回有限平滑极限（singular_at 不减，解析自势补偿）。
    if (rho < 1e-5) {
        if (rho < 1e-15) {
            // rho→0：模仿 green_direct 的自点抑制（直接项 1/(4πρ) 置 0），
            //   仅返回镜像/交叉项（有限）。装配的奇异提取 + 解析自势会补回直接项。
            //   与 solve_freespace_single_z0 的 green_direct(R<1e-30)=0 行为一致。
            if (std::abs(eps_r - 1.0) < 1e-12) {
                const Real R2 = 2*h;
                return std::exp(-Iunit*k1*R2) / (4*phys::pi*R2);   // 仅 PEC 镜像项
            }
            // ε≠1：近场主项 C_tail/(4πρ) 置 0，返回 0（残差在 rho→0 也→0）
            return Complex(0, 0);
        }
        // 1e-15 ≤ rho < 1e-5：完整尾部（含 1/(4πρ)，与 singular_at 抵消）
        if (std::abs(eps_r - 1.0) < 1e-12) {
            const Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
            return (std::exp(-Iunit*k1*rho)/rho + std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
        }
        // ε≠1 近场主项：修正后渐近系数 (1+R∞)（正），不再是旧的 -(1+R∞)/R∞（负且 ε→1 发散）。
        const Real Rinf = (eps_r - 1)/(eps_r + 1);
        const Real C_tail_re = (1.0 + Rinf);
        return C_tail_re * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
    }

    Complex G_tail(0, 0);
    std::function<Complex(Real)> resid_spec;

    if (std::abs(eps_r - 1.0) < 1e-12) {
        // ε=1：尾部 = direct + PEC image（精确闭式）
        //   修正后（见 spectral.cpp）谱域核为 j·e^{+j k_z d}/(2 k_z)，其逆变换 = e^{-jkR}/(2R)。
        //   ε=1 谱域 G_A = j·(1+e^{+j k_z·2h})/(2 k_z)（Ru=0, Rd=+1, dz=0），
        //   逆变换 = [e^{-jk1 ρ}/ρ + e^{-jk1 R2}/R2]/2 → 除 2π 后与下方 G_tail 一致。
        const Real R1 = rho;
        const Real R2 = std::sqrt(rho * rho + (2 * h) * (2 * h));
        G_tail = (std::exp(-Iunit * k1 * R1) / R1
                  + std::exp(-Iunit * k1 * R2) / R2) / (4 * phys::pi);
        resid_spec = [&](Real lam) -> Complex {
            Complex lam_c(lam, tiny);
            Complex g = sg(lam_c).G_A;
            Complex kz = sg.source_k_z(lam_c);
            // 谱域尾部（与修正后 G_A 同约定）：j·(1+e^{+j k_z·2h})/(2 k_z)
            Complex qs = Iunit * (Complex(1, 0) + std::exp(Iunit * kz * 2.0 * h)) / (2.0 * kz);
            Complex r = g - qs;
            if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
            return r;
        };
    } else {
        // ε≠1：准静态尾部提取（最稳健）。
        //   谱域格林大 kρ 渐近（已验证，见 spectral.cpp）：Re → (1+R∞)/(2 k_z1)。
        //   尾部 qs = j·(1+R∞)/(2 k_z1)，其空域逆变换 = (1+R∞)·e^{-jk1 ρ}/(4π ρ)。
        //   这样残差在大 kρ 处趋于 0（实部精确抵消），虚部（辐射）由 QWE 数值积分。
        //   不再使用两级 Aksun（旧法在 kρ=k0 处 kz2=0 分支点除零，且中等 kρ 失配）。
        const Real Rinf = (eps_r - 1) / (eps_r + 1);
        const Real C_tail_re = (1.0 + Rinf);
        G_tail = C_tail_re * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
        resid_spec = [&](Real lam) -> Complex {
            Complex lam_c(lam, tiny);
            Complex g = sg(lam_c).G_A;
            Complex kz = sg.source_k_z(lam_c);
            // 谱域尾部（含 j）：j·C_tail_re/(2 k_z1)
            Complex qs = Iunit * C_tail_re / (2.0 * kz);
            Complex r = g - qs;
            if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
            return r;
        };
    }

    Complex F = qwe_hankel(resid_spec, rho, n_intervals, gauss_order, 1e-9, 1e-14, {k0, k1});
    return G_tail + F / (2 * phys::pi);
}

// 带表面波极点提取的 QWE 空域格林
Complex spatial_GA_qwe_poles(const spectral::SpectralGreensFunction& sg,
                              Real rho, Real eps_r,
                              const std::vector<poles::Pole>& pole_list,
                              int n_intervals, int gauss_order) {
    const Real k0 = sg.k0();
    const Real k1 = k0 * std::sqrt(eps_r);
    const Real h = sg.z_src();
    const Real tiny = 1e-8 * k0;

    // 小 rho 处理（同 spatial_GA_qwe）
    if (rho < 1e-5) {
        if (rho < 1e-15) {
            if (std::abs(eps_r - 1.0) < 1e-12) {
                const Real R2 = 2*h;
                return std::exp(-Iunit*k1*R2) / (4*phys::pi*R2);
            }
            return Complex(0, 0);
        }
        if (std::abs(eps_r - 1.0) < 1e-12) {
            const Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
            return (std::exp(-Iunit*k1*rho)/rho + std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
        }
        // ε≠1 近场主项（修正后正系数）
        const Real Rinf = (eps_r - 1)/(eps_r + 1);
        const Real C_tail_re = (1.0 + Rinf);
        return C_tail_re * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
    }

    Complex G_tail(0, 0);
    std::function<Complex(Real)> resid_spec;

    if (std::abs(eps_r - 1.0) < 1e-12) {
        const Real R1 = rho;
        const Real R2 = std::sqrt(rho * rho + (2 * h) * (2 * h));
        G_tail = (std::exp(-Iunit * k1 * R1) / R1
                  + std::exp(-Iunit * k1 * R2) / R2) / (4 * phys::pi);
        resid_spec = [&](Real lam) -> Complex {
            Complex lam_c(lam, tiny);
            Complex g = sg(lam_c).G_A;
            Complex kz = sg.source_k_z(lam_c);
            // 修正后谱域尾部：j·(1+e^{+j k_z·2h})/(2 k_z)
            Complex qs = Iunit * (Complex(1, 0) + std::exp(Iunit * kz * 2.0 * h)) / (2.0 * kz);
            Complex r = g - qs - branch::pole_terms(pole_list, lam_c);
            if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
            return r;
        };
    } else {
        // ε≠1：准静态尾部提取 + 极点（见 spatial_GA_qwe 注释）
        const Real Rinf = (eps_r - 1) / (eps_r + 1);
        const Real C_tail_re = (1.0 + Rinf);
        G_tail = C_tail_re * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
        resid_spec = [&](Real lam) -> Complex {
            Complex lam_c(lam, tiny);
            Complex g = sg(lam_c).G_A;
            Complex kz = sg.source_k_z(lam_c);
            Complex qs = Iunit * C_tail_re / (2.0 * kz);
            Complex r = g - qs - branch::pole_terms(pole_list, lam_c);
            if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
            return r;
        };
    }

    Complex F = qwe_hankel(resid_spec, rho, n_intervals, gauss_order, 1e-9, 1e-14, {k0, k1});
    Complex result = G_tail + F / (2 * phys::pi);

    // 加表面波极点空域贡献
    for (const auto& p : pole_list) {
        result += surface_wave_spatial(p.residue, p.k_rho, rho);
    }
    return result;
}

Complex spatial_Gphi_qwe(const spectral::SpectralGreensFunction& sg,
                         Real rho, Real eps_r,
                         int n_intervals, int gauss_order) {
    const Real k0 = sg.k0();
    const Real k1 = k0 * std::sqrt(eps_r);
    const Real h = sg.z_src();
    const Real tiny = 1e-8 * k0;
    // rho 过小：同 G_A 处理（rho<1e-15 平滑极限，否则完整尾部）。
    // G_phi 现用 TM 反射（电荷），与 G_A 同结构（PEC 电荷镜像反号 + 1/ε）。
    // ε=1：G_phi = G_A，尾部 = direct - PEC image（精确，残差~0）。
    // ε≠1：修正后大 kρ 渐近 (1+R∞)/(2ε·kz)（正，与 G_A 一致后除 ε）。
    if (std::abs(eps_r - 1.0) < 1e-12) {
        if (rho < 1e-5) {
            if (rho < 1e-15) {
                const Real R2 = 2*h;
                return -std::exp(-Iunit*k1*R2) / (4*phys::pi*R2);
            }
            const Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
            return (std::exp(-Iunit*k1*rho)/rho - std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
        }
        const Real R1 = rho;
        const Real R2 = std::sqrt(rho * rho + (2 * h) * (2 * h));
        Complex G_tail = (std::exp(-Iunit * k1 * R1) / R1
                          - std::exp(-Iunit * k1 * R2) / R2) / (4 * phys::pi);
        std::function<Complex(Real)> resid_spec = [&](Real lam) -> Complex {
            Complex lam_c(lam, tiny);
            Complex g = sg(lam_c).G_phi;
            Complex kz = sg.source_k_z(lam_c);
            // 修正后谱域尾部：j·(1 - e^{+j k_z·2h})/(2 k_z)（电荷镜像反号）
            Complex qs = Iunit * (Complex(1, 0) - std::exp(Iunit * kz * 2.0 * h)) / (2.0 * kz);
            Complex r = g - qs;
            if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
            return r;
        };
        Complex F = qwe_hankel(resid_spec, rho, n_intervals, gauss_order, 1e-9, 1e-14, {k0, k1});
        return G_tail + F / (2 * phys::pi);
    }

    // ε≠1：与 G_A 一致的"direct + PEC image"尾部结构（镜像反号，标量势），
    //   系数 (1+R∞)/ε。这样 ε→1 时连续过渡到 ε=1 分支（不再用单 1/ρ 项导致不连续）。
    const Real Rinf = (eps_r - 1)/(eps_r + 1);
    const Real C_tail_re = (1.0 + Rinf);
    const Real eps_inv = 1.0/eps_r;

    if (rho < 1e-5) {
        if (rho < 1e-15) {
            // rho→0：仅镜像项（有限，反号）
            const Real R2 = 2*h;
            return -C_tail_re * eps_inv * std::exp(-Iunit*k1*R2) / (4*phys::pi*R2);
        }
        const Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
        return C_tail_re * eps_inv *
               (std::exp(-Iunit*k1*rho)/rho - std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
    }

    const Real R1 = rho;
    const Real R2 = std::sqrt(rho * rho + (2 * h) * (2 * h));
    Complex G_tail = C_tail_re * eps_inv *
                     (std::exp(-Iunit*k1*R1)/R1 - std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
    std::function<Complex(Real)> resid_spec = [&](Real lam) -> Complex {
        Complex lam_c(lam, tiny);
        Complex g = sg(lam_c).G_phi;
        Complex kz = sg.source_k_z(lam_c);
        // 谱域尾部（含 j，镜像反号）：j·C_tail_re·eps_inv·(1 - e^{+j k_z·2h})/(2 k_z)
        Complex qs = Iunit * C_tail_re * eps_inv *
                     (Complex(1, 0) - std::exp(Iunit * kz * 2.0 * h)) / (2.0 * kz);
        Complex r = g - qs;
        if (!std::isfinite(r.real()) || !std::isfinite(r.imag())) return Complex(0, 0);
        return r;
    };

    Complex F = qwe_hankel(resid_spec, rho, n_intervals, gauss_order, 1e-9, 1e-14, {k0, k1});
    return G_tail + F / (2 * phys::pi);
}

// =====================================================================
// CachedQWE：谱核缓存 + 线性插值加速（empymod 风格）
// =====================================================================
struct CachedQWE::Impl {
    const spectral::SpectralGreensFunction* sg;
    Real eps_r, k0, k1, h, tiny;
    Real C_tail;
    Real Rinf;
    Complex a1, a2;    // 两级 Aksun 系数（ε≠1）
    bool is_eps1;
    // 谱核残差缓存（log 网格）：lambda_grid[i], resid_A[i], resid_phi[i]
    std::vector<Real> lam_grid;          // 实轴 λ 网格（对数均匀）
    std::vector<Complex> resid_A;        // G̃_A - tail(λ) 在 λ 处
    std::vector<Complex> resid_phi;      // G̃_phi - tail(λ)
    int n_intervals, gauss_order;
    std::vector<double> j1z;             // J1 零点（缓存）

    Complex interp(const std::vector<Complex>& data, Real lam) const {
        // 在 log 网格上线性插值（复数实/虚分别）
        if (lam <= lam_grid.front()) return data.front();
        if (lam >= lam_grid.back()) return Complex(0, 0);   // 远场残差→0
        // 二分查找
        auto it = std::lower_bound(lam_grid.begin(), lam_grid.end(), lam);
        int i = int(it - lam_grid.begin()) - 1;
        if (i < 0) i = 0;
        Real x0 = lam_grid[i], x1 = lam_grid[i+1];
        Real t = (lam - x0) / (x1 - x0);
        return data[i] * (1 - t) + data[i+1] * t;
    }

    Complex tail_GA(Real rho) const {
        if (rho < 1e-15) {
            if (is_eps1) {
                Real R2 = 2*h;
                return std::exp(-Iunit*k1*R2) / (4*phys::pi*R2);
            }
            return Complex(0, 0);
        }
        if (is_eps1) {
            Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
            return (std::exp(-Iunit*k1*rho)/rho + std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
        }
        // ε≠1 准静态尾部：C_tail·e^{-jk1ρ}/(4πρ)
        return C_tail * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
    }
    Complex tail_Gphi(Real rho) const {
        Real ei = 1.0/eps_r;
        if (rho < 1e-15) {
            if (is_eps1) { Real R2=2*h; return -std::exp(-Iunit*k1*R2)/(4*phys::pi*R2); }
            return C_tail * ei * Complex(0,-k1) / (4*phys::pi);
        }
        if (is_eps1) {
            Real R2 = std::sqrt(rho*rho + (2*h)*(2*h));
            return (std::exp(-Iunit*k1*rho)/rho - std::exp(-Iunit*k1*R2)/R2) / (4*phys::pi);
        }
        return C_tail * ei * std::exp(-Iunit*k1*rho) / (4*phys::pi*rho);
    }
};

CachedQWE::CachedQWE(const spectral::SpectralGreensFunction& sg, Real eps_r,
                     Real lambda_min, Real lambda_max, int n_grid,
                     int n_intervals, int gauss_order)
    : impl_(std::make_shared<Impl>()) {
    impl_->sg = &sg;
    impl_->eps_r = eps_r;
    impl_->k0 = sg.k0();
    impl_->k1 = impl_->k0 * std::sqrt(eps_r);
    impl_->h = sg.z_src();
    impl_->tiny = 1e-8 * impl_->k0;
    impl_->is_eps1 = (std::abs(eps_r - 1.0) < 1e-12);
    impl_->Rinf = (eps_r - 1)/(eps_r + 1);
    // 准静态尾部系数（修正后正，ε→1 时→2，不再发散）。
    impl_->C_tail = (1.0 + impl_->Rinf);
    impl_->a1 = Complex(0,0); impl_->a2 = Complex(0,0);  // 准静态尾部不再用两级 Aksun
    impl_->n_intervals = n_intervals;
    impl_->gauss_order = gauss_order;

    // J1 零点（缓存，供 qwe_hankel 用）—— 此处不直接用，qwe_hankel 内部算
    // 构建对数均匀 λ 网格（覆盖装配中所有 ρ 的断点范围）
    Real lmin = std::log(std::max(lambda_min, 1e-6 * impl_->k0));
    Real lmax = std::log(lambda_max);
    impl_->lam_grid.resize(n_grid);
    impl_->resid_A.resize(n_grid);
    impl_->resid_phi.resize(n_grid);
    for (int i = 0; i < n_grid; ++i) {
        Real t = Real(i) / Real(n_grid - 1);
        Real lam = std::exp(lmin + t * (lmax - lmin));
        impl_->lam_grid[i] = lam;
        Complex lam_c(lam, impl_->tiny);
        Complex gA = sg(lam_c).G_A;
        Complex gP = sg(lam_c).G_phi;
        Complex kz = sg.source_k_z(lam_c);
        Complex rA, rP;
        if (impl_->is_eps1) {
            // 修正后谱域尾部：j·(1 ± e^{+j k_z·2h})/(2 k_z)
            Complex qsA = Iunit * (Complex(1,0) + std::exp(Iunit*kz*2.0*impl_->h)) / (2.0*kz);
            Complex qsP = Iunit * (Complex(1,0) - std::exp(Iunit*kz*2.0*impl_->h)) / (2.0*kz);
            rA = gA - qsA; rP = gP - qsP;
        } else {
            // ε≠1 准静态尾部：j·C_tail/(2 kz1)
            Real ei = 1.0/eps_r;
            rA = gA - Iunit * impl_->C_tail / (2.0*kz);
            rP = gP - Iunit * impl_->C_tail * ei / (2.0*kz);
        }
        if (!std::isfinite(rA.real()) || !std::isfinite(rA.imag())) rA = Complex(0,0);
        if (!std::isfinite(rP.real()) || !std::isfinite(rP.imag())) rP = Complex(0,0);
        impl_->resid_A[i] = rA;
        impl_->resid_phi[i] = rP;
    }
}

Complex CachedQWE::GA(Real rho) const {
    if (rho < 1e-5) return impl_->tail_GA(rho);
    Complex G_tail = impl_->tail_GA(rho);
    // QWE 用插值的残差核
    auto f = [&](Real lam){ return impl_->interp(impl_->resid_A, lam); };
    Complex F = qwe_hankel(f, rho, impl_->n_intervals, impl_->gauss_order, 1e-9, 1e-14, {impl_->k0, impl_->k1});
    return G_tail + F / (2*phys::pi);
}

Complex CachedQWE::Gphi(Real rho) const {
    if (rho < 1e-5) return impl_->tail_Gphi(rho);
    Complex G_tail = impl_->tail_Gphi(rho);
    auto f = [&](Real lam){ return impl_->interp(impl_->resid_phi, lam); };
    Complex F = qwe_hankel(f, rho, impl_->n_intervals, impl_->gauss_order, 1e-9, 1e-14, {impl_->k0, impl_->k1});
    return G_tail + F / (2*phys::pi);
}

} // namespace mom::green::qwe
