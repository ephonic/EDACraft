#include "timing_model.hpp"
#include <algorithm>
#include <cctype>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>

namespace dsim {
namespace {
struct Token {std::string text;size_t line;bool identifier=false;size_t begin=0,end=0;};
[[noreturn]] void error(const SourceLocation& at,const std::string& message) {
    throw std::runtime_error(at.file+":"+std::to_string(at.line)+": timing model: "+message);
}
std::vector<Token> lex(const std::string& s) {
    std::vector<Token> out;size_t line=1;
    for(size_t i=0;i<s.size();) {
        auto start=i;char c=s[i];
        if(std::isspace(static_cast<unsigned char>(c))) {if(c=='\n')++line;++i;continue;}
        if(s.compare(i,2,"//")==0) {while(i<s.size()&&s[i]!='\n')++i;continue;}
        if(s.compare(i,2,"/*")==0) {
            i+=2;while(i+1<s.size()&&s.compare(i,2,"*/")!=0){if(s[i++]=='\n')++line;}
            if(i+1==s.size()||i==s.size())throw std::runtime_error("unterminated timing model comment");
            i+=2;continue;
        }
        auto token_line=line;
        bool id=std::isalpha(static_cast<unsigned char>(c))||c=='_'||c=='$'||c=='\\';
        if(c=='\\') {
            ++i;while(i<s.size()&&!std::isspace(static_cast<unsigned char>(s[i])))++i;
            if(i==start+1||i==s.size())throw std::runtime_error("unterminated escaped timing model identifier");
            // Retain the escape and a terminating space when emitting text.
        } else if(id) {
            while(i<s.size()&&(std::isalnum(static_cast<unsigned char>(s[i]))||s[i]=='_'||s[i]=='$'))++i;
        } else if(c=='"') {
            ++i;bool closed=false;
            while(i<s.size()) {char d=s[i++];if(d=='\n')++line;if(d=='\\'&&i<s.size()){if(s[i]=='\n')++line;++i;}else if(d=='"'){closed=true;break;}}
            if(!closed)throw std::runtime_error("unterminated timing model string");
        } else if(std::isdigit(static_cast<unsigned char>(c))||(c=='.'&&i+1<s.size()&&std::isdigit(static_cast<unsigned char>(s[i+1])))) {
            ++i;while(i<s.size()) {
                char d=s[i];
                if(std::isalnum(static_cast<unsigned char>(d))||d=='_'||d=='.'||d=='\''||d=='?'){++i;continue;}
                if((d=='+'||d=='-')&&i>start&&(s[i-1]=='e'||s[i-1]=='E')){++i;continue;}
                break;
            }
        } else {
            bool found=false;
            for(const char* op:{"&&&","===","!==","=>","*>","==","!=","&&","||","<=",">=","<<",">>","~^","^~","+:","-:"}) {
                auto n=std::char_traits<char>::length(op);if(s.compare(i,n,op)==0){i+=n;found=true;break;}
            }
            if(!found)++i;
        }
        out.push_back({s.substr(start,i-start),token_line,id,start,i});
    }
    return out;
}
using Tokens=std::vector<Token>;
std::string text(const Tokens& v,size_t first,size_t last) {
    std::string result;
    for(size_t i=first;i<last;++i){if(!result.empty())result+=' ';result+=v[i].text;if(v[i].text.front()=='\\')result+=' ';}
    return result;
}
std::string identifier(const Token& t) {return t.text.front()=='\\'?t.text.substr(1):t.text;}
bool enclosed(const Tokens& t) {
    if(t.size()<2||t.front().text!="("||t.back().text!=")")return false;
    int depth=0;for(size_t i=0;i<t.size();++i){if(t[i].text=="(")++depth;else if(t[i].text==")")--depth;if(depth==0&&i+1<t.size())return false;}
    return depth==0;
}
Tokens unwrap(Tokens t) {while(enclosed(t)){t.erase(t.begin());t.pop_back();}return t;}
std::vector<Tokens> split(const Tokens& v,const std::string& sep) {
    std::vector<Tokens> parts(1);int paren=0,bracket=0,brace=0;
    for(const auto& t:v) {
        if(!paren&&!bracket&&!brace&&t.text==sep){parts.emplace_back();continue;}
        parts.back().push_back(t);
        if(t.text=="(")++paren;else if(t.text==")")--paren;else if(t.text=="[")++bracket;else if(t.text=="]")--bracket;else if(t.text=="{")++brace;else if(t.text=="}")--brace;
        if(paren<0||bracket<0||brace<0)throw std::runtime_error("unbalanced timing expression");
    }
    if(paren||bracket||brace)throw std::runtime_error("unbalanced timing expression");
    return parts;
}
class Reader {
    Tokens tokens;size_t pos=0;const Preprocessed& source;TimingLibrary result;
    SourceLocation location(size_t line) const {return line&&line<=source.lines.size()?source.lines[line-1]:SourceLocation{"<timing-model>",line};}
    SourceLocation at() const {return location(pos<tokens.size()?tokens[pos].line:tokens.empty()?1:tokens.back().line);}
    std::string peek() const {return pos<tokens.size()?tokens[pos].text:std::string();}
    [[noreturn]] void fail(const std::string& s) const {error(at(),s);}
    bool take(const std::string& s) {if(peek()!=s)return false;++pos;return true;}
    void expect(const std::string& s) {if(!take(s))fail("expected '"+s+"', got '"+peek()+"'");}
    std::string name() {if(pos==tokens.size()||!tokens[pos].identifier)fail("expected identifier");return identifier(tokens[pos++]);}
    Tokens group(const std::string& open="(",const std::string& close=")") {
        expect(open);auto begin=pos;int depth=1;
        while(pos<tokens.size()) {auto s=tokens[pos++].text;if(s==open)++depth;else if(s==close&&!--depth)return Tokens(tokens.begin()+begin,tokens.begin()+pos-1);}
        fail("unterminated "+open);
    }
    Tokens statement() {
        auto begin=pos;int p=0,b=0,c=0;
        while(pos<tokens.size()) {
            auto s=tokens[pos++].text;
            if(s==";"&&!p&&!b&&!c)return Tokens(tokens.begin()+begin,tokens.begin()+pos-1);
            if(s=="(")++p;else if(s==")")--p;else if(s=="[")++b;else if(s=="]")--b;else if(s=="{")++c;else if(s=="}")--c;
            if(p<0||b<0||c<0)fail("unbalanced statement");
            if(s=="endspecify"||s=="endmodule")fail("missing semicolon");
        }
        fail("unterminated statement");
    }
    std::string pin_name(const Tokens& t) {
        if(t.size()==1&&t[0].identifier)return identifier(t[0]);
        if(t.size()==4&&t[0].identifier&&t[1].text=="["&&t[3].text=="]"&&t[2].text.find_first_not_of("0123456789")==std::string::npos)
            return identifier(t[0])+"["+t[2].text+"]";
        fail("path terminals must be scalar names or constant bit selects");
    }
    void port(TimingModel& m,const std::string& pin,const std::string& direction) {
        auto old=m.ports.find(pin);if(old!=m.ports.end())fail("duplicate model port "+pin);
        m.ports.emplace(pin,direction);
    }
    void ports(TimingModel& m,const Tokens& declaration,std::string direction={},bool ansi=false) {
        std::vector<std::string> range;
        for(auto part:split(declaration,",")) {
            size_t i=0;
            if(i<part.size()&&(part[i].text=="input"||part[i].text=="output"||part[i].text=="inout")) {direction=part[i++].text;range.clear();}
            while(i<part.size()&&(part[i].text=="wire"||part[i].text=="reg"||part[i].text=="logic"||part[i].text=="signed"||part[i].text=="unsigned"))++i;
            if(i<part.size()&&part[i].text=="[") {
                range.clear();++i;while(i<part.size()&&part[i].text!="]")range.push_back(part[i++].text);
                if(i==part.size())fail("unclosed model port range");++i;
            }
            if(i+1!=part.size()||!part[i].identifier||direction.empty())fail(ansi?"mixed/unsupported ANSI model ports":"unsupported model port declaration");
            auto pin=identifier(part[i]);
            if(range.empty())port(m,pin,direction);
            else {
                if(range.size()!=3||range[1]!=":"||range[0].find_first_not_of("0123456789")!=std::string::npos||range[2].find_first_not_of("0123456789")!=std::string::npos)fail("model port range requires nonnegative literal bounds");
                uint64_t hi=std::stoull(range[0]),lo=std::stoull(range[2]);
                if(hi>1000000||lo>1000000||(hi>lo?hi-lo:lo-hi)>=1000000)fail("model port range exceeds limit");
                for(uint64_t n=std::min(hi,lo);n<=std::max(hi,lo);++n)port(m,pin+"["+std::to_string(n)+"]",direction);
            }
        }
    }
    void constants(TimingModel& m) {
        for(auto item:split(statement(),",")) {
            if(item.size()<3||!item[0].identifier||item[1].text!="=")fail("specparam requires an untyped scalar constant assignment");
            auto key=identifier(item[0]);if(!m.constants.emplace(key,text(item,2,item.size())).second)fail("duplicate constant "+key);
        }
    }
    void path(TimingModel& m) {
        TimingPath p;p.source=at();
        if(take("if")) {auto condition=group();if(condition.empty())fail("empty path condition");p.condition=text(condition,0,condition.size());}
        else if(take("ifnone"))p.ifnone=true;
        auto terminals=group();
        size_t arrow=0;int depth=0;
        for(;arrow<terminals.size();++arrow) {auto s=terminals[arrow].text;if(!depth&&(s=="=>"||s=="*>"))break;if(s=="(")++depth;else if(s==")")--depth;}
        if(arrow==terminals.size())fail("missing module path operator");
        p.full=terminals[arrow].text=="*>";
        Tokens from(terminals.begin(),terminals.begin()+arrow),to(terminals.begin()+arrow+1,terminals.end());
        if(!from.empty()&&(from.front().text=="posedge"||from.front().text=="negedge")){p.edge=from.front().text;from.erase(from.begin());}
        if(!from.empty()&&(from.back().text=="+"||from.back().text=="-")){p.polarity=from.back().text;from.pop_back();}
        for(auto part:split(from,","))p.inputs.push_back(pin_name(part));
        if(enclosed(to)) {
            to=unwrap(to);size_t colon=0;
            while(colon<to.size()&&to[colon].text!=":"&&to[colon].text!="+:"&&to[colon].text!="-:")++colon;
            if(colon==to.size()||colon+1==to.size())fail("edge path needs output:data expression");
            p.output_polarity=to[colon].text==":"?"":to[colon].text.substr(0,1);
            p.data=text(to,colon+1,to.size());to.resize(colon);
        }
        for(auto part:split(to,","))p.outputs.push_back(pin_name(part));
        if(!p.full&&(p.inputs.size()!=1||p.outputs.size()!=1))fail("parallel path must have one input and one output");
        expect("=");auto delay=unwrap(statement());
        for(auto part:split(delay,",")){if(part.empty())fail("empty model path delay");p.delays.push_back(text(part,0,part.size()));}
        if(p.delays.size()!=1&&p.delays.size()!=2&&p.delays.size()!=3&&p.delays.size()!=6&&p.delays.size()!=12)fail("model delay requires 1,2,3,6 or 12 values");
        m.paths.push_back(std::move(p));
    }
    void specify(TimingModel& m) {
        auto begin=tokens.at(pos).begin;
        expect("specify");
        while(peek()!="endspecify") {
            if(peek().empty())fail("unterminated specify block");
            if(take("specparam")){constants(m);continue;}
            if(peek()=="pulsestyle_onevent"||peek()=="pulsestyle_ondetect"||peek()=="showcancelled"||peek()=="noshowcancelled") {
                auto kind=peek();++pos;auto list=statement();if(list.empty())fail("empty pulse declaration");
                for(auto part:split(list,","))(void)pin_name(part);
                m.pulse_declarations.push_back(kind+" "+text(list,0,list.size()));continue;
            }
            if(peek().front()=='$') {
                static const std::set<std::string> kinds={"$setup","$hold","$setuphold","$recovery","$removal","$recrem","$skew","$timeskew","$fullskew","$period","$width","$nochange"};
                TimingCheckDeclaration check;check.source=at();check.kind=peek();++pos;
                if(!kinds.count(check.kind))fail("unknown timing check "+check.kind);
                auto args=group();expect(";");for(auto part:split(args,","))check.arguments.push_back(text(part,0,part.size()));
                auto n=check.arguments.size();size_t minimum=(check.kind=="$width"||check.kind=="$period")?2:(check.kind=="$setuphold"||check.kind=="$recrem"||check.kind=="$nochange"||check.kind=="$fullskew")?4:3;
                if(n<minimum)fail("too few timing-check arguments");
                for(size_t i=0;i<minimum;++i)if(check.arguments[i].empty())fail("empty required timing-check argument");
                m.checks.push_back(std::move(check));continue;
            }
            if(peek()=="("||peek()=="if"||peek()=="ifnone"){path(m);continue;}
            fail("unsupported specify construct '"+peek()+"'");
        }
        m.specify_ranges.emplace_back(begin,tokens.at(pos).end);++pos;
    }
    void module() {
        auto line=tokens[pos].line;expect("module");TimingModel m;m.source=location(line);m.time=source.timing.at(line);m.name=name();
        const auto definition_begin=pos;
        if(peek()=="#")fail("parameterized timing models require instance specialization");
        auto header=group();expect(";");
        std::vector<std::string> header_names;
        if(!header.empty()) {
            bool ansi=header.front().text=="input"||header.front().text=="output"||header.front().text=="inout";
            if(ansi)ports(m,header,{},true);
            else for(auto part:split(header,",")){if(part.size()!=1||!part[0].identifier)fail("unsupported model header");header_names.push_back(identifier(part[0]));}
        }
        // Keep function/task/behavior bodies opaque, but never let a nested
        // specify or parameterized/generate boundary masquerade as module data.
        std::vector<std::string> nested;int paren=0,brace=0;
        while(!peek().empty()&&peek()!="endmodule") {
            auto s=peek();
            if(s=="module")fail("nested or unterminated timing model");
            if(s=="function"||s=="task"||s=="begin"||s=="fork"||s=="case"||s=="casex"||s=="casez") {
                nested.push_back(s=="function"?"endfunction":s=="task"?"endtask":s=="begin"?"end":s=="fork"?"join":"endcase");++pos;continue;
            }
            if(s=="endfunction"||s=="endtask"||s=="end"||s=="join"||s=="endcase") {
                if(nested.empty()||nested.back()!=s)fail("unbalanced model body");nested.pop_back();++pos;continue;
            }
            if(s=="generate"||s=="endgenerate"||s=="parameter"||s=="defparam")fail("parameter/generate model needs elaboration before timing extraction");
            if(nested.empty()&&!paren&&!brace) {
                if(s=="specify"){specify(m);continue;}
                if(s=="input"||s=="output"||s=="inout"){++pos;ports(m,statement(),s);continue;}
                if(s=="specparam"||s=="localparam"){++pos;constants(m);continue;}
                if(s=="assign"||s=="wire") {
                    ++pos;auto parts=split(statement(),",");
                    for(const auto& part:parts)if(part.size()>2&&part[0].identifier&&part[1].text=="=") {
                        auto key=identifier(part[0]);auto rhs=text(part,2,part.size());
                        auto old=m.aliases.emplace(key,rhs);
                        if(!old.second)old.first->second.clear(); // Multiple drivers are not an alias.
                    }
                    continue;
                }
            }
            if(s=="specify"||s=="endspecify")fail("specify outside module scope");
            if(s=="(")++paren;else if(s==")")--paren;else if(s=="{")++brace;else if(s=="}")--brace;
            if(paren<0||brace<0)fail("unbalanced model body expression");++pos;
        }
        if(!nested.empty()||paren||brace)fail("unbalanced model body at endmodule");
        m.definition_key=std::to_string(m.time.unit_fs)+":"+std::to_string(m.time.precision_fs)+";";
        for(auto i=definition_begin;i<pos;++i)
            m.definition_key+=std::to_string(tokens[i].text.size())+":"+tokens[i].text;
        m.module_end=tokens.at(pos).begin;expect("endmodule");
        std::set<std::string> header_set;
        for(const auto& pin:header_names) {
            if(!header_set.insert(pin).second)error(m.source,"duplicate header port "+pin);
            if(!m.ports.count(pin)&&!std::any_of(m.ports.begin(),m.ports.end(),[&](const auto& x){return x.first.rfind(pin+"[",0)==0;}))error(m.source,"undeclared header port "+pin);
        }
        if(!header_names.empty())for(const auto& pin:m.ports) {
            bool represented=header_set.count(pin.first)!=0;
            for(const auto& name:header_names)if(pin.first.rfind(name+"[",0)==0)represented=true;
            if(!represented)error(m.source,"declared port absent from header "+pin.first);
        }
        for(const auto& p:m.paths) {
            for(const auto& pin:p.inputs) {auto found=m.ports.find(pin);if(found==m.ports.end()||found->second=="output")error(p.source,"path source is not an input/inout port: "+pin);}
            for(const auto& pin:p.outputs) {auto found=m.ports.find(pin);if(found==m.ports.end()||found->second=="input")error(p.source,"path destination is not an output/inout port: "+pin);}
        }
        for(const auto& old:result.models)if(old.name==m.name)error(m.source,"duplicate model "+m.name);
        result.models.push_back(std::move(m));
    }
public:
    explicit Reader(const Preprocessed& p):source(p) {
        auto code=p.text;
        for(auto r:p.compiler_directives)for(auto i=r.first;i<r.second;++i)if(code[i]!='\n')code[i]=' ';
        tokens=lex(code);result.dependencies=p.dependencies;
    }
    TimingLibrary run() {
        while(!peek().empty()) {if(peek()!="module")fail("expected module declaration");module();}
        if(result.models.empty())fail("no timing models");return std::move(result);
    }
};
std::string resolve(const TimingModel& m,Tokens t,int corner,std::set<std::string>& active,size_t depth) {
    if(depth>128)error(m.source,"constant expression nesting exceeds limit");
    t=unwrap(std::move(t));auto triple=split(t,":");
    if(triple.size()>1) {
        if(triple.size()!=3)error(m.source,"constant min:typ:max requires three values");
        return resolve(m,triple[size_t(corner)],corner,active,depth+1);
    }
    if(t.empty())error(m.source,"empty model constant");
    if(t.front().text=="+"||t.front().text=="-") {
        bool negative=t.front().text=="-";t.erase(t.begin());auto v=resolve(m,t,corner,active,depth+1);
        if(negative)v=v.front()=='-'?v.substr(1):"-"+v;return v;
    }
    if(t.size()==1&&t.front().identifier) {
        auto name=identifier(t.front());auto found=m.constants.find(name);
        if(found==m.constants.end())error(m.source,"unknown model constant "+name);
        if(!active.insert(name).second)error(m.source,"cyclic model constant "+name);
        auto v=resolve(m,lex(found->second),corner,active,depth+1);active.erase(name);return v;
    }
    if(t.size()!=1||t[0].identifier)error(m.source,"unsupported model delay constant expression: "+text(t,0,t.size()));
    std::string v=t[0].text;v.erase(std::remove(v.begin(),v.end(),'_'),v.end());
    // Validate the decimal grammar without quantizing it or imposing uint64
    // tick limits; huge values may be diagnosed at actual target conversion.
    size_t i=0,digits=0;while(i<v.size()&&std::isdigit(static_cast<unsigned char>(v[i]))){++i;++digits;}
    if(i<v.size()&&v[i]=='.'){++i;while(i<v.size()&&std::isdigit(static_cast<unsigned char>(v[i]))){++i;++digits;}}
    if(!digits)error(m.source,"model delay must be a decimal: "+v);
    if(i<v.size()&&(v[i]=='e'||v[i]=='E')) {++i;if(i<v.size()&&(v[i]=='+'||v[i]=='-'))++i;auto start=i;while(i<v.size()&&std::isdigit(static_cast<unsigned char>(v[i])))++i;if(i==start)error(m.source,"invalid decimal exponent");}
    if(i!=v.size())error(m.source,"unsupported model delay literal: "+v);
    return v;
}
std::string quote(const std::string& s) {
    std::ostringstream out;out<<'"';for(unsigned char c:s){if(c=='"'||c=='\\')out<<'\\'<<c;else if(c<32){const char* h="0123456789abcdef";out<<"\\u00"<<h[c>>4]<<h[c&15];}else out<<c;}out<<'"';return out.str();
}
template<class T> void strings(std::ostream& out,const T& v) {out<<'[';bool first=true;for(const auto& s:v){if(!first)out<<',';first=false;out<<quote(s);}out<<']';}
}
TimingLibrary parse_timing_models(const Preprocessed& source) {return Reader(source).run();}
TimingLibrary read_timing_models(const std::vector<std::string>& files,const PreprocessOptions& options) {auto model_options=options;model_options.timing_model_source=true;return parse_timing_models(preprocess(files,model_options));}
const TimingModel& TimingLibrary::model(const std::string& name) const {
    for(const auto& m:models)if(m.name==name)return m;
    throw std::runtime_error("missing Verilog timing model "+name);
}
std::vector<std::string> TimingModel::initial(const TimingPath& path,int corner) const {
    if(corner<0||corner>2)throw std::runtime_error("invalid timing model corner");
    std::vector<std::string> result;std::set<std::string> active;
    for(const auto& delay:path.delays)result.push_back(resolve(*this,lex(delay),corner,active,0));
    return result;
}
std::string timing_expression_key(const std::string& s) {
    auto t=unwrap(lex(s));std::string result;
    for(const auto& token:t){auto value=token.identifier?identifier(token):token.text;result+=std::to_string(value.size())+":"+value;}
    return result;
}

uint16_t timing_edge_mask(const std::string& edge) {
    // 01,10,0Z,Z1,1Z,Z0,0X,X1,1X,X0,XZ,ZX
    // X and Z are equivalent unknowns for an unqualified timing event.
    if(edge.empty())return 1023;
    if(edge=="posedge")return (1<<0)|(1<<2)|(1<<3)|(1<<6)|(1<<7);
    if(edge=="negedge")return (1<<1)|(1<<4)|(1<<5)|(1<<8)|(1<<9);
    static const std::vector<std::string> names={"01","10","0z","z1","1z","z0","0x","x1","1x","x0","xz","zx"};
    auto lower=edge;std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return char(std::tolower(c));});
    auto found=std::find(names.begin(),names.end(),lower);
    if(found==names.end())throw std::runtime_error("unsupported timing event edge: "+edge);
    return uint16_t(1u<<size_t(found-names.begin()));
}
TimingEvent timing_event(const std::string& expression) {
    auto t=unwrap(lex(expression));TimingEvent event;
    size_t cond=t.size();for(size_t i=0;i<t.size();++i)if(t[i].text=="&&&"){cond=i;break;}
    if(cond<t.size())event.condition=text(t,cond+1,t.size());
    t=unwrap(Tokens(t.begin(),t.begin()+cond));size_t first=0;
    if(!t.empty()&&(t[0].text=="posedge"||t[0].text=="negedge")){event.transitions=timing_edge_mask(t[0].text);first=1;}
    else if(!t.empty()&&t[0].text=="edge") {
        first=1;if(first==t.size()||t[first++].text!="[")throw std::runtime_error("invalid timing edge list: "+expression);
        event.transitions=0;bool need_edge=true;
        while(first<t.size()&&t[first].text!="]") {
            if(need_edge){event.transitions|=timing_edge_mask(t[first++].text);need_edge=false;}
            else {if(t[first++].text!=",")throw std::runtime_error("invalid timing edge list: "+expression);need_edge=true;}
        }
        if(need_edge||first==t.size())throw std::runtime_error("invalid timing edge list: "+expression);++first;
    }
    if(first<t.size()&&t[first].identifier) {
        event.pin=identifier(t[first++]);
        if(first+3==t.size()&&t[first].text=="["&&t[first+2].text=="]"&&t[first+1].text.find_first_not_of("0123456789")==std::string::npos) {
            event.pin+="["+t[first+1].text+"]";first+=3;
        }
    }
    if(event.pin.empty()||first!=t.size())throw std::runtime_error("unsupported timing check event: "+expression);
    return event;
}
std::vector<TimingCheckSpec> TimingModel::executable_checks(int corner) const {
    std::vector<TimingCheckSpec> result;
    for(uint32_t index=0;index<checks.size();++index) {
        const auto& c=checks[index];const auto& a=c.arguments;TimingCheckSpec check;check.declaration=index;
        static const std::map<std::string,TimingCheckSpec::Kind> kinds={{"$setup",TimingCheckSpec::Setup},{"$hold",TimingCheckSpec::Hold},{"$recovery",TimingCheckSpec::Recovery},{"$removal",TimingCheckSpec::Removal},{"$setuphold",TimingCheckSpec::SetupHold},{"$recrem",TimingCheckSpec::RecRem},{"$width",TimingCheckSpec::Width},{"$period",TimingCheckSpec::Period},{"$skew",TimingCheckSpec::Skew}};
        auto kind=kinds.find(c.kind);if(kind==kinds.end())error(c.source,"timing-check execution is not implemented: "+c.kind);
        check.kind=kind->second;
        bool single=check.kind==TimingCheckSpec::Width||check.kind==TimingCheckSpec::Period;
        bool paired=check.kind==TimingCheckSpec::SetupHold||check.kind==TimingCheckSpec::RecRem;
        size_t limit=single?1:2,required=limit+(paired?2:1),notifier=check.kind==TimingCheckSpec::Width?3:required;
        for(size_t i=notifier;i<a.size();++i)if(!a[i].empty())error(c.source,"timing-check notifier/extended arguments require functional Verilog model support");
        check.events[0]=timing_event(a[0]);if(!single)check.events[1]=timing_event(a[1]);
        if(check.kind==TimingCheckSpec::Hold||check.kind==TimingCheckSpec::SetupHold||check.kind==TimingCheckSpec::Skew)std::swap(check.events[0],check.events[1]);
        if(single&&check.events[0].transitions==4095)error(c.source,"WIDTH/PERIOD requires an edge-qualified reference event");
        for(size_t i=0;i<(paired?2u:1u);++i) {
            std::set<std::string> active;auto raw=resolve(*this,lex(a.at(limit+i)),corner,active,0);
            // Default VCS mode clips negative timing limits; delayed reference/
            // data semantics (+neg_tchk) are a separate, unsupported mode.
            bool negative=!raw.empty()&&raw.front()=='-';auto value=sdf_ticks(negative?raw.substr(1):raw,time.unit_fs,time.precision_fs);
            check.limits[i]=negative?0:value;
            if(negative&&value)++check.negative_limits_clamped;
        }
        if(check.kind==TimingCheckSpec::Width&&a.size()>2&&!a[2].empty()) {
            std::set<std::string> active;auto raw=resolve(*this,lex(a[2]),corner,active,0);check.threshold=sdf_ticks(raw,time.unit_fs,time.precision_fs);
        }
        for(size_t i=0;i<(single?1u:2u);++i)if(!ports.count(check.events[i].pin))error(c.source,"timing event is not a model port: "+check.events[i].pin);
        result.push_back(std::move(check));
    }
    return result;
}
std::string TimingModel::resolve_condition(const std::string& expression) const {
    if(expression.empty())return expression;
    auto tokens=lex(expression);bool changed=false;std::set<std::string> active;
    std::function<std::string(const std::string&)> resolve=[&](const std::string& name) -> std::string {
        if(ports.count(name))return name;
        auto found=aliases.find(name);
        if(found==aliases.end()||found->second.empty())error(source,"unknown or multiply-driven timing condition alias: "+name);
        if(active.size()>=64||!active.insert(name).second)error(source,"cyclic/deep timing condition alias: "+name);
        auto rhs=lex(found->second);
        // A direct scalar net alias has no separate expression evaluation event.
        // Boolean logic needs actual elaborated internal nets, not substitution.
        if(rhs.size()!=1||!rhs[0].identifier)error(source,"timing condition alias must directly name a scalar port: "+name);
        auto result=resolve(identifier(rhs[0]));active.erase(name);return result;
    };
    for(size_t i=0;i<tokens.size();++i) {
        auto& t=tokens[i];if(!t.identifier)continue;
        auto key=identifier(t);
        if(i+3<tokens.size()&&tokens[i+1].text=="["&&tokens[i+3].text=="]"&&ports.count(key+"["+tokens[i+2].text+"]")){i+=3;continue;}
        if(!ports.count(key)){auto name=resolve(key);t.text=name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")==std::string::npos?name:"\\"+name+" ";changed=true;}
    }
    return changed?text(tokens,0,tokens.size()):expression;
}
std::string timing_condition_code(const std::string& condition,const std::function<std::string(const std::string&)>& pin) {
    if(condition.empty())return "V(1)";
    const auto tokens=lex(condition);size_t pos=0;int depth=0;
    const std::map<std::string,std::pair<int,std::string>> ops={{"||",{1,"LogicalOr"}},{"&&",{2,"LogicalAnd"}},{"|",{3,"BitOr"}},{"^",{4,"BitXor"}},{"&",{5,"BitAnd"}},{"==",{6,"Equal"}},{"!=",{6,"NotEqual"}},{"===",{6,"CaseEqual"}},{"!==",{6,"CaseNotEqual"}}};
    auto fail=[&](){throw std::runtime_error("unsupported timing condition: "+condition);};
    std::function<std::string(int)> expr;
    std::function<std::string()> atom=[&]() -> std::string {
        if(++depth>128||pos==tokens.size())fail();auto token=tokens[pos++];std::string out;
        if(token.text=="!"||token.text=="~")out="unary(\""+token.text+"\","+atom()+",1)";
        else if(token.text=="("){out=expr(1);if(pos==tokens.size()||tokens[pos++].text!=")")fail();}
        else if(token.identifier) {
            auto name=identifier(token);if(pos+2<tokens.size()&&tokens[pos].text=="["&&tokens[pos+2].text=="]"){name+="["+tokens[pos+1].text+"]";pos+=3;}
            out=pin(name);
        } else if(token.text=="0"||token.text=="1"||token.text=="1'b0"||token.text=="1'b1")out="V("+std::string(token.text.back()=='1'?"1":"0")+")";
        else if(token.text=="1'bx"||token.text=="1'bX")out="V::x(1)";
        else if(token.text=="1'bz"||token.text=="1'bZ")out="V::z(1)";
        else fail();--depth;return out;
    };
    expr=[&](int level){auto out=atom();while(pos<tokens.size()){auto found=ops.find(tokens[pos].text);if(found==ops.end()||found->second.first<level)break;++pos;auto right=expr(found->second.first+1);out="binary_op<Binary::"+found->second.second+">("+out+","+right+",1)";}return out;};
    auto out=expr(1);if(pos!=tokens.size())fail();return out;
}
std::string TimingLibrary::report() const {
    std::ostringstream out;out<<"{\"schema\":\"dsim.timing-model.v1\",\"functional_verilog_compiled\":false,\"models\":[";
    bool first=true;
    for(const auto& m:models) {
        if(!first)out<<',';first=false;out<<"{\"name\":"<<quote(m.name)<<",\"unit_fs\":"<<m.time.unit_fs<<",\"precision_fs\":"<<m.time.precision_fs<<",\"ports\":{";
        bool f=true;for(const auto& p:m.ports){if(!f)out<<',';f=false;out<<quote(p.first)<<':'<<quote(p.second);}out<<"},\"constants\":{";
        f=true;for(const auto& p:m.constants){if(!f)out<<',';f=false;out<<quote(p.first)<<':'<<quote(p.second);}out<<"},\"paths\":[";
        f=true;for(const auto& p:m.paths) {
            if(!f)out<<',';f=false;out<<"{\"inputs\":";strings(out,p.inputs);out<<",\"outputs\":";strings(out,p.outputs);
            out<<",\"full\":"<<(p.full?"true":"false")<<",\"edge\":"<<quote(p.edge)<<",\"polarity\":"<<quote(p.polarity)<<",\"output_polarity\":"<<quote(p.output_polarity)<<",\"data\":"<<quote(p.data)<<",\"condition\":"<<quote(p.condition)<<",\"ifnone\":"<<(p.ifnone?"true":"false")<<",\"delays\":";
            strings(out,p.delays);out<<",\"file\":"<<quote(p.source.file)<<",\"line\":"<<p.source.line<<'}';
        }
        out<<"],\"checks\":[";f=true;for(const auto& c:m.checks) {if(!f)out<<',';f=false;out<<"{\"kind\":"<<quote(c.kind)<<",\"arguments\":";strings(out,c.arguments);out<<",\"file\":"<<quote(c.source.file)<<",\"line\":"<<c.source.line<<'}';}
        out<<"],\"pulse_declarations\":";strings(out,m.pulse_declarations);out<<'}';
    }
    out<<"],\"dependencies\":";strings(out,dependencies);out<<"}\n";return out.str();
}
}
