#include <cmath>
#include <cstdlib>
#include "path_collector.hh"

#include <algorithm>
#include <iostream>
#include <limits>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "concurrent/parallel_for.hh"
#include "graph/timing_graph.hh"
#include "network/network.hh"
#include "sdc/resolved_constraints.hh"
#include "timing_exceptions.hh"

namespace te {

static bool endpoint_debug_enabled() {
    const char* value = std::getenv("FSYN_TIMING_DEBUG_ENDPOINTS");
    return value && (*value == '1' || *value == 'y' || *value == 'Y' ||
                     *value == 't' || *value == 'T');
}

static std::string resolve_path_group(const std::vector<PinId>& pins,
    const std::vector<std::string>& transitions, const Network& network,
    const ResolvedConstraintSet* sdc, uint32_t launch, uint32_t capture,
    Transition launch_edge, Transition capture_edge, PinId launch_clock_pin) {
    if (!sdc || pins.empty()) return {};
    auto contains = [](const auto& selected, auto pin) {
        return std::find(selected.begin(), selected.end(), pin) != selected.end();
    };
    std::string name;
    int best_rank = 100;
    auto transition_matches = [&](size_t i, uint8_t mask) {
        return mask & (transitions[i] == "rise" ? 1 : 2);
    };
    for (const auto& group : sdc->path_groups()) {
        if (!group.from_pins.empty() && !contains(group.from_pins, pins.front()) &&
            !contains(group.from_pins, launch_clock_pin)) continue;
        if (!group.to_pins.empty() && !contains(group.to_pins, pins.back())) continue;
        if (!group.from_clocks.empty() && !contains(group.from_clocks, launch)) continue;
        if (!group.to_clocks.empty() && !contains(group.to_clocks, capture)) continue;
        const bool from_rf = group.from_clocks.empty() ? transition_matches(0, group.from_transitions) :
            (group.from_transitions & (launch_edge == Transition::Rise ? 1 : 2));
        const bool to_rf = group.to_clocks.empty() ? transition_matches(pins.size()-1, group.to_transitions) :
            (group.to_transitions & (capture_edge == Transition::Rise ? 1 : 2));
        if (!from_rf || !to_rf) continue;
        size_t cursor = 0;
        auto through = [&](const auto& selected, uint8_t mask) {
            if (selected.empty()) return true;
            while (cursor < pins.size()) {
                const auto i = cursor++;
                if (contains(selected, pins[i]) && transition_matches(i, mask)) return true;
            }
            return false;
        };
        if (!through(group.through_pins, group.through_transitions)) continue;
        bool matched = true;
        for (size_t i = 0; i < group.through_stages.size(); ++i)
            if (!through(group.through_stages[i], i < group.through_stage_transitions.size()
                    ? group.through_stage_transitions[i] : 3)) { matched = false; break; }
        // PrimeTime precedence: pin->pin, pin->clock, pin->*, clock->pin,
        // *->pin, clock->clock, clock->*, *->clock. Equal ranks use name order.
        const bool fp = !group.from_pins.empty(), tp = !group.to_pins.empty();
        const bool fc = !group.from_clocks.empty(), tc = !group.to_clocks.empty();
        const int rank = fp ? (tp ? 0 : tc ? 1 : 2) : tp ? (fc ? 3 : 4) :
            fc ? (tc ? 5 : 6) : tc ? 7 : 8;
        if (matched && (rank < best_rank || (rank == best_rank && group.name < name))) {
            best_rank = rank; name = group.name;
        }
    }
    if (best_rank == 100 && capture < sdc->clocks().size())
        name = std::string(network.str(sdc->clocks()[capture].name));
    return name;
}

// ────────────────────────────────────────────────────────────
// Per-endpoint path extraction (thread-safe, read-only graph)
// ────────────────────────────────────────────────────────────
static PathInfo extract_endpoint_path(
    const TimingGraph& graph,
    const Network& network,
    const ResolvedConstraintSet* sdc,
    MinMax mm,
    uint32_t vid,
    const TimingCheckResult* check = nullptr)
{
    Transition rf = graph.vertex_transition(vid);
    const auto* launch = check ? (check->launch_key == UINT64_MAX ? nullptr :
        graph.launch_label(vid, mm, check->launch_key)) : graph.worst_launch_label(vid, mm);
    float arrival = check ? check->arrival : launch ? launch->arrival : graph.arrival(vid, mm, rf).value;
    float required = check ? check->required : launch ? launch->required : graph.required(vid, mm, rf).value;
    if (check && check->launch_key != UINT64_MAX && !launch) {
        PathInfo invalid; invalid.slack = std::numeric_limits<float>::infinity(); return invalid;
    }
    if (!std::isfinite(arrival) || !std::isfinite(required)) {
        PathInfo invalid;
        invalid.slack = std::numeric_limits<float>::infinity();
        return invalid;
    }
    float slack = (mm == MinMax::Max)
        ? (required - arrival)
        : (arrival - required);
    PinId pin = graph.vertex_pin(vid);

    PathInfo info;
    info.slack = slack;
    info.check_kind = check ? check->coverage.kind : graph.endpoint_check_kind(vid, mm);
    {
        const auto& endpoint_pin = network.pin(pin);
        if (valid(endpoint_pin.instance)) {
            const auto& endpoint_instance = network.instance(endpoint_pin.instance);
            info.top_output =
                network.cell_name(endpoint_instance.cell) == "__top__" &&
                endpoint_pin.direction == PortDirection::Input;
        }
    }

    // Back-trace the path
    uint32_t cur_vid = vid;
    Transition cur_rf = rf;
    float cur_arrival = arrival-(check ? check->path_time_shift : 0.f);
    uint64_t current_key = launch ? launch->key : UINT64_MAX;
    std::vector<PinId> path_pin_ids;

    while (cur_vid != UINT32_MAX) {
        PinId p = graph.vertex_pin(cur_vid);
        path_pin_ids.push_back(p);
        const auto& pin_data = network.pin(p);
        std::string name;
        std::string cell_name;
        if (valid(pin_data.instance)) {
            name = std::string(network.instance_name(pin_data.instance)) + "/" +
                   std::string(network.pin_name(p));
            const auto& inst_data = network.instance(pin_data.instance);
            std::string cname = std::string(network.cell_name(inst_data.cell));
            if (cname != "__top__") {
                cell_name = cname;
            }
        } else {
            name = std::string(network.pin_name(p));
        }
        info.point_names.push_back(name);
        info.cell_names.push_back(cell_name);
        info.arrivals.push_back(cur_arrival);

        const auto* current_label = launch ? graph.launch_label(cur_vid, mm, current_key) : nullptr;
        float slew_val = current_label ? current_label->slew : graph.slew(cur_vid, mm, cur_rf).value;
        info.slews.push_back(std::isfinite(slew_val) ? slew_val : 0.0f);
        info.transitions.push_back(cur_rf == Transition::Rise ? "rise" : "fall");

        // A timing-check result has an explicit related/source pin.  Stop the
        // ordinary launch backtrace once that pin is reached so a data-check
        // report describes source -> checked endpoint rather than an
        // unrelated clock launch path.  If the source is not on the selected
        // predecessor chain we retain the full path and expose the source
        // through PathReport::check_related_name.
        if (check && !launch && check->identity.rfind("sdc_data_check:", 0) == 0 &&
            valid(check->related) && p == check->related) {
            break;
        }

        uint32_t pred_vid = current_label ? current_label->predecessor : (mm == MinMax::Max)
            ? graph.pred_max(cur_vid, mm, cur_rf) : graph.pred_min(cur_vid, mm, cur_rf);
        if (pred_vid == UINT32_MAX) break;

        if (graph.is_startpoint(cur_vid)) break;

        const auto predecessor_key = current_label ? current_label->predecessor_key : UINT64_MAX;
        const auto* previous_label = launch ? graph.launch_label(pred_vid, mm, predecessor_key) : nullptr;
        if (launch && !previous_label) { info.slack = std::numeric_limits<float>::infinity(); return info; }
        float pred_arrival = previous_label ? previous_label->arrival :
            graph.arrival(pred_vid, mm, graph.vertex_transition(pred_vid)).value;
        if (!std::isfinite(pred_arrival)) {
            info.slack = std::numeric_limits<float>::infinity();
            return info;
        }
        float delay = cur_arrival - pred_arrival;
        info.delays.push_back(delay);

        cur_vid = pred_vid;
        current_key = predecessor_key;
        cur_arrival = pred_arrival;
        cur_rf = graph.vertex_transition(cur_vid);
    }

    // Reverse to get startpoint → endpoint order
    info.delays.push_back(0.0f);
    std::reverse(info.point_names.begin(), info.point_names.end());
    std::reverse(info.cell_names.begin(), info.cell_names.end());
    std::reverse(info.delays.begin(), info.delays.end());
    std::reverse(info.arrivals.begin(), info.arrivals.end());
    std::reverse(info.slews.begin(), info.slews.end());
    std::reverse(info.transitions.begin(), info.transitions.end());
    std::reverse(path_pin_ids.begin(), path_pin_ids.end());
    if (check && check->path_time_shift!=0.f)
        for (auto& value : info.arrivals) value+=check->path_time_shift;

    // Repair must preserve each capture clock domain independently. A single
    // global worst slack can hide regressions in a faster, sparsely reported
    // clock group, so retain the resolved domains with every path report.
    if (!path_pin_ids.empty()) {
        info.start_clock_domain =
            graph.vertex_clock_domain(path_pin_ids.front().id * 2);
        info.end_clock_domain =
            graph.vertex_clock_domain(path_pin_ids.back().id * 2);
        if (launch) {
            info.start_clock_domain = launch->domain;
            info.end_clock_domain = launch->capture;
        }
    }

    // Clock-qualified rise/fall selectors refer to clock edges, independently
    // of the data transition. Follow inversion back to the physical source.
    auto source_edge = [&](uint32_t clock_vid, MinMax mode) {
        for (size_t count=0; clock_vid < graph.vertex_count() && count<graph.vertex_count(); ++count) {
            const auto edge = graph.vertex_transition(clock_vid);
            const auto pred = mode == MinMax::Max ? graph.pred_max(clock_vid,mode,edge) : graph.pred_min(clock_vid,mode,edge);
            if (pred == UINT32_MAX) return edge;
            clock_vid = pred;
        }
        return Transition::Rise;
    };
    Transition launch_edge = Transition::Rise, capture_edge = Transition::Rise;
    PinId launch_clock_pin{UINT32_MAX};
    if (!path_pin_ids.empty()) {
        const auto& start = network.pin(path_pin_ids.front());
        const auto start_rf = info.transitions.front() == "rise" ? Transition::Rise : Transition::Fall;
        const uint32_t start_vid = path_pin_ids.front().id*2+unsigned(start_rf);
        if (valid(start.instance)) {
            launch_clock_pin = PinId{graph.instance_clk_pin(start.instance.id)};
            const auto pred = mm == MinMax::Max ? graph.pred_max(start_vid,mm,start_rf) : graph.pred_min(start_vid,mm,start_rf);
            if (pred != UINT32_MAX && graph.vertex_pin(pred) == launch_clock_pin) launch_edge=source_edge(pred,mm);
        }
    }
    if (check && valid(check->related) && check->identity.rfind("sdc_data_check:",0)!=0) {
        const auto capture_mm = mm == MinMax::Max ? MinMax::Min : MinMax::Max;
        capture_edge=source_edge(check->related.id*2+unsigned(check->capture_transition),capture_mm);
    } else if (!check && graph.endpoint_capture_clock(vid,mm)!=UINT32_MAX) {
        capture_edge=source_edge(graph.endpoint_capture_clock(vid,mm),mm == MinMax::Max ? MinMax::Min : MinMax::Max);
    }
    info.path_group = resolve_path_group(path_pin_ids, info.transitions, network, sdc,
        info.start_clock_domain, check ? check->capture_domain : info.end_clock_domain,
        launch_edge,capture_edge,launch_clock_pin);

    // The ledger has already applied exception predicates and selected the
    // capture edge. Preserve its numeric contract for candidate generation.
    if (check) {
        info.check = *check;
        // Keep this flag local to document why the path may still contain a
        // clock launch when a source pin is disconnected from the selected
        // predecessor chain.  The explicit related pin is exported by the
        // public report regardless of whether trimming was possible.
        info.end_clock_domain = check->capture_domain;
        info.slack = check->slack;
        info.cppr = check->cppr;
        return info;
    }

    // Output-delay checks are relative to the capture clock edge.  Register
    // arrivals are stored relative to their launch edge at time zero, while
    // STA selects the latest launch edge strictly before the first capture
    // edge for unrelated clocks (e.g. CPU_CLK=1 ns -> V_SYS_AXI_CLK=2 ns).
    // Restore that phase for primary-output paths only; reg-to-reg required
    // times already encode the full capture period and must remain unchanged.
    if (!launch && mm == MinMax::Max && info.top_output && !path_pin_ids.empty() && sdc) {
        const auto& start_pd = network.pin(path_pin_ids.front());
        if (valid(start_pd.instance) &&
            graph.instance_clk_pin(start_pd.instance.id) != UINT32_MAX) {
            const uint32_t start_domain =
                graph.vertex_clock_domain(path_pin_ids.front().id * 2);
            const uint32_t end_domain =
                graph.vertex_clock_domain(path_pin_ids.back().id * 2);
            if (start_domain < sdc->clocks().size() &&
                end_domain < sdc->clocks().size()) {
                const float launch_period = sdc->clocks()[start_domain].period;
                const float capture_period = sdc->clocks()[end_domain].period;
                if (launch_period > 0.0f && capture_period > 0.0f &&
                    std::isfinite(launch_period) &&
                    std::isfinite(capture_period)) {
                    const float cycles = std::ceil(
                        capture_period / launch_period - 1.0e-6f) - 1.0f;
                    const float launch_phase =
                        std::max(0.0f, cycles * launch_period);
                    if (launch_phase > 0.0f) {
                        for (float& arrival_value : info.arrivals) {
                            arrival_value += launch_phase;
                        }
                        slack -= launch_phase;
                    }
                }
            }
        }
    }

    // CPPR is applied once, in the endpoint check, before required propagation.
    info.cppr = launch ? launch->cppr : graph.endpoint_cppr(vid, mm);
    info.slack = slack;

    // Check false paths
    bool is_false = false;
    if (sdc) {
        if (!path_pin_ids.empty()) {
            uint32_t start_domain = info.start_clock_domain;
            uint32_t end_domain = info.end_clock_domain;
            if (edacraft::core::resolved_clock_groups_cut_path(
                    sdc->clock_groups(), start_domain, end_domain)) {
                is_false = true;
            }
        }
        if (!launch) for (const auto& fp : sdc->false_paths()) {
            if (!false_path_applies_to_analysis(fp, mm)) continue;
            LaunchTimingLabel clock_label;
            clock_label.domain=info.start_clock_domain;
            if (!exception_clock_matches(fp,&clock_label,info.end_clock_domain)) continue;
            // Skip malformed false paths with no constraints
            if (fp.from_pins.empty() && fp.to_pins.empty() && fp.through_pins.empty() &&
                fp.from_clocks.empty() && fp.to_clocks.empty()) continue;
            bool from_match = fp.from_pins.empty();
            const bool to_match = fp.to_pins.empty() ||
                std::find(fp.to_pins.begin(), fp.to_pins.end(), path_pin_ids.back()) != fp.to_pins.end();
            const size_t stage_count = fp.through_pins.empty() ? 0 : 1 + fp.through_stages.size();
            size_t completed = 0;
            for (const auto pid : path_pin_ids) {
                from_match = from_match || std::find(fp.from_pins.begin(), fp.from_pins.end(), pid) != fp.from_pins.end();
                if (!from_match) continue;
                while (completed < stage_count) {
                    const auto& stage = completed == 0 ? fp.through_pins : fp.through_stages[completed-1];
                    if (std::find(stage.begin(), stage.end(), pid) == stage.end()) break;
                    ++completed;
                }
            }
            const bool through_match = completed == stage_count;
            if (from_match && to_match && through_match) {
                is_false = true;
                break;
            }
        }
    }
    if (is_false) {
        info.slack = std::numeric_limits<float>::infinity();
    }

    return info;
}

std::vector<PathInfo> PathCollector::collect_check_paths(
    const TimingGraph& graph, const Network& network, MinMax mm, int count,
    const ResolvedConstraintSet* sdc, TimingCheckKind kind, bool balance_groups,
    std::string_view path_group) {
    if (count <= 0) return {};
    std::vector<const TimingCheckResult*> checks;
    for (const auto& check : graph.check_results()) {
        if (check.coverage.analysis != mm || !timing_check_matches(check.coverage.kind, kind) ||
            check.coverage.state != CheckCoverageState::Evaluated || !std::isfinite(check.arrival) ||
            !std::isfinite(check.required) || !std::isfinite(check.slack)) continue;
        const uint64_t vid = uint64_t(check.coverage.pin.id)*2 + unsigned(check.coverage.transition);
        if (vid < graph.vertex_count()) checks.push_back(&check);
    }
    // Sort lightweight references first; only selected checks need a backtrace.
    // Semantic history identity keeps tie ordering independent of interning IDs.
    std::sort(checks.begin(), checks.end(), [](const auto* a, const auto* b) {
        return std::tie(a->slack, a->coverage.pin.id, a->identity, a->capture_domain,
                        a->capture_transition, a->launch_identity, a->launch_key, a->coverage.transition) <
               std::tie(b->slack, b->coverage.pin.id, b->identity, b->capture_domain,
                        b->capture_transition, b->launch_identity, b->launch_key, b->coverage.transition);
    });
    std::vector<PathInfo> paths;
    if (balance_groups && count > 1) {
        using Group = std::tuple<TimingCheckKind, uint32_t, Transition>;
        std::map<Group, size_t> group_ids;
        std::vector<std::vector<const TimingCheckResult*>> groups;
        for (auto* check : checks) {
            Group key{check->coverage.kind, check->capture_domain, check->capture_transition};
            auto [found, inserted] = group_ids.emplace(key, groups.size());
            if (inserted) groups.emplace_back();
            groups[found->second].push_back(check);
        }
        // One candidate per check/capture group is the minimum repair budget.
        // Preserve the global worst path, then visit groups in round-robin order.
        const size_t limit = path_group.empty() ? std::max(size_t(count), groups.size()) : size_t(count);
        std::vector<size_t> cursor(groups.size(), 0);
        bool remaining = true;
        while (paths.size() < limit && remaining) {
            remaining = false;
            for (size_t i = 0; i < groups.size() && paths.size() < limit; ++i) {
                while (cursor[i] < groups[i].size()) {
                    const auto* check = groups[i][cursor[i]++];
                    const auto vid = check->coverage.pin.id*2 + unsigned(check->coverage.transition);
                    auto path = extract_endpoint_path(graph, network, sdc, mm, vid, check);
                    if (!std::isfinite(path.slack)) continue;
                    if (!path_group.empty() && path.path_group != path_group) continue;
                    paths.push_back(std::move(path)); break;
                }
                remaining |= cursor[i] < groups[i].size();
            }
        }
        return paths;
    }
    paths.reserve(std::min(checks.size(), size_t(count)));
    for (const auto* check : checks) {
        const auto vid = check->coverage.pin.id*2 + unsigned(check->coverage.transition);
        auto path = extract_endpoint_path(graph, network, sdc, mm, vid, check);
        if (!std::isfinite(path.slack)) continue;
        if (!path_group.empty() && path.path_group != path_group) continue;
        paths.push_back(std::move(path));
        if (paths.size() == size_t(count)) break;
    }
    return paths;
}

std::vector<PathInfo> PathCollector::collect_worst_paths(
    const TimingGraph& graph,
    const Network& network,
    MinMax mm,
    int count,
    const ResolvedConstraintSet* sdc,
    bool sort_by_data_delay,
    TimingCheckKind kind,
    std::string_view path_group
) {
    // Phase 1: Collect all endpoint vids (serial, cheap)
    std::vector<uint32_t> endpoint_vids;
    endpoint_vids.reserve(graph.vertex_count() / 10);
    for (uint32_t vid = 0; vid < graph.vertex_count(); ++vid) {
        if (graph.is_endpoint(vid)) {
            if (!timing_check_matches(graph.endpoint_check_kind(vid, mm), kind)) continue;
            // Top-level output pins are inputs of the synthetic __top__
            // instance. Include them in hold analysis only when SDC provides
            // an explicit min output delay.
            if (mm == MinMax::Min) {
                PinId pin = graph.vertex_pin(vid);
                const auto& pin_data = network.pin(pin);
                if (valid(pin_data.instance)) {
                    const auto& inst_data = network.instance(pin_data.instance);
                    if (network.cell_name(inst_data.cell) == "__top__" &&
                        pin_data.direction == PortDirection::Input) {
                        bool has_min_output_delay = false;
                        if (sdc) {
                            for (const auto& delay : sdc->output_delays()) {
                                if (delay.is_max) continue;
                                if (std::find(delay.ports.begin(), delay.ports.end(), pin) !=
                                    delay.ports.end()) {
                                    has_min_output_delay = true;
                                    break;
                                }
                            }
                        }
                        if (!has_min_output_delay) continue;
                    }
                }
            }
            Transition rf = graph.vertex_transition(vid);
            float arrival = graph.arrival(vid, mm, rf).value;
            if (std::isfinite(arrival) && arrival != std::numeric_limits<float>::lowest()) {
                endpoint_vids.push_back(vid);
            }
        }
    }

    size_t n = endpoint_vids.size();
    if (endpoint_debug_enabled()) {
        size_t top_total = 0;
        size_t top_arrival_finite = 0;
        size_t top_required_finite = 0;
        size_t top_both_finite = 0;
        for (uint32_t vid = 0; vid < graph.vertex_count(); ++vid) {
            if (!graph.is_endpoint(vid)) continue;
            PinId pin = graph.vertex_pin(vid);
            const auto& pin_data = network.pin(pin);
            if (!valid(pin_data.instance)) continue;
            const auto& inst_data = network.instance(pin_data.instance);
            if (network.cell_name(inst_data.cell) != "__top__" ||
                pin_data.direction != PortDirection::Input) {
                continue;
            }
            ++top_total;
            Transition rf = graph.vertex_transition(vid);
            const bool arrival_finite = std::isfinite(
                graph.arrival(vid, mm, rf).value);
            const bool required_finite = std::isfinite(
                graph.required(vid, mm, rf).value);
            if (arrival_finite) ++top_arrival_finite;
            if (required_finite) ++top_required_finite;
            if (arrival_finite && required_finite) ++top_both_finite;
        }
        std::cerr << "[path_collector_debug] mm="
                  << (mm == MinMax::Max ? "max" : "min")
                  << " endpoints=" << endpoint_vids.size()
                  << " top_total=" << top_total
                  << " top_arrival_finite=" << top_arrival_finite
                  << " top_required_finite=" << top_required_finite
                  << " top_both_finite=" << top_both_finite << "\n";
    }
    if (n == 0 || count <= 0) return {};

    // Phase 2: Parallel path extraction per endpoint.
    // Each thread accumulates into its own local map to avoid contention.
    unsigned num_threads = get_num_threads();

    std::vector<std::unordered_map<uint32_t, PathInfo>> local_bests(num_threads);

    parallel_for_with_id(0, n, [&](size_t idx, unsigned tid) {
        uint32_t vid = endpoint_vids[idx];
        PathInfo info = extract_endpoint_path(graph, network, sdc, mm, vid);
        if (info.slack == std::numeric_limits<float>::infinity()) return;
        if (!path_group.empty() && info.path_group != path_group) return;

        PinId pin = graph.vertex_pin(vid);
        auto& local = local_bests[tid];
        auto it = local.find(pin.id);
        if (it == local.end() || info.slack < it->second.slack) {
            local[pin.id] = std::move(info);
        }
    });

    // Phase 3: Merge local maps (serial).
    std::unordered_map<uint32_t, PathInfo> pin_best;
    pin_best.reserve(n);
    for (auto& local : local_bests) {
        for (auto& [pid, info] : local) {
            auto it = pin_best.find(pid);
            if (it == pin_best.end() || info.slack < it->second.slack) {
                pin_best[pid] = std::move(info);
            }
        }
    }
    // Phase 4: Sort by worst slack
    std::vector<PathInfo> paths;
    paths.reserve(pin_best.size());
    for (auto& [pid, info] : pin_best) {
        paths.push_back(std::move(info));
    }
    if (paths.empty()) return {};

    if (sort_by_data_delay) {
        auto data_delay = [](const PathInfo& path) {
            if (path.arrivals.size() < 2 ||
                !std::isfinite(path.arrivals.front()) ||
                !std::isfinite(path.arrivals.back())) {
                return 0.0f;
            }
            return std::max(
                0.0f, path.arrivals.back() - path.arrivals.front());
        };
        std::sort(paths.begin(), paths.end(), [&](const PathInfo& a,
                                                  const PathInfo& b) {
            const float a_delay = data_delay(a);
            const float b_delay = data_delay(b);
            if (std::fabs(a_delay - b_delay) > 1.0e-12f) {
                return a_delay > b_delay;
            }
            return a.slack < b.slack;
        });
    } else {
        std::sort(paths.begin(), paths.end(),
                  [](const PathInfo& a, const PathInfo& b) {
            return a.slack < b.slack;
        });
    }

    // A single-path query is the scalar WNS contract used by timing reports
    // and candidate acceptance.  It must return the globally worst endpoint;
    // the interface quota below is only for multi-path diagnostics/repair,
    // where retaining one primary-output path improves coverage.
    if (count == 1) {
        paths.resize(1);
        return paths;
    }

    if (static_cast<int>(paths.size()) > count) {
        // Keep a bounded interface quota in addition to the globally worst
        // endpoints.  Large designs often have enough internal register
        // violations to crowd all primary-output paths out of the report,
        // which prevents post-netlist repair from seeing real I/O timing.
        const size_t output_quota = std::min<size_t>(
            static_cast<size_t>(count),
            std::max<size_t>(1, static_cast<size_t>(count) / 5));
        std::vector<PathInfo> selected;
        selected.reserve(static_cast<size_t>(count));
        std::vector<char> selected_flags(paths.size(), 0);
        size_t outputs = 0;
        for (size_t index = 0; index < paths.size(); ++index) {
            const auto& path = paths[index];
            if (!path.top_output || outputs >= output_quota) continue;
            selected.push_back(path);
            selected_flags[index] = 1;
            ++outputs;
        }
        for (size_t index = 0; index < paths.size(); ++index) {
            if (selected.size() >= static_cast<size_t>(count)) break;
            if (selected_flags[index]) continue;
            selected.push_back(paths[index]);
        }
        paths = std::move(selected);
        if (sort_by_data_delay) {
            auto data_delay = [](const PathInfo& path) {
                if (path.arrivals.size() < 2 ||
                    !std::isfinite(path.arrivals.front()) ||
                    !std::isfinite(path.arrivals.back())) {
                    return 0.0f;
                }
                return std::max(
                    0.0f, path.arrivals.back() - path.arrivals.front());
            };
            std::stable_sort(paths.begin(), paths.end(),
                             [&](const PathInfo& a, const PathInfo& b) {
                const float a_delay = data_delay(a);
                const float b_delay = data_delay(b);
                if (std::fabs(a_delay - b_delay) > 1.0e-12f) {
                    return a_delay > b_delay;
                }
                return a.slack < b.slack;
            });
        } else {
            std::stable_sort(paths.begin(), paths.end(),
                             [](const PathInfo& a, const PathInfo& b) {
                return a.slack < b.slack;
            });
        }
        if (static_cast<int>(paths.size()) > count) paths.resize(count);
    }

    return paths;
}

} // namespace te
