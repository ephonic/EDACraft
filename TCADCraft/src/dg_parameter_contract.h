#pragma once

#include "math_types.h"
#include <initializer_list>
#include <stdexcept>

namespace tcad { namespace detail {
// Native DG entry contracts preserve finite zero/negative/fallback values.
// Test in real_t so a finite float128 value wider than double stays finite.
inline void validate_dg_finite(std::initializer_list<real_t> values,
                               const char* message) {
    for (real_t value : values)
        if (!isfinite_q(value)) throw std::invalid_argument(message);
}
} } // namespace tcad::detail
