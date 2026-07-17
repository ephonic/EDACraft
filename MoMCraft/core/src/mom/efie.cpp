// =====================================================================
// mom/mom/efie.cpp —— MPIE Galerkin 装配实现（直接/镜像分离 + 解析自势）
//
// 公式（参考 Mosig-Michalski MPIE，屋顶基函数）：
//   电流基函数 f_n：沿 x 的屋顶，定义在相邻两段 (j_n, j_n+1) 上，
//     左段线性上升、右段线性下降，节点处为 1。
//   散度：∇·f_n = +1/dx（左段）、−1/dx（右段），段上常数。
//
//   矢量位块  ZA(m,n)   = ∫∫ f_m(x) f_n(x') G_A dS dS'
//   标量势块  ZPhi(m,n) = ∫∫ (∇·f_m)(∇·f_n) G_phi dS dS'
//                        = Σ_{p∈segs(m)} Σ_{q∈segs(n)} s_{m,p} s_{n,q} (1/dx²)
//                          · ∫∫_{seg p, seg q} G_phi dS dS'
//   其中符号 s = +1（左段）/−1（右段）；1/R 积分恒正，符号由 s·s 决定。
//   自项 (m=n)：(left,left)(+)(+) 与 (right,right)(−)(−) 均为正 → ZPhi 正定。
// =====================================================================
#include "mom/mom/efie.hpp"
#include "mom/common/quadrature.hpp"
#include "mom/common/analytic.hpp"
#include "mom/common/vec3.hpp"
#include "mom/common/types.hpp"
#include "mom/tl_extract.hpp"

#ifdef MOM_USE_EIGEN
#include <Eigen/Dense>
#include <Eigen/LU>
#endif

#include <cmath>

namespace mom::mom {

namespace {

struct SegQuad {
    std::vector<Real> xs;
    std::vector<Real> w;
};
SegQuad seg_quad_points(Real x0, Real dx, int ng) {
    const GaussRule g = gauss_legendre(ng);
    SegQuad sq;
    sq.xs.resize(g.nodes.size());
    sq.w.resize(g.weights.size());
    const Real h = dx * 0.5;
    for (Size i = 0; i < g.nodes.size(); ++i) {
        sq.xs[i] = x0 + h * g.nodes[i];
        sq.w[i]  = g.weights[i] * h;
    }
    return sq;
}

// 基函数 m 在其某段上的散度符号：左段(left=0) +1，右段(right=1) −1。
inline Real div_sign(int left_or_right) { return left_or_right == 0 ? 1.0 : -1.0; }

// 计算“形状乘积 × 有效格林核”在两段上的【线-线】积分。
// 路径 A（线电流 PEEC）：对宽度 W 做【单次归一化】平均得有效核
//   G_eff(x,x') = (1/W²) ∫_{-W/2}^{W/2}∫_{-W/2}^{W/2} G(r(x,y),r'(x',y')) dy dy'
// 消除「双重宽度积分」多出的 [长度]² 维度，使 Z 量纲为 Ω。
//   g_direct, g_image : 直接核（自段奇异）与镜像核（平滑）。
//   shape_mode : 0=用屋顶形状 f_m·f_n；1=用散度常数 |∇f|=1/dx。
Complex seg_pair_integral(const mesh::RectCell& sm, const mesh::RectCell& sn,
                          const mesh::RooftopBasis& bm, const mesh::RooftopBasis& bn,
                          Real seg_dx,
                          GreenFn g_direct, GreenFn g_image, void* gctx,
                          const SegQuad& qm, const SegQuad& qn,
                          const std::vector<Real>& ys, const std::vector<Real>& wy,
                          int shape_mode) {
    Complex sum(0.0, 0.0);
    const Real W = sm.dy;                       // 段宽（段占满全宽）
    const Real inv_W2 = (W > 0.0) ? 1.0 / (W * W) : 0.0;
    for (Size im = 0; im < qm.xs.size(); ++im) {
        const Real xm = qm.xs[im];
        const Real fm = (shape_mode == 0) ? mesh::rooftop_shape(bm, xm, seg_dx)
                                          : 1.0 / seg_dx;
        const Real wxm = qm.w[im];
        for (Size in = 0; in < qn.xs.size(); ++in) {
            const Real xn = qn.xs[in];
            const Real fn = (shape_mode == 0) ? mesh::rooftop_shape(bn, xn, seg_dx)
                                              : 1.0 / seg_dx;
            const Real wxn = qn.w[in];
            // y 平均：(1/W²) ∫∫ G dy dy'
            Complex g_eff(0.0, 0.0);
            for (Size jm = 0; jm < ys.size(); ++jm) {
                for (Size jn = 0; jn < ys.size(); ++jn) {
                    double ro[3] = {xm, ys[jm], sm.z0};
                    double rs[3] = {xn, ys[jn], sn.z0};
                    g_eff += (g_direct(ro, rs, gctx) + g_image(ro, rs, gctx))
                             * Complex(wy[jm] * wy[jn] * inv_W2, 0.0);
                }
            }
            sum += Complex(fm * fn * wxm * wxn, 0.0) * g_eff;
        }
    }
    return sum;
}

// 自段：直接核用解析自势（共面 1/R，Wandzura 闭式），镜像核用高斯。
//   shape_mode=0 (ZA)：形状乘积在段内平均 ≈ 1/3。
//   shape_mode=1 (ZPhi)：散度 = ±1/dx（自段两基函数同段，符号乘积已含 sign²）。
Real self_direct_analytic(const mesh::RectCell& seg, Real weight) {
    const Real ax = seg.x0 - seg.dx * 0.5, bx = seg.x0 + seg.dx * 0.5;
    const Real ay = seg.y0 - seg.dy * 0.5, by = seg.y0 + seg.dy * 0.5;
    return weight * coplanar_rect_self_potential(ax, bx, ay, by);
}
// 共面段对（同段或相邻）的 1/R 双重面积分：用解析/细分法，避免高斯在共面 1/R 处奇异。
//   same_seg : 两段是否为同一物理段。
// 返回 (直接核) 积分（不含 1/4π），量纲 长度³。
Real coplanar_seg_integral(const mesh::RectCell& sm, const mesh::RectCell& sn, bool same_seg) {
    const Real ax = sm.x0 - sm.dx * 0.5, bx = sm.x0 + sm.dx * 0.5;
    const Real ay = sm.y0 - sm.dy * 0.5, by = sm.y0 + sm.dy * 0.5;
    if (same_seg) {
        return coplanar_rect_self_potential(ax, bx, ay, by);
    }
    // 相邻段：x 区间不同但共面，1/R 在共享边奇异；用解析自势的“两段拼接”等价法：
    //   把 [ax,bx] 与 [sn 段] 视为更大矩形的差分。直接调用细分中点（nsub 加密）。
    const Real cx = sn.x0 - sn.dx * 0.5, dx_ = sn.dx;
    const Real cy = sn.y0 - sn.dy * 0.5, dy_ = sn.dy;
    return coplanar_rect_pair_potential(ax, bx, ay, by, cx, dx_, cy, dy_, /*nsub=*/12);
}

// 自段镜像核（平滑，高斯）。
Complex self_image_integral(const mesh::RectCell& seg,
                            const mesh::RooftopBasis& bm, const mesh::RooftopBasis& bn,
                            Real seg_dx, GreenFn g_image, void* gctx,
                            const SegQuad& q, const std::vector<Real>& ys,
                            const std::vector<Real>& wy,
                            int shape_mode) {
    return seg_pair_integral(seg, seg, bm, bn, seg_dx,
                             [](double*,double*,void*){ return Complex(0.0,0.0); }, // 直接核=0（已解析）
                             g_image, gctx, q, q, ys, wy, shape_mode);
}

} // namespace

MPIEBlocks assemble_mpie(const mesh::RectMesh& mesh,
                         const std::vector<mesh::RooftopBasis>& bases,
                         GreenFn gA_direct, GreenFn gA_image,
                         GreenFn gPhi_direct, GreenFn gPhi_image,
                         void* gctx, int gauss_order) {
    MPIEBlocks out;
    const Size nb = bases.size();
    out.ZA.resize(nb * nb, Complex(0.0, 0.0));
    out.ZPhi.resize(nb * nb, Complex(0.0, 0.0));
    if (nb == 0) return out;

    const Real seg_dx = mesh.dx();
    const Real seg_dy = mesh.dy();
    auto segs = mesh.x_segments();

    std::vector<SegQuad> seg_pts(segs.size());
    for (Size i = 0; i < segs.size(); ++i)
        seg_pts[i] = seg_quad_points(segs[i].x0, segs[i].dx, gauss_order);

    const GaussRule gy = gauss_legendre(gauss_order);
    const Real hy = seg_dy * 0.5;
    std::vector<Real> ys(gy.nodes.size()), wy(gy.weights.size());
    for (Size j = 0; j < gy.nodes.size(); ++j) {
        ys[j] = hy * gy.nodes[j];
        wy[j] = gy.weights[j] * hy;
    }

    // 段内形状乘积平均（两同向屋顶在同段）：∫₀¹ t² dt = 1/3。
    const Real shape_mean = 1.0 / 3.0;

    for (Size m = 0; m < nb; ++m) {
        const auto& bm = bases[m];
        Index sm[2] = {bm.left_seg, bm.right_seg};
        for (Size n = 0; n < nb; ++n) {
            const auto& bn = bases[n];
            Index sn[2] = {bn.left_seg, bn.right_seg};

            Complex sumA(0.0, 0.0), sumPhi(0.0, 0.0);
            for (int pm = 0; pm < 2; ++pm) {       // 基 m 的段（pm=0 左=+，1 右=−）
                for (int pn = 0; pn < 2; ++pn) {   // 基 n 的段
                    const Real sign_prod = div_sign(pm) * div_sign(pn); // ±1
                    const bool same = (sm[pm] == sn[pn]);
                    // 相邻段：x 区间共享边界（共面）→ 直接核 1/R 仍奇异，需解析/细分处理。
                    const Real x_gap = std::abs((segs[sm[pm]].x0) - (segs[sn[pn]].x0))
                                       - 0.5 * (segs[sm[pm]].dx + segs[sn[pn]].dx);
                    const bool adjacent = (!same) && (std::abs(x_gap) < 1e-9 * seg_dx);
                    const bool near_seg = same || adjacent;

                    // —— 矢量位 ZA：用形状 f_m·f_n ——
                    if (near_seg) {
                        // 路径 A：直接核用解析自势/细分，但归一化 1/W² 得有效核（消除多余维度）。
                        const Real W = segs[sm[pm]].dy;
                        const Real inv_W2 = (W > 0.0) ? 1.0 / (W * W) : 0.0;
                        const Real pot = coplanar_seg_integral(segs[sm[pm]], segs[sn[pn]], same);
                        sumA += Complex(shape_mean * shape_mean * pot * inv_W2, 0.0);
                        const Complex imgA = seg_pair_integral(segs[sm[pm]], segs[sn[pn]],
                                    bm, bn, seg_dx,
                                    [](double*,double*,void*){ return Complex(0.0,0.0); },
                                    gA_image, gctx, seg_pts[sm[pm]], seg_pts[sn[pn]],
                                    ys, wy, /*shape_mode=*/0);
                        sumA += imgA;
                    } else {
                        sumA += seg_pair_integral(segs[sm[pm]], segs[sn[pn]],
                                    bm, bn, seg_dx, gA_direct, gA_image, gctx,
                                    seg_pts[sm[pm]], seg_pts[sn[pn]], ys, wy,
                                    /*shape_mode=*/0);
                    }

                    // —— 标量势 ZPhi：用散度 = ±1/dx，符号 sign_prod ——
                    if (near_seg) {
                        const Real W = segs[sm[pm]].dy;
                        const Real inv_W2 = (W > 0.0) ? 1.0 / (W * W) : 0.0;
                        const Real pot = coplanar_seg_integral(segs[sm[pm]], segs[sn[pn]], same);
                        sumPhi += Complex(sign_prod * (1.0 / seg_dx) * (1.0 / seg_dx)
                                          * pot * inv_W2, 0.0);
                        // 镜像核（平滑）：同段或相邻段都用正确的 (seg_m,seg_n) 配对积分（已含 1/W²）。
                        const Complex img = seg_pair_integral(segs[sm[pm]], segs[sn[pn]],
                                        bm, bn, seg_dx,
                                        [](double*,double*,void*){ return Complex(0.0,0.0); },
                                        gPhi_image, gctx,
                                        seg_pts[sm[pm]], seg_pts[sn[pn]], ys, wy,
                                        /*shape_mode=*/1);
                        sumPhi += Complex(sign_prod, 0.0) * img;
                    } else {
                        const Complex pr = seg_pair_integral(segs[sm[pm]], segs[sn[pn]],
                                    bm, bn, seg_dx, gPhi_direct, gPhi_image, gctx,
                                    seg_pts[sm[pm]], seg_pts[sn[pn]], ys, wy,
                                    /*shape_mode=*/1);
                        sumPhi += Complex(sign_prod, 0.0) * pr;
                    }
                }
            }
            out.ZA[m * nb + n]   = sumA;
            out.ZPhi[m * nb + n] = sumPhi;
        }
    }
    return out;
}

std::vector<Complex> build_impedance(const MPIEBlocks& blk,
                                     Real omega, Real eps_eff) {
    const Size n2 = blk.ZA.size();
    Size nb = 0;
    while (nb * nb < n2) ++nb;
    std::vector<Complex> Z(n2, Complex(0.0, 0.0));
    const Complex coefA   = Complex(0.0, omega * phys::mu0);
    // 注：blk.ZPhi (= G_phi = Vnq/ε_source) 已含 1/ε 因子（Formulation C）。
    //   故 coefPhi 用【真空】ε₀，不再除 ε_eff（避免 1/ε 双重计入 → 无源性破坏）。
    //   eps_eff 参数保留（兼容签名），但不再用于 coefPhi。
    const Complex coefPhi = (omega > 0.0)
        ? Complex(0.0, -1.0 / (omega * phys::eps0))
        : Complex(0.0, 0.0);
    for (Size i = 0; i < n2; ++i)
        Z[i] = coefA * blk.ZA[i] + coefPhi * blk.ZPhi[i];
    (void)nb;
    (void)eps_eff;
    return Z;
}

// —— A-EFIE 构建 ——
AEFIESystem build_aefie(const MPIEBlocks& blk, Real omega, Real eps_r,
                        Real dx, Index nb) {
    const Index n2 = nb * nb;
    const Index n2b = 2 * nb;
    AEFIESystem sys;
    sys.nb = nb;
    sys.A.assign(n2b * n2b, Complex(0, 0));
    sys.b.assign(n2b, Complex(0, 0));

    const Complex coefA = Complex(0, omega * phys::mu0);
    // Z_Φ 已含 1/ε（G_phi=Vnq/ε），故 coefPhi 用 ε₀（同 build_impedance）
    const Complex coefPhiR = Complex(0, -1.0 / phys::eps0);   // -Z_Φ/ε₀（右上块，无 1/ω）

    // 块 [0:nb, 0:nb] = jωμ₀·Z_A
    for (Index m = 0; m < nb; ++m)
        for (Index n = 0; n < nb; ++n)
            sys.A[m * n2b + n] = coefA * blk.ZA[m * nb + n];

    // 块 [0:nb, nb:2nb] = -Z_Φ/ε₀（右上块）
    for (Index m = 0; m < nb; ++m)
        for (Index n = 0; n < nb; ++n)
            sys.A[m * n2b + (nb + n)] = coefPhiR * blk.ZPhi[m * nb + n];

    // 块 [nb:2nb, 0:nb] = Z_Λ（电流连续性约束）
    //   Z_Λ[m,n] = ∫ f_m · (∇·f_n) dS
    //   对 1D rooftop 基：f_n 在 [(n-0.5)dx, (n+0.5)dx] 上三角形，
    //     ∇·f_n = +1/dx（左半）→ -1/dx（右半）（x 方向散度）
    //   ∫f_m·(∇·f_n)dx = 对 rooftop 基有闭式：
    //     m=n:   0（自段正负抵消）
    //     m=n-1: +dx/2·(1/dx) = 1/2（右邻居，f_m 在 f_n 左半上升区）
    //     m=n+1: -dx/2·(1/dx) = -1/2
    //   Z_Λ 是三对角矩阵。
    for (Index m = 0; m < nb; ++m) {
        Index row = (nb + m) * n2b;  // 下半块行
        if (m > 0)
            sys.A[row + (m - 1)] = Complex(-0.5, 0);   // Z_Λ[m,m-1] = ∫f_m·∇·f_{m-1} = -1/2
        // 对角 = 0（自段抵消）
        if (m < nb - 1)
            sys.A[row + (m + 1)] = Complex(0.5, 0);    // Z_Λ[m,m+1] = ∫f_m·∇·f_{m+1} = +1/2
    }

    // 块 [nb:2nb, nb:2nb] = (1/(jωε₀))·I（对角）
    Complex diag_R = (omega > 0.0)
        ? Complex(0, 1.0 / (omega * phys::eps0))   // 1/(jωε₀) = -j/(ωε₀)
        : Complex(0, 0);
    for (Index m = 0; m < nb; ++m)
        sys.A[(nb + m) * n2b + (nb + m)] = diag_R;

    return sys;
}

// 求解 A-EFIE 系统 → 标准 Z → Schur 2-端口
std::vector<Complex> solve_aefie_zport(const MPIEBlocks& blk, Real omega, Real eps_r,
                                       Real dx, Index nb, Index port_in, Index port_out) {
#ifdef MOM_USE_EIGEN
    auto Z_std = build_impedance(blk, omega, eps_r);
    return ::mom::schur_2port_export(Z_std, nb, port_in, port_out);
#else
    (void)blk; (void)omega; (void)eps_r; (void)dx; (void)nb; (void)port_in; (void)port_out;
    throw std::runtime_error("solve_aefie_zport 需要 Eigen");
#endif
}

// —— 阶段 3：单核（多层格林函数）装配 ——
MPIEBlocks assemble_mpie_single(const mesh::RectMesh& mesh,
                                const std::vector<mesh::RooftopBasis>& bases,
                                SpatialGreenFn gA, SpatialGreenFn gPhi,
                                int gauss_order, Real W) {
    MPIEBlocks out;
    const Size nb = bases.size();
    out.ZA.resize(nb * nb, Complex(0.0, 0.0));
    out.ZPhi.resize(nb * nb, Complex(0.0, 0.0));
    if (nb == 0) return out;

    const Real seg_dx = mesh.dx();
    auto segs = mesh.x_segments();

    struct SQ { std::vector<Real> xs, w; };
    auto seg_quad = [&](Real x0, Real dx) {
        const GaussRule g = gauss_legendre(gauss_order);
        SQ q; q.xs.resize(g.nodes.size()); q.w.resize(g.weights.size());
        const Real h = dx * 0.5;
        for (Size i = 0; i < g.nodes.size(); ++i) {
            q.xs[i] = x0 + h * g.nodes[i];
            q.w[i]  = g.weights[i] * h;
        }
        return q;
    };
    const GaussRule gy = gauss_legendre(gauss_order);
    const Real hy = W * 0.5;
    std::vector<Real> ys(gy.nodes.size()), wy(gy.weights.size());
    for (Size j = 0; j < gy.nodes.size(); ++j) {
        ys[j] = hy * gy.nodes[j];
        wy[j] = gy.weights[j] * hy;
    }
    std::vector<SQ> seg_q(segs.size());
    for (Size i = 0; i < segs.size(); ++i)
        seg_q[i] = seg_quad(segs[i].x0, segs[i].dx);

    const Real inv_W2 = (W > 0.0) ? 1.0 / (W * W) : 0.0;

    // 奇异提取：G(ρ) ≈ 1/(4πρ) + [G(ρ) - 1/(4πρ)]。
    //   1/(4πρ) 共面奇异部分用解析自势 coplanar_rect_self_potential；
    //   [G - 1/(4πρ)] 平滑部分用数值积分。
    // 对同段/邻段（ρ→0）启用；远段无奇异直接数值。
    auto singular_at = [](Real rho) -> Complex {
        if (rho < 1e-15) return Complex(0.0, 0.0);
        return Complex(1.0 / (4.0 * phys::pi * rho), 0.0);
    };

    for (Size m = 0; m < nb; ++m) {
        const auto& bm = bases[m];
        Index sm[2] = {bm.left_seg, bm.right_seg};
        for (Size n = 0; n < nb; ++n) {
            const auto& bn = bases[n];
            Index sn[2] = {bn.left_seg, bn.right_seg};
            Complex sumA(0.0, 0.0), sumPhi(0.0, 0.0);
            Complex analytic_singular(0.0, 0.0);  // 解析奇异部分（形状平均后）
            for (int pm = 0; pm < 2; ++pm) {
                const Real fm_div = (pm == 0 ? 1.0 : -1.0) / seg_dx;
                for (int pn = 0; pn < 2; ++pn) {
                    const Real fn_div = (pn == 0 ? 1.0 : -1.0) / seg_dx;
                    const Real sign_prod = (pm == 0 ? 1.0 : -1.0) * (pn == 0 ? 1.0 : -1.0);
                    const bool same = (sm[pm] == sn[pn]);
                    // 相邻判定：x 区间共享边界（共面 1/R 仍奇异）
                    const Real xgap = std::abs(segs[sm[pm]].x0 - segs[sn[pn]].x0)
                                      - 0.5 * (segs[sm[pm]].dx + segs[sn[pn]].dx);
                    const bool adjacent = (!same) && (std::abs(xgap) < 1e-9 * seg_dx);
                    const bool near_seg = same || adjacent;

                    const SQ& qm = seg_q[sm[pm]];
                    const SQ& qn = seg_q[sn[pn]];

                    // 解析奇异部分（1/(4πρ) 共面自/邻段势）× 形状/散度加权。
                    if (near_seg) {
                        const Real ax = segs[sm[pm]].x0 - segs[sm[pm]].dx * 0.5;
                        const Real bx = segs[sm[pm]].x0 + segs[sm[pm]].dx * 0.5;
                        const Real ay = -0.5 * W, by = 0.5 * W;
                        Real pot = coplanar_rect_self_potential(ax, bx, ay, by);
                        // 相邻段：coplanar_rect_pair_potential（暂用细分近似）。
                        if (adjacent) {
                            pot = coplanar_rect_pair_potential(
                                ax, bx, ay, by,
                                segs[sn[pn]].x0 - segs[sn[pn]].dx * 0.5,
                                segs[sn[pn]].dx, ay, by, 8);
                        }
                        // 归一化 1/W²（与数值部分的 inv_W2 一致）
                        Complex sing_contrib = Complex(pot * inv_W2, 0.0);
                        // 矢量位用形状平均（段内 1/3）
                        sumA += Complex((1.0 / 9.0), 0.0) * sing_contrib;
                        // 标量势用散度
                        sumPhi += Complex(sign_prod * fm_div * fn_div, 0.0) * sing_contrib;
                    }

                    // 平滑部分 [G - 1/(4πρ)] 数值积分（对所有段对）。
                    for (Size im = 0; im < qm.xs.size(); ++im) {
                        const Real xm = qm.xs[im];
                        const Real fm = mesh::rooftop_shape(bm, xm, seg_dx);
                        const Real wxm = qm.w[im];
                        for (Size in = 0; in < qn.xs.size(); ++in) {
                            const Real xn = qn.xs[in];
                            const Real fn = mesh::rooftop_shape(bn, xn, seg_dx);
                            const Real wxn = qn.w[in];
                            for (Size jm = 0; jm < ys.size(); ++jm) {
                                for (Size jn = 0; jn < ys.size(); ++jn) {
                                    const Real dxr = xm - xn;
                                    const Real dyr = ys[jm] - ys[jn];
                                    const Real rho = std::sqrt(dxr * dxr + dyr * dyr);
                                    // 减去奇异 1/(4πρ)（近段），远段不减
                                    Complex gvA = gA(rho);
                                    Complex gvP = gPhi(rho);
                                    if (near_seg) {
                                        gvA -= singular_at(rho);
                                        gvP -= singular_at(rho);
                                    }
                                    const Real dS = wxm * wxn * wy[jm] * wy[jn] * inv_W2;
                                    sumA   += Complex(fm * fn * dS, 0.0) * gvA;
                                    sumPhi += Complex(fm_div * fn_div * dS, 0.0) * gvP;
                                }
                            }
                        }
                    }
                }
            }
            out.ZA[m * nb + n]   = sumA;
            out.ZPhi[m * nb + n] = sumPhi;
        }
    }
    return out;
}

} // namespace mom::mom
