#include "preprocessor.hpp"
#include <algorithm>
#include <cctype>
#include <fstream>
#include <functional>
#include <iterator>
#include <set>
#include <sstream>
#include <stdexcept>
namespace dsim {
namespace {
namespace fs=std::filesystem;
constexpr size_t max_bytes=256*1024*1024, max_tokens=8*1024*1024;
std::string read(const fs::path& p) {
    std::ifstream f(p,std::ios::binary); if(!f) throw std::runtime_error("cannot read "+p.string());
    std::string s; char buffer[16384];
    while(f) {f.read(buffer,sizeof buffer);s.append(buffer,size_t(f.gcount()));if(s.size()>max_bytes) throw std::runtime_error(p.string()+": input exceeds 256 MiB");}
    if(!f.eof()) throw std::runtime_error("failed reading "+p.string());
    if(s.find('\0')!=std::string::npos) throw std::runtime_error(p.string()+": NUL byte in input");
    std::string out;out.reserve(s.size());
    for(size_t i=0;i<s.size();++i) {if(s[i]=='\r') {if(i+1<s.size()&&s[i+1]=='\n')++i;out+='\n';}else out+=s[i];}
    return out;
}
std::string canonical_path(const fs::path& p) {return fs::weakly_canonical(fs::absolute(p)).string();}
bool first(char c) {return std::isalpha(static_cast<unsigned char>(c))||c=='_';}
bool rest(char c) {return first(c)||std::isdigit(static_cast<unsigned char>(c))||c=='$';}
bool space(char c) {return std::isspace(static_cast<unsigned char>(c));}
std::string json(const std::string& s) {
    const char* hex="0123456789abcdef";std::string out="\"";
    for(unsigned char c:s) {if(c=='"'||c=='\\') {out+='\\';out+=char(c);}else if(c<32) {out+="\\u00";out+=hex[c>>4];out+=hex[c&15];}else out+=char(c);}
    return out+'"';
}
[[noreturn]] void error(const SourceLocation& p,const std::string& s) {throw std::runtime_error(p.file+":"+std::to_string(p.line)+": "+s);}
enum Kind { Other,Id,White,Newline,String,Macro,Paste,Quote,Continuation,CommentContinuation };
struct Token {std::string text; Kind kind; SourceLocation at;};
using Tokens=std::vector<Token>;
Tokens lex(const std::string& text,SourceLocation at) {
    Tokens out;
    auto put=[&](size_t a,size_t b,Kind kind) {if(out.size()>=max_tokens)error(at,"preprocessor token limit exceeded");out.push_back({text.substr(a,b-a),kind,at});};
    for(size_t i=0;i<text.size();) {
        size_t a=i;char c=text[i];
        if(c=='\n') {put(i,i+1,Newline);++i;++at.line;}
        else if(space(c)) {while(i<text.size()&&text[i]!='\n'&&space(text[i]))++i;put(a,i,White);}
        else if(c=='/'&&i+1<text.size()&&text[i+1]=='/') {
            while(i<text.size()&&text[i]!='\n')++i;
            out.push_back({" ",White,at});
            // A final backslash continues a macro definition, but does not
            // extend the comment onto the next physical line. Elsewhere the
            // comment still ends at an ordinary newline.
            if(i<text.size()&&i>a&&text[i-1]=='\\') {
                out.push_back({"\n",CommentContinuation,at});++i;++at.line;
            }
        }
        else if(c=='/'&&i+1<text.size()&&text[i+1]=='*') {
            i+=2;out.push_back({" ",White,at});bool closed=false;
            while(i<text.size()) {if(text[i]=='*'&&i+1<text.size()&&text[i+1]=='/') {i+=2;closed=true;break;}if(text[i++]=='\n'){out.push_back({"\n",Newline,at});++at.line;}}
            if(!closed)error(at,"unterminated block comment");
        } else if(c=='\\'&&i+1<text.size()&&text[i+1]=='\n') {put(i,i+2,Continuation);i+=2;++at.line;}
        else if(c=='"') {
            ++i;bool closed=false;
            while(i<text.size()) {char v=text[i++];if(v=='\n')error(at,"newline in string literal");if(v=='"'){closed=true;break;}if(v=='\\'){if(i==text.size())break;if(text[i]=='\n')++at.line;++i;}}
            if(!closed)error(at,"unterminated string literal");put(a,i,String);
        } else if(c=='\\') {++i;while(i<text.size()&&!space(text[i]))++i;put(a,i,Other);}
        else if(first(c)) {++i;while(i<text.size()&&rest(text[i]))++i;put(a,i,Id);}
        else if(c=='`'&&i+1<text.size()&&text[i+1]=='`') {put(i,i+2,Paste);i+=2;}
        else if(c=='`'&&i+1<text.size()&&text[i+1]=='"') {put(i,i+2,Quote);i+=2;}
        else if(c=='`'&&i+1<text.size()&&first(text[i+1])) {i+=2;while(i<text.size()&&rest(text[i]))++i;put(a,i,Macro);}
        else {put(i,i+1,Other);++i;}
    }
    return out;
}
bool blank(const Token& t) {return t.kind==White||t.kind==Newline||t.kind==CommentContinuation;}
bool newline(const Token& t) {return t.kind==Newline||t.kind==CommentContinuation;}
void trim(Tokens& ts) {while(!ts.empty()&&blank(ts.back()))ts.pop_back();size_t i=0;while(i<ts.size()&&blank(ts[i]))++i;ts.erase(ts.begin(),ts.begin()+i);}
std::string join(const Tokens& ts) {std::string s;for(auto& t:ts)s+=t.text;return s;}
struct Definition {bool function=false;std::vector<std::string> parameters;std::vector<Tokens> defaults;std::vector<bool> has_default;Tokens body;};
class Processor {
    PreprocessOptions options;
    std::map<std::string,Definition> definitions;
    Preprocessed result;
    size_t expansion_count=0;
    struct Conditional {bool parent,taken,active,otherwise=false;SourceLocation at;};
    std::vector<Conditional> stack;
    bool active() const {return stack.empty()||stack.back().active;}
    bool conditional(const Tokens& ts,size_t& i) {
        const auto& use=ts[i];
        if(use.kind!=Macro)return false;
        auto name=use.text.substr(1);
        if(name!="ifdef"&&name!="ifndef"&&name!="elsif"&&name!="else"&&name!="endif")return false;
        ++i;std::string identifier;
        if(name=="ifdef"||name=="ifndef"||name=="elsif") {
            while(i<ts.size()&&ts[i].kind==White)++i;
            if(i==ts.size()||ts[i].kind!=Id)error(use.at,"expected one macro name after "+use.text);
            identifier=ts[i++].text;
        }
        if(name=="ifdef"||name=="ifndef") {
            bool yes=definitions.count(identifier)!=0;
            if(name=="ifndef")yes=!yes;
            bool parent=active();stack.push_back({parent,yes,parent&&yes,false,use.at});
        } else {
            if(stack.empty())error(use.at,"unmatched "+use.text);
            auto& s=stack.back();
            if(name=="endif")stack.pop_back();
            else {
                if(s.otherwise)error(use.at,"conditional branch after `else");
                bool yes=name=="else"||definitions.count(identifier)!=0;
                if(name=="else")s.otherwise=true;
                s.active=s.parent&&!s.taken&&yes;s.taken=s.taken||yes;
            }
        }
        return true;
    }
    bool line_start=true;
    bool in_module=false;
    bool in_package=false;
    TimeScale current_scale;
    bool current_directive=false;
    void emit(const Token& t) {
        if(t.kind==Id&&(t.text=="module"||((t.text=="package"||t.text=="interface")&&!in_module))) {
            result.timing.modules.push_back({result.lines.size()+(line_start?1:0),current_scale,current_directive});
            in_package=t.text=="package";
            in_module=true;
        } else if(t.kind==Id&&(t.text=="endmodule"||t.text=="endinterface"||(t.text=="endpackage"&&in_package))){in_module=false;in_package=false;}
        for(char c:t.text) {
            if(result.text.size()>=max_bytes)error(t.at,"preprocessed output exceeds 256 MiB");
            if(line_start) {result.lines.push_back(t.at);line_start=false;}
            result.text+=c;if(c=='\n')line_start=true;
        }
    }
    void remember(const std::string& p) {if(std::find(result.dependencies.begin(),result.dependencies.end(),p)==result.dependencies.end())result.dependencies.push_back(p);}
    size_t skip(const Tokens& ts,size_t i) {while(i<ts.size()&&blank(ts[i]))++i;return i;}
    void arguments(const Tokens& ts,size_t& i,std::vector<Tokens>& args,const Token& use) {
        Tokens current;std::vector<char> brackets; // commas in (), [], {} are protected
        ++i;
        for(;i<ts.size();++i) {
            auto& t=ts[i];
            if(t.kind==Other&&t.text.size()==1) {
                char c=t.text[0];
                if(c=='('||c=='['||c=='{')brackets.push_back(c);
                else if(c==')'&&brackets.empty()) {trim(current);args.push_back(current);++i;return;}
                else if(c==')'||c==']'||c=='}') {
                    char want=c==')'?'(':c==']'?'[':'{';
                    if(brackets.empty()||brackets.back()!=want)error(t.at,"unbalanced macro argument delimiters");brackets.pop_back();
                } else if(c==','&&brackets.empty()) {trim(current);args.push_back(current);current.clear();continue;}
            }
            current.push_back(t);
        }
        error(use.at,"unterminated macro argument list for "+use.text);
    }
    Tokens expand(const Tokens& ts,int depth=0,bool quoted_paste=false) {
        Tokens out;
        for(size_t i=0;i<ts.size();) {
            if(conditional(ts,i))continue;
            if(!active()) {if(newline(ts[i]))out.push_back(ts[i]);++i;continue;}
            if(quoted_paste&&ts[i].kind==Paste) {out.push_back(ts[i++]);continue;}
            // A not-yet-complete macro name can be built by paste inside a
            // quoted replacement. Resolve it after joining the name parts.
            if(quoted_paste&&ts[i].kind==Macro&&ts[i].text!="`__FILE__"&&ts[i].text!="`__LINE__"&&
               !definitions.count(ts[i].text.substr(1))) {
                size_t next=skip(ts,i+1);
                if(next<ts.size()&&ts[next].kind==Paste) {out.push_back(ts[i++]);continue;}
            }
            if(ts[i].kind==Macro) {auto more=invocation(ts,i,depth);if(more.size()>max_tokens-out.size())error(ts.front().at,"expanded token limit exceeded");out.insert(out.end(),more.begin(),more.end());}
            else if(ts[i].kind==Quote) {
                auto use=ts[i++];Tokens content;
                for(;i<ts.size()&&ts[i].kind!=Quote;++i)content.push_back(ts[i]);
                if(i==ts.size())error(use.at,"unterminated macro quote");
                ++i;
                auto expanded=expand(content,depth+1,true);
                out.push_back({json(join(expand(paste(expanded,use.at),depth+1))),String,use.at});
            }
            else {if(ts[i].kind==Paste)error(ts[i].at,"macro paste/quote outside a macro definition");out.push_back(ts[i++]);}
        }
        return out;
    }
    Tokens paste(const Tokens& ts,const SourceLocation& at,bool protect_quotes=false) {
        std::string text;bool quoted=false;
        for(size_t k=0;k<ts.size();++k) {
            if(protect_quotes&&ts[k].kind==Quote)quoted=!quoted;
            if(ts[k].kind==Paste&&!quoted) {
                while(!text.empty()&&space(text.back()))text.pop_back();
                while(k+1<ts.size()&&blank(ts[k+1]))++k;
            } else text+=ts[k].text;
        }
        return lex(text,at);
    }
    Tokens invocation(const Tokens& ts,size_t& i,int depth) {
        Token use=ts[i++];if(depth>=100||++expansion_count>1000000)error(use.at,"macro expansion limit exceeded at "+use.text);
        auto name=use.text.substr(1);
        if(name=="__FILE__")return {{json(use.at.file),String,use.at}};
        if(name=="__LINE__")return {{std::to_string(use.at.line),Other,use.at}};
        auto found=definitions.find(name);if(found==definitions.end())error(use.at,"undefined macro "+use.text);
        auto& def=found->second;std::map<std::string,Tokens> actual;
        if(def.function) {
            i=skip(ts,i);if(i==ts.size()||ts[i].text!="(")error(use.at,"function macro requires arguments: "+use.text);
            std::vector<Tokens> args;arguments(ts,i,args,use);
            if(def.parameters.empty()&&args.size()==1&&args[0].empty())args.clear();
            if(args.size()>def.parameters.size())error(use.at,"too many macro arguments: "+use.text);
            for(size_t k=0;k<def.parameters.size();++k) {
                bool empty=k>=args.size()||args[k].empty();
                if(k>=args.size()&&!def.has_default[k])error(use.at,"missing macro argument: "+def.parameters[k]);
                actual[def.parameters[k]]=empty&&def.has_default[k]?def.defaults[k]:k<args.size()?args[k]:Tokens{};
            }
        }
        Tokens body;
        for(auto t:def.body) {
            t.at=use.at;
            auto p=actual.find(t.text);
            if(t.kind==Id&&p!=actual.end()) {auto a=p->second;for(auto& v:a)v.at=use.at;body.insert(body.end(),a.begin(),a.end());}
            else {
                if(t.kind==String&&def.function) {
                    // Formal names substitute inside a replacement string too.
                    // Backticks there stay literal; only paste separators are
                    // removed. Preserve escapes without inspecting their byte.
                    std::string replaced;
                    for(size_t k=0;k<t.text.size();) {
                        if(t.text[k]=='\\'&&k+1<t.text.size()) {replaced+=t.text.substr(k,2);k+=2;}
                        else if(t.text.compare(k,2,"``")==0)k+=2;
                        else if(first(t.text[k])) {
                            size_t end=k+1;while(end<t.text.size()&&rest(t.text[end]))++end;
                            auto word=t.text.substr(k,end-k);auto value=actual.find(word);
                            replaced+=value==actual.end()?word:join(value->second);k=end;
                        } else replaced+=t.text[k++];
                    }
                    t.text=std::move(replaced);
                }
                body.push_back(t);
            }
        }
        // Quotes and nested macros expand in source order so inactive branches
        // do not evaluate their arguments or quoted contents.
        return expand(paste(body,use.at,true),depth+1);
    }
    void define(const Tokens& line) {
        size_t i=skip(line,0);if(i==line.size()||line[i].kind!=Id)error(line.empty()?SourceLocation{"<define>",1}:line.front().at,"expected macro name");
        auto at=line[i].at;std::string name=line[i++].text;
        if(name=="__FILE__"||name=="__LINE__")error(at,"cannot redefine builtin macro "+name);
        Definition def;
        if(i<line.size()&&line[i].text=="(") {
            def.function=true;Token use={name,Id,at};std::vector<Tokens> params;arguments(line,i,params,use);
            if(params.size()==1&&params[0].empty())error(at,"function macro requires at least one formal parameter");std::set<std::string> seen;
            for(auto p:params) {
                if(p.empty()||p.front().kind!=Id||!seen.insert(p.front().text).second)error(at,"invalid/duplicate macro parameter");
                def.parameters.push_back(p.front().text);size_t j=skip(p,1);bool has=j<p.size();
                if(has&&p[j].text!="=")error(at,"expected '=' in macro default");
                Tokens value;if(has)value.assign(p.begin()+j+1,p.end());trim(value);def.defaults.push_back(value);def.has_default.push_back(has);
            }
        }
        def.body.assign(line.begin()+i,line.end());trim(def.body);definitions[name]=std::move(def);
    }
    void file(const fs::path& path,int depth) {
        if(depth>=64)throw std::runtime_error(path.string()+": include nesting limit exceeded (64)");
        auto full=canonical_path(path);remember(full);auto ts=lex(read(path),{path.string(),1});
        for(size_t i=0;i<ts.size();) {
            auto t=ts[i];
            if(conditional(ts,i))continue;
            if(t.kind==Macro) {
                auto name=t.text.substr(1);
                if((options.timing_model_source||options.gate_source)&&(name=="celldefine"||name=="endcelldefine")) {
                    ++i;
                    if(active()) {
                        if(in_module)error(t.at,t.text+" must appear outside a module");
                        auto begin=result.text.size();emit(t);
                        result.compiler_directives.push_back({begin,result.text.size()});
                    }
                    continue;
                }
                if(name=="timescale"||name=="resetall") {
                    ++i;Tokens value;
                    while(i<ts.size()&&!newline(ts[i]))value.push_back(ts[i++]);
                    if(active()) {
                        if(in_module)error(t.at,t.text+" must appear outside a module");
                        auto content=expand(value);trim(content);
                        try {
                            if(name=="timescale") {
                                current_scale=parse_timescale(join(content));current_directive=true;
                                auto& minimum=result.timing.declared_precision_fs;
                                minimum=minimum?std::min(minimum,current_scale.precision_fs):current_scale.precision_fs;
                            }
                            else {if(!content.empty())error(t.at,"unexpected tokens after `resetall");current_scale=options.default_timescale;current_directive=false;}
                        }catch(const std::exception& e){error(t.at,e.what());}
                        auto begin=result.text.size();emit(t);if(!content.empty())emit({" ",White,t.at});for(const auto& v:content)emit(v);
                        result.compiler_directives.push_back({begin,result.text.size()});
                    }
                    if(i<ts.size())emit(ts[i++]);
                    continue;
                }
                static const std::set<std::string> directives={"define","undef","undefineall","include"};
                if(directives.count(name)) {
                    ++i;Tokens line;size_t newlines=0;
                    if(name=="define"||name=="include") {
                        for(;i<ts.size()&&(!newline(ts[i])||(name=="define"&&ts[i].kind==CommentContinuation));++i) {
                            if(ts[i].kind==Continuation||ts[i].kind==CommentContinuation) {line.push_back({" ",White,ts[i].at});++newlines;}else line.push_back(ts[i]);
                        }
                        if(i<ts.size()){++i;++newlines;}trim(line);
                    } else if(name=="undef") {
                        while(i<ts.size()&&ts[i].kind==White)++i;
                        if(i<ts.size()&&ts[i].kind==Id)line.push_back(ts[i++]);
                    }
                    auto identifier=[&]() {if(line.size()!=1||line[0].kind!=Id)error(t.at,"expected one macro name after "+t.text);return line[0].text;};
                    auto empty=[&]() {if(!line.empty())error(t.at,"unexpected tokens after "+t.text);};
                    if(active()) {
                        if(name=="define")define(line);
                        else if(name=="undef")definitions.erase(identifier());
                        else if(name=="undefineall") {empty();definitions.clear();}
                        else {
                            auto expanded=expand(line);trim(expanded);
                            if(expanded.size()!=1||expanded[0].kind!=String)error(t.at,"`include requires one quoted filename");
                            std::string inc=expanded[0].text.substr(1,expanded[0].text.size()-2);
                            if(inc.find('\\')!=std::string::npos)error(t.at,"escaped include filenames are not supported");
                            fs::path selected=inc;
                            if(!fs::is_regular_file(selected)) {
                                bool found=false;for(const auto& dir:options.include_dirs)if(fs::is_regular_file(dir/inc)){selected=dir/inc;found=true;break;}
                                if(!found)error(t.at,"include file not found: "+inc);
                            }
                            file(selected,depth+1);
                        }
                    }
                    for(size_t n=0;n<newlines;++n)emit({"\n",Newline,{t.at.file,t.at.line+n}});
                    continue;
                }
                if(active()) {
                    static const std::set<std::string> unsupported={"default_nettype","celldefine","endcelldefine","line","pragma","begin_keywords","end_keywords","unconnected_drive","nounconnected_drive"};
                    if(unsupported.count(name))error(t.at,"preprocessing directives: "+t.text+" is not supported yet");
                    auto expanded=invocation(ts,i,0);for(auto& v:expanded)emit(v);continue;}
            }
            if(active()) {if(t.kind==Continuation)error(t.at,"line continuation outside a macro definition");if(t.kind==Paste||t.kind==Quote)error(t.at,"macro paste/quote outside a macro definition");emit(t);}
            else if(newline(t))emit(t);
            ++i;
        }
        if(!line_start)emit({"\n",Newline,{path.string(),ts.empty()?1:ts.back().at.line}});
    }
public:
    explicit Processor(const PreprocessOptions& o):options(o),current_scale(o.default_timescale) {
        result.timing.defaults=o.default_timescale;
        for(auto& item:o.defines) {
            auto at=SourceLocation{"<command-line>",1};auto equal=item.first.find('=');auto name=item.first.substr(0,equal);
            if(name.empty()||!first(name[0])||!std::all_of(name.begin(),name.end(),rest))error(at,"invalid command-line macro name");
            if(item.second)definitions.erase(name);
            else define(lex(name+" "+(equal==std::string::npos?"1":item.first.substr(equal+1)),at));
        }
    }
    Preprocessed run(const std::vector<std::string>& files) {for(const auto& f:files)file(f,0);if(!stack.empty())error(stack.back().at,"unterminated conditional compilation");return std::move(result);}
};
}
Preprocessed preprocess(const std::vector<std::string>& files,const PreprocessOptions& options) {return Processor(options).run(files);}
std::string Preprocessed::report() const {
    std::ostringstream s;s<<"{\n  \"schema\": \"dsim.preprocessing.v1\",\n  \"dependencies\": [";
    for(size_t i=0;i<dependencies.size();++i)s<<(i?",":"")<<json(dependencies[i]);s<<"],\n  \"lines\": [";
    for(size_t i=0;i<lines.size();++i)s<<(i?",":"")<<"["<<json(lines[i].file)<<","<<lines[i].line<<"]";
    s<<"],\n  \"timing\": {\"default_unit_fs\":"<<timing.defaults.unit_fs<<",\"default_precision_fs\":"<<timing.defaults.precision_fs<<",\"declared_min_precision_fs\":"<<timing.global_precision()<<",\"modules\":[";
    for(size_t i=0;i<timing.modules.size();++i) {auto m=timing.modules[i];s<<(i?",":"")<<"{\"line\":"<<m.line<<",\"unit_fs\":"<<m.scale.unit_fs<<",\"precision_fs\":"<<m.scale.precision_fs<<"}";}
    s<<"]}\n}\n";return s.str();
}
std::vector<std::string> expand_filelists(const std::vector<std::string>& args,std::vector<std::string>& dependencies) {
    std::vector<std::string> out;std::set<std::string> pending;size_t count=0;
    std::function<void(const std::vector<std::string>&,const fs::path&,int)> visit;
    visit=[&](const std::vector<std::string>& values,const fs::path& base,int depth) {
        if(depth>=64)throw std::runtime_error("filelist nesting limit exceeded (64)");
        auto path=[&](const std::string& p) {return (base.empty()?fs::path(p):base/p).lexically_normal().string();};
        for(size_t i=0;i<values.size();++i) {
            std::string a=values[i];if(++count>1000000)throw std::runtime_error("filelist argument limit exceeded");
            if(a=="-f"||a=="-F") {
                if(++i==values.size())throw std::runtime_error("missing argument for "+a);auto p=path(values[i]);auto full=canonical_path(p);
                if(!pending.insert(full).second)throw std::runtime_error("recursive filelist: "+p);dependencies.push_back(full);
                // Quotes group spaces; comments are recognized only between arguments.
                auto text=read(p);std::vector<std::string> tokens;
                for(size_t j=0;j<text.size();) {
                    while(j<text.size()&&space(text[j]))++j;if(j==text.size())break;
                    if(text[j]=='#'||text.compare(j,2,"//")==0) {while(j<text.size()&&text[j]!='\n')++j;continue;}
                    if(text.compare(j,2,"/*")==0) {auto end=text.find("*/",j+2);if(end==std::string::npos)throw std::runtime_error(p+": unterminated filelist comment");j=end+2;continue;}
                    std::string token;char quote=0;
                    while(j<text.size()&&(quote||!space(text[j]))) {
                        char c=text[j++];
                        if(c=='\\'&&j<text.size()&&(text[j]=='"'||text[j]=='\''||text[j]=='\\'||space(text[j]))) {if(text[j]!='\n')token+=text[j];++j;continue;}
                        if(quote){if(c==quote)quote=0;else token+=c;}
                        else if(c=='"'||(c=='\''&&token.empty()))quote=c;
                        else token+=c;
                    }
                    if(quote)throw std::runtime_error(p+": unterminated filelist quote");if(!token.empty())tokens.push_back(token);
                }
                visit(tokens,a=="-F"?fs::path(p).parent_path():fs::path(),depth+1);pending.erase(full);continue;
            }
            if(a=="-I"||a=="--include-dir") {if(++i==values.size())throw std::runtime_error("missing argument for "+a);out.push_back(a);out.push_back(path(values[i]));}
            else if(a.rfind("-I",0)==0&&a.size()>2)out.push_back("-I"+path(a.substr(2)));
            else if(a.rfind("+incdir+",0)==0) {
                std::string result="+incdir+";size_t start=8;
                while(start<=a.size()){auto end=a.find('+',start);auto part=a.substr(start,end-start);if(part.empty())throw std::runtime_error("empty +incdir+ path");result+=path(part);if(end==std::string::npos)break;result+='+';start=end+1;}out.push_back(result);
            } else if(a=="-o"||a=="--emit-cpp"||a=="--emit-ir"||a=="--emit-deps"||a=="--emit-preprocessed"||a=="--gate-netlist"||a=="--sdf-check"||a=="--sdf-annotate"||a=="--sdf-bind-check"||a=="--gate-models"||a=="--liberty") {
                if(++i==values.size())throw std::runtime_error("missing argument for "+a);out.push_back(a);out.push_back(path(values[i]));
            } else if(a=="--top"||a=="-top"||a=="--gate-top"||a=="--cxx"||a=="-D"||a=="-U"||a=="--timescale"||a=="--sdf-corner"||a=="--sdf-tick"||a=="--sdf-unit"||a=="--gate-model-corner") {
                if(++i==values.size())throw std::runtime_error("missing argument for "+a);out.push_back(a);out.push_back(values[i]);
            } else if(!a.empty()&&a[0]!='-'&&a[0]!='+')out.push_back(path(a));
            else out.push_back(a);
        }
    };
    visit(args,{},0);return out;
}
}
