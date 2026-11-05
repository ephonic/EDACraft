#include "device_simulator.h"
#include "device_simulator_double.h"
#include <array>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace tcad;
namespace {
size_t checks = 0;
template<class Call> void rejects(Call call) {
    try { call(); }
    catch (const std::invalid_argument&) { ++checks; return; }
    throw std::runtime_error("invalid transport parameters were accepted");
}
template<class Sim, class Scalar> void invalid_parameters(Sim& sim) {
    const Scalar inf = static_cast<Scalar>(std::numeric_limits<double>::infinity());
    const Scalar nan = static_cast<Scalar>(std::numeric_limits<double>::quiet_NaN());
    for (size_t slot = 0; slot < 4; ++slot) {
        for (Scalar bad : {Scalar(-1), Scalar(0), inf, -inf, nan}) {
            std::array<Scalar, 4> p = {Scalar(5e4), Scalar(4e4), Scalar(2), Scalar(1)};
            p[slot] = bad;
            rejects([&] { sim.set_high_field_saturation(false, p[0], p[1], p[2], p[3], 1); });
        }
        for (Scalar bad : {Scalar(-1), inf, -inf, nan}) {
            std::array<Scalar, 4> p = {Scalar(10), Scalar(0), Scalar(20), Scalar(0)};
            p[slot] = bad;
            rejects([&] { sim.set_ii_params(p[0], p[1], p[2], p[3]); });
        }
    }
    for (int driving : {-1, 2, 7})
        rejects([&] { sim.set_high_field_saturation(true, 5e4, 4e4, 2, 1, driving); });
    sim.set_ii_params(0, 0, 0, 0);
    ++checks;
}
}

int main() {
    try {
        DeviceSimulator native(2, 1, 1, TCAD_CONST(1e-6), 1, 1);
        DeviceSimulatorDouble facade(2, 1, 1, 1e-6, 1, 1);
        invalid_parameters<DeviceSimulator, real_t>(native);
        invalid_parameters<DeviceSimulatorDouble, double>(facade);
        size_t wide_checks = 0;
        if (real_max_decimal_exponent() > std::numeric_limits<double>::max_exponent10) {
            // Setter range contract only; no claim that huge physical parameters
            // yield a well-conditioned or solvable device.
            const real_t wide = static_cast<real_t>(std::numeric_limits<double>::max()) * 2;
            if (!isfinite_q(wide)) throw std::runtime_error("wide native fixture overflow");
            for (size_t slot = 0; slot < 4; ++slot) {
                std::array<real_t, 4> p = {5e4, 4e4, 2, 1};
                p[slot] = wide;
                native.set_high_field_saturation(true, p[0], p[1], p[2], p[3], 1);
                native.set_ii_params(p[0], p[1], p[2], p[3]);
                checks += 2; wide_checks += 2;
            }
        }
        std::cout << "{\"checks\":" << checks << ",\"wide_native_checks\":"
                  << wide_checks << ",\"mantissa_bits\":" << real_mantissa_bits()
                  << ",\"profile\":\"" << compiled_constants_profile_name() << "\"}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
