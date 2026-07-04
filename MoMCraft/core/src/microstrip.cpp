// =====================================================================
// mom/microstrip.cpp —— 微带线 MoM 求解器实现
// =====================================================================
#include "mom/microstrip.hpp"
#include "mom/mesh/mesh.hpp"
#include "mom/mom/efie.hpp"
#include "mom/solver/dense.hpp"
#include "mom/tl_extract.hpp"

#include <stdexcept>

namespace mom {

namespace {

// 格林函数回调上下文：波数 k 与接地平面 z。
struct GreenCtx { Real k; Real ground_z; };

// 直接核（self 段奇异，pair 段平滑）：e^{-jkR}/R，self 点返回 0（装配层解析处理）。
Complex cb_direct(double* r_obs, double* r_src, void* ctx) {
    auto* g = static_cast<GreenCtx*>(ctx);
    Vec3 ro(r_obs[0], r_obs[1], r_obs[2]);
    Vec3 rs(r_src[0], r_src[1], r_src[2]);
    return green::green_direct(ro, rs, g->k);
}
// 镜像核（处处平滑，含 ±号）：矢量势同号、标量势反号。
// 这里返回“矢量势镜像核”；标量势镜像核在装配时由 cb_image_phi 提供。
Complex cb_image_A(double* r_obs, double* r_src, void* ctx) {
    auto* g = static_cast<GreenCtx*>(ctx);
    Vec3 ro(r_obs[0], r_obs[1], r_obs[2]);
    Vec3 rs(r_src[0], r_src[1], r_src[2]);
    return green::vector_green_image(ro, rs, g->k, g->ground_z);
}
Complex cb_image_phi(double* r_obs, double* r_src, void* ctx) {
    auto* g = static_cast<GreenCtx*>(ctx);
    Vec3 ro(r_obs[0], r_obs[1], r_obs[2]);
    Vec3 rs(r_src[0], r_src[1], r_src[2]);
    return green::scalar_green_image(ro, rs, g->k, g->ground_z);
}

} // namespace

std::vector<Complex> solve_microstrip_sparam(Real freq,
                                             const MicrostripConfig& cfg) {
    // 1) 网格：z=h 的带子，沿 x 从 0 到 L，宽度 ±W/2。
    mesh::RectMesh mesh;
    mesh.x_min = 0.0;
    mesh.x_max = cfg.length;
    mesh.y_min = -0.5 * cfg.width;
    mesh.y_max =  0.5 * cfg.width;
    mesh.z0    = cfg.height;
    mesh.nx    = cfg.nx;
    mesh.ny    = 1;                              // 1D 基函数（段占满全宽）

    auto bases = mesh.bases();
    if (bases.size() < 2)
        throw std::runtime_error("微带线分段过少：nx 至少为 2");
    const Index nb = Index(bases.size());

    // 2) MPIE 装配（时谐格林函数，直接/镜像分离）
    const Real omega = 2.0 * phys::pi * freq;
    const Real k = green::k0(omega) * std::sqrt(cfg.eps_eff);  // 有效介质内波数
    GreenCtx gctx{k, cfg.has_ground ? 0.0
                                    : std::numeric_limits<Real>::quiet_NaN()};
    auto blk = mom::assemble_mpie(mesh, bases,
                                  cb_direct, cb_image_A,    // 矢量位 A
                                  cb_direct, cb_image_phi,  // 标量势 Φ（同直接核，镜像反号）
                                  &gctx, cfg.gauss);

    // 3) 合成阻抗矩阵。green:: 的核为 e^{-jkR}/R 形式，MPIE 标准格林含 1/(4π)；
    //    双重面积分故补 (1/4π)² 系数。
    constexpr Real inv4pi2 = phys::inv_4pi * phys::inv_4pi;
    for (auto& v : blk.ZA)   v *= inv4pi2;
    for (auto& v : blk.ZPhi) v *= inv4pi2;

    auto Z = build_impedance(blk, omega, cfg.eps_eff);

    // 4) 端口：用 Schur 降阶获取正确的 2 端口阻抗矩阵（修复 port_impedance_matrix
    //    的 Z·Z⁻¹=I 数学退化，使 S21≠0）。Schur 补：Zport = Z_pp - Z_pi·Z_ii⁻¹·Z_ip。
    auto Zport = schur_2port_export(Z, nb, 0, nb - 1);

    // 5) S 参数
    return solver::zport_to_sparam(Zport, cfg.z0_ref, 2);
}

} // namespace mom
