#include "gate_timing.hpp"
#include <algorithm>
#include <limits>
#include <set>
#include <tuple>
namespace dsim {
std::shared_ptr<GateTimingData> build_gate_timing(const GateDesign& d,const TimingLibrary& library,const SdfPathAnnotation& annotation,bool disable_checks) {
    auto result=std::make_shared<GateTimingData>();result->annotated_updates=annotation.path_updates;
    result->interconnects=annotation.interconnects;result->interconnect_updates=annotation.interconnect_updates;
    result->port_updates=annotation.port_updates;result->device_updates=annotation.device_updates;result->port_pins=annotation.port_pins;
    static const std::set<std::string> checks={"SETUP","HOLD","SETUPHOLD","RECOVERY","REMOVAL","RECREM","SKEW","BIDIRECTSKEW","WIDTH","PERIOD","NOCHANGE"};
    for(const auto& e:annotation.deferred_entries) {
        if(disable_checks&&checks.count(e.first)){result->disabled_checks+=e.second;continue;}
        throw std::runtime_error("SDF runtime does not implement "+e.first+(checks.count(e.first)?" (use --no-timingchecks to disable checks explicitly)":""));
    }
    using Key=std::tuple<uint32_t,uint32_t,uint32_t,uint32_t>;
    std::map<Key,const AnnotatedPath*> updates;
    for(const auto& p:annotation.paths)updates.emplace(Key{p.instance,p.path,p.input,p.output},&p);
    std::map<std::string,const TimingModel*> models;
    for(const auto& m:library.models)models.emplace(m.name,&m);
    std::map<std::pair<uint32_t,std::string>,uint32_t> condition_indices;
    for(uint32_t i=0;i<d.instances.size();++i) {
        const auto& cell=d.instances[i];const auto& functional=d.models[cell.model];
        if(functional.copy_width||functional.name=="__assign__")continue;
        const auto& model=*models.at(functional.name);
        result->precision_fs=result->precision_fs?std::min(result->precision_fs,model.time.precision_fs):model.time.precision_fs;
        if(!disable_checks) {
            auto found=annotation.checks.find(i);
            if(!model.checks.empty()&&found==annotation.checks.end())throw std::runtime_error("missing executable timing-check model: "+model.name);
            if(found!=annotation.checks.end())for(auto check:found->second) {
                for(auto& event:check.events)event.condition=model.resolve_condition(event.condition);
                result->checks.push_back({i,cell.first,std::move(check),model.time.precision_fs});
            }
        }
        if(!model.pulse_declarations.empty())throw std::runtime_error("runtime pulse declarations are not implemented: "+model.name);
        auto pin=[&](const std::string& name) {
            auto found=std::find_if(functional.pins.begin(),functional.pins.end(),[&](const auto& p){return p.name==name;});
            if(found==functional.pins.end())throw std::runtime_error("missing functional timing pin "+name);
            return cell.first+uint32_t(found-functional.pins.begin());
        };
        for(uint32_t p=0;p<model.paths.size();++p) {
            const auto& path=model.paths[p];
            uint32_t condition=0;
            if(!path.condition.empty()) {
                auto expression=model.resolve_condition(path.condition);
                auto key=std::make_pair(cell.model,timing_expression_key(expression));
                auto inserted=condition_indices.emplace(key,uint32_t(result->conditions.size()));
                if(inserted.second)result->conditions.push_back({cell.model,std::move(expression)});
                condition=inserted.first->second;
            }
            result->conditional_paths=result->conditional_paths||condition!=0||path.ifnone;
            if(path.ifnone&&!path.edge.empty())throw std::runtime_error("ifnone requires a simple path: "+model.name);
            if(!path.polarity.empty()||!path.output_polarity.empty())throw std::runtime_error("runtime path polarity is not implemented: "+model.name);
            uint8_t edge=path.edge.empty()?0:path.edge=="posedge"?1:path.edge=="negedge"?2:3;
            if(edge==3)throw std::runtime_error("unsupported runtime path edge: "+path.edge);
            for(uint32_t a=0;a<path.inputs.size();++a)for(uint32_t z=0;z<path.outputs.size();++z) {
                auto found=updates.find(Key{i,p,a,z});
                auto table=found==updates.end()?SdfPathDelays(model.time,model.initial(path,annotation.model_corner)):found->second->delays;
                result->arcs.push_back({pin(path.inputs[a]),pin(path.outputs[z]),edge,model.time.precision_fs,table.model_quanta()});
                auto& arc=result->arcs.back();arc.first=cell.first;arc.condition=condition;arc.ifnone=path.ifnone;
            }
        }
    }
    if(result->conditional_paths) {
        std::map<std::pair<uint32_t,uint32_t>,uint8_t> groups;
        for(const auto& arc:result->arcs) {
            auto& kinds=groups[{arc.input,arc.output}];
            if(arc.ifnone)kinds|=1;
            else if(!arc.condition)kinds|=2;
            if(kinds==3)throw std::runtime_error("ifnone and unconditional paths share source/destination terminals");
        }
    }
    // Contiguous arcs for each driven output. Stable order retains declaration
    // order within an output; selection uses latest source time and min ties.
    std::stable_sort(result->arcs.begin(),result->arcs.end(),[](const auto& a,const auto& b){return a.output<b.output;});
    result->check_updates=annotation.check_updates;
    result->negative_check_limits_clamped=annotation.negative_check_limits_clamped;
    if(!result->precision_fs)throw std::runtime_error("SDF runtime requires at least one timing model");
    return result;
}
}
