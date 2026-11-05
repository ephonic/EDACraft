#include "math_types.h"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

static void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    using namespace tcad;
    try {
        // The consumer sees the PUBLIC header definition; the out-of-line
        // identity and decimal value come from the linked library object.
        check(std::string(constants_profile_name()) == compiled_constants_profile_name(),
              "constants profile mismatch between consumer and core");
#ifdef TCAD_CONSTANTS_LEGACY_CHARGE
        const real_t expected = TCAD_CONST(1.602192e-19);
#else
        const real_t expected = TCAD_CONST(1.602176634e-19);
#endif
        check(QE == expected, "header charge differs from the selected profile");
        const std::string decimal = compiled_elementary_charge_decimal();
        char* end = nullptr;
#ifdef TCAD_USE_FLOAT128
        const real_t compiled = strtoflt128(decimal.c_str(), &end);
#else
        const real_t compiled = std::strtold(decimal.c_str(), &end);
#endif
        check(end && *end == '\0' && compiled == QE,
              "compiled charge does not round-trip to the consumer charge");
        check(KB == TCAD_CONST(1.380649e-23) && EPS0 == TCAD_CONST(8.854187817e-12),
              "charge selection changed another shared constant");
        std::cout << "profile=" << compiled_constants_profile_name()
                  << " charge_C=" << decimal
                  << " mantissa_bits=" << real_mantissa_bits() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
