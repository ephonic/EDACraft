#pragma once

#include "math_types.h"
#include "poisson_solver.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include "statistics.h"
#include <vector>
#include <map>

namespace tcad {

struct NewtonOptions {
    size_t max_iter = 30;
    real_t tol = 1e-12Q;
    real_t abs_tol = 1e-20Q;
    real_t damping = 1.0Q;
    real_t min_damping = 0.01Q;
    bool use_line_search = true;
    size_t line_search_max = 10;
    SolverType linear_solver = SolverType::BICGSTAB_ILU0;
    real_t linear_tol = 1e-20Q;
    bool verbose = false;
    bool enable_quantum = false;
    bool use_log_damping = false;
    real_t jacobian_reuse_threshold = 0.0Q;  // reuse if residual drops by >this factor (0=disabled)

    // Log-space density solve (audit §18 / M6b).  When true the carrier blocks
    // of the Newton state vector carry u=log(n), v=log(p) instead of n, p.
    // This keeps the Jacobian conditioning bounded across the ~1e47 carrier
    // dynamic range (depletion 1e3 -> inversion 1e26 in cryo/FE devices):
    //   - SG flux / Poisson / SRH residuals are evaluated on the linearised
    //     densities n=exp(u), p=exp(v), so the physics is identical to the
    //     linear-space path.
    //   - Jacobian carrier columns get the chain-rule factor dF/du = dF/dn * n
    //     (and dF/dv = dF/dp * p), turning a 1e22-wide diagonal into O(1).
    //   - Dirichlet carrier BC rows become u - log(n_bc); insulator rows become
    //     u - log(1e-30); the BE transient term becomes (exp(u)-exp(u_prev))/dt.
    //   - Newton updates are additive in log-space (u += du), which is
    //     equivalent to the exponential update but cleaner — no division by the
    //     current density (the use_log_damping path divides dx[n]/x[n], which
    //     blows up when x[n] underflows).
    // Gummel stays in linear space and feeds a linear-space initial guess;
    // solve() converts phi/n/p -> phi/log(n)/log(p) on entry when this flag is
    // set.  See audit §18.
    bool use_log_space = false;

    // Band-to-band tunneling
    bool enable_btbt = false;
    real_t btbt_A = 3.1e21Q;
    real_t btbt_B = 2.0e7Q;
    int btbt_D = 2;
    // Avalanche impact ionization (Chynoweth).  alpha(E)=A*exp(-B/|E|) [1/m].
    // G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q.  Defaults are silicon (SI units,
    // pre-converted from the 1/cm and V/cm literature values — see
    // ImpactIonizationParams in gummel_solver.h for the provenance).
    bool enable_ii = false;
    real_t ii_A_n = 7.03e7Q;     // [1/m]
    real_t ii_B_n = 1.231e8Q;    // [V/m]
    real_t ii_A_p = 1.58e8Q;     // [1/m]
    real_t ii_B_p = 2.036e8Q;    // [V/m]
    real_t ii_E_floor = 1.0e5Q;  // [V/m]
    // Temperature and statistics
    real_t temperature = 300.0Q;
    StatisticsType statistics_type = StatisticsType::BOLTZMANN;
    // Transient (backward Euler).  When transient_enabled is true the carrier
    // continuity residual gets an extra term +(c - c_prev)/dt * dx (with the
    // proper +dx/dt Jacobian diagonal).  The dx factor matches the cell-integrated
    // units [m^-2 s^-1] of the rest of the carrier residual (SG flux and (G-R)*dx
    // source), so the BE term has the correct dimensional weight relative to the
    // SRH source — neither over-pinning (no dx, ~1e8x too strong) nor the audit
    // §14 "too weak" claim (which confused BE-vs-diffusion with BE-vs-source).
    // See audit §17 (transient BE redo).
    bool transient_enabled = false;
    real_t transient_dt = 1.0e-12Q;
    std::vector<real_t> n_prev, p_prev;  // carrier densities at previous time step
    // Freeze phi at its initial/Dirichlet values during the Newton solve.
    // The Poisson rows become identity (phi never moves), so the coupled
    // system reduces to a 2-block (n,p) solve that is diagonal-dominant and
    // well-conditioned — avoiding the ~1e47 dynamic range of the full 3-block
    // Jacobian (Bernoulli phi<>n coupling ~1e29 vs phi diagonal ~1e5) that
    // defeats even quad-precision direct solves.  Phi is quasi-static for
    // the BE transient (contacts pinned, perturbation is in the carriers),
    // so freezing it is an accurate approximation.  See audit §17.
    bool freeze_phi = false;

    // Freeze the majority carrier (n in n-type, p in p-type) to its current
    // value, reducing the Newton solve to a 1-block (minority) system.  In a
    // uniformly-doped device the majority carrier is pinned by doping
    // (n≈Nd, the BE term pins n=n_prev=Nd, and the majority continuity
    // equation is trivially satisfied), so its residual is pure SG-flux
    // cancellation noise (center*n ~ 1e25 with ~1e25 cancellation leaves ~1e6,
    // and a 1e-16 relative perturbation adds 1e9 of noise).  Freezing it
    // eliminates this noise and lets the minority (SRH-governed) block solve
    // cleanly.  See audit §17.
    bool freeze_n = false;
    bool freeze_p = false;
};

class NewtonSolver {
public:
    explicit NewtonSolver(const Grid3D& grid, const NewtonOptions& opt = {});

    void set_permittivity(const std::vector<real_t>& eps);
    void set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p);
    void set_doping(const std::vector<real_t>& Nd_minus_Na);
    void set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p);
    void set_optical_generation(const std::vector<real_t>& G_opt);
    void set_thermal_voltage(real_t VT);
    void set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv);
    void set_bandgap(const std::vector<real_t>& Eg);

    void set_phi_dirichlet(const std::map<size_t, real_t>& bc);
    void set_electron_bc(const std::map<size_t, real_t>& bc);
    void set_hole_bc(const std::map<size_t, real_t>& bc);

    // Ferroelectric polarization feedback into the Newton Poisson residual.
    // The Newton path previously OMITTED the -div(P) bound-charge term that the
    // Gummel path applies in PoissonSolver::assemble, so any solve routed
    // through Newton (use_newton=True, or solve_transient) silently dropped
    // ferroelectric coupling entirely.  DeviceSimulator injects the current P
    // (already refreshed by the Gummel warm-up) and the FE mask here; the
    // Poisson residual then adds -div(P) exactly as PoissonSolver does.
    void set_ferroelectric_polarization(const std::vector<char>& fe_mask,
                                        const std::vector<real_t>& fe_polarization);

    // Interface/bulk trap state (P6). Mirrors PoissonSolver's trap charge
    // injection so the Newton Poisson residual also carries Q_it + Q_ot
    // (audit §21 lesson: a charge term missing from Newton silently vanishes
    // whenever use_newton=True / solve_transient).
    void set_trap_charge(const std::vector<char>& trap_mask,
                         real_t D_it, real_t E_t,
                         const std::vector<real_t>& Q_ot);

    bool solve(std::vector<real_t>& phi,
               std::vector<real_t>& n,
               std::vector<real_t>& p);

    const std::vector<real_t>& residuals() const { return residuals_; }

private:
    Grid3D g_;
    NewtonOptions opt_;

    std::vector<real_t> eps_;
    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> tau_n_, tau_p_;
    std::vector<real_t> G_opt_;
    std::vector<real_t> Nc_, Nv_, Eg_;
    real_t VT_ = 0.02585Q;

    std::map<size_t, real_t> phi_bc_;
    std::map<size_t, real_t> n_bc_;
    std::map<size_t, real_t> p_bc_;

    // Ferroelectric feedback state (optional; no-op when fe_mask_ is empty).
    // Set by DeviceSimulator before solve() so the Newton Poisson residual
    // includes the -div(P) bound-charge term (audit §21 / FE-coupling fix).
    std::vector<char> fe_mask_;                  // length npts (0/1)
    std::vector<real_t> fe_polarization_;        // [Px,Py,Pz] interleaved, len 3*npts

    // Interface/bulk trap charge (P6). Mirrors PoissonSolver.
    std::vector<char> trap_mask_;
    real_t trap_D_it_ = 0.0Q;
    real_t trap_E_t_ = 0.0Q;
    std::vector<real_t> Q_ot_;

    std::vector<real_t> residuals_;

    size_t phi_idx(size_t i) const { return i; }
    size_t n_idx(size_t i) const { return g_.npts() + i; }
    size_t p_idx(size_t i) const { return 2 * g_.npts() + i; }

    void assemble_residual(const std::vector<real_t>& x, std::vector<real_t>& F);
    void assemble_jacobian(const std::vector<real_t>& x, SparseMatrix& J);

    static real_t bernoulli(real_t x);
    static real_t d_bernoulli_dx(real_t x);

    void compute_srh_and_derivs(size_t idx, real_t n, real_t p, real_t ni,
                                real_t& R, real_t& dR_dn, real_t& dR_dp) const;

    // Compute BTBT generation rate (Kane's model) at a given node
    real_t compute_btbt_at(const real_t* phi, size_t idx) const;

    // Compute avalanche impact-ionization generation rate [m^-3 s^-1] at node
    // idx, summed over the up-to-6 SG edges meeting at idx (edge form, same
    // convention as GummelSolver::compute_impact_ionization).
    real_t compute_ii_at(const real_t* phi, const real_t* n,
                         const real_t* p, size_t idx) const;
};

} // namespace tcad
