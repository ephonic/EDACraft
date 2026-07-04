// =====================================================================
// mom/green/poles/poles.hpp —— surface-wave 极点搜索与留数（第四象限）
//
// 阶段 2.4 实现：
//   1. Weng Cho Chew 极点搜索算法：在复 k_rho 平面扫描，定位全部 surface-wave
//      极点（位于第四象限，即 Re>0, Im<0）。
//   2. 柯西留数定理：解析计算每个极点的留数贡献，得到 surface-wave 空域项。
//
// 极点搜索方法：谱域核 G̃(k_rho) 的极点出现在「广义反射系数递推分母为零」处，
//   即 1 + r·R̃·phase = 0。在第四象限网格采样 1/G̃，用局部多项式求根定位极点，
//   网格细化收敛。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/green/spectral.hpp"
#include <vector>

namespace mom::green::poles {

struct Pole {
    Complex k_rho;   // 极点横向波数（第四象限）
    Complex residue; // 该极点留数（对 G̃ 而言）
};

// Chew 极点搜索：在复 k_rho 平面第四象限扫描，定位谱域核的 surface-wave 极点。
//   sg      : 谱域格林函数求值器
//   k_min   : 搜索范围实部下界（>0）
//   k_max   : 搜索范围实部上界（如 3*k0）
//   im_max  : 搜索范围虚部下界深度（如 -k_max，向下搜到 Im=-im_max）
//   grid_n  : 每方向网格点数
// 返回找到的极点集合（含留数）。
std::vector<Pole> find_surface_wave_poles(
    const spectral::SpectralGreensFunction& sg,
    Real k_min, Real k_max, Real im_max, int grid_n);

// 单极点留数：在极点附近用小圆周积分（柯西留数定理）精确计算。
//   sg   : 谱域求值器
//   k_p  : 极点位置（初值）
//   r    : 小圆半径
// 返回 (精化极点, 留数)。
Pole refine_and_residue(const spectral::SpectralGreensFunction& sg,
                        Complex k_p, Real r);

} // namespace mom::green::poles
