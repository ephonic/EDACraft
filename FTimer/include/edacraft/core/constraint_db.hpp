#ifndef EDACRAFT_CORE_CONSTRAINT_DB_HPP
#define EDACRAFT_CORE_CONSTRAINT_DB_HPP

#include "edacraft/core/ids.hpp"
#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <algorithm>
#include <unordered_set>

namespace edacraft::core {

// Declarative relationship, retained when writing SDC rather than flattening
// a generated clock into an unrelated primary clock.
struct GeneratedClockDef {
    std::string source;
    bool source_is_pin = false;
    std::string master_clock;
    std::string resolved_master_clock;
    uint32_t divide_by = 0;
    uint32_t multiply_by = 0;
    float duty_cycle = 0.0f;
    bool invert = false;
    bool combinational = false;
    std::vector<uint32_t> edges;
    std::vector<float> edge_shifts_ns;
};

// ─── Clock definition ───────────────────────────────────────────────
struct ClockDef {
    std::string name;
    std::string source_port;        // top-level port name (e.g. "clk")
    float period_ns = 0.0f;
    float rise_edge_ns = 0.0f;      // waveform rise time
    float fall_edge_ns = 0.0f;      // waveform fall time
    bool  waveform_explicit = false; // true if -waveform was specified
    float transition_ns = -1.0f;    // set_clock_transition; negative means ideal/default
    float latency_ns = 0.0f;
    bool source_is_pin = false;
    // PrimeTime's set_propagated_clock selects real clock-tree propagation.
    // Existing flows keep ideal clocks unless this is explicitly enabled.
    bool propagated = false;
    std::optional<GeneratedClockDef> generated;
};

// ─── Clock groups ───────────────────────────────────────────────────
struct ClockGroupDef {
    enum class Mode {
        Asynchronous,
        LogicallyExclusive,
        PhysicallyExclusive
    };

    Mode mode = Mode::Asynchronous;
    std::vector<std::vector<std::string>> groups;
};

// ─── I/O delay ──────────────────────────────────────────────────────
struct IoDelay {
    std::string clock_name;
    float delay_ns = 0.0f;
    Transition clock_edge = Transition::Rise;
    bool is_max = true;              // true = -max (setup), false = -min (hold)
    bool is_input = true;            // true = set_input_delay, false = set_output_delay
    std::vector<std::string> port_names;
};

// ─── Path delay constraint (max_delay / min_delay) ──────────────────
struct PathDelay {
    float delay_ns = 0.0f;
    bool is_max = true;              // true = set_max_delay, false = set_min_delay
    std::vector<std::string> from_pins;
    std::vector<std::string> through_pins;
    std::vector<std::string> to_pins;
    std::vector<std::vector<std::string>> through_stages;
    std::vector<std::string> from_clocks, to_clocks;
    bool ignore_clock_latency = false;
};

// Explicit SDC data check between two pins.  The timing graph can consume
// this record as a setup/hold endpoint check without losing the original
// selectors and transition qualifiers.
struct DataCheckDef {
    float delay_ns = 0.0f;
    bool is_setup = true;
    std::vector<std::string> from_pins;
    std::vector<std::string> to_pins;
    uint8_t from_transitions = 3;
    uint8_t to_transitions = 3;
};

struct PathGroupDef {
    std::string name;
    std::vector<std::string> from_pins;
    std::vector<std::string> through_pins;
    std::vector<std::string> to_pins;
    std::vector<std::vector<std::string>> through_stages;
    float weight = 1.0f;
    bool weight_explicit = false;
    std::vector<std::string> from_clocks, to_clocks;
    uint8_t from_transitions = 3, to_transitions = 3, through_transitions = 3;
    std::vector<uint8_t> through_stage_transitions;
};

// ─── Clock latency ──────────────────────────────────────────────────
struct ClockLatencyDef {
    std::string clock_name;
    float latency_ns = 0.0f;
    std::vector<std::string> pin_names;
};

// ─── Clock uncertainty ──────────────────────────────────────────────
struct ClockUncertaintyDef {
    std::string clock_name;
    float setup_uncertainty_ns = 0.0f;
    float hold_uncertainty_ns = 0.0f;
};

// ─── Multicycle path ────────────────────────────────────────────────
struct MulticyclePathDef {
    int setup_cycles = 1;
    int hold_cycles = 0;
    std::vector<std::string> from_pins;
    std::vector<std::string> to_pins;
    std::vector<std::string> from_clocks, to_clocks;
    bool is_hold = false;
    bool use_start = false;          // setup defaults to end; hold defaults to start
};

// ─── False path ─────────────────────────────────────────────────────
struct FalsePathDef {
    std::vector<std::string> from_pins;
    std::vector<std::string> through_pins;
    std::vector<std::string> to_pins;
    // Additional ordered OR groups after the first through_pins group.
    std::vector<std::vector<std::string>> through_stages;
    bool setup = true;
    bool hold = true;
    uint8_t from_transitions = 3;
    uint8_t to_transitions = 3;
    uint8_t through_transitions = 3;
    std::vector<uint8_t> through_stage_transitions;
    std::vector<std::string> from_clocks, to_clocks;
};

// ─── Disable timing ─────────────────────────────────────────────────
struct DisableTimingDef {
    std::string from_pin;
    std::string to_pin;              // empty means disable all arcs from from_pin
};

// ─── Case analysis ──────────────────────────────────────────────────
struct CaseAnalysisDef {
    enum Value { Zero = 0, One = 1, Rise = 2, Fall = 3 };
    Value value = Zero;
    std::string pin_name;
};

// ─── Set load ───────────────────────────────────────────────────────
struct SetLoadDef {
    float capacitance_pf = 0.0f;
    std::vector<std::string> pin_names;
};

// ─── Set input transition ───────────────────────────────────────────
struct InputTransitionDef {
    float transition_ns = 0.0f;
    std::vector<std::string> port_names;
    bool rise = true;
    bool fall = true;
    bool min = true, max = true;
    uint64_t order = 0;
};

// A library cell outside the design drives a primary input's real load.
struct DrivingCellDef {
    std::string cell, library, pin, from_pin;
    float input_transition_rise_ns = 0.f, input_transition_fall_ns = 0.f;
    bool rise = true, fall = true, min = true, max = true;
    bool no_design_rule = false, dont_scale = false;
    uint64_t order = 0;
    std::vector<std::string> port_names;
};

// ─── OCV derate ─────────────────────────────────────────────────────
struct OcvDerateDef {
    float early_data = 1.0f;
    float late_data = 1.0f;
    float early_clock = 1.0f;
    float late_clock = 1.0f;
};

// ─── AOCV table ─────────────────────────────────────────────────────
struct AocvPointDef {
    int depth = 0;
    float late_derate = 1.0f;
    float early_derate = 1.0f;
};

// ─── Design rule constraints ────────────────────────────────────────
struct DesignRuleDef {
    float max_fanout = -1.0f;        // negative = not set
    float max_capacitance = -1.0f;
    float max_transition = -1.0f;
};

// ─── Unified constraint database ────────────────────────────────────
// This is the single source of truth for all SDC-style constraints.
// Both fsyn and ftimer read from and write to this database.
//
// String-based interface: pin/port names are resolved to handles
// by the consumer (ftimer resolves against its attached gate view,
// fsyn against its own port naming).
class ConstraintDB {
public:
    ConstraintDB() = default;

    // ── Clocks ───────────────────────────────────────────────────
    void add_clock(ClockDef clock);
    const ClockDef* find_clock(const std::string& name) const;
    const ClockDef* clock_for_port(const std::string& port) const;
    const std::vector<ClockDef>& clocks() const { return clocks_; }
    void set_clock_propagated(const std::string& name, bool propagated = true);
    // Recompute dependent waveforms after a master definition changes.
    // Missing/ambiguous masters, cycles and unrepresentable waveforms fail.
    bool resolve_generated_clocks(std::string& error);

    // ── Clock groups ────────────────────────────────────────────────
    void add_clock_group(ClockGroupDef group);
    const std::vector<ClockGroupDef>& clock_groups() const { return clock_groups_; }

    // ── I/O delays ───────────────────────────────────────────────
    void add_io_delay(IoDelay delay);
    const std::vector<IoDelay>& io_delays() const { return io_delays_; }
    std::vector<IoDelay> input_delays() const;
    std::vector<IoDelay> output_delays() const;

    // ── Path delays ──────────────────────────────────────────────
    void add_path_delay(PathDelay pd);
    const std::vector<PathDelay>& path_delays() const { return path_delays_; }

    void add_data_check(DataCheckDef check);
    const std::vector<DataCheckDef>& data_checks() const { return data_checks_; }

    void add_path_group(PathGroupDef group);
    const std::vector<PathGroupDef>& path_groups() const { return path_groups_; }

    // ── Clock latency ────────────────────────────────────────────
    void add_clock_latency(ClockLatencyDef cl);
    const std::vector<ClockLatencyDef>& clock_latencies() const { return clock_latencies_; }

    // ── Clock uncertainty ────────────────────────────────────────
    void set_clock_uncertainty(ClockUncertaintyDef cu);
    const std::vector<ClockUncertaintyDef>& clock_uncertainties() const { return clock_uncertainties_; }

    // ── Clock waveform ───────────────────────────────────────────
    void set_clock_waveform(const std::string& clock_name,
                            float rise_ns, float fall_ns);
    // Set the source slew used when an ideal clock launches through a
    // characterized clock/data arc.  A negative value restores the default.
    bool set_clock_transition(const std::string& clock_name, float transition_ns);

    // ── Multicycle paths ─────────────────────────────────────────
    void add_multicycle_path(MulticyclePathDef mcp);
    const std::vector<MulticyclePathDef>& multicycle_paths() const { return multicycle_paths_; }

    // ── False paths ──────────────────────────────────────────────
    void add_false_path(FalsePathDef fp);
    const std::vector<FalsePathDef>& false_paths() const { return false_paths_; }

    // ── Disable timing ───────────────────────────────────────────
    void add_disable_timing(DisableTimingDef dt);
    const std::vector<DisableTimingDef>& disable_timings() const { return disable_timings_; }

    // ── Case analysis ────────────────────────────────────────────
    void add_case_analysis(CaseAnalysisDef ca);
    const std::vector<CaseAnalysisDef>& case_analyses() const { return case_analyses_; }

    // ── Set load ─────────────────────────────────────────────────
    void add_set_load(SetLoadDef sl);
    const std::vector<SetLoadDef>& set_loads() const { return set_loads_; }

    // ── Input transition ─────────────────────────────────────────
    void add_input_transition(InputTransitionDef it);
    const std::vector<InputTransitionDef>& input_transitions() const { return input_transitions_; }
    void add_driving_cell(DrivingCellDef driver);
    const std::vector<DrivingCellDef>& driving_cells() const { return driving_cells_; }

    // ── OCV/AOCV ─────────────────────────────────────────────────
    void set_ocv_derate(OcvDerateDef derate);
    const OcvDerateDef& ocv_derate() const { return ocv_derate_; }

    void add_aocv_point(AocvPointDef point);
    const std::vector<AocvPointDef>& aocv_points() const { return aocv_points_; }

    // ── Design rules ─────────────────────────────────────────────
    void set_max_fanout(float value);
    void set_max_capacitance(float value);
    void set_max_transition(float value);
    const DesignRuleDef& design_rules() const { return design_rules_; }

    // ── Utility ──────────────────────────────────────────────────
    bool has_constraints() const;
    void clear();

    // ── Port name expansion helper ───────────────────────────────
    // Register bus port widths so that "p" can be expanded to "p[0]".."p[N-1]".
    void register_bus_port(const std::string& base_name, uint16_t width);
    std::vector<std::string> expand_port_name(const std::string& name) const;
    // Materialize I/O, input-transition and driver port globs against the
    // current linked top ports. Unmatched selectors remain diagnosable.
    void materialize_port_collections(const std::vector<std::string>& ports);
    // Directional all-port collections need linked port direction evidence.
    // Preserve unresolved selectors when no matching ports exist; an empty
    // scope must never silently turn into an unconstrained or all-object scope.
    void materialize_port_collections(const std::vector<std::string>& ports,
                                     const std::vector<std::string>& inputs,
                                     const std::vector<std::string>& outputs) {
        auto expand = [&](std::vector<std::string>& selectors) {
            std::vector<std::string> result;
            std::unordered_set<std::string> seen;
            for (const auto& selector : selectors) {
                const std::vector<std::string>* collection = nullptr;
                if (std::find(ports.begin(), ports.end(), selector) == ports.end()) {
                    if (selector == "all_inputs") collection = &inputs;
                    if (selector == "all_outputs") collection = &outputs;
                }
                if (collection && !collection->empty()) {
                    for (const auto& port : *collection)
                        if (seen.insert(port).second) result.push_back(port);
                } else if (seen.insert(selector).second) result.push_back(selector);
            }
            selectors = std::move(result);
        };
        for (auto& delay : io_delays_) expand(delay.port_names);
        for (auto& transition : input_transitions_) expand(transition.port_names);
        for (auto& driver : driving_cells_) expand(driver.port_names);
        for (auto& load : set_loads_) expand(load.pin_names);
        materialize_port_collections(ports);
    }

private:
    std::vector<ClockDef> clocks_;
    std::vector<ClockGroupDef> clock_groups_;
    std::vector<IoDelay> io_delays_;
    std::vector<PathDelay> path_delays_;
    std::vector<DataCheckDef> data_checks_;
    std::vector<PathGroupDef> path_groups_;
    std::vector<ClockLatencyDef> clock_latencies_;
    std::vector<ClockUncertaintyDef> clock_uncertainties_;
    std::vector<MulticyclePathDef> multicycle_paths_;
    std::vector<FalsePathDef> false_paths_;
    std::vector<DisableTimingDef> disable_timings_;
    std::vector<CaseAnalysisDef> case_analyses_;
    std::vector<SetLoadDef> set_loads_;
    std::vector<InputTransitionDef> input_transitions_;
    std::vector<DrivingCellDef> driving_cells_;
    uint64_t input_driver_order_ = 0;
    OcvDerateDef ocv_derate_;
    std::vector<AocvPointDef> aocv_points_;
    DesignRuleDef design_rules_;

    // Bus port width map: base_name -> width
    std::unordered_map<std::string, uint16_t> bus_port_widths_;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_CONSTRAINT_DB_HPP
