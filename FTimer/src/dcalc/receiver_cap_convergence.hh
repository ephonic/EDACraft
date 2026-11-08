#pragma once

#include "rc_waveform_dcalc.hh"
#include <cmath>

namespace te {

// Receiver C1/C2 are expressed in extraction units. A meaningful update must
// exceed both 0.1 fF and 1% of the previous value, independently per region.
// Below that tolerance the original waveform remains the accepted solution.
inline bool receiver_caps_need_refinement(
    const std::vector<RcReceiverCapacitance>& before,
    const std::vector<RcReceiverCapacitance>& after, double cap_scale) {
    if (before.size() != after.size()) return true;
    const double absolute_tolerance = 1e-16 / cap_scale;
    const auto changed = [absolute_tolerance](double old_cap, double new_cap) {
        const double difference = std::fabs(new_cap - old_cap);
        return difference > absolute_tolerance && difference > .01 * std::fabs(old_cap);
    };
    for (size_t i = 0; i < before.size(); ++i) {
        if (before[i].node != after[i].node ||
            changed(before[i].first, after[i].first) ||
            changed(before[i].second, after[i].second)) return true;
    }
    return false;
}

} // namespace te
