#include "sdf.hpp"
#include <algorithm>
#include <cctype>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace dsim {
namespace {
bool space(int c) { return c!=EOF && std::isspace(static_cast<unsigned char>(c)); }
std::string trim(std::string s) {
    auto a=s.find_first_not_of(" \t\r\n"),b=s.find_last_not_of(" \t\r\n");
    return a==std::string::npos?std::string():s.substr(a,b-a+1);
}
bool decimal(const std::string& s) {
    size_t i=0,digits=0;
    if(i<s.size()&&(s[i]=='+'||s[i]=='-'))++i;
    while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}
    if(i<s.size()&&s[i]=='.') {
        ++i;while(i<s.size()&&s[i]>='0'&&s[i]<='9'){++i;++digits;}
    }
    if(!digits)return false;
    if(i<s.size()&&(s[i]=='e'||s[i]=='E')) {
        ++i;if(i<s.size()&&(s[i]=='+'||s[i]=='-'))++i;
        auto begin=i;while(i<s.size()&&s[i]>='0'&&s[i]<='9')++i;
        if(i==begin)return false;
    }
    return i==s.size();
}
std::string quote(const std::string& s) {
    std::string r="\"";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\')r+='\\';
        if(c=='\n')r+="\\n";else if(c=='\r')r+="\\r";else if(c=='\t')r+="\\t";
        else if(c<32) { const char* h="0123456789abcdef";r+="\\u00";r+=h[c>>4];r+=h[c&15]; }
        else r+=char(c);
    }
    return r+'"';
}
struct Token { enum Kind { Open,Close,Atom,String,End } kind=End; std::string text;size_t line=1,column=1; };
struct Node { bool list=false,quoted=false;std::string text;std::vector<Node> children;size_t line=0; };
class Parser {
    std::istream& in;
    std::string filename;
    SdfCallbacks callbacks;
    size_t line=1,column=1,nodes=0,entry_bytes=0;
    Token token;
    SdfStats stats;
    SdfCell cell;
    int take() {int c=in.get();if(c=='\n'){++line;column=1;}else if(c!=EOF)++column;return c;}
    [[noreturn]] void error(const std::string& message,size_t at=0) const {
        throw std::runtime_error(filename+":"+std::to_string(at?at:token.line)+":"+std::to_string(token.column)+": SDF: "+message);
    }
    void next() {
        for(;;) {
            while(space(in.peek()))take();
            if(in.peek()!='/')break;
            take();
            if(in.peek()=='/') {while(in.peek()!=EOF&&take()!='\n'){};continue;}
            if(in.peek()=='*') {
                take();bool done=false;
                while(in.peek()!=EOF) {if(take()=='*'&&in.peek()=='/'){take();done=true;break;}}
                if(!done)error("unterminated block comment",line);
                continue;
            }
            token={Token::Atom,"/",line,column-1};return;
        }
        token={Token::End,"",line,column};
        int c=in.peek();if(c==EOF){if(in.bad())error("input read failed");return;}
        take();
        if(c=='('){token.kind=Token::Open;return;}
        if(c==')'){token.kind=Token::Close;return;}
        if(c=='"') {
            token.kind=Token::String;bool done=false;
            while(in.peek()!=EOF) {
                c=take();if(c=='"'){done=true;break;}
                if(c=='\\') {if(in.peek()==EOF)break;c=take();if(c!='"'&&c!='\\')token.text+='\\';}
                token.text+=char(c);if(token.text.size()>1048576)error("token exceeds 1 MiB");
            }
            if(!done)error("unterminated quoted string");
            return;
        }
        token.kind=Token::Atom;token.text+=char(c);
        if(c=='\\'&&in.peek()!=EOF)token.text+=char(take());
        while(in.peek()!=EOF&&!space(in.peek())&&in.peek()!='('&&in.peek()!=')'&&in.peek()!='"') {
            c=take();token.text+=char(c);
            if(c=='\\'&&in.peek()!=EOF)token.text+=char(take());
            if(token.text.size()>1048576)error("token exceeds 1 MiB");
        }
    }
    void expect(Token::Kind kind,const std::string& message) {if(token.kind!=kind)error(message);}
    std::string open() {expect(Token::Open,"expected '('");next();expect(Token::Atom,"expected keyword");auto key=token.text;next();return key;}
    void close(){expect(Token::Close,"expected ')'");next();}
    Node node(size_t depth=0) {
        if(depth>128||++nodes>65536)error("entry exceeds nesting/node limit");
        Node n;n.line=token.line;
        if(token.kind==Token::Open) {
            n.list=true;next();while(token.kind!=Token::Close) {
                if(token.kind==Token::End)error("unterminated list",n.line);
                n.children.push_back(node(depth+1));
            }
            next();
        } else {
            if(token.kind!=Token::Atom&&token.kind!=Token::String)error("expected value");
            n.quoted=token.kind==Token::String;n.text=token.text;
            entry_bytes+=n.text.size();if(entry_bytes>8*1048576)error("entry exceeds 8 MiB");next();
        }
        return n;
    }
    Node entry_node(){nodes=entry_bytes=0;return node();}
    std::string atom(const Node& n,bool string=false) const {
        if(n.list||(!string&&n.text.empty())||(string&&!n.quoted)||(!string&&n.quoted))error(string?"expected quoted string":"expected identifier/number",n.line);
        return n.text;
    }
    std::string key(const Node& n) const {
        if(!n.list||n.children.empty())error("expected nonempty keyword list",n.line);
        return atom(n.children[0]);
    }
    std::string render(const Node& n) const {
        if(!n.list)return n.quoted?quote(n.text):n.text;
        std::string s="(";for(const auto& c:n.children){if(s.size()>1)s+=' ';s+=render(c);}return s+")";
    }
    std::string expression(const std::vector<Node>& ns,size_t a,size_t b) const {
        if(a==b)error("empty condition");
        std::string s;for(size_t i=a;i<b;++i){if(!s.empty())s+=' ';s+=render(ns[i]);}return s;
    }
    SdfTriple triple(const Node& n) const {
        if(!n.list)error("timing value must be parenthesized",n.line);
        std::string s;
        for(const auto& c:n.children){if(c.list||c.quoted)error("expected decimal/triple",c.line);if(!s.empty())s+=' ';s+=c.text;}
        SdfTriple t;if(s.empty())return t;
        auto p=s.find(':');
        if(p==std::string::npos) {
            s=trim(s);if(!decimal(s))error("invalid decimal value: "+s,n.line);
            t.scalar=true;for(auto& c:t.corner)c=s;return t;
        }
        auto q=s.find(':',p+1);
        if(q==std::string::npos||s.find(':',q+1)!=std::string::npos)error("expected min:typ:max triple",n.line);
        std::array<std::string,3> pieces={s.substr(0,p),s.substr(p+1,q-p-1),s.substr(q+1)};
        bool any=false;
        for(size_t i=0;i<3;++i) {auto v=trim(pieces[i]);if(v.empty())continue;if(!decimal(v))error("invalid decimal corner: "+v,n.line);t.corner[i]=v;any=true;}
        if(!any)error("all-empty triple must be written ()",n.line);
        return t;
    }
    SdfDelayValue delay_value(const Node& n) const {
        if(!n.list)error("delay must be parenthesized",n.line);
        if(n.children.empty()||!n.children[0].list)return {triple(n),{}, {}};
        if(n.children.size()>3)error("delay has more than three pulse values",n.line);
        SdfDelayValue v;v.delay=triple(n.children[0]);
        if(n.children.size()>1)v.reject=triple(n.children[1]);
        if(n.children.size()>2)v.xlimit=triple(n.children[2]);
        return v;
    }
    SdfPort port(const Node& n,bool timing=false) const {
        if(!n.list)return {atom(n),"","",""};
        auto k=key(n);
        if(k=="COND"&&timing) {
            auto& cs=n.children;size_t a=1;std::string label;
            if(a<cs.size()&&cs[a].quoted)label=cs[a++].text;
            if(a+1>=cs.size())error("conditional timing port requires expression and port",n.line);
            auto p=port(cs.back());p.condition=expression(cs,a,cs.size()-1);p.label=label;return p;
        }
        static const std::vector<std::string> edges={"posedge","negedge","01","10","0z","z1","1z","z0","0Z","Z1","1Z","Z0"};
        if(n.children.size()!=2||std::find(edges.begin(),edges.end(),k)==edges.end())error("invalid edge port",n.line);
        return {atom(n.children[1]),k,"",""};
    }
    SdfEntry delay(const Node& n,SdfEntry::Mode mode) const {
        SdfEntry e;e.mode=mode;e.line=n.line;e.kind=key(n);const auto& cs=n.children;size_t a=1;
        if(e.kind=="COND"||e.kind=="CONDELSE") {
            if(cs.size()<2)error("empty conditional path",n.line);
            auto nested=delay(cs.back(),mode);
            if(nested.kind!="IOPATH"||!nested.condition.empty()||nested.conditional_else)error("COND/CONDELSE requires one IOPATH",n.line);
            if(e.kind=="CONDELSE") {if(cs.size()!=2)error("CONDELSE has unexpected values",n.line);nested.conditional_else=true;}
            else {if(cs[a].quoted)nested.label=cs[a++].text;nested.condition=expression(cs,a,cs.size()-1);}
            nested.line=n.line;return nested;
        }
        size_t count=e.kind=="IOPATH"||e.kind=="INTERCONNECT"?2:e.kind=="PORT"?1:0;
        if(e.kind!="IOPATH"&&e.kind!="INTERCONNECT"&&e.kind!="PORT"&&e.kind!="DEVICE")error("unsupported delay construct: "+e.kind,n.line);
        if(e.kind=="DEVICE"&&a<cs.size()&&!cs[a].list)count=1;
        if(cs.size()<1+count)error("missing path endpoint",n.line);
        for(size_t i=0;i<count;++i) {
            if(e.kind=="IOPATH"&&i==0)e.ports.push_back(port(cs[a++]));
            else e.ports.push_back({atom(cs[a++]),"","",""});
        }
        while(a<cs.size()&&cs[a].list&&!cs[a].children.empty()&&!cs[a].children[0].list&&cs[a].children[0].text=="RETAIN") {
            if(e.kind!="IOPATH")error("RETAIN is only valid for IOPATH",cs[a].line);
            const auto& r=cs[a++];std::vector<SdfDelayValue> values;
            for(size_t i=1;i<r.children.size();++i)values.push_back(delay_value(r.children[i]));
            if(values.empty())error("empty RETAIN",r.line);
            e.retain.push_back(std::move(values));
        }
        for(;a<cs.size();++a)e.values.push_back(delay_value(cs[a]));
        auto size=e.values.size();
        if(size!=1&&size!=2&&size!=3&&size!=6&&size!=12)error("delay list must have 1, 2, 3, 6 or 12 values",n.line);
        for(const auto& r:e.retain)if(r.size()!=1&&r.size()!=2&&r.size()!=3&&r.size()!=6&&r.size()!=12)error("invalid RETAIN transition count",n.line);
        return e;
    }
    SdfEntry check(const Node& n) const {
        SdfEntry e;e.mode=SdfEntry::Mode::TimingCheck;e.line=n.line;e.kind=key(n);
        static const std::map<std::string,std::pair<size_t,size_t>> shape={
            {"SETUP",{2,1}},{"HOLD",{2,1}},{"SETUPHOLD",{2,2}},
            {"RECOVERY",{2,1}},{"REMOVAL",{2,1}},{"RECREM",{2,2}},
            {"SKEW",{2,1}},{"BIDIRECTSKEW",{2,2}},{"WIDTH",{1,1}},
            {"PERIOD",{1,1}},{"NOCHANGE",{2,2}}};
        auto it=shape.find(e.kind);if(it==shape.end())error("unsupported timing check: "+e.kind,n.line);
        auto [ports,values]=it->second;
        if(n.children.size()!=1+ports+values)error("invalid timing-check arity (optional extensions not supported yet)",n.line);
        for(size_t i=1;i<=ports;++i)e.ports.push_back(port(n.children[i],true));
        for(size_t i=1+ports;i<n.children.size();++i)e.values.push_back({triple(n.children[i]),{}, {}});
        return e;
    }
    void emit(SdfEntry e) {
        ++stats.entries;++stats.kinds[e.kind];stats.retains+=e.retain.size();
        if(e.mode==SdfEntry::Mode::Increment)++stats.incremental;
        bool conditional=!e.condition.empty()||e.conditional_else;
        for(const auto& p:e.ports)conditional=conditional||!p.condition.empty();
        stats.conditional+=conditional;
        if(callbacks.entry)callbacks.entry(cell,e);
    }
    void parse_cell(size_t at) {
        cell={};cell.line=at;
        auto type=entry_node();if(key(type)!="CELLTYPE"||type.children.size()!=2)error("CELL must start with CELLTYPE",type.line);
        cell.type=atom(type.children[1],true);
        auto instance=entry_node();if(key(instance)!="INSTANCE"||instance.children.size()>2)error("expected INSTANCE",instance.line);
        if(instance.children.size()==2)cell.instance=atom(instance.children[1]);
        ++stats.cells;if(callbacks.cell)callbacks.cell(cell);
        while(token.kind!=Token::Close) {
            auto section=open();
            if(section=="DELAY") {
                while(token.kind!=Token::Close) {
                    auto k=open();auto mode=SdfEntry::Mode::Absolute;
                    if(k=="INCREMENT")mode=SdfEntry::Mode::Increment;
                    else if(k!="ABSOLUTE")error("unsupported DELAY section: "+k);
                    while(token.kind!=Token::Close)emit(delay(entry_node(),mode));
                    close();
                }
            } else if(section=="TIMINGCHECK") {
                while(token.kind!=Token::Close)emit(check(entry_node()));
            } else error("unsupported CELL section: "+section);
            close();
        }
        close();
    }
    void header(const Node& n) {
        auto k=key(n);const auto& cs=n.children;
        if(stats.header.fields.count(k))error("duplicate header: "+k,n.line);
        static const std::vector<std::string> strings={"SDFVERSION","DESIGN","DATE","VENDOR","PROGRAM","VERSION","PROCESS"};
        if(std::find(strings.begin(),strings.end(),k)!=strings.end()) {
            if(cs.size()!=2)error("invalid string header",n.line);
            stats.header.fields[k]=atom(cs[1],true);
        } else if(k=="DIVIDER") {
            if(cs.size()!=2)error("invalid DIVIDER",n.line);
            auto v=atom(cs[1]);
            if(v!="."&&v!="/")error("DIVIDER must be . or /",n.line);
            stats.header.divider=v[0];stats.header.fields[k]=v;
        } else if(k=="TIMESCALE") {
            auto v=expression(cs,1,cs.size());v.erase(std::remove_if(v.begin(),v.end(),[](char c){return space(c);}),v.end());
            auto first=v.find_first_not_of("0123456789");
            if(first==std::string::npos)error("TIMESCALE requires a unit",n.line);
            auto multiplier=v.substr(0,first),unit=v.substr(first);
            if(multiplier!="1"&&multiplier!="10"&&multiplier!="100")error("TIMESCALE multiplier must be 1/10/100",n.line);
            static const std::map<std::string,uint64_t> units={{"fs",1},{"ps",1000},{"ns",1000000},{"us",1000000000},{"ms",1000000000000},{"s",1000000000000000}};
            auto u=units.find(unit);if(u==units.end())error("invalid TIMESCALE unit",n.line);
            stats.header.timescale_fs=std::stoull(multiplier)*u->second;stats.header.fields[k]=v;
        } else if(k=="VOLTAGE"||k=="TEMPERATURE") {
            Node values;values.list=true;values.line=n.line;values.children.assign(cs.begin()+1,cs.end());(void)triple(values);
            stats.header.fields[k]=expression(cs,1,cs.size());
        } else error("unsupported header: "+k,n.line);
    }
public:
    Parser(std::istream& input,std::string file,SdfCallbacks cb):in(input),filename(std::move(file)),callbacks(std::move(cb)){}
    SdfStats run() {
        next();if(open()!="DELAYFILE")error("expected DELAYFILE");
        bool cells=false;
        while(token.kind!=Token::Close) {
            // Read the keyword but leave the rest of CELL streaming.
            expect(Token::Open,"expected header or CELL");
            // A one-token lookahead is enough: consume '(' and keyword here.
            auto at=token;next();expect(Token::Atom,"expected keyword");auto k=token;next();
            if(k.text=="CELL") {
                if(!cells) {
                    if(!stats.header.fields.count("SDFVERSION"))error("missing SDFVERSION");
                    if(callbacks.header)callbacks.header(stats.header);
                    cells=true;
                }
                parse_cell(at.line);
            } else {
                if(cells)error("header after CELL is not allowed",at.line);
                Node n;n.list=true;n.line=at.line;Node keyword;keyword.text=k.text;keyword.line=k.line;n.children.push_back(std::move(keyword));nodes=entry_bytes=0;
                while(token.kind!=Token::Close){if(token.kind==Token::End)error("unterminated header");n.children.push_back(node());}close();header(n);
            }
        }
        close();if(token.kind!=Token::End)error("trailing data after DELAYFILE");
        if(!stats.cells)error("DELAYFILE requires at least one CELL");
        return stats;
    }
};
}
SdfStats parse_sdf(std::istream& in,const std::string& filename,const SdfCallbacks& cb) {return Parser(in,filename,cb).run();}
SdfStats read_sdf(const std::string& filename,const SdfCallbacks& cb) {
    std::ifstream in(filename,std::ios::binary);if(!in)throw std::runtime_error("cannot read SDF "+filename);
    return parse_sdf(in,filename,cb);
}
std::string SdfStats::report() const {
    std::ostringstream out;out<<"{\"schema\":\"dsim.sdf.summary.v1\",\"annotation\":false,\"cells\":"<<cells<<",\"entries\":"<<entries
        <<",\"conditional\":"<<conditional<<",\"incremental\":"<<incremental<<",\"retains\":"<<retains<<",\"divider\":"<<quote(std::string(1,header.divider))<<",\"timescale_fs\":";
    if(header.timescale_fs)out<<*header.timescale_fs;else out<<"null";
    out<<",\"header\":{";bool first=true;for(const auto& [k,v]:header.fields){if(!first)out<<',';first=false;out<<quote(k)<<':'<<quote(v);}out<<"},\"kinds\":{";
    first=true;for(const auto& [k,v]:kinds){if(!first)out<<',';first=false;out<<quote(k)<<':'<<v;}out<<"}}\n";return out.str();
}
uint64_t sdf_ticks(const std::string& text,uint64_t scale,uint64_t tick) {
    if(!decimal(text)||!scale||!tick)throw std::runtime_error("invalid SDF decimal/time unit");
    auto power10=[](uint64_t v){int p=0;while(v>1&&v%10==0){v/=10;++p;}if(v!=1)throw std::runtime_error("SDF units must be powers of ten");return p;};
    int shift=power10(scale)-power10(tick);size_t i=0;
    bool negative=text[0]=='-';if(text[0]=='+'||text[0]=='-')++i;
    std::string digits;bool fraction=false;
    for(;i<text.size()&&text[i]!='e'&&text[i]!='E';++i) {
        if(text[i]=='.'){fraction=true;continue;}digits+=text[i];if(fraction)--shift;
    }
    if(i<text.size()) {
        ++i;bool neg=false;if(text[i]=='+'||text[i]=='-'){neg=text[i]=='-';++i;}
        int exp=0;for(;i<text.size();++i){if(exp>100000)throw std::runtime_error("SDF decimal exponent exceeds limit");exp=exp*10+text[i]-'0';}
        shift+=neg?-exp:exp;
    }
    auto begin=digits.find_first_not_of('0');if(begin==std::string::npos)return 0;digits.erase(0,begin);
    if(negative)throw std::runtime_error("negative SDF value requires signed annotation handling");
    bool round=false;
    if(shift<0) {
        auto remove=size_t(-shift);
        if(remove>digits.size())return 0;
        round=digits[digits.size()-remove]>='5';digits.resize(digits.size()-remove);
    } else {
        if(size_t(shift)+digits.size()>20)throw std::runtime_error("SDF tick overflow");
        digits.append(size_t(shift),'0');
    }
    uint64_t value=0;
    for(char c:digits){if(value>(std::numeric_limits<uint64_t>::max()-uint64_t(c-'0'))/10)throw std::runtime_error("SDF tick overflow");value=value*10+uint64_t(c-'0');}
    if(round){if(value==std::numeric_limits<uint64_t>::max())throw std::runtime_error("SDF tick overflow");++value;}
    return value;
}
}
