#include "math_types.h"
#include "linear_solver.h"
#include <iostream>
#include <stdexcept>
#include <type_traits>
using namespace tcad;

static_assert(std::is_same<decltype(TCAD_CONST(0.1)), real_t>::value,
              "constants must use the scalar backend, without mixed arithmetic");
static_assert(std::is_same<decltype(TCAD_CONST(0.1) + real_t(1)), real_t>::value,
              "arithmetic must not promote long double back to software quad");

static void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
int main() {
    try {
        const real_t one = TCAD_CONST(1.0), epsilon = epsilon_q();
        check(real_mantissa_bits() >= 53, "invalid scalar precision");
        check(one + epsilon > one && one + epsilon / 2 == one,
              "reported epsilon does not describe native arithmetic");
        // An increment below double resolution must survive in extended types.
        const real_t increment = TCAD_CONST(1e-18);
        if (real_mantissa_bits() > 53)
            check(one + increment > one, "scalar arithmetic silently narrowed to double");
        const real_t tiny = TCAD_CONST(1e-40);
        check(abs_q(expm1_q(tiny) / tiny - one) <= 8 * epsilon,
              "expm1 lost a representable short-time increment");
        const real_t large = TCAD_CONST(1e300);
        check(abs_q(log_q(exp_q(TCAD_CONST(100.0))) - TCAD_CONST(100.0)) < 1000 * epsilon,
              "native exponential/log wrappers disagree");
        check(isfinite_q(large * large), "scalar exponent range collapsed to double");
        SparseMatrix matrix(3);
        matrix.add_entry(0,0,one);
        matrix.add_entry(1,0,TCAD_CONST(-1e-80));
        matrix.add_entry(1,1,TCAD_CONST(4e-80));
        matrix.add_entry(1,2,TCAD_CONST(-1e-80));
        matrix.add_entry(2,2,one); matrix.finalize();
        Vector expected{one,TCAD_CONST(2.0),TCAD_CONST(3.0)};
        Vector rhs=matrix.apply(expected), actual(3,0);
        SolverOptions options; options.type=SolverType::DENSE_DIRECT;
        LinearSolver solver(options);
        check(solver.solve(matrix,rhs,actual), "scaled native dense solve failed");
        for (size_t i=0;i<3;++i)
            check(abs_q(actual[i]-expected[i]) < 100 * epsilon,
                  "scaled native dense solution differs from analytic reference");
        std::cout << "backend=" << (uses_float128()?"float128":"long_double")
                  << " mantissa_bits=" << real_mantissa_bits()
                  << " max_decimal_exponent=" << real_max_decimal_exponent() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
