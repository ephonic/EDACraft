#include "required_propagator.hh"
#include "data_checks.hh"
#include "arrival_propagator.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>

#include "concurrent/parallel_for.hh"
#include "edacraft/core/liberty_db.hpp"
#include "graph/timing_graph.hh"
#include "network/network.hh"
#include "liberty/core_liberty_utils.hh"
#include "sdc/resolved_constraints.hh"
#include "timing_exceptions.hh"
#include "endpoint_checks.hh"

namespace te {

namespace ec = edacraft::core;

// Forward declarations
static float lookup_hold_constraint(
    const TimingGraph& graph,
    const Network& network,
    const ec::LibertyDB& liberty,
    uint32_t vid);

// Helper: check if a pin is a sequential output (Q)
static bool is_register_output(const Network& net, const ec::LibertyDB& liberty, PinId pin) {
    const auto& pin_data = net.pin(pin);
    if (!valid(pin_data.instance)) return false;
    const auto& inst_data = net.instance(pin_data.instance);
    const auto& cell_data = net.cell(inst_data.cell);
    if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) return false;
    const auto& lib_cell = liberty.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));
    for (const auto& arc : lib_cell.arcs) {
        if ((arc.type == ec::LibertyTimingType::RisingEdge || arc.type == ec::LibertyTimingType::FallingEdge) &&
            arc.to_pin == pin_data.name) {
            return true;
        }
    }
    return false;
}

// ────────────────────────────────────────────────────────────
// Endpoint initialization helpers
// ────────────────────────────────────────────────────────────

static float get_clock_period(const ResolvedConstraintSet* sdc, uint32_t domain = 0) {
    if (sdc) {
        if (domain < sdc->clocks().size()) {
            return sdc->clocks()[domain].period;
        }
        if (!sdc->clocks().empty()) {
            return sdc->clocks().front().period;
        }
    }
    return 0.0f;
}

static uint32_t get_clock_id(const ResolvedConstraintSet* sdc, uint32_t domain = 0) {
    if (sdc) {
        if (domain < sdc->clocks().size()) {
            return domain;
        }
        if (!sdc->clocks().empty()) {
            return 0;
        }
    }
    return UINT32_MAX;
}

static float get_clock_latency(const ResolvedConstraintSet* sdc, uint32_t domain = 0) {
    uint32_t clock_id = get_clock_id(sdc, domain);
    if (sdc && clock_id != UINT32_MAX) {
        for (const auto& cl : sdc->clock_latencies()) {
            if (cl.clock == clock_id) return cl.latency;
        }
    }
    return 0.0f;
}

static float get_setup_uncertainty(const ResolvedConstraintSet* sdc, uint32_t domain = 0) {
    uint32_t clock_id = get_clock_id(sdc, domain);
    if (sdc && clock_id != UINT32_MAX) {
        for (const auto& cu : sdc->clock_uncertainties()) {
            if (cu.clock == clock_id) return cu.setup_uncertainty;
        }
    }
    return 0.0f;
}

static float get_hold_uncertainty(const ResolvedConstraintSet* sdc, uint32_t domain = 0) {
    uint32_t clock_id = get_clock_id(sdc, domain);
    if (sdc && clock_id != UINT32_MAX) {
        for (const auto& cu : sdc->clock_uncertainties()) {
            if (cu.clock == clock_id) return cu.hold_uncertainty;
        }
    }
    return 0.0f;
}

static bool pin_in_list(PinId pin, const std::vector<PinId>& pins) {
    for (auto p : pins) {
        if (p == pin) return true;
    }
    return false;
}

// Helper: get the clock pin for a register data pin (D)
static PinId get_clock_pin_for_data(
    const TimingGraph& graph,
    const Network& network,
    const ec::LibertyDB& liberty,
    PinId data_pin)
{
    const auto& pin_data = network.pin(data_pin);
    if (!valid(pin_data.instance)) return PinId{UINT32_MAX};
    const auto& inst_data = network.instance(pin_data.instance);
    const auto& cell_data = network.cell(inst_data.cell);
    if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) return PinId{UINT32_MAX};
    const auto& lib_cell = liberty.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));

    for (const auto& arc : lib_cell.arcs) {
        if ((arc.type == ec::LibertyTimingType::SetupRising || arc.type == ec::LibertyTimingType::SetupFalling ||
             arc.type == ec::LibertyTimingType::HoldRising || arc.type == ec::LibertyTimingType::HoldFalling) &&
            arc.to_pin == pin_data.name) {
            for (auto pid : inst_data.pins) {
                const auto& p = network.pin(pid);
                if (p.name == arc.from_pin) return pid;
            }
            break;
        }
    }
    return PinId{UINT32_MAX};
}

// Output checks use the reference clock's rising edge for both data
// transitions. The output-delay transition selects rise/fall DATA, not
// opposite edges of the reference clock. Use the same repeating-edge search
// as Liberty checks for primary and generated launch/capture clock pairs.
static float output_clock_relation(const ResolvedConstraintSet* sdc,
    uint32_t capture, const LaunchTimingLabel* launch, MinMax mm) {
    const float period = get_clock_period(sdc, capture);
    if (!sdc || capture >= sdc->clocks().size() || !launch ||
        launch->domain >= sdc->clocks().size())
        return mm == MinMax::Max ? period : 0.f;
    const float phase = std::max(0.f, sdc->clocks()[capture].rise_time);
    const auto relation = generated_capture_relation(sdc->clocks()[launch->domain].period,
        period, launch->phase, phase, mm);
    return relation ? phase + *relation : std::numeric_limits<float>::quiet_NaN();
}

static void init_endpoint_required_setup(
    TimingGraph& graph, uint32_t vid,
    const ResolvedConstraintSet* sdc,
    const Network& network,
    const ec::LibertyDB& liberty, const LaunchTimingLabel* launch = nullptr)
{
    uint32_t domain = graph.vertex_clock_domain(vid);
    float clock_period = get_clock_period(sdc, domain);
    PinId pin = graph.vertex_pin(vid);

    const Transition tr = graph.vertex_transition(vid);
    Required req = (clock_period > 0.0f) ? Required{clock_period} : Delay::INF();

    // Check for max_delay override
    bool has_max_delay = false;
    if (sdc) {
        for (size_t i=0;i<sdc->max_delays().size();++i) {
            const auto& md=sdc->max_delays()[i];
            if (path_delay_matches(graph,*sdc,launch,md,MinMax::Max,i,pin)) {
                req = Required{md.delay+(launch?graph.path_origin(launch->key,path_delay_history_index(*sdc,MinMax::Max,i)):0.f)};
                has_max_delay = true;
                break;
            }
        }
    }

    // Explicit path delays override the clock relation and multicycle rules.
    if (!has_max_delay && sdc) {
        req = Required{output_clock_relation(sdc, domain, launch, MinMax::Max) +
            multicycle_relation_shift(graph, *sdc, launch, pin, domain, MinMax::Max)};
    }

    // Subtract output delay if defined for this pin (setup uses -max delays matching transition)
    if (sdc) {
        for (const auto& it : sdc->output_delays()) {
            if (!it.is_max) continue;  // skip -min delays for setup analysis
            if (it.clock_edge != tr) continue;  // only matching transition
            if (it.clock != domain && it.clock != UINT32_MAX) continue;
            for (auto p : it.ports) {
                if (p == pin) {
                    req.value -= it.delay;
                    break;
                }
            }
        }
    }

    // Apply setup uncertainty and clock latency (capture uses late derate)
    req.value -= get_setup_uncertainty(sdc, domain);
    {
        float latency = get_clock_latency(sdc, domain);
        // Use propagated clock arrival if available (CLK pin has been processed)
        PinId clk_pin = get_clock_pin_for_data(graph, network, liberty, pin);
        if (valid(clk_pin)) {
            uint32_t clk_vid = clk_pin.id * 2 + static_cast<int>(Transition::Rise);
            float propagated = graph.arrival(clk_vid, MinMax::Max, Transition::Rise).value;
            // A setup endpoint can expose an enable/data timing check whose
            // clock pin is not on the intended capture clock tree.  In that
            // case the generic arrival walk may pick up a reset or unrelated
            // control cone and produce a multi-cycle-scale value (for C906,
            // about 75 ns on a 1 ns clock).  Treat such values as invalid
            // propagated latency and retain the SDC latency instead; real
            // clock insertion/skew remains within one period plus a small
            // absolute margin in these mapped designs.
            const float max_reasonable_propagated =
                clock_period > 0.0f ? clock_period + 1.0f : 4.0f;
            if (propagated > 0.0f && std::isfinite(propagated) &&
                propagated <= max_reasonable_propagated) {
                latency = propagated;
            }
        }
        if (sdc) latency *= sdc->ocv_derate().late_clock;
        req.value += latency;
    }

    graph.set_required(vid, MinMax::Max, tr, req);
}

// Check if an endpoint is reachable from any register output via
// combinational logic (backward BFS through reverse edges).
static bool endpoint_has_reg_predecessor(
    const TimingGraph& graph,
    const Network& network,
    const ec::LibertyDB& liberty,
    uint32_t vid)
{
    std::vector<uint32_t> queue;
    std::vector<uint8_t> visited(graph.vertex_count(), 0);
    queue.push_back(vid);
    visited[vid] = 1;

    size_t head = 0;
    while (head < queue.size()) {
        uint32_t cur = queue[head++];
        for (uint32_t eid : graph.reverse_edges(cur)) {
            uint32_t from_vid = graph.edge_from(eid);
            if (visited[from_vid]) continue;
            visited[from_vid] = 1;
            PinId from_pin = graph.vertex_pin(from_vid);
            if (is_register_output(network, liberty, from_pin)) return true;
            queue.push_back(from_vid);
        }
    }
    return false;
}

static void init_endpoint_required_hold(
    TimingGraph& graph, uint32_t vid,
    const ResolvedConstraintSet* sdc,
    const Network& network,
    const ec::LibertyDB& liberty, const LaunchTimingLabel* launch = nullptr)
{
    PinId pin = graph.vertex_pin(vid);
    uint32_t domain = graph.vertex_clock_domain(vid);
    float clock_period = get_clock_period(sdc, domain);

    const Transition tr = graph.vertex_transition(vid);
    Required req = Delay::ZERO();

    // Check for min_delay override
    bool has_min_delay = false;
    if (sdc) {
        for (size_t i=0;i<sdc->min_delays().size();++i) {
            const auto& md=sdc->min_delays()[i];
            if (path_delay_matches(graph,*sdc,launch,md,MinMax::Min,i,pin)) {
                req = Required{md.delay+(launch?graph.path_origin(launch->key,path_delay_history_index(*sdc,MinMax::Min,i)):0.f)};
                has_min_delay = true;
                break;
            }
        }
    }

    // Hold is relative to the setup relation and its matching hold exception.
    if (!has_min_delay && sdc) {
        req = Required{output_clock_relation(sdc, domain, launch, MinMax::Min) +
            multicycle_relation_shift(graph, *sdc, launch, pin, domain, MinMax::Min)};
    }

    // Add output delay if defined for this pin (hold uses -min delays matching transition)
    if (sdc) {
        for (const auto& it : sdc->output_delays()) {
            if (it.is_max) continue;  // skip -max delays for hold analysis
            if (it.clock_edge != tr) continue;  // only matching transition
            if (it.clock != domain && it.clock != UINT32_MAX) continue;
            for (auto p : it.ports) {
                if (p == pin) {
                    req.value -= it.delay;
                    break;
                }
            }
        }
    }

    // Apply library hold constraint
    float hold_constraint = lookup_hold_constraint(
        graph, network, liberty, vid);
    req.value += hold_constraint;

    // Apply hold uncertainty and clock latency (capture uses early derate)
    req.value += get_hold_uncertainty(sdc, domain);
    {
        float latency = get_clock_latency(sdc, domain);
        // Use propagated clock arrival if available
        PinId clk_pin = get_clock_pin_for_data(graph, network, liberty, pin);
        if (valid(clk_pin)) {
            uint32_t clk_vid = clk_pin.id * 2 + static_cast<int>(Transition::Rise);
            float propagated = graph.arrival(clk_vid, MinMax::Min, Transition::Rise).value;
            if (propagated > 0.0f && std::isfinite(propagated)) {
                latency = propagated;
            }
        }
        if (sdc) latency *= sdc->ocv_derate().early_clock;
        req.value += latency;
    }

    graph.set_required(vid, MinMax::Min, tr, req);
}

// ────────────────────────────────────────────────────────────
// Vertex required computation
// ────────────────────────────────────────────────────────────

static float compute_vertex_required_setup(TimingGraph& graph,
                                           const ResolvedConstraintSet* sdc,
                                           uint32_t vid) {
    Transition rf = graph.vertex_transition(vid);
    float arr = graph.arrival(vid, MinMax::Max, rf).value;
    Required req = graph.required(vid, MinMax::Max, rf);

    // Iterate over forward edges (fanouts)
    for (uint32_t eid : graph.forward_edges(vid)) {
        uint32_t to_vid = graph.edge_to(eid);
        if (timing_exception_cuts_edge(graph, sdc, vid, to_vid)) continue;
        Transition to_rf = graph.vertex_transition(to_vid);

        // Use the stored edge delay from arrival propagation when available
        // (gate arcs).  For net edges (arc_idx == UINT32_MAX), compute from
        // arrival difference.
        float edge_delay = graph.edge_propagated_delay(eid, MinMax::Max);
        if (graph.edge_delay_source(eid, MinMax::Max) == DelayModelSource::None) {
            // Fallback: compute from arrival difference
            float to_arr = graph.arrival(to_vid, MinMax::Max, to_rf).value;
            if (to_arr > arr && std::isfinite(to_arr) && std::isfinite(arr)) {
                edge_delay = to_arr - arr;
            }
        }

        Required to_req = graph.required(to_vid, MinMax::Max, to_rf);
        float candidate = to_req.value - edge_delay;
        if (candidate < req.value) {
            req.value = candidate;
        }
    }

    if (std::isfinite(req.value)) {
        graph.set_required(vid, MinMax::Max, rf, req);
    }
    return req.value;
}

static float compute_vertex_required_hold(TimingGraph& graph,
                                          const ResolvedConstraintSet* sdc,
                                          uint32_t vid) {
    Transition rf = graph.vertex_transition(vid);
    float arr = graph.arrival(vid, MinMax::Min, rf).value;
    Required req = graph.required(vid, MinMax::Min, rf);

    // Iterate over forward edges (fanouts)
    for (uint32_t eid : graph.forward_edges(vid)) {
        uint32_t to_vid = graph.edge_to(eid);
        if (timing_exception_cuts_edge(graph, sdc, vid, to_vid)) continue;
        Transition to_rf = graph.vertex_transition(to_vid);
        float to_arr = graph.arrival(to_vid, MinMax::Min, to_rf).value;

        // At a merge, the earliest arrival need not come from this edge.
        // Use its own early delay, including negative delays and OCV/AOCV.
        float edge_delay = graph.edge_propagated_delay(eid, MinMax::Min);
        if (graph.edge_delay_source(eid, MinMax::Min) == DelayModelSource::None &&
            to_arr > arr && std::isfinite(to_arr) && std::isfinite(arr)) {
            edge_delay = to_arr - arr;
        }

        Required to_req = graph.required(to_vid, MinMax::Min, to_rf);
        float candidate = to_req.value - edge_delay;
        // For hold: use MAX over fanouts (most restrictive = largest required)
        if (candidate > req.value) {
            req.value = candidate;
        }
    }

    if (std::isfinite(req.value)) {
        graph.set_required(vid, MinMax::Min, rf, req);
    }
    return req.value;
}

// ────────────────────────────────────────────────────────────
// Constraint lookups
// ────────────────────────────────────────────────────────────

static float lookup_setup_constraint(
    const TimingGraph& graph,
    const Network& network,
    const ec::LibertyDB& liberty,
    uint32_t vid)
{
    PinId pin = graph.vertex_pin(vid);
    const auto& pin_data = network.pin(pin);
    if (!valid(pin_data.instance)) return 0.0f;

    const auto& inst_data = network.instance(pin_data.instance);
    const auto& cell_data = network.cell(inst_data.cell);
    if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) return 0.0f;

    const auto& lib_cell = liberty.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));

    Transition data_rf = graph.vertex_transition(vid);
    const uint32_t data_vid =
        pin.id * 2 + static_cast<uint32_t>(data_rf);
    const float data_slew =
        graph.slew(data_vid, MinMax::Max, data_rf).value;

    // Multiple conditional setup arcs can target the same pin (for example,
    // an enable check conditioned on D and !D). Without case-state proof the
    // strictest matching constraint is the safe STA result.
    float result = -std::numeric_limits<float>::infinity();
    for (const auto& arc : lib_cell.arcs) {
        if ((arc.type != ec::LibertyTimingType::SetupRising &&
             arc.type != ec::LibertyTimingType::SetupFalling) ||
            arc.to_pin != pin_data.name) {
            continue;
        }
        PinId clk_pin = NULL_PIN;
        for (auto pid : inst_data.pins) {
            if (network.pin(pid).name == arc.from_pin) {
                clk_pin = pid;
                break;
            }
        }
        if (!valid(clk_pin)) continue;
        const Transition clock_rf =
            arc.type == ec::LibertyTimingType::SetupFalling
                ? Transition::Fall
                : Transition::Rise;
        const uint32_t clock_vid =
            clk_pin.id * 2 + static_cast<uint32_t>(clock_rf);
        const float clock_slew =
            graph.slew(clock_vid, MinMax::Max, clock_rf).value;
        const auto& table = data_rf == Transition::Rise
            ? arc.rise_constraint
            : arc.fall_constraint;
        if (table.rows == 0 || table.cols == 0) continue;
        result = std::max(
            result,
            liberty::constraint_ns(table, clock_slew, data_slew,
                liberty::time_unit_ns(liberty.library(cell_data.liberty_library.id))));
    }
    return std::isfinite(result) ? result : 0.0f;
}

static float lookup_hold_constraint(
    const TimingGraph& graph,
    const Network& network,
    const ec::LibertyDB& liberty,
    uint32_t vid)
{
    PinId pin = graph.vertex_pin(vid);
    const auto& pin_data = network.pin(pin);
    if (!valid(pin_data.instance)) return 0.0f;

    const auto& inst_data = network.instance(pin_data.instance);
    const auto& cell_data = network.cell(inst_data.cell);
    if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) return 0.0f;

    const auto& lib_cell = liberty.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));

    Transition data_rf = graph.vertex_transition(vid);
    const uint32_t data_vid =
        pin.id * 2 + static_cast<uint32_t>(data_rf);
    const float data_slew =
        graph.slew(data_vid, MinMax::Max, data_rf).value;

    float result = -std::numeric_limits<float>::infinity();
    for (const auto& arc : lib_cell.arcs) {
        if ((arc.type != ec::LibertyTimingType::HoldRising &&
             arc.type != ec::LibertyTimingType::HoldFalling) ||
            arc.to_pin != pin_data.name) {
            continue;
        }
        PinId clk_pin = NULL_PIN;
        for (auto pid : inst_data.pins) {
            if (network.pin(pid).name == arc.from_pin) {
                clk_pin = pid;
                break;
            }
        }
        if (!valid(clk_pin)) continue;
        const Transition clock_rf =
            arc.type == ec::LibertyTimingType::HoldFalling
                ? Transition::Fall
                : Transition::Rise;
        const uint32_t clock_vid =
            clk_pin.id * 2 + static_cast<uint32_t>(clock_rf);
        const float clock_slew =
            graph.slew(clock_vid, MinMax::Min, clock_rf).value;
        const auto& table = data_rf == Transition::Rise
            ? arc.rise_constraint
            : arc.fall_constraint;
        if (table.rows == 0 || table.cols == 0) continue;
        result = std::max(
            result,
            liberty::constraint_ns(table, clock_slew, data_slew,
                liberty::time_unit_ns(liberty.library(cell_data.liberty_library.id))));
    }
    return std::isfinite(result) ? result : 0.0f;
}

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────

void RequiredPropagator::propagate_launch_labels() {
    uint32_t route_id = 0;
    auto distinguish = [&](LaunchTimingLabel& label) {
        if (!exhaustive_) return;
        if (route_id >= path_limit_ || route_id == UINT32_MAX)
            throw std::runtime_error("Exhaustive PBA path-label budget exceeded; no partial result returned");
        label.key = graph_.unique_path_key(label.key, ++route_id);
    };
    const char* history_setting = std::getenv("FSYN_TIMING_PATH_CONDITIONS");
    const bool track_history = history_setting && (*history_setting == '1' ||
        *history_setting == 'y' || *history_setting == 'Y' ||
        *history_setting == 't' || *history_setting == 'T');
    const auto empty_required = [](MinMax mm) {
        return mm == MinMax::Max ? Delay::INF().value : Delay::NEG_INF().value;
    };
    const auto label_edge = [&](uint32_t eid, MinMax mm, const LaunchTimingLabel& previous) {
        ArrivalPropagator::LabelEdgeResult result;
        result.delay = graph_.edge_propagated_delay(eid, mm);
        result.slew = graph_.edge_output_slew(eid, mm);
        result.wire_source_slew = previous.wire_source_slew;
        result.waveform_context = previous.waveform_context;
        // Clock and exception labels select checks in ordinary GBA; they do
        // not select a new driver waveform. Recharacterizing them with the
        // arrival-winning route's slew discards the graph's worst slew at a
        // reconvergence, making GBA depend on whether a second clock exists.
        // Only explicit exhaustive PBA uses route-specific operating points.
        if (arrival_ && exhaustive_) result = arrival_->characterize_label_edge(eid, mm,
            previous.slew, previous.wire_source_slew, previous.waveform_context,
            previous.path_depth + (graph_.edge_arc(eid) != UINT32_MAX));
        const auto from = graph_.edge_from(eid), to = graph_.edge_to(eid);
        // Ideal clock nets can assign an absolute waveform/latency arrival
        // instead of adding physical wire delay. Preserve that offset for
        // a clock source that also launches a data route.
        if (graph_.edge_arc(eid) == UINT32_MAX &&
            graph_.vertex_clock_domain(from) != UINT32_MAX &&
            graph_.vertex_clock_domain(from) == graph_.vertex_clock_domain(to)) {
            const float a = graph_.arrival(from, mm, graph_.vertex_transition(from)).value;
            const float b = graph_.arrival(to, mm, graph_.vertex_transition(to)).value;
            if (std::isfinite(a) && std::isfinite(b)) result.delay = b-a;
        }
        return result;
    };
    // Rebuild even for an incremental update: an ECO can change a launch cone,
    // an exception, or the related capture clock without dirtying a data edge.
    for (auto mm : {MinMax::Min, MinMax::Max}) {
        for (int level = 0; level <= graph_.max_level(); ++level) {
            for (const auto vid : graph_.vertices_at_level(level)) {
                auto& labels = graph_.launch_labels(vid, mm);
                const auto rf = graph_.vertex_transition(vid);
                if (graph_.is_startpoint(vid) || graph_.reverse_edges(vid).empty()) {
                    LaunchTimingLabel seed;
                    seed.domain = graph_.vertex_clock_domain(vid);
                    seed.start = vid;
                    seed.phase = check_launch_phase(graph_, network_, liberty_, sdc_, vid, mm)
                        .value_or(std::numeric_limits<float>::quiet_NaN());
                    const bool reg = is_register_output(network_, liberty_, graph_.vertex_pin(vid));
                    bool falling = false;
                    if (seed.domain < sdc_->clocks().size()) {
                        const auto& clock = sdc_->clocks()[seed.domain];
                        const float rise = clock.rise_time >= 0 ? clock.rise_time : 0.f;
                        falling = seed.phase != rise;
                    }
                    seed.key = (uint64_t(seed.domain)<<2) | (uint64_t(falling)<<1) | reg;
                    seed.key = advance_false_path_history(graph_, sdc_, seed.key, graph_.vertex_pin(vid), rf, true);
                    seed.arrival = graph_.arrival(vid, mm, rf).value;
                    seed.slew = graph_.slew(vid, mm, rf).value;
                    seed.wire_source_slew = seed.slew;
                    if (arrival_ && exhaustive_) seed.waveform_context = arrival_->seed_label_waveform(vid,mm);
                    seed.key=graph_.record_path_origins(seed.key,graph_.vertex_pin(vid),seed.arrival,true);
                    seed.required = empty_required(mm);
                    // A port can launch independent paths relative to several
                    // virtual clocks. Do not collapse their delays to the
                    // single domain stored on the graph vertex.
                    std::map<uint32_t, float> input_references;
                    if (!reg) for (const auto& d : sdc_->input_delays()) {
                        if (d.clock_edge != rf || d.is_max != (mm == MinMax::Max) ||
                            !pin_in_list(graph_.vertex_pin(vid), d.ports)) continue;
                        auto [it, fresh] = input_references.emplace(d.clock, d.delay);
                        if (!fresh) it->second = mm == MinMax::Max ? std::max(it->second,d.delay) : std::min(it->second,d.delay);
                    }
                    if (input_references.empty()) { distinguish(seed); labels.push_back(seed); }
                    else for (const auto& [domain, delay] : input_references) {
                        auto port_seed = seed;
                        port_seed.domain = domain; port_seed.arrival = delay;
                        port_seed.phase = domain < sdc_->clocks().size()
                            ? std::max(0.f,sdc_->clocks()[domain].rise_time) : std::numeric_limits<float>::quiet_NaN();
                        // Input delay is relative to this reference edge. Keep
                        // the same physical arrival used by forward propagation,
                        // including independent labels for virtual clocks.
                        if (std::isfinite(port_seed.phase)) port_seed.arrival += port_seed.phase;
                        port_seed.key = advance_false_path_history(graph_,sdc_,uint64_t(domain)<<2,
                            graph_.vertex_pin(vid),rf,true);
                        port_seed.key=graph_.record_path_origins(port_seed.key,graph_.vertex_pin(vid),port_seed.arrival,true);
                        distinguish(port_seed); labels.push_back(port_seed);
                    }
                    continue;
                }
                for (const auto eid : graph_.reverse_edges(vid)) {
                    const auto from = graph_.edge_from(eid);
                    if (timing_exception_cuts_edge(graph_, sdc_, from, vid)) continue;
                    if (graph_.vertex_level(from) >= graph_.vertex_level(vid)) {
                        if (exhaustive_) throw std::runtime_error("Exhaustive PBA requires an acyclic timed graph");
                        LaunchTimingLabel unknown;
                        unknown.key = uint64_t(UINT32_MAX)<<2;
                        unknown.arrival = std::numeric_limits<float>::quiet_NaN();
                        unknown.required = empty_required(mm);
                        labels.push_back(unknown);
                        continue;
                    }
                    for (const auto& previous : graph_.launch_labels(from, mm)) {
                        auto candidate = previous;
                        if (exhaustive_) {
                            bool consistent = true;
                            for (const auto literal : graph_.edge_conditions(eid)) {
                                const auto found = std::find_if(candidate.path_conditions.begin(), candidate.path_conditions.end(),
                                    [&](const auto& old) { return old.first == literal.net; });
                                if (found != candidate.path_conditions.end() && found->second != literal.value) { consistent = false; break; }
                                if (found == candidate.path_conditions.end()) candidate.path_conditions.push_back({literal.net, literal.value});
                            }
                            if (!consistent) continue;
                        }
                        candidate.key = advance_false_path_history(graph_, sdc_, previous.key, graph_.vertex_pin(vid), rf);
                        candidate.predecessor_key = previous.key;
                        const auto edge = label_edge(eid, mm, previous);
                        candidate.arrival += edge.delay;
                        candidate.key=graph_.record_path_origins(candidate.key,graph_.vertex_pin(vid),candidate.arrival,false);
                        candidate.path_depth += graph_.edge_arc(eid) != UINT32_MAX;
                        distinguish(candidate);
                        candidate.slew = edge.slew;
                        candidate.wire_source_slew = edge.wire_source_slew;
                        candidate.waveform_context = edge.waveform_context;
                        candidate.predecessor = from;
                        candidate.required = empty_required(mm);
                        candidate.kind = TimingCheckKind::None;
                        candidate.unresolved_history |= !exhaustive_ && track_history && !graph_.edge_conditions(eid).empty();
                        if (graph_.edge_delay_source(eid, mm) == DelayModelSource::None)
                            candidate.arrival = std::numeric_limits<float>::quiet_NaN();
                        auto existing = std::find_if(labels.begin(), labels.end(), [&](const auto& label) {
                            return label.key == candidate.key;
                        });
                        if (existing == labels.end()) labels.push_back(candidate);
                        else {
                            const bool unresolved = existing->unresolved_history || candidate.unresolved_history;
                            if (!std::isfinite(existing->arrival) || !std::isfinite(candidate.arrival)) {
                                // A missing characterization on any retained route must
                                // remain visible, including when another route is finite.
                                existing->arrival = std::numeric_limits<float>::quiet_NaN();
                            } else if ((mm == MinMax::Max && candidate.arrival > existing->arrival) ||
                                       (mm == MinMax::Min && candidate.arrival < existing->arrival)) *existing = candidate;
                            existing->unresolved_history = unresolved;
                        }
                    }
                }
            }
        }

        for (uint32_t vid = 0; vid < graph_.vertex_count(); ++vid) {
            if (!graph_.is_endpoint(vid)) continue;
            auto& labels = graph_.launch_labels(vid, mm);
            const auto rf = graph_.vertex_transition(vid);
            const auto coverage_begin = graph_.check_coverage().size();
            // An empty cone still needs its Liberty/structural coverage audit.
            if (labels.empty()) {
                if (!initialize_liberty_check_required(graph_, network_, liberty_, sdc_, vid, mm) &&
                    !initialize_output_check_exclusion(graph_, sdc_, vid, mm) &&
                    graph_.vertex_clock_domain(vid) != UINT32_MAX) {
                    graph_.add_check_coverage({graph_.vertex_pin(vid), UINT32_MAX, rf, mm,
                        TimingCheckKind::OutputDelay, CheckCoverageState::MissingArrival});
                    record_output_check_result(graph_, vid, mm, CheckCoverageState::MissingArrival);
                }
                continue;
            }
            for (auto& label : labels) {
                graph_.set_required(vid, mm, rf, Required{empty_required(mm)});
                graph_.set_endpoint_check_kind(vid, mm, TimingCheckKind::None);
                if (graph_.is_path_only_endpoint(vid)) {
                    label.required=empty_required(mm);label.kind=TimingCheckKind::None;
                    auto evaluate=[&](const auto& delays) {
                        for(size_t i=0;i<delays.size();++i) {
                            const auto& delay=delays[i];
                            if(!path_delay_matches(graph_,*sdc_,&label,delay,mm,i,graph_.vertex_pin(vid)))continue;
                            TimingCheckResult check;
                            auto state=false_path_excludes_launch(graph_,sdc_,vid,mm,label)
                                ?CheckCoverageState::ExcludedFalsePath:CheckCoverageState::Evaluated;
                            if(state==CheckCoverageState::Evaluated && !std::isfinite(label.arrival))state=CheckCoverageState::MissingArrival;
                            check.coverage={graph_.vertex_pin(vid),UINT32_MAX,rf,mm,TimingCheckKind::OutputDelay,state};
                            check.identity="path_delay:"+std::to_string(unsigned(mm))+":"+std::to_string(i);
                            check.capture_domain=label.domain;check.capture_transition=rf;
                            check.launch_key=label.key;check.launch_identity=graph_.launch_identity(label.key);
                            if(state==CheckCoverageState::Evaluated) {
                                check.arrival=label.arrival;
                                check.required=delay.delay+graph_.path_origin(label.key,path_delay_history_index(*sdc_,mm,i));
                                check.slack=mm==MinMax::Max?check.required-check.arrival:check.arrival-check.required;
                                if((mm==MinMax::Max && check.required<label.required) ||
                                    (mm==MinMax::Min && check.required>label.required)) {
                                    label.required=check.required;label.kind=TimingCheckKind::OutputDelay;label.capture=label.domain;
                                }
                            }
                            graph_.add_check_coverage(check.coverage);graph_.add_check_result(std::move(check));
                        }
                    };
                    if(mm==MinMax::Max)evaluate(sdc_->max_delays());else evaluate(sdc_->min_delays());
                    graph_.set_required(vid,mm,rf,Required{label.required});
                    graph_.set_endpoint_check_kind(vid,mm,label.kind);
                    continue;
                }
                if (!initialize_liberty_check_required(graph_, network_, liberty_, sdc_, vid, mm, &label)) {
                    const auto original_domain = graph_.vertex_clock_domain(vid);
                    std::vector<uint32_t> captures;
                    for (const auto& d : sdc_->output_delays()) {
                        if (d.clock_edge == rf && d.is_max == (mm == MinMax::Max) &&
                            pin_in_list(graph_.vertex_pin(vid),d.ports) &&
                            std::find(captures.begin(),captures.end(),d.clock)==captures.end()) captures.push_back(d.clock);
                    }
                    if (captures.empty()) captures.push_back(original_domain);
                    float output_required = empty_required(mm);
                    uint32_t worst_capture = UINT32_MAX;
                    for (const auto capture : captures) {
                        graph_.set_vertex_clock_domain(vid,capture);
                        graph_.set_required(vid,mm,rf,Required{empty_required(mm)});
                        bool explicit_delay=false;
                        auto matches_delay=[&](const auto& delays) {
                            for(size_t i=0;i<delays.size();++i)explicit_delay|=path_delay_matches(graph_,*sdc_,&label,delays[i],mm,i,graph_.vertex_pin(vid));
                        };
                        if(mm==MinMax::Max)matches_delay(sdc_->max_delays());else matches_delay(sdc_->min_delays());
                        if (initialize_output_check_exclusion(graph_,sdc_,vid,mm,&label) || (capture==UINT32_MAX && !explicit_delay)) continue;
                        if (!std::isfinite(label.arrival)) {
                            graph_.add_check_coverage({graph_.vertex_pin(vid), UINT32_MAX, rf, mm,
                                TimingCheckKind::OutputDelay, CheckCoverageState::MissingArrival});
                            record_output_check_result(graph_,vid,mm,CheckCoverageState::MissingArrival,&label);
                            continue;
                        }
                        if (mm==MinMax::Max) init_endpoint_required_setup(graph_,vid,sdc_,network_,liberty_,&label);
                        else init_endpoint_required_hold(graph_,vid,sdc_,network_,liberty_,&label);
                        label.capture=capture;
                        record_output_check_result(graph_,vid,mm,CheckCoverageState::Evaluated,&label);
                        const float candidate=graph_.required(vid,mm,rf).value;
                        if ((mm==MinMax::Max && candidate<output_required) ||
                            (mm==MinMax::Min && candidate>output_required)) {
                            output_required=candidate;worst_capture=capture;
                        }
                    }
                    graph_.set_vertex_clock_domain(vid,original_domain);
                    graph_.set_required(vid,mm,rf,Required{output_required});
                    graph_.set_endpoint_check_kind(vid,mm,worst_capture==UINT32_MAX?TimingCheckKind::None:TimingCheckKind::OutputDelay);
                    label.capture=worst_capture;
                }
                label.required = graph_.required(vid, mm, rf).value;
                label.kind = graph_.endpoint_check_kind(vid, mm);
            }
            graph_.merge_launch_check_coverage(coverage_begin);
        }

        // Carry each capture requirement only along routes with the same
        // launch label. Sequential Q is a new launch, so do not cross CP->Q.
        for (int level = graph_.max_level(); level >= 0; --level) {
            for (const auto vid : graph_.vertices_at_level(level)) {
                for (auto& label : graph_.launch_labels(vid, mm)) {
                    for (const auto eid : graph_.forward_edges(vid)) {
                        const auto to = graph_.edge_to(eid);
                        if (graph_.is_startpoint(to) || graph_.vertex_level(to) <= level ||
                            timing_exception_cuts_edge(graph_, sdc_, vid, to)) continue;
                        if (exhaustive_) {
                            for (const auto& target : graph_.launch_labels(to, mm)) {
                                if (target.predecessor != vid || target.predecessor_key != label.key ||
                                    !std::isfinite(target.required)) continue;
                                const float candidate = target.required - (target.arrival-label.arrival);
                                if ((mm == MinMax::Max && candidate < label.required) ||
                                    (mm == MinMax::Min && candidate > label.required)) label.required = candidate;
                            }
                            continue;
                        }
                        const auto edge=label_edge(eid,mm,label);
                        auto target_key = advance_false_path_history(graph_, sdc_, label.key, graph_.vertex_pin(to), graph_.vertex_transition(to));
                        target_key=graph_.record_path_origins(target_key,graph_.vertex_pin(to),label.arrival+edge.delay,false);
                        const auto* target = graph_.launch_label(to, mm, target_key);
                        if (!target || !std::isfinite(target->required)) continue;
                        const float candidate = target->required-edge.delay;
                        if ((mm == MinMax::Max && candidate < label.required) ||
                            (mm == MinMax::Min && candidate > label.required)) label.required = candidate;
                    }
                }
            }
        }
        // Publish the worst valid per-launch slack into the scalar SOA used
        // by the DesignDB bridge, criticality and existing sizing callers.
        // Reports retain the physical tagged arrival and required values.
        for (uint32_t vid = 0; vid < graph_.vertex_count(); ++vid) {
            const auto rf = graph_.vertex_transition(vid);
            const auto* worst = graph_.worst_launch_label(vid, mm);
            float required = empty_required(mm);
            if (worst) {
                const float slack = mm == MinMax::Max ? worst->required-worst->arrival : worst->arrival-worst->required;
                const float arrival = graph_.arrival(vid, mm, rf).value;
                required = arrival + (mm == MinMax::Max ? slack : -slack);
            }
            graph_.set_required(vid, mm, rf, Required{required});
            if (graph_.is_endpoint(vid)) graph_.set_endpoint_check_kind(vid, mm,
                worst ? worst->kind : TimingCheckKind::None);
        }
    }
}

void RequiredPropagator::propagate_all() {
    graph_.clear_check_coverage();
    graph_.reset_launch_labels(sdc_ && (exhaustive_ || sdc_->clocks().size() > 1 ||
        !sdc_->clock_groups().empty() || !sdc_->false_paths().empty() ||
        !sdc_->max_delays().empty() || !sdc_->min_delays().empty() || !sdc_->multicycle_paths().empty() || !sdc_->data_checks().empty()));
    graph_.prepare_false_path_history(sdc_);
    // Clear previous requirements so a removed/relaxed check cannot survive a
    // full update. Min fanout reduction starts at negative infinity.
    for (uint32_t vid = 0; vid < graph_.vertex_count(); ++vid) {
        for (auto mm : {MinMax::Min, MinMax::Max}) {
            graph_.set_required(vid, mm, graph_.vertex_transition(vid),
                mm == MinMax::Max ? Delay::INF() : Delay::NEG_INF());
            graph_.set_endpoint_check_kind(vid, mm, TimingCheckKind::None);
        }
    }
    if (graph_.has_launch_labels()) {
        propagate_launch_labels();
        apply_sdc_data_checks(graph_,network_,*sdc_,path_limit_);
        return;
    }
    // --- Setup (Max) propagation ---
    // Initialize endpoints
    for (uint32_t vid = 0; vid < graph_.vertex_count(); ++vid) {
        if (graph_.is_endpoint(vid)) {
            if (initialize_liberty_check_required(graph_, network_, liberty_, sdc_, vid, MinMax::Max)) continue;
            if (initialize_output_check_exclusion(graph_, sdc_, vid, MinMax::Max)) continue;
            if (graph_.vertex_clock_domain(vid) == UINT32_MAX) continue;
            init_endpoint_required_setup(graph_, vid, sdc_, network_, liberty_);
            graph_.set_endpoint_check_kind(vid, MinMax::Max, TimingCheckKind::OutputDelay);

            // For register D inputs, subtract setup time
            if (!graph_.is_startpoint(vid)) {
                float setup = lookup_setup_constraint(graph_, network_, liberty_, vid);
                if (setup > 0.0f) {
                    const Transition rf = graph_.vertex_transition(vid);
                    auto r = graph_.required(vid, MinMax::Max, rf);
                    r.value -= setup;
                    graph_.set_required(vid, MinMax::Max, rf, r);
                }
            }
            record_output_check_result(graph_, vid, MinMax::Max, CheckCoverageState::Evaluated);
        }
    }

    // Process vertices in reverse topological order, level by level
    for (int level = graph_.max_level(); level >= 0; --level) {
        auto verts = graph_.vertices_at_level(level);
        parallel_for(0, verts.size(), [&](size_t i) {
            compute_vertex_required_setup(graph_, sdc_, verts[i]);
        });
    }

    // --- Hold (Min) propagation ---
    // Initialize endpoints
    for (uint32_t vid = 0; vid < graph_.vertex_count(); ++vid) {
        if (graph_.is_endpoint(vid)) {
            if (initialize_liberty_check_required(graph_, network_, liberty_, sdc_, vid, MinMax::Min)) continue;
            if (initialize_output_check_exclusion(graph_, sdc_, vid, MinMax::Min)) continue;
            if (graph_.vertex_clock_domain(vid) == UINT32_MAX) continue;
            init_endpoint_required_hold(graph_, vid, sdc_, network_, liberty_);
            graph_.set_endpoint_check_kind(vid, MinMax::Min, TimingCheckKind::OutputDelay);
            record_output_check_result(graph_, vid, MinMax::Min, CheckCoverageState::Evaluated);

            // Hold constraint is already added in init_endpoint_required_hold
        }
    }

    // Process vertices in reverse topological order for hold
    for (int level = graph_.max_level(); level >= 0; --level) {
        auto verts = graph_.vertices_at_level(level);
        parallel_for(0, verts.size(), [&](size_t i) {
            compute_vertex_required_hold(graph_, sdc_, verts[i]);
        });
    }
}

void RequiredPropagator::propagate_dirty() {
    // Related-clock arrival/slew affects checks without a data edge. Fresh
    // requirements also permit relaxed or removed checks after an ECO.
    propagate_all();
}

} // namespace te
