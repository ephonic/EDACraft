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
    //     u - log(EPSILON); the BE transient term becomes (exp(u)-exp(u_prev))/dt.
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
    real_t btbt_B = 2.0e9Q;  // V/m (SI; 2e7 V/cm)
    real_t btbt_D = 2.0Q;
    int btbt_field_mode = 0;
    real_t btbt_field_cap = 0.0Q;
    real_t btbt_field_alpha = 0.0Q;
    real_t btbt_field_ref = 1.0e8Q;
    real_t btbt_continuity_scale = 1.0Q;
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
    // Auger recombination (Sentaurus Si defaults, SI units).  This must be
    // present in the fully coupled Newton path as well as Gummel; otherwise a
    // Newton-primary avalanche solve silently drops its dominant high-
    // injection recombination mechanism.
    bool enable_auger = false;
    real_t auger_Cn = 2.8e-43Q;   // [m^6/s]
    real_t auger_Cp = 9.9e-44Q;   // [m^6/s]
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
    void set_edge_permittivity(const std::vector<real_t>& x_plus,
                               const std::vector<real_t>& x_minus,
                               const std::vector<real_t>& y_plus,
                               const std::vector<real_t>& y_minus,
                               const std::vector<real_t>& z_plus,
                               const std::vector<real_t>& z_minus);
    void set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p);
    void set_doping(const std::vector<real_t>& Nd_minus_Na);
    void set_charge_volume_fraction(const std::vector<real_t>& fraction);
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
    void set_semiconductor_mask(const std::vector<char>& mask) { semi_mask_ = mask; }
    void set_density_gradient_coefficients(real_t bn, real_t bp) {
        dg_bn_ = bn; dg_bp_ = bp;
    }
    void set_density_gradient_silicon_multivalley(bool enable,
                                                  real_t ml, real_t mt,
                                                  size_t subbands) {
        dg_silicon_multivalley_ = enable;
        dg_silicon_ml_ = ml; dg_silicon_mt_ = mt;
        dg_silicon_subbands_ = subbands;
    }
    void set_density_gradient_interface_distance_factor(real_t factor) {
        dg_interface_distance_factor_ = factor;
    }
    void set_density_gradient_step_boundary(
        bool enable, real_t electron_barrier_eV, real_t hole_barrier_eV,
        real_t electron_barrier_mass, real_t hole_barrier_mass,
        real_t electron_gamma, real_t hole_gamma,
        real_t electron_theta, real_t hole_theta) {
        dg_step_boundary_enabled_ = enable;
        dg_step_e_barrier_eV_ = electron_barrier_eV;
        dg_step_h_barrier_eV_ = hole_barrier_eV;
        dg_step_e_mass_ = electron_barrier_mass;
        dg_step_h_mass_ = hole_barrier_mass;
        dg_step_e_gamma_ = electron_gamma;
        dg_step_h_gamma_ = hole_gamma;
        dg_step_e_theta_ = electron_theta;
        dg_step_h_theta_ = hole_theta;
    }
    void set_ohmic_contacts(const std::set<size_t>& nodes,
                            const std::map<size_t, real_t>& EFn,
                            const std::map<size_t, real_t>& EFp,
                            real_t ni) {
        ohmic_nodes_ = nodes; ohmic_EFn_ = EFn; ohmic_EFp_ = EFp; ohmic_ni_ = ni;
    }

    bool solve(std::vector<real_t>& phi,
               std::vector<real_t>& n,
               std::vector<real_t>& p);

    const std::vector<real_t>& residuals() const { return residuals_; }

    // Debug utility (issues0719 follow-up / plan0728 §1.1): finite-difference
    // verification of assemble_jacobian against assemble_residual at the
    // given state (phi,n,p in linear space; the log-space conversion is
    // applied internally exactly as in solve()).  Prints the worst
    // mismatched J entries with block/node mapping.  Returns the count of
    // entries whose relative error exceeds rel_tol.
    size_t debug_fd_jacobian_check(const std::vector<real_t>& phi,
                                   const std::vector<real_t>& n,
                                   const std::vector<real_t>& p,
                                   double rel_tol = 5e-2,
                                   size_t max_report = 40);

    // Debug probe for the Newton line-search stall (plan0728 §1.1): at the
    // given state, assembles F and J, solves J dx = -F with the configured
    // linear solver, then prints ||J*dx + F||/||F|| (solve accuracy) and
    // ||F(x + a*dx)|| for a range of step fractions a.  An exact Jacobian +
    // accurate solve must show the residual decreasing for small a; if the
    // solve is accurate but no a decreases ||F||, the Jacobian is
    // inconsistent with the residual.
    void debug_solve_probe(const std::vector<real_t>& phi,
                           const std::vector<real_t>& n,
                           const std::vector<real_t>& p);

private:
    Grid3D g_;
    NewtonOptions opt_;

    std::vector<real_t> eps_;
    std::vector<real_t> edge_eps_x_plus_, edge_eps_x_minus_;
    std::vector<real_t> edge_eps_y_plus_, edge_eps_y_minus_;
    std::vector<real_t> edge_eps_z_plus_, edge_eps_z_minus_;
    std::vector<real_t> mu_n_, mu_p_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> charge_volume_fraction_;
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

    // DG semiconductor mask (1=semi, 0=oxide). Empty = no DG.
    std::vector<char> semi_mask_;
    real_t dg_bn_ = 4.885e-20Q;
    real_t dg_bp_ = 3.432e-20Q;
    bool dg_silicon_multivalley_ = false;
    real_t dg_silicon_ml_ = 0.916Q;
    real_t dg_silicon_mt_ = 0.190Q;
    size_t dg_silicon_subbands_ = 4;
    real_t dg_interface_distance_factor_ = 1.0Q;
    bool dg_step_boundary_enabled_ = false;
    real_t dg_step_e_barrier_eV_ = 3.17Q;
    real_t dg_step_h_barrier_eV_ = 4.70Q;
    real_t dg_step_e_mass_ = 0.42Q;
    real_t dg_step_h_mass_ = 1.0Q;
    // Eq. 250 uses gamma(0+), i.e. the non-solved barrier side.
    real_t dg_step_e_gamma_ = 1.0Q;
    real_t dg_step_h_gamma_ = 1.0Q;
    real_t dg_step_e_theta_ = 0.5Q;
    real_t dg_step_h_theta_ = 0.5Q;
    // Picard/Newton DG state.  dQ/dn is intentionally omitted from the
    // three-block Jacobian, so one Newton iteration (including all line-search
    // trials) must use one frozen Q.  It is refreshed from the accepted x at
    // the start of the next outer iteration.
    bool use_lagged_quantum_potential_ = false;
    std::vector<real_t> lagged_Qn_, lagged_Qp_;
    // Per-node quantum rescue active set.  Deeply depleted log-density
    // variables below the mobile-charge error reference are numerically
    // unobservable and are pinned to their accepted Gummel value.
    std::vector<char> inactive_n_, inactive_p_;
    // Ohmic contact data
    std::set<size_t> ohmic_nodes_;
    std::map<size_t, real_t> ohmic_EFn_, ohmic_EFp_;
    real_t ohmic_ni_ = 1.07e16Q;

    std::vector<real_t> residuals_;

    size_t phi_idx(size_t i) const { return i; }
    size_t n_idx(size_t i) const { return g_.npts() + i; }
    size_t p_idx(size_t i) const { return 2 * g_.npts() + i; }

    void assemble_residual(const std::vector<real_t>& x, std::vector<real_t>& F);
    void assemble_jacobian(const std::vector<real_t>& x, SparseMatrix& J);
    void refresh_lagged_quantum_potential(const std::vector<real_t>& x);

    static real_t bernoulli(real_t x);
    static real_t d_bernoulli_dx(real_t x);
    real_t edge_epsilon(size_t idx, size_t nbr,
                        const std::vector<real_t>& override_values) const;
    real_t active_carrier_width(size_t idx, size_t j, size_t k, int axis,
                                const std::vector<real_t>& mobility) const;

    void compute_srh_and_derivs(size_t idx, real_t n, real_t p, real_t ni,
                                real_t& R, real_t& dR_dn, real_t& dR_dp) const;

    // Compute BTBT generation rate (Kane's model) at a given node
    real_t compute_btbt_at(const real_t* phi, size_t idx) const;

    // Compute avalanche impact-ionization generation rate [m^-3 s^-1] at node
    // idx, summed over the up-to-6 SG edges meeting at idx (edge form, same
    // convention as GummelSolver::compute_impact_ionization).
    real_t compute_ii_at(const real_t* phi, const real_t* n,
                         const real_t* p, size_t idx) const;

    // Add the exact piecewise-smooth derivatives of the Chynoweth source to
    // one carrier-continuity row.  Both electron and hole equations contain
    // -G_ii, so the same block is inserted in each row.  Omitting these terms
    // turns Newton into a Picard iteration precisely where avalanche feedback
    // becomes critical and was the main source of breakdown-sweep stalls.
    void add_ii_jacobian_row(SparseMatrix& J, size_t row,
                             const real_t* phi, const real_t* n,
                             const real_t* p, size_t idx,
                             real_t source_scale) const;
};

} // namespace tcad
