// =====================================================================
// mom/green/dyadic.cpp —— 并矢格林函数实现（水平电流版本）
// =====================================================================
#include "mom/green/dyadic.hpp"
#include "mom/green/qwe.hpp"

namespace mom::green::dyadic {

Complex SpatialDyadic::GA(Real rho) const {
    if (!pole_list.empty())
        return qwe::spatial_GA_qwe_poles(*sg_ptr, rho, eps_r, pole_list, n_intervals, gauss_order);
    return qwe::spatial_GA_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

Complex SpatialDyadic::GAzz(Real rho) const {
    // G_Azz = TM 电压 TLGF（垂直电流矢量位）
    return qwe::spatial_GAzz_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

Complex SpatialDyadic::GAxz(Real rho) const {
    // G_Axz = 水平-垂直交叉耦合（J1 Sommerfeld 积分）
    return qwe::spatial_GAxz_qwe(*sg_ptr, rho, eps_r, n_intervals, gauss_order);
}

Complex SpatialDyadic::Gphi(Real rho) const {
    if (!pole_list.empty())
        return qwe::spatial_Gphi_qwe_poles(*sg_ptr, rho, eps_r, pole_list, n_intervals, gauss_order);
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
    dyad.pole_list = pole_list;  // 存储极点（不再忽略）

    return dyad;
}

} // namespace mom::green::dyadic
