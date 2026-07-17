// =====================================================================
// mom/green/poles.cpp —— Chew 极点搜索 + 柯西留数实现
// =====================================================================
#include "mom/green/poles.hpp"
#include "mom/green/spectral.hpp"
#include "mom/common/types.hpp"

#include <cmath>
#include <complex>
#include <vector>
#include <algorithm>

namespace mom::green::poles {

namespace {
// 复核求值（取 G_A 分量，surface-wave 极点在 A 与 phi 同位）。
Complex eval_GA(const spectral::SpectralGreensFunction& sg, Complex kr) {
    return sg(kr).G_A;
}
} // namespace

std::vector<Pole> find_surface_wave_poles(
    const spectral::SpectralGreensFunction& sg,
    Real k_min, Real k_max, Real im_max, int grid_n) {
    // 第四象限：Re∈[k_min, k_max]，Im∈[-im_max, 0]（Im<0）。
    // 极点处 G̃→∞，故 |1/G̃|→0。在网格上找 |1/G̃| 的局部极小（候选极点）。
    std::vector<Pole> poles;

    const Real dre = (k_max - k_min) / Real(grid_n);
    const Real dim = im_max / Real(grid_n);
    auto inv_mag = [&](Real re, Real im) -> Real {
        Complex kr(re, im);
        Complex g = eval_GA(sg, kr);
        if (std::abs(g) < 1e-30) return 1e30;   // 避免发散点误判
        return 1.0 / std::abs(g);
    };

    // 先求全局最小 |1/G|（粗估极点强度），阈值取其若干倍作为候选门限。
    Real global_min = 1e30;
    for (int i = 0; i <= grid_n; ++i)
        for (int j = 0; j <= grid_n; ++j) {
            Real v = inv_mag(k_min + i * dre, -Real(j) * dim);
            if (v < global_min) global_min = v;
        }
    // 候选门限：取全局最小 × 倍数（宽极点也纳入）。兜底放宽。
    const Real threshold = std::max(global_min * 8.0, 1.0);

    // 网格采样，找局部极小（候选）。
    std::vector<std::pair<Real, std::pair<Real, Real>>> cands;  // (inv_mag, (re,im))
    for (int i = 1; i < grid_n; ++i) {
        for (int j = 1; j < grid_n; ++j) {
            const Real re = k_min + i * dre;
            const Real im = -Real(j) * dim;       // Im<0
            const Real v = inv_mag(re, im);
            // 邻域比较（8 邻域）
            const Real v_l = inv_mag(re - dre, im);
            const Real v_r = inv_mag(re + dre, im);
            const Real v_d = inv_mag(re, im - dim);
            const Real v_u = inv_mag(re, im + dim);
            if (v < v_l && v < v_r && v < v_d && v < v_u && v < threshold) {
                cands.emplace_back(v, std::make_pair(re, im));
            }
        }
    }
    // 按 inv_mag 升序，依次精化并去重（距离阈值）。
    std::sort(cands.begin(), cands.end());
    const Real merge_dist = 0.05 * (k_max - k_min);
    for (auto& c : cands) {
        Complex kp(c.second.first, c.second.second);
        Pole p = refine_and_residue(sg, kp, 0.5 * std::min(dre, dim));
        // 去重：与已找到极点距离 > merge_dist
        bool dup = false;
        for (auto& q : poles) {
            if (std::abs(q.k_rho - p.k_rho) < merge_dist) { dup = true; break; }
        }
        if (!dup && std::abs(p.residue) > 0.0)
            poles.push_back(p);
    }
    return poles;
}

Pole refine_and_residue(const spectral::SpectralGreensFunction& sg,
                        Complex k_p, Real r) {
    // 数值留数：对简单极点，residue = lim_{k→k_p} (k-k_p)·G(k)。
    // 在极点附近用小步长 ε 沿实轴/虚轴采样，取 (k-k_p)·G 的稳定值。
    // 同时用「圆周上 |G| 最大点」精化极点位置。
    const int N = 64;
    Complex g_max(0.0, 0.0);
    Complex k_at_max = k_p;
    for (int i = 0; i < N; ++i) {
        const Real th = 2.0 * phys::pi * Real(i) / Real(N);
        const Complex dk(r * std::cos(th), r * std::sin(th));
        const Complex k = k_p + dk;
        const Complex g = eval_GA(sg, k);
        if (std::abs(g) > std::abs(g_max)) {
            g_max = g; k_at_max = k;
        }
    }
    // 留数：在精化极点 k_at_max 附近，取小偏移 ε 求 (k-k_p)·G 的稳定估计。
    // 用沿 Im 方向（极点法线，Im<0 方向）的两个偏移点拟合。
    const Real eps = r * 0.1;
    const Complex kp = k_at_max;
    const Complex g0 = eval_GA(sg, kp + Complex(0.0, -eps));
    const Complex g1 = eval_GA(sg, kp + Complex(0.0, -2.0 * eps));
    // 简单极点：G(k) ≈ R/(k-kp)。取 k=kp-ε：G=R/(-ε) → R=-ε·G。
    // 用两点平均更稳健（极点位置精度有限）。
    Complex residue = -eps * g0;
    // 校核：第二点 R ≈ -2ε·g1，应与上面接近；取平均。
    Complex residue2 = -2.0 * eps * g1;
    residue = Complex(0.5, 0.0) * (residue + residue2);

    Pole p;
    p.k_rho = k_at_max;
    p.residue = residue;
    return p;
}

} // namespace mom::green::poles
