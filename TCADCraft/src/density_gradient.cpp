#include "density_gradient.h"
#include "dg_parameter_contract.h"
#include <algorithm>
#include <cmath>

namespace tcad {

DensityGradient::DensityGradient(const Grid3D& grid) : g_(grid) {}

void DensityGradient::set_coefficients(real_t bn, real_t bp) {
    detail::validate_dg_finite({bn, bp}, "DG coefficients must be finite");
    bn_ = bn;
    bp_ = bp;
}

void DensityGradient::set_silicon_multivalley(bool enable,
                                              real_t longitudinal_mass,
                                              real_t transverse_mass,
                                              size_t subbands) {
    detail::validate_dg_finite({longitudinal_mass, transverse_mass},
                               "DG silicon effective masses must be finite");
    silicon_multivalley_ = enable;
    silicon_ml_ = longitudinal_mass;
    silicon_mt_ = transverse_mass;
    silicon_subbands_ = subbands;
}

void DensityGradient::set_interface_distance_factor(real_t factor) {
    detail::validate_dg_finite({factor}, "DG interface distance factor must be finite");
    interface_distance_factor_ = factor;
}

void DensityGradient::set_step_boundary(
    bool enable, real_t electron_barrier_eV, real_t hole_barrier_eV,
    real_t electron_barrier_mass, real_t hole_barrier_mass,
    real_t electron_gamma, real_t hole_gamma,
    real_t electron_theta, real_t hole_theta) {
    detail::validate_dg_finite({electron_barrier_eV, hole_barrier_eV,
        electron_barrier_mass, hole_barrier_mass, electron_gamma, hole_gamma,
        electron_theta, hole_theta}, "DG step-boundary parameters must be finite");
    step_boundary_enabled_ = enable;
    step_e_barrier_eV_ = electron_barrier_eV;
    step_h_barrier_eV_ = hole_barrier_eV;
    step_e_mass_ = electron_barrier_mass;
    step_h_mass_ = hole_barrier_mass;
    step_e_gamma_ = electron_gamma;
    step_h_gamma_ = hole_gamma;
    step_e_theta_ = electron_theta;
    step_h_theta_ = hole_theta;
}

void DensityGradient::set_thermal_voltage(real_t VT) {
    detail::validate_dg_finite({VT}, "DG thermal voltage must be finite");
    VT_ = VT;
}

real_t DensityGradient::electron_coefficient(size_t idx) const {
    if (!silicon_multivalley_ || idx >= L_conf_.size() ||
        L_conf_[idx] <= TCAD_CONST(0.0) || VT_ <= TCAD_CONST(0.0)) {
        return bn_;
    }

    // b = hbar^2/(6*q*m).  Preserve bn_ as a global calibration multiplier
    // relative to the historical Si DOS mass 0.26*m0, then resolve the two
    // normal-mass families explicitly.
    const real_t b_mass_constant = TCAD_CONST(4.885e-20) * TCAD_CONST(0.26);
    const real_t strength = bn_ / TCAD_CONST(4.885e-20);
    const real_t b_long = strength * b_mass_constant / silicon_ml_;
    const real_t b_trans = strength * b_mass_constant / silicon_mt_;
    const real_t pi2 = TCAD_CONST(9.869604401089358);
    const real_t inv_L2 = TCAD_CONST(1.0) / (L_conf_[idx] * L_conf_[idx]);
    const real_t E1_long = pi2 * b_long * inv_L2;
    const real_t E1_trans = pi2 * b_trans * inv_L2;

    auto partition = [&](real_t E1) -> real_t {
        real_t value = TCAD_CONST(0.0);
        for (size_t subband = 1; subband <= silicon_subbands_; ++subband) {
            real_t n2 = static_cast<real_t>(subband * subband);
            real_t exponent = -n2 * E1 / VT_;
            if (exponent >= -TCAD_CONST(100.0)) value += exp_q(exponent);
        }
        return value;
    };

    // For the two valleys whose longitudinal axis is normal to confinement,
    // the in-plane DOS mass is mt.  Each of the four transverse-normal
    // valleys has in-plane DOS mass sqrt(ml*mt).
    const real_t weight_long = TCAD_CONST(2.0) * silicon_mt_ * partition(E1_long);
    const real_t weight_trans =
        TCAD_CONST(4.0) * sqrt_q(silicon_ml_ * silicon_mt_) * partition(E1_trans);
    const real_t total = weight_long + weight_trans;
    if (!(total > EPSILON)) return bn_;
    return (weight_long * b_long + weight_trans * b_trans) / total;
}

void DensityGradient::laplace_sqrt_over_sqrt(const std::vector<real_t>& f,
                                             std::vector<real_t>& out) const {
    const size_t N = g_.npts();
    out.assign(N, TCAD_CONST(0.0));

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!semi_.empty() && idx < semi_.size() && semi_[idx] == 0) {
                    out[idx] = TCAD_CONST(0.0); continue;
                }
                real_t f_reg = f[idx];
                if (f_reg < TCAD_CONST(1.0e10)) f_reg = TCAD_CONST(1.0e10);
                real_t sqrt_f = sqrt_q(f_reg);
                if (sqrt_f < EPSILON) { out[idx] = TCAD_CONST(0.0); continue; }

                // Helper: is this neighbor semiconductor?
                auto is_semi = [&](size_t ni) -> bool {
                    if (ni >= N) return false;
                    if (semi_.empty()) return true;
                    return (ni < semi_.size() && semi_[ni] != 0);
                };
                // sqrt of f at a semiconductor node
                auto sq = [&](size_t ni) -> real_t {
                    real_t fn = (ni < N) ? f[ni] : f_reg;
                    if (fn < TCAD_CONST(1.0e10)) fn = TCAD_CONST(1.0e10);
                    return sqrt_q(fn);
                };

                real_t lap = TCAD_CONST(0.0);
                // Three-point second derivative on a non-uniform mesh:
                //   2/(h- + h+) * ((u+ - u0)/h+ - (u0 - u-)/h-)
                // This reduces to the usual central difference for h-=h+.
                // Poisson and SG transport already honor the explicit node
                // positions; DG must use the same metric or local interface
                // refinement changes the physical quantum length scale.
                auto second_derivative = [&](real_t gm, real_t gc, real_t gp,
                                             real_t hm, real_t hp) -> real_t {
                    return TCAD_CONST(2.0) / (hm + hp) *
                           ((gp - gc) / hp - (gc - gm) / hm);
                };
                // X axis: central difference with Dirichlet BC (ghost=0) at
                // insulator boundaries. Use the actual mesh metric here;
                // changing this distance as a function of film thickness
                // makes refinement change the physical boundary condition.
                if (i + 1 < g_.nx && i > 0) {
                    bool sp = is_semi(idx + 1), sm = is_semi(idx - 1);
                    real_t gp = sp ? sq(idx + 1) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    real_t gm = sm ? sq(idx - 1) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    if (sp || sm) {
                        real_t hm = g_.dx_edge(i - 1) *
                                    (sm ? TCAD_CONST(1.0) : interface_distance_factor_);
                        real_t hp = g_.dx_edge(i) *
                                    (sp ? TCAD_CONST(1.0) : interface_distance_factor_);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
                }
                // Y axis
                if (j + 1 < g_.ny && j > 0) {
                    bool sp = is_semi(idx + g_.nx), sm = is_semi(idx - g_.nx);
                    real_t gp = sp ? sq(idx + g_.nx) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    real_t gm = sm ? sq(idx - g_.nx) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    if (sp || sm) {
                        real_t hm = g_.dy_edge(j - 1) *
                                    (sm ? TCAD_CONST(1.0) : interface_distance_factor_);
                        real_t hp = g_.dy_edge(j) *
                                    (sp ? TCAD_CONST(1.0) : interface_distance_factor_);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
                }
                // Z axis
                if (k + 1 < g_.nz && k > 0) {
                    bool sp = is_semi(idx + g_.nx*g_.ny), sm = is_semi(idx - g_.nx*g_.ny);
                    real_t gp = sp ? sq(idx + g_.nx*g_.ny) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    real_t gm = sm ? sq(idx - g_.nx*g_.ny) :
                        (step_boundary_enabled_ ? sqrt_f : TCAD_CONST(0.0));
                    if (sp || sm) {
                        real_t hm = g_.dz_edge(k - 1) *
                                    (sm ? TCAD_CONST(1.0) : interface_distance_factor_);
                        real_t hp = g_.dz_edge(k) *
                                    (sp ? TCAD_CONST(1.0) : interface_distance_factor_);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
                }
                out[idx] = lap / sqrt_f;
            }
        }
    }
}

void DensityGradient::apply_step_boundary(std::vector<real_t>& Qn,
                                          std::vector<real_t>& Qp) const {
    if (!step_boundary_enabled_ || semi_.empty() || !(VT_ > TCAD_CONST(0.0))) return;

    auto is_semi = [&](size_t idx) -> bool {
        return idx < semi_.size() && semi_[idx] != 0;
    };
    std::vector<real_t> Qn_new = Qn, Qp_new = Qp;
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                const size_t idx = g_.index(i, j, k);
                if (!is_semi(idx)) continue;
                real_t lambda_n_sum = TCAD_CONST(0.0), lambda_p_sum = TCAD_CONST(0.0);
                size_t faces = 0;
                auto add_face = [&](bool outside, bool has_inside,
                                    size_t inside, bool has_second,
                                    size_t second, real_t spacing,
                                    real_t second_spacing) {
                    if (!outside || !has_inside || !is_semi(inside)) return;
                    real_t lambda_n_interior = -Qn[inside];
                    real_t lambda_p_interior = -Qp[inside];
                    real_t effective_spacing_n = spacing;
                    real_t effective_spacing_p = spacing;
                    second_order_boundary_stencil(
                        -Qn[inside],
                        has_second && is_semi(second) ? -Qn[second] : -Qn[inside],
                        spacing, second_spacing,
                        has_second && is_semi(second),
                        lambda_n_interior, effective_spacing_n);
                    second_order_boundary_stencil(
                        -Qp[inside],
                        has_second && is_semi(second) ? -Qp[second] : -Qp[inside],
                        spacing, second_spacing,
                        has_second && is_semi(second),
                        lambda_p_interior, effective_spacing_p);
                    const real_t lambda_n = step_boundary_value(
                        lambda_n_interior, effective_spacing_n,
                        step_e_barrier_eV_, step_e_mass_,
                        step_e_gamma_, step_e_theta_);
                    const real_t lambda_p = step_boundary_value(
                        lambda_p_interior, effective_spacing_p,
                        step_h_barrier_eV_, step_h_mass_,
                        step_h_gamma_, step_h_theta_);
                    lambda_n_sum += lambda_n;
                    lambda_p_sum += lambda_p;
                    ++faces;
                };
                if (i > 0 && i + 1 < g_.nx) {
                    add_face(!is_semi(idx - 1), true, idx + 1,
                             i + 2 < g_.nx, idx + 2, g_.dx_edge(i),
                             i + 1 < g_.nx - 1 ? g_.dx_edge(i + 1) : TCAD_CONST(1.0));
                    add_face(!is_semi(idx + 1), true, idx - 1,
                             i > 1, idx - 2, g_.dx_edge(i - 1),
                             i > 1 ? g_.dx_edge(i - 2) : TCAD_CONST(1.0));
                }
                if (j > 0 && j + 1 < g_.ny) {
                    add_face(!is_semi(idx - g_.nx), true, idx + g_.nx,
                             j + 2 < g_.ny, idx + 2 * g_.nx,
                             g_.dy_edge(j),
                             j + 1 < g_.ny - 1 ? g_.dy_edge(j + 1) : TCAD_CONST(1.0));
                    add_face(!is_semi(idx + g_.nx), true, idx - g_.nx,
                             j > 1, idx - 2 * g_.nx, g_.dy_edge(j - 1),
                             j > 1 ? g_.dy_edge(j - 2) : TCAD_CONST(1.0));
                }
                const size_t plane = g_.nx * g_.ny;
                if (k > 0 && k + 1 < g_.nz) {
                    add_face(!is_semi(idx - plane), true, idx + plane,
                             k + 2 < g_.nz, idx + 2 * plane,
                             g_.dz_edge(k),
                             k + 1 < g_.nz - 1 ? g_.dz_edge(k + 1) : TCAD_CONST(1.0));
                    add_face(!is_semi(idx + plane), true, idx - plane,
                             k > 1, idx - 2 * plane, g_.dz_edge(k - 1),
                             k > 1 ? g_.dz_edge(k - 2) : TCAD_CONST(1.0));
                }
                if (faces > 0) {
                    Qn_new[idx] = -lambda_n_sum / static_cast<real_t>(faces);
                    Qp_new[idx] = -lambda_p_sum / static_cast<real_t>(faces);
                }
            }
        }
    }
    Qn.swap(Qn_new);
    Qp.swap(Qp_new);
}

real_t DensityGradient::step_boundary_value(
    real_t interior_lambda, real_t spacing, real_t barrier, real_t mass,
    real_t gamma, real_t theta) const {
    if (!(spacing > TCAD_CONST(0.0)) || !(barrier > TCAD_CONST(0.0)) || !(mass > TCAD_CONST(0.0)) ||
        !(gamma > TCAD_CONST(0.0)) || !(theta > TCAD_CONST(0.0)) || !(VT_ > TCAD_CONST(0.0))) {
        return interior_lambda;
    }
    const real_t hbar = TCAD_CONST(1.054571817e-34);
    const real_t q = TCAD_CONST(1.602176634e-19);
    const real_t m0 = TCAD_CONST(9.1093837015e-31);
    // Sentaurus Device Eq. 250 in voltage/eV units.
    const real_t inverse_length = sqrt_q(
        TCAD_CONST(24.0) * mass * m0 * q * VT_ / (hbar * hbar * gamma));
    auto f_step = [&](real_t x) -> real_t {
        if (abs_q(x) < TCAD_CONST(1.0e-5)) {
            const real_t value = TCAD_CONST(0.5) + x / TCAD_CONST(6.0) + x * x / TCAD_CONST(24.0);
            return sqrt_q(std::max(value, TCAD_CONST(0.0)));
        }
        const real_t value = ((exp_q(x) - TCAD_CONST(1.0)) / x - TCAD_CONST(1.0)) / x;
        return sqrt_q(std::max(value, TCAD_CONST(0.0)));
    };
    auto residual = [&](real_t lambda) -> real_t {
        const real_t x = TCAD_CONST(2.0) * theta * (lambda - barrier) / VT_;
        return lambda - interior_lambda - spacing * inverse_length *
            (barrier - lambda) * f_step(x);
    };
    real_t lo = interior_lambda;
    const real_t hi_initial = barrier;
    real_t hi = hi_initial;
    if (!(lo < hi) || residual(lo) >= TCAD_CONST(0.0)) return lo;
    for (size_t iteration = 0; iteration < 80; ++iteration) {
        const real_t mid = TCAD_CONST(0.5) * (lo + hi);
        if (residual(mid) > TCAD_CONST(0.0)) hi = mid;
        else lo = mid;
    }
    return TCAD_CONST(0.5) * (lo + hi);
}

void DensityGradient::second_order_boundary_stencil(
    real_t first, real_t second, real_t first_spacing,
    real_t second_spacing, bool has_second, real_t& effective_interior,
    real_t& effective_spacing) const {
    effective_interior = first;
    effective_spacing = first_spacing;
    if (!has_second || !(first_spacing > TCAD_CONST(0.0)) ||
        !(second_spacing > TCAD_CONST(0.0))) return;

    // Non-uniform three-point outward derivative at a material-side boundary:
    //   a0*l0 + a1*l1 + a2*l2 = F(l0)
    // Rewrite it as l0 - l_eff = h_eff*F(l0), which can reuse the
    // equation-250 nonlinear root. Uniform spacing gives
    // l_eff=(4*l1-l2)/3 and h_eff=2*h/3.
    const real_t h1 = first_spacing;
    const real_t h2 = second_spacing;
    const real_t a0 = (TCAD_CONST(2.0) * h1 + h2) / (h1 * (h1 + h2));
    const real_t a1 = -(h1 + h2) / (h1 * h2);
    const real_t a2 = h1 / (h2 * (h1 + h2));
    if (!(a0 > TCAD_CONST(0.0))) return;
    effective_interior = -(a1 * first + a2 * second) / a0;
    effective_spacing = TCAD_CONST(1.0) / a0;
}

void DensityGradient::quantum_potential_potential_form(
    const std::vector<real_t>& n,
    const std::vector<real_t>& p,
    const std::vector<real_t>& Qn_reference,
    const std::vector<real_t>& Qp_reference,
    std::vector<real_t>& Qn,
    std::vector<real_t>& Qp) const {
    const size_t N = g_.npts();
    if (n.size() != N || p.size() != N ||
        Qn_reference.size() != N || Qp_reference.size() != N ||
        !(VT_ > TCAD_CONST(0.0))) {
        quantum_potential(n, p, Qn, Qp);
        return;
    }

    auto solve_species = [&](const std::vector<real_t>& carrier,
                             const std::vector<real_t>& reference_Q,
                             const std::vector<real_t>& dos,
                             bool electron,
                             std::vector<real_t>& Q) {
        const real_t fallback_dos = electron ? TCAD_CONST(2.780e25) : TCAD_CONST(3.143e25);
        std::vector<real_t> H(N, TCAD_CONST(0.0)), lambda(N, TCAD_CONST(0.0));
        for (size_t idx = 0; idx < N; ++idx) {
            const real_t local_dos =
                idx < dos.size() && dos[idx] > EPSILON ? dos[idx] : fallback_dos;
            const real_t local_carrier = std::max(carrier[idx], TCAD_CONST(1.0e10));
            // Sentaurus lambda has the opposite sign to TCADCraft's Q.
            // Freeze the quasi-Fermi source from the preceding nonlinear
            // state instead of differentiating noisy carrier data directly.
            lambda[idx] = -reference_Q[idx];
            H[idx] = VT_ * log_q(local_carrier / local_dos) + lambda[idx];
        }

        auto is_semi = [&](size_t idx) -> bool {
            return semi_.empty() || (idx < semi_.size() && semi_[idx] != 0);
        };
        const size_t plane = g_.nx * g_.ny;
        const real_t cap = TCAD_CONST(16.0) * VT_;
        // Nonlinear Gauss-Seidel is substantially faster than a Jacobi copy
        // on strongly confined, locally refined MOS meshes.  The potential-
        // form equation must nevertheless be solved well inside the outer Q
        // fixed-point gate.  Eight historical sweeps left unresolved spatial
        // modes in strong inversion; the outer Gummel map then converged to a
        // nonzero Q-residual cycle that was insensitive to further damping.
        // Use a strict update-equivalent PDE residual and a bounded cap.  Easy
        // states still exit early, while refined devices no longer delegate
        // an under-solved inner PDE to hundreds of outer iterations.
        constexpr size_t maximum_potential_form_sweeps = 64;
        const real_t potential_form_update_tol = TCAD_CONST(1.0e-8) * VT_;

        for (size_t iteration = 0;
             iteration < maximum_potential_form_sweeps; ++iteration) {
            real_t max_change = TCAD_CONST(0.0);
            for (size_t k = 0; k < g_.nz; ++k) {
                for (size_t j = 0; j < g_.ny; ++j) {
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, j, k);
                        if (!is_semi(idx) || carrier[idx] >= TCAD_CONST(5.0e25)) {
                            lambda[idx] = TCAD_CONST(0.0);
                            continue;
                        }

                        real_t boundary_sum = TCAD_CONST(0.0);
                        size_t boundary_faces = 0;
                        auto add_boundary = [&](bool outside, bool has_inside,
                                                size_t inside, bool has_second,
                                                size_t second, real_t spacing,
                                                real_t second_spacing) {
                            if (!outside || !has_inside || !is_semi(inside)) return;
                            real_t effective_interior = lambda[inside];
                            real_t effective_spacing = spacing;
                            second_order_boundary_stencil(
                                lambda[inside],
                                has_second && is_semi(second)
                                    ? lambda[second] : lambda[inside],
                                spacing, second_spacing,
                                has_second && is_semi(second),
                                effective_interior, effective_spacing);
                            // The public interface-distance calibration is a
                            // boundary-metric property and must apply to the
                            // potential-form equation as well as the density
                            // stencil.  Previously Eq. (248)/(250) silently
                            // ignored it, so shared-node FinFET/GAA interfaces
                            // could not represent their material-side distance
                            // without changing barrier physics.
                            effective_spacing *= interface_distance_factor_;
                            real_t value = effective_interior;
                            if (step_boundary_enabled_) {
                                value = electron
                                    ? step_boundary_value(
                                          value, effective_spacing,
                                          step_e_barrier_eV_,
                                          step_e_mass_, step_e_gamma_, step_e_theta_)
                                    : step_boundary_value(
                                          value, effective_spacing,
                                          step_h_barrier_eV_,
                                          step_h_mass_, step_h_gamma_, step_h_theta_);
                            }
                            boundary_sum += value;
                            ++boundary_faces;
                        };
                        if (!semi_.empty()) {
                            if (i > 0 && i + 1 < g_.nx) {
                                add_boundary(!is_semi(idx - 1), true, idx + 1,
                                             i + 2 < g_.nx, idx + 2,
                                             g_.dx_edge(i),
                                             i + 1 < g_.nx - 1
                                                 ? g_.dx_edge(i + 1) : TCAD_CONST(1.0));
                                add_boundary(!is_semi(idx + 1), true, idx - 1,
                                             i > 1, idx - 2,
                                             g_.dx_edge(i - 1),
                                             i > 1 ? g_.dx_edge(i - 2) : TCAD_CONST(1.0));
                            }
                            if (j > 0 && j + 1 < g_.ny) {
                                add_boundary(!is_semi(idx - g_.nx), true,
                                             idx + g_.nx, j + 2 < g_.ny,
                                             idx + 2 * g_.nx, g_.dy_edge(j),
                                             j + 1 < g_.ny - 1
                                                 ? g_.dy_edge(j + 1) : TCAD_CONST(1.0));
                                add_boundary(!is_semi(idx + g_.nx), true,
                                             idx - g_.nx, j > 1,
                                             idx - 2 * g_.nx, g_.dy_edge(j - 1),
                                             j > 1 ? g_.dy_edge(j - 2) : TCAD_CONST(1.0));
                            }
                            if (k > 0 && k + 1 < g_.nz) {
                                add_boundary(!is_semi(idx - plane), true,
                                             idx + plane, k + 2 < g_.nz,
                                             idx + 2 * plane, g_.dz_edge(k),
                                             k + 1 < g_.nz - 1
                                                 ? g_.dz_edge(k + 1) : TCAD_CONST(1.0));
                                add_boundary(!is_semi(idx + plane), true,
                                             idx - plane, k > 1,
                                             idx - 2 * plane, g_.dz_edge(k - 1),
                                             k > 1 ? g_.dz_edge(k - 2) : TCAD_CONST(1.0));
                            }
                        }

                        real_t target = TCAD_CONST(0.0);
                        if (boundary_faces > 0) {
                            target = boundary_sum /
                                static_cast<real_t>(boundary_faces);
                        } else {
                            const real_t b = electron ? electron_coefficient(idx) : bp_;
                            const real_t a = b / (TCAD_CONST(2.0) * VT_);
                            real_t coefficient_sum = TCAD_CONST(0.0);
                            real_t lambda_neighbor_sum = TCAD_CONST(0.0);
                            real_t laplace_H = TCAD_CONST(0.0);
                            real_t gradient_squared = TCAD_CONST(0.0);
                            auto add_axis = [&](bool available, size_t minus,
                                                size_t plus, real_t hm, real_t hp) {
                                if (!available || !is_semi(minus) || !is_semi(plus) ||
                                    !(hm > TCAD_CONST(0.0)) || !(hp > TCAD_CONST(0.0))) return;
                                const real_t cm = TCAD_CONST(2.0) / (hm * (hm + hp));
                                const real_t cp = TCAD_CONST(2.0) / (hp * (hm + hp));
                                coefficient_sum += cm + cp;
                                lambda_neighbor_sum +=
                                    cm * lambda[minus] + cp * lambda[plus];
                                laplace_H += cm * H[minus] + cp * H[plus] -
                                    (cm + cp) * H[idx];
                                const real_t gradient =
                                    (H[plus] - lambda[plus] -
                                     H[minus] + lambda[minus]) / (hm + hp);
                                gradient_squared += gradient * gradient;
                            };
                            add_axis(i > 0 && i + 1 < g_.nx, idx - 1, idx + 1,
                                     i > 0 ? g_.dx_edge(i - 1) : TCAD_CONST(1.0),
                                     i + 1 < g_.nx ? g_.dx_edge(i) : TCAD_CONST(1.0));
                            add_axis(j > 0 && j + 1 < g_.ny, idx - g_.nx,
                                     idx + g_.nx,
                                     j > 0 ? g_.dy_edge(j - 1) : TCAD_CONST(1.0),
                                     j + 1 < g_.ny ? g_.dy_edge(j) : TCAD_CONST(1.0));
                            add_axis(k > 0 && k + 1 < g_.nz, idx - plane,
                                     idx + plane,
                                     k > 0 ? g_.dz_edge(k - 1) : TCAD_CONST(1.0),
                                     k + 1 < g_.nz ? g_.dz_edge(k) : TCAD_CONST(1.0));
                            const real_t rhs = -a * laplace_H -
                                b * gradient_squared /
                                    (TCAD_CONST(4.0) * VT_ * VT_);
                            target = (rhs + a * lambda_neighbor_sum) /
                                (TCAD_CONST(1.0) + a * coefficient_sum);
                        }
                        target = std::max(-cap, std::min(cap, target));
                        const real_t old_value = lambda[idx];
                        // Mild under-relaxation protects the nonlinear
                        // gradient term without discarding the Gauss-Seidel
                        // propagation gained during this sweep.
                        lambda[idx] = TCAD_CONST(0.25) * old_value + TCAD_CONST(0.75) * target;
                        max_change = std::max(
                            max_change, abs_q(lambda[idx] - old_value));
                    }
                }
            }
            if (max_change <= potential_form_update_tol) break;
        }
        Q.resize(N);
        for (size_t idx = 0; idx < N; ++idx) Q[idx] = -lambda[idx];
    };

    solve_species(n, Qn_reference, Nc_, true, Qn);
    solve_species(p, Qp_reference, Nv_, false, Qp);
}

void DensityGradient::quantum_potential(const std::vector<real_t>& n,
                                        const std::vector<real_t>& p,
                                        std::vector<real_t>& Qn,
                                        std::vector<real_t>& Qp) const {
    laplace_sqrt_over_sqrt(n, Qn);
    laplace_sqrt_over_sqrt(p, Qp);
    for (size_t i = 0; i < g_.npts(); ++i) {
        Qn[i] = electron_coefficient(i) * Qn[i];
        Qp[i] = bp_ * Qp[i];
    }
    apply_step_boundary(Qn, Qp);
    // Effective DOS for the flat-profile finite-well fallback.
    const real_t Nc_eff = TCAD_CONST(2.780e25);
    const real_t Nv_eff = TCAD_CONST(3.143e25);
    for (size_t i = 0; i < g_.npts(); ++i) {
        bool lap_active_n = (abs_q(Qn[i]) > TCAD_CONST(1e-15));
        bool lap_active_p = (abs_q(Qp[i]) > TCAD_CONST(1e-15));
        real_t bn_local = electron_coefficient(i);

        // Degenerately doped source/drain reservoirs are contact-controlled,
        // not quantum wells. A transverse interface correction there creates
        // an artificial Q step beside the ohmic Dirichlet boundary.
        bool reservoir_n = n[i] >= TCAD_CONST(5.0e25);
        bool reservoir_p = p[i] >= TCAD_CONST(5.0e25);
        if (reservoir_n) Qn[i] = TCAD_CONST(0.0);
        if (reservoir_p) Qp[i] = TCAD_CONST(0.0);

        if (!L_conf_.empty() && i < L_conf_.size() && L_conf_[i] > TCAD_CONST(0.0)) {
            real_t pi2 = TCAD_CONST(9.8696);
            real_t E1n = pi2 * bn_local / (L_conf_[i] * L_conf_[i]);
            real_t E1p = pi2 * bp_ / (L_conf_[i] * L_conf_[i]);
            real_t fn = TCAD_CONST(1.0) / (TCAD_CONST(1.0) + (n[i] / Nc_eff) * (n[i] / Nc_eff));
            real_t fp = TCAD_CONST(1.0) / (TCAD_CONST(1.0) + (p[i] / Nv_eff) * (p[i] / Nv_eff));
            real_t Qn_model = -E1n * fn;
            real_t Qp_model = -E1p * fp;

            if (!reservoir_n && !lap_active_n) {
                // Laplacian was zero (flat profile): use model, but ONLY
                // when n is below the S/D doping level.  In S/D regions
                // (n~1e26) the z-profile is also flat, but the carriers
                // come from doping, not gate confinement — DG shouldn't
                // apply there.
                if (n[i] < TCAD_CONST(5.0e25)) {
                    Qn[i] = Qn_model;
                }
            } else if (!reservoir_n) {
                // Preserve either sign of the active Laplacian.  This is a
                // solver overflow guard, so express it in thermal-energy
                // units instead of changing it with film thickness.  The old
                // 9*E1/64*E1 geometry interpolation clipped the converged
                // 5 nm Sentaurus interface target (about 8.5*VT) before the
                // boundary model could be calibrated.
                const real_t transient_cap = TCAD_CONST(16.0) * VT_;
                if (Qn[i] < -transient_cap) Qn[i] = -transient_cap;
                if (Qn[i] >  transient_cap) Qn[i] =  transient_cap;
            }
            if (!reservoir_p && !lap_active_p) {
                if (p[i] < TCAD_CONST(5.0e25)) Qp[i] = Qp_model;
            } else if (!reservoir_p) {
                const real_t transient_cap = TCAD_CONST(16.0) * VT_;
                if (Qp[i] < -transient_cap) Qp[i] = -transient_cap;
                if (Qp[i] >  transient_cap) Qp[i] =  transient_cap;
            }
        }
        // A discontinuous doping profile on an all-semiconductor grid has no
        // finite-well L_conf cap, while the discrete sqrt(n) curvature can be
        // singular. Bound only such pathological transients to the same
        // exponent range used by correct(); calibrated MOS values (~60 mV at
        // 300 K) remain comfortably inside this +/-4VT guard.
        const bool has_finite_well =
            !L_conf_.empty() && i < L_conf_.size() && L_conf_[i] > TCAD_CONST(0.0);
        if (!has_finite_well) {
            const real_t transient_cap = TCAD_CONST(4.0) * VT_;
            if (Qn[i] < -transient_cap) Qn[i] = -transient_cap;
            if (Qn[i] >  transient_cap) Qn[i] =  transient_cap;
            if (Qp[i] < -transient_cap) Qp[i] = -transient_cap;
            if (Qp[i] >  transient_cap) Qp[i] =  transient_cap;
        }
    }
}

void DensityGradient::correct(const std::vector<real_t>& n,
                              const std::vector<real_t>& p,
                              std::vector<real_t>& n_q,
                              std::vector<real_t>& p_q) const {
    std::vector<real_t> Qn, Qp;
    quantum_potential(n, p, Qn, Qp);
    const size_t N = g_.npts();
    n_q.resize(N);
    p_q.resize(N);
    for (size_t i = 0; i < N; ++i) {
        // Phase 3.6 sign fix (audit §16.3): the Ancona-Stafford DG quantum
        // potential is V_q = -(b/2)·∇²√n/√n, applied as n_q = n·exp(-V_q/VT),
        // i.e. n_q = n·exp(+(b/2)·∇²√n/√n/VT).  At a density peak ∇²√n<0,
        // so the exponent is negative and exp<1 -> DG DEPLETES the interface
        // peak (the physical quantum-confinement effect).
        //
        // Qn here is b·∇²√n/√n (without the 1/2 factor and without the
        // leading minus).  So the correct exponential is exp(+Qn/VT).
        // The previous code used exp(-Qn/VT), which amplified the peak —
        // the opposite of the intended physics.  Flipped here.
        real_t arg_n = Qn[i] / VT_;
        real_t arg_p = Qp[i] / VT_;
        // Phase 3.5 (audit §16): with the physical b_n (V·m²), the exponent
        // is O(1) and no clamp is needed for correctness.  We keep a wide
        // guard [-100, 100] purely to absorb transients from pathological
        // grids (NaN/Inf protection) during iteration; at steady state on a
        // sane grid the exponent never approaches this band.
        // Tight guard [-4,4]: the physical DG exponent is O(1); values beyond
        // indicate the n->0 singularity leaking through and would amplify
        // carriers by exp(>4)=55x (spurious).  Regularization in the sqrt
        // path keeps it O(1) at steady state; this is a transient guard.
        if (arg_n > TCAD_CONST(4.0)) arg_n = TCAD_CONST(4.0);
        if (arg_n < -TCAD_CONST(4.0)) arg_n = -TCAD_CONST(4.0);
        if (arg_p > TCAD_CONST(4.0)) arg_p = TCAD_CONST(4.0);
        if (arg_p < -TCAD_CONST(4.0)) arg_p = -TCAD_CONST(4.0);
        n_q[i] = n[i] * exp_q(arg_n);
        p_q[i] = p[i] * exp_q(arg_p);
    }
}

void DensityGradient::compute_confinement() {
    const size_t N = g_.npts();
    L_conf_.assign(N, TCAD_CONST(0.0));  // 0 = no finite-well fallback correction
    N_conf_.assign(N, 0);
    if (semi_.empty()) return;  // all-semiconductor: no insulator boundaries

    auto is_semi = [&](size_t idx) -> bool {
        return (idx < semi_.size() && semi_[idx] != 0);
    };

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!is_semi(idx)) continue;

                // For each axis, find the distance to the nearest insulator
                // boundary.  L_axis = extent of contiguous semiconductor
                // region containing this node along that axis.
                real_t L_min = TCAD_CONST(1e10);  // start huge
                size_t N_min = 0;

                // Z axis.  A finite-well fallback is valid only when this is
                // a real mesh dimension and the semiconductor segment is
                // bounded by insulator nodes on both sides.  Treating nz=1 as
                // a one-cell quantum well created a spurious ~1 nm confinement
                // energy in every 1-D device.
                if (g_.nz > 1) {
                    size_t k0 = k, k1 = k;
                    while (k0 > 0 && is_semi(g_.index(i, j, k0 - 1))) --k0;
                    while (k1 + 1 < g_.nz && is_semi(g_.index(i, j, k1 + 1))) ++k1;
                    if (k0 > 0 && k1 + 1 < g_.nz) {
                        real_t Lz = TCAD_CONST(0.0);
                        for (size_t kk = k0; kk <= k1; ++kk)
                            Lz += g_.dz_cell(kk);
                        if (Lz < L_min) {
                            L_min = Lz;
                            N_min = k1 - k0 + 1;
                        }
                    }
                }
                // X axis
                if (g_.nx > 1) {
                    size_t i0 = i, i1 = i;
                    while (i0 > 0 && is_semi(g_.index(i0 - 1, j, k))) --i0;
                    while (i1 + 1 < g_.nx && is_semi(g_.index(i1 + 1, j, k))) ++i1;
                    if (i0 > 0 && i1 + 1 < g_.nx) {
                        real_t Lx = TCAD_CONST(0.0);
                        for (size_t ii = i0; ii <= i1; ++ii)
                            Lx += g_.dx_cell(ii);
                        if (Lx < L_min) {
                            L_min = Lx;
                            N_min = i1 - i0 + 1;
                        }
                    }
                }
                // Y axis
                if (g_.ny > 1) {
                    size_t j0 = j, j1 = j;
                    while (j0 > 0 && is_semi(g_.index(i, j0 - 1, k))) --j0;
                    while (j1 + 1 < g_.ny && is_semi(g_.index(i, j1 + 1, k))) ++j1;
                    if (j0 > 0 && j1 + 1 < g_.ny) {
                        real_t Ly = TCAD_CONST(0.0);
                        for (size_t jj = j0; jj <= j1; ++jj)
                            Ly += g_.dy_cell(jj);
                        if (Ly < L_min) {
                            L_min = Ly;
                            N_min = j1 - j0 + 1;
                        }
                    }
                }

                if (L_min < TCAD_CONST(1e9)) {
                    L_conf_[idx] = L_min;
                    N_conf_[idx] = N_min;
                }
            }
        }
    }
}

} // namespace tcad
