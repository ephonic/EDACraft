#pragma once

#include <algorithm>
#include <cmath>
#include <vector>
#include <unordered_set>
#include "graph/timing_graph.hh"
#include "network/network.hh"

namespace te {

// Find the last common physical pin on the selected early/late clock routes.
// Routes may diverge and rejoin before that pin. Source latency alone is not
// evidence of a shared path; opposite source transitions never cancel.
inline float clock_path_pessimism(const TimingGraph& graph, uint32_t launch_clock,
                                  uint32_t capture_clock, MinMax data_mode) {
    const auto capture_mode = data_mode == MinMax::Max ? MinMax::Min : MinMax::Max;
    auto route = [&](uint32_t vid, MinMax mode) {
        std::vector<uint32_t> vertices;
        for (size_t count = 0; vid < graph.vertex_count() && count < graph.vertex_count(); ++count) {
            vertices.push_back(vid);
            const auto rf = graph.vertex_transition(vid);
            const auto previous = mode == MinMax::Max ? graph.pred_max(vid, mode, rf) : graph.pred_min(vid, mode, rf);
            if (previous == UINT32_MAX) break;
            vid = previous;
        }
        return vertices;
    };
    const auto launch = route(launch_clock, data_mode), capture = route(capture_clock, capture_mode);
    if (launch.empty() || capture.empty() || launch.back()!=capture.back()) return 0;
    const std::unordered_set<uint32_t> capture_vertices(capture.begin(),capture.end());
    for (const auto common : launch) if (capture_vertices.count(common)) {
        const auto rf = graph.vertex_transition(common);
        const float a = graph.arrival(common,data_mode,rf).value;
        const float b = graph.arrival(common,capture_mode,rf).value;
        const float correction = data_mode == MinMax::Max ? a-b : b-a;
        return std::isfinite(correction) ? std::max(0.f,correction) : 0.f;
    }
    return 0;
}

inline float check_clock_pessimism(const TimingGraph& graph, const Network& network,
    uint32_t start, uint32_t capture, MinMax mm) {
    if (start >= graph.vertex_count()) return 0;
    const auto& pin = network.pin(graph.vertex_pin(start));
    if (!valid(pin.instance)) return 0;
    const auto clock_pin = graph.instance_clk_pin(pin.instance.id);
    if (clock_pin == UINT32_MAX) return 0;
    // The chosen clock-to-Q predecessor retains the actual launch edge,
    // including inversion. It is deliberately outside the data startpoint.
    const auto rf = graph.vertex_transition(start);
    const auto predecessor = mm == MinMax::Max ? graph.pred_max(start, mm, rf) : graph.pred_min(start, mm, rf);
    if (predecessor == UINT32_MAX || graph.vertex_pin(predecessor).id != clock_pin) return 0;
    return clock_path_pessimism(graph, predecessor, capture, mm);
}
} // namespace te
