#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "density_gradient.h"
#include "mobility_model.h"
#include "statistics.h"
#include <vector>
#include <functional>

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

struct FerroelectricParams {
    bool enabled = false;
    std::vector<char> fe_mask;
    real_t alpha = -1.0e8Q;   // Landau alpha [m/F]
    real_t beta = 1.0e18Q;    // Landau beta [m^5/(F*C^2)]
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
    // Band-to-band tunneling
    BTBTParams btbt;
    // Ferroelectric polarization
    FerroelectricParams ferro;
    // Cryo-CMOS models
    StatisticsType statistics_type = StatisticsType::BOLTZMANN;
    MobilityModelType mobility_model_type = MobilityModelType::CONSTANT;
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
    void set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv);
    void set_bandgap(const std::vector<real_t>& Eg);

    // Set Dirichlet BC for n, p at contact nodes (indices -> values)
    void set_electron_bc(const std::map<size_t, real_t>& bc);
    void set_hole_bc(const std::map<size_t, real_t>& bc);

    // Forward material/BC settings to internal Poisson solver
    void set_poisson_dirichlet(const std::map<size_t, real_t>& bc) { poisson_.set_dirichlet(bc); }
    void set_permittivity(const std::vector<real_t>& eps) { poisson_.set_permittivity(eps); }
    void set_ferroelectric_gamma(real_t gamma) { poisson_.set_ferroelectric_gamma(gamma); }
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

private:
    Grid3D g_;
    GummelOptions opt_;
    PoissonSolver poisson_;
    DensityGradient dg_;

    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    std::map<size_t, real_t> n_bc_, p_bc_;

    std::vector<real_t> poisson_res_;
    std::vector<real_t> cont_res_;

    bool solve_continuity(const std::vector<real_t>& phi,
                          std::vector<real_t>& n,
                          std::vector<real_t>& p);

    // Build and solve electron continuity: div(Jn) = R
    bool solve_electron_density(const std::vector<real_t>& phi,
                                std::vector<real_t>& n,
                                const std::vector<real_t>& p);
    bool solve_hole_density(const std::vector<real_t>& phi,
                            const std::vector<real_t>& n,
                            std::vector<real_t>& p);

    // Bernoulli function for Scharfetter-Gummel
    static real_t bernoulli(real_t x);

    // Compute BTBT generation rate from electric field (Kane's model)
    void compute_btbt(const std::vector<real_t>& phi,
                      std::vector<real_t>& G_btbt) const;

    // Non-local BTBT: path-integral WKB tunneling probability
    void compute_nonlocal_btbt(const std::vector<real_t>& phi,
                               std::vector<real_t>& G_btbt) const;
};

} // namespace tcad
