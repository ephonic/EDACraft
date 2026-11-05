#pragma once

#include "device_simulator.h"
#include <vector>

namespace tcad {

struct EquilibriumResultDouble {
    std::vector<double> phi, n, p;
    std::vector<double> residual_history, update_history, damping_history;
    bool converged = false;
    size_t iterations = 0;
    std::string status;
};

struct NonlinearSolveHistoryDouble {
    std::string solver;
    bool converged = false;
    double final_poisson_residual = -1.0;
    std::vector<std::vector<double>> samples;
};

struct TransientTrialHistoryDouble {
    std::string role;
    std::string solver = "newton";
    double start_time = 0.0, end_time = 0.0, step_dt = 0.0;
    bool solver_called = false, converged = false, retained = false, exception = false;
    std::vector<std::vector<double>> samples;
};

struct TransientAttemptHistoryDouble {
    double start_time = 0.0, end_time = 0.0, step_dt = 0.0;
    size_t retry_index = 0;
    bool error_control = false, accepted = false, error_estimate_available = false;
    bool polarization_control = false, electrical_control = false;
    double polarization_error_ratio = -1.0, electrical_error_ratio = -1.0;
    double exported_polarization_error_ratio = -1.0, exported_electrical_error_ratio = -1.0;
    std::string status, stopping_reason;
    std::vector<TransientTrialHistoryDouble> trials;
};

struct SteadyThermalLedgerDouble {
    bool available = false, linear_solve_converged = false, current_projected = false;
    double projected_Jx = 0.0, source_power = 0.0, outward_heat = 0.0;
    double balance_residual = 0.0, max_cell_residual = 0.0;
    std::vector<double> node_volumes, power_density, flux_x, flux_y, flux_z, bath_heat;
    std::vector<size_t> bath_nodes;
    std::vector<double> bath_temperatures;
    bool mobility_feedback = false, feedback_converged = false, transient_storage = false;
    size_t feedback_iterations = 0;
    double feedback_residual = 0.0, feedback_tolerance = 0.0, dt = 0.0, storage_power = 0.0;
    double carrier_temperature = 0.0, carrier_VT = 0.0;
    std::vector<double> mobility_temperature, mobility_n, mobility_p;
    std::vector<double> previous_temperature, heat_capacity, node_storage_power;
};

struct TransientResultDouble {
    std::vector<double> phi, n, p, Ex, Ey, Ez;
    std::vector<double> P;
    std::vector<double> Jn_x, Jn_y, Jn_z, Jp_x, Jp_y, Jp_z;
    double time = 0.0, attempted_time = 0.0, accepted_dt = 0.0;
    bool converged = false, initial_state = false, majority_frozen = false;
    bool phi_frozen = false;
    size_t iterations = 0;
    bool charge_ledger_available = false;
    double mobile_charge = 0.0;
    std::vector<double> terminal_currents;
    bool electrostatic_flux_available = false, displacement_current_available = false;
    bool electrode_charge_available = false, total_terminal_current_available = false;
    std::vector<double> D_x, D_y, D_z, Jdisp_x, Jdisp_y, Jdisp_z;
    std::vector<double> Jdielectric_x, Jdielectric_y, Jdielectric_z;
    std::vector<double> Jpolarization_x, Jpolarization_y, Jpolarization_z;
    std::vector<int> electrode_faces;
    std::vector<double> electrode_voltages, electrode_charges;
    std::vector<double> electrode_conduction_currents;
    std::vector<double> electrode_displacement_currents, electrode_total_currents;
    std::vector<double> electrode_dielectric_currents, electrode_polarization_currents;
    std::vector<double> electrode_charge_increments;
    bool dielectric_energy_available = false, dielectric_energy_increment_available = false;
    double dielectric_energy = 0.0, dielectric_energy_increment = 0.0;
    bool lk_energy_available = false, lk_energy_increment_available = false;
    bool lk_coupled = false;
    bool lk_material_field = false;
    bool lk_substepping = false;
    double lk_step_limit = 0.0;
    bool lk_error_control = false, lk_error_estimate_available = false;
    double lk_error_ratio = 0.0, lk_error_interval = 0.0, lk_error_end = 0.0;
    double lk_error_rtol = 0.0, lk_error_atol = 0.0;
    size_t lk_rejected_attempts = 0;
    std::string lk_error_status;
    std::vector<double> lk_coarse_P, lk_error_delta_P;
    bool lk_electrical_error_control = false;
    bool electrical_error_control = false;
    bool nls_error_control = false;
    double lk_electrical_error_ratio = 0.0;
    double lk_phi_atol = 0.0, lk_carrier_rtol = 0.0, lk_carrier_atol = 0.0;
    std::vector<double> lk_coarse_phi, lk_coarse_n, lk_coarse_p;
    std::vector<double> lk_delta_phi, lk_delta_n, lk_delta_p;
    double lk_free_energy = 0.0, lk_free_energy_increment = 0.0;
    double lk_dissipation = 0.0, lk_field_work = 0.0, lk_be_correction = 0.0;
    std::vector<double> lk_node_volumes, lk_parameters;
    std::vector<double> lk_drive_field, lk_polarization_increment;
};

// Python-friendly wrapper that accepts/returns double vectors.
// All internal computation remains 128-bit quad precision.
// Owns the native precision continuation; exported vectors are independent copies.
// The originating DeviceSimulatorDouble must outlive this object.
class NlsTransientContinuationDouble {
public:
    std::vector<TransientResultDouble> history() const;
    std::vector<TransientAttemptHistoryDouble> trace() const;
    int status() const { return static_cast<int>(native_.status()); }
    size_t allocation_failures() const { return native_.allocation_failures(); }
    size_t solver_failures() const { return native_.solver_failures(); }
    size_t retries() const { return native_.retries(); }
    double suggested_dt() const { return static_cast<double>(native_.suggested_dt()); }
    size_t accuracy_rejections() const { return native_.accuracy_rejections(); }
private:
    friend class DeviceSimulatorDouble;
    NlsTransientContinuation native_;
};

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
    void set_charge_volume_fraction(const std::vector<double>& fraction);
    void set_optical_generation(const std::vector<double>& G_opt);
    void set_btbt_weight(const std::vector<double>& weight);
    void set_recombination(const std::vector<double>& tau_n, const std::vector<double>& tau_p);
    void set_thermal_voltage(double VT);
    void set_effective_dos(const std::vector<double>& Nc, const std::vector<double>& Nv);
    void set_bandgap(const std::vector<double>& Eg);

    void set_dirichlet_potential(const std::map<size_t, double>& bc);
    void set_electron_bc(const std::map<size_t, double>& bc);
    void set_hole_bc(const std::map<size_t, double>& bc);

    void set_quantum_enabled(bool enable);
    void set_density_gradient_coefficients(double bn, double bp);
    void set_density_gradient_silicon_multivalley(bool enable,
                                                  double longitudinal_mass,
                                                  double transverse_mass,
                                                  size_t subbands);
    void set_density_gradient_interface_distance_factor(double factor);
    void set_density_gradient_potential_form(bool enable);
    void set_density_gradient_step_boundary(
        bool enable, double electron_barrier_eV, double hole_barrier_eV,
        double electron_barrier_mass, double hole_barrier_mass,
        double electron_gamma, double hole_gamma,
        double electron_theta, double hole_theta);
    void set_gummel_max_iter(size_t max_iter);
    void set_nonlinear_history_enabled(bool enable) { sim_.set_nonlinear_history_enabled(enable); }
    void set_tolerance(double tol);
    void set_poisson_solver_type(int type);
    void set_continuity_solver_type(int type);
    void set_use_newton(bool enable);
    void set_newton_primary(bool enable);
    EquilibriumResultDouble solve_equilibrium(size_t max_iter = 100,
        double tolerance = 1e-10, const std::vector<char>& carrier_mask = {});
    void set_ohmic_contacts(const std::set<size_t>& nodes,
                            const std::map<size_t, double>& EFn,
                            const std::map<size_t, double>& EFp,
                            double ni);
    void clear_ohmic_contacts();
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
    void set_newton_log_density_update(const std::string& mode);
    std::string get_newton_log_density_update() const;
    void set_newton_jacobian_reuse_threshold(double threshold);

    void set_thermal_coupling_enabled(bool enable);
    void set_lattice_mobility_feedback(bool enable, size_t max_iter, double temperature_tol, double relaxation);
    void solve_lattice_step(const std::vector<double>& previous_temperature,
        const std::vector<double>& heat_capacity, double dt);
    void set_thermal_conductivity(const std::vector<double>& kappa);
    void set_ambient_temperature(double T_ambient);
    void set_thermal_dirichlet(const std::map<size_t, double>& bc);
    void set_btbt_enabled(bool enable);
    void set_btbt_params(double A, double B, double D);
    void set_btbt_field_mode(int mode);
    void set_btbt_field_options(int mode, double cap);
    void set_btbt_field_shape(int mode, double cap, double alpha, double ref);
    void set_btbt_continuity_scale(double scale);
    void set_btbt_use_nonlocal(bool enable);
    void set_btbt_nonlocal_params(double tunnel_path_frac, size_t wkb_npts);
    void set_btbt_nonlocal_mass(double mass_ratio);
    void set_high_field_saturation(bool enable, double vsat_n, double vsat_p,
                                   double beta_n, double beta_p, int driving);
    void set_hfs_quasi_fermi_at_contacts(bool enabled);
    bool get_hfs_quasi_fermi_at_contacts() const;
    void set_high_field_reference_density(double n0, double p0);
    double get_high_field_reference_density_n() const;
    double get_high_field_reference_density_p() const;
    void set_hfs_low_field_cutoff(double cutoff);
    double get_hfs_low_field_cutoff() const;
    // Avalanche impact ionization (Chynoweth).  alpha(E)=A*exp(-B/|E|) [1/m].
    void set_ii_enabled(bool enable);
    void set_ii_reference_density(double n0, double p0);
    double get_ii_reference_density_n() const;
    double get_ii_reference_density_p() const;
    void set_ii_driving(int driving);
    int get_ii_driving() const;
    void set_ii_field_floor(double floor);
    double get_ii_field_floor() const;
    void set_ii_params(double A_n, double B_n, double A_p, double B_p);
    // Auger recombination: R = (Cn*n + Cp*p)*(n*p - ni²)
    void set_auger_enabled(bool enable);
    void set_auger_params(double Cn, double Cp);
    // Dielectric breakdown (M7b).
    void set_breakdown_enabled(bool enable);
    void set_breakdown_params(const std::vector<signed char>& bd_mask,
                              const std::vector<double>& E_bd, double sigma_bd);
    std::vector<signed char> breakdown_state();
    void set_ferroelectric_enabled(bool enable);
    void set_history_updates_enabled(bool enable);
    void begin_reliability_transaction();
    void commit_reliability_transaction();
    void rollback_reliability_transaction();
    void set_ferroelectric_params(const std::vector<signed char>& fe_mask, double alpha, double beta);
    // Ferroelectric model + Preisach (M7c).
    void set_ferroelectric_model(int model);
    void set_ferroelectric_preisach(double ps, double ec, double escale);
    void set_ferroelectric_builtin_field(double E_bi);   // P2.1
    void set_ferroelectric_depol(double eps_fe);   // comments2.docx P3
    void set_ferroelectric_nls(double tau0, double E0, double dt);  // P3
    void set_ferroelectric_polar_axis(int axis);  // 0=x, 1=y, 2=z
    void set_leakage(const std::vector<signed char>& mask,
                     double C_pf, double B_pf, double phi_t,
                     double C_fn, double B_fn, double phi_b,
                     double E_floor, double sigma_cap);   // P2.2
    void set_leakage_fn_polarity(double C_positive, double B_positive,
                                 double C_negative, double B_negative);
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
    void set_transient_lk_coupled(bool enable) { sim_.set_transient_lk_coupled(enable); }
    void set_transient_lk_material_field(bool enable) { sim_.set_transient_lk_material_field(enable); }
    void set_transient_lk_zero_d_faces(const std::string& faces) { sim_.set_transient_lk_zero_d_faces(faces); }
    void set_transient_lk_substepping(bool enable, double safety) {
        sim_.set_transient_lk_substepping(enable, (real_t)safety);
    }
    void set_transient_lk_error_control(bool enable, double rtol, double atol,
        double min_dt, size_t max_reject) {
        sim_.set_transient_lk_error_control(enable, (real_t)rtol, (real_t)atol,
            (real_t)min_dt, max_reject);
    }
    void set_transient_lk_electrical_error_control(bool enable, double phi_atol,
        double carrier_rtol, double carrier_atol) {
        sim_.set_transient_lk_electrical_error_control(enable, (real_t)phi_atol,
            (real_t)carrier_rtol, (real_t)carrier_atol);
    }
    void set_transient_electrical_error_control(bool enable, double phi_atol,
        double carrier_rtol, double carrier_atol, double min_dt, size_t max_reject) {
        sim_.set_transient_electrical_error_control(enable, (real_t)phi_atol,
            (real_t)carrier_rtol, (real_t)carrier_atol, (real_t)min_dt, max_reject);
    }
    void set_transient_nls_error_control(bool enable, double rtol, double atol,
        double phi_atol, double carrier_rtol, double carrier_atol,
        double min_dt, size_t max_reject) {
        sim_.set_transient_nls_error_control(enable, (real_t)rtol, (real_t)atol,
            (real_t)phi_atol, (real_t)carrier_rtol, (real_t)carrier_atol, (real_t)min_dt, max_reject);
    }
    void set_transient_nls_event_control(bool enable, double half_width) {
        sim_.set_transient_nls_event_control(enable, (real_t)half_width);
    }
    void set_transient_voltage_waveforms(const std::vector<double>& times,
        const std::map<size_t, std::vector<double>>& offsets);
    void clear_transient_voltage_waveforms();
    void set_ferroelectric_gamma(double gamma);
    void set_ferroelectric_history(const std::vector<double>& polarization) {
        sim_.set_ferroelectric_history(to_real_t(polarization)); solved_ = false;
    }
    std::vector<double> get_ferroelectric_history() const {
        return to_double(sim_.fe_polarization());
    }
    void set_ferroelectric_ensemble_history(const std::vector<double>& p, const std::vector<double>& play) {
        sim_.set_ferroelectric_ensemble_history(to_real_t(p),to_real_t(play)); solved_=false;
    }
    std::vector<double> get_ferroelectric_play_history() const { return to_double(sim_.ferroelectric_play_history()); }
    std::vector<double> get_ferroelectric_ensemble_parameters() const { return to_double(sim_.ferroelectric_ensemble_parameters()); }
    std::vector<int> get_ferroelectric_mask() const {
        const auto& mask = sim_.ferroelectric_mask();
        return std::vector<int>(mask.begin(), mask.end());
    }
    std::vector<double> get_ferroelectric_lk_parameters() const {
        return to_double(sim_.ferroelectric_lk_parameters());
    }
    std::vector<double> get_permittivity() const { return to_double(sim_.permittivity()); }
    void set_transient_start_time(double time) { sim_.set_transient_start_time((real_t)time); }

    // Returns flattened arrays of size nx*ny*nz
    std::vector<double> solve_potential();
    std::vector<double> solve_electrons();
    std::vector<double> solve_holes();
    std::vector<double> solve_Ex();
    std::vector<double> solve_Ey();
    std::vector<double> solve_Ez();
    std::vector<double> solve_temperature();
    SteadyThermalLedgerDouble solve_thermal_ledger();
    std::vector<double> solve_Qn();
    std::vector<double> solve_Qp();
    // Edge-centered SG current densities [A/m^2], full-precision (Audit §20).
    std::vector<double> solve_Jn_x();
    std::vector<double> solve_Jn_y();
    std::vector<double> solve_Jn_z();
    std::vector<double> solve_Jp_x();
    std::vector<double> solve_Jp_y();
    std::vector<double> solve_Jp_z();
    std::vector<double> solve_Jleak_x();
    std::vector<double> solve_Jleak_y();
    std::vector<double> solve_Jleak_z();
    std::vector<double> solve_G_btbt();
    std::vector<double> solve_G_ii();
    bool solve_converged() const;
    size_t solve_iterations() const;
    double solve_poisson_residual() const;
    double solve_quantum_residual() const;
    std::vector<double> solve_steady_gummel_audit() const;
    void audit_steady_equations();
    std::string solve_steady_gummel_audit_status() const;
    bool solve_nonlinear_history_enabled() const { return solved_ && last_result_.nonlinear_history_enabled; }
    std::vector<NonlinearSolveHistoryDouble> solve_nonlinear_history() const;
    std::vector<TransientAttemptHistoryDouble> transient_attempt_history() const;

    // Transient solve: returns flat history [step][field...]
    // Each step is a flattened array of size nx*ny*nz
    std::vector<std::vector<double>> solve_transient_phi();
    std::vector<std::vector<double>> solve_transient_n();
    std::vector<std::vector<double>> solve_transient_p();
    std::vector<bool> solve_transient_converged() const;
    std::vector<TransientResultDouble> solve_transient_results();
    void advance_transient_nls(NlsTransientContinuationDouble& continuation, size_t max_retries=1) {
        sim_.advance_transient_nls(continuation.native_, max_retries);
    }



    void configure_three_temperature(const std::vector<std::string>& c,const std::vector<std::string>& f,
        const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& a,double time) {
        sim_.configure_three_temperature(c,f,vn,vp,a,time);
    }
    void configure_energy_coordinate(const std::vector<std::string>& c,const std::vector<std::string>& f,
        const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& a,
        const std::vector<std::string>& laws,const std::vector<std::string>& excess,double time) {
        sim_.configure_energy_coordinate(c,f,vn,vp,a,laws,excess,time);
    }
    EnergyCoordinateSnapshot prepare_energy_coordinate(double dt,double q,double p,double e,int budget) {
        return sim_.prepare_energy_coordinate(dt,q,p,e,budget);
    }
    void commit_energy_coordinate(size_t token) {sim_.commit_energy_coordinate(token);}
    void discard_energy_coordinate(size_t token) {sim_.discard_energy_coordinate(token);}
    EnergyCoordinateSnapshot energy_coordinate_state() const {return sim_.energy_coordinate_state();}
    bool energy_coordinate_enabled() const {return sim_.energy_coordinate_enabled();}
    ThreeTemperatureDispatchResult prepare_three_temperature(double dt,double q,double p,double e,int budget) {
        return sim_.prepare_three_temperature(dt,q,p,e,budget);
    }
    size_t three_temperature_token() const {return sim_.three_temperature_token();}
    void discard_three_temperature(size_t token) {sim_.discard_three_temperature(token);}
    void commit_three_temperature(size_t token) {last_result_=sim_.commit_three_temperature(token);solved_=true;}
    ThreeTemperatureDispatchResult three_temperature_state() const {return sim_.three_temperature_state();}
    double three_temperature_time() const {return sim_.three_temperature_time();}
    std::vector<std::vector<double>> structured_three_temperature_seed() const {return sim_.structured_three_temperature_seed();}
    bool three_temperature_enabled() const {return sim_.three_temperature_enabled();}
    std::vector<std::vector<double>> three_temperature_result() const {
        if(!solved_ || !last_result_.explicit_cell_three_temperature)
            throw std::logic_error("no committed three-temperature result");
        return {to_double(last_result_.phi),to_double(last_result_.n),to_double(last_result_.p),
            to_double(last_result_.electron_temperature),to_double(last_result_.hole_temperature),
            to_double(last_result_.temperature)};
    }

    void configure_isolated_relaxation(const std::vector<std::string>& initial,
        const std::vector<std::string>& parameters,const std::vector<double>& vn,
        const std::vector<double>& vp,double time) {
        sim_.configure_isolated_relaxation(initial,parameters,vn,vp,time);
    }
    void configure_lattice_excess(const std::vector<std::string>& initial,
        const std::vector<std::string>& parameters,const std::vector<std::string>& faces,
        const std::vector<double>& vn,const std::vector<double>& vp,double time,
        const std::vector<std::string>& baths={},const std::vector<std::string>& varshni={}) {
        sim_.configure_lattice_excess(initial,parameters,faces,vn,vp,time,baths,varshni);
    }
    std::vector<std::string> prepare_isolated_relaxation(double dt,double q,double p,double e,int budget,
            const std::vector<std::string>& source={}) {
        return sim_.prepare_isolated_relaxation(dt,q,p,e,budget,source);
    }
    size_t isolated_relaxation_token() const {return sim_.isolated_relaxation_token();}
    void discard_isolated_relaxation(size_t token) {sim_.discard_isolated_relaxation(token);}
    void commit_isolated_relaxation(size_t token) {sim_.commit_isolated_relaxation(token);}
    IsolatedRelaxationSnapshot isolated_relaxation_state() const {return sim_.isolated_relaxation_state();}
    bool isolated_relaxation_enabled() const {return sim_.isolated_relaxation_enabled();}

    // Reset the solved flag so the next query triggers a new solve
    void reset_solved();

    size_t nx() const;
    size_t ny() const;
    size_t nz() const;
    size_t npts() const;

    // Set non-uniform z-node positions for local mesh refinement.
    // When set, the Poisson/continuity/current assembly uses per-edge
    // spacing derived from these positions instead of the uniform dz.
    void set_z_positions(const std::vector<double>& z_pos);
    void set_x_positions(const std::vector<double>& x_pos);
    void set_y_positions(const std::vector<double>& y_pos);

private:
    DeviceSimulator sim_;
    SimulationResult last_result_;
    bool solved_ = false;

    std::vector<std::vector<double>> transient_history_phi_;
    std::vector<std::vector<double>> transient_history_n_;
    std::vector<std::vector<double>> transient_history_p_;
    std::vector<bool> transient_history_converged_;

    // Match the native transaction stack, including observable query caches.
    struct ResultCheckpoint {
        SimulationResult result;
        bool solved;
        std::vector<std::vector<double>> phi, n, p;
        std::vector<bool> converged;
    };
    std::vector<ResultCheckpoint> result_checkpoints_;

    void solve_transient_once();
    std::vector<real_t> to_real_t(const std::vector<double>& v) const;
    std::vector<double> to_double(const std::vector<real_t>& v) const;
};

} // namespace tcad
