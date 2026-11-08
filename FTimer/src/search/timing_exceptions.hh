#pragma once

#include <cstdint>
#include <algorithm>
#include <vector>

#include "edacraft/core/resolved_constraint_set.hpp"
#include "graph/timing_graph.hh"
#include "sdc/resolved_constraints.hh"

namespace te {

inline bool timing_exception_pin_in_list(PinId pin, const std::vector<PinId>& pins) {
    for (auto p : pins) {
        if (p == pin) return true;
    }
    return false;
}

inline bool timing_exception_cuts_edge(const TimingGraph&,
                                       const ResolvedConstraintSet*,
                                       uint32_t, uint32_t) {
    // Clock-group exceptions belong to a launch/capture pair. Intermediate
    // domains do not identify that pair at reconvergence; filter the endpoint
    // launch labels instead, and characterize every data edge here.
    // False paths are also launch/history/capture predicates. Characterize
    // the complete graph; endpoint labels apply them without losing an
    // unexcluded branch that reconverges with a false route.
    return false;
}

inline uint64_t advance_false_path_history(TimingGraph& graph,
    const ResolvedConstraintSet* sdc, uint64_t key, PinId pin, Transition rf, bool seed = false) {
    if (!sdc || (sdc->false_paths().empty() && sdc->max_delays().empty() &&
        sdc->min_delays().empty() && sdc->multicycle_paths().empty())) return key;
    return graph.advance_false_path_history(key, pin, seed, rf);
}

inline bool false_path_applies_to_analysis(const ResolvedConstraintSet::FalsePath& fp, MinMax mm) {
    return mm == MinMax::Max ? fp.setup : fp.hold;
}

inline size_t path_delay_history_index(const ResolvedConstraintSet& sdc,MinMax mm,size_t index) {
    return sdc.false_paths().size()+3*(index+(mm==MinMax::Min?sdc.max_delays().size():0));
}

template<class Path>
inline bool exception_clock_matches(const Path& path, const LaunchTimingLabel* launch,
                                    uint32_t capture) {
    const auto contains = [](const auto& clocks, uint32_t domain) {
        return domain != UINT32_MAX && std::find(clocks.begin(),clocks.end(),domain)!=clocks.end();
    };
    return (path.from_clocks.empty() || (launch && contains(path.from_clocks,launch->domain))) &&
           (path.to_clocks.empty() || contains(path.to_clocks,capture));
}
template<class Path>
inline bool path_delay_matches(const TimingGraph& graph,const ResolvedConstraintSet& sdc,
    const LaunchTimingLabel* launch,const Path& path,MinMax mm,size_t index,PinId endpoint,
    uint32_t capture=UINT32_MAX) {
    if(capture==UINT32_MAX)capture=graph.vertex_clock_domain(endpoint.id*2);
    if(!exception_clock_matches(path,launch,capture))return false;
    if(!path.to_pins.empty() && !timing_exception_pin_in_list(endpoint,path.to_pins))return false;
    if(!launch)return path.from_pins.empty() && path.through_pins.empty();
    const auto stages=path.through_pins.empty()?0:1+path.through_stages.size();
    const uint32_t complete=stages?uint32_t(stages*2+1):3u;
    return graph.launch_history(launch->key).at(path_delay_history_index(sdc,mm,index))==complete;
}
inline bool multicycle_matches(const TimingGraph& graph,const ResolvedConstraintSet& sdc,
    const LaunchTimingLabel* launch,size_t index,PinId endpoint,uint32_t capture=UINT32_MAX) {
    const auto& path=sdc.multicycle_paths()[index];
    if(capture==UINT32_MAX)capture=graph.vertex_clock_domain(endpoint.id*2);
    if(!exception_clock_matches(path,launch,capture))return false;
    if(!path.to_pins.empty() && !timing_exception_pin_in_list(endpoint,path.to_pins))return false;
    if(!launch)return path.from_pins.empty();
    const auto slot=sdc.false_paths().size()+3*(sdc.max_delays().size()+sdc.min_delays().size())+index;
    return graph.launch_history(launch->key).at(slot)==3u;
}

// Setup and hold are independent exceptions on the same path. Hold moves
// back from the setup relation; its default period is the launch period,
// while setup defaults to the capture period. Do not stop on the setup
// record and discard the matching hold record (including an explicit zero).
inline float multicycle_relation_shift(const TimingGraph& graph,
    const ResolvedConstraintSet& sdc, const LaunchTimingLabel* launch,
    PinId endpoint, uint32_t capture, MinMax mm) {
    if (capture >= sdc.clocks().size()) return 0.f;
    const float capture_period = sdc.clocks()[capture].period;
    const float launch_period = launch && launch->domain < sdc.clocks().size()
        ? sdc.clocks()[launch->domain].period : capture_period;
    const ResolvedConstraintSet::MulticyclePath* setup = nullptr;
    const ResolvedConstraintSet::MulticyclePath* hold = nullptr;
    for (size_t i = 0; i < sdc.multicycle_paths().size(); ++i) {
        if (!multicycle_matches(graph, sdc, launch, i, endpoint, capture)) continue;
        const auto& rule = sdc.multicycle_paths()[i];
        if (rule.is_hold) hold = &rule;
        else setup = &rule;
    }
    float shift = setup ? (setup->setup_cycles - 1) *
        (setup->use_start ? launch_period : capture_period) : 0.f;
    if (mm == MinMax::Min) {
        if (hold) shift -= hold->hold_cycles *
            (hold->use_start ? launch_period : capture_period);
        // Preserve the public API's legacy combined setup/hold record.
        else if (setup && setup->hold_cycles > 0)
            shift -= setup->hold_cycles * launch_period;
    }
    return shift;
}

inline bool false_path_excludes_launch(const TimingGraph& graph,
    const ResolvedConstraintSet* sdc, uint32_t endpoint, MinMax mm, const LaunchTimingLabel& launch,
    uint32_t capture=UINT32_MAX) {
    if (!sdc || sdc->false_paths().empty()) return false;
    const auto& history = graph.launch_history(launch.key);
    for (size_t i = 0; i < sdc->false_paths().size(); ++i) {
        const auto& fp = sdc->false_paths()[i];
        if(capture==UINT32_MAX)capture=graph.vertex_clock_domain(endpoint);
        if(!exception_clock_matches(fp,&launch,capture))continue;
        if (!false_path_applies_to_analysis(fp, mm)) continue;
        if (!(fp.to_transitions & (1u << unsigned(graph.vertex_transition(endpoint))))) continue;
        if (fp.from_pins.empty() && fp.to_pins.empty() && fp.through_pins.empty() &&
            fp.from_clocks.empty() && fp.to_clocks.empty()) continue;
        const auto stages = fp.through_pins.empty() ? 0 : 1 + fp.through_stages.size();
        const auto complete = stages == 0 ? uint32_t(3) : (uint32_t(stages) << 1) | 1;
        if (history[i] == complete && (fp.to_pins.empty() ||
            timing_exception_pin_in_list(graph.vertex_pin(endpoint), fp.to_pins))) return true;
    }
    return false;
}

} // namespace te
