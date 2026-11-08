#pragma once

#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <unordered_set>
#include "graph/timing_graph.hh"
#include "network/network.hh"
#include "liberty/core_liberty_utils.hh"
#include "sdc/resolved_constraints.hh"
#include "timing_exceptions.hh"
#include "clock_pessimism.hh"

namespace te {

// Return the worst capture relation across a repeating pair of waveforms,
// expressed as an offset from the capture phase. One launch edge at t=0
// is insufficient when a generated period spans several master cycles.
// Bound the common-cycle search; an unresolved relation must not pass STA.
inline std::optional<float> generated_capture_relation(float launch_period,
    float capture_period, float launch_phase, float capture_phase, MinMax mm) {
    const double lp = launch_period, cp = capture_period;
    if (!(lp > 0 && cp > 0) || !std::isfinite(lp) || !std::isfinite(cp) ||
        !std::isfinite(launch_phase) || !std::isfinite(capture_phase)) return std::nullopt;
    const double tolerance = 8.0 * std::numeric_limits<float>::epsilon() * std::max(lp, cp);
    unsigned cycles = 0;
    for (unsigned i = 1; i <= 4096; ++i) {
        const double captures = std::round(i * lp / cp);
        if (captures >= 1 && captures <= 4096 &&
            std::fabs(i * lp - captures * cp) <= tolerance*std::max(double(i),captures)) {
            cycles = i; break;
        }
    }
    if (!cycles) return std::nullopt;
    double gap = mm == MinMax::Max ? std::numeric_limits<double>::infinity()
                                   : -std::numeric_limits<double>::infinity();
    for (unsigned i = 0; i < cycles; ++i) {
        double phase = std::fmod(double(launch_phase) + i * lp - capture_phase, cp);
        if (phase < 0) phase += cp;
        if (phase <= tolerance || cp - phase <= tolerance) phase = 0;
        if (mm == MinMax::Max) gap = std::min(gap, cp - phase);
        else gap = std::max(gap, -phase);
    }
    const double relation = double(launch_phase) + gap - capture_phase;
    if (!std::isfinite(relation) || std::fabs(relation) > std::numeric_limits<float>::max()) return std::nullopt;
    return static_cast<float>(relation);
}

// Exclude a whole check only when every structural launch route is covered.
// A false path on one branch must not erase checks on another branch. Through
// exceptions need path history and are deliberately not proven here.
inline bool check_fully_false_pathed(const TimingGraph& graph,
    const ResolvedConstraintSet* sdc, uint32_t endpoint, MinMax mm) {
    if (!sdc || sdc->false_paths().empty()) return false;
    std::unordered_set<uint32_t> cuts;
    for (const auto& fp : sdc->false_paths()) {
        // Clock predicates are evaluated per launch/capture label below.
        if (!fp.from_clocks.empty() || !fp.to_clocks.empty()) continue;
        if (!false_path_applies_to_analysis(fp, mm) || !fp.through_pins.empty()) continue;
        if (!fp.to_pins.empty() &&
            !timing_exception_pin_in_list(graph.vertex_pin(endpoint), fp.to_pins)) continue;
        if (fp.from_pins.empty()) {
            if (!fp.to_pins.empty()) return true;
        } else for (const auto pin : fp.from_pins) cuts.insert(pin.id);
    }
    if (cuts.empty()) return false;
    std::vector<uint32_t> pending{endpoint};
    std::unordered_set<uint32_t> seen;
    bool reached_cut = false;
    while (!pending.empty()) {
        const auto vid = pending.back(); pending.pop_back();
        if (!seen.insert(vid).second) continue;
        if (cuts.count(graph.vertex_pin(vid).id)) { reached_cut = true; continue; }
        const auto edges = graph.reverse_edges(vid);
        if (graph.is_startpoint(vid) || edges.empty()) return false;
        for (const auto edge : edges) {
            const auto from = graph.edge_from(edge);
            // Unresolved loops cannot establish a complete launch-route proof.
            if (graph.vertex_level(from) >= graph.vertex_level(vid)) return false;
            pending.push_back(from);
        }
    }
    return reached_cut;
}

// Clock domains on intermediate vertices are lossy at reconvergence. Prove
// exclusion from all structural launch points, never from that single domain.
// Cache per capture clock across endpoints, transitions and min/max. Iterative
// traversal avoids stack overflow on deep logic cones; loops fail closed.
inline CheckCoverageState clock_group_check_coverage(TimingGraph& graph,
    const ResolvedConstraintSet* sdc, uint32_t endpoint, uint32_t capture,
    const LaunchTimingLabel* launch = nullptr) {
    if (!sdc) return CheckCoverageState::Evaluated;
    if (sdc->clock_groups().empty()) return launch && launch->unresolved_history
        ? CheckCoverageState::UnsupportedMixedClockPaths : CheckCoverageState::Evaluated;
    if (capture >= sdc->clocks().size()) return CheckCoverageState::MissingCaptureClock;
    if (launch) {
        if (launch->domain >= sdc->clocks().size()) return CheckCoverageState::MissingLaunchClock;
        if (edacraft::core::resolved_clock_groups_cut_path(sdc->clock_groups(), launch->domain, capture))
            return CheckCoverageState::ExcludedClockGroup;
        return launch->unresolved_history ? CheckCoverageState::UnsupportedMixedClockPaths : CheckCoverageState::Evaluated;
    }
    constexpr uint8_t kept = 1, cut = 2, unknown = 4;
    std::vector<std::pair<uint32_t, bool>> pending{{endpoint, false}};
    while (!pending.empty()) {
        const auto [vid, expanded] = pending.back(); pending.pop_back();
        if (graph.clock_route_coverage(vid, capture)) continue;
        if (graph.is_startpoint(vid)) {
            const auto launch = graph.vertex_clock_domain(vid);
            const auto coverage = launch >= sdc->clocks().size() ? unknown :
                edacraft::core::resolved_clock_groups_cut_path(sdc->clock_groups(), launch, capture) ? cut : kept;
            graph.set_clock_route_coverage(vid, capture, coverage); continue;
        }
        const auto edges = graph.reverse_edges(vid);
        if (edges.empty()) { graph.set_clock_route_coverage(vid, capture, unknown); continue; }
        if (!expanded) {
            pending.push_back({vid, true});
            for (const auto edge : edges) {
                const auto from = graph.edge_from(edge);
                if (graph.vertex_level(from) < graph.vertex_level(vid) &&
                    !graph.clock_route_coverage(from, capture)) pending.push_back({from, false});
            }
        } else {
            uint8_t coverage = 0;
            for (const auto edge : edges) {
                const auto from = graph.edge_from(edge);
                coverage |= graph.vertex_level(from) >= graph.vertex_level(vid) ? unknown :
                    graph.clock_route_coverage(from, capture).value_or(unknown);
            }
            graph.set_clock_route_coverage(vid, capture, coverage);
        }
    }
    const auto coverage = graph.clock_route_coverage(endpoint, capture).value_or(unknown);
    if (coverage & unknown) return CheckCoverageState::MissingLaunchClock;
    if (coverage == cut) return CheckCoverageState::ExcludedClockGroup;
    if (coverage == (cut | kept)) return CheckCoverageState::UnsupportedMixedClockPaths;
    return CheckCoverageState::Evaluated;
}

inline void record_output_check_result(TimingGraph& graph, uint32_t vid,
    MinMax mm, CheckCoverageState state, const LaunchTimingLabel* launch = nullptr) {
    const auto rf = graph.vertex_transition(vid);
    TimingCheckResult result;
    result.coverage = {graph.vertex_pin(vid), UINT32_MAX, rf, mm, TimingCheckKind::OutputDelay, state};
    result.identity = "output_delay";
    result.capture_transition = rf;
    result.capture_domain = graph.vertex_clock_domain(vid);
    result.launch_key = launch ? launch->key : UINT64_MAX;
    if (launch) result.launch_identity = graph.launch_identity(launch->key);
    if (state == CheckCoverageState::Evaluated) {
        result.arrival = launch ? launch->arrival : graph.arrival(vid, mm, rf).value;
        result.required = graph.required(vid, mm, rf).value;
        result.slack = mm == MinMax::Max ? result.required-result.arrival : result.arrival-result.required;
        if (!std::isfinite(result.arrival) || !std::isfinite(result.required) || !std::isfinite(result.slack)) {
            result.coverage.state = !std::isfinite(result.arrival)
                ? CheckCoverageState::MissingArrival : CheckCoverageState::InvalidCheck;
            graph.add_check_coverage(result.coverage);
        }
    }
    graph.add_check_result(std::move(result));
}

inline bool initialize_output_check_exclusion(TimingGraph& graph,
    const ResolvedConstraintSet* sdc, uint32_t vid, MinMax mm,
    const LaunchTimingLabel* launch = nullptr) {
    auto state = CheckCoverageState::Evaluated;
    if (graph.is_static_constant_vertex(vid)) state = CheckCoverageState::ExcludedConstant;
    else if (launch ? false_path_excludes_launch(graph, sdc, vid, mm, *launch) :
        check_fully_false_pathed(graph, sdc, vid, mm)) state = CheckCoverageState::ExcludedFalsePath;
    else if (graph.vertex_clock_domain(vid) != UINT32_MAX)
        state = clock_group_check_coverage(graph, sdc, vid, graph.vertex_clock_domain(vid), launch);
    if (state == CheckCoverageState::Evaluated) {
        // Retain an active output check in the ledger when another launch is
        // excluded. Otherwise the excluded record alone describes this mixed
        // endpoint as fully cut despite its finite timing requirement.
        const bool mixed_false_paths = launch && sdc && !sdc->false_paths().empty() &&
            std::any_of(graph.launch_labels(vid, mm).begin(), graph.launch_labels(vid, mm).end(),
                [&](const auto& other) { return false_path_excludes_launch(graph, sdc, vid, mm, other); });
        if (launch && (mixed_false_paths || clock_group_check_coverage(graph, sdc, vid, graph.vertex_clock_domain(vid)) ==
            CheckCoverageState::UnsupportedMixedClockPaths))
            graph.add_check_coverage({graph.vertex_pin(vid), UINT32_MAX,
                graph.vertex_transition(vid), mm, TimingCheckKind::OutputDelay, state});
        return false;
    }
    graph.add_check_coverage({graph.vertex_pin(vid), UINT32_MAX,
        graph.vertex_transition(vid), mm, TimingCheckKind::OutputDelay,
        state});
    record_output_check_result(graph, vid, mm, state, launch);
    return true;
}

inline std::optional<float> check_launch_phase(const TimingGraph& graph,
    const Network& net, const edacraft::core::LibertyDB& db,
    const ResolvedConstraintSet* sdc, uint32_t vid, MinMax mm) {
    namespace ec = edacraft::core;
    for (uint32_t steps = 0; steps < graph.vertex_count(); ++steps) {
        const auto rf = graph.vertex_transition(vid);
        auto pred = mm == MinMax::Max ? graph.pred_max(vid, mm, rf) : graph.pred_min(vid, mm, rf);
        if (!graph.is_startpoint(vid) && pred != UINT32_MAX) { vid = pred; continue; }
        const auto pin_id = graph.vertex_pin(vid);
        const auto& pin = net.pin(pin_id);
        auto domain = graph.vertex_clock_domain(vid);
        auto launch_rf = Transition::Rise;
        if (valid(pin.instance)) {
            const auto& inst = net.instance(pin.instance);
            const auto& cell = net.cell(inst.cell);
            if (valid(cell.liberty_library) && valid(cell.liberty_cell)) {
                const auto& lc = db.cell(liberty::to_core(cell.liberty_library), liberty::to_core(cell.liberty_cell));
                for (const auto& a : lc.arcs) {
                    if (a.to_pin != pin.name || (a.type != ec::LibertyTimingType::RisingEdge &&
                        a.type != ec::LibertyTimingType::FallingEdge)) continue;
                    launch_rf = a.type == ec::LibertyTimingType::FallingEdge ? Transition::Fall : Transition::Rise;
                    break;
                }
            }
        }
        if (!sdc || domain >= sdc->clocks().size()) return std::nullopt;
        const auto& clock = sdc->clocks()[domain];
        if (std::find(clock.sources.begin(), clock.sources.end(), pin_id) != clock.sources.end()) launch_rf = rf;
        return launch_rf == Transition::Fall ?
            (clock.fall_time >= 0 ? clock.fall_time : clock.period*.5f) :
            (clock.rise_time >= 0 ? clock.rise_time : 0.f);
    }
    return std::nullopt;
}

// Return true for a characterized check pin, including unavailable checks.
// Absence of a table or related clock must never create a zero-time check.
inline bool initialize_liberty_check_required(
    TimingGraph& graph, const Network& network,
    const edacraft::core::LibertyDB& db,
    const ResolvedConstraintSet* sdc, uint32_t vid, MinMax mm,
    LaunchTimingLabel* launch = nullptr) {
    namespace ec = edacraft::core;
    const auto& pin = network.pin(graph.vertex_pin(vid));
    if (!valid(pin.instance)) return false;
    const auto& inst = network.instance(pin.instance);
    const auto& cell = network.cell(inst.cell);
    if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) return false;
    const auto& lc = db.cell(liberty::to_core(cell.liberty_library),
                            liberty::to_core(cell.liberty_cell));
    bool has_check = false;
    const auto rf = graph.vertex_transition(vid);
    float required = mm == MinMax::Max ? Delay::INF().value : Delay::NEG_INF().value;
    auto kind = TimingCheckKind::None;
    for (const auto& arc : lc.arcs) {
        if (arc.to_pin != pin.name || !ec::liberty_timing_type_is_check(arc.type)) continue;
        has_check = true;
        if (ec::liberty_timing_type_is_min_check(arc.type) != (mm == MinMax::Min)) continue;
        // Liberty's rising/falling timing_type suffix selects the RELATED
        // clock edge. The data/check-pin edges come from the declared
        // constraint groups. An undeclared opposite edge is not a check;
        // a declared but missing/invalid table must still fail below.
        const uint8_t edge = rf == Transition::Rise ? 1 : 2;
        if (arc.constraint_transition_mask && !(arc.constraint_transition_mask & edge)) continue;
        const auto arc_index = static_cast<uint32_t>(&arc-lc.arcs.data());
        const auto check_kind = ec::liberty_timing_type_is_async_check(arc.type)
            ? (mm == MinMax::Max ? TimingCheckKind::Recovery : TimingCheckKind::Removal)
            : (mm == MinMax::Max ? TimingCheckKind::Setup : TimingCheckKind::Hold);
        TimingCheckCoverage record{graph.vertex_pin(vid), arc_index, rf, mm, check_kind,
                                   CheckCoverageState::InvalidCheck};
        TimingCheckResult result;
        const auto related_name = std::string(network.str(arc.from_pin));
        const auto when = arc.when == UINT32_MAX ? std::string{} : std::string(network.str(arc.when));
        uint32_t ordinal = 0;
        for (uint32_t i = 0; i < arc_index; ++i) {
            const auto& previous = lc.arcs[i];
            ordinal += previous.type == arc.type && previous.to_pin == arc.to_pin &&
                previous.from_pin == arc.from_pin && previous.when == arc.when;
        }
        result.identity = std::to_string(static_cast<unsigned>(arc.type)) + ":" +
            std::to_string(related_name.size()) + ":" + related_name + ":" +
            std::to_string(when.size()) + ":" + when + ":" + std::to_string(ordinal);
        result.capture_transition = ec::liberty_timing_type_is_falling_check(arc.type)
            ? Transition::Fall : Transition::Rise;
        result.launch_key = launch ? launch->key : UINT64_MAX;
        if (launch) result.launch_identity = graph.launch_identity(launch->key);
        auto record_state = [&](CheckCoverageState state) {
            record.state = state; graph.add_check_coverage(record);
            result.coverage = record; graph.add_check_result(result);
        };
        if (graph.check_arc_disabled(pin.instance.id, arc_index)) {
            record_state(CheckCoverageState::ExcludedDisabled); continue;
        }
        // A data/check pin driven by a statically constant net has no
        // physical transition to time.  The arrival is intentionally absent
        // because graph construction disables both transitions; report that
        // as a valid exclusion instead of an MCMM coverage failure.
        if (graph.is_static_constant_vertex(vid)) {
            record_state(CheckCoverageState::ExcludedConstant); continue;
        }
        PinId related = NULL_PIN;
        for (auto p : inst.pins) if (network.pin(p).name == arc.from_pin) { related = p; break; }
        if (!valid(related)) { record_state(CheckCoverageState::MissingRelatedPin); continue; }
        const auto crf = ec::liberty_timing_type_is_falling_check(arc.type)
            ? Transition::Fall : Transition::Rise;
        const uint32_t cvid = related.id * 2 + static_cast<unsigned>(crf);
        const auto domain = graph.vertex_clock_domain(cvid);
        result.related = related;
        result.capture_domain = domain;
        const bool false_pathed = launch ? false_path_excludes_launch(graph,sdc,vid,mm,*launch,domain) :
            check_fully_false_pathed(graph,sdc,vid,mm);
        if (false_pathed) { record_state(CheckCoverageState::ExcludedFalsePath); continue; }
        if (!sdc || domain >= sdc->clocks().size()) {
            record_state(CheckCoverageState::MissingCaptureClock); continue;
        }
        const auto& clock = sdc->clocks()[domain];
        if (!(clock.period > 0.0f) || !std::isfinite(clock.period)) {
            record_state(CheckCoverageState::MissingCaptureClock); continue;
        }
        const auto clock_coverage = clock_group_check_coverage(graph, sdc, vid, domain, launch);
        if (clock_coverage != CheckCoverageState::Evaluated) { record_state(clock_coverage); continue; }
        const auto& table = rf == Transition::Rise ? arc.rise_constraint : arc.fall_constraint;
        if (!table.rows || !table.cols || table.values.size() != table.rows * table.cols) {
            record_state(CheckCoverageState::MissingTable); continue;
        }
        if (!std::isfinite(launch ? launch->arrival : graph.arrival(vid, mm, rf).value)) {
            record_state(CheckCoverageState::MissingArrival); continue;
        }
        const float cslew = graph.slew(cvid, mm, crf).value;
        const float dslew = launch ? launch->slew : graph.slew(vid, mm, rf).value;
        if (!std::isfinite(cslew) || cslew < 0 || !std::isfinite(dslew) || dslew < 0) {
            record_state(CheckCoverageState::InvalidCheck); continue;
        }
        const float check = liberty::constraint_ns(table, cslew, dslew,
            liberty::time_unit_ns(db.library(cell.liberty_library.id)));
        if (!std::isfinite(check)) { record_state(CheckCoverageState::InvalidCheck); continue; }
        // Early capture is restrictive for setup/recovery; late capture is
        // restrictive for hold/removal. Clock arrival already includes waveform,
        // source latency and OCV derate, so do not add them a second time.
        const auto capture_mode = mm == MinMax::Max ? MinMax::Min : MinMax::Max;
        float capture = graph.arrival(cvid, capture_mode, crf).value;
        if (!std::isfinite(capture)) { record_state(CheckCoverageState::MissingCaptureClock); continue; }
        auto launch_phase = launch ? std::optional<float>{launch->phase} :
            check_launch_phase(graph, network, db, sdc, vid, mm);
        if (!launch_phase || !std::isfinite(*launch_phase)) { record_state(CheckCoverageState::MissingLaunchClock); continue; }
        const float capture_phase = crf == Transition::Fall ?
            (clock.fall_time >= 0 ? clock.fall_time : clock.period*.5f) :
            (clock.rise_time >= 0 ? clock.rise_time : 0.f);
        // Choose the capture edge from launch phase, never data arrival:
        // late data must violate its original edge, not move to another cycle.
        const float cycle = std::floor((*launch_phase-capture_phase)/clock.period + 1e-6f);
        float edge_relation = (cycle + (mm == MinMax::Max ? 1.f : 0.f))*clock.period;
        // Related primary clocks with different periods need the same
        // repeating-edge search as generated clocks (e.g. C906 CPU/APB).
        if (clock.generated || (launch && launch->domain < sdc->clocks().size())) {
            const auto relation = launch && launch->domain < sdc->clocks().size()
                ? generated_capture_relation(sdc->clocks()[launch->domain].period, clock.period,
                    *launch_phase, capture_phase, mm) : std::nullopt;
            if (!relation) { record_state(CheckCoverageState::InvalidCheck); continue; }
            edge_relation = *relation;
        }
        float relation = edge_relation;
        bool override_delay = false;
        bool ignore_clock_latency = false;
        bool pin_delay_override = false;
        auto apply_delays = [&](const auto& delays) {
            for (size_t i=0;i<delays.size();++i) {
                const auto& d=delays[i];
                if (path_delay_matches(graph,*sdc,launch,d,mm,i,graph.vertex_pin(vid),domain)) {
                    relation = d.delay+(launch?graph.path_origin(launch->key,path_delay_history_index(*sdc,mm,i)):0.f);
                    ignore_clock_latency = d.ignore_clock_latency;
                    pin_delay_override = !d.from_pins.empty();
                    override_delay = true; break;
                }
            }
        };
        if (mm == MinMax::Max) apply_delays(sdc->max_delays());
        else apply_delays(sdc->min_delays());
        if (!override_delay) {
            relation = edge_relation + multicycle_relation_shift(
                graph, *sdc, launch, graph.vertex_pin(vid), domain, mm);
        }
        float uncertainty = 0.0f;
        for (const auto& u : sdc->clock_uncertainties()) if (u.clock == domain) {
            uncertainty = mm == MinMax::Max ? u.setup_uncertainty : u.hold_uncertainty; break;
        }
        uint32_t start = launch ? launch->start : vid;
        if (!launch) for (size_t i = 0; i < graph.vertex_count() && !graph.is_startpoint(start); ++i) {
            const auto srf = graph.vertex_transition(start);
            const auto pred = mm == MinMax::Max ? graph.pred_max(start, mm, srf) : graph.pred_min(start, mm, srf);
            if (pred == UINT32_MAX) break;
            start = pred;
        }
        if (override_delay && !pin_delay_override) {
            if (ignore_clock_latency) {
                // Keep the graph's absolute arrival basis, but use the same
                // launch clock latency on the required side so both clock
                // networks cancel. The data path still includes clock-to-Q.
                capture = *launch_phase;
                if (start < graph.vertex_count()) {
                    const auto& sp = network.pin(graph.vertex_pin(start));
                    const auto pred = mm==MinMax::Max ? graph.pred_max(start,mm,graph.vertex_transition(start))
                                                     : graph.pred_min(start,mm,graph.vertex_transition(start));
                    if (valid(sp.instance) && pred!=UINT32_MAX &&
                        graph.vertex_pin(pred).id==graph.instance_clk_pin(sp.instance.id))
                        capture = graph.arrival(pred,mm,graph.vertex_transition(pred)).value;
                }
            } else capture += *launch_phase-capture_phase;
        }
        result.cppr = (ignore_clock_latency || pin_delay_override) ? 0.f
            : check_clock_pessimism(graph, network, start, cvid, mm);
        const float candidate = capture + relation + (mm == MinMax::Max ? result.cppr : -result.cppr) +
            (mm == MinMax::Max ? -check - uncertainty : check + uncertainty);
        if (!std::isfinite(candidate)) { record_state(CheckCoverageState::InvalidCheck); continue; }
        result.arrival = launch ? launch->arrival : graph.arrival(vid, mm, rf).value;
        result.required = candidate;
        result.slack = mm == MinMax::Max ? candidate-result.arrival : result.arrival-candidate;
        if (!std::isfinite(result.slack)) { record_state(CheckCoverageState::InvalidCheck); continue; }
        record_state(CheckCoverageState::Evaluated);
        if ((mm == MinMax::Max && candidate < required) ||
            (mm == MinMax::Min && candidate > required)) {
            required = candidate;
            graph.set_endpoint_cppr(vid, mm, result.cppr);
            graph.set_endpoint_capture_clock(vid, mm, cvid);
            if (launch) launch->cppr = result.cppr;
            if (launch) launch->capture = domain;
            kind = ec::liberty_timing_type_is_async_check(arc.type)
                ? (mm == MinMax::Max ? TimingCheckKind::Recovery : TimingCheckKind::Removal)
                : (mm == MinMax::Max ? TimingCheckKind::Setup : TimingCheckKind::Hold);
        }
    }
    if (has_check) {
        graph.set_required(vid, mm, rf, Required{required});
        graph.set_endpoint_check_kind(vid, mm, kind);
    }
    return has_check;
}

} // namespace te
