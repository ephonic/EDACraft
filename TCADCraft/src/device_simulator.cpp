#include "device_simulator.h"
#include "statistics.h"
#include <iostream>
#include <cmath>

namespace tcad {

DeviceSimulator::DeviceSimulator(size_t nx, size_t ny, size_t nz,
                                 real_t dx, real_t dy, real_t dz)
    : g_{nx, ny, nz, dx, dy, dz},
      poisson_(g_),
      gummel_(g_),
      newton_(g_),
      dg_(g_) {
    const size_t N = g_.npts();
    eps_.assign(N, EPS0 * 11.7Q);
    mu_n_.assign(N, 0.14Q);
    mu_p_.assign(N, 0.045Q);
    // Default: effectively no SRH (infinite lifetime) to avoid perturbing
    // existing simulations.  Users must explicitly call set_recombination()
    // to enable SRH modeling.
    tau_n_.assign(N, 1e100Q);
    tau_p_.assign(N, 1e100Q);
    Nd_minus_Na_.assign(N, 0.0Q);
    G_opt_.assign(N, 0.0Q);
    Nc_.assign(N, 2.8e19Q);   // Default Si conduction-band DOS [cm^-3]
    Nv_.assign(N, 1.04e19Q);  // Default Si valence-band DOS [cm^-3]
    Eg_.assign(N, 1.12Q);     // Default Si bandgap [eV]
    thermal_conductivity_.assign(N, 150.0Q); // Default: Silicon thermal conductivity [W/(m*K)]
}

void DeviceSimulator::set_permittivity(const std::vector<real_t>& eps) {
    if (eps.size() != g_.npts()) throw std::invalid_argument("permittivity size mismatch");
    eps_ = eps;
    poisson_.set_permittivity(eps_);
}

void DeviceSimulator::set_edge_permittivity(const std::vector<real_t>& x_plus,
                                            const std::vector<real_t>& x_minus,
                                            const std::vector<real_t>& y_plus,
                                            const std::vector<real_t>& y_minus,
                                            const std::vector<real_t>& z_plus,
                                            const std::vector<real_t>& z_minus) {
    poisson_.set_edge_permittivity(x_plus, x_minus, y_plus, y_minus, z_plus, z_minus);
}

void DeviceSimulator::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    mu_n_ = mu_n; mu_p_ = mu_p;
    gummel_.set_mobility(mu_n_, mu_p_);
}

void DeviceSimulator::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    Nd_minus_Na_ = Nd_minus_Na;
    poisson_.set_doping(Nd_minus_Na_);
    gummel_.set_doping(Nd_minus_Na_);
}

void DeviceSimulator::set_optical_generation(const std::vector<real_t>& G_opt) {
    if (G_opt.size() != g_.npts()) throw std::invalid_argument("optical generation size mismatch");
    G_opt_ = G_opt;
    gummel_.set_optical_generation(G_opt_);
}

void DeviceSimulator::set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p) {
    if (tau_n.size() != g_.npts() || tau_p.size() != g_.npts())
        throw std::invalid_argument("recombination lifetime size mismatch");
    tau_n_ = tau_n;
    tau_p_ = tau_p;
    gummel_.set_recombination(tau_n_, tau_p_);
}

void DeviceSimulator::set_thermal_voltage(real_t VT) {
    VT_ = VT;
    gummel_.set_mobility(mu_n_, mu_p_); // Re-apply with same values (GummelOptions has VT)
}

void DeviceSimulator::set_dirichlet_potential(const std::map<size_t, real_t>& bc) {
    for (const auto& kv : bc) {
        phi_bc_[kv.first] = kv.second;
    }
    poisson_.set_dirichlet(phi_bc_);
}

void DeviceSimulator::set_electron_bc(const std::map<size_t, real_t>& bc) {
    for (const auto& kv : bc) {
        n_bc_[kv.first] = kv.second;
    }
    gummel_.set_electron_bc(n_bc_);
}

void DeviceSimulator::set_hole_bc(const std::map<size_t, real_t>& bc) {
    for (const auto& kv : bc) {
        p_bc_[kv.first] = kv.second;
    }
    gummel_.set_hole_bc(p_bc_);
}

void DeviceSimulator::set_quantum_enabled(bool enable) {
    quantum_enabled_ = enable;
}

void DeviceSimulator::set_phi_freezing_enabled(bool enable) {
    // Applied during solve() when rebuilding GummelSolver
    // For now we store it in a member that will be checked in solve()
    // (Need to add member variable)
}

void DeviceSimulator::set_newton_freeze_phi(bool enable) { newton_freeze_phi_ = enable; }
void DeviceSimulator::set_newton_freeze_n(bool enable) { newton_freeze_n_ = enable; }
void DeviceSimulator::set_newton_freeze_p(bool enable) { newton_freeze_p_ = enable; }

void DeviceSimulator::set_gummel_max_iter(size_t max_iter) {
    max_iter_ = max_iter;
}

void DeviceSimulator::set_tolerance(real_t tol) {
    tol_ = tol;
}

void DeviceSimulator::set_poisson_solver_type(int type) {
    poisson_solver_type_ = static_cast<SolverType>(type);
    gummel_.set_poisson_solver_type(poisson_solver_type_);
}

void DeviceSimulator::set_continuity_solver_type(int type) {
    continuity_solver_type_ = static_cast<SolverType>(type);
    gummel_.set_continuity_solver_type(continuity_solver_type_);
}

void DeviceSimulator::set_use_newton(bool enable) {
    use_newton_ = enable;
}

void DeviceSimulator::set_newton_damping(real_t damping) {
    newton_damping_ = damping;
}

void DeviceSimulator::set_newton_min_damping(real_t min_damping) {
    newton_min_damping_ = min_damping;
}

void DeviceSimulator::set_newton_use_line_search(bool enable) {
    newton_use_line_search_ = enable;
}

void DeviceSimulator::set_newton_line_search_max(size_t max) {
    newton_line_search_max_ = max;
}

void DeviceSimulator::set_newton_use_log_damping(bool enable) {
    newton_use_log_damping_ = enable;
}

void DeviceSimulator::set_newton_use_log_space(bool enable) {
    newton_use_log_space_ = enable;
}

void DeviceSimulator::set_newton_jacobian_reuse_threshold(real_t threshold) {
    newton_jacobian_reuse_threshold_ = threshold;
}

void DeviceSimulator::set_thermal_coupling_enabled(bool enable) {
    thermal_coupling_enabled_ = enable;
}

void DeviceSimulator::set_thermal_conductivity(const std::vector<real_t>& kappa) {
    if (kappa.size() != g_.npts()) throw std::invalid_argument("thermal conductivity size mismatch");
    thermal_conductivity_ = kappa;
}

void DeviceSimulator::set_ambient_temperature(real_t T_ambient) {
    ambient_temperature_ = T_ambient;
}

void DeviceSimulator::set_thermal_dirichlet(const std::map<size_t, real_t>& bc) {
    thermal_bc_ = bc;
}

void DeviceSimulator::set_btbt_enabled(bool enable) {
    btbt_enabled_ = enable;
}

void DeviceSimulator::set_btbt_params(real_t A, real_t B, int D) {
    btbt_A_ = A;
    btbt_B_ = B;
    btbt_D_ = D;
}

void DeviceSimulator::set_btbt_use_nonlocal(bool enable) {
    btbt_use_nonlocal_ = enable;
}

void DeviceSimulator::set_ii_enabled(bool enable) {
    ii_enabled_ = enable;
}

void DeviceSimulator::set_ii_params(real_t A_n, real_t B_n, real_t A_p, real_t B_p) {
    ii_A_n_ = A_n;
    ii_B_n_ = B_n;
    ii_A_p_ = A_p;
    ii_B_p_ = B_p;
}

void DeviceSimulator::set_breakdown_enabled(bool enable) {
    bd_enabled_ = enable;
}

void DeviceSimulator::set_breakdown_params(const std::vector<char>& bd_mask,
                                           const std::vector<real_t>& E_bd,
                                           real_t sigma_bd) {
    if (bd_mask.size() != g_.npts())
        throw std::invalid_argument("bd_mask size mismatch");
    if (E_bd.size() != g_.npts())
        throw std::invalid_argument("E_bd size mismatch");
    bd_mask_ = bd_mask;
    E_bd_ = E_bd;
    sigma_bd_ = sigma_bd;
}

void DeviceSimulator::set_ferroelectric_enabled(bool enable) {
    fe_enabled_ = enable;
}

void DeviceSimulator::set_ferroelectric_params(const std::vector<char>& fe_mask,
                                               real_t alpha, real_t beta) {
    if (fe_mask.size() != g_.npts())
        throw std::invalid_argument("fe_mask size mismatch");
    fe_mask_ = fe_mask;
    fe_alpha_ = alpha;
    fe_beta_ = beta;
}

void DeviceSimulator::set_ferroelectric_model(int model) {
    // 0 = Landau-Khalatnikov, 1 = Preisach (play operator). M7c.
    fe_model_ = model;
}

void DeviceSimulator::set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale) {
    fe_ps_ = ps;
    fe_ec_ = ec;
    fe_escale_ = escale;
}

void DeviceSimulator::set_ferroelectric_builtin_field(real_t E_bi) {
    fe_E_bi_ = E_bi;   // P2.1: internal/imprint offset; 0 => symmetric
}

void DeviceSimulator::set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt) {
    fe_nls_tau0_ = tau0;   // P3: Merz tau(E) = tau0*exp(E0/|E|)
    fe_nls_E0_ = E0;
    fe_nls_dt_ = dt;
}

void DeviceSimulator::set_leakage(const std::vector<char>& mask,
                                  real_t C_pf, real_t B_pf, real_t phi_t,
                                  real_t C_fn, real_t B_fn, real_t phi_b,
                                  real_t E_floor, real_t sigma_cap) {
    if (mask.size() != g_.npts())
        throw std::invalid_argument("leakage mask size mismatch");
    leak_mask_ = mask;
    leak_C_pf_ = C_pf; leak_B_pf_ = B_pf; leak_phi_t_ = phi_t;
    leak_C_fn_ = C_fn; leak_B_fn_ = B_fn; leak_phi_b_ = phi_b;
    leak_E_floor_ = E_floor;
    leak_sigma_cap_ = sigma_cap;
    leak_enabled_ = true;
}

void DeviceSimulator::set_leakage_enabled(bool enable) {
    leak_enabled_ = enable;
}

void DeviceSimulator::set_interface_traps(const std::vector<char>& mask,
                                          real_t D_it, real_t E_t) {
    if (mask.size() != g_.npts())
        throw std::invalid_argument("trap mask size mismatch");
    trap_mask_ = mask;
    trap_D_it_ = D_it;
    trap_E_t_ = E_t;
}

void DeviceSimulator::set_oxide_traps(const std::vector<real_t>& Q_ot) {
    Q_ot_ = Q_ot;
}

void DeviceSimulator::set_initial_guess(const std::vector<real_t>& phi,
                                         const std::vector<real_t>& n,
                                         const std::vector<real_t>& p) {
    if (phi.size() != g_.npts() || n.size() != g_.npts() || p.size() != g_.npts())
        throw std::invalid_argument("initial guess size mismatch");
    init_phi_ = phi;
    init_n_ = n;
    init_p_ = p;
    has_initial_guess_ = true;
}

void DeviceSimulator::clear_initial_guess() {
    has_initial_guess_ = false;
    init_phi_.clear();
    init_n_.clear();
    init_p_.clear();
}

void DeviceSimulator::set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv) {
    if (Nc.size() != g_.npts() || Nv.size() != g_.npts())
        throw std::invalid_argument("effective DOS size mismatch");
    Nc_ = Nc;
    Nv_ = Nv;
}

void DeviceSimulator::set_bandgap(const std::vector<real_t>& Eg) {
    if (Eg.size() != g_.npts()) throw std::invalid_argument("bandgap size mismatch");
    Eg_ = Eg;
}

void DeviceSimulator::set_temperature(real_t T) {
    temperature_ = T;
    VT_ = 8.617333262e-5Q * T;
}

void DeviceSimulator::set_statistics_type(int type) {
    statistics_type_ = (type == 1) ? StatisticsType::FERMI_DIRAC : StatisticsType::BOLTZMANN;
}

void DeviceSimulator::set_mobility_model(int type) {
    if (type == 1) mobility_model_type_ = MobilityModelType::ARORA;
    else if (type == 2) mobility_model_type_ = MobilityModelType::LOW_TEMP;
    else mobility_model_type_ = MobilityModelType::CONSTANT;
}

void DeviceSimulator::set_transient_enabled(bool enable) { transient_enabled_ = enable; }
void DeviceSimulator::set_transient_dt(real_t dt) { transient_dt_ = dt; }
void DeviceSimulator::set_transient_t_final(real_t t_final) { transient_t_final_ = t_final; }
void DeviceSimulator::set_ferroelectric_gamma(real_t gamma) { fe_gamma_ = gamma; }

SimulationResult DeviceSimulator::solve() {
    const size_t N = g_.npts();
    SimulationResult res;
    res.phi.assign(N, 0.0Q);
    res.n.assign(N, 0.0Q);
    res.p.assign(N, 0.0Q);

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
    }

    // Apply mobility model if not constant
    std::vector<real_t> mu_n_eff = mu_n_, mu_p_eff = mu_p_;
    if (mobility_model_type_ != MobilityModelType::CONSTANT) {
        for (size_t i = 0; i < N; ++i) {
            mu_n_eff[i] = evaluate_mobility(mobility_model_type_, true, temperature_, Nd_minus_Na_[i], 0.0Q, mu_n_[i]);
            mu_p_eff[i] = evaluate_mobility(mobility_model_type_, false, temperature_, 0.0Q, Nd_minus_Na_[i], mu_p_[i]);
        }
    }

    if (has_initial_guess_) {
        // Use provided initial guess (e.g. from previous ramp step)
        res.phi = init_phi_;
        res.n = init_n_;
        res.p = init_p_;
    } else {
        // Initial guess: equilibrium (charge neutrality + Boltzmann/FD)
        for (size_t i = 0; i < N; ++i) {
            real_t C = Nd_minus_Na_[i];
            // n*p = ni^2, n - p = C
            // Use numerically stable formulas to avoid catastrophic cancellation
            real_t half_C = C / 2.0Q;
            real_t disc = sqrt_q(ni[i] * ni[i] + half_C * half_C);
            real_t n_eq, p_eq;
            if (C >= 0.0Q) {
                n_eq = disc + half_C;           // ~Nd on n-side
                p_eq = (n_eq > EPSILON) ? (ni[i] * ni[i] / n_eq) : 0.0Q;
            } else {
                p_eq = disc - half_C;           // ~Na on p-side
                n_eq = (p_eq > EPSILON) ? (ni[i] * ni[i] / p_eq) : 0.0Q;
            }
            res.n[i] = n_eq;
            res.p[i] = p_eq;
            // Equilibrium potential: phi_eq = VT * ln(n/ni) = -VT * ln(p/ni)
            if (n_eq > EPSILON) {
                res.phi[i] = VT_ * log_q(n_eq / ni[i]);
            } else if (p_eq > EPSILON) {
                res.phi[i] = -VT_ * log_q(p_eq / ni[i]);
            } else {
                res.phi[i] = 0.0Q;
            }
        }
    }

    // Apply BCs to initial guess (overrides equilibrium where specified)
    for (const auto& [idx, val] : n_bc_) res.n[idx] = val;
    for (const auto& [idx, val] : p_bc_) res.p[idx] = val;

    // For phi, if Dirichlet BCs are given, keep equilibrium phi and only
    // override at the boundary nodes.  Equilibrium phi (from local doping)
    // is already a good initial guess for the Poisson solve.
    for (const auto& [idx, val] : phi_bc_) res.phi[idx] = val;

    GummelOptions opt;
    opt.max_iter = max_iter_;
    opt.poisson_tol = tol_;
    opt.continuity_tol = tol_;
    opt.enable_quantum = quantum_enabled_;
    opt.VT = VT_;
    // Auto-switch from dense direct to iterative/PETSc for large systems
    // to avoid O(n^3) slowdown.  User overrides are respected.
    if (N > 2000) {
#ifdef TCAD_USE_PETSC
        if (poisson_solver_type_ == SolverType::DENSE_DIRECT)
            opt.poisson_solver = SolverType::PETSC;
        else
            opt.poisson_solver = poisson_solver_type_;
        if (continuity_solver_type_ == SolverType::DENSE_DIRECT)
            opt.continuity_solver = SolverType::PETSC;
        else
            opt.continuity_solver = continuity_solver_type_;
#else
        if (poisson_solver_type_ == SolverType::DENSE_DIRECT)
            opt.poisson_solver = SolverType::BICGSTAB_ILU0;
        else
            opt.poisson_solver = poisson_solver_type_;
        if (continuity_solver_type_ == SolverType::DENSE_DIRECT)
            opt.continuity_solver = SolverType::BICGSTAB_ILU0;
        else
            opt.continuity_solver = continuity_solver_type_;
#endif
    } else {
        opt.poisson_solver = poisson_solver_type_;
        opt.continuity_solver = continuity_solver_type_;
    }
    // BTBT parameters
    opt.btbt.enabled = btbt_enabled_;
    opt.btbt.A_kane = btbt_A_;
    opt.btbt.B_kane = btbt_B_;
    opt.btbt.D = btbt_D_;
    opt.btbt.use_nonlocal = btbt_use_nonlocal_;
    // Impact ionization parameters
    opt.ii.enabled = ii_enabled_;
    opt.ii.A_n = ii_A_n_;
    opt.ii.B_n = ii_B_n_;
    opt.ii.A_p = ii_A_p_;
    opt.ii.B_p = ii_B_p_;
    // Ferroelectric parameters
    opt.ferro.enabled = fe_enabled_;
    opt.ferro.fe_mask = fe_mask_;
    opt.ferro.alpha = fe_alpha_;
    opt.ferro.beta = fe_beta_;
    opt.ferro.model = static_cast<FerroelectricModel>(fe_model_);
    opt.ferro.ps = fe_ps_;
    opt.ferro.ec = fe_ec_;
    opt.ferro.escale = fe_escale_;
    opt.ferro.E_bi = fe_E_bi_;   // P2.1: internal/imprint offset
    opt.ferro.nls_tau0 = fe_nls_tau0_;   // P3: NLS Merz parameters
    opt.ferro.nls_E0 = fe_nls_E0_;
    opt.ferro.nls_dt = fe_nls_dt_;
    // Leakage current (PF/FN) parameters (P2.2)
    opt.leakage.enabled = leak_enabled_;
    opt.leakage.mask = leak_mask_;
    opt.leakage.C_pf = leak_C_pf_; opt.leakage.B_pf = leak_B_pf_; opt.leakage.phi_t = leak_phi_t_;
    opt.leakage.C_fn = leak_C_fn_; opt.leakage.B_fn = leak_B_fn_; opt.leakage.phi_b = leak_phi_b_;
    opt.leakage.E_floor = leak_E_floor_;
    opt.leakage.sigma_cap = leak_sigma_cap_;

    // Dielectric breakdown: one-time init of the irreversible state vector
    // (mirrors fe_polarization_init_).  bd_state_ persists across solve() so a
    // broken-down node stays broken down on subsequent bias points. (M7b, §22)
    if (bd_enabled_) {
        if (!bd_state_init_) {
            bd_state_.assign(N, 0);
            bd_state_init_ = true;
        }
    }

    if (use_newton_) {
        // Hybrid: Gummel first for robust initial guess, then Newton for fast convergence
        gummel_ = GummelSolver(g_, opt);
        gummel_.set_mobility(mu_n_eff, mu_p_eff);
        gummel_.set_doping(Nd_minus_Na_);
        gummel_.set_recombination(tau_n_, tau_p_);
        gummel_.set_optical_generation(G_opt_);
        gummel_.set_effective_dos(Nc_, Nv_);
        gummel_.set_bandgap(Eg_);
        gummel_.set_electron_bc(n_bc_);
        gummel_.set_hole_bc(p_bc_);
        gummel_.set_poisson_dirichlet(phi_bc_);
        gummel_.set_permittivity(eps_);
        // Inject the persistent vector P so this bias point continues from the
        // previous one (path dependence -> hysteresis). GummelSolver (and its
        // PoissonSolver.fe_polarization_) is rebuilt every solve(); without
        // this injection P would be reset to zero and no loop could form.
        if (fe_enabled_) {
            if (!fe_polarization_init_) {
                fe_polarization_.assign(3 * N, 0.0Q);
                fe_polarization_init_ = true;
            }
            gummel_.set_fe_polarization(fe_polarization_);
            // Inject the persistent Preisach play state (M7c).
            if (fe_model_ == 1) {
                if (fe_play_state_.size() != N) fe_play_state_.assign(N, 0.0Q);
                gummel_.set_fe_play_state(fe_play_state_);
            }
        }
        // Inject the persistent breakdown state so the Gummel warm-up Poisson
        // assemble applies the leakage term at already-broken nodes. (M7b)
        if (bd_enabled_) {
            gummel_.set_breakdown_state(bd_state_, sigma_bd_);
        }
        // Inject trap charge into Gummel's PoissonSolver (P6).
        if (!trap_mask_.empty()) {
            gummel_.set_interface_traps(trap_mask_, trap_D_it_, trap_E_t_);
        }
        if (!Q_ot_.empty()) gummel_.set_oxide_traps(Q_ot_);
        bool gummel_ok = gummel_.solve(res.phi, res.n, res.p);
        if (fe_enabled_) {
            fe_polarization_ = gummel_.fe_polarization();
            if (fe_model_ == 1) fe_play_state_ = gummel_.fe_play_state();
        }
        size_t gummel_iters = gummel_.poisson_residuals().size();

        if (gummel_ok) {
            // Use Gummel solution as initial guess for Newton
            NewtonOptions nopt;
            nopt.max_iter = max_iter_;
            nopt.tol = (double)tol_;
            nopt.abs_tol = 1e-20Q;
            nopt.verbose = false;
            nopt.damping = newton_damping_;
            nopt.min_damping = newton_min_damping_;
            nopt.use_line_search = newton_use_line_search_;
            nopt.line_search_max = newton_line_search_max_;
            nopt.use_log_damping = newton_use_log_damping_;
            nopt.use_log_space = newton_use_log_space_;
            nopt.jacobian_reuse_threshold = newton_jacobian_reuse_threshold_;
            nopt.enable_btbt = btbt_enabled_;
            nopt.btbt_A = btbt_A_;
            nopt.btbt_B = btbt_B_;
            nopt.btbt_D = btbt_D_;
            nopt.enable_ii = ii_enabled_;
            nopt.ii_A_n = ii_A_n_;
            nopt.ii_B_n = ii_B_n_;
            nopt.ii_A_p = ii_A_p_;
            nopt.ii_B_p = ii_B_p_;
            nopt.temperature = temperature_;
            nopt.statistics_type = statistics_type_;
            nopt.linear_solver = (N > 2000) ? SolverType::PETSC : SolverType::DENSE_DIRECT;
            // C档: Newton freeze flags (isolated-continuity MMS).
            nopt.freeze_phi = newton_freeze_phi_;
            nopt.freeze_n = newton_freeze_n_;
            nopt.freeze_p = newton_freeze_p_;
            newton_ = NewtonSolver(g_, nopt);
            newton_.set_permittivity(eps_);
            newton_.set_mobility(mu_n_eff, mu_p_eff);
            newton_.set_doping(Nd_minus_Na_);
            newton_.set_recombination(tau_n_, tau_p_);
            newton_.set_optical_generation(G_opt_);
            newton_.set_effective_dos(Nc_, Nv_);
            newton_.set_bandgap(Eg_);
            newton_.set_thermal_voltage(VT_);
            newton_.set_phi_dirichlet(phi_bc_);
            newton_.set_electron_bc(n_bc_);
            newton_.set_hole_bc(p_bc_);
            // Inject ferroelectric P + mask so the Newton Poisson residual
            // includes -div(P) (FE-coupling fix, audit §21).  P was already
            // refreshed by the Gummel warm-up above and read back into
            // fe_polarization_; without this, Newton silently dropped FE.
            if (fe_enabled_) {
                newton_.set_ferroelectric_polarization(fe_mask_, fe_polarization_);
            }
            // Inject trap charge so Newton Poisson residual carries Q_it+Q_ot (P6).
            if (!trap_mask_.empty()) {
                newton_.set_trap_charge(trap_mask_, trap_D_it_, trap_E_t_, Q_ot_);
            }
            res.converged = newton_.solve(res.phi, res.n, res.p);
            // Report total iterations (Gummel + Newton) for transparency
            res.iterations = gummel_iters + newton_.residuals().size();
        } else {
            // Gummel failed, report that
            res.converged = false;
            res.iterations = gummel_iters;
        }
    } else {
        // Rebuild gummel solver with options (simplified)
        gummel_ = GummelSolver(g_, opt);
        gummel_.set_mobility(mu_n_eff, mu_p_eff);
        gummel_.set_doping(Nd_minus_Na_);
        gummel_.set_recombination(tau_n_, tau_p_);
        gummel_.set_optical_generation(G_opt_);
        gummel_.set_effective_dos(Nc_, Nv_);
        gummel_.set_bandgap(Eg_);
        gummel_.set_electron_bc(n_bc_);
        gummel_.set_hole_bc(p_bc_);
        gummel_.set_poisson_dirichlet(phi_bc_);
        gummel_.set_permittivity(eps_);
        if (fe_enabled_) {
            if (!fe_polarization_init_) {
                fe_polarization_.assign(3 * N, 0.0Q);
                fe_polarization_init_ = true;
            }
            gummel_.set_fe_polarization(fe_polarization_);
            if (fe_model_ == 1) {
                if (fe_play_state_.size() != N) fe_play_state_.assign(N, 0.0Q);
                gummel_.set_fe_play_state(fe_play_state_);
            }
        }
        // Inject the persistent breakdown state (M7b).
        if (bd_enabled_) {
            gummel_.set_breakdown_state(bd_state_, sigma_bd_);
        }
        // Inject trap charge into Gummel's PoissonSolver (P6).
        if (!trap_mask_.empty()) {
            gummel_.set_interface_traps(trap_mask_, trap_D_it_, trap_E_t_);
        }
        if (!Q_ot_.empty()) gummel_.set_oxide_traps(Q_ot_);

        res.converged = gummel_.solve(res.phi, res.n, res.p);
        if (fe_enabled_) {
            fe_polarization_ = gummel_.fe_polarization();
            if (fe_model_ == 1) fe_play_state_ = gummel_.fe_play_state();
        }
        res.iterations = gummel_.poisson_residuals().size();
    }

    // DeviceSimulator's own poisson_ is used for post-processing (E-field)
    poisson_.set_dirichlet(phi_bc_);
    poisson_.set_permittivity(eps_);

    // Compute E-field even if not fully converged (results may still be useful)
    poisson_.compute_electric_field(res.phi, res.Ex, res.Ey, res.Ez);

    // Dielectric breakdown detection (M7b, audit §22).  After the field is
    // known, flag any masked dielectric node whose |E| exceeds its material
    // breakdown field E_bd.  The flip is IRREVERSIBLE (bd_state_ only goes 0->1)
    // and persists across solve() calls — a broken-down oxide node stays broken
    // down on subsequent (even lower) bias points, modelling the conductive
    // filament.  The leakage term itself is applied on the NEXT solve() via
    // set_breakdown_state above (this solve already assembled without it).
    if (bd_enabled_ && !bd_mask_.empty() && E_bd_.size() == N) {
        for (size_t i = 0; i < N; ++i) {
            if (!bd_mask_[i] || bd_state_[i]) continue;   // skip non-dielectric / already broken
            real_t E2 = res.Ex[i] * res.Ex[i] + res.Ey[i] * res.Ey[i] + res.Ez[i] * res.Ez[i];
            if (E_bd_[i] > 0.0Q && E2 > E_bd_[i] * E_bd_[i]) {
                bd_state_[i] = 1;   // irreversible soft-breakdown
            }
        }
    }

    // Full-precision edge current densities (Audit §20).  Computed in
    // __float128 from the converged phi/n/p to avoid the catastrophic
    // cancellation of double-precision Python re-derivation.
    compute_edge_currents(res, res.phi, res.n, res.p);

    // Thermal coupling (self-heating)
    if (thermal_coupling_enabled_) {
        res.temperature.assign(N, ambient_temperature_);
        
        // Compute self-heating power density: P = sigma * |E|^2 [W/m^3]
        // sigma = q * (mu_n * n + mu_p * p)  [S/m]
        std::vector<real_t> power(N, 0.0Q);
        for (size_t i = 0; i < N; ++i) {
            real_t sigma = QE * (mu_n_[i] * res.n[i] + mu_p_[i] * res.p[i]);
            real_t E2 = res.Ex[i] * res.Ex[i] + res.Ey[i] * res.Ey[i] + res.Ez[i] * res.Ez[i];
            power[i] = sigma * E2;
        }
        
        // If no explicit thermal BCs set, anchor contacts to ambient temperature
        std::map<size_t, real_t> tbc = thermal_bc_;
        if (tbc.empty()) {
            for (const auto& [idx, val] : phi_bc_) {
                tbc[idx] = ambient_temperature_;
            }
        }
        
        // Solve thermal equation: div(kappa * grad(T)) = -P
        PoissonSolver thermal_solver(g_);
        thermal_solver.set_permittivity(thermal_conductivity_);
        thermal_solver.set_dirichlet(tbc);
        // Use PETSc direct solver for thermal — dense solver suffers catastrophic
        // cancellation when matrix coefficients (~1e16) dwarf ambient (~300 K).
        SolverOptions thermal_opt;
        thermal_opt.type = SolverType::PETSC;
        thermal_opt.max_iter = 1;
        thermal_opt.tol = 1e-12Q;
        thermal_solver.set_solver_options(thermal_opt);
        thermal_solver.assemble_thermal(power);
        
        if (!thermal_solver.solve(res.temperature)) {
            std::cerr << "Thermal solve failed\n";
        }
    }

    return res;
}

void DeviceSimulator::compute_edge_currents(SimulationResult& res,
                                            const std::vector<real_t>& phi,
                                            const std::vector<real_t>& n,
                                            const std::vector<real_t>& p) {
    // Full-precision Scharfetter-Gummel edge fluxes from the converged state.
    // Jn = (QE*Dn/d) * (n[i]*B(-dphi/VT) - n[j]*B(+dphi/VT))   [A/m^2]
    // Jp = (QE*Dp/d) * (p[i]*B(+dphi/VT) - p[j]*B(-dphi/VT))
    // where Dn = mu_n*VT, d = grid spacing, dphi = phi[j]-phi[i].
    // Computed in __float128 so the Bernoulli cancellation that destroys the
    // double-precision Python re-derivation (p~1e24, dphi~1e-15) is retained.
    // (Audit §20.)
    const size_t N = g_.npts();
    auto B = [](real_t x) -> real_t {
        // Bernoulli B(x) = x/(exp(x)-1), stable near 0.
        if (x > 100.0Q) return 0.0Q;
        if (x < -100.0Q) return -x;
        if (x > -1e-10Q && x < 1e-10Q) {
            // Taylor: 1 - x/2 + x^2/12
            return 1.0Q - x / 2.0Q + x * x / 12.0Q;
        }
        return x / expm1_q(x);
    };

    res.Jn_x.assign(N, 0.0Q); res.Jn_y.assign(N, 0.0Q); res.Jn_z.assign(N, 0.0Q);
    res.Jp_x.assign(N, 0.0Q); res.Jp_y.assign(N, 0.0Q); res.Jp_z.assign(N, 0.0Q);

    auto fill_axis = [&](std::vector<real_t>& Jn_ax,
                         std::vector<real_t>& Jp_ax,
                         real_t d, size_t stride,
                         size_t n0, size_t n1, size_t n2) {
        // Iterate over nodes that HAVE a +neighbor along this axis.
        for (size_t k = 0; k < n2; ++k) {
            for (size_t j = 0; j < n1; ++j) {
                for (size_t i = 0; i < n0; ++i) {
                    size_t idx = g_.index(i, j, k);
                    size_t nbr = idx + stride;
                    real_t dphi = phi[nbr] - phi[idx];
                    real_t delta = dphi / VT_;
                    real_t Bm = B(-delta);   // B(-dphi/VT)
                    real_t Bp = B(delta);    // B(+dphi/VT)
                    real_t Dn = mu_n_[idx] * VT_ / d;
                    real_t Dp = mu_p_[idx] * VT_ / d;
                    Jn_ax[idx] = QE * Dn * (n[idx] * Bm - n[nbr] * Bp);
                    Jp_ax[idx] = QE * Dp * (p[idx] * Bp - p[nbr] * Bm);
                }
            }
        }
    };

    // +x neighbor exists when i < nx-1 (use upwind mobility mu_[idx])
    fill_axis(res.Jn_x, res.Jp_x, g_.dx, 1,            g_.nx - 1, g_.ny,     g_.nz);
    fill_axis(res.Jn_y, res.Jp_y, g_.dy, g_.nx,        g_.nx,     g_.ny - 1, g_.nz);
    fill_axis(res.Jn_z, res.Jp_z, g_.dz, g_.nx * g_.ny, g_.nx,     g_.ny,     g_.nz - 1);
}

std::vector<SimulationResult> DeviceSimulator::solve_transient() {
    const size_t N = g_.npts();
    std::vector<SimulationResult> history;

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
    }

    // Apply mobility model if not constant
    std::vector<real_t> mu_n_eff = mu_n_, mu_p_eff = mu_p_;
    if (mobility_model_type_ != MobilityModelType::CONSTANT) {
        for (size_t i = 0; i < N; ++i) {
            mu_n_eff[i] = evaluate_mobility(mobility_model_type_, true, temperature_, Nd_minus_Na_[i], 0.0Q, mu_n_[i]);
            mu_p_eff[i] = evaluate_mobility(mobility_model_type_, false, temperature_, 0.0Q, Nd_minus_Na_[i], mu_p_[i]);
        }
    }

    // Build Newton options with transient (backward-Euler) settings.
    //
    // The transient is driven by the fully-coupled Newton solver with the
    // corrected BE term (audit §17).  Each time step solves the coupled
    // Poisson + carrier system with the BE pin (c-c_prev)/dt*dx in the carrier
    // residual (cell-integrated units, +dx/dt Jacobian diagonal).  The
    // operator-split Gummel alternative 2-cycles on the perturbed state
    // (Poisson-continuity feedback limit cycle), so full Newton — which
    // couples all three blocks in one solve — is the robust choice despite
    // the wide Jacobian dynamic range (handled by row equilibration in
    // NewtonSolver).  See §17.
    //
    // The convergence tolerance is loose (1e-3): a stiff BE step only moves
    // the carriers by ~dt/tau ~ 1% per step, so a 0.1% residual is ample.
    // The old |F|/(|x|+1) test false-converged at iter 0 (dominated by
    // |x|~n~1e22); the Newton solver now uses |F|/|F0| (scale-invariant).
    NewtonOptions nopt;
    nopt.max_iter = std::max(max_iter_, (size_t)60);
    nopt.tol = 1e-3Q;               // A stiff BE step only moves carriers by
                                    // ~dt/tau ~ 1% per step, so 0.1% residual is
                                    // ample.  The 2-block (n,p) frozen-phi system
                                    // is diagonal-dominant; Newton reaches
                                    // |F|/|F0| ~ 1e-3 in 2-3 iters then the
                                    // line-search stagnates on the last 0.1%
                                    // (the equilibrated norm trades a large
                                    // residual for a small one), so 1e-3 is the
                                    // natural cutoff.  See audit §17.
    nopt.abs_tol = 1e-18Q;
    nopt.verbose = false;
    nopt.use_log_damping = true;    // exponential carrier update (n*exp(dn/n)).
                                    // The frozen-phi 2-block Jacobian is
                                    // well-conditioned, but the Newton DIRECTION
                                    // can still be large in absolute terms
                                    // (dx[n]~1e9 for n~1e22, a 1e-7 relative
                                    // change) because the SG flux coupling
                                    // amplifies it at neighbours.  A linear
                                    // update applies that 1e9 directly and the
                                    // flux balance at distant nodes explodes
                                    // (22x residual growth => line-search stall).
                                    // The exponential update turns dx into a
                                    // relative step (exp(dx/n)-1 ~ dx/n) so the
                                    // 1e-9 relative change is applied safely.
                                    // Combined with the L-inf line-search merit
                                    // this converges.  See audit §17.
    nopt.damping = 1.0Q;
    nopt.use_line_search = true;    // full Newton step overshoots on the stiff BE
                                    // system (dp ~ p); line search tames it while
                                    // keeping the quadratic-convergence basin.
    nopt.min_damping = 1e-6Q;
    nopt.line_search_max = 30;
    nopt.jacobian_reuse_threshold = newton_jacobian_reuse_threshold_;
    nopt.use_log_space = newton_use_log_space_;
    nopt.temperature = temperature_;
    nopt.statistics_type = statistics_type_;
    nopt.linear_solver = SolverType::DENSE_DIRECT;  // row-equilibrated in NewtonSolver
    nopt.transient_enabled = true;
    nopt.transient_dt = transient_dt_;
    nopt.freeze_phi = true;         // frozen-phi 2-block BE transient (audit §17)

    // Freeze the majority carrier in uniformly-doped (single-type) devices.
    // In an n-type slab the majority carrier n≈Nd is pinned by doping and the
    // BE term pins n=n_prev=Nd, so the electron continuity residual is pure
    // SG-flux cancellation noise (center*n~1e25 with ~1e25 cancellation).  A
    // 1e-16 relative perturbation adds ~1e9 of noise, which defeats Newton at
    // boundary-adjacent nodes.  Freezing n reduces the solve to a 1-block (p)
    // system that converges cleanly.  We detect "uniformly n-type" by checking
    // that every node has Nd-Na > 0 (and vice-versa for p-type).  Mixed
    // (pn-junction) devices keep both carriers active.  See audit §17.
    bool all_n_type = true, all_p_type = true;
    for (size_t i = 0; i < N; ++i) {
        if (Nd_minus_Na_[i] < 0.0Q) all_n_type = false;
        if (Nd_minus_Na_[i] > 0.0Q) all_p_type = false;
    }
    if (all_n_type) {
        nopt.freeze_n = true;
        if (nopt.verbose) std::cout << "[transient] uniformly n-type => freeze_n\n";
    } else if (all_p_type) {
        nopt.freeze_p = true;
        if (nopt.verbose) std::cout << "[transient] uniformly p-type => freeze_p\n";
    }

    // Initialize from equilibrium or initial guess
    std::vector<real_t> phi(N, 0.0Q), n(N, 0.0Q), p(N, 0.0Q);
    if (has_initial_guess_) {
        phi = init_phi_; n = init_n_; p = init_p_;
    } else {
        for (size_t i = 0; i < N; ++i) {
            real_t C = Nd_minus_Na_[i];
            real_t half_C = C / 2.0Q;
            real_t disc = sqrt_q(ni[i] * ni[i] + half_C * half_C);
            real_t n_eq, p_eq;
            if (C >= 0.0Q) { n_eq = disc + half_C; p_eq = (n_eq > EPSILON) ? (ni[i] * ni[i] / n_eq) : 0.0Q; }
            else { p_eq = disc - half_C; n_eq = (p_eq > EPSILON) ? (ni[i] * ni[i] / p_eq) : 0.0Q; }
            n[i] = n_eq; p[i] = p_eq;
            if (n_eq > EPSILON) phi[i] = VT_ * log_q(n_eq / ni[i]);
            else if (p_eq > EPSILON) phi[i] = -VT_ * log_q(p_eq / ni[i]);
        }
    }
    for (const auto& [idx, val] : n_bc_) n[idx] = val;
    for (const auto& [idx, val] : p_bc_) p[idx] = val;
    for (const auto& [idx, val] : phi_bc_) phi[idx] = val;

    // Store previous time step carriers for backward Euler
    std::vector<real_t> n_prev = n, p_prev = p;

    // Time stepping: Backward Euler
    real_t dt = transient_dt_;
    real_t t_final = transient_t_final_;
    size_t n_steps = static_cast<size_t>(t_final / dt) + 1;

    for (size_t step = 0; step < n_steps; ++step) {
        nopt.n_prev = n_prev;
        nopt.p_prev = p_prev;

        newton_ = NewtonSolver(g_, nopt);
        newton_.set_permittivity(eps_);
        newton_.set_mobility(mu_n_eff, mu_p_eff);
        newton_.set_doping(Nd_minus_Na_);
        newton_.set_recombination(tau_n_, tau_p_);
        newton_.set_optical_generation(G_opt_);
        newton_.set_effective_dos(Nc_, Nv_);
        newton_.set_bandgap(Eg_);
        newton_.set_thermal_voltage(VT_);
        newton_.set_phi_dirichlet(phi_bc_);
        newton_.set_electron_bc(n_bc_);
        newton_.set_hole_bc(p_bc_);

        bool ok = newton_.solve(phi, n, p);

        // Update previous carriers for next time step
        n_prev = n;
        p_prev = p;

        // Record snapshot
        SimulationResult snap;
        snap.phi = phi;
        snap.n = n;
        snap.p = p;
        snap.converged = ok;
        snap.iterations = newton_.residuals().size();
        // Compute E-field
        poisson_.set_dirichlet(phi_bc_);
        poisson_.set_permittivity(eps_);
        poisson_.compute_electric_field(phi, snap.Ex, snap.Ey, snap.Ez);
        history.push_back(std::move(snap));

        if (!ok) break;
    }

    return history;
}

} // namespace tcad
