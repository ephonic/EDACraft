#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include "poisson_solver.h"
#include <vector>

namespace tcad {

// Density Gradient (DG) quantum correction
// Adds the Ancona-Stafford/Bohm density-gradient transport potential:
//   Q_n = b_n * grad^2(sqrt(n)) / sqrt(n)
//   n_quantum / n_classical = exp(Q_n / VT)
// and iterates Q, Poisson and continuity to self-consistency. At a confined
// interface density peak Q_n is negative and therefore depletes the peak.
//
// This class computes the quantum correction term on a structured grid
// and returns corrected carrier densities for the Poisson solver.

class DensityGradient {
public:
    explicit DensityGradient(const Grid3D& grid);

    // Set coefficients b_n, b_p.
    // Phase 3.5 fix (audit §16): units are V·m² (so Qn = b·∇²√n/√n is in
    // volts and exp(Qn/VT) is dimensionless).  Defaults are the Si
    // historical scalar-mass values b = ħ²/(6·q·m*) with
    // m*_n=0.26 m_0, m*_p=0.37 m_0
    // (= 4.9e-20 and 3.4e-20 V·m²).  The previous defaults 3.86e-6 were
    // dimensionless, giving Qn ~ 1e10..1e12 and an exponent far outside
    // the solver clamp — DG did nothing useful.
    void set_coefficients(real_t bn, real_t bp);

    // Optional silicon Delta-valley closure for confinement along a <100>
    // axis.  Two valleys use the longitudinal mass normal to the interface;
    // four use the transverse mass. Their 2-D DOS and finite-well subband
    // partition functions determine a local effective electron coefficient.
    // bn remains an overall Sentaurus-calibratable strength multiplier.
    void set_silicon_multivalley(bool enable,
                                 real_t longitudinal_mass = 0.916Q,
                                 real_t transverse_mass = 0.190Q,
                                 size_t subbands = 4);

    // Scale only the mesh distance from an interface semiconductor node to
    // an inactive neighbor. This is a reference-model boundary closure, not
    // a film-thickness correction; 1 uses the literal mesh distance.
    void set_interface_distance_factor(real_t factor);

    // Enable the potential-form inhomogeneous Neumann closure derived from
    // the analytic 1-D material step (Sentaurus Device Eq. 250).  Barrier
    // energies are in eV; barrier masses are relative to m0. Gamma and theta
    // are the parameters of the non-solved barrier material (the 0+ side in
    // Sentaurus Device Eq. 250), not those of the semiconductor. The closure is
    // explicit and opt-in because it requires material-interface parameters
    // that cannot be inferred from the semiconductor mask alone.
    void set_step_boundary(bool enable,
                           real_t electron_barrier_eV,
                           real_t hole_barrier_eV,
                           real_t electron_barrier_mass,
                           real_t hole_barrier_mass,
                           real_t electron_gamma,
                           real_t hole_gamma,
                           real_t electron_theta,
                           real_t hole_theta);

    // Select the potential-form DG fixed-point map used by GummelSolver.
    // This remains opt-in while the Sentaurus calibration matrix is being
    // completed; the density-form map above remains the compatibility path.
    void set_potential_form(bool enable) { potential_form_enabled_ = enable; }
    bool potential_form_enabled() const { return potential_form_enabled_; }

    // Per-node effective density of states used to reconstruct the lagged
    // quasi-Fermi source H = VT*log(carrier/DOS) - Q_reference.
    void set_effective_dos(const std::vector<real_t>& Nc,
                           const std::vector<real_t>& Nv) {
        Nc_ = Nc;
        Nv_ = Nv;
    }

    // Set thermal voltage VT = kB*T/q
    void set_thermal_voltage(real_t VT);

    // Compute quantum-corrected electron and hole densities
    // Input: classical densities n, p (per grid point)
    // Output: corrected densities n_q, p_q
    void correct(const std::vector<real_t>& n,
                 const std::vector<real_t>& p,
                 std::vector<real_t>& n_q,
                 std::vector<real_t>& p_q) const;

    // Compute the quantum potential Q_n, Q_p directly (for inspection)
    void quantum_potential(const std::vector<real_t>& n,
                           const std::vector<real_t>& p,
                           std::vector<real_t>& Qn,
                           std::vector<real_t>& Qp) const;

    // Solve the Sentaurus potential-form DG equation with a lagged
    // quasi-Fermi source. Q_reference is the transport potential from the
    // preceding nonlinear iteration. Equation (250), when enabled, is
    // imposed inside this solve rather than applied as post-processing.
    void quantum_potential_potential_form(
        const std::vector<real_t>& n,
        const std::vector<real_t>& p,
        const std::vector<real_t>& Qn_reference,
        const std::vector<real_t>& Qp_reference,
        std::vector<real_t>& Qn,
        std::vector<real_t>& Qp) const;

    // Semiconductor-region mask (1 = active region where DG applies; 0 =
    // oxide/insulator where DG is suppressed).  Set from mobility (>0 = semi).
    void set_semiconductor_mask(const std::vector<char>& m) { semi_ = m; compute_confinement(); }

private:
    Grid3D g_;
    std::vector<char> semi_;   // empty = treat all nodes as semiconductor
    std::vector<real_t> L_conf_;  // confinement length per node (m)
    std::vector<size_t> N_conf_;  // nodes across the selected confinement axis
    // Scalar Si DG coefficients (V·m²): ħ²/(6·q·m*) with
    // m*_n=0.26, m*_p=0.37. These are not the six-valley DOS masses used by
    // Sentaurus; callers can resolve gamma/m_DOS explicitly through the API.
    // A local multi-valley transverse-mass
    // correction is applied from the computed confinement length.
    real_t bn_ = 4.885e-20Q;
    real_t bp_ = 3.432e-20Q;
    real_t VT_ = 0.02585Q; // ~300K
    bool silicon_multivalley_ = false;
    real_t silicon_ml_ = 0.916Q;  // longitudinal mass / m0
    real_t silicon_mt_ = 0.190Q;  // transverse mass / m0
    size_t silicon_subbands_ = 4;
    real_t interface_distance_factor_ = 1.0Q;
    bool step_boundary_enabled_ = false;
    real_t step_e_barrier_eV_ = 3.17Q;
    real_t step_h_barrier_eV_ = 4.70Q;
    real_t step_e_mass_ = 0.42Q;
    real_t step_h_mass_ = 1.0Q;
    real_t step_e_gamma_ = 1.0Q;
    real_t step_h_gamma_ = 1.0Q;
    real_t step_e_theta_ = 0.5Q;
    real_t step_h_theta_ = 0.5Q;
    bool potential_form_enabled_ = false;
    std::vector<real_t> Nc_, Nv_;

    void laplace_sqrt_over_sqrt(const std::vector<real_t>& f,
                                std::vector<real_t>& out) const;
    void compute_confinement();
    real_t electron_coefficient(size_t idx) const;
    void apply_step_boundary(std::vector<real_t>& Qn,
                             std::vector<real_t>& Qp) const;
    real_t step_boundary_value(real_t interior_lambda, real_t spacing,
                               real_t barrier, real_t mass, real_t gamma,
                               real_t theta) const;
    void second_order_boundary_stencil(real_t first, real_t second,
                                       real_t first_spacing,
                                       real_t second_spacing,
                                       bool has_second,
                                       real_t& effective_interior,
                                       real_t& effective_spacing) const;
};

} // namespace tcad
