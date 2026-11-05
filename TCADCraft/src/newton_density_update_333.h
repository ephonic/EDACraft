#pragma once
#include "math_types.h"
namespace tcad {
// Interpret a log-Jacobian correction du as the relative physical density
// correction dn/n. The proposed physical density is n*(1+step).
// Reject invalid proposals atomically; caller must shorten the trial first.
// Valid output may still round to u for sub-resolution steps.
inline bool additive_density_log_update_333(real_t u,real_t step,real_t& output) {
    if (!isfinite_q(u) || !isfinite_q(step) || step <= -TCAD_CONST(1.0))
        return false;
#ifdef TCAD_USE_FLOAT128
    const real_t increment=log1pq(step);
#else
    const real_t increment=log1pl(step);
#endif
    const real_t candidate=u+increment;
    if (!isfinite_q(candidate)) return false;
    output=candidate;
    return true;
}
}
