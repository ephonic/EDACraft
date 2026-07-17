// =====================================================================
// mom/mom/efie.hpp —— EFIE / A-EFIE 矩阵装配（阶段 1：MPIE Galerkin）
//
// 阶段 1 实现 MPIE（混合势积分方程），用于验证 MoM 闭环：
//   阻抗矩阵 Z = jωμ0·Z_A + (1/jωε0)·Z_Φ，其中
//     Z_A(m,n) = ∫∫ f_m(r) · G_A(r,r') · f_n(r') dS dS'   （矢量位）
//     Z_Φ(m,n) = ∫∫ div f_m(r) · G_Φ(r,r') · div f_n(r') dS dS'（标量势）
//   电流沿 x，G_A/G_Φ 为空域格林函数（阶段 1 自由空间 + 接地镜像）。
//
// 阶段 3 将升级为 A-EFIE（电流+电荷增广系统，低频稳定），此处先建立
// 矢量位/标量势两个块，便于平滑迁移。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/mesh/mesh.hpp"
#include <vector>
#include <complex>
#include <functional>

namespace mom::mom {

enum class Formulation { EFIE, AEFIE };

// MPIE 装配所需格林函数接口（阶段 1 由 green:: 提供，阶段 2 替换）。
// 拆分为【直接】（self-segment 处奇异）与【镜像/介质】（处处平滑）两部分：
//   - 直接部分：self-segment 用解析自势，pair-segment 用高斯积分；
//   - 镜像部分：始终平滑，全程高斯积分。
// 阶段 2：镜像部分将被完整多层格林函数替换。
using GreenFn = Complex (*)(double* r_obs, double* r_src, void* ctx);

// 计算矢量位块 Z_A(m,n) 与标量势块 Z_Phi(m,n)。
// 两者尺寸均为 (nbasis × nbasis)，按行主序存储。
// 输出写入调用方提供的 vector（自动 resize）。
struct MPIEBlocks {
    std::vector<Complex> ZA;     // 矢量位块（实对称，存为 complex 便于合并）
    std::vector<Complex> ZPhi;   // 标量势块（实对称）
};

// 装配 MPIE 两块（矢量位 + 标量势）。
// 四个格林核回调：
//   gA_direct / gA_image   : 矢量位（A）的直接/镜像核
//   gPhi_direct / gPhi_image: 标量势（Φ）的直接/镜像核
// 直接核在 self 段奇异（由装配层用解析自势处理）；镜像核处处平滑。
MPIEBlocks assemble_mpie(const mesh::RectMesh& mesh,
                         const std::vector<mesh::RooftopBasis>& bases,
                         GreenFn gA_direct, GreenFn gA_image,
                         GreenFn gPhi_direct, GreenFn gPhi_image,
                         void* gctx, int gauss_order);

// 由 ZA、ZPhi 合成总阻抗矩阵 Z = jωμ0·ZA + (1/jωε0)·ZPhi（行主序，复数）。
// eps_eff：有效介电常数（阶段 1 近似体现介质；阶段 2 由格林函数吸收）。
std::vector<Complex> build_impedance(const MPIEBlocks& blk,
                                     Real omega, Real eps_eff);

// —— 阶段 3：单核（多层格林函数）装配接口 ——
// 全空域格林函数求值器：给定水平距离 ρ（同层源/场），返回 G_A(ρ) 或 G_phi(ρ)。
// 不区分 direct/image，直接给完整空域格林函数（阶段 3 用数值 Sommerfeld）。
// 用 std::function 便于绑定 LayeredSpatialGreen、lambda 等。
using SpatialGreenFn = std::function<Complex(Real rho)>;

// 装配 MPIE 两块（矢量位 + 标量势），用【单核】空域格林函数。
//   gA   : 矢量位空域格林 G_A(ρ)
//   gPhi : 标量势空域格林 G_phi(ρ)
// 注：self 段（ρ→0）奇异由【数值积分在中点规则下规避】（多点加密）；
//     阶段 1 的解析自势仅适用于自由空间+镜像，这里多层情况用高密度数值积分。
MPIEBlocks assemble_mpie_single(const mesh::RectMesh& mesh,
                                const std::vector<mesh::RooftopBasis>& bases,
                                SpatialGreenFn gA, SpatialGreenFn gPhi,
                                int gauss_order, Real W);

// —— A-EFIE（Augmented EFIE）低频稳定矩阵 ——
//
// 标准 MPIE: Z·I = V，Z = jωμ₀·Z_A + (1/jωε₀)·Z_Φ。
// 低频 jωμ₀→0，矩阵病态。A-EFIE 将电流 J 和电荷 ρ̃ 分离为独立未知数：
//   [jωμ₀·Z_A    -Z_Φ/ε₀ ] [J]     [V]
//   [Z_Λ          1/(jωε₀)] [ρ̃]  = [0]
// 其中 Z_Λ[m,n] = ∫f_m·(∇·f_n)dS 是电流连续性约束（divergence coupling）。
// 增广矩阵 2nb×2nb，条件数在 ω→0 时保持有界。
//
// 输出：增广矩阵 A（行主序 2nb×2nb）+ 右端 b（2nb）。
//   A[0:nb, 0:nb]     = jωμ₀·Z_A
//   A[0:nb, nb:2nb]   = -Z_Φ/ε₀
//   A[nb:2nb, 0:nb]   = Z_Λ
//   A[nb:2nb, nb:2nb] = (1/(jωε₀))·I（对角）
//   b[0:nb] = 端口激励，b[nb:2nb] = 0
struct AEFIESystem {
    std::vector<Complex> A;   // 2nb × 2nb 行主序
    std::vector<Complex> b;   // 2nb 右端
    Index nb;                 // 基函数数（A 为 2nb×2nb）
};

// 构建 A-EFIE 系统。blk 来自 assemble_mpie_single，dx 为网格步长。
AEFIESystem build_aefie(const MPIEBlocks& blk, Real omega, Real eps_r,
                        Real dx, Index nb);

// 求解 A-EFIE 系统，从 J 分量重建标准 Z 端口矩阵（2-端口 Schur）。
//   返回 [Z00, Z01, Z10, Z11]（行主序 2×2）。
std::vector<Complex> solve_aefie_zport(const MPIEBlocks& blk, Real omega, Real eps_r,
                                       Real dx, Index nb, Index port_in, Index port_out);

// 从 A-EFIE 解（J, ρ̃）提取 2-端口 S 参数（Schur 降阶）。
//   解 A·x=b 得 x=[J, ρ̃]，取端口 J 分量，构建端口 Z 矩阵 → S。
//   简化：直接用 J 分量（忽略 ρ̃）做端口提取。
std::vector<Complex> aefie_to_zport(const AEFIESystem& sys,
                                    const std::vector<Complex>& x,
                                    Index nb, Real z0_ref);

} // namespace mom::mom
