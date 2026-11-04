#include "gate_source.hpp"
#include <algorithm>
#include <chrono>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace dsim {
namespace {
bool first(unsigned char c){return std::isalpha(c)||c=='_';}
bool body(unsigned char c){return first(c)||std::isdigit(c)||c=='$';}
bool white(unsigned char c){return std::isspace(c);}
std::string quoted(const std::string& s) {
    std::string r="\"";const char* hex="0123456789abcdef";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\'){r+='\\';r+=char(c);}
        else if(c<32){r+="\\u00";r+=hex[c>>4];r+=hex[c&15];}
        else r+=char(c);
    }
    return r+'"';
}
std::string read(const std::string& file) {
    std::ifstream f(file,std::ios::binary);if(!f)throw std::runtime_error("cannot read "+file);
    std::string s((std::istreambuf_iterator<char>(f)),{});
    if(f.bad())throw std::runtime_error("failed reading "+file);
    if(s.find('\0')!=std::string::npos)throw std::runtime_error(file+": NUL byte in input");
    // Normalize in place; no second full-size allocation for large netlists.
    size_t out=0;
    for(size_t i=0;i<s.size();++i) {
        if(s[i]=='\r'){if(i+1<s.size()&&s[i+1]=='\n')++i;s[out++]='\n';}
        else s[out++]=s[i];
    }
    s.resize(out);return s;
}
// A lexical pass only. The network parser remains responsible for structural
// grammar. Unknown/complex directives select the common macro preprocessor.
bool scan(GateSource& result,TimeScale defaults,const TimingConfig* expanded=nullptr) {
    auto& s=result.text;size_t i=0,line=1,module_line=1;bool in_module=false,want_name=false;
    TimeScale scale=defaults;
    while(i<s.size()) {
        unsigned char c=s[i];
        if(white(c)){if(c=='\n')++line;++i;continue;}
        if(c=='/'&&i+1<s.size()&&s[i+1]=='/') {
            i=s.find('\n',i);if(i==std::string::npos)i=s.size();continue;
        }
        if(c=='/'&&i+1<s.size()&&s[i+1]=='*') {
            auto end=s.find("*/",i+2);if(end==std::string::npos)return false;
            line+=size_t(std::count(s.begin()+i,s.begin()+end+2,'\n'));i=end+2;continue;
        }
        if(c=='"') {
            ++i;bool closed=false;
            while(i<s.size()) {
                char ch=s[i++];if(ch=='\n')return false;
                if(ch=='"'){closed=true;break;}
                if(ch=='\\'){if(i==s.size())return false;if(s[i]=='\n')++line;++i;}
            }
            if(!closed)return false;continue;
        }
        if(c=='`') {
            if(expanded||in_module)return false;
            size_t start=i++;while(i<s.size()&&body(s[i]))++i;
            auto name=s.substr(start+1,i-start-1);auto end=s.find('\n',i);
            if(end==std::string::npos)end=s.size();
            auto value=s.substr(i,end-i);
            // Comments, macro values, continuations and same-line declarations
            // are handled by the common implementation, never guessed here.
            try {
                if(name=="timescale")scale=parse_timescale(value);
                else if(name=="resetall"||name=="celldefine"||name=="endcelldefine") {
                    if(!std::all_of(value.begin(),value.end(),white))return false;
                    if(name=="resetall")scale=defaults;
                } else return false;
            } catch(const std::exception&){return false;}
            std::fill(s.begin()+start,s.begin()+end,' ');i=end;continue;
        }
        bool escaped=c=='\\';
        if(first(c)||escaped) {
            size_t start=i++;
            if(escaped)while(i<s.size()&&!white(s[i]))++i;
            else while(i<s.size()&&body(s[i]))++i;
            std::string_view token(s.data()+start+(escaped?1:0),i-start-(escaped?1:0));
            if(want_name) {
                auto time=expanded?expanded->at(module_line):scale;
                result.modules.push_back({std::string(token),module_line,time});want_name=false;
            } else if(!escaped&&token=="module"){in_module=true;want_name=true;module_line=line;}
            else if(!escaped&&token=="endmodule")in_module=false;
            continue;
        }
        ++i;
    }
    return true;
}
}
SourceLocation GateSource::location(size_t line) const {
    if(!lines.empty()&&line&&line<=lines.size())return lines[line-1];
    return {file,line?line:1};
}
TimeScale GateSource::time(const std::string& module) const {
    auto found=module_times.find(module);
    if(found==module_times.end())throw std::runtime_error("missing structural module timescale: "+module);
    return found->second;
}
GateSource prepare_gate_source(const std::string& file,const PreprocessOptions& options) {
    const auto begin=std::chrono::steady_clock::now();
    // Keep command-line macro validation identical even when no expansion is
    // needed. Gate and RTL files use independent compilation-unit state.
    auto gate_options=options;gate_options.gate_source=true;
    (void)preprocess({},gate_options);
    GateSource result;result.file=std::filesystem::weakly_canonical(std::filesystem::absolute(file)).string();
    result.text=read(file);result.dependencies={result.file};
    if(scan(result,options.default_timescale))result.fast_path=true;
    else {
        auto p=preprocess({file},gate_options);
        for(auto range:p.compiler_directives)
            for(size_t i=range.first;i<range.second;++i)if(p.text[i]!='\n')p.text[i]=' ';
        result.text=std::move(p.text);result.lines=std::move(p.lines);result.dependencies=std::move(p.dependencies);
        result.modules.clear();
        if(!scan(result,options.default_timescale,&p.timing))
            throw std::runtime_error(file+": invalid preprocessed structural source");
    }
    result.bytes=result.text.size();
    for(const auto& m:result.modules)if(!result.module_times.emplace(m.name,m.scale).second) {
        auto at=result.location(m.line);
        throw std::runtime_error(at.file+":"+std::to_string(at.line)+": duplicate module "+m.name);
    }
    result.seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    return result;
}
std::string GateSource::report() const {
    std::ostringstream out;out<<"{\"frontend\":\"gate-preprocessing\",\"fast_path\":"<<(fast_path?"true":"false")
        <<",\"bytes\":"<<bytes<<",\"seconds\":"<<seconds<<",\"dependencies\":[";
    for(size_t i=0;i<dependencies.size();++i)out<<(i?",":"")<<quoted(dependencies[i]);
    out<<"],\"modules\":[";
    for(size_t i=0;i<modules.size();++i){const auto& m=modules[i];auto at=location(m.line);
        out<<(i?",":"")<<"{\"name\":"<<quoted(m.name)<<",\"line\":"<<m.line<<",\"file\":"<<quoted(at.file)
           <<",\"source_line\":"<<at.line<<",\"unit_fs\":"<<m.scale.unit_fs<<",\"precision_fs\":"<<m.scale.precision_fs<<"}";
    }
    out<<"]}";return out.str();
}
}
