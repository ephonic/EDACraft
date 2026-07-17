// =====================================================================
// mom/common/quadrature.hpp —— 高斯积分节点与面积分辅助
//
// 阶段 1：屋顶基函数是分段线性的，矩阵元用低阶高斯-勒让德积分即可。
// 谱域格林函数的奇异/近奇异点（段重合）在 mom/ 内单独处理。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include <vector>
#include <array>

namespace mom {

// N 点高斯-勒让德节点/权重（N=1..4 足够阶段 1）。返回 [-1,1] 上。
struct GaussRule {
    std::vector<Real> nodes;
    std::vector<Real> weights;
};

GaussRule gauss_legendre(int n);

// 矩形面积分：在 [x0-dx/2,x0+dx/2]×[y0-dy/2,y0+dy/2] 上对 f 求积分。
// f 接收 (x, y)。内部分别用 nx、ny 点高斯积分。
// 为减少模板膨胀，这里用函数指针式回调（阶段 1 性能足够）。
using QuadFn2 = Real (*)(Real x, Real y, void* ctx);
Real integrate_rect(QuadFn2 f, void* ctx,
                    Real x0, Real y0, Real dx, Real dy,
                    int nx, int ny);

} // namespace mom
