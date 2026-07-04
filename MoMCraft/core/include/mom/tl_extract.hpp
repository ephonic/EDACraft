// =====================================================================
// mom/tl_extract.hpp —— 传输线参数提取（开路-短路法，阶段 1 验证用）
//
// 背景：直接 delta-gap 端口 S 参数提取在 1D 屋顶基离散上端点电荷守恒建模
// 繁琐。改用传输线理论的开路-短路法稳健提取特征阻抗 Z0：
//   - 在线的一端（基函数 0）注入 1A 电流；
//   - 开路工况：另一端（基函数 N-1）无约束 → 得输入阻抗 Z_oc；
//   - 短路工况：另一端强制电流 = −1A（回流）→ 得输入阻抗 Z_sc；
//   - 无损传输线：Z0 = sqrt(Z_oc · Z_sc)，βl = atan(sqrt(Z_sc/Z_oc))。
//
// 对低频准静态情形，Z_oc 与 Z_sc 分别主要由电容、电感贡献，Z0 与
// Hammerstad-Jensen 解析值对照即可验证格林函数 + 装配正确。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <vector>
#include <complex>

namespace mom {

// 开路-短路法提取结果。
struct TLParams {
    Complex z_oc;      // 开路输入阻抗（Ω）
    Complex z_sc;      // 短路输入阻抗（Ω）
    Complex z0;        // 特征阻抗 sqrt(Z_oc·Z_sc)
    Real    beta_l;    // 电长度 atan(sqrt(Z_sc/Z_oc))
};

// 给定已装配的阻抗矩阵 Z（行主序 nb×nb）与端点基函数索引，
// 用开路-短路法提取传输线参数。
//   Z        : 全线 MoM 阻抗矩阵
//   nb       : 基函数数
//   port_in  : 激励端基函数（注入 +1A）
//   port_out : 远端基函数（开路：无约束；短路：强制 −1A）
TLParams extract_tl_open_short(const std::vector<Complex>& Z, Index nb,
                               Index port_in, Index port_out);

// —— 本征模法提取传输线 Z0、γ（对电抗≫电阻的准静态/低频区鲁棒）——
//
// 原理：对均匀传输线的 MoM 阻抗矩阵 Z（nb×nb，行主序），内部（远离端口）
// 区域近似 Toeplitz，其本征模为平面波 I_n ∝ λ^n。取 Z 的【次对角块】构造
// 单步递推矩阵，其本征值 λ = e^{-γ·dx}，本征向量给出电流模态形状；
// 再由沿线电压 V_n = Σ_j Z[n,j]·I_j 与电流 I_n 之比在传播区取 Z0。
//
//   Z        : 全线 MoM 阻抗矩阵（行主序 nb×nb）
//   nb       : 基函数数
//   dx       : 网格步长（m）
// 返回 TLParams（z_oc/z_sc 留空，z0 与 beta_l 有效）。
TLParams extract_tl_eigenmode(const std::vector<Complex>& Z, Index nb, Real dx);

// Schur 降阶 2 端口阻抗矩阵（行主序 2×2，4 元素）。
//   Zport2 = Z_pp - Z_pi·Z_ii⁻¹·Z_ip（关于内部基函数的 Schur 补）。
//   返回 [Z00, Z01, Z10, Z11]。
std::vector<Complex> schur_2port_export(const std::vector<Complex>& Z, Index nb,
                                        Index port_in, Index port_out);

// Schur 降阶 N 端口阻抗矩阵（行主序 N×N）。
//   ports : 端口基函数索引列表（长度 N）。
//   返回 N×N 行主序 Zport 矩阵（关于内部基函数的 Schur 补）。
std::vector<Complex> schur_nport_export(const std::vector<Complex>& Z, Index nb,
                                        const std::vector<Index>& ports);

// N-端口阻抗矩阵 → S 参数（等参考阻抗 z0）。
//   S = (Z - z0·I)·(Z + z0·I)⁻¹。返回 N×N 行主序。
std::vector<Complex> zport_n_to_sparam(const std::vector<Complex>& Zport, Index np, Real z0);

} // namespace mom
