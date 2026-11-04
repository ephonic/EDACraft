#include "sdf_annotation.hpp"
#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <tuple>

namespace dsim {
namespace {
std::string quote(const std::string& s) {
    std::ostringstream out;out<<'"';for(unsigned char c:s){if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<32){const char* h="0123456789abcdef";out<<"\\u00"<<h[c>>4]<<h[c&15];}else out<<c;}out<<'"';return out.str();
}
}
SdfPathAnnotation annotate_sdf_paths(const std::string& file,const GateDesign& design,const TimingLibrary& library,SdfBindOptions options,int model_corner,bool annotate_interconnect,bool annotate_checks) {
    if(model_corner<0||model_corner>2)throw std::runtime_error("invalid model delay corner");
    options.numeric_preview=false; // Each target model supplies its precision.
    SdfPathAnnotation staged;
    staged.model_corner=model_corner;
    std::map<std::tuple<uint32_t,uint32_t,uint32_t,uint32_t>,size_t> by_path;
    std::vector<int> model_index(design.models.size(),-1);
    std::vector<std::vector<TimingCheckSpec>> check_models(design.models.size());
    std::vector<uint8_t> drivers,root_inputs;
    std::map<uint32_t,size_t> by_input;
    std::map<std::string,std::vector<std::string>> identical_definitions;
    options.wildcard_model_aliases.clear();
    if(annotate_interconnect) {
        drivers.resize(design.constants.size());
        root_inputs.resize(design.constants.size());
        auto add=[&](int net){auto& n=drivers.at(size_t(net));if(n<2)++n;};
        for(size_t i=0;i<design.constants.size();++i)if(design.constants[i]>=0)add(int(i));
        for(const auto& port:design.ports)if(port.direction=="input"||port.direction=="inout")for(int net:port.nets) {
            add(net);
            if(port.direction=="input")root_inputs.at(size_t(net))=1;
        }
        for(const auto& cell:design.instances) {
            const auto& model=design.models.at(cell.model);
            for(size_t p=0;p<model.pins.size();++p)if(model.pins[p].output)add(design.pin_nets.at(cell.first+p));
        }
    }
    for(size_t i=0;i<design.models.size();++i) {
        const auto& model=design.models[i];
        if(model.copy_width||model.name=="__assign__")continue;
        const auto& timing=library.model(model.name);
        model_index[i]=int(&timing-library.models.data());
        if(!timing.definition_key.empty())identical_definitions[timing.definition_key].push_back(model.name);
        if(annotate_checks)check_models[i]=timing.executable_checks(model_corner);
        for(const auto& p:model.pins) {
            if(p.internal)continue;
            auto it=timing.ports.find(p.name);
            auto direction=p.inout?"inout":p.output?"output":"input";
            if(it==timing.ports.end()||it->second!=direction)throw std::runtime_error("timing model/Liberty pin mismatch: "+model.name+"."+p.name);
        }
        size_t external=std::count_if(model.pins.begin(),model.pins.end(),[](const auto& p){return !p.internal;});
        if(timing.ports.size()!=external)throw std::runtime_error("timing model/Liberty port set mismatch: "+model.name);
        // Validate initial values even if a later ABSOLUTE would replace them:
        // the caller must supply an actual elaborated model, never a guessed 0.
        for(const auto& path:timing.paths)(void)SdfPathDelays(timing.time,timing.initial(path,model_corner));
    }
    for(auto& group:identical_definitions)if(group.second.size()>1) {
        auto& types=group.second;std::sort(types.begin(),types.end());
        for(const auto& name:types)options.wildcard_model_aliases.emplace(name,types);
    }
    if(annotate_checks)for(uint32_t i=0;i<design.instances.size();++i) {
        const auto& checks=check_models.at(design.instances[i].model);
        if(!checks.empty())staged.checks.emplace(i,checks);
        for(const auto& check:checks)staged.negative_check_limits_clamped+=check.negative_limits_clamped;
    }
    staged.binding=bind_sdf_file(file,design,options,[&](const SdfBoundEntry& b) {
        const auto& e=*b.syntax;
        auto fail=[&](const std::string& why) {throw std::runtime_error(file+":"+std::to_string(e.line)+": SDF path annotation: "+why);};
        if(e.mode==SdfEntry::Mode::TimingCheck&&annotate_checks) {
            using C=TimingCheckSpec;
            // Family and limit slots share identities across separate and
            // combined declarations; event order follows SDF (data, reference).
            auto family=[](C::Kind k){return k==C::Setup||k==C::Hold||k==C::SetupHold?0:k==C::Recovery||k==C::Removal||k==C::RecRem?1:k==C::Width?2:k==C::Period?3:4;};
            auto phases=[](C::Kind k){return k==C::SetupHold||k==C::RecRem?3:k==C::Hold||k==C::Removal?2:1;};
            static const std::map<std::string,C::Kind> kinds={{"SETUP",C::Setup},{"HOLD",C::Hold},{"SETUPHOLD",C::SetupHold},{"RECOVERY",C::Recovery},{"REMOVAL",C::Removal},{"RECREM",C::RecRem},{"WIDTH",C::Width},{"PERIOD",C::Period},{"SKEW",C::Skew}};
            auto kind=kinds.find(e.kind);if(kind==kinds.end())fail("timing-check execution is not implemented: "+e.kind);
            if(b.cell.scope)fail("timing check requires a leaf cell model");
            auto found=staged.checks.find(b.cell.id);if(found==staged.checks.end())fail("no matching model timing check: "+e.kind);
            std::array<TimingEvent,2> events;
            for(size_t i=0;i<e.ports.size();++i){const auto& p=e.ports[i];if(!p.label.empty())fail("timing-check event labels are not implemented");events[i]={p.name,p.condition,timing_edge_mask(p.edge)};}
            if(e.ports.size()==1)events[1].transitions=1023;
            if(kind->second==C::Skew)std::swap(events[0],events[1]);
            const auto& model=library.models.at(size_t(model_index.at(design.instances.at(b.cell.id).model)));
            std::array<std::optional<uint64_t>,2> limits;
            for(size_t i=0;i<e.values.size();++i){const auto& raw=e.values[i].delay.corner.at(size_t(b.corner));if(raw){bool neg=raw->front()=='-';auto q=sdf_ticks(neg?raw->substr(1):*raw,b.unit_fs,model.time.precision_fs);limits[i]=neg?0:q;if(neg&&q)++staged.negative_check_limits_clamped;}}
            std::vector<C> next;int matched_phases=0;
            for(const auto& old:found->second) {
                bool identity=family(old.kind)==family(kind->second)&&(phases(old.kind)&phases(kind->second));
                for(size_t i=0;i<e.ports.size();++i)identity=identity&&old.events[i].pin==events[i].pin&&old.events[i].transitions==events[i].transitions&&timing_expression_key(old.events[i].condition)==timing_expression_key(events[i].condition);
                uint16_t a=old.events[0].transitions&events[0].transitions,z=old.events[1].transitions&events[1].transitions;
                if(!identity||!a||!z){next.push_back(old);continue;}
                matched_phases|=phases(old.kind)&phases(kind->second);
                // Timing-check edge identities are exact. Unlike module paths,
                // VCS does not bind an edged SDF event to an unedged check.
                auto update=old;
                for(int phase=0;phase<2;++phase)if((phases(old.kind)&phases(kind->second))&(1<<phase)) {
                    size_t source=phases(kind->second)==3?size_t(phase):0,target=phases(old.kind)==3?size_t(phase):0;
                    if(limits[source])update.limits[target]=*limits[source];
                }
                next.push_back(std::move(update));
            }
            if(matched_phases!=phases(kind->second))fail("no matching model timing check (kind/events/conditions/edges): "+e.kind+" in "+model.name);
            found->second=std::move(next);++staged.check_updates;return;
        }
        if((e.kind=="INTERCONNECT"||e.kind=="PORT")&&annotate_interconnect) {
            const bool port=e.kind=="PORT";
            const size_t terminals=port?1:2;
            if(b.ports.size()!=terminals||e.ports.size()!=terminals)fail(e.kind+" has an invalid terminal count");
            const auto& target=b.ports[port?0:1];
            if(target.owner.scope||target.direction!="input")fail(e.kind+" runtime requires a leaf receiving input pin");
            if(!e.condition.empty()||e.conditional_else||!e.label.empty()||!e.retain.empty())fail("conditional/label/RETAIN "+e.kind+" is not implemented");
            for(const auto& p:e.ports)if(!p.edge.empty()||!p.condition.empty()||!p.label.empty())fail("conditional/edge "+e.kind+" is not implemented");
            const auto& cell=design.instances.at(target.owner.id);
            int model=model_index.at(cell.model);if(model<0)fail(e.kind+" receiver has no leaf timing model");
            const auto& timing=library.models.at(size_t(model));
            uint32_t pin=cell.first+target.pin;
            auto found=by_input.find(pin);
            if(found==by_input.end()) {
                found=by_input.emplace(pin,staged.interconnects.size()).first;
                staged.interconnects.push_back({target.owner.id,pin,timing.time.precision_fs,{}});
            }
            auto& record=staged.interconnects.at(found->second);
            const auto count=e.values.size();
            if(count!=1&&count!=2&&count!=3&&count!=6&&count!=12)fail(e.kind+" requires 1, 2, 3, 6 or 12 values");
            struct Change {bool present=false,negative=false;uint64_t value=0;};
            std::vector<Change> selected;
            for(const auto& value:e.values) {
                if(value.reject||value.xlimit)fail(e.kind+" pulse thresholds are not implemented");
                const auto& raw=value.delay.corner.at(size_t(b.corner));
                if(!raw){selected.push_back({});continue;}
                bool negative=!raw->empty()&&raw->front()=='-';
                uint64_t value_ticks=sdf_ticks(negative?raw->substr(1):*raw,b.unit_fs,timing.time.precision_fs);
                selected.push_back({true,negative&&value_ticks!=0,value_ticks});
            }
            std::array<Change,3> changes;
            if(count==1)changes.fill(selected[0]);
            else {
                changes[0]=selected[0];changes[1]=selected[1];
                if(count==2) {
                    if(!selected[0].present||!selected[1].present)fail("sparse two-value "+e.kind+" is not implemented");
                    auto a=selected[0],z=selected[1];
                    bool less=a.negative!=z.negative?a.negative:a.negative?a.value>z.value:a.value<z.value;
                    changes[2]=less?a:z;
                } else changes[2]=selected[2];
            }
            auto next=record.quanta;
            // VCS's default MAXIMUM MIPD policy also applies to PORT:
            // Repeated ABSOLUTE updates retain the larger delay for resolved
            // multi-driver nets and for incoming root input ports. Internal
            // single-driver nets use the last update. The root-port policy is
            // independent of the external RTL driver kind; PORT and IC share
            // the same receiving delay stage.
            // A top input retains MAXIMUM even when driven by one external
            // reg/assign/primitive/module. Internal single-driver nets instead
            // replace the previous ABS value; do not infer policy from fanin alone.
            bool maximum=drivers.at(size_t(target.net))>1||root_inputs.at(size_t(target.net));
            for(size_t i=0;i<3;++i) {
                auto change=changes[i];
                if(!change.present) {if(e.mode==SdfEntry::Mode::Absolute)next[i]=0;continue;}
                if(e.mode==SdfEntry::Mode::Absolute) {
                    uint64_t value=change.negative?0:change.value;
                    // A zero ABSOLUTE does not clear an existing MIPD;
                    // INCREMENT can still reduce the effective value to zero.
                    if(next[i]&&value==0)continue;
                    next[i]=maximum?std::max(next[i],value):value;
                } else if(e.mode==SdfEntry::Mode::Increment) {
                    if(change.negative)next[i]=change.value>next[i]?0:next[i]-change.value;
                    else {if(change.value>UINT64_MAX-next[i])fail(e.kind+" increment overflow");next[i]+=change.value;}
                } else fail("invalid "+e.kind+" annotation mode");
            }
            record.quanta=next;
            if(port) {++staged.port_updates;if(!record.port)++staged.port_pins;record.port=true;}
            else {++staged.interconnect_updates;record.interconnect=true;}
            return;
        }
        if(e.kind=="DEVICE"&&annotate_interconnect) {
            if(!e.condition.empty()||e.conditional_else||!e.label.empty()||!e.retain.empty())
                fail("conditional/label/RETAIN DEVICE is not implemented");
            std::vector<std::optional<std::string>> values;
            for(const auto& value:e.values) {
                if(value.reject||value.xlimit)fail("DEVICE pulse thresholds require path runtime support");
                values.push_back(value.delay.corner.at(size_t(b.corner)));
            }
            // DEVICE on a module updates all module paths driving the named
            // output(s), retaining each path's edge/condition and timing origin.
            // A primitive without a module path needs its actual primitive body;
            // a Liberty function alone does not establish an annotatable gate.
            for(const auto& output:b.ports) {
                if(output.owner.scope||output.direction!="output")fail("DEVICE runtime requires a leaf output pin");
                const auto& instance=design.instances.at(output.owner.id);
                int model=model_index.at(instance.model);if(model<0)fail("DEVICE has no leaf timing model");
                const auto& timing=library.models.at(size_t(model));
                const auto& name=design.models.at(instance.model).pins.at(output.pin).name;
                bool matched=false;
                for(size_t i=0;i<timing.paths.size();++i) {
                    const auto& path=timing.paths[i];
                    for(uint32_t z=0;z<path.outputs.size();++z)if(path.outputs[z]==name)
                        for(uint32_t a=0;a<path.inputs.size();++a) {
                            if(i>UINT32_MAX)fail("DEVICE timing path index overflow");
                            auto key=std::make_tuple(output.owner.id,uint32_t(i),a,z);
                            auto found=by_path.find(key);
                            if(found==by_path.end()) {
                                auto index=staged.paths.size();
                                staged.paths.emplace_back(output.owner.id,uint32_t(model),uint32_t(i),a,z,
                                    SdfPathDelays(timing.time,timing.initial(path,model_corner)));
                                found=by_path.emplace(key,index).first;
                            }
                            auto& record=staged.paths.at(found->second);
                            try {staged.clamped_transition_slots+=record.delays.apply(e.mode,values,b.unit_fs,record.iopath_updated);}
                            catch(const std::exception& error) {fail(timing.name+": "+error.what());}
                            record.device_updated=true;
                            ++staged.path_updates;matched=true;
                        }
                }
                if(!matched)fail("DEVICE output has no module path; primitive body annotation is not implemented: "+timing.name+"."+name);
            }
            ++staged.device_updates;return;
        }
        if(e.kind!="IOPATH") {++staged.deferred_entries[e.kind];return;}
        if(b.cell.scope)fail("IOPATH on hierarchical scope requires hierarchical timing-model elaboration");
        const auto& instance=design.instances.at(b.cell.id);
        int model=model_index.at(instance.model);if(model<0)fail("missing leaf timing model");
        const auto& timing=library.models.at(size_t(model));
        if(e.ports.size()!=2||b.ports.size()!=2)fail("IOPATH requires two terminals");
        if(!e.retain.empty()||!e.label.empty())fail("RETAIN/label update requires path runtime support");
        for(const auto& p:e.ports)if(!p.condition.empty()||!p.label.empty())fail("conditional terminal update is not supported");
        std::vector<std::optional<std::string>> values;
        for(const auto& value:e.values) {
            if(value.reject||value.xlimit)fail("pulse thresholds require path runtime support");
            values.push_back(value.delay.corner.at(size_t(b.corner)));
        }
        bool matched=false;
        for(size_t i=0;i<timing.paths.size();++i) {
            const auto& p=timing.paths[i];
            if(std::find(p.inputs.begin(),p.inputs.end(),e.ports[0].name)==p.inputs.end()||
               std::find(p.outputs.begin(),p.outputs.end(),e.ports[1].name)==p.outputs.end()||
               (!p.edge.empty()&&!e.ports[0].edge.empty()&&p.edge!=e.ports[0].edge)||!e.ports[1].edge.empty()||
               p.ifnone!=e.conditional_else||timing_expression_key(p.condition)!=timing_expression_key(e.condition))continue;
            if(i>UINT32_MAX)fail("timing path index overflow");
            auto input=uint32_t(std::find(p.inputs.begin(),p.inputs.end(),e.ports[0].name)-p.inputs.begin());
            auto output=uint32_t(std::find(p.outputs.begin(),p.outputs.end(),e.ports[1].name)-p.outputs.begin());
            // Each full-path terminal pair owns its own annotation state.
            auto key=std::make_tuple(b.cell.id,uint32_t(i),input,output);auto found=by_path.find(key);
            if(found==by_path.end()) {
                auto index=staged.paths.size();
                staged.paths.emplace_back(b.cell.id,uint32_t(model),uint32_t(i),input,output,SdfPathDelays(timing.time,timing.initial(p,model_corner)));
                found=by_path.emplace(key,index).first;
            }
            auto& record=staged.paths.at(found->second);
            try{staged.clamped_transition_slots+=record.delays.apply(e.mode,values,b.unit_fs,record.device_updated);}
            catch(const std::exception& x){fail(timing.name+": "+x.what());}
            record.iopath_updated=true;
            ++staged.path_updates;matched=true;
        }
        if(!matched)fail("no exact model path (terminals/edge/condition/ifnone): "+timing.name+"."+e.ports[0].name+" -> "+e.ports[1].name);
    });
    return staged;
}
std::string SdfPathAnnotation::report(const TimingLibrary& library,uint64_t tick) const {
    std::ostringstream out;
    out<<"{\"schema\":\"dsim.sdf-path-tables.v1\",\"runtime_annotation\":false,\"model_corner\":"<<model_corner<<",\"path_updates\":"<<path_updates<<",\"distinct_paths\":"<<paths.size()<<",\"clamped_transition_slots\":"<<clamped_transition_slots<<",\"tick_fs\":"<<tick<<",\"deferred_entries\":{";
    bool first=true;for(const auto& e:deferred_entries){if(!first)out<<',';first=false;out<<quote(e.first)<<':'<<e.second;}
    out<<"},\"binding\":"<<binding.report()<<",\"paths\":[";
    first=true;for(const auto& p:paths) {
        const auto& model=library.models.at(p.model);const auto& path=model.paths.at(p.path);auto ticks=p.delays.ticks(tick);
        if(!first)out<<',';first=false;out<<"{\"instance\":"<<p.instance<<",\"model\":"<<quote(model.name)<<",\"path\":"<<p.path<<",\"input\":"<<quote(path.inputs.at(p.input))<<",\"output\":"<<quote(path.outputs.at(p.output))<<",\"edge\":"<<quote(path.edge)<<",\"condition\":"<<quote(path.condition)<<",\"ifnone\":"<<(path.ifnone?"true":"false")<<",\"precision_fs\":"<<model.time.precision_fs<<",\"ticks\":[";
        for(size_t i=0;i<ticks.size();++i){if(i)out<<',';out<<ticks[i];}out<<"]}";
    }
    out<<"]}\n";return out.str();
}
}
