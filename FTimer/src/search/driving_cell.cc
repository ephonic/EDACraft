#include "arrival_propagator.hh"
#include "graph/timing_graph.hh"
#include "network/network.hh"
#include "liberty/core_liberty_utils.hh"
#include "dcalc/awe_dcalc.hh"
#include "dcalc/dmp_ceff.hh"
#include "dcalc/nldm_rc_waveform.hh"
#include "dcalc/receiver_cap_convergence.hh"
#include "dcalc/unified_dcalc.hh"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <stdexcept>

namespace te {
namespace ec = edacraft::core;
namespace {
bool flag(const char* name) {
    const auto* v = std::getenv(name);
    return v && (std::string(v) == "1" || std::string(v) == "true" ||
                 std::string(v) == "yes" || std::string(v) == "on");
}
}

void ArrivalPropagator::apply_driving_cells() {
    if (!sdc_ || sdc_->driving_cells().empty()) return;
    // Select the last definition independently for each transition/analysis.
    using Driver = ResolvedConstraintSet::DrivingCell;
    std::map<uint32_t, std::array<const Driver*, 4>> selected;
    for (const auto& driver : sdc_->driving_cells()) {
        for (auto pin : driver.ports) {
            if (pin.id >= network_.pin_count())
                throw std::runtime_error("set_driving_cell requires primary input ports");
            const auto& pd = network_.pin(pin);
            // The parsed netlist represents a top-level input as an output
            // of its synthetic __top__ instance. Gate views can also expose
            // an unowned input pin directly.
            const bool primary = valid(pd.instance)
                ? network_.cell_name(network_.instance(pd.instance).cell) == "__top__" &&
                    pd.direction != PortDirection::Input
                : pd.direction != PortDirection::Output;
            if (!primary) throw std::runtime_error("set_driving_cell requires a primary input: " + std::string(network_.pin_name(pin)));
            auto& entries = selected[pin.id];
            for (auto mm : {MinMax::Min, MinMax::Max})
                for (auto rf : {Transition::Rise, Transition::Fall}) {
                    const auto& d = driver.model;
                    if ((mm == MinMax::Min ? !d.min : !d.max) ||
                        (rf == Transition::Rise ? !d.rise : !d.fall)) continue;
                    auto& old = entries[mm_rf_index(mm, rf)];
                    if (!old || d.order >= old->model.order) old = &driver;
                }
        }
    }
    for (const auto& transition : sdc_->input_transitions())
        for (auto pin : transition.ports) {
            auto it = selected.find(pin.id);
            if (it == selected.end()) continue;
            for (auto mm : {MinMax::Min, MinMax::Max})
                for (auto rf : {Transition::Rise, Transition::Fall}) {
                    if ((mm == MinMax::Min ? !transition.min : !transition.max) ||
                        (rf == Transition::Rise ? !transition.rise : !transition.fall)) continue;
                    auto& entry = it->second[mm_rf_index(mm, rf)];
                    if (entry && transition.order > entry->model.order) entry = nullptr;
                }
        }

    for (const auto& [pid, entries] : selected) {
        const PinId pin{pid};
        const auto net = network_.pin(pin).net;
        if (!valid(net)) continue;
        const auto owner = rc_owner_[net.id];
        for (auto mm : {MinMax::Max, MinMax::Min})
            for (auto rf : {Transition::Rise, Transition::Fall}) {
                const unsigned index = mm_rf_index(mm, rf);
                if (!entries[index]) continue;
                const auto& model = entries[index]->model;
                const ec::LibertyLibrary* library = nullptr;
                const ec::LibertyCellData* cell = nullptr;
                for (uint32_t li = 0; li < liberty_.library_count(); ++li) {
                    const auto& candidate = liberty_.library(li);
                    if (!model.library.empty() && network_.str(candidate.name) != model.library) continue;
                    for (uint32_t ci = 0; ci < candidate.cells.size(); ++ci) {
                        const auto& c = candidate.cells[ci];
                        if (network_.str(c.name) == model.cell) {
                            if (cell) throw std::runtime_error("Ambiguous set_driving_cell library: " + model.cell);
                            library = &candidate; cell = &c;
                        }
                    }
                }
                if (!cell) throw std::runtime_error("Unknown set_driving_cell: " + model.cell);
                const auto& units = library->units;
                const float unit_ns = units.time_unit_seconds / 1e-9f;
                const float cap_unit = units.capacitance_unit_farads;
                const float port_cap_unit = liberty::pin_cap_unit(network_, liberty_, pin);
                const float source_threshold = rf == Transition::Rise ? units.output_threshold_rise : 1.f-units.output_threshold_fall;
                const float sink_threshold = rf == Transition::Rise ? units.input_threshold_rise : 1.f-units.input_threshold_fall;
                uint32_t output = UINT32_MAX;
                for (const auto& p : cell->pins)
                    if (p.direction == ec::PortDirection::Output &&
                        (model.pin.empty() || network_.str(p.name) == model.pin)) {
                        if (output != UINT32_MAX && model.pin.empty())
                            throw std::runtime_error("set_driving_cell requires -pin for multiple outputs: " + model.cell);
                        output = p.name;
                    }
                if (output == UINT32_MAX) throw std::runtime_error("Unknown set_driving_cell output pin: " + model.cell + "/" + model.pin);

                const bool late = mm == MinMax::Max;
                float best_delay = late ? -std::numeric_limits<float>::infinity() : std::numeric_limits<float>::infinity();
                float best_slew = best_delay;
                std::unordered_map<uint32_t, DelayResult> responses;
                bool found = false;
                for (const auto& arc : cell->arcs) {
                    if (arc.type != ec::LibertyTimingType::Combinational || arc.to_pin != output ||
                        (!model.from_pin.empty() && network_.str(arc.from_pin) != model.from_pin)) continue;
                    for (auto irf : {Transition::Rise, Transition::Fall}) {
                        if (arc.sense == ec::LibertyTimingSense::PositiveUnate && irf != rf) continue;
                        if (arc.sense == ec::LibertyTimingSense::NegativeUnate && irf == rf) continue;
                        const float input = (irf == Transition::Rise ? model.input_transition_rise_ns : model.input_transition_fall_ns) / unit_ns;
                        const auto& delay = rf == Transition::Rise ? arc.rise_delay : arc.fall_delay;
                        const auto& slew = rf == Transition::Rise ? arc.rise_output_slew : arc.fall_output_slew;
                        const auto& raw_current = rf == Transition::Rise ? arc.csm_output_current_rise : arc.csm_output_current_fall;
                        PiModel pi{0.f, 0.f, 0.f};
                        if (auto reduced = parasitics_.get_reduced(network_.net(NetId{owner}).driver, index)) pi = *reduced;
                        pi.c1 *= pi.cap_scale / cap_unit; pi.c2 *= pi.cap_scale / cap_unit; pi.cap_scale = cap_unit;
                        const float lumped = net_load_cap_[net.id][index] * port_cap_unit / cap_unit;
                        const float total = pi.c1 + pi.c2 + lumped;
                        const bool has_nldm = !delay.values.empty() && !slew.values.empty();
                        const bool use_csm = !raw_current.empty() && !flag("FSYN_TIMING_DISABLE_CSM") &&
                            (pi.rpi > 0.f || !has_nldm || flag("FSYN_TIMING_FORCE_CSM"));
                        std::optional<RcWaveformResult> full;
                        DelayResult result;
                        if (use_csm) {
                            auto current = raw_current;
                            const double scale = double(units.current)*1e-3*units.time_unit_seconds/cap_unit;
                            if (std::fabs(scale-1.) > 1e-6)
                                for (auto& wave : current.waveforms) for (auto& value : wave.current) value *= scale;
                            const auto* extraction = effective_rc(net);
                            if (extraction && !flag("FSYN_TIMING_DISABLE_RC_WAVEFORM")) {
                                FullRcNetwork loaded = *extraction;
                                float receiver_slew = has_nldm ? std::max(0.f, slew.lookup(input, total)) : input;
                                if (flag("FTIMER_CCS_ADAPTIVE_RUNTIME"))
                                    receiver_slew = liberty::receiver_initial_slew(receiver_slew, units.slew_lower, units.slew_upper, late);
                                const bool segmented = flag("FSYN_TIMING_USE_SEGMENTED_RECEIVER_CAP") || flag("FTIMER_CCS_ADAPTIVE_RUNTIME");
                                std::vector<RcReceiverCapacitance> regions;
                                load_rc_receivers(loaded, net, rf, receiver_slew, total,
                                    segmented ? &regions : nullptr, nullptr, unit_ns, late);
                                RcDelayThresholds thresholds;
                                RcSlewThresholds windows;
                                for (const auto& node : loaded.nodes) {
                                    if (node.id == loaded.driver_node_id || !valid(node.pin)) continue;
                                    const auto& pd = network_.pin(node.pin);
                                    if (!valid(pd.instance)) continue;
                                    const auto& c = network_.cell(network_.instance(pd.instance).cell);
                                    if (!valid(c.liberty_library)) continue;
                                    const auto& u = liberty_.library(c.liberty_library.id).units;
                                    const float rail = u.voltage / vdd_;
                                    thresholds[node.id] = rf == Transition::Rise ? rail*u.input_threshold_rise : 1.f-rail*u.input_threshold_fall;
                                    windows[node.id] = rf == Transition::Rise ? RcSlewWindow{rail*u.slew_lower,rail*u.slew_upper,u.slew_derate} :
                                        RcSlewWindow{1.f-rail*u.slew_upper,1.f-rail*u.slew_lower,u.slew_derate};
                                }
                                auto solve = [&](const FullRcNetwork& rc) {
                                    return RcWaveformCalc().calculate(csm_calc_, current, rc, input, vdd_, &delay,
                                        units.slew_lower, units.slew_upper, units.slew_derate,
                                        cap_unit, units.time_unit_seconds, source_threshold, sink_threshold,
                                        &regions, CcsSourceRepresentation::PrimeTimeCompressed, &thresholds, &windows);
                                };
                                full = solve(loaded);
                                if (full && !full->lumped_ccs_runtime &&
                                    !flag("FSYN_TIMING_DISABLE_DYNAMIC_RECEIVER_CAP") && full->driver.output_slew.value > 0.f) {
                                    expand_alias_responses(*full, net);
                                    const auto initial = std::move(regions); regions = {};
                                    FullRcNetwork refined = *extraction;
                                    load_rc_receivers(refined, net, rf, full->driver.output_slew.value, total,
                                        segmented ? &regions : nullptr, segmented ? &*full : nullptr, unit_ns, late);
                                    if (!full->adaptive_integration || receiver_caps_need_refinement(initial, regions, refined.cap_scale))
                                        if (auto value = solve(refined)) full = std::move(value);
                                }
                            }
                            auto csm_pi = pi;
                            csm_pi.rpi *= cap_unit*1e3f/units.time_unit_seconds;
                            result = full ? full->driver : UnifiedDelayCalc().calculate_csm_gate_arc(csm_calc_, current,
                                input, total, vdd_, csm_pi, -1.f, &delay, &slew, units.slew_lower,
                                units.slew_upper, 0.f, units.slew_derate);
                        }
                        if (!use_csm || !result.converged) {
                            if (!has_nldm) throw std::runtime_error("No usable set_driving_cell characterization: " + model.cell);
                            full.reset();
                            // An external cell drives the same extracted net
                            // as an internal output. Retain its receiver
                            // crossings instead of falling back to a lumped
                            // slew and a separate wire approximation.
                            const bool characterized=std::getenv("FTIMER_NLDM_CHARACTERIZED_RUNTIME")
                                ? flag("FTIMER_NLDM_CHARACTERIZED_RUNTIME") : flag("FTIMER_CCS_ADAPTIVE_RUNTIME");
                            if(const auto* extraction=effective_rc(net);
                               characterized && extraction && !flag("FSYN_TIMING_DISABLE_RC_WAVEFORM")) {
                                FullRcNetwork loaded=*extraction;
                                std::vector<double> precise_caps;
                                const double accumulated_cap=load_rc_receivers(loaded,
                                    net,rf,0.f,0.f,nullptr,nullptr,0.f,late,false,&precise_caps)*loaded.cap_scale/cap_unit;
                                FullRcNetwork nominal_rise=*extraction,nominal_fall=*extraction;
                                load_rc_receivers(nominal_rise,net,Transition::Rise,0.f,0.f,nullptr,nullptr,0.f,late);
                                load_rc_receivers(nominal_fall,net,Transition::Fall,0.f,0.f,nullptr,nullptr,0.f,late);
                                for(size_t i=0;i<nominal_rise.nodes.size();++i)
                                    nominal_rise.nodes[i].gnd_cap=.5f*(nominal_rise.nodes[i].gnd_cap+nominal_fall.nodes[i].gnd_cap);
                                RcDelayThresholds thresholds;RcSlewThresholds windows;
                                for(const auto& node:loaded.nodes) {
                                    if(node.id==loaded.driver_node_id || !valid(node.pin))continue;
                                    const auto& pd=network_.pin(node.pin);
                                    if(!valid(pd.instance))continue;
                                    const auto& sink_cell=network_.cell(network_.instance(pd.instance).cell);
                                    if(!valid(sink_cell.liberty_library))continue;
                                    const auto& u=liberty_.library(sink_cell.liberty_library.id).units;
                                    if(!(units.voltage>0.f && u.voltage>0.f))continue;
                                    const float rail=u.voltage/units.voltage;
                                    thresholds[node.id]=rf==Transition::Rise?rail*u.input_threshold_rise:1.f-rail*u.input_threshold_fall;
                                    windows[node.id]=rf==Transition::Rise?RcSlewWindow{rail*u.slew_lower,rail*u.slew_upper,u.slew_derate}:RcSlewWindow{1.f-rail*u.slew_upper,1.f-rail*u.slew_lower,u.slew_derate};
                                }
                                double receiver_pin_cap=-1.;
                                if(loaded.nodes.size()==extraction->nodes.size() &&
                                   network_.net(net).loads.size()+1==loaded.nodes.size() && !parasitics_.includes_pin_caps(net) &&
                                   alias_pin_nodes_.find(owner)==alias_pin_nodes_.end()) {
                                    double wire=0.;
                                    for(const auto& node:extraction->nodes)wire+=double(node.gnd_cap);
                                    receiver_pin_cap=accumulated_cap-wire*loaded.cap_scale/cap_unit;
                                }
                                full=NldmRcWaveformCalc().calculate(loaded,pi,input,delay,slew,
                                    units.slew_lower,units.slew_upper,units.slew_derate,
                                    source_threshold,sink_threshold,cap_unit,units.time_unit_seconds,
                                    &thresholds,&windows,true,!late,receiver_pin_cap,accumulated_cap,extraction,&nominal_rise,&precise_caps);
                            }
                            if(full)result=full->driver;
                            else {
                            float ceff = total;
                            if (pi.rpi > 0.f && pi.c1 > 0.f) {
                                auto native_pi = pi; native_pi.c2 += lumped;
                                native_pi.rpi *= cap_unit*1e3f/units.time_unit_seconds;
                                ceff = DmpCeffCalc().compute(native_pi, input, delay, slew).ceff;
                            }
                            result = UnifiedDelayCalc().calculate_nldm_gate_arc(delay, slew, input, ceff);
                            full.reset();
                            }
                        }
                        if (!result.converged || !std::isfinite(result.delay.value) || !std::isfinite(result.output_slew.value))
                            throw std::runtime_error("set_driving_cell solve failed: " + model.cell);
                        // Input delay is specified at the port with no internal
                        // load. Only the external cell's load-dependent delay
                        // is added; its intrinsic delay must not be counted twice.
                        const float intrinsic = delay.values.empty() ? 0.f : lookup_nldm(delay,input,0.f);
                        const float load_delay = (result.delay.value-intrinsic)*unit_ns;
                        const float output_slew = result.output_slew.value*unit_ns;
                        if (!found || (late ? load_delay > best_delay : load_delay < best_delay)) best_delay = load_delay;
                        if (!found || (late ? output_slew > best_slew : output_slew < best_slew)) {
                            best_slew = output_slew;
                            responses.clear();
                            if (full) {
                                expand_alias_responses(*full, net);
                                responses = full->loads;
                                for (auto& [sink, response] : responses) {
                                    response.delay.value *= unit_ns;
                                    response.output_slew.value *= unit_ns;
                                }
                            }
                        }
                        found = true;
                    }
                }
                if (!found) throw std::runtime_error("No combinational set_driving_cell arc: " + model.cell);
                const uint32_t vid = pid*2+unsigned(rf);
                auto arrival = graph_.arrival(vid, mm, rf);
                arrival.value += best_delay;
                graph_.set_arrival(vid, mm, rf, arrival);
                graph_.set_slew(vid, mm, rf, Slew{best_slew});
                net_waveforms_[owner][index] = std::move(responses);
            }
    }
}
} // namespace te
