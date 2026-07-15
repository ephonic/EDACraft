#include "gummel_solver.h"
#include "linear_solver.h"
#include "statistics.h"
#include <iostream>
#include <cmath>

namespace tcad {

GummelSolver::GummelSolver(const Grid3D& grid, const GummelOptions& opt)
    : g_(grid), opt_(opt), poisson_(grid), dg_(grid) {
    const size_t N = g_.npts();
    mu_n_.assign(N, 0.14Q);   // Default Si m^2/(V*s)
    mu_p_.assign(N, 0.045Q);
    tau_n_.assign(N, 1e-7Q);
    tau_p_.assign(N, 1e-7Q);
    Nd_minus_Na_.assign(N, 0.0Q);
    // Configure Poisson solver
    SolverOptions poisson_opt = LinearSolver::default_poisson_options();
    poisson_opt.type = opt_.poisson_solver;
    poisson_.set_solver_options(poisson_opt);
    // Ferroelectric
    if (opt_.ferro.enabled && !opt_.ferro.fe_mask.empty()) {
        poisson_.set_ferroelectric(opt_.ferro.fe_mask, opt_.ferro.alpha, opt_.ferro.beta);
        // Model selection + Preisach params (M7c).
        poisson_.set_ferroelectric_model(static_cast<int>(opt_.ferro.model));
        poisson_.set_ferroelectric_preisach(opt_.ferro.ps, opt_.ferro.ec, opt_.ferro.escale);
        // P2.1: internal/imprint field offset.
        poisson_.set_ferroelectric_builtin_field(opt_.ferro.E_bi);
        // comments2.docx P3: depolarization field.
        poisson_.set_ferroelectric_depol(opt_.ferro.eps_fe);
        // P3: NLS Merz-law parameters.
        poisson_.set_ferroelectric_nls(opt_.ferro.nls_tau0, opt_.ferro.nls_E0,
                                       opt_.ferro.nls_dt);
    }
    // Leakage current (PF/FN) (P2.2)
    if (opt_.leakage.enabled && !opt_.leakage.mask.empty()) {
        poisson_.set_leakage(opt_.leakage.mask,
                             opt_.leakage.C_pf, opt_.leakage.B_pf, opt_.leakage.phi_t,
                             opt_.leakage.C_fn, opt_.leakage.B_fn, opt_.leakage.phi_b,
                             opt_.leakage.E_floor, opt_.leakage.sigma_cap);
    }
}

void GummelSolver::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    mu_n_ = mu_n; mu_p_ = mu_p;
}

void GummelSolver::set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p) {
    tau_n_ = tau_n; tau_p_ = tau_p;
}

void GummelSolver::set_optical_generation(const std::vector<real_t>& G_opt) {
    G_opt_ = G_opt;
}

void GummelSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    Nd_minus_Na_ = Nd_minus_Na;
    poisson_.set_doping(Nd_minus_Na);
}

void GummelSolver::set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv) {
    Nc_ = Nc;
    Nv_ = Nv;
}

void GummelSolver::set_bandgap(const std::vector<real_t>& Eg) {
    Eg_ = Eg;
}

void GummelSolver::set_electron_bc(const std::map<size_t, real_t>& bc) { n_bc_.insert(bc.begin(), bc.end()); }
void GummelSolver::set_hole_bc(const std::map<size_t, real_t>& bc) { p_bc_.insert(bc.begin(), bc.end()); }

void GummelSolver::compute_btbt(const std::vector<real_t>& phi,
                                std::vector<real_t>& G_btbt) const {
    const size_t N = g_.npts();
    G_btbt.assign(N, 0.0Q);
    if (!opt_.btbt.enabled) return;

    // Non-local (path-integral WKB) model
    if (opt_.btbt.use_nonlocal) {
        compute_nonlocal_btbt(phi, G_btbt);
        return;
    }

    // Local Kane's model (original)
    // Scale A_kane from cm^-3 to m^-3: multiply by 1e6
    real_t A = opt_.btbt.A_kane * 1.0e6Q;
    real_t B = opt_.btbt.B_kane;
    int D = opt_.btbt.D;

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                // Skip insulator/metal regions
                if (mu_n_[idx] < EPSILON) continue;

                // Compute |E| from potential gradients (central differences)
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
                if (E_mag < 1.0e4Q) continue;  // negligible field threshold

                // Kane's model: G = A * |E|^D * exp(-B / |E|)
                real_t E_D = 1.0Q;
                for (int d = 0; d < D; ++d) E_D *= E_mag;
                real_t G = A * E_D * exp_q(-B / E_mag);
                G_btbt[idx] = G;
            }
        }
    }
}

void GummelSolver::compute_impact_ionization(const std::vector<real_t>& phi,
                                             const std::vector<real_t>& n,
                                             const std::vector<real_t>& p,
                                             std::vector<real_t>& G_ii) const {
    // Avalanche impact ionization (Chynoweth).  alpha(E) = A*exp(-B/|E|) [1/m].
    // Per-pair generation rate G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q [m^-3 s^-1].
    //
    // We use the EDGE form, which is the physically correct and numerically
    // stable convention used by commercial tools (Sentaurus/DESSIS): for each
    // interior edge (idx -> nbr) the Scharfetter-Gummel current density is
    //   Jn = q*Dn/d * (n[idx]*B(-dphi/VT) - n[nbr]*B(+dphi/VT))   [A/m^2]
    // (identical to DeviceSimulator::compute_edge_currents, audit §20).
    // The ionization integral contribution of that edge is
    //   alpha_n(|E_edge|) * |Jn_edge| / q   [+ alpha_p*|Jp_edge|/q],
    // and it is deposited half to each endpoint with a 1/d weighting so the
    // returned per-node G_ii has units [m^-3 s^-1] matching SRH/BTBT.  |E_edge|
    // is the edge-aligned field component (the gradient along the edge), which
    // is what accelerates carriers across that edge — using the full |grad phi|
    // here would double-count across the three axes.
    const size_t N = g_.npts();
    G_ii.assign(N, 0.0Q);
    if (!opt_.ii.enabled) return;

    const real_t VT = opt_.VT;
    const real_t E_floor = opt_.ii.E_floor;

    // Helper: ionization coefficient alpha for a given |E| and (A,B) pair.
    auto alpha_of = [&](real_t E_mag, real_t A, real_t B) -> real_t {
        if (E_mag < E_floor) return 0.0Q;     // negligible below ~1e5 V/m
        return A * exp_q(-B / E_mag);
    };

    // Process one axis.  stride/spacing/dim pick out x/y/z.  `idx` -> `nbr`.
    auto process_axis = [&](size_t stride, real_t d, size_t n0) {
        for (size_t k = 0; k < g_.nz; ++k) {
            for (size_t j = 0; j < g_.ny; ++j) {
                for (size_t i = 0; i < n0; ++i) {  // i in [0, dim-1): +neighbor exists
                    size_t idx = g_.index(i, j, k);
                    size_t nbr = idx + stride;
                    // Skip edges touching insulator/metal: no carrier flux there.
                    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) continue;
                    if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) continue;

                    real_t dphi = phi[nbr] - phi[idx];
                    real_t delta = dphi / VT;
                    real_t Bm = bernoulli(-delta);
                    real_t Bp = bernoulli(delta);
                    // Edge-aligned electric field magnitude [V/m] along this edge.
                    real_t E_edge = abs_q(dphi / d);

                    real_t alpha_n = alpha_of(E_edge, opt_.ii.A_n, opt_.ii.B_n);
                    real_t alpha_p = alpha_of(E_edge, opt_.ii.A_p, opt_.ii.B_p);
                    if (alpha_n == 0.0Q && alpha_p == 0.0Q) continue;

                    // SG current densities along this edge [A/m^2].
                    real_t Dn = mu_n_[idx] * VT / d;
                    real_t Dp = mu_p_[idx] * VT / d;
                    real_t Jn = QE * Dn * (n[idx] * Bm - n[nbr] * Bp);
                    real_t Jp = QE * Dp * (p[idx] * Bp - p[nbr] * Bm);

                    // alpha*|J|/q [m^-3 s^-1], split half to each endpoint.
                    // (The 1/d already implicit in D = mu*VT/d is the per-edge
                    //  volume weighting; depositing half to each node matches the
                    //  box-integration of the continuity source term.)
                    real_t g_node = (alpha_n * abs_q(Jn) + alpha_p * abs_q(Jp)) / QE * 0.5Q;
                    G_ii[idx] += g_node;
                    G_ii[nbr] += g_node;
                }
            }
        }
    };

    process_axis(1,             g_.dx, g_.nx - 1);                 // +x edges
    process_axis(g_.nx,         g_.dy, g_.ny - 1);                 // +y edges
    process_axis(g_.nx * g_.ny, g_.dz, g_.nz - 1);                 // +z edges
}

void GummelSolver::compute_nonlocal_btbt(const std::vector<real_t>& phi,
                                         std::vector<real_t>& G_btbt) const {
    const size_t N = g_.npts();
    G_btbt.assign(N, 0.0Q);

    // Physical constants for WKB tunneling (SI units)
    const double hbar = 1.054571817e-34;  // reduced Planck constant [J*s]
    const double m0 = 9.1093837015e-31;   // electron rest mass [kg]
    const double qe = 1.602176634e-19;    // elementary charge [C]
    // Si effective tunneling mass ~ 0.25 m0 (averaged over valleys)
    const double mt_eff = 0.25 * m0;
    // Prefactor for BTBT generation
    const double pre_wkb = 1.0e27; // m^-3 s^-1

    const size_t n_wkb = opt_.btbt.wkb_npts;

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);

                // Skip insulator/metal regions
                if (mu_n_[idx] < EPSILON) continue;

                // Tunneling primarily along x (source-channel direction for TFETs).
                //
                // Phase 3.3 fix (audit §12.3): the path length is no longer
                // fixed to a single grid spacing dx.  The old code set
                // path_L = dx, which truncated the WKB integral at one cell
                // whenever the band-crossing distance d_min = Eg/(qE) exceeded
                // dx (i.e. in the off-state / low-field regime).  That
                // under-estimated the true barrier and over-estimated T by
                // many orders of magnitude, making BTBT-Ioff unreliable.
                //
                // The correct path extends until the linearised barrier
                // actually exhausts (2*d_min, where barrier(x)=Eg-qEx drops
                // from Eg to 0 and back to 0 on the far side of the well).
                // We cap at the available grid (distance to the nearer x
                // boundary) so the linear band-edge model — which only sees
                // the local field — is not extrapolated past the device.
                const double dx_m = (double)g_.dx;

                // Local electric field along x
                double Ex_val = 0.0;
                if (i > 0 && i + 1 < g_.nx) {
                    Ex_val = -((double)phi[g_.index(i+1, j, k)] - (double)phi[g_.index(i-1, j, k)])
                           / (2.0 * dx_m);
                } else if (i + 1 < g_.nx) {
                    Ex_val = -((double)phi[g_.index(i+1, j, k)] - (double)phi[idx]) / dx_m;
                } else if (i > 0) {
                    Ex_val = -((double)phi[idx] - (double)phi[g_.index(i-1, j, k)]) / dx_m;
                }

                // Local bandgap from per-node material property
                const double Eg_eV = (idx < Eg_.size()) ? (double)Eg_[idx] : 1.12;

                // WKB integral: integrate sqrt(2*mt*(Ec(x) - Ev(x))) / hbar along path
                // Model band profile: linear drop across tunneling window, offset by local Ec-Ev
                // The tunneling window where Ec < Ev is when q*E*x > Eg
                const double Eg_J = Eg_eV * qe;
                const double E_field = fabs(Ex_val);

                // Band-crossing distance: where the linearised barrier would
                // reach zero.  For negligible field there is no crossing and
                // the barrier is effectively infinite -> no tunnelling.
                const double d_min = (E_field > 1.0) ? (Eg_J / (qe * E_field))
                                                    : 1.0e-6;  // 1 µm sentinel

                // Path length is the full band-crossing window (2*d_min), so
                // the WKB integral covers the *actual* barrier rather than a
                // single-cell slice.  Capped at the distance to the nearer x
                // boundary so we do not extrapolate the local linear field
                // beyond the simulated device.
                const double avail_lo = (double)i * dx_m;            // to x=0 face
                const double avail_hi = (double)(g_.nx - 1 - i) * dx_m; // to x=Lx face
                const double avail = std::min(avail_lo, avail_hi);
                const double path_L = std::min(2.0 * d_min, avail);

                // effective_L == path_L now (no second truncation); kept for
                // clarity of the integration loop below.
                const double effective_L = path_L;

                if (effective_L < 1e-12) {
                    // Path is zero (boundary node with no interior room): no
                    // tunnelling can be represented at this node.
                    G_btbt[idx] = 0.0Q;
                    continue;
                }

                // Simpson's rule integration
                double wkb_integral = 0.0;
                if (n_wkb >= 4) {
                    const double h = effective_L / (double)(n_wkb);
                    for (size_t s = 0; s <= n_wkb; ++s) {
                        const double x = (double)s * h;
                        // Linear band drop: barrier height at position x
                        const double barrier = std::max(Eg_J - qe * E_field * x, 0.0);
                        if (barrier <= 0.0) {
                            // Classically allowed: no contribution
                            continue;
                        }
                        const double integrand = sqrt(2.0 * mt_eff * barrier) / hbar;
                        if (std::isinf(integrand)) {
                            wkb_integral = 1e10; // cap to avoid overflow
                            break;
                        }
                        double weight = (s == 0 || s == n_wkb) ? 1.0 :
                                        (s % 2 == 1 ? 4.0 : 2.0);
                        wkb_integral += weight * integrand;
                    }
                    wkb_integral *= h / 3.0;
                } else {
                    // Fallback: single-step estimate
                    wkb_integral = sqrt(2.0 * mt_eff * Eg_J) / hbar * effective_L;
                }

                // Tunneling probability: T = exp(-2 * WKB integral)
                const double exponent = -2.0 * wkb_integral;
                if (exponent < -700.0) {
                    // T ~ exp(-700) ~ 10^-304: effectively zero
                    G_btbt[idx] = 0.0Q;
                    continue;
                }
                const double T_prob = std::exp(exponent);

                // BTBT generation rate
                const double G_val = pre_wkb * T_prob;
                if (G_val > 1e50) {
                    G_btbt[idx] = (real_t)1e50;
                } else {
                    G_btbt[idx] = (real_t)G_val;
                }
            }
        }
    }
}

real_t GummelSolver::bernoulli(real_t x) {
    if (abs_q(x) < 1e-12Q) return 1.0Q;
    if (x > 100.0Q) return 0.0Q;
    if (x < -100.0Q) return -x;
    return x / expm1_q(x);
}

bool GummelSolver::solve_electron_density(const std::vector<real_t>& phi,
                                          std::vector<real_t>& n,
                                          const std::vector<real_t>& p) {
    // Compute BTBT generation and add to optical generation
    std::vector<real_t> G_btbt;
    if (opt_.btbt.enabled) {
        compute_btbt(phi, G_btbt);
    }
    // Compute avalanche impact-ionization generation
    std::vector<real_t> G_ii;
    if (opt_.ii.enabled) {
        compute_impact_ionization(phi, n, p, G_ii);
    }

    const size_t N = g_.npts();
    SparseMatrix A(N);
    Vector rhs(N, 0.0Q);
    std::vector<char> is_bc(N, 0);
    for (const auto& [idx, val] : n_bc_) { is_bc[idx] = 1; }

    // Scharfetter-Gummel discretization
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_bc[idx]) {
                    A.add_entry(idx, idx, 1.0Q);
                    rhs[idx] = n_bc_.at(idx);
                    continue;
                }
                // Insulator / metal: zero mobility -> freeze carrier density
                if (mu_n_[idx] < EPSILON) {
                    // Use a large diagonal to prevent pivot swapping in dense direct
                    A.add_entry(idx, idx, 1.0e20Q);
                    rhs[idx] = 1.0e20Q * EPSILON;
                    continue;
                }

                real_t center = 0.0Q;

                auto add_link = [&](size_t nbr, real_t dx, real_t mu) {
                    // Skip coupling to insulator/metal neighbors: zero carrier flux
                    if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = phi[nbr] - phi[idx];
                    real_t B_plus = bernoulli(dphi / opt_.VT);
                    real_t B_minus = bernoulli(-dphi / opt_.VT);
                    real_t D = mu * opt_.VT / dx;
                    // Original SG discretization (kept for self-consistency)
                    real_t a_ii = D * B_minus;   // contribution to diagonal (positive)
                    real_t a_ij = -D * B_plus;   // off-diagonal (negative)
                    A.add_entry(idx, nbr, a_ij);
                    return a_ii;
                };

                if (i + 1 < g_.nx) center += add_link(idx + 1, g_.dx, mu_n_[idx]);
                if (i > 0)        center += add_link(idx - 1, g_.dx, mu_n_[idx]);
                if (j + 1 < g_.ny) center += add_link(idx + g_.nx, g_.dy, mu_n_[idx]);
                if (j > 0)        center += add_link(idx - g_.nx, g_.dy, mu_n_[idx]);
                if (k + 1 < g_.nz) center += add_link(idx + g_.nx * g_.ny, g_.dz, mu_n_[idx]);
                if (k > 0)        center += add_link(idx - g_.nx * g_.ny, g_.dz, mu_n_[idx]);

                // Recombination (SRH simplified): R = (n*p - ni^2) / (tau_p*(n+ni) + tau_n*(p+ni))
                // Explicit treatment in Gummel iteration
                real_t ni = intrinsic_density(Eg_[idx], opt_.temperature, Nc_[idx], Nv_[idx], opt_.statistics_type);
                real_t R = 0.0Q;
                if (idx < tau_n_.size() && idx < tau_p_.size() &&
                    tau_n_[idx] > EPSILON && tau_p_[idx] > EPSILON) {
                    real_t np = n[idx] * p[idx];
                    real_t denom = tau_p_[idx] * (n[idx] + ni) + tau_n_[idx] * (p[idx] + ni);
                    if (denom > EPSILON)
                        R = (np - ni * ni) / denom;
                }
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.btbt.enabled && idx < G_btbt.size()) G += G_btbt[idx];
                if (opt_.ii.enabled && idx < G_ii.size()) G += G_ii[idx];
                real_t source_scale = g_.dx;
                A.add_entry(idx, idx, center);
                rhs[idx] = (G - R) * source_scale;
                // Transient term: backward Euler.  The cell-integrated BE
                // continuity eqn is (n - n_prev)/dt*dx = center*n + flux + (G-R)*dx.
                // Moving the n_new terms left and knowns right gives
                //   (center + dx/dt)*n_new + flux = (G-R)*dx + n_prev*dx/dt
                // so the diagonal gets +dx/dt and the rhs gets +n_prev*dx/dt.
                // (The previous code had -dx/dt on the diagonal and used the
                // current iterate n instead of n_prev on the rhs — a sign and
                // consistency bug.  See audit §17.)
                if (opt_.transient_enabled && idx < opt_.n_prev.size()) {
                    A.add_entry(idx, idx, source_scale / opt_.transient_dt);
                    rhs[idx] += opt_.n_prev[idx] / opt_.transient_dt * source_scale;
                }
            }
        }
    }
    A.finalize();
    SolverOptions cont_opt = LinearSolver::default_continuity_options();
    cont_opt.type = opt_.continuity_solver;
    LinearSolver solver(cont_opt);
    Vector x(n.begin(), n.end());
    solver.solve(A, rhs, x);
    bool has_nan = false;
    for (size_t i = 0; i < N; ++i) {
        if (std::isnan((double)x[i]) || std::isinf((double)x[i])) {
            has_nan = true;
            std::cerr << "NaN/Inf in electron continuity at i=" << i << " x=" << (double)x[i] << std::endl;
        }
        n[i] = x[i];
        if (n[i] < 0.0Q) n[i] = EPSILON;
    }
    if (has_nan) return false;
    return true;
}

bool GummelSolver::solve_hole_density(const std::vector<real_t>& phi,
                                      const std::vector<real_t>& n,
                                      std::vector<real_t>& p) {
    // Compute BTBT generation and add to optical generation
    std::vector<real_t> G_btbt;
    if (opt_.btbt.enabled) {
        compute_btbt(phi, G_btbt);
    }
    // Compute avalanche impact-ionization generation
    std::vector<real_t> G_ii;
    if (opt_.ii.enabled) {
        compute_impact_ionization(phi, n, p, G_ii);
    }

    // Symmetric to electron solve with sign flips for holes
    const size_t N = g_.npts();
    SparseMatrix A(N);
    Vector rhs(N, 0.0Q);
    std::vector<char> is_bc(N, 0);
    for (const auto& [idx, val] : p_bc_) { is_bc[idx] = 1; }

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_bc[idx]) {
                    A.add_entry(idx, idx, 1.0Q);
                    rhs[idx] = p_bc_.at(idx);
                    continue;
                }
                // Insulator / metal: zero mobility -> freeze carrier density
                if (mu_p_[idx] < EPSILON) {
                    // Use a large diagonal to prevent pivot swapping in dense direct
                    A.add_entry(idx, idx, 1.0e20Q);
                    rhs[idx] = 1.0e20Q * EPSILON;
                    continue;
                }
                real_t center = 0.0Q;
                auto add_link = [&](size_t nbr, real_t dx, real_t mu) {
                    // Skip coupling to insulator/metal neighbors: zero carrier flux
                    if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                    real_t dphi = phi[nbr] - phi[idx];
                    real_t B_plus = bernoulli(dphi / opt_.VT);
                    real_t B_minus = bernoulli(-dphi / opt_.VT);
                    real_t D = mu * opt_.VT / dx;
                    // Hole SG: J_p = -q*D*[B(dphi/VT)*p_i - B(-dphi/VT)*p_j]
                    // Equation: B_plus*p_i - B_minus*p_j = 0
                    // => diagonal coeff = D*B_plus, off-diagonal = -D*B_minus
                    real_t a_ii = D * B_plus;    // contribution to diagonal (positive)
                    real_t a_ij = -D * B_minus;  // off-diagonal (negative)
                    A.add_entry(idx, nbr, a_ij);
                    return a_ii;
                };
                if (i + 1 < g_.nx) center += add_link(idx + 1, g_.dx, mu_p_[idx]);
                if (i > 0)        center += add_link(idx - 1, g_.dx, mu_p_[idx]);
                if (j + 1 < g_.ny) center += add_link(idx + g_.nx, g_.dy, mu_p_[idx]);
                if (j > 0)        center += add_link(idx - g_.nx, g_.dy, mu_p_[idx]);
                if (k + 1 < g_.nz) center += add_link(idx + g_.nx * g_.ny, g_.dz, mu_p_[idx]);
                if (k > 0)        center += add_link(idx - g_.nx * g_.ny, g_.dz, mu_p_[idx]);
                real_t ni = intrinsic_density(Eg_[idx], opt_.temperature, Nc_[idx], Nv_[idx], opt_.statistics_type);
                real_t R = 0.0Q;
                if (idx < tau_n_.size() && idx < tau_p_.size() &&
                    tau_n_[idx] > EPSILON && tau_p_[idx] > EPSILON) {
                    real_t np = n[idx] * p[idx];
                    real_t denom = tau_p_[idx] * (n[idx] + ni) + tau_n_[idx] * (p[idx] + ni);
                    if (denom > EPSILON)
                        R = (np - ni * ni) / denom;
                }
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.btbt.enabled && idx < G_btbt.size()) G += G_btbt[idx];
                if (opt_.ii.enabled && idx < G_ii.size()) G += G_ii[idx];
                real_t source_scale = g_.dx;
                A.add_entry(idx, idx, center);
                rhs[idx] = (G - R) * source_scale;
                // Transient term: backward Euler (see electron block above).
                if (opt_.transient_enabled && idx < opt_.p_prev.size()) {
                    A.add_entry(idx, idx, source_scale / opt_.transient_dt);
                    rhs[idx] += opt_.p_prev[idx] / opt_.transient_dt * source_scale;
                }
            }
        }
    }
    A.finalize();

    SolverOptions cont_opt = LinearSolver::default_continuity_options();
    cont_opt.type = opt_.continuity_solver;
    LinearSolver solver(cont_opt);
    Vector x(p.begin(), p.end());
    solver.solve(A, rhs, x);
    bool has_nan = false;
    for (size_t i = 0; i < N; ++i) {
        if (std::isnan((double)x[i]) || std::isinf((double)x[i])) {
            has_nan = true;
            std::cerr << "NaN/Inf in hole continuity at i=" << i << " x=" << (double)x[i] << std::endl;
        }
        p[i] = x[i];
        if (p[i] < 0.0Q) p[i] = EPSILON;
    }
    if (has_nan) return false;
    return true;
}

bool GummelSolver::solve_continuity(const std::vector<real_t>& phi,
                                    std::vector<real_t>& n,
                                    std::vector<real_t>& p) {
    bool ok = true;
    std::vector<real_t> n_ref = n, p_ref = p;
    for (size_t inner = 0; inner < opt_.inner_iterations; ++inner) {
        bool ok1 = solve_electron_density(phi, n, p);
        bool ok2 = solve_hole_density(phi, n, p);
        ok = ok && ok1 && ok2;
        // Apply carrier damping relative to the reference (start of inner loop)
        for (size_t i = 0; i < n.size(); ++i) {
            if (opt_.use_log_damping && n[i] > EPSILON && p[i] > EPSILON) {
                real_t ratio_n = n[i] / n_ref[i];
                real_t ratio_p = p[i] / p_ref[i];
                if (ratio_n > opt_.log_damping_threshold || ratio_n < 1.0Q / opt_.log_damping_threshold) {
                    n[i] = n_ref[i] * exp_q(opt_.cont_damping * log_q(ratio_n));
                } else {
                    n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_ref[i];
                }
                if (ratio_p > opt_.log_damping_threshold || ratio_p < 1.0Q / opt_.log_damping_threshold) {
                    p[i] = p_ref[i] * exp_q(opt_.cont_damping * log_q(ratio_p));
                } else {
                    p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_ref[i];
                }
            } else {
                n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_ref[i];
                p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_ref[i];
            }
            if (n[i] < 0.0Q) n[i] = EPSILON;
            if (p[i] < 0.0Q) p[i] = EPSILON;
        }
    }
    return ok;
}

bool GummelSolver::solve(std::vector<real_t>& phi,
                         std::vector<real_t>& n,
                         std::vector<real_t>& p) {
    poisson_res_.clear();
    cont_res_.clear();
    const size_t N = Nd_minus_Na_.size();

    std::vector<real_t> phi_old(N);
    std::vector<real_t> n_old(N), p_old(N);

    bool phi_frozen = false;
    for (size_t iter = 0; iter < opt_.max_iter; ++iter) {
        phi_old = phi;
        n_old = n;
        p_old = p;

        // --- Step 1: Solve Poisson with frozen n, p (skip if phi already frozen) ---
        // Ferroelectric polarization is refreshed EVERY iteration, even when phi
        // is frozen.  Previously P was updated inside the (!phi_frozen) block,
        // so once phi froze the polarization was pinned to its value at the
        // freeze instant — it could no longer follow the (externally ramped)
        // gate bias, producing sporadic non-switching in HZO and no memory
        // window.  Refreshing P against the current phi (which still carries
        // the latest contact voltages even when the Gummel update is frozen)
        // restores the path-dependent loop.  (FE-coupling fix, audit §21.)
        if (opt_.ferro.enabled) {
            if (opt_.transient_enabled) {
                poisson_.update_ferroelectric_polarization_transient(phi, opt_.transient_dt);
            } else {
                poisson_.update_ferroelectric_polarization(phi);
            }
        }
        if (!phi_frozen) {
            std::vector<real_t> n_solve = n, p_solve = p;
            if (opt_.enable_quantum) {
                dg_.correct(n, p, n_solve, p_solve);
            }
            // P2.2: cache phi for the leakage field-dependent conductance.
            // P6: also needed for interface-trap charge (uses cached phi for f_t).
            // Always cache - it's cheap and serves both leakage and trap models.
            poisson_.set_leakage_field(phi);
            poisson_.assemble(n_solve, p_solve);
            if (!poisson_.solve(phi)) {
                std::cerr << "Gummel iter " << iter << ": Poisson solve failed\n";
                return false;
            }
            // Damping for phi: uniform linear damping + optional log cap for extremes
            real_t current_damping = opt_.damping;
            if (opt_.adaptive_damping && iter >= 10 && poisson_res_.size() >= opt_.oscillation_window) {
                // Detect oscillation: rel_dPhi increasing for several consecutive iterations
                bool increasing = true;
                for (size_t k = 1; k <= opt_.oscillation_window; ++k) {
                    if (poisson_res_[poisson_res_.size() - k] <=
                        poisson_res_[poisson_res_.size() - k - 1]) {
                        increasing = false;
                        break;
                    }
                }
                if (increasing) {
                    current_damping *= 0.7Q;
                    if (current_damping < opt_.min_damping) current_damping = opt_.min_damping;
                    std::cout << "  [Adaptive] phi damping reduced to " << (double)current_damping << std::endl;
                }
            }
            for (size_t i = 0; i < N; ++i) {
                real_t upd = phi[i] - phi_old[i];
                // Step 1: uniform linear damping
                upd *= current_damping;
                // Step 2: soft log cap for extreme swings (prevents Inf/NaN)
                real_t cap = opt_.phi_log_damp_threshold * opt_.VT;
                if (abs_q(upd) > cap) {
                    real_t sign = (upd > 0.0Q) ? 1.0Q : -1.0Q;
                    upd = sign * cap * log_q(1.0Q + abs_q(upd) / cap);
                }
                phi[i] = phi_old[i] + upd;
            }
            // Detect stable limit-cycle oscillation:
            // Requirements:
            //  1. iter >= 20 (don't freeze early)
            //  2. Amplitude is small (< 0.1 relative)
            //  3. At least 2 rises in the last 5 consecutive pairs (true oscillation)
            //  4. Overall variation in the last 6 iters is modest (< 30%)
            // Condition 3 is the key discriminator: slow monotonic convergence has
            // 0 or 1 rises, while a limit-cycle has 2+.
            if (iter >= 20 && poisson_res_.size() >= 6) {
                real_t max_r = poisson_res_[poisson_res_.size()-1];
                real_t min_r = max_r;
                size_t rises = 0;
                for (size_t k = 0; k < 5; ++k) {
                    real_t r1 = poisson_res_[poisson_res_.size()-1-k];
                    real_t r2 = poisson_res_[poisson_res_.size()-2-k];
                    if (r1 > r2) ++rises;
                    max_r = std::max(max_r, r1);
                    max_r = std::max(max_r, r2);
                    min_r = std::min(min_r, r1);
                    min_r = std::min(min_r, r2);
                }
                // Only freeze when oscillation amplitude is small (< 0.1),
                // and there are at least 2 rises in the last 5 pairs (true oscillation).
                if (opt_.enable_phi_freezing && min_r > 0 && max_r < 1e-1Q && rises >= 2 &&
                    (max_r - min_r) / min_r < 0.3Q) {
                    phi_frozen = true;
                    std::cout << "  [Stabilize] phi frozen at iter " << iter
                              << " (rel_dPhi=" << (double)max_r << ")" << std::endl;
                }
            }
            if (phi_frozen) {
                phi = phi_old;
            }
        }

        // --- Step 2: Solve continuity with new phi ---
        if (!solve_electron_density(phi, n, p)) {
            std::cerr << "Gummel iter " << iter << ": Electron continuity failed\n";
            return false;
        }
        if (!solve_hole_density(phi, n, p)) {
            std::cerr << "Gummel iter " << iter << ": Hole continuity failed\n";
            return false;
        }
        // Damping for n and p
        for (size_t i = 0; i < N; ++i) {
            if (opt_.use_log_damping && n_old[i] > EPSILON && p_old[i] > EPSILON) {
                real_t ratio_n = n[i] / n_old[i];
                real_t ratio_p = p[i] / p_old[i];
                if (ratio_n > opt_.log_damping_threshold || ratio_n < 1.0Q / opt_.log_damping_threshold) {
                    n[i] = n_old[i] * exp_q(opt_.cont_damping * log_q(ratio_n));
                } else {
                    n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_old[i];
                }
                if (ratio_p > opt_.log_damping_threshold || ratio_p < 1.0Q / opt_.log_damping_threshold) {
                    p[i] = p_old[i] * exp_q(opt_.cont_damping * log_q(ratio_p));
                } else {
                    p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_old[i];
                }
            } else {
                n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_old[i];
                p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_old[i];
            }
            if (n[i] < 0.0Q) n[i] = EPSILON;
            if (p[i] < 0.0Q) p[i] = EPSILON;
        }

        // --- Step 3: Convergence check ---
        real_t dphi = 0.0Q, dn = 0.0Q, dp = 0.0Q;
        real_t phi_scale = 1.0Q, n_scale = 1.0Q, p_scale = 1.0Q;
        bool has_nan = false;
        for (size_t i = 0; i < N; ++i) {
            if (std::isnan((double)phi[i]) || std::isnan((double)n[i]) || std::isnan((double)p[i]) ||
                std::isinf((double)phi[i]) || std::isinf((double)n[i]) || std::isinf((double)p[i])) {
                has_nan = true;
                break;
            }
            dphi = std::max(dphi, abs_q(phi[i] - phi_old[i]));
            dn   = std::max(dn,   abs_q(n[i]   - n_old[i]));
            dp   = std::max(dp,   abs_q(p[i]   - p_old[i]));
            phi_scale = std::max(phi_scale, abs_q(phi[i]));
            n_scale   = std::max(n_scale,   abs_q(n[i]));
            p_scale   = std::max(p_scale,   abs_q(p[i]));
        }

        if (has_nan) {
            std::cerr << "Gummel iter " << iter << ": NaN/Inf detected, aborting\n";
            phi = phi_old; n = n_old; p = p_old;
            return false;
        }

        real_t rel_dphi = dphi / (phi_scale + 1.0Q);
        real_t rel_dn   = dn   / (n_scale   + 1.0Q);
        real_t rel_dp   = dp   / (p_scale   + 1.0Q);
        real_t rel_cont = std::max(rel_dn, rel_dp);

        poisson_res_.push_back(rel_dphi);
        cont_res_.push_back(rel_cont);

        std::cout << "Gummel iter " << iter
                  << "  rel_dPhi=" << (double)rel_dphi
                  << "  rel_dN=" << (double)rel_dn
                  << "  rel_dP=" << (double)rel_dp << std::endl;

        if (rel_dphi < opt_.poisson_tol && rel_cont < opt_.continuity_tol) {
            std::cout << "Gummel converged in " << iter + 1 << " iterations.\n";

            // --- Final undamped continuity polish --------------------------------
            // Throughout the iteration the carrier updates were under-relaxed
            // (cont_damping < 1) for stability.  The returned (n,p) therefore
            // do *not* exactly satisfy the discrete continuity equations for
            // the converged phi, which breaks Kirchhoff's current law by O(1)
            // on biased devices (see audit0618.md §10.3).  Re-solve continuity
            // once with damping disabled so the returned fields are the true
            // discrete steady state at this phi.  phi is held fixed here, so
            // the Poisson-continuity coupling is not perturbed.
            if (opt_.cont_damping < 1.0Q || opt_.use_log_damping) {
                GummelOptions polish_opt = opt_;
                polish_opt.cont_damping = 1.0Q;       // no relaxation
                polish_opt.use_log_damping = false;    // no log-space blend
                polish_opt.inner_iterations = 1;       // single clean pass
                // Temporarily swap options for the polish call.
                GummelOptions saved = opt_;
                opt_ = polish_opt;
                bool polish_ok = solve_continuity(phi, n, p);
                opt_ = saved;
                if (!polish_ok) {
                    std::cerr << "Gummel final continuity polish failed "
                              << "(continuing with damped fields)\n";
                }
            }
            return true;
        }
    }

    std::cerr << "Gummel did not converge within max_iter\n";
    return false;
}

void GummelSolver::set_poisson_solver_type(SolverType type) {
    opt_.poisson_solver = type;
    SolverOptions poisson_opt = LinearSolver::default_poisson_options();
    poisson_opt.type = type;
    poisson_.set_solver_options(poisson_opt);
}

void GummelSolver::set_continuity_solver_type(SolverType type) {
    opt_.continuity_solver = type;
}

} // namespace tcad
