// =====================================================================
// mom/common/analytic.hpp —— 共面矩形的解析自势（1/R 奇异积分）
//
// 阶段 1：微带带（同平面）的 MoM 自项存在 1/R 面奇异。
// 当观测矩形与源矩形重合或相邻时，用解析/半解析公式替代高斯积分，
// 消除 inf 并保证对角项精度。
//
//   同平面矩形 [ax,bx]×[ay,by] 上：
//     I = ∫_rect ∫_rect 1/√((x-x')²+(y-y')²) dx dx' dy dy'
//   有闭式（4 顶点求和的反对称多项式对数形式）。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"

namespace mom {

// 共面矩形上的双重面积分 ∫∫∫∫ 1/|r-r'| dS dS'。
//   ax,bx : x 范围；ay,by : y 范围（同 z 平面）。
// 返回积分值（量纲 长度³）。
Real coplanar_rect_self_potential(Real ax, Real bx, Real ay, Real by);

// 共面但【不同】两矩形间的 1/R 双重面积分。
// 若两矩形 x 区间相邻/分离、y 区间相同，用细分高斯积分（无奇异，但近邻
// 精度需加密）。此处提供“细分网格直接积分”版本，调用方控制细分数。
Real coplanar_rect_pair_potential(
    Real ax, Real bx, Real ay, Real by,   // 观测矩形
    Real cx, Real dx_, Real cy, Real dy_, // 源矩形
    int nsub);                            // 每边细分数

} // namespace mom
