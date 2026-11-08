#pragma once

#include "time_engine/types.hh"

namespace te {

// Timing result for a single pin.
struct PinTimingResult {
    PinId pin;
    Arrival arrival_rise_max;
    Arrival arrival_fall_max;
    Arrival arrival_rise_min;
    Arrival arrival_fall_min;
    Slew slew_rise_max;
    Slew slew_fall_max;
    Slack slack_setup;
    Slack slack_hold;
};

} // namespace te
