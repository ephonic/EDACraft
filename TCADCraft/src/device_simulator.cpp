#include "device_simulator.h"
#include "statistics.h"
#include <algorithm>
#include <iostream>
#include <cmath>
#include <string>
#include <cstdlib>

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
    charge_volume_fraction_.assign(N, 1.0Q);
    G_opt_.assign(N, 0.0Q);
    Nc_.assign(N, 2.8e19Q);   // Default Si conduction-band DOS [cm^-3]
    Nv_.assign(N, 1.04e19Q);  // Default Si valence-band DOS [cm^-3]
    Eg_.assign(N, 1.12Q);     // Default Si bandgap [eV]
    dg_.set_effective_dos(Nc_, Nv_);
    thermal_conductivity_.assign(N, 150.0Q); // Default: Silicon thermal conductivity [W/(m*K)]
}

namespace {
bool finite_vector(const std::vector<real_t>& values) {
    return std::all_of(values.begin(), values.end(), [](real_t value) {
        return std::isfinite((double)value);
    });
}

bool auto_petsc_enabled() {
    const char* value = std::getenv("TCADCRAFT_AUTO_PETSC");
    return value && std::string(value) == "1";
}

void validate_boundary_values(const std::map<size_t, real_t>& bc,
                              size_t node_count, const char* name,
                              bool require_nonnegative) {
    for (const auto& [node, value] : bc) {
        if (node >= node_count)
            throw std::out_of_range(std::string(name) +
                                    " boundary node is outside the grid");
        if (!std::isfinite((double)value) ||
            (require_nonnegative && value < 0.0Q))
            throw std::invalid_argument(std::string(name) +
                                        " boundary value must be finite" +
                                        (require_nonnegative
                                             ? " and nonnegative" : ""));
    }
}

void validate_positions(const std::vector<real_t>& positions, size_t expected,
                        const char* axis) {
    if (positions.size() != expected)
        throw std::invalid_argument(std::string(axis) + " position count mismatch");
    for (size_t i = 1; i < positions.size(); ++i) {
        if (!(positions[i] > positions[i - 1]))
            throw std::invalid_argument(std::string(axis) +
                                        " positions must be strictly increasing");
    }
}
}  // namespace

void DeviceSimulator::set_grid_z(const std::vector<real_t>& z_pos) {
    validate_positions(z_pos, g_.nz, "z");
    g_.zx = z_pos;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    // Grid-owning helpers store Grid3D by value. Refresh them immediately so
    // final E/J/Q post-processing uses exactly the mesh used by the nonlinear
    // solve (Gummel/Newton are rebuilt from g_ inside solve()).
    poisson_ = PoissonSolver(g_);
    poisson_.set_permittivity(eps_);
    poisson_.set_doping(Nd_minus_Na_);
    poisson_.set_charge_volume_fraction(charge_volume_fraction_);
    poisson_.set_dirichlet(phi_bc_);
    dg_ = DensityGradient(g_);
    dg_.set_coefficients(dg_bn_, dg_bp_);
    dg_.set_silicon_multivalley(dg_silicon_multivalley_, dg_silicon_ml_,
                                dg_silicon_mt_, dg_silicon_subbands_);
    dg_.set_interface_distance_factor(dg_interface_distance_factor_);
    dg_.set_potential_form(dg_potential_form_enabled_);
    dg_.set_effective_dos(Nc_, Nv_);
    dg_.set_step_boundary(
        dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
        dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
        dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
        dg_step_h_theta_);
}

void DeviceSimulator::set_grid_x(const std::vector<real_t>& x_pos) {
    validate_positions(x_pos, g_.nx, "x");
    g_.xx = x_pos;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    poisson_ = PoissonSolver(g_);
    poisson_.set_permittivity(eps_);
    poisson_.set_doping(Nd_minus_Na_);
    poisson_.set_charge_volume_fraction(charge_volume_fraction_);
    poisson_.set_dirichlet(phi_bc_);
    dg_ = DensityGradient(g_);
    dg_.set_coefficients(dg_bn_, dg_bp_);
    dg_.set_silicon_multivalley(dg_silicon_multivalley_, dg_silicon_ml_,
                                dg_silicon_mt_, dg_silicon_subbands_);
    dg_.set_interface_distance_factor(dg_interface_distance_factor_);
    dg_.set_potential_form(dg_potential_form_enabled_);
    dg_.set_effective_dos(Nc_, Nv_);
    dg_.set_step_boundary(
        dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
        dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
        dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
        dg_step_h_theta_);
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
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
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

void DeviceSimulator::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("charge volume fraction size mismatch");
    for (real_t value : fraction) {
        if (value < 0.0Q || value > 1.0Q)
            throw std::invalid_argument(
                "charge volume fraction must be in [0,1]");
    }
    charge_volume_fraction_ = fraction;
    poisson_.set_charge_volume_fraction(charge_volume_fraction_);
}

void DeviceSimulator::set_optical_generation(const std::vector<real_t>& G_opt) {
    if (G_opt.size() != g_.npts()) throw std::invalid_argument("optical generation size mismatch");
    G_opt_ = G_opt;
    gummel_.set_optical_generation(G_opt_);
}

void DeviceSimulator::set_btbt_weight(const std::vector<real_t>& weight) {
    if (!weight.empty() && weight.size() != g_.npts()) {
        throw std::invalid_argument("BTBT weight size mismatch");
    }
    if (!finite_vector(weight)) {
        throw std::invalid_argument("BTBT weight values must be finite");
    }
    btbt_weight_ = weight;
    gummel_.set_btbt_weight(btbt_weight_);
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
    validate_boundary_values(bc, g_.npts(), "potential", false);
    for (const auto& kv : bc) {
        phi_bc_[kv.first] = kv.second;
    }
    poisson_.set_dirichlet(phi_bc_);
}

void DeviceSimulator::set_electron_bc(const std::map<size_t, real_t>& bc) {
    validate_boundary_values(bc, g_.npts(), "electron", true);
    for (const auto& kv : bc) {
        n_bc_[kv.first] = kv.second;
    }
    gummel_.set_electron_bc(n_bc_);
}

void DeviceSimulator::set_hole_bc(const std::map<size_t, real_t>& bc) {
    validate_boundary_values(bc, g_.npts(), "hole", true);
    for (const auto& kv : bc) {
        p_bc_[kv.first] = kv.second;
    }
    gummel_.set_hole_bc(p_bc_);
}

void DeviceSimulator::set_quantum_enabled(bool enable) {
    if (quantum_enabled_ != enable) {
        dg_transport_Qn_.clear();
        dg_transport_Qp_.clear();
    }
    quantum_enabled_ = enable;
}

void DeviceSimulator::set_density_gradient_coefficients(real_t bn, real_t bp) {
    if (!(bn > 0.0Q) || !(bp > 0.0Q) ||
        !std::isfinite((double)bn) || !std::isfinite((double)bp))
        throw std::invalid_argument("density-gradient coefficients must be positive");
    dg_bn_ = bn;
    dg_bp_ = bp;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    dg_.set_coefficients(bn, bp);
}

void DeviceSimulator::set_density_gradient_silicon_multivalley(
    bool enable, real_t longitudinal_mass, real_t transverse_mass,
    size_t subbands) {
    if (!(longitudinal_mass > 0.0Q) || !(transverse_mass > 0.0Q) ||
        !std::isfinite((double)longitudinal_mass) ||
        !std::isfinite((double)transverse_mass))
        throw std::invalid_argument("silicon DG effective masses must be positive");
    if (subbands < 1 || subbands > 32)
        throw std::invalid_argument("silicon DG subbands must be in [1,32]");
    dg_silicon_multivalley_ = enable;
    dg_silicon_ml_ = longitudinal_mass;
    dg_silicon_mt_ = transverse_mass;
    dg_silicon_subbands_ = subbands;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    dg_.set_silicon_multivalley(enable, longitudinal_mass, transverse_mass,
                                subbands);
}

void DeviceSimulator::set_density_gradient_interface_distance_factor(
    real_t factor) {
    if (!(factor > 0.0Q) || !std::isfinite((double)factor))
        throw std::invalid_argument(
            "density-gradient interface distance factor must be positive");
    dg_interface_distance_factor_ = factor;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    dg_.set_interface_distance_factor(factor);
}

void DeviceSimulator::set_density_gradient_potential_form(bool enable) {
    if (dg_potential_form_enabled_ != enable) {
        dg_transport_Qn_.clear();
        dg_transport_Qp_.clear();
    }
    dg_potential_form_enabled_ = enable;
    dg_.set_potential_form(enable);
}

void DeviceSimulator::set_density_gradient_step_boundary(
    bool enable, real_t electron_barrier_eV, real_t hole_barrier_eV,
    real_t electron_barrier_mass, real_t hole_barrier_mass,
    real_t electron_gamma, real_t hole_gamma,
    real_t electron_theta, real_t hole_theta) {
    const real_t values[] = {
        electron_barrier_eV, hole_barrier_eV,
        electron_barrier_mass, hole_barrier_mass,
        electron_gamma, hole_gamma, electron_theta, hole_theta};
    for (real_t value : values) {
        if (!(value > 0.0Q) || !std::isfinite((double)value))
            throw std::invalid_argument(
                "density-gradient step-boundary parameters must be positive");
    }
    dg_step_boundary_enabled_ = enable;
    dg_step_e_barrier_eV_ = electron_barrier_eV;
    dg_step_h_barrier_eV_ = hole_barrier_eV;
    dg_step_e_mass_ = electron_barrier_mass;
    dg_step_h_mass_ = hole_barrier_mass;
    dg_step_e_gamma_ = electron_gamma;
    dg_step_h_gamma_ = hole_gamma;
    dg_step_e_theta_ = electron_theta;
    dg_step_h_theta_ = hole_theta;
    dg_transport_Qn_.clear();
    dg_transport_Qp_.clear();
    dg_.set_step_boundary(enable, electron_barrier_eV, hole_barrier_eV,
                          electron_barrier_mass, hole_barrier_mass,
                          electron_gamma, hole_gamma,
                          electron_theta, hole_theta);
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

void DeviceSimulator::set_btbt_params(real_t A, real_t B, real_t D) {
    btbt_A_ = A;
    btbt_B_ = B;
    btbt_D_ = D;
}

void DeviceSimulator::set_btbt_field_mode(int mode) {
    set_btbt_field_options(mode, btbt_field_cap_);
}

void DeviceSimulator::set_btbt_field_options(int mode, real_t cap) {
    set_btbt_field_shape(mode, cap, btbt_field_alpha_, btbt_field_ref_);
}

void DeviceSimulator::set_btbt_field_shape(int mode, real_t cap,
                                           real_t alpha, real_t ref) {
    if (mode < 0 || mode > 3) {
        mode = 0;
    }
    btbt_field_mode_ = mode;
    btbt_field_cap_ = cap > 0.0Q ? cap : 0.0Q;
    btbt_field_alpha_ = std::isfinite((double)alpha) ? alpha : 0.0Q;
    btbt_field_ref_ = ref > 0.0Q ? ref : 1.0e8Q;
}

void DeviceSimulator::set_btbt_continuity_scale(real_t scale) {
    if (!std::isfinite((double)scale) || scale < 0.0Q) {
        throw std::invalid_argument("BTBT continuity scale must be finite and non-negative");
    }
    btbt_continuity_scale_ = scale;
}

void DeviceSimulator::set_btbt_use_nonlocal(bool enable) {
    btbt_use_nonlocal_ = enable;
}

void DeviceSimulator::set_btbt_nonlocal_params(real_t tunnel_path_frac, size_t wkb_npts) {
    if (!std::isfinite((double)tunnel_path_frac)) {
        throw std::invalid_argument("BTBT tunnel_path_frac must be finite");
    }
    if (wkb_npts < 2) {
        throw std::invalid_argument("BTBT wkb_npts must be >= 2");
    }
    btbt_tunnel_path_frac_ = tunnel_path_frac;
    btbt_wkb_npts_ = wkb_npts;
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

void DeviceSimulator::set_auger_enabled(bool enable) {
    auger_enabled_ = enable;
}

void DeviceSimulator::set_auger_params(real_t Cn, real_t Cp) {
    auger_Cn_ = Cn;
    auger_Cp_ = Cp;
}

void DeviceSimulator::set_ohmic_contacts(const std::set<size_t>& nodes,
                                         const std::map<size_t, real_t>& EFn,
                                         const std::map<size_t, real_t>& EFp,
                                         real_t ni) {
    ohmic_nodes_ = nodes;
    ohmic_EFn_ = EFn;
    ohmic_EFp_ = EFp;
    ohmic_ni_ = ni;
}

void DeviceSimulator::clear_ohmic_contacts() {
    ohmic_nodes_.clear();
}

void DeviceSimulator::solve_equilibrium() {
    // Poisson-Boltzmann equilibrium: iteratively solve Poisson with
    // n=ni*exp(phi/VT), p=ni*exp(-phi/VT) until convergence.
    // This mimics Sentaurus's Coupled(Iterations=100){ Poisson } which
    // finds the equilibrium potential WITHOUT continuity (no current).
    // The result is used as initial guess for coupled Newton — this
    // initialization sequence puts Newton in the "on-state" basin of
    // attraction for lightly-doped devices (DG FinFET).
    const size_t N = g_.npts();

    // Build a Poisson solver for equilibrium
    GummelOptions eq_opt;
    eq_opt.max_iter = 200;
    eq_opt.poisson_tol = 1e-8Q;
    eq_opt.continuity_tol = 1e-8Q;
    eq_opt.VT = VT_;
    eq_opt.statistics_type = statistics_type_;
    eq_opt.poisson_solver = (N > 2000)
        ? (auto_petsc_enabled() ? SolverType::PETSC : SolverType::BICGSTAB_ILU0)
        : SolverType::DENSE_DIRECT;
    eq_opt.continuity_solver = eq_opt.poisson_solver;

    GummelSolver eq_gummel(g_, eq_opt);
    eq_gummel.set_mobility(mu_n_, mu_p_);
    eq_gummel.set_doping(Nd_minus_Na_);
    eq_gummel.set_recombination(tau_n_, tau_p_);
    eq_gummel.set_effective_dos(Nc_, Nv_);
    eq_gummel.set_bandgap(Eg_);
    eq_gummel.set_permittivity(eps_);
    eq_gummel.set_poisson_dirichlet(phi_bc_);
    eq_gummel.set_electron_bc(n_bc_);
    eq_gummel.set_hole_bc(p_bc_);

    // Initial guess: uniform Boltzmann from doping
    std::vector<real_t> phi_eq(N, 0.0Q), n_eq(N), p_eq(N);
    for (size_t i = 0; i < N; ++i) {
        real_t ni_local = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
        real_t net = Nd_minus_Na_[i];
        if (net > 0) {
            n_eq[i] = net;
            p_eq[i] = ni_local * ni_local / net;
            phi_eq[i] = VT_ * log_q(net / ni_local);
        } else if (net < 0) {
            p_eq[i] = -net;
            n_eq[i] = ni_local * ni_local / (-net);
            phi_eq[i] = -VT_ * log_q((-net) / ni_local);
        } else {
            n_eq[i] = ni_local;
            p_eq[i] = ni_local;
        }
    }

    // Poisson-Boltzmann iteration: solve Poisson, update n/p from Boltzmann
    // relation n=ni*exp(phi/VT), p=ni*exp(-phi/VT).  This is the Sentaurus
    // Coupled{Poisson} mode — carrier densities FOLLOW the potential (no
    // current), so a channel node near S/D potential gets n~1e18 (on-state).
    // This is DIFFERENT from charge-neutrality which gives n~ni regardless
    // of phi.
    for (int iter = 0; iter < 100; ++iter) {
        // Solve Poisson with current n, p
        eq_gummel.recompute_poisson(phi_eq, n_eq, p_eq);

        // Update n, p from new phi using Boltzmann relation
        real_t max_dphi = 0.0Q;
        for (size_t i = 0; i < N; ++i) {
            real_t ni_local = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
            real_t phi_new = phi_eq[i];
            real_t arg_n = phi_new / VT_;
            // Clamp to prevent overflow
            if (arg_n > 50.0Q) arg_n = 50.0Q;
            if (arg_n < -50.0Q) arg_n = -50.0Q;
            real_t arg_p = -phi_new / VT_;
            if (arg_p > 50.0Q) arg_p = 50.0Q;
            if (arg_p < -50.0Q) arg_p = -50.0Q;
            real_t n_new = ni_local * exp_q(arg_n);
            real_t p_new = ni_local * exp_q(arg_p);
            // Ensure minimum density
            if (n_new < 1.0Q) n_new = 1.0Q;
            if (p_new < 1.0Q) p_new = 1.0Q;
            n_eq[i] = n_new;
            p_eq[i] = p_new;
        }

        if (max_dphi < 1e-10Q) {
            std::cout << "Equilibrium converged in " << iter + 1 << " iterations.\n";
            break;
        }
    }

    // Store as initial guess
    init_phi_ = phi_eq;
    init_n_ = n_eq;
    init_p_ = p_eq;
    has_initial_guess_ = true;
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

void DeviceSimulator::set_ferroelectric_depol(real_t eps_fe) {
    fe_eps_fe_ = eps_fe;   // comments2.docx P3: depol field
}

void DeviceSimulator::set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt) {
    fe_nls_tau0_ = tau0;   // P3: Merz tau(E) = tau0*exp(E0/|E|)
    fe_nls_E0_ = E0;
    fe_nls_dt_ = dt;
}

void DeviceSimulator::set_ferroelectric_polar_axis(int axis) {
    // P0-1: polar axis 0 = x, 1 = y, 2 = z; clamped to the valid range.
    if (axis < 0) axis = 0;
    if (axis > 2) axis = 2;
    fe_polar_axis_ = axis;
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
    leak_fn_polarity_enabled_ = false;
    leak_E_floor_ = E_floor;
    leak_sigma_cap_ = sigma_cap;
    leak_enabled_ = true;
}

void DeviceSimulator::set_leakage_fn_polarity(real_t C_positive,
                                               real_t B_positive,
                                               real_t C_negative,
                                               real_t B_negative) {
    if (!std::isfinite((double)C_positive) ||
        !std::isfinite((double)B_positive) ||
        !std::isfinite((double)C_negative) ||
        !std::isfinite((double)B_negative) ||
        C_positive < 0.0Q || B_positive < 0.0Q ||
        C_negative < 0.0Q || B_negative < 0.0Q)
        throw std::invalid_argument(
            "FN polarity coefficients must be finite and nonnegative");
    leak_C_fn_positive_ = C_positive;
    leak_B_fn_positive_ = B_positive;
    leak_C_fn_negative_ = C_negative;
    leak_B_fn_negative_ = B_negative;
    leak_fn_polarity_enabled_ = true;
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
    dg_.set_effective_dos(Nc_, Nv_);
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
    // A cycle-mean/frozen state must respect the requested accuracy.  The
    // historical fixed 1e-3 gate silently accepted four orders less accuracy
    // than a tol=1e-7 quantum run and produced bias-to-bias current jumps.
    opt.frozen_residual_gate = std::min(
        std::max(100.0Q * tol_, 1.0e-8Q), 1.0e-4Q);
    opt.enable_quantum = quantum_enabled_;
    // The density-gradient fixed-point map is substantially stiffer than
    // classical DD in ultra-thin films. Keep the outer carrier update
    // contractive; the final undamped continuity polish still returns the
    // same discrete solution once the coupled state has converged.
    if (quantum_enabled_) opt.cont_damping = 0.2Q;
    opt.VT = VT_;
    // Auto-switch the public DENSE_DIRECT default before the quad-precision
    // O(n^3) fallback becomes the dominant cost.  A 16x9x4 MOS mesh has only
    // 576 nodes but already needs several minutes for a four-point sweep when
    // its 3D bandwidth prevents the portable band solver from being used.
    // PETSc/SuperLU (or the portable sparse fallback) is both direct enough
    // for the nonlinear tolerance and orders of magnitude faster there.
    constexpr size_t dense_direct_node_limit = 256;
    if (N > dense_direct_node_limit) {
#ifdef TCAD_USE_PETSC
        if (poisson_solver_type_ == SolverType::DENSE_DIRECT)
            opt.poisson_solver = auto_petsc_enabled()
                ? SolverType::PETSC : SolverType::BICGSTAB_ILU0;
        else
            opt.poisson_solver = poisson_solver_type_;
        if (continuity_solver_type_ == SolverType::DENSE_DIRECT)
            opt.continuity_solver = auto_petsc_enabled()
                ? SolverType::PETSC : SolverType::BICGSTAB_ILU0;
        else
            opt.continuity_solver = continuity_solver_type_;
#else
        const size_t structured_bandwidth = std::max(
            (size_t)1,
            std::max(g_.ny > 1 ? g_.nx : (size_t)1,
                     g_.nz > 1 ? g_.nx * g_.ny : (size_t)1));
        const bool portable_narrow_band = structured_bandwidth <= 128 &&
            4 * (2 * structured_bandwidth + 1) < N;
        if (poisson_solver_type_ == SolverType::DENSE_DIRECT)
            opt.poisson_solver = portable_narrow_band
                ? SolverType::DENSE_DIRECT : SolverType::GMRES;
        else
            opt.poisson_solver = poisson_solver_type_;
        if (continuity_solver_type_ == SolverType::DENSE_DIRECT)
            opt.continuity_solver = portable_narrow_band
                ? SolverType::DENSE_DIRECT : SolverType::GMRES;
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
    opt.btbt.field_mode = btbt_field_mode_;
    opt.btbt.field_cap = btbt_field_cap_;
    opt.btbt.field_alpha = btbt_field_alpha_;
    opt.btbt.field_ref = btbt_field_ref_;
    opt.btbt.continuity_scale = btbt_continuity_scale_;
    opt.btbt.use_nonlocal = btbt_use_nonlocal_;
    opt.btbt.tunnel_path_frac = btbt_tunnel_path_frac_;
    opt.btbt.wkb_npts = btbt_wkb_npts_;
    // Impact ionization parameters
    opt.ii.enabled = ii_enabled_;
    opt.ii.A_n = ii_A_n_;
    opt.ii.B_n = ii_B_n_;
    opt.ii.A_p = ii_A_p_;
    opt.ii.B_p = ii_B_p_;
    // Auger recombination
    opt.auger.enabled = auger_enabled_;
    opt.auger.Cn = auger_Cn_;
    opt.auger.Cp = auger_Cp_;
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
    opt.ferro.eps_fe = fe_eps_fe_;   // comments2.docx P3: depol permittivity
    opt.ferro.nls_tau0 = fe_nls_tau0_;   // P3: NLS Merz parameters
    opt.ferro.nls_E0 = fe_nls_E0_;
    opt.ferro.nls_dt = fe_nls_dt_;
    opt.ferro.polar_axis = fe_polar_axis_;   // P0-1: FE polar axis (0=x,1=y,2=z)
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

    // Records whether the accepted, unmodified carrier state came from
    // Gummel.  Its density-gradient potential is under-relaxed and therefore
    // cannot be reconstructed exactly from the returned n/p alone.
    bool accepted_gummel_state = false;

    if (use_newton_) {
        // Under Fermi-Dirac statistics the potential-form DG branch owns an
        // independent Q PDE that is not present in the three-block Newton
        // system.  Every other DG branch is represented directly by Q(n,p)
        // in Newton and can use it as a genuine fixed-point-cycle rescue.
        const bool independent_dg_potential_pde =
            quantum_enabled_ && dg_potential_form_enabled_ &&
            statistics_type_ == StatisticsType::FERMI_DIRAC;
        // Hybrid: Gummel first for robust initial guess, then Newton for fast
        // convergence.  The warm-up runs to convergence normally, but exits
        // EARLY at the first detected limit cycle: a cycle means the
        // fixed-point map has an unstable fixed point (Newton's job), and
        // grinding retries scrubs the state back and forth, damaging the
        // initial guess.  Normal contracting warm-up progress is never
        // interrupted.  (issues0719 P0-3 follow-up.)
        GummelOptions warm_opt = opt;
        // Complete classical/Fermi-potential stabilisation when possible.
        // For a Newton-representable quantum branch, however, grinding a
        // detected scalar DG cycle for hundreds of expensive iterations only
        // revisits the same plateau.  Hand that finite state to Newton.  Keep
        // the classical PN behaviour unchanged because an early cycle-mean
        // hand-off there degraded Newton/Gummel KCL agreement.
        warm_opt.exit_on_limit_cycle =
            quantum_enabled_ && !independent_dg_potential_pde;
        gummel_ = GummelSolver(g_, warm_opt);
        gummel_.set_density_gradient_coefficients(dg_bn_, dg_bp_);
        gummel_.set_density_gradient_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        gummel_.set_density_gradient_interface_distance_factor(
            dg_interface_distance_factor_);
        gummel_.set_density_gradient_potential_form(
            dg_potential_form_enabled_);
        gummel_.set_density_gradient_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        if (dg_potential_form_enabled_ &&
            dg_transport_Qn_.size() == N && dg_transport_Qp_.size() == N) {
            gummel_.set_transport_quantum_state(
                dg_transport_Qn_, dg_transport_Qp_);
        }
        gummel_.set_mobility(mu_n_eff, mu_p_eff);
        gummel_.set_doping(Nd_minus_Na_);
        gummel_.set_charge_volume_fraction(charge_volume_fraction_);
        gummel_.set_recombination(tau_n_, tau_p_);
        gummel_.set_optical_generation(G_opt_);
        gummel_.set_btbt_weight(btbt_weight_);
        gummel_.set_effective_dos(Nc_, Nv_);
        gummel_.set_bandgap(Eg_);
        gummel_.set_electron_bc(n_bc_);
        gummel_.set_hole_bc(p_bc_);
        gummel_.set_poisson_dirichlet(phi_bc_);
        // Ohmic contacts: pass to Gummel's Poisson solver
        if (!ohmic_nodes_.empty()) {
            gummel_.set_ohmic_contacts(ohmic_nodes_, ohmic_EFn_, ohmic_EFp_, ohmic_ni_);
        }
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
            if (fe_model_ == 1 || fe_model_ == 3) {
                const size_t state_size = (fe_model_ == 3) ? 2 * N : N;
                if (fe_play_state_.size() != state_size)
                    fe_play_state_.assign(state_size, 0.0Q);
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
        // Newton-primary mode: skip Gummel warm-up entirely, go to Newton
        // directly from the initial guess.  Needed for lightly-doped 3D
        // devices (e.g. DG FinFET) where Gummel converges to the "off"
        // state but the physical solution is "on" (S/D injection fills body).
        // A skipped stage has not converged.  Initialising this to true made
        // newton_primary mode report success even when the primary Newton
        // solve stalled: res.converged below used (gummel_ok || newton_ok),
        // so the nonexistent Gummel warm-up masked a genuine Newton failure
        // and let a KCL-broken state seed the next bias point.
        bool gummel_ok = false;
        // Sentaurus equations (247) and (248) are algebraically identical
        // under Boltzmann statistics.  Only the Fermi-Dirac potential-form
        // branch introduces an independent Q PDE that the three-block
        // Newton solver does not carry.  Keying this decision on the public
        // potential-form flag alone disabled a mathematically valid Newton
        // rescue for the Boltzmann-equivalent density map and left refined
        // MOS sweeps trapped in a scalar DG fixed-point cycle.
        const std::vector<real_t> phi_before_gummel = res.phi;
        const std::vector<real_t> n_before_gummel = res.n;
        const std::vector<real_t> p_before_gummel = res.p;
        if (!newton_primary_ || independent_dg_potential_pde) {
            gummel_ok = gummel_.solve(res.phi, res.n, res.p);
        }
        // A failed warm-up may still provide a useful finite Newton seed, but
        // never pass a poisoned NaN/Inf state into the coupled solver.
        if (!gummel_ok &&
            (!finite_vector(res.phi) || !finite_vector(res.n) ||
             !finite_vector(res.p))) {
            res.phi = phi_before_gummel;
            res.n = n_before_gummel;
            res.p = p_before_gummel;
        }
        if (fe_enabled_) {
            fe_polarization_ = gummel_.fe_polarization();
            if (fe_model_ == 1 || fe_model_ == 3)
                fe_play_state_ = gummel_.fe_play_state();
        }
        size_t gummel_iters = gummel_.poisson_residuals().size();
        // Convergence-honesty diagnostics from the Gummel warm-up (P0-3).
        res.poisson_residual = gummel_.poisson_residual_final();
        res.quantum_residual = gummel_.quantum_residual_final();
        res.phi_frozen = gummel_.phi_was_frozen();

        // issues0719 P0-3 follow-up: ALWAYS attempt the Newton polish, even
        // when the Gummel warm-up stalled in a limit cycle.  A limit cycle
        // is precisely the failure mode a line-searched Newton finishes —
        // requiring full Gummel convergence first defeated the purpose of
        // the Gummel->Newton cascade (the MoS2 FeFET template cycles at the
        // inversion onset and never reached Newton).  The verdict stays
        // honest: res.converged reflects ONLY Newton's true residual test.
        {
            // Use Gummel solution as initial guess for Newton
            NewtonOptions nopt;
            // set_gummel_max_iter() controls the inexpensive block warm-up.
            // Reusing a 600-step quantum-Gummel budget here allowed a failed
            // quad-precision Newton rescue to burn several minutes before the
            // caller could apply its voltage-bisection fallback.  A coupled
            // Newton solve that has not converged in 60 iterations is stalled,
            // not under-budgeted; retain smaller caller limits but cap only
            // this rescue stage.
            nopt.max_iter = std::min(max_iter_, size_t{60});
            nopt.tol = (double)tol_;
            nopt.abs_tol = 1e-20Q;
            nopt.verbose = (getenv("TCAD_NEWTON_VERBOSE") != nullptr);
            nopt.damping = newton_damping_;
            nopt.min_damping = newton_min_damping_;
            nopt.use_line_search = newton_use_line_search_;
            nopt.line_search_max = newton_line_search_max_;
            nopt.use_log_damping = newton_use_log_damping_;
            // A true Newton-primary solve has no Gummel state to compress the
            // initial carrier correction.  In linear density variables that
            // first correction is routinely O(1e25), making even the quad
            // Jacobian effectively singular through flux cancellation.
            // Log-density is the mathematically equivalent positive
            // formulation and is required for a robust primary solve.
            nopt.use_log_space = newton_use_log_space_ || newton_primary_;
            nopt.jacobian_reuse_threshold = newton_jacobian_reuse_threshold_;
            nopt.enable_btbt = btbt_enabled_;
            nopt.enable_quantum = quantum_enabled_;
            nopt.btbt_A = btbt_A_;
            nopt.btbt_B = btbt_B_;
            nopt.btbt_D = btbt_D_;
            nopt.btbt_field_mode = btbt_field_mode_;
            nopt.btbt_field_cap = btbt_field_cap_;
            nopt.btbt_field_alpha = btbt_field_alpha_;
            nopt.btbt_field_ref = btbt_field_ref_;
            nopt.btbt_continuity_scale = btbt_continuity_scale_;
            nopt.enable_ii = ii_enabled_;
            nopt.ii_A_n = ii_A_n_;
            nopt.ii_B_n = ii_B_n_;
            nopt.ii_A_p = ii_A_p_;
            nopt.ii_B_p = ii_B_p_;
            nopt.enable_auger = auger_enabled_;
            nopt.auger_Cn = auger_Cn_;
            nopt.auger_Cp = auger_Cp_;
            nopt.temperature = temperature_;
            nopt.statistics_type = statistics_type_;
#ifdef TCAD_USE_PETSC
            // The coupled, two-sided-equilibrated Jacobian is sparse but can
            // remain strongly non-normal at material interfaces.  The legacy
            // IR_BICGSTAB path returned its best guess even when every inner
            // solve hit the iteration limit; Newton then accepted updates as
            // large as 1e11 in log-density space.  PETSc's sparse LU provides
            // a deterministic direction for this production path, while the
            // residual audit in NewtonSolver rejects any inaccurate solve.
            // Linear-density Newton can require corrections of order 1e25;
            // casting that tiny residual / huge solution cancellation to a
            // double-precision external factorisation loses all meaningful
            // backward accuracy.  Keep the quad direct path for small legacy
            // linear-space systems, and use PETSc for the bounded log-space
            // production formulation.
            nopt.linear_solver = nopt.use_log_space
                ? SolverType::PETSC
                : (N <= 256 ? SolverType::DENSE_DIRECT
                            : SolverType::IR_BICGSTAB);
#else
            // Without PETSc, requesting it silently no-ops the linear solve
            // (universal Newton stall on >2000-node problems).  Fall back to
            // GMRES (more robust than BiCGStab on the ill-conditioned Newton
            // Jacobian, where BiCGStab stagnates and silently returns garbage).
            nopt.linear_solver = (N > 2000) ? SolverType::GMRES : SolverType::DENSE_DIRECT;
#endif
            // C档: Newton freeze flags (isolated-continuity MMS).
            nopt.freeze_phi = newton_freeze_phi_;
            const real_t gummel_n_update =
                gummel_.electron_update_final();
            const real_t gummel_p_update = gummel_.hole_update_final();
            const bool gummel_n_settled = gummel_n_update >= 0.0Q &&
                gummel_n_update < tol_;
            const bool gummel_p_settled = gummel_p_update >= 0.0Q &&
                gummel_p_update < tol_;
            // In a quantum limit-cycle rescue, keep a single already-settled
            // minority block fixed while Newton closes the active carrier and
            // Poisson equations.  Updating that physically negligible block
            // excites a log-density near-null space (|du|~1e12) and pollutes
            // the coupled direction.  Freeze only when exactly one carrier
            // block has passed the same strict update gate; if both or neither
            // have settled, retain the full coupled system.
            const bool freeze_settled_n = quantum_enabled_ && !gummel_ok &&
                gummel_n_settled && !gummel_p_settled;
            const bool freeze_settled_p = quantum_enabled_ && !gummel_ok &&
                gummel_p_settled && !gummel_n_settled;
            nopt.freeze_n = newton_freeze_n_ || freeze_settled_n;
            nopt.freeze_p = newton_freeze_p_ || freeze_settled_p;
            newton_ = NewtonSolver(g_, nopt);
            newton_.set_density_gradient_coefficients(dg_bn_, dg_bp_);
            newton_.set_density_gradient_silicon_multivalley(
                dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
                dg_silicon_subbands_);
            newton_.set_density_gradient_interface_distance_factor(
                dg_interface_distance_factor_);
            newton_.set_density_gradient_step_boundary(
                dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
                dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
                dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
                dg_step_h_theta_);
            newton_.set_permittivity(eps_);
            newton_.set_edge_permittivity(
                edge_eps_x_plus_, edge_eps_x_minus_,
                edge_eps_y_plus_, edge_eps_y_minus_,
                edge_eps_z_plus_, edge_eps_z_minus_);
            newton_.set_mobility(mu_n_eff, mu_p_eff);
            newton_.set_doping(Nd_minus_Na_);
            newton_.set_charge_volume_fraction(charge_volume_fraction_);
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
            // DG semiconductor mask for Newton (same as Gummel)
            if (quantum_enabled_ && !mu_n_eff.empty()) {
                std::vector<char> semi(N, 0);
                for (size_t i = 0; i < N; ++i)
                    semi[i] = (mu_n_eff[i] > 1e-30Q || mu_p_eff[i] > 1e-30Q) ? 1 : 0;
                newton_.set_semiconductor_mask(semi);
            }
            // Pass Ohmic contacts to Newton
            if (!ohmic_nodes_.empty()) {
                newton_.set_ohmic_contacts(ohmic_nodes_, ohmic_EFn_, ohmic_EFp_, ohmic_ni_);
            }
            // ALWAYS attempt the Newton polish (2026-08 follow-up): the
            // Gummel warm-up's update-norm criterion does NOT imply a small
            // true coupled residual — at high injection a Gummel-"converged"
            // state can violate current continuity (div J >> qR), corrupting
            // terminal currents (KCL imbalance observed in the NPN BJT).
            // The Newton fixed point enforces the true residual.  To avoid
            // the regression warned about in fix0719 (a stalled Newton's
            // write-back degrading an earned Gummel state), the warm-up
            // state is saved and restored when the polish fails.
            // Newton polish ONLY when the Gummel warm-up did not converge (limit
            // cycle / high injection).  When Gummel converged, the state already
            // satisfies the update-norm criterion and a Newton polish just stalls
            // (line search makes no progress) then rolls back — pure waste
            // (~20s/solve on the 10k-node nMOS).  High-injection cases where
            // Gummel "converges" but violates continuity instead hit a Gummel
            // limit cycle (gummel_ok=false) and so still get the Newton rescue.
            std::vector<real_t> phi_w = res.phi, n_w = res.n, p_w = res.p;
            bool newton_ok = false;
            // Run Newton when Gummel didn't converge OR newton_primary mode.
            if ((!gummel_ok || newton_primary_) &&
                !independent_dg_potential_pde) {
                newton_ok = newton_.solve(res.phi, res.n, res.p);
                if (newton_ok &&
                    (!finite_vector(res.phi) || !finite_vector(res.n) ||
                     !finite_vector(res.p))) {
                    std::cerr << "Newton returned non-finite fields; "
                              << "rejecting convergence\n";
                    newton_ok = false;
                }
                // Newton already returns one coupled Poisson/electron/hole
                // state.  A former "polish" re-solved Poisson alone here,
                // changing phi without re-solving n and p.  The change can be
                // numerically tiny yet destroy drift/diffusion cancellation
                // at an abrupt high-doping junction, producing a KCL-broken
                // 1e6 A/m^2 local current from an equilibrium solution.
                if (!newton_ok) {
                    // Roll back: keep the earned Gummel (limit-cycle) state.
                    res.phi = phi_w; res.n = n_w; res.p = p_w;
                }
            }
            // Newton path (P0-3): no phi freezing applies; score the final
            // state against the Gummel Poisson operator (one re-assembly,
            // cheap) instead of the warm-up residual.
            res.phi_frozen = false;
            res.poisson_residual = gummel_.compute_poisson_residual(res.phi, res.n, res.p);
            // Newton evaluates Q directly from its current state and has no
            // independent lagged transport-Q variable.
            if (newton_ok) res.quantum_residual = 0.0Q;
            // Report total iterations (Gummel + Newton) for transparency
            res.iterations = gummel_iters + newton_.residuals().size();
            // Convergence verdict: a point is converged if ANY stage met
            // the true-residual criteria.  A converged Gummel warm-up earned
            // its verdict on the honest update-norm + polish path; a failed
            // warm-up (limit cycle) is rescued only by a genuinely converged
            // Newton polish.
            const bool finite_fields = finite_vector(res.phi) &&
                finite_vector(res.n) && finite_vector(res.p);
            res.converged = (gummel_ok || newton_ok) && finite_fields &&
                std::isfinite((double)res.poisson_residual);
            accepted_gummel_state = gummel_ok && !newton_ok;
            // Cross-bias transport Q is continuation state, not a diagnostic
            // scratch buffer.  Commit it only with the finite Gummel state
            // that earned the final verdict.  Persisting Q from a rejected
            // warm-up paired the next retry's restored n/p/phi with a failed
            // quantum iterate and made adaptive voltage bisection diverge.
            if (accepted_gummel_state && dg_potential_form_enabled_ &&
                gummel_.transport_quantum_n().size() == N &&
                gummel_.transport_quantum_p().size() == N) {
                dg_transport_Qn_ = gummel_.transport_quantum_n();
                dg_transport_Qp_ = gummel_.transport_quantum_p();
            }
            // NOTE: no second Gummel fallback pass — a fresh solve() would
            // advance the FE memory state (Preisach/NLS) a SECOND time for
            // the same bias point, breaking the one-state-advance-per-bias-
            // step semantics of the P0-2 fix.
            // In Newton-primary mode no Gummel warm-up was attempted, so do
            // not label the primary solver's status as a Gummel limit cycle.
            if (!gummel_ok && !newton_primary_) {
                if (res.converged) {
                    std::cout << "Gummel warm-up stalled (limit cycle); "
                              << "Newton polish converged (true residual="
                              << (double)res.poisson_residual << ")\n";
                } else {
                    std::cerr << "Gummel warm-up stalled AND Newton polish "
                              << "failed; point is non-converged\n";
                }
            }
        }
    } else {
        // Rebuild gummel solver with options (simplified)
        gummel_ = GummelSolver(g_, opt);
        gummel_.set_density_gradient_coefficients(dg_bn_, dg_bp_);
        gummel_.set_density_gradient_silicon_multivalley(
            dg_silicon_multivalley_, dg_silicon_ml_, dg_silicon_mt_,
            dg_silicon_subbands_);
        gummel_.set_density_gradient_interface_distance_factor(
            dg_interface_distance_factor_);
        gummel_.set_density_gradient_potential_form(
            dg_potential_form_enabled_);
        gummel_.set_density_gradient_step_boundary(
            dg_step_boundary_enabled_, dg_step_e_barrier_eV_,
            dg_step_h_barrier_eV_, dg_step_e_mass_, dg_step_h_mass_,
            dg_step_e_gamma_, dg_step_h_gamma_, dg_step_e_theta_,
            dg_step_h_theta_);
        if (dg_potential_form_enabled_ &&
            dg_transport_Qn_.size() == N && dg_transport_Qp_.size() == N) {
            gummel_.set_transport_quantum_state(
                dg_transport_Qn_, dg_transport_Qp_);
        }
        gummel_.set_mobility(mu_n_eff, mu_p_eff);
        gummel_.set_doping(Nd_minus_Na_);
        gummel_.set_charge_volume_fraction(charge_volume_fraction_);
        gummel_.set_recombination(tau_n_, tau_p_);
        gummel_.set_optical_generation(G_opt_);
        gummel_.set_btbt_weight(btbt_weight_);
        gummel_.set_effective_dos(Nc_, Nv_);
        gummel_.set_bandgap(Eg_);
        gummel_.set_electron_bc(n_bc_);
        gummel_.set_hole_bc(p_bc_);
        gummel_.set_poisson_dirichlet(phi_bc_);
        // Ohmic contacts: pass to Gummel's Poisson solver
        if (!ohmic_nodes_.empty()) {
            gummel_.set_ohmic_contacts(ohmic_nodes_, ohmic_EFn_, ohmic_EFp_, ohmic_ni_);
        }
        gummel_.set_permittivity(eps_);
        if (fe_enabled_) {
            if (!fe_polarization_init_) {
                fe_polarization_.assign(3 * N, 0.0Q);
                fe_polarization_init_ = true;
            }
            gummel_.set_fe_polarization(fe_polarization_);
            if (fe_model_ == 1 || fe_model_ == 3) {
                const size_t state_size = (fe_model_ == 3) ? 2 * N : N;
                if (fe_play_state_.size() != state_size)
                    fe_play_state_.assign(state_size, 0.0Q);
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
        if (res.converged && dg_potential_form_enabled_ &&
            gummel_.transport_quantum_n().size() == N &&
            gummel_.transport_quantum_p().size() == N) {
            dg_transport_Qn_ = gummel_.transport_quantum_n();
            dg_transport_Qp_ = gummel_.transport_quantum_p();
        }
        accepted_gummel_state = res.converged;
        if (fe_enabled_) {
            fe_polarization_ = gummel_.fe_polarization();
            if (fe_model_ == 1 || fe_model_ == 3)
                fe_play_state_ = gummel_.fe_play_state();
        }
        // Convergence-honesty diagnostics (P0-3).
        res.poisson_residual = gummel_.poisson_residual_final();
        res.quantum_residual = gummel_.quantum_residual_final();
        res.phi_frozen = gummel_.phi_was_frozen();
        res.iterations = gummel_.poisson_residuals().size();
    }

    // Final API invariant: no solver path may label a non-finite state as
    // converged.  This guard also covers the simplified non-hybrid branch.
    if (res.converged &&
        (!finite_vector(res.phi) || !finite_vector(res.n) ||
         !finite_vector(res.p) ||
         !std::isfinite((double)res.poisson_residual) ||
         (quantum_enabled_ &&
          !std::isfinite((double)res.quantum_residual)))) {
        std::cerr << "Non-finite converged state rejected\n";
        res.converged = false;
    }

    // --- Failure-path robustness: physical clamp on a non-converged state. ---
    // A diverged Gummel warm-up can leave non-finite / extreme carrier values
    // that produce garbage edge currents (1e10+ A/m^2) and corrupt downstream
    // IV comparison.  Clamp n, p (and phi) to physical bounds so that even a
    // non-converged point yields a usable, finite current instead of NaN/inf.
    // `!(x > lo)` is false for NaN, so NaN is replaced too.  Never apply this
    // to a converged state: a reverse-biased depletion region can legitimately
    // fall below 1 cm^-3, and changing that density after the coupled solve
    // breaks continuity/KCL.
    if (!res.converged) {
        const real_t CARR_FLOOR = 1e6Q;    // m^-3  (1 cm^-3)
        const real_t CARR_CEIL  = 1e28Q;   // m^-3  (1e22 cm^-3, above any doping)
        const real_t PHI_CEIL   = 50.0Q;   // V
        for (size_t i = 0; i < res.n.size(); ++i) {
            real_t nv = res.n[i];
            if (!(nv > CARR_FLOOR)) nv = CARR_FLOOR; else if (nv > CARR_CEIL) nv = CARR_CEIL;
            res.n[i] = nv;
            real_t pv = res.p[i];
            if (!(pv > CARR_FLOOR)) pv = CARR_FLOOR; else if (pv > CARR_CEIL) pv = CARR_CEIL;
            res.p[i] = pv;
        }
        for (size_t i = 0; i < res.phi.size(); ++i) {
            real_t ph = res.phi[i];
            if (!(ph > -PHI_CEIL)) ph = -PHI_CEIL; else if (ph > PHI_CEIL) ph = PHI_CEIL;
            res.phi[i] = ph;
        }
    }

    // DeviceSimulator's own poisson_ is used for post-processing (E-field)
    poisson_.set_dirichlet(phi_bc_);
    poisson_.set_permittivity(eps_);

    // Compute E-field even if not fully converged (results may still be useful)
    poisson_.compute_electric_field(res.phi, res.Ex, res.Ey, res.Ez);

    // Sentaurus-style mechanism diagnostic: expose the exact BTBT source
    // evaluated at the returned electrostatic state.  This is deliberately
    // recomputed after any Newton polish/rollback so it cannot describe a
    // stale intermediate Gummel iterate.
    gummel_.evaluate_btbt_generation(res.phi, res.G_btbt);
    gummel_.evaluate_impact_ionization(res.phi, res.n, res.p, res.G_ii);

    // Dielectric breakdown detection (M7b, audit §22).  After the field is
    // known, flag any masked dielectric node whose |E| exceeds its material
    // breakdown field E_bd.  The flip is IRREVERSIBLE (bd_state_ only goes 0->1)
    // and persists across solve() calls — a broken-down oxide node stays broken
    // down on subsequent (even lower) bias points, modelling the conductive
    // filament.  The leakage term itself is applied on the NEXT solve() via
    // set_breakdown_state above (this solve already assembled without it).
    const std::vector<char> bd_state_entered = bd_state_;
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
    const std::vector<char> bd_state_detected = bd_state_;
    bd_state_ = bd_state_entered;
    const std::vector<real_t>* transport_Qn = nullptr;
    const std::vector<real_t>* transport_Qp = nullptr;
    if (quantum_enabled_ && accepted_gummel_state) {
        transport_Qn = &gummel_.transport_quantum_n();
        transport_Qp = &gummel_.transport_quantum_p();
    }
    compute_edge_currents(res, res.phi, res.n, res.p,
                          transport_Qn, transport_Qp);

    // Thermal coupling (self-heating)
    if (thermal_coupling_enabled_ && res.converged) {
        res.temperature.assign(N, ambient_temperature_);
        
        // Compute carrier Joule heating from the *net SG current*, not
        // sigma*|E|^2.  In a junction at equilibrium drift and diffusion
        // cancel (J=0) despite a large built-in field; sigma*E^2 therefore
        // created spurious zero-bias heating.  Deposit each edge's J.E half
        // to either endpoint to preserve the finite-volume energy balance.
        std::vector<real_t> power(N, 0.0Q);
        // In a steady 1-D device div(Jn+Jp)=0, so the physically admissible
        // total-current field is constant.  Contact Dirichlet edges can carry
        // large cancellation spikes even when the coupled residual passes;
        // feeding those spikes into J.E creates a false contact hotspot.  Use
        // the robust L1 (median) conservative projection for heat deposition,
        // while leaving the raw edge currents untouched for explicit KCL QA.
        bool project_1d_current = (g_.ny == 1 && g_.nz == 1 && g_.nx > 4);
        real_t projected_Jx = 0.0Q;
        if (project_1d_current) {
            std::vector<real_t> interior_J;
            interior_J.reserve(g_.nx - 3);
            for (size_t i = 1; i + 2 < g_.nx; ++i)
                interior_J.push_back(res.Jn_x[i] + res.Jp_x[i]);
            auto middle = interior_J.begin() + interior_J.size() / 2;
            std::nth_element(interior_J.begin(), middle, interior_J.end());
            projected_Jx = *middle;
        }
        auto add_mobile_heat = [&](const std::vector<real_t>& Jn_ax,
                                   const std::vector<real_t>& Jp_ax,
                                   int axis, size_t stride,
                                   size_t n0, size_t n1, size_t n2) {
            for (size_t k = 0; k < n2; ++k)
                for (size_t j = 0; j < n1; ++j)
                    for (size_t i = 0; i < n0; ++i) {
                        size_t idx = g_.index(i, j, k);
                        size_t nbr = idx + stride;
                        real_t d = (axis == 0) ? g_.dx_edge(i)
                                 : (axis == 1) ? g_.dy_edge(j) : g_.dz_edge(k);
                        real_t E_axis = -(res.phi[nbr] - res.phi[idx]) / d;
                        real_t Jtotal = (project_1d_current && axis == 0)
                                      ? projected_Jx : Jn_ax[idx] + Jp_ax[idx];
                        real_t qdot = abs_q(Jtotal * E_axis);
                        power[idx] += 0.5Q * qdot;
                        power[nbr] += 0.5Q * qdot;
                    }
        };
        add_mobile_heat(res.Jn_x, res.Jp_x, 0, 1,
                        g_.nx - 1, g_.ny, g_.nz);
        add_mobile_heat(res.Jn_y, res.Jp_y, 1, g_.nx,
                        g_.nx, g_.ny - 1, g_.nz);
        add_mobile_heat(res.Jn_z, res.Jp_z, 2, g_.nx * g_.ny,
                        g_.nx, g_.ny, g_.nz - 1);

        // Add dielectric Joule heating J_leak·E, including PF/FN and the
        // explicit post-breakdown filament current. Edge power is split
        // equally between its two control volumes. The absolute value guards
        // against round-off/sign conventions while preserving non-negative
        // irreversible heat generation.
        auto add_leak_heat = [&](const std::vector<real_t>& J_ax,
                                 int axis, size_t stride,
                                 size_t n0, size_t n1, size_t n2) {
            for (size_t k = 0; k < n2; ++k)
                for (size_t j = 0; j < n1; ++j)
                    for (size_t i = 0; i < n0; ++i) {
                        size_t idx = g_.index(i, j, k);
                        size_t nbr = idx + stride;
                        if (J_ax[idx] == 0.0Q) continue;
                        real_t d = (axis == 0) ? g_.dx_edge(i)
                                 : (axis == 1) ? g_.dy_edge(j) : g_.dz_edge(k);
                        real_t E_axis = -(res.phi[nbr] - res.phi[idx]) / d;
                        real_t qdot = abs_q(J_ax[idx] * E_axis);
                        power[idx] += 0.5Q * qdot;
                        power[nbr] += 0.5Q * qdot;
                    }
        };
        add_leak_heat(res.Jleak_x, 0, 1,              g_.nx - 1, g_.ny,     g_.nz);
        add_leak_heat(res.Jleak_y, 1, g_.nx,          g_.nx,     g_.ny - 1, g_.nz);
        add_leak_heat(res.Jleak_z, 2, g_.nx * g_.ny,  g_.nx,     g_.ny,     g_.nz - 1);
        
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
#ifdef TCAD_USE_PETSC
        thermal_opt.type = SolverType::PETSC;
        thermal_opt.max_iter = 1;
#else
        // Never request an unavailable backend. The previous unconditional
        // PETSC enum made every electrothermal solve a no-op in the normal
        // non-PETSc Python build.
        thermal_opt.type = SolverType::DENSE_DIRECT;
        thermal_opt.max_iter = 5000;
#endif
        thermal_opt.tol = 1e-12Q;
        thermal_solver.set_solver_options(thermal_opt);
        thermal_solver.assemble_thermal(power);
        
        if (!thermal_solver.solve(res.temperature)) {
            std::cerr << "Thermal solve failed\n";
        }
    }

    // Reject KCL-broken electrothermal states with the same mixed
    // absolute/relative criterion as the Newton convergence guard. Relative
    // spread alone is ill-conditioned at equilibrium, while a power-only gate
    // previously admitted large non-conservative leakage currents.
    if (thermal_coupling_enabled_ && res.converged &&
        g_.ny == 1 && g_.nz == 1 && g_.nx > 2 &&
        !res.temperature.empty()) {
        real_t jmin = res.Jn_x[0] + res.Jp_x[0];
        real_t jmax = jmin;
        real_t jabs = abs_q(jmin);
        for (size_t i = 1; i + 1 < g_.nx; ++i) {
            real_t jt = res.Jn_x[i] + res.Jp_x[i];
            jmin = std::min(jmin, jt);
            jmax = std::max(jmax, jt);
            jabs = std::max(jabs, abs_q(jt));
        }
        real_t absolute_spread = jmax - jmin;
        real_t relative_spread = absolute_spread / (jabs + 1e-30Q);
        if (absolute_spread > 1.0e-8Q && relative_spread > 1.0e-2Q) {
            std::cerr << "Electrothermal KCL gate rejected state: relative "
                      << "current spread=" << (double)relative_spread << "\n";
            res.converged = false;
        }
    }

    // A DeviceSimulator instance represents one device along a bias sweep.
    // Retain an honestly converged state as the default initial guess for the
    // next solve.  Previously the low-level API silently restarted every bias
    // point from charge-neutral equilibrium unless callers manually copied
    // phi/n/p back with set_initial_guess(); NLS/Preisach branches and abrupt
    // FinFET/GAA sweeps then left the convergence basin despite a good previous
    // solution being available.
    // Newly detected dielectric filaments affect the next solve, keeping the
    // electrical result, reported current, and heat source synchronized.
    bd_state_ = bd_state_detected;
    if (res.converged) {
        init_phi_ = res.phi;
        init_n_ = res.n;
        init_p_ = res.p;
        has_initial_guess_ = true;
    }

    return res;
}

void DeviceSimulator::compute_edge_currents(SimulationResult& res,
                                             const std::vector<real_t>& phi,
                                             const std::vector<real_t>& n,
                                             const std::vector<real_t>& p,
                                             const std::vector<real_t>* transport_Qn,
                                             const std::vector<real_t>* transport_Qp) {
    // Full-precision Scharfetter-Gummel edge fluxes from the converged state.
    // CONVENTIONAL current densities (so Jn + Jp = total current, positive in
    // the +axis direction):
    // Jn = (QE*Dn/d) * (n[j]*B(+dphi/VT) - n[i]*B(-dphi/VT))   [A/m^2]
    // Jp = (QE*Dp/d) * (p[i]*B(+dphi/VT) - p[j]*B(-dphi/VT))
    // where Dn = mu_n*VT, d = grid spacing, dphi = phi[j]-phi[i].
    // NOTE: Jn must carry the opposite sign to the raw electron SG flux
    // (conventional current vs electron particle flow); an earlier version
    // stored Jn with the opposite sign, making Jn+Jp subtract the two
    // physical components instead of adding them (verified against Sentaurus).
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

    // Use the same DG-shifted transport potential as the continuity solver.
    // Recomputing terminal currents from classical phi after a quantum solve
    // produced non-conservative currents and even the wrong sign near threshold.
    std::vector<real_t> Qn(N, 0.0Q), Qp(N, 0.0Q);
    if (quantum_enabled_) {
        std::vector<char> semi(N, 0);
        for (size_t i = 0; i < N; ++i)
            semi[i] = (mu_n_[i] > EPSILON || mu_p_[i] > EPSILON) ? 1 : 0;
        dg_.set_semiconductor_mask(semi);
        dg_.set_thermal_voltage(VT_);
        if (dg_potential_form_enabled_ &&
            statistics_type_ == StatisticsType::FERMI_DIRAC &&
            transport_Qn != nullptr &&
            transport_Qp != nullptr && transport_Qn->size() == N &&
            transport_Qp->size() == N) {
            dg_.quantum_potential_potential_form(
                n, p, *transport_Qn, *transport_Qp, Qn, Qp);
        } else {
            dg_.quantum_potential(n, p, Qn, Qp);
        }
        for (const auto& bc : n_bc_) Qn[bc.first] = 0.0Q;
        for (const auto& bc : p_bc_) Qp[bc.first] = 0.0Q;
    }
    res.Qn = Qn;
    res.Qp = Qp;

    // A converged Gummel solve used the lagged/under-relaxed Q stored by the
    // solver.  Use it for flux reconstruction while exposing the undamped
    // physical Q(n,p) above.  Newton has no lagged state and falls back to the
    // freshly evaluated potential.  Validate sizes so a skipped/failed solve
    // can never leak a stale vector into current post-processing.
    const std::vector<real_t>& Qn_flux =
        (transport_Qn != nullptr && transport_Qn->size() == N) ? *transport_Qn : Qn;
    const std::vector<real_t>& Qp_flux =
        (transport_Qp != nullptr && transport_Qp->size() == N) ? *transport_Qp : Qp;

    auto fill_axis = [&](std::vector<real_t>& Jn_ax,
                         std::vector<real_t>& Jp_ax,
                         int axis, size_t stride,
                         size_t n0, size_t n1, size_t n2) {
        for (size_t k = 0; k < n2; ++k) {
            for (size_t j = 0; j < n1; ++j) {
                for (size_t i = 0; i < n0; ++i) {
                    size_t idx = g_.index(i, j, k);
                    size_t nbr = idx + stride;
                    // Per-edge spacing for non-uniform grid
                    real_t d;
                    if (axis == 0)      d = g_.dx_edge(i);
                    else if (axis == 1) d = g_.dy_edge(j);
                    else                d = g_.dz_edge(k);
                    real_t delta_n = ((phi[nbr] + Qn_flux[nbr]) -
                                      (phi[idx] + Qn_flux[idx])) / VT_;
                    real_t delta_p = ((phi[nbr] - Qp_flux[nbr]) -
                                      (phi[idx] - Qp_flux[idx])) / VT_;
                    real_t Bmn = B(-delta_n);
                    real_t Bpn = B(delta_n);
                    real_t Bmp = B(-delta_p);
                    real_t Bpp = B(delta_p);
                    real_t mu_ne = 2.0Q * mu_n_[idx] * mu_n_[nbr] / (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
                    real_t mu_pe = 2.0Q * mu_p_[idx] * mu_p_[nbr] / (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
                    real_t Dn = mu_ne * VT_ / d;
                    real_t Dp = mu_pe * VT_ / d;
                    Jn_ax[idx] = QE * Dn * (n[nbr] * Bpn - n[idx] * Bmn);
                    Jp_ax[idx] = QE * Dp * (p[idx] * Bpp - p[nbr] * Bmp);
                }
            }
        }
    };

    fill_axis(res.Jn_x, res.Jp_x, 0, 1,            g_.nx - 1, g_.ny,     g_.nz);
    fill_axis(res.Jn_y, res.Jp_y, 1, g_.nx,        g_.nx,     g_.ny - 1, g_.nz);
    fill_axis(res.Jn_z, res.Jp_z, 2, g_.nx * g_.ny, g_.nx,     g_.ny,     g_.nz - 1);

    // Dielectric PF/FN and post-breakdown filament conduction are real
    // conventional-current fluxes, not charge terms in Poisson. Store them on
    // the same +axis edges as Jn/Jp so terminal integration and KCL checks use
    // explicit A/m^2 quantities.
    res.Jleak_x.assign(N, 0.0Q);
    res.Jleak_y.assign(N, 0.0Q);
    res.Jleak_z.assign(N, 0.0Q);
    const bool have_pf_fn = leak_enabled_ && leak_mask_.size() == N;
    const bool have_breakdown = bd_enabled_ && bd_state_.size() == N &&
                                bd_mask_.size() == N && sigma_bd_ > 0.0Q;
    if (!have_pf_fn && !have_breakdown) return;

    auto conductivity = [&](real_t E_mag, real_t E_axis) -> real_t {
        if (E_mag <= leak_E_floor_) return 0.0Q;
        real_t sigma = 0.0Q;  // [S/m]
        if (leak_C_pf_ > 0.0Q && leak_phi_t_ > 0.0Q) {
            real_t arg = leak_B_pf_ * sqrt_q(leak_phi_t_ / E_mag);
            sigma += leak_C_pf_ * exp_q(-arg);
        }
        real_t C_fn = leak_C_fn_;
        real_t B_fn = leak_B_fn_;
        if (leak_fn_polarity_enabled_) {
            if (E_axis >= 0.0Q) {
                C_fn = leak_C_fn_positive_;
                B_fn = leak_B_fn_positive_;
            } else {
                C_fn = leak_C_fn_negative_;
                B_fn = leak_B_fn_negative_;
            }
        }
        if (C_fn > 0.0Q && leak_phi_b_ > 0.0Q) {
            real_t arg = B_fn * pow_q(leak_phi_b_, 1.5Q) / E_mag;
            // J_FN=C_fn*E^2*exp(-arg), hence sigma_FN=J/E.
            sigma += C_fn * E_mag * exp_q(-arg);
        }
        if (leak_sigma_cap_ > 0.0Q && sigma > leak_sigma_cap_)
            sigma = leak_sigma_cap_;
        return sigma;
    };

    auto fill_leak_axis = [&](std::vector<real_t>& J_ax,
                              int axis, size_t stride,
                              size_t n0, size_t n1, size_t n2) {
        for (size_t k = 0; k < n2; ++k)
            for (size_t j = 0; j < n1; ++j)
                for (size_t i = 0; i < n0; ++i) {
                    size_t idx = g_.index(i, j, k);
                    size_t nbr = idx + stride;
                    const bool pf_edge = have_pf_fn &&
                                         (leak_mask_[idx] || leak_mask_[nbr]);
                    const bool bd_edge = have_breakdown &&
                                         (bd_state_[idx] || bd_state_[nbr]) &&
                                         (bd_mask_[idx] || bd_mask_[nbr]);
                    if (!pf_edge && !bd_edge) continue;
                    real_t d = (axis == 0) ? g_.dx_edge(i)
                             : (axis == 1) ? g_.dy_edge(j) : g_.dz_edge(k);
                    real_t E_axis = -(phi[nbr] - phi[idx]) / d;
                    real_t E2_i = res.Ex[idx]*res.Ex[idx] + res.Ey[idx]*res.Ey[idx] + res.Ez[idx]*res.Ez[idx];
                    real_t E2_j = res.Ex[nbr]*res.Ex[nbr] + res.Ey[nbr]*res.Ey[nbr] + res.Ez[nbr]*res.Ez[nbr];
                    real_t E_mag = 0.5Q * (sqrt_q(E2_i) + sqrt_q(E2_j));
                    if (E_mag < abs_q(E_axis)) E_mag = abs_q(E_axis);
                    real_t sigma = pf_edge ? conductivity(E_mag, E_axis) : 0.0Q;
                    if (bd_edge) sigma += sigma_bd_;
                    J_ax[idx] = sigma * E_axis;
                }
    };
    fill_leak_axis(res.Jleak_x, 0, 1,             g_.nx - 1, g_.ny,     g_.nz);
    fill_leak_axis(res.Jleak_y, 1, g_.nx,         g_.nx,     g_.ny - 1, g_.nz);
    fill_leak_axis(res.Jleak_z, 2, g_.nx * g_.ny, g_.nx,     g_.ny,     g_.nz - 1);
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
        newton_.set_edge_permittivity(
            edge_eps_x_plus_, edge_eps_x_minus_,
            edge_eps_y_plus_, edge_eps_y_minus_,
            edge_eps_z_plus_, edge_eps_z_minus_);
        newton_.set_mobility(mu_n_eff, mu_p_eff);
        newton_.set_doping(Nd_minus_Na_);
        newton_.set_charge_volume_fraction(charge_volume_fraction_);
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
