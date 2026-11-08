#pragma once

#include "parasitics/timing_parasitics.hh"
#include <algorithm>
#include <array>

namespace te {

// The output-load coordinate of a CCS receiver table is estimated before
// solving its output waveform. It is distinct from the final gate Ceff.
// Late and early propagation use the lower and upper raw RF envelopes,
// respectively. Select before the RC estimate, which is not monotonic in C.
inline float receiver_output_load(const std::array<float, 2>& totals,
                                  float cap_unit_farads,
                                  const FullRcNetwork* rc, unsigned fanout, bool late = true) {
    const float total = late ? std::min(totals[0], totals[1]) : std::max(totals[0], totals[1]);
    if (!rc || !fanout || !(total > 0.f)) return total;
    float resistance_kohm = 0.f;
    for (const auto& resistor : rc->resistors)
        resistance_kohm += resistor.resistance * rc->res_scale * .001f;
    const float capacitance_pf = total * (cap_unit_farads / 1e-12f);
    const float tau_ns = float(resistance_kohm * capacitance_pf) / float(fanout);
    const double factor = tau_ns < .01 ? 1. : tau_ns >= .15 ? .3 :
        1.05 - .005 * double(float(1000.f * tau_ns));
    return float(double(total) * factor);
}

} // namespace te
