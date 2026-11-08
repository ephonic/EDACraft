#pragma once

#include <algorithm>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"

namespace te {
// ────────────────────────────────────────────────────────────
// NLDM Gate Delay Calculator
// ────────────────────────────────────────────────────────────
// Computes gate delay and output slew from NLDM 2D tables.
// Lookup: (input_slew, load_cap) → (delay, output_slew)

struct ArcDcalcResult {
    Delay delay;       // gate delay
    Slew output_slew;  // output transition
};

class NldmDelayCalc {
public:
    NldmDelayCalc() = default;

    // Compute gate delay for a specific arc.
    ArcDcalcResult gate_delay(
        const edacraft::core::NldmTable& delay_table,
        const edacraft::core::NldmTable& slew_table,
        float input_slew,
        float load_cap
    ) const;
};

// ────────────────────────────────────────────────────────────
// Inline implementations
// ────────────────────────────────────────────────────────────
inline ArcDcalcResult NldmDelayCalc::gate_delay(
    const edacraft::core::NldmTable& delay_table,
    const edacraft::core::NldmTable& slew_table,
    float input_slew,
    float load_cap
) const {
    ArcDcalcResult result;
    result.delay.value = delay_table.lookup(input_slew, load_cap);
    result.output_slew.value = std::max(0.0f, slew_table.lookup(input_slew, load_cap));
    return result;
}

} // namespace te
