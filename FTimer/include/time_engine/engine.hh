#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "edacraft/core/ids.hpp"
#include "edacraft/core/string_pool.hpp"

namespace edacraft::core {
class ConstraintDB;
class DesignDB;
class GateNetlistView;
}

namespace te {

// All values are in ns. A data-path arrival retains its launch event phase;
// a raw PT pin attribute can use a different (zero-origin) time reference.
struct ClockPinTiming {
    float clock_arrival;
    float clock_slew;
    float data_path_arrival;
    float data_path_slew;
};

struct PathReport {
    float slack;
    float cppr;  // Common Path Pessimism Removal
    uint32_t start_clock_domain = UINT32_MAX;
    uint32_t end_clock_domain = UINT32_MAX;
    std::vector<std::string> point_names;
    std::vector<std::string> cell_names;
    std::vector<float> delays;
    std::vector<float> arrivals;
    std::vector<float> slews;           // transition slew at each point
    std::vector<std::string> transitions; // "rise" / "fall" at each point
    TimingCheckKind check_kind = TimingCheckKind::None;
    // Present for report_check_paths: identifies the exact Liberty/output
    // check, capture edge and launch history whose numeric slack is reported.
    std::optional<TimingCheckResult> check;
    // Explicit endpoints for checks whose related pin is not the ordinary
    // graph predecessor used by the path back-tracer (for example SDC
    // set_data_check).  Keeping these names in the report makes the
    // constraint source/destination observable to CLI, Python and C users.
    std::string check_related_name;
    std::string check_endpoint_name;
    std::string path_group;
    bool path_based = false;
};

// A lightweight in-process MCMM container.  Each scenario owns its timing
// engine, so Liberty/SDC/SPEF/PVT state cannot leak between corners.  This
// is intentionally independent of fsyn and can be used by C++ regression
// drivers in the same way as the Python scenario sweep.
struct ScenarioSpec {
    std::string name;
    std::vector<std::string> liberty_files;
    std::string verilog_file;
    std::string spef_file;
    std::string sdc_file;
    float voltage = 1.0f;
    float temperature = 25.0f;
};

struct ScenarioResult {
    std::string name;
    float voltage = 1.0f;
    float temperature = 25.0f;
    float setup_slack = 0.0f;
    float hold_slack = 0.0f;
    uint64_t timing_generation = 0;
};

struct DrivenNetInfo {
    NetId net = NULL_NET;
    std::string name;
    uint32_t fanout = 0;
    float fanout_load = 0.0f;
    float total_load_cap = 0.0f;
    PinId driver_pin = NULL_PIN;
    std::string driver_instance_name;
    std::string driver_cell_name;
};

struct GateViewAttachResult {
    std::unordered_map<std::string, PinId> pins_by_full_name;
    std::unordered_map<uint32_t, edacraft::core::PinHandle> pin_to_core_pin;
    std::unordered_map<uint32_t, PinId> core_pin_to_pin;
    std::unordered_map<std::string, std::vector<PinId>> port_aliases;
};

// ────────────────────────────────────────────────────────────
// TimingView: zero-copy read-only access to timing results
// ────────────────────────────────────────────────────────────
// The pointer fields point into TimingGraph's internal SOA arrays.
// They are valid until the next update_timing() call.
// ────────────────────────────────────────────────────────────
struct TimingView {
    uint32_t vertex_count = 0;

    // Flat arrays: index = vid * 4 + mm_rf_index(mm, rf)
    //   mm_rf_index(MinMax::Min, Transition::Rise) = 0
    //   mm_rf_index(MinMax::Min, Transition::Fall) = 1
    //   mm_rf_index(MinMax::Max, Transition::Rise) = 2
    //   mm_rf_index(MinMax::Max, Transition::Fall) = 3
    const float* arrival = nullptr;
    const float* slew = nullptr;
    const float* required = nullptr;

    // Path tracing predecessors (per-mm_rf, same layout as arrival)
    const uint32_t* pred_max = nullptr;
    const uint32_t* pred_min = nullptr;

    static constexpr uint32_t idx(MinMax mm, Transition rf) {
        return static_cast<uint32_t>(mm) * 2 + static_cast<uint32_t>(rf);
    }

    float get_arrival(uint32_t vid, MinMax mm, Transition rf) const {
        if (!arrival || vid >= vertex_count) return 0.0f;
        return arrival[vid * 4 + idx(mm, rf)];
    }
    float get_slew(uint32_t vid, MinMax mm, Transition rf) const {
        if (!slew || vid >= vertex_count) return 0.0f;
        return slew[vid * 4 + idx(mm, rf)];
    }
    float get_required(uint32_t vid, MinMax mm, Transition rf) const {
        if (!required || vid >= vertex_count) return 0.0f;
        return required[vid * 4 + idx(mm, rf)];
    }
    float get_slack(uint32_t vid, MinMax mm, Transition rf) const {
        float arrival = get_arrival(vid, mm, rf);
        float required = get_required(vid, mm, rf);
        return mm == MinMax::Min ? (arrival - required) : (required - arrival);
    }
    uint32_t get_pred_max(uint32_t vid, MinMax mm, Transition rf) const {
        if (!pred_max || vid >= vertex_count) return UINT32_MAX;
        return pred_max[vid * 4 + idx(mm, rf)];
    }
    uint32_t get_pred_min(uint32_t vid, MinMax mm, Transition rf) const {
        if (!pred_min || vid >= vertex_count) return UINT32_MAX;
        return pred_min[vid * 4 + idx(mm, rf)];
    }
};

// Main engine facade. Uses Pimpl for ABI stability.
class TimingEngine {
public:
    // Exhaustive DAG path enumeration with route-specific slew, delay, AOCV
    // depth and constraints. Exceeding the label budget throws (no truncation).
    std::vector<PathReport> report_pba_paths(MinMax mm, int count,
        std::string_view group = {}, size_t path_label_limit = 1000000,
        TimingCheckKind kind = TimingCheckKind::Data) const;
    using ConstraintPinResolver = std::function<std::vector<PinId>(const std::string&)>;
    using ConstraintStringInterner = std::function<uint32_t(const std::string&)>;
    using DrivenNetVisitor = std::function<void(const DrivenNetInfo&)>;

    TimingEngine();
    ~TimingEngine();

    // Configuration
    void set_thread_count(int n);
    void set_pvt(float voltage, float temperature);
    void set_temperature(float temperature);
    void set_verbose(bool verbose = true);
    // Select the Verilog root explicitly when a file contains multiple
    // uninstantiated modules (for example a design plus black-box stubs).
    // Must be called before read_verilog().  An empty name restores automatic
    // root detection.
    void set_top_design(std::string_view top_name);

    // Loading
    void read_liberty(std::string_view filepath);
    void use_external_liberty(const edacraft::core::LibertyDB& liberty);
    // Import an external Liberty database whose StringId values belong to a
    // different pool.  The database is remapped into this engine's network
    // pool before linking the design.
    void use_external_liberty(
        const edacraft::core::LibertyDB& liberty,
        const edacraft::core::StringPool& liberty_strings);
    void read_verilog(std::string_view filepath);
    void read_spef(std::string_view filepath);
    void read_sdc(std::string_view filepath);
    void apply_constraints(const edacraft::core::ConstraintDB& constraints,
                           const ConstraintPinResolver& pin_resolver,
                           const ConstraintStringInterner& string_interner,
                           bool verbose = false);
    void apply_design_constraints(edacraft::core::DesignDB& design,
                                  bool verbose = false);

    // Linking
    void link_design();

    // Timing analysis
    void update_timing();
    void update_incremental();

    // Results: all timing quantities use ns, independently of Liberty units.
    float get_arrival(PinId pin, Transition rf, MinMax mm) const;
    // Separate clock-event and physical data-path results at a sequential
    // clock input. Missing/unreachable data observations are NaN, never zero.
    std::optional<ClockPinTiming> get_clock_pin_timing(PinId pin, Transition rf, MinMax mm) const;
    // Unavailable required time is +/-infinity; unavailable slack is NaN.
    float get_required(PinId pin, Transition rf, MinMax mm) const;
    float get_slew(PinId pin, Transition rf, MinMax mm) const;
    float get_slack(PinId pin, Transition rf, MinMax mm) const;
    float worst_slack(MinMax mm, TimingCheckKind kind = TimingCheckKind::Data) const;
    uint64_t timing_generation() const;
    std::vector<PinId> endpoint_pins() const;
    std::vector<PathReport> report_worst_paths(MinMax mm, int count,
        TimingCheckKind kind = TimingCheckKind::Data,
        std::string_view path_group = {}) const;
    std::vector<PinId> timing_check_endpoints(TimingCheckKind kind = TimingCheckKind::Any) const;
    std::vector<TimingCheckCoverage> timing_check_coverage() const;
    // Every Liberty check/launch and characterized output check, including
    // nonbinding checks and explicit exclusions. Numeric values are in ns.
    std::vector<TimingCheckResult> timing_check_results() const;
    // One path per evaluated check/launch/data transition, ordered by slack.
    // Excluded and unavailable checks are omitted. Unlike endpoint reports,
    // this preserves nonbinding captures and uses the check ledger's slack
    // directly (no additional report-only CPPR or output phase adjustment).
    std::vector<PathReport> report_check_paths(MinMax mm, int count,
        TimingCheckKind kind = TimingCheckKind::Any, bool balance_groups = false,
        std::string_view path_group = {}) const;
    // Report paths with the largest propagated data delay, independent of
    // clock period/slack.  Useful for preserving coverage across unrelated
    // clock domains when the internal timing model is approximate.
    std::vector<PathReport> report_longest_paths(MinMax mm, int count) const;

    // Dirty tracking
    void mark_net_dirty(NetId net);
    void mark_pin_dirty(PinId pin);
    void mark_all_dirty();

    // Net / pin lookup
    std::optional<NetId> find_net(std::string_view name) const;
    // Explicit literal on the CURRENT attached net, never an inferred gate
    // constant. Reject driven nets, stale pin IDs and changed net bindings.
    std::optional<int> literal_constant_value(PinId pin,
        std::string_view expected_net_name) const;
    std::optional<PinId> find_pin(std::string_view name) const;
    std::optional<PinId> find_instance_pin(
        std::string_view instance_name,
        std::string_view port_name) const;
    void for_each_driven_net(const DrivenNetVisitor& visitor) const;
    uint32_t pin_count() const;
    std::string_view pin_name(PinId pin) const;
    std::string_view pin_instance_name(PinId pin) const;

    // Parasitics access (for external engines)
    float get_net_cap(NetId net) const;
    // Physical wire + receiver/external loading, without double-counting
    // extracted pin caps. Returns the worst transition in driver library units.
    float get_net_load_cap(NetId net) const;
    // Explicit terminal loads, excluding Liberty receiver and wire capacitance.
    // Uses the same driver-library units as get_net_load_cap().
    float get_net_terminal_load_cap(NetId net) const;
    void set_wire_pi_model(NetId net, float c1, float rpi, float c2,
                           float cap_scale = 1e-15f);
    void add_coupling_capacitance(NetId net1, NetId net2, float capacitance);

    // AOCV (Advanced OCV) depth-based derate table
    struct AocvPoint {
        int depth;
        float late_derate;
        float early_derate;
    };
    void set_aocv_derate(const std::vector<AocvPoint>& points);

    // ── Synthesis integration (zero-copy, non-text) ─────────────────

    GateViewAttachResult attach_gate_view(
        const edacraft::core::GateNetlistView& view,
        const std::unordered_map<std::string, std::vector<std::string>>& port_aliases = {},
        edacraft::core::StringPool* shared_string_pool = nullptr);
    GateViewAttachResult attach_design_db(
        edacraft::core::DesignDB& design,
        const std::unordered_map<std::string, std::vector<std::string>>& port_aliases = {});
    bool replace_instance_cell(std::string_view instance_name,
                               std::string_view cell_name,
                               const std::vector<std::string>& input_pins,
                               std::string_view output_pin);
    bool replace_instance_cell(std::string_view instance_name,
                               std::string_view cell_name,
                               const std::vector<std::string>& input_pins,
                               const std::vector<std::string>& output_pins);
    std::optional<edacraft::core::PinHandle> core_pin_for_pin(PinId pin) const;
    std::optional<PinId> pin_for_core_pin(edacraft::core::PinHandle core_pin) const;

    // Batch incremental analysis: mark changed nets/pins dirty and propagate.
    // This avoids the overhead of per-net/pin API calls when the synthesis
    // tool already knows exactly what changed.
    void update_timing_incremental(
        const std::vector<NetId>& changed_nets,
        const std::vector<PinId>& changed_pins
    );

    // Liberty cell queries: input/output timing in ns, load in cell-library units.
    float get_cell_area(std::string_view cell_name) const;
    float get_cell_delay(std::string_view cell_name,
                          std::string_view from_pin,
                          std::string_view to_pin,
                          float input_slew = 0.02f,
                          float load_cap = 0.001f) const;
    float get_cell_output_slew(std::string_view cell_name,
                                std::string_view from_pin,
                                std::string_view to_pin,
                                float input_slew = 0.02f,
                                float load_cap = 0.001f) const;

    // Averaged power with independent-input activity propagation. Reference
    // clocks enable a per-cycle transition matrix (simultaneous transitions
    // cancel) and simple FF data propagation. Without source clocks use the
    // continuous-time Boolean derivative when no reference frequency exists.
    // This is not PT's random simulator.
    // Explicit net activity always takes precedence. Activity
    // is BOTH-edge toggles per reference cycle (clock activity is 2).
    // No glitch or sequential-state correlation model is implied.
    struct PowerSummary {
        float leakage_w = 0.0f;
        float internal_w = 0.0f;
        float switching_w = 0.0f;
        float total_w = 0.0f;
        float frequency_hz = 0.0f;
        float activity = 0.0f;
    };
    PowerSummary estimate_power(float frequency_hz,
                                float activity = 0.1f) const;
    // Explicit net or pin activity: both-edge transitions/second and P(1).
    // A pin annotation applies to its connected net. Unknown objects fail.
    void set_power_activity(std::string_view object, double toggle_rate_hz,
                            double static_probability = .5);
    // "clocked" (default) or legacy "independent" Boolean-derivative rates.
    // The fastest SDC clock supplies the observation interval, or frequency_hz
    // when no SDC clock exists. Explicit activities are never rescaled.
    void set_power_propagation_mode(std::string_view mode);
    // Events already include state/path conditioning; no second P(when) factor.
    // Empty when selects an unconditional group; related_pin is a cell pin name.
    // Input-pin groups without related_pin use an empty name and their local
    // density directly; inferred groups are capped by the residual input budget.
    // Output groups share the net's event budget.
    void set_power_internal_activity(std::string_view pin, std::string_view when,
        std::string_view related_pin, double toggle_rate_hz, double rise_ratio=.5);
    void clear_power_activity();
    struct PowerNet {
        std::string name, source;
        double toggle_rate_hz=0, static_probability=.5, capacitance_f=0;
        float switching_w=0;
        bool included_in_total=false;
    };
    struct PowerCell {
        std::string name;
        float leakage_w=0, internal_w=0, switching_w=0, total_w=0;
        std::string cell_name;
    };
    struct PowerDetail {
        PowerSummary summary;
        std::vector<PowerNet> nets;
        std::vector<PowerCell> cells;
        uint32_t annotated_nets=0, propagated_nets=0, default_nets=0, constant_nets=0;
        uint32_t clock_nets=0;
        uint32_t internal_annotated_groups=0;
        uint32_t unsupported_expressions=0;
        double activity_sample_hz=0;
        uint32_t activity_samples=0; // deterministic zero-delay samples for reconvergence/feedback
        uint32_t feedback_boundary_nets=0; // optional averaged primary-control boundaries
        uint64_t internal_groups_available=0, internal_groups_evaluated=0;
    };
    PowerDetail estimate_power_detail(float frequency_hz, float activity=.1f) const;
    // Call-local inputs leave persistent annotations and timing/SDC unchanged.
    // A positive reference frequency selects the power observation interval,
    // independently of the clocks used to explore timing architectures.
    struct PowerActivityValue {
        std::string object;
        double toggle_rate_hz=0, static_probability=.5;
    };
    struct PowerOptions {
        bool propagate_activity=true;
        double static_probability=.5, reference_frequency_hz=0;
        double clock_transitions_per_cycle=-1; // negative: native clock default
        std::vector<PowerActivityValue> activities;
        // Used only for unannotated inputs without a physical SDC clock.
        std::vector<PowerActivityValue> fallback_activities;
        std::vector<std::pair<std::string,uint8_t>> fixed_values;
        // Permit call-local power values to replace SDC case assumptions.
        // Physical constants and contradictory explicit aliases still reject.
        bool fixed_values_override_sdc=false;
    };
    PowerDetail estimate_power_detail(float frequency_hz, float activity,
                                      const PowerOptions& options) const;

    // Coupling inventory and SI capabilities. The standalone linear waveform
    // solver is separate from timing propagation; no CCSN/iterative SI STA.
    struct SiSummary {
        uint32_t victim_nets = 0;
        float total_coupling_cap = 0.0f;
        float max_victim_coupling_cap = 0.0f;
        bool crosstalk_waveform_solver = true;
        bool si_timing_applied = false;
    };
    SiSummary analyze_si() const;
    struct SiCoupling {
        std::string victim_net;
        std::string aggressor_net;
        float coupling_cap = 0.0f;
        float victim_total_coupling_cap = 0.0f;
        float coupling_ratio = 0.0f;
    };
    // Return normalized coupling pairs sorted by descending capacitance.
    // This is an SI inventory; it does not claim a solved noise waveform.
    std::vector<SiCoupling> analyze_si_detail() const;

    struct SiAggressor {
        std::string net;
        bool rise = false;
        float offset_ns = 0;
        // >0: explicit Thevenin R. Otherwise use an effective fixed SDC input
        // transition as a prescribed port waveform; estimate R for other sources.
        float driver_resistance_ohm = 0;
    };
    struct SiWaveformOptions {
        bool victim_rise = true;
        bool quiet_victim = false;
        bool respect_timing_windows = true;
        // >0: explicit R; otherwise a switching primary input with an effective
        // fixed SDC transition uses its prescribed waveform. Quiet victims
        // still need a holding model; fixed switching slew does not provide one.
        float victim_resistance_ohm = 0;
        float step_ns = 0.0005f;
        uint32_t max_steps = 100000;
    };
    // Characterized quiet-victim output I-V: absolute volts and injected mA;
    // ordered voltages and nonincreasing currents. Supplied explicitly,
    // without automatic Liberty selection or a full dynamic CCSN model.
    struct SiStaticIv {
        std::vector<double> voltage_v, current_ma;
        // Optional output-node charge in pC, PWL on voltage_v, nondecreasing.
        // Its time derivative is drawn from the physical driver node. Supply
        // only de-embedded intrinsic charge, excluding SPEF, receiver and
        // separately stamped Miller capacitances. An empty table adds none.
        // Charge is defined up to an additive constant; no voltage extrapolation.
        std::vector<double> output_charge_pc;
    };
    // Explicit source law at an aggressor's physical driver node:
    // I(t,V) = injection_ma(t) - conductance_ma_per_v(t) * V.
    // Times are absolute ns in the solve frame, not offsets from STA arrival.
    // All sources must share a complete analysis window, including recovery.
    // Tables are PWL, with no time extrapolation. The caller is responsible
    // for characterization/de-embedding; these are not automatic CCSN models.
    struct SiNortonSource {
        std::string net;
        std::vector<double> time_ns, injection_ma, conductance_ma_per_v;
    };
    // Explicit experimental single-stage CCSN-data circuit with prescribed
    // input. A caller selects the stage/when and supplies de-embedded parameters.
    // No automatic stage assembly, receiver feedback or STA graph update.
    // tau_ns>0 relaxes input excitation at the initial output reference;
    // output recovery feedback remains instantaneous. This is an explicit
    // hypothesis, not a complete reconstruction of a vendor CCSN model.
    struct SiExperimentalStage {
        std::string provenance;
        std::vector<double> input_voltage_v, output_voltage_v, current_ma;
        std::vector<double> time_ns, input_v;
        double miller_pf=0., output_pf=0., tau_ns=0.;
        // Optional intrinsic (output V, differential pF) profile, added to
        // output_pf and integrated as charge. Ordered finite V, nonnegative C,
        // >=2 knots, constant endpoint C. Excludes Cm, SPEF and receiver load.
        // Explicit supplied hypothesis; never inferred automatically from CCSN.
        std::vector<std::pair<double,double>> output_cap_profile;
        // Explicitly reproduce the old whole-current relaxation for diagnostics.
        // Default false avoids delaying quiet-output restoring feedback.
        bool lag_output_feedback=false;
    };
    struct SiCharacterizationWaveform {
        std::string kind;
        double input_transition_ns=0., noise_height_v=0., noise_width_ns=0., load_pf=0.;
        std::vector<double> time_ns, output_v;
    };
    struct SiLibraryStage {
        SiExperimentalStage model; // Cout/tau remain zero until explicitly supplied
        std::string stage_type; // pull_up / pull_down / both; does not identify CCB count/topology
        bool inverting=false;
        uint32_t equivalent_conditions=0;
        std::vector<SiCharacterizationWaveform> characterization; // measured references, not fitted current laws
    };
    // Read a condition-selected retained stage. Empty related_pin selects a
    // pin-owned stage; otherwise select an output pin's timing-owned stage.
    // Fixed states must resolve all conditions; no topology/parameter fitting.
    SiLibraryStage read_si_ccsn_stage(std::string_view owner_pin,
        std::string_view related_pin,bool first_stage,bool output_rise,
        const std::vector<std::pair<std::string,int>>& fixed_state) const;
    struct SiReceiverStage {
        std::string input_pin, output_net;
        SiExperimentalStage model; // input waveform must be empty: input is solved
        double input_pf=0.; // intrinsic input-to-ground C excluding Miller C
        double initial_output_v=0.;
    };
    struct SiNodeWaveform {
        uint32_t node = UINT32_MAX;
        std::string pin;
        std::vector<float> baseline_voltage, voltage;
        float delay_delta_ns = 0, slew_delta_ns = 0, noise_peak_v = 0;
        float noise_width_ns = 0; // width above 10% Vdd relative to baseline
        std::string net; // receiver-enabled solves also return receiver output nets
    };
    struct SiWaveformResult {
        std::string victim_net;
        std::string model = "linear_thevenin";
        uint32_t active_aggressors = 0;
        std::vector<float> time_ns;
        std::vector<SiNodeWaveform> nodes;
    };
    // Solve the coupled extracted RC component, including off-diagonal C,
    // multiple switching aggressors and quiet-victim noise. Uses effective
    // fixed SDC input waveforms at switching primary ports, and linear Thevenin
    // surrogates for other drivers. An explicit I-V replaces the quiet victim
    // driver only. This is not CCSN signoff.
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options) const;
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
        const SiStaticIv& victim_iv) const;
    // Explicit ideal primary-port aggressors. Their prescribed ramp is
    // enforced at the physical driver node; no slew-derived source R is
    // added. Names must select aggressors driven by primary ports. This also
    // permits an explicit boundary when no fixed SDC input transition is active.
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
        const SiStaticIv& victim_iv, const std::vector<std::string>& ideal_port_aggressors) const;
    // Characterized aggressors replace their Thevenin surrogates, retaining
    // physical R/C and voltage feedback. Requires explicit alignment
    // (respect_timing_windows=false, offset_ns=0) and no R/ideal override for
    // those nets. Other aggressors retain their existing source models.
    // The baseline holds each characterized source at its initial rail with
    // the same time-dependent conductance and event grid.
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
        const SiStaticIv& victim_iv, const std::vector<std::string>& ideal_port_aggressors,
        const std::vector<SiNortonSource>& characterized_sources) const;

    // Replaces a quiet victim's Thevenin driver with the explicit stage law.
    // Input waveform defines the complete solve window, including recovery.
    // Static I-V and victim R overrides cannot be combined with this stage.
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
        const SiStaticIv& victim_iv, const std::vector<std::string>& ideal_port_aggressors,
        const std::vector<SiNortonSource>& characterized_sources,
        const SiExperimentalStage& victim_stage) const;
    // Explicit connected receivers replace their pin load C and output drivers.
    // Requires SPEF without pin caps on these input nets, extracted output RC,
    // unique input/output bindings, and no characterized Norton sources.
    SiWaveformResult solve_si_waveforms(std::string_view victim,
        const std::vector<SiAggressor>& aggressors,const SiWaveformOptions& options,
        const SiStaticIv& victim_iv,const std::vector<std::string>& ideal_port_aggressors,
        const std::vector<SiNortonSource>& characterized_sources,
        const SiExperimentalStage& victim_stage,const std::vector<SiReceiverStage>& receivers) const;

    struct DesignRuleLimits {
        float max_fanout = -1.0f;
        float max_capacitance = -1.0f;
        float max_transition = -1.0f;
    };
    struct DesignRuleViolation {
        std::string rule;
        std::string object;
        float limit = 0.0f;
        float value = 0.0f;
    };
    // Return resolved SDC design-rule limits. Negative values mean unset.
    DesignRuleLimits design_rule_limits() const;
    // Global SDC checks: fanout is the sum of Liberty fanout_load, cap is
    // physical load in pF, and slew checks include driver/receiver pins.
    // Liberty-only and per-object rule overrides are not included yet.
    std::vector<DesignRuleViolation> design_rule_violations() const;

    // Obtain a zero-copy view of the current timing results.
    // Pointers are valid until the next update_timing() call.
    TimingView get_timing_view() const;

    // Write the current timing snapshot into the unified data model.
    // Uses the canonical pin binding table when one has been supplied; direct
    // ftimer flows fall back to PinId.id -> PinHandle.id.
    void update_design_db(edacraft::core::DesignDB& design) const;
    void update_design_db_points(edacraft::core::DesignDB& design) const;
    void update_design_db_incremental(edacraft::core::DesignDB& design) const;

    // Serialization
    void save_state(std::string_view filepath);
    void load_state(std::string_view filepath);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

class ScenarioManager {
public:
    void add_scenario(ScenarioSpec spec);
    void clear();
    const std::vector<ScenarioSpec>& scenarios() const { return specs_; }
    // Analyze every scenario independently and return one normalized result
    // per scenario.  File/parse errors propagate with the scenario name in
    // the exception message so batch regressions can identify the failure.
    std::vector<ScenarioResult> analyze() const;

private:
    std::vector<ScenarioSpec> specs_;
};

} // namespace te
