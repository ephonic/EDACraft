#include "dcalc/nldm_dcalc.hh"
#include "dcalc/awe_dcalc.hh"
#include "network/network.hh"
#include "graph/timing_graph.hh"
#include "engine_impl.hh"
#include "liberty/logic_expression.hh"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <map>
#include <numeric>
#include <random>
#include <stdexcept>
#include <tuple>
#include <unordered_set>

namespace te {
namespace {
struct Activity {
    double rate=0, probability=.5;
    std::string source="default";
};
// A truth table preserves repeated-variable identity within one expression.
// Independence between different nets is an explicit averaged-power model.
struct Truth {
    std::vector<uint32_t> nets;
    std::vector<bool> values;
    bool valid=false;
};
// A call-local cache stores power truth tables in cell pin-name coordinates.
// Power integration intentionally distinguishes physical cell pins, making
// these tables reusable across instances without merging tied design nets.
using PowerTruthCache=std::map<std::tuple<uint32_t,std::string,bool>,Truth>;
struct StateBinding {
    std::string_view positive,negative;
    uint32_t net;
    bool inverted;
};
bool sequential_cell(const edacraft::core::LibertyCellData& cell) {
    return cell.ff_state!=UINT32_MAX || cell.ff_clocked_on!=UINT32_MAX || cell.ff_enable!=UINT32_MAX;
}
#include "power_clock_gate.inc"
Truth truth_table(const Network& network, InstanceId instance, std::string_view expression,
                  const edacraft::core::LibertyCellData* combinational_cell=nullptr,
                  bool power_pin_statistics=false, PowerTruthCache* cache=nullptr,
                  const StateBinding* state=nullptr) {
    Truth result;
    const auto key=std::make_tuple(network.instance(instance).cell.id,std::string(expression),combinational_cell!=nullptr);
    if (cache && power_pin_statistics) {
        const auto found=cache->find(key);
        if (found!=cache->end()) {
            result=found->second;
            for (auto& name:result.nets) {
                const auto pin=network.find_pin(instance,network.str(name));
                if (!pin || !valid(network.pin(*pin).net)) return {};
                name=network.net_count()+pin->id;
            }
            return result;
        }
    }
    // Liberty state conditions often name both inputs and outputs. Expand
    // combinational outputs before enumeration: treating Y=f(A,B) as another
    // independent random variable discards valid state probability. Consult
    // the library even for an output omitted from the mapped netlist.
    std::vector<uint32_t> expanding;
    std::function<std::optional<int>(std::string_view,const std::function<std::optional<int>(uint32_t)>&)> lookup;
    lookup=[&](std::string_view name,const std::function<std::optional<int>(uint32_t)>& value) -> std::optional<int> {
        // Liberty next_state may refer to its internal state (for example
        // an enabled FF's E*D + !E*IQ). Bind IQ/IQN to the actual output net;
        // the internal state name need not be a physical cell pin.
        if (state && (name==state->positive || (!state->negative.empty() && name==state->negative))) {
            const auto current=value(state->net);
            if (!current) return {};
            return (state->inverted ^ (name==state->negative)) ? 1-*current : *current;
        }
        if (combinational_cell) for (const auto& pin : combinational_cell->pins) {
            if (network.str(pin.name)!=name || pin.function==UINT32_MAX) continue;
            if (std::find(expanding.begin(),expanding.end(),pin.name)!=expanding.end()) return {};
            expanding.push_back(pin.name);
            const auto evaluated=evaluate_liberty_boolean(network.str(pin.function),
                [&](std::string_view input) { return lookup(input,value); });
            expanding.pop_back();
            return evaluated ? std::optional<int>{int(*evaluated)} : std::nullopt;
        }
        const auto pin=network.find_pin(instance,name);
        if (!pin || !valid(network.pin(*pin).net)) return {};
        // PT's averaged cell power integrates Liberty pin states separately,
        // even when two distinct cell inputs connect to one design net. Net
        // propagation still retains that physical net's Boolean identity.
        return value(power_pin_statistics ? network.net_count()+pin->id : network.pin(*pin).net.id);
    };
    const auto parsed=evaluate_liberty_boolean(expression,[&](std::string_view name) -> std::optional<int> {
        return lookup(name,[&](uint32_t net) -> std::optional<int> {
            if (std::find(result.nets.begin(),result.nets.end(),net)==result.nets.end()) result.nets.push_back(net);
            return 0;
        });
    });
    if (!parsed || result.nets.size()>12) return result;
    result.values.reserve(size_t(1)<<result.nets.size());
    for (size_t mask=0;mask<(size_t(1)<<result.nets.size());++mask) {
        const auto value=evaluate_liberty_boolean(expression,[&](std::string_view name) -> std::optional<int> {
            return lookup(name,[&](uint32_t net) -> std::optional<int> {
                const auto i=std::find(result.nets.begin(),result.nets.end(),net)-result.nets.begin();
                return int((mask>>i)&1);
            });
        });
        if (!value) return result;
        result.values.push_back(*value);
    }
    result.valid=true;
    if (cache && power_pin_statistics) {
        auto prototype=result;
        for (auto& n:prototype.nets) n=network.pin(PinId{uint32_t(n-network.net_count())}).name;
        cache->emplace(key,std::move(prototype));
    }
    return result;
}
double mask_probability(const Truth& truth, size_t mask, const std::vector<Activity>& activity, int ignore=-1) {
    double p=1;
    for (size_t bit=0;bit<truth.nets.size();++bit) if (int(bit)!=ignore) {
        const auto one=activity.at(truth.nets[bit]).probability;
        p*=((mask>>bit)&1) ? one : 1-one;
    }
    return p;
}
double probability(const Truth& truth, const std::vector<Activity>& activity) {
    double p=0;
    for (size_t mask=0;mask<truth.values.size();++mask) if (truth.values[mask])
        p+=mask_probability(truth,mask,activity);
    return p;
}
bool equivalent(const Truth& a, const Truth& b) {
    if (!a.valid || !b.valid) return false;
    auto nets=a.nets;
    for (const auto net : b.nets)
        if (std::find(nets.begin(),nets.end(),net)==nets.end()) nets.push_back(net);
    if (nets.size()>12) return false;
    auto value=[&](const Truth& truth,size_t mask) {
        size_t sub=0;
        for (size_t bit=0;bit<truth.nets.size();++bit) {
            const auto pos=std::find(nets.begin(),nets.end(),truth.nets[bit])-nets.begin();
            sub|=((mask>>pos)&1)<<bit;
        }
        return truth.values[sub];
    };
    for (size_t mask=0;mask<(size_t(1)<<nets.size());++mask)
        if (value(a,mask)!=value(b,mask)) return false;
    return true;
}

double transition_rate(const Truth& truth, const std::vector<Activity>& activity, double sample_hz=0) {
    if (sample_hz>0 && truth.nets.size()>1) {
        // A clocked activity estimate has a finite observation interval. The
        // infinitesimal Boolean derivative below counts simultaneous input
        // changes separately; in deep XOR/multiplier cones it can grow without
        // bound. Integrate the two-state transition matrix over a reference cycle
        // instead. The tensor product costs O(n*2^n), not O(4^n).
        std::vector<double> next(truth.values.begin(),truth.values.end());
        for (size_t bit=0;bit<truth.nets.size();++bit) {
            const auto& a=activity.at(truth.nets[bit]);
            const double p=a.probability;
            const double q=std::clamp(a.rate/sample_hz,0.,2*std::min(p,1-p));
            const double up=p<1 ? .5*q/(1-p) : 0, down=p>0 ? .5*q/p : 0;
            for (size_t mask=0;mask<next.size();++mask) if (!(mask&(size_t(1)<<bit))) {
                const auto other=mask|(size_t(1)<<bit);
                const double zero=next[mask],one=next[other];
                next[mask]=(1-up)*zero+up*one;
                next[other]=down*zero+(1-down)*one;
            }
        }
        double changed=0;
        for (size_t mask=0;mask<next.size();++mask)
            changed+=mask_probability(truth,mask,activity)*(truth.values[mask] ? 1-next[mask] : next[mask]);
        return std::max(0.,changed*sample_hz);
    }
    double rate=0;
    for (size_t bit=0;bit<truth.nets.size();++bit) {
        double sensitization=0;
        for (size_t mask=0;mask<truth.values.size();++mask) if (!(mask&(size_t(1)<<bit)) &&
            truth.values[mask]!=truth.values[mask|(size_t(1)<<bit)])
            sensitization+=mask_probability(truth,mask,activity,int(bit));
        rate+=activity.at(truth.nets[bit]).rate*sensitization;
    }
    return rate;
}

// Integrate sensitization and when jointly, rather than multiplying their
// probabilities (which double-counts a side input present in both).
double event_weight(const Truth& function, const Truth& condition, uint32_t trigger,
                    const std::vector<Activity>& activity) {
    Truth joint; joint.nets=function.nets;
    for (const auto net : condition.nets)
        if (std::find(joint.nets.begin(),joint.nets.end(),net)==joint.nets.end()) joint.nets.push_back(net);
    if (std::find(joint.nets.begin(),joint.nets.end(),trigger)==joint.nets.end()) joint.nets.push_back(trigger);
    if (joint.nets.size()>12) return NAN;
    const auto bit=std::find(joint.nets.begin(),joint.nets.end(),trigger)-joint.nets.begin();
    auto value=[&](const Truth& truth,size_t mask) {
        size_t sub=0;
        for (size_t i=0;i<truth.nets.size();++i) {
            const auto position=std::find(joint.nets.begin(),joint.nets.end(),truth.nets[i])-joint.nets.begin();
            sub|=((mask>>position)&1)<<i;
        }
        return truth.values[sub];
    };
    double weight=0;
    for (size_t mask=0;mask<(size_t(1)<<joint.nets.size());++mask) if (!(mask&(size_t(1)<<bit))) {
        const auto other=mask|(size_t(1)<<bit);
        if (value(function,mask)!=value(function,other))
            weight+=mask_probability(joint,mask,activity,int(bit))*.5*
                (int(value(condition,mask))+int(value(condition,other)));
    }
    return weight;
}
}

void TimingEngine::set_power_activity(std::string_view object, double rate, double probability) {
    if (!std::isfinite(rate) || rate<0 || !std::isfinite(probability) || probability<0 || probability>1)
        throw std::invalid_argument("Power activity requires finite nonnegative Hz and probability in [0,1]");
    auto net=find_net(object);
    if (!net) {
        const auto pin=find_pin(object);
        if (pin && valid(impl_->network->pin(*pin).net)) net=impl_->network->pin(*pin).net;
    }
    if (!net) throw std::invalid_argument("Power activity object not found: "+std::string(object));
    impl_->power_activity[net->id]={rate,probability};
}
void TimingEngine::set_power_internal_activity(std::string_view name, std::string_view when,
    std::string_view related_name, double rate, double rise_ratio) {
    if (!std::isfinite(rate) || rate<0 || !std::isfinite(rise_ratio) || rise_ratio<0 || rise_ratio>1)
        throw std::invalid_argument("Internal power activity requires nonnegative Hz and rise_ratio in [0,1]");
    const auto pin=find_pin(name);
    if (!pin) throw std::invalid_argument("Internal power pin not found: "+std::string(name));
    const auto& network=*impl_->network;
    const auto& pd=network.pin(*pin);
    if (!valid(pd.instance) || !valid(pd.liberty_pin) ||
        (pd.direction!=PortDirection::Input && pd.direction!=PortDirection::Output))
        throw std::invalid_argument("Internal power annotation requires a library cell input or output pin");
    const auto& cell=network.cell(network.instance(pd.instance).cell);
    if (!valid(cell.liberty_library) || !valid(cell.liberty_cell))
        throw std::invalid_argument("Internal power annotation requires a linked library cell");
    if (!impl_->liberty->library(cell.liberty_library.id).power_metadata_complete)
        throw std::runtime_error("Internal power activity needs regenerated .ftlib v12 or Liberty text");
    const auto& lc=impl_->liberty->library(cell.liberty_library.id).cells[cell.liberty_cell.id];
    const auto& groups=lc.pins.at(pd.liberty_pin.id).internal_power;
    const bool unconditional=when.empty();
    const auto truth=unconditional ? Truth{} : truth_table(network,pd.instance,when,nullptr,true);
    if (!unconditional && !truth.valid) throw std::invalid_argument("Invalid internal power state condition");
    std::vector<size_t> matches;
    for (size_t index=0;index<groups.size();++index) {
        const auto& group=groups[index];
        const auto group_related=group.related_pin==UINT32_MAX ? std::string_view{} : network.str(group.related_pin);
        if (group_related!=related_name) continue;
        if (unconditional ? group.when==UINT32_MAX :
            group.when!=UINT32_MAX && equivalent(truth,truth_table(network,pd.instance,network.str(group.when),nullptr,true)))
            matches.push_back(index);
    }
    if (matches.empty()) throw std::invalid_argument("No internal power group matches pin, condition and related pin");
    for (const auto index : matches)
        impl_->power_internal_activity[(uint64_t(pin->id)<<32)|uint32_t(index)]={rate,rise_ratio};
}
void TimingEngine::clear_power_activity() {
    impl_->power_activity.clear(); impl_->power_internal_activity.clear();
}
void TimingEngine::set_power_propagation_mode(std::string_view mode) {
    if (mode!="clocked" && mode!="independent")
        throw std::invalid_argument("Power propagation mode must be clocked or independent");
    impl_->power_clocked_propagation=mode=="clocked";
}

TimingEngine::PowerSummary TimingEngine::estimate_power(float frequency, float activity) const {
    return estimate_power_detail(frequency,activity).summary;
}

TimingEngine::PowerDetail TimingEngine::estimate_power_detail(float frequency, float default_activity) const {
    return estimate_power_detail(frequency,default_activity,PowerOptions{});
}

TimingEngine::PowerDetail TimingEngine::estimate_power_detail(float frequency, float default_activity,
                                                             const PowerOptions& options) const {
    if (!std::isfinite(frequency) || frequency<0 || !std::isfinite(default_activity) || default_activity<0)
        throw std::invalid_argument("Power frequency and activity must be finite and nonnegative");
    if (!std::isfinite(options.static_probability) || options.static_probability<0 || options.static_probability>1 ||
        !std::isfinite(options.reference_frequency_hz) || options.reference_frequency_hz<0 ||
        !std::isfinite(options.clock_transitions_per_cycle) || options.clock_transitions_per_cycle< -1)
        throw std::invalid_argument("Invalid call-local power observation options");
    PowerDetail result;
    result.summary.frequency_hz=frequency; result.summary.activity=default_activity;
    if (!impl_->network || !impl_->liberty) return result;
    const auto& network=*impl_->network;
    PowerTruthCache power_truth_cache;
    for (uint32_t li=0;li<impl_->liberty->library_count();++li) {
        if (!impl_->liberty->library(li).power_metadata_complete)
            throw std::runtime_error("Power analysis needs regenerated .ftlib v12 or Liberty text; legacy power metadata is incomplete");
        const auto& library=impl_->liberty->library(li);
        if (!library.sequential_metadata_complete)
            for (uint32_t ci=0;ci<library.cells.size();++ci) if (sequential_cell(library.cells[ci]))
                throw std::runtime_error("Sequential power analysis needs regenerated .ftlib v15 or Liberty text; complementary FF state metadata is incomplete");
    }
    std::vector<Activity> activity(network.net_count(),Activity{double(frequency)*default_activity,options.static_probability,"default"});
    for (const auto& [net,value] : impl_->power_activity) if (net<activity.size())
        activity[net]={value.rate,value.probability,"annotated"};
    if (impl_->sdc) for (const auto& clock : impl_->sdc->clocks()) {
        if (!(clock.period>0)) continue;
        for (const auto pin : clock.sources) if (pin.id<network.pin_count()) {
            const auto net=network.pin(pin).net;
            if (valid(net) && activity[net.id].source=="default") {
                double duty=.5;
                if (clock.rise_time>=0 && clock.fall_time>=0)
                    duty=std::clamp(double(clock.fall_time-clock.rise_time)/clock.period,0.,1.);
                const double edges=options.clock_transitions_per_cycle<0 ? 2 : options.clock_transitions_per_cycle;
                activity[net.id]={edges/(clock.period*1e-9),duty,
                    options.clock_transitions_per_cycle<0 ? "clock" : "annotated"};
            }
        }
    }
    auto resolve_activity_net=[&](const std::string& object) {
        auto net=find_net(object);
        if (!net) {
            const auto pin=find_pin(object);
            if (pin && valid(network.pin(*pin).net)) net=network.pin(*pin).net;
        }
        if (!net) throw std::invalid_argument("Power activity object not found: "+object);
        return *net;
    };
    for (const auto& value:options.fallback_activities) {
        if (!std::isfinite(value.toggle_rate_hz) || value.toggle_rate_hz<0 ||
            !std::isfinite(value.static_probability) || value.static_probability<0 || value.static_probability>1)
            throw std::invalid_argument("Invalid fallback power activity");
        auto& target=activity[resolve_activity_net(value.object).id];
        if (target.source=="default") target={value.toggle_rate_hz,value.static_probability,"annotated"};
    }
    std::unordered_map<uint32_t,std::pair<double,double>> call_annotations;
    for (const auto& value:options.activities) {
        if (!std::isfinite(value.toggle_rate_hz) || value.toggle_rate_hz<0 ||
            !std::isfinite(value.static_probability) || value.static_probability<0 || value.static_probability>1)
            throw std::invalid_argument("Invalid call-local power activity");
        const auto id=resolve_activity_net(value.object).id;
        const auto stats=std::make_pair(value.toggle_rate_hz,value.static_probability);
        const auto inserted=call_annotations.emplace(id,stats);
        if (!inserted.second && inserted.first->second!=stats)
            throw std::invalid_argument("Conflicting power activity aliases");
        activity[id]={value.toggle_rate_hz,value.static_probability,"annotated"};
    }
    for (uint32_t id=0;id<network.net_count();++id) if (network.net(NetId{id}).constant_value>=0)
        activity[id]={0,double(network.net(NetId{id}).constant_value),"constant"};
    if (impl_->sdc) for (const auto& c : impl_->sdc->case_analyses()) {
        if (unsigned(c.value)>1 || c.pin.id>=network.pin_count()) continue;
        const auto net=network.pin(c.pin).net;
        if (valid(net)) activity[net.id]={0,double(c.value),"constant"};
    }
    std::unordered_map<uint32_t,uint8_t> call_fixed_values;
    for (const auto& value:options.fixed_values) {
        if (value.second>1) throw std::invalid_argument("Power fixed value must be zero or one");
        const auto id=resolve_activity_net(value.first).id;
        const auto inserted=call_fixed_values.emplace(id,value.second);
        if (!inserted.second && inserted.first->second!=value.second)
            throw std::invalid_argument("Conflicting fixed power aliases");
        const auto physical_constant=network.net(NetId{id}).constant_value;
        if ((physical_constant>=0 && physical_constant!=value.second) ||
            (!options.fixed_values_override_sdc && activity[id].source=="constant" &&
             activity[id].probability!=double(value.second)))
            throw std::invalid_argument("Conflicting fixed power value");
        activity[id]={0,double(value.second),"constant"};
    }
    // Sort output functions by graph level, so a declared downstream instance
    // before its driver still receives propagated activity in a DAG.
    double sample_hz=0;
    if (impl_->sdc) for (const auto& clock : impl_->sdc->clocks())
        if (clock.period>0) sample_hz=std::max(sample_hz,1./(clock.period*1e-9));
    if (sample_hz==0) sample_hz=double(frequency);
    if (options.reference_frequency_hz>0) sample_hz=options.reference_frequency_hz;
    if (!impl_->power_clocked_propagation) sample_hz=0;
    result.activity_sample_hz=sample_hz;
    struct Output {
        uint32_t level; InstanceId instance; uint32_t net; Truth truth;
        bool sequential=false; Truth clock, clear, preset; bool inverted=false, latch=false;
    };
    std::vector<Output> outputs;
    for (uint32_t iid=0;iid<network.instance_count();++iid) {
        const InstanceId instance{iid}; const auto& inst=network.instance(instance);
        const auto& cell=network.cell(inst.cell);
        // Flattened hierarchy and continuous assignments are zero-delay
        // connectivity, not independent activity sources. These pseudo-cells
        // have no Liberty record, but must forward data, clock and constants.
        if (network.cell_name(inst.cell)=="__assign__") {
            const auto input=network.find_pin(instance,"A"),output=network.find_pin(instance,"X");
            if (input && output && valid(network.pin(*input).net) && valid(network.pin(*output).net)) {
                const auto vertex=output->id*2;
                const auto level=vertex<impl_->graph->vertex_count() ? impl_->graph->vertex_level(vertex) : 0;
                outputs.push_back({uint32_t(std::max(0,int(level))),instance,network.pin(*output).net.id,
                    Truth{{network.pin(*input).net.id},{false,true},true},false,{}});
            }
            continue;
        }
        if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
        const auto& lc=impl_->liberty->library(cell.liberty_library.id).cells[cell.liberty_cell.id];
        const auto clock_gate=power_clock_gate(network,instance,lc);
        const bool requires_clock_gate=lc.clock_gating_integrated_cell!=UINT32_MAX &&
            std::any_of(lc.pins.begin(),lc.pins.end(),[](const auto& pin) {
                return pin.direction==edacraft::core::PortDirection::Output && pin.function==UINT32_MAX;
            });
        if (requires_clock_gate && !clock_gate.valid) {
            ++result.unsupported_expressions;continue;
        }
        if (clock_gate.valid) {
            const auto clock_net=network.pin(PinId{clock_gate.clock}).net.id;
            const auto output_net=network.pin(PinId{clock_gate.output}).net.id;
            Truth enable{{network.pin(PinId{clock_gate.enable}).net.id},{false,true},true};
            if (clock_gate.test!=UINT32_MAX) {
                const auto test=network.pin(PinId{clock_gate.test}).net.id;
                if (test!=enable.nets.front()) {enable.nets.push_back(test);enable.values={false,true,true,true};}
            }
            // Call-local virtual state is consumed only by activity sampling;
            // it never enters the physical netlist or timing graph.
            const auto held=uint32_t(activity.size());activity.push_back({0,.5,"default"});
            outputs.push_back({0,instance,held,std::move(enable),true,
                Truth{{clock_net},{true,false},true},{},{},false,true});
            const auto vertex=clock_gate.output*2;
            const auto level=vertex<impl_->graph->vertex_count()?impl_->graph->vertex_level(vertex):0;
            outputs.push_back({uint32_t(std::max(0,int(level))),instance,output_net,
                Truth{{clock_net,held},{false,false,false,true},true},false,{}});
            continue;
        }
        for (const auto pin : inst.pins) {
            const auto& pd=network.pin(pin);
            if (pd.direction!=PortDirection::Output || !valid(pd.net) || !valid(pd.liberty_pin)) continue;
            const auto fn=lc.pins.at(pd.liberty_pin.id).function;
            if (fn==UINT32_MAX) continue;
            auto expression=network.str(fn);
            bool sequential=sequential_cell(lc);
            Truth clock_truth, clear_truth, preset_truth;
            bool inverted=false;
            StateBinding state_binding{};
            const bool latch=lc.ff_clocked_on==UINT32_MAX && lc.ff_enable!=UINT32_MAX;
            if (sequential) {
                // FFs retain their clock and asynchronous control expressions
                // for event sampling. Latches retain a level enable.
                if (lc.ff_state==UINT32_MAX || lc.ff_next_state==UINT32_MAX ||
                    (lc.ff_clocked_on==UINT32_MAX && !latch)) {
                    ++result.unsupported_expressions; continue;
                }
                const auto state=network.str(lc.ff_state);
                const auto state_neg=lc.ff_state_neg==UINT32_MAX ? std::string_view{} : network.str(lc.ff_state_neg);
                auto at=[&](int value) { return evaluate_liberty_boolean(expression,[&](std::string_view variable)->std::optional<int> {
                    if (variable==state) return value;
                    if (!state_neg.empty() && variable==state_neg) return 1-value;
                    return std::nullopt;
                }); };
                const auto zero=at(0),one=at(1);
                if (!zero || !one || *zero==*one) { ++result.unsupported_expressions; continue; }
                inverted=*zero;
                state_binding={state,state_neg,pd.net.id,inverted};
                clock_truth=truth_table(network,instance,network.str(latch?lc.ff_enable:lc.ff_clocked_on));
                if (!clock_truth.valid) { ++result.unsupported_expressions; continue; }
                if (lc.ff_clear!=UINT32_MAX) clear_truth=truth_table(network,instance,network.str(lc.ff_clear));
                if (lc.ff_preset!=UINT32_MAX) preset_truth=truth_table(network,instance,network.str(lc.ff_preset));
                if ((lc.ff_clear!=UINT32_MAX && !clear_truth.valid) ||
                    (lc.ff_preset!=UINT32_MAX && !preset_truth.valid) ||
                    (clear_truth.valid && preset_truth.valid)) {
                    ++result.unsupported_expressions; continue;
                }
                expression=network.str(lc.ff_next_state);
            }
            auto truth=truth_table(network,instance,expression,nullptr,false,nullptr,
                                   sequential?&state_binding:nullptr);
            if (!truth.valid) { ++result.unsupported_expressions; continue; }
            if (inverted) for (size_t i=0;i<truth.values.size();++i) truth.values[i]=!truth.values[i];
            const uint32_t vertex=pin.id*2;
            const auto level=vertex<impl_->graph->vertex_count() ? impl_->graph->vertex_level(vertex) : 0;
            outputs.push_back({uint32_t(std::max(0,int(level))),instance,pd.net.id,
                std::move(truth),sequential,std::move(clock_truth),std::move(clear_truth),std::move(preset_truth),inverted,latch});
        }
    }
    std::stable_sort(outputs.begin(),outputs.end(),[](const auto& a,const auto& b) { return a.level<b.level; });

    // Large reconvergent designs need joint state trajectories too. A
    // bit-parallel evaluator keeps 64 independent trajectories per word.
#include "power_sampling.inc"

    // Marginal propagation loses shared-input and sequential feedback
    // correlations. Sample the actual Boolean network for bounded cones with
    // these dependencies. Independent gates retain the exact analytical path.
    // This is zero-delay activity estimation, not glitch simulation.
    auto sample_correlated=[&]() -> bool {
        if (!(sample_hz>0) || outputs.size()>4096) return false;
        for (const auto& output:outputs)
            if (output.clear.valid || output.preset.valid || output.latch) return false;
        std::vector<int> driver(activity.size(),-1),comb_driver(activity.size(),-1);
        std::vector<size_t> sequential,comb;
        for (size_t i=0;i<outputs.size();++i) {
            const auto& o=outputs[i];
            if (activity[o.net].source!="default") continue;
            driver[o.net]=int(i);
            if (o.sequential) sequential.push_back(i);
            else { comb.push_back(i);comb_driver[o.net]=int(i); }
        }
        // Kahn's algorithm, once with register dependencies to detect feedback,
        // then with registers as roots to obtain a combinational evaluation order.
        auto order=[&](bool cross_registers) {
            std::vector<size_t> result;
            std::vector<unsigned> pending(outputs.size(),0);
            std::vector<std::vector<size_t>> users(outputs.size());
            size_t expected=0;
            for (size_t i=0;i<outputs.size();++i) {
                const auto& o=outputs[i];
                if (driver[o.net]<0 || (!cross_registers && o.sequential)) continue;
                ++expected;
                for (auto net:o.truth.nets) {
                    const int d=cross_registers ? driver[net] : comb_driver[net];
                    if (d>=0) {++pending[i];users[size_t(d)].push_back(i);}
                }
                if (!pending[i]) result.push_back(i);
            }
            for (size_t at=0;at<result.size();++at)
                for (auto user:users[result[at]]) if (!--pending[user]) result.push_back(user);
            return std::make_pair(std::move(result),expected);
        };
        const auto all=order(true);
        const bool feedback=all.first.size()!=all.second;
        const auto combinational=order(false);
        if (combinational.first.size()!=comb.size()) return false;
        bool reconvergent=false,composed=false;
        std::vector<std::vector<uint32_t>> support(activity.size());
        for (uint32_t n=0;n<activity.size();++n)
            if (comb_driver[n]<0 && activity[n].source!="constant" && activity[n].source!="clock")
                support[n].push_back(n);
        for (size_t i:combinational.first) {
            auto& roots=support[outputs[i].net];
            for (auto net:outputs[i].truth.nets) {
                // A multi-input gate's output is generally not a first-order
                // Markov source even when its input cones are disjoint.
                const int d=comb_driver[net];
                if (d>=0 && outputs[size_t(d)].truth.nets.size()>1 && outputs[i].truth.nets.size()>1)
                    composed=true;
                for (auto root:support[net]) {
                if (std::find(roots.begin(),roots.end(),root)!=roots.end()) reconvergent=true;
                else roots.push_back(root);
                if (roots.size()>256) return false;
                }
            }
        }
        bool sampled_logic=false;
        for (size_t i:sequential) for (auto n:outputs[i].truth.nets)
            sampled_logic|=comb_driver[n]>=0;
        if (!feedback && !reconvergent && !composed && !sampled_logic) return false;
        // Require a common simple clock source, allowing buffers/inverters.
        int common_clock=-1,common_edge=-1;
        std::vector<bool> clock_net(activity.size(),false);
        for (size_t n=0;n<activity.size();++n) clock_net[n]=activity[n].source=="clock";
        for (size_t i:sequential) {
            const auto& clock=outputs[i].clock;
            if (clock.nets.size()!=1) return false;
            if (clock.values[0]==clock.values[1]) return false;
            bool inverted=clock.values[0];
            uint32_t n=clock.nets[0];
            size_t steps=0;
            while (activity[n].source!="clock") {
                if (++steps>outputs.size() || comb_driver[n]<0) return false;
                clock_net[n]=true;
                const auto& t=outputs[size_t(comb_driver[n])].truth;
                if (t.nets.size()!=1 || t.values[0]==t.values[1]) return false;
                inverted^=t.values[0];
                n=t.nets[0];
            }
            clock_net[n]=true;
            if (std::abs(activity[n].rate-2*sample_hz)>sample_hz*1e-6 ||
                (common_clock>=0 && common_clock!=int(n)) ||
                (common_edge>=0 && common_edge!=int(inverted))) return false;
            common_clock=int(n);
            common_edge=int(inverted);
        }
        // Clock-as-data and gated clocks require event timing beyond this
        // two-phase model. Keep the analytical fallback for those cones.
        for (size_t i:combinational.first) if (!clock_net[outputs[i].net])
            for (auto n:outputs[i].truth.nets) if (clock_net[n]) return false;
        std::vector<uint32_t> roots;
        std::vector<bool> needed(activity.size(),false);
        for (const auto& o:outputs) if (driver[o.net]>=0 && !clock_net[o.net])
            for (auto n:o.truth.nets) needed[n]=true;
        for (uint32_t n=0;n<activity.size();++n) if (needed[n] && driver[n]<0 && !clock_net[n]) {
            if (activity[n].rate>2*sample_hz) return false;
            // A zero-rate unknown state needs an ensemble of trajectories;
            // one temporal trajectory cannot estimate its marginal P.
            if (activity[n].rate==0 && activity[n].probability>0 && activity[n].probability<1) return false;
            roots.push_back(n);
        }
        std::mt19937_64 random(0x4654494d4552ULL);
        auto uniform=[&]() {return double(random()>>11)*0x1.0p-53;};
        std::vector<uint8_t> state(activity.size()),previous(activity.size());
        std::vector<uint64_t> ones(activity.size()),changes(activity.size());
        for (size_t n=0;n<state.size();++n) state[n]=uniform()<activity[n].probability;
        for (auto i:sequential) state[outputs[i].net]=outputs[i].inverted;
        // Flatten small truth tables once. Most mapped gates have <=4 inputs;
        // interpreting their pin vectors at every half-cycle dominated bounded
        // arithmetic sampling. These are exact table lookups, with the same
        // state and random trajectory as the general evaluator.
        struct ScalarFunction {
            uint32_t nets[4]={};
            uint16_t code=0;
            unsigned arity=5;
            const Truth* truth=nullptr;
        };
        std::vector<ScalarFunction> functions;
        functions.reserve(outputs.size());
        for(const auto& output:outputs) {
            const auto& t=output.truth;ScalarFunction f;f.truth=&t;
            if(t.valid && t.nets.size()<=4 && t.values.size()==(size_t{1}<<t.nets.size())) {
                f.arity=unsigned(t.nets.size());
                for(size_t bit=0;bit<t.nets.size();++bit)f.nets[bit]=t.nets[bit];
                for(size_t row=0;row<t.values.size();++row)
                    if(t.values[row])f.code|=uint16_t(uint16_t{1}<<row);
            }
            functions.push_back(f);
        }
        auto evaluate=[&](size_t index) {
            const auto& f=functions[index];
            switch(f.arity) {
            case 0:return uint8_t(f.code&1);
            case 1:return uint8_t((f.code>>state[f.nets[0]])&1);
            case 2:return uint8_t((f.code>>(state[f.nets[0]]|(unsigned(state[f.nets[1]])<<1)))&1);
            case 3: {
                const auto a=state[f.nets[0]],b=state[f.nets[1]],c=state[f.nets[2]];
                switch(f.code) {
                case 0x96:return uint8_t(a^b^c);
                case 0x69:return uint8_t(1^a^b^c);
                case 0xe8:return uint8_t((a&b)|((a|b)&c));
                case 0x17:return uint8_t(1^((a&b)|((a|b)&c)));
                default:return uint8_t((f.code>>(a|(unsigned(b)<<1)|(unsigned(c)<<2)))&1);
                }
            }
            case 4:return uint8_t((f.code>>(state[f.nets[0]]|(unsigned(state[f.nets[1]])<<1)|
                (unsigned(state[f.nets[2]])<<2)|(unsigned(state[f.nets[3]])<<3)))&1);
            default:break;
            }
            const auto& t=*f.truth;
            size_t mask=0;
            for (size_t bit=0;bit<t.nets.size();++bit) mask|=size_t(state[t.nets[bit]])<<bit;
            return uint8_t(t.values[mask]);
        };
        auto settle=[&]() {
            for (size_t i:combinational.first) state[outputs[i].net]=evaluate(i);
        };
        constexpr unsigned burn=1024;
        // Bound root-event sampling noise across activity settings. Rarely
        // changing roots need longer trajectories than high-activity inputs.
        // The cap bounds runtime; the actual budget is reported to callers.
        unsigned samples=65536;
        for (auto n:roots) if (activity[n].rate>0)
            while (samples<1048576 && samples*activity[n].rate/sample_hz<16384) samples*=2;
        // Root probabilities do not change during a trajectory. Compile the
        // same conditional transition thresholds once, preserving root order
        // and every random draw (including zero-probability transitions).
        struct RootTransition { uint32_t net;double up,down;bool can_up,can_down; };
        std::vector<RootTransition> transitions;
        for (auto n:roots) {
            const auto& a=activity[n];
            const double q=std::clamp(a.rate/(2*sample_hz),0.,2*std::min(a.probability,1-a.probability));
            transitions.push_back({n,a.probability<1?.5*q/(1-a.probability):0,
                a.probability>0?.5*q/a.probability:0,a.probability<1,a.probability>0});
        }
        // Only driven, non-clock outputs consume sampled counters below.
        // Root annotations stay exact; counting unused nets cannot affect the
        // trajectory. Deduplicate aliases exactly as the old all-net loop did.
        std::vector<uint32_t> observed;
        std::vector<bool> observing(activity.size(),false);
        for (const auto& o:outputs) if (driver[o.net]>=0 && !clock_net[o.net] && !observing[o.net]) {
            observing[o.net]=true;observed.push_back(o.net);
        }
        std::vector<uint8_t> next(sequential.size());
        settle();
        // Root statistics describe transitions within a clock cycle. Use two
        // observation phases; only one phase captures edge-triggered state.
        // Sampling roots once per cycle incorrectly passes D activity directly
        // to Q and discards combinational events between register edges.
        for (unsigned step=0;step<2*(burn+samples);++step) {
            for (const auto& r:transitions) {
                const bool high=state[r.net];
                if ((high?r.can_down:r.can_up) && uniform()<(high?r.down:r.up)) state[r.net]^=1;
            }
            settle();
            if (step%2==0 && !sequential.empty()) {
                for (size_t i=0;i<sequential.size();++i) next[i]=evaluate(sequential[i]);
                for (size_t i=0;i<sequential.size();++i) state[outputs[sequential[i]].net]=next[i];
                settle();
            }
            for (auto n:observed) {
                if (step>=2*burn) {
                    ones[n]+=state[n];changes[n]+=state[n]!=previous[n];
                }
                previous[n]=state[n];
            }
        }
        for (const auto& o:outputs) if (driver[o.net]>=0 && !clock_net[o.net])
            activity[o.net]={double(changes[o.net])*sample_hz/samples,double(ones[o.net])/(2*samples),"propagated"};
        // Buffers/inverters are exact copies of their source statistics; do
        // not introduce sampling noise on an independently annotated root.
        for (size_t i:combinational.first) {
            const auto& o=outputs[i];const auto& t=o.truth;
            if (clock_net[o.net]) continue;
            if (t.nets.empty()) activity[o.net]={0,double(t.values[0]),"propagated"};
            else if (t.nets.size()==1) {
                const auto& a=activity[t.nets[0]];
                const bool constant=t.values[0]==t.values[1];
                activity[o.net]={constant ? 0 : a.rate,
                    constant ? double(t.values[0]) : (t.values[0] ? 1-a.probability : a.probability),"propagated"};
            }
        }
        result.activity_samples=samples;
        return true;
    };
    const bool sampled=options.propagate_activity && (sample_parallel() || sample_correlated());
    std::vector<bool> sampled_net(activity.size(),false),driven(activity.size(),false);
    for (const auto& output:outputs) {
        sampled_net[output.net]=sampled && activity[output.net].source=="propagated";
        driven[output.net]=activity[output.net].source=="default" || activity[output.net].source=="propagated";
    }
    for (unsigned pass=0;options.propagate_activity && pass<32;++pass) {
        double change=0;
        auto captured=activity;
        if (sample_hz>0) for (uint32_t n=0;n<activity.size();++n) if (!driven[n]) {
            // Exact one-cycle joint statistics for independent roots
            // undergoing two stationary Markov transitions per cycle.
            const double variance=activity[n].probability*(1-activity[n].probability);
            const double q=variance>0 ? std::clamp(activity[n].rate/(2*sample_hz),0.,2*std::min(activity[n].probability,1-activity[n].probability)) : 0;
            captured[n].rate=sample_hz*(2*q-(variance>0 ? q*q/(2*variance) : 0));
        }
        for (const auto& output : outputs) {
            auto& a=activity[output.net];
            if (a.source!="default" && a.source!="propagated") continue;
            if (sampled_net[output.net]) continue;
            if (output.clear.valid || output.preset.valid || output.latch) {
                if (!pass) ++result.unsupported_expressions;
                continue;
            }
            double rate=transition_rate(output.truth,activity,output.sequential ? 0 : 2*sample_hz);
            const double p=probability(output.truth,activity);
            if (output.sequential) {
                if (sample_hz>0) {
                    rate=transition_rate(output.truth,captured,sample_hz);
                }
                rate=std::min(rate,std::min(p,1-p)*transition_rate(output.clock,activity));
            }
            change=std::max(change,std::max(std::abs(a.rate-rate)/std::max(1.,sample_hz),std::abs(a.probability-p)));
            a={rate,p,"propagated"};
            // Combinational activity is measured at half-cycle resolution;
            // a receiving FF observes the composition over a full cycle.
            // Keep that second propagation context through every gate, rather
            // than replacing it with the half-cycle density. The bounded
            // sampler handles this directly, but large designs use this path.
            captured[output.net]=output.sequential || !(sample_hz>0) ? a :
                Activity{transition_rate(output.truth,captured,sample_hz),p,"propagated"};
        }
        if (change<1e-8) break;
        if (pass==31) ++result.unsupported_expressions;
    }

    // Per-pin power variables alias their net's marginal statistics, but have
    // distinct Boolean identities in a library's state/event partitions.
    // Discard virtual latch state before physical per-pin statistics reuse
    // these indices. No synthetic state may be mistaken for a physical pin.
    activity.resize(network.net_count());
    activity.resize(network.net_count()+network.pin_count());
    for (uint32_t p=0;p<network.pin_count();++p) {
        const auto n=network.pin(PinId{p}).net;
        if (valid(n)) activity[network.net_count()+p]=activity[n.id];
    }
    std::map<uint32_t,size_t> cell_record;
    for (uint32_t iid=0;iid<network.instance_count();++iid) {
        const InstanceId instance{iid}; const auto& inst=network.instance(instance);
        const auto& cell=network.cell(inst.cell);
        if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
        const auto& lib=impl_->liberty->library(cell.liberty_library.id);
        const auto& lc=lib.cells[cell.liberty_cell.id];
        const auto clock_gate=power_clock_gate(network,instance,lc);
        PowerCell record; record.name=std::string(network.instance_name(instance));
        record.cell_name=std::string(network.cell_name(inst.cell));
        auto condition=[&](uint32_t when) {
            if (when==UINT32_MAX) return 1.;
            if (clock_gate.valid) {
                const double p=power_clock_gate_condition(network,instance,clock_gate,network.str(when),activity);
                if (!std::isfinite(p)) {++result.unsupported_expressions;return 0.;}
                return p;
            }
            const auto truth=truth_table(network,instance,network.str(when),sequential_cell(lc) ? nullptr : &lc,true,&power_truth_cache);
            if (!truth.valid) { ++result.unsupported_expressions; return 0.; }
            return probability(truth,activity);
        };
        // Each supply has its own conditional partition and fallback. Adding
        // probabilities across rails can exceed one and erase another rail's
        // uncovered leakage. Legacy libraries without groups use cell leakage.
        struct LeakageRail { double value=0, covered=0, fallback=0; bool has_fallback=false; };
        std::map<uint32_t,LeakageRail> rails;
        for (const auto& group : lc.leakage_power) {
            auto& rail=rails[group.related_pg_pin];
            if (group.when==UINT32_MAX) { rail.fallback+=group.value; rail.has_fallback=true; }
            else { const double p=condition(group.when); rail.covered+=p; rail.value+=p*group.value; }
        }
        double leakage=rails.empty() ? lc.cell_leakage_power : 0;
        for (const auto& [name,rail] : rails)
            leakage+=rail.value+std::max(0.,1-rail.covered)*
                (rail.has_fallback ? rail.fallback : (rails.size()==1 ? lc.cell_leakage_power : 0.));
        record.leakage_w=float(std::max(0.,leakage)*lib.units.leakage_power_unit_watts);
        const double energy_unit=lib.units.capacitance_unit_farads*
            double(lib.units.voltage_unit_volts)*lib.units.voltage_unit_volts;
        for (const auto pin : inst.pins) {
            const auto& pd=network.pin(pin);
            if (!valid(pd.liberty_pin) || !valid(pd.net)) continue;
            const auto& lp=lc.pins.at(pd.liberty_pin.id);
            const double load=(pd.direction==PortDirection::Output) ? get_net_load_cap(pd.net) : 0;
            bool has_internal_annotation=false;
            // Input SDPD describes local input events, including events that
            // do not switch the output. PT uses those densities directly,
            // independently of the net's total activity. Only output groups
            // share an output event budget (see input SDPD PT controls).
            for (size_t index=0;index<lp.internal_power.size();++index)
                has_internal_annotation|=impl_->power_internal_activity.count((uint64_t(pin.id)<<32)|uint32_t(index))!=0;
            const bool normalize_internal=has_internal_annotation && pd.direction==PortDirection::Output;
            double pin_internal=0, annotated_energy=0, annotated_density=0;
            double inferred_energy=0, inferred_density=0;
            for (size_t power_index=0;power_index<lp.internal_power.size();++power_index) {
                ++result.internal_groups_available;
                const auto unsupported_before=result.unsupported_expressions;
                const auto& power=lp.internal_power[power_index];
                auto related=power.related_pin==UINT32_MAX ? std::optional<PinId>{pin} :
                    network.find_pin(instance,network.str(power.related_pin));
                if (!related || !valid(network.pin(*related).net)) { ++result.unsupported_expressions; continue; }
                const auto trigger=network.pin(*related).net.id;
                double rate=activity[trigger].rate;
                double rise_ratio=.5, weight=1;
                const auto annotated=impl_->power_internal_activity.find((uint64_t(pin.id)<<32)|uint32_t(power_index));
                if (annotated!=impl_->power_internal_activity.end()) {
                    rate=annotated->second.rate; rise_ratio=annotated->second.rise_ratio;
                    ++result.internal_annotated_groups;
                } else {
                    weight=condition(power.when);
                    if (pd.direction==PortDirection::Output && power.related_pin!=UINT32_MAX) {
                        const auto fn=lp.function==UINT32_MAX ? Truth{} : truth_table(network,instance,network.str(lp.function),nullptr,true,&power_truth_cache);
                        const auto cond=power.when==UINT32_MAX ? Truth{{},{true},true} :
                            truth_table(network,instance,network.str(power.when),nullptr,true,&power_truth_cache);
                        if (fn.valid && cond.valid) weight=event_weight(fn,cond,network.net_count()+related->id,activity);
                        else {
                            // FF output energy is charged for Q events, not
                            // every clock edge. Its function names a state
                            // variable rather than a combinational input.
                            if (!sequential_cell(lc) && !clock_gate.valid) ++result.unsupported_expressions;
                            rate=activity[pd.net.id].rate;
                        }
                        if (!std::isfinite(weight)) { ++result.unsupported_expressions; continue; }
                        if (fn.valid && (activity[pd.net.id].source=="annotated" || activity[pd.net.id].source=="propagated") && !normalize_internal) {
                            const auto derived=transition_rate(fn,activity);
                            rate*=derived>0 ? activity[pd.net.id].rate/derived : 0;
                        }
                    }
                }
                if (result.unsupported_expressions==unsupported_before) ++result.internal_groups_evaluated;
                if (!rate && !normalize_internal) continue;
                double sum=0;
                for (const auto rf : {Transition::Rise,Transition::Fall}) {
                    const auto& table=rf==Transition::Rise ? power.rise_power : power.fall_power;
                    if (table.values.empty()) continue;
                    auto input_rf=rf;
                    for (const auto& arc : lc.arcs) if (arc.from_pin==network.pin(*related).name && arc.to_pin==pd.name &&
                        arc.sense==edacraft::core::LibertyTimingSense::NegativeUnate) {
                        input_rf=rf==Transition::Rise ? Transition::Fall : Transition::Rise; break;
                    }
                    const float slew=get_slew(*related,input_rf,MinMax::Max);
                    const float unit_ns=lib.units.time_unit_seconds / 1e-9f;
                    sum+=table.lookup(std::max(0.f,slew)/unit_ns,float(load))*
                        (rf==Transition::Rise ? rise_ratio : 1-rise_ratio);
                }
                const double density=rate*weight, energy=sum*energy_unit;
                pin_internal+=energy*density;
                if (annotated!=impl_->power_internal_activity.end()) {
                    annotated_energy+=energy*density; annotated_density+=density;
                } else {
                    inferred_energy+=energy*density; inferred_density+=density;
                }
            }
            // PT gives annotated groups their output event budget first. The
            // remaining groups share the residual; if all groups are annotated,
            // normalize them together to the total output density instead.
            if (normalize_internal) {
                const double output_rate=activity[pd.net.id].rate;
                if (!(inferred_density>0))
                    pin_internal=annotated_density>0 ? annotated_energy*output_rate/annotated_density : 0;
                else {
                    pin_internal=annotated_density>0 ? annotated_energy*
                        std::min(output_rate,annotated_density)/annotated_density : 0;
                    const double remaining=std::max(0.,output_rate-annotated_density);
                    pin_internal+=remaining*inferred_energy/inferred_density;
                }
            } else if (has_internal_annotation) {
                // Local input annotations keep their full density, even when
                // it exceeds the net's activity. Inferred groups keep their
                // estimate unless it would exceed the remaining input budget;
                // unlike output SDPD, unused input budget is not filled.
                const double remaining=std::max(0.,activity[pd.net.id].rate-annotated_density);
                pin_internal=annotated_energy+(inferred_density>0 ?
                    inferred_energy*std::min(1.,remaining/inferred_density) : 0.);
            }
            record.internal_w+=float(pin_internal);
        }
        cell_record[iid]=result.cells.size(); result.cells.push_back(std::move(record));
    }
    for (uint32_t id=0;id<network.net_count();++id) {
        const NetId net{id}; const auto& nd=network.net(net);
        // Scalar wire aliases retain queryable names after electrical merging.
        // Report their canonical activity, while the disconnected alias entry
        // keeps zero capacitance so switching power is charged only once.
        const auto canonical=network.find_net(network.net_name(net));
        const auto& a=activity[canonical ? canonical->id : id];
        PowerNet record; record.name=std::string(network.net_name(net)); record.source=a.source;
        record.toggle_rate_hz=a.rate; record.static_probability=a.probability;
        if (a.source=="annotated") ++result.annotated_nets;
        else if (a.source=="propagated") ++result.propagated_nets;
        else if (a.source=="constant") ++result.constant_nets;
        else if (a.source=="clock") ++result.clock_nets;
        else ++result.default_nets;
        if (valid(nd.driver)) {
            const auto& pd=network.pin(nd.driver);
            double cap_unit=1e-12;
            if (valid(pd.instance)) {
                const auto& cell=network.cell(network.instance(pd.instance).cell);
                if (valid(cell.liberty_library)) cap_unit=impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
            }
            record.capacitance_f=std::max(0.f,get_net_load_cap(net))*cap_unit;
            double voltage=impl_->voltage;
            if (!impl_->power_voltage_explicit && valid(pd.instance)) {
                const auto& cell=network.cell(network.instance(pd.instance).cell);
                if (valid(cell.liberty_library)) voltage=impl_->liberty->library(cell.liberty_library.id).units.voltage;
            }
            record.switching_w=float(.5*a.rate*record.capacitance_f*voltage*voltage);
            // Primary input power is supplied outside this design. Preserve
            // its capacitance/activity in detail but do not charge cell total.
            const auto cell=cell_record.find(pd.instance.id);
            if (cell!=cell_record.end()) {
                record.included_in_total=true;
                result.cells[cell->second].switching_w+=record.switching_w;
            }
        }
        result.nets.push_back(std::move(record));
    }
    double leak=0,internal=0,switching=0;
    for (auto& cell : result.cells) {
        cell.total_w=cell.leakage_w+cell.internal_w+cell.switching_w;
        leak+=cell.leakage_w; internal+=cell.internal_w; switching+=cell.switching_w;
    }
    result.summary.leakage_w=float(leak); result.summary.internal_w=float(internal);
    result.summary.switching_w=float(switching); result.summary.total_w=float(leak+internal+switching);
    return result;
}
} // namespace te
