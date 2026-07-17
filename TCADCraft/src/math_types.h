#pragma once

#include <cmath>
#include <cstddef>

// Platform-specific 128-bit support
// Note: __SIZEOF_FLOAT128__ is not defined on all targets that support
// __float128 (e.g. Apple Silicon / aarch64 with gcc).  Detect via
// __GNUC__ and the availability of the type itself, gated on the
// -fext-numeric-literals flag (set in setup.py) which enables the q-suffix.
#if (defined(__GNUC__) || defined(__clang__)) && !defined(__SIZEOF_FLOAT128__)
    // Probe: __float128 may still be available even without the macro.
    #define TCAD_HAS_FLOAT128_TYPE 1
#endif
#if defined(__SIZEOF_FLOAT128__) || defined(TCAD_HAS_FLOAT128_TYPE)
    #define TCAD_USE_FLOAT128
    #include <quadmath.h>
#endif

namespace tcad {

#ifdef TCAD_USE_FLOAT128
    using real_t = __float128;
    #define TCAD_CONST(x) (x##Q)
#else
    // Fallback: long double (80-bit on x86_64 Linux, 64-bit on Apple Silicon)
    // For true 128-bit on unsupported platforms, use boost::multiprecision
    using real_t = long double;
    #define TCAD_CONST(x) (x##L)
#endif

// Constants
constexpr real_t PI = TCAD_CONST(3.141592653589793238462643383279502884);
constexpr real_t EPSILON = TCAD_CONST(1e-20);  // Small value for numerical stability
constexpr real_t KB = TCAD_CONST(1.380649e-23); // Boltzmann constant [J/K]
constexpr real_t QE = TCAD_CONST(1.602176634e-19); // Elementary charge [C]
constexpr real_t EPS0 = TCAD_CONST(8.854187817e-12); // Vacuum permittivity [F/m]

// Math wrappers
#ifdef TCAD_USE_FLOAT128
    inline real_t sqrt_q(real_t x) { return sqrtq(x); }
    inline real_t exp_q(real_t x) { return expq(x); }
    inline real_t expm1_q(real_t x) { return expm1q(x); }
    inline real_t log_q(real_t x) { return logq(x); }
    inline real_t pow_q(real_t x, real_t y) { return powq(x, y); }
    inline real_t sinh_q(real_t x) { return sinhq(x); }
    inline real_t cosh_q(real_t x) { return coshq(x); }
    inline real_t tanh_q(real_t x) { return tanhq(x); }
    inline real_t abs_q(real_t x) { return fabsq(x); }
#else
    inline real_t sqrt_q(real_t x) { return sqrtl(x); }
    inline real_t exp_q(real_t x) { return expl(x); }
    inline real_t expm1_q(real_t x) { return expm1l(x); }
    inline real_t log_q(real_t x) { return logl(x); }
    inline real_t pow_q(real_t x, real_t y) { return powl(x, y); }
    inline real_t sinh_q(real_t x) { return sinhl(x); }
    inline real_t cosh_q(real_t x) { return coshl(x); }
    inline real_t tanh_q(real_t x) { return tanhl(x); }
    inline real_t abs_q(real_t x) { return fabsl(x); }
#endif

// Convert to/from double for I/O
inline double to_double(real_t x) { return (double)x; }
inline real_t from_double(double x) { return (real_t)x; }

} // namespace tcad
