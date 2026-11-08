#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <queue>
#include <optional>
#include <map>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "dcalc/delay_result.hh"
#include "sdc/resolved_constraints.hh"

// Forward declarations
namespace te {
class Network;
}

namespace te {

// Lightweight span replacement for C++17 (no std::span)
template<typename T>
struct Span {
    const T* data_;
    size_t size_;
    Span(const T* d, size_t s) : data_(d), size_(s) {}
    const T* data() const { return data_; }
    size_t size() const { return size_; }
    const T* begin() const { return data_; }
    const T* end() const { return data_ + size_; }
    const T& operator[](size_t i) const { return data_[i]; }
    bool empty() const { return size_ == 0; }
};

// ────────────────────────────────────────────────────────────
// Timing graph data (SOA layout for cache-friendly BFS)
// ────────────────────────────────────────────────────────────
struct EdgeConditionLiteral {
    uint32_t net = UINT32_MAX;
    int8_t value = -1;
};

// One GBA label per launch clock/edge/source class, rather than per register.
// Delay and slew are characterized with each retained label's input slew. Keep a separate
// predecessor for each label so an excluded launch cannot hide a timed route.
struct LaunchTimingLabel {
    uint64_t key = 0;
    uint32_t domain = UINT32_MAX;
    uint32_t capture = UINT32_MAX;
    uint32_t start = UINT32_MAX;
    uint32_t predecessor = UINT32_MAX;
    uint64_t predecessor_key = UINT64_MAX;
    float phase = 0;
    float arrival = 0;
    float slew = 0;
    float wire_source_slew = 0;
    uint64_t waveform_context = 0;
    float required = 0;
    float cppr = 0;
    bool unresolved_history = false;
    TimingCheckKind kind = TimingCheckKind::None;
    int path_depth = 0;
    std::vector<std::pair<uint32_t, int8_t>> path_conditions;
};

class TimingGraph {
public:
    void set_verbose(bool verbose) { verbose_ = verbose; }
    TimingGraph() = default;

    // Build graph from network + liberty data
    int build(const Network& net, const edacraft::core::LibertyDB& lib,
              const ResolvedConstraintSet* sdc = nullptr);

    // ── Vertex access ──────────────────────────────────────
    uint32_t vertex_count() const { return vertices_; }
    PinId vertex_pin(uint32_t vid) const { return vid < vertices_ ? pin_[vid] : PinId{UINT32_MAX}; }
    Transition vertex_transition(uint32_t vid) const { return vid < vertices_ ? transition_[vid] : Transition::Rise; }
    int vertex_level(uint32_t vid) const { return vid < vertices_ ? level_[vid] : 0; }
    int max_level() const { return max_level_; }
    bool verbose() const { return verbose_; }
    uint32_t vertex_clock_domain(uint32_t vid) const { return clock_domain_[vid]; }
    void set_vertex_clock_domain(uint32_t vid, uint32_t domain) { clock_domain_[vid] = domain; }
    uint32_t instance_clk_pin(uint32_t iid) const {
        return iid < instance_clk_pin_.size() ? instance_clk_pin_[iid] : UINT32_MAX;
    }
    bool is_startpoint(uint32_t vid) const { return startpoints_[vid]; }
    void set_startpoint(uint32_t vid, bool val) { startpoints_[vid] = val; }
    bool is_endpoint(uint32_t vid) const { return endpoints_[vid]; }
    bool is_path_only_endpoint(uint32_t vid) const { return path_only_endpoints_[vid]; }
    bool is_static_constant_vertex(uint32_t vid) const {
        if (vid >= pin_.size()) return false;
        const auto pid = pin_[vid].id;
        return pid < static_pin_constants_.size() && static_pin_constants_[pid] >= 0;
    }
    int static_pin_value(PinId pin) const {
        return pin.id < static_pin_constants_.size() ? static_pin_constants_[pin.id] : -1;
    }

    // ── Edge access ────────────────────────────────────────
    uint32_t edge_count() const { return edge_from_.size(); }
    uint32_t edge_from(uint32_t eid) const { return edge_from_[eid]; }
    uint32_t edge_to(uint32_t eid) const { return edge_to_[eid]; }
    uint32_t edge_arc(uint32_t eid) const { return edge_arc_[eid]; }
    Span<EdgeConditionLiteral> edge_conditions(uint32_t eid) const;
    void set_edge_delay(uint32_t eid, float delay) {
        for (auto mm : {MinMax::Min, MinMax::Max}) set_edge_delay(eid, delay, mm);
    }
    void set_edge_delay(uint32_t eid, float delay, MinMax mm) {
        if (eid >= edge_delay_.size()) edge_delay_.resize(eid + 1);
        if (eid >= edge_propagated_delay_.size()) edge_propagated_delay_.resize(eid + 1);
        edge_delay_[eid][unsigned(mm)] = delay;
        edge_propagated_delay_[eid][unsigned(mm)] = delay;
    }
    void set_edge_delay_result(uint32_t eid, const DelayResult& result) {
        for (auto mm : {MinMax::Min, MinMax::Max}) set_edge_delay_result(eid, result, mm);
    }
    void set_edge_delay_result(uint32_t eid, const DelayResult& result, MinMax mm,
                               float derate = 1.0f, float phase_offset = 0.f) {
        set_edge_delay(eid, result.delay.value, mm);
        if (eid >= edge_output_slew_.size()) edge_output_slew_.resize(eid + 1);
        if (eid >= edge_ceff_.size()) edge_ceff_.resize(eid + 1);
        if (eid >= edge_delay_source_.size()) {
            edge_delay_source_.resize(eid + 1);
        }
        edge_output_slew_[eid][unsigned(mm)] = result.output_slew.value;
        edge_ceff_[eid][unsigned(mm)] = result.ceff;
        edge_delay_source_[eid][unsigned(mm)] = result.source;
        edge_propagated_delay_[eid][unsigned(mm)] = result.delay.value * derate + phase_offset;
    }
    float edge_delay(uint32_t eid, MinMax mm = MinMax::Max) const {
        return (eid < edge_delay_.size()) ? edge_delay_[eid][unsigned(mm)] : 0.0f;
    }
    float edge_propagated_delay(uint32_t eid, MinMax mm) const {
        return (eid < edge_propagated_delay_.size()) ? edge_propagated_delay_[eid][unsigned(mm)] : 0.0f;
    }
    float edge_output_slew(uint32_t eid, MinMax mm = MinMax::Max) const {
        return (eid < edge_output_slew_.size()) ? edge_output_slew_[eid][unsigned(mm)] : 0.0f;
    }
    float edge_ceff(uint32_t eid, MinMax mm = MinMax::Max) const {
        return (eid < edge_ceff_.size()) ? edge_ceff_[eid][unsigned(mm)] : 0.0f;
    }
    DelayModelSource edge_delay_source(uint32_t eid, MinMax mm = MinMax::Max) const {
        return (eid < edge_delay_source_.size())
            ? edge_delay_source_[eid][unsigned(mm)]
            : DelayModelSource::None;
    }

    // ── Graph access ────────────────────────────────────────
    Span<uint32_t> forward_edges(uint32_t vid) const;
    Span<uint32_t> reverse_edges(uint32_t vid) const;
    Arrival arrival(uint32_t vid, MinMax mm, Transition rf) const;
    void set_arrival(uint32_t vid, MinMax mm, Transition rf, Arrival a);
    Slew slew(uint32_t vid, MinMax mm, Transition rf) const;
    void set_slew(uint32_t vid, MinMax mm, Transition rf, Slew s);
    Required required(uint32_t vid, MinMax mm, Transition rf) const;
    void set_required(uint32_t vid, MinMax mm, Transition rf, Required r);
    bool check_arc_disabled(uint32_t instance, uint32_t arc) const {
        return disabled_checks_.count((uint64_t(instance) << 32) | arc) != 0;
    }
    TimingCheckKind endpoint_check_kind(uint32_t vid, MinMax mm) const {
        return check_kinds_[vid * 2 + static_cast<unsigned>(mm)];
    }
    void set_endpoint_check_kind(uint32_t vid, MinMax mm, TimingCheckKind kind) {
        check_kinds_[vid * 2 + static_cast<unsigned>(mm)] = kind;
    }
    void clear_check_coverage() { check_coverage_.clear(); check_results_.clear(); clock_route_coverage_.clear();
        endpoint_cppr_.assign(vertices_, {});
        endpoint_capture_clock_.assign(vertices_, {UINT32_MAX,UINT32_MAX}); }
    float endpoint_cppr(uint32_t vid, MinMax mm) const {
        return vid < endpoint_cppr_.size() ? endpoint_cppr_[vid][unsigned(mm)] : 0.f;
    }
    void set_endpoint_cppr(uint32_t vid, MinMax mm, float correction) {
        if (endpoint_cppr_.size() < vertices_) endpoint_cppr_.resize(vertices_);
        endpoint_cppr_[vid][unsigned(mm)] = correction;
    }
    uint32_t endpoint_capture_clock(uint32_t vid, MinMax mm) const {
        return vid < endpoint_capture_clock_.size() ? endpoint_capture_clock_[vid][unsigned(mm)] : UINT32_MAX;
    }
    void set_endpoint_capture_clock(uint32_t vid, MinMax mm, uint32_t clock_vid) {
        if (endpoint_capture_clock_.size()<vertices_) endpoint_capture_clock_.resize(vertices_, {UINT32_MAX,UINT32_MAX});
        endpoint_capture_clock_[vid][unsigned(mm)] = clock_vid;
    }
    std::optional<uint8_t> clock_route_coverage(uint32_t vid, uint32_t capture) const {
        const auto entry = clock_route_coverage_.find((uint64_t(capture) << 32) | vid);
        return entry == clock_route_coverage_.end() ? std::nullopt : std::optional<uint8_t>{entry->second};
    }
    void set_clock_route_coverage(uint32_t vid, uint32_t capture, uint8_t coverage) {
        clock_route_coverage_[(uint64_t(capture) << 32) | vid] = coverage;
    }
    void add_check_coverage(TimingCheckCoverage record) { check_coverage_.push_back(record); }
    const std::vector<TimingCheckCoverage>& check_coverage() const { return check_coverage_; }
    void add_check_result(TimingCheckResult record) { check_results_.push_back(std::move(record)); }
    const std::vector<TimingCheckResult>& check_results() const { return check_results_; }
    void reset_launch_labels(bool enabled) {
        launch_labels_.clear();
        exception_histories_.clear(); exception_history_ids_.clear();
        exception_histories_.push_back({}); exception_history_ids_[{}] = 0;
        exception_pin_events_.clear(); exception_seed_key_ = 0;
        if (enabled) launch_labels_.resize(vertices_);
    }
    static constexpr uint64_t launch_base_mask = (uint64_t(1) << 34)-1;
    // Compile from/through events once per analysis. Unmentioned pins preserve
    // the history without copying it or scanning every exception on each edge.
    void prepare_false_path_history(const ResolvedConstraintSet* sdc) {
        exception_pin_events_.clear(); exception_seed_key_ = 0;
        path_origin_events_.clear(); path_origin_slots_.clear();
        if (!sdc) return;
        const size_t nf=sdc->false_paths().size(), nd=sdc->max_delays().size()+sdc->min_delays().size();
        std::vector<uint32_t> initial(nf+3*nd+sdc->multicycle_paths().size());
        if (initial.empty()) return;
        for (size_t i = 0; i < nf; ++i) {
            const auto& fp = sdc->false_paths()[i];
            if (fp.from_pins.empty()) initial[i] |= 1;
            if (fp.through_pins.empty() && !fp.through_stages.empty())
                throw std::runtime_error("Ordered false path has an empty first through stage");
            const size_t stages = fp.through_pins.empty() ? 0 : 1 + fp.through_stages.size();
            if (stages > (UINT32_MAX >> 1))
                throw std::runtime_error("Timing exception through stage capacity exceeded");
            if (stages == 0) initial[i] |= 2;
            auto add_events = [&](const auto& pins, uint32_t stage, uint8_t mask) {
                for (auto pin : pins) for (unsigned rf = 0; rf < 2; ++rf)
                    if (mask & (1u << rf)) exception_pin_events_[pin.id * 2 + rf].push_back({i, stage});
            };
            add_events(fp.from_pins, 0, fp.from_transitions);
            add_events(fp.through_pins, 1, fp.through_transitions);
            for (size_t stage = 0; stage < fp.through_stages.size(); ++stage) {
                if (fp.through_stages[stage].empty())
                    throw std::runtime_error("Ordered false path has an empty through stage");
                add_events(fp.through_stages[stage], static_cast<uint32_t>(2 + stage),
                    stage < fp.through_stage_transitions.size() ? fp.through_stage_transitions[stage] : 3);
            }
        }
        // Path delays and multicycles need the same ordered route history.
        auto compile = [&](size_t index, const auto& from, const auto& through, const auto& stages) {
            if (from.empty()) initial[index]|=1;
            if (through.empty()) initial[index]|=2;
            auto events=[&](const auto& pins,uint32_t stage) {
                for (auto pin:pins) for(unsigned rf=0;rf<2;++rf)
                    exception_pin_events_[pin.id*2+rf].push_back({index,stage});
            };
            events(from,0);events(through,1);
            for(size_t i=0;i<stages.size();++i)events(stages[i],uint32_t(i+2));
        };
        size_t di=0;
        auto compile_delays=[&](const auto& delays) {
            for(const auto& d:delays) {
                const auto index=nf+3*di++;
                compile(index,d.from_pins,d.through_pins,d.through_stages);
                path_origin_slots_.insert(index+1);
                for(auto pin:d.from_pins)path_origin_events_[pin.id].push_back(index+1);
            }
        };
        compile_delays(sdc->max_delays());compile_delays(sdc->min_delays());
        for(size_t i=0;i<sdc->multicycle_paths().size();++i) {
            const auto& m=sdc->multicycle_paths()[i];
            compile(nf+3*nd+i,m.from_pins,std::vector<PinId>{},std::vector<std::vector<PinId>>{});
        }
        // Process from first, then through stages in order at the same pin.
        // Deduplicate identical events without combining distinct stage numbers.
        for (auto& entry : exception_pin_events_) {
            auto& events = entry.second;
            std::sort(events.begin(), events.end());
            events.erase(std::unique(events.begin(), events.end()), events.end());
        }
        exception_seed_key_ = launch_key_with_history(0, initial);
    }
    uint64_t advance_false_path_history(uint64_t key, PinId pin, bool seed, Transition rf) {
        // Cyclic/backward graph edges can introduce an unknown launch label
        // with the empty history class. Normalize it before indexing events,
        // just as the previous propagation resized and initialized that class.
        if (seed || !(key >> 34)) key = (key & launch_base_mask) | exception_seed_key_;
        const auto found = exception_pin_events_.find(pin.id * 2 + unsigned(rf));
        if (found == exception_pin_events_.end()) return key;
        const auto& current = launch_history(key);
        std::vector<uint32_t> history;
        for (const auto& event : found->second) {
            const auto before = history.empty() ? current[event.first] : history[event.first];
            auto state = before;
            if (event.second == 0) state |= 1;
            // Low bit means from matched; high bits count completed stages.
            // Earlier stages never reset progress and later stages cannot skip.
            else if ((state & 1) && (state >> 1) == event.second - 1) state += 2;
            if (state == before) continue;
            if (history.empty()) history = current;
            history[event.first] = state;
        }
        return history.empty() ? key : launch_key_with_history(key, history);
    }
    uint64_t record_path_origins(uint64_t key, PinId pin, float arrival, bool startpoint) {
        const auto found=path_origin_events_.find(pin.id);
        if(found==path_origin_events_.end() || !std::isfinite(arrival))return key;
        auto history=launch_history(key);
        const float origin=startpoint?0.f:arrival;
        uint32_t bits;std::memcpy(&bits,&origin,sizeof(bits));
        for(const auto index:found->second) { history[index]=bits;history[index+1]=path_origin_pin_ids_.at(pin.id); }
        return launch_key_with_history(key,history);
    }
    float path_origin(uint64_t key,size_t state_index) const {
        const auto bits=launch_history(key).at(state_index+1);
        float result;std::memcpy(&result,&bits,sizeof(result));return result;
    }
    size_t exception_history_count() const { return exception_histories_.size(); }
    uint64_t unique_path_key(uint64_t key, uint32_t route) {
        auto history = launch_history(key);
        history.resize(launch_history(exception_seed_key_).size() + 1);
        history.back() = route;
        return launch_key_with_history(key, history);
    }
    size_t exception_event_pin_count() const { return exception_pin_events_.size(); }
    uint64_t launch_key_with_history(uint64_t key, const std::vector<uint32_t>& history) {
        const auto found = exception_history_ids_.find(history);
        uint32_t id;
        if (found != exception_history_ids_.end()) id = found->second;
        else {
            if (exception_histories_.size() >= (uint64_t(1)<<30))
                throw std::runtime_error("Timing exception history capacity exceeded");
            id = static_cast<uint32_t>(exception_histories_.size());
            exception_histories_.push_back(history); exception_history_ids_.emplace(history, id);
        }
        return (key & launch_base_mask) | (uint64_t(id)<<34);
    }
    const std::vector<uint32_t>& launch_history(uint64_t key) const {
        return exception_histories_.at(key>>34);
    }
    std::string launch_identity(uint64_t key) const {
        const auto& history = launch_history(key);
        if (history.empty()) return {};
        auto result = std::to_string(key & launch_base_mask) + ":fp=";
        for (size_t i=0;i<history.size();++i) {
            // Numeric origins are analysis state, not logical check identity.
            // The following slot records the stable source pin instead.
            if(!path_origin_slots_.count(i))result += std::to_string(history[i]) + ",";
        }
        return result;
    }
    bool has_launch_labels() const { return !launch_labels_.empty(); }
    std::vector<LaunchTimingLabel>& launch_labels(uint32_t vid, MinMax mm) {
        return launch_labels_[vid][static_cast<unsigned>(mm)];
    }
    const LaunchTimingLabel* launch_label(uint32_t vid, MinMax mm, uint64_t key) const {
        if (!has_launch_labels() || vid >= launch_labels_.size()) return nullptr;
        for (const auto& label : launch_labels_[vid][static_cast<unsigned>(mm)])
            if (label.key == key) return &label;
        return nullptr;
    }
    const LaunchTimingLabel* worst_launch_label(uint32_t vid, MinMax mm) const {
        if (!has_launch_labels() || vid >= launch_labels_.size()) return nullptr;
        const LaunchTimingLabel* result = nullptr;
        float worst = Delay::INF().value;
        for (const auto& label : launch_labels_[vid][static_cast<unsigned>(mm)]) {
            const float slack = mm == MinMax::Max ? label.required-label.arrival : label.arrival-label.required;
            if (std::isfinite(slack) && slack < worst) { worst = slack; result = &label; }
        }
        return result;
    }
    // Collapse the per-launch ledger for one endpoint/mode only. Invalid
    // coverage wins; otherwise any evaluated launch keeps the check active.
    void merge_launch_check_coverage(size_t begin) {
        size_t end = check_coverage_.size();
        for (size_t i = begin; i < end; ++i) {
            size_t target = begin;
            for (; target < i; ++target) if (check_coverage_[target].arc == check_coverage_[i].arc) break;
            if (target == i) continue;
            auto& state = check_coverage_[target].state;
            const auto incoming = check_coverage_[i].state;
            if (check_coverage_valid(state) &&
                (!check_coverage_valid(incoming) || incoming == CheckCoverageState::Evaluated)) state = incoming;
            check_coverage_.erase(check_coverage_.begin()+i); --i; --end;
        }
    }
    void set_pred_max(uint32_t vid, MinMax mm, Transition rf, uint32_t pred_vid);
    uint32_t pred_max(uint32_t vid, MinMax mm, Transition rf) const;
    void set_pred_min(uint32_t vid, MinMax mm, Transition rf, uint32_t pred_vid);
    uint32_t pred_min(uint32_t vid, MinMax mm, Transition rf) const;
    void mark_dirty(uint32_t vid);
    bool is_dirty(uint32_t vid) const;
    void clear_dirty();
    void increment_generation();
    uint64_t generation() const { return generation_; }
    const float* arrival_data() const { return reinterpret_cast<const float*>(arrivals_.data()); }
    const float* slew_data() const { return reinterpret_cast<const float*>(slews_.data()); }
    const float* required_data() const { return reinterpret_cast<const float*>(requireds_.data()); }
    const uint32_t* pred_max_data() const { return pred_max_.data(); }
    const uint32_t* pred_min_data() const { return pred_min_.data(); }
    int levelize();
    Span<uint32_t> vertices_at_level(int level) const;

private:
    void propagate_clock_domains();

    // Vertex count and per-vertex data
    uint32_t vertices_ = 0;
    std::vector<PinId> pin_;
    std::vector<Transition> transition_;
    std::vector<int> level_;
    std::vector<uint8_t> startpoints_;
    std::vector<uint8_t> endpoints_;
    std::vector<uint8_t> dirty_;

    // Edge data
    std::vector<uint32_t> edge_from_;
    std::vector<uint32_t> edge_to_;
    std::vector<uint32_t> edge_arc_;
    std::vector<std::vector<EdgeConditionLiteral>> edge_conditions_;
    std::vector<std::array<float, 2>> edge_delay_;
    std::vector<std::array<float, 2>> edge_propagated_delay_;
    std::vector<std::array<float, 2>> edge_output_slew_;
    std::vector<std::array<float, 2>> edge_ceff_;
    std::vector<std::array<DelayModelSource, 2>> edge_delay_source_;

    // CSR adjacency (forward)
    std::vector<uint32_t> fwd_offset_;
    std::vector<uint32_t> fwd_edge_;

    // CSR adjacency (reverse)
    std::vector<uint32_t> rev_offset_;
    std::vector<uint32_t> rev_edge_;

    // Timing results: [vid * 4 + mm_rf_index(mm, rf)]
    std::vector<Arrival> arrivals_;
    std::vector<Slew> slews_;
    std::vector<Required> requireds_;
    std::vector<TimingCheckKind> check_kinds_;
    std::vector<TimingCheckCoverage> check_coverage_;
    std::vector<TimingCheckResult> check_results_;
    std::vector<std::array<float,2>> endpoint_cppr_;
    std::vector<std::array<uint32_t,2>> endpoint_capture_clock_;
    std::vector<std::array<std::vector<LaunchTimingLabel>, 2>> launch_labels_;
    std::vector<std::vector<uint32_t>> exception_histories_;
    std::map<std::vector<uint32_t>, uint32_t> exception_history_ids_;
    std::unordered_map<uint32_t, std::vector<std::pair<size_t, uint32_t>>> exception_pin_events_;
    uint64_t exception_seed_key_ = 0;
    std::unordered_map<uint32_t,std::vector<size_t>> path_origin_events_;
    std::unordered_set<size_t> path_origin_slots_;
    std::unordered_map<uint32_t,uint32_t> path_origin_pin_ids_;
    std::vector<uint8_t> path_only_endpoints_;
    std::unordered_map<uint64_t, uint8_t> clock_route_coverage_;
    std::unordered_map<uint64_t, bool> disabled_checks_;

    // Path tracing: predecessor on max/min-arrival path
    std::vector<uint32_t> pred_max_;
    std::vector<uint32_t> pred_min_;

    // Level-sorted vertex ordering
    std::vector<uint32_t> level_sorted_;
    std::vector<int> level_offsets_;
    std::vector<uint32_t> clock_domain_;
    std::vector<uint32_t> instance_clk_pin_;
    std::vector<int8_t> static_pin_constants_;
    int max_level_ = 0;
    uint64_t generation_ = 0;
    bool verbose_ = false;
};

// ────────────────────────────────────────────────────────────
// Inline implementations
// ────────────────────────────────────────────────────────────
inline Span<uint32_t> TimingGraph::forward_edges(uint32_t vid) const {
    if (vid >= vertices_) return {nullptr, 0};
    uint32_t begin = fwd_offset_[vid];
    uint32_t end = fwd_offset_[vid + 1];
    return {fwd_edge_.data() + begin, end - begin};
}

inline Span<uint32_t> TimingGraph::reverse_edges(uint32_t vid) const {
    if (vid >= vertices_) return {nullptr, 0};
    uint32_t begin = rev_offset_[vid];
    uint32_t end = rev_offset_[vid + 1];
    return {rev_edge_.data() + begin, end - begin};
}

inline Span<EdgeConditionLiteral> TimingGraph::edge_conditions(uint32_t eid) const {
    if (eid >= edge_conditions_.size() || edge_conditions_[eid].empty()) {
        return {nullptr, 0};
    }
    const auto& conditions = edge_conditions_[eid];
    return {conditions.data(), conditions.size()};
}

inline Arrival TimingGraph::arrival(uint32_t vid, MinMax mm, Transition rf) const {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx >= arrivals_.size()) return Arrival{Delay::ZERO()};
    return arrivals_[idx];
}

inline void TimingGraph::set_arrival(uint32_t vid, MinMax mm, Transition rf, Arrival a) {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx < arrivals_.size()) arrivals_[idx] = a;
}

inline Slew TimingGraph::slew(uint32_t vid, MinMax mm, Transition rf) const {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx >= slews_.size()) return Slew{Delay::ZERO()};
    return slews_[idx];
}

inline void TimingGraph::set_slew(uint32_t vid, MinMax mm, Transition rf, Slew s) {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx < slews_.size()) slews_[idx] = s;
}

inline Required TimingGraph::required(uint32_t vid, MinMax mm, Transition rf) const {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx >= requireds_.size()) return Required{Delay::ZERO()};
    return requireds_[idx];
}

inline void TimingGraph::set_required(uint32_t vid, MinMax mm, Transition rf, Required r) {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx < requireds_.size()) requireds_[idx] = r;
}

inline void TimingGraph::set_pred_max(uint32_t vid, MinMax mm, Transition rf, uint32_t pred_vid) {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx < pred_max_.size()) pred_max_[idx] = pred_vid;
}

inline uint32_t TimingGraph::pred_max(uint32_t vid, MinMax mm, Transition rf) const {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    return idx < pred_max_.size() ? pred_max_[idx] : UINT32_MAX;
}

inline void TimingGraph::set_pred_min(uint32_t vid, MinMax mm, Transition rf, uint32_t pred_vid) {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    if (idx < pred_min_.size()) pred_min_[idx] = pred_vid;
}

inline uint32_t TimingGraph::pred_min(uint32_t vid, MinMax mm, Transition rf) const {
    size_t idx = static_cast<size_t>(vid) * 4 + mm_rf_index(mm, rf);
    return idx < pred_min_.size() ? pred_min_[idx] : UINT32_MAX;
}

inline void TimingGraph::mark_dirty(uint32_t vid) {
    if (vid < dirty_.size()) dirty_[vid] = 1;
}

inline bool TimingGraph::is_dirty(uint32_t vid) const {
    return vid < dirty_.size() && dirty_[vid];
}

inline void TimingGraph::clear_dirty() {
    std::fill(dirty_.begin(), dirty_.end(), 0);
}

inline void TimingGraph::increment_generation() {
    ++generation_;
}

inline Span<uint32_t> TimingGraph::vertices_at_level(int level) const {
    if (level < 0 || level > max_level_) return {nullptr, 0};
    int begin = level_offsets_[level];
    int end = level_offsets_[level + 1];
    if (begin >= end) return {nullptr, 0};
    return {level_sorted_.data() + begin, static_cast<size_t>(end - begin)};
}

} // namespace te
