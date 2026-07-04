// =====================================================================
// mom/lc_extract.hpp —— 基于 L/C 的传输线 Z0 提取（避免 open-short 病态）
//
// 对电小尺寸传输线（βL≪1），直接从 MoM 阻抗矩阵提取单位长度 L、C：
//   - 串联阻抗 Z_series（感性，主导 L）：Z 矩阵中相邻基函数的差（局部电流-电压关系）
//   - 并联导纳 Y_shunt（容性，主导 C）：标量势部分的对角贡献
//   Z0 = √(Z_series/Y_shunt)，β = √(Z_series·Y_shunt)
//
// 更稳健：用 Z 矩阵的本征分解或直接从 G_A、G_phi 的空间积分提取 L、C。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/green/spectral.hpp"
#include "mom/green/qwe.hpp"
#include <complex>

namespace mom::lc {

// 从装配好的阻抗矩阵（行主序 nb×nb）提取传输线 Z0、β（基于 L/C）。
//   ZA, ZPhi : assemble_mpie_single 返回的矢量位/标量位块（行主序 nb×nb）
//   omega    : 角频率
//   eps_r    : 相对介电常数（用于 coefPhi 归一化）
//   length   : 传输线总长度
//   width    : 传输线宽度
//   nb       : 基函数数
// 返回 {Z0, beta, L_per_length, C_per_length}（结构 TLParams）。
struct LCParams {
    Complex z0;       // 特征阻抗
    Real beta;        // 传播常数（rad/m）
    Real L_per_len;   // 单位长度电感（H/m）
    Real C_per_len;   // 单位长度电容（F/m）
};

// 方法：从中心段的局部阻抗参数提取。
//   Z_series = jω·L（感性）来自 ZA 块：Z_series/m = jω·μ₀·∫∫G_A·f'f'（电流回路电感）
//   Y_shunt = jω·C（容性）来自 ZPhi 块：Y_shunt·m = jω·ε₀·∫∫G_phi·∇f·∇f
//   电小段：Z0 = √(Z_series/Y_shunt)
LCParams extract_lc(const std::vector<Complex>& ZA, const std::vector<Complex>& ZPhi,
                    Real omega, Real eps_r, Real length, Real width, Index nb);

} // namespace mom::lc
