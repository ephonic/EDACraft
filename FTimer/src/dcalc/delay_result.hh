#pragma once

#include <cstdint>

#include "time_engine/types.hh"

namespace te {

enum class DelayModelSource : uint8_t {
    None,
    Nldm,
    Csm,
    AwePi,
    Lumped,
};

struct DelayResult {
    Delay delay{0.0f};
    Slew output_slew{0.0f};
    float ceff = 0.0f;
    DelayModelSource source = DelayModelSource::None;
    bool converged = true;
    // Provenance of a selected CCS response, retained by label/alias caches.
    // Empirical T12 net fits must never alter unrelated analytic waveforms.
    bool ccs_local_fit = false;
};

} // namespace te
