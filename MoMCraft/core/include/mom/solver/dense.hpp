// =====================================================================
// mom/solver/dense.hpp - dense direct solve and n-port extraction
// =====================================================================
#pragma once

#include "mom/common/types.hpp"

#include <complex>
#include <vector>

namespace mom::solver {

// Solve Z * I = V for the basis-current vector I.
std::vector<Complex> solve_dense(const std::vector<Complex>& Z,
                                 const std::vector<Complex>& V,
                                 Index nb);

// Extract the reduced n-port impedance matrix seen at the selected basis
// functions. The reduction is done with a Schur complement over the internal
// degrees of freedom, so the result matches the true terminal Z-matrix rather
// than a single-basis readout.
std::vector<Complex> port_impedance_matrix(const std::vector<Index>& port_basis,
                                           const std::vector<Complex>& Z,
                                           Index nb);

// Convert an n-port Z-matrix to S-parameters with a uniform real reference
// impedance z0.
std::vector<Complex> zport_to_sparam(const std::vector<Complex>& Zport,
                                     Real z0, Index nport);

} // namespace mom::solver
