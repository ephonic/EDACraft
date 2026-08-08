#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "density_gradient.h"
#include "mobility_model.h"
#include "statistics.h"
#include <vector>
#include <functional>
#include <memory>

namespace tcad {

// Continuity equation solver (simplified drift-diffusion)
// Solves for carrier densities n, p given potential phi and electric field
// For now, implemented on structured grid with Scharfetter-Gummel discretization

struct BTBTParams {
    real_t A_kane = 3.1e21Q;   // Kane A coefficient [cm^-3 s^-1 V^-D] -> scaled to m^-3
    // Phase 3.4 fix (audit §12.4): the field |E| in compute_btbt is in V/m
    // (phi in volts, dx in metres), so B_kane must be in V/m to match.
    // The previous default 2.0e7 was the Si Kane B in the V/cm convention
    // (Hurkx 1992: 1.5e7..4e7 V/cm) mistakenly used as a V/m value — that
    // made exp(-B/|E|) ~1 at typical on-state fields (E=1e9 V/m gave
    // exp(-0.02)=0.98, i.e. the model reported almost no barrier).  2.0e9 V/m
    // is the SI-equivalent of the published 2.0e7 V/cm value.
    real_t B_kane = 2.0e9Q;    // Kane B coefficient [V/m] for Si (was 2.0e7 — unit bug)
    int D = 2;                  // Exponent: 2 for direct, 2.5 for indirect tunneling
    bool enabled = false;
    // Non-local (path-integral WKB) tunneling:
    bool use_nonlocal = false;
    real_t tunnel_path_frac = 0.5Q; // Fraction of grid spacing to search (source side)
    size_t wkb_npts = 64;            // Number of points for WKB numerical integration
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
    std::vector<char> fe_mask;
    real_t alpha = -5.0e8Q;   // Landau alpha [m/F] (P1.2)
    real_t beta = 1.5e10Q;    // Landau beta [m^5/(F*C^2)] (P1.2)
    // Preisach parameters. For PREISACH, Escale is the play-operator tanh
    // width. For SENTAURUS_PREISACH it is 1/w in SDevice Eq. 986; given Pr,
    // use Escale=2*Ec/log((Ps+Pr)/(Ps-Pr)).
    // Ps = saturation polarization [C/m^2], Ec = coercive field [V/m],
    // Escale = tanh output width [V/m] (0 => Escale=Ec for correct loop shape;
    // <Ec lets |P| approach Ps on a monotonic ramp but steepens the loop).
    // Defaults are typical HfZrO.
    FerroelectricModel model = FerroelectricModel::LANDAU_KHALATNIKOV;
    real_t ps = 0.2Q;         // saturation polarization [C/m^2]
    real_t ec = 1.0e9Q;       // coercive field [V/m]
    real_t escale = 0.0Q;     // tanh width [V/m]; 0 => Ec (loop-shape default)
    real_t E_bi = 0.0Q;       // internal/imprint field offset [V/m] (P2.1); 0 => symmetric
    real_t eps_fe = 0.0Q;     // FE permittivity for depol (comments2.docx P3); 0 => off
    // NLS (P3, model==2): Merz tau(E) = tau0*exp(E0/|E|).
    real_t nls_tau0 = 1.0e-6Q;   // characteristic switching time [s]
    real_t nls_E0 = 2.0e9Q;      // Merz activation field [V/m]
    real_t nls_dt = 1.0e-6Q;     // effective dwell time per bias step [s]
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
    real_t C_pf = 0.0Q;           // PF conductivity prefactor [S/m]
    real_t B_pf = 0.0Q;           // PF barrier coefficient [(V/m)^(1/2)]
    real_t phi_t = 0.0Q;          // PF trap ionization energy [eV]
    real_t C_fn = 0.0Q;           // FN current prefactor [A/V^2]
    real_t B_fn = 0.0Q;           // FN exponent coefficient [V/m·eV^(-3/2)]
    real_t phi_b = 0.0Q;          // FN barrier height [eV]
    real_t E_floor = 1.0e6Q;      // below this |E| [V/m] leakage is negligible
    real_t sigma_cap = 0.05Q;     // total conductivity cap [S/m]
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
    bool enabled = false;
    real_t A_n = 7.03e7Q;     // electron ionization coefficient A [1/m]
    real_t B_n = 1.231e8Q;    // electron ionization coefficient B [V/m]
    real_t A_p = 1.58e8Q;     // hole ionization coefficient A [1/m]
    real_t B_p = 2.036e8Q;    // hole ionization coefficient B [V/m]
    real_t E_floor = 1.0e5Q;  // below this |E| [V/m] alpha is negligible -> 0
};

struct AugerParams {
    bool enabled = false;
    // Sentaurus Si defaults (MaterialDB): Cn=2.8e-31, Cp=9.9e-32 [cm^6/s]
    // Converted to SI: multiply by 1e-12 (cm^6 → m^6)
    real_t Cn = 2.8e-43Q;     // electron Auger coefficient [m^6/s]
    real_t Cp = 9.9e-44Q;     // hole Auger coefficient [m^6/s]
};

struct GummelOptions {
    size_t max_iter = 50;
    real_t poisson_tol = 1e-25Q;
    real_t continuity_tol = 1e-25Q;
    real_t damping = 1.0Q;        // Uniform linear damping for phi updates (1.0 = no damping)
    real_t cont_damping = 0.5Q;   // Damping for n/p continuity updates
    bool enable_quantum = true;
    real_t VT = 0.02585Q;  // Thermal voltage [V]
    real_t temperature = 300.0Q; // Temperature [K]
    SolverType poisson_solver = SolverType::DENSE_DIRECT;
    SolverType continuity_solver = SolverType::DENSE_DIRECT;
    bool use_log_damping = true; // Use geometric (log-space) damping for n/p
    real_t log_damping_threshold = 10.0Q; // Ratio threshold to trigger log-damping
    // Phi log-damping: cap extreme swings after uniform damping
    real_t phi_log_damp_threshold = 0.3Q; // in units of VT
    // Adaptive damping: automatically reduce phi damping when oscillation detected
    bool adaptive_damping = true;
    real_t min_damping = 0.05Q;
    size_t oscillation_window = 3; // consecutive rising residuals to trigger reduction
    // Inner continuity iterations: fix phi, solve n/p multiple times before next Poisson
    size_t inner_iterations = 1;
    bool enable_phi_freezing = true;
    // Warm-up mode (Gummel->Newton cascade): break out of the iteration at
    // the FIRST detected limit cycle instead of burning damping retries to
    // max_iter — a cycle means the fixed-point map has an unstable fixed
    // point, which is precisely what the Newton polish is for.  Normal
    // (contracting) warm-up progress is never interrupted.
    bool exit_on_limit_cycle = false;
    // P0-3: acceptance gate on the TRUE relative Poisson residual
    // ||A*phi - rhs||/||rhs|| of a permanently phi-frozen (limit-cycle) exit
    // state.  A frozen state is only reported converged below this gate;
    // otherwise it is honestly rejected as non-converged.  Converged sweeps
    // typically reach O(1e-6); 1e-3 is a deliberately strict-yet-attainable
    // gate for the cycle-mean state.
    real_t frozen_residual_gate = 1e-3Q;
    // Band-to-band tunneling
    BTBTParams btbt;
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
    real_t transient_dt = 1.0e-12Q;
    std::vector<real_t> n_prev, p_prev;  // carrier densities at previous time step
};

class GummelSolver {
public:
    GummelSolver(const Grid3D& grid, const GummelOptions& opt = {});

    // Set material properties per grid point
    void set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p);
    void set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p);
    void set_optical_generation(const std::vector<real_t>& G_opt);
    void set_doping(const std::vector<real_t>& Nd_minus_Na);
    void set_charge_volume_fraction(const std::vector<real_t>& fraction) {
        poisson_.set_charge_volume_fraction(fraction);
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

    // Main solve: self-consistent Poisson + Continuity (+ optional DG)
    // On input, phi, n, p should contain initial guesses
    bool solve(std::vector<real_t>& phi,
               std::vector<real_t>& n,
               std::vector<real_t>& p);

    // Access residuals history
    const std::vector<real_t>& poisson_residuals() const { return poisson_res_; }
    const std::vector<real_t>& continuity_residuals() const { return cont_res_; }

    // Convergence-honesty diagnostics (P0-3 fix).
    // True relative Poisson equation residual ||A*phi - rhs|| / ||rhs|| at the
    // returned state, computed after the Gummel loop exits (converged or not);
    // -1 means "not computed" (early failure return).
    real_t poisson_residual_final() const { return poisson_residual_final_; }
    // True if the limit-cycle stabiliser permanently pinned phi during the
    // last solve() (such a state only reports converged when the true update
    // norm at freeze time was already below poisson_tol).
    bool phi_was_frozen() const { return phi_was_frozen_; }
    // On-demand true Poisson residual at an externally supplied state (used by
    // the hybrid Gummel->Newton path to score the Newton result against the
    // Gummel Poisson operator).
    real_t compute_poisson_residual(const std::vector<real_t>& phi,
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
        compute_btbt(phi, G_btbt);
    }

    void evaluate_impact_ionization(
        const std::vector<real_t>& phi,
        const std::vector<real_t>& n,
        const std::vector<real_t>& p,
        std::vector<real_t>& G_ii) const {
        compute_impact_ionization(phi, n, p, G_ii);
    }

private:
    Grid3D g_;
    GummelOptions opt_;
    PoissonSolver poisson_;
    DensityGradient dg_;
    // Persistent continuity linear solvers (lazily created) so the PETSc
    // factorization cache (Mat/KSP/symbolic) is reused across Gummel iters
    // for BOTH electron and hole solves, not just the Poisson solve.
    std::unique_ptr<LinearSolver> cont_e_solver_, cont_h_solver_;
    // DG quantum potential damping (under-relaxation to stabilize the Qn->n->Qn
    // feedback loop that otherwise prevents Gummel convergence with DG).
    std::vector<real_t> Qn_prev_, Qp_prev_;

    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    std::map<size_t, real_t> n_bc_, p_bc_;

    std::vector<real_t> poisson_res_;
    std::vector<real_t> cont_res_;

    // Convergence-honesty state (P0-3 fix), reset at the top of each solve().
    real_t poisson_residual_final_ = -1.0Q;  // -1 = not computed
    bool phi_was_frozen_ = false;

    bool solve_continuity(const std::vector<real_t>& phi,
                          std::vector<real_t>& n,
                          std::vector<real_t>& p);

    // Build and solve electron continuity: div(Jn) = R
    bool solve_electron_density(const std::vector<real_t>& phi,
                                 std::vector<real_t>& n,
                                 const std::vector<real_t>& p,
                                 const std::vector<real_t>* transport_phi);
    bool solve_hole_density(const std::vector<real_t>& phi,
                             const std::vector<real_t>& n,
                             std::vector<real_t>& p,
                             const std::vector<real_t>* transport_phi);

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
                                   std::vector<real_t>& G_ii) const;

    // Non-local BTBT: path-integral WKB tunneling probability
    void compute_nonlocal_btbt(const std::vector<real_t>& phi,
                               std::vector<real_t>& G_btbt) const;
};

} // namespace tcad
