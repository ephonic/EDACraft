#include "dcalc/coupled_rc_solver.hh"
#include "dcalc/connected_ccsn_solver.hh"
#include "liberty/ccsn_stage_builder.hh"
#include "dcalc/si_waveform_basis.hh"
#include "dcalc/nldm_dcalc.hh"
#include "dcalc/awe_dcalc.hh"
#include "graph/timing_graph.hh"
#include "network/network.hh"
#include "engine_impl.hh"
#include <map>
#include <set>
#include <stdexcept>

namespace te {

TimingEngine::SiLibraryStage TimingEngine::read_si_ccsn_stage(std::string_view owner_name,
    std::string_view related_pin,bool first_stage,bool output_rise,
    const std::vector<std::pair<std::string,int>>& fixed_state) const {
    const auto pin=find_pin(owner_name);
    if(!pin)throw std::runtime_error("CCSN owner pin not found");
    const auto& network=*impl_->network;const auto& pd=network.pin(*pin);
    if(!valid(pd.instance))throw std::runtime_error("CCSN owner must be a cell pin");
    const auto& cell=network.cell(network.instance(pd.instance).cell);
    if(!valid(cell.liberty_library) || !valid(cell.liberty_cell))
        throw std::runtime_error("CCSN owner has no linked library cell");
    const auto& lib=impl_->liberty->library(cell.liberty_library.id);
    const auto& lc=lib.cells[cell.liberty_cell.id];
    std::map<std::string,int> state;
    for(const auto& item:fixed_state) {
        bool known=false;for(const auto& lp:lc.pins)known|=network.str(lp.name)==item.first;
        if(!known || (item.second!=0 && item.second!=1) || !state.emplace(item).second)
            throw std::runtime_error("Invalid or duplicate CCSN fixed input state");
    }
    auto lookup=[&](std::string_view name)->std::optional<int> {
        const auto it=state.find(std::string(name));
        return it==state.end()?std::nullopt:std::optional<int>(it->second);
    };
    using Builder=CcsnStageBuilder;
    const auto stage_name=first_stage?"ccsn_first_stage":"ccsn_last_stage";
    const Builder::Node* selected=nullptr;size_t equivalents=0;
    auto consider=[&](const auto& nodes,std::string_view when) {
        const auto s=Builder::select(nodes,stage_name,when,lookup);
        if(!s.stage)return;
        if(s.disabled)throw std::runtime_error("Selected CCSN stage is explicitly disabled");
        if(selected && !Builder::same(*selected,*s.stage,true))
            throw std::runtime_error("Ambiguous condition-selected CCSN timing models");
        selected=s.stage;equivalents+=s.equivalent_indices.size();
    };
    if(related_pin.empty()) {
        bool found=false;
        for(const auto& lp:lc.pins)if(network.str(lp.name)==network.pin_name(*pin)) {
            consider(lp.ccsn_stages,"");found=true;
        }
        if(!found)throw std::runtime_error("Linked CCSN pin not found");
    } else {
        for(const auto& arc:lc.arcs)if(network.str(arc.to_pin)==network.pin_name(*pin) &&
            network.str(arc.from_pin)==related_pin)
            consider(arc.ccsn_stages,arc.when==UINT32_MAX?std::string_view{}:network.str(arc.when));
    }
    if(!selected)throw std::runtime_error("No active CCSN stage for selected owner/state");
    const auto built=Builder::build(*selected,lib.ccsn_templates,lib.units,output_rise);
    SiLibraryStage out;out.stage_type=built.stage_type;out.inverting=built.inverting;
    out.equivalent_conditions=uint32_t(equivalents);
    out.model.provenance=std::string(owner_name)+":"+std::string(related_pin)+":"+stage_name;
    out.model.input_voltage_v=built.table.input_voltage;
    out.model.output_voltage_v=built.table.output_voltage;
    out.model.current_ma=built.table.current_ma;out.model.miller_pf=built.table.miller_pf;
    for(const auto& w:built.waveforms)out.characterization.push_back({w.kind,w.input_transition_ns,
        w.noise_height_v,w.noise_width_ns,w.load_pf,w.time_ns,w.output_v});
    return out;
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options) const {
    return solve_si_waveforms(victim_name,aggressors,options,SiStaticIv{});
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
    const SiStaticIv& victim_iv) const {
    return solve_si_waveforms(victim_name,aggressors,options,victim_iv,{});
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
    const SiStaticIv& victim_iv, const std::vector<std::string>& ideal_port_aggressors) const {
    return solve_si_waveforms(victim_name,aggressors,options,victim_iv,ideal_port_aggressors,{});
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
    const SiStaticIv& victim_iv, const std::vector<std::string>& ideal_port_aggressors,
    const std::vector<SiNortonSource>& characterized_sources) const {
    return solve_si_waveforms(victim_name,aggressors,options,victim_iv,ideal_port_aggressors,
        characterized_sources,SiExperimentalStage{});
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors, const SiWaveformOptions& options,
    const SiStaticIv& supplied_iv, const std::vector<std::string>& ideal_port_aggressors,
    const std::vector<SiNortonSource>& characterized_sources,
    const SiExperimentalStage& victim_stage) const {
    return solve_si_waveforms(victim_name,aggressors,options,supplied_iv,ideal_port_aggressors,
        characterized_sources,victim_stage,{});
}

TimingEngine::SiWaveformResult TimingEngine::solve_si_waveforms(std::string_view victim_name,
    const std::vector<SiAggressor>& aggressors,const SiWaveformOptions& options,
    const SiStaticIv& supplied_iv,const std::vector<std::string>& ideal_port_aggressors,
    const std::vector<SiNortonSource>& characterized_sources,
    const SiExperimentalStage& victim_stage,const std::vector<SiReceiverStage>& receivers) const {
    const bool dynamic_stage=!victim_stage.time_ns.empty();
    const bool connected_stage=!receivers.empty() || !victim_stage.output_cap_profile.empty();
    if(connected_stage && (!dynamic_stage || !characterized_sources.empty()))
        throw std::runtime_error("Connected stages/charge require an explicit victim stage and no Norton sources");
    CoupledRcSolver::DynamicStage stage{0,victim_stage.input_voltage_v,victim_stage.output_voltage_v,
        victim_stage.current_ma,victim_stage.time_ns,victim_stage.input_v,
        victim_stage.miller_pf,victim_stage.output_pf,victim_stage.tau_ns,victim_stage.lag_output_feedback};
    SiStaticIv victim_iv=supplied_iv;
    if(dynamic_stage) {
        if(victim_stage.provenance.empty() || !options.quiet_victim || options.respect_timing_windows ||
            options.victim_resistance_ohm!=0 || !supplied_iv.voltage_v.empty() ||
            !supplied_iv.current_ma.empty() || !supplied_iv.output_charge_pc.empty())
            throw std::runtime_error("SI experimental stage requires provenance, quiet victim and explicit alignment without I-V/R overrides");
        victim_iv.voltage_v=stage.output_voltage;
        victim_iv.current_ma=CoupledRcSolver::stage_slice(stage,
            CoupledRcSolver::stage_input(stage,stage.time.front()));
    } else if(!victim_stage.provenance.empty() || !victim_stage.input_voltage_v.empty() ||
        !victim_stage.output_voltage_v.empty() || !victim_stage.current_ma.empty() ||
        !victim_stage.input_v.empty() || victim_stage.miller_pf!=0 ||
        victim_stage.output_pf!=0 || victim_stage.tau_ns!=0 || victim_stage.lag_output_feedback ||
        !victim_stage.output_cap_profile.empty())
        throw std::runtime_error("SI experimental stage missing prescribed input window");
    const auto victim = find_net(victim_name);
    if (!victim || !impl_->graph) throw std::runtime_error("SI victim net not found");
    if (!std::isfinite(options.victim_resistance_ohm)) throw std::runtime_error("Invalid SI victim resistance");
    const bool static_iv=!victim_iv.voltage_v.empty() || !victim_iv.current_ma.empty() ||
        !victim_iv.output_charge_pc.empty();
    if (static_iv && (!options.quiet_victim || options.victim_resistance_ohm>0))
        throw std::runtime_error("SI static I-V requires a quiet victim without a resistance override");
    if (static_iv && (victim_iv.voltage_v.size()<2 ||
        victim_iv.voltage_v.size()!=victim_iv.current_ma.size()))
        throw std::runtime_error("Invalid SI victim I-V dimensions");
    if (!victim_iv.output_charge_pc.empty() &&
        victim_iv.output_charge_pc.size()!=victim_iv.voltage_v.size())
        throw std::runtime_error("Invalid SI victim output charge dimensions");
    for (size_t k=0;static_iv && k<victim_iv.voltage_v.size();++k) {
        const auto& x=victim_iv.voltage_v;const auto& y=victim_iv.current_ma;
        if (!std::isfinite(x[k]) || !std::isfinite(y[k]) ||
            (k && (!(x[k]>x[k-1]) || y[k]>y[k-1])))
            throw std::runtime_error("SI victim I-V must be finite, ordered and passive");
        const auto& q=victim_iv.output_charge_pc;
        if (!q.empty() && (!std::isfinite(q[k]) || (k && q[k]<q[k-1])))
            throw std::runtime_error("SI victim output charge must be finite and nondecreasing");
    }
    const auto& network = *impl_->network;
    const auto& graph = *impl_->graph;
    const auto records = impl_->parasitics->node_couplings();
    std::map<uint32_t,const SiReceiverStage*> receiver_outputs;
    std::map<uint32_t,PinId> receiver_inputs;
    std::set<uint32_t> replaced_pin_caps;
    for(const auto& receiver:receivers) {
        const auto input=find_pin(receiver.input_pin);
        const auto output=find_net(receiver.output_net);
        if(!input || !output || output==victim || receiver.model.provenance.empty() ||
            !receiver.model.time_ns.empty() || !receiver.model.input_v.empty() ||
            !std::isfinite(receiver.initial_output_v) || !std::isfinite(receiver.input_pf) || receiver.input_pf<0 ||
            !receiver_outputs.emplace(output->id,&receiver).second ||
            !replaced_pin_caps.insert(input->id).second)
            throw std::runtime_error("Invalid or duplicate connected receiver binding");
        const auto& in=network.pin(*input);const auto driver=network.net(*output).driver;
        if(!valid(in.net) || !valid(in.instance) || !valid(driver) ||
            in.instance!=network.pin(driver).instance || in.direction!=PortDirection::Input)
            throw std::runtime_error("Receiver input/output must belong to the same cell");
        if(impl_->parasitics->includes_pin_caps(in.net))
            throw std::runtime_error("Connected receiver needs SPEF without included input pin capacitance");
        receiver_inputs.emplace(output->id,*input);
    }
    std::set<uint32_t> component{victim->id};
    bool changed = true;
    while (changed) {
        changed = false;
        for (const auto& cap : records) if (component.count(cap.net1.id) || component.count(cap.net2.id)) {
            changed |= component.insert(cap.net1.id).second;
            changed |= component.insert(cap.net2.id).second;
        }
        for(const auto& item:receiver_inputs)
            if(component.count(network.pin(item.second).net.id))changed|=component.insert(item.first).second;
    }
    for(const auto& item:receiver_outputs)if(!component.count(item.first))
        throw std::runtime_error("Connected receiver is unreachable from the victim component");
    std::map<uint32_t, const SiAggressor*> switching;
    for (const auto& aggr : aggressors) {
        if (!std::isfinite(aggr.offset_ns) || !std::isfinite(aggr.driver_resistance_ohm))
            throw std::runtime_error("Invalid SI aggressor offset/resistance");
        const auto net = find_net(aggr.net);
        if (!net || net == victim || !component.count(net->id) || receiver_outputs.count(net->id))
            throw std::runtime_error("SI aggressor is not in the victim coupling component: " + aggr.net);
        if (!switching.emplace(net->id,&aggr).second) throw std::runtime_error("Duplicate SI aggressor");
    }
    std::set<uint32_t> ideal_ports;
    for(const auto& name:ideal_port_aggressors) {
        const auto net=find_net(name);
        if(!net || !switching.count(net->id) || !ideal_ports.insert(net->id).second)
            throw std::runtime_error("SI ideal port must select a unique aggressor");
        const auto driver=impl_->network->net(*net).driver;
        if(!valid(driver) || (valid(impl_->network->pin(driver).instance) &&
            impl_->network->cell_name(impl_->network->instance(impl_->network->pin(driver).instance).cell)!="__top__"))
            throw std::runtime_error("SI ideal source must be a primary-port driver");
        if(switching.at(net->id)->driver_resistance_ohm>0)
            throw std::runtime_error("SI ideal port conflicts with a resistance override");
    }
    if (!characterized_sources.empty() && options.respect_timing_windows)
        throw std::runtime_error("SI characterized sources require explicit time alignment");
    std::map<uint32_t,const SiNortonSource*> characterized;
    size_t source_samples=0;
    for (const auto& source:characterized_sources) {
        const auto net=find_net(source.net);
        if (!net || !switching.count(net->id) || ideal_ports.count(net->id) ||
            !characterized.emplace(net->id,&source).second)
            throw std::runtime_error("SI characterized source must select a unique non-ideal aggressor");
        const auto& aggr=*switching.at(net->id);
        if (aggr.offset_ns!=0 || aggr.driver_resistance_ohm!=0)
            throw std::runtime_error("SI characterized source conflicts with offset/resistance override");
        const auto m=source.time_ns.size();
        if (m<2 || m!=source.injection_ma.size() || m!=source.conductance_ma_per_v.size() ||
            m>8000000-source_samples)
            throw std::runtime_error("Invalid SI characterized source dimensions/budget");
        source_samples+=m;
        for (size_t k=0;k<m;++k)
            if (!std::isfinite(source.time_ns[k]) || !std::isfinite(source.injection_ma[k]) ||
                !std::isfinite(source.conductance_ma_per_v[k]) || source.conductance_ma_per_v[k]<0 ||
                (k && !(source.time_ns[k]>source.time_ns[k-1])))
                throw std::runtime_error("SI characterized source must be finite, ordered and passive");
        const auto& first=characterized_sources.front();
        if (source.time_ns.front()!=first.time_ns.front() || source.time_ns.back()!=first.time_ns.back())
            throw std::runtime_error("SI characterized sources must share their analysis window");
    }
    using Solver = CoupledRcSolver;
    std::vector<Solver::Resistor> resistors;
    std::vector<Solver::Capacitor> capacitors;
    std::vector<Solver::Driver> active, baseline;
    std::vector<Solver::NortonSource> active_sources, baseline_sources;
    std::map<uint32_t,size_t> offsets;
    std::map<uint32_t,const FullRcNetwork*> networks;
    size_t n = 0;
    for (const auto net_id : component) {
        const auto* rc = impl_->parasitics->get_network(NetId{net_id});
        if (!rc || rc->driver_node_id >= rc->nodes.size())
            throw std::runtime_error("SI needs an extracted RC network and resolved driver for every coupled net");
        offsets[net_id] = n; networks[net_id] = rc; n += rc->nodes.size();
    }
    if (n > 512) throw std::runtime_error("SI component exceeds the 512-node solver limit");
    std::vector<double> initial(n,0);
    float vdd = impl_->voltage;
    if (impl_->liberty->library_count()) vdd = impl_->liberty->library(0).units.voltage;
    const auto victim_driver = network.net(*victim).driver;
    if (!valid(victim_driver)) throw std::runtime_error("SI victim has no driver");
    const edacraft::core::LibertyLibrary::Units defaults;
    auto units_for = [&](PinId pin) -> const edacraft::core::LibertyLibrary::Units& {
        if (valid(pin) && valid(network.pin(pin).instance)) {
            const auto& cell=network.cell(network.instance(network.pin(pin).instance).cell);
            if (valid(cell.liberty_library))return impl_->liberty->library(cell.liberty_library.id).units;
        }
        // Primary ports use the main library's thresholds/derate too.
        return impl_->liberty->library_count()?impl_->liberty->library(0).units:defaults;
    };
    auto basis_for = [&](PinId pin,bool output,bool rise) {
        const auto& u=units_for(pin);
        SiWaveformBasis basis{u.slew_lower,u.slew_upper,u.slew_derate,
            output?(rise?u.output_threshold_rise:u.output_threshold_fall):
                   (rise?u.input_threshold_rise:u.input_threshold_fall)};
        basis.validate();return basis;
    };
    auto cell_driver = [&](PinId pin) {
        return valid(network.pin(pin).instance) &&
            valid(network.cell(network.instance(network.pin(pin).instance).cell).liberty_library);
    };
    auto fixed_port_waveform = [&](PinId pin, bool rise, MinMax mm) {
        const auto& pd=network.pin(pin);
        const bool primary=valid(pd.instance)
            ? network.cell_name(network.instance(pd.instance).cell)=="__top__" &&
                pd.direction!=PortDirection::Input
            : pd.direction!=PortDirection::Output;
        if (!primary || !impl_->sdc) return false;
        const ResolvedInputTransition* fixed=nullptr;
        uint64_t cell_order=0;
        bool has_cell=false;
        auto applies=[&](const auto& m) {
            return (rise?m.rise:m.fall) && (mm==MinMax::Min?m.min:m.max);
        };
        for (const auto& t:impl_->sdc->input_transitions())
            if (applies(t) && std::find(t.ports.begin(),t.ports.end(),pin)!=t.ports.end() &&
                (!fixed || t.order>=fixed->order)) fixed=&t;
        for (const auto& d:impl_->sdc->driving_cells())
            if (applies(d.model) && std::find(d.ports.begin(),d.ports.end(),pin)!=d.ports.end()) {
                has_cell=true;cell_order=std::max(cell_order,d.model.order);
            }
        // set_input_transition prescribes the waveform at the port, independent
        // of its load. Inferring an extra source R from that same slew would
        // filter the prescribed waveform a second time. Keep driving-cell
        // precedence independently for each transition and analysis envelope.
        return fixed && (!has_cell || fixed->order>cell_order);
    };
    const auto vrf = options.victim_rise ? Transition::Rise : Transition::Fall;
    const float timing_mid = get_arrival(victim_driver, vrf, MinMax::Max);
    const float timing_early = get_arrival(victim_driver, vrf, MinMax::Min);
    const float timing_slew = get_slew(victim_driver, vrf, MinMax::Max);
    const bool victim_has_timing = std::isfinite(timing_mid) && std::isfinite(timing_early) &&
        std::isfinite(timing_slew) && timing_slew > 0;
    // Case analysis removes switching timing, not the quiet net's physical
    // response to coupling. With an explicit quiet model no switching slew
    // is needed. Use a time origin only; do not invent a slew to infer R.
    const bool quiet_without_timing = options.quiet_victim && !victim_has_timing &&
        (static_iv || options.victim_resistance_ohm > 0);
    if (!victim_has_timing && !quiet_without_timing)
        throw std::runtime_error("SI victim timing window/slew is invalid; update timing first");
    const float victim_mid = quiet_without_timing ? 0.f : timing_mid;
    const float victim_early = quiet_without_timing ? 0.f : timing_early;
    const float victim_slew = quiet_without_timing ? 0.f : timing_slew;
    const auto victim_basis=basis_for(victim_driver,cell_driver(victim_driver),options.victim_rise);
    const double victim_ramp=victim_basis.ramp(victim_slew);
    double begin = INFINITY, end = -INFINITY, settle = 0;
    SiWaveformResult result; result.victim_net = std::string(victim_name);
    bool used_ideal_port=!ideal_ports.empty();
    if (static_iv) result.model="static_victim_iv_thevenin_aggressors";
    for (const auto net_id : component) {
        const auto& rc = *networks.at(net_id);
        const auto offset = offsets.at(net_id);
        const auto driver = network.net(NetId{net_id}).driver;
        if (!valid(driver)) throw std::runtime_error("SI coupled net has no logical driver");
        const bool is_victim = net_id == victim->id;
        const bool receiver_output=receiver_outputs.count(net_id)!=0;
        const auto aggr = switching.find(net_id);
        const auto characterized_it=characterized.find(net_id);
        const bool norton=characterized_it!=characterized.end();
        const bool rise = is_victim ? options.victim_rise : aggr == switching.end() ? true : aggr->second->rise;
        const auto rf = rise ? Transition::Rise : Transition::Fall;
        const bool fixed_quiet = (is_victim && quiet_without_timing) || receiver_output;
        const float early = fixed_quiet ? victim_early : get_arrival(driver, rf, MinMax::Min);
        const float late = fixed_quiet ? victim_mid : get_arrival(driver, rf, MinMax::Max);
        float slew = fixed_quiet ? 0.f : get_slew(driver, rf, MinMax::Max);
        MinMax source_envelope=MinMax::Max;
        if (!is_victim && aggr != switching.end() && options.quiet_victim) {
            // Static noise must retain the fast switching envelope. The
            // slow STA envelope can come from another input/conditional arc
            // and suppress the worst bump even when that arc arrives last.
            // This remains the explicit linear-Thevenin approximation; a
            // characterized CCSN solve must retain individual source arcs.
            const float fast_slew = get_slew(driver, rf, MinMax::Min);
            if (std::isfinite(fast_slew) && fast_slew > 0) {
                if (!(slew>0) || fast_slew<=slew) source_envelope=MinMax::Min;
                slew = slew > 0 ? std::min(slew,fast_slew) : fast_slew;
            }
        }
        if (!std::isfinite(early) || !std::isfinite(late) || (!fixed_quiet && !(slew > 0)))
            throw std::runtime_error("SI coupled driver timing is invalid");
        float unit = 1e-12f;
        const auto& pd = network.pin(driver);
        if (valid(pd.instance)) {
            const auto& cell = network.cell(network.instance(pd.instance).cell);
            if (valid(cell.liberty_library)) {
                const auto& u = impl_->liberty->library(cell.liberty_library.id).units;
                unit = u.capacitance_unit_farads;
            }
        }
        const auto basis=basis_for(driver,cell_driver(driver),rise);
        const double ramp=basis.ramp(slew);
        float resistance = is_victim ? options.victim_resistance_ohm : aggr == switching.end() ? 0 : aggr->second->driver_resistance_ohm;
        if(receiver_output)resistance=1.; // horizon placeholder; removed before connected MNA
        const bool ideal_port=!norton && (ideal_ports.count(net_id)!=0 ||
            ((is_victim ? !options.quiet_victim : aggr!=switching.end()) && !(resistance>0) &&
             fixed_port_waveform(driver,rise,source_envelope)));
        used_ideal_port |= ideal_port;
        if (ideal_port) resistance=0;
        if (!(resistance > 0) && !ideal_port && !(fixed_quiet && static_iv) && !norton) {
            // Step-response surrogate in the library's physical threshold
            // interval. This is not a characterized quiet-state IV model or
            // a de-embedded switching source. Explicit overrides are needed
            // for controlled physical RC comparisons.
            const double load_pf = get_net_load_cap(NetId{net_id})*unit/1e-12;
            resistance = load_pf > 0 ? float(basis.resistance(slew,load_pf,rise)) : 1.f;
        }
        if (is_victim && static_iv) {
            // Use the characterized rail slope only to estimate a settling
            // horizon. The actual solve uses the full table, never this R.
            const auto& x=victim_iv.voltage_v;
            const auto& y=victim_iv.current_ma;
            const double rail=rise?0.:vdd;
            auto k=std::upper_bound(x.begin(),x.end(),rail)-x.begin();
            k=std::min(std::max(k,decltype(k)(1)),decltype(k)(x.size()-1))-1;
            const double slope=(y[k+1]-y[k])/(x[k+1]-x[k]);
            if (std::isfinite(slope) && slope<0) resistance=float(-1000./slope);
        }
        if (!std::isfinite(resistance) || (!ideal_port && !norton && !(resistance > 0))) throw std::runtime_error("Invalid SI driver resistance");
        bool enabled = is_victim ? !options.quiet_victim : aggr != switching.end();
        double center = is_victim ? victim_mid : aggr == switching.end() ? victim_mid : victim_mid+aggr->second->offset_ns;
        if (!is_victim && enabled && options.respect_timing_windows) {
            // A quiet victim has no switching window to overlap. Retain
            // the aggressor's own timing window for the noise waveform.
            if (!options.quiet_victim) {
                const double vl = std::min(victim_early,victim_mid)-victim_basis.progress(options.victim_rise)*victim_ramp;
                const double vh = std::max(victim_early,victim_mid)+(1.-victim_basis.progress(options.victim_rise))*victim_ramp;
                enabled = std::min(early,late)-basis.progress(rise)*ramp <= vh &&
                    std::max(early,late)+(1.-basis.progress(rise))*ramp >= vl;
            }
            center = std::clamp(center,double(std::min(early,late)),double(std::max(early,late)));
        }
        // Driver::center is its 50% point; the STA arrival can use another
        // library threshold. Falling transitions use progress from Vdd.
        center += (.5-basis.progress(rise))*ramp;
        if (!is_victim && enabled) ++result.active_aggressors;
        const double low = receiver_output?receiver_outputs.at(net_id)->initial_output_v:(rise ? 0. : vdd);
        const double high = rise ? vdd : 0.;
        Solver::Driver d{offset+rc.driver_node_id,resistance,low,enabled ? high : low,center,ramp};
        if (norton) {
            const auto& source=*characterized_it->second;
            Solver::NortonSource law{d.node,source.time_ns,source.injection_ma,source.conductance_ma_per_v};
            active_sources.push_back(law);
            // Removing the switching injection alone would pull a high-rail
            // source to ground. Hold its initial rail with the SAME g(t).
            for (size_t k=0;k<law.time.size();++k) law.injection_ma[k]=law.conductance_ma_per_v[k]*low;
            baseline_sources.push_back(std::move(law));
        } else {
            active.push_back(d);
            if (!is_victim) d.final = d.initial;
            baseline.push_back(d);
        }
        begin = std::min(begin,center-ramp*.5); end = std::max(end,center+ramp*.5);
        double total_pf = 0, total_r = resistance;
        for (size_t i=0;i<rc.nodes.size();++i) {
            initial[offset+i] = low;
            double cap = rc.nodes[i].gnd_cap*rc.cap_scale/1e-12;
            const auto pin = rc.nodes[i].pin;
            if (valid(pin) && pin != driver && !replaced_pin_caps.count(pin.id) &&
                !impl_->parasitics->includes_pin_caps(NetId{net_id})) {
                const auto& receiver = network.pin(pin);
                float pin_unit = unit;
                if (valid(receiver.instance)) {
                    const auto& cell = network.cell(network.instance(receiver.instance).cell);
                    if (valid(cell.liberty_library)) pin_unit = impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
                }
                cap += std::max(0.f,receiver.load_cap)*pin_unit/1e-12;
            }
            capacitors.push_back({offset+i,SIZE_MAX,cap}); total_pf += cap;
        }
        for (const auto& r : rc.resistors) {
            if (r.node1 >= rc.nodes.size() || r.node2 >= rc.nodes.size()) throw std::runtime_error("Invalid SI resistor endpoint");
            resistors.push_back({offset+r.node1,offset+r.node2,std::max(1e-6,double(r.resistance*rc.res_scale))});
            total_r += r.resistance*rc.res_scale;
        }
        for (const auto& cap : rc.capacitors) if (cap.node2!=UINT32_MAX) {
            if (cap.node1>=rc.nodes.size() || cap.node2>=rc.nodes.size()) throw std::runtime_error("Invalid SI capacitor endpoint");
            const double pf=cap.capacitance*rc.cap_scale/1e-12;
            capacitors.push_back({offset+cap.node1,offset+cap.node2,pf});
            total_pf+=pf;
        }
        total_pf += impl_->parasitics->total_coupling_cap(NetId{net_id});
        if (is_victim && !victim_iv.output_charge_pc.empty()) {
            double intrinsic_pf=0;
            for (size_t k=1;k<victim_iv.voltage_v.size();++k)
                intrinsic_pf=std::max(intrinsic_pf,
                    (victim_iv.output_charge_pc[k]-victim_iv.output_charge_pc[k-1])/
                    (victim_iv.voltage_v[k]-victim_iv.voltage_v[k-1]));
            if (!std::isfinite(intrinsic_pf)) throw std::runtime_error("Invalid SI output capacitance");
            total_pf+=intrinsic_pf;
        }
        settle = std::max(settle,10.*total_r*total_pf/1000.);
    }
    if (used_ideal_port) result.model+="_with_ideal_ports";
    if (!active_sources.empty()) result.model+="_with_characterized_norton";
    if (!victim_iv.output_charge_pc.empty()) result.model+="_with_output_charge";
    for (const auto& cap : records) if (component.count(cap.net1.id) && component.count(cap.net2.id)) {
        if (cap.node1 >= networks.at(cap.net1.id)->nodes.size() || cap.node2 >= networks.at(cap.net2.id)->nodes.size())
            throw std::runtime_error("Unresolved physical SI coupling endpoint");
        capacitors.push_back({offsets.at(cap.net1.id)+cap.node1,offsets.at(cap.net2.id)+cap.node2,cap.cap_pf});
    }
    begin -= std::max(.01,settle*.1); end += std::max(.1,settle);
    if (!characterized_sources.empty()) {
        // Characterization defines the whole solve interval. Do not invent
        // a source tail by extrapolating its first/last current or feedback.
        begin=characterized_sources.front().time_ns.front();
        end=characterized_sources.front().time_ns.back();
        for (const auto& d:active) if (d.initial!=d.final &&
            (d.center-d.ramp*.5<begin || d.center+d.ramp*.5>end))
            throw std::runtime_error("SI characterized window truncates another aggressor transition");
    }
    if(dynamic_stage) {
        if(!characterized_sources.empty() &&
            (begin!=stage.time.front() || end!=stage.time.back()))
            throw std::runtime_error("SI stage and characterized sources require the same complete window");
        begin=stage.time.front();end=stage.time.back();
        for(const auto& d:active) if(d.initial!=d.final &&
            (d.center-d.ramp*.5<begin || d.center+d.ramp*.5>end))
            throw std::runtime_error("SI stage window truncates an aggressor transition");
        stage.node=offsets.at(victim->id)+networks.at(victim->id)->driver_node_id;
        result.model="experimental_prescribed_input_ccsn_dc_miller";
        if(stage.tau_ns>0) result.model+=stage.lag_output_feedback?"_current_lag":"_input_excitation_lag";
        if(used_ideal_port) result.model+="_with_ideal_ports";
        if(!active_sources.empty()) result.model+="_with_characterized_norton";
    }
    Solver::StaticDriver quiet_iv{offsets.at(victim->id)+networks.at(victim->id)->driver_node_id,
        victim_iv.voltage_v,victim_iv.current_ma,victim_iv.output_charge_pc};
    auto baseline_stage=stage;
    if(dynamic_stage) std::fill(baseline_stage.input_v.begin(),baseline_stage.input_v.end(),stage.input_v.front());
    Solver::Result base,wave;
    if(!connected_stage) {
        const auto shared_grid=Solver::source_grid(active_sources,dynamic_stage?&stage:nullptr);
        base=Solver::solve(n,resistors,capacitors,baseline,initial,begin,end,options.step_ns,options.max_steps,
            static_iv && !dynamic_stage?&quiet_iv:nullptr,baseline_sources,dynamic_stage?&baseline_stage:nullptr,&shared_grid);
        wave=Solver::solve(n,resistors,capacitors,active,initial,begin,end,options.step_ns,options.max_steps,
            static_iv && !dynamic_stage?&quiet_iv:nullptr,active_sources,dynamic_stage?&stage:nullptr,&shared_grid);
        if(base.time!=wave.time)throw std::runtime_error("SI active/baseline event grid mismatch");
    } else {
        using Connected=ConnectedCcsnSolver;
        const size_t input_node=n;auto connected_initial=initial;connected_initial.push_back(stage.input_v.front());
        std::vector<Connected::Stage> stages{{input_node,stage.node,stage,0.,victim_stage.output_cap_profile}};
        for(const auto& item:receiver_outputs) {
            const auto& receiver=*item.second;
            const auto input=receiver_inputs.at(item.first);const auto input_net=network.pin(input).net;
            const auto& rc=*networks.at(input_net.id);size_t found=SIZE_MAX;
            for(size_t k=0;k<rc.nodes.size();++k)if(rc.nodes[k].pin==input) {
                if(found!=SIZE_MAX)throw std::runtime_error("Ambiguous physical receiver input node");found=k;
            }
            if(found==SIZE_MAX)throw std::runtime_error("Receiver input pin is not resolved in SPEF");
            const auto& model=receiver.model;
            Solver::DynamicStage table{0,model.input_voltage_v,model.output_voltage_v,model.current_ma,{}, {},
                model.miller_pf,model.output_pf,model.tau_ns,model.lag_output_feedback};
            stages.push_back({offsets.at(input_net.id)+found,
                offsets.at(item.first)+networks.at(item.first)->driver_node_id,std::move(table),receiver.input_pf,model.output_cap_profile});
        }
        auto boundaries=[&](const auto& drivers,bool baseline_input) {
            std::vector<Connected::Source> sources;
            for(const auto& driver:drivers) {
                bool replaced=driver.node==stage.node;
                for(const auto& item:receiver_outputs)
                    replaced|=driver.node==offsets.at(item.first)+networks.at(item.first)->driver_node_id;
                if(replaced)continue;
                Connected::Source source{driver.node,driver.ohms,{begin,end},{}};
                if(driver.initial!=driver.final && !(driver.ramp>0))
                    throw std::runtime_error("Connected SI requires finite source ramps");
                for(double t:{driver.center-.5*driver.ramp,driver.center+.5*driver.ramp,
                    driver.center+4.5*driver.ramp})if(t>begin && t<end)source.time.push_back(t);
                std::sort(source.time.begin(),source.time.end());
                source.time.erase(std::unique(source.time.begin(),source.time.end()),source.time.end());
                for(double t:source.time) {
                    const double fraction=driver.ramp>0?std::clamp((t-driver.center)/driver.ramp+.5,0.,1.):0.;
                    source.voltage.push_back(driver.initial+(driver.final-driver.initial)*fraction);
                }
                sources.push_back(std::move(source));
            }
            Connected::Source input{input_node,0.,stage.time,stage.input_v};
            if(baseline_input)std::fill(input.voltage.begin(),input.voltage.end(),stage.input_v.front());
            sources.push_back(std::move(input));return sources;
        };
        base=Connected::solve(n+1,resistors,capacitors,boundaries(baseline,true),stages,connected_initial,
            begin,end,options.step_ns,options.max_steps);
        wave=Connected::solve(n+1,resistors,capacitors,boundaries(active,false),stages,connected_initial,
            begin,end,options.step_ns,options.max_steps);
        if(base.time!=wave.time)throw std::runtime_error("Connected SI baseline event grid mismatch");
        result.model="experimental_connected_ccsn_stages";
        for(const auto& s:stages)if(!s.output_cap_profile.empty()) {
            result.model+="_with_output_charge";break;
        }
    }
    for (const double t : wave.time) result.time_ns.push_back(float(t));
    std::vector<uint32_t> reported_nets{victim->id};
    for(const auto& item:receiver_outputs)reported_nets.push_back(item.first);
    for(uint32_t reported_net:reported_nets) {
    const auto& vrc = *networks.at(reported_net);
    const auto vo = offsets.at(reported_net);
    for (size_t i=0;i<vrc.nodes.size();++i) {
        SiNodeWaveform node; node.node = uint32_t(i);
        node.net=std::string(network.net_name(NetId{reported_net}));
        const auto pin = vrc.nodes[i].pin;
        if (valid(pin)) {
            const auto& pd = network.pin(pin);
            if (valid(pd.instance)) node.pin = std::string(network.instance_name(pd.instance)) + "/";
            node.pin += std::string(network.pin_name(pin));
        }
        for (size_t k=0;k<wave.time.size();++k) {
            node.baseline_voltage.push_back(float(base.voltage[k][vo+i]));
            node.voltage.push_back(float(wave.voltage[k][vo+i]));
            const double noise = std::fabs(wave.voltage[k][vo+i]-base.voltage[k][vo+i]);
            node.noise_peak_v = std::max(node.noise_peak_v,float(noise));
            if (k) node.noise_width_ns += float((wave.time[k]-wave.time[k-1])*
                SiWaveformBasis::width_fraction(wave.voltage[k-1][vo+i]-base.voltage[k-1][vo+i],
                    wave.voltage[k][vo+i]-base.voltage[k][vo+i],.1*vdd));
        }
        if (!options.quiet_victim) {
            const auto measure=valid(pin)?basis_for(pin,pin==victim_driver && cell_driver(victim_driver),options.victim_rise):victim_basis;
            auto crossing=[&](const auto& values,double fraction) {
                return SiWaveformBasis::crossing(result.time_ns,values,fraction*vdd,options.victim_rise);
            };
            const double first=options.victim_rise?measure.lower:measure.upper;
            const double last=options.victim_rise?measure.upper:measure.lower;
            node.delay_delta_ns=float(crossing(node.voltage,measure.threshold)-crossing(node.baseline_voltage,measure.threshold));
            node.slew_delta_ns=float(((crossing(node.voltage,last)-crossing(node.voltage,first))-
                (crossing(node.baseline_voltage,last)-crossing(node.baseline_voltage,first)))/measure.derate);
            if (!std::isfinite(node.delay_delta_ns) || !std::isfinite(node.slew_delta_ns))
                throw std::runtime_error("SI waveform did not cross its timing thresholds");
        }
        result.nodes.push_back(std::move(node));
    }
    }
    return result;
}
} // namespace te
