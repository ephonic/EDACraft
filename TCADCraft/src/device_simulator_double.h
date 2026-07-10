#pragma once

#include "device_simulator.h"
#include <vector>

namespace tcad {

// Python-friendly wrapper that accepts/returns double vectors.
// All internal computation remains 128-bit quad precision.
class DeviceSimulatorDouble {
public:
    DeviceSimulatorDouble(size_t nx, size_t ny, size_t nz,
                          double dx, double dy, double dz);

    void set_permittivity(const std::vector<double>& eps);
    void set_edge_permittivity(const std::vector<double>& x_plus,
                               const std::vector<double>& x_minus,
                               const std::vector<double>& y_plus,
                               const std::vector<double>& y_minus,
                               const std::vector<double>& z_plus,
                               const std::vector<double>& z_minus);
    void set_mobility(const std::vector<double>& mu_n, const std::vector<double>& mu_p);
    void set_doping(const std::vector<double>& Nd_minus_Na);
    void set_optical_generation(const std::vector<double>& G_opt);
    void set_recombination(const std::vector<double>& tau_n, const std::vector<double>& tau_p);
    void set_thermal_voltage(double VT);
    void set_effective_dos(const std::vector<double>& Nc, const std::vector<double>& Nv);
    void set_bandgap(const std::vector<double>& Eg);

    void set_dirichlet_potential(const std::map<size_t, double>& bc);
    void set_electron_bc(const std::map<size_t, double>& bc);
    void set_hole_bc(const std::map<size_t, double>& bc);

    void set_quantum_enabled(bool enable);
    void set_gummel_max_iter(size_t max_iter);
    void set_tolerance(double tol);
    void set_poisson_solver_type(int type);
    void set_continuity_solver_type(int type);
    void set_use_newton(bool enable);
    // C档: Newton freeze flags (isolated-continuity MMS).
    void set_newton_freeze_phi(bool enable);
    void set_newton_freeze_n(bool enable);
    void set_newton_freeze_p(bool enable);

    void set_newton_damping(double damping);
    void set_newton_min_damping(double min_damping);
    void set_newton_use_line_search(bool enable);
    void set_newton_line_search_max(size_t max);
    void set_newton_use_log_damping(bool enable);
    void set_newton_use_log_space(bool enable);
    void set_newton_jacobian_reuse_threshold(double threshold);

    void set_thermal_coupling_enabled(bool enable);
    void set_thermal_conductivity(const std::vector<double>& kappa);
    void set_ambient_temperature(double T_ambient);
    void set_thermal_dirichlet(const std::map<size_t, double>& bc);
    void set_btbt_enabled(bool enable);
    void set_btbt_params(double A, double B, int D);
    void set_btbt_use_nonlocal(bool enable);
    // Avalanche impact ionization (Chynoweth).  alpha(E)=A*exp(-B/|E|) [1/m].
    void set_ii_enabled(bool enable);
    void set_ii_params(double A_n, double B_n, double A_p, double B_p);
    // Dielectric breakdown (M7b).
    void set_breakdown_enabled(bool enable);
    void set_breakdown_params(const std::vector<signed char>& bd_mask,
                              const std::vector<double>& E_bd, double sigma_bd);
    std::vector<signed char> breakdown_state();
    void set_ferroelectric_enabled(bool enable);
    void set_ferroelectric_params(const std::vector<signed char>& fe_mask, double alpha, double beta);
    // Ferroelectric model + Preisach (M7c).
    void set_ferroelectric_model(int model);
    void set_ferroelectric_preisach(double ps, double ec, double escale);
    void set_ferroelectric_builtin_field(double E_bi);   // P2.1
    void set_ferroelectric_nls(double tau0, double E0, double dt);  // P3
    void set_leakage(const std::vector<signed char>& mask,
                     double C_pf, double B_pf, double phi_t,
                     double C_fn, double B_fn, double phi_b,
                     double E_floor, double sigma_cap);   // P2.2
    void set_leakage_enabled(bool enable);                // P2.2
    void set_interface_traps(const std::vector<signed char>& mask, double D_it, double E_t);  // P6
    void set_oxide_traps(const std::vector<double>& Q_ot);  // P6
    // Persistent signed polarization field (double-converted from internal quad).
    std::vector<double> fe_polarization();

    void set_initial_guess(const std::vector<double>& phi,
                           const std::vector<double>& n,
                           const std::vector<double>& p);
    void clear_initial_guess();

    // Cryo-CMOS
    void set_temperature(double T);
    void set_statistics_type(int type);
    void set_mobility_model(int type);

    // Transient
    void set_transient_enabled(bool enable);
    void set_transient_dt(double dt);
    void set_transient_t_final(double t_final);
    void set_ferroelectric_gamma(double gamma);

    // Returns flattened arrays of size nx*ny*nz
    std::vector<double> solve_potential();
    std::vector<double> solve_electrons();
    std::vector<double> solve_holes();
    std::vector<double> solve_Ex();
    std::vector<double> solve_Ey();
    std::vector<double> solve_Ez();
    std::vector<double> solve_temperature();
    // Edge-centered SG current densities [A/m^2], full-precision (Audit §20).
    std::vector<double> solve_Jn_x();
    std::vector<double> solve_Jn_y();
    std::vector<double> solve_Jn_z();
    std::vector<double> solve_Jp_x();
    std::vector<double> solve_Jp_y();
    std::vector<double> solve_Jp_z();
    bool solve_converged() const;
    size_t solve_iterations() const;

    // Transient solve: returns flat history [step][field...]
    // Each step is a flattened array of size nx*ny*nz
    std::vector<std::vector<double>> solve_transient_phi();
    std::vector<std::vector<double>> solve_transient_n();
    std::vector<std::vector<double>> solve_transient_p();
    std::vector<bool> solve_transient_converged() const;

    // Reset the solved flag so the next query triggers a new solve
    void reset_solved();

    size_t nx() const;
    size_t ny() const;
    size_t nz() const;
    size_t npts() const;

private:
    DeviceSimulator sim_;
    SimulationResult last_result_;
    bool solved_ = false;

    std::vector<std::vector<double>> transient_history_phi_;
    std::vector<std::vector<double>> transient_history_n_;
    std::vector<std::vector<double>> transient_history_p_;
    std::vector<bool> transient_history_converged_;

    std::vector<real_t> to_real_t(const std::vector<double>& v) const;
    std::vector<double> to_double(const std::vector<real_t>& v) const;
};

} // namespace tcad
