#pragma once

#include <mutex>
#include <map>
#include <tuple>
#include <array>
#include <utility>
#include <unordered_map>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "parasitics/timing_parasitics.hh"
#include "sdc/resolved_constraints.hh"
#include "dcalc/delay_result.hh"
#include "dcalc/rc_waveform_dcalc.hh"

namespace te {

class TimingGraph;
class Network;
class NldmDelayCalc;
class CsmDelayCalc;
class AweDelayCalc;

// ────────────────────────────────────────────────────────────
// Arrival Propagator: forward BFS from startpoints
// ────────────────────────────────────────────────────────────
//
// Propagates arrival times through the timing graph:
// 1. Initialize startpoints with arrival = 0 (or input delay from SDC)
// 2. Process vertices in topological order (level by level)
// 3. For each vertex:
//    a. Collect arrival + delay from all fanin edges
//    b. Take worst (max for max analysis, min for min analysis)
//    c. Store arrival and slew at this vertex
//
// For each vertex, we compute 4 values:
//   arrival(mm, rf) where mm ∈ {Min, Max}, rf ∈ {Rise, Fall}

class ArrivalPropagator {
public:
    ArrivalPropagator(
        TimingGraph& graph,
        const Network& network,
        const edacraft::core::LibertyDB& liberty,
        TimingParasiticDB& parasitics,
        const NldmDelayCalc& gate_calc,
        const CsmDelayCalc& csm_calc,
        const AweDelayCalc& wire_calc,
        const ResolvedConstraintSet* sdc = nullptr,
        float vdd = 1.0f
    ) : graph_(graph), network_(network), liberty_(liberty),
        parasitics_(parasitics), gate_calc_(gate_calc), csm_calc_(csm_calc),
        wire_calc_(wire_calc), sdc_(sdc), vdd_(vdd) {}

    // Full forward propagation (all vertices, level by level)
    void propagate_all();

    // Incremental propagation from dirty vertices
    void propagate_dirty();

    // Refresh the CCS lumped receiver envelope, e.g. after cell replacement.
    bool refine_receiver_caps(Network& network);
    bool used_full_propagation() const { return full_propagation_; }

    // Independent data-path observations at sequential clock inputs. These
    // must never replace the clock event used for clock-to-Q or timing checks.
    using ClockPinDataPaths = std::unordered_map<uint32_t, std::array<float, 8>>;
    void set_clock_pin_data_paths(const ClockPinDataPaths& values) { clock_pin_data_paths_ = values; }
    const ClockPinDataPaths& clock_pin_data_paths() const { return clock_pin_data_paths_; }

    struct LabelEdgeResult {
        float delay = 0, slew = 0, wire_source_slew = 0;
        uint64_t waveform_context = 0;
    };
    LabelEdgeResult characterize_label_edge(uint32_t eid, MinMax mm,
        float input_slew, float wire_source_slew, uint64_t waveform_context, int path_depth = -1);
    uint64_t seed_label_waveform(uint32_t vid, MinMax mm);

private:
    // Process a single vertex: compute arrival from all fanin
    void process_vertex(uint32_t vid);
    void process_vertex_analysis(uint32_t vid, MinMax mm, uint32_t only_edge = UINT32_MAX);

    // Pre-compute total load capacitance per net for the current parasitic state.
    void prepare_net_load_caps();
    void apply_driving_cells();
    void prepare_alias_rc();
    const FullRcNetwork* effective_rc(NetId net, bool detailed_only = true) const;
    void expand_alias_responses(RcWaveformResult& result, NetId net) const;
    // Returns total charge in extraction capacitance units, accumulating
    // wire and receiver contributions before rounding additions into nodes.
    double load_rc_receivers(FullRcNetwork& rc, NetId net, Transition rf,
                           float receiver_slew = -1.0f,
                           float receiver_load = -1.0f,
                           std::vector<RcReceiverCapacitance>* regions = nullptr,
                           const RcWaveformResult* previous = nullptr,
                           float driver_time_unit_ns = 0.f, bool late = true,
                           bool initial_reported_slew = false,
                           std::vector<double>* precise_node_caps = nullptr) const;

    // Compute logic depth (gate levels from startpoint) for each vertex
    void compute_depths();
    void prepare_clock_pin_data_paths(bool reset);

    // AOCV depth-based derate lookup
    float get_aocv_late_derate(int depth) const;
    float get_aocv_early_derate(int depth) const;

    TimingGraph& graph_;
    const Network& network_;
    const edacraft::core::LibertyDB& liberty_;
    TimingParasiticDB& parasitics_;
    const NldmDelayCalc& gate_calc_;
    const CsmDelayCalc& csm_calc_;
    const AweDelayCalc& wire_calc_;
    const ResolvedConstraintSet* sdc_;
    float vdd_;

    // Per-vertex logic depth for AOCV (number of gate arcs from startpoint)
    std::vector<int> vertex_depth_;
    std::vector<uint8_t> clock_cone_;

    // Cached total load per net, independently for min/max and rise/fall.
    std::vector<std::array<float, 4>> net_load_cap_;
    // Receiver-table output coordinates, frozen after all loaded Pi reductions.
    // Min/max coordinates stay separate; values use the output driver's cap unit.
    std::vector<std::array<float,2>> receiver_output_load_;
    std::vector<std::array<std::unordered_map<uint32_t, float>, 4>> net_pin_elmore_;
    std::vector<std::array<std::unordered_map<uint32_t, DelayResult>, 4>> net_waveforms_;
    using LabelWaveforms = std::unordered_map<uint32_t, DelayResult>;
    std::map<std::tuple<uint32_t, unsigned, float, float, uint64_t, int>, LabelEdgeResult> label_edge_cache_;
    std::unordered_map<uint64_t, LabelWaveforms> label_waveforms_;
    uint64_t next_waveform_context_ = 1;
    std::vector<uint32_t> rc_owner_;
    std::vector<uint32_t> net_component_;
    std::unordered_map<uint32_t, float> alias_coupling_;
    std::unordered_map<uint32_t, FullRcNetwork> alias_rc_;
    std::unordered_map<uint32_t, std::vector<std::pair<PinId, uint32_t>>> alias_pin_nodes_;
    bool full_propagation_ = false;
    ClockPinDataPaths clock_pin_data_paths_;

    // Simple path sensitization state for Liberty `when` conditions.
    std::vector<std::vector<std::pair<uint32_t, int8_t>>> max_condition_state_;
    std::vector<std::vector<std::pair<uint32_t, int8_t>>> min_condition_state_;

    // Cached driver resistance per (pin, transition) for 2-pole solver.
    // Key = (pin_id << 1) | (is_rise ? 1 : 0)
    mutable std::mutex rd_cache_mutex_;
    std::unordered_map<uint64_t, float> rd_cache_;
};

} // namespace te
