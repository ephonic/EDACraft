#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "gummel_solver.h"
#include "newton_solver.h"
#include "density_gradient.h"
#include "mobility_model.h"
#include "statistics.h"
#include <vector>
#include <map>
#include <string>

namespace tcad {

// High-level device simulator interface consumed by Python/Cython
struct SimulationResult {
    std::vector<real_t> phi;    // Electrostatic potential [V]
    std::vector<real_t> n;      // Electron concentration [m^-3]
    std::vector<real_t> p;      // Hole concentration [m^-3]
    std::vector<real_t> Ex, Ey, Ez; // Electric field [V/m]
    std::vector<real_t> temperature; // Lattice temperature [K]
    // Edge-centered SG current densities [A/m^2], computed in __float128 at
    // full solver precision (post-convergence) and downcast to real_t.  These
    // avoid the catastrophic cancellation that plagues Python re-derivation
    // from double phi/n/p when carrier densities are large (e.g. p~1e24 at
    // Na=1e18 cm^-3).  Length = npts per axis-direction array; entry idx is the
    // +axis edge leaving node idx (x_plus[idx] = edge idx->idx+1, etc.).
    // Zero entries indicate domain-boundary or insulator edges.  (Audit §20.)
    std::vector<real_t> Jn_x, Jn_y, Jn_z;  // electron current density
    std::vector<real_t> Jp_x, Jp_y, Jp_z;  // hole current density
    bool converged = false;
    size_t iterations = 0;
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
    void set_optical_generation(const std::vector<real_t>& G_opt);
    void set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p);
    void set_thermal_voltage(real_t VT);
    void set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv);
    void set_bandgap(const std::vector<real_t>& Eg);

    // Boundary conditions
    void set_dirichlet_potential(const std::map<size_t, real_t>& bc);
    void set_electron_bc(const std::map<size_t, real_t>& bc);
    void set_hole_bc(const std::map<size_t, real_t>& bc);

    // Simulation control
    void set_quantum_enabled(bool enable);
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
    void set_tolerance(real_t tol);
    void set_poisson_solver_type(int type);
    void set_continuity_solver_type(int type);
    void set_use_newton(bool enable);

    // Newton solver options
    void set_newton_damping(real_t damping);
    void set_newton_min_damping(real_t min_damping);
    void set_newton_use_line_search(bool enable);
    void set_newton_line_search_max(size_t max);
    void set_newton_use_log_damping(bool enable);
    void set_newton_use_log_space(bool enable);
    void set_newton_jacobian_reuse_threshold(real_t threshold);

    // Thermal coupling
    void set_thermal_coupling_enabled(bool enable);
    void set_thermal_conductivity(const std::vector<real_t>& kappa);
    void set_ambient_temperature(real_t T_ambient);
    void set_thermal_dirichlet(const std::map<size_t, real_t>& bc);

    // Band-to-band tunneling
    void set_btbt_enabled(bool enable);
    void set_btbt_params(real_t A, real_t B, int D);
    void set_btbt_use_nonlocal(bool enable);

    // Avalanche impact ionization (Chynoweth).  alpha(E)=A*exp(-B/|E|) [1/m].
    // G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q injected into both continuity eqns.
    void set_ii_enabled(bool enable);
    void set_ii_params(real_t A_n, real_t B_n, real_t A_p, real_t B_p);

    // Dielectric breakdown (M7b, audit §22).  Flags dielectric nodes whose
    // |E| exceeds the material breakdown field E_bd and applies a soft-
    // breakdown leakage term sigma_bd [F/m^3] there (added to the Poisson
    // diagonal, same units as eps/dx^2, locally relaxing phi toward 0 so a
    // gate leak develops).  The breakdown state is IRREVERSIBLE and persisted
    // across solve() calls (like fe_polarization_).
    void set_breakdown_enabled(bool enable);
    void set_breakdown_params(const std::vector<char>& bd_mask,
                              const std::vector<real_t>& E_bd,
                              real_t sigma_bd);
    // Persistent breakdown state (1 = node has broken down). Read back after
    // solve() so callers can inspect which oxide nodes failed.
    const std::vector<char>& breakdown_state() const { return bd_state_; }

    // Ferroelectric polarization (Landau-Khalatnikov)
    void set_ferroelectric_enabled(bool enable);
    void set_ferroelectric_params(const std::vector<char>& fe_mask,
                                  real_t alpha, real_t beta);
    // Ferroelectric model selection (M7c): 0 = Landau-Khalatnikov, 1 = Preisach.
    void set_ferroelectric_model(int model);
    // Preisach parameters (M7c, used only when model == 1). Escale=0 => Ec/3
    // (P1.3); a smaller Escale lets |P| approach the named saturation Ps.
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
    void set_leakage_enabled(bool enable);
    // Interface traps (Dit) + bulk oxide traps (P6).
    void set_interface_traps(const std::vector<char>& mask,
                             real_t D_it, real_t E_t);
    void set_oxide_traps(const std::vector<real_t>& Q_ot);
    // Persistent signed polarization field (survives solve() rebuilds so a bias
    // sweep has path-dependent memory -> hysteresis). Read back for inspection.
    const std::vector<real_t>& fe_polarization() const { return fe_polarization_; }

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
    void set_ferroelectric_gamma(real_t gamma);
    std::vector<SimulationResult> solve_transient();

    // Run simulation
    SimulationResult solve();

    // Grid accessors for Python
    size_t nx() const { return g_.nx; }
    size_t ny() const { return g_.ny; }
    size_t nz() const { return g_.nz; }
    size_t npts() const { return g_.npts(); }

private:
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
                               const std::vector<real_t>& p);

    Grid3D g_;
    PoissonSolver poisson_;
    GummelSolver gummel_;
    NewtonSolver newton_;
    DensityGradient dg_;
    std::vector<real_t> eps_;
    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    std::map<size_t, real_t> phi_bc_, n_bc_, p_bc_;
    bool has_initial_guess_ = false;
    std::vector<real_t> init_phi_, init_n_, init_p_;
    bool quantum_enabled_ = false;
    size_t max_iter_ = 100;   // raised from 50 for correct div(P) coupling
    real_t tol_ = 1e-25Q;
    real_t VT_ = 0.02585Q;
    SolverType poisson_solver_type_ = SolverType::DENSE_DIRECT;
    SolverType continuity_solver_type_ = SolverType::DENSE_DIRECT;
    bool use_newton_ = false;
    // Newton freeze flags (C档) — expose NewtonOptions::freeze_phi/n/p.
    bool newton_freeze_phi_ = false;
    bool newton_freeze_n_ = false;
    bool newton_freeze_p_ = false;
    // Newton options
    real_t newton_damping_ = 1.0Q;
    real_t newton_min_damping_ = 0.01Q;
    bool newton_use_line_search_ = true;
    size_t newton_line_search_max_ = 10;
    bool newton_use_log_damping_ = false;
    bool newton_use_log_space_ = false;
    real_t newton_jacobian_reuse_threshold_ = 0.0Q;
    // Thermal coupling
    bool thermal_coupling_enabled_ = false;
    std::vector<real_t> thermal_conductivity_;
    real_t ambient_temperature_ = 300.0Q;
    std::map<size_t, real_t> thermal_bc_;
    // BTBT
    bool btbt_enabled_ = false;
    real_t btbt_A_ = 3.1e21Q;
    real_t btbt_B_ = 2.0e7Q;
    int btbt_D_ = 2;
    bool btbt_use_nonlocal_ = false;
    // Avalanche impact ionization (SI units; defaults = silicon, see
    // ImpactIonizationParams in gummel_solver.h)
    bool ii_enabled_ = false;
    real_t ii_A_n_ = 7.03e7Q;
    real_t ii_B_n_ = 1.231e8Q;
    real_t ii_A_p_ = 1.58e8Q;
    real_t ii_B_p_ = 2.036e8Q;
    // Dielectric breakdown (M7b, audit §22)
    bool bd_enabled_ = false;
    std::vector<char> bd_mask_;       // which nodes participate (dielectric) [npts]
    std::vector<real_t> E_bd_;        // per-node breakdown field [V/m] [npts]
    real_t sigma_bd_ = 1.0e-2Q;   // soft-breakdown leakage term [F/m^3] (A档)
    std::vector<char> bd_state_;      // 1 = node broken down (irreversible) [npts]
    bool bd_state_init_ = false;
    // Ferroelectric
    bool fe_enabled_ = false;
    std::vector<char> fe_mask_;
    real_t fe_alpha_ = -5.0e8Q;    // Landau alpha [m/F] for HfZrO (P1.2)
    real_t fe_beta_ = 1.5e10Q;     // Landau beta [m^5/(F*C^2)] (P1.2)
    // Ferroelectric model + Preisach params (M7c)
    int fe_model_ = 0;             // 0 = LK, 1 = PREISACH
    real_t fe_ps_ = 0.2Q;          // Preisach saturation polarization [C/m^2]
    real_t fe_ec_ = 1.0e9Q;        // Preisach coercive field [V/m]
    real_t fe_escale_ = 0.0Q;      // Preisach tanh width [V/m]; 0 => Ec (default)
    real_t fe_E_bi_ = 0.0Q;        // Internal/imprint field offset [V/m] (P2.1)
    real_t fe_eps_fe_ = 0.0Q;      // FE relative permittivity for depol (comments2.docx P3)
    real_t fe_nls_tau0_ = 1.0e-6Q; // NLS Merz tau0 [s] (P3)
    real_t fe_nls_E0_ = 2.0e9Q;    // NLS Merz E0 [V/m] (P3)
    real_t fe_nls_dt_ = 1.0e-6Q;   // NLS dwell time [s] (P3)
    std::vector<real_t> fe_play_state_;  // Preisach play-operator state, len npts
    // Authoritative vector P (3 components/node, interleaved [Px,Py,Pz]),
    // persistent across solve() calls (GummelSolver is rebuilt every solve();
    // without this, P is wiped and hysteresis vanishes). Layout: [3*idx+c].
    std::vector<real_t> fe_polarization_;
    bool fe_polarization_init_ = false;
    // Leakage current (PF/FN) (P2.2)
    bool leak_enabled_ = false;
    std::vector<char> leak_mask_;
    real_t leak_C_pf_ = 0.0Q, leak_B_pf_ = 0.0Q, leak_phi_t_ = 0.0Q;
    real_t leak_C_fn_ = 0.0Q, leak_B_fn_ = 0.0Q, leak_phi_b_ = 0.0Q;
    real_t leak_E_floor_ = 1.0e6Q;
    real_t leak_sigma_cap_ = 0.05Q;
    // Interface traps (Dit) + bulk oxide traps (P6)
    std::vector<char> trap_mask_;
    real_t trap_D_it_ = 0.0Q;       // interface trap density [cm^-2 eV^-1]
    real_t trap_E_t_ = 0.0Q;        // trap energy [eV] rel. intrinsic
    std::vector<real_t> Q_ot_;      // bulk oxide trap charge [C/m^3]
    // Cryo-CMOS
    real_t temperature_ = 300.0Q;
    StatisticsType statistics_type_ = StatisticsType::BOLTZMANN;
    MobilityModelType mobility_model_type_ = MobilityModelType::CONSTANT;
    // Transient
    bool transient_enabled_ = false;
    real_t transient_dt_ = 1.0e-12Q;
    real_t transient_t_final_ = 1.0e-9Q;
    real_t fe_gamma_ = 1.0e-8Q;
};

} // namespace tcad
