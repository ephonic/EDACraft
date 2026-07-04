// =====================================================================
// mom/common/analytic.cpp —— 共面矩形解析自势实现
// =====================================================================
#include "mom/common/analytic.hpp"
#include "mom/common/quadrature.hpp"
#include <cmath>
#include <algorithm>

namespace mom {

namespace {

// 经典 1D 区间对数核自积分的“四角函数”。
// 对矩形双重积分 ∫∫∫∫ 1/√((x-x')²+(y-y')²)，按顶点组合求和。
// 参考形式（Murphy, 1975 / Wandzura）：每对顶点贡献一个多项式对数项。
//   f(u,v) = u*v*atan(u*v / (s*sqrt(s²+u²+v²))) ... 较繁；
// 这里采用更稳健的“沿一边解析、另一边高斯”的半解析法。
//   I = ∫_ay^by dy ∫_ax^bx dx ∫_ay^by dy' ∫_ax^bx dx' 1/R
// 先做内层 (x,x') 解析：∫_ax^bx∫_ax^bx dx dx' /√((x-x')²+(y-y')²)
//   = 2∫_0^L (L-ξ)·[ sqrt(ξ²+d²) ... ] 对 ξ 积分，d=|y-y'|。
// 为简化且保证正确，此处用“对 y,y' 高斯 + 内层 x,x' 解析核”半解析。
//
// 解析核：对于固定 dy=|y-y'|，
//   K(dy) = ∫_0^L∫_0^L dx dx' / sqrt((x-x')²+dy²)
//         = ∫_0^L (L-ξ)·[ 2·(sqrt(ξ²+dy²)) ] dξ / ... 
// 实际：∫∫_{0..L} 1/sqrt((x-x')²+d²) dx dx' = ∫_0^L 2(L-ξ)/sqrt(ξ²+d²) dξ
//   该 1D 积分解析为：
//     2·[ L·asinh(L/d) - (sqrt(L²+d²) - d) ]   (d>0)
//     2·[ L·(ln(2L/d)) - L ]                      (d→0 极限)
Real xkernel_same_segment(Real L, Real d) {
    // 同段 x 内核积分 K(dy)=∫∫ dx dx'/√((x-x')²+dy²)
    //   = 2·[ L·asinh(L/dy) - (sqrt(L²+dy²) - dy) ]
    // 数值稳定：asinh(L/dy) = ln((L+sqrt(L²+dy²))/dy)，避免大比值的浮点溢出。
    if (d < 1e-30) {
        // dy→0 极限：2·[L·ln(2L/eps) - L]
        return 2.0 * L * (std::log(2.0 * L / 1e-30) - 1.0);
    }
    const Real s = std::sqrt(L * L + d * d);
    return 2.0 * (L * std::log((L + s) / d) - s + d);
}

} // namespace

namespace {
// 共面矩形自势的角点核（单个角点贡献，带符号由调用方控制）。
// Wandzura/Murphy 闭式：对于以一角为原点、边长 a(=|X|) 与 b(=|Y|) 的矩形，
// 双重自势 ∫∫∫∫ 1/|r-r'| dS dS' 的闭式为
//   I = (1/6)[ a b (a²+b²) - a b³ asinh(a/b) - b a³ asinh(b/a) ]   (a,b>0)
// asinh 用稳定式 asinh(t)=ln(t+√(t²+1))。
Real corner_term(Real X, Real Y) {
    Real a = std::fabs(X), b = std::fabs(Y);
    if (a < 1e-30 || b < 1e-30) return 0.0;
    auto asinh_stable = [](Real t) { return std::log(t + std::sqrt(t * t + 1.0)); };
    return (a * b * (a * a + b * b)
            - a * b * b * b * asinh_stable(a / b)
            - b * a * a * a * asinh_stable(b / a)) / 6.0;
}
} // namespace

Real coplanar_rect_self_potential(Real ax, Real bx, Real ay, Real by) {
    // 共面矩形 [ax,bx]×[ay,by] 上的双重自势。
    // 平移不变 → 仅取决于边长 Lx、Ly，结果等于单角点闭式 corner_term(Lx,Ly)。
    // 【约定】返回（直接核）积分，**不含** 1/(4π)，与 green_direct（e^{-jkR}/R）一致；
    //   QWE 装配路径（Green 含 1/(4π)）在调用处显式乘 inv_4pi 以对齐。
    const Real Lx = bx - ax;
    const Real Ly = by - ay;
    if (!(Lx > 0) || !(Ly > 0)) return 0.0;
    return corner_term(Lx, Ly);
}

Real coplanar_rect_pair_potential(
    Real ax, Real bx, Real ay, Real by,
    Real cx, Real dx_, Real cy, Real dy_,
    int nsub) {
    // 两矩形共面、x 区间可能相邻/分离；无奇异（除非完全重合，应调用 self 版）。
    // 用 nsub×nsub 细分 + 中点规则直接积分 1/R。近邻精度靠 nsub 保证。
    // 【约定】不含 1/(4π)，与 green_direct 一致。
    const Real hx = (bx - ax) / Real(nsub);
    const Real hxp = (cx + dx_ - (cx)) / Real(nsub); // 源矩形宽 dx_
    // 注：参数命名 dx_ 是矩形宽度，cx 是左端；源矩形 [cx, cx+dx_]
    const Real hy_ = (by - ay) / Real(nsub);
    const Real hyp = dy_ / Real(nsub);
    Real total = 0.0;
    for (int i = 0; i < nsub; ++i) {
        const Real xm = ax + (Real(i) + 0.5) * hx;
        for (int ip = 0; ip < nsub; ++ip) {
            const Real xpm = cx + (Real(ip) + 0.5) * hxp;
            for (int j = 0; j < nsub; ++j) {
                const Real ym = ay + (Real(j) + 0.5) * hy_;
                for (int jp = 0; jp < nsub; ++jp) {
                    const Real ypm = cy + (Real(jp) + 0.5) * hyp;
                    const Real R = std::sqrt((xm - xpm) * (xm - xpm)
                                           + (ym - ypm) * (ym - ypm));
                    if (R > 0) total += hx * hxp * hy_ * hyp / R;
                }
            }
        }
    }
    return total;
}

} // namespace mom
