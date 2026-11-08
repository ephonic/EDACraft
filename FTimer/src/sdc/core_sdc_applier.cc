#include "sdc/core_sdc_applier.hh"

#include "sdc/resolved_constraints.hh"

#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

namespace te {

std::vector<PinId> resolve_sdc_pin_list(
    const std::vector<std::string>& names,
    const PinResolver& pin_resolver) {
    std::vector<PinId> result;
    result.reserve(names.size());
    for (const auto& name : names) {
        auto opt = pin_resolver(name);
        if (opt) result.push_back(*opt);
    }
    return result;
}

std::vector<PinId> resolve_sdc_pin_list(
    const std::vector<std::string>& names,
    const PinListResolver& pin_resolver) {
    std::vector<PinId> result;
    for (const auto& name : names) {
        auto pins = pin_resolver(name);
        result.insert(result.end(), pins.begin(), pins.end());
    }
    return result;
}

uint32_t apply_core_sdc(
    const edacraft::core::ConstraintDB& constraints,
    ResolvedConstraintSet& sdc_ctx,
    const PinResolver& pin_resolver,
    const StringInterner& string_interner,
    bool verbose) {
    PinListResolver list_resolver = [&pin_resolver](const std::string& name) {
        std::vector<PinId> pins;
        auto pin = pin_resolver(name);
        if (pin) pins.push_back(*pin);
        return pins;
    };
    return apply_core_sdc(constraints, sdc_ctx, list_resolver, string_interner, verbose);
}

uint32_t apply_core_sdc(
    const edacraft::core::ConstraintDB& constraints,
    ResolvedConstraintSet& sdc_ctx,
    const PinListResolver& pin_resolver,
    const StringInterner& string_interner,
    bool verbose) {
    uint32_t applied = 0;
    auto clock_constraints = constraints;
    std::string clock_error;
    if (!clock_constraints.resolve_generated_clocks(clock_error)) throw std::runtime_error(clock_error);
    std::unordered_map<std::string, uint32_t> clock_ids;
    std::vector<std::vector<PinId>> clock_sources;
    for (const auto& clk : clock_constraints.clocks()) {
        uint32_t name_id = string_interner(clk.name);
        uint32_t clock_id = sdc_ctx.create_clock(
            name_id, clk.period_ns, clk.transition_ns >= 0.0f ? clk.transition_ns : 0.0f);
        clock_ids[clk.name] = clock_id;

        auto source_pins = resolve_sdc_pin_list({clk.source_port}, pin_resolver);
        clock_sources.push_back(source_pins);
        for (auto pin : source_pins) {
            sdc_ctx.add_clock_source(clock_id, pin);
        }
        if (clk.propagated) sdc_ctx.set_clock_propagated(clock_id, true);

        if (clk.waveform_explicit) {
            sdc_ctx.set_clock_waveform(clock_id, clk.rise_edge_ns, clk.fall_edge_ns);
        }

        if (verbose) {
            std::cerr << "[core_sdc] create_clock '" << clk.name
                      << "' period=" << clk.period_ns << " ns\n";
        }
        ++applied;
    }
    for (size_t index = 0; index < clock_constraints.clocks().size(); ++index) {
        const auto& clk = clock_constraints.clocks()[index];
        if (!clk.generated) continue;
        const auto& def = *clk.generated;
        auto source = resolve_sdc_pin_list({def.source}, pin_resolver);
        const auto master = clock_ids.find(def.resolved_master_clock);
        if (source.size() != 1 || clock_sources[index].size() != 1 || master == clock_ids.end())
            throw std::runtime_error("Generated clock " + clk.name + " needs one bound source and target and an existing master");
        const auto target = clock_sources[index].front();
        if (source.front() == target) throw std::runtime_error("Generated clock source and target must be distinct");
        for (uint32_t other = 0; other < sdc_ctx.clocks().size(); ++other) {
            if (other == clock_ids.at(clk.name)) continue;
            const auto& pins = sdc_ctx.clocks()[other].sources;
            if (std::find(pins.begin(), pins.end(), target) != pins.end())
                throw std::runtime_error("Multiple clocks on generated target " + clk.source_port + " are unsupported");
        }
        sdc_ctx.set_generated_clock(clock_ids.at(clk.name), master->second, source.front());
    }

    auto find_clock_id = [&](const std::string& name) -> uint32_t {
        const auto& clocks = sdc_ctx.clocks();
        uint32_t expected_id = string_interner(name);
        for (uint32_t i = 0; i < clocks.size(); ++i) {
            if (clocks[i].name == expected_id) return i;
        }
        if (!clocks.empty()) return 0;
        return UINT32_MAX;
    };

    auto find_exact_clock_id = [&](const std::string& name) -> uint32_t {
        const auto& clocks = sdc_ctx.clocks();
        uint32_t expected_id = string_interner(name);
        for (uint32_t i = 0; i < clocks.size(); ++i) {
            if (clocks[i].name == expected_id) return i;
        }
        return UINT32_MAX;
    };

    for (const auto& group_def : constraints.clock_groups()) {
        std::vector<std::vector<uint32_t>> resolved_groups;
        resolved_groups.reserve(group_def.groups.size());
        for (const auto& group : group_def.groups) {
            std::vector<uint32_t> resolved_group;
            resolved_group.reserve(group.size());
            for (const auto& clock_name : group) {
                uint32_t clock_id = find_exact_clock_id(clock_name);
                if (clock_id == UINT32_MAX) continue;
                if (std::find(resolved_group.begin(), resolved_group.end(), clock_id) ==
                    resolved_group.end()) {
                    resolved_group.push_back(clock_id);
                }
            }
            if (!resolved_group.empty()) {
                resolved_groups.push_back(std::move(resolved_group));
            }
        }
        if (resolved_groups.size() < 2) continue;

        auto mode = edacraft::core::ResolvedClockGroupMode::Asynchronous;
        switch (group_def.mode) {
            case edacraft::core::ClockGroupDef::Mode::Asynchronous:
                mode = edacraft::core::ResolvedClockGroupMode::Asynchronous;
                break;
            case edacraft::core::ClockGroupDef::Mode::LogicallyExclusive:
                mode = edacraft::core::ResolvedClockGroupMode::LogicallyExclusive;
                break;
            case edacraft::core::ClockGroupDef::Mode::PhysicallyExclusive:
                mode = edacraft::core::ResolvedClockGroupMode::PhysicallyExclusive;
                break;
        }
        sdc_ctx.set_clock_groups(mode, std::move(resolved_groups));
        ++applied;
    }

    for (const auto& cl : constraints.clock_latencies()) {
        uint32_t clock_id = find_clock_id(cl.clock_name);
        auto pins = resolve_sdc_pin_list(cl.pin_names, pin_resolver);
        sdc_ctx.set_clock_latency(cl.latency_ns, clock_id, std::move(pins));
        ++applied;
    }

    for (const auto& cu : constraints.clock_uncertainties()) {
        uint32_t clock_id = find_clock_id(cu.clock_name);
        if (cu.setup_uncertainty_ns != 0.0f) {
            sdc_ctx.set_clock_uncertainty(cu.setup_uncertainty_ns, clock_id, true);
        }
        if (cu.hold_uncertainty_ns != 0.0f) {
            sdc_ctx.set_clock_uncertainty(cu.hold_uncertainty_ns, clock_id, false);
        }
        ++applied;
    }

    for (const auto& d : constraints.io_delays()) {
        uint32_t clock_id = find_clock_id(d.clock_name);
        auto pins = resolve_sdc_pin_list(d.port_names, pin_resolver);
        if (pins.empty()) continue;

        Transition edge = (d.clock_edge == edacraft::core::Transition::Rise)
            ? Transition::Rise
            : Transition::Fall;

        if (d.is_input) {
            sdc_ctx.set_input_delay(clock_id, d.delay_ns, d.is_max, edge, std::move(pins));
        } else {
            sdc_ctx.set_output_delay(clock_id, d.delay_ns, d.is_max, edge, std::move(pins));
        }
        ++applied;
    }

    auto exception_pins = [&](const std::vector<std::string>& names) {
        auto pins = resolve_sdc_pin_list(names, pin_resolver);
        if (!names.empty() && pins.empty()) pins.push_back(NULL_PIN);
        return pins;
    };
    auto exception_clocks = [&](const std::vector<std::string>& names) {
        std::vector<uint32_t> ids;
        for (const auto& name : names) ids.push_back(find_exact_clock_id(name));
        return ids;
    };
    for (const auto& pd : constraints.path_delays()) {
        auto from_pins = exception_pins(pd.from_pins);
        auto to_pins = exception_pins(pd.to_pins);
        auto through_pins = exception_pins(pd.through_pins);
        std::vector<std::vector<PinId>> stages;
        for (const auto& stage : pd.through_stages) stages.push_back(exception_pins(stage));
        if (pd.is_max) {
            sdc_ctx.set_max_delay(pd.delay_ns, std::move(from_pins), std::move(to_pins),std::move(through_pins),std::move(stages),exception_clocks(pd.from_clocks),exception_clocks(pd.to_clocks),pd.ignore_clock_latency);
        } else {
            sdc_ctx.set_min_delay(pd.delay_ns, std::move(from_pins), std::move(to_pins),std::move(through_pins),std::move(stages),exception_clocks(pd.from_clocks),exception_clocks(pd.to_clocks),pd.ignore_clock_latency);
        }
        ++applied;
    }

    for (const auto& check : constraints.data_checks()) {
        auto from_pins = resolve_sdc_pin_list(check.from_pins, pin_resolver);
        auto to_pins = resolve_sdc_pin_list(check.to_pins, pin_resolver);
        if (from_pins.empty() || to_pins.empty()) continue;
        sdc_ctx.set_data_check(check.delay_ns, check.is_setup,
                               std::move(from_pins), std::move(to_pins),
                               check.from_transitions, check.to_transitions);
        ++applied;
    }

    for (const auto& group : constraints.path_groups()) {
        // An unresolved nonempty selector must never turn into match-all.
        auto resolve = [&](const std::vector<std::string>& names) {
            auto pins = resolve_sdc_pin_list(names, pin_resolver);
            if (!names.empty() && pins.empty()) pins.push_back(NULL_PIN);
            return pins;
        };
        ResolvedConstraintSet::PathGroup resolved;
        resolved.name = group.name;
        resolved.weight = group.weight;
        resolved.from_transitions = group.from_transitions;
        resolved.to_transitions = group.to_transitions;
        resolved.through_transitions = group.through_transitions;
        resolved.through_stage_transitions = group.through_stage_transitions;
        for (const auto& name : group.from_clocks) resolved.from_clocks.push_back(find_exact_clock_id(name));
        for (const auto& name : group.to_clocks) resolved.to_clocks.push_back(find_exact_clock_id(name));
        resolved.from_pins = resolve(group.from_pins);
        resolved.through_pins = resolve(group.through_pins);
        resolved.to_pins = resolve(group.to_pins);
        for (const auto& stage : group.through_stages)
            resolved.through_stages.push_back(resolve(stage));
        sdc_ctx.add_path_group(std::move(resolved));
        ++applied;
    }

    for (const auto& sl : constraints.set_loads()) {
        auto pins = resolve_sdc_pin_list(sl.pin_names, pin_resolver);
        if (pins.empty()) continue;
        sdc_ctx.set_load(sl.capacitance_pf, std::move(pins));
        ++applied;
    }

    for (const auto& it : constraints.input_transitions()) {
        auto pins = resolve_sdc_pin_list(it.port_names, pin_resolver);
        if (pins.empty()) continue;
        sdc_ctx.set_input_transition(it.transition_ns, std::move(pins),
                                    it.rise, it.fall, it.min, it.max, it.order);
        ++applied;
    }

    for (const auto& driver : constraints.driving_cells()) {
        auto pins = resolve_sdc_pin_list(driver.port_names, pin_resolver);
        if (pins.empty()) continue;
        sdc_ctx.set_driving_cell(driver, std::move(pins));
        ++applied;
    }

    for (const auto& mcp : constraints.multicycle_paths()) {
        auto from_pins = exception_pins(mcp.from_pins);
        auto to_pins = exception_pins(mcp.to_pins);
        sdc_ctx.set_multicycle_path(mcp.setup_cycles, mcp.hold_cycles,
                                    std::move(from_pins), std::move(to_pins),exception_clocks(mcp.from_clocks),exception_clocks(mcp.to_clocks),mcp.is_hold,mcp.use_start);
        ++applied;
    }

    for (const auto& fp : constraints.false_paths()) {
        auto from_pins = exception_pins(fp.from_pins);
        auto through_pins = exception_pins(fp.through_pins);
        auto to_pins = exception_pins(fp.to_pins);
        std::vector<std::vector<PinId>> through_stages;
        for (const auto& stage : fp.through_stages)
            through_stages.push_back(exception_pins(stage));
        sdc_ctx.set_false_path(std::move(from_pins), std::move(through_pins),
                               std::move(to_pins), std::move(through_stages), fp.setup, fp.hold,
                               fp.from_transitions, fp.to_transitions, fp.through_transitions,
                               fp.through_stage_transitions,exception_clocks(fp.from_clocks),exception_clocks(fp.to_clocks));
        ++applied;
    }

    for (const auto& dt : constraints.disable_timings()) {
        PinId from_pin = NULL_PIN;
        PinId to_pin = NULL_PIN;
        if (!dt.from_pin.empty()) {
            auto pins = pin_resolver(dt.from_pin);
            if (!pins.empty()) from_pin = pins.front();
        }
        if (!dt.to_pin.empty()) {
            auto pins = pin_resolver(dt.to_pin);
            if (!pins.empty()) to_pin = pins.front();
        }
        sdc_ctx.set_disable_timing(from_pin, to_pin);
        ++applied;
    }

    for (const auto& ca : constraints.case_analyses()) {
        auto pins = pin_resolver(ca.pin_name);
        // CaseAnalysisDef retains the collection as one string. Resolve all
        // its members, while allowing an exact alias to contain whitespace.
        if (pins.empty()) {
            auto names = ca.pin_name;
            if (names.size() >= 2 &&
                ((names.front() == '{' && names.back() == '}') ||
                 (names.front() == '"' && names.back() == '"')))
                names = names.substr(1, names.size()-2);
            std::istringstream list(names);
            std::string name;
            while (list >> name) {
                auto members = pin_resolver(name);
                pins.insert(pins.end(), members.begin(), members.end());
            }
        }
        if (pins.empty()) continue;
        CaseAnalysis::Value val;
        switch (ca.value) {
            case edacraft::core::CaseAnalysisDef::Zero:
                val = CaseAnalysis::Zero;
                break;
            case edacraft::core::CaseAnalysisDef::One:
                val = CaseAnalysis::One;
                break;
            case edacraft::core::CaseAnalysisDef::Rise:
                val = CaseAnalysis::Rise;
                break;
            case edacraft::core::CaseAnalysisDef::Fall:
                val = CaseAnalysis::Fall;
                break;
        }
        for (auto pin : pins) {
            sdc_ctx.set_case_analysis(val, pin);
            ++applied;
        }
    }

    const auto& ocv = constraints.ocv_derate();
    if (ocv.early_data != 1.0f || ocv.late_data != 1.0f) {
        sdc_ctx.set_timing_derate(ocv.early_data, ocv.late_data, false);
        ++applied;
    }
    if (ocv.early_clock != 1.0f || ocv.late_clock != 1.0f) {
        sdc_ctx.set_timing_derate(ocv.early_clock, ocv.late_clock, true);
        ++applied;
    }

    if (!constraints.aocv_points().empty()) {
        std::vector<AocvPoint> points;
        points.reserve(constraints.aocv_points().size());
        for (const auto& ap : constraints.aocv_points()) {
            points.push_back({ap.depth, ap.late_derate, ap.early_derate});
        }
        sdc_ctx.set_aocv_derate(std::move(points));
        ++applied;
    }

    const auto& dr = constraints.design_rules();
    if (dr.max_fanout >= 0.0f || dr.max_capacitance >= 0.0f ||
        dr.max_transition >= 0.0f) {
        sdc_ctx.set_design_rules(dr.max_fanout, dr.max_capacitance,
                                 dr.max_transition);
        ++applied;
    }

    if (verbose) {
        std::cerr << "[core_sdc] Applied " << applied
                  << " constraints from ConstraintDB to ResolvedConstraintSet\n";
    }

    return applied;
}

} // namespace te
