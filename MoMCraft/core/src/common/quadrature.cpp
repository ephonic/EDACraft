// =====================================================================
// mom/common/quadrature.cpp —— 高斯-勒让德积分实现
// =====================================================================
#include "mom/common/quadrature.hpp"

#include <cmath>

namespace mom {

GaussRule gauss_legendre(int n) {
    GaussRule g;
    switch (n) {
        case 1:
            g.nodes  = {0.0};
            g.weights = {2.0};
            break;
        case 2:
            g.nodes  = {-0.5773502691896257, 0.5773502691896257};
            g.weights = {1.0, 1.0};
            break;
        case 3:
            g.nodes  = {-0.7745966692414834, 0.0, 0.7745966692414834};
            g.weights = {0.5555555555555556, 0.8888888888888888, 0.5555555555555556};
            break;
        case 4:
            g.nodes  = {-0.8611363115940526, -0.3399810435848563,
                        0.3399810435848563,  0.8611363115940526};
            g.weights = {0.3478548451374538, 0.6521451548625461,
                         0.6521451548625461, 0.3478548451374538};
            break;
        default: // 回退到 2 点
            g.nodes  = {-0.5773502691896257, 0.5773502691896257};
            g.weights = {1.0, 1.0};
    }
    return g;
}

Real integrate_rect(QuadFn2 f, void* ctx,
                    Real x0, Real y0, Real dx, Real dy,
                    int nx, int ny) {
    const GaussRule gx = gauss_legendre(nx);
    const GaussRule gy = gauss_legendre(ny);
    Real sum = 0.0;
    const Real hx = dx * 0.5, hy = dy * 0.5;
    for (int i = 0; i < nx; ++i) {
        const Real xi = x0 + hx * gx.nodes[i];
        const Real wi = gx.weights[i] * hx;
        for (int j = 0; j < ny; ++j) {
            const Real yj = y0 + hy * gy.nodes[j];
            const Real wj = gy.weights[j] * hy;
            sum += wi * wj * f(xi, yj, ctx);
        }
    }
    return sum;
}

} // namespace mom
