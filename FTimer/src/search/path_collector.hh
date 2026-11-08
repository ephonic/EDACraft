#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "time_engine/types.hh"
#include "sdc/resolved_constraints.hh"

namespace te {

class TimingGraph;

// Collects worst paths for reporting.
struct PathInfo {
    float slack;
    float cppr;  // Common Path Pessimism Removal
    uint32_t start_clock_domain = UINT32_MAX;
    uint32_t end_clock_domain = UINT32_MAX;
    std::vector<std::string> point_names;
    std::vector<std::string> cell_names;
    std::vector<float> delays;
    std::vector<float> arrivals;
    std::vector<float> slews;
    std::vector<std::string> transitions;
    bool top_output = false;
    TimingCheckKind check_kind = TimingCheckKind::None;
    std::optional<TimingCheckResult> check;
    std::string path_group;
};

class Network;

class PathCollector {
public:
    static std::vector<PathInfo> collect_check_paths(
        const TimingGraph& graph, const Network& network, MinMax mm, int count,
        const ResolvedConstraintSet* sdc = nullptr,
        TimingCheckKind kind = TimingCheckKind::Any, bool balance_groups = false,
        std::string_view path_group = {});
    // Collect worst N paths by slack with full path back-trace.
    static std::vector<PathInfo> collect_worst_paths(
        const TimingGraph& graph,
        const Network& network,
        MinMax mm,
        int count,
        const ResolvedConstraintSet* sdc = nullptr,
        bool sort_by_data_delay = false,
        TimingCheckKind kind = TimingCheckKind::Any,
        std::string_view path_group = {}
    );
};

} // namespace te
