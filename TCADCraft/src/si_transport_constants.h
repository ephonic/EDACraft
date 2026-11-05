#pragma once
#include "math_types.h"

namespace tcad {
namespace si_transport {
// Cut-cell spectral APIs exchange SI charge/energy with Python SI models and
// independent auditors. Their charge must not inherit the separate classical
// drift-diffusion legacy-charge compatibility profile.
constexpr real_t elementary_charge = TCAD_CONST(1.602176634e-19);
inline double charge_as_double() { return static_cast<double>(elementary_charge); }
} // namespace si_transport
} // namespace tcad
