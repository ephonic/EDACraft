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
    // Non-uniform position arrays (empty = uniform mode, backward compatible)
    std::vector<real_t> zx;  // z node positions, size nz
    std::vector<real_t> xx;  // x node positions, size nx
    std::vector<real_t> yx;  // y node positions, size ny

    size_t npts() const { return nx * ny * nz; }
    size_t index(size_t i, size_t j, size_t k) const {
        return i + nx * (j + ny * k);
    }
    // Edge spacing (node n -> n+1)
    real_t dz_edge(size_t k) const { return zx.empty() ? dz : (zx[k+1]-zx[k]); }
    real_t dx_edge(size_t i) const { return xx.empty() ? dx : (xx[i+1]-xx[i]); }
    real_t dy_edge(size_t j) const { return yx.empty() ? dy : (yx[j+1]-yx[j]); }
    // FV cell size at node n
    real_t dz_cell(size_t k) const {
        if (zx.empty()) return dz;
        real_t l = (k > 0) ? (zx[k] - zx[k-1]) / 2 : (zx[1] - zx[0]) / 2;
        real_t r = (k+1 < nz) ? (zx[k+1] - zx[k]) / 2 : (zx[nz-1] - zx[nz-2]) / 2;
        return l + r;
    }
    real_t dx_cell(size_t i) const {
        if (xx.empty()) return dx;
        real_t l = (i > 0) ? (xx[i] - xx[i-1]) / 2 : (xx[1] - xx[0]) / 2;
        real_t r = (i+1 < nx) ? (xx[i+1] - xx[i]) / 2 : (xx[nx-1] - xx[nx-2]) / 2;
        return l + r;
    }
    real_t dy_cell(size_t j) const {
        if (yx.empty()) return dy;
        real_t l = (j > 0) ? (yx[j] - yx[j-1]) / 2 : (yx[1] - yx[0]) / 2;
        real_t r = (j+1 < ny) ? (yx[j+1] - yx[j]) / 2 : (yx[ny-1] - yx[ny-2]) / 2;
        return l + r;
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

    // Depolarization field (comments2.docx P3). Sets the FE relative permittivity
    // so the update applies E_dep = -P/(eps_fe * eps_0). 0 disables the term.
    void set_ferroelectric_depol(real_t eps_fe);

    // NLS (Nucleation-Limited Switching) parameters (P3, model==2). Sets the
    // Merz-law switching-time parameters tau0 [s] and E0 [V/m], plus an
    // effective dwell time dt [s] per bias step (controls loop slope).
    void set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt);

    // Polar axis for the scalar FE models (Preisach / NLS) and for the LK
    // built-in field + depolarization drive: 0 = x, 1 = y, 2 = z (clamped).
    // The built-in FeFET template stacks gate/FE/oxide/channel along Z, so
    // axis 2 is required there; default 0 = legacy x-only behavior.
    void set_ferroelectric_polar_axis(int axis);

    // Leakage current (Poole-Frenkel / Fowler-Nordheim) (P2.2). Sets the leaky
    // node mask and PF/FN coefficients. During assemble(), a field-dependent
    // conductance sigma_leak(|E|) is added to the Poisson diagonal of masked
    // nodes, modelling a residual leakage path that prevents P-V loop closure
    // at V=0. Empty mask or zero coefficients disable the term.
    // Stabilized-Gummel Boltzmann linearization (plan0728 §1.2): when
    // enabled, assemble() adds the carrier-charge linearization
    // -(q/VT)(n+p) to the Poisson diagonal and -(q/VT)(n+p)*phi_old to the
    // RHS (phi_old from set_leakage_field).  The fixed point is IDENTICAL
    // (the terms cancel at convergence), but the iteration becomes
    // semi-implicit: nodes whose carriers overshoot (depletion-edge
    // Boltzmann swing, p ~ 1e6x Na on the Na=1e24 junction) get a huge
    // diagonal and stop moving instead of ratcheting into a limit cycle.
    void set_boltzmann_linearization(bool enable, real_t VT) {
        boltzmann_lin_ = enable;
        VT_ = VT;
    }
    // Ohmic contact: mark nodes where Poisson should use Boltzmann n(phi)
    // instead of frozen n from continuity BC.  EFn/EFp are quasi-Fermi
    // shifts (source=0, drain=Vd) at each Ohmic node.
    void set_ohmic_contacts(const std::set<size_t>& nodes,
                            const std::map<size_t, real_t>& EFn,
                            const std::map<size_t, real_t>& EFp,
                            real_t ni) {
        ohmic_nodes_ = nodes;
        ohmic_EFn_ = EFn;
        ohmic_EFp_ = EFp;
        ohmic_ni_ = ni;
    }
    void clear_ohmic_contacts() { ohmic_nodes_.clear(); }

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

    // True Poisson equation residual (P0-3 fix): reassembles A_ and rhs_ for
    // the given carrier densities (WITHOUT solving) and returns the relative
    // residual ||A_*phi - rhs_||_2 / (||rhs_||_2 + tiny). Callers that use the
    // trap/leakage terms should call set_leakage_field(phi) first so the
    // occupancy / field-dependent conductance use this phi.
    real_t residual_norm(const std::vector<real_t>& phi,
                         const std::vector<real_t>& n,
                         const std::vector<real_t>& p);

private:
    Grid3D g_;
    bool boltzmann_lin_ = true;     // stabilized-Gummel charge linearization
    real_t VT_ = 0.02585Q;          // thermal voltage for the linearization
    // Ohmic contact data
    std::set<size_t> ohmic_nodes_;
    std::map<size_t, real_t> ohmic_EFn_, ohmic_EFp_;
    real_t ohmic_ni_ = 1.07e16Q;   // intrinsic density for Boltzmann n(phi)
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
    // Depolarization field (comments2.docx P3). The bound-charge self-field
    // E_dep = -P / (eps_fe * eps_0) opposes the polarization, limiting it in
    // thin films. eps_fe is the FE relative permittivity; 0 => no depol term.
    real_t fe_eps_fe_ = 0.0Q;     // FE layer relative permittivity (0 => disabled)
    // Under-relaxation factor for P update (comments2.docx): correct div(P)
    // coupling produces stronger P-phi feedback; a relaxation factor < 1
    // stabilises the self-consistent iteration. P_new = relax*P_new + (1-relax)*P_old.
    real_t fe_relax_ = 1.0Q;   // 1.0 = no relaxation (full update)
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

    // Polar axis for the scalar FE models (0 = x, 1 = y, 2 = z). The Preisach
    // and NLS updates drive ONLY fe_polarization_[3*idx + fe_axis_]; the LK
    // path stays vector but applies the built-in field E_bi and the
    // depolarization term to the fe_axis_ component. Default 0 reproduces the
    // legacy x-only behavior bit-for-bit.
    int fe_axis_ = 0;

    // Trap layer thickness cache (P0-6 fix): extent of trap_mask_ along its
    // thinnest axis (the interface normal) [m], used to convert the surface
    // charge Q_it [C/m^2] into a mesh-invariant volume charge [C/m^3].
    // Computed in set_interface_traps(); 0 => not computed (falls back to dx).
    real_t trap_layer_thickness_ = 0.0Q;

    // Electric field component E_axis = -d(phi)/d(axis) at grid node (i,j,k):
    // central differences interior, one-sided at the domain boundary (the same
    // differencing template as compute_electric_field).
    real_t e_field_component(const std::vector<real_t>& phi,
                             size_t i, size_t j, size_t k, int axis) const;

    // Extent of trap_mask_ along its thinnest axis [m] (P0-6 helper).
    real_t compute_trap_layer_thickness() const;

    // Stencil coefficients for finite difference/volume
    real_t cx_plus(size_t idx) const;
    real_t cx_minus(size_t idx) const;
    real_t cy_plus(size_t idx) const;
    real_t cy_minus(size_t idx) const;
    real_t cz_plus(size_t idx) const;
    real_t cz_minus(size_t idx) const;
};

} // namespace tcad
