#include "sdf_binding.hpp"
#include <algorithm>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
namespace dsim {
std::vector<std::string> sdf_path_parts(const std::string& text,char divider) {
    std::vector<std::string> parts;std::string part;
    for(size_t i=0;i<text.size();++i) {
        char c=text[i];
        if(c=='\\') {
            if(++i==text.size())throw std::runtime_error("unterminated SDF name escape");
            part+=text[i];
        } else if(c==divider) {
            if(part.empty())throw std::runtime_error("empty SDF path component");
            parts.push_back(std::move(part));part.clear();
        } else part+=c;
    }
    if(part.empty())throw std::runtime_error("empty SDF path component");
    parts.push_back(std::move(part));return parts;
}
namespace {
std::vector<std::string> decode(std::string_view key) {
    std::vector<std::string> path;
    while(!key.empty()) {
        if(key.size()<4)throw std::runtime_error("invalid timing path key");
        uint32_t n=0;for(int i=0;i<4;++i)n|=uint32_t(static_cast<unsigned char>(key[i]))<<(i*8);
        key.remove_prefix(4);if(!n||n>key.size())throw std::runtime_error("invalid timing path component");
        path.emplace_back(key.substr(0,n));key.remove_prefix(n);
    }
    return path;
}
class Binder {
    const GateDesign& design;
    const GateTimingNames& names;
    SdfBindOptions options;
    std::function<void(const SdfBoundEntry&)> callback;
    std::string filename;
    char divider='.';
    std::map<std::string_view,uint32_t> scopes;
    std::unordered_map<std::string,std::vector<SdfBoundCell>> types;
    std::vector<std::unordered_map<std::string,uint32_t>> model_pins,scope_pins;
    std::vector<SdfBoundCell> targets;
    std::unordered_map<int,std::vector<int>> copies;
    std::vector<uint32_t> seen;
    std::vector<int> search;
    uint32_t generation=0;
    SdfBindStats stats;
    [[noreturn]] void fail(size_t line,const std::string& message) const {throw std::runtime_error(filename+":"+std::to_string(line)+": SDF binding: "+message);}
    std::string_view type(SdfBoundCell cell) const {return cell.scope?std::string_view(names.scopes.at(cell.id).type):std::string_view(design.models.at(design.instances.at(cell.id).model).name);}
    std::vector<std::string> path(SdfBoundCell cell) const {return decode(names.key(cell.scope?names.scopes.at(cell.id).name:names.instance_names.at(cell.id)));}
    SdfBoundCell find(const std::vector<std::string>& path,size_t line) const {
        auto id=names.find_instance(path);if(id>=0)return {false,uint32_t(id)};
        auto scope=scopes.find(GateTimingNames::encode(path));if(scope!=scopes.end())return {true,scope->second};
        std::string display;for(const auto& p:path){if(!display.empty())display+='/';display+=p;}
        fail(line,"unknown instance/scope "+display);
    }
    SdfBoundPin pin(SdfBoundCell cell,const std::string& port,size_t line) const {
        if(cell.scope) {
            auto it=scope_pins.at(cell.id).find(port);if(it==scope_pins.at(cell.id).end())fail(line,"unknown scope pin "+port);
            const auto& p=names.scopes.at(cell.id).pins.at(it->second);return {cell,it->second,p.net,p.direction};
        }
        const auto& inst=design.instances.at(cell.id);const auto& model=design.models.at(inst.model);
        auto it=model_pins.at(inst.model).find(port);if(it==model_pins.at(inst.model).end())fail(line,"unknown cell pin "+std::string(type(cell))+"."+port);
        const auto& p=model.pins.at(it->second);
        if(p.internal)fail(line,"internal Liberty pin is not an external timing endpoint: "+port);
        return {cell,it->second,design.pin_nets.at(inst.first+it->second),p.inout?"inout":p.output?"output":"input"};
    }
    std::vector<std::string> parts(const std::string& text,size_t line) const {
        try{return sdf_path_parts(text,divider);}catch(const std::exception& e){fail(line,e.what());}
    }
    SdfBoundPin endpoint(SdfBoundCell base,const std::string& text,size_t line) const {
        auto components=parts(text,line);auto port=std::move(components.back());components.pop_back();
        if(components.empty())return pin(base,port,line);
        auto relative=path(base);relative.insert(relative.end(),components.begin(),components.end());return pin(find(relative,line),port,line);
    }
    bool reachable(int from,int to) {
        if(from==to)return true;
        if(++generation==0){std::fill(seen.begin(),seen.end(),0);++generation;}
        search.clear();search.push_back(from);seen.at(size_t(from))=generation;
        for(size_t i=0;i<search.size();++i) {
            auto edges=copies.find(search[i]);if(edges==copies.end())continue;
            for(auto next:edges->second) {
                if(next==to)return true;
                if(seen.at(size_t(next))!=generation){seen[size_t(next)]=generation;search.push_back(next);}
            }
        }
        return false;
    }
    void direction(const SdfBoundPin& pin,const char* expected,size_t line) const {
        if(pin.direction!=expected&&pin.direction!="inout")fail(line,"pin direction must be "+std::string(expected));
    }
    std::optional<SdfSignedTicks> select(const SdfTriple& triple,size_t line) {
        const auto& decimal=triple.corner.at(size_t(options.corner));
        if(!decimal){++stats.missing_values;return {};}
        bool negative=!decimal->empty()&&decimal->front()=='-';
        uint64_t value;
        try{value=sdf_ticks(negative?decimal->substr(1):*decimal,stats.unit_fs,options.tick_fs);}
        catch(const std::exception& e){fail(line,e.what());}
        if(negative&&value)++stats.negative_values;
        return SdfSignedTicks{negative&&value!=0,value};
    }
    SdfSelectedValue select(const SdfDelayValue& value,size_t line) {
        SdfSelectedValue result;result.delay=select(value.delay,line);
        if(value.reject)result.reject=select(*value.reject,line);
        if(value.xlimit)result.xlimit=select(*value.xlimit,line);
        return result;
    }
    void count_missing(const SdfDelayValue& value) {
        auto count=[&](const SdfTriple& t){if(!t.corner.at(size_t(options.corner)))++stats.missing_values;};
        count(value.delay);
        if(value.reject)count(*value.reject);
        if(value.xlimit)count(*value.xlimit);
    }
    void cell(const SdfCell& cell) {
        targets.clear();
        if(cell.instance=="*") {
            auto it=types.find(cell.type);if(it==types.end()||it->second.empty())fail(cell.line,"wildcard matched no CELLTYPE "+cell.type);
            targets=it->second;
            auto aliases=options.wildcard_model_aliases.find(cell.type);
            if(aliases!=options.wildcard_model_aliases.end()) {
                auto original=targets.size();
                for(const auto& alias:aliases->second)if(alias!=cell.type) {
                    auto found=types.find(alias);if(found==types.end())continue;
                    for(auto target:found->second)if(!target.scope)targets.push_back(target);
                }
                // Match the existing name-index order, independent of the
                // order in which equivalent model declarations were loaded.
                std::sort(targets.begin(),targets.end(),[&](auto a,auto b) {
                    if(a.scope!=b.scope)return a.scope>b.scope;
                    return names.key(a.scope?names.scopes[a.id].name:names.instance_names[a.id])<
                           names.key(b.scope?names.scopes[b.id].name:names.instance_names[b.id]);
                });
                targets.erase(std::unique(targets.begin(),targets.end(),[](auto a,auto b){return a.scope==b.scope&&a.id==b.id;}),targets.end());
                stats.wildcard_alias_targets+=targets.size()-original;
            }
        } else {
            auto target=find(cell.instance.empty()?std::vector<std::string>{}:parts(cell.instance,cell.line),cell.line);
            if(type(target)!=cell.type)fail(cell.line,"CELLTYPE mismatch: expected "+std::string(type(target))+", got "+cell.type);
            targets.push_back(target);
        }
        stats.target_cells+=targets.size();
    }
    void entry(const SdfEntry& entry) {
        // Corner conversion is independent of wildcard expansion. Missing
        // values and signed increments remain explicit, never guessed as zero.
        SdfBoundEntry bound;bound.syntax=&entry;
        bound.unit_fs=stats.unit_fs;bound.corner=options.corner;bound.numeric_preview=options.numeric_preview;
        if(options.numeric_preview) {
            for(const auto& v:entry.values)bound.values.push_back(select(v,entry.line));
            for(const auto& r:entry.retain) {bound.retain.emplace_back();for(const auto& v:r)bound.retain.back().push_back(select(v,entry.line));}
        } else {
            for(const auto& v:entry.values)count_missing(v);
            for(const auto& r:entry.retain)for(const auto& v:r)count_missing(v);
        }
        for(auto target:targets) {
            bound.cell=target;bound.ports.clear();
            for(const auto& p:entry.ports)bound.ports.push_back(endpoint(target,p.name,entry.line));
            if(entry.kind=="IOPATH") {
                direction(bound.ports.at(0),"input",entry.line);direction(bound.ports.at(1),"output",entry.line);
                // An IOPATH port belongs to this cell, not a nested instance.
                for(const auto& p:bound.ports)if(p.owner.scope!=target.scope||p.owner.id!=target.id)fail(entry.line,"IOPATH must reference local cell ports");
            } else if(entry.kind=="INTERCONNECT") {
                auto own=[&](const SdfBoundPin& p){return p.owner.scope==target.scope&&p.owner.id==target.id;};
                direction(bound.ports.at(0),target.scope&&own(bound.ports[0])?"input":"output",entry.line);
                direction(bound.ports.at(1),target.scope&&own(bound.ports[1])?"output":"input",entry.line);
                if(!reachable(bound.ports[0].net,bound.ports[1].net))fail(entry.line,"INTERCONNECT endpoints are not connected through wires/copies");
                ++stats.interconnects;
            } else if(entry.kind=="PORT")direction(bound.ports.at(0),"input",entry.line);
            else if(entry.kind=="DEVICE") {
                if(bound.ports.empty()) {
                    if(target.scope)for(uint32_t i=0;i<names.scopes[target.id].pins.size();++i) {
                        const auto& p=names.scopes[target.id].pins[i];if(p.direction!="input")bound.ports.push_back(pin(target,p.name,entry.line));
                    } else for(const auto& p:design.models[design.instances[target.id].model].pins)if(!p.internal&&(p.output||p.inout))bound.ports.push_back(pin(target,p.name,entry.line));
                }
                for(const auto& p:bound.ports)direction(p,"output",entry.line);
                if(bound.ports.empty())fail(entry.line,"DEVICE has no output pins");
            }
            ++stats.bound_entries;if(callback)callback(bound);
        }
    }
public:
    Binder(const GateDesign& d,const SdfBindOptions& o,const std::function<void(const SdfBoundEntry&)>& cb,const std::string& file):design(d),names(*d.timing_names),options(o),callback(cb),filename(file) {
        if(o.corner<0||o.corner>2||(o.numeric_preview&&!o.tick_fs))throw std::runtime_error("SDF binding requires a corner and nonzero target precision for numeric preview");
        if(o.tick_fs)(void)sdf_ticks("0",o.tick_fs,o.tick_fs);
        if(o.default_unit_fs)(void)sdf_ticks("0",*o.default_unit_fs,*o.default_unit_fs);
        stats.corner=o.corner;stats.tick_fs=o.tick_fs;stats.numeric_preview=o.numeric_preview;
        stats.topology_instances=d.instances.size();stats.named_instances=names.sorted_instances.size();stats.hierarchical_scopes=names.scopes.size();
        stats.name_pool_bytes=names.bytes.size();stats.name_index_bytes=4*(names.instance_names.size()+names.sorted_instances.size());
        model_pins.resize(d.models.size());scope_pins.resize(names.scopes.size());seen.resize(d.constants.size());
        for(size_t i=0;i<d.models.size();++i)for(uint32_t p=0;p<d.models[i].pins.size();++p)if(!model_pins[i].emplace(d.models[i].pins[p].name,p).second)throw std::runtime_error("duplicate timing model pin");
        for(uint32_t i=0;i<names.scopes.size();++i) {
            const auto& scope=names.scopes[i];
            if(!scopes.emplace(names.key(scope.name),i).second||names.find_instance(decode(names.key(scope.name)))>=0)throw std::runtime_error("ambiguous timing scope/instance path");
            for(uint32_t p=0;p<scope.pins.size();++p)if(!scope_pins[i].emplace(scope.pins[p].name,p).second)throw std::runtime_error("duplicate timing scope pin");
            types[scope.type].push_back({true,i});
        }
        for(auto id:names.sorted_instances)types[d.models[d.instances[id].model].name].push_back({false,id});
        for(const auto& inst:d.instances) {
            const auto& m=d.models[inst.model];auto first=inst.first;
            if(m.copy_width)for(size_t p=0;p<m.copy_width;++p)copies[d.pin_nets[first+p]].push_back(d.pin_nets[first+m.copy_width+p]);
            else if(m.name=="__assign__")copies[d.pin_nets[first]].push_back(d.pin_nets[first+1]);
        }
    }
    SdfBindStats run(std::istream& input) {
        SdfCallbacks cb;
        cb.header=[&](const SdfHeader& h) {
            divider=h.divider;auto unit=h.timescale_fs?h.timescale_fs:options.default_unit_fs;
            if(!unit)fail(1,"missing TIMESCALE; supply an explicit default SDF unit");
            stats.unit_fs=*unit;
        };
        cb.cell=[&](const SdfCell& c){cell(c);};cb.entry=[&](const SdfCell&,const SdfEntry& e){entry(e);};
        stats.parsed=parse_sdf(input,filename,cb);return stats;
    }
};
}
SdfBindStats bind_sdf(std::istream& input,const std::string& filename,const GateDesign& design,const SdfBindOptions& options,const std::function<void(const SdfBoundEntry&)>& callback) {
    if(!design.timing_names)throw std::runtime_error("gate topology has no timing names");
    return Binder(design,options,callback,filename).run(input);
}
SdfBindStats bind_sdf_file(const std::string& filename,const GateDesign& design,const SdfBindOptions& options,const std::function<void(const SdfBoundEntry&)>& callback) {
    std::ifstream file(filename,std::ios::binary);if(!file)throw std::runtime_error("cannot read SDF "+filename);return bind_sdf(file,filename,design,options,callback);
}
std::string SdfBindStats::report() const {
    std::ostringstream out;
    out<<"{\"schema\":\"dsim.sdf-binding.v1\",\"binding\":true,\"annotation\":false,\"arc_semantics_validated\":false,\"conditions_evaluated\":false,\"timing_checks_applied\":false,\"merge_applied\":false,\"duplicates_checked\":false,\"corner\":\""<<std::vector<const char*>{"min","typ","max"}.at(size_t(corner))<<"\",\"unit_fs\":"<<unit_fs<<",\"tick_fs\":"<<tick_fs<<",\"numeric_preview\":"<<(numeric_preview?"true":"false")<<",\"target_cells\":"<<target_cells<<",\"bound_entries\":"<<bound_entries<<",\"interconnects\":"<<interconnects<<",\"missing_selected_values\":"<<missing_values<<",\"negative_selected_values\":";
    if(numeric_preview)out<<negative_values;else out<<"null";
    out<<",\"topology_instances\":"<<topology_instances<<",\"named_instances\":"<<named_instances<<",\"hierarchical_scopes\":"<<hierarchical_scopes<<",\"name_pool_bytes\":"<<name_pool_bytes<<",\"name_index_bytes\":"<<name_index_bytes<<",\"wildcard_alias_targets\":"<<wildcard_alias_targets<<",\"parsed\":"<<parsed.report()<<"}\n";return out.str();
}
}
