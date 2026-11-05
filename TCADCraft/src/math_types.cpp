#include "math_types.h"
#include <cstdio>

// Implementation file for any non-inline math utilities
namespace tcad {

const char* compiled_constants_profile_name() {
    return constants_profile_name();
}

std::string compiled_elementary_charge_decimal() {
    char value[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(value, sizeof(value), "%.40Qg", QE);
#else
    std::snprintf(value, sizeof(value), "%.40Lg", QE);
#endif
    return value;
}

} // namespace tcad
