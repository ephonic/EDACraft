#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "gummel_solver.h"
#include "newton_solver.h"
#include "density_gradient.h"
#include "mobility_model.h"
#include "statistics.h"
#include "three_temperature_device.h"
#include "energy_coordinate_device.h"
#include "isolated_relaxation_device.h"
#include <vector>
#include <map>
#include <string>

namespace tcad {

struct EquilibriumResult {
    std::vector<real_t> phi, n, p;
    std::vector<real_t> residual_history, update_history, damping_history;
    bool converged = false;
    size_t iterations = 0;
    std::string status;
};

// Integrated lattice-power ledger. Optional BE storage is lattice-only;
// carrier heat transport, traps, quantum and FE domain dynamics are excluded.
struct SteadyThermalLedger {
    bool available = false, linear_solve_converged = false, current_projected = false;
    real_t projected_Jx = TCAD_CONST(0.0);
    real_t source_power = TCAD_CONST(0.0), outward_heat = TCAD_CONST(0.0);
    real_t balance_residual = TCAD_CONST(0.0), max_cell_residual = TCAD_CONST(0.0);
    std::vector<real_t> node_volumes, power_density, flux_x, flux_y, flux_z;
    std::vector<real_t> bath_heat;
    std::vector<size_t> bath_nodes;
    std::vector<real_t> bath_temperatures;
    bool mobility_feedback = false, feedback_converged = false, transient_storage = false;
    size_t feedback_iterations = 0;
    real_t feedback_residual = TCAD_CONST(0.0), feedback_tolerance = TCAD_CONST(0.0);
    real_t dt = TCAD_CONST(0.0), storage_power = TCAD_CONST(0.0);
    real_t carrier_temperature = TCAD_CONST(0.0), carrier_VT = TCAD_CONST(0.0);
    std::vector<real_t> mobility_temperature, mobility_n, mobility_p;
    std::vector<real_t> previous_temperature, heat_capacity, node_storage_power;
};

// High-level device simulator interface consumed by Python/Cython
struct SimulationResult {
    std::vector<real_t> phi;    // Electrostatic potential [V]
    std::vector<real_t> n;      // Electron concentration [m^-3]
    std::vector<real_t> p;      // Hole concentration [m^-3]
    std::vector<real_t> Ex, Ey, Ez; // Electric field [V/m]
    std::vector<real_t> temperature; // Lattice temperature [K]
    std::vector<real_t> electron_temperature, hole_temperature;
    bool explicit_cell_three_temperature = false;
    SteadyThermalLedger thermal;
    // Final density-gradient quantum potentials [V]. Always length npts;
    // identically zero for a classical solve.
    std::vector<real_t> Qn, Qp;
    // Ferroelectric polarization snapshot [Px, Py, Pz] interleaved per node.
    // Empty for a classical run; populated by transient snapshots when FE is
    // enabled so the time-dependent state is auditable at every accepted step.
    std::vector<real_t> P;
    // Edge-centered SG current densities [A/m^2], computed in __float128 at
    // full solver precision (post-convergence) and downcast to real_t.  These
    // avoid the catastrophic cancellation that plagues Python re-derivation
    // from double phi/n/p when carrier densities are large (e.g. p~1e24 at
    // Na=1e18 cm^-3).  Length = npts per axis-direction array; entry idx is the
    // +axis edge leaving node idx (x_plus[idx] = edge idx->idx+1, etc.).
    // Zero entries indicate domain-boundary or insulator edges.  (Audit §20.)
    std::vector<real_t> Jn_x, Jn_y, Jn_z;  // electron current density
    std::vector<real_t> Jp_x, Jp_y, Jp_z;  // hole current density
    // Edge-centered dielectric leakage current density [A/m^2].  PF is
    // represented as a field-dependent conductivity and FN as a tunnelling
    // current; both are projected onto each edge.  These currents are kept
    // separate from mobile-carrier Jn/Jp so gate leakage can be audited.
    std::vector<real_t> Jleak_x, Jleak_y, Jleak_z;
    // Band-to-band pair generation rate [m^-3 s^-1] evaluated on the final
    // potential with the exact local-Kane/non-local-WKB model used by the
    // continuity equations.  Always length npts (zeros when BTBT is disabled).
    std::vector<real_t> G_btbt;
    // Impact-ionization pair generation [m^-3 s^-1], evaluated at the final
    // state with the same edge Chynoweth model used by the carrier equations.
    std::vector<real_t> G_ii;
    bool converged = false;
    size_t iterations = 0;
    bool nonlinear_history_enabled = false;
    std::vector<NonlinearSolveHistory> nonlinear_history;
    // Final physical Poisson scaled Linf residual (-1 = not computed), and
    // whether the potential was frozen by the limit-cycle guard.
    real_t poisson_residual = static_cast<real_t>(-1.0);
    real_t quantum_residual = static_cast<real_t>(-1.0);
    bool phi_frozen = false;
    // Final returned-state reassembly (Gummel by default; supported classical
    // Newton states may request the same SG row audit explicitly).
    // [Poisson scaled Linf, electron/hole row backward error, equation gate,
    // requested update tolerance, native gate verdict]. Empty when unavailable.
    std::vector<real_t> steady_gummel_audit;
    std::string steady_gummel_audit_status = "unsupported_solver_formulation";
    // Transient timeline: initial state at t=0; rejected attempts retain the
    // last accepted time and expose their proposed endpoint separately.
    real_t time = TCAD_CONST(0.0);
    real_t attempted_time = TCAD_CONST(0.0);
    real_t accepted_dt = TCAD_CONST(0.0);
    bool initial_state = false;
    bool transient_majority_frozen = false;
    bool transient_charge_ledger_available = false;
    real_t mobile_charge = TCAD_CONST(0.0);
    std::vector<real_t> terminal_currents;
    // FV electric displacement [C/m^2] and accepted-interval BE derivative
    // [A/m^2]. Same +axis edge layout as Jn/Jp. No derivative at t=0 or on
    // rejected steps. Electrode currents are positive into free-node volume.
    bool electrostatic_flux_available = false;
    bool displacement_current_available = false;
    bool electrode_charge_available = false;
    bool total_terminal_current_available = false;
    std::vector<real_t> D_x, D_y, D_z, Jdisp_x, Jdisp_y, Jdisp_z;
    std::vector<real_t> Jdielectric_x, Jdielectric_y, Jdielectric_z;
    std::vector<real_t> Jpolarization_x, Jpolarization_y, Jpolarization_z;
    std::vector<int> electrode_faces; // x_min,x_max,y_min,y_max,z_min,z_max = 0..5
    std::vector<real_t> electrode_voltages, electrode_charges;
    std::vector<real_t> electrode_conduction_currents;
    std::vector<real_t> electrode_displacement_currents, electrode_total_currents;
    std::vector<real_t> electrode_dielectric_currents, electrode_polarization_currents;
    std::vector<real_t> electrode_charge_increments;
    // Graph/FV field energy over edges touching free nodes. Available only
    // for a charge-free linear lossless dielectric with the electrode scope
    // above. FE/transport/fixed-volume charge need additional energy terms.
    bool dielectric_energy_available = false;
    bool dielectric_energy_increment_available = false;
    real_t dielectric_energy = TCAD_CONST(0.0);
    real_t dielectric_energy_increment = TCAD_CONST(0.0);
    // Local LK kinetic identity under geometric nodal quadrature. This is
    // not the device/electrode energy balance: the electrical solve is split.
    bool lk_energy_available = false, lk_energy_increment_available = false;
    bool lk_coupled = false;
    bool lk_material_field = false;
    bool lk_substepping = false;
    real_t lk_step_limit = TCAD_CONST(0.0);
    bool lk_error_control = false, lk_error_estimate_available = false;
    real_t lk_error_ratio = TCAD_CONST(0.0), lk_error_interval = TCAD_CONST(0.0), lk_error_end = TCAD_CONST(0.0);
    real_t lk_error_rtol = TCAD_CONST(0.0), lk_error_atol = TCAD_CONST(0.0);
    size_t lk_rejected_attempts = 0;
    std::string lk_error_status;
    std::vector<real_t> lk_coarse_P, lk_error_delta_P;
    bool lk_electrical_error_control = false;
    // Both controllers share the step-doubling diagnostic storage below and
    // lk_error_interval/end/status/rejected fields; Python exports distinct scopes.
    bool electrical_error_control = false;
    bool nls_error_control = false;
    real_t lk_electrical_error_ratio = TCAD_CONST(0.0);
    real_t lk_phi_atol = TCAD_CONST(0.0), lk_carrier_rtol = TCAD_CONST(0.0), lk_carrier_atol = TCAD_CONST(0.0);
    std::vector<real_t> lk_coarse_phi, lk_coarse_n, lk_coarse_p;
    std::vector<real_t> lk_delta_phi, lk_delta_n, lk_delta_p;
    real_t lk_free_energy = TCAD_CONST(0.0), lk_free_energy_increment = TCAD_CONST(0.0);
    real_t lk_dissipation = TCAD_CONST(0.0), lk_field_work = TCAD_CONST(0.0), lk_be_correction = TCAD_CONST(0.0);
    std::vector<real_t> lk_node_volumes, lk_parameters;
    std::vector<real_t> lk_drive_field, lk_polarization_increment;
};

enum class NlsContinuationStatus {
    not_started, complete, allocation_failure, solver_failure, unexpected_failure,
    max_reject, minimum_step, time_resolution, unrepresentable_estimate
};

// Native opt-in continuation. Owns the complete accepted history and diagnostic
// trace, including discarded trials. No caller-side state/time reconstruction.
// The originating simulator must outlive this object and keep its configuration.
class NlsTransientContinuation {
public:
    NlsTransientContinuation() = default;
    NlsTransientContinuation(const NlsTransientContinuation&) = delete;
    NlsTransientContinuation& operator=(const NlsTransientContinuation&) = delete;
    const std::vector<SimulationResult>& history() const { return history_; }
    const std::vector<TransientAttemptHistory>& trace() const { return trace_; }
    NlsContinuationStatus status() const { return status_; }
    size_t allocation_failures() const { return allocation_failures_; }
    size_t solver_failures() const { return solver_failures_; }
    size_t retries() const { return retries_; }
    real_t suggested_dt() const { return proposal_; }
    size_t accuracy_rejections() const { return rejected_; }
private:
    friend class DeviceSimulator;
    const class DeviceSimulator* owner_ = nullptr;
    std::vector<SimulationResult> history_;
    std::vector<TransientAttemptHistory> trace_;
    std::vector<real_t> configuration_;
    NlsContinuationStatus status_ = NlsContinuationStatus::not_started;
    size_t allocation_failures_ = 0, solver_failures_ = 0, retries_ = 0;
    // Controller state belongs to the last complete accepted group boundary.
    // Resource retries do not consume accuracy rejections or shrink this step.
    real_t proposal_ = TCAD_CONST(0.0);
    size_t rejected_ = 0;
};

class DeviceSimulator {
public:
    DeviceSimulator(size_t nx, size_t ny, size_t nz,
                    real_t dx, real_t dy, real_t dz);

    // Set material arrays (length nx*ny*nz)
    void set_permittivity(const std::vector<real_t>& eps);
    void set_edge_permittivity(const std::vector<real_t>& x_plus,
                               const std::vector<real_t>& x_minus,
                               const std::vector<real_t>& y_plus,
                               const std::vector<real_t>& y_minus,
                               const std::vector<real_t>& z_plus,
                               const std::vector<real_t>& z_minus);
    void set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p);
    void set_doping(const std::vector<real_t>& Nd_minus_Na);
    void set_charge_volume_fraction(const std::vector<real_t>& fraction);
    void set_optical_generation(const std::vector<real_t>& G_opt);
    void set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p);
    void set_thermal_voltage(real_t VT);
    void set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv);
    void set_bandgap(const std::vector<real_t>& Eg);
    void set_btbt_weight(const std::vector<real_t>& weight);

    // Boundary conditions
    void set_dirichlet_potential(const std::map<size_t, real_t>& bc);
    void set_electron_bc(const std::map<size_t, real_t>& bc);
    void set_hole_bc(const std::map<size_t, real_t>& bc);

    // Simulation control
    void set_quantum_enabled(bool enable);
    // Density-gradient coefficients [V*m^2].  Exposed so Sentaurus-calibrated
    // effective masses can be applied without recompiling the core.
    void set_density_gradient_coefficients(real_t bn, real_t bp);
    void set_density_gradient_silicon_multivalley(bool enable,
                                                  real_t longitudinal_mass,
                                                  real_t transverse_mass,
                                                  size_t subbands);
    void set_density_gradient_interface_distance_factor(real_t factor);
    void set_density_gradient_potential_form(bool enable);
    void set_density_gradient_step_boundary(
        bool enable, real_t electron_barrier_eV, real_t hole_barrier_eV,
        real_t electron_barrier_mass, real_t hole_barrier_mass,
        real_t electron_gamma, real_t hole_gamma,
        real_t electron_theta, real_t hole_theta);
    void set_grid_z(const std::vector<real_t>& z_pos);
    void set_grid_x(const std::vector<real_t>& x_pos);
    void set_grid_y(const std::vector<real_t>& y_pos);
    void set_phi_freezing_enabled(bool enable);
    // C档: Newton freeze flags — pin a block (phi/n/p) to its current value so
    // the Newton solve reduces to the other blocks. freeze_phi enables an
    // isolated continuity solve (flat band, drift term killed) for DD MMS.
    // These are Newton-only (nopt); the Gummel phi-freezing limit-cycle
    // stabiliser is separate and unaffected.
    void set_newton_freeze_phi(bool enable);
    void set_newton_freeze_n(bool enable);
    void set_newton_freeze_p(bool enable);
    void set_gummel_max_iter(size_t max_iter);
    void set_nonlinear_history_enabled(bool enable) { nonlinear_history_enabled_ = enable; }
    void set_tolerance(real_t tol);
    void set_poisson_solver_type(int type);
    void set_continuity_solver_type(int type);
    void set_use_newton(bool enable);
    void set_newton_primary(bool enable) { newton_primary_ = enable; }
    void set_ohmic_contacts(const std::set<size_t>& nodes,
                            const std::map<size_t, real_t>& EFn,
                            const std::map<size_t, real_t>& EFp,
                            real_t ni);
    void clear_ohmic_contacts();
    // Classical zero-Fermi Poisson-Boltzmann seed; commit only on convergence.
    EquilibriumResult solve_equilibrium(size_t max_iter = 100,
        real_t tolerance = TCAD_CONST(1e-10), const std::vector<char>& carrier_mask = {});

    // Newton solver options
    void set_newton_damping(real_t damping);
    void set_newton_min_damping(real_t min_damping);
    void set_newton_use_line_search(bool enable);
    void set_newton_line_search_max(size_t max);
    void set_newton_use_log_damping(bool enable);
    void set_newton_use_log_space(bool enable);
    void set_newton_log_density_update(const std::string& mode);
    std::string get_newton_log_density_update() const;
    void set_newton_jacobian_reuse_threshold(real_t threshold);

    // Thermal coupling
    void set_thermal_coupling_enabled(bool enable);
    void set_thermal_conductivity(const std::vector<real_t>& kappa);
    void set_ambient_temperature(real_t T_ambient);
    void set_thermal_dirichlet(const std::map<size_t, real_t>& bc);
    // Local lattice temperature feeds mobility only; carrier VT/statistics
    // remain at the reference temperature. Not a carrier-energy model.
    void set_lattice_mobility_feedback(bool enable, size_t max_iter,
        real_t temperature_tol, real_t relaxation);
    SimulationResult solve_lattice_step(const std::vector<real_t>& previous_temperature,
        const std::vector<real_t>& heat_capacity, real_t dt);

    // Band-to-band tunneling
    void set_btbt_enabled(bool enable);
    void set_btbt_params(real_t A, real_t B, real_t D);
    void set_btbt_field_mode(int mode);
    void set_btbt_field_options(int mode, real_t cap);
    void set_btbt_field_shape(int mode, real_t cap, real_t alpha, real_t ref);
    void set_btbt_continuity_scale(real_t scale);
    void set_btbt_use_nonlocal(bool enable);
    void set_btbt_nonlocal_params(real_t tunnel_path_frac, size_t wkb_npts);
    void set_btbt_nonlocal_mass(real_t mass_ratio);
    void set_high_field_saturation(bool enable, real_t vsat_n, real_t vsat_p,
                                   real_t beta_n, real_t beta_p, int driving);

    // Explicit edge driving-force cutoff [V/m]; equality is active.
    void set_hfs_quasi_fermi_at_contacts(bool enabled) { hfs_qf_at_contacts_ = enabled; }
    bool get_hfs_quasi_fermi_at_contacts() const { return hfs_qf_at_contacts_; }
    void set_high_field_reference_density(real_t n0, real_t p0);
    real_t get_high_field_reference_density_n() const { return hfs_refdens_n_; }
    real_t get_high_field_reference_density_p() const { return hfs_refdens_p_; }
    void set_hfs_low_field_cutoff(real_t cutoff);
    real_t get_hfs_low_field_cutoff() const { return hfs_low_field_cutoff_; }

    // Avalanche impact ionization (Chynoweth).  alpha(E)=A*exp(-B/|E|) [1/m].
    // G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q injected into both continuity eqns.
    void set_ii_enabled(bool enable);
    // Numerical avalanche source cutoff [V/m], inclusive at equality.
    void set_ii_reference_density(real_t n0, real_t p0);
    real_t get_ii_reference_density_n() const { return ii_refdens_n_; }
    real_t get_ii_reference_density_p() const { return ii_refdens_p_; }
    void set_ii_driving(int driving);
    int get_ii_driving() const { return ii_driving_; }
    void set_ii_field_floor(real_t floor);
    real_t get_ii_field_floor() const { return ii_field_floor_; }
    void set_ii_params(real_t A_n, real_t B_n, real_t A_p, real_t B_p);
    void set_auger_enabled(bool enable);
    void set_auger_params(real_t Cn, real_t Cp);

    // Dielectric breakdown (M7b, audit §22). Flags dielectric nodes whose
    // |E| exceeds E_bd. On subsequent solves, edges touching a failed node
    // carry the explicit conventional current J_bd=sigma_bd*E [A/m^2]. The
    // state is irreversible and persisted across solve() calls.
    void set_breakdown_enabled(bool enable);
    void set_breakdown_params(const std::vector<char>& bd_mask,
                              const std::vector<real_t>& E_bd,
                              real_t sigma_bd);
    // Persistent breakdown state (1 = node has broken down). Read back after
    // solve() so callers can inspect which oxide nodes failed.
    const std::vector<char>& breakdown_state() const { return bd_state_; }

    // Ferroelectric polarization (Landau-Khalatnikov)
    void set_ferroelectric_enabled(bool enable);
    // Freeze FE/irreversible breakdown history during numerical continuation.
    // Electrical initial guesses still advance; this is not a full snapshot API.
    void set_history_updates_enabled(bool enable) { history_updates_enabled_ = enable; }
    // Scoped protocol checkpoint, not a general multiphysics snapshot.
    void begin_reliability_transaction();
    void commit_reliability_transaction();
    void rollback_reliability_transaction();
    void set_ferroelectric_params(const std::vector<char>& fe_mask,
                                  real_t alpha, real_t beta);
    // Ferroelectric model selection (M7c): 0 = Landau-Khalatnikov, 1 = Preisach.
    void set_ferroelectric_model(int model);
    // FE polar axis: 0=x, 1=y, 2=z (P0-1)
    void set_ferroelectric_polar_axis(int axis);
    // Preisach parameters (M7c, used only when model == 1). Escale=0 => Ec;
    // a smaller Escale lets |P| approach the named saturation Ps.
    void set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale);
    // Internal field / Imprint offset (P2.1). Shifts E_eff = E - E_bi; 0 => symmetric.
    void set_ferroelectric_builtin_field(real_t E_bi);
    // Depolarization field (comments2.docx P3). Sets FE relative permittivity.
    void set_ferroelectric_depol(real_t eps_fe);
    // NLS (P3, model==2): Merz-law parameters tau0 [s], E0 [V/m], dt [s].
    void set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt);
    // Leakage current (PF/FN) (P2.2). Sets leaky-node mask + coefficients.
    void set_leakage(const std::vector<char>& mask,
                     real_t C_pf, real_t B_pf, real_t phi_t,
                     real_t C_fn, real_t B_fn, real_t phi_b,
                     real_t E_floor, real_t sigma_cap);
    // Optional signed-field Fowler-Nordheim coefficients. Positive/negative
    // refer to the field component on each oriented mesh edge.
    void set_leakage_fn_polarity(real_t C_positive, real_t B_positive,
                                 real_t C_negative, real_t B_negative);
    void set_leakage_enabled(bool enable);
    // Interface traps (Dit) + bulk oxide traps (P6).
    void set_interface_traps(const std::vector<char>& mask,
                             real_t D_it, real_t E_t);
    void set_oxide_traps(const std::vector<real_t>& Q_ot);
    // Persistent signed polarization field (survives solve() rebuilds so a bias
    // sweep has path-dependent memory -> hysteresis). Read back for inspection.
    const std::vector<real_t>& fe_polarization() const { return fe_polarization_; }
    // Explicit accepted cubic-LK restart, never advances physical time.
    void set_ferroelectric_history(const std::vector<real_t>& polarization);
    void set_ferroelectric_ensemble_history(const std::vector<real_t>& polarization,
                                           const std::vector<real_t>& play);
    const std::vector<real_t>& ferroelectric_play_history() const { return fe_play_state_; }
    std::vector<real_t> ferroelectric_ensemble_parameters() const {
        return {static_cast<real_t>(fe_model_), fe_ps_, fe_ec_, fe_escale_,
                fe_nls_tau0_, fe_nls_E0_, fe_nls_dt_, fe_E_bi_, fe_eps_fe_,
                static_cast<real_t>(fe_polar_axis_)};
    }
    const std::vector<char>& ferroelectric_mask() const { return fe_mask_; }
    std::vector<real_t> ferroelectric_lk_parameters() const {
        return {fe_alpha_, fe_beta_, fe_gamma_, fe_E_bi_, fe_eps_fe_, static_cast<real_t>(fe_polar_axis_)};
    }
    const std::vector<real_t>& permittivity() const { return eps_; }


    void configure_three_temperature(const std::vector<std::string>& c,const std::vector<std::string>& f,
        const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& args,double time) {
        if(!reliability_checkpoints_.empty()) throw std::logic_error("cannot enter three-temperature mode inside reliability transaction");
        if(isolated_relaxation_.enabled() || energy_coordinate_.enabled()) throw std::logic_error("isolated or energy-coordinate mode already configured");
        three_temperature_.configure(npts(),c,f,vn,vp,args,time);
    }
    ThreeTemperatureDispatchResult prepare_three_temperature(double dt,double q,double p,double e,int budget) {
        return three_temperature_.prepare(dt,q,p,e,budget);
    }
    size_t three_temperature_token() const {return three_temperature_.token();}
    void discard_three_temperature(size_t token) {three_temperature_.discard(token);}
    ThreeTemperatureDispatchResult three_temperature_state() const {return three_temperature_.state();}
    double three_temperature_time() const {return three_temperature_.time();}
    bool three_temperature_enabled() const {return three_temperature_.enabled();}
    SimulationResult commit_three_temperature(size_t token);
    std::vector<std::vector<double>> structured_three_temperature_seed() const;

    void configure_energy_coordinate(const std::vector<std::string>& c,const std::vector<std::string>& f,
        const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& args,
        const std::vector<std::string>& laws,const std::vector<std::string>& excess,double time) {
        if(!reliability_checkpoints_.empty() || three_temperature_.enabled() || isolated_relaxation_.enabled())
            throw std::logic_error("cannot enter energy-coordinate mode inside another mode or reliability transaction");
        energy_coordinate_.configure(npts(),c,f,vn,vp,args,laws,excess,time);
    }
    EnergyCoordinateSnapshot prepare_energy_coordinate(double dt,double q,double p,double e,int budget) {
        return energy_coordinate_.prepare(dt,q,p,e,budget);
    }
    void commit_energy_coordinate(size_t token) {energy_coordinate_.commit(token);}
    void discard_energy_coordinate(size_t token) {energy_coordinate_.discard(token);}
    EnergyCoordinateSnapshot energy_coordinate_state() const {return energy_coordinate_.snapshot();}
    bool energy_coordinate_enabled() const {return energy_coordinate_.enabled();}

    void configure_isolated_relaxation(const std::vector<std::string>& initial,
        const std::vector<std::string>& parameters,const std::vector<double>& vn,
        const std::vector<double>& vp,double time) {
        if(!reliability_checkpoints_.empty() || three_temperature_.enabled() || energy_coordinate_.enabled())
            throw std::logic_error("cannot enter isolated relaxation inside another mode or reliability transaction");
        isolated_relaxation_.configure(npts(),initial,parameters,vn,vp,time);
    }
    void configure_lattice_excess(const std::vector<std::string>& initial,
        const std::vector<std::string>& parameters,const std::vector<std::string>& faces,
        const std::vector<double>& vn,const std::vector<double>& vp,double time,
        const std::vector<std::string>& baths={},const std::vector<std::string>& varshni={}) {
        if(!reliability_checkpoints_.empty() || three_temperature_.enabled() || energy_coordinate_.enabled())
            throw std::logic_error("cannot enter lattice excess inside another mode or reliability transaction");
        isolated_relaxation_.configure_lattice(npts(),initial,parameters,faces,vn,vp,time,baths,varshni);
    }
    std::vector<std::string> prepare_isolated_relaxation(double dt,double q,double p,double e,int budget,
            const std::vector<std::string>& source={}) {
        return isolated_relaxation_.prepare(dt,q,p,e,budget,source);
    }
    size_t isolated_relaxation_token() const {return isolated_relaxation_.token();}
    void discard_isolated_relaxation(size_t token) {isolated_relaxation_.discard(token);}
    void commit_isolated_relaxation(size_t token) {isolated_relaxation_.commit(token);}
    IsolatedRelaxationSnapshot isolated_relaxation_state() const {return isolated_relaxation_.snapshot();}
    bool isolated_relaxation_enabled() const {return isolated_relaxation_.enabled();}

    // Initial guess (optional). If set, solve() uses these instead of equilibrium.
    void set_initial_guess(const std::vector<real_t>& phi,
                           const std::vector<real_t>& n,
                           const std::vector<real_t>& p);
    void clear_initial_guess();

    // Cryo-CMOS: Temperature-dependent models
    void set_temperature(real_t T);
    void set_statistics_type(int type);   // 0=Boltzmann, 1=FermiDirac
    void set_mobility_model(int type);    // 0=Constant, 1=Arora, 2=LowTemp

    // Transient simulation
    void set_transient_enabled(bool enable);
    void set_transient_dt(real_t dt);
    void set_transient_t_final(real_t t_final);
    void set_transient_start_time(real_t time);
    void set_transient_lk_coupled(bool enable) {
        transient_lk_coupled_ = enable;
        transient_lk_coupled_configured_ = true;
    }
    void set_transient_lk_material_field(bool enable) {
        transient_lk_material_field_ = enable;
        transient_lk_material_field_configured_ = true;
    }
    void set_transient_lk_zero_d_faces(const std::string& faces);
    void set_transient_lk_substepping(bool enable, real_t safety);
    void set_transient_lk_error_control(bool enable, real_t rtol, real_t atol,
        real_t min_dt, size_t max_reject);
    void set_transient_lk_electrical_error_control(bool enable, real_t phi_atol,
        real_t carrier_rtol, real_t carrier_atol);
    void set_transient_electrical_error_control(bool enable, real_t phi_atol,
        real_t carrier_rtol, real_t carrier_atol, real_t min_dt, size_t max_reject);
    void set_transient_nls_error_control(bool enable, real_t rtol, real_t atol,
        real_t phi_atol, real_t carrier_rtol, real_t carrier_atol,
        real_t min_dt, size_t max_reject);
    // Opt-in two-sided event sampling for fixed-step split NLS. Initially
    // requires full FE support, complete polar end contacts and no depolarization.
    // Half width is a physical time interval, not a coercive-field threshold.
    void set_transient_nls_event_control(bool enable, real_t half_width) {
        if (!isfinite_q(half_width) || half_width <= TCAD_CONST(0.0))
            throw std::invalid_argument("NLS event half width must be finite and positive");
        transient_nls_event_control_ = enable;
        transient_nls_event_half_width_ = half_width;
    }
    // Piecewise-linear potential offsets relative to configured Dirichlet BCs.
    // All nodes share a clock starting at zero. Every knot is a step endpoint.
    void set_transient_voltage_waveforms(const std::vector<real_t>& times,
        const std::map<size_t, std::vector<real_t>>& offsets);
    void clear_transient_voltage_waveforms();
    void set_ferroelectric_gamma(real_t gamma);
    std::vector<SimulationResult> solve_transient();
    // Fixed or error-controlled split-NLS. Retries are bounded per complete
    // accepted interval/group, separately from accuracy-driven rejections. Once the
    // initial ledger is ready, allocation exhaustion returns an accepted prefix
    // and a status without allocating. Call again on the same continuation to
    // resume after memory becomes available. Setup/preflight can still throw
    // while leaving an existing continuation untouched. Its trace is owned by
    // the continuation, not transient_attempt_history() after this call.
    void advance_transient_nls(NlsTransientContinuation& continuation, size_t max_retries = 1);
    const std::vector<TransientAttemptHistory>& transient_attempt_history() const {
        return transient_attempt_history_;
    }

    // Run simulation
    SimulationResult solve();
    // Optional telemetry on a result from this simulator's current steady solve.
    // Does not solve, alter returned fields, or change the convergence verdict.
    void audit_steady_equations(SimulationResult& result, bool include_newton = false);

    // Grid accessors for Python
    size_t nx() const { return g_.nx; }
    size_t ny() const { return g_.ny; }
    size_t nz() const { return g_.nz; }
    size_t npts() const { return g_.npts(); }

private:
    std::vector<real_t> nls_continuation_configuration() const;
    std::vector<SimulationResult> solve_transient_impl(NlsTransientContinuation* recovery, size_t max_retries);
    SimulationResult solve_lattice_attempt();
    void validate_lattice_scope() const;
    void transport_mobilities(std::vector<real_t>& mn, std::vector<real_t>& mp) const;
    void add_transient_electrostatic_ledger(
        SimulationResult& state, const SimulationResult* previous) const;
    void add_transient_lk_ledger(SimulationResult& state,
        const SimulationResult* previous, const std::vector<real_t>& drive_phi) const;
    // Compute edge-centered SG electron/hole current densities [A/m^2] in full
    // __float128 precision from the converged solution, writing into res.Jn_x
    // /Jn_y/Jn_z/Jp_x/Jp_y/Jp_z.  Each array has length npts; entry idx is the
    // +axis edge leaving node idx (x: idx->idx+1, y: idx->idx+nx, z: idx->idx+
    // nx*ny).  Domain-boundary edges (no +neighbor) are set to 0.  This avoids
    // the catastrophic cancellation of Python re-derivation from double phi/n/p
    // when carrier densities are large.  (Audit §20.)
    void compute_edge_currents(SimulationResult& res,
                               const std::vector<real_t>& phi,
                               const std::vector<real_t>& n,
                               const std::vector<real_t>& p,
                               const std::vector<real_t>* transport_Qn = nullptr,
                               const std::vector<real_t>* transport_Qp = nullptr);

    ThreeTemperatureDeviceSession three_temperature_;
    EnergyCoordinateDeviceSession energy_coordinate_;
    IsolatedRelaxationDeviceSession isolated_relaxation_;
    Grid3D g_;
    PoissonSolver poisson_;
    GummelSolver gummel_;
    NewtonSolver newton_;
    DensityGradient dg_;
    std::vector<real_t> eps_;
    std::vector<real_t> edge_eps_x_plus_, edge_eps_x_minus_;
    std::vector<real_t> edge_eps_y_plus_, edge_eps_y_minus_;
    std::vector<real_t> edge_eps_z_plus_, edge_eps_z_minus_;
    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> charge_volume_fraction_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> btbt_weight_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    std::map<size_t, real_t> phi_bc_, n_bc_, p_bc_;
    bool has_initial_guess_ = false;
    bool nonlinear_history_enabled_ = false;
    std::vector<TransientAttemptHistory> transient_attempt_history_;
    std::vector<real_t> init_phi_, init_n_, init_p_;
    bool quantum_enabled_ = false;
    real_t dg_bn_ = TCAD_CONST(4.885e-20);
    real_t dg_bp_ = TCAD_CONST(3.432e-20);
    bool dg_silicon_multivalley_ = false;
    real_t dg_silicon_ml_ = TCAD_CONST(0.916);
    real_t dg_silicon_mt_ = TCAD_CONST(0.190);
    size_t dg_silicon_subbands_ = 4;
    real_t dg_interface_distance_factor_ = TCAD_CONST(1.0);
    bool dg_potential_form_enabled_ = false;
    // Accepted potential-form transport state persisted across bias points.
    // GummelSolver is rebuilt for every solve(), so continuation would
    // otherwise restart from a density-form estimate at every voltage step.
    std::vector<real_t> dg_transport_Qn_, dg_transport_Qp_;
    bool dg_step_boundary_enabled_ = false;
    real_t dg_step_e_barrier_eV_ = TCAD_CONST(3.17);
    real_t dg_step_h_barrier_eV_ = TCAD_CONST(4.70);
    real_t dg_step_e_mass_ = TCAD_CONST(0.42);
    real_t dg_step_h_mass_ = TCAD_CONST(1.0);
    // Eq. 250 uses gamma(0+), i.e. the non-solved barrier side.
    real_t dg_step_e_gamma_ = TCAD_CONST(1.0);
    real_t dg_step_h_gamma_ = TCAD_CONST(1.0);
    real_t dg_step_e_theta_ = TCAD_CONST(0.5);
    real_t dg_step_h_theta_ = TCAD_CONST(0.5);
    size_t max_iter_ = 100;   // raised from 50 for correct div(P) coupling
    // A relative update tolerance below float64/linear-solver accuracy made
    // otherwise valid bias sweeps hit max_iter and then restart from thermal
    // equilibrium at the next point.  1e-6 is the production default used by
    // the high-level API and is tight enough for terminal-current extraction.
    real_t tol_ = TCAD_CONST(1e-6);
    real_t VT_ = TCAD_CONST(0.02585);
    SolverType poisson_solver_type_ = SolverType::DENSE_DIRECT;
    SolverType continuity_solver_type_ = SolverType::DENSE_DIRECT;
    // Ohmic contact data
    std::set<size_t> ohmic_nodes_;
    std::map<size_t, real_t> ohmic_EFn_, ohmic_EFp_;
    real_t ohmic_ni_ = TCAD_CONST(1.07e16);

    bool use_newton_ = false;
    bool phi_freezing_enabled_ = true;
    bool newton_primary_ = false;  // skip Gummel warm-up, Newton from initial guess
    // Newton freeze flags (C档) — expose NewtonOptions::freeze_phi/n/p.
    bool newton_freeze_phi_ = false;
    bool newton_freeze_n_ = false;
    bool newton_freeze_p_ = false;
    // Newton options
    real_t newton_damping_ = TCAD_CONST(1.0);
    real_t newton_min_damping_ = TCAD_CONST(0.01);
    bool newton_use_line_search_ = true;
    size_t newton_line_search_max_ = 10;
    bool newton_use_log_damping_ = false;
    bool newton_use_log_space_ = false;
    bool newton_additive_log_density_update_ = false;
    real_t newton_jacobian_reuse_threshold_ = TCAD_CONST(0.0);
    // Thermal coupling
    bool thermal_coupling_enabled_ = false;
    std::vector<real_t> thermal_conductivity_;
    real_t ambient_temperature_ = TCAD_CONST(300.0);
    std::map<size_t, real_t> thermal_bc_;
    bool lattice_feedback_enabled_ = false;
    size_t lattice_feedback_max_iter_ = 100;
    real_t lattice_feedback_tol_ = TCAD_CONST(1e-7), lattice_relaxation_ = TCAD_CONST(0.5);
    std::vector<real_t> mobility_temperature_;
    real_t lattice_dt_ = TCAD_CONST(0.0);
    std::vector<real_t> lattice_previous_temperature_, lattice_heat_capacity_;
    // BTBT
    bool btbt_enabled_ = false;
    real_t btbt_A_ = TCAD_CONST(3.1e21);
    real_t btbt_B_ = TCAD_CONST(2.0e9);  // V/m (SI; 2e7 V/cm)
    real_t btbt_D_ = TCAD_CONST(2.0);
    int btbt_field_mode_ = 0;
    real_t btbt_field_cap_ = TCAD_CONST(0.0);
    real_t btbt_field_alpha_ = TCAD_CONST(0.0);
    real_t btbt_field_ref_ = TCAD_CONST(1.0e8);
    real_t btbt_continuity_scale_ = TCAD_CONST(1.0);
    bool btbt_use_nonlocal_ = false;
    real_t btbt_tunnel_path_frac_ = TCAD_CONST(0.5);
    size_t btbt_wkb_npts_ = 64;
    real_t btbt_nonlocal_mass_ = TCAD_CONST(0.25);
    bool hfs_enabled_ = false;
    real_t hfs_vsat_n_ = TCAD_CONST(1.07e5);
    real_t hfs_vsat_p_ = TCAD_CONST(8.37e4);
    real_t hfs_beta_n_ = TCAD_CONST(2.0);
    real_t hfs_beta_p_ = TCAD_CONST(1.0);
    void validate_hfs_reference_scope() const;
    real_t hfs_refdens_n_ = TCAD_CONST(0.0), hfs_refdens_p_ = TCAD_CONST(0.0);
    int hfs_driving_ = 0;
    bool hfs_qf_at_contacts_ = true;
    real_t hfs_low_field_cutoff_ = TCAD_CONST(0.0);
    // Avalanche impact ionization (SI units; defaults = silicon, see
    // ImpactIonizationParams in gummel_solver.h)
    bool ii_enabled_ = false;
    real_t ii_A_n_ = TCAD_CONST(7.03e7);
    real_t ii_B_n_ = TCAD_CONST(1.231e8);
    real_t ii_A_p_ = TCAD_CONST(1.58e8);
    real_t ii_B_p_ = TCAD_CONST(2.036e8);
    void validate_ii_driving_scope() const;
    int ii_driving_ = 0;
    real_t ii_refdens_n_ = TCAD_CONST(0.0), ii_refdens_p_ = TCAD_CONST(0.0);
    real_t ii_field_floor_ = TCAD_CONST(1.0e5);
    // Auger recombination (SI units; defaults = silicon Sentaurus MaterialDB)
    bool auger_enabled_ = false;
    real_t auger_Cn_ = TCAD_CONST(2.8e-43);  // m^6/s (2.8e-31 cm^6/s)
    real_t auger_Cp_ = TCAD_CONST(9.9e-44);  // m^6/s (9.9e-32 cm^6/s)
    // Dielectric breakdown (M7b, audit §22)
    bool bd_enabled_ = false;
    std::vector<char> bd_mask_;       // which nodes participate (dielectric) [npts]
    std::vector<real_t> E_bd_;        // per-node breakdown field [V/m] [npts]
    real_t sigma_bd_ = TCAD_CONST(1.0e-2);   // post-breakdown filament conductivity [S/m]
    std::vector<char> bd_state_;      // 1 = node broken down (irreversible) [npts]
    bool bd_state_init_ = false;
    // Ferroelectric
    bool fe_enabled_ = false;
    bool history_updates_enabled_ = true;
    std::vector<char> fe_mask_;
    real_t fe_alpha_ = -TCAD_CONST(5.0e8);    // Landau alpha [m/F] for HfZrO (P1.2)
    real_t fe_beta_ = TCAD_CONST(1.5e10);     // Landau beta [m^5/(F*C^2)] (P1.2)
    // Ferroelectric model + Preisach params (M7c)
    int fe_model_ = 0;             // 0 = LK, 1 = PREISACH
    int fe_polar_axis_ = 0;        // 0=x, 1=y, 2=z
    real_t fe_ps_ = TCAD_CONST(0.2);          // Preisach saturation polarization [C/m^2]
    real_t fe_ec_ = TCAD_CONST(1.0e9);        // Preisach coercive field [V/m]
    real_t fe_escale_ = TCAD_CONST(0.0);      // Preisach tanh width [V/m]; 0 => Ec (default)
    real_t fe_E_bi_ = TCAD_CONST(0.0);        // Internal/imprint field offset [V/m] (P2.1)
    real_t fe_eps_fe_ = TCAD_CONST(0.0);      // FE relative permittivity for depol (comments2.docx P3)
    real_t fe_nls_tau0_ = TCAD_CONST(1.0e-6); // NLS Merz tau0 [s] (P3)
    real_t fe_nls_E0_ = TCAD_CONST(2.0e9);    // NLS Merz E0 [V/m] (P3)
    real_t fe_nls_dt_ = TCAD_CONST(1.0e-6);   // NLS dwell time [s] (P3)
    std::vector<real_t> fe_play_state_;  // Preisach play-operator state, len npts
    // Authoritative vector P (3 components/node, interleaved [Px,Py,Pz]),
    // persistent across solve() calls (GummelSolver is rebuilt every solve();
    // without this, P is wiped and hysteresis vanishes). Layout: [3*idx+c].
    std::vector<real_t> fe_polarization_;
    bool fe_polarization_init_ = false;
    // Leakage current (PF/FN) (P2.2)
    bool leak_enabled_ = false;
    std::vector<char> leak_mask_;
    real_t leak_C_pf_ = TCAD_CONST(0.0), leak_B_pf_ = TCAD_CONST(0.0), leak_phi_t_ = TCAD_CONST(0.0);
    real_t leak_C_fn_ = TCAD_CONST(0.0), leak_B_fn_ = TCAD_CONST(0.0), leak_phi_b_ = TCAD_CONST(0.0);
    bool leak_fn_polarity_enabled_ = false;
    real_t leak_C_fn_positive_ = TCAD_CONST(0.0), leak_B_fn_positive_ = TCAD_CONST(0.0);
    real_t leak_C_fn_negative_ = TCAD_CONST(0.0), leak_B_fn_negative_ = TCAD_CONST(0.0);
    real_t leak_E_floor_ = TCAD_CONST(1.0e6);
    real_t leak_sigma_cap_ = TCAD_CONST(0.05);
    // Interface traps (Dit) + bulk oxide traps (P6)
    std::vector<char> trap_mask_;
    real_t trap_D_it_ = TCAD_CONST(0.0);       // interface trap density [cm^-2 eV^-1]
    real_t trap_E_t_ = TCAD_CONST(0.0);        // trap energy [eV] rel. intrinsic
    std::vector<real_t> Q_ot_;      // bulk oxide trap charge [C/m^3]
    // Cryo-CMOS
    real_t temperature_ = TCAD_CONST(300.0);
    StatisticsType statistics_type_ = StatisticsType::BOLTZMANN;
    MobilityModelType mobility_model_type_ = MobilityModelType::CONSTANT;
    // Transient
    bool transient_enabled_ = false;
    bool transient_lk_coupled_ = false;
    bool transient_lk_coupled_configured_ = false;
    bool transient_lk_material_field_ = false;
    bool transient_lk_material_field_configured_ = false;
    bool transient_lk_substepping_ = false;
    real_t transient_lk_safety_ = TCAD_CONST(0.5);
    bool transient_lk_error_control_ = false;
    bool transient_lk_electrical_error_control_ = false;
    bool transient_electrical_error_control_ = false;
    bool transient_nls_error_control_ = false;
    bool transient_nls_event_control_ = false;
    real_t transient_nls_event_half_width_ = TCAD_CONST(1e-18);
    struct NlsErrorOptions {
        real_t rtol = TCAD_CONST(1.0e-3), atol = TCAD_CONST(1.0e-8), phi_atol = TCAD_CONST(1.0e-6);
        real_t carrier_rtol = TCAD_CONST(1.0e-3), carrier_atol = TCAD_CONST(1.0e10), min_dt = TCAD_CONST(1.0e-15);
        size_t max_reject = 20;
    } transient_nls_error_;
    real_t transient_phi_atol_ = TCAD_CONST(1.0e-6), transient_carrier_rtol_ = TCAD_CONST(1.0e-3);
    real_t transient_carrier_atol_ = TCAD_CONST(1.0e10), transient_error_min_dt_ = TCAD_CONST(1.0e-15);
    size_t transient_error_max_reject_ = 20;
    real_t transient_lk_phi_atol_ = TCAD_CONST(1.0e-6);
    real_t transient_lk_carrier_rtol_ = TCAD_CONST(1.0e-3), transient_lk_carrier_atol_ = TCAD_CONST(1.0e10);
    real_t transient_lk_error_rtol_ = TCAD_CONST(1.0e-3), transient_lk_error_atol_ = TCAD_CONST(1.0e-6);
    real_t transient_lk_min_dt_ = TCAD_CONST(1.0e-15);
    size_t transient_lk_max_reject_ = 20;
    real_t transient_dt_ = TCAD_CONST(1.0e-12);
    real_t transient_t_final_ = TCAD_CONST(1.0e-9);
    real_t transient_start_time_ = TCAD_CONST(0.0);
    std::vector<real_t> transient_waveform_times_;
    std::map<size_t, std::vector<real_t>> transient_voltage_offsets_;
    // Zero keeps classical transients independent of FE configuration. LK
    // transient callers must explicitly provide a positive damping value.
    real_t fe_gamma_ = TCAD_CONST(0.0);
    struct ReliabilityCheckpoint {
        std::vector<real_t> polarization, play, charge, phi, n, p;
        std::vector<char> breakdown;
        std::map<size_t, real_t> phi_bc, n_bc, p_bc;
        bool polarization_init, breakdown_init, initial_guess, history_updates;
        real_t ps, ec, escale, builtin_field, tau0, e0, dwell, start_time;
        // Continuation potentials belong to the accepted electrical seed;
        // empty caches and each nested checkpoint must also be preserved.
        std::vector<real_t> transport_Qn, transport_Qp;
    };
    std::vector<ReliabilityCheckpoint> reliability_checkpoints_;
};

} // namespace tcad
