#include "gate_compiler.hpp"
#include "gate_timing.hpp"
#include "gate_source.hpp"
#include "gate/gate_netlist_parser.hh"
#include "liberty/db_api.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <regex>

namespace dsim {
namespace {
std::string quote(const std::string& s) {
    std::ostringstream out; out<<'"';
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') out<<'\\'<<c;
        else if(c<32) out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<int(c)<<std::dec;
        else out<<c;
    }
    return out.str()+'"';
}
std::string verilog_id(const std::string& s) { return GateDesign::rtl_identifier(s)+" "; }
// Liberty precedence: inversion, XOR, AND (including adjacency), OR.
// Expressions become native C++ once per cell model, never per gate instance.
class Function {
    const std::string& text;
    const std::unordered_map<std::string,int>& inputs;
    std::set<int>* references;
    size_t pos=0; int depth=0;
    [[noreturn]] void fail() const { throw std::runtime_error("unsupported/invalid Liberty function near offset "+std::to_string(pos)+": "+text); }
    char peek() { while(pos<text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos; return pos<text.size()?text[pos]:0; }
    static std::string binary(const char* op,const std::string& a,const std::string& b) {
        return "binary_op<Binary::"+std::string(op)+">("+a+","+b+",1)";
    }
    std::string unary() {
        if(++depth>256) fail();
        std::string result;
        char c=peek();
        if(c=='!') { ++pos; result="inv(("+unary()+").size(1))"; }
        else if(c=='(') { ++pos; result=logical_or(); if(peek()!=')') fail(); ++pos; }
        else {
            size_t start=pos;
            while(pos<text.size() && (std::isalnum(static_cast<unsigned char>(text[pos])) || text[pos]=='_' || text[pos]=='$' || text[pos]=='[' || text[pos]==']')) ++pos;
            if(start==pos) fail();
            auto name=text.substr(start,pos-start);
            if(name=="0" || name=="1") result="V("+name+")";
            else {
                auto found=inputs.find(name); if(found==inputs.end()) fail();
                if(references && found->second>=0) references->insert(found->second);
                result=found->second==-1?"state.value()":found->second==-2?"state.value(true)":"s.get(p["+std::to_string(found->second)+"])";
            }
        }
        while(peek()=='\'') { ++pos; result="inv(("+result+").size(1))"; }
        --depth; return result;
    }
    std::string logical_xor() {
        auto result=unary();
        while(peek()=='^') { ++pos; result=binary("BitXor",result,unary()); }
        return result;
    }
    std::string logical_and() {
        auto result=logical_xor();
        for(;;) {
            char c=peek();
            if(c=='*'||c=='&') ++pos;
            else if(!(c=='('||c=='!'||std::isalnum(static_cast<unsigned char>(c))||c=='_')) break;
            result=binary("BitAnd",result,logical_xor());
        }
        return result;
    }
    std::string logical_or() {
        auto result=logical_and();
        while(peek()=='+'||peek()=='|') { ++pos; result=binary("BitOr",result,logical_and()); }
        return result;
    }
public:
    Function(const std::string& t,const std::unordered_map<std::string,int>& in,std::set<int>* refs=nullptr):text(t),inputs(in),references(refs) {}
    std::string compile() { auto value=logical_or(); if(peek()) fail(); return value; }
};
}

GateDesign parse_gate(const std::string& file,const std::string& top,const std::vector<std::string>& libraries,GateOptions options) {
    using Clock=std::chrono::steady_clock;
    auto source=options.source?options.source:std::make_shared<GateSource>(prepare_gate_source(file));
    if(source->text.empty())throw std::runtime_error("empty or already consumed gate source: "+file);
    if(source->file!=std::filesystem::weakly_canonical(std::filesystem::absolute(file)).string())
        throw std::runtime_error("prepared gate source does not match input file");
    auto library_start=Clock::now();
    edacraft::core::StringPool strings;
    edacraft::core::LibertyDB db;
    for(const auto& path:libraries) {
        std::string error;
        if(!edacraft::core::dbio::read_library_file(path,db,strings,&error))
            throw std::runtime_error(error);
    }
    std::unordered_map<std::string,const edacraft::core::LibertyCellData*> cells;
    for(uint32_t l=0;l<db.library_count();++l) for(uint32_t c=0;c<db.library(l).cells.size();++c) {
        const auto& cell=db.library(l).cells[c]; auto name=std::string(strings.view(cell.name));
        if(!cells.emplace(name,&cell).second) throw std::runtime_error("ambiguous Liberty cell "+name);
    }
    GateDesign d;d.wave_enabled=options.wave_names;d.timing_only=options.timing_only;
    d.preprocessing_report=source->report();
    const bool wave_names=options.wave_names;
    if(options.timing_names)d.timing_names=std::make_shared<GateTimingNames>();
    std::vector<uint32_t> network_names;
    te::Network network;
    te::GateNetlistParser parser(network); parser.set_simulation_mode(true);
    te::GateNetlistParser::SimulationPorts library_ports;
    for(const auto& entry:cells) for(const auto& pin:entry.second->pins) {
        auto dir=pin.direction==edacraft::core::PortDirection::Output?te::PortDirection::Output:
                 pin.direction==edacraft::core::PortDirection::Inout?te::PortDirection::Inout:te::PortDirection::Input;
        library_ports[entry.first].push_back({std::string(strings.view(pin.name)),dir});
    }
    parser.set_simulation_ports(std::move(library_ports));
    te::GateNetlistParser::LeafObserver leaf;
    if(d.timing_names)leaf=[&](te::InstanceId id,const std::vector<std::string>& path) {
        if(network_names.size()<=id.id)network_names.resize(size_t(id.id)+1,UINT32_MAX);
        network_names[id.id]=d.timing_names->append(path);
    };
    parser.set_timing_observers(std::move(leaf),[&](const std::vector<std::string>& path,const std::string& type,const std::vector<te::GateNetlistParser::TimingPort>& pins) {
        auto time=source->time(type);
        d.structural_precision_fs=d.structural_precision_fs?std::min(d.structural_precision_fs,time.precision_fs):time.precision_fs;
        if(!d.timing_names)return;
        GateTimingNames::Scope scope{d.timing_names->append(path),type,{},time};
        for(const auto& p:pins)scope.pins.push_back({p.name,p.direction==te::PortDirection::Input?"input":p.direction==te::PortDirection::Output?"output":"inout",int(p.net.id)});
        d.timing_names->scopes.push_back(std::move(scope));
    });
    auto start=Clock::now();
    double library_seconds=std::chrono::duration<double>(start-library_start).count();
    try {d.top=parser.parse_source(std::move(source->text),file,top);}
    catch(const std::exception& e) {
        std::string message=e.what();std::smatch match;
        if(std::regex_search(message,match,std::regex("line ([0-9]+)"))) {
            auto at=source->location(std::stoull(match[1]));
            throw std::runtime_error(at.file+":"+std::to_string(at.line)+": "+message);
        }
        throw std::runtime_error(file+": "+message);
    }
    d.top_time=source->time(d.top);
    d.structural_precision_fs=d.structural_precision_fs?std::min(d.structural_precision_fs,d.top_time.precision_fs):d.top_time.precision_fs;
    auto parsed=Clock::now();
    d.parse_seconds=std::chrono::duration<double>(parsed-start).count();
    d.network_nets=network.net_count(); d.network_pins=network.pin_count(); d.network_instances=network.instance_count();
    if(network.net_count()>size_t(std::numeric_limits<int>::max())) throw std::runtime_error("gate net ID overflow");
    d.constants.resize(network.net_count(),-1);
    if(wave_names)d.wave_names.reserve(network.net_count());
    for(uint32_t i=0;i<network.net_count();++i) {
        auto name=network.net_name(te::NetId{i});
        if(wave_names)d.wave_names.emplace_back(name);
        auto value=network.net(te::NetId{i}).constant_value;
        if(value>=0) d.constants[i]=value;
        else if(name=="1'bx"||name=="1'bX") d.constants[i]=2;
        else if(name=="1'bz"||name=="1'bZ") d.constants[i]=3;
    }
    for(const auto& p:parser.top_ports()) {
        GatePort port; port.name=p.name;
        port.direction=p.direction==te::PortDirection::Input?"input":p.direction==te::PortDirection::Output?"output":"inout";
        port.packed=p.bits.size()!=1 || p.bits.front()!=p.name;
        if(port.packed) {
            auto index=[&](const std::string& bit){return std::stoi(bit.substr(p.name.size()+1));};
            port.high=index(p.bits.front()); port.low=index(p.bits.back());
            if(!options.timing_only && (p.bits.size()>1048576 || port.high<port.low)) throw std::runtime_error("gate top ports currently require descending width 1..1048576: "+p.name);
        }
        for(const auto& bit:p.bits) {
            auto net=network.find_net(bit); if(!net) throw std::runtime_error("missing gate top port net "+bit);
            port.nets.push_back(int(net->id));
        }
        d.ports.push_back(std::move(port));
    }
    if(d.timing_names) {
        GateTimingNames::Scope root{d.timing_names->append({}),d.top,{},d.top_time};
        for(const auto& p:d.ports)for(size_t bit=0;bit<p.nets.size();++bit) {
            auto name=p.packed?p.name+"["+std::to_string(p.high+(p.high<=p.low?int(bit):-int(bit)))+"]":p.name;
            root.pins.push_back({name,p.direction,p.nets[bit]});
        }
        d.timing_names->scopes.push_back(std::move(root));
    }
    std::unordered_map<uint32_t,uint32_t> models;
    std::unordered_set<uint32_t> instance_names;
    for(uint32_t i=0;i<network.instance_count();++i) {
        const auto& inst=network.instance(te::InstanceId{i});
        if(!instance_names.insert(inst.name).second) throw std::runtime_error("duplicate flattened gate instance "+std::string(network.instance_name(te::InstanceId{i})));
        auto cellname=std::string(network.cell_name(inst.cell));
        if(cellname=="__top__") continue;
        auto found=models.find(inst.cell.id);
        if(found==models.end()) {
            GateModel model; model.name=cellname;
            if(cellname=="__assign__") model.pins={{"A",false,{}},{"X",true,"s.get(p[0])"}};
            else if(cellname.rfind("__dsim_copy_",0)==0) {
                size_t width=std::stoul(cellname.substr(12));
                if(!width || width>1000000) throw std::runtime_error("invalid structural copy model");
                model.copy_width=width;
                for(size_t bit=0;bit<width;++bit) model.pins.push_back({"A"+std::to_string(bit),false,{}});
                for(size_t bit=0;bit<width;++bit) model.pins.push_back({"X"+std::to_string(bit),true,{}});
            } else {
                auto lib=cells.find(cellname);
                if(lib==cells.end()) throw std::runtime_error("unbound gate cell "+cellname+" at "+std::string(network.instance_name(te::InstanceId{i})));
                const auto& cell=*lib->second;
                if(!options.timing_only && (cell.sequential_unsupported || cell.sequential_kind>2))
                    throw std::runtime_error("unsupported Liberty sequential description: "+cellname);
                model.sequential_kind=options.timing_only?0:int(cell.sequential_kind);
                if(!options.timing_only && !model.sequential_kind && (cell.ff_state!=UINT32_MAX || cell.ff_clocked_on!=UINT32_MAX || cell.ff_enable!=UINT32_MAX))
                    throw std::runtime_error("incomplete legacy Liberty sequential metadata: "+cellname);
                std::unordered_map<std::string,int> inputs;
                std::set<int> watches;
                std::unordered_set<std::string> pin_names;
                for(const auto& pin:cell.pins) {
                    auto name=std::string(strings.view(pin.name));
                    if(!pin_names.insert(name).second) throw std::runtime_error("duplicate Liberty pin "+cellname+"."+name);
                    if(!options.timing_only && pin.direction==edacraft::core::PortDirection::Inout) throw std::runtime_error("inout Liberty cell pins are not supported yet: "+cellname+"."+name);
                    if(pin.direction==edacraft::core::PortDirection::Input) inputs.emplace(name,int(model.pins.size()));
                    model.pins.push_back({name,pin.direction==edacraft::core::PortDirection::Output,{},pin.direction==edacraft::core::PortDirection::Inout,pin.direction==edacraft::core::PortDirection::Internal});
                }
                if(model.sequential_kind) {
                    auto require=[&](uint32_t id,const char* field) {
                        if(id==UINT32_MAX || strings.view(id).empty()) throw std::runtime_error("missing Liberty sequential "+std::string(field)+": "+cellname);
                        return std::string(strings.view(id));
                    };
                    auto control=model.sequential_kind==1?cell.ff_clocked_on:cell.ff_enable;
                    auto next=model.sequential_kind==1?cell.ff_next_state:cell.latch_data_in;
                    if((model.sequential_kind==1 && (cell.ff_enable!=UINT32_MAX || cell.latch_data_in!=UINT32_MAX)) ||
                       (model.sequential_kind==2 && (cell.ff_clocked_on!=UINT32_MAX || cell.ff_next_state!=UINT32_MAX)))
                        throw std::runtime_error("mixed Liberty ff/latch attributes: "+cellname);
                    // An SR latch without enable/data is a valid storage element.
                    bool sr=model.sequential_kind==2 && control==UINT32_MAX && next==UINT32_MAX;
                    model.control=sr?"V(0)":Function(require(control,"clocked_on/enable"),inputs,&watches).compile();
                    model.clear=cell.ff_clear==UINT32_MAX?"V(0)":Function(std::string(strings.view(cell.ff_clear)),inputs,&watches).compile();
                    model.preset=cell.ff_preset==UINT32_MAX?"V(0)":Function(std::string(strings.view(cell.ff_preset)),inputs,&watches).compile();
                    if(sr && cell.ff_clear==UINT32_MAX && cell.ff_preset==UINT32_MAX)
                        throw std::runtime_error("empty Liberty latch: "+cellname);
                    auto state=require(cell.ff_state,"state variable"),inverse=require(cell.ff_state_inverse,"inverse state variable");
                    if(state==inverse || pin_names.count(state) || pin_names.count(inverse))
                        throw std::runtime_error("invalid Liberty state variable names: "+cellname);
                    inputs.emplace(state,-1); inputs.emplace(inverse,-2);
                    model.next=sr?"state.value()":Function(require(next,"next_state/data_in"),inputs,model.sequential_kind==2?&watches:nullptr).compile();
                    auto conflict=[&](uint32_t id) {
                        if(id==UINT32_MAX) return 'X';
                        auto value=std::string(strings.view(id));
                        if(value.size()!=1 || std::string("LHNTX").find(value[0])==std::string::npos)
                            throw std::runtime_error("invalid Liberty clear_preset value: "+cellname);
                        return value[0];
                    };
                    bool both=cell.ff_clear!=UINT32_MAX && cell.ff_preset!=UINT32_MAX;
                    bool attrs=cell.clear_preset_var1!=UINT32_MAX || cell.clear_preset_var2!=UINT32_MAX;
                    if(both!=attrs) throw std::runtime_error("Liberty clear/preset requires conflict attributes: "+cellname);
                    model.conflict1=conflict(cell.clear_preset_var1); model.conflict2=conflict(cell.clear_preset_var2);
                }
                std::set<int> output_inputs;
                for(size_t k=0;k<cell.pins.size();++k) if(!options.timing_only && model.pins[k].output) {
                    const auto& pin=cell.pins[k];
                    if(pin.function==UINT32_MAX) throw std::runtime_error("missing Liberty output function "+cellname+"."+model.pins[k].name);
                    auto expression=std::string(strings.view(pin.function));
                    model.pins[k].expression=Function(expression,inputs,&output_inputs).compile();
                    if(pin.three_state!=UINT32_MAX) {
                        auto disable=std::string(strings.view(pin.three_state));
                        model.pins[k].expression="tristate("+Function(disable,inputs,&output_inputs).compile()+","+model.pins[k].expression+",1)";
                    }
                }
                model.output_reads_inputs=!output_inputs.empty();
                watches.insert(output_inputs.begin(),output_inputs.end());
                if(model.sequential_kind) model.wait_inputs.assign(watches.begin(),watches.end());
                if(!options.timing_only && std::none_of(model.pins.begin(),model.pins.end(),[](const auto& p){return p.output;})) throw std::runtime_error("Liberty cell has no functional outputs: "+cellname);
            }
            if(!model.sequential_kind) for(size_t k=0;k<model.pins.size();++k) if(!model.pins[k].output) model.wait_inputs.push_back(int(k));
            auto id=uint32_t(d.models.size()); d.models.push_back(std::move(model)); found=models.emplace(inst.cell.id,id).first;
        }
        const auto& model=d.models[found->second];
        std::vector<int> pins(model.pins.size(),-1);
        for(auto id:inst.pins) {
            auto name=network.pin_name(id);
            size_t k=0;
            if(model.copy_width) {
                auto bit=std::stoul(std::string(name.substr(1)));
                if(bit>=model.copy_width || (name.front()!='A' && name.front()!='X')) throw std::runtime_error("invalid structural copy pin");
                k=bit+(name.front()=='X'?model.copy_width:0);
            } else {
                auto formal=std::find_if(model.pins.begin(),model.pins.end(),[&](const auto& p){return p.name==name;});
                if(formal==model.pins.end()) throw std::runtime_error("unknown pin "+cellname+"."+std::string(name));
                k=size_t(formal-model.pins.begin());
            }
            const auto& formal=model.pins[k];
            if(pins[k]!=-1) throw std::runtime_error("duplicate connected pin "+cellname+"."+std::string(name));
            auto net=network.pin(id).net;
            if(te::valid(net)) {
                if(formal.output && d.constants[net.id]>=0)
                    throw std::runtime_error("gate output cannot drive a constant: "+cellname+"."+std::string(name));
                pins[k]=int(net.id);
            }
        }
        for(auto& id:pins) if(id<0) { id=int(d.constants.size()); d.constants.push_back(-1); }
        if(d.pin_nets.size()+pins.size()>size_t(std::numeric_limits<int>::max())) throw std::runtime_error("gate pin ID overflow");
        if(d.timing_names)d.timing_names->instance_names.push_back(i<network_names.size()?network_names[i]:UINT32_MAX);
        d.instances.push_back({found->second,uint32_t(d.pin_nets.size())});
        d.pin_nets.insert(d.pin_nets.end(),pins.begin(),pins.end());
    }
    if(d.timing_names)d.timing_names->finalize();
    d.bind_seconds=library_seconds+std::chrono::duration<double>(Clock::now()-parsed).count();
    return d;
}

std::string GateDesign::rtl_identifier(const std::string& name) {
    bool simple=!name.empty() && (std::isalpha(static_cast<unsigned char>(name[0])) || name[0]=='_');
    for(unsigned char c:name) simple=simple&&(std::isalnum(c)||c=='_'||c=='$');
    return simple?name:"\\"+name;
}

std::string GateDesign::stub() const {
    if(timing_only)throw std::runtime_error("timing-only topology cannot generate RTL stubs");
    std::ostringstream out; out<<"module "<<verilog_id(top)<<"(";
    for(size_t i=0;i<ports.size();++i) { if(i) out<<","; out<<verilog_id(ports[i].name); }
    out<<");\n";
    for(const auto& p:ports) {
        out<<p.direction<<" "; if(p.packed) out<<"["<<p.high<<":"<<p.low<<"] ";
        out<<verilog_id(p.name)<<";\n";
    }
    out<<"endmodule\n"; return out.str();
}

std::string GateDesign::report() const {
    std::ostringstream out;
    out<<"{\"schema\":\"dsim.gate.v1\",\"frontend\":\"gate-network\",\"top\":"<<quote(top)
       <<",\"functional_binding\":"<<(timing_only?"false":"true")<<",\"gate_preprocessing\":"<<preprocessing_report
       <<",\"structural_precision_fs\":"<<structural_precision_fs<<",\"timing_name_bytes\":"<<(timing_names?timing_names->bytes.size():0)<<",\"timing_named_instances\":"<<(timing_names?timing_names->sorted_instances.size():0)
       <<",\"network_net_count\":"<<network_nets<<",\"network_pin_count\":"<<network_pins
       <<",\"network_instance_count\":"<<network_instances<<",\"net_count\":"<<constants.size()
       <<",\"instance_count\":"<<instances.size()<<",\"pin_count\":"<<pin_nets.size()
       <<",\"model_count\":"<<models.size()<<",\"parse_seconds\":"<<parse_seconds<<",\"bind_seconds\":"<<bind_seconds<<",\"ports\":[";
    size_t storage=0; for(const auto& i:instances) if(models[i.model].sequential_kind) ++storage;
    // Keep the original report fields, adding storage accounting below.
    bool first=true;
    for(const auto& p:ports) { if(!first) out<<","; first=false;
        out<<"{\"name\":"<<quote(p.name)<<",\"direction\":"<<quote(p.direction)<<",\"width\":"<<p.nets.size()<<",\"msb\":"<<p.high<<",\"lsb\":"<<p.low<<",\"nets\":[";
        for(size_t i=0;i<p.nets.size();++i) { if(i) out<<","; out<<p.nets[i]; } out<<"]}";
    }
    out<<"],\"models\":[";
    for(size_t i=0;i<models.size();++i) { if(i) out<<","; out<<quote(models[i].name); }
    out<<"],\"model_wait_pin_count\":[";
    for(size_t i=0;i<models.size();++i) { if(i) out<<","; out<<models[i].wait_inputs.size(); }
    out<<"],\"model_output_input_dependent\":[";
    for(size_t i=0;i<models.size();++i) {if(i)out<<",";out<<(models[i].output_reads_inputs?"true":"false");}
    out<<"],\"sequential_instance_count\":"<<storage<<",\"sequential_state_bit_count\":"<<2*storage;
    if(timing)out<<",\"sdf_runtime\":true,\"module_path_arcs\":"<<timing->arcs.size()<<",\"disabled_sdf_timing_checks\":"<<timing->disabled_checks;
    if(timing&&timing->conditional_paths)out<<",\"conditional_module_paths\":true,\"path_conditions\":"<<timing->conditions.size()-1;
    if(timing&&!timing->checks.empty())out<<",\"timing_checks\":"<<timing->checks.size()<<",\"timing_check_updates\":"<<timing->check_updates<<",\"negative_check_limits_clamped\":"<<timing->negative_check_limits_clamped;
    if(timing&&timing->interconnect_updates)out<<",\"interconnect_pins\":"<<std::count_if(timing->interconnects.begin(),timing->interconnects.end(),[](const auto& p){return p.interconnect;})<<",\"interconnect_updates\":"<<timing->interconnect_updates;
    if(timing&&timing->port_updates)out<<",\"input_delay_pins\":"<<timing->interconnects.size()<<",\"port_delay_pins\":"<<timing->port_pins<<",\"port_delay_updates\":"<<timing->port_updates;
    if(timing&&timing->device_updates)out<<",\"device_delay_updates\":"<<timing->device_updates;
    if(!partitioning_report.empty())out<<",\"partition_analysis\":"<<partitioning_report;
    if(batch_enabled)out<<",\"batch_execution\":true";
    if(scalar_timing_enabled)out<<",\"scalar_timing\":true";
    if(sdf_jobs_enabled)out<<",\"sdf_jobs\":true";
    if(path_dictionary_enabled)out<<",\"path_delay_dictionary\":true";
    if(fold_zero_inputs&&timing)out<<",\"zero_input_pins_folded\":"<<std::count_if(timing->interconnects.begin(),timing->interconnects.end(),[](const auto& p){return std::all_of(p.quanta.begin(),p.quanta.end(),[](auto q){return q==0;});});
    out<<"}"; return out.str();
}

namespace {
struct LookupOutput {std::string table,drive;};
// Small pure output expressions have a complete four-state truth table. Build
// it from the original native V expression, then read inputs separately for
// EACH output: an earlier drive may change an aliased input of a later output.
LookupOutput lookup_output(size_t model,size_t output,const std::string& original) {
    if(original.find("state.")!=std::string::npos)return {};
    const std::string marker="s.get(p[";std::set<size_t> pins;
    for(size_t pos=0;(pos=original.find(marker,pos))!=std::string::npos;) {
        auto begin=pos+marker.size(),end=original.find("])",begin);
        if(end==std::string::npos||end==begin||original.substr(begin,end-begin).find_first_not_of("0123456789")!=std::string::npos)
            throw std::runtime_error("invalid generated Liberty pin read");
        pins.insert(std::stoull(original.substr(begin,end-begin)));pos=end+2;
    }
    if(pins.size()<2||pins.size()>4)return {};
    auto name="gate_lut_"+std::to_string(model)+"_"+std::to_string(output);
    auto size=size_t(1)<<(2*pins.size());std::string expression=original;
    std::ostringstream declarations,runtime;size_t index=0;
    for(auto pin:pins) {
        auto p=std::to_string(pin),shift=std::to_string(2*index);
        auto needle="s.get(p["+p+"])",replacement="input_"+p;
        for(size_t pos=0;(pos=expression.find(needle,pos))!=std::string::npos;pos+=replacement.size())
            expression.replace(pos,needle.size(),replacement);
        declarations<<"const V input_"<<p<<"((i>>"<<shift<<")&1,(i>>"<<2*index+1<<")&1,1);";
        runtime<<"{const V value=s.get(p["<<p<<"]);index|=uint32_t((value.a&1)|((value.b&1)<<1))<<"<<shift<<";}";
        ++index;
    }
    std::ostringstream table,drive;
    table<<"static const std::array<uint8_t,"<<size<<"> "<<name<<"=[] { std::array<uint8_t,"<<size
         <<"> table{};for(uint32_t i=0;i<"<<size<<";++i){"<<declarations.str()<<"const V result="<<expression
         <<";table[i]=uint8_t((result.a&1)|((result.b&1)<<1));}return table;}();\n";
    drive<<"{uint32_t index=0;"<<runtime.str()<<"const uint8_t bits="<<name<<"[index];s.drive(p["<<output
         <<"],driver+"<<output<<",V(bits&1,bits>>1,1));}\n";
    return {table.str(),drive.str()};
}
std::vector<uint8_t> compact_candidates(const GateDesign& design) {
    std::vector<uint8_t> drivers(design.constants.size(),0),eligible(design.constants.size(),0);
    for(const auto& cell:design.instances) {
        const auto& model=design.models.at(cell.model);
        for(size_t k=0;k<model.pins.size();++k)if(model.pins[k].output) {
            auto net=size_t(design.pin_nets.at(cell.first+k));
            auto& count=drivers.at(net);if(count<2)++count;
        }
    }
    for(size_t i=0;i<eligible.size();++i)eligible[i]=drivers[i]==1&&design.constants[i]<0;
    for(const auto& port:design.ports)for(int net:port.nets)eligible.at(size_t(net))=0;
    return eligible;
}
struct PathDelayDictionary {
    std::vector<std::array<uint64_t,12>> tables;
    std::vector<uint32_t> indices;
    PathDelayDictionary(const GateTimingData& timing,uint64_t precision_fs) {
        std::map<std::array<uint64_t,12>,uint32_t> index;
        indices.reserve(timing.arcs.size());
        for(const auto& arc:timing.arcs) {
            auto ticks=arc.ticks(precision_fs);
            auto found=index.find(ticks);
            if(found==index.end()) {
                if(tables.size()>UINT32_MAX)throw std::runtime_error("path delay dictionary index overflow");
                found=index.emplace(ticks,uint32_t(tables.size())).first;
                tables.push_back(ticks);
            }
            indices.push_back(found->second);
        }
    }
    void emit(std::ostream& out) const {
        out<<"static const uint64_t path_delay_tables[][12]={";
        for(const auto& table:tables) {out<<"{";for(auto tick:table)out<<tick<<"ULL,";out<<"},";}
        out<<"{0}};\n";
    }
};
void conditional_paths(std::ostream& out,const GateDesign& design,uint64_t precision_fs,const PathDelayDictionary* dictionary) {
    const auto& timing=*design.timing;
    out<<"static const ModulePathCondition path_conditions[]={+[](Sim&,const int*){return true;},";
    for(size_t i=1;i<timing.conditions.size();++i) {
        const auto& condition=timing.conditions[i];const auto& model=design.models.at(condition.model);
        auto code=timing_condition_code(condition.expression,[&](const std::string& name) {
            auto pin=std::find_if(model.pins.begin(),model.pins.end(),[&](const auto& p){return p.name==name;});
            if(pin==model.pins.end())throw std::runtime_error("unknown path condition pin: "+name);
            return "s.get(p["+std::to_string(pin-model.pins.begin())+"])";
        });
        // Specify conditions use their LSB and treat X/Z as enabled. This is
        // deliberately different from the timing-check condition convention.
        out<<"+[](Sim& s,const int* p){(void)s;(void)p;return ("<<code<<").bit(0)!=0;},";
    }
    out<<"};\n";
    if(dictionary)dictionary->emit(out);
    out<<"static const "<<(dictionary?"DictionaryConditionalModulePathArc":"ConditionalModulePathArc")<<" path_arcs[]={";
    for(size_t i=0;i<timing.arcs.size();++i) {
        const auto& arc=timing.arcs[i];out<<"{{"<<arc.input<<",";
        if(dictionary)out<<dictionary->indices[i]<<","<<unsigned(arc.edge)<<"},";
        else {out<<unsigned(arc.edge)<<",{";for(auto tick:arc.ticks(precision_fs))out<<tick<<"ULL,";out<<"}},";}
        out<<arc.first<<","<<arc.condition<<","<<(arc.ifnone?"true":"false")<<"},";
    }
    out<<(dictionary?"{{0,0,0},0,0,false}};\n":"{{0,0,{}},0,0,false}};\n")<<"struct PathOutput{uint32_t pin,first,count;};static const PathOutput path_outputs[]={";
    for(size_t i=0;i<timing.arcs.size();) {
        auto first=i;auto output=timing.arcs[i].output;while(i<timing.arcs.size()&&timing.arcs[i].output==output)++i;
        out<<"{"<<output<<","<<first<<","<<i-first<<"},";
    }
    out<<"{0,0,0}};\nstruct PathContext{std::shared_ptr<const std::vector<int>> pins;struct Output{int raw,site;uint32_t channel;uint8_t previous=2;};std::vector<Output> outputs;};\n"
       <<"auto path_state=std::make_shared<PathContext>();path_state->pins=std::make_shared<const std::vector<int>>(state->pins);auto path_context=s.compiled_context(path_state);\n"
       <<"auto path_handler=s.compiled_handler(path_context,+[](Sim& s,void* raw,uint32_t i){auto& state=*static_cast<PathContext*>(raw);auto& output=state.outputs[i];auto descriptor=path_outputs[i];";
    if(!design.sdf_jobs_enabled)out<<"s.arm_fixed_wait(output.site);";
    if(design.scalar_timing_enabled)out<<"int next=s.get_scalar(output.raw);";
    else out<<"auto value=s.get(output.raw);int next=value.bit(0);";
    out<<"if(output.previous==next)return;auto delay="<<(dictionary?"dictionary_conditional_module_path_delay":"conditional_module_path_delay")<<"(s,state.pins->data(),path_arcs+descriptor.first,descriptor.count,output.previous,next,path_conditions"<<(dictionary?",path_delay_tables":"")<<");output.previous=uint8_t(next);";
    if(design.scalar_timing_enabled)out<<"s.drive_scalar_after(output.channel,uint8_t(next),delay);";
    else out<<"s.drive_after(output.channel,value,delay);";
    out<<"});\nfor(size_t i=0;path_outputs[i].count;++i){auto output=path_outputs[i];auto raw=s.signal(1,true);s.set(raw,V::x(1));auto channel=s.module_path_driver(state->pins[output.pin],driver+int(output.pin));state->pins[output.pin]=raw;";
    if(design.sdf_jobs_enabled)out<<"s.compiled_sdf_job(path_handler,uint32_t(i),raw);int site=-1;";
    else out<<"auto process=s.compiled_process(path_handler,uint32_t(i));auto site=s.add_fixed_wait(process,{{raw,0}});";
    out<<"path_state->outputs.push_back({raw,site,channel,2});}\n";
}
}
std::string GateDesign::cpp(uint64_t precision_fs,bool parallel_wave) const {
    if(sdf_jobs_enabled&&(!scalar_timing_enabled||!timing))throw std::runtime_error("SDF jobs require scalar annotated timing");
    if(path_dictionary_enabled&&!timing)throw std::runtime_error("path delay dictionary requires annotated timing");
    if(timing_only)throw std::runtime_error("timing-only topology cannot generate simulation code");
    std::ostringstream out,tables; out<<"#include <memory>\n#include <array>\nusing namespace dsim;\n";
    for(size_t i=0;i<models.size();++i) {
        if(models[i].sequential_kind) {
            const auto& m=models[i];
            out<<"static void gate_sample_"<<i<<"(Sim& s,const int* p,GateState& state) {\n"
               <<"state.capture("<<(m.sequential_kind==2?"true":"false")<<","<<m.control<<","<<m.next<<","<<m.clear<<","<<m.preset<<",'"<<m.conflict1<<"','"<<m.conflict2<<"');\n}\n";
        }
        out<<"static void gate_eval_"<<i<<"(Sim& s,const int* p,int driver"<<(models[i].sequential_kind?",GateState& state":"")<<") {\n";
        if(models[i].copy_width) {
            auto width=models[i].copy_width;
            out<<"s.drive_copies(p+"<<width<<",p,driver+"<<width<<","<<width<<");\n";
        } else for(size_t k=0;k<models[i].pins.size();++k) if(models[i].pins[k].output) {
            auto lookup=lookup_output(i,k,models[i].pins[k].expression);
            if(!lookup.table.empty()){tables<<lookup.table;out<<lookup.drive;}
            else out<<"s.drive(p["<<k<<"],driver+"<<k<<","<<models[i].pins[k].expression<<");\n";
        }
        out<<"}\n";
    }
    if(wave_enabled&&parallel_enabled&&parallel_wave)out<<"template<class Wave>\n";
    out<<"static void install_gate(Sim& s,const std::vector<std::pair<int,int>>& ports,int driver";
    if(wave_enabled)out<<(parallel_enabled&&parallel_wave?",Wave& wave,const std::vector<std::string>& wave_scope":",WaveCapture& wave,const std::vector<std::string>& wave_scope");
    out<<") {\n"
       <<"static const int8_t constants[]={";
    for(auto c:constants) out<<int(c)<<","; out<<"-1};\n";
    out<<"static const uint32_t pin_nets[]={"; for(auto n:pin_nets) out<<n<<","; out<<"0};\n";
    out<<"struct Cell { uint32_t model,first,seq; }; static const Cell cells[]={";
    size_t sequential_count=0;
    for(auto i:instances) {
        out<<"{"<<i.model<<","<<i.first<<",";
        if(models[i.model].sequential_kind)out<<sequential_count++;else out<<"UINT32_MAX";
        out<<"},";
    }
    out<<"{0,0,UINT32_MAX}};\n";
    out<<"using Eval=void(*)(Sim&,const int*,int); static const Eval eval[]={";
    for(size_t i=0;i<models.size();++i) { if(models[i].sequential_kind) out<<"nullptr,"; else out<<"gate_eval_"<<i<<","; } out<<"nullptr};\n";
    out<<"using SeqEval=void(*)(Sim&,const int*,int,GateState&); static const SeqEval seq_eval[]={";
    for(size_t i=0;i<models.size();++i) { if(models[i].sequential_kind) out<<"gate_eval_"<<i<<","; else out<<"nullptr,"; } out<<"nullptr};\n";
    out<<"using Sample=void(*)(Sim&,const int*,GateState&); static const Sample sample[]={";
    for(size_t i=0;i<models.size();++i) { if(models[i].sequential_kind) out<<"gate_sample_"<<i<<","; else out<<"nullptr,"; } out<<"nullptr};\n";
    out<<"static const bool is_latch[]={"; for(const auto& m:models) out<<(m.sequential_kind==2?"true,":"false,"); out<<"false};\n";
    out<<"static const bool output_reads_inputs[]={"; for(const auto& m:models) out<<(m.output_reads_inputs?"true,":"false,"); out<<"false};\n";
    out<<"static const uint32_t input_first[]={"; size_t count=0;
    for(const auto& m:models) {out<<count<<","; count+=m.wait_inputs.size();} out<<count<<"};\n";
    out<<"static const uint32_t inputs[]={";
    for(const auto& m:models) for(auto k:m.wait_inputs) out<<k<<",";
    out<<"0};\n";
    out<<"struct State { std::vector<int> pins,sites; std::vector<GateState> seq; int driver=0; "<<(batch_enabled?"uint32_t batch_handler=0; ":"")<<"}; auto state=std::make_shared<State>(); state->driver=driver;\nstd::vector<int> nets; nets.reserve("<<constants.size()<<");\n"
       <<"static const uint8_t compact[]={";
    for(auto eligible:compact_candidates(*this))out<<int(eligible)<<",";
    out<<"0}; for(size_t i=0;i<"<<constants.size()<<";++i) nets.push_back(compact[i]?s.compact_net():s.signal(1,true));\nsize_t port=0;\n";
    if(wave_enabled) {
        out<<"if(wave.enabled()) { static const char* const wave_names[]={";
        for(const auto& name:wave_names) {
            // Scalar top ports already have a same-scope RTL stub declaration.
            // Both runtime signals are linked, so record the visible port once.
            bool port=std::any_of(ports.begin(),ports.end(),[&](const auto& p){return !p.packed&&p.name==name;});
            out<<(port?"nullptr":quote(name))<<",";
        }
        out<<"nullptr}; for(size_t i=0;i<"<<wave_names.size()<<";++i) if(constants[i]<0 && wave_names[i]) wave.gate_net(nets[i],wave_scope,wave_names[i]); }\n";
    }
    for(const auto& p:ports) for(size_t bit=0;bit<p.nets.size();++bit)
        out<<"s.connect_net(nets["<<p.nets[bit]<<"],0,ports.at(port).first,ports.at(port).second); ++port;\n";
    out<<"state->pins.reserve("<<pin_nets.size()<<"); for(size_t i=0;i<"<<pin_nets.size()<<";++i) state->pins.push_back(nets[pin_nets[i]]);\nstate->sites.resize("<<instances.size()<<");\n"
       <<"state->seq.resize("<<sequential_count<<"); auto context=s.compiled_context(state);\n"
       ;
    // Only final rounded IC/PORT triples qualify. Module paths and checks
    // continue to observe the original source, including its path timestamp.
    if(fold_zero_inputs&&!timing)throw std::runtime_error("zero input folding requires annotated timing");
    const std::vector<AnnotatedInterconnect> empty_inputs;
    const auto& all_inputs=timing?timing->interconnects:empty_inputs;
    std::vector<AnnotatedInterconnect> retained_inputs,folded_inputs;
    if(fold_zero_inputs)for(const auto& input:all_inputs) {
        auto zero=std::all_of(input.quanta.begin(),input.quanta.end(),[](auto q){return q==0;});
        (zero?folded_inputs:retained_inputs).push_back(input);
    }
    const auto& delayed_inputs=fold_zero_inputs?retained_inputs:all_inputs;
    auto emit_input_wave_names=[&](const std::vector<AnnotatedInterconnect>& inputs) {
            out<<"static const char* const input_names[]={";
            for(const auto& input:inputs) {
                const auto& cell=instances.at(input.instance);
                out<<quote(models.at(cell.model).pins.at(input.pin-cell.first).name)<<",";
            }
            out<<"nullptr};\nstatic const uint32_t input_scope_first[]={0,";
            size_t total=0;
            std::vector<std::string> components;
            for(const auto& input:inputs) {
                auto key=timing_names->key(timing_names->instance_names.at(input.instance));
                for(size_t offset=0;offset<key.size();) {
                    if(key.size()-offset<4)throw std::runtime_error("invalid INTERCONNECT instance name");
                    uint32_t length=0;for(int byte=0;byte<4;++byte)length|=uint32_t(static_cast<unsigned char>(key[offset+byte]))<<(8*byte);
                    offset+=4;if(length>key.size()-offset)throw std::runtime_error("invalid INTERCONNECT name component");
                    components.emplace_back(key.substr(offset,length));offset+=length;++total;
                }
                out<<total<<",";
            }
            out<<"0};\nstatic const char* const input_scope_parts[]={";
            for(const auto& part:components)out<<quote(part)<<",";
            out<<"nullptr};\n";
    };
    if(wave_enabled&&!folded_inputs.empty()) {
        out<<"if(wave.enabled()){\n";
        emit_input_wave_names(folded_inputs);
        out<<"static const uint32_t folded_input_pins[]={";
        for(const auto& input:folded_inputs)out<<input.pin<<",";
        out<<"0};for(size_t i=0;i<"<<folded_inputs.size()<<";++i){auto scope=wave_scope;for(size_t p=input_scope_first[i];p<input_scope_first[i+1];++p)scope.push_back(input_scope_parts[p]);wave.gate_net(state->pins[folded_input_pins[i]],scope,input_names[i]);}}\n";
    }
    if(!delayed_inputs.empty()) {
        out<<"struct InputDelay {uint32_t pin;uint64_t rise,fall,off;}; static const InputDelay input_delays[]={";
        for(const auto& input:delayed_inputs) {
            if(!precision_fs||input.precision_fs%precision_fs)throw std::runtime_error("invalid INTERCONNECT global precision");
            auto scale=input.precision_fs/precision_fs;
            out<<"{"<<input.pin<<",";
            for(auto value:input.quanta) {
                if(value>UINT64_MAX/scale)throw std::runtime_error("INTERCONNECT global tick overflow");
                out<<value*scale<<"ULL,";
            }
            out<<"},";
        }
        out<<"{0,0,0,0}};\nstruct InputContext {struct Pin {int source,site;uint32_t channel;uint8_t previous=2;};std::vector<Pin> pins;};\n"
           <<"auto input_state=std::make_shared<InputContext>();auto input_context=s.compiled_context(input_state);\n"
           <<(scalar_timing_enabled?
              "auto input_handler=s.compiled_handler(input_context,+[](Sim& s,void* raw,uint32_t i){auto& input=static_cast<InputContext*>(raw)->pins[i];"+std::string(sdf_jobs_enabled?"":"s.arm_fixed_wait(input.site);")+"int next=s.get_scalar(input.source);if(next==input.previous)return;input.previous=uint8_t(next);auto delay=input_delays[i];uint64_t ticks=next==1?delay.rise:next==0?delay.fall:next==3?delay.off:std::min(delay.rise,std::min(delay.fall,delay.off));s.drive_scalar_after(input.channel,uint8_t(next),ticks);});\n":
              "auto input_handler=s.compiled_handler(input_context,+[](Sim& s,void* raw,uint32_t i){auto& input=static_cast<InputContext*>(raw)->pins[i];"+std::string(sdf_jobs_enabled?"":"s.arm_fixed_wait(input.site);")+"auto value=s.get(input.source);int next=value.bit(0);if(next==input.previous)return;input.previous=uint8_t(next);auto delay=input_delays[i];uint64_t ticks=next==1?delay.rise:next==0?delay.fall:next==3?delay.off:std::min(delay.rise,std::min(delay.fall,delay.off));s.drive_after(input.channel,value,ticks);});\n");
        if(wave_enabled) {
            emit_input_wave_names(delayed_inputs);
        }
        out<<"for(size_t i=0;i<"<<delayed_inputs.size()<<";++i){auto descriptor=input_delays[i];int source=state->pins[descriptor.pin];int target=s.compact_net();s.set(target,V::z(1));s.set(target,V::x(1));auto channel=s.delayed_driver(target,driver+int(descriptor.pin),Sim::DelayPolicy::ReplacePending);state->pins[descriptor.pin]=target;";
        if(sdf_jobs_enabled)out<<"s.compiled_sdf_job(input_handler,uint32_t(i),source);int site=-1;";
        else out<<"auto process=s.compiled_process(input_handler,uint32_t(i));auto site=s.add_fixed_wait(process,{{source,0}});";
        out<<"input_state->pins.push_back({source,site,channel,2});";
        if(wave_enabled)out<<"if(wave.enabled()){auto scope=wave_scope;for(size_t p=input_scope_first[i];p<input_scope_first[i+1];++p)scope.push_back(input_scope_parts[p]);wave.gate_net(target,scope,input_names[i]);}";
        out<<"}\n";
    }

    if(timing&&!timing->checks.empty()) {
        std::map<std::pair<uint32_t,std::string>,uint32_t> condition_index;
        std::vector<std::string> conditions;
        auto condition=[&](uint32_t model,const std::string& text) {
            auto key=std::make_pair(model,timing_expression_key(text));auto found=condition_index.find(key);
            if(found!=condition_index.end())return found->second;
            auto index=uint32_t(conditions.size());
            auto expr=timing_condition_code(text,[&](const std::string& name) {
                const auto& pins=models.at(model).pins;auto pin=std::find_if(pins.begin(),pins.end(),[&](const auto& p){return p.name==name;});
                if(pin==pins.end())throw std::runtime_error("unknown timing condition pin: "+name);
                return "s.get(p["+std::to_string(pin-pins.begin())+"])";
            });
            conditions.push_back("+[](Sim& s,const int* p){(void)s;(void)p;return ("+expr+").truth()==1;}");condition_index.emplace(key,index);return index;
        };
        std::ostringstream descriptors;
        for(const auto& check:timing->checks) {
            const auto& cell=instances.at(check.instance);const auto& spec=check.spec;
            auto pin=[&](const std::string& name) {const auto& pins=models[cell.model].pins;auto found=std::find_if(pins.begin(),pins.end(),[&](const auto& p){return p.name==name;});if(found==pins.end())throw std::runtime_error("missing check pin: "+name);return uint32_t(found-pins.begin());};
            bool single=spec.kind==TimingCheckSpec::Width||spec.kind==TimingCheckSpec::Period;
            auto convert=[&](uint64_t q){if(!precision_fs||check.precision_fs%precision_fs||q>UINT64_MAX/(check.precision_fs/precision_fs))throw std::runtime_error("timing check global tick overflow");return q*(check.precision_fs/precision_fs);};
            std::string name=std::to_string(check.instance);
            if(timing_names) {
                name.clear();auto key=timing_names->key(timing_names->instance_names.at(check.instance));
                for(size_t offset=0;offset<key.size();) {if(key.size()-offset<4)throw std::runtime_error("invalid timing instance name");uint32_t n=0;for(int i=0;i<4;++i)n|=uint32_t(static_cast<unsigned char>(key[offset+i]))<<(8*i);offset+=4;if(n>key.size()-offset)throw std::runtime_error("invalid timing instance name");if(!name.empty())name+='/';name+=key.substr(offset,n);offset+=n;}
            }
            descriptors<<"{"<<check.first<<","<<pin(spec.events[0].pin)<<","<<(single?0:pin(spec.events[1].pin))<<","<<condition(cell.model,spec.events[0].condition)<<","<<(single?0:condition(cell.model,spec.events[1].condition))<<","<<spec.events[0].transitions<<","<<spec.events[1].transitions<<","<<unsigned(spec.kind)<<","<<convert(spec.limits[0])<<"ULL,"<<convert(spec.limits[1])<<"ULL,"<<convert(spec.threshold)<<"ULL,"<<quote("cell="+name+" model="+models[cell.model].name+" declaration="+std::to_string(spec.declaration))<<"},";
        }
        out<<"using CheckCondition=bool(*)(Sim&,const int*);static const CheckCondition check_conditions[]={";
        for(const auto& code:conditions)out<<code<<",";
        out<<"nullptr};\nstatic const RuntimeTimingCheck timing_checks[]={"<<descriptors.str()<<"};\n"
           <<"struct CheckContext {std::shared_ptr<const std::vector<int>> pins;std::vector<TimingCheckState> states;};auto check_state=std::make_shared<CheckContext>();check_state->pins=std::make_shared<const std::vector<int>>(state->pins);check_state->states.resize("<<timing->checks.size()<<");auto check_context=s.compiled_context(check_state);\n"
           <<"auto check_change=+[](Sim& s,void* raw,uint32_t payload,int before,int after){auto& state=*static_cast<CheckContext*>(raw);auto i=payload/2;auto role=payload%2;const auto& c=timing_checks[i];auto p=state.pins->data()+c.first;bool enabled=check_conditions[role?c.condition_reference:c.condition_data](s,p);state.states[i].change(s,c,int(role),before,after,enabled);};\n"
           <<"for(uint32_t i=0;i<"<<timing->checks.size()<<";++i){const auto& c=timing_checks[i];auto p=check_state->pins->data()+c.first;s.timing_watch(p[c.data],check_context,check_change,2*i);if(c.kind!=6&&c.kind!=7)s.timing_watch(p[c.reference],check_context,check_change,2*i+1);}\n";
    }
    std::unique_ptr<PathDelayDictionary> path_dictionary;
    if(path_dictionary_enabled)path_dictionary=std::make_unique<PathDelayDictionary>(*timing,precision_fs);
    if(timing&&timing->conditional_paths)conditional_paths(out,*this,precision_fs,path_dictionary.get());
    else if(timing) {
        if(path_dictionary)path_dictionary->emit(out);
        out<<"static const "<<(path_dictionary?"DictionaryModulePathArc":"ModulePathArc")<<" path_arcs[]={";
        for(size_t i=0;i<timing->arcs.size();++i) {
            const auto& arc=timing->arcs[i];out<<"{"<<arc.input<<",";
            if(path_dictionary)out<<path_dictionary->indices[i]<<","<<unsigned(arc.edge)<<"},";
            else {out<<unsigned(arc.edge)<<",{";for(auto tick:arc.ticks(precision_fs))out<<tick<<"ULL,";out<<"}},";}
        }
        out<<(path_dictionary?"{0,0,0}};\n":"{0,0,{}}};\n")<<"struct PathOutput {uint32_t pin,first,count;}; static const PathOutput path_outputs[]={";
        for(size_t i=0;i<timing->arcs.size();) {
            auto first=i;auto output=timing->arcs[i].output;while(i<timing->arcs.size()&&timing->arcs[i].output==output)++i;
            out<<"{"<<output<<","<<first<<","<<i-first<<"},";
        }
        auto selector=std::string(path_dictionary?"dictionary_module_path_delay":"module_path_delay");
        auto dictionary_argument=std::string(path_dictionary?",path_delay_tables":"");
        out<<"{0,0,0}};\nstruct PathContext {std::shared_ptr<State> gate; struct Output {int raw,site; uint32_t channel; uint8_t previous=2;}; std::vector<Output> outputs;};\n"
           <<"auto path_state=std::make_shared<PathContext>(); path_state->gate=state; auto path_context=s.compiled_context(path_state);\n"
           <<(scalar_timing_enabled?
              "auto path_handler=s.compiled_handler(path_context,+[](Sim& s,void* raw,uint32_t i) {auto& state=*static_cast<PathContext*>(raw);auto& output=state.outputs[i];auto descriptor=path_outputs[i];"+std::string(sdf_jobs_enabled?"":"s.arm_fixed_wait(output.site);")+"int next=s.get_scalar(output.raw);if(output.previous==next)return;auto delay="+selector+"(s,state.gate->pins.data(),path_arcs+descriptor.first,descriptor.count,output.previous,next"+dictionary_argument+");output.previous=uint8_t(next);s.drive_scalar_after(output.channel,uint8_t(next),delay);});\n":
              "auto path_handler=s.compiled_handler(path_context,+[](Sim& s,void* raw,uint32_t i) {auto& state=*static_cast<PathContext*>(raw);auto& output=state.outputs[i];auto descriptor=path_outputs[i];"+std::string(sdf_jobs_enabled?"":"s.arm_fixed_wait(output.site);")+"auto value=s.get(output.raw);int next=value.bit(0);if(output.previous==next)return;auto delay="+selector+"(s,state.gate->pins.data(),path_arcs+descriptor.first,descriptor.count,output.previous,next"+dictionary_argument+");output.previous=uint8_t(next);s.drive_after(output.channel,value,delay);});\n")
           <<"for(size_t i=0;path_outputs[i].count;++i){auto output=path_outputs[i];auto raw=s.signal(1,true);s.set(raw,V::x(1));auto channel=s.module_path_driver(state->pins[output.pin],driver+int(output.pin));state->pins[output.pin]=raw;";
        if(sdf_jobs_enabled)out<<"s.compiled_sdf_job(path_handler,uint32_t(i),raw);int site=-1;";
        else out<<"auto process=s.compiled_process(path_handler,uint32_t(i));auto site=s.add_fixed_wait(process,{{raw,0}});";
        out<<"path_state->outputs.push_back({raw,site,channel,2});}\n";
    }
    out<<"auto commit_handler=s.compiled_handler(context,+[](Sim& s,void* raw,uint32_t i) { auto& state=*static_cast<State*>(raw); auto cell=cells[i]; auto& storage=state.seq[cell.seq]; bool changed=storage.apply(); if(changed || output_reads_inputs[cell.model]) seq_eval[cell.model](s,state.pins.data()+cell.first,state.driver+int(cell.first),storage); if(changed && is_latch[cell.model]) s.enqueue(storage.sample); });\n"
       <<"auto sample_handler=s.compiled_handler(context,+[](Sim& s,void* raw,uint32_t i) { auto& state=*static_cast<State*>(raw); auto cell=cells[i]; auto& storage=state.seq[cell.seq]; bool first=!storage.initialized; s.arm_fixed_wait(state.sites[i]); sample[cell.model](s,state.pins.data()+cell.first,storage); if(first || output_reads_inputs[cell.model]) seq_eval[cell.model](s,state.pins.data()+cell.first,state.driver+int(cell.first),storage); if(storage.pending()) s.enqueue_nba(storage.commit); });\n"
       ;
    if(batch_enabled) {
        out<<"auto eval_handler=s.compiled_handler(context,+[](Sim& s,void* raw,uint32_t first) { auto& state=*static_cast<State*>(raw); s.compiled_batch(state.batch_handler,first,[&](uint32_t i) {auto cell=cells[i];s.arm_fixed_wait(state.sites[i]);auto p=state.pins.data()+cell.first;auto driver=state.driver+int(cell.first);switch(cell.model){\n";
        for(size_t i=0;i<models.size();++i)if(!models[i].sequential_kind)out<<"case "<<i<<": gate_eval_"<<i<<"(s,p,driver);break;\n";
        out<<"default:throw std::runtime_error(\"invalid combinational batch model\");}});});state->batch_handler=eval_handler;\n";
    } else out<<"auto eval_handler=s.compiled_handler(context,+[](Sim& s,void* raw,uint32_t i) { auto& state=*static_cast<State*>(raw); auto cell=cells[i]; s.arm_fixed_wait(state.sites[i]); eval[cell.model](s,state.pins.data()+cell.first,state.driver+int(cell.first)); });\n";
    out<<"for(size_t i=0;i<"<<instances.size()<<";++i) { auto cell=cells[i]; int process;\n"
       <<"if(sample[cell.model]) { auto& storage=state->seq[cell.seq];\n"
       <<"storage.commit=s.compiled_process(commit_handler,uint32_t(i));\n"
       <<"process=s.compiled_process(sample_handler,uint32_t(i)); storage.sample=process;\n"
       <<"} else process=s.compiled_process(eval_handler,uint32_t(i));\n"
       <<"std::vector<std::pair<int,int>> events; for(size_t k=input_first[cell.model];k<input_first[cell.model+1];++k) events.push_back({state->pins[cell.first+inputs[k]],0});\n"
       <<"state->sites[i]=s.add_fixed_wait(process,events); }\n"
       <<"for(size_t i=0;i<"<<constants.size()<<";++i) if(constants[i]>=0) { int signal=nets[i],value=constants[i];\n"
       <<"s.process([&s,signal,value,driver] { s.drive(signal,driver+"<<pin_nets.size()<<",value==0?V(0):value==1?V(1):value==2?V::x(1):V::z(1)); }); }\n}\n";
    auto result=out.str();
    if(!tables.str().empty())result.insert(result.find("static void gate_eval_"),tables.str());
    return result;
}
}
