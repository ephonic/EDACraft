#pragma once

#include "math_types.h"
#include <algorithm>
#include <vector>

namespace tcad { namespace detail {

// Probe the undamped DG equations without committing their Q. The scales are
// those of the candidate's current fixed-Q Newton system, just as in its merit
// evaluation. This is a residual acceptance check, not a dQ/dn linearization.
template<class Assemble, class Kcl>
bool fresh_quantum_acceptance(
    bool& use_lagged, size_t nodes,
    const std::vector<real_t>& row_scale,
    const std::vector<real_t>& measurement_scale,
    real_t abs_tol, real_t tol, Assemble assemble, Kcl kcl) {
    struct Restore {
        bool& flag;
        bool saved;
        ~Restore() { flag = saved; }
    } restore{use_lagged, use_lagged};
    use_lagged = false;
    if (nodes == 0 || row_scale.size() != 3 * nodes ||
        measurement_scale.size() != 3 * nodes) return false;
    std::vector<real_t> residual;
    assemble(residual);
    if (residual.size() != 3 * nodes) return false;
    real_t blocks[3] = {TCAD_CONST(0.0), TCAD_CONST(0.0), TCAD_CONST(0.0)};
    real_t norm = TCAD_CONST(0.0);
    for (size_t i = 0; i < residual.size(); ++i) {
        const real_t measured = residual[i] * row_scale[i] * measurement_scale[i];
        if (!isfinite_q(residual[i]) || !isfinite_q(measured)) return false;
        blocks[i / nodes] += residual[i] * residual[i];
        norm = std::max(norm, abs_q(measured));
    }
    bool all_abs = true;
    for (real_t block : blocks)
        if (!isfinite_q(block) || !(sqrt_q(block) < abs_tol)) all_abs = false;
    return (all_abs || norm < tol) && kcl();
}

}} // namespace tcad::detail
