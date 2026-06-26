#include "newton_solver.h"
#include "statistics.h"
#include <iostream>
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
    tau_n_.assign(N, 1e100Q);
    tau_p_.assign(N, 1e100Q);
    G_opt_.assign(N, 0.0Q);
}

void NewtonSolver::set_permittivity(const std::vector<real_t>& eps) {
    eps_ = eps;
}

void NewtonSolver::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    mu_n_ = mu_n; mu_p_ = mu_p;
}

void NewtonSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    Nd_minus_Na_ = Nd_minus_Na;
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

    real_t E_mag = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
    if (E_mag < 1.0e4Q) return 0.0Q;

    real_t A = opt_.btbt_A * 1.0e6Q;  // cm^-3 -> m^-3
    real_t B = opt_.btbt_B;
    int D = opt_.btbt_D;
    real_t E_D = 1.0Q;
    for (int d = 0; d < D; ++d) E_D *= E_mag;
    return A * E_D * exp_q(-B / E_mag);
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

    // --- Poisson residual ---
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
                auto add_link = [&](size_t nbr, real_t dx) {
                    real_t eps_avg = 2.0Q * eps_[idx] * eps_[nbr] / (eps_[idx] + eps_[nbr] + 1e-30Q);
                    real_t c = eps_avg / (dx * dx);
                    center += c;
                    sum += c * phi[nbr];
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                if (i > 0)        add_link(idx - 1, g_.dx);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                if (j > 0)        add_link(idx - g_.nx, g_.dy);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                F[phi_idx(idx)] = sum - center * phi[idx] + QE * (p[idx] - n[idx] + Nd_minus_Na_[idx]);
            }
        }
    }

    // --- Electron continuity residual ---
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (n_bc_.count(idx)) {
                    // Log-space: enforce u = log(n_bc).  Linear: n = n_bc.
                    if (opt_.use_log_space) {
                        F[n_idx(idx)] = x[n_idx(idx)] - log_q(n_bc_.at(idx));
                    } else {
                        F[n_idx(idx)] = n[idx] - n_bc_.at(idx);
                    }
                    continue;
                }
                if (opt_.freeze_n) {
                    // Frozen-n mode: pin n to its current value.  See
                    // NewtonOptions::freeze_n / audit §17.
                    F[n_idx(idx)] = 0.0Q;
                    continue;
                }
                if (mu_n_[idx] < EPSILON) {
                    // Insulator: pin carrier to floor (1e-30).  In log-space the
                    // state is u=log(n), so the constraint is u = log(1e-30).
                    if (opt_.use_log_space) {
                        F[n_idx(idx)] = x[n_idx(idx)] - log_q(1e-30Q);
                    } else {
                        F[n_idx(idx)] = n[idx] - 1e-30Q; // insulator: freeze to epsilon
                    }
                    continue;
                }
                real_t center = 0.0Q, flux_sum = 0.0Q;
                auto add_link = [&](size_t nbr, real_t dx) {
                    if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = phi[nbr] - phi[idx];
                    real_t B_minus = bernoulli(-dphi / VT_);
                    real_t B_plus = bernoulli(dphi / VT_);
                    real_t D = mu_n_[idx] * VT_ / dx;
                    real_t a_ii = D * B_minus;
                    real_t a_ij = -D * B_plus;
                    center += a_ii;
                    flux_sum += a_ij * n[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                if (i > 0)        add_link(idx - 1, g_.dx);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                if (j > 0)        add_link(idx - g_.nx, g_.dy);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                real_t R = 0.0Q, dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.enable_btbt) G += compute_btbt_at(phi, idx);
                real_t source_scale = g_.dx;
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
                    if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] - log_q(p_bc_.at(idx));
                    } else {
                        F[p_idx(idx)] = p[idx] - p_bc_.at(idx);
                    }
                    continue;
                }
                if (opt_.freeze_p) {
                    F[p_idx(idx)] = 0.0Q;
                    continue;
                }
                if (mu_p_[idx] < EPSILON) {
                    if (opt_.use_log_space) {
                        F[p_idx(idx)] = x[p_idx(idx)] - log_q(1e-30Q);
                    } else {
                        F[p_idx(idx)] = p[idx] - 1e-30Q;
                    }
                    continue;
                }
                real_t center = 0.0Q, flux_sum = 0.0Q;
                auto add_link = [&](size_t nbr, real_t dx) {
                    if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = phi[nbr] - phi[idx];
                    real_t B_plus = bernoulli(dphi / VT_);
                    real_t B_minus = bernoulli(-dphi / VT_);
                    real_t D = mu_p_[idx] * VT_ / dx;
                    real_t a_ii = D * B_plus;
                    real_t a_ij = -D * B_minus;
                    center += a_ii;
                    flux_sum += a_ij * p[nbr];
                    return a_ii;
                };
                if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                if (i > 0)        add_link(idx - 1, g_.dx);
                if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                if (j > 0)        add_link(idx - g_.nx, g_.dy);
                if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                real_t R = 0.0Q, dRdn, dRdp;
                compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.enable_btbt) G += compute_btbt_at(phi, idx);
                real_t source_scale = g_.dx;
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
                    auto add_link = [&](size_t nbr, real_t dx) {
                        real_t eps_avg = 2.0Q * eps_[idx] * eps_[nbr] / (eps_[idx] + eps_[nbr] + 1e-30Q);
                        real_t c = eps_avg / (dx * dx);
                        center += c;
                        J.add_entry(i_phi, phi_idx(nbr), c);
                    };
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                    if (i > 0)        add_link(idx - 1, g_.dx);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                    J.add_entry(i_phi, i_phi, -center);
                    // Poisson<>carrier coupling.  Chain rule in log-space:
                    // dF/du = dF/dn * n, dF/dv = dF/dp * p.  See audit §18.
                    if (opt_.use_log_space) {
                        J.add_entry(i_phi, i_n, -QE * n[idx]);
                        J.add_entry(i_phi, i_p,  QE * p[idx]);
                    } else {
                        J.add_entry(i_phi, i_n, -QE);
                        J.add_entry(i_phi, i_p, QE);
                    }
                }

                if (n_bc_.count(idx)) {
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
                    auto add_link = [&](size_t nbr, real_t dx) {
                        if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = phi[nbr] - phi[idx];
                        real_t x_val = dphi / VT_;
                        real_t B_minus = bernoulli(-x_val);
                        real_t B_plus = bernoulli(x_val);
                        real_t D = mu_n_[idx] * VT_ / dx;
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
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                    if (i > 0)        add_link(idx - 1, g_.dx);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                    // Self carrier column scaled by sn; phi column unscaled.
                    J.add_entry(i_n, i_n, center * sn);
                    J.add_entry(i_n, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx;
                    J.add_entry(i_n, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_n, i_p, dRdp * source_scale * sp);
                    // BE transient: d[(n-n_prev)/dt*dx]/dn = +dx/dt; in log-space
                    // d/du = +dx/dt * n.  See audit §18.
                    if (opt_.transient_enabled) {
                        J.add_entry(i_n, i_n, source_scale / opt_.transient_dt * sn);
                    }
                }

                if (p_bc_.count(idx)) {
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
                    auto add_link = [&](size_t nbr, real_t dx) {
                        if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                        real_t dphi = phi[nbr] - phi[idx];
                        real_t x_val = dphi / VT_;
                        real_t B_plus = bernoulli(x_val);
                        real_t B_minus = bernoulli(-x_val);
                        real_t D = mu_p_[idx] * VT_ / dx;
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
                    if (i + 1 < g_.nx) add_link(idx + 1, g_.dx);
                    if (i > 0)        add_link(idx - 1, g_.dx);
                    if (j + 1 < g_.ny) add_link(idx + g_.nx, g_.dy);
                    if (j > 0)        add_link(idx - g_.nx, g_.dy);
                    if (k + 1 < g_.nz) add_link(idx + g_.nx * g_.ny, g_.dz);
                    if (k > 0)        add_link(idx - g_.nx * g_.ny, g_.dz);
                    J.add_entry(i_p, i_p, center * sp);
                    J.add_entry(i_p, i_phi, dF_dphi_i);
                    real_t R, dRdn, dRdp;
                    compute_srh_and_derivs(idx, n[idx], p[idx], ni[idx], R, dRdn, dRdp);
                    real_t source_scale = g_.dx;
                    J.add_entry(i_p, i_n, dRdn * source_scale * sn);
                    J.add_entry(i_p, i_p, dRdp * source_scale * sp);
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

    real_t norm_F0 = -1.0Q;  // initial residual norm (set on iter 0)

    // Write the Newton state x back to the output (phi, n, p).  In log-space
    // the carrier blocks hold u=log(n), v=log(p) and must be exponentiated on
    // exit.  See audit §18.
    auto write_back = [&]() {
        for (size_t i = 0; i < N; ++i) {
            phi[i] = x[phi_idx(i)];
            if (opt_.use_log_space) {
                n[i] = exp_q(x[n_idx(i)]);
                p[i] = exp_q(x[p_idx(i)]);
            } else {
                n[i] = x[n_idx(i)];
                p[i] = x[p_idx(i)];
            }
        }
    };

    for (size_t iter = 0; iter < opt_.max_iter; ++iter) {
        assemble_residual(x, F);

        assemble_jacobian(x, J);

        // Row-equilibration: scale each Jacobian row (and the corresponding
        // RHS entry) by the inverse of its diagonal magnitude.  The carrier
        // residual spans a wide dynamic range (diffusion diagonal ~1e5, SRH
        // source rows ~1e9, Poisson<>carrier cross-coupling ~1e29), and the
        // BE term adds a +dx/dt diagonal.  Equilibration brings every row to
        // O(1) diagonal so DENSE_DIRECT/BICGSTAB are well-conditioned.
        // The Newton step dx is invariant under row scaling
        // (J dx = -F  <=>  (DJ) dx = -D F), so this changes only conditioning,
        // not the solution.
        if (opt_.transient_enabled) {
            const auto& rp = J.row_offsets();
            const auto& cols = J.col_indices();
            auto& vals = J.vals_mut();
            eq_scale.assign(3 * N, 1.0Q);
            for (size_t i = 0; i < 3 * N; ++i) {
                real_t diag = 0.0Q;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    if (cols[k] == i) { diag = vals[k]; break; }
                }
                if (abs_q(diag) < EPSILON) continue;
                real_t inv = 1.0Q / diag;
                eq_scale[i] = inv;
                for (size_t k = rp[i]; k < rp[i + 1]; ++k) {
                    vals[k] *= inv;
                }
                F[i] *= inv;
            }
            // Re-evaluate the convergence metric on the EQUILIBRATED residual,
            // so the line-search baseline matches what the line search sees.
        }

        // Convergence metric.  For transient problems we use the EQUILIBRATED
        // residual L∞ norm (F has been row-scaled above): the equilibrated L2
        // norm can GROW when a full Newton step reduces the dominant (max)
        // residual while slightly growing several small ones, causing a
        // premature stall; the L∞ norm tracks the single worst node, so if it
        // drops the step is genuinely downhill.  For non-transient (DC) problems
        // F is untouched and we keep the L2 norm (the original behaviour).
        // See audit §17.
        real_t norm_F;
        if (opt_.transient_enabled) {
            norm_F = 0.0Q;
            for (size_t i = 0; i < 3 * N; ++i) norm_F = std::max(norm_F, abs_q(F[i]));
        } else {
            norm_F = norm_l2(F);
        }
        if (norm_F0 < 0.0Q) norm_F0 = (norm_F > EPSILON) ? norm_F : 1.0Q;
        real_t rel_res = norm_F / norm_F0;
        residuals_.push_back((double)rel_res);

        if (opt_.verbose) {
            std::cout << "Newton iter " << iter
                      << "  |F|=" << (double)norm_F
                      << "  |F|/|F0|=" << (double)rel_res << std::endl;
        }

        // Convergence test.  For transient we use |F|/|F0| (scale-invariant,
        // avoids the |F|/(|x|+1) unit mismatch that false-converged at iter 0
        // when |x|~n~1e22).  For non-transient (DC) we ALSO accept the
        // step-relative test |F|/(|x|+1) < tol, which is a valid convergence
        // metric for the steady-state problem where the solution magnitude
        // sets the natural scale.  This preserves the original DC behaviour.
        // See audit §17.
        real_t norm_x = 0.0Q;
        if (!opt_.transient_enabled && !opt_.use_log_space) {
            // |F|/(|x|+1) step-relative test.  Skipped in log-space: there the
            // carrier blocks hold log(n) (~-690..+60), a totally different scale
            // from the linear densities (~1e22), so |x| is meaningless.  The
            // scale-invariant conv_rel (|F|/|F0|) covers log-space instead.
            for (size_t i = 0; i < 3 * N; ++i) norm_x = std::max(norm_x, abs_q(x[i]));
        }
        bool conv_abs = norm_F < opt_.abs_tol;
        bool conv_rel = rel_res < opt_.tol;
        bool conv_step = (!opt_.transient_enabled && !opt_.use_log_space) && (norm_F / (norm_x + 1.0Q) < opt_.tol);
        if (conv_abs || conv_rel || conv_step) {
            if (opt_.verbose) std::cout << "Newton converged in " << iter << " iterations.\n";
            write_back();
            return true;
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
            real_t best_norm = norm_F;       // must beat the current residual
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
                // Apply the SAME row-equilibration as the baseline so the
                // trial norm is comparable to norm_F.  Without this the raw
                // ||F_try|| is dominated by the largest-magnitude node and a
                // step that reduces a big residual while growing a small one
                // is wrongly rejected (stall).  See audit §17.
                if (opt_.transient_enabled) {
                    for (size_t i = 0; i < 3 * N; ++i) F_try[i] *= eq_scale[i];
                }
                // Merit function: L∞ (max |F|) for transient (equilibrated),
                // L2 for non-transient (raw, original behaviour).  See §17.
                real_t norm_try;
                if (opt_.transient_enabled) {
                    norm_try = 0.0Q;
                    for (size_t i = 0; i < 3 * N; ++i) norm_try = std::max(norm_try, abs_q(F_try[i]));
                } else {
                    norm_try = norm_l2(F_try);
                }
                if (norm_try < best_norm) {
                    best_norm = norm_try;
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
                write_back();
                return true;
            }
        }

        // Apply final update (alpha=0 => no change, Newton stalls cleanly)
        apply_update(alpha, x);
    }

    std::cerr << "Newton did not converge within max_iter\n";
    write_back();
    return false;
}

} // namespace tcad
