#pragma once

#include <cstdint>
#include <vector>
#include <unordered_map>

#include "parasitics/timing_parasitics.hh"

namespace te {

// Compute Elmore delay from driver to each load pin in an RC network.
// Returns a map: load_pin_id → Elmore delay (in same time units as R*C)
struct ElmoreResult {
    std::unordered_map<uint32_t, float> pin_delay;   // pin_id → delay (ps)
    std::unordered_map<uint32_t, float> pin_impulse; // pin_id → impulse (ps²)
    float total_load_cap = 0.0f;                     // sum of all ground caps (fF)
    float sum_r_c2 = 0.0f;                           // Σ R_edge·C_subtree² (raw RC units)
    float rc_to_ps = 1.0f;                           // conversion factor from raw RC to ps
};

ElmoreResult compute_elmore_delays(const FullRcNetwork& rc);

} // namespace te
