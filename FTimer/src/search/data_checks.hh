#pragma once

#include "endpoint_checks.hh"

namespace te {

// SDC nonsequential checks have a zero-cycle relation: setup constrains the
// checked signal before the early reference. Default hold checks the next
// launch cycle against that reference (PrimeTime's zero-cycle setup relation).
// Evaluate both route sets, including the reference's opposite analysis.
inline void apply_sdc_data_checks(TimingGraph& graph, const Network& network,
    const ResolvedConstraintSet& sdc, size_t pair_limit) {
    if (sdc.data_checks().empty()) return;
    size_t pairs=0;
    for (size_t index=0;index<sdc.data_checks().size();++index) {
        const auto& constraint=sdc.data_checks()[index];
        const auto mm=constraint.is_setup ? MinMax::Max : MinMax::Min;
        const auto reference_mode=constraint.is_setup ? MinMax::Min : MinMax::Max;
        const auto kind=constraint.is_setup ? TimingCheckKind::Setup : TimingCheckKind::Hold;
        for (const auto from : constraint.from_pins) for (const auto to : constraint.to_pins)
        for (const auto frf : {Transition::Rise,Transition::Fall})
        for (const auto trf : {Transition::Rise,Transition::Fall}) {
            if (!(constraint.from_transitions & (frf==Transition::Rise?1:2)) ||
                !(constraint.to_transitions & (trf==Transition::Rise?1:2))) continue;
            const uint32_t fv=from.id*2+unsigned(frf), tv=to.id*2+unsigned(trf);
            if (fv>=graph.vertex_count() || tv>=graph.vertex_count()) continue;
            const auto& references=graph.launch_labels(fv,reference_mode);
            auto& targets=graph.launch_labels(tv,mm);
            if (references.empty() || targets.empty()) {
                graph.add_check_coverage({to,0x80000000u|uint32_t(index),trf,mm,kind,CheckCoverageState::MissingArrival});
                continue;
            }
            for (const auto& reference : references) for (auto& target : targets) {
                if (++pairs>pair_limit) throw std::runtime_error("SDC data-check route-pair budget exceeded");
                bool compatible=true;
                for (const auto literal : reference.path_conditions) {
                    const auto other=std::find_if(target.path_conditions.begin(),target.path_conditions.end(),
                        [&](const auto& p) { return p.first==literal.first; });
                    if (other!=target.path_conditions.end() && other->second!=literal.second) { compatible=false; break; }
                }
                if (!compatible) continue;
                TimingCheckResult result;
                result.coverage={to,0x80000000u|uint32_t(index),trf,mm,kind,CheckCoverageState::Evaluated};
                result.identity="sdc_data_check:"+std::to_string(index)+":"+std::to_string(from.id)+":"+
                    std::to_string(unsigned(frf))+":"+std::to_string(reference.key);
                result.related=from; result.capture_transition=frf; result.capture_domain=reference.domain;
                result.launch_key=target.key; result.launch_identity=graph.launch_identity(target.key);
                result.arrival=target.arrival;
                auto& state=result.coverage.state;
                if (target.unresolved_history || reference.unresolved_history)
                    state=CheckCoverageState::UnsupportedMixedClockPaths;
                else if (!std::isfinite(target.arrival) || !std::isfinite(reference.arrival))
                    state=CheckCoverageState::MissingArrival;
                else if (false_path_excludes_launch(graph,&sdc,tv,mm,target))
                    state=CheckCoverageState::ExcludedFalsePath;
                else if (edacraft::core::resolved_clock_groups_cut_path(sdc.clock_groups(),target.domain,reference.domain))
                    state=CheckCoverageState::ExcludedClockGroup;
                // Cross-domain zero-cycle waveform matching still requires a
                // full related-event relation. Surface this gap in coverage.
                else if (target.domain!=reference.domain ||
                    !std::isfinite(target.phase) || !std::isfinite(reference.phase) ||
                    std::fabs(target.phase-reference.phase)>1e-6f)
                    state=CheckCoverageState::UnsupportedMixedClockPaths;
                if (state==CheckCoverageState::Evaluated) {
                    auto clock_vertex=[&](const LaunchTimingLabel& label, MinMax mode) {
                        if (label.start>=graph.vertex_count()) return UINT32_MAX;
                        const auto& pd=network.pin(graph.vertex_pin(label.start));
                        if (!valid(pd.instance)) return UINT32_MAX;
                        const auto rf=graph.vertex_transition(label.start);
                        const auto pred=mode==MinMax::Max ? graph.pred_max(label.start,mode,rf) : graph.pred_min(label.start,mode,rf);
                        return pred!=UINT32_MAX && graph.vertex_pin(pred).id==graph.instance_clk_pin(pd.instance.id) ? pred : UINT32_MAX;
                    };
                    const auto data_clock=clock_vertex(target,mm), reference_clock=clock_vertex(reference,reference_mode);
                    if (data_clock!=UINT32_MAX && reference_clock!=UINT32_MAX)
                        result.cppr=clock_path_pessimism(graph,data_clock,reference_clock,mm);
                    if (!constraint.is_setup && target.domain<sdc.clocks().size()) {
                        result.path_time_shift=sdc.clocks()[target.domain].period;
                        result.arrival+=result.path_time_shift;
                    }
                    result.required=reference.arrival+(constraint.is_setup ? -constraint.delay+result.cppr : constraint.delay-result.cppr);
                    result.slack=constraint.is_setup ? result.required-result.arrival : result.arrival-result.required;
                    if (!std::isfinite(result.required) || !std::isfinite(result.slack)) state=CheckCoverageState::InvalidCheck;
                    else if (constraint.is_setup ? result.required<target.required : result.required-result.path_time_shift>target.required) {
                        target.required=result.required-result.path_time_shift; target.kind=kind; target.cppr=result.cppr; target.capture=reference.domain;
                    }
                }
                graph.add_check_coverage(result.coverage); graph.add_check_result(std::move(result));
            }
        }
    }
    // Publish these additional requirements on their actual predecessor routes
    // so get_slack(), criticality, incremental updates and the bridge agree
    // with check reports. Existing tighter Liberty/IO requirements are retained.
    for (auto mm : {MinMax::Min,MinMax::Max}) {
        for (int level=graph.max_level();level>=0;--level) for (const auto vid : graph.vertices_at_level(level)) {
            if (!graph.is_startpoint(vid)) for (const auto& target : graph.launch_labels(vid,mm)) {
                if (target.predecessor==UINT32_MAX || !std::isfinite(target.required)) continue;
                for (auto& previous : graph.launch_labels(target.predecessor,mm)) if (previous.key==target.predecessor_key) {
                    const float required=target.required-(target.arrival-previous.arrival);
                    if (mm==MinMax::Max ? required<previous.required : required>previous.required) previous.required=required;
                    break;
                }
            }
        }
        for (uint32_t vid=0;vid<graph.vertex_count();++vid) {
            const auto* worst=graph.worst_launch_label(vid,mm);
            if (!worst) continue;
            const auto rf=graph.vertex_transition(vid);
            const float slack=mm==MinMax::Max ? worst->required-worst->arrival : worst->arrival-worst->required;
            const float arrival=graph.arrival(vid,mm,rf).value;
            graph.set_required(vid,mm,rf,Required{arrival+(mm==MinMax::Max?slack:-slack)});
            if (graph.is_endpoint(vid)) {
                graph.set_endpoint_check_kind(vid,mm,worst->kind);
                graph.set_endpoint_cppr(vid,mm,worst->cppr);
            }
        }
    }
}
} // namespace te
