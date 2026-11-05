#include "hfs_reference.h"
#include "device_simulator.h"
#include "linearized_wkb.h"
#include "quantum_contact.h"
#include "ii_driving.h"
#include "statistics.h"
#include "transport_contract.h"
#include "polarization_flux.h"
#include "lk_material_field.h"
#include "transient_candidate_transaction.h"
#include <algorithm>
#include <iostream>
#include <cmath>
#include <string>
#include <cstdlib>
#include <limits>
#include <exception>
#include <optional>

namespace tcad {

DeviceSimulator::DeviceSimulator(size_t nx, size_t ny, size_t nz,
                                 real_t dx, real_t dy, real_t dz)
    : g_{nx, ny, nz, dx, dy, dz},
      poisson_(g_),
      gummel_(g_),
      newton_(g_),
      dg_(g_) {
    const size_t N = g_.npts();
    eps_.assign(N, EPS0 * TCAD_CONST(11.7));
    mu_n_.assign(N, TCAD_CONST(0.14));
    mu_p_.assign(N, TCAD_CONST(0.045));
    // Default: effectively no SRH (infinite lifetime) to avoid perturbing
    // existing simulations.  Users must explicitly call set_recombination()
    // to enable SRH modeling.
    tau_n_.assign(N, TCAD_CONST(1e100));
    tau_p_.assign(N, TCAD_CONST(1e100));
    Nd_minus_Na_.assign(N, TCAD_CONST(0.0));
    charge_volume_fraction_.assign(N, TCAD_CONST(1.0));
    G_opt_.assign(N, TCAD_CONST(0.0));
    Nc_.assign(N, TCAD_CONST(2.8e19));   // Default Si conduction-band DOS [cm^-3]
    Nv_.assign(N, TCAD_CONST(1.04e19));  // Default Si valence-band DOS [cm^-3]
    Eg_.assign(N, TCAD_CONST(1.12));     // Default Si bandgap [eV]
    dg_.set_effective_dos(Nc_, Nv_);
    thermal_conductivity_.assign(N, TCAD_CONST(150.0)); // Default: Silicon thermal conductivity [W/(m*K)]
}

namespace {
bool paired_mobile_carriers(real_t mu_n, real_t mu_p) {
    return isfinite_q(mu_n) && isfinite_q(mu_p) &&
        mu_n > EPSILON && mu_p > EPSILON;
}

bool valid_pair_sources(real_t generation, real_t tau_n, real_t tau_p) {
    return isfinite_q(generation) && generation >= TCAD_CONST(0.0) &&
        isfinite_q(tau_n) && isfinite_q(tau_p) &&
        tau_n > TCAD_CONST(0.0) && tau_p > TCAD_CONST(0.0);
}

bool empty_blocked_carrier_row(real_t mu_n, real_t mu_p, real_t n, real_t p,
                              real_t generation, real_t tau_n, real_t tau_p) {
    return mu_n == TCAD_CONST(0.0) && mu_p == TCAD_CONST(0.0) &&
        isfinite_q(n) && n >= TCAD_CONST(0.0) && n <= EPSILON && n == p &&
        generation == TCAD_CONST(0.0) && isfinite_q(tau_n) && isfinite_q(tau_p) &&
        tau_n >= TCAD_CONST(1e90) && tau_p >= TCAD_CONST(1e90);
}

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
            (require_nonnegative && value < TCAD_CONST(0.0)))
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
    if (!finite_vector(positions))
        throw std::invalid_argument(std::string(axis) + " positions must be finite");
    for (size_t i = 1; i < positions.size(); ++i) {
        if (!(positions[i] > positions[i - 1]))
            throw std::invalid_argument(std::string(axis) +
                                        " positions must be strictly increasing");
    }
}
}  // namespace

void DeviceSimulator::set_transient_lk_zero_d_faces(const std::string& faces) {
    std::array<bool,6> selected{};
    const std::string names="xXyYzZ";
    const size_t sizes[]={g_.nx,g_.ny,g_.nz};
    size_t active=0; for(auto n:sizes) if(n>1) ++active;
    for(char face:faces) {
        const auto q=names.find(face);
        if(q==std::string::npos || selected[q])
            throw std::invalid_argument("zero-D faces must be unique characters from xXyYzZ");
        if(sizes[q/2]<2 || active<2)
            throw std::invalid_argument("zero-D exterior half cells require an active face axis on a multidimensional grid");
        selected[q]=true;
    }
    g_.lk_zero_d_faces=selected;
}

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

void DeviceSimulator::set_grid_y(const std::vector<real_t>& y_pos) {
    validate_positions(y_pos, g_.ny, "y");
    g_.yx = y_pos;
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
    for (real_t value : eps)
        if (!isfinite_q(value))
            throw std::invalid_argument("permittivity values must be finite");
    eps_ = eps;
    poisson_.set_permittivity(eps_);
}

void DeviceSimulator::set_edge_permittivity(const std::vector<real_t>& x_plus,
                                            const std::vector<real_t>& x_minus,
                                            const std::vector<real_t>& y_plus,
                                            const std::vector<real_t>& y_minus,
                                            const std::vector<real_t>& z_plus,
                                            const std::vector<real_t>& z_minus) {
    // Validate before replacing persistent inputs: a rejected setter must not
    // poison the next reconstruction of a steady solver.
    poisson_.set_edge_permittivity(x_plus, x_minus, y_plus, y_minus, z_plus, z_minus);
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
}

void DeviceSimulator::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    if (mu_n.size() != g_.npts() || mu_p.size() != g_.npts())
        throw std::invalid_argument("mobility size mismatch");
    for (const auto* values : {&mu_n, &mu_p})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("mobility values must be finite");
    mu_n_ = mu_n; mu_p_ = mu_p;
    gummel_.set_mobility(mu_n_, mu_p_);
}

void DeviceSimulator::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    if (Nd_minus_Na.size() != g_.npts())
        throw std::invalid_argument("Doping size mismatch");
    for (real_t value : Nd_minus_Na)
        if (!isfinite_q(value))
            throw std::invalid_argument("doping values must be finite");
    Nd_minus_Na_ = Nd_minus_Na;
    poisson_.set_doping(Nd_minus_Na_);
    gummel_.set_doping(Nd_minus_Na_);
}

void DeviceSimulator::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("charge volume fraction size mismatch");
    for (real_t value : fraction) {
        if (!isfinite_q(value) || value < TCAD_CONST(0.0) || value > TCAD_CONST(1.0))
            throw std::invalid_argument(
                "charge volume fraction must be in [0,1]");
    }
    charge_volume_fraction_ = fraction;
    poisson_.set_charge_volume_fraction(charge_volume_fraction_);
}

void DeviceSimulator::set_optical_generation(const std::vector<real_t>& G_opt) {
    if (G_opt.size() != g_.npts()) throw std::invalid_argument("optical generation size mismatch");
    for (real_t value : G_opt)
        if (!isfinite_q(value))
            throw std::invalid_argument("optical generation values must be finite");
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
    for (const auto* values : {&tau_n, &tau_p})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("recombination lifetime values must be finite");
    tau_n_ = tau_n;
    tau_p_ = tau_p;
    gummel_.set_recombination(tau_n_, tau_p_);
}

void DeviceSimulator::set_thermal_voltage(real_t VT) {
    if (!isfinite_q(VT) || VT <= TCAD_CONST(0.0))
        throw std::invalid_argument("thermal voltage must be finite and positive");
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
    if (!(bn > TCAD_CONST(0.0)) || !(bp > TCAD_CONST(0.0)) ||
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
    if (!(longitudinal_mass > TCAD_CONST(0.0)) || !(transverse_mass > TCAD_CONST(0.0)) ||
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
    if (!(factor > TCAD_CONST(0.0)) || !std::isfinite((double)factor))
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
        if (!(value > TCAD_CONST(0.0)) || !std::isfinite((double)value))
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
    phi_freezing_enabled_ = enable;
}

void DeviceSimulator::set_newton_freeze_phi(bool enable) { newton_freeze_phi_ = enable; }
void DeviceSimulator::set_newton_freeze_n(bool enable) { newton_freeze_n_ = enable; }
void DeviceSimulator::set_newton_freeze_p(bool enable) { newton_freeze_p_ = enable; }

void DeviceSimulator::set_gummel_max_iter(size_t max_iter) {
    max_iter_ = max_iter;
}

void DeviceSimulator::set_tolerance(real_t tol) {
    if (!isfinite_q(tol) || tol <= TCAD_CONST(0.0))
        throw std::invalid_argument("solver tolerance must be finite and positive");
    tol_ = tol;
}

void DeviceSimulator::set_poisson_solver_type(int type) {
    LinearSolver::validate_solver_type(type);
    poisson_solver_type_ = static_cast<SolverType>(type);
    gummel_.set_poisson_solver_type(poisson_solver_type_);
}

void DeviceSimulator::set_continuity_solver_type(int type) {
    LinearSolver::validate_solver_type(type);
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

void DeviceSimulator::set_newton_log_density_update(const std::string& mode) {
    if (mode != "exponential" && mode != "additive")
        throw std::invalid_argument("Newton log-density update must be exponential or additive");
    newton_additive_log_density_update_ = (mode == "additive");
}

std::string DeviceSimulator::get_newton_log_density_update() const {
    return newton_additive_log_density_update_ ? "additive" : "exponential";
}

void DeviceSimulator::set_newton_jacobian_reuse_threshold(real_t threshold) {
    newton_jacobian_reuse_threshold_ = threshold;
}

void DeviceSimulator::set_thermal_coupling_enabled(bool enable) {
    thermal_coupling_enabled_ = enable;
}

void DeviceSimulator::set_thermal_conductivity(const std::vector<real_t>& kappa) {
    if (kappa.size() != g_.npts()) throw std::invalid_argument("thermal conductivity size mismatch");
    for (real_t value : kappa)
        if (!isfinite_q(value) || value <= TCAD_CONST(0.0))
            throw std::invalid_argument("thermal conductivity must be finite and positive");
    thermal_conductivity_ = kappa;
}

void DeviceSimulator::set_ambient_temperature(real_t T_ambient) {
    if (!isfinite_q(T_ambient) || T_ambient <= TCAD_CONST(0.0))
        throw std::invalid_argument("ambient temperature must be finite and positive");
    ambient_temperature_ = T_ambient;
}

void DeviceSimulator::set_thermal_dirichlet(const std::map<size_t, real_t>& bc) {
    for (const auto& [idx, value] : bc)
        if (idx >= g_.npts() || !isfinite_q(value) || value <= TCAD_CONST(0.0))
            throw std::invalid_argument("invalid thermal Dirichlet node or temperature");
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
    btbt_field_cap_ = cap > TCAD_CONST(0.0) ? cap : TCAD_CONST(0.0);
    btbt_field_alpha_ = std::isfinite((double)alpha) ? alpha : TCAD_CONST(0.0);
    btbt_field_ref_ = ref > TCAD_CONST(0.0) ? ref : TCAD_CONST(1.0e8);
}

void DeviceSimulator::set_btbt_continuity_scale(real_t scale) {
    if (!std::isfinite((double)scale) || scale < TCAD_CONST(0.0)) {
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
    validate_linearized_wkb_work(g_.npts(), wkb_npts);
    btbt_tunnel_path_frac_ = tunnel_path_frac;
    btbt_wkb_npts_ = wkb_npts;
}

void DeviceSimulator::set_btbt_nonlocal_mass(real_t mass_ratio) {
    if (!std::isfinite((double)mass_ratio) || mass_ratio <= 0.0) {
        throw std::invalid_argument("BTBT nonlocal mass ratio must be finite and > 0");
    }
    btbt_nonlocal_mass_ = mass_ratio;
}

void DeviceSimulator::set_high_field_saturation(bool enable, real_t vsat_n,
                                                real_t vsat_p, real_t beta_n,
                                                real_t beta_p, int driving) {
    // Validate the complete request before changing any model state. Keep
    // validation in real_t so finite native values are not narrowed to double.
    validate_hfs_parameters(vsat_n, vsat_p, beta_n, beta_p, driving);
    hfs_vsat_n_ = vsat_n;
    hfs_vsat_p_ = vsat_p;
    hfs_beta_n_ = beta_n;
    hfs_beta_p_ = beta_p;
    hfs_driving_ = driving;
    hfs_enabled_ = enable;
}

void DeviceSimulator::set_high_field_reference_density(real_t n0, real_t p0) {
    validate_hfs_reference_density(n0,p0);
    hfs_refdens_n_=n0; hfs_refdens_p_=p0;
}
void DeviceSimulator::validate_hfs_reference_scope() const {
    if (!active_hfs_reference(hfs_enabled_,hfs_driving_,hfs_refdens_n_,hfs_refdens_p_)) return;
    validate_hfs_reference_geometry(g_,statistics_type_!=StatisticsType::BOLTZMANN ||
        quantum_enabled_ || fe_enabled_ || lattice_feedback_enabled_ || thermal_coupling_enabled_ ||
        mobility_model_type_!=MobilityModelType::CONSTANT);
    validate_hfs_reference_material(g_.npts(),Nc_,Nv_,Eg_,mu_n_,mu_p_);
}

void DeviceSimulator::set_hfs_low_field_cutoff(real_t cutoff) {
    validate_hfs_low_field_cutoff(cutoff);
    hfs_low_field_cutoff_ = cutoff;
}

void DeviceSimulator::set_ii_enabled(bool enable) {
    ii_enabled_ = enable;
}

void DeviceSimulator::set_ii_reference_density(real_t n0, real_t p0) {
    validate_ii_reference_density(n0,p0);
    ii_refdens_n_=n0; ii_refdens_p_=p0;
}
void DeviceSimulator::set_ii_driving(int driving) {
    validate_ii_driving(driving);
    ii_driving_=driving;
}
void DeviceSimulator::validate_ii_driving_scope() const {
    if(!ii_enabled_ || ii_driving_!=1) return;
    validate_ii_gqf_geometry(g_,statistics_type_!=StatisticsType::BOLTZMANN || quantum_enabled_ ||
        fe_enabled_ || lattice_feedback_enabled_ || thermal_coupling_enabled_ || mobility_model_type_!=MobilityModelType::CONSTANT);
    validate_ii_gqf_material(g_.npts(),Nc_,Nv_,Eg_,mu_n_,mu_p_);
}

void DeviceSimulator::set_ii_field_floor(real_t floor) {
    validate_ii_floor(floor);
    ii_field_floor_ = floor;
}

void DeviceSimulator::set_ii_params(real_t A_n, real_t B_n, real_t A_p, real_t B_p) {
    validate_ii_coefficients(A_n, B_n, A_p, B_p);
    ii_A_n_ = A_n;
    ii_B_n_ = B_n;
    ii_A_p_ = A_p;
    ii_B_p_ = B_p;
}

void DeviceSimulator::set_auger_enabled(bool enable) {
    auger_enabled_ = enable;
}

void DeviceSimulator::set_auger_params(real_t Cn, real_t Cp) {
    validate_auger_coefficients(Cn, Cp);
    auger_Cn_ = Cn;
    auger_Cp_ = Cp;
}

void DeviceSimulator::set_ohmic_contacts(const std::set<size_t>& nodes,
                                         const std::map<size_t, real_t>& EFn,
                                         const std::map<size_t, real_t>& EFp,
                                         real_t ni) {
    for (size_t node : nodes)
        if (node >= g_.npts())
            throw std::out_of_range("ohmic contact node is outside the grid");
    for (const auto* shifts : {&EFn, &EFp})
        for (const auto& entry : *shifts)
            if (entry.first >= g_.npts())
                throw std::out_of_range("ohmic quasi-Fermi node is outside the grid");
    for (const auto* shifts : {&EFn, &EFp})
        for (const auto& entry : *shifts)
            if (!isfinite_q(entry.second))
                throw std::invalid_argument("ohmic quasi-Fermi values must be finite");
    if (!isfinite_q(ni) || ni <= TCAD_CONST(0.0))
        throw std::invalid_argument("ohmic intrinsic density must be finite and positive");
    ohmic_nodes_ = nodes;
    ohmic_EFn_ = EFn;
    ohmic_EFp_ = EFp;
    ohmic_ni_ = ni;
}

void DeviceSimulator::clear_ohmic_contacts() {
    ohmic_nodes_.clear();
}

EquilibriumResult DeviceSimulator::solve_equilibrium(size_t max_iter, real_t tolerance,
        const std::vector<char>& carrier_mask) {
    // A classical, zero-common-Fermi PB seed, not a biased transport solution.
    // Keep all work local: invalid input, failed linear solves or exhausted
    // budgets must not replace a previously accepted initialization.
    const size_t N = g_.npts();
    if (!carrier_mask.empty() && (carrier_mask.size() != N ||
        !std::all_of(carrier_mask.begin(), carrier_mask.end(),
                     [](char value) { return value == 0 || value == 1; })))
        throw std::invalid_argument("equilibrium carrier mask must contain one boolean per mesh node");
    // A zero carrier volume would also remove fixed Poisson charge. Keep
    // material selection separate so a charged insulator can be exactly empty
    // of mobile carriers without erasing its immobile charge or permittivity.
    auto carrier_active = [&](size_t node) {
        return (carrier_mask.empty() || carrier_mask[node]) &&
            charge_volume_fraction_[node] > TCAD_CONST(0.0) && eps_[node] >= EPSILON;
    };
    if (!isfinite_q(tolerance) || tolerance <= TCAD_CONST(0.0) ||
        !isfinite_q(VT_) || VT_ <= TCAD_CONST(0.0) ||
        !isfinite_q(temperature_) || temperature_ <= TCAD_CONST(0.0))
        throw std::invalid_argument("equilibrium requires positive finite tolerance, VT and temperature");
    if (statistics_type_ != StatisticsType::BOLTZMANN || !ohmic_nodes_.empty())
        throw std::invalid_argument("equilibrium supports Boltzmann statistics and a zero common Fermi reference");
    if (phi_bc_.empty())
        throw std::invalid_argument("equilibrium requires a potential Dirichlet anchor");

    EquilibriumResult out;
    out.phi.assign(N, TCAD_CONST(0.0)); out.n.resize(N); out.p.resize(N);
    std::vector<real_t> ni(N), log_ni(N);
    for (size_t i = 0; i < N; ++i) {
        const bool active = carrier_active(i);
        if (!isfinite_q(Nc_[i]) || !isfinite_q(Nv_[i]) || Nc_[i] < TCAD_CONST(0.0) || Nv_[i] < TCAD_CONST(0.0) ||
            (active && (Nc_[i] == TCAD_CONST(0.0) || Nv_[i] == TCAD_CONST(0.0))) ||
            !isfinite_q(Eg_[i]) || Eg_[i] < TCAD_CONST(0.0) || !isfinite_q(Nd_minus_Na_[i]) ||
            !isfinite_q(eps_[i]) || eps_[i] < TCAD_CONST(0.0) ||
            !isfinite_q(charge_volume_fraction_[i]))
            throw std::invalid_argument("equilibrium requires finite material fields and positive DOS");
        if (!active) { ni[i] = TCAD_CONST(0.0); log_ni[i] = TCAD_CONST(0.0); continue; }
        // No wide-gap cutoff or intrinsic-density floor in the PB model.
        log_ni[i] = (log_q(Nc_[i])+log_q(Nv_[i]))/TCAD_CONST(2.0) - Eg_[i]/(TCAD_CONST(2.0)*TCAD_CONST(8.617333262e-5)*temperature_);
        ni[i] = exp_q(log_ni[i]);
        if (!isfinite_q(ni[i]) || ni[i] <= TCAD_CONST(0.0))
            throw std::invalid_argument("equilibrium intrinsic density is not representable");
        const real_t half = abs_q(Nd_minus_Na_[i]) / TCAD_CONST(2.0);
        const real_t majority = half + sqrt_q(half*half + ni[i]*ni[i]);
        out.phi[i] = VT_ * (log_q(majority) - log_ni[i]);
        if (Nd_minus_Na_[i] < TCAD_CONST(0.0)) out.phi[i] = -out.phi[i];
    }
    for (const auto& [node, value] : phi_bc_) {
        if (node >= N || !isfinite_q(value))
            throw std::invalid_argument("equilibrium requires finite potential boundary values");
        out.phi[node] = value;
    }
    auto carriers = [&](const std::vector<real_t>& phi, std::vector<real_t>& n,
                         std::vector<real_t>& p) {
        n.resize(N); p.resize(N);
        for (size_t i = 0; i < N; ++i) {
            if (!isfinite_q(phi[i])) return false;
            if (!carrier_active(i)) {
                n[i] = p[i] = TCAD_CONST(0.0); continue;
            }
            n[i] = exp_q(log_ni[i] + phi[i]/VT_);
            p[i] = exp_q(log_ni[i] - phi[i]/VT_);
            // The Python API exports doubles. Never export an infinite seed
            // or quietly substitute a clipped/floored carrier population.
            if (!isfinite_q(n[i]) || !isfinite_q(p[i]) || n[i] <= TCAD_CONST(0.0) || p[i] <= TCAD_CONST(0.0) ||
                !std::isfinite(static_cast<double>(n[i])) ||
                !std::isfinite(static_cast<double>(p[i])) ||
                static_cast<double>(n[i]) == 0.0 || static_cast<double>(p[i]) == 0.0)
                return false;
        }
        return true;
    };
    if (!carriers(out.phi, out.n, out.p))
        throw std::invalid_argument("equilibrium boundary carrier density is not representable");
    for (const auto* bc : {&n_bc_, &p_bc_}) {
        const auto& density = (bc == &n_bc_) ? out.n : out.p;
        for (const auto& [node, value] : *bc) {
            if (node >= N || !phi_bc_.count(node) || !isfinite_q(value) || value < TCAD_CONST(0.0) ||
                abs_q(value-density[node]) > TCAD_CONST(1e-6)*std::max(abs_q(value),abs_q(density[node])))
                throw std::invalid_argument("equilibrium carrier BC must match the anchored zero-Fermi Boltzmann reservoir");
        }
    }

    PoissonSolver op(g_);
    op.set_permittivity(eps_); op.set_doping(Nd_minus_Na_);
    op.set_charge_volume_fraction(charge_volume_fraction_);
    op.set_edge_permittivity(edge_eps_x_plus_, edge_eps_x_minus_, edge_eps_y_plus_,
                            edge_eps_y_minus_, edge_eps_z_plus_, edge_eps_z_minus_);
    op.set_dirichlet(phi_bc_);
    auto options = LinearSolver::default_poisson_options();
    options.type = (N > 2000)
        ? (auto_petsc_enabled() ? SolverType::PETSC : SolverType::BICGSTAB_ILU0)
        : SolverType::DENSE_DIRECT;
    op.set_solver_options(options);
    // Residuals always use the unlinearized operator. The per-row scale is
    // VT*sum|Aij| + q*f*(n+p+|doping|), with VT for Dirichlet/frozen rows.
    auto residual = [&](const std::vector<real_t>& phi, const std::vector<real_t>& n,
                         const std::vector<real_t>& p, Vector& scale, bool keep_scale) {
        op.set_boltzmann_linearization(false, VT_); op.assemble(n,p);
        const auto& A = op.matrix(); const auto& b = op.rhs();
        const auto Ax = A.apply(phi);
        if (!keep_scale) scale.assign(N, TCAD_CONST(0.0));
        real_t norm = TCAD_CONST(0.0);
        for (size_t i = 0; i < N; ++i) {
            if (!keep_scale) {
                real_t row = TCAD_CONST(0.0);
                for (size_t j = A.row_offsets()[i]; j < A.row_offsets()[i+1]; ++j)
                    row += abs_q(A.vals()[j]);
                scale[i] = row*VT_;
                if (!phi_bc_.count(i) && eps_[i] >= EPSILON)
                    scale[i] += QE*charge_volume_fraction_[i]*(n[i]+p[i]+abs_q(Nd_minus_Na_[i]));
            }
            if (!isfinite_q(Ax[i]) || !isfinite_q(b[i]) || !isfinite_q(scale[i]) || scale[i] <= TCAD_CONST(0.0))
                return static_cast<real_t>(std::numeric_limits<double>::infinity());
            norm = std::max(norm, abs_q(Ax[i]-b[i])/scale[i]);
        }
        return norm;
    };
    Vector scale;
    real_t norm = residual(out.phi,out.n,out.p,scale,false);
    if (!isfinite_q(norm)) throw std::invalid_argument("equilibrium operator is not finite or anchored");
    out.residual_history.push_back(norm);
    for (;;) {
        if (norm <= tolerance && (out.update_history.empty() || out.update_history.back() <= VT_*tolerance)) {
            out.converged = true; out.status = "converged"; break;
        }
        if (out.iterations == max_iter) { out.status = "max_iter"; break; }
        op.set_boltzmann_linearization(true, VT_); op.set_leakage_field(out.phi);
        op.assemble(out.n,out.p);
        auto proposed = out.phi;
        if (!op.solve(proposed)) { out.status = "linear_solver_failure"; break; }
        real_t largest = TCAD_CONST(0.0);
        for (size_t i = 0; i < N; ++i) largest = std::max(largest,abs_q(proposed[i]-out.phi[i]));
        real_t damping = largest > TCAD_CONST(4.0)*VT_ ? TCAD_CONST(4.0)*VT_/largest : TCAD_CONST(1.0);
        std::vector<real_t> trial(N), n, p;
        bool accepted = false;
        real_t update = TCAD_CONST(0.0);
        for (int backtrack = 0; backtrack < 40; ++backtrack, damping *= TCAD_CONST(0.5)) {
            update = TCAD_CONST(0.0);
            for (size_t i = 0; i < N; ++i) {
                trial[i] = out.phi[i] + damping*(proposed[i]-out.phi[i]);
                update = std::max(update,abs_q(trial[i]-out.phi[i]));
            }
            if (!carriers(trial,n,p)) continue;
            const real_t merit = residual(trial,n,p,scale,true);
            if (isfinite_q(merit) && (merit <= (TCAD_CONST(1.0)-TCAD_CONST(1e-4)*damping)*norm ||
                (merit <= tolerance && update <= VT_*tolerance))) { accepted = true; break; }
        }
        if (!accepted) { out.status = "line_search_failure"; break; }
        out.phi.swap(trial); out.n.swap(n); out.p.swap(p);
        ++out.iterations;
        out.update_history.push_back(update); out.damping_history.push_back(damping);
        norm = residual(out.phi,out.n,out.p,scale,false);
        out.residual_history.push_back(norm);
        if (!isfinite_q(norm)) { out.status = "nonfinite_residual"; break; }
    }
    if (out.converged) {
        init_phi_ = out.phi; init_n_ = out.n; init_p_ = out.p; has_initial_guess_ = true;
    }
    return out;
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
    for (real_t value : E_bd)
        if (!isfinite_q(value))
            throw std::invalid_argument("E_bd values must be finite");
    if (!isfinite_q(sigma_bd))
        throw std::invalid_argument("sigma_bd must be finite");
    bd_mask_ = bd_mask;
    E_bd_ = E_bd;
    sigma_bd_ = sigma_bd;
}

void DeviceSimulator::set_ferroelectric_enabled(bool enable) {
    fe_enabled_ = enable;
}

void DeviceSimulator::begin_reliability_transaction() {
    if(three_temperature_.enabled() || isolated_relaxation_.enabled() || energy_coordinate_.enabled()) throw std::logic_error("legacy solve/transaction unavailable in explicit-cell three-temperature mode");
    reliability_checkpoints_.push_back({
        fe_polarization_, fe_play_state_, Q_ot_, init_phi_, init_n_, init_p_,
        bd_state_, phi_bc_, n_bc_, p_bc_, fe_polarization_init_, bd_state_init_,
        has_initial_guess_, history_updates_enabled_, fe_ps_, fe_ec_, fe_escale_,
        fe_E_bi_, fe_nls_tau0_, fe_nls_E0_, fe_nls_dt_, transient_start_time_,
        dg_transport_Qn_, dg_transport_Qp_});
}

void DeviceSimulator::commit_reliability_transaction() {
    if (reliability_checkpoints_.empty())
        throw std::logic_error("no active reliability transaction");
    reliability_checkpoints_.pop_back();
}

void DeviceSimulator::rollback_reliability_transaction() {
    if (reliability_checkpoints_.empty())
        throw std::logic_error("no active reliability transaction");
    auto s = std::move(reliability_checkpoints_.back());
    reliability_checkpoints_.pop_back();
    fe_polarization_ = std::move(s.polarization);
    fe_play_state_ = std::move(s.play);
    Q_ot_ = std::move(s.charge);
    init_phi_ = std::move(s.phi); init_n_ = std::move(s.n); init_p_ = std::move(s.p);
    dg_transport_Qn_ = std::move(s.transport_Qn);
    dg_transport_Qp_ = std::move(s.transport_Qp);
    bd_state_ = std::move(s.breakdown);
    phi_bc_ = std::move(s.phi_bc); n_bc_ = std::move(s.n_bc); p_bc_ = std::move(s.p_bc);
    fe_polarization_init_ = s.polarization_init; bd_state_init_ = s.breakdown_init;
    has_initial_guess_ = s.initial_guess; history_updates_enabled_ = s.history_updates;
    fe_ps_ = s.ps; fe_ec_ = s.ec; fe_escale_ = s.escale; fe_E_bi_ = s.builtin_field;
    fe_nls_tau0_ = s.tau0; fe_nls_E0_ = s.e0; fe_nls_dt_ = s.dwell;
    transient_start_time_ = s.start_time;
}

void DeviceSimulator::set_ferroelectric_params(const std::vector<char>& fe_mask,
                                               real_t alpha, real_t beta) {
    if (fe_mask.size() != g_.npts())
        throw std::invalid_argument("fe_mask size mismatch");
    if (!isfinite_q(alpha) || !isfinite_q(beta))
        throw std::invalid_argument("FE alpha and beta must be finite");
    fe_mask_ = fe_mask;
    fe_alpha_ = alpha;
    fe_beta_ = beta;
}

void DeviceSimulator::set_ferroelectric_model(int model) {
    // 0 = Landau-Khalatnikov, 1 = Preisach (play operator). M7c.
    fe_model_ = model;
}

void DeviceSimulator::set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale) {
    if (!isfinite_q(ps) || !isfinite_q(ec) || !isfinite_q(escale) ||
        ps < TCAD_CONST(0.0) || ec < TCAD_CONST(0.0) || escale < TCAD_CONST(0.0))
        throw std::invalid_argument("FE Ps, Ec and Escale must be finite and nonnegative");
    fe_ps_ = ps;
    fe_ec_ = ec;
    fe_escale_ = escale;
}

void DeviceSimulator::set_ferroelectric_builtin_field(real_t E_bi) {
    if (!isfinite_q(E_bi))
        throw std::invalid_argument("FE builtin field must be finite");
    fe_E_bi_ = E_bi;   // P2.1: internal/imprint offset; 0 => symmetric
}

void DeviceSimulator::set_ferroelectric_depol(real_t eps_fe) {
    if (!isfinite_q(eps_fe) || eps_fe < TCAD_CONST(0.0))
        throw std::invalid_argument("extra depolarization permittivity must be finite and nonnegative");
    fe_eps_fe_ = eps_fe;   // comments2.docx P3: depol field
}

void DeviceSimulator::set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt) {
    if (!isfinite_q(tau0) || !isfinite_q(E0) || !isfinite_q(dt) ||
        tau0 <= TCAD_CONST(0.0) || E0 < TCAD_CONST(0.0) || dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("NLS requires finite tau0>0, E0>=0 and dt>0");
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
    for (real_t value : {C_pf, B_pf, phi_t, C_fn, B_fn, phi_b,
                         E_floor, sigma_cap})
        if (!isfinite_q(value))
            throw std::invalid_argument("leakage parameters must be finite");
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
        C_positive < TCAD_CONST(0.0) || B_positive < TCAD_CONST(0.0) ||
        C_negative < TCAD_CONST(0.0) || B_negative < TCAD_CONST(0.0))
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
    if (!isfinite_q(D_it) || D_it < TCAD_CONST(0.0))
        throw std::invalid_argument("interface trap density must be finite and nonnegative");
    if (!isfinite_q(E_t))
        throw std::invalid_argument("interface trap energy must be finite");
    trap_mask_ = mask;
    trap_D_it_ = D_it;
    trap_E_t_ = E_t;
}

void DeviceSimulator::set_oxide_traps(const std::vector<real_t>& Q_ot) {
    if (!Q_ot.empty() && Q_ot.size() != g_.npts())
        throw std::invalid_argument("oxide trap charge size mismatch");
    for (real_t value : Q_ot)
        if (!isfinite_q(value))
            throw std::invalid_argument("oxide trap charge must be finite");
    Q_ot_ = Q_ot;
}

void DeviceSimulator::set_initial_guess(const std::vector<real_t>& phi,
                                         const std::vector<real_t>& n,
                                         const std::vector<real_t>& p) {
    if (phi.size() != g_.npts() || n.size() != g_.npts() || p.size() != g_.npts())
        throw std::invalid_argument("initial guess size mismatch");
    for (const auto* values : {&phi, &n, &p})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("initial guess values must be finite");
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
    for (const auto* values : {&Nc, &Nv})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("effective DOS values must be finite");
    Nc_ = Nc;
    Nv_ = Nv;
    dg_.set_effective_dos(Nc_, Nv_);
}

void DeviceSimulator::set_bandgap(const std::vector<real_t>& Eg) {
    if (Eg.size() != g_.npts()) throw std::invalid_argument("bandgap size mismatch");
    for (real_t value : Eg)
        if (!isfinite_q(value))
            throw std::invalid_argument("bandgap values must be finite");
    Eg_ = Eg;
}

void DeviceSimulator::set_temperature(real_t T) {
    if (!isfinite_q(T) || T <= TCAD_CONST(0.0))
        throw std::invalid_argument("temperature must be finite and positive");
    temperature_ = T;
    VT_ = TCAD_CONST(8.617333262e-5) * T;
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
void DeviceSimulator::set_transient_dt(real_t dt) {
    if (!std::isfinite((double)dt) || dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("transient dt must be finite and positive");
    transient_dt_ = dt;
}
void DeviceSimulator::set_transient_t_final(real_t t_final) {
    if (!std::isfinite((double)t_final) || t_final < TCAD_CONST(0.0))
        throw std::invalid_argument("transient t_final must be finite and nonnegative");
    transient_t_final_ = t_final;
}

void DeviceSimulator::set_transient_start_time(real_t time) {
    if (!isfinite_q(time) || time < TCAD_CONST(0.0))
        throw std::invalid_argument("transient start time must be finite and nonnegative");
    transient_start_time_ = time;
}

void DeviceSimulator::set_ferroelectric_history(const std::vector<real_t>& polarization) {
    const size_t N = g_.npts();
    if (!fe_enabled_ || fe_model_ != 0 || fe_mask_.size() != N || polarization.size() != 3*N)
        throw std::invalid_argument("history restart requires enabled cubic LK, a mesh mask and 3N polarization values");
    for (size_t i=0;i<N;++i)
        for (size_t a=0;a<3;++a)
            if (!isfinite_q(polarization[3*i+a]) || (!fe_mask_[i] && polarization[3*i+a]!=TCAD_CONST(0.0)))
                throw std::invalid_argument("history requires finite polarization and zero outside FE");
    fe_polarization_ = polarization;
    fe_polarization_init_ = true;
    fe_play_state_.clear();
}
void DeviceSimulator::set_ferroelectric_ensemble_history(
    const std::vector<real_t>& polarization, const std::vector<real_t>& play) {
    const size_t N=g_.npts();
    if (!fe_enabled_ || fe_model_<1 || fe_model_>3 || fe_mask_.size()!=N || polarization.size()!=3*N)
        throw std::invalid_argument("ensemble history requires enabled non-LK FE and 3N polarization");
    if ((fe_model_==1 && play.size()!=N) || (fe_model_==2 && !play.empty()) ||
        (fe_model_==3 && (play.size()<2*N+4 || (play.size()-2*N)%2!=0)))
        throw std::invalid_argument("invalid ensemble memory layout");
    size_t first=N;
    for (size_t i=0;i<N;++i) {
        if (fe_mask_[i] && first==N) first=i;
        for (int a=0;a<3;++a) {
            const real_t p=polarization[3*i+a];
            if (!isfinite_q(p) || ((!fe_mask_[i] || a!=fe_polar_axis_) && p!=TCAD_CONST(0.0)) ||
                abs_q(p)>fe_ps_*(TCAD_CONST(1.0)+TCAD_CONST(1.e-14)))
                throw std::invalid_argument("invalid scalar ensemble polarization");
        }
        if (fe_mask_[i] && first!=N && polarization[3*i+fe_polar_axis_]!=polarization[3*first+fe_polar_axis_])
            throw std::invalid_argument("nonuniform ensemble polarization cannot preserve compact memory");
        const size_t blocks=(fe_model_==3)?2:((fe_model_==1)?1:0);
        for (size_t b=0;b<blocks;++b) {
            const real_t v=play[b*N+i];
            if (!isfinite_q(v) || (!fe_mask_[i] && v!=TCAD_CONST(0.0)) ||
                (fe_mask_[i] && v!=play[b*N+first]) ||
                (fe_model_==3 && b==1 && fe_mask_[i] && v!=TCAD_CONST(1.0) && v!=-TCAD_CONST(1.0)))
                throw std::invalid_argument("invalid or incompatible ensemble branch memory");
        }
    }
    if (first==N) throw std::invalid_argument("ensemble history requires nonempty FE support");
    if (fe_model_==3) for (size_t i=2*N;i<play.size();++i) {
        if (!isfinite_q(play[i]) || (i%2==1 && abs_q(play[i])>fe_ps_*(TCAD_CONST(1.0)+TCAD_CONST(1.e-14))))
            throw std::invalid_argument("invalid turning point stack");
    }
    // All validation precedes mutation; branch stack is copied without averaging.
    fe_polarization_=polarization;fe_play_state_=play;fe_polarization_init_=true;
}
void DeviceSimulator::set_transient_lk_substepping(bool enable, real_t safety) {
    if (!isfinite_q(safety) || safety <= TCAD_CONST(0.0) || safety >= TCAD_CONST(1.0))
        throw std::invalid_argument("LK substepping safety must be finite and in (0, 1)");
    transient_lk_substepping_ = enable;
    transient_lk_safety_ = safety;
}
void DeviceSimulator::set_transient_lk_error_control(bool enable, real_t rtol,
    real_t atol, real_t min_dt, size_t max_reject) {
    if (!std::isfinite((double)rtol) || rtol <= TCAD_CONST(0.0) || rtol >= TCAD_CONST(1.0) ||
        !std::isfinite((double)atol) || atol <= TCAD_CONST(0.0) ||
        !std::isfinite((double)min_dt) || min_dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("LK error control requires 0<rtol<1, positive atol and min_dt");
    transient_lk_error_control_ = enable;
    transient_lk_error_rtol_ = rtol; transient_lk_error_atol_ = atol;
    transient_lk_min_dt_ = min_dt; transient_lk_max_reject_ = max_reject;
}
void DeviceSimulator::set_transient_lk_electrical_error_control(bool enable,
    real_t phi_atol, real_t carrier_rtol, real_t carrier_atol) {
    if (!std::isfinite((double)phi_atol) || (double)phi_atol <= 0.0 ||
        !std::isfinite((double)carrier_rtol) || carrier_rtol <= TCAD_CONST(0.0) || carrier_rtol >= TCAD_CONST(1.0) ||
        !std::isfinite((double)carrier_atol) || (double)carrier_atol <= 0.0)
        throw std::invalid_argument("LK electrical error control requires positive phi/carrier atol and 0<carrier_rtol<1");
    transient_lk_electrical_error_control_ = enable;
    transient_lk_phi_atol_ = phi_atol;
    transient_lk_carrier_rtol_ = carrier_rtol;
    transient_lk_carrier_atol_ = carrier_atol;
}
void DeviceSimulator::set_transient_electrical_error_control(bool enable,
    real_t phi_atol, real_t carrier_rtol, real_t carrier_atol, real_t min_dt, size_t max_reject) {
    if (!std::isfinite((double)phi_atol) || (double)phi_atol <= 0.0 ||
        !std::isfinite((double)carrier_rtol) || (double)carrier_rtol <= 0.0 || carrier_rtol >= TCAD_CONST(1.0) ||
        !std::isfinite((double)carrier_atol) || (double)carrier_atol <= 0.0 ||
        !std::isfinite((double)min_dt) || (double)min_dt <= 0.0)
        throw std::invalid_argument("electrical error control requires positive finite atol/min_dt and 0<carrier_rtol<1");
    transient_electrical_error_control_ = enable;
    transient_phi_atol_ = phi_atol; transient_carrier_rtol_ = carrier_rtol;
    transient_carrier_atol_ = carrier_atol; transient_error_min_dt_ = min_dt;
    transient_error_max_reject_ = max_reject;
}
void DeviceSimulator::set_transient_nls_error_control(bool enable, real_t rtol, real_t atol,
    real_t phi_atol, real_t carrier_rtol, real_t carrier_atol, real_t min_dt, size_t max_reject) {
    for (real_t value : {rtol, atol, phi_atol, carrier_rtol, carrier_atol, min_dt})
        if (!std::isfinite((double)value) || (double)value <= 0.0)
            throw std::invalid_argument("NLS error control requires positive finite real budgets");
    if (rtol >= TCAD_CONST(1.0) || carrier_rtol >= TCAD_CONST(1.0))
        throw std::invalid_argument("NLS error control relative budgets must be in (0, 1)");
    transient_nls_error_control_ = enable;
    transient_nls_error_ = {rtol, atol, phi_atol, carrier_rtol, carrier_atol, min_dt, max_reject};
}
void DeviceSimulator::set_ferroelectric_gamma(real_t gamma) {
    if (!std::isfinite((double)gamma) || gamma < TCAD_CONST(0.0))
        throw std::invalid_argument("FE transient gamma must be finite and nonnegative");
    fe_gamma_ = gamma;
}

void DeviceSimulator::set_transient_voltage_waveforms(const std::vector<real_t>& times,
    const std::map<size_t, std::vector<real_t>>& offsets) {
    if (times.size() < 2 || times.front() != TCAD_CONST(0.0) || offsets.empty())
        throw std::invalid_argument("waveforms require at least two times starting at zero and nonempty offsets");
    for (size_t i = 0; i < times.size(); ++i)
        if (!std::isfinite((double)times[i]) || (i && times[i] <= times[i - 1]))
            throw std::invalid_argument("waveform times must be finite and strictly increasing");
    for (const auto& [idx, values] : offsets) {
        if (idx >= g_.npts() || !phi_bc_.count(idx))
            throw std::invalid_argument("waveform node must be a configured potential contact");
        if (values.size() != times.size())
            throw std::invalid_argument("waveform offsets must match the time count");
        for (real_t value : values)
            if (!std::isfinite((double)value))
                throw std::invalid_argument("waveform offsets must be finite");
    }
    transient_waveform_times_ = times;
    transient_voltage_offsets_ = offsets;
}

void DeviceSimulator::clear_transient_voltage_waveforms() {
    transient_waveform_times_.clear();
    transient_voltage_offsets_.clear();
}

void DeviceSimulator::set_lattice_mobility_feedback(bool enable, size_t max_iter,
    real_t temperature_tol, real_t relaxation) {
    if (max_iter == 0 || max_iter > 10000 || !isfinite_q(temperature_tol) ||
        temperature_tol <= TCAD_CONST(0.0) || !isfinite_q(relaxation) ||
        relaxation <= TCAD_CONST(0.0) || relaxation > TCAD_CONST(1.0))
        throw std::invalid_argument("invalid lattice feedback iteration controls");
    lattice_feedback_enabled_ = enable;
    lattice_feedback_max_iter_ = max_iter;
    lattice_feedback_tol_ = temperature_tol;
    lattice_relaxation_ = relaxation;
}

void DeviceSimulator::validate_lattice_scope() const {
    if (!thermal_coupling_enabled_)
        throw std::invalid_argument("lattice feedback/steps require thermal coupling");
    if (fe_enabled_ || quantum_enabled_ || bd_enabled_ || leak_enabled_ ||
        btbt_enabled_ || ii_enabled_ || auger_enabled_ || hfs_enabled_ ||
        statistics_type_ != StatisticsType::BOLTZMANN || trap_D_it_ != TCAD_CONST(0.0) ||
        std::any_of(Q_ot_.begin(), Q_ot_.end(), [](real_t v){return v != TCAD_CONST(0.0);}) ||
        std::any_of(G_opt_.begin(), G_opt_.end(), [](real_t v){return v != TCAD_CONST(0.0);}))
        throw std::invalid_argument("lattice mobility feedback/steps support classical quasistatic DD only");
}

void DeviceSimulator::transport_mobilities(std::vector<real_t>& mn, std::vector<real_t>& mp) const {
    mn = mu_n_; mp = mu_p_;
    if (mobility_model_type_ == MobilityModelType::CONSTANT) return;
    for (size_t i=0; i<g_.npts(); ++i) {
        const real_t T = mobility_temperature_.empty() ? temperature_ : mobility_temperature_[i];
        const real_t nd = std::max(Nd_minus_Na_[i], TCAD_CONST(0.0));
        const real_t na = std::max(-Nd_minus_Na_[i], TCAD_CONST(0.0));
        // Zero mobility defines an insulating node and must stay zero.
        if (mu_n_[i] > TCAD_CONST(0.0)) mn[i] = evaluate_mobility(mobility_model_type_, true, T, nd, na, mu_n_[i]);
        if (mu_p_[i] > TCAD_CONST(0.0)) mp[i] = evaluate_mobility(mobility_model_type_, false, T, nd, na, mu_p_[i]);
    }
}

SimulationResult DeviceSimulator::solve_lattice_step(const std::vector<real_t>& previous_temperature,
    const std::vector<real_t>& heat_capacity, real_t dt) {
    validate_lattice_scope();
    if (previous_temperature.size() != g_.npts() || heat_capacity.size() != g_.npts() ||
        !isfinite_q(dt) || dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("lattice step needs positive dt and nodal history/capacity");
    for (size_t i=0; i<g_.npts(); ++i)
        if (!isfinite_q(previous_temperature[i]) || previous_temperature[i] <= TCAD_CONST(0.0) ||
            !isfinite_q(heat_capacity[i]) || heat_capacity[i] <= TCAD_CONST(0.0))
            throw std::invalid_argument("lattice history and volumetric capacity must be finite and positive");
    // These fields are call-local context, including while copying the input
    // arrays. Install cleanup before the first write: either copy can allocate
    // and throw before solve() is entered.
    struct LatticeStepScope {
        real_t& dt;
        std::vector<real_t>& previous;
        std::vector<real_t>& capacity;
        ~LatticeStepScope() noexcept {
            dt = TCAD_CONST(0.0);
            previous.clear();
            capacity.clear();
        }
    } step{lattice_dt_, lattice_previous_temperature_, lattice_heat_capacity_};
    lattice_dt_ = dt;
    lattice_previous_temperature_ = previous_temperature;
    lattice_heat_capacity_ = heat_capacity;
    return solve();
}



std::vector<std::vector<double>> DeviceSimulator::structured_three_temperature_seed() const {
    if(three_temperature_.enabled() || isolated_relaxation_.enabled() || energy_coordinate_.enabled() || !reliability_checkpoints_.empty() || transient_enabled_ ||
        !transient_waveform_times_.empty() || lattice_dt_!=TCAD_CONST(0.0) ||
        newton_freeze_phi_ || newton_freeze_n_ || newton_freeze_p_ ||
        quantum_enabled_ || fe_enabled_ || bd_enabled_ || leak_enabled_ || btbt_enabled_ ||
        ii_enabled_ || auger_enabled_ || hfs_enabled_ || lattice_feedback_enabled_ ||
        statistics_type_!=StatisticsType::BOLTZMANN || mobility_model_type_!=MobilityModelType::CONSTANT ||
        trap_D_it_!=TCAD_CONST(0.0) || !ohmic_nodes_.empty() || !thermal_coupling_enabled_)
        throw std::invalid_argument("StructuredGrid three-temperature migration requires classical fixed coefficients and enabled lattice heat; unsupported physics/transaction/drive/frozen equation active");
    if(std::abs(double(VT_-TCAD_CONST(8.617333262e-5)*temperature_)) >
            1e-12*std::abs(double(TCAD_CONST(8.617333262e-5)*temperature_)))
        throw std::invalid_argument("StructuredGrid migration requires thermal voltage consistent with native temperature");
    const auto nonzero=[](const auto& v) {return std::any_of(v.begin(),v.end(),[](auto x){return x!=0;});};
    if(nonzero(G_opt_) || nonzero(Q_ot_) ||
        std::any_of(charge_volume_fraction_.begin(),charge_volume_fraction_.end(),[](auto x){return x!=1;}) ||
        std::any_of(tau_n_.begin(),tau_n_.end(),[](auto x){return x<TCAD_CONST(1e90);}) ||
        std::any_of(tau_p_.begin(),tau_p_.end(),[](auto x){return x<TCAD_CONST(1e90);}) ||
        !edge_eps_x_plus_.empty() || !edge_eps_x_minus_.empty() || !edge_eps_y_plus_.empty() ||
        !edge_eps_y_minus_.empty() || !edge_eps_z_plus_.empty() || !edge_eps_z_minus_.empty() ||
        std::any_of(g_.lk_zero_d_faces.begin(),g_.lk_zero_d_faces.end(),[](bool x){return x;}))
        throw std::invalid_argument("StructuredGrid three-temperature migration does not support recombination/generation/traps/fractional or cut-cell coefficients");
    const auto values=[](const auto& v) {std::vector<double> out;for(auto x:v) out.push_back(double(x));return out;};
    const auto boundary=[](const auto& map) {std::vector<double> out;for(auto [i,v]:map){out.push_back(double(i));out.push_back(double(v));}return out;};
    std::vector<std::vector<double>> out={values(eps_),values(mu_n_),values(mu_p_),values(Nd_minus_Na_),
        values(Nc_),values(Nv_),values(Eg_),values(thermal_conductivity_),
        {double(temperature_),double(ambient_temperature_)},boundary(phi_bc_),boundary(n_bc_),boundary(p_bc_),boundary(thermal_bc_)};
    for(const auto& positions:{g_.xx,g_.yx,g_.zx}) out.push_back(values(positions));
    out.push_back({double(g_.dx),double(g_.dy),double(g_.dz)});
    return out;
}

SimulationResult DeviceSimulator::commit_three_temperature(size_t token) {
    const auto raw=three_temperature_.candidate(token);
    SimulationResult result;
    result.n=fermi_local_detail::decimals(raw.n);result.p=fermi_local_detail::decimals(raw.p);
    for(size_t i=0;i<npts();++i) result.phi.push_back(real_t(raw.new_poisson[0][i]));
    for(double v:raw.temperature_n) result.electron_temperature.push_back(real_t(v));
    for(double v:raw.temperature_p) result.hole_temperature.push_back(real_t(v));
    for(double v:raw.temperature_l) result.temperature.push_back(real_t(v));
    result.explicit_cell_three_temperature=true;result.converged=true;
    result.iterations=size_t(raw.newton[1][1]);
    three_temperature_.commit(token);
    result.time=real_t(three_temperature_.time());
    return result;
}

SimulationResult DeviceSimulator::solve() {
    validate_ii_driving_scope();
    validate_hfs_reference_scope();
    if(three_temperature_.enabled() || isolated_relaxation_.enabled() || energy_coordinate_.enabled()) throw std::logic_error("legacy solve/transaction unavailable in explicit-cell three-temperature mode");
    if (!lattice_feedback_enabled_ && lattice_dt_ == TCAD_CONST(0.0)) return solve_lattice_attempt();
    validate_lattice_scope();
    // Each inner solve can accept a continuation seed before the outer heat
    // loop is accepted. Protect the whole outer call, including mobility setup
    // and result construction, and never allocate while rolling it back.
    struct LatticeAttemptGuard {
        std::vector<real_t>& phi;
        std::vector<real_t>& n;
        std::vector<real_t>& p;
        bool& guess;
        std::vector<real_t>& mobility;
        std::vector<real_t> entered_phi, entered_n, entered_p, entered_mobility;
        bool entered_guess;
        bool accepted = false;
        LatticeAttemptGuard(std::vector<real_t>& phi_, std::vector<real_t>& n_,
                            std::vector<real_t>& p_, bool& guess_, std::vector<real_t>& mobility_)
            : phi(phi_), n(n_), p(p_), guess(guess_), mobility(mobility_),
              entered_phi(phi_), entered_n(n_), entered_p(p_),
              entered_mobility(mobility_), entered_guess(guess_) {}
        ~LatticeAttemptGuard() noexcept {
            mobility.swap(entered_mobility);
            if (!accepted) {
                phi.swap(entered_phi);
                n.swap(entered_n);
                p.swap(entered_p);
                guess = entered_guess;
            }
        }
    } attempt(init_phi_, init_n_, init_p_, has_initial_guess_, mobility_temperature_);
    if (lattice_feedback_enabled_) {
        mobility_temperature_ = lattice_dt_ > TCAD_CONST(0.0) ? lattice_previous_temperature_
            : std::vector<real_t>(g_.npts(), ambient_temperature_);
        if (thermal_bc_.empty()) {
            for (const auto& bc : phi_bc_) mobility_temperature_[bc.first] = ambient_temperature_;
        } else for (const auto& bc : thermal_bc_) mobility_temperature_[bc.first] = bc.second;
    }
    SimulationResult result;
    size_t total_iterations = 0;
    const size_t limit = lattice_feedback_enabled_ ? lattice_feedback_max_iter_ : 1;
    for (size_t outer=0; outer<limit; ++outer) {
            result = solve_lattice_attempt(); total_iterations += result.iterations;
            auto& ledger = result.thermal;
            ledger.mobility_feedback = lattice_feedback_enabled_;
            ledger.feedback_iterations = outer+1;
            ledger.feedback_tolerance = lattice_feedback_enabled_ ? lattice_feedback_tol_ : TCAD_CONST(0.0);
            if (!result.converged || !ledger.available) break;
            real_t residual = TCAD_CONST(0.0);
            if (lattice_feedback_enabled_)
                for (size_t i=0; i<g_.npts(); ++i)
                    residual = std::max(residual, abs_q(result.temperature[i]-mobility_temperature_[i]));
            ledger.feedback_residual = residual;
            ledger.feedback_converged = !lattice_feedback_enabled_ || residual <= lattice_feedback_tol_;
            if (ledger.feedback_converged) {
                result.iterations = total_iterations;
                attempt.accepted = true;
                return result;
            }
            for (size_t i=0; i<g_.npts(); ++i)
                mobility_temperature_[i] += lattice_relaxation_*(result.temperature[i]-mobility_temperature_[i]);
    }
    result.converged = false; result.thermal.available = false;
    result.iterations = total_iterations;
    return result;
}

SimulationResult DeviceSimulator::solve_lattice_attempt() {
    // WKB feedback currently has a qualified classical steady x-1D Newton
    // route. Keep rejecting the other routes before changing material history.
    const bool nonlocal_btbt_feedback = btbt_enabled_ && btbt_use_nonlocal_
        && btbt_continuity_scale_ != TCAD_CONST(0.0);
    const bool independent_quantum_pde = quantum_enabled_ && dg_potential_form_enabled_
        && statistics_type_ == StatisticsType::FERMI_DIRAC;
    const bool unsupported_newton_wkb = nonlocal_btbt_feedback &&
        (g_.nx<2 || g_.ny!=1 || g_.nz!=1 || quantum_enabled_ ||
         statistics_type_!=StatisticsType::BOLTZMANN);
    if (unsupported_newton_wkb && use_newton_ && newton_primary_ && !independent_quantum_pde)
        throw std::invalid_argument("Newton-primary nonlocal BTBT feedback is unsupported; use Gummel");
    if(std::any_of(g_.lk_zero_d_faces.begin(),g_.lk_zero_d_faces.end(),[](bool v){return v;}))
        throw std::invalid_argument("zero-D exterior half cells are supported only by transient material-field LK");
    const size_t N = g_.npts();
    // A numerical attempt is not an additional physical dwell. Keep the
    // incoming material memory until the electrical state is accepted, so
    // retries cannot accumulate switching or initialize/commit breakdown at
    // a rejected point, including an exception during final state preparation.
    struct MaterialAttemptGuard {
        std::vector<real_t>& polarization;
        std::vector<real_t>& play;
        bool& initialized;
        std::vector<char>& breakdown;
        bool& breakdown_initialized;
        std::vector<real_t> entered_polarization;
        std::vector<real_t> entered_play;
        std::vector<char> entered_breakdown;
        bool entered_initialized;
        bool entered_breakdown_initialized;
        bool accepted = false;

        MaterialAttemptGuard(std::vector<real_t>& p, std::vector<real_t>& h,
                             bool& init, std::vector<char>& bd, bool& bd_init)
            : polarization(p), play(h), initialized(init), breakdown(bd),
              breakdown_initialized(bd_init), entered_polarization(p), entered_play(h),
              entered_breakdown(bd), entered_initialized(init),
              entered_breakdown_initialized(bd_init) {}

        ~MaterialAttemptGuard() noexcept {
            if (!accepted) {
                // Also runs during exception unwinding. Swapping the saved
                // vectors cannot allocate, including after std::bad_alloc.
                polarization.swap(entered_polarization);
                play.swap(entered_play);
                breakdown.swap(entered_breakdown);
                initialized = entered_initialized;
                breakdown_initialized = entered_breakdown_initialized;
            }
        }
    } material_attempt(fe_polarization_, fe_play_state_, fe_polarization_init_,
                       bd_state_, bd_state_init_);
    SimulationResult res;
    res.nonlinear_history_enabled = nonlinear_history_enabled_;
    auto record_gummel = [&](bool converged) {
        if (!nonlinear_history_enabled_) return;
        res.nonlinear_history.push_back({"gummel", converged,
            gummel_.poisson_residual_final(), gummel_.nonlinear_samples()});
    };
    res.phi.assign(N, TCAD_CONST(0.0));
    res.n.assign(N, TCAD_CONST(0.0));
    res.p.assign(N, TCAD_CONST(0.0));

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
    }

    // Apply mobility model if not constant
    std::vector<real_t> mu_n_eff, mu_p_eff;
    transport_mobilities(mu_n_eff, mu_p_eff);

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
            real_t half_C = C / TCAD_CONST(2.0);
            real_t disc = sqrt_q(ni[i] * ni[i] + half_C * half_C);
            real_t n_eq, p_eq;
            if (C >= TCAD_CONST(0.0)) {
                n_eq = disc + half_C;           // ~Nd on n-side
                p_eq = (n_eq > EPSILON) ? (ni[i] * ni[i] / n_eq) : TCAD_CONST(0.0);
            } else {
                p_eq = disc - half_C;           // ~Na on p-side
                n_eq = (p_eq > EPSILON) ? (ni[i] * ni[i] / p_eq) : TCAD_CONST(0.0);
            }
            res.n[i] = n_eq;
            res.p[i] = p_eq;
            // Equilibrium potential: phi_eq = VT * ln(n/ni) = -VT * ln(p/ni)
            if (n_eq > EPSILON) {
                res.phi[i] = VT_ * log_q(n_eq / ni[i]);
            } else if (p_eq > EPSILON) {
                res.phi[i] = -VT_ * log_q(p_eq / ni[i]);
            } else {
                res.phi[i] = TCAD_CONST(0.0);
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
    opt.enable_phi_freezing = phi_freezing_enabled_;
    opt.record_nonlinear_history = nonlinear_history_enabled_;
    opt.max_iter = max_iter_;
    opt.poisson_tol = tol_;
    opt.continuity_tol = tol_;
    // A cycle-mean/frozen state must respect the requested accuracy.  The
    // historical fixed 1e-3 gate silently accepted four orders less accuracy
    // than a tol=1e-7 quantum run and produced bias-to-bias current jumps.
    opt.frozen_residual_gate = std::min(
        std::max(TCAD_CONST(100.0) * tol_, TCAD_CONST(1.0e-8)), TCAD_CONST(1.0e-4));
    opt.enable_quantum = quantum_enabled_;
    // The density-gradient fixed-point map is substantially stiffer than
    // classical DD in ultra-thin films. Keep the outer carrier update
    // contractive; the final undamped continuity polish still returns the
    // same discrete solution once the coupled state has converged.
    if (quantum_enabled_) opt.cont_damping = TCAD_CONST(0.2);
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
    opt.btbt.nonlocal_mass = btbt_nonlocal_mass_;
    opt.hfs.enabled = hfs_enabled_;
    opt.hfs.vsat_n = hfs_vsat_n_;
    opt.hfs.vsat_p = hfs_vsat_p_;
    opt.hfs.beta_n = hfs_beta_n_;
    opt.hfs.beta_p = hfs_beta_p_;
    opt.hfs.refdens_n = hfs_refdens_n_; opt.hfs.refdens_p = hfs_refdens_p_;
    opt.hfs.driving = hfs_driving_;
    opt.hfs.quasi_fermi_at_contacts = hfs_qf_at_contacts_;
    opt.hfs.low_field_cutoff = hfs_low_field_cutoff_;
    // Impact ionization parameters
    opt.ii.driving = ii_driving_; opt.ii.refdens_n = ii_refdens_n_; opt.ii.refdens_p = ii_refdens_p_;
    opt.ii.enabled = ii_enabled_;
    opt.ii.A_n = ii_A_n_;
    opt.ii.B_n = ii_B_n_;
    opt.ii.A_p = ii_A_p_;
    opt.ii.B_p = ii_B_p_;
    opt.ii.E_floor = ii_field_floor_;
    // Auger recombination
    opt.auger.enabled = auger_enabled_;
    opt.auger.Cn = auger_Cn_;
    opt.auger.Cp = auger_Cp_;
    // Ferroelectric parameters
    opt.ferro.enabled = fe_enabled_;
    opt.ferro.update_state = history_updates_enabled_;
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
        const bool strong_dos_heterogeneity = [&]() {
            real_t nc_min = TCAD_CONST(1.0e300), nc_max = TCAD_CONST(0.0);
            real_t nv_min = TCAD_CONST(1.0e300), nv_max = TCAD_CONST(0.0);
            real_t eg_min = TCAD_CONST(1.0e300), eg_max = -TCAD_CONST(1.0e300);
            for (size_t i = 0; i < N; ++i) {
                if (Nc_[i] > TCAD_CONST(0.0) && std::isfinite((double)Nc_[i])) {
                    nc_min = std::min(nc_min, Nc_[i]);
                    nc_max = std::max(nc_max, Nc_[i]);
                }
                if (Nv_[i] > TCAD_CONST(0.0) && std::isfinite((double)Nv_[i])) {
                    nv_min = std::min(nv_min, Nv_[i]);
                    nv_max = std::max(nv_max, Nv_[i]);
                }
                if (std::isfinite((double)Eg_[i])) {
                    eg_min = std::min(eg_min, Eg_[i]);
                    eg_max = std::max(eg_max, Eg_[i]);
                }
            }
            const bool nc_spread =
                nc_max > TCAD_CONST(0.0) && nc_min < TCAD_CONST(1.0e300) &&
                (nc_min < TCAD_CONST(1.0e24) || nc_max / std::max(nc_min, TCAD_CONST(1.0)) > TCAD_CONST(20.0));
            const bool nv_spread =
                nv_max > TCAD_CONST(0.0) && nv_min < TCAD_CONST(1.0e300) &&
                (nv_min < TCAD_CONST(1.0e24) || nv_max / std::max(nv_min, TCAD_CONST(1.0)) > TCAD_CONST(20.0));
            const bool eg_spread =
                eg_max > -TCAD_CONST(1.0e299) && eg_min < TCAD_CONST(1.0e299) &&
                (eg_max - eg_min) > TCAD_CONST(0.5);
            return nc_spread || nv_spread || eg_spread;
        }();
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
            (quantum_enabled_ && !independent_dg_potential_pde) ||
            strong_dos_heterogeneity;
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
        gummel_.set_edge_permittivity(
            edge_eps_x_plus_, edge_eps_x_minus_, edge_eps_y_plus_, edge_eps_y_minus_,
            edge_eps_z_plus_, edge_eps_z_minus_);
        // Inject the persistent vector P so this bias point continues from the
        // previous one (path dependence -> hysteresis). GummelSolver (and its
        // PoissonSolver.fe_polarization_) is rebuilt every solve(); without
        // this injection P would be reset to zero and no loop could form.
        if (fe_enabled_) {
            if (!fe_polarization_init_) {
                fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
                fe_polarization_init_ = true;
            }
            gummel_.set_fe_polarization(fe_polarization_);
            // Inject the persistent Preisach play state (M7c).
            if (fe_model_ == 1 || fe_model_ == 3) {
                const size_t state_size = (fe_model_ == 3) ? 2 * N : N;
                if (fe_play_state_.size() < state_size ||
                    (fe_model_ == 1 && fe_play_state_.size() != state_size))
                    fe_play_state_.assign(state_size, TCAD_CONST(0.0));
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
            record_gummel(gummel_ok);
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
            nopt.record_nonlinear_history = nonlinear_history_enabled_;
            // set_gummel_max_iter() controls the inexpensive block warm-up.
            // Reusing a 600-step quantum-Gummel budget here allowed a failed
            // quad-precision Newton rescue to burn several minutes before the
            // caller could apply its voltage-bisection fallback.  A coupled
            // Newton solve that has not converged in 60 iterations is stalled,
            // not under-budgeted; retain smaller caller limits but cap only
            // this rescue stage.
            nopt.max_iter = std::min(max_iter_, size_t{60});
            nopt.tol = (double)tol_;
            nopt.abs_tol = TCAD_CONST(1e-20);
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
            nopt.additive_log_density_update = newton_additive_log_density_update_;
            nopt.jacobian_reuse_threshold = newton_jacobian_reuse_threshold_;
            nopt.enable_btbt = btbt_enabled_;
            nopt.hfs_enabled = hfs_enabled_;
            nopt.hfs_vsat_n = hfs_vsat_n_;
            nopt.hfs_vsat_p = hfs_vsat_p_;
            nopt.hfs_beta_n = hfs_beta_n_;
            nopt.hfs_beta_p = hfs_beta_p_;
            nopt.hfs_refdens_n = hfs_refdens_n_; nopt.hfs_refdens_p = hfs_refdens_p_;
            nopt.hfs_driving = hfs_driving_;
            nopt.hfs_qf_at_contacts = hfs_qf_at_contacts_;
            nopt.hfs_low_field_cutoff = hfs_low_field_cutoff_;
            nopt.enable_quantum = quantum_enabled_;
            nopt.btbt_A = btbt_A_;
            nopt.btbt_B = btbt_B_;
            nopt.btbt_D = btbt_D_;
            nopt.btbt_field_mode = btbt_field_mode_;
            nopt.btbt_field_cap = btbt_field_cap_;
            nopt.btbt_field_alpha = btbt_field_alpha_;
            nopt.btbt_field_ref = btbt_field_ref_;
            nopt.btbt_continuity_scale = btbt_continuity_scale_;
            nopt.btbt_weight = btbt_weight_;
            nopt.btbt_use_nonlocal = btbt_use_nonlocal_;
            nopt.btbt_nonlocal_mass = btbt_nonlocal_mass_;
            nopt.btbt_tunnel_path_frac = btbt_tunnel_path_frac_;
            nopt.btbt_wkb_npts = btbt_wkb_npts_;
            nopt.ii_driving = ii_driving_; nopt.ii_refdens_n = ii_refdens_n_; nopt.ii_refdens_p = ii_refdens_p_;
            nopt.enable_ii = ii_enabled_;
            nopt.ii_A_n = ii_A_n_;
            nopt.ii_B_n = ii_B_n_;
            nopt.ii_A_p = ii_A_p_;
            nopt.ii_B_p = ii_B_p_;
            nopt.ii_E_floor = ii_field_floor_;
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
            const bool gummel_n_settled = gummel_n_update >= TCAD_CONST(0.0) &&
                gummel_n_update < tol_;
            const bool gummel_p_settled = gummel_p_update >= TCAD_CONST(0.0) &&
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
            if (!trap_mask_.empty() || !Q_ot_.empty()) {
                newton_.set_trap_charge(trap_mask_, trap_D_it_, trap_E_t_, Q_ot_);
            }
            // DG semiconductor mask for Newton (same as Gummel)
            if (quantum_enabled_ && !mu_n_eff.empty()) {
                std::vector<char> semi(N, 0);
                for (size_t i = 0; i < N; ++i)
                    semi[i] = (mu_n_eff[i] > TCAD_CONST(1e-30) || mu_p_eff[i] > TCAD_CONST(1e-30)) ? 1 : 0;
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
                !independent_dg_potential_pde && !unsupported_newton_wkb) {
                newton_ok = newton_.solve(res.phi, res.n, res.p);
                if (nonlinear_history_enabled_)
                    res.nonlinear_history.push_back({"newton", newton_ok,
                        -TCAD_CONST(1.0), newton_.nonlinear_samples()});
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
            if (newton_ok) res.quantum_residual = TCAD_CONST(0.0);
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
                std::isfinite((double)res.poisson_residual) &&
                (!fe_enabled_ || !newton_ok ||
                 res.poisson_residual < opt.frozen_residual_gate);
            accepted_gummel_state = gummel_ok && !newton_ok;
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
                    if (unsupported_newton_wkb)
                        std::cerr << "Newton fallback unavailable for nonlocal BTBT feedback; ";
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
        gummel_.set_edge_permittivity(
            edge_eps_x_plus_, edge_eps_x_minus_, edge_eps_y_plus_, edge_eps_y_minus_,
            edge_eps_z_plus_, edge_eps_z_minus_);
        if (fe_enabled_) {
            if (!fe_polarization_init_) {
                fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
                fe_polarization_init_ = true;
            }
            gummel_.set_fe_polarization(fe_polarization_);
            if (fe_model_ == 1 || fe_model_ == 3) {
                const size_t state_size = (fe_model_ == 3) ? 2 * N : N;
                if (fe_play_state_.size() < state_size ||
                    (fe_model_ == 1 && fe_play_state_.size() != state_size))
                    fe_play_state_.assign(state_size, TCAD_CONST(0.0));
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
        record_gummel(res.converged);
        size_t gummel_iters_total = gummel_.poisson_residuals().size();
        // Classical drift-diffusion problems with strong uniform generation
        // can be contracting but still miss the caller's per-solve max_iter
        // by a small tail.  A second solve at the same bias starts from the
        // finite state just produced and is equivalent to an internal
        // continuation of the fixed-point iteration.  Keep this retry out of
        // history-dependent models (FE, breakdown) and quantum transport,
        // where an extra solve would also advance hidden state.
        const bool has_optical_generation = [&]() {
            for (const real_t value : G_opt_)
                if (abs_q(value) > TCAD_CONST(0.0)) return true;
            return false;
        }();
        if (!res.converged && has_optical_generation &&
            !fe_enabled_ && !bd_enabled_ && !quantum_enabled_ &&
            finite_vector(res.phi) && finite_vector(res.n) &&
            finite_vector(res.p)) {
            constexpr size_t same_bias_retries = 2;
            for (size_t retry = 0; retry < same_bias_retries; ++retry) {
                res.converged = gummel_.solve(res.phi, res.n, res.p);
                record_gummel(res.converged);
                gummel_iters_total += gummel_.poisson_residuals().size();
                if (res.converged ||
                    !finite_vector(res.phi) ||
                    !finite_vector(res.n) ||
                    !finite_vector(res.p))
                    break;
            }
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
        res.iterations = gummel_iters_total;
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
        const real_t CARR_FLOOR = TCAD_CONST(1e6);    // m^-3  (1 cm^-3)
        const real_t CARR_CEIL  = TCAD_CONST(1e28);   // m^-3  (1e22 cm^-3, above any doping)
        const real_t PHI_CEIL   = TCAD_CONST(50.0);   // V
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

    // Dielectric breakdown detection (M7b, audit §22).  After the field is
    // known, flag any masked dielectric node whose |E| exceeds its material
    // breakdown field E_bd.  The flip is IRREVERSIBLE (bd_state_ only goes 0->1)
    // and persists across solve() calls — a broken-down oxide node stays broken
    // down on subsequent (even lower) bias points, modelling the conductive
    // filament.  The leakage term itself is applied on the NEXT solve() via
    // set_breakdown_state above (this solve already assembled without it).
    std::vector<char> bd_state_detected = bd_state_;
    if (history_updates_enabled_ && bd_enabled_ && !bd_mask_.empty() && E_bd_.size() == N) {
        for (size_t i = 0; i < N; ++i) {
            if (!bd_mask_[i] || bd_state_[i]) continue;   // skip non-dielectric / already broken
            real_t E2 = res.Ex[i] * res.Ex[i] + res.Ey[i] * res.Ey[i] + res.Ez[i] * res.Ez[i];
            if (E_bd_[i] > TCAD_CONST(0.0) && E2 > E_bd_[i] * E_bd_[i]) {
                bd_state_detected[i] = 1;   // candidate, committed only on acceptance
            }
        }
    }

    // Full-precision edge current densities (Audit §20).  Computed in
    // __float128 from the converged phi/n/p to avoid the catastrophic
    // cancellation of double-precision Python re-derivation.
    const std::vector<real_t>* transport_Qn = nullptr;
    const std::vector<real_t>* transport_Qp = nullptr;
    if (quantum_enabled_ && accepted_gummel_state) {
        transport_Qn = &gummel_.transport_quantum_n();
        transport_Qp = &gummel_.transport_quantum_p();
    }
    compute_edge_currents(res, res.phi, res.n, res.p,
                          transport_Qn, transport_Qp);
    // Generation and returned currents must describe the identical flux Q,
    // including a committed lagged Gummel state or a failed-state rebuild.
    gummel_.evaluate_impact_ionization(res.phi, res.n, res.p, res.G_ii,
        transport_Qn ? transport_Qn : &res.Qn,
        transport_Qp ? transport_Qp : &res.Qp);

    // Thermal coupling (self-heating)
    if (thermal_coupling_enabled_ && res.converged) {
        res.temperature.assign(N, ambient_temperature_);
        
        // Compute carrier Joule heating from the *net SG current*, not
        // sigma*|E|^2.  In a junction at equilibrium drift and diffusion
        // cancel (J=0) despite a large built-in field; sigma*E^2 therefore
        // created spurious zero-bias heating.  Deposit each edge's J.E half
        // to either endpoint to preserve the finite-volume energy balance.
        std::vector<real_t> power(N, TCAD_CONST(0.0)), volume(N);
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i)
                    volume[g_.index(i,j,k)] = g_.dx_cell(i)*g_.dy_cell(j)*g_.dz_cell(k);
        // Split integrated edge power [W], then divide by each node's own
        // volume. Splitting W/m^3 directly loses power on a graded grid.
        auto deposit = [&](size_t idx, size_t nbr, int axis, real_t distance, real_t qdot) {
            const size_t i=idx%g_.nx, j=(idx/g_.nx)%g_.ny, k=idx/(g_.nx*g_.ny);
            const real_t area = axis==0 ? g_.dy_cell(j)*g_.dz_cell(k)
                : axis==1 ? g_.dx_cell(i)*g_.dz_cell(k) : g_.dx_cell(i)*g_.dy_cell(j);
            const real_t half_power = TCAD_CONST(0.5)*qdot*distance*area;
            power[idx] += half_power/volume[idx];
            power[nbr] += half_power/volume[nbr];
        };
        // In a steady 1-D device div(Jn+Jp)=0, so the physically admissible
        // total-current field is constant.  Contact Dirichlet edges can carry
        // large cancellation spikes even when the coupled residual passes;
        // feeding those spikes into J.E creates a false contact hotspot.  Use
        // the robust L1 (median) conservative projection for heat deposition,
        // while leaving the raw edge currents untouched for explicit KCL QA.
        bool project_1d_current = (!lattice_feedback_enabled_ && g_.ny == 1 && g_.nz == 1 && g_.nx > 4);
        real_t projected_Jx = TCAD_CONST(0.0);
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
                        deposit(idx, nbr, axis, d, qdot);
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
                        if (J_ax[idx] == TCAD_CONST(0.0)) continue;
                        real_t d = (axis == 0) ? g_.dx_edge(i)
                                 : (axis == 1) ? g_.dy_edge(j) : g_.dz_edge(k);
                        real_t E_axis = -(res.phi[nbr] - res.phi[idx]) / d;
                        real_t qdot = abs_q(J_ax[idx] * E_axis);
                        deposit(idx, nbr, axis, d, qdot);
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
        thermal_opt.tol = TCAD_CONST(1e-12);
        thermal_solver.set_solver_options(thermal_opt);
        thermal_solver.assemble_thermal(power, lattice_heat_capacity_, lattice_previous_temperature_, lattice_dt_);
        
        res.thermal.linear_solve_converged = thermal_solver.solve(res.temperature);
        if (!res.thermal.linear_solve_converged) {
            std::cerr << "Thermal solve failed\n";
            res.converged = false;
        } else {
            auto& ledger = res.thermal;
            ledger.mobility_feedback = lattice_feedback_enabled_;
            ledger.carrier_temperature = temperature_; ledger.carrier_VT = VT_;
            ledger.mobility_temperature = mobility_temperature_.empty()
                ? std::vector<real_t>(N, temperature_) : mobility_temperature_;
            transport_mobilities(ledger.mobility_n, ledger.mobility_p);
            ledger.transient_storage = lattice_dt_ > TCAD_CONST(0.0);
            ledger.dt = lattice_dt_;
            ledger.previous_temperature = lattice_previous_temperature_;
            ledger.heat_capacity = lattice_heat_capacity_;
            ledger.node_storage_power.assign(N, TCAD_CONST(0.0));
            ledger.current_projected = project_1d_current;
            ledger.projected_Jx = projected_Jx;
            ledger.node_volumes = volume;
            ledger.power_density = power;
            ledger.flux_x.assign(N, TCAD_CONST(0.0));
            ledger.flux_y.assign(N, TCAD_CONST(0.0));
            ledger.flux_z.assign(N, TCAD_CONST(0.0));
            ledger.bath_heat.assign(N, TCAD_CONST(0.0));
            std::vector<real_t> divergence(N, TCAD_CONST(0.0));
            std::vector<real_t>* flux[3] = {&ledger.flux_x, &ledger.flux_y, &ledger.flux_z};
            const size_t count[3] = {g_.nx,g_.ny,g_.nz}, stride[3] = {1,g_.nx,g_.nx*g_.ny};
            for (size_t idx=0; idx<N; ++idx) {
                const size_t coordinate[3] = {idx%g_.nx,(idx/g_.nx)%g_.ny,idx/(g_.nx*g_.ny)};
                const real_t width[3] = {g_.dx_cell(coordinate[0]),g_.dy_cell(coordinate[1]),g_.dz_cell(coordinate[2])};
                for (int axis=0; axis<3; ++axis) {
                    if (coordinate[axis]+1 == count[axis]) continue;
                    const size_t nbr=idx+stride[axis];
                    const real_t distance=axis==0 ? g_.dx_edge(coordinate[0])
                        : axis==1 ? g_.dy_edge(coordinate[1]) : g_.dz_edge(coordinate[2]);
                    const real_t conductance=TCAD_CONST(2.0)*thermal_conductivity_[idx]*thermal_conductivity_[nbr]/
                        (thermal_conductivity_[idx]+thermal_conductivity_[nbr])*
                        width[(axis+1)%3]*width[(axis+2)%3]/distance;
                    const real_t value=conductance*(res.temperature[idx]-res.temperature[nbr]);
                    (*flux[axis])[idx]=value;
                    divergence[idx]+=value; divergence[nbr]-=value;
                }
            }
            for (const auto& [idx,value] : tbc) {
                ledger.bath_nodes.push_back(idx);
                ledger.bath_temperatures.push_back(value);
            }
            for (size_t idx=0; idx<N; ++idx) {
                const real_t input=power[idx]*volume[idx];
                const real_t storage = ledger.transient_storage ? lattice_heat_capacity_[idx]*volume[idx]*
                    (res.temperature[idx]-lattice_previous_temperature_[idx])/lattice_dt_ : TCAD_CONST(0.0);
                ledger.node_storage_power[idx] = storage; ledger.storage_power += storage;
                ledger.source_power+=input;
                if (tbc.count(idx)) {
                    // Heat deposited on pinned nodes goes straight to the
                    // bath; it is absent from the free-node linear equations.
                    ledger.bath_heat[idx]=input-divergence[idx]-storage;
                    ledger.outward_heat+=ledger.bath_heat[idx];
                } else {
                    ledger.max_cell_residual=std::max(ledger.max_cell_residual,abs_q(divergence[idx]+storage-input));
                }
            }
            ledger.balance_residual=ledger.source_power-ledger.outward_heat-ledger.storage_power;
            auto finite = [](real_t v) { return isfinite_q(v) && std::isfinite((double)v)
                && (v==TCAD_CONST(0.0) || (double)v!=0.0); };
            ledger.available = finite(ledger.source_power) && finite(ledger.outward_heat)
                && finite(ledger.balance_residual) && finite(ledger.max_cell_residual) && finite(ledger.storage_power)
                && std::all_of(res.temperature.begin(),res.temperature.end(),[&](real_t v) { return finite(v) && v>TCAD_CONST(0.0); });
            for (const auto* values : {&ledger.node_volumes,&ledger.power_density,&ledger.flux_x,
                                      &ledger.flux_y,&ledger.flux_z,&ledger.bath_heat,
                                      &ledger.mobility_temperature,&ledger.mobility_n,&ledger.mobility_p,
                                      &ledger.node_storage_power})
                ledger.available = ledger.available && std::all_of(values->begin(),values->end(),finite);
            if (!ledger.available) res.converged=false;
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
        real_t relative_spread = absolute_spread / (jabs + TCAD_CONST(1e-30));
        if (absolute_spread > TCAD_CONST(1.0e-8) && relative_spread > TCAD_CONST(1.0e-2)) {
            std::cerr << "Electrothermal KCL gate rejected state: relative "
                      << "current spread=" << (double)relative_spread << "\n";
            res.converged = false;
        }
    }

    audit_steady_equations(res);

    // A DeviceSimulator instance represents one device along a bias sweep.
    // Retain an honestly converged state as the default initial guess for the
    // next solve.  Previously the low-level API silently restarted every bias
    // point from charge-neutral equilibrium unless callers manually copied
    // phi/n/p back with set_initial_guess(); NLS/Preisach branches and abrupt
    // FinFET/GAA sweeps then left the convergence basin despite a good previous
    // solution being available.
    // Newly detected dielectric filaments affect the next solve, keeping the
    // electrical result, reported current, and heat source synchronized.
    if (res.converged) {
        // Transport Q must advance with the accepted electrical seed. A
        // converged Gummel stage can still fail the final finite-field,
        // thermal or KCL gates. Committing earlier left retries paired with
        // Q from a rejected step, even though phi/n/p were rolled back.
        const bool commit_transport_Q = accepted_gummel_state && dg_potential_form_enabled_ &&
            gummel_.transport_quantum_n().size() == N &&
            gummel_.transport_quantum_p().size() == N;
        // Prepare all allocating copies before touching the accepted seed or
        // its paired transport Q. An exception must not leave a new phi with
        // old carriers, or a single new quantum potential. Material memory is
        // protected by material_attempt throughout this preparation.
        auto next_phi = res.phi;
        auto next_n = res.n;
        auto next_p = res.p;
        std::vector<real_t> next_Qn, next_Qp;
        if (commit_transport_Q) {
            next_Qn = gummel_.transport_quantum_n();
            next_Qp = gummel_.transport_quantum_p();
        }
        // No allocations or throwing operations past this point. This is an
        // exception guarantee for a single-threaded attempt, not a concurrent
        // snapshot or an asynchronous interruption protocol.
        if (commit_transport_Q) {
            dg_transport_Qn_.swap(next_Qn);
            dg_transport_Qp_.swap(next_Qp);
        }
        bd_state_.swap(bd_state_detected);
        init_phi_.swap(next_phi);
        init_n_.swap(next_n);
        init_p_.swap(next_p);
        has_initial_guess_ = true;
        material_attempt.accepted = true;
    }

    return res;
}

void DeviceSimulator::audit_steady_equations(SimulationResult& res, bool include_newton) {
    // Reassemble the returned fields, including rollback and failed-state
    // clipping.  History samples and Newton's stopping metric are different
    // diagnostics.  Never extend the SG audit to unsupported transport states.
    if ((use_newton_ && !include_newton) || (!use_newton_ && include_newton)) return;
    if (use_newton_) {
        const auto uniform = [](const std::vector<real_t>& v) {
            return !v.empty() && std::all_of(v.begin(), v.end(),
                [&](real_t x) { return x == v.front(); });
        };
        const auto zero = [](const auto& v) {
            return std::all_of(v.begin(), v.end(), [](auto x) { return x == 0; });
        };
        const auto mobile = [](const auto& v) {
            return std::all_of(v.begin(), v.end(), [](real_t x) { return x > EPSILON; });
        };
        const bool basic_quantum = !dg_potential_form_enabled_ &&
            !dg_silicon_multivalley_ && !dg_step_boundary_enabled_ &&
            dg_interface_distance_factor_ == TCAD_CONST(1.0) &&
            uniform(mu_n_) && uniform(mu_p_);
        const bool supported = (!quantum_enabled_ || basic_quantum) &&
            statistics_type_ == StatisticsType::BOLTZMANN &&
            ((g_.nx > 1) + (g_.ny > 1) + (g_.nz > 1) == 1) &&
            uniform(Nc_) && uniform(Nv_) && uniform(Eg_) &&
            mobility_model_type_ == MobilityModelType::CONSTANT &&
            mobile(mu_n_) && mobile(mu_p_) && ohmic_nodes_.empty() &&
            !btbt_enabled_ && !fe_enabled_ &&
            !leak_enabled_ && !bd_enabled_ && !thermal_coupling_enabled_ &&
            !lattice_feedback_enabled_ && lattice_dt_ == TCAD_CONST(0.0) &&
            zero(trap_mask_) && zero(Q_ot_) &&
            !newton_freeze_phi_ && !newton_freeze_n_ && !newton_freeze_p_;
        if (!supported) {
            res.steady_gummel_audit.clear();
            res.steady_gummel_audit_status = "unsupported_newton_audit_physics";
            return;
        }
    }
    if (!quantum_enabled_ || use_newton_) {
        try {
            const real_t gate = std::min(std::max(TCAD_CONST(100.0) * tol_,
                TCAD_CONST(1.0e-8)), TCAD_CONST(1.0e-4));
            std::pair<real_t,real_t> carrier_rows;
            if (quantum_enabled_) {
                const size_t N = g_.npts();
                if (res.phi.size() != N || res.n.size() != N || res.p.size() != N)
                    throw std::invalid_argument("quantum returned audit requires full states");
                for (size_t i = 0; i < N; ++i)
                    if (!isfinite_q(res.phi[i]) || !isfinite_q(res.n[i]) ||
                        !isfinite_q(res.p[i]) || res.n[i] < 0 || res.p[i] < 0)
                        throw std::invalid_argument("quantum returned audit requires finite physical states");
                // Recompute from the actual returned densities, not either
                // solver's lagged cache or previously exported result Q.
                DensityGradient physical_dg(dg_);
                physical_dg.set_semiconductor_mask(std::vector<char>(N, 1));
                physical_dg.set_thermal_voltage(VT_);
                std::vector<real_t> Qn, Qp;
                physical_dg.quantum_potential(res.n, res.p, Qn, Qp);
                detail::pin_quantum_contacts(n_bc_, p_bc_, Qn, Qp);
                carrier_rows = gummel_.compute_quantum_continuity_residuals(
                    res.phi, res.n, res.p, Qn, Qp);
            } else {
                carrier_rows = gummel_.compute_continuity_residuals(
                    res.phi, res.n, res.p);
            }
            const real_t poisson_row = gummel_.compute_poisson_residual(
                res.phi, res.n, res.p, true);
            const bool rows_pass = std::max(poisson_row,
                std::max(carrier_rows.first, carrier_rows.second)) < gate;
            res.steady_gummel_audit = {poisson_row, carrier_rows.first,
                carrier_rows.second, gate, tol_, real_t(rows_pass)};
            res.steady_gummel_audit_status = quantum_enabled_
                ? "available_quantum_newton_sg"
                : (use_newton_ ? "available_newton_sg" : "available");
        } catch (const std::exception& error) {
            res.steady_gummel_audit.clear();
            // A failed FE solve can leave nonfinite hidden field caches even
            // when the returned electrical iterate has been made finite.
            // Optional telemetry must not replace that honest failure result
            // with an exception or fabricate passing equation residuals.
            res.steady_gummel_audit_status =
                std::string("reassembly_failed: ") + error.what();
        }
    }

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
        if (x > TCAD_CONST(100.0)) return TCAD_CONST(0.0);
        if (x < -TCAD_CONST(100.0)) return -x;
        if (x > -TCAD_CONST(1e-10) && x < TCAD_CONST(1e-10)) {
            // Taylor: 1 - x/2 + x^2/12
            return TCAD_CONST(1.0) - x / TCAD_CONST(2.0) + x * x / TCAD_CONST(12.0);
        }
        return x / expm1_q(x);
    };

    res.Jn_x.assign(N, TCAD_CONST(0.0)); res.Jn_y.assign(N, TCAD_CONST(0.0)); res.Jn_z.assign(N, TCAD_CONST(0.0));
    res.Jp_x.assign(N, TCAD_CONST(0.0)); res.Jp_y.assign(N, TCAD_CONST(0.0)); res.Jp_z.assign(N, TCAD_CONST(0.0));

    // Use the same DG-shifted transport potential as the continuity solver.
    // Recomputing terminal currents from classical phi after a quantum solve
    // produced non-conservative currents and even the wrong sign near threshold.
    std::vector<real_t> Qn(N, TCAD_CONST(0.0)), Qp(N, TCAD_CONST(0.0));
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
        for (const auto& bc : n_bc_) Qn[bc.first] = TCAD_CONST(0.0);
        for (const auto& bc : p_bc_) Qp[bc.first] = TCAD_CONST(0.0);
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

    std::vector<real_t> mu_n_eff, mu_p_eff;
    transport_mobilities(mu_n_eff, mu_p_eff);
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
                    real_t mu_ne = TCAD_CONST(2.0) * mu_n_eff[idx] * mu_n_eff[nbr] / (mu_n_eff[idx] + mu_n_eff[nbr] + TCAD_CONST(1e-30));
                    // High-field saturation must reduce the POST-PROCESSING
                    // edge mobility identically to the continuity equation,
                    // otherwise terminal currents ignore the model (found by
                    // the 1-D resistor analytic golden).  The driving force
                    // here uses the CONVERGED quasi-Fermi gradient - the
                    // self-consistent force at the returned state.
                    if (hfs_enabled_) {
                        real_t efn_i = (phi[idx] + Qn_flux[idx])
                            - VT_ * log_q(hfs_reference_carrier(n[idx], hfs_refdens_n_) / std::max(Nc_[idx], TCAD_CONST(1.0)));
                        real_t efn_j = (phi[nbr] + Qn_flux[nbr])
                            - VT_ * log_q(hfs_reference_carrier(n[nbr], hfs_refdens_n_) / std::max(Nc_[nbr], TCAD_CONST(1.0)));
                        real_t force = abs_q(efn_j - efn_i) / d;
                        if (hfs_edge_driving(hfs_driving_, hfs_qf_at_contacts_, n_bc_.count(idx) || n_bc_.count(nbr)) == 1)
                            force = abs_q((phi[nbr] + Qn_flux[nbr]) - (phi[idx] + Qn_flux[idx])) / d;
                        force = hfs_active_driving_force(force, hfs_low_field_cutoff_);
                        real_t ratio = mu_ne * force / hfs_vsat_n_;
                        if (ratio > TCAD_CONST(1.0e-12))
                            mu_ne /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, hfs_beta_n_), TCAD_CONST(1.0) / hfs_beta_n_);
                    }
                    real_t mu_pe = TCAD_CONST(2.0) * mu_p_eff[idx] * mu_p_eff[nbr] / (mu_p_eff[idx] + mu_p_eff[nbr] + TCAD_CONST(1e-30));
                    if (hfs_enabled_) {
                        real_t efp_i = (phi[idx] - Qp_flux[idx])
                            + VT_ * log_q(hfs_reference_carrier(p[idx], hfs_refdens_p_) / std::max(Nv_[idx], TCAD_CONST(1.0)));
                        real_t efp_j = (phi[nbr] - Qp_flux[nbr])
                            + VT_ * log_q(hfs_reference_carrier(p[nbr], hfs_refdens_p_) / std::max(Nv_[nbr], TCAD_CONST(1.0)));
                        real_t force = abs_q(efp_j - efp_i) / d;
                        if (hfs_edge_driving(hfs_driving_, hfs_qf_at_contacts_, p_bc_.count(idx) || p_bc_.count(nbr)) == 1)
                            force = abs_q((phi[nbr] - Qp_flux[nbr]) - (phi[idx] - Qp_flux[idx])) / d;
                        force = hfs_active_driving_force(force, hfs_low_field_cutoff_);
                        real_t ratio = mu_pe * force / hfs_vsat_p_;
                        if (ratio > TCAD_CONST(1.0e-12))
                            mu_pe /= pow_q(TCAD_CONST(1.0) + pow_q(ratio, hfs_beta_p_), TCAD_CONST(1.0) / hfs_beta_p_);
                    }
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
    res.Jleak_x.assign(N, TCAD_CONST(0.0));
    res.Jleak_y.assign(N, TCAD_CONST(0.0));
    res.Jleak_z.assign(N, TCAD_CONST(0.0));
    const bool have_pf_fn = leak_enabled_ && leak_mask_.size() == N;
    const bool have_breakdown = bd_enabled_ && bd_state_.size() == N &&
                                bd_mask_.size() == N && sigma_bd_ > TCAD_CONST(0.0);
    if (!have_pf_fn && !have_breakdown) return;

    auto conductivity = [&](real_t E_mag, real_t E_axis) -> real_t {
        if (E_mag <= leak_E_floor_) return TCAD_CONST(0.0);
        real_t sigma = TCAD_CONST(0.0);  // [S/m]
        if (leak_C_pf_ > TCAD_CONST(0.0) && leak_phi_t_ > TCAD_CONST(0.0)) {
            real_t arg = leak_B_pf_ * sqrt_q(leak_phi_t_ / E_mag);
            sigma += leak_C_pf_ * exp_q(-arg);
        }
        real_t C_fn = leak_C_fn_;
        real_t B_fn = leak_B_fn_;
        if (leak_fn_polarity_enabled_) {
            if (E_axis >= TCAD_CONST(0.0)) {
                C_fn = leak_C_fn_positive_;
                B_fn = leak_B_fn_positive_;
            } else {
                C_fn = leak_C_fn_negative_;
                B_fn = leak_B_fn_negative_;
            }
        }
        if (C_fn > TCAD_CONST(0.0) && leak_phi_b_ > TCAD_CONST(0.0)) {
            real_t arg = B_fn * pow_q(leak_phi_b_, TCAD_CONST(1.5)) / E_mag;
            // J_FN=C_fn*E^2*exp(-arg), hence sigma_FN=J/E.
            sigma += C_fn * E_mag * exp_q(-arg);
        }
        if (leak_sigma_cap_ > TCAD_CONST(0.0) && sigma > leak_sigma_cap_)
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
                    real_t E_mag = TCAD_CONST(0.5) * (sqrt_q(E2_i) + sqrt_q(E2_j));
                    if (E_mag < abs_q(E_axis)) E_mag = abs_q(E_axis);
                    real_t sigma = pf_edge ? conductivity(E_mag, E_axis) : TCAD_CONST(0.0);
                    if (bd_edge) sigma += sigma_bd_;
                    J_ax[idx] = sigma * E_axis;
                }
    };
    fill_leak_axis(res.Jleak_x, 0, 1,             g_.nx - 1, g_.ny,     g_.nz);
    fill_leak_axis(res.Jleak_y, 1, g_.nx,         g_.nx,     g_.ny - 1, g_.nz);
    fill_leak_axis(res.Jleak_z, 2, g_.nx * g_.ny, g_.nx,     g_.ny,     g_.nz - 1);
}

void DeviceSimulator::add_transient_electrostatic_ledger(
    SimulationResult& state, const SimulationResult* previous) const {
    const size_t N = g_.npts();
    if (state.phi_frozen) return;
    for (real_t epsilon : eps_)
        if (!isfinite_q(epsilon) || epsilon < EPSILON) return;

    const size_t count[3] = {g_.nx, g_.ny, g_.nz};
    const size_t stride[3] = {1, g_.nx, g_.nx * g_.ny};
    const std::vector<real_t>* plus[3] = {
        &edge_eps_x_plus_, &edge_eps_y_plus_, &edge_eps_z_plus_};
    const std::vector<real_t>* minus[3] = {
        &edge_eps_x_minus_, &edge_eps_y_minus_, &edge_eps_z_minus_};
    std::vector<real_t>* D[3] = {&state.D_x, &state.D_y, &state.D_z};
    auto epsilon_face = [&](size_t node, size_t neighbor,
                            const std::vector<real_t>& values) {
        if (values.size() == N && values[node] > TCAD_CONST(0.0)) return values[node];
        return TCAD_CONST(2.0) * eps_[node] * eps_[neighbor] / (eps_[node] + eps_[neighbor]);
    };
    const bool interval = state.converged && state.accepted_dt > TCAD_CONST(0.0) && previous &&
        previous->electrostatic_flux_available;
    std::vector<real_t>* Jdisp[3] = {&state.Jdisp_x, &state.Jdisp_y, &state.Jdisp_z};
    std::vector<real_t>* Jelectric[3] = {&state.Jdielectric_x, &state.Jdielectric_y, &state.Jdielectric_z};
    std::vector<real_t>* Jpolar[3] = {&state.Jpolarization_x, &state.Jpolarization_y, &state.Jpolarization_z};
    std::vector<real_t> delta_phi, delta_polarization;
    if (interval) {
        delta_phi.resize(N);
        for (size_t idx = 0; idx < N; ++idx) delta_phi[idx] = state.phi[idx] - previous->phi[idx];
        if (fe_enabled_) {
            delta_polarization.resize(3 * N);
            for (size_t idx = 0; idx < 3 * N; ++idx)
                delta_polarization[idx] = state.P[idx] - previous->P[idx];
        }
        for (int axis = 0; axis < 3; ++axis) {
            Jdisp[axis]->assign(N, TCAD_CONST(0.0));
            Jelectric[axis]->assign(N, TCAD_CONST(0.0));
            Jpolar[axis]->assign(N, TCAD_CONST(0.0));
        }
    }
    for (auto values : D) values->assign(N, TCAD_CONST(0.0));
    for (size_t idx = 0; idx < N; ++idx)
        for (int axis = 0; axis < 3; ++axis) {
            const size_t coordinate = (idx / stride[axis]) % count[axis];
            if (coordinate + 1 == count[axis]) continue;
            const size_t neighbor = idx + stride[axis];
            const real_t epsilon = epsilon_face(idx, neighbor, *plus[axis]);
            const real_t backward = epsilon_face(neighbor, idx, *minus[axis]);
            // One shared face flux requires reciprocal endpoint coefficients.
            // Check reciprocity in the same pass that computes D and currents.
            if (!isfinite_q(epsilon) || epsilon <= TCAD_CONST(0.0) || epsilon != backward) return;
            const real_t edge = axis == 0 ? g_.dx_edge(coordinate)
                : axis == 1 ? g_.dy_edge(coordinate) : g_.dz_edge(coordinate);
            real_t value = -epsilon * (state.phi[neighbor] - state.phi[idx]) / edge;
            if (fe_enabled_)
                value += polarization_face(fe_mask_, state.P, eps_, idx, neighbor, axis, epsilon);
            (*D[axis])[idx] = value;
            if (interval) {
                // Difference the independently stored components before adding
                // their large static backgrounds. Subtracting D_new-D_old can
                // erase a resolved small P increment even in quad precision.
                const real_t electric_increment = -epsilon *
                    (delta_phi[neighbor] - delta_phi[idx]) / edge;
                const real_t polar_increment = fe_enabled_
                    ? polarization_face(fe_mask_, delta_polarization, eps_,
                                        idx, neighbor, axis, epsilon) : TCAD_CONST(0.0);
                (*Jelectric[axis])[idx] = electric_increment / state.accepted_dt;
                (*Jpolar[axis])[idx] = polar_increment / state.accepted_dt;
                (*Jdisp[axis])[idx] = (electric_increment + polar_increment) / state.accepted_dt;
            }
        }
    state.electrostatic_flux_available = true;
    state.displacement_current_available = interval;

    // Terminal charge/current scope: complete, equipotential outer planes
    // with unit charge volumes. Contact nodes and inter-contact edges belong
    // to reservoirs; integrate only faces joining an electrode to free volume.
    for (real_t fraction : charge_volume_fraction_)
        if (fraction != TCAD_CONST(1.0)) return;
    std::vector<char> electrodes(N, 0);
    for (int axis = 0; axis < 3; ++axis) {
        if (count[axis] < 2) continue;
        for (int upper = 0; upper < 2; ++upper) {
            const size_t coordinate = upper ? count[axis] - 1 : 0;
            bool complete = true, voltage_set = false;
            real_t voltage = TCAD_CONST(0.0);
            for (size_t idx = 0; idx < N; ++idx) {
                if ((idx / stride[axis]) % count[axis] != coordinate) continue;
                const auto contact = phi_bc_.find(idx);
                if (contact == phi_bc_.end()) { complete = false; break; }
                if (voltage_set && contact->second != voltage) return;
                voltage = contact->second;
                voltage_set = true;
            }
            if (!complete) continue;
            state.electrode_faces.push_back(2 * axis + upper);
            state.electrode_voltages.push_back(voltage);
            for (size_t idx = 0; idx < N; ++idx)
                if ((idx / stride[axis]) % count[axis] == coordinate) electrodes[idx] = 1;
        }
    }
    bool free_volume = false;
    for (size_t idx = 0; idx < N; ++idx) {
        if (static_cast<bool>(electrodes[idx]) != static_cast<bool>(phi_bc_.count(idx))) return;
        free_volume = free_volume || !electrodes[idx];
    }
    if (!free_volume || state.electrode_faces.size() < 2) return;
    const std::vector<real_t>* Jn[3] = {&state.Jn_x, &state.Jn_y, &state.Jn_z};
    const std::vector<real_t>* Jp[3] = {&state.Jp_x, &state.Jp_y, &state.Jp_z};
    for (int face : state.electrode_faces) {
        const int axis = face / 2;
        const bool upper = face % 2;
        const size_t coordinate = upper ? count[axis] - 2 : 0;
        const real_t sign = upper ? -TCAD_CONST(1.0) : TCAD_CONST(1.0);
        real_t charge = TCAD_CONST(0.0), conduction = TCAD_CONST(0.0), displacement = TCAD_CONST(0.0);
        real_t electric = TCAD_CONST(0.0), polar = TCAD_CONST(0.0), increment = TCAD_CONST(0.0);
        for (size_t idx = 0; idx < N; ++idx) {
            if ((idx / stride[axis]) % count[axis] != coordinate) continue;
            const size_t neighbor = idx + stride[axis];
            if (electrodes[idx] == electrodes[neighbor]) continue;
            const size_t i = idx % g_.nx, j = (idx / g_.nx) % g_.ny, k = idx / (g_.nx * g_.ny);
            const real_t width[3] = {g_.dx_cell(i), g_.dy_cell(j), g_.dz_cell(k)};
            const real_t area = width[(axis + 1) % 3] * width[(axis + 2) % 3];
            charge += sign * area * (*D[axis])[idx];
            conduction += sign * area * ((*Jn[axis])[idx] + (*Jp[axis])[idx]);
            if (state.displacement_current_available) {
                displacement += sign * area * (*Jdisp[axis])[idx];
                electric += sign * area * (*Jelectric[axis])[idx];
                polar += sign * area * (*Jpolar[axis])[idx];
                increment += sign * area * (*Jdisp[axis])[idx] * state.accepted_dt;
            }
        }
        state.electrode_charges.push_back(charge);
        state.electrode_conduction_currents.push_back(conduction);
        if (state.displacement_current_available) {
            state.electrode_displacement_currents.push_back(displacement);
            state.electrode_total_currents.push_back(conduction + displacement);
            state.electrode_dielectric_currents.push_back(electric);
            state.electrode_polarization_currents.push_back(polar);
            state.electrode_charge_increments.push_back(increment);
        }
    }
    state.electrode_charge_available = true;
    // All BE rows now share Poisson's full node geometry, including mixed
    // 2-D/3-D grids. Mobile reservoirs must match the electrode volume.
    // Empty blocked rows need no carrier reservoir, but cannot discard net
    // charge or pair sources. Check both ends of an accepted interval so a
    // pinned row cannot erase initial charge and then claim Ampere closure.
    bool closed_transport = true, pure_dielectric = true;
    for (size_t idx = 0; idx < N; ++idx) {
        const bool mobile = paired_mobile_carriers(mu_n_[idx], mu_p_[idx]);
        const bool contacts_match =
            static_cast<bool>(n_bc_.count(idx)) == static_cast<bool>(electrodes[idx]) &&
            static_cast<bool>(p_bc_.count(idx)) == static_cast<bool>(electrodes[idx]);
        const bool blocked = empty_blocked_carrier_row(mu_n_[idx], mu_p_[idx],
            state.n[idx], state.p[idx], G_opt_[idx], tau_n_[idx], tau_p_[idx]);
        const bool previous_blocked = !interval || empty_blocked_carrier_row(
            mu_n_[idx], mu_p_[idx], previous->n[idx], previous->p[idx],
            G_opt_[idx], tau_n_[idx], tau_p_[idx]);
        pure_dielectric = pure_dielectric && blocked;
        closed_transport = closed_transport &&
            valid_pair_sources(G_opt_[idx], tau_n_[idx], tau_p_[idx]) &&
            ((blocked && previous_blocked) || (mobile && contacts_match));
    }
    state.total_terminal_current_available = state.displacement_current_available &&
        closed_transport && !state.transient_majority_frozen;

    // An independent field-energy ledger, not source work relabelled as
    // storage. Restrict closure to an explicitly lossless, charge-free model.
    if (!state.converged || fe_enabled_ || !pure_dielectric) return;
    for (size_t idx = 0; idx < N; ++idx)
        if (mu_n_[idx] != TCAD_CONST(0.0) || mu_p_[idx] != TCAD_CONST(0.0) ||
            Nd_minus_Na_[idx] != TCAD_CONST(0.0) || G_opt_[idx] != TCAD_CONST(0.0) ||
            state.n[idx] != state.p[idx]) return;
    real_t energy = TCAD_CONST(0.0), increment = TCAD_CONST(0.0);
    for (size_t idx = 0; idx < N; ++idx) {
        const size_t i = idx % g_.nx, j = (idx / g_.nx) % g_.ny, k = idx / (g_.nx * g_.ny);
        const real_t width[3] = {g_.dx_cell(i), g_.dy_cell(j), g_.dz_cell(k)};
        for (int axis = 0; axis < 3; ++axis) {
            const size_t coordinate = (idx / stride[axis]) % count[axis];
            if (coordinate + 1 == count[axis]) continue;
            const size_t neighbor = idx + stride[axis];
            if (electrodes[idx] && electrodes[neighbor]) continue;
            const real_t edge = axis == 0 ? g_.dx_edge(coordinate)
                : axis == 1 ? g_.dy_edge(coordinate) : g_.dz_edge(coordinate);
            const real_t weight = epsilon_face(idx, neighbor, *plus[axis]) *
                width[(axis + 1) % 3] * width[(axis + 2) % 3] / edge;
            const real_t potential = state.phi[neighbor] - state.phi[idx];
            energy += TCAD_CONST(0.5) * weight * potential * potential;
            if (interval && previous->dielectric_energy_available) {
                const real_t delta = delta_phi[neighbor] - delta_phi[idx];
                // Preserve changes below the precision of absolute energies.
                increment += weight * delta * (potential - TCAD_CONST(0.5) * delta);
            }
        }
    }
    auto representable = [](real_t value) {
        return isfinite_q(value) && std::isfinite((double)value) &&
            (value == TCAD_CONST(0.0) || (double)value != 0.0);
    };
    if (!representable(energy)) return;
    state.dielectric_energy = energy;
    state.dielectric_energy_available = true;
    if (interval && previous->dielectric_energy_available && representable(increment)) {
        state.dielectric_energy_increment = increment;
        state.dielectric_energy_increment_available = true;
    }
}

void DeviceSimulator::add_transient_lk_ledger(SimulationResult& state,
        const SimulationResult* previous, const std::vector<real_t>& drive_phi) const {
    const size_t N = g_.npts();
    if (!fe_enabled_ || fe_model_ != 0 || !state.converged || state.P.size() != 3*N ||
        fe_mask_.size() != N || fe_gamma_ <= TCAD_CONST(0.0) ||
        (!charge_volume_fraction_.empty() &&
         !std::all_of(charge_volume_fraction_.begin(), charge_volume_fraction_.end(),
                      [](real_t x) { return x == TCAD_CONST(1.0); }))) return;
    auto representable = [](real_t x) {
        return isfinite_q(x) && std::isfinite((double)x) && (x == TCAD_CONST(0.0) || (double)x != 0.0);
    };
    if (!std::all_of(state.P.begin(), state.P.end(), representable)) return;
    const bool interval = previous && state.accepted_dt > TCAD_CONST(0.0);
    if (interval && (!previous->lk_energy_available || previous->P.size() != 3*N ||
                     drive_phi.size() != N)) return;
    std::vector<real_t> volumes(N, TCAD_CONST(0.0)), drive, delta;
    std::vector<real_t> parameters{fe_alpha_, fe_beta_, fe_gamma_, fe_E_bi_,
                                   fe_eps_fe_, (real_t)fe_polar_axis_};
    if (!std::all_of(parameters.begin(), parameters.end(), representable)) return;
    if (interval) {
        std::vector<real_t> ex, ey, ez;
        poisson_.compute_electric_field(drive_phi, ex, ey, ez);
        if (state.lk_material_field) {
            const int axis=g_.nx>1 ? 0 : g_.ny>1 ? 1 : 2;
            const auto fields=lk_material_field_nd(g_,eps_,fe_mask_,state.P,drive_phi,axis);
            for(size_t i=0;i<N;++i) { ex[i]=fields[3*i]; ey[i]=fields[3*i+1]; ez[i]=fields[3*i+2]; }
        }
        drive.resize(3*N); delta.resize(3*N);
        for (size_t idx = 0; idx < N; ++idx) {
            drive[3*idx] = ex[idx]; drive[3*idx+1] = ey[idx]; drive[3*idx+2] = ez[idx];
            for (int c = 0; c < 3; ++c)
                delta[3*idx+c] = state.P[3*idx+c] - previous->P[3*idx+c];
        }
        if (!std::all_of(drive.begin(), drive.end(), representable) ||
            !std::all_of(delta.begin(), delta.end(), representable)) return;
    }
    // Geometric dual cells terminate at the physical boundary, including FE
    // electrode nodes with half widths. Singleton axes use explicit extrusion.
    // This quadrature is independent of the mobile free-node control volume.
    auto width = [&](int axis, size_t index, size_t count, real_t extrusion, auto edge) {
        if (count == 1) return extrusion;
        return ((index ? edge(index-1) :
                    (state.lk_material_field && g_.lk_zero_d_faces[2*axis] ? edge(0):TCAD_CONST(0.0))) +
                (index+1 < count ? edge(index) :
                    (state.lk_material_field && g_.lk_zero_d_faces[2*axis+1] ? edge(count-2):TCAD_CONST(0.0)))) / TCAD_CONST(2.0);
    };
    real_t energy = TCAD_CONST(0.0), increment = TCAD_CONST(0.0), loss = TCAD_CONST(0.0), work = TCAD_CONST(0.0), correction = TCAD_CONST(0.0);
    for (size_t k = 0; k < g_.nz; ++k)
        for (size_t j = 0; j < g_.ny; ++j)
            for (size_t i = 0; i < g_.nx; ++i) {
                const size_t idx = g_.index(i,j,k);
                if (!fe_mask_[idx]) continue;
                const real_t volume =
                    width(0, i, g_.nx, g_.dx, [&](size_t q) { return g_.dx_edge(q); }) *
                    width(1, j, g_.ny, g_.dy, [&](size_t q) { return g_.dy_edge(q); }) *
                    width(2, k, g_.nz, g_.dz, [&](size_t q) { return g_.dz_edge(q); });
                if (volume <= TCAD_CONST(0.0) || !representable(volume)) return;
                volumes[idx] = volume;
                for (int c = 0; c < 3; ++c) {
                    const real_t p = state.P[3*idx+c];
                    real_t a = fe_alpha_, b = TCAD_CONST(0.0);
                    if (c == fe_polar_axis_) {
                        b = fe_E_bi_;
                        if (fe_eps_fe_ > TCAD_CONST(0.0)) a += TCAD_CONST(1.0) / (fe_eps_fe_ * EPS0);
                    }
                    energy += volume * (TCAD_CONST(0.5)*a*p*p + TCAD_CONST(0.25)*fe_beta_*p*p*p*p + b*p);
                    if (!interval) continue;
                    const real_t d = delta[3*idx+c];
                    // Polynomial differences computed from quad delta first;
                    // no subtraction of large absolute free energies.
                    increment += volume*d*(a*(p-TCAD_CONST(0.5)*d) + b + fe_beta_*
                        (p*p*p - TCAD_CONST(1.5)*p*p*d + p*d*d - TCAD_CONST(0.25)*d*d*d));
                    loss += volume*fe_gamma_*d*d/state.accepted_dt;
                    work += volume*drive[3*idx+c]*d;
                    // Signed BE chain-rule correction, not physical heat.
                    correction += volume*d*d*(TCAD_CONST(0.5)*a + fe_beta_*
                        (TCAD_CONST(1.5)*p*p - p*d + TCAD_CONST(0.25)*d*d));
                }
            }
    if (!std::any_of(volumes.begin(), volumes.end(), [](real_t v) { return v > TCAD_CONST(0.0); }) ||
        !representable(energy)) return;
    state.lk_energy_available = true;
    state.lk_free_energy = energy;
    state.lk_node_volumes = std::move(volumes);
    state.lk_parameters = std::move(parameters);
    if (!interval || !representable(increment) || !representable(loss) ||
        !representable(work) || !representable(correction)) return;
    state.lk_energy_increment_available = true;
    state.lk_free_energy_increment = increment; state.lk_dissipation = loss;
    state.lk_field_work = work; state.lk_be_correction = correction;
    state.lk_drive_field = std::move(drive);
    state.lk_polarization_increment = std::move(delta);
}

std::vector<SimulationResult> DeviceSimulator::solve_transient() {
    return solve_transient_impl(nullptr, 0);
}

void DeviceSimulator::advance_transient_nls(NlsTransientContinuation& continuation, size_t max_retries) {
    auto history = solve_transient_impl(&continuation, max_retries);
    continuation.history_.swap(history);
    continuation.trace_.swap(transient_attempt_history_);
}

std::vector<real_t> DeviceSimulator::nls_continuation_configuration() const {
    std::vector<real_t> stamp = {
        real_t(g_.nx), real_t(g_.ny), real_t(g_.nz), g_.dx, g_.dy, g_.dz,
        tol_, real_t(max_iter_), temperature_, VT_, real_t(statistics_type_),
        real_t(newton_use_log_space_), real_t(newton_additive_log_density_update_),
        newton_jacobian_reuse_threshold_, real_t(has_initial_guess_),
        real_t(nonlinear_history_enabled_), real_t(history_updates_enabled_),
        transient_start_time_, transient_t_final_, transient_dt_,
        real_t(transient_nls_error_control_), transient_nls_error_.rtol,
        transient_nls_error_.atol, transient_nls_error_.phi_atol,
        transient_nls_error_.carrier_rtol, transient_nls_error_.carrier_atol,
        transient_nls_error_.min_dt, real_t(transient_nls_error_.max_reject),
        fe_alpha_, fe_beta_, fe_gamma_, fe_ps_, fe_ec_, fe_escale_, fe_E_bi_,
        fe_eps_fe_, fe_nls_tau0_, fe_nls_E0_, fe_nls_dt_, real_t(fe_polar_axis_)};
    auto vector = [&](const std::vector<real_t>& values) {
        stamp.push_back(real_t(values.size()));
        stamp.insert(stamp.end(), values.begin(), values.end());
    };
    for (const auto* values : {&g_.xx, &g_.yx, &g_.zx, &eps_, &edge_eps_x_plus_,
        &edge_eps_x_minus_, &edge_eps_y_plus_, &edge_eps_y_minus_, &edge_eps_z_plus_,
        &edge_eps_z_minus_, &mu_n_, &mu_p_, &tau_n_, &tau_p_, &Nd_minus_Na_,
        &charge_volume_fraction_, &G_opt_, &Nc_, &Nv_, &Eg_, &init_phi_, &init_n_,
        &init_p_, &transient_waveform_times_}) vector(*values);
    for (const auto* boundary : {&phi_bc_, &n_bc_, &p_bc_}) {
        stamp.push_back(real_t(boundary->size()));
        for (const auto& item : *boundary) { stamp.push_back(real_t(item.first)); stamp.push_back(item.second); }
    }
    stamp.push_back(real_t(transient_voltage_offsets_.size()));
    for (const auto& item : transient_voltage_offsets_) { stamp.push_back(real_t(item.first)); vector(item.second); }
    return stamp;
}

std::vector<SimulationResult> DeviceSimulator::solve_transient_impl(NlsTransientContinuation* recovery, size_t max_retries) {
    const bool resuming = recovery && recovery->owner_;
    std::vector<real_t> recovery_configuration;
    if (recovery) {
#ifndef TCAD_USE_FLOAT128
        throw std::invalid_argument("NLS continuation requires the float128 backend");
#endif
        if (resuming && recovery->owner_ != this)
            throw std::invalid_argument("NLS continuation belongs to another simulator");
        const size_t sizes[] = {g_.nx, g_.ny, g_.nz};
        bool full_contacts = fe_polar_axis_ >= 0 && fe_polar_axis_ < 3 && sizes[fe_polar_axis_] > 1;
        for (size_t q = 0; q < g_.npts() && full_contacts; ++q) {
            const size_t coordinate[] = {q % g_.nx, (q/g_.nx) % g_.ny, q/(g_.nx*g_.ny)};
            const bool end = coordinate[fe_polar_axis_] == 0 || coordinate[fe_polar_axis_] + 1 == sizes[fe_polar_axis_];
            full_contacts = bool(phi_bc_.count(q)) == end && bool(n_bc_.count(q)) == end && bool(p_bc_.count(q)) == end;
        }
        if (!fe_enabled_ || fe_model_ != 2 || !full_contacts || fe_mask_.size() != g_.npts() ||
            std::any_of(fe_mask_.begin(), fe_mask_.end(), [](char v) { return !v; }) ||
            !fe_play_state_.empty() || transient_lk_coupled_ || transient_lk_substepping_ || transient_lk_material_field_ ||
            transient_lk_error_control_ || transient_lk_electrical_error_control_ ||
            transient_electrical_error_control_ || transient_nls_event_control_ ||
            newton_freeze_phi_ || newton_freeze_n_ || newton_freeze_p_ || hfs_enabled_ || auger_enabled_ ||
            statistics_type_ != StatisticsType::BOLTZMANN || !isfinite_q(tol_) || tol_ <= 0 || tol_ > TCAD_CONST(1e-16) ||
            std::any_of(g_.lk_zero_d_faces.begin(), g_.lk_zero_d_faces.end(), [](bool v) { return v; }))
            throw std::invalid_argument("NLS continuation requires full FE/full polar contacts, unfrozen split NLS, tolerance <=1e-16 and no other adaptive/event/HFS/Auger controls");
        recovery_configuration = nls_continuation_configuration();
        if (resuming && (recovery_configuration != recovery->configuration_ || recovery->history_.empty() ||
            fe_polarization_ != recovery->history_.back().P || !fe_polarization_init_))
            throw std::invalid_argument("NLS continuation configuration or accepted material state changed");
    }
    const real_t run_start = resuming ? recovery->history_.back().time : transient_start_time_;
    // Clear even when preflight throws; never expose a previous run as this run.
    transient_attempt_history_.clear();
    validate_ii_driving_scope();
    validate_hfs_reference_scope();
    if(three_temperature_.enabled() || isolated_relaxation_.enabled() || energy_coordinate_.enabled()) throw std::logic_error("legacy solve/transaction unavailable in explicit-cell three-temperature mode");
    // No history is returned when this call throws. Material memory is then
    // restored below, so diagnostic "retained" dwell must be withdrawn too.
    // Prepare the terminal labels before any physical mutation: exception
    // cleanup must remain safe under persistent allocation failure.
    struct TransientTraceRestore {
        std::vector<TransientAttemptHistory>& groups;
        std::string exception_status, exception_reason;
        int entered_exceptions;
        ~TransientTraceRestore() noexcept {
            if (std::uncaught_exceptions() <= entered_exceptions || groups.empty()) return;
            // Completed accepted labels have eight characters. Rewrite and
            // shorten them in place, without relying on small-string storage.
            auto aborted = [](std::string& label) noexcept {
                if (label.size() < 7) { label.clear(); return; }
                for (size_t i = 0; i < 7; ++i) label[i] = "aborted"[i];
                while (label.size() > 7) label.pop_back();
            };
            for (auto& group : groups) {
                if (group.accepted) {
                    aborted(group.status);
                    aborted(group.stopping_reason);
                }
                group.accepted = false;
                for (auto& trial : group.trials) trial.retained = false;
            }
            groups.back().status.swap(exception_status);
            groups.back().stopping_reason.swap(exception_reason);
        }
    } trace_restore{transient_attempt_history_,
        nonlinear_history_enabled_ ? "exception" : "",
        nonlinear_history_enabled_ ? "exception" : "", std::uncaught_exceptions()};
    if (transient_start_time_ > transient_t_final_)
        throw std::invalid_argument("transient start time must not exceed final time");
    const size_t N = g_.npts();
    std::vector<SimulationResult> history;
    const bool error_control = transient_lk_error_control_ || transient_electrical_error_control_ || transient_nls_error_control_;
    const bool electrical_control = transient_lk_electrical_error_control_ || transient_electrical_error_control_ || transient_nls_error_control_;
    const bool polarization_control = transient_lk_error_control_ || transient_nls_error_control_;
    const real_t phi_atol = transient_nls_error_control_ ? transient_nls_error_.phi_atol :
        (transient_electrical_error_control_ ? transient_phi_atol_ : transient_lk_phi_atol_);
    const real_t carrier_rtol = transient_nls_error_control_ ? transient_nls_error_.carrier_rtol :
        (transient_electrical_error_control_ ? transient_carrier_rtol_ : transient_lk_carrier_rtol_);
    const real_t carrier_atol = transient_nls_error_control_ ? transient_nls_error_.carrier_atol :
        (transient_electrical_error_control_ ? transient_carrier_atol_ : transient_lk_carrier_atol_);
    const real_t error_min_dt = transient_nls_error_control_ ? transient_nls_error_.min_dt :
        (transient_electrical_error_control_ ? transient_error_min_dt_ : transient_lk_min_dt_);
    const size_t error_max_reject = transient_nls_error_control_ ? transient_nls_error_.max_reject :
        (transient_electrical_error_control_ ? transient_error_max_reject_ : transient_lk_max_reject_);
    const real_t polarization_atol = transient_nls_error_control_ ? transient_nls_error_.atol : transient_lk_error_atol_;
    const real_t polarization_rtol = transient_nls_error_control_ ? transient_nls_error_.rtol : transient_lk_error_rtol_;
    if (transient_nls_error_control_ &&
        (!fe_enabled_ || fe_model_ != 2 || transient_electrical_error_control_ ||
         transient_lk_coupled_ || transient_lk_substepping_ || transient_lk_error_control_ ||
         transient_lk_electrical_error_control_ || newton_freeze_phi_ || newton_freeze_n_ || newton_freeze_p_))
        throw std::invalid_argument("NLS error control requires enabled split NLS, unfrozen phi/n/p and no other controllers");
    if (transient_electrical_error_control_ &&
        (fe_enabled_ || transient_lk_coupled_ || transient_lk_substepping_ ||
         transient_lk_error_control_ || transient_lk_electrical_error_control_ ||
         newton_freeze_phi_ || newton_freeze_n_ || newton_freeze_p_))
        throw std::invalid_argument("classical electrical error control requires no FE/LK controls and unfrozen phi/n/p");
    if (!std::isfinite((double)tol_) || tol_ <= TCAD_CONST(0.0))
        throw std::invalid_argument("transient tolerance must be finite and positive");
    // These branches are implemented by the steady solver, but the current
    // BE carrier path does not evolve them. Do not silently
    // run a different physical model when the caller enabled them. FE is the
    // explicit exception: split kinetics or simultaneous monotone LK is wired
    // below, with polarization injected into every Newton Poisson solve.
    if ((!fe_enabled_ && fe_gamma_ != TCAD_CONST(0.0)) ||
        (fe_enabled_ && fe_model_ == 0 &&
         (!std::isfinite((double)fe_gamma_) || fe_gamma_ <= TCAD_CONST(0.0))) ||
        quantum_enabled_ || thermal_coupling_enabled_ || lattice_feedback_enabled_ ||
        trap_D_it_ != TCAD_CONST(0.0) ||
        std::any_of(Q_ot_.begin(), Q_ot_.end(),
                    [](real_t value) { return value != TCAD_CONST(0.0); }) || btbt_enabled_ || ii_enabled_ ||
        leak_enabled_ || bd_enabled_ || !ohmic_nodes_.empty() ||
        mobility_model_type_ != MobilityModelType::CONSTANT)
        throw std::invalid_argument(
            "transient currently supports classical SRH/Auger/optical carrier transport "
            "and split FE or simultaneous LK; LK FE requires positive gamma; "
            "traps, quantum, thermal, BTBT, avalanche, leakage, "
            "breakdown, nonconstant mobility and coupled ohmic models are not implemented");

    // Zero coefficients are the disabled operator, including scope and Newton
    // options. Every strictly positive coefficient keeps the active scope guard.
    const bool active_auger = auger_enabled_ &&
        (auger_Cn_ > TCAD_CONST(0.0) || auger_Cp_ > TCAD_CONST(0.0));
    if (active_auger) {
        bool mobile = true;
        for (size_t idx = 0; idx < N; ++idx)
            mobile = mobile && paired_mobile_carriers(mu_n_[idx], mu_p_[idx]);
        if (fe_enabled_ || statistics_type_ != StatisticsType::BOLTZMANN || !mobile)
            throw std::invalid_argument(
                "Auger transient requires Boltzmann statistics, no FE and paired positive mobilities");
    }

    if (fe_enabled_) {
        if (newton_freeze_phi_)
            throw std::invalid_argument("FE transient does not support a frozen potential request");
        if (fe_mask_.size() != N)
            throw std::invalid_argument("FE transient requires a mesh-sized FE mask");
        if (fe_model_ < 0 || fe_model_ > 3 || !isfinite_q(fe_E_bi_))
            throw std::invalid_argument("FE transient requires a supported model and finite imprint field");
        if (fe_model_ == 0 && (!isfinite_q(fe_alpha_) ||
            !isfinite_q(fe_beta_) || fe_beta_ <= TCAD_CONST(0.0)))
            throw std::invalid_argument("LK requires finite coefficients and positive beta");
    }
    if (!newton_freeze_phi_ && phi_bc_.empty())
        throw std::invalid_argument("coupled transient requires a Dirichlet potential reference");
    real_t effective_dt = transient_dt_;
    if (transient_lk_electrical_error_control_ && !transient_lk_error_control_)
        throw std::invalid_argument("LK electrical error control requires LK polarization error control");
    if (transient_lk_error_control_ && !transient_lk_substepping_)
        throw std::invalid_argument("LK error control requires coupled LK substepping");
    if (transient_lk_substepping_) {
        if (!transient_lk_coupled_ || !fe_enabled_ || fe_model_ != 0)
            throw std::invalid_argument("LK substepping requires enabled coupled LK mode");
        if (fe_alpha_ < TCAD_CONST(0.0))
            effective_dt = std::min(effective_dt,
                transient_lk_safety_ * fe_gamma_ / (-fe_alpha_));
        // The quad solver could advance smaller intervals, but returned double
        // clocks would alias. Reject before initializing/evolving any state.
        if (!std::isfinite((double)effective_dt) || (double)effective_dt <= 0.0 ||
            effective_dt <= TCAD_CONST(8.0) * std::numeric_limits<double>::epsilon() * transient_t_final_)
            throw std::invalid_argument("LK substep cannot be represented on the returned transient timeline");
    }
    if (error_control && error_min_dt > effective_dt *
        (TCAD_CONST(1.0) + TCAD_CONST(4.0) * std::numeric_limits<double>::epsilon()))
        throw std::invalid_argument("electrical/LK error control min_dt exceeds the configured step limit");
    if (error_control && error_min_dt <=
        TCAD_CONST(8.0) * std::numeric_limits<double>::epsilon() * transient_t_final_)
        throw std::invalid_argument("electrical/LK error control min_dt cannot be represented on the returned timeline");
    real_t maximum_dt = std::min(effective_dt, transient_t_final_ - transient_start_time_);
    if (!transient_waveform_times_.empty()) {
        // Every voltage knot is an endpoint. A coarse nominal dt is safe
        // when all active waveform segments force shorter monotone steps.
        maximum_dt = TCAD_CONST(0.0);
        real_t previous = transient_start_time_;
        for (size_t knot = 1; knot < transient_waveform_times_.size(); ++knot) {
            const real_t endpoint = std::min(transient_waveform_times_[knot], transient_t_final_);
            if (endpoint <= previous) continue;
            maximum_dt = std::max(maximum_dt, std::min(effective_dt, endpoint-previous));
            previous = endpoint;
            if (endpoint >= transient_t_final_) break;
        }
    }
    const bool monotone_lk_steps = maximum_dt == TCAD_CONST(0.0) ||
        (isfinite_q(fe_alpha_ + fe_gamma_/maximum_dt) &&
         fe_alpha_ + fe_gamma_/maximum_dt > TCAD_CONST(0.0));
    if (transient_lk_coupled_) {
        if (!fe_enabled_ || fe_model_ != 0)
            throw std::invalid_argument("coupled LK mode requires enabled LK ferroelectric model");
        if (!monotone_lk_steps)
            throw std::invalid_argument("coupled LK requires alpha+gamma/dt > 0; reduce the configured time step");
    }

    int material_axis = -1;
    auto zero = [](const std::vector<real_t>& values) {
        return std::all_of(values.begin(), values.end(), [](real_t v) { return v == TCAD_CONST(0.0); });
    };
    // A material-field override is sticky; automatic selection is recomputed
    // from the complete model and initial/contact carriers on every run.
    // Never discard a carrier equation, source or geometric override to make
    // an ineligible model fit either material-side solver.
    auto no_srh = [](const std::vector<real_t>& values) {
        return std::all_of(values.begin(),values.end(),[](real_t v) {
            return v == TCAD_CONST(1e100) || v == (real_t)1e100;
        });
    };
    const size_t material_sizes[] = {g_.nx,g_.ny,g_.nz};
    int material_active = 0;
    for (int axis=0;axis<3;++axis) if(material_sizes[axis]>1) { ++material_active; material_axis=axis; }
    const bool finite_fixed_charge = std::all_of(Nd_minus_Na_.begin(),Nd_minus_Na_.end(),
        [](real_t v) { return isfinite_q(v); });
    // Multidimensional material response is an explicit opt-in initially.
    // Keep the validated automatic policy restricted to its 1-D scope.
    const bool material_contacts_supported = material_active == 1 ?
        (phi_bc_.size()==2 && phi_bc_.count(0) && phi_bc_.count(N-1)) :
        (material_active > 1 && !phi_bc_.empty() && transient_lk_material_field_);
    bool material_contact_charge_zero = true;
    for (const auto& contact : phi_bc_)
        if (Nd_minus_Na_[contact.first] != 0) material_contact_charge_zero = false;
    const bool material_transport_supported = fe_enabled_ && fe_model_ == 0 &&
        N >= 3 && material_contacts_supported &&
        finite_fixed_charge &&
        material_contact_charge_zero &&
        !newton_freeze_n_ && !newton_freeze_p_ &&
        edge_eps_x_plus_.empty() && edge_eps_x_minus_.empty() &&
        edge_eps_y_plus_.empty() && edge_eps_y_minus_.empty() &&
        edge_eps_z_plus_.empty() && edge_eps_z_minus_.empty() &&
        std::all_of(charge_volume_fraction_.begin(),charge_volume_fraction_.end(),
            [](real_t v) { return v == TCAD_CONST(1.0); });
    const bool material_geometry_supported = material_transport_supported &&
        zero(mu_n_) && zero(mu_p_) && zero(G_opt_) && no_srh(tau_n_) && no_srh(tau_p_);
    if (transient_lk_material_field_) {
        if (!finite_fixed_charge)
            throw std::invalid_argument("material-field LK fixed doping must be finite");
        if (!transient_lk_coupled_ || !material_transport_supported)
            throw std::invalid_argument("material-field LK requires coupled LK on a structured grid with valid potential contacts, zero endpoint doping (1-D) or zero contact doping, no carrier freezes, edge overrides or fractional volumes");
    }

    const bool driven = !transient_waveform_times_.empty();
    if (transient_nls_event_control_) {
#ifndef TCAD_USE_FLOAT128
        throw std::invalid_argument("NLS event control requires the float128 backend");
#endif
        const size_t sizes[] = {g_.nx, g_.ny, g_.nz};
        const int axis = fe_polar_axis_;
        bool contacts_complete = axis >= 0 && axis < 3 && sizes[axis] > 1;
        if (contacts_complete) {
            contacts_complete = phi_bc_.size() == 2 * (N / sizes[axis]);
            for (size_t k=0;k<g_.nz;++k) for (size_t j=0;j<g_.ny;++j) for (size_t i=0;i<g_.nx;++i) {
                const size_t xyz[] = {i,j,k};
                if (xyz[axis] == 0 || xyz[axis]+1 == sizes[axis])
                    contacts_complete = contacts_complete && phi_bc_.count(g_.index(i,j,k));
            }
        }
        if (!driven || !fe_enabled_ || fe_model_ != 2 || error_control ||
            transient_lk_coupled_ || transient_lk_substepping_ ||
            newton_freeze_phi_ || newton_freeze_n_ || newton_freeze_p_ ||
            fe_eps_fe_ != TCAD_CONST(0.0) || !contacts_complete ||
            fe_mask_.size() != N || !std::all_of(fe_mask_.begin(),fe_mask_.end(),[](char v){return v!=0;}))
            throw std::invalid_argument("NLS event control requires fixed split NLS, full FE, complete polar contact planes, zero depolarization and unfrozen carriers");
        if (transient_nls_event_half_width_ >= effective_dt/TCAD_CONST(8.0))
            throw std::invalid_argument("NLS event half width must be smaller than dt/8");
        if (transient_t_final_-transient_nls_event_half_width_ == transient_t_final_)
            throw std::invalid_argument("NLS event half width exceeds time resolution");
    }
    if (driven) {
        if (newton_freeze_phi_)
            throw std::invalid_argument("voltage waveforms require an unfrozen potential");
        if (transient_t_final_ > transient_waveform_times_.back())
            throw std::invalid_argument("voltage waveform must cover transient t_final");
        for (const auto& [idx, offsets] : transient_voltage_offsets_)
            if (!phi_bc_.count(idx))
                throw std::invalid_argument("waveform node is no longer a potential contact");
    }
    // Restore the configured DC contacts even on exceptions. Waveform values
    // are temporary offsets, never accumulated onto a preceding time sample.
    struct ContactRestore {
        std::map<size_t, real_t>& live;
        std::map<size_t, real_t> configured;
        bool active;
        ~ContactRestore() { if (active) live.swap(configured); }
    } contacts{phi_bc_, driven ? phi_bc_ : std::map<size_t, real_t>{}, driven};
    auto waveform_segment = [&](real_t time) {
        auto next = std::upper_bound(transient_waveform_times_.begin(),
                                     transient_waveform_times_.end(), time);
        const size_t hi = next == transient_waveform_times_.end()
            ? transient_waveform_times_.size() - 1
            : (size_t)(next - transient_waveform_times_.begin());
        const size_t lo = hi - 1;
        const real_t f = (time - transient_waveform_times_[lo]) /
            (transient_waveform_times_[hi] - transient_waveform_times_[lo]);
        return std::make_pair(lo, f);
    };
    auto waveform_voltage = [&](size_t idx, const std::vector<real_t>& values,
                                size_t lo, real_t f) {
        // Form absolute endpoints before interpolation. A large DC and its
        // cancelling offset must not become a spurious field at interior times.
        const real_t base = contacts.configured.at(idx);
        const real_t left = base + values[lo];
        const real_t right = base + values[lo + 1];
        return (TCAD_CONST(1.0) - f) * left + f * right;
    };
    auto validate_voltage = [&](real_t time) {
        const auto [lo, f] = waveform_segment(time);
        for (const auto& [idx, values] : transient_voltage_offsets_) {
            const real_t voltage = waveform_voltage(idx, values, lo, f);
            if (!std::isfinite((double)voltage))
                throw std::invalid_argument("waveform contact potential exceeds the finite output range");
        }
    };
    if (driven) {
        // A linear segment is bounded by its endpoints. Check all active knots
        // and the possibly clipped final endpoint before initializing or
        // evolving physical memory. Unused future voltages need not be in range.
        validate_voltage(TCAD_CONST(0.0));
        for (real_t knot : transient_waveform_times_) {
            if (knot <= TCAD_CONST(0.0)) continue;
            if (knot >= transient_t_final_) break;
            validate_voltage(knot);
        }
        validate_voltage(transient_t_final_);
    }
    auto apply_voltage = [&](real_t time) {
        if (!driven) return;
        const auto [lo, f] = waveform_segment(time);
        for (const auto& [idx, values] : transient_voltage_offsets_) {
            const real_t voltage = waveform_voltage(idx, values, lo, f);
            if (!std::isfinite((double)voltage))
                throw std::invalid_argument("waveform contact potential exceeds the finite output range");
            phi_bc_[idx] = voltage;
        }
    };
    apply_voltage(run_start);

    // Per-node intrinsic carrier density (using spatially varying Nc, Nv, Eg)
    std::vector<real_t> ni(N);
    for (size_t i = 0; i < N; ++i) {
        ni[i] = intrinsic_density(Eg_[i], temperature_, Nc_[i], Nv_[i], statistics_type_);
    }

    // Apply mobility model if not constant
    std::vector<real_t> mu_n_eff, mu_p_eff;
    transport_mobilities(mu_n_eff, mu_p_eff);

    // Build Newton options with transient (backward-Euler) settings.
    //
    // Newton solves both continuity equations with the corrected BE term.
    // Poisson feeds back in both classical and FE mode by default. An
    // explicitly frozen potential is available for classical benchmarks. The BE pin
    // (c-c_prev)/dt*dx has cell-integrated units and a +dx/dt diagonal. The
    // operator-split Gummel alternative 2-cycles on the perturbed state
    // (Poisson-continuity feedback limit cycle), so full Newton — which
    // couples all three blocks in one solve — is the robust choice despite
    // the wide Jacobian dynamic range (handled by row equilibration in
    // NewtonSolver).  See §17.
    //
    // Use the caller's tolerance and iteration budget. Transient mode must
    // not silently relax an accuracy request or turn a zero budget into 60.
    NewtonOptions nopt;
    nopt.record_nonlinear_history = nonlinear_history_enabled_;
    nopt.max_iter = max_iter_;
    nopt.tol = tol_;
    nopt.abs_tol = TCAD_CONST(1e-18);
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
    nopt.damping = TCAD_CONST(1.0);
    nopt.use_line_search = true;    // full Newton step overshoots on the stiff BE
                                    // system (dp ~ p); line search tames it while
                                    // keeping the quadratic-convergence basin.
    nopt.min_damping = TCAD_CONST(1e-6);
    nopt.line_search_max = 30;
    nopt.jacobian_reuse_threshold = newton_jacobian_reuse_threshold_;
    nopt.use_log_space = newton_use_log_space_;
    nopt.additive_log_density_update = newton_additive_log_density_update_;
    nopt.temperature = temperature_;
    nopt.statistics_type = statistics_type_;
    nopt.linear_solver = SolverType::DENSE_DIRECT;  // row-equilibrated in NewtonSolver
    nopt.transient_enabled = true;
    nopt.transient_dt = transient_dt_;
    // A fixed-potential transport benchmark is an explicit caller choice;
    // classical space charge must otherwise drive the Poisson equation too.
    nopt.freeze_phi = newton_freeze_phi_;
    nopt.hfs_enabled = hfs_enabled_;
    nopt.hfs_vsat_n = hfs_vsat_n_;
    nopt.hfs_vsat_p = hfs_vsat_p_;
    nopt.hfs_beta_n = hfs_beta_n_;
    nopt.hfs_beta_p = hfs_beta_p_;
    nopt.hfs_refdens_n = hfs_refdens_n_; nopt.hfs_refdens_p = hfs_refdens_p_;
    nopt.hfs_driving = hfs_driving_;
    nopt.hfs_qf_at_contacts = hfs_qf_at_contacts_;
    nopt.hfs_low_field_cutoff = hfs_low_field_cutoff_;
    nopt.enable_auger = active_auger;
    nopt.auger_Cn = auger_Cn_;
    nopt.auger_Cp = auger_Cp_;

    // Doping is fixed charge, not a constraint that pins a mobile species.
    // Both continuity equations must respond to diffusion and pair sources,
    // including uniformly n-type/p-type devices. Automatically freezing the
    // majority species silently discarded its BE storage and G-R equation.

    // Initialize from equilibrium or initial guess
    std::vector<real_t> phi(N, TCAD_CONST(0.0)), n(N, TCAD_CONST(0.0)), p(N, TCAD_CONST(0.0));
    if (resuming) {
        const auto& accepted = recovery->history_.back();
        phi = accepted.phi; n = accepted.n; p = accepted.p;
    } else if (has_initial_guess_) {
        phi = init_phi_; n = init_n_; p = init_p_;
    } else {
        for (size_t i = 0; i < N; ++i) {
            real_t C = Nd_minus_Na_[i];
            real_t half_C = C / TCAD_CONST(2.0);
            real_t disc = sqrt_q(ni[i] * ni[i] + half_C * half_C);
            real_t n_eq, p_eq;
            if (C >= TCAD_CONST(0.0)) { n_eq = disc + half_C; p_eq = (n_eq > EPSILON) ? (ni[i] * ni[i] / n_eq) : TCAD_CONST(0.0); }
            else { p_eq = disc - half_C; n_eq = (p_eq > EPSILON) ? (ni[i] * ni[i] / p_eq) : TCAD_CONST(0.0); }
            n[i] = n_eq; p[i] = p_eq;
            if (n_eq > EPSILON) phi[i] = VT_ * log_q(n_eq / ni[i]);
            else if (p_eq > EPSILON) phi[i] = -VT_ * log_q(p_eq / ni[i]);
        }
    }
    for (const auto& [idx, val] : n_bc_) n[idx] = val;
    for (const auto& [idx, val] : p_bc_) p[idx] = val;
    for (const auto& [idx, val] : phi_bc_) phi[idx] = val;
    for (size_t idx = 0; idx < N; ++idx) {
        if (!std::isfinite((double)phi[idx]) ||
            !std::isfinite((double)n[idx]) || !std::isfinite((double)p[idx]) ||
            n[idx] < TCAD_CONST(0.0) || p[idx] < TCAD_CONST(0.0))
            throw std::invalid_argument("transient initial state must be finite with nonnegative carriers");
    }

    const bool material_carriers_supported = zero(n) && zero(p);
    // A blocked material has no mobile charge or pair sources. Reject input
    // that its pinned carrier rows would otherwise silently discard. Interfaces
    // lie at node midpoints; full node volumes are used for Poisson and BE/SG.
    bool material_mobile_chain = material_transport_supported;
    for (size_t idx=0; idx<N && material_mobile_chain; ++idx) {
        const real_t mn=mu_n_eff[idx], mp=mu_p_eff[idx];
        const bool mobile=isfinite_q(mn) && isfinite_q(mp) && mn>EPSILON && mp>EPSILON;
        const bool blocked=mn==TCAD_CONST(0.0) && mp==TCAD_CONST(0.0) &&
            n[idx]<=EPSILON && p[idx]<=EPSILON && G_opt_[idx]==TCAD_CONST(0.0) &&
            tau_n_[idx]>=TCAD_CONST(1e90) && tau_p_[idx]>=TCAD_CONST(1e90);
        material_mobile_chain=mobile || blocked;
    }
    if(transient_lk_material_field_ &&
       !(material_geometry_supported && material_carriers_supported) && !material_mobile_chain)
        throw std::invalid_argument("material-field LK transport requires paired positive mobilities, or paired zero mobilities with carriers at most the numerical floor, zero generation and disabled SRH");
    // With neither override set, use the fully implicit spatially consistent
    // solver only where all equations and actual step sizes meet its scope.
    // Explicit split/centered requests remain reproducible; do not change dt,
    // drop transport physics, or latch an automatic choice into configuration.
    const bool material_model_supported =
        (material_geometry_supported && material_carriers_supported) || material_mobile_chain;
    const bool use_lk_coupled = transient_lk_coupled_ ||
        (!transient_lk_coupled_configured_ && !transient_lk_material_field_configured_ &&
         material_model_supported && monotone_lk_steps);
    const bool use_lk_material_field = transient_lk_material_field_ ||
        (!transient_lk_material_field_configured_ && use_lk_coupled &&
         material_model_supported);
    const bool use_lk_material_chain = use_lk_material_field && material_active == 1 &&
        material_geometry_supported && material_carriers_supported;
    // Whole natural faces can meet contacts along edges on other boundary
    // normals, but cannot contain a contact in their own face interior.
    for(size_t face=0;face<6;++face) if(g_.lk_zero_d_faces[face]) {
        for(const auto& contact:phi_bc_) {
            const size_t q=contact.first;
            const size_t c[]={q%g_.nx,(q/g_.nx)%g_.ny,q/(g_.nx*g_.ny)};
            if(c[face/2]!=(face%2 ? material_sizes[face/2]-1:0)) continue;
            bool intersection=false;
            for(size_t axis=0;axis<3;++axis) if(axis!=face/2 && material_sizes[axis]>1) {
                if(c[axis]==0 && !g_.lk_zero_d_faces[2*axis]) intersection=true;
                if(c[axis]+1==material_sizes[axis] && !g_.lk_zero_d_faces[2*axis+1]) intersection=true;
            }
            if(!intersection)
                throw std::invalid_argument("zero-D face interior contains a potential contact");
        }
    }
    if(std::any_of(g_.lk_zero_d_faces.begin(),g_.lk_zero_d_faces.end(),[](bool v){return v;}) &&
       !(use_lk_material_field && use_lk_coupled && material_active>1))
        throw std::invalid_argument("zero-D exterior half cells require multidimensional coupled material-field LK");

    // Cartesian material LK has line-local Schur couplings. Avoid a dense 3N
    // factorization for larger blocked-carrier capacitors. Newton retains its
    // true linear-residual check and the caller's nonlinear tolerance.
    const bool sparse_material_capacitor = use_lk_material_field && material_active>1 && N>256 &&
        std::all_of(mu_n_eff.begin(),mu_n_eff.end(),[](real_t v){return v==0;}) &&
        std::all_of(mu_p_eff.begin(),mu_p_eff.end(),[](real_t v){return v==0;});
    if(sparse_material_capacitor) nopt.linear_solver=SolverType::GMRES;

    auto project_potential_at = [&](const std::vector<real_t>& polarization,
                                    const std::map<size_t,real_t>& boundary,
                                    std::vector<real_t>& prediction) {
        // Potential is an algebraic constraint at t=0, not a time-dependent
        // initial degree of freedom. Project it onto Gauss' law with the
        // prescribed initial carriers and existing P, without advancing any
        // carrier or FE history. Use a fresh helper so cached steady-solve
        // linearizations, traps or contacts cannot contaminate this solve.
        PoissonSolver initial_poisson(g_);
        if(sparse_material_capacitor) {
            auto options=LinearSolver::default_poisson_options();
            options.type=SolverType::GMRES;
            options.prec=PreconditionerType::ILU0;
            options.max_iter=10000;
            options.restart=50;
            initial_poisson.set_solver_options(options);
        }
        initial_poisson.set_permittivity(eps_);
        initial_poisson.set_edge_permittivity(
            edge_eps_x_plus_, edge_eps_x_minus_,
            edge_eps_y_plus_, edge_eps_y_minus_,
            edge_eps_z_plus_, edge_eps_z_minus_);
        initial_poisson.set_doping(Nd_minus_Na_);
        initial_poisson.set_charge_volume_fraction(charge_volume_fraction_);
        initial_poisson.set_dirichlet(boundary);
        if (fe_enabled_) {
            initial_poisson.set_ferroelectric(fe_mask_, fe_alpha_, fe_beta_);
            initial_poisson.set_fe_polarization(polarization);
        }
        initial_poisson.assemble(n, p);
        if (!initial_poisson.solve(prediction))
            throw std::runtime_error("transient initial Poisson solve failed");
        const auto& matrix = initial_poisson.matrix();
        const Vector initial_residual = matrix.apply(prediction) - initial_poisson.rhs();
        const auto& rows = matrix.row_offsets();
        const auto& values = matrix.vals();
        for (size_t row = 0; row < N; ++row) {
            real_t row_scale = TCAD_CONST(0.0);
            for (size_t k = rows[row]; k < rows[row + 1]; ++k)
                row_scale = std::max(row_scale, abs_q(values[k]));
            if (!isfinite_q(prediction[row]) || !isfinite_q(initial_residual[row]) ||
                row_scale <= TCAD_CONST(0.0) ||
                abs_q(initial_residual[row]) / row_scale > std::max(tol_, TCAD_CONST(1e-12)))
                throw std::runtime_error("transient initial Poisson residual exceeds tolerance");
        }
    };
    auto project_potential = [&](const std::vector<real_t>& polarization) {
        project_potential_at(polarization, phi_bc_, phi);
    };
    if (!nopt.freeze_phi && !resuming)
        project_potential(fe_polarization_init_
            ? fe_polarization_ : std::vector<real_t>(3 * N, TCAD_CONST(0.0)));

    // Initialize persistent FE state only after validating the electrical
    // initial state. Invalid runs must not create or reset physical memory.
    // An exception returns no transient history, including any accepted prefix.
    // Restore the entered material memory in that case so retrying this call
    // does not silently consume polarization/dwell twice. Ordinary returns,
    // including a nonconverged history with an accepted prefix, retain it.
    // Install before initialization and use allocation-free restoration: local
    // trial/group catch handlers may themselves fail while copying diagnostics
    // or restoring vectors under persistent memory exhaustion.
    struct TransientMaterialRestore {
        std::vector<real_t>& polarization;
        std::vector<real_t>& play;
        bool& initialized;
        std::vector<real_t> entered_polarization, entered_play;
        bool entered_initialized;
        bool active;
        int entered_exceptions;
        ~TransientMaterialRestore() noexcept {
            if (active && std::uncaught_exceptions() > entered_exceptions) {
                polarization.swap(entered_polarization);
                play.swap(entered_play);
                initialized = entered_initialized;
            }
        }
    } material_restore{fe_polarization_, fe_play_state_, fe_polarization_init_,
        fe_enabled_ ? fe_polarization_ : std::vector<real_t>{},
        fe_enabled_ ? fe_play_state_ : std::vector<real_t>{},
        fe_polarization_init_, fe_enabled_, std::uncaught_exceptions()};
    if (fe_enabled_) {
        if (!fe_polarization_init_) {
            fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
            fe_polarization_init_ = true;
        }
        poisson_.set_permittivity(eps_);
        poisson_.set_ferroelectric(fe_mask_, fe_alpha_, fe_beta_);
        poisson_.set_ferroelectric_model(fe_model_);
        poisson_.set_ferroelectric_preisach(fe_ps_, fe_ec_, fe_escale_);
        poisson_.set_ferroelectric_builtin_field(fe_E_bi_);
        poisson_.set_ferroelectric_depol(fe_eps_fe_);
        poisson_.set_ferroelectric_nls(fe_nls_tau0_, fe_nls_E0_, fe_nls_dt_);
        poisson_.set_ferroelectric_polar_axis(fe_polar_axis_);
        poisson_.set_ferroelectric_gamma(fe_gamma_);
        poisson_.set_fe_polarization(fe_polarization_);
        if (fe_model_ == 1 || fe_model_ == 3) {
            const size_t state_size = (fe_model_ == 3) ? 2 * N : N;
            if (fe_play_state_.size() < state_size ||
                (fe_model_ == 1 && fe_play_state_.size() != state_size))
                fe_play_state_.assign(state_size, TCAD_CONST(0.0));
            poisson_.set_fe_play_state(fe_play_state_);
        }
    }

    // Store previous time step carriers for backward Euler
    std::vector<real_t> n_prev = n, p_prev = p;

    std::vector<real_t> lk_drive_phi;
    std::vector<std::vector<real_t>> material_samples;
    auto snapshot = [&](real_t time, real_t attempted, real_t dt, bool ok,
                        bool initial) {
        SimulationResult snap;
        snap.phi = phi; snap.n = n; snap.p = p;
        if (fe_enabled_) snap.P = fe_polarization_;
        snap.time = time; snap.attempted_time = attempted;
        snap.accepted_dt = dt; snap.initial_state = initial;
        snap.converged = ok;
        snap.lk_coupled = use_lk_coupled;
        snap.lk_material_field = use_lk_material_field;
        snap.lk_substepping = transient_lk_substepping_;
        snap.lk_step_limit = (transient_lk_substepping_ || error_control) ? effective_dt : TCAD_CONST(0.0);
        snap.lk_error_control = transient_lk_error_control_;
        snap.lk_electrical_error_control = transient_lk_electrical_error_control_;
        snap.electrical_error_control = transient_electrical_error_control_;
        snap.nls_error_control = transient_nls_error_control_;
        if (electrical_control) {
            snap.lk_phi_atol = phi_atol;
            snap.lk_carrier_rtol = carrier_rtol;
            snap.lk_carrier_atol = carrier_atol;
        }
        if (error_control) {
            snap.lk_error_rtol = polarization_rtol;
            snap.lk_error_atol = polarization_atol;
            snap.lk_error_status = initial ? "initial" : "pending";
        }
        snap.iterations = initial ? 0 : (use_lk_material_chain ? material_samples.size() : newton_.residuals().size());
        snap.phi_frozen = nopt.freeze_phi;
        snap.transient_majority_frozen = nopt.freeze_n || nopt.freeze_p;
        poisson_.set_dirichlet(phi_bc_);
        poisson_.set_permittivity(eps_);
        poisson_.compute_electric_field(phi, snap.Ex, snap.Ey, snap.Ez);
        if (use_lk_material_field) {
            const auto fields=lk_material_field_nd(g_,eps_,fe_mask_,fe_polarization_,phi,material_axis);
            for(size_t i=0;i<N;++i) { snap.Ex[i]=fields[3*i]; snap.Ey[i]=fields[3*i+1]; snap.Ez[i]=fields[3*i+2]; }
        }
        // The transient has the same mobility/HFS convention as its Newton
        // equations. Reconstruct currents at full core precision, not from
        // downcast carrier fields in the Python layer.
        compute_edge_currents(snap, phi, n, p);
        // A closed mobile-charge ledger is available when the two carrier
        // reservoirs occupy complete boundary planes.  This is the
        // finite-volume generalisation of the original 1-D endpoint ledger:
        // prescribed contact nodes are external reservoirs, while every other
        // node contributes its control volume.  The six possible terminal
        // currents are ordered x-min, x-max, y-min, y-max, z-min, z-max, with
        // a positive sign meaning current entering the free-node volume.
        // Edges between two contact nodes are outside this control volume,
        // including edges along intersections of complete contact planes.
        bool matching_carrier_contacts = n_bc_.size() == p_bc_.size() &&
            !n_bc_.empty();
        if (matching_carrier_contacts) {
            for (const auto& [idx, value] : n_bc_)
                if (!p_bc_.count(idx)) matching_carrier_contacts = false;
        }
        std::vector<char> ledger_contacts(N, 0);
        auto contact_node = [&](size_t idx) -> bool {
            return matching_carrier_contacts && n_bc_.count(idx) && p_bc_.count(idx);
        };
        auto mark_plane = [&](int axis, bool upper) -> bool {
            if ((axis == 0 && g_.nx < 2) ||
                (axis == 1 && g_.ny < 2) ||
                (axis == 2 && g_.nz < 2)) return false;
            bool complete = true;
            for (size_t k = 0; k < g_.nz; ++k)
                for (size_t j = 0; j < g_.ny; ++j)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const bool on_plane =
                            (axis == 0 && i == (upper ? g_.nx - 1 : 0)) ||
                            (axis == 1 && j == (upper ? g_.ny - 1 : 0)) ||
                            (axis == 2 && k == (upper ? g_.nz - 1 : 0));
                        if (on_plane) {
                            const size_t idx = g_.index(i, j, k);
                            if (!contact_node(idx)) complete = false;
                        }
                    }
            if (!complete) return false;
            for (size_t k = 0; k < g_.nz; ++k)
                for (size_t j = 0; j < g_.ny; ++j)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const bool on_plane =
                            (axis == 0 && i == (upper ? g_.nx - 1 : 0)) ||
                            (axis == 1 && j == (upper ? g_.ny - 1 : 0)) ||
                            (axis == 2 && k == (upper ? g_.nz - 1 : 0));
                        if (on_plane) ledger_contacts[g_.index(i, j, k)] = 1;
                    }
            return true;
        };
        const bool x_min = mark_plane(0, false), x_max = mark_plane(0, true);
        const bool y_min = mark_plane(1, false), y_max = mark_plane(1, true);
        const bool z_min = mark_plane(2, false), z_max = mark_plane(2, true);
        bool all_contacts_on_planes = matching_carrier_contacts;
        if (all_contacts_on_planes) {
            for (const auto& [idx, value] : n_bc_)
                if (!ledger_contacts[idx]) all_contacts_on_planes = false;
        }
        const int plane_count = static_cast<int>(x_min) + static_cast<int>(x_max) +
            static_cast<int>(y_min) + static_cast<int>(y_max) +
            static_cast<int>(z_min) + static_cast<int>(z_max);
        // Every BE transport row uses full node-centred volumes and common
        // face areas, independently of the LK field policy. Empty paired
        // blocked nodes have zero net charge and zero SG face flux.
        bool carrier_rows_closed = true;
        bool pair_sources_valid = true;
        bool full_charge_volumes = true;
        bool has_free_volume = false;
        bool has_mobile_free_volume = false;
        for (size_t idx = 0; idx < N; ++idx) {
            has_free_volume = has_free_volume || !ledger_contacts[idx];
            const bool mobile = paired_mobile_carriers(mu_n_eff[idx], mu_p_eff[idx]);
            const bool blocked = empty_blocked_carrier_row(mu_n_eff[idx], mu_p_eff[idx],
                n[idx], p[idx], G_opt_[idx], tau_n_[idx], tau_p_[idx]);
            if (!mobile && !blocked) carrier_rows_closed = false;
            has_mobile_free_volume = has_mobile_free_volume ||
                (mobile && !ledger_contacts[idx]);
            // Optical generation, SRH and Auger appear identically in the electron
            // and hole equations. Subtracting them for q*(p-n) cancels the
            // pair source exactly; this charge ledger makes no energy claim.
            if (!valid_pair_sources(G_opt_[idx], tau_n_[idx], tau_p_[idx]))
                pair_sources_valid = false;
            // This API scales Poisson charge only, not continuity storage or
            // face geometry. Do not advertise physical charge closure until
            // cut-cell transport has matching storage/flux weights.
            if (charge_volume_fraction_[idx] != TCAD_CONST(1.0))
                full_charge_volumes = false;
        }
        if (all_contacts_on_planes && plane_count >= 2 && carrier_rows_closed &&
            pair_sources_valid && full_charge_volumes && has_free_volume &&
            has_mobile_free_volume &&
            !nopt.freeze_n && !nopt.freeze_p) {
            for (size_t k = 0; k < g_.nz; ++k)
                for (size_t j = 0; j < g_.ny; ++j)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, j, k);
                        if (ledger_contacts[idx]) continue;
                        const real_t volume = g_.dx_cell(i) * g_.dy_cell(j) *
                            g_.dz_cell(k);
                        snap.mobile_charge += QE * (p[idx] - n[idx]) * volume;
                    }
            auto total_x = [&](size_t idx) { return snap.Jn_x[idx] + snap.Jp_x[idx]; };
            auto total_y = [&](size_t idx) { return snap.Jn_y[idx] + snap.Jp_y[idx]; };
            auto total_z = [&](size_t idx) { return snap.Jn_z[idx] + snap.Jp_z[idx]; };
            if (x_min) {
                real_t current = TCAD_CONST(0.0);
                for (size_t k = 0; k < g_.nz; ++k)
                    for (size_t j = 0; j < g_.ny; ++j) {
                        const size_t idx = g_.index(0, j, k);
                        if (ledger_contacts[idx + 1]) continue;
                        current += g_.dy_cell(j) * g_.dz_cell(k) * total_x(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            if (x_max) {
                real_t current = TCAD_CONST(0.0);
                for (size_t k = 0; k < g_.nz; ++k)
                    for (size_t j = 0; j < g_.ny; ++j) {
                        const size_t idx = g_.index(g_.nx - 2, j, k);
                        if (ledger_contacts[idx]) continue;
                        current -= g_.dy_cell(j) * g_.dz_cell(k) * total_x(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            if (y_min) {
                real_t current = TCAD_CONST(0.0);
                for (size_t k = 0; k < g_.nz; ++k)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, 0, k);
                        if (ledger_contacts[idx + g_.nx]) continue;
                        current += g_.dx_cell(i) * g_.dz_cell(k) * total_y(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            if (y_max) {
                real_t current = TCAD_CONST(0.0);
                for (size_t k = 0; k < g_.nz; ++k)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, g_.ny - 2, k);
                        if (ledger_contacts[idx]) continue;
                        current -= g_.dx_cell(i) * g_.dz_cell(k) * total_y(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            if (z_min) {
                real_t current = TCAD_CONST(0.0);
                for (size_t j = 0; j < g_.ny; ++j)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, j, 0);
                        if (ledger_contacts[idx + g_.nx * g_.ny]) continue;
                        current += g_.dx_cell(i) * g_.dy_cell(j) * total_z(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            if (z_max) {
                real_t current = TCAD_CONST(0.0);
                for (size_t j = 0; j < g_.ny; ++j)
                    for (size_t i = 0; i < g_.nx; ++i) {
                        const size_t idx = g_.index(i, j, g_.nz - 2);
                        if (ledger_contacts[idx]) continue;
                        current -= g_.dx_cell(i) * g_.dy_cell(j) * total_z(idx);
                    }
                snap.terminal_currents.push_back(current);
            }
            snap.transient_charge_ledger_available = true;
        }
        add_transient_electrostatic_ledger(snap, history.empty() ? nullptr : &history.back());
        add_transient_lk_ledger(snap, history.empty() ? nullptr : &history.back(), lk_drive_phi);
        return snap;
    };
    if (resuming) {
        // All setup allocations succeeded. Transfer ownership only now; the
        // candidate loop catches failures and returns this accepted prefix.
        history.swap(recovery->history_);
        transient_attempt_history_.swap(recovery->trace_);
    } else {
        history.push_back(snapshot(run_start, run_start, TCAD_CONST(0.0), true, true));
        if (recovery) {
            recovery->configuration_.swap(recovery_configuration); recovery->owner_ = this;
            recovery->proposal_ = effective_dt; recovery->rejected_ = 0;
        }
    }

    using CandidateTransaction = detail::TransientCandidateTransaction<SimulationResult>;
    const CandidateTransaction::State candidate_state = {
        &phi, &n, &p, &n_prev, &p_prev, &fe_polarization_, &fe_play_state_,
        &poisson_.fe_polarization_, &poisson_.fe_play_state_, &lk_drive_phi};
    const bool transactional_nls = fe_enabled_ && fe_model_ == 2;
    // A trial advances only its local BE interval. Callers can discard a
    // complete coarse/fine group without consuming polarization or dwell.
    auto attempt = [&](real_t start, real_t endpoint, real_t step_dt, const char* role) {
        TransientTrialHistory* diagnostic = nullptr;
        // Includes setup/snapshot copies and diagnostic sample copies outside
        // the solver try block. Preserve measured convergence independently.
        struct TrialExceptionMark {
            TransientTrialHistory*& trial;
            int entered_exceptions;
            ~TrialExceptionMark() noexcept {
                if (trial && std::uncaught_exceptions() > entered_exceptions)
                    trial->exception = true;
            }
        } exception_mark{diagnostic, std::uncaught_exceptions()};
        if (nonlinear_history_enabled_) {
            auto& trials = transient_attempt_history_.back().trials;
            trials.emplace_back();
            diagnostic = &trials.back();
            diagnostic->role = role;
            diagnostic->start_time = start;
            diagnostic->end_time = endpoint;
            diagnostic->step_dt = step_dt;
        }
        std::optional<CandidateTransaction> candidate;
        if (transactional_nls) candidate.emplace(candidate_state, phi_bc_, history);
        nopt.transient_dt = step_dt;
        nopt.n_prev = n_prev;
        nopt.p_prev = p_prev;
        const auto phi_previous = phi;
        const auto fe_previous = fe_polarization_;
        const auto fe_play_previous = fe_play_state_;
        const auto contacts_previous = driven ? phi_bc_ : std::map<size_t, real_t>{};
        auto restore_attempt = [&]() {
            if (candidate) { candidate->restore(); return; }
            phi = phi_previous; n = n_prev; p = p_prev;
            if (driven) phi_bc_ = contacts_previous;
            if (fe_enabled_) {
                fe_polarization_ = fe_previous;
                fe_play_state_ = fe_play_previous;
                poisson_.set_fe_polarization(fe_polarization_);
                if (fe_model_ == 1 || fe_model_ == 3)
                    poisson_.set_fe_play_state(fe_play_state_);
            }
        };
        bool ok = false;
        try {
            apply_voltage(endpoint);
            // Predict the endpoint potential algebraically with the accepted
            // carriers/P. This also applies tiny voltage changes that Newton's
            // absolute residual tolerance would otherwise leave unapplied.
            // For pure capacitors it avoids an unnecessary 3N Newton solve.
            if (driven) project_potential(fe_previous);
            if (fe_enabled_ && fe_model_ == 0) lk_drive_phi = phi;
            if (fe_enabled_ && !use_lk_coupled) {
                // Drive kinetics with this endpoint's applied field and the
                // previous accepted P/carriers. This algebraic projection
                // consumes no dwell and does not advance hidden FE memory.
                poisson_.set_fe_polarization(fe_polarization_);
                if (fe_model_ == 1 || fe_model_ == 3)
                    poisson_.set_fe_play_state(fe_play_state_);
                poisson_.update_ferroelectric_polarization_transient(phi, step_dt);
                fe_polarization_ = poisson_.fe_polarization();
                if (fe_model_ == 1 || fe_model_ == 3)
                    fe_play_state_ = poisson_.fe_play_state();
            }

            if (use_lk_material_chain) {
                if (diagnostic) { diagnostic->solver = "lk_material_field_1d"; diagnostic->solver_called=true; }
                ok=solve_lk_material_chain(g_,eps_,fe_mask_,fe_previous,fe_alpha_,fe_beta_,
                    fe_gamma_,fe_E_bi_,fe_eps_fe_,fe_polar_axis_,material_axis,step_dt,
                    phi_bc_.at(0),phi_bc_.at(N-1),max_iter_,phi,fe_polarization_,material_samples,Nd_minus_Na_);
                if (ok) { poisson_.set_fe_polarization(fe_polarization_); lk_drive_phi=phi; }
            } else {
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
            if (fe_enabled_)
                newton_.set_ferroelectric_polarization(fe_mask_, fe_polarization_);
            if (use_lk_coupled)
                newton_.set_transient_lk(fe_mask_, fe_previous, fe_alpha_, fe_beta_,
                    fe_gamma_, fe_E_bi_, fe_eps_fe_, fe_polar_axis_, use_lk_material_field);

            if (diagnostic) diagnostic->solver_called = true;
            ok = newton_.solve(phi, n, p);
            if (diagnostic) diagnostic->converged = ok;
            if (ok && use_lk_coupled) {
                fe_polarization_ = newton_.ferroelectric_polarization();
                poisson_.set_fe_polarization(fe_polarization_);
                lk_drive_phi = phi;
            }
            }
        } catch (...) {
            // Restore before diagnostic copies, which can themselves allocate.
            if (candidate) restore_attempt();
            if (diagnostic) {
                diagnostic->exception = true;
                if (diagnostic->solver_called)
                    diagnostic->samples = use_lk_material_chain ? material_samples : newton_.nonlinear_samples();
                auto& group = transient_attempt_history_.back();
                group.status = "exception";
                group.stopping_reason = "exception";
            }
            if (!candidate) restore_attempt();
            throw;
        }
        if (diagnostic) {
            diagnostic->converged = ok;
            diagnostic->samples = use_lk_material_chain ? material_samples : newton_.nonlinear_samples();
        }
        if (!ok) restore_attempt();
        else if (candidate) candidate->commit();
        return ok;
    };

    auto endpoint = [&](real_t time, real_t proposal, real_t limit) {
        real_t target = std::min(time + proposal, limit);
        const real_t roundoff = TCAD_CONST(16.0) * std::numeric_limits<double>::epsilon() *
            std::max(abs_q(limit), abs_q(proposal));
        const bool safe_snap = !transient_lk_substepping_ ||
            ((limit-time) <= proposal *
                (TCAD_CONST(1.0) + TCAD_CONST(32.0) * std::numeric_limits<double>::epsilon()) &&
             fe_alpha_ + fe_gamma_/(limit-time) > TCAD_CONST(0.0));
        if (limit-target <= roundoff && safe_snap) target = limit;
        if ((transient_lk_substepping_ || error_control) && target < limit) {
            double exported = (double)target;
            if ((real_t)exported > target)
                exported = std::nextafter(exported, -std::numeric_limits<double>::infinity());
            target = (real_t)exported;
        }
        if (error_control && target < limit &&
            std::nextafter((double)target, std::numeric_limits<double>::infinity()) >= (double)limit) {
            // A remaining one-ULP tail cannot be split into two exposed half
            // steps. Reserve a two-ULP final interval rather than accepting a
            // state from which the mandatory error estimate is impossible.
            double reserved = std::nextafter((double)limit,
                -std::numeric_limits<double>::infinity());
            target = (real_t)std::nextafter(reserved,
                -std::numeric_limits<double>::infinity());
        }
        if (target <= time ||
            ((transient_lk_substepping_ || error_control) && (double)target <= (double)time))
            throw std::runtime_error("transient step cannot advance the returned timeline");
        return target;
    };
    auto nls_event_endpoint = [&](real_t start, real_t proposed) {
        if (!transient_nls_event_control_) return proposed;
        // All probes are independent electrostatic solves at frozen accepted
        // n/p/P. Neither contact maps nor live solver/material memory change.
        PoissonSolver observer(g_);
        observer.set_ferroelectric(fe_mask_,fe_alpha_,fe_beta_);
        observer.set_ferroelectric_model(2);
        observer.set_ferroelectric_polar_axis(fe_polar_axis_);
        observer.set_ferroelectric_builtin_field(fe_E_bi_);
        observer.set_fe_polarization(fe_polarization_);
        auto probe = [&](real_t t) {
            auto boundary=contacts.configured;
            const auto [lo,f]=waveform_segment(t);
            for (const auto& [idx,values]:transient_voltage_offsets_)
                boundary[idx]=waveform_voltage(idx,values,lo,f);
            auto prediction=phi;
            project_potential_at(fe_polarization_,boundary,prediction);
            return observer.ferroelectric_nls_drive(prediction);
        };
        const auto first=probe(start), last=probe(proposed);
        const real_t a=first.raw_mean_field, b=last.raw_mean_field;
        const bool opposite=(a>0 && b<0)||(a<0 && b>0);
        const real_t width=transient_nls_event_half_width_;
        if (first.mean_field==0) {
            if (last.mean_field==0) return proposed;
            // A waveform knot or restarted checkpoint can be the root itself.
            // Sample its outgoing side as well; a flat numerical-zero band
            // must not trigger arbitrarily many tiny steps along a plateau.
            const real_t outgoing=std::min(proposed,start+width);
            if (outgoing<=start)
                throw std::runtime_error("NLS event step cannot advance timeline");
            if (outgoing<proposed && probe(outgoing).mean_field==0) return proposed;
            return outgoing;
        }
        if (!opposite && last.mean_field!=0) return proposed;
        real_t low=start, high=proposed;
        // A guarded endpoint is already a numerical root. Take a finite step
        // on its incoming side before ever accepting that zero-field endpoint.
        if (last.mean_field!=0) {
            bool resolved=false;
            for (size_t i=0;i<128;++i) {
                if (high-low<=width*TCAD_CONST(1e-24)) {resolved=true;break;}
                const real_t middle=low+(high-low)/TCAD_CONST(2.0);
                if (middle<=low || middle>=high)
                    throw std::runtime_error("NLS event root exceeds time resolution");
                const real_t value=probe(middle).raw_mean_field;
                if (value==0) {low=high=middle;resolved=true;break;}
                if ((value>0)==(a>0)) low=middle; else high=middle;
            }
            if (!resolved) throw std::runtime_error("NLS event root localization exhausted");
        } else low=high=proposed;
        const real_t root=low+(high-low)/TCAD_CONST(2.0);
        const real_t incoming=root-width;
        // Recompute from accepted state on every call. Once at the incoming
        // side, cross a narrow interval instead of repeatedly approaching it.
        const real_t selected=incoming>start+width/TCAD_CONST(8.0)
            ? incoming : std::min(proposed,root+width);
        if (selected<=start || selected>proposed)
            throw std::runtime_error("NLS event step cannot advance timeline");
        return selected;
    };
    real_t time = run_start, proposal = recovery ? recovery->proposal_ : effective_dt;
    size_t next_knot = 1;
    while (time < transient_t_final_) {
        while (driven && next_knot < transient_waveform_times_.size() &&
               transient_waveform_times_[next_knot] <= time) ++next_knot;
        const real_t limit = driven && next_knot < transient_waveform_times_.size()
            ? std::min(transient_t_final_, transient_waveform_times_[next_knot])
            : transient_t_final_;
        size_t rejected = recovery ? recovery->rejected_ : 0;
        size_t recovery_retries = 0;
        while (true) {
            const size_t trace_start = transient_attempt_history_.size();
            auto withdraw_recovery = [&](const char* status, const char* reason) noexcept {
                if (transient_attempt_history_.size() == trace_start) return;
                auto& group = transient_attempt_history_.back();
                group.accepted = false;
                // Recoverable groups reserve both labels before insertion.
                auto label = [](std::string& out, const char* in) noexcept {
                    out.clear(); for (; *in; ++in) out.push_back(*in);
                };
                label(group.status, status); label(group.stopping_reason, reason);
                for (auto& trial : group.trials) { trial.retained = false; trial.exception = true; }
            };
            try {
            const real_t target = nls_event_endpoint(time, endpoint(time, proposal, limit)), dt = target-time;
            std::optional<CandidateTransaction> candidate_group;
            if (transactional_nls) candidate_group.emplace(candidate_state, phi_bc_, history, &time);
            TransientAttemptHistory* diagnostic = nullptr;
            if (nonlinear_history_enabled_) {
                if (recovery) {
                    TransientAttemptHistory prepared;
                    prepared.status.reserve(32); prepared.stopping_reason.reserve(32);
                    transient_attempt_history_.push_back(std::move(prepared));
                } else transient_attempt_history_.emplace_back();
                diagnostic = &transient_attempt_history_.back();
                diagnostic->start_time = time;
                diagnostic->end_time = target;
                diagnostic->step_dt = dt;
                diagnostic->retry_index = error_control ? rejected : recovery ? recovery_retries : rejected;
                diagnostic->error_control = error_control;
                diagnostic->polarization_control = polarization_control;
                diagnostic->electrical_control = electrical_control;
            }
            auto finish_diagnostic = [&](bool accepted, const std::string& status,
                                         const std::string& reason) {
                if (!diagnostic) return;
                diagnostic->accepted = accepted;
                diagnostic->status = status;
                diagnostic->stopping_reason = reason;
                for (auto& trial : diagnostic->trials)
                    trial.retained = accepted && trial.converged && trial.role != "coarse";
            };
            if (!error_control) {
                if (!attempt(time, target, dt, "fixed")) {
                    finish_diagnostic(false, "solver_failure", "solver_failure");
                    if (recovery) {
                        ++recovery->solver_failures_;
                        finish_diagnostic(false, "solver_failure", recovery_retries < max_retries ? "retry" : "retry_limit");
                        if (recovery_retries < max_retries) {
                            ++recovery_retries; ++recovery->retries_; continue;
                        }
                        recovery->status_ = NlsContinuationStatus::solver_failure;
                        return history;
                    }
                    history.push_back(snapshot(time, target, TCAD_CONST(0.0), false, false));
                    if (candidate_group) candidate_group->commit();
                    return history;
                }
                finish_diagnostic(true, "accepted", "accepted");
                time = target; n_prev = n; p_prev = p;
                history.push_back(snapshot(time, target, dt, true, false));
                if (candidate_group) candidate_group->commit();
                break;
            }
            const auto phi_start = phi, n_start = n_prev, p_start = p_prev;
            const auto P_start = fe_polarization_, play_start = fe_play_state_;
            const auto contact_start = driven ? phi_bc_ : std::map<size_t, real_t>{};
            const auto drive_start = lk_drive_phi;
            const size_t history_start = history.size();
            auto restore_group = [&]() {
                if (candidate_group) { candidate_group->restore(); return; }
                phi = phi_start; n = n_start; p = p_start;
                n_prev = n_start; p_prev = p_start;
                fe_polarization_ = P_start; fe_play_state_ = play_start;
                poisson_.set_fe_polarization(fe_polarization_);
                if (driven) phi_bc_ = contact_start;
                lk_drive_phi = drive_start;
                history.resize(history_start);
            };
            const real_t mid = (real_t)(double)(time+dt/TCAD_CONST(2.0));
            bool solved = false, inputs_available = false;
            real_t ratio = TCAD_CONST(0.0), exported_ratio = TCAD_CONST(0.0);
            std::vector<real_t> coarse, delta;
            real_t electrical_ratio = TCAD_CONST(0.0), exported_electrical_ratio = TCAD_CONST(0.0);
            std::vector<real_t> coarse_phi, coarse_n, coarse_p, delta_phi, delta_n, delta_p;
            std::string status = "solver_failure";
            try {
                if (mid <= time || mid >= target ||
                    (double)mid <= (double)time || (double)mid >= (double)target) {
                    status = "time_resolution";
                } else if (attempt(time, target, dt, "coarse")) {
                    if (polarization_control) coarse = fe_polarization_;
                    if (electrical_control) {
                        coarse_phi = phi; coarse_n = n; coarse_p = p;
                    }
                    restore_group();
                    // The coarse candidate was discarded. Prepare a new
                    // checkpoint before either fine half-step can mutate it.
                    if (candidate_group) candidate_group.emplace(candidate_state, phi_bc_, history, &time);
                    if (attempt(time, mid, mid-time, "fine_first")) {
                        n_prev = n; p_prev = p;
                        history.push_back(snapshot(mid, mid, mid-time, true, false));
                        if (attempt(mid, target, target-mid, "fine_second")) {
                            n_prev = n; p_prev = p;
                            history.push_back(snapshot(target, target, target-mid, true, false));
                            delta.resize(coarse.size());
                            inputs_available = true;
                            bool all_finite = true;
                            for (size_t i = 0; i < coarse.size(); ++i) {
                                delta[i] = fe_polarization_[i]-coarse[i];
                                all_finite = all_finite && isfinite_q(delta[i]) &&
                                    isfinite_q(coarse[i]) && isfinite_q(fe_polarization_[i]);
                                const real_t scale = polarization_atol +
                                    polarization_rtol * std::max(
                                        abs_q(fe_polarization_[i]), abs_q(coarse[i]));
                                ratio = std::max(ratio, abs_q(delta[i])/scale);
                                inputs_available = inputs_available &&
                                    std::isfinite((double)fe_polarization_[i]) &&
                                    std::isfinite((double)coarse[i]) &&
                                    std::isfinite((double)delta[i]) &&
                                    (delta[i] == TCAD_CONST(0.0) || (double)delta[i] != 0.0);
                                if (inputs_available) {
                                    const real_t exported_scale = polarization_atol +
                                        polarization_rtol * std::max(
                                            abs_q((real_t)(double)fe_polarization_[i]),
                                            abs_q((real_t)(double)coarse[i]));
                                    exported_ratio = std::max(exported_ratio,
                                        abs_q((real_t)(double)delta[i])/exported_scale);
                                }
                            }
                            if (electrical_control) {
                                // One group shares one acceptance decision. Absolute
                                // voltage error avoids dependence on the potential gauge.
                                auto estimate = [&](const std::vector<real_t>& fine,
                                    const std::vector<real_t>& trial, std::vector<real_t>& change,
                                    real_t absolute, real_t relative) {
                                    change.resize(fine.size());
                                    for (size_t i = 0; i < fine.size(); ++i) {
                                        change[i] = fine[i]-trial[i];
                                        const real_t scale = absolute + relative *
                                            std::max(abs_q(fine[i]), abs_q(trial[i]));
                                        const real_t norm = abs_q(change[i])/scale;
                                        all_finite = all_finite && isfinite_q(fine[i]) &&
                                            isfinite_q(trial[i]) && isfinite_q(change[i]) && isfinite_q(norm);
                                        electrical_ratio = std::max(electrical_ratio, norm);
                                        const bool representable = std::isfinite((double)fine[i]) &&
                                            std::isfinite((double)trial[i]) && std::isfinite((double)change[i]) &&
                                            (change[i] == TCAD_CONST(0.0) || (double)change[i] != 0.0);
                                        inputs_available = inputs_available && representable;
                                        if (representable) {
                                            const real_t exported_scale = absolute + relative * std::max(
                                                abs_q((real_t)(double)fine[i]), abs_q((real_t)(double)trial[i]));
                                            exported_electrical_ratio = std::max(exported_electrical_ratio,
                                                abs_q((real_t)(double)change[i])/exported_scale);
                                        }
                                    }
                                };
                                estimate(phi, coarse_phi, delta_phi, phi_atol, TCAD_CONST(0.0));
                                estimate(n, coarse_n, delta_n, carrier_atol, carrier_rtol);
                                estimate(p, coarse_p, delta_p, carrier_atol, carrier_rtol);
                                inputs_available = inputs_available && std::isfinite((double)electrical_ratio) &&
                                    abs_q(exported_electrical_ratio-electrical_ratio) <= TCAD_CONST(5.0e-9) *
                                        std::max(abs_q(exported_electrical_ratio), abs_q(electrical_ratio));
                            }
                            solved = all_finite && isfinite_q(ratio) && isfinite_q(electrical_ratio);
                            inputs_available = inputs_available && std::isfinite((double)ratio);
                            // The public auditor recomputes the norm from the
                            // exported vectors. Reject lost/overly quantized
                            // diagnostics before committing either half step.
                            // Leave margin under its default relative tolerance.
                            inputs_available = inputs_available &&
                                abs_q(exported_ratio-ratio) <= TCAD_CONST(5.0e-9) *
                                    std::max(abs_q(exported_ratio), abs_q(ratio));
                            status = solved && inputs_available
                                ? "accuracy_limit" : "unrepresentable_estimate";
                        }
                    }
                }
            } catch (...) {
                restore_group();
                finish_diagnostic(false, "exception", "exception");
                throw;
            }
            if (diagnostic) {
                diagnostic->error_estimate_available = solved && inputs_available;
                if (solved && inputs_available) {
                    diagnostic->polarization_error_ratio = ratio;
                    diagnostic->electrical_error_ratio = electrical_ratio;
                    diagnostic->exported_polarization_error_ratio = exported_ratio;
                    diagnostic->exported_electrical_error_ratio = exported_electrical_ratio;
                }
            }
            auto annotate = [&](SimulationResult& state, const std::string& label) {
                state.lk_error_status = label;
                state.lk_error_ratio = std::isfinite((double)ratio) ? ratio : TCAD_CONST(0.0);
                state.lk_electrical_error_ratio = std::isfinite((double)electrical_ratio) ? electrical_ratio : TCAD_CONST(0.0);
                state.lk_error_estimate_available = solved && inputs_available;
                state.lk_error_interval = dt; state.lk_error_end = target;
                state.lk_rejected_attempts = rejected;
            };
            auto attach_electrical_estimate = [&](SimulationResult& state) {
                state.lk_coarse_phi = std::move(coarse_phi); state.lk_delta_phi = std::move(delta_phi);
                state.lk_coarse_n = std::move(coarse_n); state.lk_delta_n = std::move(delta_n);
                state.lk_coarse_p = std::move(coarse_p); state.lk_delta_p = std::move(delta_p);
            };
            if (solved && inputs_available && ratio <= TCAD_CONST(1.0) && exported_ratio <= TCAD_CONST(1.0) &&
                electrical_ratio <= TCAD_CONST(1.0) && exported_electrical_ratio <= TCAD_CONST(1.0)) {
                finish_diagnostic(true, "accepted", "accepted");
                annotate(history[history_start], "accepted");
                annotate(history[history_start+1], "accepted");
                history.back().lk_coarse_P = std::move(coarse);
                history.back().lk_error_delta_P = std::move(delta);
                attach_electrical_estimate(history.back());
                time = target;
                const real_t factor = std::min(TCAD_CONST(2.0), std::max(TCAD_CONST(0.5),
                    TCAD_CONST(0.9)/sqrt_q(std::max(std::max(ratio, electrical_ratio), TCAD_CONST(1.0e-12)))));
                proposal = std::min(effective_dt, std::max(error_min_dt, dt*factor));
                if (recovery) { recovery->proposal_ = proposal; recovery->rejected_ = 0; }
                if (candidate_group) candidate_group->commit();
                break;
            }
            restore_group();
            if (recovery && status == "solver_failure") {
                ++recovery->solver_failures_;
                const bool retry = recovery_retries < max_retries;
                finish_diagnostic(false, status, retry ? "retry" : "retry_limit");
                if (!retry) { recovery->status_ = NlsContinuationStatus::solver_failure; return history; }
                ++recovery_retries; ++recovery->retries_;
                continue;
            }
            if (status == "time_resolution" || status == "unrepresentable_estimate" ||
                rejected >= error_max_reject ||
                dt/TCAD_CONST(2.0) < error_min_dt *
                    (TCAD_CONST(1.0) - TCAD_CONST(4.0) * std::numeric_limits<double>::epsilon())) {
                finish_diagnostic(false, status,
                    status == "time_resolution" || status == "unrepresentable_estimate"
                        ? status : rejected >= error_max_reject ? "max_reject" : "min_dt");
                if (recovery) {
                    recovery->status_ = status == "time_resolution" ? NlsContinuationStatus::time_resolution :
                        status == "unrepresentable_estimate" ? NlsContinuationStatus::unrepresentable_estimate :
                        rejected >= error_max_reject ? NlsContinuationStatus::max_reject : NlsContinuationStatus::minimum_step;
                    return history;
                }
                auto failed = snapshot(time, target, TCAD_CONST(0.0), false, false);
                annotate(failed, status);
                // Include the terminal discarded proposal as well as retries.
                failed.lk_rejected_attempts = rejected+1;
                failed.lk_coarse_P = std::move(coarse);
                failed.lk_error_delta_P = std::move(delta);
                attach_electrical_estimate(failed);
                history.push_back(std::move(failed));
                return history;
            }
            finish_diagnostic(false, status, "retry");
            ++rejected;
            proposal = dt/TCAD_CONST(2.0);
            if (recovery) { recovery->proposal_ = proposal; recovery->rejected_ = rejected; }
            } catch (const std::bad_alloc&) {
                if (!recovery) throw;
                ++recovery->allocation_failures_;
                const bool retry = recovery_retries < max_retries;
                withdraw_recovery("allocation_failure", retry ? "retry" : "retry_limit");
                if (!retry) { recovery->status_ = NlsContinuationStatus::allocation_failure; return history; }
                ++recovery_retries; ++recovery->retries_;
            } catch (...) {
                if (!recovery) throw;
                withdraw_recovery("unexpected_failure", "stopped");
                recovery->status_ = NlsContinuationStatus::unexpected_failure;
                return history;
            }
        }
    }

    if (recovery) recovery->status_ = NlsContinuationStatus::complete;
    return history;
}

} // namespace tcad
