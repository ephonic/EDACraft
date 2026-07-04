// =====================================================================
// mom/green/dyadic.cpp —— 并矢格林函数实现（水平电流版本）
// =====================================================================
#include "mom/green/dyadic.hpp"
#include "mom/green/qwe.hpp"

namespace mom::green::dyadic {

Complex SpatialDyadic::GA(Real rho) const {
    return qwe::spatial_GA_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

Complex SpatialDyadic::GAzz(Real rho) const {
    // G_Azz 对应于 TM 电压 TLGF（G_P）
    // 对于同层情况，可以用 G_P 近似
    // 这里简化处理：使用与 G_A 相同的函数（对于水平电流）
    // 对于垂直电流，需要更复杂的处理（不同层之间的耦合）
    // TODO: 实现完整的 G_Azz（TM 电压 TLGF）
    return qwe::spatial_GA_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

Complex SpatialDyadic::Gphi(Real rho) const {
    return qwe::spatial_Gphi_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

SpatialDyadic build_horizontal_dyadic(
    const spectral::SpectralGreensFunction& sg,
    Real eps_r,
    const std::vector<poles::Pole>& pole_list,
    int n_intervals, int gauss_order) {

    SpatialDyadic dyad;
    dyad.sg_ptr = std::make_shared<spectral::SpectralGreensFunction>(sg);
    dyad.eps_r = eps_r;
    dyad.n_intervals = n_intervals;
    dyad.gauss_order = gauss_order;

    return dyad;
}

} // namespace mom::green::dyadic
