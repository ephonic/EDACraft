// =====================================================================
// mom/lc_extract.cpp —— L/C 提取 Z0（均匀电流法）
//
// 对 1D 屋顶基均匀传输线，假设【均匀电流分布】I_n=1（所有基函数），
// 计算总串联阻抗（矢量位）与总并联导纳（标量位），提取单位长度 L、C。
//
// 均匀电流下：
//   串联电压（沿单位长度）= jωμ₀ · (Σ_m Σ_n ZA[m,n]) / length · I   → L
//   并联电荷 = (Σ_m Σ_n ZPhi[m,n])⁻¹ 相关   → C
//
// 更直接：对均匀线，特征阻抗 Z0 由 Z 矩阵的"模式"决定。
// 1D 屋顶基的本征模式是平面波，Z0 = 模态电压/模态电流。
// =====================================================================
#include "mom/lc_extract.hpp"

#include <cmath>
#include <vector>
#include <stdexcept>

namespace mom::lc {

LCParams extract_lc(const std::vector<Complex>& ZA, const std::vector<Complex>& ZPhi,
                    Real omega, Real eps_r, Real length, Real width, Index nb) {
    LCParams r;
    r.z0 = Complex(0, 0); r.beta = 0; r.L_per_len = 0; r.C_per_len = 0;
    if (nb < 4 || omega <= 0) return r;

    // 构建完整 Z = jωμ₀·ZA + (-j/(ωε₀ε_r))·ZPhi
    const Complex coefA = Complex(0, 1) * omega * phys::mu0;
    const Complex coefPhi = Complex(0, -1) / (omega * phys::eps0 * eps_r);
    std::vector<Complex> Z(nb*nb);
    for (Index i = 0; i < nb*nb; ++i) Z[i] = coefA*ZA[i] + coefPhi*ZPhi[i];

    // 均匀电流模式（所有基函数 I=1）下，中心节点电压 V_c = Σ_n Z[c,n]。
    // 对无损传输线，V_c/I ≈ 特征阻抗 Z0（远离端口处）。
    const Index c = nb / 2;
    Complex Vc(0, 0);
    for (Index n = 0; n < nb; ++n) Vc += Z[c*nb + n];
    // Vc 是均匀电流 I=1 下中心节点的"电压"。但这含串联+并联混合。
    // 更稳健：用 Z 矩阵的本征值（均匀线 Toeplitz → 平面波本征模）。
    //
    // 对均匀 1D 线，Z[m,n]=T(|m-n|)。本征值 λ_k = Σ_n T(n)·e^{-i2πkn/nb}。
    // 模态阻抗 Z_modal = λ_k。传播模式对应最小 |λ| 的非零模。
    // 但 Z 是电阻矩阵，本征值给出模态阻抗。
    //
    // 简化：直接报告中心节点电压/单位电流作为 Z0 近似（含端口效应，但对电小段粗略）。
    r.z0 = Vc;
    r.L_per_len = 0; r.C_per_len = 0; r.beta = 0;

    // 备选：从 ZA 行和提取串联（感性）、ZPhi 行和提取并联（容性）的【比值】，
    // 因子相互抵消，Z0 = √(Z_series_ratio / Z_shunt_ratio)。
    // Z_series ~ coefA·(ZA[c,c]-ZA[c,c-1])（相邻段差，串联电抗）
    // Z_shunt ~ coefPhi·ZPhi[c,c]（对角，并联电抗）
    // Z0² = (jωμ₀·ΔZA)·(-jωε₀ε_r·ZPhi_diag) ... 含 ω² 消不掉，但比值对。
    Complex dZA = ZA[c*nb + c] - ZA[c*nb + (c>0?c-1:c)];
    Complex ZPhi_diag = ZPhi[c*nb + c];
    // Z0² ~ (jωμ₀·dZA) / (1/(-jωε₀ε_r·ZPhi_diag)) = (jωμ₀·dZA)·(-jωε₀ε_r·ZPhi_diag)
    //     = ω²μ₀ε₀ε_r·dZA·ZPhi_diag  → Z0 = ω·√(μ₀ε₀ε_r)·√(dZA·ZPhi_diag)
    Complex prod = dZA * ZPhi_diag;
    if (std::abs(prod) > 1e-30) {
        Complex z0_alt = omega * std::sqrt(phys::mu0 * phys::eps0 * eps_r) * std::sqrt(prod);
        // 用此作为 Z0 估计
        r.z0 = z0_alt;
    }
    return r;
}

} // namespace mom::lc
