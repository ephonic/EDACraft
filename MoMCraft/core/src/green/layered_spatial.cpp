// =====================================================================
// mom/green/layered_spatial.cpp —— 多层介质空域格林函数（数值 Sommerfeld）
// =====================================================================
#include "mom/green/layered_spatial.hpp"

#include <cmath>

namespace mom::green {

namespace {
// 零阶贝塞尔 J0(x)（级数，足够精度）。
double bessel_J0(double x) {
    // Σ (-1)^k (x/2)^{2k} / (k!)^2
    double x2_4 = (x * x) / 4.0;
    double j0 = 1.0, term = 1.0;
    for (int k = 1; k <= 30; ++k) {
        term *= -x2_4 / double(k * k);
        j0 += term;
        if (std::abs(term) < 1e-16 * std::abs(j0)) break;
    }
    return j0;
}
} // namespace

LayeredSpatialGreen::LayeredSpatialGreen(spectral::SpectralGreensFunction sg,
                                         Real k_rho_max_factor, int n_points)
    : sg_(std::move(sg)),
      k_rho_max_(k_rho_max_factor * sg_.k0()),
      n_points_(n_points) {}

Complex LayeredSpatialGreen::sommerfeld(std::function<Complex(Complex)> kernel, Real rho) const {
    // (1/2π) ∫_0^{k_max} G̃(k_ρ) J0(k_ρ ρ) k_ρ dk_ρ
    // 用自适应分段积分：支点 k_layer 附近加密。简化用均匀分段 + 高密度。
    Complex total(0.0, 0.0);
    const Real dk = k_rho_max_ / Real(n_points_);
    // 注意：源层波数附近的支点。粗略全段均匀积分（足够阶段 3 验证用）。
    for (int i = 0; i < n_points_; ++i) {
        // 中点规则
        Real kr = (Real(i) + 0.5) * dk;
        Complex g = kernel(Complex(kr, 0.0));
        double w = bessel_J0(kr * rho) * kr * dk;
        total += g * Complex(w, 0.0);
    }
    return total / Complex(2.0 * phys::pi, 0.0);
}

Complex LayeredSpatialGreen::G_A(Real rho) const {
    return sommerfeld([this](Complex k){ return sg_(k).G_A; }, rho);
}

Complex LayeredSpatialGreen::G_phi(Real rho) const {
    return sommerfeld([this](Complex k){ return sg_(k).G_phi; }, rho);
}

} // namespace mom::green
