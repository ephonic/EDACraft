#include "newton_solver.h"
#include "statistics.h"
#include "density_gradient.h"
#include <iostream>
#include <cstdio>
#include <cmath>
#include <algorithm>

namespace tcad {

NewtonSolver::NewtonSolver(const Grid3D& grid, const NewtonOptions& opt)
    : g_(grid), opt_(opt) {
    const size_t N = g_.npts();
    eps_.assign(N, EPS0 * 11.7Q);
    mu_n_.assign(N, 0.14Q);
    mu_p_.assign(N, 0.045Q);
    Nd_minus_Na_.assign(N, 0.0Q);
    charge_volume_fraction_.assign(N, 1.0Q);
    tau_n_.assign(N, 1e100Q);
    tau_p_.assign(N, 1e100Q);
    G_opt_.assign(N, 0.0Q);
}

void NewtonSolver::set_permittivity(const std::vector<real_t>& eps) {
    eps_ = eps;
}

void NewtonSolver::set_edge_permittivity(
    const std::vector<real_t>& x_plus,
    const std::vector<real_t>& x_minus,
    const std::vector<real_t>& y_plus,
    const std::vector<real_t>& y_minus,
    const std::vector<real_t>& z_plus,
    const std::vector<real_t>& z_minus) {
    const size_t N = g_.npts();
    for (const auto* values : {&x_plus, &x_minus, &y_plus, &y_minus,
                               &z_plus, &z_minus}) {
        if (!values->empty() && values->size() != N)
            throw std::invalid_argument("Newton edge permittivity size mismatch");
    }
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
}

real_t NewtonSolver::edge_epsilon(
    size_t idx, size_t nbr,
    const std::vector<real_t>& override_values) const {
    if (override_values.size() == g_.npts() && override_values[idx] > 0.0Q)
        return override_values[idx];
    return 2.0Q * eps_[idx] * eps_[nbr] /
           (eps_[idx] + eps_[nbr] + 1e-30Q);
}

real_t NewtonSolver::active_carrier_width(
    size_t idx, size_t j, size_t k, int axis,
    const std::vector<real_t>& mobility) const {
    // A node on a semiconductor/insulator interface belongs to the mobile
    // material only on the semiconductor side.  Clip the transverse control
    // volume at zero-mobility neighbours so Newton uses the same finite-volume
    // geometry as Gummel and as terminal-current integration.
    if (axis == 1) {
        real_t width = g_.dy_cell(j);
        if (j > 0 && mobility[idx - g_.nx] < EPSILON)
            width -= 0.5Q * g_.dy_edge(j - 1);
        if (j + 1 < g_.ny && mobility[idx + g_.nx] < EPSILON)
            width -= 0.5Q * g_.dy_edge(j);
        return width > EPSILON ? width : g_.dy_cell(j);
    }
    if (axis == 2) {
        real_t width = g_.dz_cell(k);
        const size_t z_stride = g_.nx * g_.ny;
        if (k > 0 && mobility[idx - z_stride] < EPSILON)
            width -= 0.5Q * g_.dz_edge(k - 1);
        if (k + 1 < g_.nz && mobility[idx + z_stride] < EPSILON)
            width -= 0.5Q * g_.dz_edge(k);
        return width > EPSILON ? width : g_.dz_cell(k);
    }
    throw std::invalid_argument("active carrier width axis must be y or z");
}

void NewtonSolver::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    mu_n_ = mu_n; mu_p_ = mu_p;
}

void NewtonSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    Nd_minus_Na_ = Nd_minus_Na;
}

void NewtonSolver::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("charge volume fraction size mismatch");
    charge_volume_fraction_ = fraction;
}

void NewtonSolver::set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p) {
    tau_n_ = tau_n; tau_p_ = tau_p;
}

void NewtonSolver::set_optical_generation(const std::vector<real_t>& G_opt) {
    G_opt_ = G_opt;
}

void NewtonSolver::set_thermal_voltage(real_t VT) {
    VT_ = VT;
}

void NewtonSolver::set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv) {
    Nc_ = Nc;
    Nv_ = Nv;
}

void NewtonSolver::set_bandgap(const std::vector<real_t>& Eg) {
    Eg_ = Eg;
}

void NewtonSolver::set_phi_dirichlet(const std::map<size_t, real_t>& bc) {
    phi_bc_ = bc;
}

void NewtonSolver::set_electron_bc(const std::map<size_t, real_t>& bc) {
    n_bc_ = bc;
}

void NewtonSolver::set_hole_bc(const std::map<size_t, real_t>& bc) {
    p_bc_ = bc;
}

void NewtonSolver::set_ferroelectric_polarization(const std::vector<char>& fe_mask,
                                                  const std::vector<real_t>& fe_polarization) {
    // fe_polarization is [Px,Py,Pz] interleaved per node (length 3*npts);
    // fe_mask is length npts.  Empty mask disables the FE feedback.
    fe_mask_ = fe_mask;
    fe_polarization_ = fe_polarization;
}

void NewtonSolver::set_trap_charge(const std::vector<char>& trap_mask,
                                   real_t D_it, real_t E_t,
                                   const std::vector<real_t>& Q_ot) {
    trap_mask_ = trap_mask;
    trap_D_it_ = D_it;
    trap_E_t_ = E_t;
    Q_ot_ = Q_ot;
}

real_t NewtonSolver::compute_btbt_at(const real_t* phi, size_t idx) const {
    if (!opt_.enable_btbt) return 0.0Q;
    // Skip insulator/metal
    if (mu_n_[idx] < EPSILON) return 0.0Q;

    size_t i = idx % g_.nx;
    size_t j = (idx / g_.nx) % g_.ny;
    size_t k = idx / (g_.nx * g_.ny);

    real_t Ex = 0.0Q, Ey = 0.0Q, Ez = 0.0Q;
    if (i > 0 && i + 1 < g_.nx) {
        Ex = -(phi[g_.index(i+1, j, k)] - phi[g_.index(i-1, j, k)]) / (2.0Q * g_.dx);
    } else if (i + 1 < g_.nx) {
        Ex = -(phi[g_.index(i+1, j, k)] - phi[idx]) / g_.dx;
    } else if (i > 0) {
        Ex = -(phi[idx] - phi[g_.index(i-1, j, k)]) / g_.dx;
    }
    if (j > 0 && j + 1 < g_.ny) {
        Ey = -(phi[g_.index(i, j+1, k)] - phi[g_.index(i, j-1, k)]) / (2.0Q * g_.dy);
    } else if (j + 1 < g_.ny) {
        Ey = -(phi[g_.index(i, j+1, k)] - phi[idx]) / g_.dy;
    } else if (j > 0) {
        Ey = -(phi[idx] - phi[g_.index(i, j-1, k)]) / g_.dy;
    }
    if (k > 0 && k + 1 < g_.nz) {
        Ez = -(phi[g_.index(i, j, k+1)] - phi[g_.index(i, j, k-1)]) / (2.0Q * g_.dz);
    } else if (k + 1 < g_.nz) {
        Ez = -(phi[g_.index(i, j, k+1)] - phi[idx]) / g_.dz;
    } else if (k > 0) {
        Ez = -(phi[idx] - phi[g_.index(i, j, k-1)]) / g_.dz;
    }

    real_t E_mag = 0.0Q;
    if (opt_.btbt_field_mode == 1) {
        E_mag = abs_q(Ex);
    } else if (opt_.btbt_field_mode == 2) {
        E_mag = abs_q(Ey);
    } else if (opt_.btbt_field_mode == 3) {
        E_mag = abs_q(Ez);
    } else {
        E_mag = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
    }
    if (opt_.btbt_field_cap > 0.0Q && E_mag > opt_.btbt_field_cap) {
        E_mag = opt_.btbt_field_cap;
    }
    if (E_mag < 1.0e4Q) return 0.0Q;
    if (opt_.btbt_field_alpha != 0.0Q && opt_.btbt_field_ref > 0.0Q) {
        E_mag *= pow_q(E_mag / opt_.btbt_field_ref, opt_.btbt_field_alpha);
    }

    real_t A = opt_.btbt_A * 1.0e6Q;  // cm^-3 -> m^-3
    real_t B = opt_.btbt_B;
    real_t D = opt_.btbt_D;
    real_t E_D = pow_q(E_mag, D);
    return A * E_D * exp_q(-B / E_mag);
}

real_t NewtonSolver::compute_ii_at(const real_t* phi, const real_t* n,
                                   const real_t* p, size_t idx) const {
    // Per-node impact-ionization generation [m^-3 s^-1] via the EDGE form
    // (same convention as GummelSolver::compute_impact_ionization and
    // DeviceSimulator::compute_edge_currents).  For each of the up-to-6 edges
    // meeting at idx we add alpha(|E_edge|)*|J_edge|/q (full edge, not halved —
    // the per-node variant sums whole edges rather than splitting, matching how
    // SRH/BTBT are returned as per-node rates here).
    if (!opt_.enable_ii) return 0.0Q;
    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) return 0.0Q;

    size_t i = idx % g_.nx;
    size_t j = (idx / g_.nx) % g_.ny;
    size_t k = idx / (g_.nx * g_.ny);
    const real_t VT = VT_;

    auto alpha_of = [&](real_t E_mag, real_t A, real_t B) -> real_t {
        if (E_mag < opt_.ii_E_floor) return 0.0Q;
        return A * exp_q(-B / E_mag);
    };

    real_t G = 0.0Q;

    // process one +neighbor edge: idx -> nbr (spacing d).
    auto edge = [&](size_t nbr, real_t d) {
        if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) return;
        real_t dphi = phi[nbr] - phi[idx];
        real_t delta = dphi / VT;
        real_t Bm = bernoulli(-delta);
        real_t Bp = bernoulli(delta);
        real_t E_edge = abs_q(dphi / d);
        real_t an = alpha_of(E_edge, opt_.ii_A_n, opt_.ii_B_n);
        real_t ap = alpha_of(E_edge, opt_.ii_A_p, opt_.ii_B_p);
        if (an == 0.0Q && ap == 0.0Q) return;
        real_t mu_ne = 2.0Q * mu_n_[idx] * mu_n_[nbr] /
            (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
        real_t mu_pe = 2.0Q * mu_p_[idx] * mu_p_[nbr] /
            (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
        real_t Dn = mu_ne * VT / d;
        real_t Dp = mu_pe * VT / d;
        real_t Jn = QE * Dn * (n[idx] * Bm - n[nbr] * Bp);
        real_t Jp = QE * Dp * (p[idx] * Bp - p[nbr] * Bm);
        G += 0.5Q * (an * abs_q(Jn) + ap * abs_q(Jp)) / QE;
    };

    if (i + 1 < g_.nx) edge(idx + 1, g_.dx_edge(i));
    if (i > 0)         edge(idx - 1, g_.dx_edge(i-1 > 0 ? i-1 : 0));
    if (j + 1 < g_.ny) edge(idx + g_.nx, g_.dy_edge(j));
    if (j > 0)         edge(idx - g_.nx, g_.dy_edge(j-1 > 0 ? j-1 : 0));
    if (k + 1 < g_.nz) edge(idx + g_.nx * g_.ny, g_.dz_edge(k));
    if (k > 0)         edge(idx - g_.nx * g_.ny, g_.dz_edge(k-1 > 0 ? k-1 : 0));
    return G;
}

void NewtonSolver::add_ii_jacobian_row(
    SparseMatrix& J, size_t row, const real_t* phi, const real_t* n,
    const real_t* p, size_t idx, real_t source_scale) const {
    if (!opt_.enable_ii) return;
    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) return;

    const size_t i = idx % g_.nx;
    const size_t j = (idx / g_.nx) % g_.ny;
    const size_t k = idx / (g_.nx * g_.ny);

    auto edge = [&](size_t nbr, real_t d) {
        if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) return;
        const real_t dphi = phi[nbr] - phi[idx];
        const real_t E = abs_q(dphi / d);
        if (E < opt_.ii_E_floor) return;

        const real_t delta = dphi / VT_;
        const real_t Bm = bernoulli(-delta);
        const real_t Bp = bernoulli(delta);
        const real_t dBm_ddphi = -d_bernoulli_dx(-delta) / VT_;
        const real_t dBp_ddphi = d_bernoulli_dx(delta) / VT_;

        const real_t an = opt_.ii_A_n * exp_q(-opt_.ii_B_n / E);
        const real_t ap = opt_.ii_A_p * exp_q(-opt_.ii_B_p / E);
        const real_t sign_dphi = (dphi > 0.0Q) ? 1.0Q
                                  : (dphi < 0.0Q) ? -1.0Q : 0.0Q;
        const real_t dE_ddphi = sign_dphi / d;
        const real_t dan_ddphi = an * opt_.ii_B_n / (E * E) * dE_ddphi;
        const real_t dap_ddphi = ap * opt_.ii_B_p / (E * E) * dE_ddphi;

        const real_t mu_ne = 2.0Q * mu_n_[idx] * mu_n_[nbr] /
            (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
        const real_t mu_pe = 2.0Q * mu_p_[idx] * mu_p_[nbr] /
            (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
        const real_t Dn = mu_ne * VT_ / d;
        const real_t Dp = mu_pe * VT_ / d;
        const real_t Jn = QE * Dn * (n[idx] * Bm - n[nbr] * Bp);
        const real_t Jp = QE * Dp * (p[idx] * Bp - p[nbr] * Bm);
        const real_t sign_Jn = (Jn > 0.0Q) ? 1.0Q
                               : (Jn < 0.0Q) ? -1.0Q : 0.0Q;
        const real_t sign_Jp = (Jp > 0.0Q) ? 1.0Q
                               : (Jp < 0.0Q) ? -1.0Q : 0.0Q;

        const real_t dJn_ddphi = QE * Dn *
            (n[idx] * dBm_ddphi - n[nbr] * dBp_ddphi);
        const real_t dJp_ddphi = QE * Dp *
            (p[idx] * dBp_ddphi - p[nbr] * dBm_ddphi);
        const real_t half = 0.5Q;
        const real_t dG_ddphi = half *
            (dan_ddphi * abs_q(Jn) + an * sign_Jn * dJn_ddphi
             + dap_ddphi * abs_q(Jp) + ap * sign_Jp * dJp_ddphi) / QE;

        const real_t dG_dni = half * an * sign_Jn * Dn * Bm;
        const real_t dG_dnj = -half * an * sign_Jn * Dn * Bp;
        const real_t dG_dpi = half * ap * sign_Jp * Dp * Bp;
        const real_t dG_dpj = -half * ap * sign_Jp * Dp * Bm;

        // F_carrier contains -(G_ii-R)*source_scale.  Apply the log-space
        // chain rule here when carrier unknowns are u=log(n), v=log(p).
        const real_t ni_scale = opt_.use_log_space ? n[idx] : 1.0Q;
        const real_t nj_scale = opt_.use_log_space ? n[nbr] : 1.0Q;
        const real_t pi_scale = opt_.use_log_space ? p[idx] : 1.0Q;
        const real_t pj_scale = opt_.use_log_space ? p[nbr] : 1.0Q;
        J.add_entry(row, phi_idx(idx), source_scale * dG_ddphi);
        J.add_entry(row, phi_idx(nbr), -source_scale * dG_ddphi);
        J.add_entry(row, n_idx(idx), -source_scale * dG_dni * ni_scale);
        J.add_entry(row, n_idx(nbr), -source_scale * dG_dnj * nj_scale);
        J.add_entry(row, p_idx(idx), -source_scale * dG_dpi * pi_scale);
        J.add_entry(row, p_idx(nbr), -source_scale * dG_dpj * pj_scale);
    };

    if (i + 1 < g_.nx) edge(idx + 1, g_.dx_edge(i));
    if (i > 0) edge(idx - 1, g_.dx_edge(i - 1));
    if (j + 1 < g_.ny) edge(idx + g_.nx, g_.dy_edge(j));
    if (j > 0) edge(idx - g_.nx, g_.dy_edge(j - 1));
    if (k + 1 < g_.nz) edge(idx + g_.nx * g_.ny, g_.dz_edge(k));
    if (k > 0) edge(idx - g_.nx * g_.ny, g_.dz_edge(k - 1));
}

// Bernoulli function: B(x) = x / (exp(x) - 1)
real_t NewtonSolver::bernoulli(real_t x) {
    if (abs_q(x) < 1e-12Q) return 1.0Q - x / 2.0Q;
    if (x > 100.0Q) return 0.0Q;
    if (x < -100.0Q) return -x;
    return x / expm1_q(x);
}

// Derivative of Bernoulli: B'(x) = (exp(x) - 1 - x*exp(x)) / (exp(x) - 1)^2
real_t NewtonSolver::d_bernoulli_dx(real_t x) {
    if (abs_q(x) < 1e-12Q) return -0.5Q + x / 6.0Q;
    if (x > 100.0Q) return 0.0Q;
    if (x < -100.0Q) return -1.0Q;
    real_t ex = exp_q(x);
    real_t em1 = ex - 1.0Q;
    return (em1 - x * ex) / (em1 * em1);
}

void NewtonSolver::compute_srh_and_derivs(size_t idx, real_t n, real_t p, real_t ni,
                                          real_t& R, real_t& dR_dn, real_t& dR_dp) const {
    real_t np = n * p;
    real_t ni2 = ni * ni;
    real_t tau_n = (idx < tau_n_.size()) ? tau_n_[idx] : 1e100Q;
    real_t tau_p = (idx < tau_p_.size()) ? tau_p_[idx] : 1e100Q;
    real_t denom = tau_p * (n + ni) + tau_n * (p + ni);
    R = 0.0Q; dR_dn = 0.0Q; dR_dp = 0.0Q;
    if (denom > EPSILON) {
        real_t num = np - ni2;
        R = num / denom;
        dR_dn = (p * denom - num * tau_p) / (denom * denom);
        dR_dp = (n * denom - num * tau_n) / (denom * denom);
    }
    if (opt_.enable_auger) {
        const real_t excess = np - ni2;
        const real_t prefactor = opt_.auger_Cn * n + opt_.auger_Cp * p;
        R += prefactor * excess;
        dR_dn += opt_.auger_Cn * excess + prefactor * p;
        dR_dp += opt_.auger_Cp * excess + prefactor * n;
    }
}


void NewtonSolver::refresh_lagged_quantum_potential(
    const std::vector<real_t>& x) {
    const size_t N = g_.npts();
    const std::vector<real_t> old_Qn = lagged_Qn_;
    const std::vector<real_t> old_Qp = lagged_Qp_;
    if (!opt_.enable_quantum || semi_mask_.empty()) {
        lagged_Qn_.clear();
        lagged_Qp_.clear();
        return;
    }

    std::vector<real_t> n(N), p(N);
    for (size_t i = 0; i < N; ++i) {
        if (opt_.use_log_space) {
            n[i] = exp_q(x[n_idx(i)]);
            p[i] = exp_q(x[p_idx(i)]);
        } else {
            n[i] = x[n_idx(i)];
            p[i] = x[p_idx(i)];
        }
    }
    DensityGradient dg_tmp(g_);
    dg_tmp.set_coefficients(dg_bn_, dg_bp_);
    dg_tmp.set_silicon_multivalley(
        dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
        dg_silicon_subbands_);
    dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
    dg_tmp.set_step_boundary(
        dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
        dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
        dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
        dg_step_h_theta_);
    dg_tmp.set_semiconductor_mask(semi_mask_);
    dg_tmp.set_thermal_voltage(VT_);
    std::vector<real_t> next_Qn, next_Qp;
    dg_tmp.quantum_potential(n, p, next_Qn, next_Qp);
    if (old_Qn.size() == N && old_Qp.size() == N) {
        // Outer DG Picard damping.  A fully converged fixed-Q carrier state
        // can imply a large undamped Q jump; applying that jump in one shot
        // re-excites the same limit cycle Newton was asked to rescue.  Match
        // the stable production Gummel quantum damping and let repeated
        // residual-gated refreshes approach Q(n,p) transactionally.
        constexpr real_t quantum_damping = 0.2Q;
        lagged_Qn_.resize(N);
        lagged_Qp_.resize(N);
        for (size_t i = 0; i < N; ++i) {
            lagged_Qn_[i] = old_Qn[i] +
                quantum_damping * (next_Qn[i] - old_Qn[i]);
            lagged_Qp_[i] = old_Qp[i] +
                quantum_damping * (next_Qp[i] - old_Qp[i]);
        }
    } else {
        lagged_Qn_ = std::move(next_Qn);
        lagged_Qp_ = std::move(next_Qp);
    }
}

void NewtonSolver::assemble_residual(const std::vector<real_t>& x, std::vector<real_t>& F) {
    const size_t N = g_.npts();
    F.assign(3 * N, 0.0Q);

    // Extract phi, n, p from x.  In log-space mode the carrier blocks hold
    // u=log(n), v=log(p); we materialise the linear densities into temporaries
    // so every residual formula (SG flux, Poisson, SRH, BE) is evaluated on
    // true n, p — identical physics to the linear-space path.  See audit §18.
    const real_t* phi = x.data();
    std::vector<real_t> n_lin, p_lin;
    const real_t* n;
    const real_t* p;
    if (opt_.use_log_space) {
        n_lin.resize(N);
        p_lin.resize(N);
        const real_t* u = x.data() + N;
        const real_t* v = x.data() + 2 * N;
        for (size_t i = 0; i < N; ++i) {
            n_lin[i] = exp_q(u[i]);
            p_lin[i] = exp_q(v[i]);
        }
        n = n_lin.data();
        p = p_lin.data();
    } else {
        n = x.data() + N;
        p = x.data() + 2 * N;
    }

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], opt_.temperature, Nc_[i], Nv_[i], opt_.statistics_type);
    }

    // --- DG quantum potential (lagged: computed from current n,p) ---
    // Qn modifies the Poisson charge (n → n*exp(Qn/VT)) and the continuity
    // SG potential (φ → φ+Qn).  The Jacobian treats Qn as constant (lagged),
    // which adds a few Newton iterations but avoids the 5-equation block.
    std::vector<real_t> Qn_dg, Qp_dg;
    std::vector<real_t> n_dg(N), p_dg(N);  // DG-corrected densities for Poisson
    if (opt_.enable_quantum && !semi_mask_.empty() &&
        use_lagged_quantum_potential_ && lagged_Qn_.size() == N &&
        lagged_Qp_.size() == N) {
        Qn_dg = lagged_Qn_;
        Qp_dg = lagged_Qp_;
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
    } else if (opt_.enable_quantum && !semi_mask_.empty()) {
        DensityGradient dg_tmp(g_);
        dg_tmp.set_coefficients(dg_bn_, dg_bp_);
        dg_tmp.set_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
        dg_tmp.set_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        dg_tmp.set_semiconductor_mask(semi_mask_);
        dg_tmp.set_thermal_voltage(VT_);
        dg_tmp.quantum_potential(
            std::vector<real_t>(n, n + N),
            std::vector<real_t>(p, p + N),
            Qn_dg, Qp_dg);
        // n and p are the physical quantum-corrected carrier densities.  Q is
        // already included in the SG transport potential below; multiplying
        // the Poisson charge by exp(Q/VT) again double-counted confinement.
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
    } else {
        n_dg.assign(n, n + N);
        p_dg.assign(p, p + N);
        Qn_dg.assign(N, 0.0Q);
        Qp_dg.assign(N, 0.0Q);
    }

    // --- Poisson residual ---  Uses DG-corrected charge n_dg, p_dg
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (phi_bc_.count(idx)) {
                    F[phi_idx(idx)] = phi[idx] - phi_bc_.at(idx);
                    continue;
                }
                if (opt_.freeze_phi) {
                    // Frozen-phi mode: pin phi to its current value so the
                    // Newton solve reduces to a 2-block (n,p) system.  See
                    // NewtonOptions::freeze_phi / audit §17.
                    F[phi_idx(idx)] = 0.0Q;
                    continue;
                }
                // Finite difference Laplacian with position-dependent epsilon
                real_t center = 0.0Q, sum = 0.0Q;
                auto add_link = [&](size_t nbr, real_t edge_cell,
                                    const std::vector<real_t>& edge_values) {
                    real_t eps_avg = edge_epsilon(idx, nbr, edge_values);
                    real_t c = eps_avg / edge_cell;
                    center += c;
                    sum += c * phi[nbr];
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i) * g_.dx_cell(i), edge_eps_x_plus_);
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1) * g_.dx_cell(i), edge_eps_x_minus_);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j) * g_.dy_cell(j), edge_eps_y_plus_);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1) * g_.dy_cell(j), edge_eps_y_minus_);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k) * g_.dz_cell(k), edge_eps_z_plus_);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz_edge(k-1) * g_.dz_cell(k), edge_eps_z_minus_);
                real_t rhs_poisson = sum - center * phi[idx] +
                    QE * charge_volume_fraction_[idx] *
                    (p_dg[idx] - n_dg[idx] + Nd_minus_Na_[idx]);
                // Ferroelectric bound charge: -div(P), mirroring
                // PoissonSolver::assemble (poisson_solver.cpp:187-199).  This
                // was previously MISSING from the Newton path, so any solve
                // routed through Newton (use_newton=True / solve_transient)
                // silently dropped ferroelectric coupling — the root cause of
                // sporadic HZO non-switching and missing memory window.
                // (FE-coupling fix, audit §21.)
                if (!fe_mask_.empty() && idx < fe_mask_.size() && fe_mask_[idx] &&
                    fe_polarization_.size() == 3 * g_.npts()) {
                    auto Pxc = [&](size_t id){ return fe_polarization_[3*id + 0]; };
                    auto Pyc = [&](size_t id){ return fe_polarization_[3*id + 1]; };
                    auto Pzc = [&](size_t id){ return fe_polarization_[3*id + 2]; };
                    real_t divP = 0.0Q;
                    // BUG FIX (comments2.docx): central-difference divergence
                    // (was a second-difference Laplacian due to a sign error).
                    if (i + 1 < g_.nx && i > 0)
                        divP += (Pxc(idx + 1) - Pxc(idx - 1)) / (2.0Q * g_.dx);
                    else if (i + 1 < g_.nx)
                        divP += (Pxc(idx + 1) - Pxc(idx)) / g_.dx;
                    else if (i > 0)
                        divP += (Pxc(idx) - Pxc(idx - 1)) / g_.dx;
                    if (j + 1 < g_.ny && j > 0)
                        divP += (Pyc(idx + g_.nx) - Pyc(idx - g_.nx)) / (2.0Q * g_.dy);
                    else if (j + 1 < g_.ny)
                        divP += (Pyc(idx + g_.nx) - Pyc(idx)) / g_.dy;
                    else if (j > 0)
                        divP += (Pyc(idx) - Pyc(idx - g_.nx)) / g_.dy;
                    if (k + 1 < g_.nz && k > 0)
                        divP += (Pzc(idx + g_.nx * g_.ny) - Pzc(idx - g_.nx * g_.ny)) / (2.0Q * g_.dz);
                    else if (k + 1 < g_.nz)
                        divP += (Pzc(idx + g_.nx * g_.ny) - Pzc(idx)) / g_.dz;
                    else if (k > 0)
                        divP += (Pzc(idx) - Pzc(idx - g_.nx * g_.ny)) / g_.dz;
                    rhs_poisson -= divP;
                }
                // Interface/bulk trap charge (P6), mirroring PoissonSolver.
                // Q_it = -q * D_it * dE * (f_t - 0.5), Q_ot = persistent [C/m^3].
                if (!trap_mask_.empty() && idx < trap_mask_.size() && trap_mask_[idx]) {
                    real_t E_F_shift = phi[idx] / VT_;
                    real_t f_t = 1.0Q / (1.0Q + exp_q(trap_E_t_ - E_F_shift));
                    real_t D_it_m2 = trap_D_it_ * 1.0e4Q;
                    real_t Q_it = -QE * D_it_m2 * 1.0Q * (f_t - 0.5Q) / g_.dx;
                    rhs_poisson -= Q_it;   // subtract because F = A*phi - rhs
                }
                if (!Q_ot_.empty() && idx < Q_ot_.size()) {
                    rhs_poisson -= Q_ot_[idx];
                }
                F[phi_idx(idx)] = rhs_poisson;
            }
        }
    }

    // --- Electron continuity residual ---
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (n_bc_.count(idx)) {
                    // Ohmic contact: n follows phi via Boltzmann relation
                    // n = ni*exp((phi-EFn)/VT).  This replaces the Dirichlet
                    // n=NSD BC with a self-consistent coupling.
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        real_t EFn = ohmic_EFn_.count(idx) ? ohmic_EFn_.at(idx) : 0.0Q;
                        real_t ni_local = ohmic_ni_;
                        real_t arg = (phi[idx] - EFn) / VT_;
                        if (arg > 50.0Q) arg = 50.0Q;
                        if (arg < -50.0Q) arg = -50.0Q;
                        real_t n_target = ni_local * exp_q(arg);
                        if (opt_.use_log_space) {
                            F[n_idx(idx)] = x[n_idx(idx)] - log_q(n_target);
                        } else {
                            F[n_idx(idx)] = n[idx] - n_target;
                        }
                    } else if (opt_.use_log_space) {
                        F[n_idx(idx)] = x[n_idx(idx)] - log_q(n_bc_.at(idx));
                    } else {
                        F[n_idx(idx)] = n[idx] - n_bc_.at(idx);
                    }
                    continue;
                }
                if (!inactive_n_.empty() && inactive_n_[idx]) {
                    F[n_idx(idx)] = 0.0Q;
                    continue;
                }
                if (opt_.freeze_n) {
                    // Frozen-n mode: pin n to its current value.  See
                    // NewtonOptions::freeze_n / audit §17.
                    F[n_idx(idx)] = 0.0Q;
                    continue;
                }
                if (mu_n_[idx] < EPSILON) {
                    // Insulator: pin carriers to the same global numerical
                    // floor used by Gummel and by the linear-space positivity
                    // clamp.  The former hard-coded 1e-30 target disagreed
                    // with EPSILON=1e-20 by ten decades, so every oxide node
                    // entered log-Newton with an artificial residual ln(1e10)
                    // and dominated the line-search merit.
                    if (opt_.use_log_space) {
                        F[n_idx(idx)] = x[n_idx(idx)] - log_q(EPSILON);
                    } else {
                        F[n_idx(idx)] = n[idx] - EPSILON;
                    }
                    continue;
                }
                real_t center = 0.0Q, flux_sum = 0.0Q;
                const real_t w_y = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 1, mu_n_);
                const real_t w_z = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 2, mu_n_);
                auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                    if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = (phi[nbr] + Qn_dg[nbr]) - (phi[idx] + Qn_dg[idx]);
                    real_t B_minus = bernoulli(-dphi / VT_);
                    real_t B_plus = bernoulli(dphi / VT_);
                    // Edge mobility: HARMONIC mean (current conservation fix,
                    // see gummel_solver.cpp electron block comment).
                    real_t mu_e = 2.0Q * mu_n_[idx] * mu_n_[nbr] / (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
                    // Face-area weighting (see gummel_solver.cpp comment).
                    real_t D = w * mu_e * VT_ / dx;
                    real_t a_ii = D * B_minus;
                    real_t a_ij = -D * B_plus;
                    center += a_ii;
                    flux_sum += a_ij * n[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), 1.0Q);
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), 1.0Q);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                real_t R = 0.0Q, dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.enable_btbt) {
                    G += opt_.btbt_continuity_scale * compute_btbt_at(phi, idx);
                }
                if (opt_.enable_ii)   G += compute_ii_at(phi, n, p, idx);
                real_t source_scale = g_.dx_cell(i);
                F[n_idx(idx)] = center * n[idx] + flux_sum - (G - R) * source_scale;
                // Backward-Euler transient term: +(n - n_prev)/dt * dx.
                //
                // The whole carrier residual is in CELL-INTEGRATED units [m^-2 s^-1]:
                // the SG flux  center*n  (center = mu*VT/dx [m/s]) is m^-2 s^-1, and
                // the source (G-R)*dx is m^-2 s^-1.  The BE rate (n-n_prev)/dt is
                // [m^-3 s^-1], so it MUST be multiplied by the same source_scale=dx
                // to be dimensionally consistent.  (The Gummel path at
                // gummel_solver.cpp:336 has this dx scaling; audit §14's claim that
                // "source_scale=dx makes BE too weak" was backwards — without dx the
                // BE term is ~1e8x too strong and over-pins n=n_prev.)  With the
                // correct scaling the BE diagonal dx/dt ~ 1e3 sits below the SRH
                // source R*dx ~ 1e9, giving the expected slow multi-step relaxation.
                if (opt_.transient_enabled && idx < opt_.n_prev.size()) {
                    F[n_idx(idx)] += (n[idx] - opt_.n_prev[idx]) / opt_.transient_dt * source_scale;
                }
            }
        }
    }

    // --- Hole continuity residual ---
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (p_bc_.count(idx)) {
                    // Ohmic: p follows phi via Boltzmann p = ni*exp(-(phi+EFp)/VT)
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        real_t EFp = ohmic_EFp_.count(idx) ? ohmic_EFp_.at(idx) : 0.0Q;
                        real_t arg = -(phi[idx] + EFp) / VT_;
                        if (arg > 50.0Q) arg = 50.0Q;
                        if (arg < -50.0Q) arg = -50.0Q;
                        real_t p_target = ohmic_ni_ * exp_q(arg);
                        if (opt_.use_log_space) {
                            F[p_idx(idx)] = x[p_idx(idx)] - log_q(p_target);
                        } else {
                            F[p_idx(idx)] = p[idx] - p_target;
                        }
                    } else if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] - log_q(p_bc_.at(idx));
                    } else {
                        F[p_idx(idx)] = p[idx] - p_bc_.at(idx);
                    }
                    continue;
                }
                if (!inactive_p_.empty() && inactive_p_[idx]) {
                    F[p_idx(idx)] = 0.0Q;
                    continue;
                }
                if (opt_.freeze_p) {
                    F[p_idx(idx)] = 0.0Q;
                    continue;
                }
                if (mu_p_[idx] < EPSILON) {
                    if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] - log_q(EPSILON);
                    } else {
                        F[p_idx(idx)] = p[idx] - EPSILON;
                    }
                    continue;
                }
                real_t center = 0.0Q, flux_sum = 0.0Q;
                const real_t w_y = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 1, mu_p_);
                const real_t w_z = g_.dx_cell(i) /
                    active_carrier_width(idx, j, k, 2, mu_p_);
                auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                    if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = (phi[nbr] - Qp_dg[nbr]) - (phi[idx] - Qp_dg[idx]);
                    real_t B_plus = bernoulli(dphi / VT_);
                    real_t B_minus = bernoulli(-dphi / VT_);
                    // Edge mobility: HARMONIC mean (current conservation fix).
                    real_t mu_e = 2.0Q * mu_p_[idx] * mu_p_[nbr] / (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
                    real_t D = w * mu_e * VT_ / dx;
                    real_t a_ii = D * B_plus;
                    real_t a_ij = -D * B_minus;
                    center += a_ii;
                    flux_sum += a_ij * p[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), 1.0Q);
                if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), 1.0Q);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                real_t R = 0.0Q, dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.enable_btbt) {
                    G += opt_.btbt_continuity_scale * compute_btbt_at(phi, idx);
                }
                if (opt_.enable_ii)   G += compute_ii_at(phi, n, p, idx);
                real_t source_scale = g_.dx_cell(i);
                F[p_idx(idx)] = center * p[idx] + flux_sum - (G - R) * source_scale;
                // Backward-Euler transient term (see electron block above):
                // scaled by source_scale=dx for dimensional consistency.
                if (opt_.transient_enabled && idx < opt_.p_prev.size()) {
                    F[p_idx(idx)] += (p[idx] - opt_.p_prev[idx]) / opt_.transient_dt * source_scale;
                }
            }
        }
    }
}


void NewtonSolver::assemble_jacobian(const std::vector<real_t>& x, SparseMatrix& J) {
    const size_t N = g_.npts();
    J = SparseMatrix(3 * N);

    const real_t* phi = x.data();
    // Linearise carrier blocks for log-space (see assemble_residual).  The
    // chain rule turns every dF/dn into dF/du = dF/dn * n (and dF/dp into
    // dF/dv = dF/dp * p).  See audit §18.
    std::vector<real_t> n_lin, p_lin;
    const real_t* n;
    const real_t* p;
    if (opt_.use_log_space) {
        n_lin.resize(N);
        p_lin.resize(N);
        const real_t* u = x.data() + N;
        const real_t* v = x.data() + 2 * N;
        for (size_t i = 0; i < N; ++i) {
            n_lin[i] = exp_q(u[i]);
            p_lin[i] = exp_q(v[i]);
        }
        n = n_lin.data();
        p = p_lin.data();
    } else {
        n = x.data() + N;
        p = x.data() + 2 * N;
    }

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], opt_.temperature, Nc_[i], Nv_[i], opt_.statistics_type);
    }

    // Evaluate the lagged DG transport potential at the same state as the
    // residual.  dQ/dn is intentionally omitted (Picard/Newton hybrid), but
    // Bernoulli coefficients must use phi+/-Q for a consistent descent step.
    std::vector<real_t> Qn_dg(N, 0.0Q), Qp_dg(N, 0.0Q);
    if (opt_.enable_quantum && !semi_mask_.empty() &&
        use_lagged_quantum_potential_ && lagged_Qn_.size() == N &&
        lagged_Qp_.size() == N) {
        Qn_dg = lagged_Qn_;
        Qp_dg = lagged_Qp_;
    } else if (opt_.enable_quantum && !semi_mask_.empty()) {
        DensityGradient dg_tmp(g_);
        dg_tmp.set_coefficients(dg_bn_, dg_bp_);
        dg_tmp.set_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        dg_tmp.set_interface_distance_factor(dg_interface_distance_factor_);
        dg_tmp.set_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        dg_tmp.set_semiconductor_mask(semi_mask_);
        dg_tmp.set_thermal_voltage(VT_);
        dg_tmp.quantum_potential(std::vector<real_t>(n, n + N),
                                 std::vector<real_t>(p, p + N),
                                 Qn_dg, Qp_dg);
    }

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                size_t i_phi = phi_idx(idx);
                size_t i_n = n_idx(idx);
                size_t i_p = p_idx(idx);

                // Dirichlet BC rows: identity
                if (phi_bc_.count(idx)) {
                    J.add_entry(i_phi, i_phi, 1.0Q);
                } else if (opt_.freeze_phi) {
                    // Frozen-phi: identity row, no phi<>carrier coupling.
                    J.add_entry(i_phi, i_phi, 1.0Q);
                } else {
                    // Poisson row
                    real_t center = 0.0Q;
                    auto add_link = [&](size_t nbr, real_t edge_cell,
                                        const std::vector<real_t>& edge_values) {
                        real_t eps_avg = edge_epsilon(idx, nbr, edge_values);
                        real_t c = eps_avg / edge_cell;
                        center += c;
                        J.add_entry(i_phi, phi_idx(nbr), c);
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i) * g_.dx_cell(i), edge_eps_x_plus_);
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1) * g_.dx_cell(i), edge_eps_x_minus_);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j) * g_.dy_cell(j), edge_eps_y_plus_);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1) * g_.dy_cell(j), edge_eps_y_minus_);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k) * g_.dz_cell(k), edge_eps_z_plus_);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz_edge(k-1) * g_.dz_cell(k), edge_eps_z_minus_);
                    J.add_entry(i_phi, i_phi, -center);
                    // Poisson<>carrier coupling.  Chain rule in log-space:
                    // dF/du = dF/dn * n, dF/dv = dF/dp * p.  See audit §18.
                    if (opt_.use_log_space) {
                        J.add_entry(i_phi, i_n,
                                    -QE * charge_volume_fraction_[idx] * n[idx]);
                        J.add_entry(i_phi, i_p,
                                     QE * charge_volume_fraction_[idx] * p[idx]);
                    } else {
                        J.add_entry(i_phi, i_n,
                                    -QE * charge_volume_fraction_[idx]);
                        J.add_entry(i_phi, i_p,
                                     QE * charge_volume_fraction_[idx]);
                    }
                }

                if (n_bc_.count(idx)) {
                    J.add_entry(i_n, i_n, 1.0Q);
                    // Ohmic: n follows phi, dF[n]/d[phi] = -1/VT
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        J.add_entry(i_n, i_phi, -1.0Q / VT_);
                    }
                } else if (!inactive_n_.empty() && inactive_n_[idx]) {
                    J.add_entry(i_n, i_n, 1.0Q);
                } else if (opt_.freeze_n) {
                    J.add_entry(i_n, i_n, 1.0Q);
                } else if (mu_n_[idx] < EPSILON) {
                    J.add_entry(i_n, i_n, 1.0Q);
                } else {
                    // Electron continuity row.
                    // Log-space chain rule (audit §18): dF/du = dF/dn * n,
                    // dF/dv = dF/dp * p.  Phi derivatives are unchanged (phi is
                    // not log-transformed).  sn/sp are the self-node scales.
                    real_t sn = opt_.use_log_space ? n[idx] : 1.0Q;
                    real_t sp = opt_.use_log_space ? p[idx] : 1.0Q;
                    real_t center = 0.0Q;
                    real_t dF_dphi_i = 0.0Q;
                    const real_t w_y = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 1, mu_n_);
                    const real_t w_z = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 2, mu_n_);
                    auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                        if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = (phi[nbr] + Qn_dg[nbr]) -
                                         (phi[idx] + Qn_dg[idx]);
                        real_t x_val = dphi / VT_;
                        real_t B_minus = bernoulli(-x_val);
                        real_t B_plus = bernoulli(x_val);
                        // Edge mobility: HARMONIC mean (matches residual).
                        real_t mu_e = 2.0Q * mu_n_[idx] * mu_n_[nbr] / (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
                        real_t D = w * mu_e * VT_ / dx;
                        real_t a_ii = D * B_minus;
                        real_t a_ij = -D * B_plus;
                        center += a_ii;
                        // Neighbor carrier column: scale by n[nbr] in log-space.
                        real_t nbr_scale = opt_.use_log_space ? n[nbr] : 1.0Q;
                        J.add_entry(i_n, n_idx(nbr), a_ij * nbr_scale);
                        // phi derivatives (unchanged — phi not transformed)
                        real_t dBm = d_bernoulli_dx(-x_val);
                        real_t dBp = d_bernoulli_dx(x_val);
                        real_t dflux_dphi_i = D / VT_ * (n[idx] * dBm + n[nbr] * dBp);
                        real_t dflux_dphi_j = -D / VT_ * (n[idx] * dBm + n[nbr] * dBp);
                        dF_dphi_i += dflux_dphi_i;
                        J.add_entry(i_n, phi_idx(nbr), dflux_dphi_j);
                        return a_ii;
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), 1.0Q);
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), 1.0Q);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                    // Self carrier column scaled by sn; phi column unscaled.
                    J.add_entry(i_n, i_n, center * sn);
                    J.add_entry(i_n, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx_cell(i);
                    J.add_entry(i_n, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_n, i_p, dRdp * source_scale * sp);
                    add_ii_jacobian_row(
                        J, i_n, phi, n, p, idx, source_scale);
                    // BE transient: d[(n-n_prev)/dt*dx]/dn = +dx/dt; in log-space
                    // d/du = +dx/dt * n.  See audit §18.
                    if (opt_.transient_enabled) {
                        J.add_entry(i_n, i_n, source_scale / opt_.transient_dt * sn);
                    }
                }

                if (p_bc_.count(idx)) {
                    J.add_entry(i_p, i_p, 1.0Q);
                    // Ohmic: p follows phi, dF[p]/d[phi] = +1/VT
                    if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                        J.add_entry(i_p, i_phi, 1.0Q / VT_);
                    }
                } else if (!inactive_p_.empty() && inactive_p_[idx]) {
                    J.add_entry(i_p, i_p, 1.0Q);
                } else if (opt_.freeze_p) {
                    J.add_entry(i_p, i_p, 1.0Q);
                } else if (mu_p_[idx] < EPSILON) {
                    J.add_entry(i_p, i_p, 1.0Q);
                } else {
                    // Hole continuity row.  Log-space chain rule (audit §18):
                    // dF/du = dF/dn * n, dF/dv = dF/dp * p.  sn/sp self scales.
                    real_t sn = opt_.use_log_space ? n[idx] : 1.0Q;
                    real_t sp = opt_.use_log_space ? p[idx] : 1.0Q;
                    real_t center = 0.0Q;
                    real_t dF_dphi_i = 0.0Q;
                    const real_t w_y = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 1, mu_p_);
                    const real_t w_z = g_.dx_cell(i) /
                        active_carrier_width(idx, j, k, 2, mu_p_);
                    auto add_link = [&](size_t nbr, real_t dx, real_t w) {
                        if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = (phi[nbr] - Qp_dg[nbr]) -
                                         (phi[idx] - Qp_dg[idx]);
                        real_t x_val = dphi / VT_;
                        real_t B_plus = bernoulli(x_val);
                        real_t B_minus = bernoulli(-x_val);
                        // Edge mobility: HARMONIC mean (matches residual).
                        real_t mu_e = 2.0Q * mu_p_[idx] * mu_p_[nbr] / (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
                        real_t D = w * mu_e * VT_ / dx;
                        real_t a_ii = D * B_plus;
                        real_t a_ij = -D * B_minus;
                        center += a_ii;
                        real_t nbr_scale = opt_.use_log_space ? p[nbr] : 1.0Q;
                        J.add_entry(i_p, p_idx(nbr), a_ij * nbr_scale);
                        // phi derivatives (unchanged — phi not transformed)
                        real_t dBp = d_bernoulli_dx(x_val);
                        real_t dBm = d_bernoulli_dx(-x_val);
                        real_t dflux_dphi_i = -D / VT_ * (p[idx] * dBp + p[nbr] * dBm);
                        real_t dflux_dphi_j = D / VT_ * (p[idx] * dBp + p[nbr] * dBm);
                        dF_dphi_i += dflux_dphi_i;
                        J.add_entry(i_p, phi_idx(nbr), dflux_dphi_j);
                        return a_ii;
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx_edge(i), 1.0Q);
                    if (i > 0)        add_link(idx - 1, g_.dx_edge(i-1), 1.0Q);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy_edge(j), w_y);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy_edge(j-1), w_y);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz_edge(k), w_z);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, (k > 0 ? g_.dz_edge(k-1) : g_.dz), w_z);
                    J.add_entry(i_p, i_p, center * sp);
                    J.add_entry(i_p, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx_cell(i);
                    J.add_entry(i_p, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_p, i_p, dRdp * source_scale * sp);
                    add_ii_jacobian_row(
                        J, i_p, phi, n, p, idx, source_scale);
                    // BE transient: d[(p-p_prev)/dt*dx]/dp = +dx/dt; in log-space
                    // d/dv = +dx/dt * p.  See audit §18.
                    if (opt_.transient_enabled) {
                        J.add_entry(i_p, i_p, source_scale / opt_.transient_dt * sp);
                    }
                }
            }
        }
    }
    J.finalize();
}


bool NewtonSolver::solve(std::vector<real_t>& phi,
                         std::vector<real_t>& n,
                         std::vector<real_t>& p) {
    const size_t N = g_.npts();
    auto finite_values = [](const std::vector<real_t>& values) {
        return std::all_of(values.begin(), values.end(), [](real_t value) {
            return std::isfinite((double)value);
        });
    };
    if (!finite_values(phi) || !finite_values(n) || !finite_values(p)) {
        std::cerr << "Newton rejected non-finite initial state\n";
        return false;
    }
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            // Convert linear densities to log-space state u=log(n), v=log(p).
            // Guard against non-positive inputs (Gummel floor of 1e-30 etc.)
            // by clamping before the log.  See audit §18.
            real_t ni = (n[i] > 1e-300Q) ? n[i] : 1e-300Q;
            real_t pi = (p[i] > 1e-300Q) ? p[i] : 1e-300Q;
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }

    inactive_n_.clear();
    inactive_p_.clear();
    if (opt_.enable_quantum && opt_.use_log_space &&
        semi_mask_.size() == N) {
        real_t mobile_scale = 1.0Q;
        for (size_t i = 0; i < N; ++i) {
            if (!semi_mask_[i]) continue;
            mobile_scale = std::max(mobile_scale, abs_q(n[i]));
            mobile_scale = std::max(mobile_scale, abs_q(p[i]));
        }
        // Equivalent to a carrier ErrRef: below one part in 1e10 of the
        // dominant mobile charge, a log-density correction has no resolvable
        // effect on Poisson or terminal current but can make the Jacobian
        // singular.  Preserve the accepted Gummel value at those nodes.
        const real_t carrier_error_reference = 1.0e-10Q * mobile_scale;
        inactive_n_.assign(N, 0);
        inactive_p_.assign(N, 0);
        size_t inactive_n_count = 0;
        size_t inactive_p_count = 0;
        for (size_t i = 0; i < N; ++i) {
            if (!semi_mask_[i]) continue;
            if (!opt_.freeze_n && !n_bc_.count(i) &&
                n[i] < carrier_error_reference) {
                inactive_n_[i] = 1;
                ++inactive_n_count;
            }
            if (!opt_.freeze_p && !p_bc_.count(i) &&
                p[i] < carrier_error_reference) {
                inactive_p_[i] = 1;
                ++inactive_p_count;
            }
        }
        if (opt_.verbose) {
            std::cout << "Newton quantum active set: ErrRef="
                      << (double)carrier_error_reference
                      << " inactive_n=" << inactive_n_count
                      << " inactive_p=" << inactive_p_count << std::endl;
        }
    }

    std::vector<real_t> F(3 * N);
    std::vector<real_t> dx(3 * N);
    SparseMatrix J(3 * N);
    LinearSolver lin_solver({opt_.linear_solver, 10000, opt_.linear_tol, 30, false});

    residuals_.clear();

    // Row-equilibration scale factors (reciprocal Jacobian diagonal per row),
    // saved so the line-search can evaluate trial residuals on the SAME scaled
    // system as the linear solve.  Without this the raw ||F|| is dominated by
    // whichever node has the largest-magnitude residual, and a Newton step that
    // trades a large residual for a small one elsewhere is wrongly rejected
    // (stall).  On the equilibrated norm every row is O(1) so the step is
    // judged on its true merit.  See audit §17.
    std::vector<real_t> eq_scale;
    std::vector<real_t> col_scale;

    real_t norm_F0 = -1.0Q;  // initial residual norm (set on iter 0)
    real_t blk0[3] = {-1.0Q, -1.0Q, -1.0Q};  // per-block initial residuals
    size_t stall_count = 0;    // consecutive line-search stalls (alpha=0)

    // Write the Newton state x back to the output (phi, n, p).  In log-space
    // the carrier blocks hold u=log(n), v=log(p) and must be exponentiated on
    // exit.  See audit §18.
    auto write_back = [&]() -> bool {
        std::vector<real_t> phi_out(N), n_out(N), p_out(N);
        for (size_t i = 0; i < N; ++i) {
            phi_out[i] = x[phi_idx(i)];
            if (opt_.use_log_space) {
                n_out[i] = exp_q(x[n_idx(i)]);
                p_out[i] = exp_q(x[p_idx(i)]);
            } else {
                n_out[i] = x[n_idx(i)];
                p_out[i] = x[p_idx(i)];
            }
        }
        if (!finite_values(phi_out) || !finite_values(n_out) ||
            !finite_values(p_out)) {
            std::cerr << "Newton refused to write back non-finite state\n";
            return false;
        }
        phi = std::move(phi_out);
        n = std::move(n_out);
        p = std::move(p_out);
        return true;
    };

    // Independent physical convergence guard for steady one-dimensional
    // transport.  The electron and hole generation terms cancel in
    // div(Jn+Jp), so total conventional current must be constant at every
    // section.  A small row-equilibrated Newton correction alone is not
    // sufficient: contact rows can be strongly scaled and previously allowed
    // a KCL-broken state to return as converged.
    auto steady_1d_kcl_ok = [&]() -> bool {
        if (g_.ny != 1 || g_.nz != 1 || g_.nx < 3 ||
            opt_.transient_enabled || opt_.freeze_n || opt_.freeze_p) {
            return true;
        }
        auto density = [&](size_t block, size_t node) -> real_t {
            real_t value = x[block * N + node];
            return opt_.use_log_space ? exp_q(value) : value;
        };
        real_t jmin = 0.0Q, jmax = 0.0Q, jabs = 0.0Q;
        bool first = true;
        for (size_t i = 0; i + 1 < g_.nx; ++i) {
            size_t left = g_.index(i, 0, 0);
            size_t right = g_.index(i + 1, 0, 0);
            real_t d = g_.dx_edge(i);
            real_t dphi = x[phi_idx(right)] - x[phi_idx(left)];
            real_t delta = dphi / VT_;
            real_t Bm = bernoulli(-delta);
            real_t Bp = bernoulli(delta);
            real_t mu_ne = 2.0Q * mu_n_[left] * mu_n_[right] /
                (mu_n_[left] + mu_n_[right] + 1e-30Q);
            real_t mu_pe = 2.0Q * mu_p_[left] * mu_p_[right] /
                (mu_p_[left] + mu_p_[right] + 1e-30Q);
            real_t Dn = mu_ne * VT_ / d;
            real_t Dp = mu_pe * VT_ / d;
            real_t nl = density(1, left);
            real_t nr = density(1, right);
            real_t pl = density(2, left);
            real_t pr = density(2, right);
            real_t Jn = QE * Dn * (nr * Bp - nl * Bm);
            real_t Jp = QE * Dp * (pl * Bp - pr * Bm);
            real_t Jtotal = Jn + Jp;
            if (first) {
                jmin = jmax = Jtotal;
                first = false;
            } else {
                jmin = std::min(jmin, Jtotal);
                jmax = std::max(jmax, Jtotal);
            }
            jabs = std::max(jabs, abs_q(Jtotal));
        }
        // Relative KCL is ill-conditioned around equilibrium, while a power
        // threshold can hide a large non-conservative leakage current in a
        // weak field.  Use a mixed absolute/relative test: round-off-scale
        // equilibrium current passes absolutely; a conducting state must be
        // spatially constant to 1%.  Continuing Newton beyond its scaled-row
        // tolerance is essential for drift/diffusion cancellation at abrupt
        // high-doping junctions.
        const real_t absolute_spread = jmax - jmin;
        const real_t relative_spread = absolute_spread / (jabs + 1e-30Q);
        return absolute_spread <= 1.0e-8Q || relative_spread <= 1.0e-2Q;
    };

    use_lagged_quantum_potential_ = false;
    lagged_Qn_.clear();
    lagged_Qp_.clear();
    size_t quantum_steps_since_refresh = 0;
    bool quantum_refresh_pending = opt_.enable_quantum;
    real_t quantum_carrier_trust = 5.0Q;
    for (size_t iter = 0; iter < opt_.max_iter; ++iter) {
        // Q is a Picard variable in this three-block Newton formulation: the
        // Jacobian contains derivatives with respect to phi/n/p but not dQ/dn.
        // Freeze Q for the base residual, Jacobian and every backtracking
        // trial so J*dx is a descent direction for the function actually used
        // by the line search.  Keep it fixed across an inner Newton batch,
        // then refresh and re-apply the physical convergence gate.
        use_lagged_quantum_potential_ = false;
        if (!opt_.enable_quantum || quantum_refresh_pending ||
            lagged_Qn_.size() != N || lagged_Qp_.size() != N) {
            refresh_lagged_quantum_potential(x);
            quantum_steps_since_refresh = 0;
            quantum_refresh_pending = false;
        }
        use_lagged_quantum_potential_ =
            opt_.enable_quantum && lagged_Qn_.size() == N &&
            lagged_Qp_.size() == N;
        assemble_residual(x, F);

        if (!finite_values(F)) {
            std::cerr << "Newton residual contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        assemble_jacobian(x, J);

        if (!finite_values(J.vals())) {
            std::cerr << "Newton Jacobian contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        // Per-BLOCK residual norms and per-block solution scales are computed
        // on the RAW residual below (convergence criteria keep original units).
        std::vector<real_t> F_raw(F);

        // Two-sided equilibration: row scaling (1/max_entry per row) then
        // column scaling (1/max_entry per column).  Row-only scaling leaves
        // columns unbalanced — the phi column has entries from 1 (phi row)
        // to 1e-33 (n row), making the Newton step direction biased.
        // Two-sided scaling makes the matrix entries O(1) in both dimensions,
        // dramatically improving the condition number and Newton step quality.
        {
            const auto& rp = J.row_offsets();
            const auto& cols = J.col_indices();
            auto& vals = J.vals_mut();
            // Phase 1: row scaling
            eq_scale.assign(3 * N, 1.0Q);
            for (size_t i = 0; i < 3 * N; ++i) {
                real_t mx = 0.0Q;
                const size_t row_block = i / N;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    const size_t column_block = cols[k] / N;
                    // A frozen block has an identity equation and therefore
                    // a zero Newton update.  Its cross derivatives remain in
                    // J (the linear system is unchanged), but they must not
                    // define the residual scale of an active row.  In the BE
                    // minority-carrier problem, dF_p/dphi can be ~1e11 times
                    // larger than the active dF_p/dp even though dphi is
                    // constrained to zero; including it caused norm_F<tol at
                    // iteration zero and froze the transient after ~20 steps.
                    const bool frozen_cross =
                        row_block != column_block &&
                        ((column_block == 0 && opt_.freeze_phi) ||
                         (column_block == 1 && opt_.freeze_n) ||
                         (column_block == 2 && opt_.freeze_p));
                    if (!frozen_cross)
                        mx = std::max(mx, abs_q(vals[k]));
                }
                real_t inv = (mx > EPSILON) ? 1.0Q / mx : 1.0Q;
                eq_scale[i] = inv;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k)
                    vals[k] *= inv;
                F[i] *= inv;
            }
            // Phase 2: column scaling
            col_scale.assign(3 * N, 1.0Q);
            for (size_t j = 0; j < 3 * N; ++j) col_scale[j] = 0.0Q;
            for (size_t i = 0; i < 3 * N; ++i) {
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    size_t j = cols[k];
                    col_scale[j] = std::max(col_scale[j], abs_q(vals[k]));
                }
            }
            for (size_t j = 0; j < 3 * N; ++j) {
                col_scale[j] = (col_scale[j] > EPSILON) ? 1.0Q / col_scale[j] : 1.0Q;
            }
            for (size_t i = 0; i < 3 * N; ++i) {
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    vals[k] *= col_scale[cols[k]];
                }
            }
        }

        if (!finite_values(F) || !finite_values(J.vals()) ||
            !finite_values(eq_scale) || !finite_values(col_scale)) {
            std::cerr << "Newton equilibration produced NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }

        // Merit function: equilibrated L-inf for ALL problems (2026-08): the
        // worst scaled row, so a step is judged on every row's merit instead
        // of being dominated by the largest-magnitude rows.
        real_t norm_F = 0.0Q;
        real_t merit_F_sq = 0.0Q;
        for (size_t i = 0; i < 3 * N; ++i) {
            norm_F = std::max(norm_F, abs_q(F[i]));
            merit_F_sq += F[i] * F[i];
        }
        const real_t merit_F = sqrt_q(merit_F_sq / (3.0Q * N));
        if (norm_F0 < 0.0Q) norm_F0 = (norm_F > EPSILON) ? norm_F : 1.0Q;
        // Per-BLOCK residual norms and per-block solution scales (issues0719
        // P0-3).  A single GLOBAL convergence test lets the largest-scale
        // block mask an unconverged block: the legacy |F|/(|x|+1) test used
        // |x|~n~1e25, so Newton "converged" while the re-assembled Poisson
        // residual was 0.158.  Convergence now requires EVERY block (phi, n,
        // p) to satisfy a criterion measured against ITS OWN scale.
        real_t blk[3] = {0.0Q, 0.0Q, 0.0Q};
        // Computed on the RAW residual (F_raw) so the convergence criteria
        // keep their original units regardless of row equilibration.
        {
            for (size_t i = 0; i < 3 * N; ++i) {
                size_t b = (i < N) ? 0 : ((i < 2 * N) ? 1 : 2);
                blk[b] += F_raw[i] * F_raw[i];
            }
            for (int b = 0; b < 3; ++b) blk[b] = sqrt_q(blk[b]);
        }
        if (blk0[0] < 0.0Q) {
            for (int b = 0; b < 3; ++b)
                blk0[b] = (blk[b] > EPSILON) ? blk[b] : norm_F0;
        }
        real_t rel_res = 0.0Q;
        for (int b = 0; b < 3; ++b)
            rel_res = std::max(rel_res, blk[b] / blk0[b]);
        residuals_.push_back((double)rel_res);

        if (opt_.verbose) {
            size_t worst_row = 0;
            real_t worst_scaled = 0.0Q;
            for (size_t i = 0; i < 3 * N; ++i) {
                real_t scaled = abs_q(F[i]);
                if (scaled > worst_scaled) {
                    worst_scaled = scaled;
                    worst_row = i;
                }
            }
            const char* worst_block = (worst_row < N) ? "phi"
                                      : (worst_row < 2 * N) ? "n" : "p";
            size_t worst_node = worst_row % N;
            real_t row_max = (eq_scale[worst_row] > EPSILON)
                ? 1.0Q / eq_scale[worst_row] : 0.0Q;
            std::cout << "Newton iter " << iter
                      << "  |F|=" << (double)norm_F
                      << "  |F|/|F0|=" << (double)rel_res
                      << "  worst=" << worst_block << "[" << worst_node << "]"
                      << " raw=" << (double)F_raw[worst_row]
                      << " rowmax=" << (double)row_max
                      << "  blk=(" << (double)blk[0] << ","
                      << (double)blk[1] << "," << (double)blk[2] << ")"
                      << std::endl;
        }

        // Convergence test (issues0719 P0-3): EVERY block must satisfy one
        // of the true-residual criteria measured against ITS OWN scale:
        //   conv_abs  : ||F_b|| < abs_tol;
        //   conv_rel  : ||F_b|| < tol * ||F_b,0|| (improvement from start);
        //   conv_step : ||F_b|| < tol * (max|x_b| + 1) (residual small
        //               relative to the block's own solution scale).
        // The legacy GLOBAL |F|/(|x|+1) test was killed by the n~1e25
        // carrier scale: it passed with an O(0.1) relative Poisson residual
        // — "iteration stopped changing" masquerading as "equations
        // satisfied".  Per block, the phi rows are tested against the
        // voltage scale and the carrier rows against the carrier scale, so
        // no block can hide behind another.
        bool all_abs = true;
        for (int b = 0; b < 3; ++b) {
            if (!(blk[b] < opt_.abs_tol)) all_abs = false;
        }
        // The carrier residual is cell-integrated flux [m^-2 s^-1], whereas
        // xsc is density [m^-3]; comparing blk to tol*xsc is dimensionally
        // invalid and accepted KCL-broken reverse-junction states.  The
        // row-equilibrated infinity norm is a Newton-correction estimate in
        // each row's natural unknown units and supplies the scale-independent
        // convergence test.  Relative reduction alone is also insufficient:
        // a huge initial residual can improve by 1e-6 and remain nonphysical.
        const bool equilibrated_ok = norm_F < opt_.tol;
        if ((all_abs || equilibrated_ok) && steady_1d_kcl_ok()) {
            // A fixed-Q inner Newton solution is not yet a self-consistent DG
            // solution if x has moved since Q was assembled.  Refresh Q and
            // require the same physical residual gate once more.  Only a
            // state that passes immediately after that refresh may return.
            if (use_lagged_quantum_potential_ &&
                quantum_steps_since_refresh > 0) {
                quantum_refresh_pending = true;
                continue;
            }
            if (opt_.verbose) std::cout << "Newton converged in " << iter << " iterations.\n";
            return write_back();
        }

        // Solve J * dx = -F  (F already scaled above when transient)
        Vector rhs(3 * N);
        for (size_t i = 0; i < 3 * N; ++i) rhs[i] = -F[i];
        dx.assign(3 * N, 0.0Q);
        try {
            lin_solver.solve(J, rhs, dx);
        } catch (const std::exception& e) {
            std::cerr << "Newton linear solve failed: " << e.what() << std::endl;
            return false;
        }
        // A Krylov iteration limit is not a usable Newton direction.  Some
        // portable linear backends historically returned their best guess
        // without signalling failure, which allowed enormous null-space-like
        // log-density updates to reach the trust limiter and shrink every
        // physical update to zero.  Audit the actual equilibrated system
        // before undoing column scaling.  This also guards external solvers
        // against a successful status paired with an inaccurate solution.
        {
            real_t relative_linear_error = 0.0Q;
            size_t refinement_steps = 0;
            const real_t linear_acceptance =
                opt_.enable_quantum ? 1.0e-3Q : 1.0e-6Q;
            for (; refinement_steps <= 3; ++refinement_steps) {
                const Vector Jdx = J.apply(dx);
                Vector correction_rhs(3 * N);
                real_t linear_error = 0.0Q;
                real_t rhs_scale = 0.0Q;
                for (size_t i = 0; i < 3 * N; ++i) {
                    const real_t defect = Jdx[i] + F[i];
                    correction_rhs[i] = -defect;
                    linear_error = std::max(linear_error, abs_q(defect));
                    rhs_scale = std::max(rhs_scale, abs_q(F[i]));
                }
                relative_linear_error =
                    linear_error / std::max(rhs_scale, EPSILON);
                if (!std::isfinite((double)relative_linear_error) ||
                    relative_linear_error <= linear_acceptance ||
                    refinement_steps == 3) {
                    break;
                }
                // Reuse the same sparse factorisation on the quad-computed
                // defect.  This is mixed-precision iterative refinement: the
                // external solve remains fast double precision, while the
                // backward-error measurement and correction RHS retain the
                // assembled real_t precision.
                Vector correction(3 * N, 0.0Q);
                try {
                    lin_solver.solve(J, correction_rhs, correction);
                } catch (const std::exception& e) {
                    std::cerr << "Newton linear refinement failed: "
                              << e.what() << std::endl;
                    return false;
                }
                for (size_t i = 0; i < 3 * N; ++i)
                    dx[i] += correction[i];
            }
            if (opt_.verbose) {
                std::cout << "    [linear] relative_residual="
                          << (double)relative_linear_error
                          << "  refinements=" << refinement_steps
                          << std::endl;
            }
            // PETSc/SuperLU operates in double precision after the quad
            // assembly has been equilibrated.  Classical Newton retains a
            // 1e-6 backward-error gate.  The active-set/trust-region quantum
            // path permits a standard 1e-3 inexact-Newton forcing term because
            // every trial is still accepted by the full nonlinear residual;
            // silent Krylov failures are many orders larger.
            if (!std::isfinite((double)relative_linear_error) ||
                relative_linear_error > linear_acceptance) {
                std::cerr << "Newton linear solve residual too large: "
                          << (double)relative_linear_error << std::endl;
                return false;
            }
        }
        // Undo column scaling: dx_unscaled[j] = dx_scaled[j] * col_scale[j]
        for (size_t j = 0; j < 3 * N; ++j) dx[j] *= col_scale[j];
        if (!finite_values(dx)) {
            std::cerr << "Newton step contains NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }
        // Bank-Rose style log-space step clamp (issues0719 follow-up,
        // plan0728 §1.1): in log-space an unclamped carrier update du
        // explodes the linearised densities (n = exp(u)).  Far from the
        // solution the Newton direction can have |du| ~ 1e8, so EVERY
        // backtracking fraction down to ~1e-3 still overflows/increases
        // ||F|| and the line search stalls permanently at alpha=0 — even
        // though the direction is a mathematically exact descent direction
        // (verified by FD Jacobian checks).  Clamping the carrier update
        // magnitude keeps exp(du) bounded so the direction becomes usable.
        // Apply the trust bound per component.  A single near-null-space
        // minority-carrier node must not shrink every physical phi/n/p update;
        // the full residual line search below validates this inexact direction.
        if (opt_.use_log_space) {
            real_t du_max = 0.0Q;
            size_t du_node = 0;
            const char* du_block = "n";
            for (size_t i = N; i < 3 * N; ++i) {
                if (abs_q(dx[i]) > du_max) {
                    du_max = abs_q(dx[i]);
                    du_node = i % N;
                    du_block = (i < 2 * N) ? "n" : "p";
                }
            }
            real_t dphi_max = 0.0Q;
            size_t dphi_node = 0;
            for (size_t i = 0; i < N; ++i) {
                if (abs_q(dx[i]) > dphi_max) {
                    dphi_max = abs_q(dx[i]);
                    dphi_node = i;
                }
            }
            const real_t U_MAX = opt_.enable_quantum
                ? quantum_carrier_trust : 5.0Q;
            const real_t PHI_MAX = 1.0Q;   // max electrostatic step [V]
            size_t clipped_phi = 0;
            size_t clipped_carrier = 0;
            real_t global_scale = 1.0Q;
            real_t phi_block_scale = 1.0Q;
            if (opt_.enable_quantum) {
                // Preserve the spatial Poisson direction: scale the complete
                // phi block when its trust bound is exceeded.  Component-wise
                // phi clipping flattened hundreds of nodes to +/-1 V and
                // destroyed an otherwise valid coupled descent direction.
                if (dphi_max > PHI_MAX) {
                    phi_block_scale = PHI_MAX / dphi_max;
                    for (size_t i = 0; i < N; ++i)
                        dx[i] *= phi_block_scale;
                    clipped_phi = N;
                }
                for (size_t i = N; i < 3 * N; ++i) {
                    if (abs_q(dx[i]) > U_MAX) {
                        dx[i] = (dx[i] < 0.0Q) ? -U_MAX : U_MAX;
                        ++clipped_carrier;
                    }
                }
            } else {
                if (du_max > U_MAX)
                    global_scale = std::min(global_scale, U_MAX / du_max);
                if (dphi_max > PHI_MAX)
                    global_scale = std::min(
                        global_scale, PHI_MAX / dphi_max);
                if (global_scale < 1.0Q) {
                    for (size_t i = 0; i < 3 * N; ++i)
                        dx[i] *= global_scale;
                }
            }
            if (opt_.verbose &&
                (clipped_phi || clipped_carrier || global_scale < 1.0Q)) {
                std::cout << "    [trust] clipped_phi=" << clipped_phi
                          << "  clipped_carrier=" << clipped_carrier
                          << "  carrier_limit=" << (double)U_MAX
                          << "  phi_scale=" << (double)phi_block_scale
                          << "  global_scale=" << (double)global_scale
                          << "  max_dphi=" << (double)dphi_max
                          << "@" << dphi_node
                          << "  max_d" << du_block << "=" << (double)du_max
                          << "@" << du_node << std::endl;
            }
        }
        // Helper: apply update (linear or exponential for carriers).
        // In log-space the carrier blocks already hold u=log(n), so a plain
        // additive Newton step u += du is the correct exponential update
        // (positivity is automatic: exp(u+du) > 0).  The use_log_damping path
        // (which divides dx[n]/x[n]) is for linear-space states and must NOT
        // fire here.  See audit §18.
        auto apply_update = [&](real_t a, std::vector<real_t>& x_out) {
            for (size_t i = 0; i < N; ++i) {
                x_out[phi_idx(i)] = x[phi_idx(i)] + a * dx[phi_idx(i)];
                if (opt_.use_log_space) {
                    // Additive in log-space == multiplicative in linear space.
                    x_out[n_idx(i)] = x[n_idx(i)] + a * dx[n_idx(i)];
                    x_out[p_idx(i)] = x[p_idx(i)] + a * dx[p_idx(i)];
                } else if (opt_.use_log_damping) {
                    // Exponential update: guarantees positivity
                    real_t du = a * dx[n_idx(i)] / x[n_idx(i)];
                    real_t dv = a * dx[p_idx(i)] / x[p_idx(i)];
                    x_out[n_idx(i)] = x[n_idx(i)] * exp_q(du);
                    x_out[p_idx(i)] = x[p_idx(i)] * exp_q(dv);
                } else {
                    x_out[n_idx(i)] = x[n_idx(i)] + a * dx[n_idx(i)];
                    x_out[p_idx(i)] = x[p_idx(i)] + a * dx[p_idx(i)];
                }
            }
        };

        // Line search / damping.  Backtracking from alpha=1 (full Newton step),
        // accepting the step with the smallest residual.  If NO step improves on
        // the current residual we still take the best-found (least-bad) step so
        // Newton can keep trying — but we cap it to avoid a catastrophic blow-up.
        real_t alpha = opt_.damping;
        if (opt_.use_line_search) {
            real_t best_alpha = 0.0Q;       // 0 = "take no step" if nothing helps
            real_t best_merit = merit_F;     // must beat the current RMS merit
            for (size_t ls = 0; ls < opt_.line_search_max; ++ls) {
                std::vector<real_t> x_try(3 * N);
                apply_update(alpha, x_try);
                // Safety clamp for non-log mode.  In log-space the carrier
                // blocks hold u=log(n) >= -690 (for n >= 1e-300), so they are
                // always finite and the clamp is neither needed nor correct.
                if (!opt_.use_log_space && !opt_.use_log_damping) {
                    for (size_t i = 0; i < N; ++i) {
                        if (x_try[n_idx(i)] < EPSILON) x_try[n_idx(i)] = EPSILON;
                        if (x_try[p_idx(i)] < EPSILON) x_try[p_idx(i)] = EPSILON;
                    }
                }
                std::vector<real_t> F_try(3 * N);
                assemble_residual(x_try, F_try);
                if (!finite_values(x_try) || !finite_values(F_try)) {
                    alpha *= 0.5Q;
                    if (alpha < opt_.min_damping) break;
                    continue;
                }
                // Apply the SAME row-equilibration as the baseline so the
                // trial norm is comparable to norm_F (2026-08: now always on).
                for (size_t i = 0; i < 3 * N; ++i) F_try[i] *= eq_scale[i];
                // RMS globalization merit plus an L-inf growth guard.
                real_t norm_try = 0.0Q;
                real_t merit_try_sq = 0.0Q;
                for (size_t i = 0; i < 3 * N; ++i) {
                    norm_try = std::max(norm_try, abs_q(F_try[i]));
                    merit_try_sq += F_try[i] * F_try[i];
                }
                const real_t merit_try =
                    sqrt_q(merit_try_sq / (3.0Q * N));
                // Use RMS to make progress when one SG cancellation row sits
                // on an L-inf plateau, but never permit the worst row to grow
                // materially.  Final convergence remains the strict L-inf
                // gate above, so this changes globalization, not accuracy.
                if (merit_try < best_merit &&
                    norm_try <= 1.05Q * norm_F) {
                    best_merit = merit_try;
                    best_alpha = alpha;
                }
                alpha *= 0.5Q;
                if (alpha < opt_.min_damping) break;
            }
            alpha = best_alpha;  // 0 if no step improved => stall, not blow-up
            // Good-enough early exit.  When the line search stalls (alpha=0)
            // but the equilibrated residual is already small (rel_res below a
            // loose floor), the BE step is converged to within the transient
            // accuracy budget and we accept the current state rather than
            // burning max_iter.  The equilibrated L∞ merit function can stall
            // at a few % when the worst-node residual can't drop without
            // growing a neighbour via SG-flux cancellation noise at
            // boundary-adjacent majority-carrier nodes.  The floor (3e-2 = 3%)
            // is well above the typical stall point and far below the ~10%
            // per-step BE accuracy budget for dt~0.01*tau.  See audit §17.
            if (opt_.transient_enabled && alpha == 0.0Q && rel_res < 3e-2Q) {
                if (opt_.verbose) {
                    std::cout << "Newton converged (good-enough) at iter " << iter
                              << "  |F|/|F0|=" << (double)rel_res
                              << " < 3e-2 floor (line-search stall)." << std::endl;
                }
                return write_back();
            }
        }

        // Apply final update (alpha=0 => no change, Newton stalls cleanly)
        apply_update(alpha, x);
        if (!finite_values(x)) {
            std::cerr << "Newton update produced NaN/Inf at iteration "
                      << iter << "\n";
            return false;
        }
        if (use_lagged_quantum_potential_ && alpha > 0.0Q) {
            ++quantum_steps_since_refresh;
            if (alpha >= 0.5Q) {
                quantum_carrier_trust = std::min(
                    5.0Q, 1.25Q * quantum_carrier_trust);
            }
        } else if (use_lagged_quantum_potential_ && alpha == 0.0Q) {
            // Keep Q fixed and contract only the rejected carrier trust
            // region.  Refreshing Q here changes the nonlinear target before
            // the fixed-Q equations have converged and re-enters the DG cycle.
            quantum_carrier_trust = std::max(
                0.1Q, 0.5Q * quantum_carrier_trust);
        }
        if (opt_.verbose) {
            real_t dx_max = 0.0Q;
            for (size_t i = 0; i < 3 * N; ++i) dx_max = std::max(dx_max, abs_q(dx[i]));
            std::cout << "    [ls] alpha=" << (double)alpha
                      << "  |dx|_max=" << (double)dx_max << std::endl;
        }
        // Stall watchdog: with alpha=0 the state cannot change, so further
        // iterations only burn max_iter re-evaluating the same residual.
        // Declare the honest failure early (issues0719 P0-3 follow-up — a
        // stalled Newton previously ground through 1000 iterations per bias
        // point).
        stall_count = (alpha == 0.0Q) ? stall_count + 1 : 0;
        if (stall_count >= 10) {
            std::cerr << "Newton stalled (line search made no progress for "
                      << stall_count << " consecutive iterations); "
                      << "declaring non-convergence\n";
            write_back();
            return false;
        }
    }

    std::cerr << "Newton did not converge within max_iter\n";
    write_back();
    return false;
}

void NewtonSolver::debug_solve_probe(const std::vector<real_t>& phi,
                                     const std::vector<real_t>& n,
                                     const std::vector<real_t>& p) {
    const size_t N = g_.npts();
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            real_t ni = (n[i] > 1e-300Q) ? n[i] : 1e-300Q;
            real_t pi = (p[i] > 1e-300Q) ? p[i] : 1e-300Q;
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }
    std::vector<real_t> F(3 * N), F1(3 * N);
    assemble_residual(x, F);
    SparseMatrix J(3 * N);
    assemble_jacobian(x, J);
    LinearSolver lin_solver({opt_.linear_solver, 10000, opt_.linear_tol, 30, false});
    Vector rhs(3 * N), dxv(3 * N);
    for (size_t i = 0; i < 3 * N; ++i) rhs[i] = -F[i];
    dxv.assign(3 * N, 0.0Q);
    try {
        lin_solver.solve(J, rhs, dxv);
    } catch (const std::exception& e) {
        std::printf("[probe] linear solve FAILED: %s\n", e.what());
        return;
    }
    std::vector<real_t> dx(3 * N);
    for (size_t i = 0; i < 3 * N; ++i) dx[i] = dxv[i];
    // Solve accuracy: ||J dx + F|| / ||F||
    std::vector<real_t> Jdx(3 * N, 0.0Q);
    const auto& rp = J.row_offsets();
    const auto& cols = J.col_indices();
    const auto& vals = J.vals();
    for (size_t i = 0; i < 3 * N; ++i)
        for (size_t k = rp[i]; k < rp[i + 1]; ++k)
            Jdx[i] += vals[k] * dx[cols[k]];
    real_t num = 0.0Q, den = 0.0Q, dxmax = 0.0Q;
    for (size_t i = 0; i < 3 * N; ++i) {
        num += (Jdx[i] + F[i]) * (Jdx[i] + F[i]);
        den += F[i] * F[i];
        dxmax = std::max(dxmax, abs_q(dx[i]));
    }
    std::printf("[probe] |F|=%.6g  |J*dx+F|/|F|=%.6g  |dx|max=%.6g\n",
                (double)sqrt_q(den), (double)sqrt_q(num / (den + 1e-300Q)),
                (double)dxmax);
    // Directional residual along the Newton step.
    const double alphas[] = {1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125,
                             0.015625, 0.0078125, 0.00390625};
    for (double a : alphas) {
        std::vector<real_t> xt(3 * N);
        for (size_t i = 0; i < 3 * N; ++i) xt[i] = x[i] + (real_t)a * dx[i];
        assemble_residual(xt, F1);
        real_t n1 = 0.0Q;
        for (size_t i = 0; i < 3 * N; ++i) n1 += F1[i] * F1[i];
        std::printf("[probe] a=%.6g  |F(x+a*dx)|=%.10g\n", a, (double)sqrt_q(n1));
    }
}

size_t NewtonSolver::debug_fd_jacobian_check(const std::vector<real_t>& phi,
                                             const std::vector<real_t>& n,
                                             const std::vector<real_t>& p,
                                             double rel_tol,
                                             size_t max_report) {
    const size_t N = g_.npts();
    // Build the Newton state x exactly as solve() does.
    std::vector<real_t> x(3 * N);
    for (size_t i = 0; i < N; ++i) {
        x[phi_idx(i)] = phi[i];
        if (opt_.use_log_space) {
            real_t ni = (n[i] > 1e-300Q) ? n[i] : 1e-300Q;
            real_t pi = (p[i] > 1e-300Q) ? p[i] : 1e-300Q;
            x[n_idx(i)] = log_q(ni);
            x[p_idx(i)] = log_q(pi);
        } else {
            x[n_idx(i)] = n[i];
            x[p_idx(i)] = p[i];
        }
    }
    std::vector<real_t> F0(3 * N), F1(3 * N);
    assemble_residual(x, F0);
    SparseMatrix J(3 * N);
    assemble_jacobian(x, J);
    const auto& rp = J.row_offsets();
    const auto& cols = J.col_indices();
    const auto& vals = J.vals();

    struct Bad { double err; size_t row, col; double jan, fdm; };
    std::vector<Bad> bad;
    size_t n_bad = 0, n_checked = 0;

    for (size_t j = 0; j < 3 * N; ++j) {
        // Step: quad-precision arithmetic tolerates a tiny relative step.
        real_t scale = std::max(abs_q(x[j]), real_t(1.0Q));
        real_t h = 1e-10Q * scale;
        std::vector<real_t> xp = x;
        xp[j] += h;
        assemble_residual(xp, F1);
        // Compare every J entry in column j against the FD derivative.
        for (size_t i = 0; i < 3 * N; ++i) {
            real_t fd = (F1[i] - F0[i]) / h;
            // Find J(i,j) in the CSR structure.
            real_t jan = 0.0Q;
            bool present = false;
            for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                if (cols[k] == j) { jan = vals[k]; present = true; break; }
            }
            if (!present && abs_q(fd) < 1e-12Q * (abs_q(F0[i]) + 1.0Q)) continue;
            real_t denom = std::max(abs_q(fd), abs_q(jan));
            if (denom < 1e-12Q * (abs_q(F0[i]) + 1.0Q)) continue;  // both ~0
            real_t err = abs_q(jan - fd) / denom;
            ++n_checked;
            if ((double)err > rel_tol) {
                ++n_bad;
                bad.push_back({(double)err, i, j, (double)jan, (double)fd});
            }
        }
    }
    std::sort(bad.begin(), bad.end(),
              [](const Bad& a, const Bad& b) { return a.err > b.err; });
    auto name_of = [&](size_t v, size_t& node) -> const char* {
        if (v < N) { node = v; return "phi"; }
        if (v < 2 * N) { node = v - N; return "n"; }
        node = v - 2 * N; return "p";
    };
    std::cout << "[fd-jac] state N=" << N
              << " log_space=" << (opt_.use_log_space ? 1 : 0)
              << " checked=" << n_checked << " mismatched=" << n_bad << "\n";
    size_t shown = 0;
    for (const auto& b : bad) {
        if (shown++ >= max_report) break;
        size_t rn, cn;
        const char* rb = name_of(b.row, rn);
        const char* cb = name_of(b.col, cn);
        // Node -> (i,j,k) for geometry context.
        size_t ri = rn % g_.nx, rj = (rn / g_.nx) % g_.ny, rk = rn / (g_.nx * g_.ny);
        size_t ci = cn % g_.nx, cj = (cn / g_.nx) % g_.ny, ck = cn / (g_.nx * g_.ny);
        std::printf("  err=%.3g  F[%s(%zu,%zu,%zu)] d/dx[%s(%zu,%zu,%zu)]"
                    "  J=%.6g  FD=%.6g\n",
                    b.err, rb, ri, rj, rk, cb, ci, cj, ck, b.jan, b.fdm);
    }
    return n_bad;
}

} // namespace tcad
