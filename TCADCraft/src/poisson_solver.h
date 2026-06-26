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

    // Persistent vector polarization state (3 components per node, interleaved
    // [Px,Py,Pz]; per-component sign == branch == memory). DeviceSimulator holds
    // the authoritative copy across solve() calls so a Vg sweep produces
    // path-dependent hysteresis. Layout: fe_polarization_[3*idx + c], c=0,1,2.
    const std::vector<real_t>& fe_polarization() const { return fe_polarization_; }
    void set_fe_polarization(const std::vector<real_t>& P) { fe_polarization_ = P; }

    // Update ferroelectric polarization from current potential (self-consistent).
    // Must be called before assemble() when ferroelectric is enabled.
    void update_ferroelectric_polarization(const std::vector<real_t>& phi);

    // Set ferroelectric gamma for transient LK dynamics: E = alpha*P + beta*P^3 + gamma*dP/dt
    void set_ferroelectric_gamma(real_t gamma);

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

    // Stencil coefficients for finite difference/volume
    real_t cx_plus(size_t idx) const;
    real_t cx_minus(size_t idx) const;
    real_t cy_plus(size_t idx) const;
    real_t cy_minus(size_t idx) const;
    real_t cz_plus(size_t idx) const;
    real_t cz_minus(size_t idx) const;
};

} // namespace tcad
