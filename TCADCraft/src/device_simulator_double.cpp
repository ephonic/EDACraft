#include "device_simulator_double.h"
#include <stdexcept>
#include <utility>

namespace tcad {

DeviceSimulatorDouble::DeviceSimulatorDouble(size_t nx, size_t ny, size_t nz,
                                             double dx, double dy, double dz)
    : sim_(nx, ny, nz, (real_t)dx, (real_t)dy, (real_t)dz) {}

std::vector<real_t> DeviceSimulatorDouble::to_real_t(const std::vector<double>& v) const {
    std::vector<real_t> r(v.size());
    for (size_t i = 0; i < v.size(); ++i) r[i] = (real_t)v[i];
    return r;
}

std::vector<double> DeviceSimulatorDouble::to_double(const std::vector<real_t>& v) const {
    std::vector<double> r(v.size());
    for (size_t i = 0; i < v.size(); ++i) r[i] = (double)v[i];
    return r;
}

void DeviceSimulatorDouble::set_permittivity(const std::vector<double>& eps) {
    sim_.set_permittivity(to_real_t(eps));
}

void DeviceSimulatorDouble::set_edge_permittivity(const std::vector<double>& x_plus,
                                                  const std::vector<double>& x_minus,
                                                  const std::vector<double>& y_plus,
                                                  const std::vector<double>& y_minus,
                                                  const std::vector<double>& z_plus,
                                                  const std::vector<double>& z_minus) {
    sim_.set_edge_permittivity(to_real_t(x_plus), to_real_t(x_minus),
                               to_real_t(y_plus), to_real_t(y_minus),
                               to_real_t(z_plus), to_real_t(z_minus));
}

void DeviceSimulatorDouble::set_mobility(const std::vector<double>& mu_n, const std::vector<double>& mu_p) {
    sim_.set_mobility(to_real_t(mu_n), to_real_t(mu_p));
}

void DeviceSimulatorDouble::set_doping(const std::vector<double>& Nd_minus_Na) {
    sim_.set_doping(to_real_t(Nd_minus_Na));
}

void DeviceSimulatorDouble::set_charge_volume_fraction(
    const std::vector<double>& fraction) {
    sim_.set_charge_volume_fraction(to_real_t(fraction));
}

void DeviceSimulatorDouble::set_optical_generation(const std::vector<double>& G_opt) {
    sim_.set_optical_generation(to_real_t(G_opt));
}

void DeviceSimulatorDouble::set_btbt_weight(const std::vector<double>& weight) {
    sim_.set_btbt_weight(to_real_t(weight));
}

void DeviceSimulatorDouble::set_recombination(const std::vector<double>& tau_n, const std::vector<double>& tau_p) {
    sim_.set_recombination(to_real_t(tau_n), to_real_t(tau_p));
}

void DeviceSimulatorDouble::set_thermal_voltage(double VT) {
    sim_.set_thermal_voltage((real_t)VT);
}

void DeviceSimulatorDouble::set_effective_dos(const std::vector<double>& Nc, const std::vector<double>& Nv) {
    sim_.set_effective_dos(to_real_t(Nc), to_real_t(Nv));
}

void DeviceSimulatorDouble::set_bandgap(const std::vector<double>& Eg) {
    sim_.set_bandgap(to_real_t(Eg));
}

void DeviceSimulatorDouble::set_dirichlet_potential(const std::map<size_t, double>& bc) {
    std::map<size_t, real_t> bc_q;
    for (const auto& [k, v] : bc) bc_q[k] = (real_t)v;
    sim_.set_dirichlet_potential(bc_q);
}

void DeviceSimulatorDouble::set_electron_bc(const std::map<size_t, double>& bc) {
    std::map<size_t, real_t> bc_q;
    for (const auto& [k, v] : bc) bc_q[k] = (real_t)v;
    sim_.set_electron_bc(bc_q);
}

void DeviceSimulatorDouble::set_hole_bc(const std::map<size_t, double>& bc) {
    std::map<size_t, real_t> bc_q;
    for (const auto& [k, v] : bc) bc_q[k] = (real_t)v;
    sim_.set_hole_bc(bc_q);
}

void DeviceSimulatorDouble::set_quantum_enabled(bool enable) {
    sim_.set_quantum_enabled(enable);
}

void DeviceSimulatorDouble::set_density_gradient_coefficients(double bn, double bp) {
    sim_.set_density_gradient_coefficients(static_cast<real_t>(bn),
                                           static_cast<real_t>(bp));
}

void DeviceSimulatorDouble::set_density_gradient_silicon_multivalley(
    bool enable, double longitudinal_mass, double transverse_mass,
    size_t subbands) {
    sim_.set_density_gradient_silicon_multivalley(
        enable, static_cast<real_t>(longitudinal_mass),
        static_cast<real_t>(transverse_mass), subbands);
}

void DeviceSimulatorDouble::set_density_gradient_interface_distance_factor(
    double factor) {
    sim_.set_density_gradient_interface_distance_factor(
        static_cast<real_t>(factor));
}

void DeviceSimulatorDouble::set_density_gradient_potential_form(bool enable) {
    sim_.set_density_gradient_potential_form(enable);
}

void DeviceSimulatorDouble::set_density_gradient_step_boundary(
    bool enable, double electron_barrier_eV, double hole_barrier_eV,
    double electron_barrier_mass, double hole_barrier_mass,
    double electron_gamma, double hole_gamma,
    double electron_theta, double hole_theta) {
    sim_.set_density_gradient_step_boundary(
        enable, static_cast<real_t>(electron_barrier_eV),
        static_cast<real_t>(hole_barrier_eV),
        static_cast<real_t>(electron_barrier_mass),
        static_cast<real_t>(hole_barrier_mass),
        static_cast<real_t>(electron_gamma),
        static_cast<real_t>(hole_gamma),
        static_cast<real_t>(electron_theta),
        static_cast<real_t>(hole_theta));
}

void DeviceSimulatorDouble::set_gummel_max_iter(size_t max_iter) {
    sim_.set_gummel_max_iter(max_iter);
}

void DeviceSimulatorDouble::set_tolerance(double tol) {
    sim_.set_tolerance((real_t)tol);
}

void DeviceSimulatorDouble::set_poisson_solver_type(int type) {
    sim_.set_poisson_solver_type(type);
}

void DeviceSimulatorDouble::set_continuity_solver_type(int type) {
    sim_.set_continuity_solver_type(type);
}

void DeviceSimulatorDouble::set_use_newton(bool enable) {
    sim_.set_use_newton(enable);
}

void DeviceSimulatorDouble::set_newton_primary(bool enable) {
    sim_.set_newton_primary(enable);
}

EquilibriumResultDouble DeviceSimulatorDouble::solve_equilibrium(size_t max_iter, double tolerance,
        const std::vector<char>& carrier_mask) {
    const auto r = sim_.solve_equilibrium(max_iter, static_cast<real_t>(tolerance), carrier_mask);
    EquilibriumResultDouble out;
    out.phi = to_double(r.phi); out.n = to_double(r.n); out.p = to_double(r.p);
    out.residual_history = to_double(r.residual_history);
    out.update_history = to_double(r.update_history);
    out.damping_history = to_double(r.damping_history);
    out.converged = r.converged; out.iterations = r.iterations; out.status = r.status;
    return out;
}

void DeviceSimulatorDouble::set_ohmic_contacts(const std::set<size_t>& nodes,
                                                const std::map<size_t, double>& EFn,
                                                const std::map<size_t, double>& EFp,
                                                double ni) {
    std::set<size_t> n;
    std::map<size_t, real_t> ef_n, ef_p;
    for (auto idx : nodes) n.insert(idx);
    for (auto& kv : EFn) ef_n[kv.first] = (real_t)kv.second;
    for (auto& kv : EFp) ef_p[kv.first] = (real_t)kv.second;
    sim_.set_ohmic_contacts(n, ef_n, ef_p, (real_t)ni);
}

void DeviceSimulatorDouble::clear_ohmic_contacts() {
    sim_.clear_ohmic_contacts();
}

void DeviceSimulatorDouble::set_newton_freeze_phi(bool enable) { sim_.set_newton_freeze_phi(enable); }
void DeviceSimulatorDouble::set_newton_freeze_n(bool enable) { sim_.set_newton_freeze_n(enable); }
void DeviceSimulatorDouble::set_newton_freeze_p(bool enable) { sim_.set_newton_freeze_p(enable); }

void DeviceSimulatorDouble::set_newton_damping(double damping) {
    sim_.set_newton_damping((real_t)damping);
}

void DeviceSimulatorDouble::set_newton_min_damping(double min_damping) {
    sim_.set_newton_min_damping((real_t)min_damping);
}

void DeviceSimulatorDouble::set_newton_use_line_search(bool enable) {
    sim_.set_newton_use_line_search(enable);
}

void DeviceSimulatorDouble::set_newton_line_search_max(size_t max) {
    sim_.set_newton_line_search_max(max);
}

void DeviceSimulatorDouble::set_newton_use_log_damping(bool enable) {
    sim_.set_newton_use_log_damping(enable);
}

void DeviceSimulatorDouble::set_newton_use_log_space(bool enable) {
    sim_.set_newton_use_log_space(enable);
}

void DeviceSimulatorDouble::set_newton_log_density_update(const std::string& mode) {
    sim_.set_newton_log_density_update(mode);
}

std::string DeviceSimulatorDouble::get_newton_log_density_update() const {
    return sim_.get_newton_log_density_update();
}

void DeviceSimulatorDouble::set_newton_jacobian_reuse_threshold(double threshold) {
    sim_.set_newton_jacobian_reuse_threshold((real_t)threshold);
}

void DeviceSimulatorDouble::set_thermal_coupling_enabled(bool enable) {
    sim_.set_thermal_coupling_enabled(enable);
}

void DeviceSimulatorDouble::set_thermal_conductivity(const std::vector<double>& kappa) {
    sim_.set_thermal_conductivity(to_real_t(kappa));
}

void DeviceSimulatorDouble::set_ambient_temperature(double T_ambient) {
    sim_.set_ambient_temperature((real_t)T_ambient);
}

void DeviceSimulatorDouble::set_thermal_dirichlet(const std::map<size_t, double>& bc) {
    std::map<size_t, real_t> bc_q;
    for (const auto& [k, v] : bc) bc_q[k] = (real_t)v;
    sim_.set_thermal_dirichlet(bc_q);
}

void DeviceSimulatorDouble::set_btbt_enabled(bool enable) {
    sim_.set_btbt_enabled(enable);
}

void DeviceSimulatorDouble::set_btbt_params(double A, double B, double D) {
    sim_.set_btbt_params((real_t)A, (real_t)B, (real_t)D);
}

void DeviceSimulatorDouble::set_btbt_field_mode(int mode) {
    sim_.set_btbt_field_mode(mode);
}

void DeviceSimulatorDouble::set_btbt_field_options(int mode, double cap) {
    sim_.set_btbt_field_options(mode, (real_t)cap);
}

void DeviceSimulatorDouble::set_btbt_field_shape(int mode, double cap,
                                                 double alpha, double ref) {
    sim_.set_btbt_field_shape(mode, (real_t)cap, (real_t)alpha, (real_t)ref);
}

void DeviceSimulatorDouble::set_btbt_continuity_scale(double scale) {
    sim_.set_btbt_continuity_scale((real_t)scale);
}

void DeviceSimulatorDouble::set_btbt_use_nonlocal(bool enable) {
    sim_.set_btbt_use_nonlocal(enable);
}

void DeviceSimulatorDouble::set_btbt_nonlocal_params(double tunnel_path_frac, size_t wkb_npts) {
    sim_.set_btbt_nonlocal_params((real_t)tunnel_path_frac, wkb_npts);
}

void DeviceSimulatorDouble::set_btbt_nonlocal_mass(double mass_ratio) {
    sim_.set_btbt_nonlocal_mass((real_t)mass_ratio);
}

void DeviceSimulatorDouble::set_high_field_saturation(bool enable, double vsat_n,
                                                      double vsat_p, double beta_n,
                                                      double beta_p, int driving) {
    sim_.set_high_field_saturation(enable, (real_t)vsat_n, (real_t)vsat_p,
                                   (real_t)beta_n, (real_t)beta_p, driving);
}

void DeviceSimulatorDouble::set_hfs_quasi_fermi_at_contacts(bool enabled) {
    sim_.set_hfs_quasi_fermi_at_contacts(enabled);
}

bool DeviceSimulatorDouble::get_hfs_quasi_fermi_at_contacts() const {
    return sim_.get_hfs_quasi_fermi_at_contacts();
}

void DeviceSimulatorDouble::set_high_field_reference_density(double n0, double p0) { sim_.set_high_field_reference_density(n0,p0); }
double DeviceSimulatorDouble::get_high_field_reference_density_n() const { return (double)sim_.get_high_field_reference_density_n(); }
double DeviceSimulatorDouble::get_high_field_reference_density_p() const { return (double)sim_.get_high_field_reference_density_p(); }
void DeviceSimulatorDouble::set_hfs_low_field_cutoff(double cutoff) {
    sim_.set_hfs_low_field_cutoff((real_t)cutoff);
}

double DeviceSimulatorDouble::get_hfs_low_field_cutoff() const {
    return (double)sim_.get_hfs_low_field_cutoff();
}

void DeviceSimulatorDouble::set_ii_enabled(bool enable) {
    sim_.set_ii_enabled(enable);
}

void DeviceSimulatorDouble::set_ii_reference_density(double n0, double p0) { sim_.set_ii_reference_density(n0,p0); }
double DeviceSimulatorDouble::get_ii_reference_density_n() const { return (double)sim_.get_ii_reference_density_n(); }
double DeviceSimulatorDouble::get_ii_reference_density_p() const { return (double)sim_.get_ii_reference_density_p(); }
void DeviceSimulatorDouble::set_ii_driving(int driving) { sim_.set_ii_driving(driving); }
int DeviceSimulatorDouble::get_ii_driving() const { return sim_.get_ii_driving(); }
void DeviceSimulatorDouble::set_ii_field_floor(double floor) {
    sim_.set_ii_field_floor((real_t)floor);
}

double DeviceSimulatorDouble::get_ii_field_floor() const {
    return (double)sim_.get_ii_field_floor();
}

void DeviceSimulatorDouble::set_ii_params(double A_n, double B_n, double A_p, double B_p) {
    sim_.set_ii_params((real_t)A_n, (real_t)B_n, (real_t)A_p, (real_t)B_p);
}

void DeviceSimulatorDouble::set_auger_enabled(bool enable) {
    sim_.set_auger_enabled(enable);
}

void DeviceSimulatorDouble::set_auger_params(double Cn, double Cp) {
    sim_.set_auger_params((real_t)Cn, (real_t)Cp);
}

void DeviceSimulatorDouble::set_breakdown_enabled(bool enable) {
    sim_.set_breakdown_enabled(enable);
}

void DeviceSimulatorDouble::set_breakdown_params(const std::vector<signed char>& bd_mask,
                                                 const std::vector<double>& E_bd, double sigma_bd) {
    std::vector<char> mask_q(bd_mask.begin(), bd_mask.end());
    sim_.set_breakdown_params(mask_q, to_real_t(E_bd), (real_t)sigma_bd);
}

std::vector<signed char> DeviceSimulatorDouble::breakdown_state() {
    const std::vector<char>& s = sim_.breakdown_state();
    return std::vector<signed char>(s.begin(), s.end());
}

void DeviceSimulatorDouble::set_ferroelectric_enabled(bool enable) {
    sim_.set_ferroelectric_enabled(enable);
}

void DeviceSimulatorDouble::set_history_updates_enabled(bool enable) {
    sim_.set_history_updates_enabled(enable);
}

void DeviceSimulatorDouble::set_ferroelectric_params(const std::vector<signed char>& fe_mask, double alpha, double beta) {
    std::vector<char> fe_q(fe_mask.begin(), fe_mask.end());
    sim_.set_ferroelectric_params(fe_q, (real_t)alpha, (real_t)beta);
}

void DeviceSimulatorDouble::set_ferroelectric_model(int model) {
    sim_.set_ferroelectric_model(model);
}

void DeviceSimulatorDouble::set_ferroelectric_preisach(double ps, double ec, double escale) {
    sim_.set_ferroelectric_preisach((real_t)ps, (real_t)ec, (real_t)escale);
}

void DeviceSimulatorDouble::set_ferroelectric_builtin_field(double E_bi) {
    sim_.set_ferroelectric_builtin_field((real_t)E_bi);   // P2.1
}

void DeviceSimulatorDouble::set_ferroelectric_depol(double eps_fe) {
    sim_.set_ferroelectric_depol((real_t)eps_fe);   // comments2.docx P3
}

void DeviceSimulatorDouble::set_ferroelectric_nls(double tau0, double E0, double dt) {
    sim_.set_ferroelectric_nls((real_t)tau0, (real_t)E0, (real_t)dt);   // P3
}

void DeviceSimulatorDouble::set_ferroelectric_polar_axis(int axis) {
    sim_.set_ferroelectric_polar_axis(axis);
}

void DeviceSimulatorDouble::set_leakage(const std::vector<signed char>& mask,
                                        double C_pf, double B_pf, double phi_t,
                                        double C_fn, double B_fn, double phi_b,
                                        double E_floor, double sigma_cap) {
    sim_.set_leakage(std::vector<char>(mask.begin(), mask.end()),
                     (real_t)C_pf, (real_t)B_pf, (real_t)phi_t,
                     (real_t)C_fn, (real_t)B_fn, (real_t)phi_b,
                     (real_t)E_floor, (real_t)sigma_cap);   // P2.2
}

void DeviceSimulatorDouble::set_leakage_enabled(bool enable) {
    sim_.set_leakage_enabled(enable);   // P2.2
}

void DeviceSimulatorDouble::set_leakage_fn_polarity(double C_positive,
                                                     double B_positive,
                                                     double C_negative,
                                                     double B_negative) {
    sim_.set_leakage_fn_polarity(
        (real_t)C_positive, (real_t)B_positive,
        (real_t)C_negative, (real_t)B_negative);
}

void DeviceSimulatorDouble::set_interface_traps(const std::vector<signed char>& mask,
                                                double D_it, double E_t) {
    sim_.set_interface_traps(std::vector<char>(mask.begin(), mask.end()),
                             (real_t)D_it, (real_t)E_t);   // P6
}

void DeviceSimulatorDouble::set_oxide_traps(const std::vector<double>& Q_ot) {
    sim_.set_oxide_traps(std::vector<real_t>(Q_ot.begin(), Q_ot.end()));   // P6
}

void DeviceSimulatorDouble::begin_reliability_transaction() {
    result_checkpoints_.push_back({last_result_, solved_, transient_history_phi_,
        transient_history_n_, transient_history_p_, transient_history_converged_});
    try {
        sim_.begin_reliability_transaction();
    } catch (...) {
        result_checkpoints_.pop_back();
        throw;
    }
}
void DeviceSimulatorDouble::commit_reliability_transaction() {
    if (result_checkpoints_.empty())
        throw std::logic_error("no active reliability transaction");
    sim_.commit_reliability_transaction();
    result_checkpoints_.pop_back();
}
void DeviceSimulatorDouble::rollback_reliability_transaction() {
    if (result_checkpoints_.empty())
        throw std::logic_error("no active reliability transaction");
    sim_.rollback_reliability_transaction();
    auto state = std::move(result_checkpoints_.back());
    result_checkpoints_.pop_back();
    last_result_ = std::move(state.result);
    solved_ = state.solved;
    transient_history_phi_ = std::move(state.phi);
    transient_history_n_ = std::move(state.n);
    transient_history_p_ = std::move(state.p);
    transient_history_converged_ = std::move(state.converged);
}

void DeviceSimulatorDouble::set_initial_guess(const std::vector<double>& phi,
                                               const std::vector<double>& n,
                                               const std::vector<double>& p) {
    sim_.set_initial_guess(to_real_t(phi), to_real_t(n), to_real_t(p));
}

void DeviceSimulatorDouble::clear_initial_guess() {
    sim_.clear_initial_guess();
}

void DeviceSimulatorDouble::set_temperature(double T) {
    sim_.set_temperature((real_t)T);
}

void DeviceSimulatorDouble::set_statistics_type(int type) {
    sim_.set_statistics_type(type);
}

void DeviceSimulatorDouble::set_mobility_model(int type) {
    sim_.set_mobility_model(type);
}

void DeviceSimulatorDouble::set_transient_enabled(bool enable) {
    sim_.set_transient_enabled(enable);
}

void DeviceSimulatorDouble::set_transient_dt(double dt) {
    sim_.set_transient_dt((real_t)dt);
}

void DeviceSimulatorDouble::set_transient_t_final(double t_final) {
    sim_.set_transient_t_final((real_t)t_final);
}

void DeviceSimulatorDouble::set_ferroelectric_gamma(double gamma) {
    sim_.set_ferroelectric_gamma((real_t)gamma);
}

void DeviceSimulatorDouble::set_transient_voltage_waveforms(const std::vector<double>& times,
    const std::map<size_t, std::vector<double>>& offsets) {
    std::map<size_t, std::vector<real_t>> converted;
    for (const auto& [idx, values] : offsets) converted[idx] = to_real_t(values);
    sim_.set_transient_voltage_waveforms(to_real_t(times), converted);
}

void DeviceSimulatorDouble::clear_transient_voltage_waveforms() {
    sim_.clear_transient_voltage_waveforms();
}

std::vector<double> DeviceSimulatorDouble::solve_potential() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.phi);
}

std::vector<double> DeviceSimulatorDouble::solve_electrons() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.n);
}

std::vector<double> DeviceSimulatorDouble::solve_holes() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.p);
}

std::vector<double> DeviceSimulatorDouble::solve_Ex() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Ex);
}

void DeviceSimulatorDouble::reset_solved() {
    solved_ = false;
}

std::vector<double> DeviceSimulatorDouble::solve_Ey() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Ey);
}

std::vector<double> DeviceSimulatorDouble::solve_Ez() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Ez);
}

std::vector<double> DeviceSimulatorDouble::solve_temperature() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.temperature);
}

void DeviceSimulatorDouble::set_lattice_mobility_feedback(bool enable, size_t max_iter,
    double temperature_tol, double relaxation) {
    sim_.set_lattice_mobility_feedback(enable, max_iter, (real_t)temperature_tol, (real_t)relaxation);
    solved_ = false;
}

void DeviceSimulatorDouble::solve_lattice_step(const std::vector<double>& previous_temperature,
    const std::vector<double>& heat_capacity, double dt) {
    solved_ = false;
    last_result_ = sim_.solve_lattice_step(to_real_t(previous_temperature), to_real_t(heat_capacity), (real_t)dt);
    solved_ = true;
}

SteadyThermalLedgerDouble DeviceSimulatorDouble::solve_thermal_ledger() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    const auto& src = last_result_.thermal;
    SteadyThermalLedgerDouble dst;
    dst.available = src.available && last_result_.converged;
    dst.linear_solve_converged = src.linear_solve_converged;
    dst.current_projected = src.current_projected;
    dst.projected_Jx = (double)src.projected_Jx;
    dst.source_power = (double)src.source_power;
    dst.outward_heat = (double)src.outward_heat;
    dst.balance_residual = (double)src.balance_residual;
    dst.max_cell_residual = (double)src.max_cell_residual;
    dst.node_volumes=to_double(src.node_volumes); dst.power_density=to_double(src.power_density);
    dst.flux_x=to_double(src.flux_x); dst.flux_y=to_double(src.flux_y); dst.flux_z=to_double(src.flux_z);
    dst.bath_heat=to_double(src.bath_heat); dst.bath_nodes=src.bath_nodes;
    dst.bath_temperatures=to_double(src.bath_temperatures);
    dst.mobility_feedback=src.mobility_feedback;
    dst.feedback_converged=src.feedback_converged;
    dst.transient_storage=src.transient_storage;
    dst.feedback_iterations=src.feedback_iterations;
    dst.feedback_residual=src.feedback_residual;
    dst.feedback_tolerance=src.feedback_tolerance;
    dst.dt=src.dt;
    dst.storage_power=src.storage_power;
    dst.carrier_temperature=src.carrier_temperature;
    dst.carrier_VT=src.carrier_VT;
    dst.mobility_temperature=to_double(src.mobility_temperature);
    dst.mobility_n=to_double(src.mobility_n);
    dst.mobility_p=to_double(src.mobility_p);
    dst.previous_temperature=to_double(src.previous_temperature);
    dst.heat_capacity=to_double(src.heat_capacity);
    dst.node_storage_power=to_double(src.node_storage_power);
    return dst;
}

std::vector<double> DeviceSimulatorDouble::solve_Qn() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Qn);
}

std::vector<double> DeviceSimulatorDouble::solve_Qp() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Qp);
}

std::vector<double> DeviceSimulatorDouble::solve_Jn_x() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jn_x);
}
std::vector<double> DeviceSimulatorDouble::solve_Jn_y() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jn_y);
}
std::vector<double> DeviceSimulatorDouble::solve_Jn_z() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jn_z);
}
std::vector<double> DeviceSimulatorDouble::solve_Jp_x() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jp_x);
}
std::vector<double> DeviceSimulatorDouble::solve_Jp_y() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jp_y);
}
std::vector<double> DeviceSimulatorDouble::solve_Jp_z() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jp_z);
}
std::vector<double> DeviceSimulatorDouble::solve_Jleak_x() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jleak_x);
}
std::vector<double> DeviceSimulatorDouble::solve_Jleak_y() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jleak_y);
}
std::vector<double> DeviceSimulatorDouble::solve_Jleak_z() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.Jleak_z);
}
std::vector<double> DeviceSimulatorDouble::solve_G_btbt() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.G_btbt);
}
std::vector<double> DeviceSimulatorDouble::solve_G_ii() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(last_result_.G_ii);
}

std::vector<double> DeviceSimulatorDouble::fe_polarization() {
    // Ensure a solve has populated the persistent P (sim_.fe_polarization() is
    // the authoritative cross-solve state, mirrors the solve_* getter pattern).
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    return to_double(sim_.fe_polarization());
}

bool DeviceSimulatorDouble::solve_converged() const {
    return solved_ ? last_result_.converged : false;
}

size_t DeviceSimulatorDouble::solve_iterations() const {
    return solved_ ? last_result_.iterations : 0;
}

double DeviceSimulatorDouble::solve_poisson_residual() const {
    return solved_ ? static_cast<double>(last_result_.poisson_residual) : -1.0;
}

double DeviceSimulatorDouble::solve_quantum_residual() const {
    return solved_ ? static_cast<double>(last_result_.quantum_residual) : -1.0;
}

std::vector<double> DeviceSimulatorDouble::solve_steady_gummel_audit() const {
    return solved_ ? to_double(last_result_.steady_gummel_audit) : std::vector<double>{};
}

void DeviceSimulatorDouble::audit_steady_equations() {
    if (!solved_) { last_result_ = sim_.solve(); solved_ = true; }
    sim_.audit_steady_equations(last_result_, true);
}

std::string DeviceSimulatorDouble::solve_steady_gummel_audit_status() const {
    return solved_ ? last_result_.steady_gummel_audit_status : "not_solved";
}

std::vector<NonlinearSolveHistoryDouble> DeviceSimulatorDouble::solve_nonlinear_history() const {
    std::vector<NonlinearSolveHistoryDouble> result;
    if (!solved_) return result;
    for (const auto& stage : last_result_.nonlinear_history) {
        NonlinearSolveHistoryDouble entry;
        entry.solver = stage.solver;
        entry.converged = stage.converged;
        entry.final_poisson_residual = static_cast<double>(stage.final_poisson_residual);
        for (const auto& row : stage.samples) entry.samples.push_back(to_double(row));
        result.push_back(std::move(entry));
    }
    return result;
}

static std::vector<double> export_real_vector(const std::vector<real_t>& values) {
    std::vector<double> result(values.size());
    for (size_t i=0; i<values.size(); ++i) result[i]=static_cast<double>(values[i]);
    return result;
}

static std::vector<TransientAttemptHistoryDouble> export_transient_trace(
        const std::vector<TransientAttemptHistory>& groups) {
    std::vector<TransientAttemptHistoryDouble> result;
    for (const auto& group : groups) {
        TransientAttemptHistoryDouble entry;
        entry.start_time = static_cast<double>(group.start_time);
        entry.end_time = static_cast<double>(group.end_time);
        entry.step_dt = static_cast<double>(group.step_dt);
        entry.retry_index = group.retry_index;
        entry.error_control = group.error_control;
        entry.polarization_control = group.polarization_control;
        entry.electrical_control = group.electrical_control;
        entry.accepted = group.accepted;
        entry.error_estimate_available = group.error_estimate_available;
        entry.polarization_error_ratio = static_cast<double>(group.polarization_error_ratio);
        entry.electrical_error_ratio = static_cast<double>(group.electrical_error_ratio);
        entry.exported_polarization_error_ratio = static_cast<double>(group.exported_polarization_error_ratio);
        entry.exported_electrical_error_ratio = static_cast<double>(group.exported_electrical_error_ratio);
        entry.status = group.status;
        entry.stopping_reason = group.stopping_reason;
        for (const auto& trial : group.trials) {
            TransientTrialHistoryDouble item;
            item.role = trial.role;
            item.solver = trial.solver;
            item.start_time = static_cast<double>(trial.start_time);
            item.end_time = static_cast<double>(trial.end_time);
            item.step_dt = static_cast<double>(trial.step_dt);
            item.solver_called = trial.solver_called;
            item.converged = trial.converged;
            item.retained = trial.retained;
            item.exception = trial.exception;
            for (const auto& row : trial.samples) item.samples.push_back(export_real_vector(row));
            entry.trials.push_back(std::move(item));
        }
        result.push_back(std::move(entry));
    }
    return result;
}

std::vector<TransientAttemptHistoryDouble> DeviceSimulatorDouble::transient_attempt_history() const {
    return export_transient_trace(sim_.transient_attempt_history());
}
std::vector<TransientAttemptHistoryDouble> NlsTransientContinuationDouble::trace() const {
    return export_transient_trace(native_.trace());
}

size_t DeviceSimulatorDouble::nx() const { return sim_.nx(); }
size_t DeviceSimulatorDouble::ny() const { return sim_.ny(); }
size_t DeviceSimulatorDouble::nz() const { return sim_.nz(); }
size_t DeviceSimulatorDouble::npts() const { return sim_.npts(); }

void DeviceSimulatorDouble::solve_transient_once() {
    auto results = sim_.solve_transient();
    transient_history_converged_.clear();
    transient_history_phi_.resize(results.size());
    transient_history_n_.resize(results.size());
    transient_history_p_.resize(results.size());
    for (size_t i = 0; i < results.size(); ++i) {
        transient_history_phi_[i] = to_double(results[i].phi);
        transient_history_n_[i] = to_double(results[i].n);
        transient_history_p_[i] = to_double(results[i].p);
        transient_history_converged_.push_back(results[i].converged);
    }
}

static std::vector<TransientResultDouble> export_transient_results(
        const std::vector<SimulationResult>& history) {
    std::vector<TransientResultDouble> output;
    output.reserve(history.size());
    for (const auto& state : history) {
        TransientResultDouble item;
        item.phi = export_real_vector(state.phi); item.n = export_real_vector(state.n); item.p = export_real_vector(state.p);
        item.P = export_real_vector(state.P);
        item.Ex = export_real_vector(state.Ex); item.Ey = export_real_vector(state.Ey); item.Ez = export_real_vector(state.Ez);
        item.Jn_x = export_real_vector(state.Jn_x); item.Jn_y = export_real_vector(state.Jn_y); item.Jn_z = export_real_vector(state.Jn_z);
        item.Jp_x = export_real_vector(state.Jp_x); item.Jp_y = export_real_vector(state.Jp_y); item.Jp_z = export_real_vector(state.Jp_z);
        item.time = (double)state.time; item.attempted_time = (double)state.attempted_time;
        item.accepted_dt = (double)state.accepted_dt;
        item.converged = state.converged; item.initial_state = state.initial_state;
        item.phi_frozen = state.phi_frozen;
        item.majority_frozen = state.transient_majority_frozen; item.iterations = state.iterations;
        item.charge_ledger_available = state.transient_charge_ledger_available;
        item.mobile_charge = (double)state.mobile_charge;
        item.terminal_currents = export_real_vector(state.terminal_currents);
        item.electrostatic_flux_available = state.electrostatic_flux_available;
        item.displacement_current_available = state.displacement_current_available;
        item.electrode_charge_available = state.electrode_charge_available;
        item.total_terminal_current_available = state.total_terminal_current_available;
        item.D_x = export_real_vector(state.D_x); item.D_y = export_real_vector(state.D_y); item.D_z = export_real_vector(state.D_z);
        item.Jdisp_x = export_real_vector(state.Jdisp_x); item.Jdisp_y = export_real_vector(state.Jdisp_y); item.Jdisp_z = export_real_vector(state.Jdisp_z);
        item.Jdielectric_x = export_real_vector(state.Jdielectric_x); item.Jdielectric_y = export_real_vector(state.Jdielectric_y); item.Jdielectric_z = export_real_vector(state.Jdielectric_z);
        item.Jpolarization_x = export_real_vector(state.Jpolarization_x); item.Jpolarization_y = export_real_vector(state.Jpolarization_y); item.Jpolarization_z = export_real_vector(state.Jpolarization_z);
        item.electrode_faces = state.electrode_faces;
        item.electrode_voltages = export_real_vector(state.electrode_voltages);
        item.electrode_charges = export_real_vector(state.electrode_charges);
        item.electrode_conduction_currents = export_real_vector(state.electrode_conduction_currents);
        item.electrode_displacement_currents = export_real_vector(state.electrode_displacement_currents);
        item.electrode_total_currents = export_real_vector(state.electrode_total_currents);
        item.electrode_dielectric_currents = export_real_vector(state.electrode_dielectric_currents);
        item.electrode_polarization_currents = export_real_vector(state.electrode_polarization_currents);
        item.electrode_charge_increments = export_real_vector(state.electrode_charge_increments);
        item.dielectric_energy_available = state.dielectric_energy_available;
        item.dielectric_energy_increment_available = state.dielectric_energy_increment_available;
        item.dielectric_energy = (double)state.dielectric_energy;
        item.dielectric_energy_increment = (double)state.dielectric_energy_increment;
        item.lk_energy_available = state.lk_energy_available;
        item.lk_coupled = state.lk_coupled;
        item.lk_material_field = state.lk_material_field;
        item.lk_substepping = state.lk_substepping;
        item.lk_step_limit = (double)state.lk_step_limit;
        item.lk_error_control = state.lk_error_control;
        item.lk_error_estimate_available = state.lk_error_estimate_available;
        item.lk_error_ratio = (double)state.lk_error_ratio;
        item.lk_error_interval = (double)state.lk_error_interval;
        item.lk_error_end = (double)state.lk_error_end;
        item.lk_error_rtol = (double)state.lk_error_rtol;
        item.lk_error_atol = (double)state.lk_error_atol;
        item.lk_rejected_attempts = state.lk_rejected_attempts;
        item.lk_error_status = state.lk_error_status;
        item.lk_coarse_P = export_real_vector(state.lk_coarse_P);
        item.lk_error_delta_P = export_real_vector(state.lk_error_delta_P);
        item.lk_electrical_error_control = state.lk_electrical_error_control;
        item.electrical_error_control = state.electrical_error_control;
        item.nls_error_control = state.nls_error_control;
        item.lk_electrical_error_ratio = (double)state.lk_electrical_error_ratio;
        item.lk_phi_atol = (double)state.lk_phi_atol;
        item.lk_carrier_rtol = (double)state.lk_carrier_rtol;
        item.lk_carrier_atol = (double)state.lk_carrier_atol;
        item.lk_coarse_phi = export_real_vector(state.lk_coarse_phi);
        item.lk_coarse_n = export_real_vector(state.lk_coarse_n);
        item.lk_coarse_p = export_real_vector(state.lk_coarse_p);
        item.lk_delta_phi = export_real_vector(state.lk_delta_phi);
        item.lk_delta_n = export_real_vector(state.lk_delta_n);
        item.lk_delta_p = export_real_vector(state.lk_delta_p);
        item.lk_energy_increment_available = state.lk_energy_increment_available;
        item.lk_free_energy = (double)state.lk_free_energy;
        item.lk_free_energy_increment = (double)state.lk_free_energy_increment;
        item.lk_dissipation = (double)state.lk_dissipation;
        item.lk_field_work = (double)state.lk_field_work;
        item.lk_be_correction = (double)state.lk_be_correction;
        item.lk_node_volumes = export_real_vector(state.lk_node_volumes);
        item.lk_parameters = export_real_vector(state.lk_parameters);
        item.lk_drive_field = export_real_vector(state.lk_drive_field);
        item.lk_polarization_increment = export_real_vector(state.lk_polarization_increment);
        output.push_back(std::move(item));
    }
    return output;
}

std::vector<TransientResultDouble> DeviceSimulatorDouble::solve_transient_results() {
    return export_transient_results(sim_.solve_transient());
}
std::vector<TransientResultDouble> NlsTransientContinuationDouble::history() const {
    return export_transient_results(native_.history());
}

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_phi() {
    // The Python binding requests phi, n and p through three C++ getters.
    // Execute the physical time integration once and cache every field so a
    // single API call cannot silently advance the transient three times.
    solve_transient_once();
    return transient_history_phi_;
}

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_n() {
    if (transient_history_n_.empty()) solve_transient_once();
    return transient_history_n_;
}

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_p() {
    if (transient_history_p_.empty()) solve_transient_once();
    return transient_history_p_;
}

std::vector<bool> DeviceSimulatorDouble::solve_transient_converged() const {
    return transient_history_converged_;
}

void DeviceSimulatorDouble::set_z_positions(const std::vector<double>& z_pos) {
    sim_.set_grid_z(to_real_t(z_pos));
}

void DeviceSimulatorDouble::set_x_positions(const std::vector<double>& x_pos) {
    sim_.set_grid_x(to_real_t(x_pos));
}

void DeviceSimulatorDouble::set_y_positions(const std::vector<double>& y_pos) {
    sim_.set_grid_y(to_real_t(y_pos));
}

} // namespace tcad
