#ifndef EDACRAFT_CORE_RESOLVED_CONSTRAINT_SET_HPP
#define EDACRAFT_CORE_RESOLVED_CONSTRAINT_SET_HPP

#include "edacraft/core/ids.hpp"
#include "edacraft/core/constraint_db.hpp"

#include <algorithm>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace edacraft::core {

template <typename PinHandleT>
struct BasicResolvedClock {
    uint32_t name = UINT32_MAX;
    float period = 0.0f;
    float transition = 0.0f;
    float rise_time = -1.0f;
    float fall_time = -1.0f;
    float latency = 0.0f;
    std::vector<PinHandleT> sources;
    uint32_t master_clock = UINT32_MAX;
    PinHandleT generated_source{};
    bool generated = false;
    bool propagated = false;
};

enum class ResolvedClockGroupMode {
    Asynchronous,
    LogicallyExclusive,
    PhysicallyExclusive
};

struct ResolvedClockGroup {
    ResolvedClockGroupMode mode = ResolvedClockGroupMode::Asynchronous;
    std::vector<std::vector<uint32_t>> groups;
};

inline bool resolved_clock_groups_cut_path(
    const std::vector<ResolvedClockGroup>& clock_groups,
    uint32_t launch_clock,
    uint32_t capture_clock) {
    if (launch_clock == UINT32_MAX || capture_clock == UINT32_MAX ||
        launch_clock == capture_clock) {
        return false;
    }

    for (const auto& group_def : clock_groups) {
        int launch_group = -1;
        int capture_group = -1;
        for (size_t group_idx = 0; group_idx < group_def.groups.size(); ++group_idx) {
            const auto& group = group_def.groups[group_idx];
            if (std::find(group.begin(), group.end(), launch_clock) != group.end()) {
                launch_group = static_cast<int>(group_idx);
            }
            if (std::find(group.begin(), group.end(), capture_clock) != group.end()) {
                capture_group = static_cast<int>(group_idx);
            }
        }
        if (launch_group >= 0 && capture_group >= 0 &&
            launch_group != capture_group) {
            return true;
        }
    }
    return false;
}

template <typename PinHandleT, typename TransitionT>
struct BasicResolvedInputDelay {
    float delay = 0.0f;
    uint32_t clock = UINT32_MAX;
    TransitionT clock_edge = TransitionT::Rise;
    bool is_max = true;
    std::vector<PinHandleT> ports;
};

template <typename PinHandleT, typename TransitionT>
struct BasicResolvedOutputDelay {
    float delay = 0.0f;
    uint32_t clock = UINT32_MAX;
    TransitionT clock_edge = TransitionT::Rise;
    bool is_max = true;
    std::vector<PinHandleT> ports;
};

template <typename PinHandleT>
struct BasicResolvedSetLoad {
    float capacitance = 0.0f;
    std::vector<PinHandleT> pins;
};

template <typename PinHandleT>
struct BasicResolvedInputTransition {
    float transition = 0.0f;
    std::vector<PinHandleT> ports;
    bool rise = true;
    bool fall = true;
    bool min = true, max = true;
    uint64_t order = 0;
};

template <typename PinHandleT>
struct BasicResolvedDrivingCell {
    DrivingCellDef model;
    std::vector<PinHandleT> ports;
};

template <typename PinHandleT>
struct BasicResolvedClockLatency {
    float latency = 0.0f;
    uint32_t clock = UINT32_MAX;
    std::vector<PinHandleT> pins;
};

template <typename PinHandleT>
struct BasicResolvedClockUncertainty {
    float setup_uncertainty = 0.0f;
    float hold_uncertainty = 0.0f;
    uint32_t clock = UINT32_MAX;
    std::vector<PinHandleT> pins;
};

template <typename PinHandleT>
struct BasicResolvedCaseAnalysis {
    enum Value { Zero = 0, One = 1, Rise = 2, Fall = 3 };
    Value value = Zero;
    PinHandleT pin{UINT32_MAX};
};

template <typename PinHandleT>
struct BasicResolvedMaxDelay {
    float delay = 0.0f;
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> to_pins;
    std::vector<PinHandleT> through_pins;
    std::vector<std::vector<PinHandleT>> through_stages;
    std::vector<uint32_t> from_clocks, to_clocks;
    bool ignore_clock_latency = false;
};

template <typename PinHandleT>
struct BasicResolvedMinDelay {
    float delay = 0.0f;
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> to_pins;
    std::vector<PinHandleT> through_pins;
    std::vector<std::vector<PinHandleT>> through_stages;
    std::vector<uint32_t> from_clocks, to_clocks;
    bool ignore_clock_latency = false;
};

template <typename PinHandleT, typename TransitionT>
struct BasicResolvedDataCheck {
    float delay = 0.0f;
    bool is_setup = true;
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> to_pins;
    uint8_t from_transitions = 3;
    uint8_t to_transitions = 3;
};

template <typename PinHandleT>
struct BasicResolvedMulticyclePath {
    int setup_cycles = 1;
    int hold_cycles = 0;
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> to_pins;
    std::vector<uint32_t> from_clocks, to_clocks;
    bool is_hold = false;
    bool use_start = false;
};

template <typename PinHandleT>
struct BasicResolvedPathGroup {
    std::string name;
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> through_pins;
    std::vector<PinHandleT> to_pins;
    std::vector<std::vector<PinHandleT>> through_stages;
    float weight = 1.0f;
    std::vector<uint32_t> from_clocks, to_clocks;
    uint8_t from_transitions = 3, to_transitions = 3, through_transitions = 3;
    std::vector<uint8_t> through_stage_transitions;
};

template <typename PinHandleT>
struct BasicResolvedDisableTiming {
    PinHandleT from_pin{UINT32_MAX};
    PinHandleT to_pin{UINT32_MAX};
};

template <typename PinHandleT>
struct BasicResolvedFalsePath {
    std::vector<PinHandleT> from_pins;
    std::vector<PinHandleT> through_pins;
    std::vector<PinHandleT> to_pins;
    std::vector<std::vector<PinHandleT>> through_stages;
    bool setup = true;
    bool hold = true;
    uint8_t from_transitions = 3;
    uint8_t to_transitions = 3;
    uint8_t through_transitions = 3;
    std::vector<uint8_t> through_stage_transitions;
    std::vector<uint32_t> from_clocks, to_clocks;
};

struct ResolvedOcvDerate {
    float early_data = 1.0f;
    float late_data = 1.0f;
    float early_clock = 1.0f;
    float late_clock = 1.0f;
};

struct ResolvedAocvPoint {
    int depth = 0;
    float late_derate = 1.0f;
    float early_derate = 1.0f;
};

struct ResolvedAocvTable {
    std::vector<ResolvedAocvPoint> points;
    bool empty() const { return points.empty(); }
};

struct ResolvedDesignRules {
    float max_fanout = -1.0f;
    float max_capacitance = -1.0f;
    float max_transition = -1.0f;
};

template <typename PinHandleT, typename TransitionT>
class BasicResolvedConstraintSet {
public:
    using Clock = BasicResolvedClock<PinHandleT>;
    using ClockGroup = ResolvedClockGroup;
    using InputDelay = BasicResolvedInputDelay<PinHandleT, TransitionT>;
    using OutputDelay = BasicResolvedOutputDelay<PinHandleT, TransitionT>;
    using SetLoad = BasicResolvedSetLoad<PinHandleT>;
    using InputTransition = BasicResolvedInputTransition<PinHandleT>;
    using DrivingCell = BasicResolvedDrivingCell<PinHandleT>;
    using ClockLatency = BasicResolvedClockLatency<PinHandleT>;
    using ClockUncertainty = BasicResolvedClockUncertainty<PinHandleT>;
    using CaseAnalysis = BasicResolvedCaseAnalysis<PinHandleT>;
    using MaxDelay = BasicResolvedMaxDelay<PinHandleT>;
    using MinDelay = BasicResolvedMinDelay<PinHandleT>;
    using DataCheck = BasicResolvedDataCheck<PinHandleT, TransitionT>;
    using PathGroup = BasicResolvedPathGroup<PinHandleT>;
    using MulticyclePath = BasicResolvedMulticyclePath<PinHandleT>;
    using DisableTiming = BasicResolvedDisableTiming<PinHandleT>;
    using FalsePath = BasicResolvedFalsePath<PinHandleT>;
    using OcvDerate = ResolvedOcvDerate;
    using AocvPoint = ResolvedAocvPoint;
    using AocvTable = ResolvedAocvTable;

    uint32_t create_clock(uint32_t name_id, float period, float transition);
    void set_clock_name(uint32_t clock_id, uint32_t name_id);
    void add_clock_source(uint32_t clock_id, PinHandleT pin);
    void set_generated_clock(uint32_t clock_id, uint32_t master_clock, PinHandleT source);
    void set_clock_propagated(uint32_t clock_id, bool propagated = true);
    void set_input_delay(uint32_t clock_id, float delay, bool is_max,
                         TransitionT clock_edge, std::vector<PinHandleT> ports);
    void set_input_delay(uint32_t clock_id, float delay, bool is_max,
                         std::vector<PinHandleT> ports);
    void set_output_delay(uint32_t clock_id, float delay, bool is_max,
                          TransitionT clock_edge, std::vector<PinHandleT> ports);
    void set_load(float capacitance, std::vector<PinHandleT> pins);
    void set_input_transition(float transition, std::vector<PinHandleT> ports,
                              bool rise = true, bool fall = true,
                              bool min = true, bool max = true, uint64_t order = 0);
    void set_driving_cell(DrivingCellDef model, std::vector<PinHandleT> ports) {
        if (!model.order) model.order = ++input_driver_order_;
        input_driver_order_ = std::max(input_driver_order_, model.order);
        model.port_names.clear();
        driving_cells_.push_back({std::move(model), std::move(ports)});
    }
    void set_clock_latency(float latency, uint32_t clock_id, std::vector<PinHandleT> pins);
    void set_clock_waveform(uint32_t clock_id, float rise_time, float fall_time);
    void set_clock_groups(ResolvedClockGroupMode mode,
                          std::vector<std::vector<uint32_t>> groups);
    void set_clock_uncertainty(float uncertainty, uint32_t clock_id, bool is_setup);
    void set_max_delay(float delay, std::vector<PinHandleT> from_pins,
                       std::vector<PinHandleT> to_pins, std::vector<PinHandleT> through_pins = {},
                       std::vector<std::vector<PinHandleT>> through_stages = {},
                       std::vector<uint32_t> from_clocks = {}, std::vector<uint32_t> to_clocks = {},
                       bool ignore_clock_latency = false);
    void set_min_delay(float delay, std::vector<PinHandleT> from_pins,
                       std::vector<PinHandleT> to_pins, std::vector<PinHandleT> through_pins = {},
                       std::vector<std::vector<PinHandleT>> through_stages = {},
                       std::vector<uint32_t> from_clocks = {}, std::vector<uint32_t> to_clocks = {},
                       bool ignore_clock_latency = false);
    void set_data_check(float delay, bool is_setup,
                        std::vector<PinHandleT> from_pins,
                        std::vector<PinHandleT> to_pins,
                        uint8_t from_transitions = 3,
                        uint8_t to_transitions = 3);
    void set_multicycle_path(int setup_cycles, int hold_cycles,
                             std::vector<PinHandleT> from_pins,
                             std::vector<PinHandleT> to_pins,
                             std::vector<uint32_t> from_clocks = {}, std::vector<uint32_t> to_clocks = {},
                             bool is_hold = false, bool use_start = false);
    void set_case_analysis(typename CaseAnalysis::Value value, PinHandleT pin);
    void set_disable_timing(PinHandleT from_pin, PinHandleT to_pin);
    void set_false_path(std::vector<PinHandleT> from_pins,
                        std::vector<PinHandleT> through_pins,
                        std::vector<PinHandleT> to_pins,
                        std::vector<std::vector<PinHandleT>> through_stages = {},
                        bool setup = true, bool hold = true,
                        uint8_t from_transitions = 3, uint8_t to_transitions = 3,
                        uint8_t through_transitions = 3,
                        std::vector<uint8_t> through_stage_transitions = {},
                        std::vector<uint32_t> from_clocks = {}, std::vector<uint32_t> to_clocks = {});
    void set_timing_derate(float early, float late, bool is_clock);
    void set_aocv_derate(std::vector<AocvPoint> points);
    void set_design_rules(float max_fanout, float max_capacitance,
                          float max_transition);

    const std::vector<Clock>& clocks() const { return clocks_; }
    const std::vector<ClockGroup>& clock_groups() const { return clock_groups_; }
    const std::vector<SetLoad>& set_loads() const { return set_loads_; }
    const std::vector<InputDelay>& input_delays() const { return input_delays_; }
    const std::vector<OutputDelay>& output_delays() const { return output_delays_; }
    const std::vector<InputTransition>& input_transitions() const { return input_transitions_; }
    const std::vector<DrivingCell>& driving_cells() const { return driving_cells_; }
    const std::vector<ClockLatency>& clock_latencies() const { return clock_latencies_; }
    const std::vector<ClockUncertainty>& clock_uncertainties() const { return clock_uncertainties_; }
    const std::vector<MaxDelay>& max_delays() const { return max_delays_; }
    const std::vector<MinDelay>& min_delays() const { return min_delays_; }
    const std::vector<DataCheck>& data_checks() const { return data_checks_; }
    const std::vector<PathGroup>& path_groups() const { return path_groups_; }
    void add_path_group(PathGroup group) {
        // Each definition adds another selector clause to the named group.
        for (auto& old : path_groups_) if (old.name == group.name) old.weight = group.weight;
        path_groups_.push_back(std::move(group));
    }
    const std::vector<MulticyclePath>& multicycle_paths() const { return multicycle_paths_; }
    const std::vector<CaseAnalysis>& case_analyses() const { return case_analyses_; }
    const std::vector<DisableTiming>& disable_timings() const { return disable_timings_; }
    const std::vector<FalsePath>& false_paths() const { return false_paths_; }
    const OcvDerate& ocv_derate() const { return ocv_derate_; }
    const AocvTable& aocv_table() const { return aocv_table_; }
    const ResolvedDesignRules& design_rules() const { return design_rules_; }

    void clear();

private:
    std::vector<Clock> clocks_;
    std::vector<ClockGroup> clock_groups_;
    std::vector<InputDelay> input_delays_;
    std::vector<OutputDelay> output_delays_;
    std::vector<SetLoad> set_loads_;
    std::vector<InputTransition> input_transitions_;
    std::vector<DrivingCell> driving_cells_;
    uint64_t input_driver_order_ = 0;
    std::vector<ClockLatency> clock_latencies_;
    std::vector<ClockUncertainty> clock_uncertainties_;
    std::vector<MaxDelay> max_delays_;
    std::vector<MinDelay> min_delays_;
    std::vector<DataCheck> data_checks_;
    std::vector<PathGroup> path_groups_;
    std::vector<MulticyclePath> multicycle_paths_;
    std::vector<CaseAnalysis> case_analyses_;
    std::vector<DisableTiming> disable_timings_;
    std::vector<FalsePath> false_paths_;
    OcvDerate ocv_derate_;
    AocvTable aocv_table_;
    ResolvedDesignRules design_rules_;
};

template <typename PinHandleT, typename TransitionT>
inline uint32_t BasicResolvedConstraintSet<PinHandleT, TransitionT>::create_clock(
    uint32_t name_id, float period, float transition) {
    uint32_t id = static_cast<uint32_t>(clocks_.size());
    clocks_.push_back({name_id, period, transition, -1.0f, -1.0f, 0.0f, {}, UINT32_MAX, {}, false, false});
    return id;
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_design_rules(
    float max_fanout, float max_capacitance, float max_transition) {
    design_rules_.max_fanout = max_fanout;
    design_rules_.max_capacitance = max_capacitance;
    design_rules_.max_transition = max_transition;
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_name(
    uint32_t clock_id, uint32_t name_id) {
    if (clock_id < clocks_.size()) clocks_[clock_id].name = name_id;
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::add_clock_source(
    uint32_t clock_id, PinHandleT pin) {
    if (clock_id < clocks_.size()) clocks_[clock_id].sources.push_back(pin);
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_generated_clock(
    uint32_t clock_id, uint32_t master_clock, PinHandleT source) {
    if (clock_id >= clocks_.size() || master_clock >= clocks_.size() || clock_id == master_clock) return;
    clocks_[clock_id].master_clock = master_clock;
    clocks_[clock_id].generated_source = source;
    clocks_[clock_id].generated = true;
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_propagated(
    uint32_t clock_id, bool propagated) {
    if (clock_id < clocks_.size()) clocks_[clock_id].propagated = propagated;
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_input_delay(
    uint32_t clock_id, float delay, bool is_max, TransitionT clock_edge,
    std::vector<PinHandleT> ports) {
    input_delays_.push_back({delay, clock_id, clock_edge, is_max, std::move(ports)});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_input_delay(
    uint32_t clock_id, float delay, bool is_max, std::vector<PinHandleT> ports) {
    set_input_delay(clock_id, delay, is_max, TransitionT::Rise, std::move(ports));
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_output_delay(
    uint32_t clock_id, float delay, bool is_max, TransitionT clock_edge,
    std::vector<PinHandleT> ports) {
    output_delays_.push_back({delay, clock_id, clock_edge, is_max, std::move(ports)});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_load(
    float capacitance, std::vector<PinHandleT> pins) {
    set_loads_.push_back({capacitance, std::move(pins)});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_input_transition(
    float transition, std::vector<PinHandleT> ports,
    bool rise, bool fall, bool min, bool max, uint64_t order) {
    if (!order) order = ++input_driver_order_;
    input_driver_order_ = std::max(input_driver_order_, order);
    input_transitions_.push_back({transition, std::move(ports), rise, fall, min, max, order});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_latency(
    float latency, uint32_t clock_id, std::vector<PinHandleT> pins) {
    clock_latencies_.push_back({latency, clock_id, std::move(pins)});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_waveform(
    uint32_t clock_id, float rise_time, float fall_time) {
    if (clock_id < clocks_.size()) {
        clocks_[clock_id].rise_time = rise_time;
        clocks_[clock_id].fall_time = fall_time;
    }
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_groups(
    ResolvedClockGroupMode mode, std::vector<std::vector<uint32_t>> groups) {
    if (groups.size() >= 2) {
        clock_groups_.push_back({mode, std::move(groups)});
    }
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_clock_uncertainty(
    float uncertainty, uint32_t clock_id, bool is_setup) {
    for (auto& cu : clock_uncertainties_) {
        if (cu.clock == clock_id) {
            if (is_setup) {
                cu.setup_uncertainty = uncertainty;
            } else {
                cu.hold_uncertainty = uncertainty;
            }
            return;
        }
    }
    ClockUncertainty cu{0.0f, 0.0f, clock_id, {}};
    if (is_setup) {
        cu.setup_uncertainty = uncertainty;
    } else {
        cu.hold_uncertainty = uncertainty;
    }
    clock_uncertainties_.push_back(cu);
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_max_delay(
    float delay, std::vector<PinHandleT> from_pins, std::vector<PinHandleT> to_pins,
    std::vector<PinHandleT> through_pins, std::vector<std::vector<PinHandleT>> through_stages,
    std::vector<uint32_t> from_clocks, std::vector<uint32_t> to_clocks, bool ignore_clock_latency) {
    max_delays_.push_back({delay, std::move(from_pins), std::move(to_pins),std::move(through_pins),std::move(through_stages),std::move(from_clocks),std::move(to_clocks),ignore_clock_latency});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_min_delay(
    float delay, std::vector<PinHandleT> from_pins, std::vector<PinHandleT> to_pins,
    std::vector<PinHandleT> through_pins, std::vector<std::vector<PinHandleT>> through_stages,
    std::vector<uint32_t> from_clocks, std::vector<uint32_t> to_clocks, bool ignore_clock_latency) {
    min_delays_.push_back({delay, std::move(from_pins), std::move(to_pins),std::move(through_pins),std::move(through_stages),std::move(from_clocks),std::move(to_clocks),ignore_clock_latency});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_data_check(
    float delay, bool is_setup, std::vector<PinHandleT> from_pins,
    std::vector<PinHandleT> to_pins, uint8_t from_transitions,
    uint8_t to_transitions) {
    data_checks_.push_back({delay, is_setup, std::move(from_pins),
                            std::move(to_pins), from_transitions, to_transitions});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_multicycle_path(
    int setup_cycles, int hold_cycles, std::vector<PinHandleT> from_pins,
    std::vector<PinHandleT> to_pins, std::vector<uint32_t> from_clocks, std::vector<uint32_t> to_clocks,
    bool is_hold, bool use_start) {
    multicycle_paths_.push_back({setup_cycles, hold_cycles,
                                 std::move(from_pins), std::move(to_pins),std::move(from_clocks),std::move(to_clocks),is_hold,use_start});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_case_analysis(
    typename CaseAnalysis::Value value, PinHandleT pin) {
    case_analyses_.push_back({value, pin});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_disable_timing(
    PinHandleT from_pin, PinHandleT to_pin) {
    disable_timings_.push_back({from_pin, to_pin});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_false_path(
    std::vector<PinHandleT> from_pins, std::vector<PinHandleT> through_pins,
    std::vector<PinHandleT> to_pins, std::vector<std::vector<PinHandleT>> through_stages,
    bool setup, bool hold, uint8_t from_transitions, uint8_t to_transitions,
    uint8_t through_transitions, std::vector<uint8_t> through_stage_transitions,
    std::vector<uint32_t> from_clocks, std::vector<uint32_t> to_clocks) {
    false_paths_.push_back({std::move(from_pins), std::move(through_pins),
                            std::move(to_pins), std::move(through_stages), setup, hold,
                            from_transitions, to_transitions, through_transitions,
                            std::move(through_stage_transitions),std::move(from_clocks),std::move(to_clocks)});
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_timing_derate(
    float early, float late, bool is_clock) {
    if (is_clock) {
        ocv_derate_.early_clock = early;
        ocv_derate_.late_clock = late;
    } else {
        ocv_derate_.early_data = early;
        ocv_derate_.late_data = late;
    }
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::set_aocv_derate(
    std::vector<AocvPoint> points) {
    std::sort(points.begin(), points.end(),
              [](const AocvPoint& a, const AocvPoint& b) {
                  return a.depth < b.depth;
              });
    aocv_table_.points = std::move(points);
}

template <typename PinHandleT, typename TransitionT>
inline void BasicResolvedConstraintSet<PinHandleT, TransitionT>::clear() {
    clocks_.clear();
    clock_groups_.clear();
    input_delays_.clear();
    output_delays_.clear();
    set_loads_.clear();
    input_transitions_.clear();
    driving_cells_.clear();
    input_driver_order_ = 0;
    clock_latencies_.clear();
    clock_uncertainties_.clear();
    max_delays_.clear();
    min_delays_.clear();
    data_checks_.clear();
    path_groups_.clear();
    multicycle_paths_.clear();
    case_analyses_.clear();
    disable_timings_.clear();
    false_paths_.clear();
    ocv_derate_ = {};
    aocv_table_ = {};
    design_rules_ = {};
}

using ResolvedClock = BasicResolvedClock<PinHandle>;
using ResolvedClockGroupDef = ResolvedClockGroup;
using ResolvedInputDelay = BasicResolvedInputDelay<PinHandle, Transition>;
using ResolvedOutputDelay = BasicResolvedOutputDelay<PinHandle, Transition>;
using ResolvedSetLoad = BasicResolvedSetLoad<PinHandle>;
using ResolvedInputTransition = BasicResolvedInputTransition<PinHandle>;
using ResolvedClockLatency = BasicResolvedClockLatency<PinHandle>;
using ResolvedClockUncertainty = BasicResolvedClockUncertainty<PinHandle>;
using ResolvedCaseAnalysis = BasicResolvedCaseAnalysis<PinHandle>;
using ResolvedMaxDelay = BasicResolvedMaxDelay<PinHandle>;
using ResolvedMinDelay = BasicResolvedMinDelay<PinHandle>;
using ResolvedMulticyclePath = BasicResolvedMulticyclePath<PinHandle>;
using ResolvedDisableTiming = BasicResolvedDisableTiming<PinHandle>;
using ResolvedFalsePath = BasicResolvedFalsePath<PinHandle>;
using ResolvedConstraintSet = BasicResolvedConstraintSet<PinHandle, Transition>;

} // namespace edacraft::core

#endif // EDACRAFT_CORE_RESOLVED_CONSTRAINT_SET_HPP
