#pragma once

#include "rc_waveform_dcalc.hh"
#include "parasitics/rc_topology.hh"
#include <algorithm>
#include <cmath>
#include <limits>

namespace te {

// PT's initial receiver protocol uses an RC time criterion, in femtoseconds,
// rather than a resistance threshold. Preserve both integer time conversions
// and the float capacitance/resistance products observed in the native solve.
inline bool receiver_uses_lumped_initialization(
    const FullRcNetwork& rc, const std::vector<RcReceiverCapacitance>& receivers) {
    if (receivers.empty() || !(rc.cap_scale > 0.f)) return false;
    // Native initialization bypasses the lumped prepass above nine sinks.
    // Count observation nodes, not resistor subdivisions or alias spellings.
    const auto sinks = std::count_if(rc.nodes.begin(),rc.nodes.end(),[&](const auto& node) {
        return node.id != rc.driver_node_id && valid(node.pin);
    });
    if (sinks > 9) return false;
    double wire = 0., first = 0., second = 0.;
    for (const auto& node : rc.nodes) wire += node.gnd_cap;
    for (const auto& cap : receivers) {
        if (!(cap.nominal_first > 0.f && cap.nominal_second > 0.f)) return false;
        wire -= std::max(cap.first, cap.second);
        first += cap.nominal_first;
        second += cap.nominal_second;
    }
    const double decimal = std::pow(10., std::round(std::log10(double(rc.cap_scale))));
    const double scale = (double(rc.cap_scale) == double(float(decimal))
                          ? decimal : double(rc.cap_scale)) / 1e-12;
    const float wire_pf = float(std::max(0., wire) * scale);
    const float nominal_pf = float(std::max(first, second) * scale);
    const float total_pf = wire_pf + nominal_pf;
    const float resistance_kohms = float(summarize_rc_resistance_ohms(rc).sum * .001);
    const float rc_ns = resistance_kohms * total_pf;
    const double raw_fs = double(rc_ns) * 1e6;
    if (!(raw_fs >= 0.) || raw_fs > std::numeric_limits<int>::max()) return false;
    const double ratio = (double(total_pf) + 2e-5) / (double(wire_pf) + 1e-5);
    const double criterion_fs = int(raw_fs) * ratio;
    return std::isfinite(criterion_fs) && criterion_fs >= 0. && criterion_fs < 20000.;
}

} // namespace te
