#include "device_simulator_double.h"

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

void DeviceSimulatorDouble::set_optical_generation(const std::vector<double>& G_opt) {
    sim_.set_optical_generation(to_real_t(G_opt));
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

void DeviceSimulatorDouble::set_btbt_params(double A, double B, int D) {
    sim_.set_btbt_params((real_t)A, (real_t)B, D);
}

void DeviceSimulatorDouble::set_btbt_use_nonlocal(bool enable) {
    sim_.set_btbt_use_nonlocal(enable);
}

void DeviceSimulatorDouble::set_ii_enabled(bool enable) {
    sim_.set_ii_enabled(enable);
}

void DeviceSimulatorDouble::set_ii_params(double A_n, double B_n, double A_p, double B_p) {
    sim_.set_ii_params((real_t)A_n, (real_t)B_n, (real_t)A_p, (real_t)B_p);
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

void DeviceSimulatorDouble::set_interface_traps(const std::vector<signed char>& mask,
                                                double D_it, double E_t) {
    sim_.set_interface_traps(std::vector<char>(mask.begin(), mask.end()),
                             (real_t)D_it, (real_t)E_t);   // P6
}

void DeviceSimulatorDouble::set_oxide_traps(const std::vector<double>& Q_ot) {
    sim_.set_oxide_traps(std::vector<real_t>(Q_ot.begin(), Q_ot.end()));   // P6
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

size_t DeviceSimulatorDouble::nx() const { return sim_.nx(); }
size_t DeviceSimulatorDouble::ny() const { return sim_.ny(); }
size_t DeviceSimulatorDouble::nz() const { return sim_.nz(); }
size_t DeviceSimulatorDouble::npts() const { return sim_.npts(); }

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_phi() {
    auto results = sim_.solve_transient();
    transient_history_converged_.clear();
    transient_history_phi_.resize(results.size());
    for (size_t i = 0; i < results.size(); ++i) {
        transient_history_phi_[i] = to_double(results[i].phi);
        transient_history_converged_.push_back(results[i].converged);
    }
    return transient_history_phi_;
}

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_n() {
    auto results = sim_.solve_transient();
    transient_history_n_.resize(results.size());
    for (size_t i = 0; i < results.size(); ++i) {
        transient_history_n_[i] = to_double(results[i].n);
    }
    return transient_history_n_;
}

std::vector<std::vector<double>> DeviceSimulatorDouble::solve_transient_p() {
    auto results = sim_.solve_transient();
    transient_history_p_.resize(results.size());
    for (size_t i = 0; i < results.size(); ++i) {
        transient_history_p_[i] = to_double(results[i].p);
    }
    return transient_history_p_;
}

std::vector<bool> DeviceSimulatorDouble::solve_transient_converged() const {
    return transient_history_converged_;
}

} // namespace tcad
