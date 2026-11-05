#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "density_gradient.h"
#include "mobility_model.h"
#include "statistics.h"
#include "nonlinear_history.h"
#include <vector>
#include <functional>
#include <memory>

namespace tcad {

// Continuity equation solver (simplified drift-diffusion)
// Solves for carrier densities n, p given potential phi and electric field
// For now, implemented on structured grid with Scharfetter-Gummel discretization

struct BTBTParams {
    real_t A_kane = TCAD_CONST(3.1e21);   // Kane A coefficient [cm^-3 s^-1 V^-D] -> scaled to m^-3
    // Phase 3.4 fix (audit §12.4): the field |E| in compute_btbt is in V/m
    // (phi in volts, dx in metres), so B_kane must be in V/m to match.
    // The previous default 2.0e7 was the Si Kane B in the V/cm convention
    // (Hurkx 1992: 1.5e7..4e7 V/cm) mistakenly used as a V/m value — that
    // made exp(-B/|E|) ~1 at typical on-state fields (E=1e9 V/m gave
    // exp(-0.02)=0.98, i.e. the model reported almost no barrier).  2.0e9 V/m
    // is the SI-equivalent of the published 2.0e7 V/cm value.
    real_t B_kane = TCAD_CONST(2.0e9);    // Kane B coefficient [V/m] for Si (was 2.0e7 — unit bug)
    real_t D = TCAD_CONST(2.0);            // Exponent: 2 for direct, 2.5 for indirect tunneling
    // 0 = |grad(phi)|, 1 = |Ex|, 2 = |Ey|, 3 = |Ez|.  The component modes
    // support Sentaurus-style local-Hurkx TFET calibration where the junction
    // path field is a better proxy than the total gate-normal electrostatic
    // field.
    int field_mode = 0;
    // Optional high-field cap [V/m] for local BTBT field evaluation.  <=0 keeps
    // the raw local field.  This is a calibrated local-Hurkx compatibility
    // control for sharp-grid TFET junctions where a single-node field spike can
    // dominate the volume integral.
    real_t field_cap = TCAD_CONST(0.0);
    // Optional calibrated field-shape correction for Sentaurus-Hurkx replay:
    // E_eff = E * (max(E,E_floor)/field_ref)^field_alpha.  field_alpha=0 keeps
    // the original Kane law.  Negative alpha reduces high-field over-slope.
    real_t field_alpha = TCAD_CONST(0.0);
    real_t field_ref = TCAD_CONST(1.0e8);
    // Optional multiplier for the BTBT source inserted into the carrier
    // continuity equations. It does not change the reported G_btbt array,
    // which remains the physical volumetric generation for Sentaurus
    // IntegratedBand2BandGeneration comparisons.
    real_t continuity_scale = TCAD_CONST(1.0);
    bool enabled = false;
    // Non-local (path-integral WKB) tunneling:
    bool use_nonlocal = false;
    // Maximum non-local path length as a fraction of the simulated x span.
    // A value <=0 disables this additional cap; the physical cap remains
    // min(2*Eg/qE, available distance to the nearer x boundary).
    real_t tunnel_path_frac = TCAD_CONST(0.5);
    // Number of Simpson segments for WKB numerical integration.  The solver
    // rounds odd values up internally because Simpson's rule requires an even
    // segment count.
    size_t wkb_npts = 64;
    // Effective tunneling mass ratio m_t/m0 for the WKB barrier integral
    // (M2 audit, 2026-09-18).  The generation uses the Kane-consistent
    // prefactor A_kane * E^D (same parameters and cm^-3 -> m^-3 conversion
    // as the local model) times exp(-2*Theta), so calibrated local
    // parameters transfer via the mapping B_eff = (4/3)*sqrt(2*m_t)*Eg^1.5
    // / (hbar*q): m_t = 0.25 * (B/B_eff(0.25))^2.
    real_t nonlocal_mass = TCAD_CONST(0.25);
};

// Ferroelectric model selector (M7c). LANDAU_KHALATNIKOV is the legacy cubic
// alpha*P + beta*P^3 = E path; PREISACH is the classical scalar Preisach
// (play-operator) model parameterised directly by Ps and Ec. Mirrors the
// MobilityModelType string->int mapping pattern (simulator.py:333).
enum class FerroelectricModel {
    LANDAU_KHALATNIKOV = 0,
    PREISACH = 1,
    NLS = 2,   // Nucleation-Limited Switching, Merz-law tau(E) (P3)
    SENTAURUS_PREISACH = 3, // Ps/Pr/Fc-compatible tanh branches (SDevice Eq. 986)
};

struct FerroelectricParams {
    bool enabled = false;
    // Numerical continuation keeps bound charge but consumes no FE dwell/history.
    bool update_state = true;
    std::vector<char> fe_mask;
    real_t alpha = -TCAD_CONST(5.0e8);   // Landau alpha [m/F] (P1.2)
    real_t beta = TCAD_CONST(1.5e10);    // Landau beta [m^5/(F*C^2)] (P1.2)
    // Preisach parameters. For PREISACH, Escale is the play-operator tanh
    // width. For SENTAURUS_PREISACH it is 1/w in SDevice Eq. 986; given Pr,
    // use Escale=2*Ec/log((Ps+Pr)/(Ps-Pr)).
    // Ps = saturation polarization [C/m^2], Ec = coercive field [V/m],
    // Escale = tanh output width [V/m] (0 => Escale=Ec for correct loop shape;
    // <Ec lets |P| approach Ps on a monotonic ramp but steepens the loop).
    // Defaults are typical HfZrO.
    FerroelectricModel model = FerroelectricModel::LANDAU_KHALATNIKOV;
    real_t ps = TCAD_CONST(0.2);         // saturation polarization [C/m^2]
    real_t ec = TCAD_CONST(1.0e9);       // coercive field [V/m]
    real_t escale = TCAD_CONST(0.0);     // tanh width [V/m]; 0 => Ec (loop-shape default)
    real_t E_bi = TCAD_CONST(0.0);       // internal/imprint field offset [V/m] (P2.1); 0 => symmetric
    real_t eps_fe = TCAD_CONST(0.0);     // FE permittivity for depol (comments2.docx P3); 0 => off
    // NLS (P3, model==2): Merz tau(E) = tau0*exp(E0/|E|).
    real_t nls_tau0 = TCAD_CONST(1.0e-6);   // characteristic switching time [s]
    real_t nls_E0 = TCAD_CONST(2.0e9);      // Merz activation field [V/m]
    real_t nls_dt = TCAD_CONST(1.0e-6);     // effective dwell time per bias step [s]
    // Polar axis for the scalar FE models (Preisach / NLS) and for the LK
    // built-in field + depolarization drive: 0 = x, 1 = y, 2 = z. The
    // built-in FeFET template stacks gate/FE/oxide/channel along Z, so
    // axis 2 is required there; default 0 reproduces the legacy x-only
    // behavior bit-for-bit (1D x-directed tests).
    int polar_axis = 0;
};

// Leakage current through the ferroelectric/insulator stack (P2.2).
// Poole-Frenkel (PF) and Fowler-Nordheim (FN) emission provide a field-dependent
// conventional-current path across the dielectric.  It is evaluated on mesh
// edges after the electrostatic solve and exposed as Jleak_x/y/z [A/m^2].
// It is not inserted into Poisson, whose RHS is charge density.
//
//   PF:  J = C_pf * |E| * exp( -B_pf * sqrt(phi_t / |E|) )     trap-assisted
//   FN:  J = C_fn * |E|^2 * exp( -B_fn * phi_b^(3/2) / |E| )   direct tunneling
// C_pf is an SI conductivity prefactor [S/m]; C_fn is an FN current
// prefactor [A/V^2].
struct LeakageParams {
    bool enabled = false;
    std::vector<char> mask;       // nodes that carry leakage [npts] (1 = leaky)
    real_t C_pf = TCAD_CONST(0.0);           // PF conductivity prefactor [S/m]
    real_t B_pf = TCAD_CONST(0.0);           // PF barrier coefficient [(V/m)^(1/2)]
    real_t phi_t = TCAD_CONST(0.0);          // PF trap ionization energy [eV]
    real_t C_fn = TCAD_CONST(0.0);           // FN current prefactor [A/V^2]
    real_t B_fn = TCAD_CONST(0.0);           // FN exponent coefficient [V/m·eV^(-3/2)]
    real_t phi_b = TCAD_CONST(0.0);          // FN barrier height [eV]
    real_t E_floor = TCAD_CONST(1.0e6);      // below this |E| [V/m] leakage is negligible
    real_t sigma_cap = TCAD_CONST(0.05);     // total conductivity cap [S/m]
};

// Avalanche impact ionization (Chynoweth ionization coefficient).
// alpha(E) = A * exp(-B / |E|)  [1/m], with |E| in [V/m] (SI — phi in V, dx in m).
// Generation rate (electron-hole pairs):  G_ii = (alpha_n*|Jn| + alpha_p*|Jp|) / q
// where Jn, Jp are the per-node Scharfetter-Gummel current densities [A/m^2].
// Defaults are silicon (Chynoweth 1959 / Overstraeten-De Man 1970):
//   electrons: A_n = 7.03e5 /cm -> 7.03e7 /m,  B_n = 1.231e6 V/cm -> 1.231e8 V/m
//   holes:     A_p = 1.58e6 /cm -> 1.58e8 /m,  B_p = 2.036e6 V/cm -> 2.036e8 V/m
// (All four defaults are pre-converted to SI so no runtime scaling is needed.)
struct ImpactIonizationParams {
    int driving = 0; // 0 ElectricField (default), 1 GradQuasiFermi
    real_t refdens_n = TCAD_CONST(0.0), refdens_p = TCAD_CONST(0.0);
    bool enabled = false;
    real_t A_n = TCAD_CONST(7.03e7);     // electron ionization coefficient A [1/m]
    real_t B_n = TCAD_CONST(1.231e8);    // electron ionization coefficient B [V/m]
    real_t A_p = TCAD_CONST(1.58e8);     // hole ionization coefficient A [1/m]
    real_t B_p = TCAD_CONST(2.036e8);    // hole ionization coefficient B [V/m]
    real_t E_floor = TCAD_CONST(1.0e5);  // below this |E| [V/m] alpha is negligible -> 0
};

struct HighFieldParams {
    bool enabled = false;
    // High-field velocity saturation (Sentaurus HighFieldSaturation).
    // Caugy-Thomas form applied per SG edge:
    //   mu(F) = mu_low / (1 + (mu_low*F/vsat)^beta)^(1/beta)
    // with F the edge driving force.  Default vsat are the Sentaurus Si
    // MaterialDB values (1.07e7 / 8.37e6 cm/s -> SI); beta defaults of
    // 2.0 (electrons) and 1.0 (holes) follow the Caugy-Thomas convention.
    real_t vsat_n = TCAD_CONST(1.07e5);   // [m/s] electron saturation velocity
    real_t vsat_p = TCAD_CONST(8.37e4);   // [m/s] hole saturation velocity
    real_t beta_n = TCAD_CONST(2.0);
    real_t beta_p = TCAD_CONST(1.0);
    // Driving force: 0 = |grad(quasi-Fermi potential)| along the edge
    // (Sentaurus GradQuasiFermi, the robust default); 1 = |E| from the
    // transport potential gradient.
    real_t refdens_n = TCAD_CONST(0.0), refdens_p = TCAD_CONST(0.0);
    int driving = 0;
    bool quasi_fermi_at_contacts = true;
    real_t low_field_cutoff = TCAD_CONST(0.0); // [V/m], zero preserves continuous HFS
};

struct AugerParams {
    bool enabled = false;
    // Sentaurus Si defaults (MaterialDB): Cn=2.8e-31, Cp=9.9e-32 [cm^6/s]
    // Converted to SI: multiply by 1e-12 (cm^6 → m^6)
    real_t Cn = TCAD_CONST(2.8e-43);     // electron Auger coefficient [m^6/s]
    real_t Cp = TCAD_CONST(9.9e-44);     // hole Auger coefficient [m^6/s]
};

struct GummelOptions {
    size_t max_iter = 50;
    real_t poisson_tol = TCAD_CONST(1e-25);
    real_t continuity_tol = TCAD_CONST(1e-25);
    real_t damping = TCAD_CONST(1.0);        // Uniform linear damping for phi updates (1.0 = no damping)
    real_t cont_damping = TCAD_CONST(0.5);   // Damping for n/p continuity updates
    bool enable_quantum = true;
    real_t VT = TCAD_CONST(0.02585);  // Thermal voltage [V]
    real_t temperature = TCAD_CONST(300.0); // Temperature [K]
    SolverType poisson_solver = SolverType::DENSE_DIRECT;
    SolverType continuity_solver = SolverType::DENSE_DIRECT;
    bool use_log_damping = true; // Use geometric (log-space) damping for n/p
    real_t log_damping_threshold = TCAD_CONST(10.0); // Ratio threshold to trigger log-damping
    // Phi log-damping: cap extreme swings after uniform damping
    real_t phi_log_damp_threshold = TCAD_CONST(0.3); // in units of VT
    // Adaptive damping: automatically reduce phi damping when oscillation detected
    bool adaptive_damping = true;
    real_t min_damping = TCAD_CONST(0.05);
    size_t oscillation_window = 3; // consecutive rising residuals to trigger reduction
    // Inner continuity iterations: fix phi, solve n/p multiple times before next Poisson
    size_t inner_iterations = 1;
    bool record_nonlinear_history = false;
    bool enable_phi_freezing = true;
    // Warm-up mode (Gummel->Newton cascade): break out of the iteration at
    // the FIRST detected limit cycle instead of burning damping retries to
    // max_iter — a cycle means the fixed-point map has an unstable fixed
    // point, which is precisely what the Newton polish is for.  Normal
    // (contracting) warm-up progress is never interrupted.
    bool exit_on_limit_cycle = false;
    // Acceptance gate on the physical row-scaled Poisson and continuity
    // equation residuals of a permanently phi-frozen (limit-cycle) exit
    // state.  A frozen state is only reported converged below this gate;
    // otherwise it is honestly rejected as non-converged.  Converged sweeps
    // typically reach O(1e-6); 1e-3 is a deliberately strict-yet-attainable
    // gate for the cycle-mean state.
    real_t frozen_residual_gate = TCAD_CONST(1e-3);
    // Band-to-band tunneling
    BTBTParams btbt;
    // High-field velocity saturation
    HighFieldParams hfs;
    // Avalanche impact ionization
    ImpactIonizationParams ii;
    // Auger recombination
    AugerParams auger;
    // Ferroelectric polarization
    FerroelectricParams ferro;
    // Leakage current (Poole-Frenkel / Fowler-Nordheim) (P2.2)
    LeakageParams leakage;
    // Cryo-CMOS models
    StatisticsType statistics_type = StatisticsType::BOLTZMANN;
    MobilityModelType mobility_model_type = MobilityModelType::CONSTANT;
    // Stabilized Gummel (plan0728 §1.2): semi-implicit Boltzmann charge
    // linearization in the Poisson solve (fixed point unchanged, iteration
    // damped against depletion-edge overshoot cycles).
    bool boltzmann_lin = true;
    // Transient solve: backward Euler time stepping
    bool transient_enabled = false;
    real_t transient_dt = TCAD_CONST(1.0e-12);
    std::vector<real_t> n_prev, p_prev;  // carrier densities at previous time step
};

class GummelSolver {
public:
    GummelSolver(const Grid3D& grid, const GummelOptions& opt = {});

    // Set material properties per grid point
    void set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p);
    void set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p);
    void set_optical_generation(const std::vector<real_t>& G_opt);
    void set_btbt_weight(const std::vector<real_t>& weight);
    void set_doping(const std::vector<real_t>& Nd_minus_Na);
    void set_charge_volume_fraction(const std::vector<real_t>& fraction) {
        poisson_.set_charge_volume_fraction(fraction);
        legacy_carrier_widths_ = false;
        for (real_t v : fraction)
            if (v > TCAD_CONST(0.0) && v < TCAD_CONST(1.0)) legacy_carrier_widths_ = true;
    }
    void set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv);
    void set_bandgap(const std::vector<real_t>& Eg);

    // Set Dirichlet BC for n, p at contact nodes (indices -> values)
    void set_electron_bc(const std::map<size_t, real_t>& bc);
    void set_hole_bc(const std::map<size_t, real_t>& bc);

    // Forward material/BC settings to internal Poisson solver
    void set_poisson_dirichlet(const std::map<size_t, real_t>& bc) { poisson_.set_dirichlet(bc); }
    void set_ohmic_contacts(const std::set<size_t>& nodes,
                            const std::map<size_t, real_t>& EFn,
                            const std::map<size_t, real_t>& EFp,
                            real_t ni) {
        poisson_.set_ohmic_contacts(nodes, EFn, EFp, ni);
    }
    void set_permittivity(const std::vector<real_t>& eps) { poisson_.set_permittivity(eps); }
    void set_edge_permittivity(const std::vector<real_t>& x_plus,
                               const std::vector<real_t>& x_minus,
                               const std::vector<real_t>& y_plus,
                               const std::vector<real_t>& y_minus,
                               const std::vector<real_t>& z_plus,
                               const std::vector<real_t>& z_minus) {
        poisson_.set_edge_permittivity(x_plus, x_minus, y_plus, y_minus, z_plus, z_minus);
    }
    void set_ferroelectric_gamma(real_t gamma) { poisson_.set_ferroelectric_gamma(gamma); }
    // Ferroelectric model + Preisach params (M7c): forward to PoissonSolver.
    void set_ferroelectric_model(int model) { poisson_.set_ferroelectric_model(model); }
    void set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale) { poisson_.set_ferroelectric_preisach(ps, ec, escale); }
    const std::vector<real_t>& fe_play_state() const { return poisson_.fe_play_state(); }
    void set_fe_play_state(const std::vector<real_t>& s) { poisson_.set_fe_play_state(s); }
    // Dielectric breakdown (M7b): forward to internal PoissonSolver so the
    // assemble() leakage term applies in the Gummel path too.
    void set_breakdown_state(const std::vector<char>& bd_state, real_t sigma_bd) {
        poisson_.set_breakdown_state(bd_state, sigma_bd);
    }
    // Interface/bulk trap passthrough (P6): forward to internal PoissonSolver.
    void set_interface_traps(const std::vector<char>& mask, real_t D_it, real_t E_t) {
        poisson_.set_interface_traps(mask, D_it, E_t);
    }
    void set_oxide_traps(const std::vector<real_t>& Q_ot) {
        poisson_.set_oxide_traps(Q_ot);
    }
    // Persistent vector P passthrough (3 components per node, interleaved):
    // DeviceSimulator injects the previous sweep point's P before solve(),
    // reads it back after, giving cross-bias memory for hysteresis.
    void set_fe_polarization(const std::vector<real_t>& P) { poisson_.set_fe_polarization(P); }
    const std::vector<real_t>& fe_polarization() const { return poisson_.fe_polarization(); }

    // Solver configuration
    void set_poisson_solver_type(SolverType type);
    void set_continuity_solver_type(SolverType type);
    void set_density_gradient_coefficients(real_t bn, real_t bp) {
        dg_.set_coefficients(bn, bp);
        Qn_prev_.clear();
        Qp_prev_.clear();
    }
    void set_density_gradient_silicon_multivalley(bool enable,
                                                  real_t ml, real_t mt,
                                                  size_t subbands) {
        dg_.set_silicon_multivalley(enable, ml, mt, subbands);
        Qn_prev_.clear();
        Qp_prev_.clear();
    }
    void set_density_gradient_interface_distance_factor(real_t factor) {
        dg_.set_interface_distance_factor(factor);
        Qn_prev_.clear();
        Qp_prev_.clear();
    }
    void set_density_gradient_potential_form(bool enable) {
        dg_.set_potential_form(enable);
        Qn_prev_.clear();
        Qp_prev_.clear();
    }
    void set_density_gradient_step_boundary(
        bool enable, real_t electron_barrier_eV, real_t hole_barrier_eV,
        real_t electron_barrier_mass, real_t hole_barrier_mass,
        real_t electron_gamma, real_t hole_gamma,
        real_t electron_theta, real_t hole_theta) {
        dg_.set_step_boundary(enable, electron_barrier_eV, hole_barrier_eV,
                              electron_barrier_mass, hole_barrier_mass,
                              electron_gamma, hole_gamma,
                              electron_theta, hole_theta);
        Qn_prev_.clear();
        Qp_prev_.clear();
    }

    // Main solve: self-consistent Poisson + Continuity (+ optional DG)
    // On input, phi, n, p should contain initial guesses
    bool solve(std::vector<real_t>& phi,
               std::vector<real_t>& n,
               std::vector<real_t>& p);

    // Access residuals history
    const std::vector<real_t>& poisson_residuals() const { return poisson_res_; }
    const std::vector<real_t>& continuity_residuals() const { return cont_res_; }
    const std::vector<std::vector<real_t>>& nonlinear_samples() const { return nonlinear_samples_; }
    real_t electron_update_final() const { return electron_update_final_; }
    real_t hole_update_final() const { return hole_update_final_; }

    // Quantum potentials used by the final continuity solve.  Density-gradient
    // feedback is deliberately under-relaxed, so these generally differ from
    // an undamped Q(n,p) recomputation at the returned carrier state.  Current
    // post-processing must use the same transport potential as the discrete
    // continuity equation to preserve edge-current/KCL consistency.
    const std::vector<real_t>& transport_quantum_n() const { return Qn_prev_; }
    const std::vector<real_t>& transport_quantum_p() const { return Qp_prev_; }
    void set_transport_quantum_state(const std::vector<real_t>& Qn,
                                     const std::vector<real_t>& Qp) {
        if (Qn.size() != g_.npts() || Qp.size() != g_.npts())
            throw std::invalid_argument(
                "transport quantum state size mismatch");
        for (real_t value : Qn)
            if (!isfinite_q(value))
                throw std::invalid_argument("transport quantum state must be finite");
        for (real_t value : Qp)
            if (!isfinite_q(value))
                throw std::invalid_argument("transport quantum state must be finite");
        Qn_prev_ = Qn;
        Qp_prev_ = Qp;
    }

    // Convergence-honesty diagnostics (P0-3 fix).
    // Maximum physical Poisson row residual scaled by VT stiffness and
    // unsigned charge (without the artificial Gummel linearization) at the
    // returned state, computed after the Gummel loop exits (converged or not);
    // -1 means "not computed" (early failure return).
    real_t poisson_residual_final() const { return poisson_residual_final_; }
    // Carrier-weighted relative mismatch between the undamped Q(n,p) at the
    // returned state and the lagged transport Q used by the final continuity
    // solve. Local sqrt(n/(n+p)) and sqrt(p/(n+p)) weights prevent a
    // numerically noisy minority species from masking the active DG channel.
    // Zero for a classical solve; -1 means no valid diagnostic was produced.
    real_t quantum_residual_final() const { return quantum_residual_final_; }
    // True if the limit-cycle stabiliser permanently pinned phi during the
    // last solve() (such a state only reports converged when the true update
    // norm at freeze time was already below poisson_tol).
    bool phi_was_frozen() const { return phi_was_frozen_; }
    // On-demand true Poisson residual at an externally supplied state (used by
    // the hybrid Gummel->Newton path to score the Newton result against the
    // Gummel Poisson operator).
    real_t compute_poisson_residual(const std::vector<real_t>& phi,
                                    const std::vector<real_t>& n,
                                    const std::vector<real_t>& p, bool isolated = false,
                                    bool scaled = true);
    // Assemble both continuity equations at this state without solving or
    // committing any carrier/Q updates. Uses the current transport Q cache.
    std::pair<real_t,real_t> compute_continuity_residuals(const std::vector<real_t>& phi,
                                       const std::vector<real_t>& n,
                                       const std::vector<real_t>& p);
    // Audit a specified physical Q pair without committing transport state.
    // The original pair (including empty caches) is restored on exceptions.
    std::pair<real_t,real_t> compute_quantum_continuity_residuals(
        const std::vector<real_t>& phi, const std::vector<real_t>& n,
        const std::vector<real_t>& p, const std::vector<real_t>& Qn,
        const std::vector<real_t>& Qp);
    real_t compute_continuity_residual(const std::vector<real_t>& phi,
                                      const std::vector<real_t>& n,
                                      const std::vector<real_t>& p);

    // Re-solve Poisson only (phi ← solve(∇²φ = -ρ(n,p)/ε)).
    // Used after Newton polish to ensure phi is consistent with the
    // converged n,p, fixing wrong edge currents from phi-n mismatch.
    bool recompute_poisson(std::vector<real_t>& phi,
                           const std::vector<real_t>& n,
                           const std::vector<real_t>& p);

    // Evaluate the configured BTBT model on an arbitrary potential field.
    // This post-processing entry point exposes the same source term injected
    // into both continuity equations, so callers can inspect/validate
    // Band2BandGeneration directly instead of inferring it from contact-pinned
    // extrema of n or p.  Output units are [m^-3 s^-1].
    void evaluate_btbt_generation(const std::vector<real_t>& phi,
                                  std::vector<real_t>& G_btbt) const {
        // Publish only a complete result. This also permits phi and G_btbt to
        // refer to the same vector without erasing the input before evaluation.
        std::vector<real_t> candidate;
        compute_btbt(phi, candidate);
        G_btbt.swap(candidate);
    }

    void evaluate_impact_ionization(
        const std::vector<real_t>& phi,
        const std::vector<real_t>& n,
        const std::vector<real_t>& p,
        std::vector<real_t>& G_ii,
        const std::vector<real_t>* transport_Qn = nullptr,
        const std::vector<real_t>* transport_Qp = nullptr) const {
        compute_impact_ionization(phi, n, p, G_ii, transport_Qn, transport_Qp);
    }

private:
    // Equation (248) differs from equation (247) only for Fermi statistics.
    // Under Boltzmann statistics use the algebraically equivalent density
    // map so the discrete nonuniform-grid operator obeys the same chain rule
    // instead of creating a mesh-dependent pseudo-physics branch.
    bool use_potential_form_pde() const {
        return dg_.potential_form_enabled() &&
               opt_.statistics_type == StatisticsType::FERMI_DIRAC;
    }

    Grid3D g_;
    bool legacy_carrier_widths_ = false;
    real_t active_carrier_width(size_t idx, size_t j, size_t k, int axis,
                               const std::vector<real_t>& mobility) const;
    GummelOptions opt_;
    PoissonSolver poisson_;
    DensityGradient dg_;
    // Persistent continuity linear solvers (lazily created) so the PETSc
    // factorization cache (Mat/KSP/symbolic) is reused across Gummel iters
    // for BOTH electron and hole solves, not just the Poisson solve.
    std::unique_ptr<LinearSolver> cont_e_solver_, cont_h_solver_;
    // Once the honest residual gate proves that the selected iterative
    // backend loses accuracy on this fixed narrow-band grid, avoid retrying
    // the same unsuitable backend at every nonlinear iteration.
    bool cont_e_use_banded_direct_ = false;
    bool cont_h_use_banded_direct_ = false;
    // DG quantum potential damping (under-relaxation to stabilize the Qn->n->Qn
    // feedback loop that otherwise prevents Gummel convergence with DG).
    std::vector<real_t> Qn_prev_, Qp_prev_;

    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> btbt_weight_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    std::map<size_t, real_t> n_bc_, p_bc_;

    std::vector<real_t> poisson_res_;
    std::vector<real_t> cont_res_;
    std::vector<std::vector<real_t>> nonlinear_samples_;

    // Convergence-honesty state (P0-3 fix), reset at the top of each solve().
    real_t poisson_residual_final_ = -TCAD_CONST(1.0);  // -1 = not computed
    real_t quantum_residual_final_ = -TCAD_CONST(1.0);
    // Last accepted Gummel block-update norms, both normalized by the total
    // mobile-charge scale.  The hybrid Newton hand-off uses these to freeze a
    // genuinely settled minority block instead of exciting its near-null
    // log-density direction.
    real_t electron_update_final_ = -TCAD_CONST(1.0);
    real_t hole_update_final_ = -TCAD_CONST(1.0);
    bool phi_was_frozen_ = false;

    bool solve_continuity(const std::vector<real_t>& phi,
                          std::vector<real_t>& n,
                          std::vector<real_t>& p,
                          real_t quantum_mix_scale);

    // Build and solve electron continuity: div(Jn) = R
    bool solve_electron_density(const std::vector<real_t>& phi,
                                 std::vector<real_t>& n,
                                 const std::vector<real_t>& p,
                                 const std::vector<real_t>* transport_phi,
                                 real_t* audit_residual = nullptr);
    bool solve_hole_density(const std::vector<real_t>& phi,
                             const std::vector<real_t>& n,
                             std::vector<real_t>& p,
                             const std::vector<real_t>* transport_phi,
                             real_t* audit_residual = nullptr);

    // Bernoulli function for Scharfetter-Gummel
    static real_t bernoulli(real_t x);

    // Compute BTBT generation rate from electric field (Kane's model)
    void compute_btbt(const std::vector<real_t>& phi,
                      std::vector<real_t>& G_btbt) const;

    // Compute avalanche impact-ionization generation rate per node [m^-3 s^-1]
    // from the Scharfetter-Gummel edge currents.  alpha(E)=A*exp(-B/|E|),
    // G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q, accumulated to both endpoints of
    // each interior edge (volume-weighted by 1/dx).
    void compute_impact_ionization(const std::vector<real_t>& phi,
                                   const std::vector<real_t>& n,
                                   const std::vector<real_t>& p,
                                   std::vector<real_t>& G_ii,
                                   const std::vector<real_t>* transport_Qn = nullptr,
                                   const std::vector<real_t>* transport_Qp = nullptr) const;

    // Non-local BTBT: path-integral WKB tunneling probability
    void compute_nonlocal_btbt(const std::vector<real_t>& phi,
                               std::vector<real_t>& G_btbt) const;
};

} // namespace tcad
