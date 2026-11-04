#include "sdf_models.hpp"
#include "sdf.hpp"
#include <algorithm>
#include <cctype>
#include <set>
#include <sstream>
#include <stdexcept>

namespace dsim {
namespace {
std::string quote(const std::string& s) {
    std::string r="\"";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\')r+='\\';
        if(c=='\n')r+="\\n";else if(c=='\r')r+="\\r";else if(c=='\t')r+="\\t";
        else if(c<32)throw std::runtime_error("control character in model identity");
        else r+=char(c);
    }
    return r+'"';
}
bool simple(const std::string& s) {
    if(s.empty()||!(std::isalpha(static_cast<unsigned char>(s[0]))||s[0]=='_'))return false;
    return std::all_of(s.begin()+1,s.end(),[](unsigned char c){return std::isalnum(c)||c=='_'||c=='$';});
}
std::string verilog_pin(const std::string& s) {
    if(simple(s))return s;
    auto bracket=s.find('[');
    if(bracket!=std::string::npos&&simple(s.substr(0,bracket))&&s.back()==']'&&bracket+2<s.size()&&s.substr(bracket+1,s.size()-bracket-2).find_first_not_of("0123456789")==std::string::npos)return s;
    if(s.empty()||s.find_first_of(" \t\r\n")!=std::string::npos)throw std::runtime_error("unrepresentable Verilog pin "+s);
    return "\\"+s+" ";
}
struct Identity {uint64_t occurrences=0;size_t first_line=0;std::string kind;};
struct ModelRecords {uint64_t cells=0,entries=0;std::map<std::string,Identity> declarations;};
struct Replacement {size_t begin,end;std::string text;};
}
PreparedSdfModels prepare_sdf_models(const Preprocessed& source,const std::string& file,const SdfConditionAliases& supplied) {
    auto library=parse_timing_models(source);
    std::map<std::string,const TimingModel*> models;
    for(const auto& m:library.models)models.emplace(m.name,&m);
    std::map<std::string,ModelRecords> records;
    SdfConditionAliases added;
    uint64_t interconnects=0,negative_limits=0;
    char divider='.';
    SdfCallbacks cb;
    cb.header=[&](const SdfHeader& h){divider=h.divider;};
    cb.cell=[&](const SdfCell& c){if(models.count(c.type))++records[c.type].cells;};
    cb.entry=[&](const SdfCell& c,const SdfEntry& e) {
        auto fail=[&](const std::string& why)->void {throw std::runtime_error(file+":"+std::to_string(e.line)+": SDF model preparation: "+why);};
        if(e.kind=="INTERCONNECT") {++interconnects;return;} // No cell specify declaration exists for a net delay.
        if(e.kind!="IOPATH"&&e.mode!=SdfEntry::Mode::TimingCheck)fail("cannot represent "+e.kind+" as a specify declaration");
        auto found=models.find(c.type);if(found==models.end())fail("missing functional base model "+c.type);
        const auto& model=*found->second;
        if(!e.label.empty()||!e.retain.empty())fail("label/RETAIN requires a richer model template");
        for(const auto& v:e.values)if(v.reject||v.xlimit)fail("pulse thresholds require a richer model template");
        auto pin=[&](const std::string& raw) {
            std::string decoded;
            for(size_t i=0;i<raw.size();++i) {
                if(raw[i]=='\\') {if(++i==raw.size())fail("unterminated pin escape");}
                else if(raw[i]==divider)fail("cell timing terminal must be local: "+raw);
                decoded+=raw[i];
            }
            if(!model.ports.count(decoded))fail("unknown port "+model.name+"."+decoded);
            return decoded;
        };
        auto condition=[&](const std::string& value) {
            // Validate against the same scalar expression language as execution.
            (void)timing_condition_code(value,[&](const std::string& p){
                if(model.ports.count(p))return "V(0)";
                if(model.aliases.count(p)){(void)model.resolve_condition(p);return "V(0)";}
                auto lib=supplied.find(model.name);
                if(lib==supplied.end()||!lib->second.count(p))fail("condition alias has no functional/Liberty definition: "+model.name+"."+p);
                auto target=lib->second.at(p);
                if(!model.ports.count(target))fail("Liberty condition alias must directly name a scalar port: "+model.name+"."+p+" = "+target);
                added[model.name][p]=target;return "V(0)";
            });
            return value;
        };
        auto event=[&](const SdfPort& p) {
            if(!p.label.empty())fail("event labels require a richer model template");
            std::string text;
            if(p.edge=="posedge"||p.edge=="negedge")text=p.edge+" ";
            else if(!p.edge.empty()) {
                std::string edge=p.edge;std::transform(edge.begin(),edge.end(),edge.begin(),[](unsigned char v){return char(std::tolower(v));});
                text="edge ["+edge+"] ";
            }
            text+=verilog_pin(pin(p.name));
            if(!p.condition.empty())text+=" &&& ("+condition(p.condition)+")";
            return text;
        };
        std::string declaration;
        if(e.kind=="IOPATH") {
            if(e.ports.size()!=2)fail("IOPATH requires two terminals");
            const auto& a=e.ports[0];const auto& z=e.ports[1];
            if(!a.condition.empty()||!z.condition.empty()||!a.label.empty()||!z.label.empty()||!z.edge.empty())fail("conditional path terminals cannot be represented");
            auto in=pin(a.name),out=pin(z.name);
            if(model.ports.at(in)=="output"||model.ports.at(out)=="input")fail("IOPATH port direction mismatch");
            if(!e.condition.empty())declaration="if ("+condition(e.condition)+") ";
            else if(e.conditional_else)declaration="ifnone ";
            if(!a.edge.empty()&&a.edge!="posedge"&&a.edge!="negedge")fail("IOPATH needs posedge/negedge or an unqualified source");
            declaration+="("+(a.edge.empty()?std::string():a.edge+" ")+verilog_pin(in)+" => ";
            declaration+=a.edge.empty()?verilog_pin(out):"("+verilog_pin(out)+" : 1'bx)";
            declaration+=") = 0;";
        } else {
            static const std::map<std::string,std::string> kinds={{"SETUP","$setup"},{"HOLD","$hold"},{"SETUPHOLD","$setuphold"},{"RECOVERY","$recovery"},{"REMOVAL","$removal"},{"RECREM","$recrem"},{"WIDTH","$width"},{"PERIOD","$period"},{"SKEW","$skew"}};
            auto kind=kinds.find(e.kind);if(kind==kinds.end())fail("unsupported check template "+e.kind);
            std::vector<std::string> events;for(const auto& p:e.ports)events.push_back(event(p));
            // SDF uses data,reference for HOLD/SETUPHOLD; Verilog reverses it.
            if(e.kind=="HOLD"||e.kind=="SETUPHOLD")std::swap(events.at(0),events.at(1));
            declaration=kind->second+"(";
            for(size_t i=0;i<events.size();++i){if(i)declaration+=", ";declaration+=events[i];}
            for(const auto& v:e.values) {
                declaration+=", 0";
                for(const auto& value:v.delay.corner)if(value&&!value->empty()&&value->front()=='-'){++negative_limits;break;}
            }
            declaration+=");";
        }
        auto& r=records[c.type];++r.entries;
        auto& identity=r.declarations[declaration];
        if(!identity.occurrences){identity.first_line=e.line;identity.kind=e.kind;}
        ++identity.occurrences;
    };
    auto stats=read_sdf(file,cb);
    std::vector<Replacement> replacements;
    std::ostringstream report;
    report<<"{\"schema\":\"dsim.sdf-model-preparation.v1\",\"zero_initial_delays\":true,\"vendor_model\":false,\"runtime_annotation\":false,\"sdf\":"<<quote(file)<<",\"interconnect_entries\":"<<interconnects<<",\"entries_with_negative_check_limits\":"<<negative_limits<<",\"parsed\":"<<stats.report()<<",\"models\":[";
    bool first=true;
    for(const auto& [name,r]:records) {
        if(r.declarations.empty())continue;
        const auto& model=*models.at(name);
        std::string specify="specify\n";
        if(!first)report<<',';first=false;
        report<<"{\"name\":"<<quote(name)<<",\"cells\":"<<r.cells<<",\"entries\":"<<r.entries<<",\"replaced_paths\":"<<model.paths.size()<<",\"replaced_checks\":"<<model.checks.size()<<",\"declarations\":[";
        bool initial=true;
        for(const auto& [text,i]:r.declarations) {
            specify+="    "+text+"\n";
            if(!initial)report<<',';initial=false;
            report<<"{\"kind\":"<<quote(i.kind)<<",\"text\":"<<quote(text)<<",\"occurrences\":"<<i.occurrences<<",\"first_sdf_line\":"<<i.first_line<<'}';
        }
        specify+="  endspecify";report<<"],\"added_condition_aliases\":{";
        bool first_alias=true;std::string wires;
        for(const auto& [alias,target]:added[name]) {
            if(!first_alias)report<<',';first_alias=false;report<<quote(alias)<<':'<<quote(target);
            wires+="wire "+verilog_pin(alias)+" = "+verilog_pin(target)+";\n";
        }
        report<<"}}";specify=wires+specify;
        if(model.specify_ranges.empty())replacements.push_back({model.module_end,model.module_end,specify+"\n"});
        else for(size_t i=0;i<model.specify_ranges.size();++i) {
            auto range=model.specify_ranges[i];replacements.push_back({range.first,range.second,i==0?specify:std::string()});
        }
    }
    report<<"]}\n";
    std::sort(replacements.begin(),replacements.end(),[](const auto& a,const auto& b){return a.begin<b.begin;});
    PreparedSdfModels result;size_t cursor=0;
    for(const auto& r:replacements){if(r.begin<cursor||r.end>source.text.size())throw std::runtime_error("overlapping specify source ranges");result.verilog+=source.text.substr(cursor,r.begin-cursor);result.verilog+=r.text;cursor=r.end;}
    result.verilog+=source.text.substr(cursor);result.report=report.str();return result;
}
}
