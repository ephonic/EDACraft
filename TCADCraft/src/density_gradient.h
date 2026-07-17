#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include "poisson_solver.h"
#include <vector>

namespace tcad {

// Density Gradient (DG) quantum correction
// Adds a quantum potential to the classical carrier densities:
//   n_q = n * exp( - b_n * |grad(sqrt(n))|^2 / (kT) )
// or solves self-consistently for a modified quantum density.
//
// For computational efficiency we use the *partially-coupled* DG model:
//   n_quantum = n_classical * exp( - Q_n / VT )
//   Q_n = b_n * ( grad^2(sqrt(n)) / sqrt(n) )
//
// This class computes the quantum correction term on a structured grid
// and returns corrected carrier densities for the Poisson solver.

class DensityGradient {
public:
    explicit DensityGradient(const Grid3D& grid);

    // Set coefficients b_n, b_p.
    // Phase 3.5 fix (audit §16): units are V·m² (so Qn = b·∇²√n/√n is in
    // volts and exp(-Qn/VT) is dimensionless).  Defaults are the Si
    // DOS-mass values b = ħ²/(6·q·m*) with m*_n=0.26 m_0, m*_p=0.37 m_0
    // (= 4.9e-20 and 3.4e-20 V·m²).  The previous defaults 3.86e-6 were
    // dimensionless, giving Qn ~ 1e10..1e12 and an exponent far outside
    // the solver clamp — DG did nothing useful.
    void set_coefficients(real_t bn, real_t bp);

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

private:
    Grid3D g_;
    // Si DOS-mass DG coefficients (V·m²): ħ²/(6·q·m*) with m*_n=0.26, m*_p=0.37.
    real_t bn_ = 4.885e-20Q;
    real_t bp_ = 3.432e-20Q;
    real_t VT_ = 0.02585Q; // ~300K

    void laplace_sqrt_over_sqrt(const std::vector<real_t>& f,
                                std::vector<real_t>& out) const;
};

} // namespace tcad
