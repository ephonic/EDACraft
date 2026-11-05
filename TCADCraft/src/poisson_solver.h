#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include <vector>
#include <set>
#include <functional>
#include <array>
#include <limits>
#include <stdexcept>

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
    // Explicit material-LK closure for cell-centred natural faces. The outer
    // boundary is half the adjacent edge beyond the endpoint, with D.n=0.
    // Order x-,x+,y-,y+,z-,z+; false retains endpoint-at-boundary LK support.
    std::array<bool,6> lk_zero_d_faces{};

    size_t npts() const {
        // Preserve empty-grid counts even if the two nonzero axes would
        // overflow. Nonempty grids must never allocate a wrapped node count.
        if (nx == 0 || ny == 0 || nz == 0) return 0;
        size_t plane, total;
#if defined(__GNUC__) || defined(__clang__)
        if (__builtin_mul_overflow(nx, ny, &plane) ||
            __builtin_mul_overflow(plane, nz, &total))
            throw std::overflow_error("grid node count overflows size_t");
#else
        const size_t limit = std::numeric_limits<size_t>::max();
        if (nx > limit / ny)
            throw std::overflow_error("grid node count overflows size_t");
        plane = nx * ny;
        if (plane > limit / nz)
            throw std::overflow_error("grid node count overflows size_t");
        total = plane * nz;
#endif
        return total;
    }
    size_t index(size_t i, size_t j, size_t k) const {
        return i + nx * (j + ny * k);
    }
    // Edge spacing (node n -> n+1)
    real_t dz_edge(size_t k) const { return zx.empty() ? dz : (zx[k+1]-zx[k]); }
    real_t dx_edge(size_t i) const { return xx.empty() ? dx : (xx[i+1]-xx[i]); }
    real_t dy_edge(size_t j) const { return yx.empty() ? dy : (yx[j+1]-yx[j]); }
    // FV cell size at node n. A singleton axis has no edge from which to
    // infer thickness, so retain its supplied uniform extrusion thickness
    // even when a one-element position array specifies the plane location.
    real_t dz_cell(size_t k) const {
        if (zx.size() < 2) return dz;
        real_t l = (k > 0) ? (zx[k] - zx[k-1]) / 2 : (zx[1] - zx[0]) / 2;
        real_t r = (k+1 < nz) ? (zx[k+1] - zx[k]) / 2 : (zx[nz-1] - zx[nz-2]) / 2;
        return l + r;
    }
    real_t dx_cell(size_t i) const {
        if (xx.size() < 2) return dx;
        real_t l = (i > 0) ? (xx[i] - xx[i-1]) / 2 : (xx[1] - xx[0]) / 2;
        real_t r = (i+1 < nx) ? (xx[i+1] - xx[i]) / 2 : (xx[nx-1] - xx[nx-2]) / 2;
        return l + r;
    }
    real_t dy_cell(size_t j) const {
        if (yx.size() < 2) return dy;
        real_t l = (j > 0) ? (yx[j] - yx[j-1]) / 2 : (yx[1] - yx[0]) / 2;
        real_t r = (j+1 < ny) ? (yx[j+1] - yx[j]) / 2 : (yx[ny-1] - yx[ny-2]) / 2;
        return l + r;
    }
};

// Read-only compact NLS drive for a caller-supplied potential predictor.
// This does not solve Poisson, consume dwell, or change material memory.
struct FerroelectricNlsDrive {
    bool active = false;
    real_t raw_mean_field = TCAD_CONST(0.0); // after imprint/depolarization [V/m]
    real_t mean_field = TCAD_CONST(0.0);     // after numerical-zero guard [V/m]
    real_t peak_field = TCAD_CONST(0.0);     // guarded local rate field [V/m]
    real_t mean_polarization = TCAD_CONST(0.0); // geometric FE average [C/m^2]
    real_t volume = TCAD_CONST(0.0);         // geometric FE support [m^3]
    real_t zero_field_tolerance = TCAD_CONST(0.0); // existing roundoff guard
};

class PoissonSolver {
    // Candidate rollback restores already validated material vectors by swap.
    // Keep that operation internal; public setters retain input validation.
    friend class DeviceSimulator;
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

    // Fraction of each node-centred control volume occupied by the material
    // carrying p-n+doping charge. Defaults to one. Cut-cell/interface meshes
    // use values in [0,1] so a semiconductor interface node does not smear
    // mobile charge into the dielectric half of its control volume.
    void set_charge_volume_fraction(const std::vector<real_t>& fraction);

    // Set boundary conditions: Dirichlet (value) at specific indices
    // Map: global_index -> potential_value
    void set_dirichlet(const std::map<size_t, real_t>& bc);
    void set_neumann_faces(char face); // 'x', 'y', 'z', 'X', 'Y', 'Z'

    // Build matrix and RHS for current carrier densities
    void assemble(const std::vector<real_t>& n, const std::vector<real_t>& p);

    // Build matrix and RHS for thermal equation: div(kappa * grad(T)) = -P
    // where P is the volumetric heat generation [W/m^3].
    void assemble_thermal(const std::vector<real_t>& power_density,
        const std::vector<real_t>& heat_capacity = {},
        const std::vector<real_t>& previous_temperature = {},
        real_t dt = TCAD_CONST(0.0));

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

    // Requires enabled NLS and finite mesh-sized phi and polarization.
    // Empty FE support returns active=false. Uses exactly the same volume,
    // imprint, depolarization, peak and numerical-zero rule as NLS advancement.
    FerroelectricNlsDrive ferroelectric_nls_drive(const std::vector<real_t>& phi) const;

    // Polar axis for the scalar FE models (Preisach / NLS) and for the LK
    // built-in field + depolarization drive: 0 = x, 1 = y, 2 = z (clamped).
    // The built-in FeFET template stacks gate/FE/oxide/channel along Z, so
    // axis 2 is required there; default 0 = legacy x-only behavior.
    void set_ferroelectric_polar_axis(int axis);

    // Leakage parameters are retained here because Gummel owns the Poisson
    // object and caches the field. PF/FN is no longer added to Poisson;
    // DeviceSimulator evaluates the explicit A/m^2 edge flux after solve().
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
        for (size_t node : nodes)
            if (node >= g_.npts())
                throw std::out_of_range("ohmic contact node is outside the grid");
        for (const auto* shifts : {&EFn, &EFp})
            for (const auto& entry : *shifts)
                if (entry.first >= g_.npts())
                    throw std::out_of_range("ohmic quasi-Fermi node is outside the grid");
        for (const auto* shifts : {&EFn, &EFp})
            for (const auto& entry : *shifts)
                if (!isfinite_q(entry.second))
                    throw std::invalid_argument("ohmic quasi-Fermi values must be finite");
        if (!isfinite_q(ni) || ni <= TCAD_CONST(0.0))
            throw std::invalid_argument("ohmic intrinsic density must be finite and positive");
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
    real_t trap_layer_thickness() const { return trap_layer_thickness_; }
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
    void set_fe_polarization(const std::vector<real_t>& P) {
        if (!P.empty() && P.size() != 3 * g_.npts())
            throw std::invalid_argument("FE polarization size mismatch");
        for (real_t value : P)
            if (!isfinite_q(value))
                throw std::invalid_argument("FE polarization values must be finite");
        fe_polarization_ = P;
    }

    // Persistent Preisach memory: model 1 has one play level per node;
    // model 3 has per-node previous fields/directions and a shared ensemble
    // turning-point stack (see fe_play_state_ below). Unused under L-K/NLS.
    const std::vector<real_t>& fe_play_state() const { return fe_play_state_; }
    void set_fe_play_state(const std::vector<real_t>& s) {
        // Model-dependent lengths are normalized by the existing update paths.
        for (real_t value : s)
            if (!isfinite_q(value))
                throw std::invalid_argument("FE play state values must be finite");
        fe_play_state_ = s;
    }

    // Update ferroelectric polarization from current potential (self-consistent).
    // Must be called before assemble() when ferroelectric is enabled.
    void update_ferroelectric_polarization(const std::vector<real_t>& phi);

    // Set ferroelectric gamma for transient LK dynamics: E = alpha*P + beta*P^3 + gamma*dP/dt
    void set_ferroelectric_gamma(real_t gamma);

    // Compatibility/debug injection of the persistent breakdown state.
    // sigma_bd is a conductivity [S/m]; DeviceSimulator evaluates its explicit
    // edge current. Poisson deliberately ignores both values.
    void set_breakdown_state(const std::vector<char>& bd_state, real_t sigma_bd);

    // Transient LK backward Euler: beta*P_new^3 + (alpha+gamma/dt)*P_new
    // = E_drive + gamma/dt*P_old, retaining the previous stable branch.
    void update_ferroelectric_polarization_transient(const std::vector<real_t>& phi, real_t dt);

    // Solve for potential phi
    bool solve(std::vector<real_t>& phi);

    // Access the system matrix (for Jacobian in Newton method)
    const SparseMatrix& matrix() const { return A_; }
    const Vector& rhs() const { return rhs_; }

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

    // Physical relative residual ||A*phi-rhs||_2/(||rhs||_2+tiny).
    // Excludes artificial Gummel charge stabilization from both terms and
    // refreshes trap/leakage state at phi in an isolated assembly, leaving
    // the live matrix and caches intact. At neutrality or nonzero boundary
    // offsets, prefer scaled_residual_norm for an acceptance decision.
    real_t residual_norm(const std::vector<real_t>& phi,
                         const std::vector<real_t>& n,
                         const std::vector<real_t>& p);

    // Maximum rowwise physical equation error, scaled by thermal-voltage
    // stiffness and unsigned charge. Excludes the artificial Gummel charge
    // Jacobian; meaningful at neutrality and invariant to potential offsets.
    // Uses an isolated assembly, leaving this operator and its caches intact.
    real_t scaled_residual_norm(const std::vector<real_t>& phi,
                                const std::vector<real_t>& n,
                                const std::vector<real_t>& p,
                                real_t thermal_voltage) const;

private:
    Grid3D g_;
    bool boltzmann_lin_ = true;     // stabilized-Gummel charge linearization
    real_t VT_ = TCAD_CONST(0.02585);          // thermal voltage for the linearization
    // Ohmic contact data
    std::set<size_t> ohmic_nodes_;
    std::map<size_t, real_t> ohmic_EFn_, ohmic_EFp_;
    real_t ohmic_ni_ = TCAD_CONST(1.07e16);   // intrinsic density for Boltzmann n(phi)
    std::vector<real_t> eps_;       // Permittivity at each grid point
    std::vector<real_t> edge_eps_x_plus_;
    std::vector<real_t> edge_eps_x_minus_;
    std::vector<real_t> edge_eps_y_plus_;
    std::vector<real_t> edge_eps_y_minus_;
    std::vector<real_t> edge_eps_z_plus_;
    std::vector<real_t> edge_eps_z_minus_;
    std::vector<real_t> Nd_minus_Na_;
    std::vector<real_t> charge_volume_fraction_;
    std::map<size_t, real_t> dirichlet_bc_;
    std::vector<char> is_dirichlet_;

    SparseMatrix A_;
    Vector rhs_;
    LinearSolver solver_;
    bool assembled_ = false;

    // Ferroelectric polarization
    std::vector<char> fe_mask_;
    std::vector<real_t> fe_polarization_;  // [Px,Py,Pz] per node, interleaved, len 3*npts [C/m^2]
    real_t fe_alpha_ = TCAD_CONST(0.0);
    real_t fe_beta_ = TCAD_CONST(0.0);
    real_t fe_gamma_ = TCAD_CONST(0.0);  // LK damping coefficient [V*m/C * s]
    bool fe_enabled_ = false;

    // Ferroelectric model selection + Preisach params (M7c).
    int fe_model_ = 0;            // 0=LK, 1=play Preisach, 2=NLS, 3=Sentaurus Preisach
    real_t fe_ps_ = TCAD_CONST(0.2);         // Preisach saturation polarization [C/m^2]
    real_t fe_ec_ = TCAD_CONST(1.0e9);       // Preisach coercive field [V/m]
    real_t fe_escale_ = TCAD_CONST(0.0);     // Preisach tanh width [V/m]; 0 => Ec (default)
    // Internal field / Imprint offset (P2.1). Subtracted from the applied field
    // to form the effective switching drive E_eff = E - E_bi. 0 => symmetric.
    real_t fe_E_bi_ = TCAD_CONST(0.0);
    // Depolarization field (comments2.docx P3). The bound-charge self-field
    // E_dep = -P / (eps_fe * eps_0) opposes the polarization, limiting it in
    // thin films. eps_fe is the FE relative permittivity; 0 => no depol term.
    real_t fe_eps_fe_ = TCAD_CONST(0.0);     // FE layer relative permittivity (0 => disabled)
    // Under-relaxation factor for P update (comments2.docx): correct div(P)
    // coupling produces stronger P-phi feedback; a relaxation factor < 1
    // stabilises the self-consistent iteration. P_new = relax*P_new + (1-relax)*P_old.
    real_t fe_relax_ = TCAD_CONST(1.0);   // 1.0 = no relaxation (full update)
    // NLS (P3, model==2): Merz-law tau(E) = tau0*exp(E0/|E|).
    real_t fe_nls_tau0_ = TCAD_CONST(1.0e-6);   // characteristic switching time [s]
    real_t fe_nls_E0_ = TCAD_CONST(2.0e9);      // Merz activation field [V/m]
    real_t fe_nls_dt_ = TCAD_CONST(1.0e-6);     // effective dwell time per bias step [s]
    // Preisach internal state. Model 1 uses npts play levels.
    // Model 3 starts with 2*npts entries (previous field, +/-1 direction),
    // followed by ensemble turning-point (field, polarization) pairs, newest
    // first. The final two pairs are the negative/positive saturation limits.
    // Empty under L-K/NLS.
    std::vector<real_t> fe_play_state_;

    // Dielectric breakdown state retained for API compatibility/debugging.
    // It is not assembled into the electrostatic equation.
    std::vector<char> bd_state_;
    real_t sigma_bd_ = TCAD_CONST(0.0);

    // Interface traps (Dit) + bulk oxide traps (P6).
    // trap_mask_[i]==1 marks an interface node; assemble() injects
    // Q_it = -q*D_it*dE*(f_t-0.5) into the Poisson RHS. Q_ot_ is a persistent
    // per-node oxide-trap charge [C/m^3] (evolved externally for retention).
    std::vector<char> trap_mask_;
    real_t trap_D_it_ = TCAD_CONST(0.0);     // interface trap density [cm^-2 eV^-1]
    real_t trap_E_t_ = TCAD_CONST(0.0);      // trap energy level [eV] (rel. intrinsic)
    std::vector<real_t> Q_ot_;    // bulk oxide trap charge [C/m^3]

    // Leakage-current metadata (PF/FN). Poisson only caches the field for
    // compatibility; DeviceSimulator evaluates the explicit edge flux.
    std::vector<char> leak_mask_;
    real_t leak_C_pf_ = TCAD_CONST(0.0), leak_B_pf_ = TCAD_CONST(0.0), leak_phi_t_ = TCAD_CONST(0.0);
    real_t leak_C_fn_ = TCAD_CONST(0.0), leak_B_fn_ = TCAD_CONST(0.0), leak_phi_b_ = TCAD_CONST(0.0);
    real_t leak_E_floor_ = TCAD_CONST(1.0e6);
    real_t leak_sigma_cap_ = TCAD_CONST(0.05);
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
    real_t trap_layer_thickness_ = TCAD_CONST(0.0);

    // Electric field component E_axis = -d(phi)/d(axis) at grid node (i,j,k):
    // central differences interior, one-sided at the domain boundary (the same
    // differencing template as compute_electric_field).
    real_t e_field_component(const std::vector<real_t>& phi,
                             size_t i, size_t j, size_t k, int axis) const;

    // Geometric FE dual volume; boundary half cells, singleton-axis extrusion.
    // Separate from Grid3D::*_cell(), whose boundary stencil uses ghost cells.
    real_t fe_node_volume(size_t i, size_t j, size_t k) const;

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
