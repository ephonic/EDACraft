#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include <vector>
#include <functional>

namespace tcad {

// 3D Poisson equation solver on a structured Cartesian grid
//  div(eps * grad(phi)) = -rho
// where rho = q * (p - n + Nd - Na)
// Quantum correction via Density Gradient is applied through modified n, p

struct Grid3D {
    size_t nx, ny, nz;
    real_t dx, dy, dz;
    size_t npts() const { return nx * ny * nz; }
    size_t index(size_t i, size_t j, size_t k) const {
        return i + nx * (j + ny * k);
    }
};

class PoissonSolver {
public:
    explicit PoissonSolver(const Grid3D& grid);

    // Set permittivity (can be position-dependent, per grid point)
    void set_permittivity(const std::vector<real_t>& eps);

    // Set edge-effective permittivity for cut-cell / immersed-boundary accuracy.
    // Each array has length npts(); zero or unset entries fall back to
    // harmonic averaging of the two node permittivities.
    void set_edge_permittivity(const std::vector<real_t>& x_plus,
                               const std::vector<real_t>& x_minus,
                               const std::vector<real_t>& y_plus,
                               const std::vector<real_t>& y_minus,
                               const std::vector<real_t>& z_plus,
                               const std::vector<real_t>& z_minus);

    // Reconfigure linear solver (e.g., switch to PETSc for large problems)
    void set_solver_options(const SolverOptions& opt);

    // Set fixed charge (Nd - Na)
    void set_doping(const std::vector<real_t>& Nd_minus_Na);

    // Set boundary conditions: Dirichlet (value) at specific indices
    // Map: global_index -> potential_value
    void set_dirichlet(const std::map<size_t, real_t>& bc);
    void set_neumann_faces(char face); // 'x', 'y', 'z', 'X', 'Y', 'Z'

    // Build matrix and RHS for current carrier densities
    void assemble(const std::vector<real_t>& n, const std::vector<real_t>& p);

    // Build matrix and RHS for thermal equation: div(kappa * grad(T)) = -P
    // where P is the volumetric heat generation [W/m^3].
    void assemble_thermal(const std::vector<real_t>& power_density);

    // Set ferroelectric region mask and Landau-Khalatnikov parameters.
    // fe_mask[i] == 1 marks node i as ferroelectric.
    // alpha < 0, beta > 0 give the double-well potential.
    // NOTE: does NOT zero fe_polarization_ if already sized (so an externally
    // injected persistent P survives a GummelSolver rebuild). Only allocates
    // on first call / size mismatch.
    void set_ferroelectric(const std::vector<char>& fe_mask,
                           real_t alpha, real_t beta);

    // Ferroelectric model selection + Preisach parameters (M7c). Sets the
    // model (LK vs PREISACH) and, for PREISACH, the saturation polarization Ps
    // [C/m^2], coercive field Ec [V/m], and Escale [V/m] (the tanh output
    // width). Escale=0 falls back to Escale=Ec (legacy behaviour); a smaller
    // Escale lets |P| approach the named saturation Ps. Mirrors the
    // MobilityModelType int->enum pattern.
    void set_ferroelectric_model(int model);   // 0=LK, 1=PREISACH
    void set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale);

    // Internal field / Imprint offset (P2.1). Shifts the effective ferroelectric
    // switching drive: E_eff = E_applied - E_bi. This models a built-in bias or
    // imprint that breaks the +/- loop symmetry. 0 (default) => symmetric loop.
    void set_ferroelectric_builtin_field(real_t E_bi);

    // NLS (Nucleation-Limited Switching) parameters (P3, model==2). Sets the
    // Merz-law switching-time parameters tau0 [s] and E0 [V/m], plus an
    // effective dwell time dt [s] per bias step (controls loop slope).
    void set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt);

    // Leakage current (Poole-Frenkel / Fowler-Nordheim) (P2.2). Sets the leaky
    // node mask and PF/FN coefficients. During assemble(), a field-dependent
    // conductance sigma_leak(|E|) is added to the Poisson diagonal of masked
    // nodes, modelling a residual leakage path that prevents P-V loop closure
    // at V=0. Empty mask or zero coefficients disable the term.
    void set_leakage(const std::vector<char>& mask,
                     real_t C_pf, real_t B_pf, real_t phi_t,
                     real_t C_fn, real_t B_fn, real_t phi_b,
                     real_t E_floor, real_t sigma_cap);
    // Interface traps (Dit) + bulk oxide traps (P6). Sets the interface-trap
    // mask, density D_it [cm^-2 eV^-1], and trap energy E_t [eV] relative to
    // intrinsic Fermi level. During assemble(), the trap charge
    // Q_it = -q * D_it * dE * (f_t - 0.5) is injected into the Poisson RHS of
    // masked nodes, shifting the threshold voltage. Bulk oxide traps Q_ot
    // [C/m^3] are a persistent charge array (evolved by the caller for
    // retention/endurance). Empty mask disables the interface-trap term.
    void set_interface_traps(const std::vector<char>& mask,
                             real_t D_it, real_t E_t);
    void set_oxide_traps(const std::vector<real_t>& Q_ot);
    // Cache the current potential for the leakage field-dependent conductance
    // (P2.2). Must be called before assemble() each iteration so the leaky-node
    // diagonal term sigma_leak(|E|) uses the up-to-date field. Storing phi here
    // avoids changing the assemble() signature.
    void set_leakage_field(const std::vector<real_t>& phi);

    // Persistent vector polarization state (3 components per node, interleaved
    // [Px,Py,Pz]; per-component sign == branch == memory). DeviceSimulator holds
    // the authoritative copy across solve() calls so a Vg sweep produces
    // path-dependent hysteresis. Layout: fe_polarization_[3*idx + c], c=0,1,2.
    const std::vector<real_t>& fe_polarization() const { return fe_polarization_; }
    void set_fe_polarization(const std::vector<real_t>& P) { fe_polarization_ = P; }

    // Preisach play-operator internal state (M7c). One scalar per masked node:
    // the play operator's "memory" value (the last turning-point field shifted
    // by +/-Ec). Persisted across solve() like fe_polarization_. For the L-K
    // path these are unused (kept empty).
    const std::vector<real_t>& fe_play_state() const { return fe_play_state_; }
    void set_fe_play_state(const std::vector<real_t>& s) { fe_play_state_ = s; }

    // Update ferroelectric polarization from current potential (self-consistent).
    // Must be called before assemble() when ferroelectric is enabled.
    void update_ferroelectric_polarization(const std::vector<real_t>& phi);

    // Set ferroelectric gamma for transient LK dynamics: E = alpha*P + beta*P^3 + gamma*dP/dt
    void set_ferroelectric_gamma(real_t gamma);

    // Dielectric breakdown (M7b, audit §22).  Injects the irreversible breakdown
    // state (1 = node has broken down) and the soft-breakdown leakage term
    // sigma_bd [F/m^3] — an effective added permittivity-density (same units as
    // the Poisson Laplacian diagonal eps/dx^2).  In assemble(), a broken-down
    // dielectric node gets +sigma_bd on the Poisson diagonal and +0 on the RHS,
    // locally relaxing phi toward 0 (soft short) so a gate leak develops.
    // (A档: was documented [S/m], which is dimensionally inconsistent with the
    //  [F/m^3] diagonal; redefined to [F/m^3] for dimensional self-consistency.)
    // Empty state disables the leakage term.  Call before assemble() each solve().
    void set_breakdown_state(const std::vector<char>& bd_state, real_t sigma_bd);

    // Transient LK time step: P^{k+1} = P^k + (dt/gamma)*(E - alpha*P^k - beta*(P^k)^3)
    void update_ferroelectric_polarization_transient(const std::vector<real_t>& phi, real_t dt);

    // Solve for potential phi
    bool solve(std::vector<real_t>& phi);

    // Access the system matrix (for Jacobian in Newton method)
    const SparseMatrix& matrix() const { return A_; }

    // Dirichlet mask for external solvers
    const std::vector<char>& dirichlet_mask() const { return is_dirichlet_; }

    // Assemble Jacobian J and residual F for Newton method
    // Must call assemble() first to build A_ and rhs_
    // J = A_ - (q/VT)*diag(n+p)  for internal nodes (negative-definite Jacobian)
    // F = A_*phi - rhs_           (Poisson residual)
    void assemble_newton(const std::vector<real_t>& phi,
                         const std::vector<real_t>& n,
                         const std::vector<real_t>& p,
                         real_t VT,
                         SparseMatrix& J,
                         Vector& F) const;

    // Compute electric field components from phi (central differences)
    void compute_electric_field(const std::vector<real_t>& phi,
                                std::vector<real_t>& Ex,
                                std::vector<real_t>& Ey,
                                std::vector<real_t>& Ez) const;

private:
    Grid3D g_;
    std::vector<real_t> eps_;       // Permittivity at each grid point
    std::vector<real_t> edge_eps_x_plus_;
    std::vector<real_t> edge_eps_x_minus_;
    std::vector<real_t> edge_eps_y_plus_;
    std::vector<real_t> edge_eps_y_minus_;
    std::vector<real_t> edge_eps_z_plus_;
    std::vector<real_t> edge_eps_z_minus_;
    std::vector<real_t> Nd_minus_Na_;
    std::map<size_t, real_t> dirichlet_bc_;
    std::vector<char> is_dirichlet_;

    SparseMatrix A_;
    Vector rhs_;
    LinearSolver solver_;
    bool assembled_ = false;

    // Ferroelectric polarization
    std::vector<char> fe_mask_;
    std::vector<real_t> fe_polarization_;  // [Px,Py,Pz] per node, interleaved, len 3*npts [C/m^2]
    real_t fe_alpha_ = 0.0Q;
    real_t fe_beta_ = 0.0Q;
    real_t fe_gamma_ = 0.0Q;  // LK damping coefficient [V*m/C * s]
    bool fe_enabled_ = false;

    // Ferroelectric model selection + Preisach params (M7c).
    int fe_model_ = 0;            // 0 = LK, 1 = PREISACH
    real_t fe_ps_ = 0.2Q;         // Preisach saturation polarization [C/m^2]
    real_t fe_ec_ = 1.0e9Q;       // Preisach coercive field [V/m]
    real_t fe_escale_ = 0.0Q;     // Preisach tanh width [V/m]; 0 => Ec (default)
    // Internal field / Imprint offset (P2.1). Subtracted from the applied field
    // to form the effective switching drive E_eff = E - E_bi. 0 => symmetric.
    real_t fe_E_bi_ = 0.0Q;
    // NLS (P3, model==2): Merz-law tau(E) = tau0*exp(E0/|E|).
    real_t fe_nls_tau0_ = 1.0e-6Q;   // characteristic switching time [s]
    real_t fe_nls_E0_ = 2.0e9Q;      // Merz activation field [V/m]
    real_t fe_nls_dt_ = 1.0e-6Q;     // effective dwell time per bias step [s]
    // Play-operator internal state: length npts, one "memory" value per node
    // (the play operator's internal level). Empty under L-K.
    std::vector<real_t> fe_play_state_;

    // Dielectric breakdown state (M7b, audit §22).  bd_state_[i]==1 marks a
    // node that has irreversibly broken down; assemble() adds sigma_bd_ to its
    // Poisson diagonal (soft short -> gate leak).  Empty = disabled.
    std::vector<char> bd_state_;
    real_t sigma_bd_ = 0.0Q;

    // Interface traps (Dit) + bulk oxide traps (P6).
    // trap_mask_[i]==1 marks an interface node; assemble() injects
    // Q_it = -q*D_it*dE*(f_t-0.5) into the Poisson RHS. Q_ot_ is a persistent
    // per-node oxide-trap charge [C/m^3] (evolved externally for retention).
    std::vector<char> trap_mask_;
    real_t trap_D_it_ = 0.0Q;     // interface trap density [cm^-2 eV^-1]
    real_t trap_E_t_ = 0.0Q;      // trap energy level [eV] (rel. intrinsic)
    std::vector<real_t> Q_ot_;    // bulk oxide trap charge [C/m^3]

    // Leakage current (PF/FN) state (P2.2). leak_mask_[i]==1 marks a node that
    // carries field-dependent leakage; assemble() adds sigma_leak(|E|) to its
    // Poisson diagonal. Empty mask or C_pf=C_fn=0 disables the term.
    std::vector<char> leak_mask_;
    real_t leak_C_pf_ = 0.0Q, leak_B_pf_ = 0.0Q, leak_phi_t_ = 0.0Q;
    real_t leak_C_fn_ = 0.0Q, leak_B_fn_ = 0.0Q, leak_phi_b_ = 0.0Q;
    real_t leak_E_floor_ = 1.0e6Q;
    real_t leak_sigma_cap_ = 0.05Q;
    std::vector<real_t> leak_phi_;     // cached potential for |E| (set before assemble)
    std::vector<real_t> leak_E_mag_;   // cached |E| per node (computed in set_leakage_field)

    // Stencil coefficients for finite difference/volume
    real_t cx_plus(size_t idx) const;
    real_t cx_minus(size_t idx) const;
    real_t cy_plus(size_t idx) const;
    real_t cy_minus(size_t idx) const;
    real_t cz_plus(size_t idx) const;
    real_t cz_minus(size_t idx) const;
};

} // namespace tcad
