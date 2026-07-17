// =====================================================================
// mom/solver/dense.hpp —— 稠密直接求解 + delta-gap 端口 + S 参数提取
//
// 阶段 1：小规模（N≲3k）稠密 LU 直接解，逐端口激励得到端口阻抗矩阵
//         Z_port，再转 S 参数：
//           S = (Z_port - Z0·I)(Z_port + Z0·I)^{-1}
//
// 阶段 4 将由 pFFT 预校正 FFT + 迭代解替换矩阵-向量乘；端口/S 参数
// 提取逻辑可复用。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <vector>
#include <complex>

namespace mom::solver {

// 用稠密 LU 解 Z·I = V，返回电流向量 I。Z 行主序 nb×nb。
std::vector<Complex> solve_dense(const std::vector<Complex>& Z,
                                 const std::vector<Complex>& V,
                                 Index nb);

// 对每个端口（delta-gap 在对应屋顶基函数处加 1V）逐一激励，
// 解出各端口位置的电压/电流，组成端口阻抗矩阵 Z_port（nport×nport）。
//
//   port_basis : 每个端口对应的基函数索引（激励与采样同一基函数）
//   Z          : 阻抗矩阵（行主序 nb×nb）
//   nb         : 基函数数
// 返回 nport×nport 的 Z_port（行主序）。
std::vector<Complex> port_impedance_matrix(const std::vector<Index>& port_basis,
                                           const std::vector<Complex>& Z,
                                           Index nb);

// 由端口阻抗矩阵转 S 参数：S = (Zp - Z0 I)(Zp + Z0 I)^{-1}
//   z0     : 参考阻抗（各端口同值，欧姆）
//   nport  : 端口数
std::vector<Complex> zport_to_sparam(const std::vector<Complex>& Zport,
                                     Real z0, Index nport);

} // namespace mom::solver
