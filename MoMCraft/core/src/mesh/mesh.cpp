// =====================================================================
// mom/mesh/mesh.cpp —— 矩形网格 + 屋顶基函数实现
// =====================================================================
#include "mom/mesh/mesh.hpp"

namespace mom::mesh {

std::vector<RectCell> RectMesh::x_segments() const {
    std::vector<RectCell> segs;
    segs.reserve(nx);
    const Real h = dx();
    const Real W = y_max - y_min;
    for (Index i = 0; i < nx; ++i) {
        RectCell c;
        c.x0 = x_min + (Real(i) + 0.5) * h;   // 段中心
        c.y0 = 0.5 * (y_min + y_max);          // 宽度中心
        c.z0 = z0;
        c.dx = h;
        c.dy = W;                               // 段占满全宽（1D 基函数）
        (void)W;
        segs.push_back(c);
    }
    return segs;
}

std::vector<RooftopBasis> RectMesh::bases() const {
    std::vector<RooftopBasis> bs;
    if (nx < 2) return bs;                      // 至少 2 段才能定义屋顶
    bs.reserve(nx - 1);
    const Real h = dx();
    for (Index i = 0; i < nx - 1; ++i) {
        RooftopBasis b;
        b.left_seg  = i;
        b.right_seg = i + 1;
        // 节点位于第 i+1 个段边界：x_min + (i+1)*h
        b.x_center  = x_min + Real(i + 1) * h;
        (void)h;
        bs.push_back(b);
    }
    return bs;
}

Real rooftop_shape(const RooftopBasis& b, Real x, Real seg_dx) {
    // 左段 [x_center-dx, x_center]：f = (x - (x_center-dx))/dx
    const Real xL = b.x_center - seg_dx;
    const Real xR = b.x_center + seg_dx;
    if (x <= xL || x >= xR) return 0.0;          // 屋顶支集外
    if (x <= b.x_center)
        return (x - xL) / seg_dx;                 // 上升
    return (xR - x) / seg_dx;                      // 下降
}

std::array<Real, 2> rooftop_div(const RooftopBasis& /*b*/, Real seg_dx) {
    // 左段 d(f)/dx = +1/dx；右段 d(f)/dx = -1/dx（电流连续性的电荷分布）
    return {1.0 / seg_dx, -1.0 / seg_dx};
}

} // namespace mom::mesh
