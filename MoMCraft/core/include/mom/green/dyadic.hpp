// =====================================================================
// mom/green/dyadic.hpp —— 并矢格林函数（3D 电流方向支持）
//
// M2 阶段：从标量 G_A(ρ) 扩展到并矢，支持 RWG 矢量电流。
//
// Michalski-Zheng Formulation C 并矢结构：
//   Ḡ_A = [G_Axx  0     0   ]    水平电流（x/y）：G_Axx = G_Ayy = G_A（标量）
//          [0      G_Ayy  0   ]    垂直电流（z）：  G_Azz = G_P（TM 电压 TLGF）
//          [0      0      G_Azz]    交叉项：同层 z=z' 时为零
//
//   G_phi：标量势（电荷），所有方向共用。
//
// 水平并矢（当前实现）：G_Axx = G_Ayy = G_A，G_Azz = 0。
//   适用于平面导体（z=z'，水平 RWG 电流）。
//
// 空域并矢：每分量用 QWE 积分（复用现有 qwe.cpp）。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/poles.hpp"
#include <vector>
#include <functional>

namespace mom::green::dyadic {

// 谱域并矢核（水平电流版本）
struct SpectralDyadic {
    Complex G_Axx;   // = G_A（水平 x 矢量位）
    Complex G_Ayy;   // = G_A（水平 y 矢量位，各向同性 = G_Axx）
    Complex G_Azz;   // = G_P（垂直 z 矢量位，水平版暂不用）
    Complex G_phi;   // 标量势
};

// 空域并矢核（支持水平和垂直电流）
//   对同层（z_src=z_obs）水平电流：
//     G_Axx(ρ) = G_Ayy(ρ) = G_A(ρ)（标量空域格林，QWE）
//     G_phi(ρ) = G_phi(ρ)（标量势）
//   对跨层垂直电流（z 方向）：
//     G_Azz(ρ) = G_P(ρ)（TM 电压 TLGF）
//   矢量位点积：J̄·Ḡ_A·J̄' = Jx·G_A·Jx' + Jy·G_A·Jy' + Jz·G_P·Jz'
struct SpatialDyadic {
    std::shared_ptr<spectral::SpectralGreensFunction> sg_ptr;  // 谱格林函数（共享生命周期）
    Real eps_r;
    int n_intervals;
    int gauss_order;

    // 矢量位格林函数（x/y 共用）
    Complex GA(Real rho) const;

    // 垂直矢量位格林函数（z 方向，用于过孔/TSV）
    Complex GAzz(Real rho) const;

    // 标量势格林函数
    Complex Gphi(Real rho) const;

    // 矢量位点积：f̄(r) · Ḡ_A · f̄'(r')
    //   = G_A(ρ) · (fx·fx' + fy·fy') + G_P(ρ) · fz·fz'
    Complex vector_dot(Real rho, Real fx, Real fy, Real fz, Real fxp, Real fyp, Real fzp) const {
        return GA(rho) * (fx * fxp + fy * fyp) + GAzz(rho) * fz * fzp;
    }

    // 标量势乘积：∇·f · G_phi · ∇·f'
    Complex scalar_dot(Real rho, Real div_f, Real div_fp) const {
        return Gphi(rho) * div_f * div_fp;
    }
};

// 构建空域并矢格林（QWE，复用现有 spatial_GA_qwe / spatial_Gphi_qwe）
//   水平电流版本：GA = spatial_GA_qwe, Gphi = spatial_Gphi_qwe
SpatialDyadic build_horizontal_dyadic(
    const spectral::SpectralGreensFunction& sg,
    Real eps_r,
    const std::vector<poles::Pole>& pole_list,
    int n_intervals = 60, int gauss_order = 7);

} // namespace mom::green::dyadic
