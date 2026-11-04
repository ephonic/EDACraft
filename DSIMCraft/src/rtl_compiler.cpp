#include <iostream>
#include "compiler.hpp"
#include "gate_compiler.hpp"
#include "gate_timing.hpp"
#include "src_mgr.hpp"
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "veri_stmt.hpp"
#include "veri_decl.hpp"
#include "veri_exp.hpp"
#include "veri_inst.hpp"
#include "veri_num.hpp"
#include "veri_var.hpp"
#include "veri_str.hpp"
#include "veri_tfmg.hpp"
#include "veri_symbol_table.hpp"
#include <algorithm>
#include <cctype>
#include "../include/dsim/partition.hpp"
#include <iomanip>
#include <iterator>
#include <list>
#include <map>
#include <limits>
#include <memory>
#include <set>
#include <tuple>
#include <sstream>
#include <stdexcept>
#include <utility>
using namespace rtl;
extern int verilog_first_error_line;
namespace dsim {
namespace {
struct InlineExpansionLimit : std::runtime_error {
    InlineExpansionLimit():std::runtime_error("generated function expansion exceeds the inline budget; use --shared-functions for serial simulation"){}
};
std::string quote(const std::string& s) {
    std::ostringstream o; o<<'"';
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') o<<'\\'<<c;
        else if(c=='\n') o<<"\\n";
        else if(c=='\t') o<<"\\t";
        else if(c=='\r') o<<"\\r";
        else if(c<32||c>=127) o<<'\\'<<std::oct<<std::setw(3)<<std::setfill('0')<<int(c)<<std::dec;
        else o<<c;
    }
    return o.str()+'"';
}
std::string escape_format_text(const std::string& text) {
    std::string out;for(char c:text){out+=c;if(c=='%')out+='%';}return out;
}
std::string json_quote(const std::string& s) {
    std::ostringstream out; out<<'"';
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') out<<'\\'<<c;
        else if(c<32) out<<"\\u00"<<std::hex<<std::setw(2)<<std::setfill('0')<<int(c)<<std::dec;
        else out<<c;
    }
    out<<'"'; return out.str();
}
[[noreturn]] void fail(VeriNode* n,const std::string& s) {
    throw std::runtime_error("line "+std::to_string(n?n->line():0)+": "+s);
}
std::string decode_string(std::string text,VeriNode* owner) {
    if(text.size()>=2 && text.front()=='"' && text.back()=='"')text=text.substr(1,text.size()-2);
    auto decoded=veri_decode_string(text);
    if(decoded.find('\0')!=std::string::npos)fail(owner,"embedded NUL string escape is not supported yet");
    return decoded;
}
bool struct_has_strings(VeriVar* type) {
    if(!type||!type->unpacked_struct())return false;
    for(const auto& field:type->packed_fields())if(veri_string_value(field.symbol)||struct_has_strings(field.symbol->aggregate_type()))return true;
    return false;
}
// Owned IR. Once lowered, no parser pointers survive in expressions or processes.
static constexpr int opaque_handle_type=-3;
struct Expr {
    int real_width=0;
    std::string op, literal; int width=1,signal=-1; bool signed_value=false,host_overflow=false,negative=false,procedural_only=false,canonical_literal=false;
    bool selection_checks=false,event_safe=true,io_state=false,random_state=false,function_forks=false,text_value=false,packed_literal=false,constant_text=false;
    std::shared_ptr<VeriVirtualInterface> interface_type;
    unsigned enum_id=0; // Canonical parser identity copied by value, compile time only.
    int object_type=-1; // -1 integral/string, -2 null, -3 opaque C handle, >=0 class identity.
    bool interface_namespace=false;
    bool receiver_argument=false,virtual_dispatch=false,array_value=false,event_snapshot=false,interface_dereference=false;
    std::string argument_prefix="call_arg",argument_alias_prefix;
    uint64_t value=0,unknown=0;
    std::shared_ptr<Expr> packed_value; // Alternate integral view of string literal syntax.
    std::vector<std::shared_ptr<Expr>> args; std::set<int> reads,touches,writes,function_reads,partial_writes,whole_writes,nonstatic_writes;
    std::set<std::tuple<int,int,int>> write_ranges;
    std::vector<std::shared_ptr<Expr>> sensitivity_reads;
    std::set<int> direct_reads;
};
using E=std::shared_ptr<Expr>;
E node(std::string op,int width,std::vector<E> args={}) {
    if(width<1 || width>1048576) throw std::runtime_error("expression width exceeds supported range 1..1048576");
    for(const auto& a:args)if(a->array_value&&op!="call"&&op!="array_argument")throw std::runtime_error("unpacked array value cannot be used in integral operation "+op);
    for(const auto& a:args)if(a->interface_type&&op!="call"&&op!="argument"&&op!="array_argument"&&op!="handle_mux"&&op!="=="&&op!="!="&&op!="==="&&op!="!=="&&op!="!"&&op!="&&"&&op!="||")
        throw std::runtime_error("virtual interface cannot be used in integral operation "+op);
    for(const auto& a:args)if(a->object_type==opaque_handle_type&&(op=="!"||op=="&&"||op=="||"))throw std::runtime_error("chandle cannot be used as a boolean operand");
    for(const auto& a:args)if(a->object_type!=-1&&op!="argument"&&op!="array_argument"&&op!="call"&&op!="object_format"&&op!="container_method"&&op!="container_ref"&&op!="associative_read"&&op!="object_read"&&op!="handle_mux"&&op!="=="&&op!="!="&&op!="==="&&op!="!=="&&op!="!"&&op!="&&"&&op!="||")
        throw std::runtime_error("class handle cannot be used in integral operation "+op);
    for(auto& a:args)if(a->text_value&&op.rfind("text_",0)!=0&&op!="argument"&&op!="array_argument"&&op!="call"&&op!="object_format"&&op!="container_method"&&op!="container_ref"&&op!="associative_read"&&op!="struct_string_pack"&&op!="array_reduce_with") {
        if(a->packed_value)a=a->packed_value;
        else throw std::runtime_error("string operand is not supported in integral operation "+op);
    }
    E e=std::make_shared<Expr>(); e->op=std::move(op); e->width=width; e->args=std::move(args);
    for(const auto& arg:e->args){e->event_snapshot|=arg->event_snapshot;e->interface_dereference|=arg->interface_dereference;}
    const bool real=std::any_of(e->args.begin(),e->args.end(),[](const E& a){return a->real_width!=0;});
    if(real) {
        if(e->op=="+"||e->op=="-"||e->op=="*"||e->op=="/"||e->op=="**"||e->op=="mux"){for(size_t i=e->op=="mux"?1:0;i<e->args.size();++i)e->real_width=std::max(e->real_width,e->args[i]->real_width);if(e->real_width){e->width=e->real_width;e->signed_value=true;}}
        static const std::set<std::string> integral={"~","&","|","^","%","<<",">>",">>>","===","!==","==?","!=?","concat","replicate","slice","indexed_slice","stream"};
        if(integral.count(e->op))throw std::runtime_error("operator requires integral operands: "+e->op);
    }
    for(auto& a:e->args) {e->function_forks|=a->function_forks;e->virtual_dispatch|=a->virtual_dispatch;e->io_state|=a->io_state;e->random_state|=a->random_state;e->event_safe&=a->event_safe;e->selection_checks|=a->selection_checks;e->procedural_only|=a->procedural_only;e->reads.insert(a->reads.begin(),a->reads.end());e->touches.insert(a->touches.begin(),a->touches.end());e->writes.insert(a->writes.begin(),a->writes.end());e->function_reads.insert(a->function_reads.begin(),a->function_reads.end());e->partial_writes.insert(a->partial_writes.begin(),a->partial_writes.end());e->whole_writes.insert(a->whole_writes.begin(),a->whole_writes.end());e->write_ranges.insert(a->write_ranges.begin(),a->write_ranges.end());e->nonstatic_writes.insert(a->nonstatic_writes.begin(),a->nonstatic_writes.end());}
    return e;
}
// A mixed unsigned context propagates through context-determined operands.
// Casts, concatenation items, shift amounts and logical operands are boundaries.
std::string emit_expression(E e,int context=0,bool mapped=false,int sign_context=-1) {
    int w=std::max(context,e->width);std::string sw=std::to_string(w);
    bool sign=e->signed_value&&sign_context!=0;
    auto resize=[&](const std::string& text) {
        if(e->real_width)return text;
        return sign&&w>e->width?"signed_size("+text+","+sw+")":text+".size("+sw+")";
    };
    if(e->op=="saved_ref")return e->literal;
    if(e->op=="struct_mux")return "([&](){auto c="+emit_expression(e->args[0],0,mapped)+";if(c.truth()<0)throw std::runtime_error(\"unknown struct conditional selector is not supported yet\");return c.truth()?"+emit_expression(e->args[1],0,mapped)+":"+emit_expression(e->args[2],0,mapped)+";}())";
    if(e->op=="handle_mux")return "([&](){auto handle_condition="+emit_expression(e->args[0],0,mapped)+";if(handle_condition.truth()<0)throw std::runtime_error(\"unknown chandle conditional selector\");return handle_condition.truth()?"+emit_expression(e->args[1],0,mapped)+":"+emit_expression(e->args[2],0,mapped)+";}())";
    if(e->op=="class_mux")return "([&](){auto class_condition="+emit_expression(e->args[0],0,mapped)+";if(class_condition.truth()==1)return "+emit_expression(e->args[1],0,mapped)+";if(class_condition.truth()<0)(void)("+emit_expression(e->args[1],0,mapped)+");return "+emit_expression(e->args[2],0,mapped)+";}())";
    if(e->op=="real_convert")return "real_convert("+emit_expression(e->args[0],0,mapped)+","+std::to_string(e->real_width)+","+std::to_string(e->width)+","+(e->args[0]->signed_value?"true":"false")+")";
    if(e->op=="real_system")return e->literal+"("+emit_expression(e->args[0],0,mapped)+")";
    if(e->op=="mux"&&e->real_width)return "([&](){auto c="+emit_expression(e->args[0],0,mapped)+";if(c.truth()<0)return V::real(0,"+std::to_string(e->real_width)+");return c.truth()?real_convert("+emit_expression(e->args[1],0,mapped)+","+std::to_string(e->real_width)+","+std::to_string(e->real_width)+","+(e->args[1]->signed_value?"true":"false")+"):real_convert("+emit_expression(e->args[2],0,mapped)+","+std::to_string(e->real_width)+","+std::to_string(e->real_width)+","+(e->args[2]->signed_value?"true":"false")+");}())";
    static const std::set<std::string> real_ops={"+","-","*","/","**","==","!=","<",">","<=",">=","!","&&","||"};
    if(real_ops.count(e->op)&&std::any_of(e->args.begin(),e->args.end(),[](const E& a){return a->real_width!=0;})) {
        std::string code="([&](){auto real_a="+emit_expression(e->args[0],0,mapped)+";";
        if(e->args.size()==1)return code+"return "+(e->op=="!"?"V(real_a.truth()==0)":"V::real("+(e->op=="-"?std::string("-"):std::string())+"real_a.real_value(),"+std::to_string(e->real_width)+")")+";}())";
        if(e->op=="&&")code+="if(real_a.truth()==0)return V(0);";
        if(e->op=="||")code+="if(real_a.truth()==1)return V(1);";
        code+="auto real_b="+emit_expression(e->args[1],0,mapped)+";return real_operation("+quote(e->op)+",real_a,"+(e->args[0]->signed_value?"true":"false")+",real_b,"+(e->args[1]->signed_value?"true":"false")+");}())";
        return code;
    }
    if(e->op=="struct_string_pack")return "V::string_field("+emit_expression(e->args[0],0,mapped)+")";
    if(e->op=="struct_string_default")return "([&](){auto aggregate="+emit_expression(e->args[0],0,mapped)+";aggregate.struct_strings=std::make_shared<const V::StructStrings>(V::StructStrings{"+e->literal+"});return aggregate;}())";
    if(e->op=="text_literal")return "V::text("+e->literal+")";
    if(e->op=="text_inside") {
        std::string code="([&](){auto inside_value="+emit_expression(e->args[0],0,mapped)+".text_value();";
        for(size_t i=1;i<e->args.size();++i)code+="if(inside_value=="+emit_expression(e->args[i],0,mapped)+".text_value())return V(1,0,1);";
        return code+"return V(0,0,1);}())";
    }
    if(e->op=="text_repeat")return "([&](){auto repeat_count="+emit_expression(e->args[0],0,mapped)+";auto repeat_text="+emit_expression(e->args[1],0,mapped)+";return text_repeat(repeat_count,repeat_text,"+e->literal+");}())";
    if(e->op=="text_mux"&&e->packed_value)return "V::text(format("+emit_expression(e->packed_value,0,mapped)+",'s'))";
    if(e->op=="text_mux")return "([&](){auto text_condition="+emit_expression(e->args[0],0,mapped)+";if(text_condition.truth()<0){auto text_left="+emit_expression(e->args[1],0,mapped)+";auto text_right="+emit_expression(e->args[2],0,mapped)+";return text_left.text_value()==text_right.text_value()?text_left:V::text(\"\");}return text_condition.truth()==1?"+emit_expression(e->args[1],0,mapped)+":"+emit_expression(e->args[2],0,mapped)+";}())";
    if(e->op=="text_enum"||e->op=="text_method"||e->op=="text_binary") {
        std::string code="([&](){";
        for(size_t i=0;i<e->args.size();++i)code+="auto text_arg"+std::to_string(i)+"="+emit_expression(e->args[i],0,mapped)+";";
        const auto result=code+e->literal+"}())";return e->text_value?result:resize(result);
    }
    if(e->op=="event_triggered")return "V(s.event_triggered("+(e->args.empty()?(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal)):"s.event_id("+emit_expression(e->args[0],0,mapped)+")")+")?1:0,0,1)";
    if(e->op=="reduce_item")return resize(e->literal);
    if(e->op=="array_reduce_with"||e->op=="associative_reduce_with") {
        const auto width=std::to_string(e->width);
        const auto mapping=e->args.back();
        std::string code="([&](){V reduce_value(0,0,"+width+");bool reduce_first=true;";
        const auto apply=[&](const std::string& value) {
            return "{auto "+e->args[e->args.size()-2]->literal+"="+value+";auto reduce_mapped="+emit_expression(mapping,0,mapped)+";if(reduce_first){reduce_value=reduce_mapped;reduce_first=false;}else reduce_value=binary_op<Binary::"+e->literal+">(reduce_value,reduce_mapped,"+width+");}";
        };
        if(e->signal>=0) {
            code+="auto reduce_values=s."+std::string(e->op.rfind("associative",0)==0?"associative_values":"dynamic_values")+"("+(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal))+");for(const auto& reduce_element:reduce_values)"+apply("reduce_element");
        } else for(size_t i=0;i+2<e->args.size();++i)code+=apply(emit_expression(e->args[i],0,mapped));
        return resize(code+"return reduce_value;}())");
    }
    if(e->op=="array_reduce"||e->op=="associative_reduce") {
        const auto width=std::to_string(e->width);
        std::string code="([&](){";
        const auto combine="binary_op<Binary::"+e->literal+">";
        if(e->signal>=0) {
            code+="auto reduce_values=s."+std::string(e->op.rfind("associative",0)==0?"associative_values":"dynamic_values")+"("+(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal))+");";
            code+="if(reduce_values.empty())return V(0,0,"+width+");auto reduce_value=reduce_values[0];";
            code+="for(size_t i=1;i<reduce_values.size();++i)reduce_value="+combine+"(reduce_value,reduce_values[i],"+width+");";
        } else {
            code+="auto reduce_value="+emit_expression(e->args.front(),0,mapped)+";";
            for(size_t i=1;i<e->args.size();++i)code+="reduce_value="+combine+"(reduce_value,"+emit_expression(e->args[i],0,mapped)+","+width+");";
        }
        return resize(code+"return reduce_value;}())");
    }
    if(e->op=="stream") {
        const int width=e->width;
        std::string code="([&](){auto stream_value="+emit_expression(e->args[0],0,mapped)+";";
        if(width<=64) {
            code+="uint64_t stream_a=0,stream_b=0;";
            code+="for(int start=0;start<"+std::to_string(width)+";start+="+e->literal+"){int span=std::min("+e->literal+","+std::to_string(width)+"-start);int dest="+std::to_string(width)+"-start-span;";
            code+="stream_a|=((stream_value.a>>start)&mask(span))<<dest;stream_b|=((stream_value.b>>start)&mask(span))<<dest;}";
            code+="return V(stream_a,stream_b,"+std::to_string(width)+");}())";
        } else {
            code+="std::vector<V::Word> stream_words("+std::to_string((width+63)/64)+");";
            code+="for(int start=0;start<"+std::to_string(width)+";start+="+e->literal+"){int span=std::min("+e->literal+","+std::to_string(width)+"-start);int dest="+std::to_string(width)+"-start-span;";
            code+="for(int offset=0;offset<span;){int from=start+offset,to=dest+offset;int take=std::min(span-offset,std::min(64-from%64,64-to%64));";
            code+="stream_words[to/64].a|=((stream_value.word_a(from/64)>>(from%64))&mask(take))<<(to%64);stream_words[to/64].b|=((stream_value.word_b(from/64)>>(from%64))&mask(take))<<(to%64);offset+=take;}}";
            code+="return V::from_words(std::move(stream_words),"+std::to_string(width)+");}())";
        }
        return resize(code);
    }
    if(e->op=="inside") {
        int width=e->args[0]->width;bool signed_set=e->args[0]->signed_value;
        for(size_t i=1;i<e->args.size();++i){width=std::max(width,e->args[i]->width);signed_set=signed_set&&e->args[i]->signed_value;}
        std::string code="([&](){auto inside_value="+emit_expression(e->args[0],width,mapped,int(signed_set))+";V inside_result(0);";
        for(size_t i=1;i<e->args.size();++i) {
            auto item=e->args[i];code+="{V inside_match;";
            if(item->op=="inside_range") {
                code+="auto low="+emit_expression(item->args[0],width,mapped,int(signed_set))+";auto high="+emit_expression(item->args[1],width,mapped,int(signed_set))+";";
                code+="inside_match=membership_range(inside_value,low,high,"+std::string(signed_set?"true":"false")+");";
            } else code+="inside_match=wildcard_equal(inside_value,"+emit_expression(item,width,mapped,int(signed_set))+");";
            code+="if(inside_match.truth()==1)return V(1);inside_result=binary_op<Binary::LogicalOr>(inside_result,inside_match,1);}";
        }
        return resize(code+"return inside_result;}())");
    }
    if(e->op=="dynamic_query") {
        std::string code="([&](){auto dynamic_count="+emit_expression(e->args[0],0,mapped)+";";
        if(e->args.size()>1)code+="auto dimension="+emit_expression(e->args[1],0,mapped)+";";
        return resize(code+e->literal+"}())");
    }
    if(e->op=="array_query") {
        std::string code="([&](){auto dimension="+emit_expression(e->args[0],0,mapped)+";";
        return resize(code+e->literal+"return V::x(32);}())");
    }
    if(e->op=="enum_method") {
        std::string code="([&](){auto enum_value="+emit_expression(e->args[0],0,mapped)+";";
        if(e->args.size()==2)code+="auto enum_count="+emit_expression(e->args[1],32,mapped)+";";
        return resize(code+e->literal+"}())");
    }
    if(e->op=="memory_index") {
        // Evaluate every subscript once, including those after an invalid one.
        // Bounds checks use the existing full-width four-state select helper.
        std::string code="([&](){";
        for(size_t i=0;i<e->args.size();++i)
            code+="auto memory_index"+std::to_string(i)+"="+emit_expression(e->args[i],e->args[i]->signed_value?64:0,mapped)+";";
        return resize(code+"uint64_t memory_offset=0;"+e->literal+"return V(memory_offset,0,64);}())");
    }
    if(e->op=="count_bits") {
        std::string code="([&](){";
        for(size_t i=0;i<e->args.size();++i)code+="auto count_arg"+std::to_string(i)+"="+emit_expression(e->args[i],0,mapped)+";";
        code+="unsigned selected=0;";
        for(size_t i=1;i<e->args.size();++i)code+="selected|=1u<<count_arg"+std::to_string(i)+".bit(0);";
        return resize(code+"return count_bits(count_arg0,selected);}())");
    }
    if(e->op=="vector_system")return resize("vector_system<"+e->literal+">("+emit_expression(e->args[0],0,mapped)+")");
    if(e->op=="argument")return "("+emit_expression(e->args[0],e->width,mapped)+").size("+std::to_string(e->width)+")";
    if(e->op=="two_state")return resize("two_state_value("+emit_expression(e->args[0],0,mapped)+")");
    if(e->op=="fixed_cast"||e->op=="fixed_cast_2") {
        std::string value="("+emit_expression(e->args[0],e->width,mapped)+").size("+std::to_string(e->width)+")";
        if(e->op=="fixed_cast_2")value="two_state_value("+value+")";
        return resize(value);
    }
    if(e->op=="reference"||e->op=="array_argument"||(e->op=="saved"&&e->text_value))return e->literal;
    if(e->op=="property_sample")return resize("s.property_sample("+(mapped?"qid["+std::to_string(e->value)+"]":std::to_string(e->value))+","+std::to_string(e->signal)+")");
    if(e->op=="mutation"||e->op=="random")return resize(e->literal);
    if(e->op=="call"||e->op=="object_format") {
        if(e->literal.size()>1024*1024)throw InlineExpansionLimit();
        // Large SV function bodies can occur many times inside one statement.
        // Keep their native optimization separate instead of letting inlining
        // combine hundreds of PC interpreters into a single enormous function.
        std::string code="([&]()";
        // Intel's optimizer still aggressively expands the runtime helpers in
        // these outlined bodies. Favor size within this boundary only; retain
        // the configured optimization level for the enclosing design.
        if(e->literal.size()>=1024)code+=" __attribute__((noinline))\n#if defined(__INTEL_LLVM_COMPILER)\n __attribute__((minsize))\n#endif\n";
        code+="{";
        for(size_t i=0;i<e->args.size();++i) {
            const auto name=e->receiver_argument&&i==0?std::string("call_self"):e->argument_prefix+std::to_string(i-(e->receiver_argument?1:0));
            code+="auto "+name+"="+emit_expression(e->args[i],0,mapped)+";";
            if(!e->argument_alias_prefix.empty())code+="const auto& "+e->argument_alias_prefix+(e->receiver_argument&&i==0?std::string("self"):std::to_string(i-(e->receiver_argument?1:0)))+"="+name+";";
        }
        const auto result=code+e->literal+"}())";return e->text_value||e->array_value?result:resize(result);
    }
    if(e->op=="object_read") {const auto value="s.object_get("+emit_expression(e->args[0],0,mapped)+","+e->literal+")";return e->text_value?value:resize(value);}
    if(e->op=="reverse_index") {
        const auto& index=e->args[0];
        return resize("([&](){auto packed_index="+emit_expression(index,index->signed_value?64:0,mapped)+";if(!indexed_part(0,"+e->literal+","+(index->signed_value?"true":"false")+").width)return V::x(64);return V(uint64_t("+std::to_string(e->value)+"ull)-packed_index.a,0,64);}())");
    }
    if(e->op=="container_method"||e->op=="container_ref") {
        std::string code="([&](){";
        for(size_t i=0;i<e->args.size();++i)code+="auto container_arg"+std::to_string(i)+"="+emit_expression(e->args[i],0,mapped)+";";
        std::string body=e->literal;
        const std::string object=mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal);
        for(size_t pos=0;(pos=body.find("@object",pos))!=std::string::npos;pos+=object.size())body.replace(pos,7,object);
        return e->op=="container_ref"?code+body+"}())":resize(code+body+"}())");
    }
    if((!e->writes.empty()||e->random_state||e->io_state)&&!e->args.empty()) {
        auto copy=std::make_shared<Expr>(*e);copy->writes.clear();copy->random_state=false;copy->io_state=false;
        std::string code="([&](){";
        for(size_t i=0;i<e->args.size();++i) {
            auto local=node("saved",e->args[i]->width);local->real_width=e->args[i]->real_width;local->signed_value=e->args[i]->signed_value;local->literal="operand"+std::to_string(i);copy->args[i]=local;
        }
        if(e->op=="mux") {
            code+="auto operand0="+emit_expression(e->args[0],0,mapped)+";";
            code+="if(operand0.truth()==1)return "+emit_expression(e->args[1],w,mapped,sign)+";";
            code+="if(operand0.truth()==0)return "+emit_expression(e->args[2],w,mapped,sign)+";";
        }
        for(size_t i=(e->op=="mux"?1:0);i<e->args.size();++i) {
            int operand_context=0,operand_sign=-1;
            if(e->op=="mux"){operand_context=w;operand_sign=int(sign);}
            else if(e->args.size()==1&&e->op!="slice"&&e->op!="cast"&&e->op!="replicate") {
                bool reduce=e->op=="!"||e->op=="&"||e->op=="|"||e->op=="^";
                operand_context=reduce?e->args[i]->width:w;operand_sign=reduce?-1:int(sign);
            } else if(e->args.size()==2&&e->op!="concat"&&e->op!="indexed_slice"&&e->op!="memory") {
                bool logical=e->op=="&&"||e->op=="||";
                bool compare=e->op=="=="||e->op=="!="||e->op=="==="||e->op=="!=="||e->op=="==?"||e->op=="!=?"||e->op=="<"||e->op==">"||e->op=="<="||e->op==">=";
                bool shift=e->op=="<<"||e->op==">>"||e->op==">>>";
                operand_context=logical||(shift&&i==1)?e->args[i]->width:compare?std::max(e->args[0]->width,e->args[1]->width):w;
                operand_sign=logical||(shift&&i==1)?-1:int(compare?e->args[0]->signed_value&&e->args[1]->signed_value:sign);
            }
            code+="auto operand"+std::to_string(i)+"="+emit_expression(e->args[i],operand_context,mapped,operand_sign)+";";
            if(i==0&&e->op=="&&")code+="if(operand0.truth()==0)return V(0,0,"+sw+");";
            if(i==0&&e->op=="||")code+="if(operand0.truth()==1)return V(1,0,"+sw+");";
        }
        return code+"return "+emit_expression(copy,context,mapped,sign_context)+";}())";
    }
    if(e->op=="literal"||e->op=="saved")return resize(e->literal);
    if(e->op=="signal")return resize("s.get("+(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal))+")");
    if(e->op=="dynamic_read"||e->op=="associative_read")return resize("s."+e->op+"("+(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal))+","+emit_expression(e->args[0],e->args[0]->signed_value?64:0,mapped)+","+std::to_string(e->width)+","+e->literal+")");
    if(e->op=="dynamic_size"||e->op=="associative_size")return resize("V(s."+e->op+"("+(mapped?"sid["+std::to_string(e->signal)+"]":std::to_string(e->signal))+"),0,32)");
    if(e->op=="memory") {
        const auto code=std::string(e->text_value?"text_memory_read(s,":"memory_read(s,")+e->literal+","+emit_expression(e->args[0],e->args[0]->signed_value?64:0,mapped)+","+std::to_string(e->width)+(mapped?",sid.data()":"")+")";
        return e->text_value?code:resize(code);
    }
    if(e->op=="cast")return resize("("+emit_expression(e->args[0],0,mapped)+")");
    if(e->op=="fill1") return w>64?"V::ones("+sw+")":"V(mask("+sw+"),0,"+sw+")";
    if(e->op=="fillx")return "V::x("+sw+")";
    if(e->op=="fillz")return "V::z("+sw+")";
    if(e->op=="time")return "V(s.local_time("+e->literal+"ULL),0,64)";
    if(e->op=="slice")return "slice("+emit_expression(e->args[0],0,mapped)+","+e->literal+").size("+sw+")";
    if(e->op=="indexed_slice")return "indexed_slice("+emit_expression(e->args[0],0,mapped)+","+emit_expression(e->args[1],e->args[1]->signed_value?64:0,mapped)+","+e->literal+","+(e->args[1]->signed_value?"true":"false")+").size("+sw+")";
    if(e->op=="concat")return "concat("+emit_expression(e->args[0],0,mapped)+","+emit_expression(e->args[1],0,mapped)+").size("+sw+")";
    if(e->op=="replicate")return "replicate("+emit_expression(e->args[0],0,mapped)+","+e->literal+").size("+sw+")";
    if(e->op=="mux")return "([&](){auto mux_condition="+emit_expression(e->args[0],0,mapped)+";if(mux_condition.truth()==1)return "+emit_expression(e->args[1],w,mapped,sign)+";if(mux_condition.truth()==0)return "+emit_expression(e->args[2],w,mapped,sign)+";auto mux_left="+emit_expression(e->args[1],w,mapped,sign)+";auto mux_right="+emit_expression(e->args[2],w,mapped,sign)+";return mux(mux_condition,mux_left,mux_right,"+sw+");}())";
    if(e->args.size()==1) {
        bool reduce=e->op=="!"||e->op=="&"||e->op=="|"||e->op=="^";
        int a=reduce?e->args[0]->width:w;
        static const std::map<std::string,std::string> unary_ops={{"~","BitNot"},{"!","LogicalNot"},{"+","Plus"},{"-","Minus"},{"&","ReduceAnd"},{"|","ReduceOr"},{"^","ReduceXor"}};
        return "unary_op<Unary::"+unary_ops.at(e->op)+">("+emit_expression(e->args[0],a,mapped,reduce?-1:int(sign))+","+std::to_string(a)+").size("+sw+")";
    }
    bool logical=e->op=="&&"||e->op=="||";
    bool comparison=e->op=="=="||e->op=="!="||e->op=="==="||e->op=="!=="||e->op=="==?"||e->op=="!=?"||e->op=="<"||e->op==">"||e->op=="<="||e->op==">=";
    bool shift=e->op=="<<"||e->op==">>"||e->op==">>>";
    int a=logical?e->args[0]->width:comparison?std::max(e->args[0]->width,e->args[1]->width):w;
    int b=logical||shift?e->args[1]->width:a;
    bool operands_signed=comparison?(e->args[0]->signed_value&&e->args[1]->signed_value):sign;
    std::string left=emit_expression(e->args[0],a,mapped,logical?-1:int(operands_signed));
    std::string right=emit_expression(e->args[1],b,mapped,logical||shift?-1:int(operands_signed));
    // A read may trap (for example null_handle.field). Short circuit even
    // without writes; X on the left must still evaluate the right operand.
    if(logical)return "([&](){auto logical_left="+left+";if(logical_left.truth()=="+(e->op=="&&"?"0":"1")+")return V("+(e->op=="&&"?"0":"1")+",0,"+sw+");return binary_op<Binary::"+(e->op=="&&"?"LogicalAnd":"LogicalOr")+">(logical_left,"+right+","+sw+");}())";
    if(e->op==">>>"&&sign)return "signed_shift_right("+left+","+right+","+sw+")";
    if(e->op=="==?"||e->op=="!=?")return "wildcard_equal("+left+","+right+","+(e->op=="!=?"?"true":"false")+").size("+sw+")";
    static const std::map<std::string,std::string> binary_ops={
        {"&","BitAnd"},{"|","BitOr"},{"^","BitXor"},{"&&","LogicalAnd"},{"||","LogicalOr"},
        {"===","CaseEqual"},{"!==","CaseNotEqual"},{"==","Equal"},{"!=","NotEqual"},
        {"<","Less"},{">","Greater"},{"<=","LessEqual"},{">=","GreaterEqual"},
        {"<<","ShiftLeft"},{">>","ShiftRight"},{">>>","ShiftRight"},
        {"+","Add"},{"-","Subtract"},{"*","Multiply"},{"/","Divide"},{"%","Modulo"}};
    bool signed_op=operands_signed&&(e->op=="/"||e->op=="%"||e->op=="<"||e->op==">"||e->op=="<="||e->op==">=");
    return std::string(signed_op?"signed_binary_op<Binary::":"binary_op<Binary::")+binary_ops.at(e->op)+">("+left+","+right+","+sw+")";
}

struct SignalIR { std::string name; int width,lo; bool net; bool two_state=false,named_event=false,text_value=false; int real_width=0; };
struct Instruction { std::string code; int yes=-1,no=-1; E condition; int activation_depth=0;
    int integral_target=-1; E integral_value;
    // A complete, immediate net driver, recorded before C++ emission. Other
    // writes deliberately carry no candidate: a range alone does not prove it.
    int net_target=-1; E net_value={};
    // A case selector and its forward successors, independent of PC emission.
    // The final successor is the default (including an absent default body).
    std::string case_selection;
    std::vector<int> case_targets;
};
#include "constraint_codegen.hpp"

struct PartIR { int signal,lo,width,rhs_lo; E index={}; int base=0; bool descending=false; E word_index={}; int memory=-1; int view_lo=0,view_width=0; bool continuous=false;bool struct_string_field=false;
    E virtual_handle={};std::vector<std::pair<uint64_t,int>> virtual_targets={};
    E receiver_effect={},associative_ref={};bool associative_queue=false;int associative_queue_bound=-1;
    E object={};int object_type=-1,object_field=-1,object_width=0,object_real=0;bool object_two_state=false,object_text=false,object_associative=false,object_unsigned_key=false,object_class_key=false,object_queue=false;int object_queue_bound=-1;int field_class=-1;unsigned field_enum=0;
    bool object_const=false,object_const_initialized=false,object_initializer=false;
};
struct ProcessIR {
    std::vector<Instruction> instructions;
    std::set<int> reads,touches,partial_writes,function_reads,whole_writes,nonstatic_writes;
    std::vector<PartIR> writes;
    std::vector<E> sensitivity_reads;
    std::vector<size_t> array_values;
    struct LoopTransfers {std::vector<int> breaks,continues;};
    std::vector<LoopTransfers> loops;
    struct ReturnTransfers {int result;std::vector<int> exits;unsigned enum_id=0;VeriNode* symbol=nullptr;};
    std::vector<ReturnTransfers> returns;
    bool side_effect=false,function=false,function_forks=false,selection_checks=false,event_safe=true,io_state=false,random_state=false;
    // Selection diagnostics can run in a bounded activation; other effects
    // retain the conservative interpreter path.
    bool selection_only_effects=true;
    int repeat_counters=0,delay_values=0,always_kind=akALWAYS,timing_controls=0;
    int source_line=0,startup_wait=-1,activation_depth=0;
    bool startup_adapter=false,always_process=false,fork_child=false,property_action=false,final_process=false,task_template=false;
    // Exact three-instruction continuous driver: arm, whole-net store, return.
    int continuous_wait=-1;
};
struct LValueIR { std::vector<PartIR> parts; int width=0; };
struct BitLinkIR { int a,abit,b,bbit; };
class Lower {
    // Both parser symbol types share the same compiled signal representation.
    // Keep the independent parser's integer nodes intact, including array bounds.
    struct Variable {
        VeriNode* node;
        bool integer() const {return node->tok_type()==vtINT;}
        bool formal() const {return node->tok_type()==vtTFVAR;}
        bool result() const {return node->tok_type()==vtFUNC;}
        VeriVar* packed() const {return static_cast<VeriVar*>(node);}
        VeriInt* integral() const {return static_cast<VeriInt*>(node);}
        VeriTfVar* tf() const {return static_cast<VeriTfVar*>(node);}
        VeriFunc* fn() const {return static_cast<VeriFunc*>(node);}
        VeriVar* result_type() const {return result()?fn()->func()->resolved_type():nullptr;}
        const std::string& name() const {return result()?fn()->func()->func_name():formal()?tf()->name():integer()?integral()->name():packed()->name();}
        int real_width() const {return veri_real_width(node);}
        int dlen() const {return result()?fn()->dlen():formal()?tf()->dlen():integer()?32:packed()->dlen();}
        int dend() const {return result()?fn()->dend():formal()?tf()->dend():integer()?0:packed()->dend();}
        int dstart() const {return result()?fn()->dstart():formal()?tf()->dstart():integer()?31:packed()->dstart();}
        bool dynamic() const {
            if(formal())return tf()->dynamic_array();
            if(result())return result_type()&&result_type()->dynamic_array();
            if(!range_depth())return false;
            return integer()?integral()->dynamic_array():packed()->dynamic_array();
        }
        int container_kind() const {return result()?(result_type()?result_type()->container_kind():vrSINGLE):formal()?tf()->container_kind():integer()?integral()->container_kind():packed()->container_kind();}
        int container_bound(unsigned axis=0) const {return result()?(result_type()?result_type()->container_bound(axis):-1):formal()?tf()->container_bound(axis):integer()?integral()->container_bound(axis):packed()->container_bound(axis);}
        int range_depth() const {return result()?(result_type()?result_type()->range_depth():0):formal()?tf()->range_depth():integer()?integral()->range_depth():packed()->range_depth();}
        short is_signed() const {return result()?fn()->func()->is_signed():formal()?tf()->is_signed():integer()?IS_TRUE:packed()->is_signed();}
        bool two_state() const {return !integer()&&veri_two_state(result()?fn()->func()->result_type():formal()?tf()->net_type():packed()->net_type());}
        short net_type() const {return integer()||formal()||result()?vvREG:packed()->net_type();}
        void get_range(unsigned depth,int& first,int& last,int& count) const {
            if(result())result_type()->get_range(depth,first,last,count);
            else if(formal())tf()->get_range(depth,first,last,count);
            else if(integer())integral()->get_range(depth,first,last,count);
            else packed()->get_range(depth,first,last,count);
        }
        const Variable* operator->() const {return this;}
    };
    static bool variable(VeriNode* n) {return n&&(n->tok_type()==vtVAR||n->tok_type()==vtINT||n->tok_type()==vtTFVAR||n->tok_type()==vtFUNC);}
    std::map<VeriNode*,E> queue_slice_last_indices;
    size_t queue_slice_sequence=0;
    struct DeclarationInit {
        int signal;
        E value;
        std::shared_ptr<ProcessIR> process; // Optional executable container initialization.
    };
    struct Scope {
        VeriMod* mod; std::string path;
        std::map<std::string,int> ids;
        std::map<std::string,VeriNode*> defaults;
        std::vector<std::string> wave_path;
        std::set<std::string> packed;
        TimeScale time;
        Scope* parent=nullptr; // Lexical parent within the same module instance.
        std::map<std::string,VeriNode*> symbols;
        std::vector<VeriNode*> items;
        bool generated=false,procedural=false,subroutine=false,automatic_storage=false;
        bool static_class_method=false;
        VeriSeqBlock* class_definition=nullptr;
        VeriSeqBlock* constructor_class=nullptr;
        E self;
        Scope* static_domain=nullptr;
        std::vector<std::string> static_wave_path;
        std::set<int> activation_variables;
        std::vector<DeclarationInit> activation_initializers;
        unsigned unnamed_blocks=0;
        std::set<std::string> child_names;
        std::map<std::string,int> memories;
    };
    struct Callable {
        Scope* scope=nullptr;VeriNode* body=nullptr;VeriNode* result_symbol=nullptr;VeriNode* declaration=nullptr;
        std::vector<VeriNode*> formals;
        std::vector<int> directions;
        int result=-1;bool signed_result=false,compiling=false,has_references=false,recursive=false;
        int this_signal=-1;
        ProcessIR process;
        std::set<int> locals;
        unsigned recursive_id=0;
        std::set<Callable*> recursive_captures;
        bool rebuilding_static=false;
        int task_process=-1,task_group=-1;
    };
    std::map<std::tuple<Scope*,std::string,VeriNode*,int,Scope*>,std::unique_ptr<Callable>> callables;
    // An inline template containing a back edge captures the enclosing
    // function's recursion parameter. Retain old templates for stable identity,
    // and rebuild them when that enclosing activation is no longer compiling.
    std::vector<std::unique_ptr<Callable>> retired_callables;
    std::vector<Callable*> compiling_functions;
    std::map<VeriNode*,VeriNode*> implicit_function_calls;
    unsigned recursive_function_next=0;
    #include "rtl_dpi.inc"
    std::map<VeriNode*,E> argument_values;
    E argument_receiver;
    unsigned argument_sequence=0;
    std::map<VeriNode*,E> reduction_items;
    std::map<VeriNode*,std::string> random_arrays;
    unsigned reduction_item_next=0;
    std::set<std::pair<Scope*,std::string>> active_subroutines;
    std::set<int> automatic_signals,reference_signals,readonly_signals,dynamic_signals,string_element_signals;
    std::set<int> const_property_signals;
    std::set<VeriNode*> const_properties;
    std::set<VeriSeqBlock*> active_randomization;
    unsigned randomize_sequence=0;
    unsigned constraint_loop_sequence=0;
    std::set<int> associative_signals,string_associative_signals,unsigned_associative_signals,class_associative_signals;
    bool object_associative_storage=false;
    bool object_queue_storage=false;
    std::map<int,int> queue_bounds;
    // Automatic call templates share explicit static declarations by lexical
    // identity within a module/generate instance, rather than by call site.
    std::map<std::tuple<Scope*,int,int,std::string>,int> static_variables;
    std::map<int,std::vector<std::string>> static_wave_paths;
    std::set<int> static_initializers;
    std::map<std::pair<Scope*,VeriNode*>,Scope*> block_scopes;
    std::set<int> foreach_indices;
    std::map<std::tuple<Scope*,std::string,int>,int> foreach_index_slots;
    std::set<int> subroutine_signals,function_signals,event_function_storage;
    struct Binding {
        Scope *parent,*child; VeriVar* port; VeriNode* actual; bool collapsed=false,omitted=false,bit_connected=false;
        std::vector<PartIR> parts;
        std::vector<std::pair<int,int>> array_elements;
        int instance_count=1,instance_ordinal=0;
        bool instance_array=false;
    };
    VeriMod* top;
    const GateDesign* gate_design;
    SdfTaskHandler sdf_task_handler;
    bool needs_sdf_log=false;
    std::vector<SdfTask> sdf_tasks;
    std::map<std::pair<Scope*,VeriNode*>,size_t> prepared_sdf_tasks;
    static Scope* sdf_module_scope(Scope* sc) {while(sc->parent)sc=sc->parent;return sc;}
    static bool omitted_sdf_argument(VeriNode* n) {return !n||n->detail_type()==veEXP_DUMMY_PORT;}
    std::string sdf_text(VeriNode* n) {
        if(omitted_sdf_argument(n))return {};
        if(n->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(n)->pri_type()==veSTR)
            return decode_string(static_cast<VeriPrimaryExp*>(n)->str(),n);
        if(n->tok_type()==vtEXP&&veri_elaboration_constant(n)) {
            auto* value=static_cast<VeriExp*>(n)->calc_value();
            if(value&&value->string_type()) {
                auto text=value->string_value();
                if(text.find('\0')!=std::string::npos)fail(n,"embedded NUL in $sdf_annotate string argument");
                return text;
            }
        }
        fail(n,"$sdf_annotate requires elaboration-constant string arguments");
    }
    void prepare_sdf_task(VeriSysCallerStmt* call) {
        std::vector<VeriNode*> args;
        if(call->arg()&&call->arg()->detail_type()==veEXP_MULTI)
            for(auto* a:static_cast<VeriMultiExp*>(call->arg())->exp())args.push_back(a);
        else if(call->arg())args.push_back(call->arg());
        if(args.empty()||args.size()>7)fail(call,"$sdf_annotate requires filename, optional instance and up to five annotation options (received "+std::to_string(args.size())+")");
        if(!gate_design||!sdf_task_handler)fail(call,"$sdf_annotate requires --gate-netlist, --gate-top, --gate-models and --liberty");
        auto* target=sdf_module_scope(scope);
        if(args.size()>1&&!omitted_sdf_argument(args[1])) {
            auto* argument=args[1];
            auto* symbol=argument->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(argument)->var():
                argument->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(argument)->hierarchical_symbol():nullptr;
            if(!symbol||symbol->tok_type()!=vtMOD_INST)fail(argument,"$sdf_annotate target must be a module instance");
            auto* inst=static_cast<VeriModInstance*>(static_cast<VeriModInst*>(symbol)->instance());
            target=nullptr;
            for(const auto& sc:scopes)if(!sc->generated&&sc->mod==inst->hive()) {
                if(target)fail(argument,"$sdf_annotate target is ambiguous");
                target=sc.get();
            }
            if(!target)fail(argument,"$sdf_annotate target is not elaborated");
        }
        if(target->mod->name()!=GateDesign::rtl_identifier(gate_design->top)||target->mod->line()>int(prefix_lines))
            fail(call,"$sdf_annotate currently requires the explicit structural gate root as its target");
        size_t gate_scopes_count=0;
        for(const auto& sc:scopes)if(!sc->generated&&sc->mod->name()==GateDesign::rtl_identifier(gate_design->top))++gate_scopes_count;
        if(gate_scopes_count!=1)fail(call,"$sdf_annotate currently requires exactly one structural gate instance; per-instance timing tables are not implemented");
        SdfTask task;task.line=call->line();task.file=sdf_text(args[0]);task.target=target->path;
        if(task.file.empty())fail(call,"$sdf_annotate filename must not be empty");
        if(args.size()>2)task.configuration=sdf_text(args[2]);
        if(args.size()>3)task.logfile=sdf_text(args[3]);
        if(args.size()>4) {
            auto corner=sdf_text(args[4]);
            if(corner=="MINIMUM")task.corner=0;
            else if(corner=="TYPICAL")task.corner=1;
            else if(corner=="MAXIMUM")task.corner=2;
            else if(!corner.empty()&&corner!="TOOL_CONTROL")fail(call,"unsupported $sdf_annotate mtm_spec: "+corner);
        }
        for(size_t i=5;i<args.size();++i)if(!sdf_text(args[i]).empty())
            fail(call,"$sdf_annotate scale_factors/scale_type are not implemented; omit them");
        prepared_sdf_tasks.emplace(std::make_pair(sdf_module_scope(scope),call),sdf_tasks.size());
        sdf_tasks.push_back(std::move(task));
    }
    // Follow only the unconditional, non-suspending prefix of an initial.
    // Any other encountered call is rejected during ordinary statement lowering.
    bool scan_sdf_initial(VeriNode* n) {
        if(!n)return true;
        if(n->detail_type()==vsSTMT_STMT_LIST) {
            for(auto* item:static_cast<VeriStmtList*>(n)->stmt_list())if(!scan_sdf_initial(item))return false;
            return true;
        }
        if(n->detail_type()==vsSTMT_SEQ_BLOCK) {
            auto* block=static_cast<VeriSeqBlock*>(n);
            return !block->parallel_kind()&&scan_sdf_initial(block->stmt_list());
        }
        if(n->detail_type()==vsSTMT_SYS_CALL) {
            auto* call=static_cast<VeriSysCallerStmt*>(n);
            if(call->caller()=="$sdf_annotate") {prepare_sdf_task(call);return true;}
            return call->caller()=="$display"||call->caller()=="$write";
        }
        if(n->detail_type()==vsSTMT_BLOCKING)return !static_cast<VeriBlockStmt*>(n)->event();
        return n->detail_type()==vsSTMT_DUMMY||n->detail_type()==vsSTMT_NONBLOCKING||n->detail_type()==vsSTMT_UPDATE||n->detail_type()==vsSTMT_COMPOUND;
    }
    void prepare_sdf_tasks() {
        for(const auto& sc:scopes)if(!sc->procedural&&!sc->class_definition) {
            scope=sc.get();
            for(auto* item:scope->items)if(item->detail_type()==vsSTMT_INIT&&!static_cast<VeriInitStmt*>(item)->final_process())
                scan_sdf_initial(static_cast<VeriInitStmt*>(item)->stmt());
        }
        if(sdf_task_handler)sdf_task_handler(sdf_tasks);
    }
    bool needs_text=false,needs_struct_strings=false,needs_object_format=false,needs_object_array_refs=false,needs_object_scalar_refs=false,needs_queue_ref_limits=false,needs_event_aliases=false,needs_string_replication=false;
    std::set<int> event_value_signals;
    std::set<int> struct_string_signals;
    bool needs_parts_nba=false;
    bool compact_memories=false,shared_functions=false;
    bool wave_enabled=false,needs_wide=false,needs_delayed_nba=false,needs_continuous_delay=false,needs_dump_tasks=false,needs_replication=false,needs_dynamic_delay=false,needs_indexed_select=false,needs_memory_io=false;
    bool needs_force=false;int force_site_count=0;
    bool needs_selection_checks=false,needs_variable_continuous=false,needs_named_events=false,needs_wait_order=false,needs_expression_events=false,needs_explicit_automatic=false;
    TimingConfig timing;
    size_t prefix_lines=0;
    uint64_t precision_fs=1;
    std::vector<std::string> gate_calls,gate_scopes;
    std::vector<std::set<int>> gate_touches;
    size_t parallel_count=0;
    bool serial_parallel_stats=false,diagnostics=true;
    bool needs_global_finish=false,needs_termination_unwind=false,needs_stop=false,needs_associative_refs=false,needs_random=false,needs_constraints=false;
    PartitionGraph::Plan parallel_plan;
    std::vector<size_t> signal_owner,process_owner,gate_owner;
    Scope* scope=nullptr;
    std::vector<std::unique_ptr<Scope>> scopes;
    std::map<VeriMod*,Scope*> package_scopes;
    std::vector<Binding> bindings;
    std::vector<SignalIR> signals;
    struct ObjectField {VeriNode* symbol;VeriNode* initializer;};
    struct ClassIR {int id;Scope* scope;std::vector<ObjectField> fields;};
    std::map<VeriSeqBlock*,ClassIR> classes;
    mutable std::map<int,VeriSeqBlock*> class_types;
    std::set<VeriNode*> initialized_class_statics;
    std::map<VeriNode*,std::pair<VeriSeqBlock*,int>> object_fields;
    std::map<VeriNode*,Scope*> class_statics;
    std::map<int,int> object_signals;
    int objects_signal=-1;
    unsigned allocation_sequence=0;
    std::set<VeriSeqBlock*> active_allocations;
    struct MemoryDimension { int base,count,stride; bool descending=false; };
    struct MemoryIR { int base; std::vector<int> words; std::vector<MemoryDimension> dimensions; bool dynamic=false; int fixed_count=0; };
    std::vector<MemoryIR> memories;
    std::vector<std::vector<int>> array_copy_words;
    std::string memory_table(int id) const {
        const auto& m=memories.at(size_t(id));
        return "memory_words"+std::to_string(id)+","+std::to_string(m.words.size())+","+std::to_string(m.base);
    }
    void emit_memories(std::ostream& out) const {
        for(size_t i=0;i<memories.size();++i) {
            if(memories[i].fixed_count)continue;
            out<<"static constexpr int memory_words"<<i<<"[]={";
            for(int id:memories[i].words)out<<id<<",";
            out<<"};\n";
        }
        for(size_t i=0;i<array_copy_words.size();++i) {
            out<<"static constexpr int array_copy_words"<<i<<"[]={";
            for(int id:array_copy_words[i])out<<id<<",";
            out<<"};\n";
        }
    }
    std::vector<BitLinkIR> bit_links;
    std::vector<ProcessIR> processes;
    size_t static_net_drive_count=0,typed_net_store_count=0;
    std::vector<int> typed_net_store_signals;
    std::vector<int> static_net_drive_signals;
    struct CombRegionIR {std::vector<int> members;std::set<int> inputs;std::map<int,uint64_t> subscribers;};
    std::vector<CombRegionIR> comb_regions;
    std::vector<std::pair<int,int>> comb_members;
    std::vector<bool> comb_leaves,activation_members;
    struct ClockingPortIR {VeriClocking* syntax;E input;std::vector<PartIR> target;uint64_t skew;int buffer=-1;bool step=false;};
    struct ClockingIR {VeriClocking* syntax;Scope* owner;int clock,edges;std::vector<ClockingPortIR> ports;};
    std::vector<ClockingIR> clockings;
    std::map<VeriClocking*,int> clocking_ids;
    std::map<Scope*,int> default_clockings;
    ClockingPortIR& clocking_port(VeriMemberExp* member) {
        auto found=clocking_ids.find(member->clocking_owner());
        if(found==clocking_ids.end())fail(member,"clocking reference is outside the elaborated design");
        for(auto& port:clockings[size_t(found->second)].ports)if(port.syntax->name==member->member())return port;
        fail(member,"unknown clocking member: "+member->member());
    }
    void prepare_clockings() {
        auto* previous=scope;
        for(const auto& owner:scopes)for(auto* item:owner->items)if(item->detail_type()==vsDECL_CLOCKING) {
            auto* syntax=static_cast<VeriClocking*>(item);
            if(owner->mod->is_package()||owner->class_definition)fail(item,"clocking requires a module or interface scope");
            clocking_ids.emplace(syntax,int(clockings.size()));clockings.push_back({syntax,owner.get(),-1,0,{}});
        }
        for(auto& clock:clockings) {
            scope=clock.owner;auto* syntax=clock.syntax;
            auto* events=static_cast<VeriEventStmt*>(syntax->children[0]);
            if(events->is_all()==IS_TRUE||events->event_list().size()!=1)fail(syntax,"clocking requires one explicit edge event");
            auto* event=events->event_list().front();
            if(event->detail_type()!=veEXP_EVENT)fail(event,"clocking requires posedge or negedge");
            auto* edge=static_cast<VeriEventExp*>(event);
            if(edge->condition()||(edge->etype()!=vtUPOSE&&edge->etype()!=vtUNEGE))fail(event,"clocking iff and compound edge events are not supported yet");
            auto source=expr(edge->exp_child());
            if(source->op!="signal"||source->width!=1||source->real_width||source->text_value)fail(event,"clocking event requires one scalar integral signal");
            clock.clock=source->signal;clock.edges=edge->etype()==vtUPOSE?1:2;
            VeriClocking* in_default=nullptr;VeriClocking* out_default=nullptr;
            auto ports=syntax->ports();
            for(auto* port:ports)if(port->name.empty()) {
                auto*& target=port->direction==vpIN?in_default:out_default;
                if(target)fail(port,"duplicate default clocking skew");target=static_cast<VeriClocking*>(port->children[1]);
            }
            std::set<std::string> names;
            for(auto* port:ports)if(!port->name.empty()) {
                if(!names.insert(port->name).second)fail(port,"duplicate clocking signal: "+port->name);
                auto* skew=port->children[1]?static_cast<VeriClocking*>(port->children[1]):port->direction==vpIN?in_default:out_default;
                const bool step=skew?skew->step:port->direction==vpIN;
                uint64_t ticks=0;
                if(skew&&!step)ticks=constant_delay_value(static_cast<VeriDelayExp*>(skew->children[0])->delay1());
                if(port->direction==vpIN) {
                    if(!step&&ticks)fail(port,"positive clocking input skew is not supported yet; use #1step or #0");
                    auto value=expr(port->children[0]);property_expression(port,value);
                    if(value->real_width||value->object_type>=0)fail(port,"clocking input requires a packed integral expression");
                    const int buffer=int(signals.size());signals.push_back({scope->path+"."+syntax->name+"."+port->name,value->width,0,false});
                    clock.ports.push_back({port,value,{},0,buffer,step});
                } else {
                    if(step)fail(port,"clocking output does not permit #1step");
                    auto target=lvalue(port->children[0]);
                    for(const auto& part:target.parts)if(part.index||part.word_index||part.object||part.receiver_effect||signals[part.signal].net||signals[part.signal].text_value||signals[part.signal].real_width||object_signals.count(part.signal))
                        fail(port,"clocking output currently requires static packed variable targets");
                    clock.ports.push_back({port,nullptr,std::move(target.parts),ticks});
                }
            }
        }
        for(const auto& owner:scopes)for(auto* item:owner->items) {
            int id=-1;
            if(item->detail_type()==vsDECL_CLOCKING&&static_cast<VeriClocking*>(item)->default_clock)id=clocking_ids.at(static_cast<VeriClocking*>(item));
            if(item->detail_type()==vsDECL_DEFAULT_CLOCKING) {
                auto* reference=static_cast<VeriClocking*>(item);
                auto* symbol=reference->scope()->value_within_module(reference->name);
                if(!symbol||symbol->detail_type()!=vsDECL_CLOCKING)fail(item,"unknown default clocking: "+reference->name);
                auto found=clocking_ids.find(static_cast<VeriClocking*>(symbol));
                if(found==clocking_ids.end())fail(item,"default clocking is outside the elaborated design");id=found->second;
            }
            if(id>=0&&!default_clockings.emplace(owner.get(),id).second)fail(item,"duplicate default clocking");
        }
        scope=previous;
    }
    void emit_clockings(std::ostream& out) {
        for(size_t id=0;id<clockings.size();++id) {
            const auto& clock=clockings[id];out<<"s.add_clocking("<<clock.clock<<","<<clock.edges<<");\n";
            for(const auto& port:clock.ports)if(port.input) {
                out<<"s.add_clocking_input("<<id<<","<<port.buffer<<","<<property_value(port.input,port.step,false)<<",{";
                if(port.step)for(int signal:port.input->reads)out<<signal<<",";
                out<<"});\n";
            }
        }
    }
    void clocking_wait(ProcessIR& p,int process,int clock,const std::string& count) {
        if(p.function||p.always_kind!=akALWAYS)fail(nullptr,"clocking waits require an ordinary task or process");
        ++p.timing_controls;p.touches.insert(clockings[size_t(clock)].clock);
        const int next=int(p.instructions.size())+1;
        add(p,"pc="+std::to_string(next)+";s.clocking_wait("+std::to_string(clock)+","+runtime_pid(process)+","+count+");return;");
    }
    bool clocking_assignment(ProcessIR& p,VeriNode* lhs,VeriNode* rhs,VeriNode* control,bool nba) {
        if(lhs->detail_type()!=veEXP_MEMBER||!static_cast<VeriMemberExp*>(lhs)->clocking_owner())return false;
        auto* member=static_cast<VeriMemberExp*>(lhs);auto& port=clocking_port(member);
        if(!nba||control)fail(lhs,"clocking output requires a nonblocking drive without intra-assignment control");
        if(port.input)fail(lhs,"cannot drive an input clocking signal");
        auto value=expr(rhs);if(value->text_value||value->real_width||value->object_type>=0)fail(rhs,"clocking output requires an integral value");
        read(p,value);int width=0;std::string parts="{";
        for(auto part:port.target) {
            writable(part.signal,lhs);p.writes.push_back(part);p.touches.insert(part.signal);width+=part.width;
            parts+="{"+std::to_string(part.signal)+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+",-1},";
        }
        const int clock=clocking_ids.at(member->clocking_owner());
        add(p,"s.clocking_drive("+std::to_string(clock)+","+parts+"},"+emit(value,width)+","+std::to_string(port.skew)+"ULL);");return true;
    }
    struct PropertySampleIR {int kind,depth;E value,gate;};
    struct PropertyStageIR {int delay;E value;};
    struct PropertyIR {int process,clock,edges,delay,kind;E antecedent,consequent,disable;std::vector<PropertySampleIR> samples;std::vector<PropertyStageIR> stages;size_t antecedent_stages=0;};
    std::vector<PropertyIR> properties;
    std::vector<PropertySampleIR> lowering_samples;
    int sampling_property=-1,sampling_context=0;
    std::map<std::string,VeriNode*> property_definitions;
    VeriCondStmt* property_body(VeriNode* node) {
        if(node->detail_type()==vsSTMT_PROC_TIME_CONTROL)node=static_cast<VeriProcTimeContStmt*>(node)->stmt();
        return node->detail_type()==vsSTMT_COND?static_cast<VeriCondStmt*>(node):nullptr;
    }
    std::map<VeriCondStmt*,Scope*> sequence_owners;
    VeriCondStmt* sequence_reference(VeriNode* expression) {
        if(expression->detail_type()==veEXP_CALLER) {
            auto* call=static_cast<VeriCallerExp*>(expression);
            if(call->hive())return nullptr;
            expression=call->caller();
        }
        if(expression->detail_type()!=veEXP_PRI)return nullptr;
        auto* primary=static_cast<VeriPrimaryExp*>(expression);
        return primary->pri_type()==veVAR?veri_sequence_definition(primary->var()):nullptr;
    }
    void prepare_sequences() {
        for(const auto& owner:scopes)for(auto* item:owner->items)
            if(auto* definition=veri_sequence_definition(item)) {
                if(owner->mod->is_package())fail(definition,"package sequences are not supported yet");
                sequence_owners.emplace(definition,owner.get());
            }
        // Validate the complete declaration graph, including unused sequences.
        // References are symbol edges, never owned AST children.
        std::map<VeriCondStmt*,int> state,height;int visiting=0;
        std::function<int(VeriCondStmt*)> visit;
        visit=[&](VeriCondStmt* definition) {
            if(state[definition]==1)fail(definition,"recursive sequence reference: "+definition->property_name());
            if(state[definition]==2)return height[definition];
            if(!sequence_owners.count(definition))fail(definition,"sequence is outside the elaborated lexical scopes");
            if(++visiting>128)fail(definition,"sequence reference nesting exceeds 128 declarations");
            state[definition]=1;int depth=1;
            std::vector<VeriNode*> pending{definition->if_stmt()};
            while(!pending.empty()) {
                auto* term=pending.back();pending.pop_back();
                if(term->detail_type()!=vsSTMT_COND)continue;
                auto* node=static_cast<VeriCondStmt*>(term);
                pending.push_back(node->if_stmt());
                if(node->property_group())pending.push_back(node->else_stmt());
                else if(node->property_term())if(auto* reference=sequence_reference(node->if_exp()))
                    depth=std::max(depth,1+visit(reference));
            }
            if(depth>128)fail(definition,"sequence reference nesting exceeds 128 declarations");
            state[definition]=2;--visiting;return height[definition]=depth;
        };
        for(const auto& definition:sequence_owners)visit(definition.first);
    }
    void property_expression(VeriNode* source,const E& value) {
        if(value->text_value||!value->writes.empty()||value->random_state||value->io_state)
            fail(source,"concurrent property requires a pure integral expression");
        if(value->op=="call"||value->op=="memory"||value->op=="dynamic_read"||value->op=="dynamic_size"||value->op=="associative_read"||value->op=="associative_size"||value->op=="container_method"||value->op=="associative_reduce"||value->op=="associative_reduce_with"||value->op=="event_triggered"||value->op=="reference"||value->op=="array_argument")
            fail(source,"unsupported concurrent property expression: "+value->op);
        for(int id:value->reads)if(automatic_signals.count(id)||signals[id].named_event||signals[id].text_value)
            fail(source,"concurrent property requires static integral signals");
        for(const auto& arg:value->args)property_expression(source,arg);
    }
    std::string property_value(const E& value,bool sampled,bool boolean=true) {
        auto text=emit(value);
        if(sampled) {size_t at=0;while((at=text.find("s.get(",at))!=std::string::npos){text.replace(at,6,"s.sampled_get(");at+=14;}}
        return "[&](Sim& s){return "+(boolean?"("+text+").truth()==1":text)+";}";
    }
    void emit_properties(std::ostream& out,size_t part=SIZE_MAX) {
        for(size_t i=0;i<properties.size();++i) {
            const auto& site=properties[i];if(part!=SIZE_MAX&&process_owner[site.process]!=part)continue;
            out<<(parallel_count?"qid["+std::to_string(i)+"]=":"")<<"s.add_property("<<sid(site.clock)<<","<<site.edges<<","<<pid(site.process)<<","<<site.delay<<","<<site.kind<<","<<property_value(site.antecedent,true)<<","<<property_value(site.consequent,true)<<","<<property_value(site.disable,false)<<",{";
            auto sampled=site.antecedent->reads;sampled.insert(site.consequent->reads.begin(),site.consequent->reads.end());
            for(const auto& stage:site.stages)sampled.insert(stage.value->reads.begin(),stage.value->reads.end());
            for(const auto& sample:site.samples) {
                sampled.insert(sample.value->reads.begin(),sample.value->reads.end());
                sampled.insert(sample.gate->reads.begin(),sample.gate->reads.end());
            }
            for(int id:sampled)out<<sid(id)<<",";
            out<<"},{";for(int id:site.disable->reads)out<<sid(id)<<",";out<<"});\n";
            for(const auto& stage:site.stages)
                out<<"s.add_property_stage("<<(parallel_count?"qid["+std::to_string(i)+"]":std::to_string(i))<<","<<stage.delay<<","<<property_value(stage.value,true)<<");\n";
            if(site.antecedent_stages)
                out<<"s.set_property_antecedent_stages("<<(parallel_count?"qid["+std::to_string(i)+"]":std::to_string(i))<<","<<site.antecedent_stages<<");\n";
            for(const auto& sample:site.samples)
                out<<"s.add_property_sample("<<(parallel_count?"qid["+std::to_string(i)+"]":std::to_string(i))<<","<<sample.kind<<","<<sample.depth<<","<<property_value(sample.value,true,false)<<","<<property_value(sample.gate,true)<<");\n";
        }
    }
    // Infer the sampling event from an enclosing edge-controlled process.
    // Other event controls remain legal, but cannot supply an implicit clock.
    std::pair<int,int> procedural_sample_clock(VeriNode* body) {
        if(body->detail_type()!=vsSTMT_PROC_TIME_CONTROL)return {-1,0};
        auto* control=static_cast<VeriProcTimeContStmt*>(body)->control();
        if(control->detail_type()!=vsSTMT_EVENT)return {-1,0};
        auto* events=static_cast<VeriEventStmt*>(control);
        if(events->is_all()==IS_TRUE||events->event_list().size()!=1)return {-1,0};
        auto* event=events->event_list().front();if(event->detail_type()!=veEXP_EVENT)return {-1,0};
        auto* edge=static_cast<VeriEventExp*>(event);
        if(edge->condition()||(edge->etype()!=vtUPOSE&&edge->etype()!=vtUNEGE))return {-1,0};
        auto value=expr(edge->exp_child());
        if(value->op!="signal"||value->text_value||signals[value->signal].named_event)return {-1,0};
        return {value->signal,edge->etype()==vtUPOSE?1:2};
    }
    bool lower_property(VeriNode* body) {
        auto* use=property_body(body);if(!use||use->assertion_kind()<4)return false;
        if(use->assertion_kind()==7||use->assertion_kind()==8)return true;
        auto* spec=use;auto* definition=body;
        if(!use->property_name().empty()) {
            auto found=property_definitions.find(use->property_name());
            if(found==property_definitions.end())fail(use,"unknown local property: "+use->property_name());
            definition=found->second;spec=property_body(definition);
        }
        if(definition->detail_type()!=vsSTMT_PROC_TIME_CONTROL||spec->property_delay()<0)
            fail(use,"property requires an explicit single-signal edge clock");
        auto* clock=static_cast<VeriProcTimeContStmt*>(definition)->control();
        if(clock->detail_type()!=vsSTMT_EVENT)fail(clock,"unsupported property clock");
        auto* events=static_cast<VeriEventStmt*>(clock);
        if(events->is_all()==IS_TRUE||events->event_list().size()!=1)fail(clock,"property requires a single edge clock");
        auto* event=events->event_list().front();
        if(event->detail_type()!=veEXP_EVENT)fail(event,"property requires an explicit posedge or negedge");
        auto* edge=static_cast<VeriEventExp*>(event);
        if(edge->condition()||(edge->etype()!=vtUPOSE&&edge->etype()!=vtUNEGE))fail(event,"unsupported property clock qualifier");
        auto clock_value=expr(edge->exp_child());
        if(clock_value->op!="signal"||clock_value->text_value||signals[clock_value->signal].named_event)
            fail(event,"property clock must be a static integral signal");
        auto* antecedent=static_cast<VeriCondStmt*>(spec->if_stmt());
        sampling_property=int(properties.size());sampling_context=1;lowering_samples.clear();
        auto a=expr(antecedent->if_exp());property_expression(antecedent,a);
        bool temporal=false;
        auto repeat_count=[&](VeriCondStmt* node) {
            const char* diagnostic="sequence repetition must be a known integral constant in 1..256 (empty/range repetition is not supported yet)";
            if(!veri_elaboration_constant(node->if_exp()))fail(node,diagnostic);
            auto constant=veri_constant_value(static_cast<VeriExp*>(node->if_exp()),0);
            if(!constant)fail(node,diagnostic);
            auto count=number(constant.get());
            if(count->op!="literal"||count->text_value||count->unknown||count->negative||count->host_overflow||count->value<1||count->value>256)
                fail(node,diagnostic);
            return int(count->value);
        };
        // Flatten each lexical expression once, preserving sampled-function
        // identity when a finite subsequence is repeated. Only immutable IR
        // expressions are shared; parser nodes retain their original ownership.
        std::function<std::vector<PropertyStageIR>(VeriNode*,int)> sequence;
        sequence=[&](VeriNode* term,int depth) {
            if(depth>128)fail(term,"sequence nesting exceeds 128 groups or named references");
            std::vector<PropertyStageIR> result;
            int pending=0,span=0,repetitions=1;
            auto append=[&](VeriCondStmt* source,int delay,const E& value) {
                if(result.size()==256)fail(source,"sequence exceeds 256 stages");
                if(span+delay>65536)fail(source,"sequence total delay exceeds 65536 cycles");
                span+=delay;result.push_back({delay,value});
            };
            while(term->detail_type()==vsSTMT_COND) {
                auto* node=static_cast<VeriCondStmt*>(term);
                auto* reference=node->property_term()?sequence_reference(node->if_exp()):nullptr;
                if(node->property_group()||reference) {
                    temporal=true;
                    int count=reference?repetitions:repeat_count(node);
                    auto* owner=scope;
                    if(reference)scope=sequence_owners.at(reference);
                    auto body=sequence(reference?reference->if_stmt():node->if_stmt(),depth+1);
                    scope=owner;
                    if(body.empty())fail(node,"property requires a sequence expression");
                    for(int repeat=0;repeat<count;++repeat) {
                        for(size_t stage=0;stage<body.size();++stage) {
                            int delay=body[stage].delay;
                            if(stage==0)delay+=repeat?1:pending;
                            append(node,delay,body[stage].value);
                        }
                    }
                    pending=0;repetitions=1;
                    term=reference?node->if_stmt():node->else_stmt();continue;
                } else if(node->property_repetition()) {
                    temporal=true;repetitions=repeat_count(node);
                } else if(node->property_cycle_delay()) {
                    temporal=true;
                    if(!veri_elaboration_constant(node->if_exp()))fail(node,"sequence delay must be a known integral constant in 0..65536");
                    auto constant=veri_constant_value(static_cast<VeriExp*>(node->if_exp()),0);
                    if(!constant)fail(node,"sequence delay must be a known integral constant in 0..65536");
                    auto count=number(constant.get());
                    if(count->op!="literal"||count->text_value||count->unknown||count->negative||count->host_overflow||count->value>65536)
                        fail(node,"sequence delay must be a known integral constant in 0..65536");
                    pending+=int(count->value);
                    if(span+pending>65536)fail(node,"sequence total delay exceeds 65536 cycles");
                } else {
                    auto value=expr(node->if_exp());property_expression(node,value);
                    append(node,pending,value);
                    for(int repeat=1;repeat<repetitions;++repeat)append(node,1,value);
                    repetitions=1;pending=0;
                }
                term=node->if_stmt();
            }
            return result;
        };
        auto prefix=sequence(antecedent->else_stmt(),0);
        if(prefix.empty())fail(spec,"property requires an antecedent sequence");
        // Preserve the existing scalar trigger path for a one-stage antecedent,
        // including a named sequence whose entire match is this sampled value.
        if(prefix.size()==1&&prefix.front().delay==0) {
            a=prefix.front().value;prefix.clear();
        }
        temporal=false;
        auto stages=sequence(antecedent->if_stmt(),0);
        if(!stages.empty()) {
            stages.front().delay+=spec->property_delay();
            int span=0;for(const auto& stage:stages)span+=stage.delay;
            if(span>65536)fail(spec,"sequence total delay exceeds 65536 cycles");
        }
        if(stages.empty())fail(spec,"property requires a sequence expression");
        auto c=stages.front().value;
        const size_t prefix_size=prefix.size();
        if(prefix_size) {
            if(prefix_size+stages.size()>256)fail(spec,"implication exceeds 256 combined stages");
            int span=0;for(const auto& stage:prefix)span+=stage.delay;
            for(const auto& stage:stages)span+=stage.delay;
            if(span>65536)fail(spec,"implication total delay exceeds 65536 cycles");
            prefix.insert(prefix.end(),stages.begin(),stages.end());
            stages=std::move(prefix);temporal=true;
        }
        sampling_context=2;auto d=expr(spec->if_exp());sampling_context=3;
        property_expression(spec,d);
        ProcessIR p;int id=int(processes.size()),site=int(properties.size());processes.emplace_back();
        p.source_line=use->line();p.property_action=true;
        read(p,clock_value);read(p,a);read(p,c);read(p,d);
        for(const auto& stage:stages)read(p,stage.value);
        properties.push_back({id,clock_value->signal,edge->etype()==vtUPOSE?1:2,spec->property_delay(),use->assertion_kind()-3,a,c,d,{},temporal?std::move(stages):std::vector<PropertyStageIR>{},prefix_size});
        auto* actions=static_cast<VeriCondStmt*>(use->else_stmt());
        int branch=add(p,"");p.instructions[branch].condition=node("saved",1);p.instructions[branch].condition->literal="V(s.property_result("+(parallel_count?"qid["+std::to_string(site)+"]":std::to_string(site))+"))";
        p.instructions[branch].yes=branch+1;
        statement(p,actions->if_stmt(),id);int end=add(p,"");p.instructions[branch].no=end+1;
        if(actions->else_stmt()) {
            if(use->assertion_kind()==6)fail(use,"cover property does not support an else action");
            statement(p,actions->else_stmt(),id);
        } else if(use->assertion_kind()!=6) {
            p.side_effect=true;p.selection_only_effects=false;
            const auto identity=scope->path+(use->assertion_label().empty()?"":"."+use->assertion_label());
            add(p,"s.print("+quote(escape_format_text("DSIM error: concurrent assertion failed at "+identity+":"+std::to_string(use->line())))+",{},true);");
        }
        p.instructions[end].yes=int(p.instructions.size());
        if(p.timing_controls)fail(use,"timing and suspension in property actions are not supported");
        for(const auto& inst:p.instructions)if(inst.code.find("return;")!=std::string::npos)
            fail(use,"timing and suspension in property actions are not supported");
        add(p,"pc=0;return;");
        for(const auto& sample:lowering_samples){read(p,sample.value);read(p,sample.gate);}
        properties[size_t(site)].samples=std::move(lowering_samples);
        sampling_property=-1;sampling_context=0;
        processes[size_t(id)]=std::move(p);return true;
    }

    struct WaitIR { int process; std::string events,expressions; bool ordered=false;
        std::vector<std::pair<int,int>> refs; bool static_refs=false; };
    std::vector<WaitIR> wait_sites,event_nba_sites;
    struct ForkIR {int parent;std::vector<int> children;int kind=1;};
    std::vector<ForkIR> fork_groups;
    struct DisableIR {int process,begin,end,identity;size_t first_group,last_group;};
    std::map<std::tuple<Scope*,std::string,int>,int> disable_identities;
    std::string disable_callable_identity;int disable_block_ordinal=0;
    std::vector<DisableIR> disable_targets;
    struct NamedBlock {std::string label;int target;std::vector<int> exits;};
    std::vector<std::shared_ptr<NamedBlock>> named_blocks;
    bool needs_process_control=false,needs_ipc=false,needs_process_handles=false,needs_process_lifetime=false,needs_array_stream=false;
    bool lowering_final=false,needs_final=false,needs_plusargs=false,needs_file_io=false,needs_scan=false;
    std::vector<DeclarationInit> initializers;
    std::map<int,E> aggregate_defaults;
    std::map<int,std::pair<E,E>> container_aggregate_types;
    std::map<std::pair<int,int>,std::pair<E,E>> object_aggregate_types;
    std::map<int,E> aggregate_state_masks;
    std::vector<std::string> continuous_channels;
    std::vector<int> continuous_owners;
    int driver=0;
    int add(ProcessIR& p,std::string s) { Instruction inst;inst.code=std::move(s);inst.activation_depth=p.activation_depth;p.instructions.push_back(std::move(inst));return int(p.instructions.size())-1; }
    void read(ProcessIR& p,E e) {
        if(lowering_final&&e->function_forks)fail(nullptr,"final blocks cannot spawn background processes");
        p.function_forks|=e->function_forks;p.side_effect|=e->function_forks;p.selection_only_effects&=!e->function_forks;
        p.sensitivity_reads.push_back(e);p.nonstatic_writes.insert(e->nonstatic_writes.begin(),e->nonstatic_writes.end()); p.io_state|=e->io_state;p.random_state|=e->random_state;p.side_effect|=e->random_state||e->io_state;p.selection_only_effects&=!e->random_state&&!e->io_state;p.event_safe&=e->event_safe;if(e->selection_checks){p.side_effect=true;p.selection_only_effects=false;p.selection_checks=true;} p.reads.insert(e->reads.begin(),e->reads.end()); p.touches.insert(e->reads.begin(),e->reads.end()); p.touches.insert(e->touches.begin(),e->touches.end());
        p.partial_writes.insert(e->partial_writes.begin(),e->partial_writes.end());
        p.whole_writes.insert(e->whole_writes.begin(),e->whole_writes.end());
        p.function_reads.insert(e->function_reads.begin(),e->function_reads.end());p.touches.insert(e->function_reads.begin(),e->function_reads.end());
        std::set<int> ranged;
        for(auto [id,lo,width]:e->write_ranges){p.writes.push_back({id,lo,width,0});ranged.insert(id);}
        for(int id:e->writes)if(!ranged.count(id))p.writes.push_back({id,0,signals[id].width,0});
    }
    std::string emit(E e,int context=0) {
        auto fallback=emit_expression(e,context,parallel_count!=0);
        if(needs_real||e->width!=1)return fallback;
        // Fuse a pure scalar predicate into one native word calculation. The
        // unknown guard covers every input; the ordinary four-state expression
        // remains the fallback, with no stores or scheduler boundaries removed.
        size_t operations=0;
        const auto count=[&](auto&& self,const E& term)->void {
            if(!term->args.empty())++operations;
            for(const auto& arg:term->args)self(self,arg);
        };
        count(count,e);
        if(operations<4)return fallback;
        std::set<int> ids;auto native=integral_expression(e,ids,context);
        if(native.empty()||ids.empty())return fallback;
        std::string code="([&](){\n#ifndef DSIM_RTL_REFERENCE_EXPRESSIONS\n";
        for(int id:ids)code+="auto native_value"+std::to_string(id)+"=s.get("+sid(id)+");";
        code+="if((0ULL";
        for(int id:ids)code+="|native_value"+std::to_string(id)+".b";
        code+=")==0){";
        for(int id:ids)code+="uint64_t native"+std::to_string(id)+"=native_value"+std::to_string(id)+".a;";
        return code+"return V("+native+",0,"+std::to_string(std::max(context,e->width))+");}\n#endif\nreturn "+fallback+";}())";
    }
    static std::string parallel_window_option() {
        return "else if(std::string(argv[i])==\"--parallel-window\"){"
               "if(++i==argc)throw std::runtime_error(\"--parallel-window requires a positive tick count\");"
               "std::string value=argv[i];if(value.empty()||value.find_first_not_of(\"0123456789\")!=std::string::npos)"
               "throw std::runtime_error(\"invalid --parallel-window tick count\");"
               "parallel_window=std::stoull(value);if(!parallel_window)throw std::runtime_error(\"parallel window must be positive\");}";
    }
    std::string sid(int id) const {return parallel_count?"sid["+std::to_string(id)+"]":std::to_string(id);}
    // Only total, known-bit operations enter a native loop. Unsigned host
    // arithmetic gives Verilog wraparound without signed-overflow UB.
    std::string integral_expression(E e,std::set<int>& ids,int context=0,int sign_context=-1) {
        if(needs_real)return {};
        const int w=std::max(context,e->width);
        if(w>64||e->width<1||e->text_value||!e->writes.empty()||e->random_state||e->io_state)return {};
        const bool sign=e->signed_value&&sign_context!=0;
        const auto sized=[&](std::string code,int from,bool extend) {
            if(code.empty())return code;
            if(extend&&w>from)code="(("+code+"^"+std::to_string(uint64_t(1)<<(from-1))+"ULL)-"+std::to_string(uint64_t(1)<<(from-1))+"ULL)";
            return "("+code+"&"+std::to_string(w==64?UINT64_MAX:(uint64_t(1)<<w)-1)+"ULL)";
        };
        if(e->op=="signal") {ids.insert(e->signal);return sized("native"+std::to_string(e->signal),e->width,sign);}
        if(e->op=="literal") {
            if(!e->canonical_literal||e->unknown||e->host_overflow)return {};
            return sized(std::to_string(e->value)+"ULL",e->width,sign);
        }
        if(e->op=="fill1")return std::to_string(w==64?UINT64_MAX:(uint64_t(1)<<w)-1)+"ULL";
        if((e->op=="cast"||e->op=="two_state")&&e->width==e->args[0]->width)
            return sized(integral_expression(e->args[0],ids),e->width,sign);
        if(e->args.size()==1&&(e->op=="~"||e->op=="+"||e->op=="-"||e->op=="!")) {
            auto a=integral_expression(e->args[0],ids,e->op=="!"?0:w,e->op=="!"?-1:int(sign));
            if(a.empty())return {};
            return sized("("+e->op+a+")",w,false);
        }
        if(e->op=="slice"&&e->args.size()==1) {
            const auto comma=e->literal.find(',');
            if(comma==std::string::npos)return {};
            const int lo=std::stoi(e->literal.substr(0,comma)),width=std::stoi(e->literal.substr(comma+1));
            if(lo<0||width!=e->width||lo+width>e->args[0]->width)return {};
            auto a=integral_expression(e->args[0],ids);if(a.empty())return {};
            return sized("(("+a+">>"+std::to_string(lo)+")&"+std::to_string(width==64?UINT64_MAX:(uint64_t(1)<<width)-1)+"ULL)",width,sign);
        }
        if(e->op=="replicate"&&e->args.size()==1&&e->args[0]->width==1) {
            auto a=integral_expression(e->args[0],ids);if(a.empty())return {};
            return sized("((0ULL-"+a+")&"+std::to_string(e->width==64?UINT64_MAX:(uint64_t(1)<<e->width)-1)+"ULL)",e->width,false);
        }
        if(e->args.size()!=2)return {};
        if(e->op=="<<"||e->op==">>") {
            auto a=integral_expression(e->args[0],ids,w,int(sign));
            auto b=integral_expression(e->args[1],ids);
            if(a.empty()||b.empty())return {};
            return sized("("+b+">=64?0ULL:("+a+e->op+b+"))",w,false);
        }
        const bool compare=e->op=="<"||e->op==">"||e->op=="<="||e->op==">="||e->op=="=="||e->op=="!="||e->op=="==="||e->op=="!==";
        const bool logical=e->op=="&&"||e->op=="||";
        if(!compare&&!logical&&e->op!="+"&&e->op!="-"&&e->op!="*"&&e->op!="&"&&e->op!="|"&&e->op!="^")return {};
        const int aw=compare?std::max(e->args[0]->width,e->args[1]->width):w;
        const bool operand_sign=compare?e->args[0]->signed_value&&e->args[1]->signed_value:sign;
        auto a=integral_expression(e->args[0],ids,logical?0:aw,logical?-1:int(operand_sign));
        auto b=integral_expression(e->args[1],ids,logical?0:aw,logical?-1:int(operand_sign));
        if(a.empty()||b.empty())return {};
        if(compare&&operand_sign) {
            // Flipping the common sign bit maps signed ordering to unsigned.
            const auto bias=std::to_string(uint64_t(1)<<(aw-1))+"ULL";
            a="("+a+"^"+bias+")";b="("+b+"^"+bias+")";
        }
        auto op=e->op=="==="?"==":e->op=="!=="?"!=":e->op;
        return sized("("+a+op+b+")",w,false);
    }
    std::string integral_loop(const ProcessIR& process,size_t start) {
        if(needs_process_control||dynamic_forks_enabled())return {};
        const auto& code=process.instructions;const auto& test=code[start];
        if(!test.condition||test.yes!=int(start+1)||test.no<=int(start+2)||test.no>int(code.size()))return {};
        const int end=test.no;
        if(code[size_t(end-1)].yes!=int(start)||code[size_t(end-1)].condition||!code[size_t(end-1)].code.empty())return {};
        std::set<int> ids;auto condition=integral_expression(test.condition,ids);
        if(condition.empty())return {};
        std::string body;std::set<int> writes;
        for(size_t i=start+1;i<size_t(end-1);++i) {
            const auto& inst=code[i];
            if(inst.integral_target<0||!inst.integral_value||inst.condition||inst.yes>=0||inst.activation_depth!=test.activation_depth)return {};
            const int id=inst.integral_target;auto value=integral_expression(inst.integral_value,ids,signals[size_t(id)].width);
            if(value.empty())return {};
            ids.insert(id);writes.insert(id);body+="native"+std::to_string(id)+"=("+value+")&"+std::to_string(signals[size_t(id)].width==64?UINT64_MAX:(uint64_t(1)<<signals[size_t(id)].width)-1)+"ULL;";
        }
        if(ids.empty())return {};
        for(int id:ids)if(signals[size_t(id)].net||signals[size_t(id)].text_value||signals[size_t(id)].named_event||dynamic_signals.count(id)||(automatic_signals.count(id)&&!(process.function&&event_function_storage.count(id))))return {};
        std::string result="// Native integral loop; guarded observable-state fallback.\nif(s.integral_loop_ready({";
        for(int id:ids)result+=sid(id)+",";
        result+="})){";
        for(int id:ids)result+="uint64_t native"+std::to_string(id)+"=s.integral_loop_value("+sid(id)+").a;";
        result+="bool native_budget=false;while("+condition+"){if(!s.integral_loop_steps("+std::to_string(end-int(start))+")){native_budget=true;break;}"+body+"}";
        for(int id:writes)result+="s.integral_loop_value("+sid(id)+").a=native"+std::to_string(id)+";";
        return result+"pc=native_budget?"+std::to_string(start+1)+":"+std::to_string(end)+";continue;}\n";
    }
    std::string pid(int id) const {return parallel_count?"pid["+std::to_string(id)+"]":std::to_string(id);}
    std::string wid(int id) const {return parallel_count?"wid["+std::to_string(id)+"]":std::to_string(id);}
    std::string runtime_pid(int id) const {return "s.fork_process_id("+pid(id)+")";}
    std::string runtime_wid(int id) const {return "s.fork_wait_id("+wid(id)+")";}
    std::string name(VeriNode* n) {
        if(n->detail_type()==veEXP_PRI) return static_cast<VeriPrimaryExp*>(n)->str();
        if(n->detail_type()==veEXP_ARRAY) return static_cast<VeriArrayExp*>(n)->name();
        fail(n,"expected signal name");
    }
    E static_receiver_effect(VeriNode* n) {
        if(n->detail_type()==veEXP_ARRAY)return static_receiver_effect(static_cast<VeriArrayExp*>(n)->id());
        if(n->detail_type()!=veEXP_MEMBER)return {};
        auto* member=static_cast<VeriMemberExp*>(n);
        if(member->scope_reference()||!class_statics.count(member->class_member()))return {};
        return expr(member->object());
    }
    E evaluate_before(E effect,E value) {
        if(!effect)return value;
        auto result=node("call",value->width,{effect,value});
        result->literal="return call_arg1;";result->signed_value=value->signed_value;
        result->text_value=value->text_value;result->object_type=value->object_type;result->enum_id=value->enum_id;result->interface_type=value->interface_type;
        return result;
    }
    Scope* variable_scope(VeriNode* n,Variable var) {
        if(argument_values.count(var.node))fail(n,"default argument dependence requiring formal storage is not supported yet");
        for(auto* sc=scope;sc;sc=sc->parent) {
            auto it=sc->symbols.find(var->name());
            if(it!=sc->symbols.end() && it->second==var.node)return sc;
        }
        auto shared=class_statics.find(var.node);
        if(shared!=class_statics.end())return shared->second;
        if(var.node->birth_mod()&&var.node->birth_mod()->is_package()) {
            auto it=package_scopes.find(var.node->birth_mod());
            if(it!=package_scopes.end()) {
                auto found=it->second->symbols.find(var.name());
                if(found!=it->second->symbols.end()&&found->second==var.node)return it->second;
            }
        }
        fail(n,"hierarchical expression references are not supported yet: "+var->name());
    }
    Scope* hierarchical_scope(VeriNode* n,Variable var) {
        Scope* result=nullptr;
        for(const auto& sc:scopes) {
            auto found=sc->symbols.find(var.name());
            if(found!=sc->symbols.end()&&found->second==var.node) {
                if(result)fail(n,"hierarchical instance array requires an explicit supported index");
                result=sc.get();
            }
        }
        if(!result)fail(n,"hierarchical storage was not found");
        return result;
    }
    static bool interface_compatible(const std::shared_ptr<VeriVirtualInterface>& actual,const std::shared_ptr<VeriVirtualInterface>& expected) {
        return actual&&expected&&actual->name==expected->name&&(actual->view.empty()||actual->view==expected->view);
    }
    E interface_literal(VeriMod* instance,const std::string& view,VeriNode* source) {
        for(size_t i=0;i<scopes.size();++i) {
            const auto& candidate=*scopes[i];
            if(candidate.mod!=instance||candidate.parent)continue;
            auto value=node("literal",64);value->literal="V("+std::to_string(i+1)+"ULL,0,64)";
            value->interface_namespace=true;value->interface_type=std::make_shared<VeriVirtualInterface>();value->interface_type->name=instance->name();value->interface_type->view=view;value->interface_type->prototype=instance;return value;
        }
        fail(source,"virtual interface actual instance has not been elaborated");return {};
    }
    PartIR virtual_member_part(VeriMemberExp* member) {
        const auto type=veri_virtual_interface(member->object());
        if(!type)fail(member,"virtual interface receiver type was not resolved");
        auto* symbol=member->hierarchical_symbol();
        if(!variable(symbol)||Variable{symbol}.range_depth())fail(member,"virtual interface member requires scalar or packed storage; unpacked members are not supported yet");
        PartIR part{-1,0,Variable{symbol}.dlen(),0};part.virtual_handle=expr(member->object());
        for(size_t i=0;i<scopes.size();++i) {
            const auto& candidate=*scopes[i];
            if(candidate.parent||!candidate.mod->is_interface()||candidate.mod->name()!=type->name)continue;
            auto found=candidate.ids.find(member->member());if(found==candidate.ids.end())continue;
            const int id=found->second;
            if(signals[id].width!=part.width||signals[id].real_width||signals[id].text_value||signals[id].named_event)
                fail(member,"virtual interface member layout does not match the declared type");
            part.virtual_targets.emplace_back(i+1,id);if(part.signal<0)part.signal=id;
        }
        if(part.signal<0)fail(member,"virtual interface type has no elaborated compatible instance");
        return part;
    }
    E virtual_member_read(VeriMemberExp* member) {
        auto value=virtual_part_read(virtual_member_part(member));
        value->signed_value=Variable{member->hierarchical_symbol()}.is_signed()==IS_TRUE;value->enum_id=enum_identity(member->hierarchical_symbol());return value;
    }
    E virtual_part_read(const PartIR& part) {
        auto value=node("call",signals[part.signal].width,{part.virtual_handle});value->interface_dereference=true;
        value->literal="if(call_arg0.b||!call_arg0.a)throw std::runtime_error(\"null virtual interface dereference\");switch(call_arg0.a){";
        for(const auto& target:part.virtual_targets) {
            value->literal+="case "+std::to_string(target.first)+"ULL:return s.get("+sid(target.second)+");";
            value->reads.insert(target.second);value->direct_reads.insert(target.second);
        }
        value->literal+="default:throw std::runtime_error(\"invalid virtual interface handle\");}";
        return value;
    }
    int dynamic_object(VeriNode* n) {
        if(veri_subroutine_call(n))return -1;
        auto* symbol=variable(n)?n:n->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(n)->var():
            n->detail_type()==veEXP_MEMBER?(static_cast<VeriMemberExp*>(n)->class_member()?static_cast<VeriMemberExp*>(n)->class_member():static_cast<VeriMemberExp*>(n)->hierarchical_symbol()):nullptr;
        if(!variable(symbol)||!Variable{symbol}.dynamic()||object_fields.count(symbol))return -1;
        return (n->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(n)->hierarchical_symbol()?hierarchical_scope(n,Variable{symbol}):variable_scope(n,Variable{symbol}))->ids.at(Variable{symbol}.name());
    }
    struct AssociativeView {VeriNode* symbol=nullptr;int id=-1;E receiver;std::vector<E> prefix;};
    static bool associative_kind(int kind) {return kind==vrASSOC_INT||kind==vrASSOC_UINT||kind==vrASSOC_STRING||kind==vrASSOC_CLASS;}
    AssociativeView associative_view(VeriNode* n) {
        auto* symbol=veri_array_element_symbol(n);
        if(!variable(symbol)||!associative_kind(Variable{symbol}.container_kind()))return {};
        if(n->detail_type()==veEXP_ARRAY) {
            auto* a=static_cast<VeriArrayExp*>(n);auto view=associative_view(a->id());
            if(view.id<0)return {};
            for(auto* item:a->range()) {
                if(view.prefix.size()>=size_t(Variable{symbol}.range_depth()))return {};
                auto* index=static_cast<VeriRangeExp*>(item);if(index->rtype()!=vrSINGLE)return {};
                view.prefix.push_back(associative_index(item,symbol,expr(index->left()),view.prefix.size()));
            }
            return view.prefix.size()<size_t(Variable{symbol}.range_depth())?view:AssociativeView{};
        }
        if(object_fields.count(symbol)) {
            auto receiver=n->detail_type()==veEXP_MEMBER&&!static_cast<VeriMemberExp*>(n)->scope_reference()?expr(static_cast<VeriMemberExp*>(n)->object()):implicit_this(n);
            return {symbol,objects_signal,receiver};
        }
        const int id=dynamic_object(n);return id<0?AssociativeView{}:AssociativeView{symbol,id,{}};
    }
    std::string associative_reference(const AssociativeView& view,const std::string& receiver={}) {
        if(!view.prefix.empty()) {
            auto selected=view;
            if(view.receiver&&!receiver.empty()){selected.receiver=std::make_shared<Expr>(*view.receiver);selected.receiver->op="saved";selected.receiver->args.clear();selected.receiver->literal=receiver;}
            return emit(associative_reference_expr(selected));
        }
        if(!view.receiver)return sid(view.id);
        auto field=object_fields.at(view.symbol);return "s.object_associative("+(receiver.empty()?emit(view.receiver):receiver)+","+std::to_string(classes.at(field.first).id)+","+std::to_string(field.second)+","+std::to_string(Variable{view.symbol}.dlen())+","+sid(objects_signal)+","+(Variable{view.symbol}.container_kind()==vrASSOC_UINT?"true":"false")+","+(Variable{view.symbol}.container_kind()==vrASSOC_CLASS?"true":"false")+")";
    }
    E associative_reference_expr(const AssociativeView& view) {
        std::vector<E> args;if(view.receiver)args.push_back(view.receiver);
        args.insert(args.end(),view.prefix.begin(),view.prefix.end());
        auto value=node("container_ref",1,args);value->signal=view.id;value->reads.insert(view.id);value->direct_reads.insert(view.id);
        auto root=view;root.prefix.clear();
        std::string code="auto ref="+(view.receiver?associative_reference(root,"container_arg0"):"s.associative_ref("+sid(view.id)+")")+";";
        for(size_t axis=0;axis<view.prefix.size();++axis) {
            const int next=veri_array_container_kind(view.symbol,axis+1);
            code+="ref=s.associative_subarray(ref,container_arg"+std::to_string(axis+(view.receiver?1:0))+","+(next==vrASSOC_UINT?"true":"false")+","+(next==vrASSOC_CLASS?"true":"false")+");";
        }
        value->literal=code+"return ref;";return value;
    }
    AssociativeView object_queue_view(VeriNode* n) {
        auto* symbol=veri_array_element_symbol(n);
        if(!object_fields.count(symbol)||(Variable{symbol}.container_kind()!=vrQUEUE&&Variable{symbol}.container_kind()!=vrOPEN)||n->detail_type()==veEXP_ARRAY)return {};
        auto receiver=n->detail_type()==veEXP_MEMBER&&!static_cast<VeriMemberExp*>(n)->scope_reference()?expr(static_cast<VeriMemberExp*>(n)->object()):implicit_this(n);
        return {symbol,objects_signal,receiver};
    }
    std::string object_queue_reference(const AssociativeView& view,const std::string& receiver={}) {
        auto field=object_fields.at(view.symbol);
        return "s.object_queue("+(receiver.empty()?emit(view.receiver):receiver)+","+std::to_string(classes.at(field.first).id)+","+std::to_string(field.second)+","+sid(objects_signal)+")";
    }
    std::string random_array_binding(VeriNode* array) const {
        auto* symbol=veri_array_element_symbol(array);auto it=random_arrays.find(symbol);
        if(it==random_arrays.end())return {};
        if(array->detail_type()==veEXP_PRI)return it->second;
        if(array->detail_type()==veEXP_MEMBER) {
            auto* receiver=static_cast<VeriMemberExp*>(array)->object();
            if(receiver&&receiver->detail_type()==veEXP_PRI) {
                const auto& name=static_cast<VeriPrimaryExp*>(receiver)->str();
                if(name=="this"||name=="super")return it->second;
            }
        }
        return {};
    }
    E associative_index(VeriNode* location,VeriNode* symbol,E value,unsigned axis=0) {
        if(veri_array_container_kind(symbol,axis)==vrASSOC_STRING)return text_context(value);
        if(veri_array_container_kind(symbol,axis)==vrASSOC_CLASS) {
            auto* key=veri_associative_key_type(symbol,axis);
            if(!key||!class_compatible(value->object_type,int(key->class_type()->idx())))
                fail(location,"class-key associative array requires a compatible object handle or null");
            return value;
        }
        if(value->packed_value)value=value->packed_value;
        if(value->text_value||value->object_type!=-1||value->real_width||value->array_value)fail(location,"int-key associative array requires an integral index");
        auto* key=veri_associative_key_type(symbol,axis);
        const int width=key?key->dlen():32;
        if(width>64)needs_wide=true;
        auto converted=node("argument",width,{value});converted->signed_value=value->signed_value;
        return converted;
    }
    bool associative_queue_leaf(const AssociativeView& view) const {
        return view.id>=0&&associative_kind(Variable{view.symbol}.container_kind())&&view.prefix.size()+1==size_t(Variable{view.symbol}.range_depth())&&veri_array_container_kind(view.symbol,view.prefix.size())==vrQUEUE;
    }
    bool associative_queue_type(VeriNode* symbol) const {
        return variable(symbol)&&Variable{symbol}.range_depth()>1&&associative_kind(Variable{symbol}.container_kind())&&veri_array_container_kind(symbol,Variable{symbol}.range_depth()-1)==vrQUEUE;
    }
    E container_method(VeriMemberExp* member,bool statement=false) {
        if(auto binding=random_array_binding(member->object());!binding.empty()&&member->member()=="size") {
            auto value=node("constraint_array_size",32);value->literal=binding+"_size";value->signed_value=true;return value;
        }
        const auto object_queue=object_queue_view(member->object());
        const auto view=object_queue.id>=0?object_queue:associative_view(member->object());
        const int id=view.id>=0?view.id:dynamic_object(member->object());if(id<0)return {};
        const bool nested_queue=associative_queue_leaf(view);
        const bool queue=nested_queue||object_queue.id>=0||queue_bounds.count(id),assoc=view.id>=0&&object_queue.id<0&&!nested_queue;
        if(!queue&&!assoc)return {};
        const auto& method=member->member();
        if(object_queue.id>=0&&Variable{object_queue.symbol}.container_kind()==vrOPEN&&method!="size"&&method!="delete")fail(member,"dynamic arrays support size() and delete() rather than queue mutation methods");
        const bool size=method=="size"||method=="num";
        auto effect=static_receiver_effect(member->object());
        if(size&&!view.receiver&&view.prefix.empty())return evaluate_before(effect,dynamic_size_expr(id));
        const bool pop=queue&&(method=="pop_back"||method=="pop_front");
        const bool cursor=assoc&&(method=="first"||method=="last"||method=="next"||method=="prev");
        const bool exists=assoc&&method=="exists";
        if(!statement&&!size&&!pop&&!cursor&&!exists)fail(member,"void container method requires a statement without a value");
        auto actuals=veri_system_arguments(member->arguments());std::vector<E> args;
        const bool subarray=(assoc||nested_queue)&&!view.prefix.empty();
        if(subarray)args.push_back(associative_reference_expr(view));else if(view.receiver)args.push_back(view.receiver);
        const auto argument_base=args.size();const std::string key_arg="container_arg"+std::to_string(argument_base);
        auto* element_symbol=veri_array_element_symbol(member->object());
        const int width=view.receiver?Variable{element_symbol}.dlen():signals[id].width;
        const bool two_state=view.receiver?Variable{element_symbol}.two_state():signals[id].two_state;
        const bool text=veri_string_value(element_symbol);
        for(size_t i=0;i<actuals.size();++i) {
            auto* actual=actuals[i];const bool element=!assoc&&(method=="push_back"||method=="push_front"||(method=="insert"&&i==1));
            auto value=element?context_expr(actual,element_symbol):expr(actual);
            if(assoc)value=associative_index(actual,element_symbol,value,view.prefix.size());
            else {
                if(value->packed_value)value=value->packed_value;
                if(element&&text) {args.push_back(text_context(value));continue;}
                if(value->text_value||value->real_width||value->array_value)fail(actual,"integral container method requires integral arguments");
                if(element) {
                    enum_assignment(element_symbol,value);
                    const int destination=class_type(element_symbol);
                    if(destination>=0?!class_compatible(value->object_type,destination):value->object_type!=-1)
                        fail(actual,"queue method requires a compatible element type");
                }
                else if(value->object_type!=-1)fail(actual,"container index requires an integral value");
                auto converted=node("argument",element?width:32,{value});converted->signed_value=value->signed_value;value=converted;
            }
            args.push_back(value);
        }
        auto value=node("container_method",pop?width:32,args);value->signal=id;
        if(pop){value->text_value=text;value->enum_id=enum_identity(element_symbol);value->object_type=class_type(element_symbol);}
        value->signed_value=member->is_signed()==IS_TRUE;value->reads.insert(id);value->direct_reads.insert(id);value->touches.insert(id);
        auto modify=[&](int target) {
            writable(target,member);value->writes.insert(target);value->nonstatic_writes.insert(target);
            value->touches.insert(target);value->event_safe=false;value->procedural_only=true;
        };
        auto ref=nested_queue?std::string("container_arg0"):object_queue.id>=0?object_queue_reference(view,"container_arg0"):assoc?(subarray?std::string("container_arg0"):associative_reference(view,view.receiver?"container_arg0":"")):std::string("@object");
        if(size){value->literal="return V(s."+std::string(nested_queue?"associative_queue_size":object_queue.id>=0?"object_queue_size":"associative_size")+"("+ref+"),0,32);";return evaluate_before(effect,value);}
        if(exists){value->literal="return V(s.associative_exists("+ref+","+key_arg+")?1:0,0,32);";return evaluate_before(effect,value);}
        if(cursor) {
            auto target=lvalue(actuals[0]);const bool text=veri_array_container_kind(element_symbol,view.prefix.size())==vrASSOC_STRING;
            auto* key_type=veri_associative_key_type(element_symbol,view.prefix.size());
            const bool class_key=key_type&&key_type->class_type();
            if(class_key&&class_type(actuals[0])!=int(key_type->class_type()->idx()))
                fail(member,"class-key associative cursor requires the declared key class type");
            if(key_type&&key_type->enum_type()&&enum_identity(actuals[0])!=enum_identity(key_type))
                fail(member,"enum-key associative cursor requires the declared enum type");
            if(target.parts.size()!=1||target.parts[0].index||target.parts[0].word_index||target.parts[0].lo||target.parts[0].object||signals[target.parts[0].signal].net||signals[target.parts[0].signal].text_value!=text||(!text&&target.width!=(key_type?key_type->dlen():32)))
                fail(member,class_key?"class-key associative cursor requires a whole handle variable":text?"associative cursor requires a whole string variable":!key_type||key_type->dlen()==32?"associative cursor requires a whole 32-bit integral variable":"associative cursor requires a whole integral variable of the key width");
            const int key=target.parts[0].signal;modify(key);
            value->literal="bool found=s.associative_cursor("+ref+","+key_arg+","+std::to_string(method=="first"?0:method=="last"?1:method=="next"?2:3)+");if(found)s.set("+sid(key)+","+key_arg+");return V(found?1:0,0,32);";
            return evaluate_before(effect,value);
        }
        modify(id);
        if(assoc)value->literal="s.associative_delete("+ref+","+(actuals.empty()?std::string("V(0)"):key_arg)+","+(actuals.empty()?"true":"false")+","+std::to_string(width)+");return V(0,0,32);";
        else {
            const int op=method=="push_back"?0:method=="push_front"?1:method=="pop_back"?2:method=="pop_front"?3:method=="insert"?4:actuals.empty()?6:5;
            const std::string index=op==4||op==5?key_arg:"V(0)";
            const std::string item=op<=1?key_arg:op==4?"container_arg"+std::to_string(argument_base+1):"V(0)";
            value->literal="return s."+std::string(nested_queue?"associative_queue_method":object_queue.id>=0?"object_queue_method":"queue_method")+"("+ref+","+std::to_string(op)+","+index+","+item+","+std::to_string(width)+","+(two_state?"true":"false")+","+std::to_string(nested_queue?Variable{element_symbol}.container_bound(view.prefix.size()):object_queue.id>=0?Variable{element_symbol}.container_bound():queue_bounds.at(id))+","+(text?"true":"false")+");";
        }
        return evaluate_before(effect,value);
    }
    E dynamic_size_expr(int id) {
        auto e=node(associative_signals.count(id)?"associative_size":"dynamic_size",32);e->signal=id;e->signed_value=true;e->reads.insert(id);e->direct_reads.insert(id);return e;
    }
    E dynamic_read_expr(int id,E index) {
        auto e=node(associative_signals.count(id)?"associative_read":"dynamic_read",signals[id].width,{index});e->signal=id;e->literal=signals[id].two_state?"true":"false";if(string_element_signals.count(id)){e->text_value=true;e->literal+=",true";}e->reads.insert(id);e->direct_reads.insert(id);return e;
    }
    int variable_signal(VeriNode* n,Variable var) {
        if(reduction_items.count(var.node))fail(n,"array reduction iterator is read-only");
        if(var.result()&&var.fn()->func()->is_void())fail(n,"void function has no value");
        if(var->range_depth())fail(n,"unpacked array requires an element index: "+var->name());
        return variable_scope(n,var)->ids.at(var->name());
    }
    int signal(VeriNode* n) {
        if(n->detail_type()==veEXP_ARRAY)return signal(static_cast<VeriArrayExp*>(n)->id());
        if(n->detail_type()==veEXP_PRI) {
            auto* var=static_cast<VeriPrimaryExp*>(n)->var();
            if(variable(var)){if(Variable{var}.net_type()==vvEVENT)fail(n,"event handles require event controls or triggered queries");return variable_signal(n,Variable{var});}
        }
        fail(n,"undeclared signal "+name(n));
    }
    std::string dump_target(VeriNode* n) {
        if(n->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(n)->pri_type()!=veSTR)
            fail(n,"$dumpvars target must be a scope or whole signal");
        auto raw=static_cast<VeriPrimaryExp*>(n)->str();
        if(raw.empty()||raw.front()!='\x1f')fail(n,"invalid $dumpvars target");
        auto plain=[](std::string s){if(!s.empty()&&s.front()=='\\')s.erase(0,1);return s;};
        std::vector<std::string> parts;
        for(size_t p=1;p<=raw.size();) {
            auto end=raw.find('\x1f',p);if(end==std::string::npos)end=raw.size();
            parts.push_back(plain(raw.substr(p,end-p)));p=end+1;
        }
        auto path=scope->wave_path;for(auto& p:path)p=plain(p);
        for(;;) {
            auto candidate=path;
            if(parts.front()==plain(scopes.front()->wave_path.front()))candidate.clear();
            candidate.insert(candidate.end(),parts.begin(),parts.end());
            for(const auto& sc:scopes) {
                auto base=sc->wave_path;for(auto& p:base)p=plain(p);
                bool is_scope=base==candidate,is_signal=false;
                if(candidate.size()==base.size()+1&&std::equal(base.begin(),base.end(),candidate.begin())) {
                    for(const auto& id:sc->ids)if(plain(id.first)==candidate.back())is_signal=true;
                    if(gate_design&&sc->mod->name()==GateDesign::rtl_identifier(gate_design->top))
                        for(const auto& net:gate_design->wave_names)if(plain(net)==candidate.back())is_signal=true;
                }
                if(!is_scope&&!is_signal)continue;
                std::string out="{{";for(const auto& p:base)out+=quote(p)+",";
                return out+"},"+quote(is_signal?candidate.back():std::string())+"}";
            }
            if(path.empty())break;
            path.pop_back();
        }
        fail(n,"unresolved $dumpvars scope or signal target");
    }
    bool lvalue_shape(VeriNode* n) {
        if(!n) return false;
        if(n->detail_type()==veEXP_PRI) {
            auto* var=static_cast<VeriPrimaryExp*>(n)->var();
            return variable(var);
        }
        if(n->detail_type()==veEXP_MEMBER){auto* m=static_cast<VeriMemberExp*>(n);return m->hierarchical_symbol()?variable(m->hierarchical_symbol()):!m->method_type()&&!veri_array_reduction(n)&&lvalue_shape(m->object());}
        if(n->detail_type()==veEXP_ARRAY) return !veri_queue_slice(n)&&lvalue_shape(static_cast<VeriArrayExp*>(n)->id());
        if(n->detail_type()!=veEXP_MULTI) return false;
        auto* multi=static_cast<VeriMultiExp*>(n);
        if(multi->multi_type()!=vemCONCAT_EXP || multi->exp().empty()) return false;
        for(auto* child:multi->exp()) if(!lvalue_shape(child)) return false;
        return true;
    }
    PartIR storage_part(VeriNode* n) {
        if(veri_event_symbol(n))fail(n,"event handles require event controls or triggered queries; event aliases are not supported yet");
        if(n->detail_type()==veEXP_PRI)if(auto* symbol=static_cast<VeriPrimaryExp*>(n)->var();object_fields.count(symbol))return object_part(symbol,implicit_this(n));
        if(n->detail_type()==veEXP_ARRAY)return selected(n);
        if(n->detail_type()==veEXP_MEMBER) {
            auto* member=static_cast<VeriMemberExp*>(n);
            if(member->clocking_owner())fail(n,"clocking signals require a whole-member nonblocking drive");
            if(object_fields.count(member->class_member())&&!member->called())return object_part(member->class_member(),member->scope_reference()?implicit_this(n):expr(member->object()));
            if(member->hierarchical_symbol()) {
                if(veri_virtual_interface(member->object())) {if(!member->interface_writable())fail(n,"cannot write input member through modport");return virtual_member_part(member);}
                if(member->interface_reference()&&!member->interface_writable())fail(n,"cannot write input member through modport");
                Variable var{member->hierarchical_symbol()};
                if(!variable(var.node))fail(n,"hierarchical assignment requires a variable target");
                if(var->range_depth())fail(n,"hierarchical array write requires all element indices");
                auto* owner=hierarchical_scope(n,var);int id=owner->ids.at(var->name());PartIR part{id,0,signals[id].width,0};part.receiver_effect=static_receiver_effect(n);return part;
            }
            if(veri_array_reduction(n))fail(n,"method result is not an assignment target");
            auto part=storage_part(member->object());
            if(member->event_query())fail(n,"triggered query is not an assignment target");
            if(member->method_type()||!member->field())fail(n,"method result is not an assignment target");
            if(part.index)fail(n,"member requires a whole packed aggregate");
            part.lo+=member->field()->offset;part.width=member->field()->symbol->dlen();part.struct_string_field=veri_string_value(member->field()->symbol);return part;
        }
        if(!lvalue_shape(n))fail(n,"assignment target must be a variable");
        int id=signal(n);return {id,0,signals[id].width,0};
    }
    PartIR selected(VeriNode* n) {
        auto* a=static_cast<VeriArrayExp*>(n);
        if(veri_event_symbol(a->id()))fail(n,"event handles cannot be selected as integral values");
        if(auto* symbol=veri_array_element_symbol(a->id());variable(symbol)&&Variable{symbol}.range_depth()>1&&associative_kind(Variable{symbol}.container_kind())) {
            Variable property{symbol};const size_t rank=property.range_depth();
            if(a->range().size()<rank||a->range().size()>rank+1)fail(n,"associative element requires all unpacked indices and an optional packed select");
            auto view=associative_view(a->id());if(view.id<0)fail(n,"unsupported associative element receiver");
            E key;size_t axis=0;
            for(auto* item:a->range()) {
                if(axis==rank)break;auto* range=static_cast<VeriRangeExp*>(item);
                if(range->rtype()!=vrSINGLE)fail(item,"associative array requires an element key in each dimension");
                auto value=associative_index(item,symbol,expr(range->left()),axis++);
                if(axis==rank)key=value;else view.prefix.push_back(value);
            }
            PartIR part{view.id,0,property.dlen(),0};part.associative_ref=associative_reference_expr(view);part.word_index=key;
            part.object_width=property.dlen();part.object_two_state=property.two_state();part.object_text=veri_string_value(symbol);part.associative_queue=associative_queue_leaf(view);part.associative_queue_bound=property.container_bound(rank-1);part.field_class=class_type(symbol);part.field_enum=enum_identity(symbol);
            if(!view.receiver)part.memory=(a->id()->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(a->id())->hierarchical_symbol()?hierarchical_scope(n,property):variable_scope(n,property))->memories.at(property.name());
            if(a->range().size()>rank) {
                if(class_type(symbol)!=-1)fail(n,"class handles cannot be selected as packed integral values");
                auto packed=packed_selected(n,view.id,property.dend(),static_cast<VeriRangeExp*>(a->range().back()),property.dlen(),0,true,property.dstart()<property.dend());
                part.lo=packed.lo;part.width=packed.width;part.index=packed.index;part.base=packed.base;part.descending=packed.descending;
            }
            return part;
        }
        VeriNode* field=a->id()->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(a->id())->class_member():a->id()->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(a->id())->var():nullptr;
        if(object_fields.count(field)&&Variable{field}.range_depth()) {
            Variable property{field};auto part=storage_part(a->id());
            if(a->range().empty()||a->range().size()>2)fail(n,"class associative element requires one key and optional packed select");
            auto* key=static_cast<VeriRangeExp*>(a->range().front());
            if(key->rtype()!=vrSINGLE)fail(n,"associative array requires one element key");
            part.word_index=associative_index(n,field,expr(key->left()));
            part.object_queue=property.container_kind()==vrQUEUE||property.container_kind()==vrOPEN;part.object_queue_bound=property.container_kind()==vrOPEN?-2:property.container_bound();
            part.object_associative=!part.object_queue;part.object_unsigned_key=property.container_kind()==vrASSOC_UINT;part.object_class_key=property.container_kind()==vrASSOC_CLASS;
            if(a->range().size()==2) {
                if(class_type(field)!=-1)fail(n,"class handles cannot be selected as packed integral values");
                auto packed=packed_selected(n,objects_signal,property.dend(),static_cast<VeriRangeExp*>(a->range().back()),property.dlen(),0,true,property.dstart()<property.dend());
                part.lo=packed.lo;part.width=packed.width;part.index=packed.index;part.base=packed.base;part.descending=packed.descending;
            }
            return part;
        }
        if(object_fields.count(field)) {
            Variable property{field};if(class_type(field)!=-1||veri_string_value(field))fail(n,"class and string properties cannot be selected as integral vectors");
            if(a->range().size()!=1)fail(n,"class property currently requires one packed select");
            auto original=storage_part(a->id());
            auto part=packed_selected(n,objects_signal,property.dend(),static_cast<VeriRangeExp*>(a->range().front()),property.dlen(),0,true,property.dstart()<property.dend());
            part.object_class_key=original.object_class_key;part.object=original.object;part.object_type=original.object_type;part.object_field=original.object_field;part.object_width=original.object_width;part.object_two_state=original.object_two_state;
            part.object_const=original.object_const;part.object_const_initialized=original.object_const_initialized;return part;
        }
        if(a->id()->detail_type()==veEXP_MEMBER) {
            auto* base=static_cast<VeriMemberExp*>(a->id());
            if(base->hierarchical_symbol()) {
                if(veri_virtual_interface(base->object())) {
                    if(!base->interface_writable())fail(n,"cannot write input member through modport");
                    auto part=virtual_member_part(base);
                    if(a->range().size()!=1)fail(n,"virtual interface packed member requires one selection");
                    Variable var{base->hierarchical_symbol()};
                    auto selected=packed_selected(n,part.signal,var.dend(),static_cast<VeriRangeExp*>(a->range().front()),part.width,0,false,var.dstart()<var.dend());
                    selected.virtual_handle=part.virtual_handle;selected.virtual_targets=part.virtual_targets;return selected;
                }
                if(base->interface_reference()&&!base->interface_writable())fail(n,"cannot write input member through modport");
                Variable var{base->hierarchical_symbol()};if(!variable(var.node))fail(n,"interface select requires integral storage");
                auto part=selected_storage(a,var,hierarchical_scope(n,var));part.receiver_effect=static_receiver_effect(a->id());return part;
            }
            if(a->range().size()!=1)fail(n,"only one packed member select is supported");
            auto* member=static_cast<VeriMemberExp*>(a->id());if(member->method_type()||!member->field())fail(n,member->method_type()?"select of enum method result is not supported yet":"select of method result is not supported yet");auto part=storage_part(member);
            auto result=packed_selected(n,part.signal,member->field()->symbol->dend(),static_cast<VeriRangeExp*>(a->range().front()),part.width,part.lo,false,member->field()->symbol->dstart()<member->field()->symbol->dend());
            auto selection=result;result=part;result.lo=selection.lo;result.width=selection.width;result.rhs_lo=selection.rhs_lo;
            result.index=selection.index;result.base=selection.base;result.descending=selection.descending;return result;
        }
        if(!lvalue_shape(a->id())||a->id()->detail_type()!=veEXP_PRI) fail(n,"selected object must be a signal");
        Variable var{static_cast<VeriPrimaryExp*>(a->id())->var()};
        if(var.net_type()==vvEVENT)fail(n,"event handles cannot be selected as integral values");
        auto* sc=variable_scope(n,var);
        return selected_storage(a,var,sc);
    }
    PartIR selected_storage(VeriArrayExp* a,Variable var,Scope* sc) {
        VeriNode* n=a;
        if(veri_virtual_interface(var.node)&&a->range().size()>size_t(var.range_depth()))fail(n,"virtual interface handles cannot be selected as packed integral values");
        if(class_type(var.node)!=-1&&a->range().size()>size_t(var.range_depth()))fail(n,"class handles cannot be selected as packed integral values");
        int memory=-1,id=-1; E word_index;
        size_t packed_range=0;
        const auto shape=veri_array_shape(var.node);
        // VCS accepts constant [0]/[0:0] on scalar nets/variables (including a
        // selected unpacked scalar element), despite having no packed axis.
        // Keep array-query dimensions intact and limit this compatibility path
        // to that explicit zero subscript; dynamic scalar indices have distinct
        // vendor semantics and must not silently use vector clipping rules.
        size_t selection_dimensions=shape.dimensions.size();
        if(selection_dimensions==size_t(var.range_depth())&&a->range().size()>selection_dimensions) {
            if(a->range().size()!=selection_dimensions+1)fail(n,"too many packed indices");
            auto* scalar=static_cast<VeriRangeExp*>(a->range().back());
            auto known=[&](VeriNode* index,uint64_t wanted) {
                E value;
                if(index->tok_type()==vtEXP&&elaboration_expression(index))
                    if(auto* constant=static_cast<VeriExp*>(index)->calc_value())value=number(constant);
                if(!value)value=expr(index);
                return value->op=="literal"&&!value->unknown&&!value->host_overflow&&!value->negative&&value->value==wanted;
            };
            const bool single=scalar->rtype()==vrSINGLE;
            const bool range=scalar->rtype()==vrSEMI;
            const bool indexed=scalar->rtype()==vrRAN_ADD||scalar->rtype()==vrRAN_SUB;
            if((!single&&!range&&!indexed)||!known(scalar->left(),0)||(!single&&!known(scalar->right(),indexed?1:0)))
                fail(n,"scalar select requires constant zero bounds and width one");
            ++selection_dimensions;
        }
        if(var->range_depth()) {
            memory=sc->memories.at(var->name());
            const auto& m=memories[size_t(memory)];
            const size_t depth=m.dimensions.size();
            if(a->range().size()<depth||a->range().size()>selection_dimensions)
                fail(n,"memory reference requires all unpacked element indices and an optional packed select");
            std::vector<E> indices;
            for(auto it=a->range().begin();indices.size()<depth;++it) {
                auto* word=static_cast<VeriRangeExp*>(*it);
                if(word->rtype()!=vrSINGLE)fail(n,"unpacked array slices are not supported yet");
                auto* index=word->left();E value;
                if(index->tok_type()==vtEXP&&elaboration_expression(index)&&static_cast<VeriExp*>(index)->calc_value())value=number(static_cast<VeriExp*>(index)->calc_value());
                else value=expr(index);
                if(value->width>64)needs_wide=true;
                indices.push_back(value);
            }
            if(depth==1) {
                word_index=indices.front();
                if(associative_signals.count(m.words.front()))word_index=associative_index(n,var.node,word_index);
                else if(word_index->object_type!=-1)fail(n,"array index requires an integral value, not an object handle");
                else if(word_index->text_value) {
                    if(word_index->packed_value)word_index=word_index->packed_value;
                    else fail(n,"string index requires a string-key associative array");
                }
            } else {
                word_index=node("memory_index",64,indices);
                for(size_t d=0;d<depth;++d) {
                    const auto& dim=m.dimensions[d];const auto suffix=std::to_string(d);
                    word_index->literal+="auto memory_part"+suffix+"=indexed_part(0,"+std::to_string(dim.count)+",memory_index"+suffix+","+std::to_string(dim.base)+",1,false,0);";
                    word_index->literal+="if(!memory_part"+suffix+".width)return V::x(64);memory_offset+=uint64_t(memory_part"+suffix+".lo)*"+std::to_string(dim.stride)+"ull;";
                }
                bool constant=true;uint64_t offset=0;
                for(size_t d=0;d<depth;++d) {
                    const auto& index=indices[d];const auto& dim=m.dimensions[d];
                    if(index->op!="literal"||index->unknown||index->host_overflow||index->negative||index->value<uint64_t(dim.base)||index->value-uint64_t(dim.base)>=uint64_t(dim.count)){constant=false;break;}
                    offset+=(index->value-uint64_t(dim.base))*uint64_t(dim.stride);
                }
                if(constant){word_index=node("literal",64);word_index->value=offset;word_index->literal="V("+std::to_string(offset)+"ull,0,64)";}
            }
            if(m.fixed_count&&depth==1) {
                auto offset=node("memory_index",64,{word_index});
                offset->literal="auto memory_part=indexed_part(0,"+std::to_string(m.fixed_count)+",memory_index0,"+std::to_string(m.base)+",1,false,0);if(!memory_part.width)return V::x(64);memory_offset=memory_part.lo;";
                word_index=offset;
            }
            id=m.words.front();
            if(!m.dynamic&&word_index->op=="literal"&&!word_index->unknown&&!word_index->host_overflow&&!word_index->negative&&
               word_index->value>=uint64_t(m.base)&&word_index->value-uint64_t(m.base)<m.words.size()) {
                id=m.words[size_t(word_index->value-uint64_t(m.base))];word_index.reset();memory=-1;
            }
            packed_range=depth;
        } else {
            if(a->range().size()>selection_dimensions)fail(n,"too many packed indices");
            id=sc->ids.at(var.name());
        }
        auto finish=[&](PartIR part) {part.word_index=word_index;part.memory=memory;return part;};
        if(a->range().size()==packed_range)return finish({id,0,signals[id].width,0});
        if(shape.dimensions.size()>size_t(var.range_depth()+1))
            return finish(multidimensional_selected(n,id,shape,std::vector<VeriNode*>(std::next(a->range().begin(),packed_range),a->range().end())));
        return finish(packed_selected(n,id,var->dend(),static_cast<VeriRangeExp*>(*std::next(a->range().begin(),packed_range)),0,0,false,var->dstart()<var->dend()));
    }
    E associative_part_read(const PartIR& part) {
        auto value=node("container_method",part.object_width,{part.associative_ref,part.word_index});value->signal=part.signal;
        value->literal="return s."+std::string(part.associative_queue?"associative_queue_read":"associative_read")+"(container_arg0,container_arg1,"+std::to_string(part.object_width)+","+(part.object_two_state?"true":"false")+(part.associative_queue?","+std::string(part.object_text?"true":"false"):std::string())+");";value->text_value=part.object_text;
        value->reads.insert(part.signal);value->direct_reads.insert(part.signal);value->object_type=part.field_class;value->enum_id=part.field_enum;
        if(part.index){value=node("indexed_slice",part.width,{value,part.index});value->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");}
        else if(part.lo||part.width!=part.object_width){value=node("slice",part.width,{value});value->literal=std::to_string(part.lo)+","+std::to_string(part.width);}
        return value;
    }
    E selected_read(VeriArrayExp* a,Variable var,const PartIR& part) {
        if(part.associative_ref){auto value=associative_part_read(part);value->signed_value=var.is_signed()==IS_TRUE;return value;}
        auto convert=[&](E value){if(class_type(var.node)!=-1||!signals[part.signal].two_state)return value;auto e=node("two_state",value->width,{value});e->signed_value=value->signed_value;return e;};
        E source=signal_expr(part.signal);
        if(part.word_index) {
            source=memories[size_t(part.memory)].dynamic?dynamic_read_expr(part.signal,part.word_index):node("memory",signals[part.signal].width,{part.word_index});
            if(!memories[size_t(part.memory)].dynamic)source->text_value=signals[part.signal].text_value;
            if(!memories[size_t(part.memory)].dynamic)source->literal=memory_table(part.memory);
            for(int id:memories[size_t(part.memory)].words){source->reads.insert(id);source->direct_reads.insert(id);}
        }
        if(part.index) {
            auto e=node("indexed_slice",part.width,{source,part.index});
            e->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");
            if(part.width>64)needs_wide=true;
            return convert(e);
        }
        if(var.range_depth()&&a->range().size()==size_t(var.range_depth())) {
            source->real_width=var.real_width();source->signed_value=var.is_signed()==IS_TRUE;
            auto e=convert(source);e->enum_id=enum_identity(a);e->object_type=class_type(a);return e;
        }
        E e=node("slice",part.width,{source});
        e->literal=std::to_string(part.lo)+","+std::to_string(part.width);return convert(e);
    }
    PartIR multidimensional_selected(VeriNode* n,int id,const VeriArrayShape& shape,const std::vector<VeriNode*>& ranges) {
        std::vector<std::pair<int,int>> dimensions(shape.dimensions.begin()+shape.unpacked,shape.dimensions.end());
        if(ranges.empty()||ranges.size()>dimensions.size())fail(n,"too many packed indices");
        auto select_value=[&](VeriNode* value) {
            if(value->tok_type()==vtEXP&&elaboration_expression(value))if(auto* constant=static_cast<VeriExp*>(value)->calc_value())return number(constant);
            return expr(value);
        };
        std::vector<E> indices;std::string code;
        bool constant=true;int fixed_offset=0,result_width=0;
        for(size_t d=0;d<ranges.size();++d) {
            auto* range=static_cast<VeriRangeExp*>(ranges[d]);
            const auto first=dimensions[d].first,last=dimensions[d].second;
            const bool descending=first>=last;
            const int count=int(std::abs(int64_t(first)-last)+1),base=std::min(first,last);
            int stride=1;for(size_t k=d+1;k<dimensions.size();++k)stride*=int(std::abs(int64_t(dimensions[k].first)-dimensions[k].second)+1);
            int selected_count=1;bool down=false;E index=select_value(range->left());
            if(range->rtype()!=vrSINGLE) {
                if(d+1!=ranges.size())fail(n,"a packed part-select must be the last subscript");
                auto right=select_value(range->right());
                if(range->rtype()==vrSEMI) {
                    if(index->op!="literal"||right->op!="literal"||index->unknown||right->unknown||index->host_overflow||right->host_overflow)
                        fail(n,"ordinary packed part-select bounds must be constant");
                    auto signed_value=[](E v)->int64_t {return v->negative&&v->width<64?int64_t(v->value|(~uint64_t(0)<<v->width)):int64_t(v->value);};
                    const auto left=signed_value(index),end=signed_value(right);
                    if((descending&&left<end)||(!descending&&left>end))fail(n,"packed part-select direction differs from its declaration");
                    if(std::abs(left-end)+1>1048576)fail(n,"packed part-select exceeds 1048576 elements");
                    selected_count=int(std::abs(left-end)+1);index=descending?right:index;
                } else if(range->rtype()==vrRAN_ADD||range->rtype()==vrRAN_SUB) {
                    if(right->op!="literal"||right->unknown||right->host_overflow||right->negative||!right->value||right->value>1048576)
                        fail(n,"indexed part-select width must be a positive constant <=1048576");
                    selected_count=int(right->value);down=range->rtype()==vrRAN_SUB;
                } else fail(n,"unsupported packed select");
            }
            if(int64_t(selected_count)*stride>1048576)fail(n,"packed selection exceeds 1048576 bits");
            result_width=selected_count*stride;indices.push_back(index);
            if(index->width>64)needs_wide=true;
            const auto suffix=std::to_string(d),part="packed_dim"+suffix;
            code+="auto "+part+"=packed_dimension("+std::to_string(count)+",memory_index"+suffix+","+std::to_string(base)+","+std::to_string(selected_count)+","+(down?"true":"false")+","+(index->signed_value?"true":"false")+");";
            code+="if(!"+part+".width)return V::x(64);";
            code+="memory_offset+=("+(descending?part+".lo":std::to_string(count)+"-"+part+".lo-"+part+".width")+")*"+std::to_string(stride)+";";
            if(index->op!="literal"||index->unknown||index->host_overflow)constant=false;
            else {
                const auto number=index->negative&&index->width<64?int64_t(index->value|(~uint64_t(0)<<index->width)):int64_t(index->value);
                const auto low=number-base-(down?selected_count-1:0);
                if(low<0||low>int64_t(count)-selected_count)constant=false;
                else fixed_offset+=int(descending?low:count-low-selected_count)*stride;
            }
        }
        if(constant)return {id,fixed_offset,result_width,0};
        needs_indexed_select=true;
        PartIR result{id,0,result_width,0};result.index=node("memory_index",64,std::move(indices));result.index->literal=std::move(code);return result;
    }
    PartIR packed_selected(VeriNode* n,int id,int base,VeriRangeExp* r,int view_width=0,int view_lo=0,bool read_outside=false,bool ascending=false) {
        const int total=view_width?view_width:signals[id].width;
        auto select_expr=[&](VeriNode* value) {
            if(value->tok_type()==vtEXP&&elaboration_expression(value))if(auto* constant=static_cast<VeriExp*>(value)->calc_value())return number(constant);
            return expr(value);
        };
        auto integer=[](E value,int64_t& result) {
            if(value->op!="literal"||value->unknown||value->host_overflow)return false;
            if(value->negative)result=int64_t(value->width<64?value->value|(~uint64_t(0)<<value->width):value->value);
            else {if(value->value>uint64_t(INT64_MAX))return false;result=int64_t(value->value);}
            return true;
        };
        auto part_at=[&](E index,int width,bool down) {
            int64_t value;
            if(integer(index,value)&&value>=INT32_MIN&&value<=INT32_MAX) {
                const auto lo=ascending?int64_t(base)-value-(down?0:width-1):value-base-(down?width-1:0);
                if(lo>=0&&lo<=int64_t(total)-width)return PartIR{id,int(lo)+view_lo,width,0};
            }
            needs_indexed_select=true;
            if(ascending) {
                // Validate the original full-width index before mirroring. This
                // preserves X/Z, signed clipping and huge-index rejection, and
                // evaluates a side-effecting subscript exactly once.
                auto reverse=node("reverse_index",64,{index});reverse->signed_value=true;
                reverse->value=uint64_t(int64_t(base));
                reverse->literal=std::to_string(total)+",packed_index,"+std::to_string(int64_t(base)-total+1)+","+std::to_string(width)+","+(down?"true":"false")+",0";
                index=reverse;down=!down;
            }
            PartIR part{id,0,width,0,index,ascending?0:base,down};part.view_lo=view_lo;part.view_width=view_width;return part;
        };
        if(r->rtype()==vrSINGLE||r->rtype()==vrRAN_ADD||r->rtype()==vrRAN_SUB) {
            int width=1;
            if(r->rtype()!=vrSINGLE) {
                auto count=select_expr(r->right());
                if(count->op!="literal"||count->unknown||count->host_overflow||count->negative||!count->value||count->value>1048576)
                    fail(n,"indexed part-select width must be a positive constant <=1048576");
                width=int(count->value);
            }
            return part_at(select_expr(r->left()),width,r->rtype()==vrRAN_SUB);
        }
        if(r->rtype()!=vrSEMI)fail(n,"only constant ranges or fixed-width indexed part selects are supported");
        auto left=select_expr(r->left()),right=select_expr(r->right());int64_t first,last;
        if(!integer(left,first)||!integer(right,last)||first<INT32_MIN||first>INT32_MAX||last<INT32_MIN||last>INT32_MAX)
            fail(n,"ordinary part-select bounds must be constant integers within the 32-bit index range");
        if((ascending&&first>last)||(!ascending&&first<last))fail(n,"packed part-select direction differs from its declaration");
        const auto width=std::abs(first-last)+1;
        if(width>1048576)fail(n,"part-select width must be <=1048576");
        const int64_t low=ascending?int64_t(base)-total+1:base,high=ascending?base:int64_t(base)+total-1;
        if((std::min(first,last)<low||std::max(first,last)>high)&&!read_outside)fail(n,"invalid or out-of-range select");
        // The right endpoint always names the least significant selected bit.
        return part_at(ascending?left:right,int(width),false);
    }
    void lvalue_parts(VeriNode* n,LValueIR& result) {
        if(n->detail_type()==veEXP_MULTI) {
            auto* multi=static_cast<VeriMultiExp*>(n);
            if(multi->multi_type()!=vemCONCAT_EXP || multi->exp().empty()) fail(n,"assignment target must be a signal or concatenation");
            for(auto it=multi->exp().rbegin();it!=multi->exp().rend();++it) lvalue_parts(*it,result);
            return;
        }
        PartIR part=storage_part(n);
        if(foreach_indices.count(part.signal))fail(n,"foreach index is read-only");
        if(result.width>1048576-part.width) fail(n,"assignment target width exceeds supported range 1..1048576");
        if(result.width+part.width>64)needs_wide=true;
        part.rhs_lo=result.width; result.width+=part.width; result.parts.push_back(part);
    }
    void stream_target_parts(VeriNode* n,LValueIR& result) {
        if(n->detail_type()==veEXP_MULTI) {
            auto* list=static_cast<VeriMultiExp*>(n);
            if(list->multi_type()!=vemCONCAT_EXP)fail(n,"stream target requires a storage list");
            for(auto it=list->exp().rbegin();it!=list->exp().rend();++it)stream_target_parts(*it,result);
        } else if(unpacked_value(n)) {
            auto view=array_copy_view(n);
            if(view.offset)fail(n,"stream target requires static array indices");
            for(auto it=view.words.rbegin();it!=view.words.rend();++it) {
                if(enum_identity(n))fail(n,"stream target enum elements are not supported yet");
                const int bits=signals[*it].width;
                if(result.width>1048576-bits)fail(n,"stream target exceeds supported width");
                result.parts.push_back({*it,0,bits,result.width});result.width+=bits;
            }
        } else {
            if(veri_streaming(n))fail(n,"nested streaming targets are not supported yet");
            if(enum_identity(n))fail(n,"stream target enum elements are not supported yet");
            lvalue_parts(n,result);
        }
        if(result.width>64)needs_wide=true;
    }
    LValueIR lvalue(VeriNode* n) {
        LValueIR result;
        if(veri_streaming(n)) {
            stream_target_parts(static_cast<VeriBinaryExp*>(n)->rval(),result);
            for(const auto& part:result.parts)if(part.index||part.word_index)fail(n,"stream target requires static selects");
        } else lvalue_parts(n,result);
        return result;
    }
    bool net_target(const LValueIR& value) {
        for(auto part:value.parts) if(!signals[part.signal].net) return false;
        return true;
    }
    E number(VeriNum* n) {
        if(n->string_type()) {
            needs_text=true;auto e=node("text_literal",std::max(1,n->bits()));
            e->text_value=e->constant_text=true;e->literal=quote(n->string_value());return e;
        }
        if(n->real_width()) {
            needs_real=true;auto e=node("literal",n->real_width());e->real_width=n->real_width();e->signed_value=true;
            uint64_t bits=uint64_t(n->val()[0]);if(n->real_width()==64)bits|=uint64_t(n->val()[1])<<32;
            e->literal="real_from_bits(V("+std::to_string(bits)+"ull,0,"+std::to_string(n->real_width())+"),"+std::to_string(n->real_width())+")";return e;
        }
        if(n->bits()<1 || n->bits()>1048576) fail(n,"constant width must be 1..1048576");
        std::vector<std::pair<uint64_t,uint64_t>> words(size_t((n->bits()+63)/64));
        bool unknown=false,high=false;
        for(int i=0;i<n->bits();++i) {
            int bit=n->get_certain_bit(i);auto& word=words[size_t(i/64)];auto selected=uint64_t(1)<<(i%64);
            if(bit==1||bit==VX) word.first|=selected;
            if(bit==VX||bit==VZ) {word.second|=selected;unknown=true;}
            if(i>=64&&bit!=0)high=true;
        }
        E e=node("literal",n->bits());e->canonical_literal=true;e->signed_value=n->is_signed()==IS_TRUE;e->negative=e->signed_value&&n->get_certain_bit(n->bits()-1)==1;e->value=words[0].first;e->unknown=unknown?1:0;
        if(n->bits()<=64)e->literal="V("+std::to_string(words[0].first)+"ULL,"+std::to_string(words[0].second)+"ULL,"+std::to_string(n->bits())+")";
        else {
            needs_wide=true;e->literal="V::from_words({";
            for(const auto& word:words)e->literal+="{"+std::to_string(word.first)+"ULL,"+std::to_string(word.second)+"ULL},";
            e->literal+="},"+std::to_string(n->bits())+")";
        }
        // Constant-only host-time APIs must not silently read just the low limb.
        e->host_overflow=high;
        return e;
    }
    unsigned enum_identity(VeriNode* n) const {
        auto* type=veri_enum_type(n);return type?type->idx()+1:0;
    }
    int class_identity(VeriSeqBlock* type) const {
        if(!type)return -1;
        const int id=int(type->idx());class_types.emplace(id,type);return id;
    }
    std::string class_type_name(int id) const {
        if(id==-1)return "integral/string value";
        if(id==-2)return "null";
        if(id==opaque_handle_type)return "chandle";
        auto found=class_types.find(id);
        if(found==class_types.end())return "class #"+std::to_string(id);
        try{return found->second->type_name();}catch(const std::runtime_error&){return found->second->label();}
    }
    // A method binding can create a type before a runtime layout is needed.
    // Assignment compatibility follows that semantic type's inheritance graph;
    // allocation and initialization still require explicit layout registration.
    bool class_compatible(int actual,int expected) const {
        if(actual==expected||actual==-2)return true;
        auto found=class_types.find(actual);
        if(found!=class_types.end())for(auto* base=found->second->base_class();base;base=base->base_class())
            if(int(base->idx())==expected)return true;
        return false;
    }
    void enum_assignment(VeriNode* lhs,E value) {
        auto expected_interface=veri_virtual_interface(lhs);
        if(expected_interface) {
            if(value->object_type!=-2&&!interface_compatible(value->interface_type,expected_interface))fail(lhs,"virtual interface assignment requires a compatible interface type and modport or null (expected "+expected_interface->name+"."+expected_interface->view+", actual "+(value->interface_type?value->interface_type->name+"."+value->interface_type->view:"non-interface")+")");
            return;
        }
        if(value->interface_type)fail(lhs,"virtual interface handle cannot be assigned to an integral or class variable");
        const int expected_class=class_type(lhs);
        if(expected_class!=-1) {
            if(!class_compatible(value->object_type,expected_class)) {
                if(expected_class==opaque_handle_type)fail(lhs,"chandle assignment requires a chandle or null");
                fail(lhs,"class assignment requires a compatible object handle or null: "+class_type_name(value->object_type)+" -> "+class_type_name(expected_class));
            }
        } else if(value->object_type!=-1)fail(lhs,"class handle cannot be assigned to an integral or string variable");
        unsigned expected=enum_identity(lhs);
        if(expected&&expected!=value->enum_id)fail(lhs,"enum assignment requires the same enum type or an explicit enum cast");
    }
    int class_type(VeriNode* n) const {if(veri_chandle_value(n))return opaque_handle_type;return class_identity(veri_class_type(n));}
    E implicit_this(VeriNode* source) {
        if(argument_receiver)return argument_receiver;
        for(auto* frame=scope;frame;frame=frame->parent) {
            if(frame->static_class_method)break;
            if(frame->self)return frame->self;
        }
        fail(source,"class instance member requires an object receiver");return {};
    }
    void validate_class_methods(VeriSeqBlock* definition,const std::vector<VeriNode*>& items) {
        const auto same_array_shape=[](Variable a,Variable b) {
            if(a.range_depth()!=b.range_depth()||a.dynamic()!=b.dynamic())return false;
            if(a.dynamic()&&(a.container_kind()!=b.container_kind()||a.container_bound()!=b.container_bound()))return false;
            for(int d=1;d<=a.range_depth();++d){int af,al,an,bf,bl,bn;a.get_range(d,af,al,an);b.get_range(d,bf,bl,bn);if(af!=bf||al!=bl)return false;}
            return true;
        };
        for(auto* method:items) {
            if(method->detail_type()!=vsDECL_FUNC_DECL&&method->detail_type()!=vsDECL_TASK_DECL)continue;
            auto* qualifiers=static_cast<VeriDecl*>(method);
            if(qualifiers->static_method()&&qualifiers->virtual_method())fail(method,"static methods cannot be virtual");
            if(static_cast<VeriDecl*>(method)->pure_virtual()&&!definition->abstract_class())fail(method,"pure virtual methods require a virtual class");
            const bool function=method->detail_type()==vsDECL_FUNC_DECL;
            const auto name=function?static_cast<VeriFuncDecl*>(method)->func_name():static_cast<VeriTaskDecl*>(method)->task_name();
            for(auto* base=definition->base_class();base;base=base->base_class()) {
                auto* symbol=base->scope()->value_same_level(name);if(!symbol)continue;
                VeriNode* ancestor=symbol->tok_type()==vtFUNC?static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):symbol->tok_type()==vtTASK?static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task()):nullptr;
                if(!ancestor||!static_cast<VeriDecl*>(ancestor)->virtual_method())continue;
                if(qualifiers->static_method())fail(method,"static method cannot override a virtual method");
                if(qualifiers->class_access()!=static_cast<VeriDecl*>(ancestor)->class_access())fail(method,"virtual method override access mismatch: "+name);
                auto mismatch=[&](){fail(method,"virtual method override signature mismatch: "+name);};
                if(ancestor->detail_type()!=method->detail_type())mismatch();
                auto actual=veri_subroutine_formals(method),expected=veri_subroutine_formals(ancestor);
                if(actual.size()!=expected.size())mismatch();
                for(size_t i=0;i<actual.size();++i) {
                    auto* a=veri_formal_symbol(actual[i]);auto* b=veri_formal_symbol(expected[i]);Variable av{a},bv{b};
                    if(!a||!b||a->tok_type()!=vtTFVAR||b->tok_type()!=vtTFVAR)mismatch();
                    if(static_cast<VeriTfVar*>(a)->inout()!=static_cast<VeriTfVar*>(b)->inout()||static_cast<VeriTfVar*>(a)->net_type()!=static_cast<VeriTfVar*>(b)->net_type()||av.dlen()!=bv.dlen()||av->is_signed()!=bv->is_signed()||class_type(a)!=class_type(b)||enum_identity(a)!=enum_identity(b)||!same_array_shape(av,bv))mismatch();
                    for(unsigned d=1;d<=unsigned(av.range_depth());++d){int af,al,an,bf,bl,bn;av.get_range(d,af,al,an);bv.get_range(d,bf,bl,bn);if(af!=bf||al!=bl||an!=bn)mismatch();}
                }
                if(function) {
                    auto* a=static_cast<VeriFuncDecl*>(method);auto* b=static_cast<VeriFuncDecl*>(ancestor);
                    if(a->is_void()!=b->is_void())mismatch();
                    if(!a->is_void()) {
                        Variable av{definition->scope()->value_same_level(name)},bv{base->scope()->value_same_level(name)};
                        if(!same_array_shape(av,bv))mismatch();
                        if((av.range_depth()||bv.range_depth())&&!equivalent_elements(av,bv))mismatch();
                        const int ac=class_type(definition->scope()->value_same_level(name)),bc=class_type(base->scope()->value_same_level(name));
                        if(ac>=0||bc>=0){if(ac<0||bc<0||!class_compatible(ac,bc))mismatch();}
                        else if(a->result_type()!=b->result_type()||a->is_signed()!=b->is_signed()||Variable{definition->scope()->value_same_level(name)}.dlen()!=Variable{base->scope()->value_same_level(name)}.dlen())mismatch();
                    }
                }
            }
        }
        if(!definition->abstract_class()) {
            std::set<std::string> selected;
            for(auto* base=definition;base;base=base->base_class()) {
                std::vector<VeriNode*> declarations;
                if(base->decl_list())for(auto* item:static_cast<VeriModuleItemList*>(base->decl_list())->item_list())declarations.push_back(item);
                for(auto* method:declarations) {
                    if(method->detail_type()!=vsDECL_FUNC_DECL&&method->detail_type()!=vsDECL_TASK_DECL)continue;
                    const auto name=method->detail_type()==vsDECL_FUNC_DECL?static_cast<VeriFuncDecl*>(method)->func_name():static_cast<VeriTaskDecl*>(method)->task_name();
                    if(selected.insert(name).second&&static_cast<VeriDecl*>(method)->pure_virtual())fail(definition,"nonvirtual class must implement pure virtual method: "+name);
                }
            }
        }
    }
    #include "rtl_coverage.inc"
    void register_class(VeriSeqBlock* definition) {
        if(definition->generic_class()) {for(const auto& type:definition->specializations())register_class(type.second);return;}
        if(classes.count(definition))return;
        auto* enclosing=scope;
        if(definition->base_class())register_class(definition->base_class());
        auto* lexical=generated_scope(scope,"$class$"+definition->label());lexical->procedural=true;lexical->class_definition=definition;
        auto [where,inserted]=classes.emplace(definition,ClassIR{class_identity(definition),lexical,{}});auto& type=where->second;
        if(objects_signal<0){objects_signal=int(signals.size());signals.push_back({"$dsim_object_heap",64,0,false,true});}
        // Base fields keep stable prefix offsets even when a derived property shadows a name.
        if(definition->base_class())type.fields=classes.at(definition->base_class()).fields;
        append_items(lexical,definition->decl_list());
        validate_class_methods(definition,lexical->items);
        for(auto* item:lexical->items) {
            if(item->detail_type()==vsDECL_FUNC_DECL) {
                auto* method=static_cast<VeriFuncDecl*>(item);const auto& name=method->func_name();
                if(name=="randomize"||name=="srandom"||name=="rand_mode"||name=="constraint_mode")fail(item,"built-in randomization methods cannot be redeclared");
                if(name=="pre_randomize"||name=="post_randomize") {
                    if(method->virtual_method()||method->static_method()||!method->is_void()||!veri_subroutine_formals(method).empty())fail(item,"randomization callback requires a nonvirtual nonstatic void function without arguments");
                }
            }
            if(item->detail_type()==vsDECL_FUNC_DECL||item->detail_type()==vsDECL_TASK_DECL||item->detail_type()==vsDECL_IMPORT)continue;
            if(item->detail_type()==vsDECL_CONSTRAINT||item->detail_type()==vsDECL_COVERAGE||item->detail_type()==vsDECL_PARAM)continue;
            if(item->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(item)->class_declaration()) {scope=lexical;register_class(static_cast<VeriSeqBlock*>(item));scope=enclosing;continue;}
            const bool integer=item->detail_type()==vsDECL_INT;
            if(!integer&&item->detail_type()!=vsDECL_VAR)fail(item,"unsupported class declaration item");
            auto* declaration=integer?nullptr:static_cast<VeriVarDecl*>(item);
            if(declaration&&declaration->is_typedef())continue;
            if(declaration&&(declaration->inout()!=vpNO_IO||declaration->net_type()==vvWIRE||declaration->net_type()==vvTRI))fail(item,"class property requires variable storage");
            if(static_cast<VeriDecl*>(item)->explicit_automatic())fail(item,"class properties cannot have automatic lifetime");
            if(static_cast<VeriDecl*>(item)->rand_property()&&static_cast<VeriDecl*>(item)->const_property())fail(item,"const rand properties are not supported yet");
            if(static_cast<VeriDecl*>(item)->rand_property()&&static_cast<VeriDecl*>(item)->explicit_static())fail(item,"static rand properties are not supported yet");
            if(static_cast<VeriDecl*>(item)->explicit_static()) {
                scope=lexical;declarations(item);scope=enclosing;
                for(const auto& symbol:lexical->symbols)class_statics.emplace(symbol.second,lexical);
                continue;
            }
            auto& variables=integer?static_cast<VeriIntDecl*>(item)->vars():declaration->vars();
            for(auto* entry:variables) {
                auto* lhs=entry->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(entry)->lval():entry;
                auto* symbol=veri_formal_symbol(lhs);if(!variable(symbol))fail(lhs,"unresolved class property");
                if(struct_has_strings(veri_aggregate_type(symbol)))needs_text=needs_struct_strings=true;
                Variable property{symbol};if(property.real_width())needs_real=true;
                if(veri_chandle_value(symbol)&&property.range_depth())fail(symbol,"chandle unpacked class properties are not supported yet");
                if(static_cast<VeriDecl*>(item)->rand_property()&&((property.range_depth()&&(property.range_depth()!=1||(property.container_kind()!=vrOPEN&&property.container_kind()!=vrQUEUE)||static_cast<VeriDecl*>(item)->randc_property()))||property.real_width()||veri_string_value(symbol)||(class_type(symbol)!=-1&&!(class_type(symbol)>=0&&!static_cast<VeriDecl*>(item)->randc_property()))))fail(lhs,"rand property requires a scalar integral value or one integral dynamic/queue dimension or class-handle storage (randc arrays unsupported)");
                if(static_cast<VeriDecl*>(item)->const_property())const_properties.insert(symbol);
                if(property.range_depth()) {
                    if(const_properties.count(symbol))fail(lhs,"const array class properties are not supported yet");
                    if((property.range_depth()!=1&&!associative_kind(property.container_kind()))||(!associative_kind(property.container_kind())&&property.container_kind()!=vrQUEUE&&property.container_kind()!=vrOPEN))fail(lhs,"unpacked class properties currently require associative, queue or dynamic storage");
                    if(property.container_kind()==vrOPEN&&property.real_width())fail(lhs,"dynamic class arrays of real elements are not supported yet");
                    if(auto* aggregate=veri_aggregate_type(symbol);aggregate&&aggregate->unpacked_struct()&&associative_queue_type(symbol))fail(lhs,"associative queues of structs are not supported yet");
                    if(property.container_kind()==vrQUEUE||property.container_kind()==vrOPEN||associative_queue_type(symbol))object_queue_storage=true;
                    if(associative_kind(property.container_kind()))object_associative_storage=true;
                    for(int axis=0;axis<property.range_depth();++axis)if(veri_array_container_kind(symbol,axis)==vrASSOC_STRING)needs_text=true;
                }
                if(declaration&&declaration->net_type()==vvEVENT) {
                    if(property.range_depth()||declaration->range()||entry->detail_type()==veEXP_ASSIGN||declaration->rand_property()||declaration->const_property())
                        fail(lhs,"instance event arrays, aliases/initializers and const/rand qualifiers are not supported yet");
                    needs_named_events=true;
                }
                if(property.dlen()>64)needs_wide=true;
                if(veri_string_value(symbol))needs_text=true;
                object_fields.emplace(symbol,std::make_pair(definition,int(type.fields.size())));
                type.fields.push_back({symbol,entry->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(entry)->rval():nullptr});
            }
        }
        for(size_t field=0;field<type.fields.size();++field) {
            auto* aggregate=veri_aggregate_type(type.fields[field].symbol);
            if(aggregate&&aggregate->unpacked_struct())object_aggregate_types[{type.id,int(field)}]=aggregate_components(aggregate);
        }
        scope=enclosing;
    }
    PartIR object_part(VeriNode* symbol,E receiver) {
        auto found=object_fields.find(symbol);if(found==object_fields.end())fail(symbol,"unresolved class property layout");
        const auto& type=classes.at(found->second.first);
                Variable property{symbol};if(property.real_width())needs_real=true;
        PartIR part{objects_signal,0,property.dlen(),0};part.object=std::move(receiver);part.object_type=type.id;part.object_field=found->second.second;
        part.object_real=property.real_width();part.object_width=property.dlen();part.object_two_state=property.two_state();part.object_text=veri_string_value(symbol);part.field_class=class_type(symbol);part.field_enum=enum_identity(symbol);
        part.object_const=const_properties.count(symbol);part.object_const_initialized=type.fields.at(size_t(part.object_field)).initializer!=nullptr;return part;
    }
    E object_read(const PartIR& part) {
        if(part.associative_ref)return associative_part_read(part);
        E value;
        if(part.object_queue) {
            value=node("container_method",part.object_width,{part.object,part.word_index});value->signal=objects_signal;
            value->literal="return s.object_queue_read(s.object_queue(container_arg0,"+std::to_string(part.object_type)+","+std::to_string(part.object_field)+",@object),container_arg1,"+std::to_string(part.object_width)+","+(part.object_two_state?"true":"false")+","+(part.object_text?"true":"false")+");";
        } else if(part.object_associative) {
            value=node("container_method",part.object_width,{part.object,part.word_index});value->signal=objects_signal;
            value->real_width=part.object_real;value->literal="return s.associative_read(s.object_associative(container_arg0,"+std::to_string(part.object_type)+","+std::to_string(part.object_field)+","+std::to_string(part.object_width)+",@object,"+(part.object_unsigned_key?"true":"false")+","+(part.object_class_key?"true":"false")+"),container_arg1,"+std::to_string(part.object_width)+","+(part.object_two_state?"true":"false")+");";
        } else {value=node("object_read",part.object_width,{part.object});value->literal=std::to_string(part.object_type)+","+std::to_string(part.object_field);}
        value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);value->real_width=part.object_real;value->text_value=part.object_text;value->object_type=part.field_class;value->enum_id=part.field_enum;
        if(part.index||part.lo||part.width!=part.object_width) {
            if(part.index) {value=node("indexed_slice",part.width,{value,part.index});value->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");}
            else {value=node("slice",part.width,{value});value->literal=std::to_string(part.lo)+","+std::to_string(part.width);}
            if(part.object_two_state)value=node("two_state",part.width,{value});
        }
        return value;
    }
    void register_ipc_type(VeriNode* n) {
        if(auto* type=veri_class_type(n);type&&type->process_type()){register_class(type);needs_process_handles=needs_random=true;}

        if(auto* type=veri_class_type(n);type&&type->ipc_kind()){register_class(type);needs_ipc=true;}
    }
    std::string ipc_signature(VeriNode* n) {
        if(veri_array_shape(n).unpacked)fail(n,"mailbox message must be singular");
        if(veri_chandle_value(n))fail(n,"mailbox chandle payloads are not supported yet");
        if(auto* c=veri_class_type(n))return "class:"+std::to_string(c->idx());
        if(veri_dynamic_string_value(n))return "string";
        if(int width=veri_real_width(n))return "real:"+std::to_string(width);
        if(veri_aggregate_type(n))fail(n,"mailbox aggregate message types are not supported yet");
        if(enum_identity(n))return "enum:"+std::to_string(enum_identity(n));
        auto* symbol=veri_array_element_symbol(n);if(!symbol&&(variable(n)||n->tok_type()==vtTYPE))symbol=n;
        const int width=veri_bit_width(n);
        if(variable(symbol)||(symbol&&symbol->tok_type()==vtTYPE)) {
            Variable type{symbol};
            const bool packed_select=n->detail_type()==veEXP_ARRAY&&static_cast<VeriArrayExp*>(n)->range().size()>size_t(type.range_depth());
            return "integral:"+std::to_string(width)+":"+std::to_string(!packed_select&&type.is_signed()==IS_TRUE)+":"+
                std::to_string(type.two_state());
        }
        if(n->detail_type()==veEXP_PRI) {
            auto* primary=static_cast<VeriPrimaryExp*>(n);
            if(primary->pri_type()==veNUM) {
                // Unsized decimal literals have the language's integer type.
                const auto& spelling=primary->str();const bool unsized=spelling.find('\'')==std::string::npos;
                return "integral:"+std::to_string(width)+":"+std::to_string(primary->calc_value()?primary->calc_value()->is_signed()==IS_TRUE:primary->is_signed()==IS_TRUE)+":"+
                    std::to_string(unsized);
            }
        }
        fail(n,"dynamic mailbox expression type is not supported yet; use a typed mailbox or a variable");return {};
    }
    E ipc_input(VeriMemberExp* member,VeriNode* actual) {
        auto* type=member->class_owner();auto* payload=type->ipc_payload();
        if(type->ipc_kind()==2) {
            auto value=actual?expr(actual):node("literal",32);if(!actual)value->literal="V(1,0,32)";
            if(value->text_value||value->real_width||value->object_type!=-1)fail(member,"semaphore count requires an integral value");
            auto converted=node("fixed_cast",32,{value});converted->signed_value=true;return converted;
        }
        if(!payload){auto value=expr(actual);if(!veri_dynamic_string_value(actual)&&value->packed_value)value=value->packed_value;return value;}
        auto value=context_expr(actual,payload);enum_assignment(payload,value);
        if(class_type(payload)>=0) {
            if(value->object_type!=-2&&(value->object_type<0||!class_compatible(value->object_type,class_type(payload))))fail(actual,"mailbox input class type mismatch");
        } else if(value->object_type!=-1)fail(actual,"mailbox input type mismatch");
        if(!veri_string_value(payload)&&!veri_real_width(payload)) {
            auto converted=node("argument",veri_bit_width(payload),{value});converted->signed_value=value->signed_value;
            value=converted;
            if(Variable{payload}.two_state()){needs_two_state_cast=true;value=node("two_state",value->width,{value});}
        }
        value->object_type=class_type(payload);return value;
    }
    LValueIR ipc_target(VeriMemberExp* member,VeriNode* actual) {
        auto target=lvalue(actual);
        if(target.parts.size()!=1)fail(actual,"mailbox ref destination requires one variable");
        auto& part=target.parts.front();
        if(signals[part.signal].net)fail(actual,"mailbox ref destination requires a variable");
        // Ref binds a complete singular variable. Dynamic elements need an
        // additional lifetime/generation binding and are rejected explicitly.
        if(part.index||part.lo||part.width!=((part.object||part.associative_ref)?part.object_width:signals[part.signal].width)||dynamic_signals.count(part.signal)||part.object_associative||part.associative_ref)
            fail(actual,"mailbox ref destination requires a complete scalar or fixed array element");
        if(auto* payload=member->class_owner()->ipc_payload();payload&&ipc_signature(actual)!=ipc_signature(payload))
            fail(actual,"typed mailbox ref requires equivalent message types");
        return target;
    }
    E ipc_payload_value(VeriNode* actual,const std::string& code) {
        auto value=node("saved",veri_dynamic_string_value(actual)?1:veri_real_width(actual)?veri_real_width(actual):veri_bit_width(actual));value->literal=code;
        value->text_value=veri_dynamic_string_value(actual);value->real_width=veri_real_width(actual);
        value->signed_value=static_cast<VeriExp*>(actual)->is_signed()==IS_TRUE;value->object_type=class_type(actual);value->enum_id=enum_identity(actual);return value;
    }
    E process_expression(VeriMemberExp* member,bool statement=false) {
        auto* type=member->class_owner();register_class(type);needs_process_handles=needs_random=true;
        const auto& method=member->member();
        if(method!="self"&&method!="get_randstate"&&method!="set_randstate"&&method!="srandom"&&method!="status"&&method!="kill")
            fail(member,"process control method is not supported yet: "+method);
        if(method=="status"||method=="kill")needs_process_lifetime=needs_process_control=needs_explicit_automatic=true;
        const bool random_setter=method=="srandom"||method=="set_randstate";
        const bool setter=random_setter||method=="kill";
        if(setter&&!statement)fail(member,"process setter is a void method: "+method);
        std::vector<E> args;
        if(!member->scope_reference())args.push_back(expr(member->object()));
        const auto type_id=std::to_string(classes.at(type).id);
        auto actuals=veri_system_arguments(member->arguments());
        if(random_setter) {
            auto arg=expr(actuals.front());
            if(method=="srandom") {
                if(arg->packed_value)arg=arg->packed_value;
                if(arg->text_value||arg->real_width||arg->object_type!=-1)fail(member,"process seed requires an integral value");
                arg=node("fixed_cast",32,{arg});
            } else {
                needs_text=true;
                if(arg->real_width||arg->object_type!=-1)fail(member,"process random state requires a string-compatible value");
                arg=text_context(arg);
            }
            args.push_back(arg);
        }
        // Compose all actuals before adding native effects, preserving receiver
        // and argument side effects/dependencies for partitioning and replay.
        auto value=node("call",method=="self"?64:32,std::move(args));
        value->reads.insert(objects_signal);
        if(method=="status") {
            value->enum_id=enum_identity(member);value->signed_value=true;
            value->literal="return V(s.process_status(call_arg0,"+type_id+"),0,32);";return value;
        }
        value->procedural_only=true;value->event_safe=false;value->random_state=true;
        value->writes.insert(objects_signal);value->write_ranges.emplace(objects_signal,0,64);
        if(method=="kill"){value->literal="s.process_kill(call_arg0,"+type_id+");return V(0,0,32);";return value;}
        if(method=="self") {value->object_type=type->idx();value->literal="return s.process_self("+type_id+","+sid(objects_signal)+");";return value;}
        if(method=="get_randstate") {needs_text=true;value->text_value=true;value->literal="return s.process_get_randstate(call_arg0,"+type_id+");";}
        else value->literal="s.process_"+method+"(call_arg0,"+type_id+",call_arg1);return V(0,0,32);";
        return value;
    }
    E ipc_expression(VeriMemberExp* member,bool statement=false) {
        register_ipc_type(member->object());auto* type=member->class_owner();const auto& method=member->member();
        const bool mailbox=type->ipc_kind()==1;
        if(method=="get"||method=="peek"||(mailbox&&method=="put"))fail(member,"blocking IPC method requires a task statement");
        if(!mailbox&&method=="put"&&!statement)fail(member,"semaphore put is a void function");
        auto actuals=veri_system_arguments(member->arguments());
        const bool output=mailbox&&(method=="try_get"||method=="try_peek");
        const int operation=method=="num"?3:method=="put"||method=="try_put"?0:method=="try_peek"?2:1;
        ProcessIR effect;auto receiver=expr(member->object());read(effect,receiver);
        std::string code="auto ipc_receiver="+emit(receiver)+";";std::string signature;E input;
        LValueIR target;
        if(output) {
            target=ipc_target(member,actuals.front());signature=ipc_signature(type->ipc_payload()?static_cast<VeriNode*>(type->ipc_payload()):actuals.front());
            unsigned capture=0;
            auto freeze=[&](E& expression){if(!expression)return;read(effect,expression);code+="auto ipc_ref"+std::to_string(capture)+"="+emit(expression)+";";
                auto saved=std::make_shared<Expr>(*expression);saved->op="saved";saved->args.clear();saved->literal="ipc_ref"+std::to_string(capture++);expression=saved;};
            auto& part=target.parts.front();freeze(part.receiver_effect);freeze(part.object);freeze(part.word_index);
        } else if(method!="num") {
            input=ipc_input(member,actuals.empty()?nullptr:actuals.front());read(effect,input);
            if(mailbox)signature=ipc_signature(type->ipc_payload()?static_cast<VeriNode*>(type->ipc_payload()):actuals.front());
        }
        code+="auto ipc_status=s.ipc_try(ipc_receiver,"+std::to_string(type->idx())+","+std::to_string(operation)+","+(input?emit(input):"V()")+","+quote(signature)+");";
        if(output) {
            code+="if(ipc_status.status>0){";write(effect,target,ipc_payload_value(actuals.front(),"ipc_status.value"),false,false);
            for(const auto& instruction:effect.instructions)code+=instruction.code;code+="}";
        }
        auto result=node("call",32);result->literal=code+"return V(uint32_t(ipc_status.status),0,32);";
        result->signed_value=true;result->procedural_only=true;result->event_safe=false;
        result->reads=effect.reads;result->touches=effect.touches;result->nonstatic_writes=effect.nonstatic_writes;result->function_reads=effect.function_reads;
        result->partial_writes=effect.partial_writes;result->whole_writes=effect.whole_writes;result->sensitivity_reads=effect.sensitivity_reads;
        result->io_state=effect.io_state;result->random_state=effect.random_state;result->selection_checks=effect.selection_checks;
        for(const auto& written:effect.writes){result->writes.insert(written.signal);result->write_ranges.emplace(written.signal,written.lo,written.width);}
        result->reads.insert(objects_signal);result->writes.insert(objects_signal);result->write_ranges.emplace(objects_signal,0,64);
        return result;
    }
    void ipc_task(ProcessIR& p,VeriMemberExp* member,int pidx,bool discard) {
        auto* type=member->class_owner();const auto& method=member->member();const bool mailbox=type->ipc_kind()==1;
        const bool blocking=method=="get"||method=="peek"||(mailbox&&method=="put");
        if(!blocking){auto value=ipc_expression(member,true);read(p,value);add(p,"(void)("+emit(value)+");");return;}
        if(discard||p.function||lowering_final||p.always_kind!=akALWAYS)fail(member,"blocking IPC methods require a procedural task context without always_comb/always_latch/always_ff");
        register_ipc_type(member->object());needs_process_control=true;++p.timing_controls;p.event_safe=false;p.side_effect=true;p.selection_only_effects=false;
        auto actuals=veri_system_arguments(member->arguments());auto receiver=expr(member->object());read(p,receiver);
        std::string code="{auto ipc_receiver="+emit(receiver)+";std::vector<V> ipc_refs;";std::string signature;E input;LValueIR target;
        const bool output=mailbox&&method!="put";
        if(output) {
            target=ipc_target(member,actuals.front());signature=ipc_signature(type->ipc_payload()?static_cast<VeriNode*>(type->ipc_payload()):actuals.front());
            unsigned capture=0;
            auto freeze=[&](E& expression){if(!expression)return;read(p,expression);code+="ipc_refs.push_back("+emit(expression)+");";
                auto saved=std::make_shared<Expr>(*expression);saved->op="saved";saved->args.clear();saved->literal="s.ipc_capture("+runtime_pid(pidx)+","+std::to_string(capture++)+")";expression=saved;};
            auto& part=target.parts.front();if(part.receiver_effect){read(p,part.receiver_effect);code+="(void)("+emit(part.receiver_effect)+");";part.receiver_effect={};}
            freeze(part.object);freeze(part.word_index);
        } else {
            input=ipc_input(member,actuals.empty()?nullptr:actuals.front());read(p,input);
            if(mailbox)signature=ipc_signature(type->ipc_payload()?static_cast<VeriNode*>(type->ipc_payload()):actuals.front());
        }
        const int operation=method=="put"?0:method=="peek"?2:1;
        const auto resume=std::to_string(p.instructions.size()+1);
        code+="pc="+resume+";if(s.ipc_wait("+runtime_pid(pidx)+",ipc_receiver,"+std::to_string(type->idx())+","+std::to_string(operation)+","+(input?emit(input):"V()")+","+quote(signature)+",std::move(ipc_refs)))return;continue;}";
        add(p,code);p.reads.insert(objects_signal);p.touches.insert(objects_signal);p.writes.push_back({objects_signal,0,64,0});
        if(output)write(p,target,ipc_payload_value(actuals.front(),"s.ipc_result("+runtime_pid(pidx)+")"),false,false);
        add(p,"s.ipc_finish("+runtime_pid(pidx)+");");
    }
    E object_new(VeriMultiExp* source) {
        auto* definition=source->object_type();if(definition->ipc_kind()){register_class(definition);needs_ipc=true;}auto found=classes.find(definition);if(found==classes.end())fail(source,"class type is not elaborated");
        if(definition->abstract_class())fail(source,"cannot construct a virtual class");
        if(!active_allocations.insert(definition).second)fail(source,"recursive class allocation is not supported yet");
        struct AllocationGuard {std::set<VeriSeqBlock*>& active;VeriSeqBlock* type;~AllocationGuard(){active.erase(type);}} allocation_guard{active_allocations,definition};
        auto& type=found->second;const auto suffix=std::to_string(allocation_sequence++);const auto receiver="new_object"+suffix;
        auto result=node("call",64);result->object_type=type.id;result->procedural_only=true;result->event_safe=false;
        result->argument_prefix="new_arg"+suffix+"_";
        result->reads.insert(objects_signal);result->writes.insert(objects_signal);result->write_ranges.emplace(objects_signal,0,64);
        if(definition->coverage_type()) {
            if(!source->exp().empty())fail(source,"covergroup constructor arguments are not supported yet");
            auto* owner=type.scope->parent;
            if(owner->class_definition)result->args.push_back(implicit_this(source));
            result->literal="return s.coverage_new("+std::to_string(type.id)+","+(result->args.empty()?"V()":result->argument_prefix+"0")+","+sid(objects_signal)+");";return result;
        }
        if(definition->ipc_kind()) {
            if(source->exp().size()>1)fail(source,"IPC constructor accepts at most one argument");
            auto count=source->exp().empty()?node("literal",32):expr(source->exp().front());if(source->exp().empty())count->literal="V(0,0,32)";
            if(count->text_value||count->real_width||count->object_type!=-1)fail(source,"IPC constructor count requires an integral value");
            result->args.push_back(count);result->literal="return s.ipc_new("+std::to_string(type.id)+","+std::to_string(definition->ipc_kind())+","+result->argument_prefix+"0,"+sid(objects_signal)+");";return result;
        }
        result->literal="auto "+receiver+"=s.object_new("+std::to_string(type.id)+",{";
        for(const auto& field:type.fields) {
            Variable property{field.symbol};
            if(property.net_type()==vvEVENT){result->literal+="V(uint64_t(s.named_event("+sid(objects_signal)+"))+1,0,64),";continue;}
            if(auto meta=object_aggregate_types.find({type.id,int(&field-type.fields.data())});meta!=object_aggregate_types.end()&&!property.range_depth()){result->literal+=emit(meta->second.first)+",";continue;}
            result->literal+=property.real_width()?"V::real(0,"+std::to_string(property.real_width())+"),":property.range_depth()?"V(0),":veri_string_value(field.symbol)?"V::text(\"\"),":property.two_state()?"V(0,0,"+std::to_string(property.dlen())+"),":"V::x("+std::to_string(property.dlen())+"),";
        }
        result->literal+="},"+sid(objects_signal)+",{";
        for(auto* base=definition->base_class();base;base=base->base_class())result->literal+=std::to_string(base->idx())+",";
        result->literal+="});";
        {
            auto self=node("literal",64);self->literal=receiver;self->object_type=type.id;
            auto* binding=source->hive()?static_cast<VeriNode*>(source):veri_bind_class_call(source,definition,"new",nullptr);
            auto constructor=function_call(binding,false,self);
            result->argument_alias_prefix=constructor->argument_alias_prefix;
            // SV evaluates actuals before property initializers and constructor
            // execution. Preserve each value once, with names distinct from the
            // constructor's private call_arg locals.
            for(size_t i=1;i<constructor->args.size();++i) {
                auto actual=constructor->args[i];result->args.push_back(actual);
                auto saved_arg=node("saved",actual->width);saved_arg->literal=result->argument_prefix+std::to_string(i-1);
                saved_arg->real_width=actual->real_width;saved_arg->signed_value=actual->signed_value;saved_arg->text_value=actual->text_value;saved_arg->object_type=actual->object_type;constructor->args[i]=saved_arg;
            }
            result->literal+=emit(constructor)+";";
            result->reads.insert(constructor->reads.begin(),constructor->reads.end());result->writes.insert(constructor->writes.begin(),constructor->writes.end());
            result->function_reads.insert(constructor->function_reads.begin(),constructor->function_reads.end());result->partial_writes.insert(constructor->partial_writes.begin(),constructor->partial_writes.end());
            result->nonstatic_writes.insert(constructor->nonstatic_writes.begin(),constructor->nonstatic_writes.end());result->sensitivity_reads.insert(result->sensitivity_reads.end(),constructor->sensitivity_reads.begin(),constructor->sensitivity_reads.end());
            result->touches.insert(constructor->touches.begin(),constructor->touches.end());result->write_ranges.insert(constructor->write_ranges.begin(),constructor->write_ranges.end());
            result->function_forks|=constructor->function_forks;result->io_state|=constructor->io_state;result->random_state|=constructor->random_state;result->selection_checks|=constructor->selection_checks;
        }
        result->literal+="return "+receiver+";";return result;
    }
    int event_signal(VeriNode* n) {
        auto* symbol=veri_event_symbol(n);
        if(!symbol||object_fields.count(symbol))
            fail(n,"named event requires a static scalar event identifier");
        int id=n->detail_type()==veEXP_MEMBER?hierarchical_scope(n,Variable{symbol})->ids.at(Variable{symbol}.name()):variable_signal(n,Variable{symbol});
        if(!signals[id].named_event)fail(n,"event object is not declared");
        return id;
    }
    E instance_event(VeriNode* n) {
        auto* symbol=veri_event_symbol(n);if(!symbol)return {};
        auto found=object_fields.find(symbol);
        if(found==object_fields.end()) {
            int id=n->detail_type()==veEXP_MEMBER?hierarchical_scope(n,Variable{symbol})->ids.at(Variable{symbol}.name()):variable_signal(n,Variable{symbol});
            if(!event_value_signals.count(id))return {};
            auto value=signal_expr(id);value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);return value;
        }
        E receiver;
        if(n->detail_type()==veEXP_MEMBER) {
            auto* member=static_cast<VeriMemberExp*>(n);
            receiver=member->scope_reference()?implicit_this(n):expr(member->object());
        } else receiver=implicit_this(n);
        auto value=node("object_read",64,{receiver});
        value->literal=std::to_string(classes.at(found->second.first).id)+","+std::to_string(found->second.second);
        value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);return value;
    }
    // Event values are accepted only in typed event transfers/controls. Keep
    // ordinary expr() strict so an event never becomes an integer by accident.
    bool event_assignment(ProcessIR& p,VeriNode* lhs,VeriNode* rhs,bool nba,VeriNode* timing) {
        auto* symbol=veri_event_symbol(lhs);if(!symbol)return false;
        if(nba||timing)fail(lhs,"event aliases require immediate blocking assignment");
        auto target=instance_event(lhs);
        if(!target)fail(lhs,"event handles used as alias destinations currently require a class member or automatic local event");
        E value=instance_event(rhs);
        if(!value) {
            if(veri_event_symbol(rhs)) {
                const int source=event_signal(rhs);value=node("literal",64);value->literal="V(uint64_t("+sid(source)+")+1,0,64)";
                value->reads.insert(source);value->direct_reads.insert(source);
            } else {
                value=expr(rhs);if(value->object_type!=-2)fail(rhs,"event assignment requires an event value or null");
                value=node("literal",64);value->literal="V(0,0,64)";
            }
        }
        needs_event_aliases=true;
        auto bound=node("call",64,{value});bound->literal="return s.event_alias(call_arg0,"+sid(objects_signal)+");";
        bound->event_safe=false;bound->procedural_only=true;
        LValueIR destination;destination.width=64;
        if(object_fields.count(symbol)) {
            auto part=object_part(symbol,target->args.front());part.width=part.object_width=64;destination.parts.push_back(std::move(part));
        } else {int id=target->signal;writable(id,lhs);destination.parts.push_back({id,0,64,0});}
        write(p,destination,bound,false,false);return true;
    }
    E primary(VeriNode* n) {
        if(auto it=argument_values.find(n);it!=argument_values.end()) {
            if(it->second->op=="argument_storage")fail(n,"default argument dependence requiring formal storage is not supported yet");
            return it->second;
        }
        if(auto it=reduction_items.find(n);it!=reduction_items.end())return it->second;
        if(n->tok_type()==vtNUM) return number(static_cast<VeriNum*>(n));
        if(n->tok_type()==vtPARAM) {auto e=number(static_cast<VeriParam*>(n)->get_val());e->enum_id=enum_identity(n);return e;}
        if(n->tok_type()==vtSYS_VAR) {
            if(static_cast<VeriSysVar*>(n)->name()=="$realtime"){needs_real=true;auto e=node("literal",64);e->real_width=64;e->literal="V::real(double(s.now)*"+std::to_string(precision_fs)+".0/"+std::to_string(scope->time.unit_fs)+".0)";return e;}
            if(static_cast<VeriSysVar*>(n)->name()!="$time") fail(n,"unsupported system variable");
            auto e=node("time",64);e->literal=std::to_string(scope->time.unit_fs);return e;
        }
        if(n->tok_type()==vtMOD_INST) {
            auto* instance=static_cast<VeriModInstance*>(static_cast<VeriModInst*>(n)->instance());auto* target=static_cast<VeriMod*>(instance->hive());
            if(target&&target->is_interface())return interface_literal(target,"",n);
        }
        if(variable(n)) {
            if(Variable{n}.net_type()==vvEVENT)fail(n,"event handles are not integral values");
            if(object_fields.count(n)&&(Variable{n}.container_kind()==vrQUEUE||Variable{n}.container_kind()==vrOPEN))fail(n,"class array requires an unpacked value context or element index");
            if(object_fields.count(n)){auto value=object_read(object_part(n,implicit_this(n)));value->interface_type=veri_virtual_interface(n);value->signed_value=Variable{n}.is_signed()==IS_TRUE;value->real_width=veri_real_width(n);return value;}
            if(n->tok_type()==vtVAR&&(static_cast<VeriVar*>(n)->name()=="this"||static_cast<VeriVar*>(n)->name()=="super")&&static_cast<VeriVar*>(n)->class_type())return implicit_this(n);
            if(n->tok_type()==vtVAR&&static_cast<VeriVar*>(n)->interface_port()) {auto* port=static_cast<VeriVar*>(n);return interface_literal(port->interface_instance(),port->interface_modport(),n);}
            if(Variable{n}.net_type()==vvEVENT)fail(n,"event handles are not integral values");
            if(n->tok_type()==vtFUNC&&static_cast<VeriFunc*>(n)->func()->is_void())fail(n,"void function has no value");
            int id=variable_signal(n,Variable{n});
            E e=node("signal",signals[id].width); e->signal=id; e->reads.insert(id);e->direct_reads.insert(id);e->signed_value=Variable{n}->is_signed()==IS_TRUE;e->enum_id=enum_identity(n);e->text_value=signals[id].text_value;e->real_width=signals[id].real_width;e->object_type=class_type(n);e->interface_type=veri_virtual_interface(n);return e;
        }
        fail(n,"unsupported primary token "+std::to_string(n->tok_type()));
    }
    bool elaboration_expression(VeriNode* n) const {
        if(!n)return false;
        if(n->tok_type()==vtNUM||n->tok_type()==vtPARAM||n->tok_type()==vtGENVAR)return true;
        if(n->tok_type()!=vtEXP)return false;
        if(n->detail_type()==veEXP_PRI) {
            auto* p=static_cast<VeriPrimaryExp*>(n);
            return p->pri_type()==veNUM||p->pri_type()==veSTR||(p->var()&&elaboration_expression(p->var()));
        }
        if(n->detail_type()==veEXP_UNA) {
            auto* u=static_cast<VeriUnaryExp*>(n);
            if(u->op()==vtSYS_TYPENAME)return true;
            if(veri_is_sampled(u->op()))return false;
            if(veri_dynamic_string_value(u->exp_child()))return false;
            if(u->op()==vtUPREINC||u->op()==vtUPREDEC||u->op()==vtUPOSTINC||u->op()==vtUPOSTDEC)return false;
            if(veri_is_array_query(u->op())||u->op()==vtSYS_COUNTBITS)return veri_elaboration_constant(u);
            return u->op()==vtSYS_BITS||u->op()==vtSYS_RANGE_BITS||elaboration_expression(u->exp_child());
        }
        if(n->detail_type()==veEXP_BIN) {
            auto* b=static_cast<VeriBinaryExp*>(n);
            return elaboration_expression(b->lval())&&elaboration_expression(b->rval());
        }
        return false;
    }
    bool needs_two_state_cast=false,needs_vector_system=false,needs_real=false;
    std::vector<E> inside_items(const std::vector<VeriNode*>& items) {
        std::vector<E> result;
        for(auto* item:items) {
            if(item->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(item)->multi_type()==vemINSIDE_RANGE) {
                auto& bounds=static_cast<VeriMultiExp*>(item)->exp();auto low=expr(bounds.front()),high=expr(bounds.back());
                auto range=node("inside_range",std::max(low->width,high->width),{low,high});range->signed_value=low->signed_value&&high->signed_value;result.push_back(range);
            } else if(item->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(item)->pri_type()==veVAR) {
                auto* symbol=static_cast<VeriPrimaryExp*>(item)->var();
                if(variable(symbol)&&Variable{symbol}->range_depth()) {
                    Variable var{symbol};auto* owner=variable_scope(item,var);auto found=owner->memories.find(var->name());
                    if(found==owner->memories.end())fail(item,"inside array member requires a supported static unpacked variable");
                    if(memories[size_t(found->second)].dynamic)fail(item,"inside with dynamic array sets is not supported yet");
                    for(int id:memories[size_t(found->second)].words){auto value=signal_expr(id);value->signed_value=var->is_signed()==IS_TRUE;result.push_back(value);}
                } else result.push_back(expr(item));
            } else result.push_back(expr(item));
        }
        return result;
    }
    E expr(VeriNode* n) {
        if(!n) fail(n,"missing expression");
        if(n->tok_type()!=vtEXP) return primary(n);
        // Generate arithmetic is elaboration-time work. Consume the parser's
        // per-iteration snapshot rather than emitting a runtime genvar or
        // rejecting constant signed operands such as i*8+1.
        if(scope->generated && elaboration_expression(n) && (n->detail_type()==veEXP_BIN || n->detail_type()==veEXP_UNA))
            if(auto* constant=static_cast<VeriExp*>(n)->calc_value())return number(constant);
        switch(n->detail_type()) {
        case veEXP_CONSTRAINT_FOREACH:return constraint_foreach(static_cast<VeriConstraintForeach*>(n));
        case veEXP_CALLER:return scalar_function_value(n);
        case veEXP_PRI: {
            auto* p=static_cast<VeriPrimaryExp*>(n);
            if(p->pri_type()==veQUEUE_LAST) {
                // Resolve the lexical subscript instead of inheriting an
                // ambient queue: q[packed[$]] must not use q's size.
                auto* range=n->father();
                while(range&&range->detail_type()!=veEXP_RANGE)range=range->father();
                auto* owner=range?range->father():nullptr;
                if(!owner||owner->detail_type()!=veEXP_ARRAY)fail(n,"queue last index $ requires a queue subscript");
                if(auto saved=queue_slice_last_indices.find(owner);saved!=queue_slice_last_indices.end())return saved->second;
                auto* array=static_cast<VeriArrayExp*>(owner);auto* base=array->id();
                if(auto queue=object_queue_view(base);queue.id>=0) {
                    if(Variable{queue.symbol}.container_kind()!=vrQUEUE)fail(n,"last index $ requires a queue subscript");
                    if(array->range().empty()||array->range().front()!=range)fail(n,"queue last index $ requires a queue subscript");
                    auto size=node("container_method",32,{queue.receiver});size->signal=objects_signal;size->signed_value=true;size->reads.insert(objects_signal);
                    size->literal="return V(s.object_queue_size("+object_queue_reference(queue,"container_arg0")+"),0,32);";
                    auto one=node("literal",32);one->literal="V(1,0,32)";one->value=1;one->signed_value=true;
                    auto value=node("-",32,{size,one});value->signed_value=true;return value;
                }
                auto* member=base->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(base):nullptr;
                auto* symbol=base->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(base)->var():member?(member->hierarchical_symbol()?member->hierarchical_symbol():member->class_member()):nullptr;
                if(array->range().empty()||array->range().front()!=range||!variable(symbol)||Variable{symbol}.container_kind()!=vrQUEUE||object_fields.count(symbol))
                    fail(n,"queue last index $ requires a queue subscript");
                auto* storage=member&&member->hierarchical_symbol()?hierarchical_scope(n,Variable{symbol}):variable_scope(n,Variable{symbol});
                auto size=dynamic_size_expr(storage->ids.at(Variable{symbol}.name()));
                auto one=node("literal",32);one->value=1;one->literal="V(1,0,32)";one->signed_value=true;
                auto value=node("-",32,{size,one});value->signed_value=true;return value;
            }
            if(p->pri_type()==veSTR){
                needs_text=true;const auto text=decode_string(p->str(),p);
                auto e=node("text_literal",std::max(8,int(text.size())*8));e->text_value=e->packed_literal=e->constant_text=true;e->literal=quote(text);
                e->packed_value=number(p->calc_value());return e;
            }
            if(p->pri_type()==veNUM && p->str()=="'1") return node("fill1",1);
            if(p->pri_type()==veNUM && (p->str()=="'x"||p->str()=="'X")) return node("fillx",1);
            if(p->pri_type()==veNUM && (p->str()=="'z"||p->str()=="'Z")) return node("fillz",1);
            if(p->pri_type()==veNUM && p->calc_value()) return number(p->calc_value());
            if(!p->var()) fail(n,"unresolved symbol "+p->str());
            if(p->var()->tok_type()==vtGENVAR && p->calc_value())return number(p->calc_value());
            if(p->var()->tok_type()==vtFUNC) {
                bool result_variable=false;
                for(auto* frame=p->str().find("::")==std::string::npos?scope:nullptr;frame;frame=frame->parent) {
                    auto found=frame->symbols.find(Variable{p->var()}.name());
                    if(found!=frame->symbols.end()&&found->second==p->var()){result_variable=true;break;}
                }
                if(!result_variable) {
                    auto& call=implicit_function_calls[p];
                    if(!call) {
                        call=veri_parser->gen_caller(veri_parser->gen_primary(p->str().c_str(),p->line(),p->col(),veVAR),nullptr);
                        veri_bind_semantic(call,p->scope());
                    }
                    return scalar_function_value(call);
                }
            }
            return primary(p->var());
        }
        case veEXP_MEMBER: {
            auto* member=static_cast<VeriMemberExp*>(n);auto* field=member->field();
            if(member->interface_view_instance())return interface_literal(member->interface_view_instance(),member->member(),n);
            if(member->clocking_owner()) {
                auto& port=clocking_port(member);if(!port.input)fail(n,"cannot read an output clocking signal");
                auto value=signal_expr(port.buffer);value->signed_value=port.input->signed_value;return value;
            }
            if(member->process_builtin())return process_expression(member);
            if(member->coverage_builtin())return coverage_expression(member);
            if(member->ipc_builtin())return ipc_expression(member);
            if(member->random_control_builtin())return random_control_expression(member);
            if(member->randomize_builtin())return randomize_expression(member);
            if(auto found=reduction_items.find(member->class_member());found!=reduction_items.end()) {
                if(member->object()->detail_type()==veEXP_PRI) {const auto& name=static_cast<VeriPrimaryExp*>(member->object())->str();if(name=="this"||name=="super")return found->second;}
            }
            if(object_fields.count(member->class_member())&&!member->called()){
                if(veri_event_symbol(n))fail(n,"event handles are not integral values");
                if(Variable{member->class_member()}.container_kind()==vrQUEUE||Variable{member->class_member()}.container_kind()==vrOPEN)fail(n,"class array requires an unpacked value context or element index");
                auto value=object_read(object_part(member->class_member(),member->scope_reference()?implicit_this(n):expr(member->object())));value->interface_type=veri_virtual_interface(n);value->signed_value=Variable{member->class_member()}.is_signed()==IS_TRUE;value->enum_id=enum_identity(n);value->real_width=veri_real_width(n);return value;}
            if(member->hive())return scalar_function_value(n);
            if(member->member()=="size"&&(veri_subroutine_call(member->object())||veri_array_locator(member->object())||veri_queue_slice(member->object()))&&unpacked_value(member->object())) {
                auto* source=veri_array_element_symbol(member->object());auto values=array_values(member->object(),Variable{source});
                auto result=node("call",32,{values});result->signed_value=true;result->literal="return V(call_arg0.size(),0,32);";return result;
            }
            if(auto* symbol=member->hierarchical_symbol()) {
                if(symbol->tok_type()==vtMOD_INST) {
                    auto* instance=static_cast<VeriModInstance*>(static_cast<VeriModInst*>(symbol)->instance());auto* target=static_cast<VeriMod*>(instance->hive());
                    if(target&&target->is_interface())return interface_literal(target,"",n);
                }
                if(veri_virtual_interface(member->object()))return virtual_member_read(member);
                if(symbol->tok_type()==vtPARAM)return primary(symbol);
                if(!variable(symbol)||Variable{symbol}.range_depth())fail(n,"hierarchical observation requires a scalar or packed variable");
                Variable var{symbol};int id=hierarchical_scope(n,var)->ids.at(var.name());
                if(signals[id].named_event)fail(n,"hierarchical event references are not supported yet");
                auto e=signal_expr(id);e->signed_value=var.is_signed()==IS_TRUE;e->enum_id=enum_identity(symbol);return evaluate_before(static_receiver_effect(n),e);
            }
            if(veri_string_value(member->object())&&!veri_array_shape(member->object()).unpacked) {
                const auto& method=member->member();
                if(method=="putc"||method=="itoa"||method=="hextoa"||method=="octtoa"||method=="bintoa")
                    fail(n,"void string method requires a statement without a value");
                needs_text=true;std::vector<E> args{expr(member->object())};
                for(auto* a:veri_system_arguments(member->arguments()))args.push_back(expr(a));
                const bool compare=method=="compare"||method=="icompare";
                for(size_t i=1;i<args.size();++i) {
                    if(args[i]->text_value!=compare)fail(n,"string method argument type mismatch");
                    if(!compare){auto converted=node("fixed_cast",32,{args[i]});converted->signed_value=true;args[i]=converted;}
                }
                auto e=node("text_method",method=="getc"?8:32,args);
                e->text_value=method=="substr"||method=="toupper"||method=="tolower";
                e->signed_value=member->is_signed()==IS_TRUE;
                e->literal="return text_"+method+"(";
                for(size_t i=0;i<args.size();++i){if(i)e->literal+=",";e->literal+="text_arg"+std::to_string(i);}
                e->literal+=");";return e;
            }
            if(veri_array_locator(n))return array_locator(member);
            if(veri_array_reduction(n))return array_reduction(member);
            if(veri_array_ordering(n))fail(n,"void array ordering method requires a statement without a value");
            if(auto value=container_method(member))return value;
            if(int id=dynamic_object(member->object());id>=0) {
                if(member->member()!="size")fail(n,"delete() is a statement without a value");
                return evaluate_before(static_receiver_effect(member->object()),dynamic_size_expr(id));
            }
            if(member->event_query()) {
                if(auto event=instance_event(member->object()))return node("event_triggered",1,{event});
                int id=event_signal(member->object());auto e=node("event_triggered",1);e->signal=id;e->reads.insert(id);e->direct_reads.insert(id);return e;
            }
            if(auto* type=member->method_type()) {
                if(member->member()=="name") {
                    needs_text=true;auto source=expr(member->object());auto e=node("text_enum",1,{source});e->text_value=true;
                    const auto& names=type->enum_names();const auto& values=type->enum_values();
                    if(names.size()!=values.size())fail(n,"enum name metadata is incomplete");
                    for(size_t i=0;i<values.size();++i)e->literal+="if(binary_op<Binary::CaseEqual>(text_arg0,"+number(values[i])->literal+",1).truth()==1)return V::text("+quote(names[i])+");";
                    e->literal+="return V::text(\"\");";return e;
                }
                bool iterate=member->member()=="next"||member->member()=="prev";
                if(veri_elaboration_constant(n)&&member->calc_value()) {auto e=number(member->calc_value());e->enum_id=enum_identity(n);return e;}
                auto source=expr(member->object());std::vector<E> args{source};
                if(member->arguments())args.push_back(expr(veri_system_arguments(member->arguments()).front()));
                auto e=node("enum_method",member->member()=="num"?32:type->dlen(),std::move(args));
                e->signed_value=member->is_signed()==IS_TRUE;e->enum_id=enum_identity(n);
                if(!iterate) {e->literal="(void)enum_value;return "+number(member->calc_value())->literal+";";return e;}
                auto& values=type->enum_values();const auto count=std::to_string(values.size());
                const std::string invalid=veri_two_state(type->net_type())?"V(0,0,"+std::to_string(e->width)+")":"V::x("+std::to_string(e->width)+")";
                std::string code="size_t enum_index=0;";
                if(e->width<=32) {
                    code+="switch(enum_value.a|(enum_value.b<<"+std::to_string(e->width)+")){";
                    for(size_t i=0;i<values.size();++i) {
                        uint64_t a=0,b=0;
                        for(int bit=0;bit<e->width;++bit){int v=values[i]->get_certain_bit(bit);if(v==V1||v==VX)a|=uint64_t(1)<<bit;if(v==VX||v==VZ)b|=uint64_t(1)<<bit;}
                        code+="case "+std::to_string(a|(b<<e->width))+"ull:enum_index="+std::to_string(i)+";break;";
                    }
                    code+="default:return "+invalid+";}";
                } else {
                    for(size_t i=0;i<values.size();++i)code+=(i?"else if(":"if(")+std::string("binary_op<Binary::CaseEqual>(enum_value,")+number(values[i])->literal+",1).truth()==1)enum_index="+std::to_string(i)+";";
                    code+="else return "+invalid+";";
                }
                code+="uint64_t enum_delta="+std::string(e->args.size()==2?"(enum_count.a&0xffffffffull)":"1ull")+"%"+count+";";
                code+="switch((enum_index+"+std::string(member->member()=="next"?"enum_delta":count+"-enum_delta")+")%"+count+"){";
                for(size_t i=0;i<values.size();++i)code+="case "+std::to_string(i)+":return "+number(values[i])->literal+";";
                e->literal=code+"default:return "+invalid+";}";return e;
            }
            if(veri_string_value(field->symbol)) {
                needs_text=needs_struct_strings=true;auto e=node("text_method",1,{expr(member->object())});e->text_value=true;
                e->literal="return text_arg0.read_string_field("+std::to_string(field->offset)+");";return e;
            }
            auto e=node("slice",field->symbol->dlen(),{expr(member->object())});
            e->literal=std::to_string(field->offset)+","+std::to_string(field->symbol->dlen());
            if(veri_two_state(field->symbol->net_type())){needs_two_state_cast=true;e=node("two_state",e->width,{e});}
            else e=node("cast",e->width,{e});
            e->signed_value=field->symbol->is_signed()==IS_TRUE;e->enum_id=enum_identity(n);e->object_type=class_type(field->symbol);return e;
        }
        case veEXP_ARRAY: {
            if(veri_queue_slice(n))fail(n,"queue slice requires an unpacked value context");
            auto* a=static_cast<VeriArrayExp*>(n);
            if(auto binding=random_array_binding(a->id());!binding.empty()) {
                Variable property{veri_array_element_symbol(a->id())};
                if(a->range().empty()||a->range().size()>2)fail(n,"random array requires one index and optional packed selection");
                auto* index=static_cast<VeriRangeExp*>(a->range().front());
                if(index->rtype()!=vrSINGLE)fail(n,"random array requires an element index");
                auto value=node("constraint_array_read",property.dlen(),{expr(index->left())});value->literal=binding;value->signed_value=property.is_signed()==IS_TRUE;value->enum_id=enum_identity(property.node);
                if(a->range().size()==2) {
                    auto part=packed_selected(n,0,property.dend(),static_cast<VeriRangeExp*>(a->range().back()),property.dlen(),0,true,property.dstart()<property.dend());
                    if(part.index)fail(n,"symbolic packed selection of a random array element is not supported yet");
                    auto selected=node("slice",part.width,{value});selected->literal=std::to_string(part.lo)+","+std::to_string(part.width);return selected;
                }
                return value;
            }
            if(auto* symbol=veri_array_element_symbol(a->id());variable(symbol)&&Variable{symbol}.range_depth()>1&&associative_kind(Variable{symbol}.container_kind())) {auto part=selected(n);auto value=associative_part_read(part);if(a->range().size()==size_t(Variable{symbol}.range_depth()))value->signed_value=Variable{symbol}.is_signed()==IS_TRUE;return value;}
            VeriNode* property=a->id()->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(a->id())->class_member():a->id()->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(a->id())->var():nullptr;
            if(auto found=argument_values.find(property);found!=argument_values.end()) {
                auto shape=veri_array_shape(property);
                if(shape.unpacked||shape.dimensions.size()!=1||a->range().size()!=1)
                    fail(n,"default argument dependence requiring formal storage is not supported yet");
                auto source=primary(property);auto axis=shape.dimensions.front();
                auto part=packed_selected(n,0,axis.second,static_cast<VeriRangeExp*>(a->range().front()),source->width,0,true,axis.first<axis.second);
                auto value=part.index?node("indexed_slice",part.width,{source,part.index}):node("slice",part.width,{source});
                value->literal=part.index?std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false"):std::to_string(part.lo)+","+std::to_string(part.width);
                return value;
            }
            if(object_fields.count(property)&&reduction_items.count(property)) {
                bool implicit=a->id()->detail_type()==veEXP_PRI;
                if(!implicit){auto* object=static_cast<VeriMemberExp*>(a->id())->object();implicit=object->detail_type()==veEXP_PRI&&(static_cast<VeriPrimaryExp*>(object)->str()=="this"||static_cast<VeriPrimaryExp*>(object)->str()=="super");}
                if(implicit) {
                    if(a->range().size()!=1)fail(n,"symbolic class property requires one packed select");
                    auto source=reduction_items.at(property);Variable item{property};
                    auto part=packed_selected(n,0,item.dend(),static_cast<VeriRangeExp*>(a->range().front()),source->width,0,true,item.dstart()<item.dend());
                    auto value=part.index?node("indexed_slice",part.width,{source,part.index}):node("slice",part.width,{source});
                    value->literal=part.index?std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false"):std::to_string(part.lo)+","+std::to_string(part.width);
                    return value;
                }
            }
            if(object_fields.count(property)&&!(veri_dynamic_string_value(a->id())&&!veri_array_shape(a->id()).unpacked)) {
                auto value=object_read(selected(n));
                if(a->range().size()==size_t(Variable{property}.range_depth()))value->signed_value=Variable{property}.is_signed()==IS_TRUE;
                return value;
            }
            if(veri_dynamic_string_value(a->id())&&!veri_array_shape(a->id()).unpacked) {
                if(a->range().size()!=1||static_cast<VeriRangeExp*>(a->range().front())->rtype()!=vrSINGLE)
                    fail(n,"string indexing requires one character index");
                auto index=expr(static_cast<VeriRangeExp*>(a->range().front())->left());
                if(index->text_value)fail(n,"string index requires an integral value");
                auto converted=node("fixed_cast",32,{index});converted->signed_value=true;
                auto e=node("text_method",8,{expr(a->id()),converted});
                e->literal="return text_getc(text_arg0,text_arg1);";return e;
            }
            if(veri_string_value(a->id())&&!veri_array_shape(a->id()).unpacked)fail(n,"string literal indexing requires a string variable");
            if(auto* type=veri_aggregate_type(a->id());type&&type->unpacked_struct()) {
                if(a->range().size()>size_t(veri_array_shape(a->id()).unpacked))fail(n,"unpacked struct cannot be selected as a packed integral vector");
            }
            if(a->id()->detail_type()==veEXP_PRI)if(auto found=reduction_items.find(static_cast<VeriPrimaryExp*>(a->id())->var());found!=reduction_items.end()) {
                if(a->range().size()!=1||found->second->value>1)fail(n,"array reduction iterator supports one-dimensional packed selects");
                auto source=found->second;Variable item{static_cast<VeriPrimaryExp*>(a->id())->var()};
                auto part=packed_selected(n,0,item.dend(),static_cast<VeriRangeExp*>(a->range().front()),source->width,0,true,item->dstart()<item->dend());
                E e;
                if(part.index){e=node("indexed_slice",part.width,{source,part.index});e->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");}
                else {e=node("slice",part.width,{source});e->literal=std::to_string(part.lo)+","+std::to_string(part.width);}
                if(item.two_state()){needs_two_state_cast=true;return node("two_state",e->width,{e});}return e;
            }
            if(a->id()->detail_type()==veEXP_MEMBER) {
                auto* member=static_cast<VeriMemberExp*>(a->id());
                if(auto* symbol=member->hierarchical_symbol();variable(symbol)) {
                    Variable var{symbol};if(var.real_width())needs_real=true;
                    if(var.net_type()==vvEVENT)fail(n,"event handles cannot be selected as integral values");
                    if(veri_virtual_interface(member->object())) {
                        auto source=virtual_member_read(member);auto part=virtual_member_part(member);
                        if(a->range().size()!=1)fail(n,"virtual interface packed member requires one selection");
                        auto selected=packed_selected(n,part.signal,var.dend(),static_cast<VeriRangeExp*>(a->range().front()),part.width,0,true,var.dstart()<var.dend());
                        if(selected.index){auto value=node("indexed_slice",selected.width,{source,selected.index});value->literal=std::to_string(selected.base)+","+std::to_string(selected.width)+","+(selected.descending?"true":"false");return value;}
                        auto value=node("slice",selected.width,{source});value->literal=std::to_string(selected.lo)+","+std::to_string(selected.width);return value;
                    }
                    return evaluate_before(static_receiver_effect(a->id()),selected_read(a,var,selected_storage(a,var,hierarchical_scope(n,var))));
                }
                if(a->range().size()!=1)fail(n,"only one packed member select is supported");
                auto source=expr(member);
                if(member->clocking_owner()) {
                    auto shape=veri_array_shape(member->clocking_source());
                    if(shape.unpacked||shape.dimensions.size()!=1)fail(n,"clocking input selection requires one packed dimension");
                    auto axis=shape.dimensions.front();
                    auto part=packed_selected(n,0,axis.second,static_cast<VeriRangeExp*>(a->range().front()),source->width,0,false,axis.first<axis.second);
                    auto value=part.index?node("indexed_slice",part.width,{source,part.index}):node("slice",part.width,{source});
                    value->literal=part.index?std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false"):std::to_string(part.lo)+","+std::to_string(part.width);
                    return value;
                }
                if(member->event_query())fail(n,"select of triggered query result is not supported yet");
                VeriNode* selected_symbol=member->hierarchical_symbol()?member->hierarchical_symbol():member->field()?member->field()->symbol:nullptr;
                if(member->method_type()||!selected_symbol)fail(n,member->method_type()?"select of enum method result is not supported yet":"select of method result is not supported yet");
                if(!variable(selected_symbol))fail(n,"hierarchical select requires a packed variable");
                Variable selected_var{selected_symbol};
                auto part=packed_selected(n,0,selected_var.dend(),static_cast<VeriRangeExp*>(a->range().front()),source->width,0,false,selected_var->dstart()<selected_var->dend());
                if(part.index) {
                    if(part.width>64)needs_wide=true;
                    auto e=node("indexed_slice",part.width,{source,part.index});
                    e->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");
                    if(selected_var.two_state()){needs_two_state_cast=true;return node("two_state",e->width,{e});}
                    return e;
                }
                auto e=node("slice",part.width,{source});e->literal=std::to_string(part.lo)+","+std::to_string(part.width);return e;
            }
            if(a->range().empty()) return expr(a->id());
            if(a->id()->detail_type()==veEXP_PRI) {
                auto* symbol=static_cast<VeriPrimaryExp*>(a->id())->var();
                if(symbol&&(symbol->tok_type()==vtPARAM||symbol->tok_type()==vtGENVAR)) {
                    if(veri_elaboration_constant(a)&&a->calc_value())return number(a->calc_value());
                    auto shape=veri_array_shape(symbol);
                    if(a->range().size()!=1||shape.dimensions.size()!=1)fail(n,"parameter select requires one packed dimension");
                    auto source=expr(a->id());auto axis=shape.dimensions.front();
                    auto part=packed_selected(n,0,axis.second,static_cast<VeriRangeExp*>(a->range().front()),source->width,0,true,axis.first<axis.second);
                    E result;
                    if(part.index) {result=node("indexed_slice",part.width,{source,part.index});result->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");}
                    else {result=node("slice",part.width,{source});result->literal=std::to_string(part.lo)+","+std::to_string(part.width);}
                    return result;
                }
            }
            auto part=selected(n);
            Variable var{static_cast<VeriPrimaryExp*>(a->id())->var()};
            return selected_read(a,var,part);
        }
        case veEXP_UNA: {
            auto* u=static_cast<VeriUnaryExp*>(n);
            if(u->op()==vtSYS_TYPENAME) {
                if(!u->calc_value())fail(n,"unresolved $typename query");
                return number(u->calc_value());
            }
            if(u->op()==vtSYS_CAST)return dynamic_cast_expression(u);
            if(veri_is_real_function(u->op())) {
                needs_real=true;auto input=expr(u->exp_child());
                const int op=u->op();
                if(op==vtSYS_RTOI||op==vtSYS_REALTOBITS)input=numeric_context(input,64,64);
                if(op==vtSYS_SHORTREALTOBITS)input=numeric_context(input,32,32);
                if(op==vtSYS_ITOR||op==vtSYS_BITSTOREAL||op==vtSYS_BITSTOSHORTREAL) {
                    const int width=op==vtSYS_BITSTOREAL?64:32;input=numeric_context(input,0,width);
                    auto cast=node("fixed_cast",width,{input});cast->signed_value=input->signed_value;input=cast;
                }
                auto value=node("real_system",u->op()==vtSYS_REALTOBITS||u->op()==vtSYS_BITSTOREAL||u->op()==vtSYS_ITOR?64:32,{input});
                if(u->op()==vtSYS_ITOR){auto cast=node("fixed_cast",32,{input});cast->signed_value=true;value->args[0]=cast;value->literal="real_itor";value->real_width=64;}
                if(u->op()==vtSYS_RTOI){value->literal="real_rtoi";value->signed_value=true;}
                if(u->op()==vtSYS_REALTOBITS){value->literal="real_to_bits64";}
                if(u->op()==vtSYS_SHORTREALTOBITS){value->literal="real_to_bits32";}
                if(u->op()==vtSYS_BITSTOREAL){value->literal="real_from_bits64";value->real_width=64;}
                if(u->op()==vtSYS_BITSTOSHORTREAL){value->literal="real_from_bits32";value->real_width=32;}
                return value;
            }
            if(u->op()==vtSYS_BITS&&struct_has_strings(veri_aggregate_type(u->exp_child())))fail(n,"$bits of a struct containing strings is not supported yet");
            if(auto* type=veri_aggregate_type(u->exp_child());type&&type->unpacked_struct()&&u->op()!=vtSYS_BITS)
                fail(n,"unpacked struct cannot be used as an integral operand");

            if(veri_is_sampled(u->op())) {
                if(sampling_property<0)fail(n,"sampled-value function requires a concurrent property clock or a single-edge procedural clock");
                if(sampling_context!=1&&sampling_context!=4&&u->op()!=vtSYS_SAMPLED)
                    fail(n,"only $sampled is supported in disable iff and property actions; history functions require a property expression");
                auto args=veri_system_arguments(u->exp_child());
                auto value=expr(args[0]);property_expression(n,value);
                int depth=1;
                if(args.size()>1) {
                    if(!veri_elaboration_constant(args[1]))fail(args[1],"$past depth must be a positive constant in 1..65536");
                    auto count=expr(args[1]);
                    if(count->op!="literal"||count->unknown||count->negative||count->host_overflow||!count->value||count->value>65536)
                        fail(args[1],"$past depth must be a positive constant in 1..65536");
                    depth=int(count->value);
                }
                auto gate=node("literal",1);gate->literal="V(1)";
                if(args.size()>2){gate=expr(args[2]);property_expression(args[2],gate);}
                int kind=u->op()-vtSYS_SAMPLED,slot=int(lowering_samples.size());
                lowering_samples.push_back({kind,depth,value,gate});
                auto result=node("property_sample",kind<2?value->width:1,{value,gate});
                result->value=uint64_t(sampling_property);result->signal=slot;
                result->signed_value=kind<2&&value->signed_value;
                if(value->width>64)needs_wide=true;
                return result;
            }
            if(veri_is_testbench_function(u->op()))return testbench_expression(u);
            if(veri_is_random(u->op()))return random_expression(u);
            if(u->op()==vtSYS_BITS||veri_is_array_query(u->op())) {
                auto args=u->op()==vtSYS_BITS?std::vector<VeriNode*>{u->exp_child()}:veri_system_arguments(u->exp_child());
                const auto object_array=object_queue_view(args.front());
                const int id=object_array.id>=0?-1:dynamic_object(args.front());
                const bool sliced=veri_queue_slice(args.front());
                if(id>=0||object_array.id>=0||sliced) {
                    if(u->op()==vtSYS_BITS&&object_array.id>=0&&class_type(object_array.symbol)>=0)fail(n,"$bits of class-handle containers is not supported yet");
                    if(!random_array_binding(args.front()).empty())fail(n,"random array system queries in constraints are not supported yet; use size()");
                    if(associative_signals.count(id))fail(n,"associative array system queries are not supported yet; use size()/num()");
                    auto count=sliced?E{}:object_array.id>=0?node("container_method",32,{object_array.receiver}):dynamic_size_expr(id);
                    const int element_width=sliced?Variable{veri_array_element_symbol(args.front())}.dlen():object_array.id>=0?Variable{object_array.symbol}.dlen():signals[id].width;
                    if(sliced) {
                        if(u->op()==vtSYS_BITS&&class_type(veri_array_element_symbol(args.front()))>=0)fail(n,"$bits of class-handle containers is not supported yet");
                        auto values=array_values(args.front(),Variable{veri_array_element_symbol(args.front())});
                        count=node("call",32,{values});count->signed_value=true;count->literal="return V(call_arg0.size(),0,32);";
                    }
                    if(object_array.id>=0) {
                        count->signal=objects_signal;count->signed_value=true;count->reads.insert(objects_signal);count->direct_reads.insert(objects_signal);
                        count->literal="return V(s.object_queue_size("+object_queue_reference(object_array,"container_arg0")+"),0,32);";
                    }
                    auto shape=veri_array_shape(args.front());std::vector<E> values{count};
                    if(u->op()!=vtSYS_BITS) {
                        if(args.size()==2)values.push_back(expr(args[1]));
                        else {auto one=node("literal",32);one->literal="V(1,0,32)";values.push_back(one);}
                    }
                    auto e=node("dynamic_query",32,std::move(values));e->signed_value=true;
                    if(u->op()==vtSYS_BITS)e->literal="return V(dynamic_count.a*"+std::to_string(element_width)+"ull,0,32);";
                    else if(u->op()==vtSYS_DIMENSIONS)e->literal="return V("+std::to_string(shape.dimensions.size())+",0,32);";
                    else if(u->op()==vtSYS_UNPACKED_DIMENSIONS)e->literal="return V(1,0,32);";
                    else {
                        auto answer=u->op()==vtSYS_SIZE?"dynamic_count.a":u->op()==vtSYS_LEFT||u->op()==vtSYS_LOW?"0ull":u->op()==vtSYS_INCREMENT?"uint64_t(-1)":"dynamic_count.a-1ull";
                        e->literal="if(binary_op<Binary::CaseEqual>(dimension,V(1,0,32),1).truth()==1)return V("+std::string(answer)+",0,32);";
                        for(size_t dim=2;dim<=shape.dimensions.size();++dim) {
                            bool valid=true;int answer=veri_array_query(u->op(),shape,int(dim),valid);
                            e->literal+="if(binary_op<Binary::CaseEqual>(dimension,V("+std::to_string(dim)+",0,32),1).truth()==1)return V("+std::to_string(uint32_t(answer))+"ull,0,32);";
                        }
                        e->literal+="return V::x(32);";
                    }
                    return e;
                }
            }
            if(u->op()==vtSYS_BITS||u->op()==vtSYS_RANGE_BITS) {
                if(u->op()==vtSYS_BITS&&veri_dynamic_string_value(u->exp_child())) {
                    auto value=expr(u->exp_child());auto result=node("text_method",32,{value});
                    result->signed_value=true;result->literal="return V(text_arg0.text_value().size()*8,0,32);";return result;
                }
                auto* value=u->calc_value();if(value)return number(value);
                if(u->op()!=vtSYS_BITS||veri_array_shape(u->exp_child()).unbound)fail(n,"unresolved $bits query");
                auto result=node("literal",32);result->signed_value=true;result->value=uint32_t(veri_bit_width(u->exp_child()));result->literal="V("+std::to_string(result->value)+",0,32)";return result;
            }
            if(veri_is_array_query(u->op())) {
                if(veri_elaboration_constant(u)) {
                    auto* value=u->calc_value();if(value)return number(value);
                    auto args=veri_system_arguments(u->exp_child());auto shape=veri_array_shape(args[0]);
                    if(shape.unbound)fail(n,"unresolved array query");
                    bool valid=true;int dimension=1;
                    if(args.size()==2){auto d=veri_constant_value(static_cast<VeriExp*>(args[1]),0);if(!d)fail(n,"unresolved array dimension");valid=d->no_xz()==IS_TRUE;for(int bit=31;bit<d->bits();++bit)if(d->get_certain_bit(bit)!=V0)valid=false;dimension=valid?d->get_first_int():0;}
                    int answer=valid?veri_array_query(u->op(),shape,dimension,valid):0;
                    auto result=node("literal",32);result->signed_value=true;result->value=uint32_t(answer);result->negative=valid&&answer<0;result->unknown=!valid;result->literal=valid?"V("+std::to_string(uint32_t(answer))+"ull,0,32)":"V::x(32)";return result;
                }
                auto args=veri_system_arguments(u->exp_child());auto shape=veri_array_shape(args[0]);
                auto e=node("array_query",32,{expr(args[1])});e->signed_value=true;
                for(size_t d=1;d<=shape.dimensions.size();++d) {
                    bool valid=true;int value=veri_array_query(u->op(),shape,int(d),valid);
                    e->literal+="if(binary_op<Binary::CaseEqual>(dimension,V("+std::to_string(d)+",0,32),1).truth()==1)return V("+std::to_string(uint32_t(value))+"ull,0,32);";
                }
                return e;
            }
            if(u->op()==vtSYS_COUNTBITS) {
                std::vector<E> values;for(auto* arg:veri_system_arguments(u->exp_child())){values.push_back(expr(arg));if(values.back()->width>64)needs_wide=true;}
                needs_vector_system=true;auto e=node("count_bits",32,std::move(values));e->signed_value=true;return e;
            }
            if(u->op()==vtSYS_QUERY_TYPE)fail(n,"data-type query descriptor cannot be a runtime value");
            if(veri_is_system_unary(u->op())) {
                auto value=expr(u->exp_child());needs_vector_system=true;
                int mode=u->op()==vtSYS_CLOG2?0:u->op()==vtSYS_ISUNKNOWN?1:u->op()==vtSYS_COUNTONES?2:u->op()==vtSYS_ONEHOT?3:4;
                auto e=node("vector_system",mode==0||mode==2?32:1,{value});e->literal=std::to_string(mode);e->signed_value=mode==0||mode==2;
                if(value->width>64)needs_wide=true;
                return e;
            }
            if(u->op()==vtUPREINC||u->op()==vtUPREDEC||u->op()==vtUPOSTINC||u->op()==vtUPOSTDEC) {
                auto one=node("literal",32);one->literal="V(1,0,32)";one->signed_value=true;
                ProcessIR effect;E result;
                compound(effect,n,u->exp_child(),one,u->op()==vtUPREINC||u->op()==vtUPOSTINC?"+":"-",&result,u->op()==vtUPOSTINC||u->op()==vtUPOSTDEC);
                return result;
            }
            if(veri_dynamic_string_value(u->exp_child()))fail(n,"string operand is not supported in integral unary operations");
            auto a=expr(u->exp_child()); std::string op;
            switch(u->op()) {
            case vtUADD:op="+";break; case vtUSUB:op="-";break;
            case vtUNEG:op="~";break; case vtUNOT:op="!";break;
            case vtUAND:op="&";break; case vtUOR:op="|";break; case vtUXOR:op="^";break;
            case vtUNAND:op="&";break; case vtUNOR:op="|";break; case vtUXNOR:op="^";break;
            default:fail(n,"unsupported unary operator");
            }
            bool reduce=op=="!"||op=="&"||op=="|"||op=="^";
            E e=node(op,reduce?1:a->width,{a});
            if(u->op()==vtUNAND||u->op()==vtUNOR||u->op()==vtUXNOR) e=node("~",1,{e});
            e->signed_value=!reduce&&a->signed_value; return e;
        }
        case veEXP_BIN: {
            auto* v=static_cast<VeriBinaryExp*>(n);
            if(auto* type=unpacked_cast_type(n))return array_cast_values(v,type);
            if(!veri_is_cast(v->op())&&(unpacked_value(v->lval())||unpacked_value(v->rval())))return array_equality(v);
            auto* left_type=veri_aggregate_type(v->lval());auto* right_type=veri_aggregate_type(v->rval());
            if((left_type&&left_type->unpacked_struct())||(right_type&&right_type->unpacked_struct())) {
                bool equality=v->op()==vtBLEQ||v->op()==vtBLIEQ||v->op()==vtBCEQ||v->op()==vtBCIEQ;
                if(!equality||left_type!=right_type)fail(n,"unpacked structs require matching types and cannot be used in integral arithmetic or casts");
            }

            if(veri_streaming(n)) {
                if(string_stream(v->rval())) {
                    if(v->op()!=vtSTREAM_RIGHT)fail(n,"left streaming of strings is not supported yet");
                    return string_stream_value(v->rval());
                }
                if(runtime_stream_operand(v->rval()))fail(n,"runtime-sized stream requires a packed or unpacked destination context");
                return stream_value(n,stream_payload(v->rval()));
            }
            if(v->op()==vtBINSIDE) {
                auto* list=static_cast<VeriMultiExp*>(v->rval());auto values=inside_items(std::vector<VeriNode*>(list->exp().begin(),list->exp().end()));
                auto operand=expr(v->lval());
                if(operand->text_value&&!operand->packed_value) {
                    for(auto& value:values)if(!value->text_value)fail(n,"string inside members require strings without ranges");
                    values.insert(values.begin(),operand);return node("text_inside",1,std::move(values));
                }
                values.insert(values.begin(),operand);return node("inside",1,std::move(values));
            }
            if(veri_is_cast(v->op())) {
                if(v->op()==vtCAST_STRING)return text_expression(v->rval());
                if(v->op()==vtCAST_CHANDLE){auto value=expr(v->rval());if(value->object_type!=opaque_handle_type&&value->object_type!=-2)fail(n,"chandle cast requires a chandle or null");auto result=std::make_shared<Expr>(*value);result->object_type=opaque_handle_type;return result;}
                auto width=veri_constant_value(static_cast<VeriExp*>(v->lval()),0);
                if(!veri_elaboration_constant(v->lval())||!width)fail(n,"cast width must be constant");
                const int bits=width->get_first_int();
                if(unpacked_value(v->rval())||(veri_streaming(v->rval())&&runtime_stream_operand(v->rval()))) {
                    if(v->op()==vtCAST_REAL||v->op()==vtCAST_SHORTREAL||v->op()==vtCAST_CHANDLE)fail(n,"bit-stream cast requires an integral destination");
                    auto result=runtime_stream_packed(v->rval(),bits,v->op()==vtCAST_SIGNED2||v->op()==vtCAST_UNSIGNED2,!veri_streaming(v->rval()));
                    result->signed_value=v->op()==vtCAST_SIGNED4||v->op()==vtCAST_SIGNED2;result->enum_id=enum_identity(n);return result;
                }
                auto value=expr(v->rval());
                if(v->op()==vtCAST_REAL||v->op()==vtCAST_SHORTREAL)return numeric_context(value,bits,bits);
                if(value->real_width)value=numeric_context(value,0,bits);
                bool two=v->op()==vtCAST_SIGNED2||v->op()==vtCAST_UNSIGNED2;
                auto cast=node(two?"fixed_cast_2":"fixed_cast",bits,{value});
                cast->signed_value=v->op()==vtCAST_SIZE?value->signed_value:v->op()==vtCAST_SIGNED4||v->op()==vtCAST_SIGNED2;
                cast->enum_id=enum_identity(n);
                if(bits>64)needs_wide=true;if(two)needs_two_state_cast=true;
                return cast;
            }
            auto a=expr(v->lval()),b=expr(v->rval()); std::string op;
            if(v->op()==vtBPOW&&!a->real_width&&!b->real_width)fail(n,"integral exponentiation is not supported yet");
            switch(v->op()) {
            case vtBPOW:op="**";break;
            case vtBADD:op="+";break;case vtBSUB:op="-";break;case vtBMUL:op="*";break;
            case vtBDIV:op="/";break;case vtBMOD:op="%";break;
            case vtBSAND:op="&";break;case vtBSOR:op="|";break;case vtBSXOR:op="^";break;case vtBXNOR:op="^";break;
            case vtBDAND:op="&&";break;case vtBDOR:op="||";break;
            case vtBWLEQ:op="==?";break;case vtBWLNEQ:op="!=?";break;
            case vtBLEQ:op="==";break;case vtBLIEQ:op="!=";break;case vtBCEQ:op="===";break;case vtBCIEQ:op="!==";break;
            case vtBLT:op="<";break;case vtBGT:op=">";break;case vtBLE:op="<=";break;case vtBGE:op=">=";break;
            case vtBLLS:case vtBALS:op="<<";break;case vtBLRS:op=">>";break;case vtBARS:op=">>>";break;
            default:fail(n,"unsupported binary operator");
            }
            if(a->text_value&&!a->packed_value&&!b->text_value&&veri_string_value(v->rval()))b=text_context(b);
            if(b->text_value&&!b->packed_value&&!a->text_value&&veri_string_value(v->lval()))a=text_context(a);
            if((a->packed_value&&(!b->text_value||b->packed_value))||(b->packed_value&&!a->text_value)) {
                if(a->packed_value)a=a->packed_value;if(b->packed_value)b=b->packed_value;
            }
            if(a->text_value||b->text_value) {
                if(!a->text_value||!b->text_value)fail(n,"mixed string and integral operands are not supported");
                if(op!="=="&&op!="!="&&op!="==="&&op!="!=="&&op!="<"&&op!=">"&&op!="<="&&op!=">=")fail(n,"unsupported string operator "+op);
                auto e=node("text_binary",1,{a,b});
                const auto comparison=op=="==="?"==":op=="!=="?"!=":op;
                if(a->packed_literal&&b->packed_literal) {
                    if(!a->constant_text||!b->constant_text)fail(n,"integral comparison of conditional string literals is not supported yet");
                    e->literal="return V(text_packed_compare(text_arg0,text_arg1)"+comparison+"0,0,1);";
                } else e->literal="return V(text_arg0.text_value()"+comparison+"text_arg1.text_value(),0,1);";
                return e;
            }
            bool cmp=op=="&&"||op=="||"||op=="=="||op=="!="||op=="==="||op=="!=="||op=="==?"||op=="!=?"||op=="<"||op==">"||op=="<="||op==">=";
            bool shift=op=="<<"||op==">>"||op==">>>";
            int w=cmp?1:shift?a->width:std::max(a->width,b->width);
            if(a->interface_type||b->interface_type) {
                const bool equality=op=="=="||op=="!="||op=="==="||op=="!==";
                if(equality) {
                    if(!(a->object_type==-2||b->object_type==-2||interface_compatible(a->interface_type,b->interface_type)||interface_compatible(b->interface_type,a->interface_type)))fail(n,"virtual interface equality requires compatible handles or null");
                }
            } else if(a->object_type!=-1||b->object_type!=-1) {
                const bool equality=op=="=="||op=="!="||op=="==="||op=="!==";
                if(equality&&(a->object_type==-1||b->object_type==-1||(!class_compatible(a->object_type,b->object_type)&&!class_compatible(b->object_type,a->object_type))))fail(n,"object equality requires compatible class handles or null");
            }
            E e=node(op,w,{a,b});e->signed_value=!cmp&&(shift?a->signed_value:a->signed_value&&b->signed_value);
            if(v->op()==vtBXNOR){auto inner=e;e=node("~",w,{inner});e->signed_value=inner->signed_value;}
            return e;
        }
        case veEXP_QUES: {
            auto* q=static_cast<VeriQuesExp*>(n); auto c=expr(q->ques()),a=expr(q->choice1()),b=expr(q->choice2());
            if(c->packed_value)c=c->packed_value;
            if(c->text_value)fail(n,"string cannot be used as a boolean condition");
            if(a->text_value&&!a->packed_value&&!b->text_value&&veri_string_value(q->choice2()))b=text_context(b);
            if(b->text_value&&!b->packed_value&&!a->text_value&&veri_string_value(q->choice1()))a=text_context(a);
            if((a->packed_value&&!b->text_value)||(b->packed_value&&!a->text_value)) {
                if(a->packed_value)a=a->packed_value;if(b->packed_value)b=b->packed_value;
            }
            if(a->text_value||b->text_value) {
                if(!a->text_value||!b->text_value)fail(n,"mixed string and integral conditional branches are not supported");
                auto e=node("text_mux",std::max(a->width,b->width),{c,a,b});e->text_value=true;e->packed_literal=a->packed_literal&&b->packed_literal;
                if(e->packed_literal)e->packed_value=node("mux",e->width,{c,a->packed_value,b->packed_value});return e;
            }
            if(a->interface_type||b->interface_type) {
                auto common=a->interface_type?a->interface_type:b->interface_type;
                if((a->object_type!=-2&&!interface_compatible(a->interface_type,common))||(b->object_type!=-2&&!interface_compatible(b->interface_type,common)))fail(n,"virtual interface conditional requires compatible handles or null");
                auto result=node("handle_mux",64,{c,a,b});result->interface_type=common;return result;
            }
            if(a->object_type==opaque_handle_type||b->object_type==opaque_handle_type) {
                if(c->object_type!=-1)fail(n,"handle cannot be used as a conditional selector");
                if(!class_compatible(a->object_type,opaque_handle_type)||!class_compatible(b->object_type,opaque_handle_type))fail(n,"chandle conditional requires compatible handles or null");
                if(auto value=veri_constant_value(static_cast<VeriExp*>(q->ques()),0);value&&value->no_xz()!=IS_TRUE)fail(n,"chandle conditional selector cannot be unknown");
                auto result=node("handle_mux",64,{c,a,b});result->object_type=opaque_handle_type;return result;
            }
            if(a->object_type!=-1||b->object_type!=-1) {
                int common=a->object_type;
                if(a->object_type==-1||b->object_type==-1)fail(n,"class conditional requires compatible object handles or null");
                if(a->object_type==-2)common=b->object_type;
                else if(!class_compatible(b->object_type,common)) {
                    if(class_compatible(a->object_type,b->object_type))common=b->object_type;
                    else fail(n,"class conditional requires compatible object handles or null");
                }
                auto result=node("call",64,{c,a,b});
                // Like integral ?:, ambiguous selectors evaluate both arms.
                // Class values retain handle identity; VCS selects the right
                // handle after that evaluation rather than merging its bits.
                result->op="class_mux";result->object_type=common;return result;
            }
            if(struct_has_strings(veri_aggregate_type(q->choice1()))||struct_has_strings(veri_aggregate_type(q->choice2()))) {
                if(veri_aggregate_type(q->choice1())!=veri_aggregate_type(q->choice2()))fail(n,"struct conditional requires matching types");
                return node("struct_mux",a->width,{c,a,b});
            }
            auto e=node("mux",std::max(a->width,b->width),{c,a,b});e->signed_value=a->signed_value&&b->signed_value;e->enum_id=a->enum_id==b->enum_id?a->enum_id:0;return e;
        }
        case veEXP_SIGN:case veEXP_UNSIGN: {
            auto value=expr(n->detail_type()==veEXP_SIGN?static_cast<VeriSignExp*>(n)->exp():static_cast<VeriUnsignExp*>(n)->exp());
            auto e=node("cast",value->width,{value});e->signed_value=n->detail_type()==veEXP_SIGN;return e;
        }
        case veEXP_MULTI: {
            auto* m=static_cast<VeriMultiExp*>(n);
            if(m->multi_type()==vemOBJECT_NEW)return object_new(m);
            if(m->multi_type()==vemNULL){auto value=node("literal",64);value->literal="V(0,0,64)";value->object_type=-2;return value;}
            if(assignment_pattern(n))fail(n,"assignment pattern requires a supported assignment context");
            if(m->multi_type()!=vemCONCAT_EXP || m->exp().empty()) fail(n,"expected concatenation (multi type "+std::to_string(m->multi_type())+", items "+std::to_string(m->exp().size())+")");
            if(veri_string_value(n)) {
                std::vector<E> args;bool dynamic_text=false,all_text=true;
                for(auto* item:m->exp()){auto value=expr(item);dynamic_text|=value->text_value&&!value->packed_value;all_text&=value->text_value;args.push_back(value);}
                if(!all_text&&!dynamic_text) {
                    E result;for(auto value:args){if(value->packed_value)value=value->packed_value;result=result?node("concat",result->width+value->width,{result,value}):value;}
                    if(result->width>64)needs_wide=true;return node("cast",result->width,{result});
                }
                size_t text_index=0;for(auto* item:m->exp()){if(!args[text_index]->text_value){string_concat_operand(item);args[text_index]=text_context(args[text_index]);}++text_index;}
                auto e=node("text_method",1,args);e->text_value=e->packed_literal=e->constant_text=true;for(auto value:args){e->packed_literal&=value->packed_literal;e->constant_text&=value->constant_text;}e->literal="std::string text_joined;";
                for(size_t i=0;i<args.size();++i)e->literal+="text_joined+=text_arg"+std::to_string(i)+".text_value();";
                e->literal+="return V::text(std::move(text_joined));";
                if(e->packed_literal){E packed;for(auto value:args){auto next=value->packed_value;packed=packed?node("concat",packed->width+next->width,{packed,next}):next;}e->packed_value=packed;e->width=packed->width;if(e->width>64)needs_wide=true;}return e;
            }
            E result;
            for(auto* v:m->exp()) {
                if(auto* type=veri_aggregate_type(v);type&&type->unpacked_struct())fail(v,"unpacked struct cannot be a packed concatenation operand");
                auto* literal=v;
                while(literal->detail_type()==veEXP_UNA) {
                    auto* unary=static_cast<VeriUnaryExp*>(literal);
                    if(unary->op()!=vtUADD&&unary->op()!=vtUSUB)break;
                    literal=unary->exp_child();
                }
                if(literal->detail_type()==veEXP_PRI) {
                    auto* primary=static_cast<VeriPrimaryExp*>(literal);
                    const auto& spelling=primary->str();const auto apostrophe=spelling.find('\'');
                    if(primary->pri_type()==veNUM&&!veri_real_width(primary)&&
                       (apostrophe==std::string::npos||(apostrophe==0&&spelling.size()>2)))
                        fail(v,"packed concatenation requires sized constant numbers");
                }
                auto e=expr(v);result=result?node("concat",result->width+e->width,{result,e}):e;if(result->width>64)needs_wide=true;
            }
            auto e=node("cast",result->width,{result});return e;
        }
        case veEXP_MCONCAT:return replication_value(static_cast<VeriMultiConcatExp*>(n),false);
        default:fail(n,"unsupported expression kind "+std::to_string(n->detail_type()));
        }
    }
    std::pair<E,E> aggregate_components(VeriVar* type) {
        const int width=type->dlen();std::string bits(width,'x'),strings;
        std::function<void(VeriVar*,int)> fill=[&](VeriVar* aggregate,int offset) {
            for(const auto& field:aggregate->packed_fields()) {
                const int low=offset+field.offset,count=field.symbol->dlen();
                if(auto* nested=field.symbol->aggregate_type();nested&&nested->unpacked_struct())fill(nested,low);
                else if(veri_string_value(field.symbol)){strings+="{"+std::to_string(low)+",\"\"},";bits[bits.size()-1-low]='0';}
                else if(veri_two_state(field.symbol->net_type())||class_type(field.symbol)>=0)
                    for(int bit=0;bit<count;++bit)bits[bits.size()-1-low-bit]='0';
            }
        };
        fill(type,0);auto constant=[&](const std::string& data){auto literal=std::to_string(width)+"'b"+data;VeriNum value(0,0,0,top);value.parse(literal.c_str(),literal.size());return number(&value);};
        auto initial=constant(bits);
        if(!strings.empty()){
            needs_text=needs_struct_strings=true;
            auto boxed=node("struct_string_default",width,{initial});boxed->literal=strings;initial=boxed;
        }
        for(char& bit:bits)bit=bit=='0'?'1':'0';
        needs_two_state_cast=true;if(width>64)needs_wide=true;
        return {initial,constant(bits)};
    }
    void aggregate_default(int id,VeriVar* type) {
        if(!type||!type->unpacked_struct())return;
        auto parts=aggregate_components(type);aggregate_defaults[id]=parts.first;aggregate_state_masks[id]=parts.second;
        if(struct_has_strings(type))struct_string_signals.insert(id);
    }
    void emit_aggregate_types(std::ostream& out,size_t part=SIZE_MAX) {
        for(const auto& entry:container_aggregate_types)if(part==SIZE_MAX||signal_owner[size_t(entry.first)]==part)
            out<<"s.dynamic_aggregate_type("<<sid(entry.first)<<","<<emit(entry.second.first)<<","<<emit(entry.second.second)<<");\n";
        for(const auto& entry:object_aggregate_types)
            out<<"s.object_aggregate_type("<<entry.first.first<<","<<entry.first.second<<","<<emit(entry.second.first)<<","<<emit(entry.second.second)<<");\n";
        emit_object_print_types(out);
        std::set<std::pair<int,size_t>> text_fields;
        for(const auto& entry:classes)for(size_t field=0;field<entry.second.fields.size();++field) {
            auto* symbol=entry.second.fields[field].symbol;
            if(veri_string_value(symbol)&&associative_kind(Variable{symbol}.container_kind())&&!associative_queue_type(symbol))
                text_fields.emplace(entry.second.id,field);
        }
        for(const auto& field:text_fields)out<<"s.object_associative_string("<<field.first<<","<<field.second<<");\n";
    }
    void emit_aggregate_state_masks(std::ostream& out,size_t part=SIZE_MAX) {
        for(const auto& item:aggregate_state_masks)if(part==SIZE_MAX||signal_owner[size_t(item.first)]==part)
            out<<"s.set_state_mask("<<sid(item.first)<<","<<emit(item.second)<<");\n";
    }
    void emit_aggregate_defaults(std::ostream& out,size_t part=SIZE_MAX) {
        for(const auto& item:aggregate_defaults)if(!automatic_signals.count(item.first)&&(part==SIZE_MAX||signal_owner[size_t(item.first)]==part))
            out<<"s.set("<<sid(item.first)<<","<<emit(item.second)<<");\n";
    }
    int declaration_storage(VeriNode* declaration,const std::string& name,SignalIR value,bool persistent) {
        if(persistent) {
            // The RTL parser clones subroutine bodies for individual calls.
            // Source position survives cloning, unlike the declaration pointer.
            auto key=std::make_tuple(scope->static_domain?scope->static_domain:scope,declaration->line(),declaration->col(),name);
            auto previous=static_variables.find(key);
            if(previous!=static_variables.end())return previous->second;
            const int id=int(signals.size());static_variables.emplace(key,id);
            const auto& path=scope->static_wave_path.empty()?scope->wave_path:scope->static_wave_path;
            static_wave_paths[id]=path;value.name.clear();
            for(const auto& part:path)value.name+=part+".";
            value.name+=name;
        }
        const int id=int(signals.size());signals.push_back(std::move(value));
        if(static_cast<VeriDecl*>(declaration)->const_property())const_property_signals.insert(id);
        return id;
    }
    void declarations(VeriNode* n) {
        if(!n) return;
        if(n->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(n)->class_declaration()){register_class(static_cast<VeriSeqBlock*>(n));return;}
        if(n->detail_type()==vsDECL_PORT_DECL_LIST) { for(auto* v:static_cast<VeriPortDeclList*>(n)->port_list()) declarations(v); return; }
        if(n->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST){for(auto* v:static_cast<VeriFuncItemDeclList*>(n)->func_item())declarations(v);return;}
        if(n->detail_type()==vsDECL_TASK_ITEM_DECL_LIST){for(auto* v:static_cast<VeriTaskItemDeclList*>(n)->task_item())declarations(v);return;}
        if(n->detail_type()==veEXP_MULTI) { for(auto* v:static_cast<VeriMultiExp*>(n)->exp()) declarations(v); return; }
        if(n->detail_type()==vsDECL_BLOCK_ITEM_DECL_LIST) {
            for(auto* d:static_cast<VeriBlockItemDeclList*>(n)->block_item())declarations(d);
            return;
        }
        if(n->detail_type()==vsDECL_TF_DECL) {
            for(auto* v:static_cast<VeriTfDecl*>(n)->port_ids()) {
                auto* symbol=veri_formal_symbol(v);
                if(!symbol||symbol->tok_type()!=vtTFVAR)fail(v,"unresolved subroutine formal");
                declare_callable_variable(symbol);
            }
            return;
        }
        bool integer=n->detail_type()==vsDECL_INT;
        if(n->detail_type()!=vsDECL_VAR&&!integer)return;
        auto* d=integer?nullptr:static_cast<VeriVarDecl*>(n);
        if(d&&(d->is_typedef()||d->interface_port()))return;
        const bool explicit_automatic=static_cast<VeriDecl*>(n)->explicit_automatic();
        const bool explicit_static=static_cast<VeriDecl*>(n)->explicit_static();
        if(explicit_automatic) {
            if(!scope->procedural)fail(n,"automatic variables require a procedural scope");
            needs_explicit_automatic=needs_process_control=true;
        }
        const bool automatic=!explicit_static&&(scope->automatic_storage||explicit_automatic);
        if(d&&d->net_type()!=vvSTRING && d->net_type()!=vvEVENT && d->net_type()!=vvWIRE && d->net_type()!=vvTRI && d->net_type()!=vvREG && d->net_type()!=vvLOGIC && d->net_type()!=vvINT && d->net_type()!=vvTIME && !veri_two_state(d->net_type())&&!veri_real(d->net_type()))
            fail(n,"unsupported signal type");
        if(d)check_strength(n,d->drive());
        if(d&&d->delay())for(auto* v:d->vars())
            if((d->net_type()!=vvWIRE&&d->net_type()!=vvTRI)||v->detail_type()!=veEXP_ASSIGN)
                fail(n,"net declaration delay without an assignment is not supported yet");
        auto& vars=integer?static_cast<VeriIntDecl*>(n)->vars():d->vars();
        for(auto* v:vars) {
            if(static_cast<VeriDecl*>(n)->const_property()&&v->detail_type()!=veEXP_ASSIGN)
                fail(v,"static const class property requires a declaration initializer");
            VeriNode* lhs=v->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(v)->lval():v;
            std::string nm=name(lhs);
            auto* declared=lhs->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(lhs)->id():lhs;
            auto* symbol=declared->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(declared)->var():nullptr;
            if(!variable(symbol))fail(v,"missing signal symbol "+nm);
            register_ipc_type(symbol);
            Variable var{symbol};if(var.real_width())needs_real=true;
        if(veri_chandle_value(symbol)&&var.dynamic())fail(symbol,"chandle dynamic containers are not supported yet");
            if(class_type(symbol)!=-1&&d&&d->range())fail(v,"class handle packed dimensions are not supported yet");
            if(d&&d->net_type()==vvEVENT) {
                if(var.range_depth()||d->range()||d->is_signed()==IS_TRUE||v->detail_type()==veEXP_ASSIGN)
                    fail(v,"event arrays and declaration aliases/initializers are not supported yet");
                needs_named_events=true;scope->symbols[nm]=symbol;
                if(automatic) {
                    if(objects_signal<0){objects_signal=int(signals.size());signals.push_back({"$dsim_object_heap",64,0,false,true});}
                    needs_event_aliases=true;needs_explicit_automatic=needs_process_control=true;
                    if(!scope->ids.count(nm)) {
                        int id=declaration_storage(n,nm,{scope->path+"."+nm,64,0,false},explicit_static);
                        scope->ids[nm]=id;event_value_signals.insert(id);automatic_signals.insert(id);scope->activation_variables.insert(id);
                        if(scope->subroutine)subroutine_signals.insert(id);
                    }
                    continue;
                }
                if(!scope->ids.count(nm))scope->ids[nm]=declaration_storage(n,nm,{scope->path+"."+nm,1,0,false,false,true},explicit_static);
                continue;
            }
            if(d&&d->net_type()==vvSTRING) {
                if((var.dynamic()&&var.container_kind()!=vrQUEUE&&!associative_queue_type(symbol))||d->range()||d->inout()!=vpNO_IO)fail(v,"dynamic string arrays, packed dimensions and ports are not supported yet");
                needs_text=true;
            }
            bool net=var->net_type()==vvWIRE||var->net_type()==vvTRI;
            if(var->range_depth()&&!net&&d&&d->inout()==vpINOUT)fail(v,"variable array inout ports are not supported yet");
            if(var->dlen()<1 || var->dlen()>1048576) fail(v,"packed ranges of 1..1048576 bits are supported");
            if(var->dlen()>64)needs_wide=true;
            if(d&&d->inout()==vpIN && v->detail_type()==veEXP_ASSIGN)
                scope->defaults[nm]=static_cast<VeriAssignExp*>(v)->rval();
            if(integer||d->range()||(d->named_type()&&d->vector_scalar()==vpVECTOR)||veri_integral_atom(d->net_type()))scope->packed.insert(nm);
            scope->symbols[nm]=var.node;
            if(var->range_depth()) {
                if(scope->memories.count(nm))continue;
                if(var.dynamic()) {
                    if(var.real_width())fail(v,"dynamic real containers are not supported yet");
                    if((var.range_depth()!=1&&!associative_kind(var.container_kind()))||net||(d&&d->inout()!=vpNO_IO))fail(v,"dynamic arrays currently require one unpacked dimension and variable storage without ports");
                    if(auto* aggregate=veri_aggregate_type(var.node);aggregate&&aggregate->unpacked_struct()&&associative_queue_type(var.node))fail(v,"associative queues of structs are not supported yet");
                    const int id=declaration_storage(n,nm,{scope->path+"."+nm,var.dlen(),var.dend(),false,var.two_state(),false,false,var.real_width()},explicit_static);
                    dynamic_signals.insert(id);scope->ids[nm]=id;
                    if(auto* aggregate=veri_aggregate_type(var.node);aggregate&&aggregate->unpacked_struct())container_aggregate_types[id]=aggregate_components(aggregate);
                    if(veri_string_value(symbol))string_element_signals.insert(id);
                    if(var.container_kind()==vrQUEUE)queue_bounds[id]=var.container_bound();
                    if(associative_queue_type(symbol))object_queue_storage=true;
                    if(associative_kind(var.container_kind()))associative_signals.insert(id);
                    if(var.container_kind()==vrASSOC_UINT)unsigned_associative_signals.insert(id);
            if(var.container_kind()==vrASSOC_CLASS)class_associative_signals.insert(id);
                    if(var.container_kind()==vrASSOC_STRING){string_associative_signals.insert(id);needs_text=true;}
                    for(int axis=1;axis<var.range_depth();++axis)if(veri_array_container_kind(symbol,axis)==vrASSOC_STRING)needs_text=true;
                    if(scope->subroutine)subroutine_signals.insert(id);
                    if(automatic){automatic_signals.insert(id);scope->activation_variables.insert(id);}
                    scope->memories[nm]=int(memories.size());memories.push_back({0,{id},{{0,0,1,false}},true});
                    continue;
                }
                MemoryIR memory{};int count=1;
                for(int depth=1;depth<=var->range_depth();++depth) {
                    int first,last,size;var->get_range(depth,first,last,size);
                    const int base=std::min(first,last);
                    if(base<0||size<1||count>INT32_MAX/size||int64_t(base)+size>INT32_MAX)
                        fail(v,"memory bounds must be nonnegative and fit signed 32-bit element indices");
                    memory.dimensions.push_back({base,size,0,first>last});count*=size;
                }
                int stride=1;
                for(auto it=memory.dimensions.rbegin();it!=memory.dimensions.rend();++it){it->stride=stride;stride*=it->count;}
                memory.base=memory.dimensions.size()==1?memory.dimensions.front().base:0;
                if(v->detail_type()==veEXP_ASSIGN&&d&&d->inout()!=vpNO_IO)
                    fail(v,"whole-array declaration initializers on ports are not supported yet");
                // One owner tracks changes to a large variable array. Elements
                // live in runtime storage, rather than millions of SignalIRs
                // and generated signal-registration calls. Preserve the scalar
                // representation for nets, ports, automatic storage and waves.
                if((count>1048576||(compact_memories&&count>=1024))&&!net&&!automatic&&!wave_enabled&&!parallel_count&&
                   !var.real_width()&&!veri_aggregate_type(symbol)&&class_type(symbol)==-1&&
                   (!d||d->inout()==vpNO_IO)&&!scope->subroutine&&
                   var.net_type()!=vvSTRING) {
                    const int id=declaration_storage(n,nm,{scope->path+"."+nm,var.dlen(),var.dend(),false,var.two_state()},explicit_static);
                    memory.words.push_back(id);memory.dynamic=true;memory.fixed_count=count;
                    dynamic_signals.insert(id);scope->ids[nm]=id;
                    scope->memories[nm]=int(memories.size());memories.push_back(std::move(memory));
                    needs_indexed_select=true;
                    continue;
                }
                if(count>1048576)fail(v,"this memory storage mode supports at most 1048576 elements; large compact variable arrays require serial compilation without wave support");
                for(int i=0;i<count;++i) {
                    auto word=nm;
                    for(const auto& dim:memory.dimensions)word+="["+std::to_string(int64_t(dim.base)+(i/dim.stride)%dim.count)+"]";
                    const int id=declaration_storage(n,word,{scope->path+"."+word,var->dlen(),var->dend(),net,var.two_state(),false,false,var.real_width()},explicit_static);
                    signals[id].text_value=veri_string_value(symbol);
                    aggregate_default(id,veri_aggregate_type(var.node));
                    if(class_type(symbol)!=-1)object_signals[id]=class_type(symbol);
                    memory.words.push_back(id);
                    scope->ids[word]=id;scope->symbols[word]=var.node;
                    if(integer||d->range()||(d->named_type()&&d->vector_scalar()==vpVECTOR)||veri_integral_atom(d->net_type()))scope->packed.insert(word);
                    if(scope->subroutine)subroutine_signals.insert(id);
                    if(automatic){automatic_signals.insert(id);scope->activation_variables.insert(id);}
                }
                scope->memories[nm]=int(memories.size());memories.push_back(std::move(memory));
                needs_indexed_select=true;continue;
            }
            if(scope->ids.count(nm)) continue;
            const int id=declaration_storage(n,nm,{scope->path+"."+nm,var->dlen(),var->dend(),net,var.two_state(),false,false,var.real_width()},explicit_static);
            aggregate_default(id,veri_aggregate_type(var.node));
            signals[id].text_value=d&&d->net_type()==vvSTRING;
            if(class_type(symbol)!=-1)object_signals[id]=class_type(symbol);
            if(scope->subroutine)subroutine_signals.insert(id);
            if(automatic){automatic_signals.insert(id);scope->activation_variables.insert(id);}
            scope->ids[nm]=id;
        }
    }
    static bool assignment_pattern(VeriNode* n) {
        return n&&n->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(n)->multi_type()==vemASSIGN_PATTERN;
    }
    struct PatternType {
        int width=1;bool signed_value=false,two_state=false,text_value=false;unsigned enum_id=0;
        VeriVar* aggregate=nullptr;std::vector<std::pair<int,int>> dimensions;
    };
    PatternType pattern_type(VeriNode* target) {
        PatternType type;type.width=variable(target)?Variable{target}.dlen():veri_bit_width(target);type.signed_value=target->tok_type()==vtEXP&&static_cast<VeriExp*>(target)->is_signed()==IS_TRUE;
        // Symbols are not expressions; use their declaration's signedness.
        if(variable(target))type.signed_value=Variable{target}->is_signed()==IS_TRUE;
        type.two_state=variable(target)?Variable{target}.two_state():false;type.enum_id=enum_identity(target);type.aggregate=veri_aggregate_type(target);type.text_value=veri_string_value(target);
        auto shape=veri_array_shape(target);type.dimensions.assign(shape.dimensions.begin()+shape.unpacked,shape.dimensions.end());return type;
    }
    int64_t pattern_constant(VeriNode* n) {
        if(!veri_elaboration_constant(n))fail(n,"assignment pattern key/count must be a known integral constant");
        auto value=veri_constant_value(static_cast<VeriExp*>(n),0);
        if(!value||value->no_xz()!=IS_TRUE||value->bits()>32)fail(n,"assignment pattern key/count must be a known 32-bit integral constant");
        uint32_t bits=uint32_t(value->get_first_int());return value->is_signed()==IS_TRUE?int64_t(int32_t(bits)):int64_t(bits);
    }
    std::vector<VeriNode*> pattern_entries(VeriNode* pattern) {
        std::vector<VeriNode*> entries;
        for(auto* item:static_cast<VeriMultiExp*>(pattern)->exp()) {
            if(item->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(item)->multi_type()==vemPATTERN_REPEAT) {
                auto& args=static_cast<VeriMultiExp*>(item)->exp();auto count=pattern_constant(args.front());auto body=pattern_entries(args.back());
                if(count<=0||uint64_t(count)*body.size()>1048576)fail(item,"assignment pattern repetition count must be positive and expand to at most 1048576 entries");
                for(int64_t i=0;i<count;++i)entries.insert(entries.end(),body.begin(),body.end());
            } else entries.push_back(item);
            if(entries.size()>1048576)fail(pattern,"assignment pattern exceeds 1048576 entries");
        }
        return entries;
    }
    std::vector<VeriNode*> pattern_slots(VeriNode* pattern,size_t count,int left,int right,const std::vector<std::string>& names={}) {
        auto entries=pattern_entries(pattern);std::vector<VeriNode*> slots(count,nullptr);VeriNode* fallback=nullptr;bool positional=false,keyed=false;
        size_t ordinal=0;
        for(auto* item:entries) {
            int kind=item->detail_type()==veEXP_MULTI?static_cast<VeriMultiExp*>(item)->multi_type():-1;
            if(kind==vemPATTERN_DEFAULT) {
                keyed=true;if(fallback)fail(item,"duplicate default in assignment pattern");fallback=static_cast<VeriMultiExp*>(item)->exp().front();continue;
            }
            size_t index=ordinal++;VeriNode* value=item;
            if(kind==vemPATTERN_INDEX) {
                keyed=true;auto& args=static_cast<VeriMultiExp*>(item)->exp();auto key=pattern_constant(args.front());value=args.back();
                if(!names.empty())fail(item,"struct assignment pattern requires member names");
                if(key<std::min(left,right)||key>std::max(left,right))fail(item,"assignment pattern index is out of range");
                index=size_t(left<=right?key-left:left-key);
            } else if(item->detail_type()==veEXP_NAMED_PARAM) {
                keyed=true;auto* field=static_cast<VeriNamedParamExp*>(item);auto found=std::find(names.begin(),names.end(),field->ref());
                if(found==names.end())fail(item,"unknown assignment pattern member "+field->ref());index=size_t(found-names.begin());value=field->port_exp();
            } else positional=true;
            if(index>=count)fail(item,"too many assignment pattern entries");
            if(slots[index])fail(item,"duplicate assignment pattern index/member");slots[index]=value;
        }
        if(positional&&keyed)fail(pattern,"cannot mix positional and keyed assignment pattern entries");
        for(auto& slot:slots)if(!slot){if(!fallback)fail(pattern,"assignment pattern leaves an element/member unassigned");slot=fallback;}
        return slots;
    }
    E pattern_value(VeriNode* rhs,const PatternType& type) {
        if(!assignment_pattern(rhs)) {
            auto value=expr(rhs);
            // The standard leaves keyed/default evaluation order unspecified.
            // Keep persistent side effects out of all pattern expansions.
            bool effects=!value->event_safe||value->selection_checks||value->procedural_only;
            for(int id:value->writes)if(!event_function_storage.count(id))effects=true;
            if(effects)fail(rhs,"assignment pattern values must have no persistent side effects");
            if(type.aggregate&&type.aggregate->unpacked_struct()&&veri_aggregate_type(rhs)!=type.aggregate)
                fail(rhs,"unpacked struct pattern member requires the same struct type");
            if(type.text_value)return text_context(value);
            if(type.enum_id&&value->enum_id!=type.enum_id)fail(rhs,"enum assignment requires the same enum type or an explicit enum cast");
            if(type.two_state)needs_two_state_cast=true;
            if(type.width>64)needs_wide=true;
            auto cast=node(type.two_state?"fixed_cast_2":"fixed_cast",type.width,{value});cast->signed_value=type.signed_value;cast->enum_id=type.enum_id;return cast;
        }
        if(type.enum_id)fail(rhs,"assignment pattern cannot construct an enum without an explicit enum cast");
        std::vector<E> values;
        if(type.aggregate&&type.width==type.aggregate->dlen()) {
            const auto& fields=type.aggregate->packed_fields();std::vector<std::string> names;
            int total=0;for(const auto& field:fields){names.push_back(field.name);total+=field.symbol->dlen();}
            if(total!=type.width)fail(rhs,"packed union assignment patterns are not supported yet");
            auto slots=pattern_slots(rhs,fields.size(),0,int(fields.size())-1,names);size_t i=0;
            for(const auto& field:fields) {
                auto element=pattern_type(field.symbol);
                // Packed storage has one state representation. In a mixed
                // struct, writing a bit member preserves raw X/Z; reads cast it.
                if(!type.aggregate->unpacked_struct())element.two_state=type.two_state;
                auto value=pattern_value(slots[i++],element);
                if(element.text_value)value=node("struct_string_pack",1,{value});
                values.push_back(value);
            }
        } else {
            if(type.dimensions.empty())fail(rhs,"assignment pattern requires an array or packed struct context");
            const auto bounds=type.dimensions.front();const auto count=size_t(std::abs(int64_t(bounds.first)-bounds.second)+1);
            if(count>1048576||type.width%count)fail(rhs,"invalid assignment pattern dimension");
            auto slots=pattern_slots(rhs,count,bounds.first,bounds.second);auto element=type;element.width/=int(count);element.signed_value=false;element.enum_id=0;
            element.dimensions.erase(element.dimensions.begin());
            for(auto* slot:slots)values.push_back(pattern_value(slot,element));
        }
        E result;for(auto& value:values)result=result?node("concat",result->width+value->width,{result,value}):value;
        result=node("cast",type.width,{result});result->signed_value=type.signed_value;result->enum_id=type.enum_id;
        if(type.width>64)needs_wide=true;return result;
    }
    VeriVar* unpacked_cast_type(VeriNode* n) const {
        if(n->detail_type()!=veEXP_BIN)return nullptr;
        auto* binary=static_cast<VeriBinaryExp*>(n);
        if(!veri_is_cast(binary->op())||binary->lval()->detail_type()!=veEXP_PRI)return nullptr;
        auto* symbol=static_cast<VeriPrimaryExp*>(binary->lval())->var();
        return symbol&&symbol->tok_type()==vtTYPE&&static_cast<VeriVar*>(symbol)->range_depth()?static_cast<VeriVar*>(symbol):nullptr;
    }
    bool runtime_stream_operand(VeriNode* n) const {
        if(unpacked_cast_type(n))return true;
        if(unpacked_value(n)&&veri_array_shape(n).unbound)return true;
        if(n->detail_type()==veEXP_BIN) {
            auto* binary=static_cast<VeriBinaryExp*>(n);
            if(veri_streaming(n)||veri_is_cast(binary->op()))return runtime_stream_operand(binary->rval());
        }
        if(n->detail_type()==veEXP_MULTI)for(auto* part:static_cast<VeriMultiExp*>(n)->exp())if(runtime_stream_operand(part))return true;
        return false;
    }
    void stream_element_type(VeriNode* source,Variable type) {
        if(type.real_width()||veri_string_value(type.node)||class_type(type.node)>=0||
           (veri_aggregate_type(type.node)&&veri_aggregate_type(type.node)->unpacked_struct())||associative_kind(type.container_kind()))
            fail(source,"bit stream requires integral elements without associative storage");
        if(type.dlen()>64)needs_wide=true;
    }
    E runtime_stream_bits(VeriNode* n) {
        needs_array_stream=true;
        if(veri_streaming(n)) {
            auto* stream=static_cast<VeriBinaryExp*>(n);const int slice=veri_stream_slice(n);
            if(!slice)fail(n,"stream slice size must be a known positive integral constant in 1..1048576");
            auto bits=runtime_stream_bits(stream->rval());
            if(stream->op()==vtSTREAM_RIGHT)return bits;
            auto result=node("call",1,{bits});result->array_value=true;result->literal="return stream_reverse(std::move(call_arg0),"+std::to_string(slice)+");";return result;
        }
        if(n->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(n)->multi_type()==vemCONCAT_EXP) {
            std::vector<E> parts;for(auto* part:static_cast<VeriMultiExp*>(n)->exp())parts.push_back(runtime_stream_bits(part));
            auto result=node("call",1,parts);result->array_value=true;result->literal="StreamBits joined;";
            for(size_t i=0;i<parts.size();++i)result->literal+="stream_extend(joined,call_arg"+std::to_string(i)+");";
            result->literal+="return joined;";return result;
        }
        if(auto* type=unpacked_cast_type(n)) {
            auto values=array_cast_values(static_cast<VeriBinaryExp*>(n),type);
            auto result=node("call",1,{values});result->array_value=true;result->literal="return stream_array(call_arg0);";return result;
        }
        if(unpacked_value(n)) {
            auto* symbol=veri_array_element_symbol(n);if(!symbol)fail(n,"bit stream requires an unpacked value with an element type");
            stream_element_type(n,Variable{symbol});auto values=array_values(n,Variable{symbol});
            auto result=node("call",1,{values});result->array_value=true;result->literal="return stream_array(call_arg0);";return result;
        }
        auto value=expr(n);
        if(value->array_value||value->text_value||value->real_width||value->object_type!=-1)fail(n,"bit stream requires packed integral values");
        auto result=node("call",1,{value});result->array_value=true;result->literal="return stream_scalar(call_arg0);";return result;
    }
    E runtime_stream_packed(VeriNode* source,int width,bool two=false,bool strict=false) {
        if(width>64)needs_wide=true;
        auto value=node("call",width,{runtime_stream_bits(source)});
        value->literal="return stream_pack(call_arg0,"+std::to_string(width)+","+(two?"true":"false")+","+(strict?"true":"false")+");";return value;
    }
    E runtime_stream_values(VeriNode* source,Variable target,int count=-1,bool strict=false,int bound=-1) {
        stream_element_type(source,target);
        auto result=node("call",target.dlen(),{runtime_stream_bits(source)});result->array_value=true;
        result->literal="return stream_unpack(call_arg0,"+std::to_string(target.dlen())+","+(target.two_state()?"true":"false")+","+std::to_string(count)+","+(strict?"true":"false")+","+std::to_string(bound)+");";return result;
    }
    E array_cast_values(VeriBinaryExp* cast,VeriVar* type) {
        Variable target{type};int count=1;
        if(type->range_depth()==1&&(target.container_kind()==vrQUEUE||target.container_kind()==vrOPEN))count=-1;
        else for(unsigned axis=1;axis<=unsigned(type->range_depth());++axis) {
            if(veri_array_container_kind(type,axis-1)>=vrOPEN)fail(cast,"bit-stream cast requires fixed arrays or one dynamic dimension");
            int first,last,length;target.get_range(axis,first,last,length);
            if(length<1||count>1048576/length)fail(cast,"bit-stream cast array size exceeds supported range");count*=length;
        }
        return runtime_stream_values(cast->rval(),target,count,!veri_streaming(cast->rval()),target.container_kind()==vrQUEUE?target.container_bound():-1);
    }
    bool string_stream(VeriNode* source) {
        if(source->detail_type()==veEXP_MULTI) {
            auto* list=static_cast<VeriMultiExp*>(source);
            if(list->multi_type()!=vemCONCAT_EXP)return false;
            for(auto* item:list->exp())if(string_stream(item))return true;
            return false;
        }
        auto* symbol=veri_array_element_symbol(source);
        return veri_dynamic_string_value(source)||(symbol&&veri_dynamic_string_value(symbol));
    }
    E string_stream_value(VeriNode* source) {
        needs_text=true;
        if(source->detail_type()==veEXP_MULTI) {
            auto* list=static_cast<VeriMultiExp*>(source);
            if(list->multi_type()!=vemCONCAT_EXP)fail(source,"string stream requires a concatenation list");
            std::vector<E> parts;
            for(auto* item:list->exp())parts.push_back(string_stream_value(item));
            auto result=node("text_method",1,std::move(parts));result->text_value=true;
            result->literal="std::string joined;";
            for(size_t i=0;i<result->args.size();++i)result->literal+="joined+=text_arg"+std::to_string(i)+".text_value();";
            result->literal+="return V::text(std::move(joined));";return result;
        }
        if(!unpacked_value(source)) {
            auto value=expr(source);
            if(!value->text_value)fail(source,"mixed integral and string streaming is not supported yet");
            return value;
        }
        auto* symbol=veri_array_element_symbol(source);
        if(!symbol||!veri_string_value(symbol)||veri_array_shape(source).unpacked!=1)
            fail(source,"string streaming requires one-dimensional string storage");
        auto values=array_values(source,Variable{symbol});
        auto result=node("call",1,{values});result->text_value=true;
        result->literal="std::string joined;for(const auto& part:call_arg0)joined+=part.text_value();return V::text(std::move(joined));";
        return result;
    }
    E stream_value(VeriNode* stream,E input) {
        const int size=veri_stream_slice(stream);
        if(!size)fail(stream,"stream slice size must be a known positive integral constant in 1..1048576");
        if(input->width>64)needs_wide=true;
        auto value=node(static_cast<VeriBinaryExp*>(stream)->op()==vtSTREAM_LEFT?"stream":"cast",input->width,{input});
        value->literal=std::to_string(size);return value;
    }
    E stream_payload(VeriNode* n) {
        if(n->detail_type()==veEXP_MULTI) {
            auto* list=static_cast<VeriMultiExp*>(n);
            if(list->multi_type()!=vemCONCAT_EXP)fail(n,"stream requires a concatenation list");
            E result;for(auto* item:list->exp()) {
                auto value=stream_payload(item);result=result?node("concat",result->width+value->width,{result,value}):value;
            }
            return result;
        }
        if(!unpacked_value(n))return expr(n);
        auto view=array_copy_view(n);
        if(view.offset)fail(n,"stream source requires static array indices");
        E result;
        for(int id:view.words){auto value=signal_expr(id);result=result?node("concat",result->width+value->width,{result,value}):value;}
        if(result->width>64)needs_wide=true;return result;
    }
    E packed_context(VeriNode* rhs,int width) {
        if(veri_streaming(rhs)&&runtime_stream_operand(rhs)&&!string_stream(static_cast<VeriBinaryExp*>(rhs)->rval()))return runtime_stream_packed(rhs,width);
        auto value=expr(rhs);if(value->packed_value)value=value->packed_value;if(value->text_value)return packed_string(value,width);if(!veri_streaming(rhs))return value;
        if(width<value->width)fail(rhs,"stream packing destination is smaller than source");
        if(width>value->width){const int pad=width-value->width;auto zero=node("literal",pad);zero->literal="V(0,0,"+std::to_string(pad)+")";value=node("concat",width,{value,zero});}
        if(width>64)needs_wide=true;return value;
    }
    bool runtime_replication(VeriNode* n) const {
        if(n->detail_type()==veEXP_MCONCAT) {
            auto* repeat=static_cast<VeriMultiConcatExp*>(n);
            return !veri_elaboration_constant(repeat->exp1())||runtime_replication(repeat->exp2());
        }
        if(n->detail_type()==veEXP_MULTI) {
            auto* list=static_cast<VeriMultiExp*>(n);
            if(list->multi_type()==vemCONCAT_EXP)for(auto* item:list->exp())if(runtime_replication(item))return true;
        }
        if(n->detail_type()==veEXP_QUES) {
            auto* q=static_cast<VeriQuesExp*>(n);return runtime_replication(q->choice1())||runtime_replication(q->choice2());
        }
        return false;
    }
    E packed_string(E value,int width) {
        if(width>64)needs_wide=true;
        auto packed=node("text_method",width,{value});
        packed->literal="return packed_text(text_arg0.text_value(),"+std::to_string(width)+");";return packed;
    }
    void string_concat_operand(VeriNode* source) {
        while(source->detail_type()==veEXP_UNA) {
            auto* unary=static_cast<VeriUnaryExp*>(source);
            if(unary->op()!=vtUADD&&unary->op()!=vtUSUB)break;source=unary->exp_child();
        }
        if(source->detail_type()==veEXP_PRI) {
            auto* literal=static_cast<VeriPrimaryExp*>(source);
            const auto& spelling=literal->str();const auto quote=spelling.find('\'');
            if(literal->pri_type()==veNUM&&(quote==std::string::npos||(quote==0&&spelling.size()>2)))
                fail(source,"mixed string concatenation requires sized integral operands");
        }
    }
    E text_expression(VeriNode* n) {
        if(n->detail_type()==veEXP_MCONCAT)return text_context(replication_value(static_cast<VeriMultiConcatExp*>(n),true));
        if(n->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(n)->multi_type()==vemCONCAT_EXP&&runtime_replication(n)) {
            std::vector<E> args;
            for(auto* item:static_cast<VeriMultiExp*>(n)->exp()){string_concat_operand(item);args.push_back(text_expression(item));}
            auto joined=node("text_method",1,args);joined->text_value=true;
            joined->literal="std::string text_joined;";
            for(size_t i=0;i<args.size();++i)joined->literal+="text_joined+=text_arg"+std::to_string(i)+".text_value();";
            joined->literal+="return V::text(std::move(text_joined));";return joined;
        }
        if(n->detail_type()==veEXP_QUES&&runtime_replication(n)) {
            auto* q=static_cast<VeriQuesExp*>(n);
            auto value=node("text_mux",1,{expr(q->ques()),text_expression(q->choice1()),text_expression(q->choice2())});value->text_value=true;return value;
        }
        return text_context(expr(n));
    }
    E replication_value(VeriMultiConcatExp* repeat,bool string_context) {
        if(auto* type=veri_aggregate_type(repeat->exp2());type&&type->unpacked_struct())fail(repeat,"unpacked struct cannot be replicated as a packed value");
        auto count=expr(repeat->exp1());
        if(count->text_value||count->real_width||count->object_type!=-1||count->array_value)fail(repeat,"replication count requires an integral value");
        auto value=string_context&&runtime_replication(repeat->exp2())?text_expression(repeat->exp2()):expr(repeat->exp2());
        if(veri_elaboration_constant(repeat->exp1()))
            if(auto* constant=static_cast<VeriExp*>(repeat->exp1())->calc_value())count=number(constant);
        const bool packed_count=count->op=="literal"&&!count->unknown&&!count->host_overflow&&!count->negative&&count->value&&count->value<=uint64_t(1048576/value->width);
        if(packed_count&&(!value->text_value||value->packed_value)) {
            auto result=node("replicate",int(count->value)*value->width,{value});result->literal=std::to_string(count->value);needs_replication=true;
            if(result->width>64)needs_wide=true;return result;
        }
        if(!string_context&&!value->text_value&&!veri_string_value(repeat->exp2()))
            fail(repeat,"replication count must be a positive constant expression, with total width <=1048576");
        needs_text=needs_string_replication=true;
        auto result=node("text_repeat",1,{count,text_context(value)});result->text_value=true;result->literal=count->signed_value?"true":"false";return result;
    }
    E text_context(E value) {
        if(value->object_type!=-1)fail(nullptr,"class handle cannot be converted to a string");
        if(value->real_width||value->array_value)fail(nullptr,"string conversion requires a string or packed integral value");
        needs_text=true;
        if(value->text_value)return value;
        auto text=node("text_method",1,{value});text->text_value=true;
        text->literal="return V::text(format(text_arg0,'s'));";return text;
    }
    E numeric_context(E value,int real_width,int width) {
        if(!real_width&&!value->real_width)return value;
        if(value->text_value||value->object_type!=-1)fail(nullptr,"real conversion requires a numeric value");
        needs_real=true;auto converted=node("real_convert",width,{value});converted->real_width=real_width;converted->signed_value=real_width||value->signed_value;return converted;
    }
    E argument_context(VeriNode* rhs,VeriNode* formal) {
        auto* destination=veri_aggregate_type(formal);auto* source=veri_aggregate_type(rhs);
        if((destination&&destination->unpacked_struct())||(source&&source->unpacked_struct()))
            if(!assignment_pattern(rhs)&&destination!=source)fail(rhs,"unpacked struct argument requires the same struct type");
        if(class_type(formal)!=-1)return expr(rhs);
        auto value=assignment_pattern(rhs)?pattern_value(rhs,pattern_type(formal)):
            veri_string_value(formal)?text_expression(rhs):veri_real_width(formal)?expr(rhs):packed_context(rhs,Variable{formal}->dlen());
        return numeric_context(value,veri_real_width(formal),Variable{formal}.dlen());
    }
    E context_expr(VeriNode* rhs,VeriNode* target) {
        auto* destination=veri_aggregate_type(target);auto* source=veri_aggregate_type(rhs);
        if((destination&&destination->unpacked_struct())||(source&&source->unpacked_struct())) {
            if(!assignment_pattern(rhs)&&destination!=source)fail(rhs,"unpacked struct assignment requires the same struct type");
        }

        if(veri_streaming(target)) {
            if(assignment_pattern(rhs))fail(rhs,"stream target requires a packed source");
            auto input=expr(rhs);const int width=lvalue(target).width;
            if(input->width<width)fail(rhs,"stream unpacking source is smaller than destination");
            if(input->width>width){auto slice=node("slice",width,{input});slice->literal=std::to_string(input->width-width)+","+std::to_string(width);input=slice;}
            return stream_value(target,input);
        }
        if(veri_streaming(rhs)) {
            if(veri_string_value(target))return text_context(expr(rhs));
            return packed_context(rhs,lvalue(target).width);
        }
        if(veri_string_value(target)&&!assignment_pattern(rhs))return text_expression(rhs);
        auto value=assignment_pattern(rhs)?pattern_value(rhs,pattern_type(target)):expr(rhs);
        if(veri_string_value(target)) {
            return text_context(value);
        } else if(value->packed_value)value=value->packed_value;
        else if(value->text_value&&!veri_real_width(target)&&class_type(target)==-1)value=packed_string(value,veri_bit_width(target));
        return numeric_context(value,veri_real_width(target),veri_bit_width(target));
    }
    void unpacked_pattern(VeriNode* rhs,const std::vector<MemoryDimension>& dimensions,size_t depth,const PatternType& element,std::vector<E>& values) {
        if(depth==dimensions.size()){values.push_back(pattern_value(rhs,element));return;}
        if(!assignment_pattern(rhs))fail(rhs,"nested unpacked assignment pattern requires a pattern at each dimension");
        const auto& d=dimensions[depth];int left=d.descending?d.base+d.count-1:d.base,right=d.descending?d.base:d.base+d.count-1;
        auto slots=pattern_slots(rhs,size_t(d.count),left,right);
        for(auto* slot:slots)unpacked_pattern(slot,dimensions,depth+1,element,values);
    }
    void decl_init(VeriNode* n,bool automatic_only=false) {
        if(!n)return;
        if(n->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST){for(auto* v:static_cast<VeriFuncItemDeclList*>(n)->func_item())decl_init(v,automatic_only);return;}
        if(n->detail_type()==vsDECL_TASK_ITEM_DECL_LIST){for(auto* v:static_cast<VeriTaskItemDeclList*>(n)->task_item())decl_init(v,automatic_only);return;}
        if(n->detail_type()==vsDECL_BLOCK_ITEM_DECL_LIST) {
            for(auto* d:static_cast<VeriBlockItemDeclList*>(n)->block_item())decl_init(d,automatic_only);
            return;
        }
        bool integer=n->detail_type()==vsDECL_INT;
        if(n->detail_type()!=vsDECL_VAR&&!integer)return;
        auto* d=integer?nullptr:static_cast<VeriVarDecl*>(n);
        if(d&&(d->is_typedef()||d->interface_port()))return;
        auto& vars=integer?static_cast<VeriIntDecl*>(n)->vars():d->vars();
        for(auto* v:vars) if(v->detail_type()==veEXP_ASSIGN) {
            if(d&&d->inout()==vpIN) continue; // Port defaults apply only when disconnected.
            auto* a=static_cast<VeriAssignExp*>(v);
            auto* lhs=a->lval();
            if(lhs->detail_type()==veEXP_ARRAY)lhs=static_cast<VeriArrayExp*>(lhs)->id();
            const int object=dynamic_object(lhs);
            const bool fixed=object<0&&unpacked_value(lhs);
            const int id=object>=0?object:fixed?array_copy_view(lhs).words.front():signal(a->lval());
            if(automatic_only&&!automatic_signals.count(id))continue;
            if(static_cast<VeriDecl*>(n)->explicit_static()&&!static_initializers.insert(id).second)continue;
            if(object>=0||fixed) {
                DeclarationInit init{id,{},std::make_shared<ProcessIR>()};
                if(object>=0)dynamic_array_assignment(*init.process,id,a->rval(),Variable{static_cast<VeriPrimaryExp*>(lhs)->var()});
                else {
                    if(signals[id].net)fail(v,"net array declaration initializers are not supported yet");
                    if(a->rval()->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(a->rval())->multi_type()==vemDYNAMIC_NEW)
                        fail(v,"new requires a dynamic array declaration");
                    array_assignment(*init.process,lhs,a->rval(),false,nullptr,-1);
                    // Initializers cannot suspend. Keep their copy snapshots local
                    // to this entry, independent of resumable process buffers.
                    std::string code="{";
                    for(size_t k=0;k<init.process->array_values.size();++k)
                        code+="std::vector<V> array_value"+std::to_string(k)+"("+std::to_string(init.process->array_values[k])+");";
                    for(const auto& inst:init.process->instructions)code+=inst.code;
                    code+="}";init.process->instructions.clear();init.process->array_values.clear();add(*init.process,std::move(code));
                }
                if(!automatic_signals.count(id))for(int read:init.process->reads)
                    if(automatic_signals.count(read))fail(v,object>=0?"static dynamic array initializer cannot reference an automatic variable":"static fixed array initializer cannot reference an automatic variable");
                auto& list=automatic_signals.count(id)?scope->activation_initializers:initializers;
                list.push_back(std::move(init));continue;
            }
            auto e=context_expr(a->rval(),a->lval());enum_assignment(a->lval(),e);
            if(e->text_value!=signals[id].text_value)fail(v,"string assignment requires matching string values");
            if(signals[id].net) continuous(a->lval(),e,d->delay());
            else if(automatic_signals.count(id))scope->activation_initializers.push_back({id,e,{}});
            else {
                for(int source:e->reads)if(automatic_signals.count(source))
                    fail(v,"nonconstant declaration initialization cannot reference an automatic variable from static storage");
                for(int source:e->function_reads)if(automatic_signals.count(source))
                    fail(v,"nonconstant declaration initialization cannot reference an automatic variable from static storage");
                initializers.push_back({id,e,{}});
            }
        }
    }
    void write(ProcessIR& p,const LValueIR& target,E value,bool nba,bool drive,const std::string& delay={},const std::string& event={},const std::string& count="1") {
        if(std::any_of(target.parts.begin(),target.parts.end(),[](const PartIR& part){return bool(part.virtual_handle);})) {
            if(target.parts.size()!=1||drive)fail(nullptr,"virtual interface assignment requires a single procedural target");
            const auto& part=target.parts.front();read(p,value);read(p,part.virtual_handle);if(part.index)read(p,part.index);
            const auto first=p.instructions.size();
            add(p,"{auto vif_value="+emit(value,target.width)+";auto vif_handle="+emit(part.virtual_handle)+";"+(part.index?"auto vif_index="+emit(part.index)+";":"")+"if(vif_handle.b||!vif_handle.a)throw std::runtime_error(\"null virtual interface dereference\");switch(vif_handle.a){");
            auto saved=node("literal",target.width);saved->literal="vif_value";saved->text_value=value->text_value;saved->real_width=value->real_width;
            for(const auto& choice:part.virtual_targets) {
                add(p,"case "+std::to_string(choice.first)+"ULL:{");auto selected=part;selected.signal=choice.second;selected.virtual_handle={};selected.virtual_targets.clear();
                if(part.index){selected.index=node("literal",part.index->width);selected.index->literal="vif_index";selected.index->signed_value=part.index->signed_value;}
                LValueIR plain;plain.width=target.width;plain.parts.push_back(selected);write(p,plain,saved,nba,drive,delay,event,count);add(p,"break;}");
            }
            add(p,"default:throw std::runtime_error(\"invalid virtual interface handle\");}}");
            std::string combined;for(size_t i=first;i<p.instructions.size();++i)combined+=p.instructions[i].code;
            p.instructions.resize(first);add(p,combined);return;
        }
        if(nba)for(const auto& part:target.parts)
            if(part.struct_string_field||struct_string_signals.count(part.signal)||container_aggregate_types.count(part.signal))
                fail(nullptr,"nonblocking assignment to a string or a struct containing strings is not allowed");
        if(target.parts.size()==1&&target.parts[0].struct_string_field) {
            if(drive)fail(nullptr,"struct string fields require procedural assignment");
            auto plain=target;plain.parts[0].struct_string_field=false;
            auto boxed=node("struct_string_pack",1,{text_context(value)});write(p,plain,boxed,nba,drive,delay,event,count);return;
        }
        if(target.parts.size()==1){const auto& part=target.parts[0];value=numeric_context(value,part.object?part.object_real:signals[part.signal].real_width,target.width);}
        if(std::any_of(target.parts.begin(),target.parts.end(),[](const PartIR& part){return bool(part.receiver_effect);})) {
            auto plain=target;std::string prefix="{";
            for(auto& part:plain.parts)if(part.receiver_effect){read(p,part.receiver_effect);prefix+="(void)("+emit(part.receiver_effect)+");";part.receiver_effect={};}
            const auto first=p.instructions.size();write(p,plain,value,nba,drive,delay,event,count);
            p.instructions[first].code=prefix+p.instructions[first].code;
            p.instructions.back().code+="}";return;
        }
        if(std::any_of(target.parts.begin(),target.parts.end(),[](const PartIR& part){return bool(part.associative_ref);})) {
            if(target.parts.size()!=1||nba||drive||!delay.empty()||!event.empty())fail(nullptr,"associative element requires an immediate blocking assignment without concatenation");
            const auto& part=target.parts.front();writable(part.signal);read(p,value);read(p,part.associative_ref);read(p,part.word_index);if(part.index)read(p,part.index);
            p.touches.insert(part.signal);p.partial_writes.insert(part.signal);p.writes.push_back({part.signal,0,signals[part.signal].width,0});
            std::string code="{auto associative_value="+emit(value,target.width)+";auto associative_ref="+emit(part.associative_ref)+";auto associative_key="+emit(part.word_index)+";";
            if(part.index||part.lo||part.width!=part.object_width) {
                const auto selection=part.index?"indexed_part(0,"+std::to_string(part.object_width)+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+",0,"+(part.index->signed_value?"true":"false")+")":"Part{0,"+std::to_string(part.lo)+","+std::to_string(part.width)+",0}";
                code+="s."+std::string(part.associative_queue?"associative_queue_write_slice":"associative_write_slice")+"(associative_ref,associative_key,"+selection+",associative_value,"+(part.object_two_state?"true":"false")+(part.associative_queue?","+std::to_string(part.object_width)+","+std::to_string(part.associative_queue_bound):std::string())+");}";
            } else code+="s."+std::string(part.associative_queue?"associative_queue_write":"associative_write")+"(associative_ref,associative_key,associative_value,"+std::to_string(part.object_width)+","+(part.object_two_state?"true":"false")+(part.associative_queue?","+std::to_string(part.associative_queue_bound):std::string())+");}";
            add(p,code);return;
        }
        if(std::any_of(target.parts.begin(),target.parts.end(),[](const PartIR& part){return bool(part.object);})) {
            if(target.parts.size()!=1||nba||drive||!delay.empty()||!event.empty())fail(nullptr,"class property currently requires an immediate blocking assignment without concatenation");
            const auto& part=target.parts.front();
            if(part.object_const&&!part.object_initializer) {
                if(part.object_const_initialized)fail(nullptr,"const class property with declaration initializer is read-only");
                auto* owner=scope;while(owner&&!owner->subroutine)owner=owner->parent;
                if(!owner||!owner->constructor_class||int(owner->constructor_class->idx())!=part.object_type)
                    fail(nullptr,"instance const class property can only be assigned in its declaring class constructor");
            }
            if(value->packed_value&&!part.object_text)value=value->packed_value;
            if(part.object_text!=value->text_value)fail(nullptr,"class string property requires a matching string value");
            read(p,value);read(p,part.object);if(part.index)read(p,part.index);
            if(part.object_associative||part.object_queue)read(p,part.word_index);
            p.touches.insert(objects_signal);p.partial_writes.insert(objects_signal);p.writes.push_back({objects_signal,0,64,0});
            std::string code="{auto field_receiver="+emit(part.object)+";auto field_value="+emit(value,part.object_text?0:target.width)+";";
            if(part.object_associative||part.object_queue) {
                const auto method=part.object_queue?std::string("object_queue"):std::string("associative");
                code+="auto field_key="+emit(part.word_index)+";auto field_array=s.object_"+std::string(part.object_queue?"queue":"associative")+"(field_receiver,"+std::to_string(part.object_type)+","+std::to_string(part.object_field)+","+(part.object_queue?std::string():std::to_string(part.object_width)+",")+sid(objects_signal)+(part.object_queue?std::string():","+std::string(part.object_unsigned_key?"true":"false")+","+(part.object_class_key?"true":"false"))+");";
                if(part.index||part.lo||part.width!=part.object_width) {
                    code+="auto field_selection="+(part.index?"indexed_part(0,"+std::to_string(part.object_width)+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+",0,"+(part.index->signed_value?"true":"false")+")":"Part{0,"+std::to_string(part.lo)+","+std::to_string(part.width)+",0}")+";";
                    code+="s."+method+"_write_slice(field_array,field_key,field_selection,field_value,"+(part.object_two_state?"true":"false")+(part.object_queue?","+std::to_string(part.object_width)+","+std::to_string(part.object_queue_bound):std::string())+");}";
                } else code+="s."+method+"_write(field_array,field_key,field_value,"+std::to_string(part.object_width)+","+(part.object_two_state?"true":"false")+(part.object_queue?","+std::to_string(part.object_queue_bound):std::string())+");}";
                add(p,std::move(code));return;
            }
            if(part.index||part.lo||part.width!=part.object_width) {
                code+="auto field_selection="+(part.index?"indexed_part(0,"+std::to_string(part.object_width)+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+",0,"+(part.index->signed_value?"true":"false")+")":"Part{0,"+std::to_string(part.lo)+","+std::to_string(part.width)+",0}")+";";
                code+="field_value=replace(s.object_get(field_receiver,"+std::to_string(part.object_type)+","+std::to_string(part.object_field)+"),field_selection.lo,field_selection.width,slice(field_value,field_selection.rhs_lo,field_selection.width));";
            } else if(!part.object_text)code+="field_value=field_value.size("+std::to_string(part.object_width)+");";
            if(part.object_two_state)code+="field_value=two_state_value(std::move(field_value));";
            code+=std::string(part.object_const&&!part.object_initializer?"s.object_set_const(":"s.object_set(")+"field_receiver,"+std::to_string(part.object_type)+","+std::to_string(part.object_field)+",std::move(field_value),"+sid(objects_signal)+");}";
            add(p,std::move(code));return;
        }
        for(const auto& part:target.parts)if((part.index&&part.index->text_value)||(part.word_index&&part.word_index->text_value&&!string_associative_signals.count(part.signal)))
            fail(nullptr,"string cannot be used as an integral assignment index");
        bool text_target=false;for(const auto& part:target.parts)text_target|=signals[part.signal].text_value||string_element_signals.count(part.signal);
        if(!text_target&&value->packed_value)value=value->packed_value;
        if(value->text_value||text_target) {
            if(value->text_value&&text_target&&target.parts.size()==1&&target.parts[0].word_index&&
               !memories[size_t(target.parts[0].memory)].dynamic&&!target.parts[0].index&&!drive) {
                if(nba||!delay.empty()||!event.empty())fail(nullptr,"fixed string elements require immediate blocking assignment");
                const auto& part=target.parts[0];read(p,value);read(p,part.word_index);
                for(int id:memories[size_t(part.memory)].words){writable(id);p.touches.insert(id);p.partial_writes.insert(id);p.nonstatic_writes.insert(id);p.writes.push_back({id,0,signals[id].width,0});}
                add(p,"{auto text_value="+emit(value)+";auto text_index="+emit(part.word_index,part.word_index->signed_value?64:0)+";int text_target=memory_signal("+memory_table(part.memory)+",text_index"+(parallel_count?",sid.data()":"")+");if(text_target>=0)s.set(text_target,std::move(text_value));}");return;
            }
            if(!value->text_value||!text_target||target.parts.size()!=1||target.parts[0].index||(target.parts[0].word_index&&!string_element_signals.count(target.parts[0].signal))||drive)
                fail(nullptr,"string assignment requires a whole string variable and string value");
            if(nba||!event.empty())fail(nullptr,"string nonblocking assignments are not supported yet");
        }
        // Writer-conflict ranges conservatively cover every possible dynamic
        // target. Keep lexical whole-variable stores separately: those ranges
        // alone cannot prove that every bit is excluded from implicit sensitivity.
        for(const auto& part:target.parts)
            if(!part.index&&!part.word_index&&!part.lo&&part.width==signals[part.signal].width)
                p.whole_writes.insert(part.signal);
        for(const auto& part:target.parts)if(part.index||part.word_index) {
            if(part.word_index)for(int id:memories[size_t(part.memory)].words)p.nonstatic_writes.insert(id);
            else p.nonstatic_writes.insert(part.signal);
        }
        bool dynamic=false;for(const auto& part:target.parts)dynamic|=part.memory>=0&&memories[size_t(part.memory)].dynamic;
        for(const auto& part:target.parts)if(queue_bounds.count(part.signal)||associative_signals.count(part.signal)) {
            if(nba||!delay.empty()||!event.empty())fail(nullptr,"queue and associative element timed/NBA assignments are not supported yet");
            if(target.parts.size()>1)fail(nullptr,"queue and associative elements in concatenation targets are not supported yet");
        }
        if(nba&&(dynamic||!event.empty()||target.parts.size()!=1||target.parts[0].index||
           target.parts[0].lo||target.parts[0].width!=target.width||target.width!=signals[target.parts[0].signal].width))
            needs_parts_nba=true;
        if(dynamic&&target.parts.size()>1) {
            if(drive)fail(nullptr,"dynamic array elements require a procedural assignment target");
            read(p,value);
            for(const auto& part:target.parts) {
                const bool container=part.memory>=0&&memories[size_t(part.memory)].dynamic;
                if(part.word_index) {
                    read(p,part.word_index);
                    for(int id:memories[size_t(part.memory)].words)writable(id);
                } else writable(part.signal);
                if(signals[part.signal].net)fail(nullptr,"procedural assignment requires a variable target");
                if(nba&&!container&&automatic_signals.count(part.signal))fail(nullptr,"nonblocking assignment to an automatic variable is not allowed");
                if(part.index)read(p,part.index);
                if(part.word_index) {
                    for(int id:memories[size_t(part.memory)].words) {
                        p.touches.insert(id);p.partial_writes.insert(id);p.writes.push_back({id,0,signals[id].width,0});
                    }
                } else {
                    p.touches.insert(part.signal);
                    if(part.index||part.width!=signals[part.signal].width)p.partial_writes.insert(part.signal);
                    if(part.index)p.writes.push_back({part.signal,part.view_lo,part.view_width?part.view_width:signals[part.signal].width,0});
                    else p.writes.push_back(part);
                }
            }
            std::string code="{";
            if(!delay.empty())code+="auto concat_delay="+delay+";";
            code+="auto concat_value="+emit(value,target.width)+";std::vector<Part> concat_parts("+std::to_string(target.parts.size())+");";
            // Parts carry RHS offsets from right to left; evaluate all addresses
            // left to right before committing any destination.
            for(size_t i=target.parts.size();i-->0;) {
                const auto& part=target.parts[i];const auto suffix=std::to_string(i);
                const bool container=part.memory>=0&&memories[size_t(part.memory)].dynamic;
                std::string selected_signal=sid(part.signal);
                if(container) {
                    code+="auto concat_index"+suffix+"="+emit(part.word_index,part.word_index->signed_value?64:0)+";";
                    code+="auto concat_target"+suffix+"=s.dynamic_part("+sid(part.signal)+",concat_index"+suffix+","+std::to_string(signals[part.signal].width)+","+(event.empty()?"false":"true")+","+(nba?"false":"true")+");";
                    selected_signal="0";
                } else if(part.word_index) {
                    code+="const int concat_signal"+suffix+"=memory_signal("+memory_table(part.memory)+","+emit(part.word_index,part.word_index->signed_value?64:0)+(parallel_count?",sid.data()":"")+");";
                    selected_signal="concat_signal"+suffix;
                }
                std::string selection="Part{"+selected_signal+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+"}";
                if(part.index)selection=(part.view_width?"view_indexed_part(":"indexed_part(")+selected_signal+","+(part.view_width?std::to_string(part.view_lo)+","+std::to_string(part.view_width):std::to_string(signals[part.signal].width))+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+","+std::to_string(part.rhs_lo)+","+(part.index->signed_value?"true":"false")+")";
                else if(part.word_index&&!container)selection="memory_part("+selected_signal+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+")";
                if(container) {
                    code+="auto concat_select"+suffix+"="+selection+";";
                    code+="concat_target"+suffix+".lo=concat_select"+suffix+".lo;concat_target"+suffix+".width=concat_target"+suffix+".width?concat_select"+suffix+".width:0;concat_target"+suffix+".rhs_lo=concat_select"+suffix+".rhs_lo;";
                    code+="concat_parts["+suffix+"]=concat_target"+suffix+";";
                } else code+="concat_parts["+suffix+"]="+selection+";";
            }
            if(nba)p.event_safe=false;
            if(!event.empty())code+="auto concat_count="+count+";s.assign_event_nba("+event+",concat_parts,concat_value,concat_count);";
            else if(!delay.empty())code+="s.assign_parts_after(concat_parts,concat_value,concat_delay);";
            else code+="s.assign_parts(concat_parts,concat_value,"+(nba?std::string("true"):std::string("false"))+");";
            add(p,code+"}");return;
        }
        if(dynamic) {
            if(drive)fail(nullptr,"dynamic array elements require a procedural assignment target");
            const auto& part=target.parts.front();
            writable(part.signal);read(p,value);read(p,part.word_index);if(part.index)read(p,part.index);
            p.touches.insert(part.signal);p.partial_writes.insert(part.signal);p.writes.push_back({part.signal,0,signals[part.signal].width,0});
            std::string code="{";
            if(!delay.empty())code+="auto dynamic_delay="+delay+";";
            code+="auto dynamic_value="+emit(value,target.width)+";auto dynamic_index="+emit(part.word_index,part.word_index->signed_value?64:0)+";";
            std::string selection="Part{0,"+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+"}";
            if(part.index)selection="indexed_part(0,"+std::to_string(signals[part.signal].width)+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+","+std::to_string(part.rhs_lo)+","+(part.index->signed_value?"true":"false")+")";
            code+="auto dynamic_select="+selection+";";
            if(nba) {
                p.event_safe=false;
                code+="auto dynamic_target=s.dynamic_part("+sid(part.signal)+",dynamic_index,"+std::to_string(signals[part.signal].width)+(event.empty()?"":",true")+");";
                code+="dynamic_target.lo=dynamic_select.lo;dynamic_target.width=dynamic_target.width?dynamic_select.width:0;dynamic_target.rhs_lo=dynamic_select.rhs_lo;";
                if(!event.empty())code+="auto dynamic_count="+count+";s.assign_event_nba("+event+",{dynamic_target},dynamic_value,dynamic_count);";
                else if(!delay.empty())code+="s.assign_parts_after({dynamic_target},dynamic_value,dynamic_delay);";
                else code+="s.assign_parts({dynamic_target},dynamic_value,true);";
            } else if(!part.index&&!part.lo&&part.width==signals[part.signal].width)
                code+="s."+std::string(associative_signals.count(part.signal)?"associative_write":queue_bounds.count(part.signal)?"queue_write":"dynamic_write")+"("+sid(part.signal)+",dynamic_index,dynamic_value,"+std::to_string(part.width)+","+(signals[part.signal].two_state?"true":"false")+(queue_bounds.count(part.signal)?","+std::to_string(queue_bounds.at(part.signal)):std::string())+");";
            else code+="s."+std::string(associative_signals.count(part.signal)?"associative_write_slice":queue_bounds.count(part.signal)?"queue_write_slice":"dynamic_write_slice")+"("+sid(part.signal)+",dynamic_index,dynamic_select,dynamic_value,"+(signals[part.signal].two_state?"true":"false")+(queue_bounds.count(part.signal)?","+std::to_string(queue_bounds.at(part.signal)):std::string())+");";
            add(p,code+"}");return;
        }
        for(const auto& part:target.parts) {
            if(part.word_index)for(int id:memories[size_t(part.memory)].words)writable(id);
            else writable(part.signal);
        }
        if(!drive)for(const auto& part:target.parts)
            if(signals[part.signal].net)fail(nullptr,"procedural assignment requires a variable target");
        if(nba)for(const auto& part:target.parts) {
            bool automatic=part.word_index?automatic_signals.count(memories[size_t(part.memory)].words.front()):automatic_signals.count(part.signal);
            if(automatic)fail(nullptr,"nonblocking assignment to an automatic variable is not allowed");
        }
        read(p,value);
        for(auto part:target.parts){
            if(part.word_index) {
                if(drive)fail(nullptr,"variable memory elements in continuous driver targets are not supported yet");
                read(p,part.word_index);if(part.index)read(p,part.index);
                for(int id:memories[size_t(part.memory)].words) {
                    p.touches.insert(id);p.partial_writes.insert(id);
                    p.writes.push_back({id,0,signals[id].width,0});
                }
                continue;
            }
            p.touches.insert(part.signal);
            if(part.index||part.width!=signals[part.signal].width)p.partial_writes.insert(part.signal);
            if(part.index){
                if(drive)fail(nullptr,"variable selects in continuous driver targets are not supported yet");
                if(part.index)read(p,part.index);p.writes.push_back({part.signal,part.view_lo,part.view_width?part.view_width:signals[part.signal].width,0});
            } else p.writes.push_back(part);
        }
        if(event.empty()&&target.parts.size()==1&&target.parts[0].word_index&&!target.parts[0].index&&
           target.parts[0].lo==0&&target.width==signals[target.parts[0].signal].width) {
            const auto& part=target.parts[0];
            const auto select="memory_signal("+memory_table(part.memory)+","+emit(part.word_index,part.word_index->signed_value?64:0)+(parallel_count?",sid.data()":"")+")";
            // An invalid target suppresses the store, not expression effects.
            auto capture_delay=delay.empty()?std::string():"auto word_delay="+delay+";";
            add(p,"{"+capture_delay+"auto word_value="+emit(value,target.width)+";const int word="+select+";if(word>=0)s."+(!delay.empty()?"assign_nba_after(":nba?"assign_nba(":"set(")+"word,word_value"+(delay.empty()?std::string():",word_delay")+");}");
            return;
        }
        if(event.empty()&&target.parts.size()==1 && !target.parts[0].word_index && !target.parts[0].index && target.parts[0].lo==0 && target.parts[0].width==target.width && target.width==signals[target.parts[0].signal].width) {
            int id=target.parts[0].signal;
            std::string args=sid(id)+",";
            if(drive) args+=std::to_string(driver++)+",";
            add(p,std::string("s.")+(drive?"drive(":!delay.empty()?"assign_nba_after(":nba?"assign_nba(":"set(")+args+emit(value,target.width)+(delay.empty()?std::string():","+delay)+");");
            if(!drive&&!nba&&delay.empty()&&!text_target) {
                p.instructions.back().integral_target=id;p.instructions.back().integral_value=value;
            }
            if(drive&&delay.empty()) {
                p.instructions.back().net_target=id;p.instructions.back().net_value=value;
            }
            return;
        }
        std::string parts="{";
        for(auto part:target.parts) {
            std::string selected_signal=sid(part.signal);
            if(part.word_index)selected_signal="memory_signal("+memory_table(part.memory)+","+emit(part.word_index,part.word_index->signed_value?64:0)+(parallel_count?",sid.data()":"")+")";
            if(part.index) {
                parts+=(part.view_width?"view_indexed_part(":"indexed_part(")+selected_signal+","+(part.view_width?std::to_string(part.view_lo)+","+std::to_string(part.view_width):std::to_string(signals[part.signal].width))+","+emit(part.index,part.index->signed_value?64:0)+","+std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false")+","+std::to_string(part.rhs_lo)+","+(part.index->signed_value?"true":"false")+"),";
                continue;
            }
            if(part.word_index) {
                parts+="memory_part("+selected_signal+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+"),";continue;
            }
            parts+="{"+sid(part.signal)+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo);
            if(drive) parts+=","+std::to_string(driver++);
            parts+="},";
        }
        parts+="}";
        if(!event.empty()) {add(p,"{auto event_value="+emit(value,target.width)+";auto event_count="+count+";s.assign_event_nba("+event+","+parts+",event_value,event_count);}");return;}
        std::string code=std::string(drive?"s.drive_parts(":!delay.empty()?"s.assign_parts_after(":"s.assign_parts(")+parts+","+emit(value,target.width);
        code+=!delay.empty()?","+delay+");":drive?");":nba?",true);":",false);";
        add(p,std::move(code));
    }
    struct ArrayCopyView {
        Variable variable;std::vector<MemoryDimension> dimensions;std::vector<int> words;
        E offset;std::vector<int> offsets;int memory=-1;
    };
    bool unpacked_value(VeriNode* n) const {
        if(unpacked_cast_type(n))return true;
        auto* symbol=veri_array_element_symbol(n);
        if(object_fields.count(symbol)&&Variable{symbol}.container_kind()!=vrQUEUE&&Variable{symbol}.container_kind()!=vrOPEN&&!associative_queue_type(symbol))return false;
        const size_t selected=n->detail_type()==veEXP_ARRAY&&!veri_queue_slice(n)?static_cast<VeriArrayExp*>(n)->range().size():0;
        // Query only the declaration's unpacked axes here. Scalar class
        // handles and excess selects must reach their own type diagnostics.
        return variable(symbol)&&Variable{symbol}.range_depth()>int(selected);
    }
    ArrayCopyView array_copy_view(VeriNode* n,bool metadata_only=false) {
        auto* base=n;std::vector<VeriNode*> prefix;
        if(n->detail_type()==veEXP_ARRAY) {
            auto* a=static_cast<VeriArrayExp*>(n);base=a->id();
            for(auto* item:a->range()) {
                auto* r=static_cast<VeriRangeExp*>(item);
                if(r->rtype()!=vrSINGLE)fail(n,"array copy slices are not supported yet");
                prefix.push_back(r->left());
            }
        }
        auto* symbol=veri_array_element_symbol(base);
        if(!variable(symbol)||object_fields.count(symbol))
            fail(n,"array copy requires an unpacked array or subarray");
        Variable var{symbol};if(var.real_width())needs_real=true;
        if(veri_chandle_value(symbol)&&var.dynamic())fail(symbol,"chandle dynamic containers are not supported yet");
        if(var.range_depth()<=int(prefix.size()))fail(n,"array copy requires matching unpacked array operands");
        // Compiling a subscript function may add local memories: keep an owned
        // copy rather than a reference into the growable memory vector.
        const auto memory_id=variable_scope(base,var)->memories.at(var.name());
        const auto memory=memories.at(memory_id);
        if(memory.fixed_count)fail(n,"compact large memories currently support element access and memory file operations, not whole-array copies or formals");
        if(memory.dynamic)fail(n,"dynamic arrays cannot use fixed array copies or fixed-size formals yet");
        if(metadata_only)return {var,{memory.dimensions.begin()+prefix.size(),memory.dimensions.end()},{},{},{}};
        size_t offset=0;bool constant=true;std::vector<E> indices;
        for(size_t d=0;d<prefix.size();++d) {
            auto* index=prefix[d];E value;
            if(elaboration_expression(index)&&static_cast<VeriExp*>(index)->calc_value())value=number(static_cast<VeriExp*>(index)->calc_value());
            else value=expr(index);
            if(value->width>64)needs_wide=true;
            indices.push_back(value);const auto& dim=memory.dimensions[d];
            if(value->op!="literal"||value->unknown||value->host_overflow||value->negative||value->value<uint64_t(dim.base)||value->value-uint64_t(dim.base)>=uint64_t(dim.count))constant=false;
            else offset+=size_t(value->value-uint64_t(dim.base))*size_t(dim.stride);
        }
        ArrayCopyView view{var,{memory.dimensions.begin()+prefix.size(),memory.dimensions.end()},{},{},{}};
        if(!constant) {
            view.memory=memory_id;
            view.offset=node("memory_index",64,indices);
            for(size_t d=0;d<prefix.size();++d) {
                const auto& dim=memory.dimensions[d];const auto suffix=std::to_string(d);
                view.offset->literal+="auto memory_part"+suffix+"=indexed_part(0,"+std::to_string(dim.count)+",memory_index"+suffix+","+std::to_string(dim.base)+",1,false,0);";
                view.offset->literal+="if(!memory_part"+suffix+".width)return V::x(64);memory_offset+=uint64_t(memory_part"+suffix+".lo)*"+std::to_string(dim.stride)+"ull;";
            }
            view.words=memory.words;offset=0;
        }
        size_t count=1;for(const auto& dim:view.dimensions)count*=size_t(dim.count);
        view.words.reserve(count);
        for(size_t ordinal=0;ordinal<count;++ordinal) {
            size_t word=offset;
            for(const auto& dim:view.dimensions) {
                auto element=(ordinal/size_t(dim.stride))%size_t(dim.count);
                word+=(dim.descending?size_t(dim.count)-1-element:element)*size_t(dim.stride);
            }
            if(view.offset)view.offsets.push_back(int(word));
            else view.words.push_back(memory.words.at(word));
        }
        return view;
    }
    void array_ordering(ProcessIR& p,VeriMemberExp* method) {
        auto* object=method->object();auto* symbol=veri_array_element_symbol(object);
        if(veri_queue_slice(object))fail(method,"array ordering requires writable array storage, not a queue slice value");
        if(!variable(symbol)||veri_subroutine_call(object)||veri_array_locator(object))
            fail(method,"array ordering requires writable array storage");
        Variable var{symbol};
        auto queue=object_queue_view(object);auto nested=associative_view(object);const bool nested_queue=associative_queue_leaf(nested);const int id=nested_queue?nested.id:queue.id>=0?queue.id:dynamic_object(object);
        ArrayCopyView fixed;
        std::string code="{";
        if(auto effect=static_receiver_effect(object)){read(p,effect);code+="(void)("+emit(effect)+");";}
        auto modify=[&](int target) {
            writable(target,method);if(signals[target].net)fail(method,"array ordering requires variable storage");
            p.touches.insert(target);p.nonstatic_writes.insert(target);p.partial_writes.insert(target);
            p.writes.push_back({target,0,signals[target].width,0});read(p,signal_expr(target));
        };
        if(nested_queue) {
            auto descriptor=associative_reference_expr(nested);read(p,descriptor);modify(nested.id);
            code+="auto ordering_ref="+emit(descriptor)+";auto ordering_values=s.associative_queue_values(ordering_ref);";
        } else if(queue.id>=0) {
            read(p,queue.receiver);modify(objects_signal);
            code+="auto ordering_receiver="+emit(queue.receiver)+";auto ordering_ref="+object_queue_reference(queue,"ordering_receiver")+";auto ordering_values=s.object_queue_values(ordering_ref);";
        } else if(id>=0) {
            modify(id);code+="auto ordering_values=s.dynamic_values("+sid(id)+");";
        } else {
            fixed=array_copy_view(object);
            for(int word:fixed.words)modify(word);
            if(fixed.offset){read(p,fixed.offset);code+="auto argument_offset="+emit(fixed.offset)+";if(!argument_offset.b){";}
            const auto count=std::to_string(fixed.offset?fixed.offsets.size():fixed.words.size());
            code+="std::vector<V> ordering_values("+count+");for(size_t i=0;i<ordering_values.size();++i)ordering_values[i]=s.get("+array_argument_access(fixed,"argument_offset")+");";
        }
        if(method->member()=="reverse")code+="std::reverse(ordering_values.begin(),ordering_values.end());";
        else {
            auto iterator=node("reduce_item",var.dlen());iterator->signed_value=var.is_signed()==IS_TRUE;
            iterator->object_type=class_type(symbol);iterator->enum_id=enum_identity(symbol);
            iterator->text_value=veri_string_value(symbol);iterator->real_width=var.real_width();
            iterator->literal="ordering_item_"+std::to_string(reduction_item_next++);
            E mapping=iterator;
            if(method->with_expression()) {
                reduction_items.emplace(method->iterator(),iterator);
                try {mapping=expr(method->with_expression());}catch(...){reduction_items.erase(method->iterator());throw;}
                reduction_items.erase(method->iterator());
            }
            auto* key_type=method->with_expression()?veri_aggregate_type(method->with_expression()):veri_aggregate_type(symbol);
            if(mapping->array_value||mapping->object_type!=-1||(key_type&&key_type->unpacked_struct()))
                fail(method,"array sorting requires a singular key with defined relational operators");
            read(p,mapping);
            const bool descending=method->member()=="rsort";
            std::string compare;
            if(mapping->text_value)compare="left.text_value()"+std::string(descending?">":"<")+"right.text_value()";
            else if(mapping->real_width)compare="left.real_value()"+std::string(descending?">":"<")+"right.real_value()";
            else compare=std::string(mapping->signed_value?"signed_binary_op<Binary::":"binary_op<Binary::")+(descending?"Greater":"Less")+">(left,right,1).truth()==1";
            code+="std::vector<V> ordering_keys;ordering_keys.reserve(ordering_values.size());for(const auto& "+iterator->literal+":ordering_values)ordering_keys.push_back("+emit(mapping)+");array_order_values(ordering_values,ordering_keys,[](const V& left,const V& right){return "+compare+";});";
        }
        if(nested_queue)code+="s.associative_queue_replace(ordering_ref,std::move(ordering_values),"+std::to_string(var.dlen())+","+(var.two_state()?"true":"false")+","+std::to_string(var.container_bound(nested.prefix.size()))+");";
        else if(queue.id>=0)code+="s.object_queue_replace(ordering_ref,std::move(ordering_values),"+std::to_string(var.dlen())+","+(var.two_state()?"true":"false")+","+std::to_string(var.container_bound())+");";
        else if(id>=0)code+="s.dynamic_replace("+sid(id)+",std::move(ordering_values),"+std::to_string(var.dlen())+","+(var.two_state()?"true":"false")+",true);";
        else {
            code+="for(size_t i=0;i<ordering_values.size();++i)s.set("+array_argument_access(fixed,"argument_offset")+",ordering_values[i]);";
            if(fixed.offset)code+="}";
        }
        p.event_safe=false;add(p,code+"}");
    }
    E array_locator(VeriMemberExp* method) {
        auto* object=method->object();Variable var{veri_array_element_symbol(object)};
        const auto& name=method->member();
        const bool index=name.find("index")!=std::string::npos;
        const bool unique=name=="unique"||name=="unique_index";
        const bool minimum=name=="min",maximum=name=="max";
        E values;std::string code="([&](){std::vector<V> locator_indices;";
        auto associative=associative_view(object);
        if(associative.id>=0&&!associative_queue_leaf(associative)) {
            values=node("array_argument",var.dlen());values->array_value=true;
            values->reads.insert(associative.id);values->direct_reads.insert(associative.id);values->touches.insert(associative.id);
            if(associative.receiver){read_effect(values,associative.receiver);code+="auto locator_receiver="+emit(associative.receiver)+";";}
            for(auto& key:associative.prefix)read_effect(values,key);
            const auto ref=associative_reference(associative,associative.receiver?"locator_receiver":"");
            code+="auto locator_ref="+ref+";auto locator_values=s.associative_values(locator_ref);";
            if(index)code+="{V key(0,0,32);if(s.associative_cursor(locator_ref,key,0))do{locator_indices.push_back(key);}while(s.associative_cursor(locator_ref,key,2));}";
        } else {
            values=array_values(object,var);code+="auto locator_values="+emit(values)+";";
            if(index) {
                auto shape=veri_array_shape(object);const auto dimension=shape.dimensions.front();
                const bool dynamic=shape.unbound||veri_array_container_kind(object)==vrQUEUE;
                code+="for(size_t i=0;i<locator_values.size();++i)locator_indices.emplace_back(uint64_t(int64_t("+std::to_string(dynamic?0:dimension.first)+")"+
                    (dynamic||dimension.second>=dimension.first?"+":"-")+"int64_t(i)),0,32);";
            }
        }
        auto iterator=node("reduce_item",var.dlen());iterator->signed_value=var.is_signed()==IS_TRUE;
        iterator->object_type=class_type(var.node);iterator->enum_id=enum_identity(var.node);iterator->text_value=veri_string_value(var.node);
        iterator->literal="locator_item_"+std::to_string(reduction_item_next++);
        E mapping=iterator;
        if(method->with_expression()) {
            reduction_items.emplace(method->iterator(),iterator);
            try {mapping=expr(method->with_expression());}catch(...){reduction_items.erase(method->iterator());throw;}
            reduction_items.erase(method->iterator());
        }
        if(mapping->array_value||mapping->real_width)fail(method,"array locator key requires a supported singular integral, string or class value");
        if((unique||minimum||maximum)&&mapping->object_type!=-1)fail(method,"array unique/min/max requires a key with defined relational operators");
        if(!unique&&!minimum&&!maximum&&(mapping->text_value||mapping->object_type!=-1))fail(method,"array find with clause requires an integral predicate");
        auto* key_type=index?veri_associative_key_type(object):nullptr;
        auto result=node("array_argument",index?(key_type?key_type->dlen():32):var.dlen(),{values,mapping});result->array_value=true;
        if(key_type){result->object_type=class_type(key_type);result->enum_id=enum_identity(key_type);}
        result->signed_value=index?(key_type?key_type->is_signed()==IS_TRUE:veri_array_container_kind(object)!=vrASSOC_UINT):var.is_signed()==IS_TRUE;
        code+="std::vector<V> locator_result,locator_keys;for(size_t locator_i=0;locator_i<locator_values.size();++locator_i){const auto& "+iterator->literal+"=locator_values[locator_i];auto locator_key="+emit(mapping)+";";
        const auto selected=index?std::string("locator_indices[locator_i]"):std::string("locator_values[locator_i]");
        if(unique) {
            code+="bool seen=false;for(const auto& key:locator_keys)if(key.same(locator_key)){seen=true;break;}if(!seen){locator_keys.push_back(locator_key);locator_result.push_back("+selected+");}";
        } else if(minimum||maximum) {
            std::string better;
            if(mapping->text_value)better="locator_key.text_value()"+std::string(minimum?"<":">")+"locator_keys[0].text_value()";
            else better=std::string(mapping->signed_value?"signed_binary_op<Binary::":"binary_op<Binary::")+(minimum?"Less":"Greater")+">(locator_key,locator_keys[0],1).truth()==1";
            code+="if(locator_result.empty()||("+better+")){locator_keys={locator_key};locator_result={"+selected+"};}";
        } else {
            code+="if(locator_key.truth()==1){";
            if(name=="find_last"||name=="find_last_index")code+="locator_result={"+selected+"};";
            else code+="locator_result.push_back("+selected+");";
            if(name=="find_first"||name=="find_first_index")code+="break;";
            code+="}";
        }
        result->literal=code+"}return locator_result;}())";
        return result;
    }
    E array_reduction(VeriMemberExp* method) {
        auto* object=method->object();Variable var{veri_array_element_symbol(object)};
        if((veri_aggregate_type(var.node)||enum_identity(var.node)||class_type(var.node)!=-1)&&!method->with_expression())fail(method,"array reduction enum, class and aggregate elements require an integral with expression");
        if(veri_string_value(var.node)&&!method->with_expression())fail(method,"string array reduction requires an integral with expression");
        std::vector<E> values;int id=dynamic_object(object);E materialized;
        auto associative=associative_view(object);
        if(associative.id>=0&&!associative_queue_leaf(associative)) {
            auto descriptor=associative_reference_expr(associative);
            materialized=node("array_argument",var.dlen(),{descriptor});materialized->array_value=true;
            materialized->literal="s.associative_values("+emit(descriptor)+")";
        } else if(associative_queue_leaf(associative)||object_queue_view(object).id>=0||veri_queue_slice(object))materialized=array_values(object,var);
        if(id<0&&!materialized) {
            auto view=array_copy_view(object);
            if(view.offset)fail(method,"array reduction requires static subarray indices");
            for(int word:view.words)values.push_back(signal_expr(word));
        }
        E mapping,iterator;
        if(method->with_expression()) {
            iterator=node("reduce_item",var.dlen());iterator->signed_value=var.is_signed()==IS_TRUE;auto shape=veri_array_shape(object);iterator->value=shape.dimensions.size()-shape.unpacked;iterator->literal="reduce_item_"+std::to_string(reduction_item_next++);
            iterator->text_value=veri_string_value(var.node);
            iterator->object_type=class_type(var.node);iterator->enum_id=enum_identity(var.node);
            reduction_items.emplace(method->iterator(),iterator);
            try {mapping=expr(method->with_expression());}catch(...){reduction_items.erase(method->iterator());throw;}
            reduction_items.erase(method->iterator());
            if(mapping->text_value||mapping->array_value||mapping->real_width||mapping->object_type!=-1)fail(method,"array reduction with expression requires an integral value");
            const auto validate=[&](auto&& self,const E& value)->void {
                if(value->op=="call"||!value->writes.empty()||value->procedural_only)fail(method,"array reduction with expression requires no user calls or side effects");
                for(const auto& child:value->args)self(self,child);
            };
            validate(validate,mapping);values.push_back(iterator);values.push_back(mapping);
        }
        auto result=node(mapping?"array_reduce_with":"array_reduce",mapping?mapping->width:var.dlen(),std::move(values));result->signed_value=mapping?mapping->signed_value:var.is_signed()==IS_TRUE;
        result->literal=method->member()=="sum"?"Add":method->member()=="product"?"Multiply":method->member()=="and"?"BitAnd":method->member()=="or"?"BitOr":"BitXor";
        if(materialized) {
            if(!iterator){iterator=node("reduce_item",var.dlen());iterator->literal="reduce_item_"+std::to_string(reduction_item_next++);}
            auto element=mapping?mapping:iterator;const auto operation=result->literal;const auto width=std::to_string(result->width);const bool sign=result->signed_value;
            result=node("array_argument",result->width,{materialized,element});result->signed_value=sign;
            result->literal="([&](){auto values="+emit(materialized)+";V total(0,0,"+width+");bool first=true;for(const auto& "+iterator->literal+":values){auto mapped="+emit(element)+";if(first){total=mapped;first=false;}else total=binary_op<Binary::"+operation+">(total,mapped,"+width+");}return total;}())";
        }
        if(id>=0&&!materialized){result->signal=id;result->reads.insert(id);result->direct_reads.insert(id);if(associative_signals.count(id))result->op=mapping?"associative_reduce_with":"associative_reduce";}
        if(result->width>64)needs_wide=true;
        return result;
    }
    void check_associative_transfer(const AssociativeView& target,const AssociativeView& source,VeriNode* location) {
        if(source.id<0)fail(location,"associative array assignment requires another associative array");
        Variable a{target.symbol},b{source.symbol};
        const unsigned rank_a=a.range_depth()-target.prefix.size(),rank_b=b.range_depth()-source.prefix.size();
        if(rank_a!=rank_b)fail(location,"associative array copy requires matching key types and rank");
        for(unsigned axis=0;axis<rank_a;++axis) {
            const unsigned ai=target.prefix.size()+axis,bi=source.prefix.size()+axis;
            auto* ak=veri_associative_key_type(a.node,ai);auto* bk=veri_associative_key_type(b.node,bi);
            if(veri_array_container_kind(a.node,ai)!=veri_array_container_kind(b.node,bi)||
               a.container_bound(ai)!=b.container_bound(bi)||
               (ak?ak->dlen():32)!=(bk?bk->dlen():32)||class_type(ak)!=class_type(bk)||
               enum_identity(ak)!=enum_identity(bk)||veri_aggregate_type(ak)!=veri_aggregate_type(bk))
                fail(location,"associative array copy requires matching key types");
        }
        if(!compatible_value_elements(b,a))fail(location,"associative array copy requires compatible element types");
    }
    void associative_assignment(ProcessIR& p,const AssociativeView& target,const AssociativeView& source,VeriNode* location,bool caller_context=false) {
        check_associative_transfer(target,source,location);Variable a{target.symbol};
        writable(target.id,location);read(p,signal_expr(source.id));
        if(target.receiver)read(p,target.receiver);if(source.receiver)read(p,source.receiver);
        for(auto& key:target.prefix)read(p,key);for(auto& key:source.prefix)read(p,key);
        p.touches.insert(target.id);p.writes.push_back({target.id,0,signals[target.id].width,0});
        if(caller_context)add(p,"{auto associative_source=s.associative_snapshot("+associative_reference(source)+");auto task_caller=s.task_output_context();auto associative_target="+associative_reference(target)+";s.associative_restore(associative_target,std::move(associative_source),"+std::to_string(a.dlen())+","+(a.two_state()?"true":"false")+");}");
        else add(p,"{auto associative_source="+associative_reference(source)+";auto associative_target="+associative_reference(target)+";s.associative_replace(associative_target,associative_source,"+std::to_string(a.dlen())+","+(a.two_state()?"true":"false")+");}");
    }
    // Materialize an unpacked value once, before an automatic call frame can
    // restore its storage. Both callers and whole-array stores use this path.
    E array_equality(VeriBinaryExp* comparison) {
        auto* left=comparison->lval();auto* right=comparison->rval();
        const int op=comparison->op();
        if(op!=vtBLEQ&&op!=vtBLIEQ&&op!=vtBCEQ&&op!=vtBCIEQ)
            fail(comparison,"unpacked arrays support equality operators only");
        if(!unpacked_value(left)||!unpacked_value(right))fail(comparison,"array equality requires two unpacked array values");
        Variable a{veri_array_element_symbol(left)},b{veri_array_element_symbol(right)};
        if(a.real_width()||b.real_width())fail(comparison,"real array equality is not supported yet");
        if(!equivalent_elements(a,b))fail(comparison,"array equality requires equivalent element types");
        const auto ashape=veri_array_shape(left),bshape=veri_array_shape(right);
        if(ashape.unpacked!=bshape.unpacked)fail(comparison,"array equality requires matching unpacked ranks");
        const unsigned aselected=left->detail_type()==veEXP_ARRAY&&!veri_queue_slice(left)?static_cast<VeriArrayExp*>(left)->range().size():0;
        const unsigned bselected=right->detail_type()==veEXP_ARRAY&&!veri_queue_slice(right)?static_cast<VeriArrayExp*>(right)->range().size():0;
        for(int axis=0;axis<ashape.unpacked;++axis) {
            if(veri_array_container_kind(a.node,aselected+axis)!=veri_array_container_kind(b.node,bselected+axis))
                fail(comparison,"array equality requires matching container kinds");
            const auto x=ashape.dimensions.at(axis),y=bshape.dimensions.at(axis);
            if(std::abs(int64_t(x.first)-x.second)!=std::abs(int64_t(y.first)-y.second))
                fail(comparison,"array equality requires matching unpacked dimensions");
        }
        auto result=node("call",1,{array_values(left,a),array_values(right,b)});
        result->event_snapshot=true;
        const bool negate=op==vtBLIEQ||op==vtBCIEQ,exact=op==vtBCEQ||op==vtBCIEQ;
        // Snapshot both operands once, in source order. A later call may modify
        // the first array; comparison must still use its captured value.
        result->literal="if(call_arg0.size()!=call_arg1.size())return V("+std::to_string(negate)+");bool unknown=false;for(size_t i=0;i<call_arg0.size();++i){";
        if(veri_string_value(a.node))
            result->literal+="if(call_arg0[i].text_value()!=call_arg1[i].text_value())return V("+std::to_string(negate)+");";
        else {
            result->literal+="auto equal=binary_op<Binary::"+std::string(exact?"CaseEqual":"Equal")+">(call_arg0[i],call_arg1[i],1);if(equal.truth()==0)return V("+std::to_string(negate)+");if(equal.truth()<0)unknown=true;";
        }
        result->literal+="}return unknown?V::x(1):V("+std::to_string(!negate)+");";
        return result;
    }
    E array_values(VeriNode* source,Variable target) {
        if(veri_streaming(source))return runtime_stream_values(source,target);
        if(auto* type=unpacked_cast_type(source)) {
            if(!compatible_value_elements(Variable{type},target))fail(source,"array cast requires compatible destination element types");
            return array_cast_values(static_cast<VeriBinaryExp*>(source),type);
        }
        if(!random_array_binding(source).empty())fail(source,"whole random array values, reductions and locators in constraints are not supported yet");
        if(veri_queue_slice(source)) {
            auto* array=static_cast<VeriArrayExp*>(source);auto* range=static_cast<VeriRangeExp*>(array->range().front());
            Variable actual{veri_array_element_symbol(source)};
            if(!compatible_value_elements(actual,target))fail(source,"queue slice requires compatible element types");
            auto values=array_values(array->id(),actual);
            const auto name="queue_slice_data_"+std::to_string(queue_slice_sequence++);
            auto last_index=node("saved",32);last_index->signed_value=true;last_index->literal="V(uint64_t("+name+".size())-1,0,32)";
            auto old=queue_slice_last_indices.find(source);E previous=old==queue_slice_last_indices.end()?E{}:old->second;
            queue_slice_last_indices[source]=last_index;
            auto restore=[&](){if(previous)queue_slice_last_indices[source]=previous;else queue_slice_last_indices.erase(source);};
            E first,last;
            try{first=expr(range->left());last=expr(range->right());}catch(...){restore();throw;}
            restore();
            for(auto* bound:{&first,&last}) {
                if((*bound)->packed_value)*bound=(*bound)->packed_value;
                if((*bound)->text_value||(*bound)->real_width||(*bound)->array_value||(*bound)->object_type!=-1)
                    fail(source,"queue slice bounds require integral expressions");
            }
            auto value=node("array_argument",target.dlen());value->array_value=true;
            for(auto& part:{values,first,last})read_effect(value,part);
            value->literal="([&](){auto "+name+"="+emit(values)+";auto first="+emit(first)+";auto last="+emit(last)+";";
            value->literal+="auto bound=[&](const V& index,bool sign,size_t& position,bool& negative){negative=sign&&index.bit(index.w-1)==1;bool high=false;for(int bit=0;bit<index.w;++bit){int v=index.bit(bit);if(v>1)return false;if(bit>=64&&v)high=true;}position=high||index.a>="+name+".size()?"+name+".size():size_t(index.a);return true;};";
            value->literal+="size_t begin=0,end=0;bool negative_first=false,negative_last=false;if(!bound(first,"+std::string(first->signed_value?"true":"false")+",begin,negative_first)||!bound(last,"+(last->signed_value?"true":"false")+",end,negative_last)||"+name+".empty()||negative_last)return std::vector<V>{};if(negative_first)begin=0;if(end<"+name+".size())++end;if(begin>=end)return std::vector<V>{};return std::vector<V>("+name+".begin()+begin,"+name+".begin()+end);}())";
            return value;
        }
        if(assignment_pattern(source)) {
            auto value=node("array_argument",target.dlen());value->array_value=true;
            std::string code="([&](){std::vector<V> patterned;";
            for(auto* item:pattern_entries(source)) {
                const int kind=item->detail_type()==veEXP_MULTI?static_cast<VeriMultiExp*>(item)->multi_type():-1;
                if(item->detail_type()==veEXP_NAMED_PARAM||kind==vemPATTERN_DEFAULT||kind==vemPATTERN_INDEX)
                    fail(item,"runtime array assignment patterns currently require positional entries");
                auto part=class_type(target.node)>=0?expr(item):veri_string_value(target.node)?text_context(expr(item)):pattern_value(item,pattern_type(target.node));
                enum_assignment(target.node,part);
                const int destination=class_type(target.node);
                if(destination>=0?!class_compatible(part->object_type,destination):part->object_type!=-1)
                    fail(item,"array pattern requires a compatible element type");
                if(part->text_value!=veri_string_value(target.node)||part->array_value)fail(item,"array pattern requires compatible element values");
                read_effect(value,part);code+="patterned.push_back("+emit(part,target.dlen())+");";
            }
            value->literal=code+"return patterned;}())";return value;
        }
        if(source->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(source)->multi_type()==vemCONCAT_EXP) {
            auto value=node("array_argument",target.dlen());value->array_value=true;
            std::string code="([&](){std::vector<V> concatenated;";
            for(auto* item:static_cast<VeriMultiExp*>(source)->exp()) {
                E part;
                // A concatenation item needs its own type (IEEE 1800 10.10).
                // Nested braces denote a packed/string concatenation, not an
                // unpacked value. In particular, nested {} has no such type.
                if(unpacked_value(item)) {
                    part=array_values(item,target);code+="{auto part="+emit(part)+";concatenated.insert(concatenated.end(),part.begin(),part.end());}";
                } else {
                    part=expr(item);enum_assignment(target.node,part);
                    const int destination=class_type(target.node);
                    if(destination>=0?!class_compatible(part->object_type,destination):part->object_type!=-1)
                        fail(item,"array concatenation element requires a compatible element type");
                    if(veri_string_value(target.node))part=text_context(part);
                    if(part->text_value!=veri_string_value(target.node)||part->array_value)fail(item,"array concatenation requires compatible element values");
                    code+="concatenated.push_back("+emit(part,target.dlen())+");";
                }
                read_effect(value,part);
            }
            value->literal=code+"return concatenated;}())";return value;
        }
        auto* symbol=veri_array_element_symbol(source);
        if(!variable(symbol)||!unpacked_value(source))fail(source,"array value requires an unpacked array expression");
        Variable actual{symbol};
        if(auto view=associative_view(source);associative_queue_leaf(view)) {
            if(!compatible_value_elements(actual,target))fail(source,"array value requires compatible element types");
            auto descriptor=associative_reference_expr(view);auto value=node("array_argument",target.dlen(),{descriptor});value->array_value=true;
            value->literal="s.associative_queue_values("+emit(descriptor)+")";return value;
        }
        if(associative_kind(actual.container_kind()))fail(source,"associative arrays require matching key types");
        if(!compatible_value_elements(actual,target))fail(source,"array value requires compatible element types");
        if(auto view=object_queue_view(source);view.id>=0) {
            auto value=node("array_argument",target.dlen(),{view.receiver});value->array_value=true;
            value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);
            value->literal="s.object_queue_values("+object_queue_reference(view)+")";return value;
        }
        if(veri_array_locator(source))return array_locator(static_cast<VeriMemberExp*>(source));
        if(veri_subroutine_call(source)) {
            auto value=function_call(source);if(!value->array_value)fail(source,"array function result is not an unpacked value");
            return value;
        }
        const int id=dynamic_object(source);
        auto value=node("array_argument",target.dlen());value->array_value=true;
        if(id>=0) {
            value->reads.insert(id);value->direct_reads.insert(id);value->touches.insert(id);
            value->literal="s.dynamic_values("+sid(id)+")";
        } else {
            auto view=array_copy_view(source);
            std::string code="([&](){";
            if(view.offset){read_effect(value,view.offset);code+="auto argument_offset="+emit(view.offset)+";";}
            const size_t count=view.offset?view.offsets.size():view.words.size();
            code+="std::vector<V> values("+std::to_string(count)+");for(size_t i=0;i<values.size();++i)values[i]=";
            const auto load="s.get("+array_argument_access(view,"argument_offset")+")";
            code+=(view.offset?"argument_offset.b?"+std::string(target.two_state()?"V(0,0,":"V::x(")+std::to_string(target.dlen())+"):"+load:load)+";return values;}())";
            value->literal=std::move(code);
            for(int word:view.words){value->reads.insert(word);value->direct_reads.insert(word);value->touches.insert(word);}
        }
        if(auto effect=static_receiver_effect(source)) {
            read_effect(value,effect);value->literal="([&](){(void)("+emit(effect)+");return "+value->literal+";}())";
        }
        return value;
    }
    void object_queue_assignment(ProcessIR& p,const AssociativeView& queue,VeriNode* source) {
        Variable target{queue.symbol};
        const bool allocation=source->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(source)->multi_type()==vemDYNAMIC_NEW;
        E count;VeriNode* initializer=source;
        if(allocation) {
            if(target.container_kind()!=vrOPEN)fail(source,"new[] requires a dynamic array, not a queue");
            auto& args=static_cast<VeriMultiExp*>(source)->exp();count=expr(args.front());initializer=args.size()==2?args.back():nullptr;
        }
        auto value=initializer?array_values(initializer,target):node("array_argument",target.dlen());
        if(!initializer){value->array_value=true;value->literal="std::vector<V>{}";}
        read(p,queue.receiver);read(p,value);writable(objects_signal,source);
        p.touches.insert(objects_signal);p.partial_writes.insert(objects_signal);p.writes.push_back({objects_signal,0,64,0});
        if(allocation) {
            read(p,count);add(p,"{auto queue_receiver="+emit(queue.receiver)+";auto array_count="+emit(count,count->signed_value?64:0)+";auto queue_values="+emit(value)+";s.object_dynamic_new("+object_queue_reference(queue,"queue_receiver")+",array_count,"+std::to_string(target.dlen())+","+(target.two_state()?"true":"false")+",queue_values,"+(veri_string_value(target.node)?"true":"false")+");}");return;
        }
        add(p,"{auto queue_receiver="+emit(queue.receiver)+";auto queue_values="+emit(value)+";s.object_queue_replace("+
            object_queue_reference(queue,"queue_receiver")+",std::move(queue_values),"+std::to_string(target.dlen())+","+
            (target.two_state()?"true":"false")+","+std::to_string(target.container_bound())+");}");
    }
    void read_effect(E& value,const E& effect) {
        // Use ordinary expression composition so scheduler effects do not get
        // lost when an array's native representation is a vector, rather than V.
        auto combined=node("array_argument",value->width,{value,effect});
        combined->literal=value->literal;combined->array_value=value->array_value;value=combined;
    }
    std::string replace_array_values(int id,const std::string& values) const {
        const auto suffix=","+std::to_string(signals[id].width)+","+(signals[id].two_state?"true":"false");
        if(associative_signals.count(id))return "s.associative_restore(s.associative_ref("+sid(id)+"),"+values+suffix+");";
        if(queue_bounds.count(id))return "s.queue_replace("+sid(id)+","+values+suffix+","+std::to_string(queue_bounds.at(id))+");";
        return "s.dynamic_replace("+sid(id)+","+values+suffix+");";
    }
    void dynamic_array_assignment(ProcessIR& p,int object,VeriNode* rhs,Variable target) {
        p.touches.insert(object);p.writes.push_back({object,0,signals[object].width,0});
        if(associative_signals.count(object)) {associative_assignment(p,{target.node,object,{}},associative_view(rhs),rhs);return;}
        const int source_object=dynamic_object(rhs);
        if(!associative_queue_leaf(associative_view(rhs))&&(associative_signals.count(source_object)||associative_view(rhs).id>=0))fail(rhs,"associative array assignment requires matching key types");
        std::string code="{";auto* source=rhs;bool allocation=rhs->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(rhs)->multi_type()==vemDYNAMIC_NEW;
        if(allocation&&queue_bounds.count(object))fail(rhs,"new[] requires a dynamic array, not a queue");
        if(allocation) {
            auto& args=static_cast<VeriMultiExp*>(rhs)->exp();auto size=expr(args.front());read(p,size);
            code+="auto dynamic_count="+emit(size,size->signed_value?64:0)+";";
            source=args.size()==2?args.back():nullptr;
        }
        std::string values="{}";int dynamic_initializer=-1;
        if(source) {
            int actual=dynamic_object(source);
            if(veri_streaming(source)||unpacked_cast_type(source)||assignment_pattern(source)||(source->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(source)->multi_type()==vemCONCAT_EXP)) {
                auto value=array_values(source,target);read(p,value);values=emit(value);
            } else if((veri_subroutine_call(source)||veri_array_locator(source)||veri_queue_slice(source)||object_queue_view(source).id>=0||associative_queue_leaf(associative_view(source)))&&unpacked_value(source)) {
                if(veri_array_shape(source).unpacked!=1)fail(source,"dynamic array assignment requires one unpacked dimension");
                auto value=array_values(source,target);read(p,value);values=emit(value);
            } else if(actual>=0) {
                dynamic_initializer=actual;
                if(signals[actual].width!=signals[object].width)
                    fail(source,"dynamic array assignment currently requires equal element width");
                Variable source_type{veri_array_element_symbol(source)};
                if((!allocation||veri_aggregate_type(target.node)||veri_aggregate_type(source_type.node)||enum_identity(target.node)||enum_identity(source_type.node)||class_type(target.node)>=0||class_type(source_type.node)>=0)&&!compatible_value_elements(source_type,target))
                    fail(source,"dynamic array copy requires compatible element types");
                read(p,signal_expr(actual));p.touches.insert(actual);values="s.dynamic_values("+sid(actual)+")";
            } else {
                auto view=array_copy_view(source);
                if(view.dimensions.size()!=1||view.variable.dlen()!=signals[object].width)
                    fail(source,"dynamic array initializer requires a compatible one-dimensional array");
                if((!allocation||veri_aggregate_type(target.node)||veri_aggregate_type(view.variable.node)||enum_identity(target.node)||enum_identity(view.variable.node)||class_type(target.node)>=0||class_type(view.variable.node)>=0)&&!compatible_value_elements(view.variable,target))fail(source,"dynamic array copy requires compatible element types");
                if(view.offset)fail(source,"dynamic array initializer subarray indices are not supported yet");
                values="std::vector<V>{";for(int id:view.words){auto value=signal_expr(id);read(p,value);values+=emit(value)+",";}values+="}";
            }
            code+="auto dynamic_source="+values+";";values="dynamic_source";
        }
        code+=std::string("s.")+(allocation?"dynamic_new(":queue_bounds.count(object)?"queue_replace(":"dynamic_replace(")+sid(object)+","+(allocation?"dynamic_count,":"")+
            (allocation?std::to_string(signals[object].width)+","+(signals[object].two_state?"true":"false")+","+values+(dynamic_initializer>=0?","+sid(dynamic_initializer):std::string()):values+","+std::to_string(signals[object].width)+","+(signals[object].two_state?"true":"false"))+(queue_bounds.count(object)?","+std::to_string(queue_bounds.at(object)):std::string())+");}";
        add(p,std::move(code));
    }
    bool stream_assignment(ProcessIR& p,VeriNode* lhs,VeriNode* rhs,bool nba,VeriNode* control) {
        if(!veri_streaming(lhs))return false;
        struct Target {
            VeriNode* syntax=nullptr;int kind=0,minimum=0,slice=0,dynamic=-1,id=-1;
            bool reverse=false,greedy=false;
            std::vector<Target> children;LValueIR packed;
            std::optional<ArrayCopyView> fixed;AssociativeView object;
        };
        int dynamics=0,sequence=0;
        std::function<Target(VeriNode*)> collect=[&](VeriNode* n) {
            Target target;target.syntax=n;target.id=sequence++;
            if(veri_streaming(n)) {
                target.slice=veri_stream_slice(n);if(!target.slice)fail(n,"stream slice size must be a known positive integral constant in 1..1048576");
                target.reverse=static_cast<VeriBinaryExp*>(n)->op()==vtSTREAM_LEFT;
                target.children.push_back(collect(static_cast<VeriBinaryExp*>(n)->rval()));
            } else if(n->detail_type()==veEXP_MULTI) {
                auto* list=static_cast<VeriMultiExp*>(n);
                if(list->multi_type()!=vemCONCAT_EXP)fail(n,"stream target requires a storage list");
                for(auto* part:list->exp())target.children.push_back(collect(part));
            } else if(unpacked_value(n)) {
                auto* symbol=veri_array_element_symbol(n);if(!variable(symbol))fail(n,"stream target requires an array variable");
                Variable type{symbol};stream_element_type(n,type);
                if(enum_identity(symbol))fail(n,"stream target enum elements are not supported yet");
                target.object=object_queue_view(n);
                const int id=dynamic_object(n);
                if(target.object.id>=0||id>=0) {
                    if(type.range_depth()!=1||(type.container_kind()!=vrOPEN&&type.container_kind()!=vrQUEUE))fail(n,"stream target requires fixed storage or one dynamic/queue dimension");
                    target.kind=3;target.dynamic=dynamics++;target.greedy=target.dynamic==0;
                    if(target.object.id<0)target.object={symbol,id,{}};
                } else {
                    target.kind=2;target.fixed=array_copy_view(n);
                    const auto count=target.fixed->offset?target.fixed->offsets.size():target.fixed->words.size();
                    if(count>1048576/size_t(type.dlen()))fail(n,"stream target exceeds supported width");
                    target.minimum=int(count)*type.dlen();
                }
            } else {
                if(veri_virtual_interface(n)||veri_string_value(n)||veri_real_width(n)||class_type(n)!=-1)fail(n,"stream target requires integral variable storage");
                if(enum_identity(n))fail(n,"stream target enum elements are not supported yet");
                target.kind=1;target.packed=lvalue(n);target.minimum=target.packed.width;
            }
            for(const auto& child:target.children) {
                if(target.minimum>1048576-child.minimum)fail(n,"stream target exceeds supported width");
                target.minimum+=child.minimum;target.greedy|=child.greedy;
            }
            return target;
        };
        auto target=collect(lhs);
        if(nba||control) {
            if(dynamics)fail(lhs,"runtime stream target requires an immediate blocking assignment");
            return false; // Retain existing fixed-width timed assignment handling.
        }
        if(!dynamics&&!unpacked_value(rhs)&&!runtime_stream_operand(rhs)) {
            bool direct=true;int streams=0;
            std::function<void(const Target&)> check=[&](const Target& item) {
                streams+=item.slice!=0;
                if(item.kind==2)direct=false;
                for(const auto& part:item.packed.parts)
                    direct&=!part.virtual_handle&&!part.object&&!part.associative_ref&&!part.index&&!part.word_index&&!part.receiver_effect;
                for(const auto& child:item.children)check(child);
            };
            check(target);
            if(direct&&streams==1)return false; // Keep the packed scalar fast path.
        }
        auto source=runtime_stream_bits(rhs);read(p,source);
        if(!unpacked_value(rhs)&&!veri_streaming(rhs)) {
            const int width=veri_bit_width(rhs);
            if(width>0&&width<target.minimum)fail(rhs,"stream unpacking source is smaller than destination");
        }
        std::string prefix="{auto stream_source="+emit(source)+";if(stream_source.size()<"+std::to_string(target.minimum)+")throw std::runtime_error(\"stream unpacking source is smaller than destination\");";
        prefix+="const size_t stream_extra="+(dynamics?"stream_source.size()-"+std::to_string(target.minimum):"size_t(0)")+";";
        if(!dynamics)prefix+="stream_source.resize("+std::to_string(target.minimum)+");";
        // Capture every address once, after the RHS and before any store.
        // A preceding target must not change a later index or receiver.
        std::function<void(Target&)> capture=[&](Target& item) {
            auto save=[&](E& address) {
                if(!address)return;read(p,address);auto original=address;
                address=node(original->op=="container_ref"?"saved_ref":"saved",original->width);
                address->signed_value=original->signed_value;address->real_width=original->real_width;address->object_type=original->object_type;
                address->text_value=original->text_value;address->enum_id=original->enum_id;
                address->literal="stream_address"+std::to_string(sequence++);
                prefix+="auto "+address->literal+"="+emit(original)+";";
            };
            if(auto effect=static_receiver_effect(item.syntax);item.kind>1&&effect){read(p,effect);prefix+="(void)("+emit(effect)+");";}
            if(item.kind==1)for(auto& part:item.packed.parts) {
                if(signals[part.signal].net)fail(item.syntax,"procedural assignment to a net");
                if(part.receiver_effect){read(p,part.receiver_effect);prefix+="(void)("+emit(part.receiver_effect)+");";part.receiver_effect={};}
                for(auto* address:{&part.virtual_handle,&part.associative_ref,&part.object,&part.word_index,&part.index})save(*address);
            }
            if(item.fixed)save(item.fixed->offset);
            if(item.kind==3) {
                writable(item.object.id,item.syntax);
                if(item.object.receiver) {
                    save(item.object.receiver);
                    prefix+="auto stream_object"+std::to_string(item.id)+"="+object_queue_reference(item.object)+";";
                }
            }
            for(auto& child:item.children)capture(child);
        };
        capture(target);
        const auto first=p.instructions.size();add(p,std::move(prefix));
        std::function<void(Target&,const std::string&,const std::string&)> store=[&](Target& item,const std::string& bits,const std::string& offset) {
            const auto suffix=std::to_string(item.id),local="stream_bits"+suffix,cursor="stream_offset"+suffix;
            const auto length=std::to_string(item.minimum)+(item.greedy?"+stream_extra":"");
            if(item.kind==0) {
                std::string input=bits;
                if(item.slice) {
                    add(p,"StreamBits "+local+"("+bits+".begin()+"+offset+","+bits+".begin()+"+offset+"+"+length+");");
                    if(item.reverse)add(p,local+"=stream_reverse(std::move("+local+"),"+std::to_string(item.slice)+");");
                    input=local;
                }
                add(p,"size_t "+cursor+"="+(item.slice?"0":offset)+";");
                for(auto& child:item.children) {
                    store(child,input,cursor);
                    add(p,cursor+"+="+std::to_string(child.minimum)+(child.greedy?"+stream_extra":"")+";");
                }
                return;
            }
            if(item.kind==1) {
                auto value=node("call",item.minimum);value->literal="return stream_piece("+bits+","+offset+","+std::to_string(item.minimum)+",false);";
                write(p,item.packed,value,false,false);return;
            }
            Variable type{veri_array_element_symbol(item.syntax)};
            if(item.kind==2) {
                const auto& view=*item.fixed;const auto count=view.offset?view.offsets.size():view.words.size();
                for(int word:view.words){writable(word,item.syntax);if(signals[word].net)fail(item.syntax,"procedural assignment to a net");p.touches.insert(word);p.writes.push_back({word,0,signals[word].width,0});if(view.offset)p.partial_writes.insert(word);}
                const auto address=array_argument_access(view,view.offset?emit(view.offset):"unused");
                add(p,"for(size_t i=0;i<"+std::to_string(count)+";++i)"+(view.offset?"if(!"+emit(view.offset)+".b)":"")+"s.set("+address+",stream_piece("+bits+","+offset+"+i*"+std::to_string(type.dlen())+","+std::to_string(type.dlen())+","+(type.two_state()?"true":"false")+"));");return;
            }
            p.touches.insert(item.object.id);p.partial_writes.insert(item.object.id);p.writes.push_back({item.object.id,0,signals[item.object.id].width,0});
            const int bound=type.container_kind()==vrQUEUE?type.container_bound():-1;
            std::string code="{StreamBits "+local+"("+bits+".begin()+"+offset+","+bits+".begin()+"+offset+"+"+(item.greedy?"stream_extra":"size_t(0)")+");auto stream_values=stream_unpack("+local+","+std::to_string(type.dlen())+","+(type.two_state()?"true":"false")+",-1,false,"+std::to_string(bound)+");";
            if(item.object.receiver)code+="s.object_queue_replace(stream_object"+suffix+",std::move(stream_values),"+std::to_string(type.dlen())+","+(type.two_state()?"true":"false")+","+std::to_string(bound)+");";
            else code+=replace_array_values(item.object.id,"std::move(stream_values)");
            add(p,code+"}");
        };
        store(target,"stream_source","size_t(0)");add(p,"}");
        // One blocking assignment owns these temporaries and has no scheduler
        // suspension point between its captures and stores.
        std::string code;
        for(size_t i=first;i<p.instructions.size();++i)code+=p.instructions[i].code;
        p.instructions.resize(first);add(p,std::move(code));
        return true;
    }
    bool array_assignment(ProcessIR& p,VeriNode* lhs,VeriNode* rhs,bool nba,VeriNode* control,int pidx) {
        if(stream_assignment(p,lhs,rhs,nba,control))return true;
        if(veri_queue_slice(lhs))fail(lhs,"queue slice assignment requires a whole queue destination");
        if(auto queue=object_queue_view(lhs);queue.id>=0) {
            if(nba||control)fail(lhs,"whole class queue assignment requires blocking assignment without timing control");
            object_queue_assignment(p,queue,rhs);return true;
        }
        if(unpacked_value(lhs)||unpacked_value(rhs))for(auto* value:{lhs,rhs})if(auto effect=static_receiver_effect(value)) {
            read(p,effect);add(p,"(void)("+emit(effect)+");");
        }
        auto associative=associative_view(lhs);
        if(associative_queue_leaf(associative)) {
            if(nba||control)fail(lhs,"whole queue assignment requires blocking assignment without timing control");
            auto descriptor=associative_reference_expr(associative);Variable target{associative.symbol};auto values=array_values(rhs,target);
            read(p,descriptor);read(p,values);writable(associative.id,lhs);p.touches.insert(associative.id);p.partial_writes.insert(associative.id);p.writes.push_back({associative.id,0,signals[associative.id].width,0});
            add(p,"{auto queue_ref="+emit(descriptor)+";auto queue_values="+emit(values)+";s.associative_queue_replace(queue_ref,std::move(queue_values),"+std::to_string(target.dlen())+","+(target.two_state()?"true":"false")+","+std::to_string(target.container_bound(associative.prefix.size()))+");}");return true;
        }
        if(associative.id>=0) {
            if(nba||control)fail(lhs,"whole associative array assignment requires blocking assignment without timing control");
            associative_assignment(p,associative,associative_view(rhs),lhs);return true;
        }
        int object=dynamic_object(lhs);
        if(object>=0) {
            if(nba||control)fail(lhs,"whole dynamic array assignment requires blocking assignment without timing control");
            writable(object,lhs);dynamic_array_assignment(p,object,rhs,Variable{veri_array_element_symbol(lhs)});return true;
        }
        if(!unpacked_value(lhs)&&!unpacked_value(rhs))return false;
        if(lhs->detail_type()==veEXP_MEMBER&&unpacked_value(lhs)&&!unpacked_value(rhs)&&!assignment_pattern(rhs))
            fail(lhs,"hierarchical array write from a scalar requires all element indices");
        if(((veri_subroutine_call(rhs)||veri_array_locator(rhs)||unpacked_cast_type(rhs))&&unpacked_value(rhs))||veri_streaming(rhs)) {
            if(nba||control)fail(lhs,"array function values currently require blocking assignment without timing control");
            auto target=array_copy_view(lhs);auto shape=veri_array_shape(rhs);
            if(!veri_streaming(rhs)&&shape.unpacked!=int(target.dimensions.size()))fail(lhs,"array copy rank mismatch");
            if(!veri_streaming(rhs)&&!shape.unbound)for(int d=0;d<shape.unpacked;++d)
                if(std::abs(int64_t(shape.dimensions[d].first)-shape.dimensions[d].second)+1!=target.dimensions[d].count)fail(lhs,"array copy dimension size mismatch");
            auto value=veri_streaming(rhs)?runtime_stream_values(rhs,target.variable,int(target.words.size())):array_values(rhs,target.variable);read(p,value);
            const auto count=std::to_string(target.offset?target.offsets.size():target.words.size());
            std::string code="{auto returned_values="+emit(value)+";if(returned_values.size()!="+count+")throw std::runtime_error(\"array function return size mismatch\");";
            if(target.offset){read(p,target.offset);code+="auto argument_offset="+emit(target.offset)+";";}
            for(int word:target.words){writable(word,lhs);if(signals[word].net)fail(lhs,"procedural assignment to a net");p.touches.insert(word);p.writes.push_back({word,0,signals[word].width,0});}
            code+="for(size_t i=0;i<returned_values.size();++i)";
            if(target.offset)code+="if(!argument_offset.b)";
            code+="s.set("+array_argument_access(target,"argument_offset")+",returned_values[i]);}";add(p,std::move(code));return true;
        }
        auto target=array_copy_view(lhs);const bool pattern=assignment_pattern(rhs);std::vector<E> pattern_values;
        if(pattern)unpacked_pattern(rhs,target.dimensions,0,pattern_type(target.variable.node),pattern_values);
        auto source=pattern?target:array_copy_view(rhs);
        if(target.dimensions.size()!=source.dimensions.size())fail(lhs,"array copy rank mismatch");
        for(size_t d=0;d<target.dimensions.size();++d)
            if(target.dimensions[d].count!=source.dimensions[d].count)fail(lhs,"array copy dimension size mismatch");
        const auto a=target.variable,b=source.variable;
        if((struct_has_strings(veri_aggregate_type(a.node))||struct_has_strings(veri_aggregate_type(b.node)))&&veri_aggregate_type(a.node)!=veri_aggregate_type(b.node))
            fail(lhs,"struct string arrays require matching element types");
        if(nba&&struct_has_strings(veri_aggregate_type(a.node)))fail(lhs,"nonblocking assignment to struct string arrays is not allowed");
        if((class_type(a.node)>=0||class_type(b.node)>=0)?!compatible_value_elements(b,a):!equivalent_elements(a,b,false,false))
            fail(lhs,"array copy requires compatible element types (width, signedness, atomic kind and enum identity)");
        for(int id:target.words) {
            writable(id,lhs);
            if(signals[id].net)fail(lhs,"procedural assignment to a net");
            if(nba&&automatic_signals.count(id))fail(lhs,"nonblocking assignment to an automatic variable is not allowed");
        }
        if(control&&p.always_kind!=akALWAYS)fail(lhs,"intra-assignment timing is not allowed in always_comb/always_latch/always_ff");
        if(control&&control->detail_type()!=veEXP_DELAY)fail(control,"intra-assignment event controls on unpacked arrays are not supported");
        const auto ticks=control?procedural_delay(p,control):std::string();
        const auto count=std::to_string(source.offset?source.offsets.size():source.words.size());
        const auto buffer="array_value"+std::to_string(p.array_values.size());p.array_values.push_back(source.offset?source.offsets.size():source.words.size());
        const auto table=[&](const ArrayCopyView& view){
            // Dynamic views share the existing memory ID table; only the small
            // declaration-order offsets are specific to this copy site.
            if(view.offset)return "memory_words"+std::to_string(view.memory);
            auto name="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(view.words);return name;
        };
        const auto source_table=pattern?std::string():table(source),target_table=table(target);
        const auto index=[&](const std::string& table,const ArrayCopyView& view,const std::string& name){
            std::string word="i";
            if(view.offset) {
                const auto offsets="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(view.offsets);
                word=name+".a+"+offsets+"[i]";
            }
            auto id=table+"["+word+"]";return parallel_count?"sid["+id+"]":id;
        };
        const auto source_id=pattern?std::string():index(source_table,source,"array_source"),target_id=index(target_table,target,"array_target");
        if(!pattern&&source.offset)read(p,source.offset);
        if(target.offset)read(p,target.offset);
        if(!pattern)for(int id:source.words){read(p,signal_expr(id));p.touches.insert(id);}
        for(int id:target.words){p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});if(target.offset){p.partial_writes.insert(id);p.nonstatic_writes.insert(id);}else p.whole_writes.insert(id);}
        const auto invalid=source.variable.two_state()?"V(0,0,":"V::x(";
        std::string value="s.get("+source_id+")";
        // The checked offset is always 64 bits, including in narrow builds.
        if(source.offset)value="array_source.b?"+std::string(invalid)+std::to_string(b.dlen())+"):"+value;
        std::string snapshot=(source.offset?"auto array_source="+emit(source.offset)+";":"")+"for(size_t i=0;i<"+count+";++i)"+buffer+"[i]="+value+";";
        if(pattern) {
            snapshot.clear();for(size_t i=0;i<pattern_values.size();++i){read(p,pattern_values[i]);snapshot+=buffer+"["+std::to_string(i)+"]="+emit(pattern_values[i])+";";}
        }
        std::string store=(target.offset?"auto array_target="+emit(target.offset)+";if(!array_target.b)":"")+"for(size_t i=0;i<"+count+";++i)s.";
        if(nba) {
            if(control)needs_delayed_nba=true;
            store+=(control?"assign_nba_after(":"assign_nba(")+target_id+","+buffer+"[i]"+(control?",array_delay":"")+");";
            // The dynamic delay is evaluated once, before any element is queued.
            add(p,"{"+(control?"auto array_delay="+ticks+";":"")+snapshot+store+"}");
        } else {
            store+="set("+target_id+","+buffer+"[i]);";
            add(p,source.offset?"{"+snapshot+"}":snapshot);
            if(control) {
                const int next=int(p.instructions.size())+1;
                add(p,"pc="+std::to_string(next)+";s.delay("+runtime_pid(pidx)+","+ticks+");return;");
            }
            add(p,target.offset?"{"+store+"}":store);
        }
        return true;
    }
    #include "rtl_object_format.inc"
    void string_format_features(VeriNode* format_node) {
        needs_text=true;
        if(format_node->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(format_node)->pri_type()!=veSTR)needs_real=true;
        else {
            const auto text=decode_string(static_cast<VeriPrimaryExp*>(format_node)->str(),format_node);
            for(size_t i=0;i<text.size();++i)if(text[i]=='%'&&++i<text.size()) {
                if(text[i]=='%')continue;
                while(i<text.size()&&(std::isdigit(static_cast<unsigned char>(text[i]))||text[i]=='.'))++i;
                if(i<text.size()&&std::string("fFeEgG").find(text[i])!=std::string::npos)needs_real=true;
            }
        }
    }
    E formatted_value(VeriNode* format_node,const std::vector<VeriNode*>& arguments) {
        string_format_features(format_node);
        auto fmt=expr(format_node);std::vector<E> values{fmt};
        std::string signs="{",objects="{";bool has_objects=false;
        for(auto* argument:arguments) {
            auto value=expr(argument);if(value->interface_namespace)fail(argument,"interface namespace cannot be formatted as an integral value");const bool object=value->object_type>=0;
            objects+=object?"true,":"false,";has_objects|=object;
            if(object)value=formatted_object(value);
            else if(value->packed_literal&&value->packed_value)value=value->packed_value;
            signs+=value->signed_value?"true,":"false,";values.push_back(value);
        }
        auto result=node("call",1,values);result->text_value=true;
        std::string code="return s.format_text(call_arg0,{";
        for(size_t i=1;i<values.size();++i)code+="call_arg"+std::to_string(i)+",";
        std::string path=scope->path;
        if(!scope->static_wave_path.empty()) {
            path.clear();for(const auto& part:scope->static_wave_path){if(!path.empty())path+='.';path+=part;}
        }
        result->literal=code+"},"+signs+"},"+quote(path)+","+std::to_string(scope->time.unit_fs)+"ULL"+(has_objects?","+objects+"}":std::string())+");";
        return result;
    }
    E swrite_value(const std::vector<VeriNode*>& arguments,char radix) {
        needs_text=true;
        std::vector<E> values;std::string signs="{",packed_widths="{",objects="{";bool has_objects=false;
        for(auto* argument:arguments) {
            if(unpacked_value(argument))fail(argument,"$swrite unpacked aggregate output is not supported yet");
            if(veri_string_value(argument))string_format_features(argument);
            auto value=expr(argument);
            if(value->object_type==opaque_handle_type)fail(argument,"$swrite chandle output is not supported yet");
            const bool object=value->object_type>=0;objects+=object?"true,":"false,";has_objects|=object;
            if(object)value=formatted_object(value);
            if(!veri_string_value(argument)&&value->packed_value)value=value->packed_value;
            packed_widths+=std::to_string(value->packed_literal&&value->packed_value?value->packed_value->width:0)+",";
            signs+=value->signed_value?"true,":"false,";values.push_back(value);
        }
        auto result=node("call",1,values);result->text_value=true;
        std::string code="return s.write_text({";
        for(size_t i=0;i<values.size();++i)code+="call_arg"+std::to_string(i)+",";
        std::string path=scope->path;
        if(!scope->static_wave_path.empty()) {
            path.clear();for(const auto& part:scope->static_wave_path){if(!path.empty())path+='.';path+=part;}
        }
        result->literal=code+"},"+signs+"},"+packed_widths+"},"+quote(path)+","+std::to_string(scope->time.unit_fs)+"ULL,'"+radix+"'"+(has_objects?","+objects+"}":std::string())+");";
        return result;
    }
    E binary_read_expression(VeriUnaryExp* call) {
        needs_file_io=true;needs_text=true;
        const auto args=veri_system_arguments(call->exp_child());
        std::vector<E> values;
        // File/range expressions run before the destination address. A memory
        // element's address is evaluated only when at least one byte is read.
        for(size_t i=1;i<args.size();++i) {
            auto value=expr(args[i]);
            if(value->text_value)fail(args[i],"$fread descriptor/range requires an integral value");
            values.push_back(value);
        }
        auto result=node("call",32,values);result->signed_value=true;
        result->procedural_only=true;result->event_safe=false;result->io_state=true;
        ProcessIR effect;std::string code;
        if(unpacked_value(args[0])) {
            auto view=array_copy_view(args[0]);
            if(view.dimensions.size()!=1||view.variable.range_depth()!=1||view.offset)
                fail(args[0],"$fread requires a whole fixed one-dimensional array");
            if(enum_identity(view.variable.node)||veri_dynamic_string_value(args[0]))
                fail(args[0],"$fread requires integral non-enum elements");
            const int width=view.variable.dlen();if(width>64)needs_wide=true;
            // Unlike assignment, fread traverses increasing numeric indices,
            // including for memories declared with descending bounds.
            if(view.dimensions.front().descending)std::reverse(view.words.begin(),view.words.end());
            for(int id:view.words) {
                writable(id,args[0]);
                if(signals[id].net)fail(args[0],"$fread requires an integral variable target");
                effect.touches.insert(id);effect.partial_writes.insert(id);
                effect.writes.push_back({id,0,signals[id].width,0});
            }
            const auto table="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(view.words);
            const auto& dim=view.dimensions.front();
            code="const auto binary_fd=s.file_integer(call_arg0);s.file_handle(binary_fd);";
            code+="const int64_t binary_start="+(args.size()>2?"int32_t(s.file_integer(call_arg1))":std::to_string(dim.base))+";";
            code+="const int64_t binary_count="+(args.size()>3?"int32_t(s.file_integer(call_arg2))":std::to_string(int64_t(dim.base)+dim.count)+"-binary_start")+";";
            code+="if(binary_start<"+std::to_string(dim.base)+"||binary_start>="+std::to_string(int64_t(dim.base)+dim.count)+"||binary_count<0)throw std::runtime_error(\"$fread array range out of bounds\");uint32_t binary_bytes=0;";
            code+="for(int64_t i=binary_start;i<std::min<int64_t>("+std::to_string(int64_t(dim.base)+dim.count)+",binary_start+binary_count);++i){auto binary_word=s.file_read_word(binary_fd,"+std::to_string(width)+");binary_bytes+=uint32_t(binary_word.count);if(binary_word.count!="+std::to_string((width-1)/8+1)+")break;";
            auto id=table+"[i-("+std::to_string(dim.base)+")]";if(parallel_count)id="sid["+id+"]";
            code+="s.set("+id+",binary_word.value);}return V(binary_bytes,0,32);";
        } else {
            if(args.size()!=2)fail(args[0],"$fread start/count require an unpacked array");
            if(enum_identity(args[0])||veri_dynamic_string_value(args[0]))fail(args[0],"$fread requires an integral non-enum target");
            auto target=lvalue(args[0]);
            if(target.parts.size()!=1||(args[0]->detail_type()!=veEXP_PRI&&args[0]->detail_type()!=veEXP_ARRAY))
                fail(args[0],"$fread member/concatenation targets are not supported yet");
            for(const auto& part:target.parts) {
                if(signals[part.signal].net)fail(args[0],"$fread requires a variable target");
                if(part.memory>=0&&memories[size_t(part.memory)].dynamic)fail(args[0],"$fread dynamic array targets are not supported yet");
            }
            if(target.width>64)needs_wide=true;
            const bool selected_target=args[0]->detail_type()==veEXP_ARRAY;
            code="auto binary_word=s.file_read_word(s.file_integer(call_arg0),"+std::to_string(target.width)+");";
            if(selected_target)code+="if(binary_word.count>0){";
            auto value=node("saved",target.width);value->literal="binary_word.value";
            write(effect,target,value,false,false);
            for(const auto& instruction:effect.instructions)code+=instruction.code;
            if(selected_target)code+="}";
            code+="return V(uint32_t(binary_word.count),0,32);";
        }
        result->literal=std::move(code);
        result->selection_checks|=effect.selection_checks;result->random_state|=effect.random_state;result->io_state|=effect.io_state;
        result->reads.insert(effect.reads.begin(),effect.reads.end());result->touches.insert(effect.touches.begin(),effect.touches.end());
        result->function_reads.insert(effect.function_reads.begin(),effect.function_reads.end());
        result->partial_writes.insert(effect.partial_writes.begin(),effect.partial_writes.end());result->whole_writes.insert(effect.whole_writes.begin(),effect.whole_writes.end());
        result->nonstatic_writes.insert(effect.nonstatic_writes.begin(),effect.nonstatic_writes.end());result->sensitivity_reads=effect.sensitivity_reads;
        for(const auto& part:effect.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        return result;
    }
    E dynamic_cast_expression(VeriUnaryExp* call,bool task=false) {
        const auto args=veri_system_arguments(call->exp_child());
        if(args.size()!=2)fail(call,"$cast requires exactly two arguments");
        if(veri_virtual_interface(args[0])||veri_virtual_interface(args[1]))fail(call,"$cast on virtual interface handles is not supported; use a compatible typed assignment");
        if(unpacked_value(args[0])||unpacked_value(args[1]))fail(call,"$cast requires singular arguments");
        auto target=lvalue(args[0]);
        if(target.parts.size()!=1)fail(args[0],"$cast destination requires a variable lvalue");
        auto& part=target.parts.front();
        if(signals[part.signal].net)fail(args[0],"$cast destination requires a variable");
        if(!part.object)writable(part.signal,args[0]);
        ProcessIR effect;std::string code;unsigned capture=0;
        // Evaluate destination selectors once, even when the type check fails.
        auto freeze=[&](E& expression) {
            if(!expression)return;
            read(effect,expression);auto saved=std::make_shared<Expr>(*expression);
            const auto name="cast_destination"+std::to_string(capture++);
            code+="auto "+name+"="+emit(expression)+";";
            saved->op=expression->op=="container_ref"?"saved_ref":"saved";saved->literal=name;saved->args.clear();expression=saved;
        };
        freeze(part.associative_ref);freeze(part.object);freeze(part.index);freeze(part.word_index);
        auto source=expr(args[1]);if(source->interface_type)fail(call,"$cast on virtual interface handles is not supported; use a compatible typed assignment");read(effect,source);
        const int destination_class=class_type(args[0]);
        std::string check="true";bool incompatible=false;
        if(destination_class>=0) {
            incompatible=source->object_type==-1||(source->object_type>=0&&!class_compatible(source->object_type,destination_class)&&!class_compatible(destination_class,source->object_type));
            effect.reads.insert(objects_signal);
            check=incompatible?"false":"s.object_can_cast(cast_source,"+std::to_string(destination_class)+")";
        } else {
            const bool text=part.object?part.object_text:signals[part.signal].text_value;
            incompatible=source->object_type!=-1||text!=source->text_value;
            if(incompatible)check="false";
            else if(auto* enumeration=veri_enum_type(args[0])) {
                check="false";
                auto saved=std::make_shared<Expr>(*source);saved->op="saved";saved->literal="cast_source";saved->args.clear();
                for(auto* member:enumeration->enum_values())check+="||("+emit(node("===",1,{saved,number(member)}))+").truth()==1";
            }
        }
        code+="auto cast_source="+emit(source)+";if("+check+"){";
        auto accepted=std::make_shared<Expr>(*source);accepted->op="saved";accepted->literal="cast_source";accepted->args.clear();
        accepted->object_type=destination_class;
        if(!incompatible)write(effect,target,accepted,false,false);
        for(const auto& instruction:effect.instructions)code+=instruction.code;
        code+="return V(1,0,32);}";
        code+=task?"throw std::runtime_error(\"$cast failed: destination unchanged\");":"return V(0,0,32);";
        auto result=node("call",32);result->literal=std::move(code);result->signed_value=true;
        result->procedural_only=true;result->event_safe=false;result->selection_checks=effect.selection_checks;
        result->io_state=effect.io_state;result->random_state=effect.random_state;
        result->reads=effect.reads;result->touches=effect.touches;result->function_reads=effect.function_reads;
        result->partial_writes=effect.partial_writes;result->whole_writes=effect.whole_writes;result->nonstatic_writes=effect.nonstatic_writes;
        result->sensitivity_reads=effect.sensitivity_reads;
        for(const auto& written:effect.writes){result->writes.insert(written.signal);result->write_ranges.emplace(written.signal,written.lo,written.width);}
        return result;
    }
    E file_expression(VeriUnaryExp* call) {
        if(call->op()==vtSYS_FREAD)return binary_read_expression(call);
        needs_file_io=true;needs_text=true;
        auto args=veri_system_arguments(call->exp_child());
        const int op=call->op();
        std::vector<E> values;
        for(size_t i=0;i<args.size();++i)if(op!=vtSYS_FGETS||i!=0) {
            auto value=expr(args[i]);
            if(op!=vtSYS_FOPEN&&value->text_value)fail(args[i],"file descriptor/offset requires an integral value");
            values.push_back(value);
        }
        auto result=node("call",32,values);result->signed_value=true;result->procedural_only=true;result->event_safe=false;result->io_state=true;
        if(op==vtSYS_FOPEN) {
            result->literal="return V(s.file_open(format(call_arg0,'s'),"+std::string(args.size()==2?"format(call_arg1,'s')":"std::string()")+","+(args.size()==1?"true":"false")+"),0,32);";return result;
        }
        if(op!=vtSYS_FGETS) {
            const std::string method=op==vtSYS_FGETC?"file_getc":op==vtSYS_UNGETC?"file_ungetc":op==vtSYS_FEOF?"file_eof":op==vtSYS_FTELL?"file_tell":op==vtSYS_FSEEK?"file_seek":"file_rewind";
            std::string parameters;
            for(size_t i=0;i<values.size();++i){if(i)parameters+=",";parameters+="s.file_integer("+std::string(values[i]->signed_value?"signed_size(":"(")+"call_arg"+std::to_string(i)+std::string(values[i]->signed_value?",32)":").size(32)")+")";}
            result->literal="return V(uint32_t(s."+method+"("+parameters+")),0,32);";return result;
        }
        auto target=lvalue(args[0]);
        if(enum_identity(args[0]))fail(args[0],"$fgets enum target requires an explicit conversion");
        for(const auto& part:target.parts)if(signals[part.signal].net)fail(args[0],"$fgets requires a variable target");
        const bool text=veri_dynamic_string_value(args[0]);
        if(!text&&target.width<8)fail(args[0],"$fgets packed target requires at least one byte");
        if(target.width>64)needs_wide=true;
        ProcessIR effect;
        std::string code="auto line=s.file_gets(s.file_integer(call_arg0),"+(text?"0":std::to_string(target.width/8))+ ");if(line.count>0"+(text?std::string("||line.count==0"):std::string())+"){";
        auto value=node("saved",target.width);value->text_value=text;
        value->literal=text?"V::text(line.text.substr(0,line.text.find('\\0')))":"packed_text(line.text,"+std::to_string(target.width)+")";
        write(effect,target,value,false,false);
        for(const auto& instruction:effect.instructions)code+=instruction.code;
        result->literal=code+"}return V(uint32_t(line.count),0,32);";
        result->selection_checks|=effect.selection_checks;result->random_state|=effect.random_state;result->io_state|=effect.io_state;
        result->reads.insert(effect.reads.begin(),effect.reads.end());result->touches.insert(effect.touches.begin(),effect.touches.end());
        result->function_reads.insert(effect.function_reads.begin(),effect.function_reads.end());
        result->partial_writes.insert(effect.partial_writes.begin(),effect.partial_writes.end());result->whole_writes.insert(effect.whole_writes.begin(),effect.whole_writes.end());
        result->nonstatic_writes.insert(effect.nonstatic_writes.begin(),effect.nonstatic_writes.end());result->sensitivity_reads=effect.sensitivity_reads;
        for(const auto& part:effect.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        return result;
    }
    E random_control_expression(VeriMemberExp* call,bool statement=false) {
        needs_random=needs_constraints=true;
        auto arguments=veri_system_arguments(call->arguments());const bool seed=call->member()=="srandom";
        if((seed&&arguments.size()!=1)||arguments.size()>1)fail(call,"random control argument count mismatch");
        if(!statement&&(seed||!arguments.empty()))fail(call,"random control setter is a void method");
        auto* target=call->object()->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(call->object()):nullptr;
        if(target&&(!target->class_member()||!target->class_owner()))target=nullptr;
        if(seed)target=nullptr;
        auto* implicit_target=!seed&&call->object()->detail_type()==veEXP_PRI?call->class_member():nullptr;
        if(!seed&&!target&&!implicit_target&&arguments.empty())fail(call,"random control query requires an individual property or constraint");
        auto result=node("call",32,{implicit_target?implicit_this(call):expr(target?target->object():call->object())});result->procedural_only=true;result->event_safe=false;result->random_state=true;
        result->signed_value=true;
        if(!arguments.empty())result->args.push_back(expr(arguments.front()));
        result->reads.insert(objects_signal);result->writes.insert(objects_signal);result->write_ranges.emplace(objects_signal,0,64);
        if(seed){result->literal="s.object_srandom(call_arg0,call_arg1);return V(0,0,32);";return result;}
        std::string method=call->member()=="rand_mode"?"object_rand_mode":"object_constraint_mode",selector;
        if(target)selector=call->member()=="rand_mode"?","+std::to_string(object_fields.at(target->class_member()).second):","+quote(static_cast<VeriConstraintDecl*>(target->class_member())->name());
        if(implicit_target)selector=","+std::to_string(object_fields.at(implicit_target).second);
        if(arguments.empty()&&call->member()=="rand_mode")method="object_rand_mode_enabled";
        result->literal=arguments.empty()?"return V(s."+method+"(call_arg0"+selector+"),0,32);":"s."+method+"(call_arg0"+selector+",call_arg1);return V(0,0,32);";
        return result;
    }
    E constraint_foreach(VeriConstraintForeach* loop) {
        const auto saved=reduction_items;
        struct Restore {std::map<VeriNode*,E>& items;std::map<VeriNode*,E> saved;~Restore(){items=std::move(saved);}} restore{reduction_items,saved};
        auto* array=loop->array();auto* symbol=veri_array_element_symbol(array);
        if(!variable(symbol))fail(loop,"constraint foreach requires variable array storage");
        auto shape=veri_array_shape(array);const auto& names=loop->names();
        const auto suffix=std::to_string(constraint_loop_sequence++);
        const auto assoc=associative_view(array),queue=object_queue_view(array);
        const int dynamic=dynamic_object(array);
        auto value=node("constraint_foreach",1);std::string code;
        if(assoc.id>=0) {
            if(names.size()>size_t(shape.unpacked))fail(loop,"constraint foreach has too many indices");
            auto view=assoc;
            for(size_t axis=0;axis<names.size();++axis) {
                if(names[axis].empty())fail(loop,"omitted multidimensional associative constraint indices are not supported yet");
                const auto cursor="constraint_index"+suffix+"_"+std::to_string(axis),ref="constraint_array"+suffix+"_"+std::to_string(axis),more=cursor+"_more";
                auto descriptor=associative_reference_expr(view);const auto count=value->value;read_effect(value,descriptor);value->value=count;
                if(associative_queue_leaf(view))code+="auto "+ref+"="+emit(descriptor)+";for(size_t "+more+"=0;"+more+"<s.associative_queue_size("+ref+");++"+more+"){V "+cursor+"(uint32_t("+more+"),0,32);";
                else code+="auto "+ref+"="+emit(descriptor)+";V "+cursor+";for(bool "+more+"=s.associative_cursor("+ref+","+cursor+",0);"+more+";"+more+"=s.associative_cursor("+ref+","+cursor+",2)){";
                auto index=node("reduce_item",32);index->literal=cursor;index->signed_value=Variable{loop->index_scope()->value_same_level(names[axis])}.is_signed()==IS_TRUE;
                index->text_value=veri_array_container_kind(array,axis)==vrASSOC_STRING;
                if(auto* key=veri_associative_key_type(array,axis)){index->width=key->dlen();index->signed_value=key->is_signed()==IS_TRUE;index->object_type=class_type(key);index->enum_id=enum_identity(key);}
                reduction_items[loop->index_scope()->value_same_level(names[axis])]=index;view.prefix.push_back(index);++value->value;
            }
        } else if(queue.id>=0||dynamic>=0) {
            if(names.size()!=1||names[0].empty())fail(loop,"dynamic constraint foreach requires one index");
            if(queue.id>=0)read_effect(value,queue.receiver);
            const int dependency=queue.id>=0?queue.id:dynamic;value->reads.insert(dependency);value->direct_reads.insert(dependency);
            const auto cursor="constraint_index"+suffix,ref="constraint_array"+suffix,ordinal="constraint_ordinal"+suffix;
            const auto random=random_array_binding(array);
            const auto size=!random.empty()?random+".size()":queue.id>=0?"s.object_queue_size("+object_queue_reference(queue)+")":"s.dynamic_size("+sid(dynamic)+")";
            code="auto "+ref+"="+size+";for(size_t "+ordinal+"=0;"+ordinal+"<"+ref+";++"+ordinal+"){V "+cursor+"(uint32_t("+ordinal+"),0,32);";
            auto index=node("reduce_item",32);index->literal=cursor;index->signed_value=true;
            reduction_items[loop->index_scope()->value_same_level(names[0])]=index;value->value=1;
        } else {
            if(object_fields.count(symbol))fail(loop,"unsupported class array in constraint foreach");
            if(shape.unbound)fail(loop,"unsupported unbound constraint foreach receiver");
            // Fixed axes retain declaration direction and may omit indices.
            for(size_t d=0;d<names.size();++d)if(!names[d].empty()) {
                const auto cursor="constraint_index"+suffix+"_"+std::to_string(d),ordinal=cursor+"_ordinal";
                const auto bounds=shape.dimensions.at(d);
                const auto count=uint64_t(std::abs(int64_t(bounds.first)-bounds.second))+1;
                code+="for(uint64_t "+ordinal+"=0;"+ordinal+"<"+std::to_string(count)+"ull;++"+ordinal+"){V "+cursor+"(uint32_t(int64_t("+std::to_string(bounds.first)+")"+(bounds.first<=bounds.second?"+":"-")+"int64_t("+ordinal+")),0,32);";
                auto index=node("reduce_item",32);index->literal=cursor;index->signed_value=true;
                reduction_items[loop->index_scope()->value_same_level(names[d])]=index;++value->value;
            }
        }
        const auto loop_count=value->value;
        auto predicate=expr(loop->body());read_effect(value,predicate);value->value=loop_count;
        value->op="constraint_foreach";value->width=1;value->literal=std::move(code);
        value->args={predicate};return value;
    }
    std::string random_enum_domain(VeriNode* symbol,const E& value) {
        auto* type=veri_enum_type(symbol);if(!type)return {};
        std::string members;
        for(auto* member:type->enum_values()) {
            if(member->no_xz()!=IS_TRUE)fail(symbol,"random enum with X/Z enumerators is not supported yet");
            if(!members.empty())members+=",";
            members+=number(member)->literal;
        }
        return "q.domain("+value->literal+",{"+members+"});";
    }
    E randomize_expression(VeriMemberExp* call) {
        needs_random=needs_constraints=true;
        auto result=node("call",32);result->signed_value=true;result->random_state=true;result->procedural_only=true;result->event_safe=false;
        const auto merge=[&](const E& e) {
            result->reads.insert(e->reads.begin(),e->reads.end());result->touches.insert(e->touches.begin(),e->touches.end());
            result->writes.insert(e->writes.begin(),e->writes.end());result->write_ranges.insert(e->write_ranges.begin(),e->write_ranges.end());
            result->nonstatic_writes.insert(e->nonstatic_writes.begin(),e->nonstatic_writes.end());result->function_reads.insert(e->function_reads.begin(),e->function_reads.end());
            result->io_state|=e->io_state;result->selection_checks|=e->selection_checks;
        };
        auto* caller_scope=scope;
        auto saved_items=reduction_items;
        struct Restore {Lower& lower;Scope* previous;std::map<VeriNode*,E> items;std::map<VeriNode*,std::string> arrays;~Restore(){lower.scope=previous;lower.reduction_items=std::move(items);lower.random_arrays=std::move(arrays);}} restore{*this,scope,std::move(saved_items),random_arrays};
        auto arguments=veri_system_arguments(call->arguments());
        if(call->scope_randomize()) {
            std::vector<LValueIR> targets;std::set<VeriNode*> seen;
            result->literal="ConstraintSolver q;";
            for(auto* arg:arguments) {
                if(arg->detail_type()!=veEXP_PRI)fail(arg,"std::randomize target currently requires a whole scalar variable");
                auto* symbol=static_cast<VeriPrimaryExp*>(arg)->var();
                if(!variable(symbol)||Variable{symbol}.range_depth()||class_type(symbol)!=-1||veri_string_value(symbol)||veri_real_width(symbol))fail(arg,"std::randomize target requires a scalar integral variable");
                if(!seen.insert(symbol).second)fail(arg,"duplicate std::randomize variable");
                auto target=lvalue(arg);if(target.parts.size()!=1||target.parts[0].object)fail(arg,"std::randomize target requires scalar variable storage");
                if(signals.at(target.parts[0].signal).net)fail(arg,"std::randomize target cannot be a net");
                auto value=node("constraint_var",target.width);value->signed_value=Variable{symbol}.is_signed()==IS_TRUE;value->enum_id=enum_identity(symbol);
                value->literal="r"+std::to_string(targets.size());reduction_items[symbol]=value;
                result->literal+="auto "+value->literal+"=q.variable("+std::to_string(value->width)+");"+random_enum_domain(symbol,value);targets.push_back(std::move(target));
            }
            if(call->with_expression()){auto predicate=expr(call->with_expression());merge(predicate);result->literal+="q.require("+emit_constraint(predicate,call,parallel_count!=0)+");";}
            result->literal+="std::vector<V> solved;if(!q.solve([&](){return uint32_t(s.random_unsigned().a);},solved))return V(0,0,32);";
            for(size_t i=0;i<targets.size();++i) {
                auto value=node("saved",targets[i].width);value->enum_id=enum_identity(arguments[i]);value->literal="solved["+std::to_string(i)+"]";
                ProcessIR effect;write(effect,targets[i],value,false,false);
                for(const auto& inst:effect.instructions)result->literal+=inst.code;
                result->reads.insert(effect.reads.begin(),effect.reads.end());result->touches.insert(effect.touches.begin(),effect.touches.end());
                for(auto part:effect.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
            }
            result->literal+="return V(1,0,32);";return result;
        }
        std::set<VeriNode*> selected_fields;
        for(auto* argument:arguments) {
            if(arguments.size()==1&&argument->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(argument)->multi_type()==vemNULL)continue;
            if(argument->detail_type()!=veEXP_PRI)fail(argument,"class randomize variable list requires property names");
            auto* field=static_cast<VeriPrimaryExp*>(argument)->var();
            if(!variable(field)||!object_fields.count(field))fail(argument,"class randomize variable list requires object properties");
            bool member=false;for(auto* owner=call->class_owner();owner;owner=owner->base_class())if(object_fields.at(field).first==owner)member=true;
            if(!member)fail(argument,"class randomize variable list requires properties of the receiver");
            veri_check_class_access(field,call->scope());
            Variable property{field};
            if((property.range_depth()&&(property.range_depth()!=1||(property.container_kind()!=vrOPEN&&property.container_kind()!=vrQUEUE)))||property.real_width()||veri_string_value(field)||class_type(field)!=-1)fail(argument,"class randomize target requires a scalar integral property or one integral dynamic/queue dimension");
            if(static_cast<VeriDecl*>(field->father())->const_property())fail(argument,"class randomize target cannot be const");
            if(!selected_fields.insert(field).second)fail(argument,"duplicate class randomize property");
        }
        if(!active_randomization.insert(call->class_owner()).second)fail(call,"recursive randomization callbacks are not supported yet");
        struct RandomGuard {std::set<VeriSeqBlock*>& active;VeriSeqBlock* type;~RandomGuard(){active.erase(type);}} guard{active_randomization,call->class_owner()};
        result->args.push_back(expr(call->object()));merge(result->args[0]);
        auto receiver=node("saved",64);receiver->literal="random_self";receiver->object_type=call->class_owner()->idx();
        result->reads.insert(objects_signal);result->writes.insert(objects_signal);result->write_ranges.emplace(objects_signal,0,64);
        result->literal="auto random_self=call_arg0;switch(s.object_type(random_self)){";
        // Callback lowering allocates activation slots. Pointer-map order
        // depends on the allocator and even argv path lengths, so use the
        // declaration identity to keep generated slots and cases repeatable.
        std::vector<VeriSeqBlock*> candidates;
        for(const auto& candidate:classes)candidates.push_back(candidate.first);
        std::sort(candidates.begin(),candidates.end(),[](auto* a,auto* b){return a->idx()<b->idx();});
        for(auto* definition:candidates) {
            bool derived=false;
            for(auto* base=definition;base;base=base->base_class())if(base==call->class_owner())derived=true;
            if(!derived||definition->abstract_class())continue;
            scope=generated_scope(caller_scope,"$randomize$"+std::to_string(randomize_sequence++));scope->procedural=true;scope->class_definition=definition;scope->self=receiver;
            reduction_items=restore.items;random_arrays=restore.arrays;
            const auto& type=classes.at(definition);
            // Handle arrays retain references; their pointees must participate
            // in one joint constraint problem. Never treat references as random
            // integers or silently solve each child in a separate randomize().
            bool object_graph=false;
            for(const auto& field:type.fields)if(class_type(field.symbol)>=0&&
                (static_cast<VeriDecl*>(field.symbol->father())->rand_property()||selected_fields.count(field.symbol))&&
                (arguments.empty()||selected_fields.count(field.symbol)))
                object_graph=true;
            if(object_graph) {
                const std::string message="random class-handle properties require joint object-graph constraint solving, which is not supported yet";
                if(definition==call->class_owner()&&compiling_functions.empty())fail(call,message);
                // A supported base call must not require every possible derived
                // solver feature. Library functions can also contain an unused
                // optional rerandomization path. Reject its actual execution
                // explicitly instead of rejecting every caller of the library.
                result->literal+="case "+std::to_string(type.id)+":throw std::runtime_error("+quote(message+": "+class_type_name(type.id))+");";
                continue;
            }
            std::string code="case "+std::to_string(type.id)+":{";
            const auto callback=[&](const char* name) {
                for(auto* base=definition;base;base=base->base_class())if(auto* symbol=base->scope()->value_same_level(name)) {
                    if(symbol->tok_type()!=vtFUNC)fail(call,std::string(name)+" must be a function");
                    auto* bound=veri_bind_class_call(call,base,name,nullptr);
                    auto value=function_call(bound,false,receiver,false);merge(value);return "(void)("+emit(value)+");";
                }
                return std::string();
            };
            const auto pre=callback("pre_randomize"),post=callback("post_randomize");code+=pre;
            std::vector<VeriNode*> random_fields,array_fields;
            for(const auto& field:type.fields)if(class_type(field.symbol)==-1&&(Variable{field.symbol}.container_kind()==vrOPEN||Variable{field.symbol}.container_kind()==vrQUEUE)&&(static_cast<VeriDecl*>(field.symbol->father())->rand_property()||selected_fields.count(field.symbol)))array_fields.push_back(field.symbol);
            const bool arrays=!array_fields.empty();
            if(arrays)code+="std::vector<V> random_sizes;auto random_phase=[&](bool random_size_phase){ConstraintSolver q;";
            else code+="ConstraintSolver q;";
            const auto enabled_field=[&](VeriNode* symbol) {
                return arguments.empty()?"s.object_rand_mode_enabled(random_self,"+std::to_string(object_fields.at(symbol).second)+")":std::string(selected_fields.count(symbol)?"true":"false");
            };
            std::string reset_cycles;
            for(const auto& field:type.fields) {
                auto* declaration=static_cast<VeriDecl*>(field.symbol->father());
                if(!declaration->rand_property()&&!selected_fields.count(field.symbol))continue;
                if(Variable{field.symbol}.range_depth()||class_type(field.symbol)>=0)continue;
                auto value=node("constraint_var",Variable{field.symbol}.dlen());value->signed_value=Variable{field.symbol}.is_signed()==IS_TRUE;value->enum_id=enum_identity(field.symbol);
                value->literal="r"+std::to_string(random_fields.size());reduction_items[field.symbol]=value;
                const auto& location=object_fields.at(field.symbol);
                code+="auto "+value->literal+"=q.variable("+std::to_string(value->width)+",\"f"+std::to_string(location.second)+"\");";random_fields.push_back(field.symbol);
                const auto enabled=enabled_field(field.symbol);
                code+="if(!("+enabled+"))q.require(q.binary(\"==\","+value->literal+",q.constant(s.object_get(random_self,"+std::to_string(classes.at(location.first).id)+","+std::to_string(location.second)+"))));";
                code+="else {"+random_enum_domain(field.symbol,value);
                if(declaration->randc_property()) {
                    code+=(arrays?"if(!random_size_phase){":"")+std::string("auto& cycle=s.object_random_cycle(random_self,")+std::to_string(location.second)+");q.cyclic("+value->literal+",cycle.constraints,cycle.used);"+(arrays?"}":"");
                    reset_cycles+="if("+enabled+"){auto& cycle=s.object_random_cycle(random_self,"+std::to_string(location.second)+");cycle.constraints.clear();cycle.used.clear();}";
                }
                code+="}";
            }
            for(auto* field:array_fields) {
                const auto prefix="ra"+std::to_string(object_fields.at(field).second);random_arrays[field]=prefix;
                const auto ref=object_queue_reference({field,objects_signal,receiver});
                code+="auto "+prefix+"_size=q.variable(32,\""+prefix+"_size\");bool "+prefix+"_enabled="+enabled_field(field)+","+prefix+"_resize=false;auto "+prefix+"_state=s.object_queue_values("+ref+");std::vector<ConstraintSolver::Value> "+prefix+";size_t "+prefix+"_begin=0;";
            }
            std::map<std::string,VeriConstraintDecl*> constraints;
            for(auto* base=definition;base;base=base->base_class()) {
                for(auto* item:classes.at(base).scope->items)if(item->detail_type()==vsDECL_CONSTRAINT) {
                    auto* constraint=static_cast<VeriConstraintDecl*>(item);constraints.emplace(constraint->name(),constraint);
                }
            }
            struct Atom {E value;VeriNode* source;std::string guard;};std::vector<Atom> atoms;
            std::function<void(E,VeriNode*,const std::string&)> add_atom=[&](E value,VeriNode* source,const std::string& guard) {
                if(arrays&&value->op=="&&"){for(auto& child:value->args)add_atom(child,source,guard);return;}
                atoms.push_back({value,source,guard});
            };
            for(const auto& entry:constraints) {auto* constraint=entry.second;constraint->bind();auto predicate=expr(constraint->body());merge(predicate);add_atom(predicate,constraint,"s.object_constraint_mode(random_self,"+quote(entry.first)+")");}
            if(call->with_expression()){auto predicate=expr(call->with_expression());merge(predicate);add_atom(predicate,call,"true");}
            std::vector<bool> element_atoms;
            for(const auto& atom:atoms) {
                std::set<std::string> sizes;bool elements=false;
                std::function<void(const E&)> scan=[&](const E& value) {
                    if(value->op=="constraint_foreach"){elements=true;return;}
                    if(value->op=="constraint_array_read")elements=true;
                    if(value->op=="constraint_array_size")sizes.insert(value->literal.substr(0,value->literal.size()-5));
                    for(auto& child:value->args)scan(child);
                };scan(atom.value);element_atoms.push_back(elements);
                if(arrays&&elements&&!sizes.empty())fail(atom.source,"array size constraints mixed with random elements or foreach require separate constraint expressions");
                for(auto& size:sizes)code+="if("+atom.guard+")"+size+"_resize=true;";
            }
            for(size_t i=0;i<array_fields.size();++i) {
                auto* field=array_fields[i];Variable property{field};const auto prefix=random_arrays.at(field),size_index=std::to_string(random_fields.size()+i);
                if(property.container_kind()==vrQUEUE&&property.container_bound()>=0&&property.container_bound()<1048576)
                    code+="q.require(q.binary(\"<=\","+prefix+"_size,q.constant(V("+std::to_string(uint64_t(property.container_bound())+1)+",0,32)),true));";
                code+="q.require(q.binary(\">=\","+prefix+"_size,q.constant(V(0,0,32)),true));if(random_size_phase){if(!"+prefix+"_enabled||!"+prefix+"_resize)q.require(q.binary(\"==\","+prefix+"_size,q.constant(V("+prefix+"_state.size(),0,32))));}else{q.require(q.binary(\"==\","+prefix+"_size,q.constant(random_sizes.at("+size_index+"))));auto count=random_sizes.at("+size_index+").a;if(count>1048576)throw std::runtime_error(\"random dynamic array size exceeds 1048576 elements\");"+prefix+"_begin=q.variable_count();for(size_t i=0;i<count;++i){auto random_element="+prefix+"_enabled?q.variable("+std::to_string(property.dlen())+"):q.constant(V(0,0,"+std::to_string(property.dlen())+"));";
                auto element=node("constraint_var",property.dlen());element->literal="random_element";
                code+="if("+prefix+"_enabled){"+random_enum_domain(field,element)+"}"+prefix+".push_back(random_element);}}";
            }
            for(size_t i=0;i<atoms.size();++i) {
                const auto& atom=atoms[i];code+="if("+atom.guard+(arrays&&element_atoms[i]?"&&!random_size_phase":"")+")q.require("+emit_constraint(atom.value,atom.source,parallel_count!=0)+");";
            }
            code+="std::vector<V> solved;if(!q.solve([&](){return s.object_random(call_arg0);},solved)){"+(arrays?"if(random_size_phase){"+reset_cycles+"}return false;":"return V(0,0,32);")+"}";
            if(arrays)code+="if(random_size_phase){random_sizes=std::move(solved);return true;}";
            for(size_t i=0;i<random_fields.size();++i) {auto* field=random_fields[i];const auto& location=object_fields.at(field);code+="s.object_set(call_arg0,"+std::to_string(classes.at(location.first).id)+","+std::to_string(location.second)+",solved["+std::to_string(i)+"],"+sid(objects_signal)+");";}
            for(auto* field:array_fields) {
                const auto prefix=random_arrays.at(field);Variable property{field};
                code+="if("+prefix+"_enabled){std::vector<V> values(solved.begin()+"+prefix+"_begin,solved.begin()+"+prefix+"_begin+"+prefix+".size());s.object_queue_replace("+object_queue_reference({field,objects_signal,receiver})+",std::move(values),"+std::to_string(property.dlen())+","+(property.two_state()?"true":"false")+","+std::to_string(property.container_bound())+");}";
            }
            if(arrays)code+="return true;};if(!random_phase(true)||!random_phase(false))return V(0,0,32);";
            result->literal+=code+post+"return V(1,0,32);}";
        }
        result->literal+="default:throw std::runtime_error(\"invalid randomize receiver\");}return V(0,0,32);";
        return result;
    }
    E scan_expression(VeriUnaryExp* call) {
        needs_scan=true;needs_text=true;
        const bool file=call->op()==vtSYS_FSCANF;
        needs_file_io|=file;
        const auto args=veri_system_arguments(call->exp_child());
        auto source=expr(args[0]),fmt=expr(args[1]);
        if(file&&source->text_value)fail(args[0],"$fscanf descriptor requires an integral value");
        auto result=node("call",32,{source,fmt});
        result->signed_value=true;result->procedural_only=true;result->event_safe=false;result->io_state|=file;
        ProcessIR effect;std::string entry,specs="{",stores;
        for(size_t i=2;i<args.size();++i) {
            auto target=lvalue(args[i]);
            if(enum_identity(args[i]))fail(args[i],"scan enum target requires an explicit conversion");
            for(const auto& part:target.parts)if(signals[part.signal].net)fail(args[i],"scan requires a variable target");
            const bool text=veri_dynamic_string_value(args[i]);
            if(target.width>64)needs_wide=true;
            specs+="{"+std::to_string(target.width)+","+(text?"true":"false")+"},";
            // Inout actuals are read left to right before scanning. Only
            // successful conversions evaluate their addresses again at copy-out.
            auto before=expr(args[i]);read(effect,before);entry+="(void)("+emit(before)+");";
            stores+="if(scan_result.values["+std::to_string(i-2)+"].matched){";
            auto value=node("saved",target.width);value->text_value=text;
            value->literal="scan_result.values["+std::to_string(i-2)+"].value";
            const auto first=effect.instructions.size();write(effect,target,value,false,false);
            for(size_t j=first;j<effect.instructions.size();++j)stores+=effect.instructions[j].code;
            stores+="}";
        }
        result->literal=entry+"auto scan_result=s."+(file?"scan_file(s.file_integer(call_arg0)":"scan_string(scan_source(call_arg0)")+",scan_source(call_arg1),"+specs+"}"+(file?"":source->text_value&&!source->packed_literal?",false":",true")+");"+stores+"return V(uint32_t(scan_result.count),0,32);";
        result->selection_checks|=effect.selection_checks;result->io_state|=effect.io_state;result->random_state|=effect.random_state;
        result->reads.insert(effect.reads.begin(),effect.reads.end());result->touches.insert(effect.touches.begin(),effect.touches.end());
        result->function_reads.insert(effect.function_reads.begin(),effect.function_reads.end());
        result->partial_writes.insert(effect.partial_writes.begin(),effect.partial_writes.end());result->whole_writes.insert(effect.whole_writes.begin(),effect.whole_writes.end());
        result->nonstatic_writes.insert(effect.nonstatic_writes.begin(),effect.nonstatic_writes.end());
        result->sensitivity_reads.insert(result->sensitivity_reads.end(),effect.sensitivity_reads.begin(),effect.sensitivity_reads.end());
        for(const auto& part:effect.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        return result;
    }
    E testbench_expression(VeriUnaryExp* call) {
        if(call->op()==vtSYS_SSCANF||call->op()==vtSYS_FSCANF)return scan_expression(call);
        if(veri_is_file_function(call->op()))return file_expression(call);
        const auto args=veri_system_arguments(call->exp_child());
        if(call->op()==vtSYS_SFORMATF)return formatted_value(args[0],{args.begin()+1,args.end()});
        needs_plusargs=true;
        auto format_value=expr(args[0]);
        if(call->op()==vtSYS_TEST_PLUSARGS) {
            auto value=node("call",32,{format_value});value->signed_value=true;
            value->literal="return V(s.test_plusarg(format(call_arg0,'s'))?1:0,0,32);";return value;
        }
        auto target=lvalue(args[1]);
        if(enum_identity(args[1]))fail(args[1],"$value$plusargs enum target requires an explicit conversion");
        for(const auto& part:target.parts)if(signals[part.signal].net)fail(args[1],"$value$plusargs requires a variable target");
        const bool text=veri_dynamic_string_value(args[1]);
        if(text)needs_text=true;
        auto result=node("call",32,{format_value});result->signed_value=true;result->procedural_only=true;result->event_safe=false;
        ProcessIR effect;
        // VCS evaluates the inout actual on entry, and again at successful
        // copy-out. Even a missing plusarg evaluates its actual once.
        auto before=expr(args[1]);read(effect,before);
        std::string code="(void)("+emit(before)+");auto plusarg_value=s.value_plusarg(format(call_arg0,'s'),"+std::to_string(target.width)+","+(text?"true":"false")+");if(plusarg_value.matched){";
        auto value=node("saved",target.width);value->text_value=text;value->literal="plusarg_value.value";
        write(effect,target,value,false,false);
        for(const auto& instruction:effect.instructions)code+=instruction.code;
        result->literal=code+"}return V(plusarg_value.matched?1:0,0,32);";
        result->selection_checks|=effect.selection_checks;result->io_state|=effect.io_state;result->random_state|=effect.random_state;
        result->reads.insert(effect.reads.begin(),effect.reads.end());result->touches.insert(effect.touches.begin(),effect.touches.end());
        result->function_reads.insert(effect.function_reads.begin(),effect.function_reads.end());
        result->partial_writes.insert(effect.partial_writes.begin(),effect.partial_writes.end());
        result->whole_writes.insert(effect.whole_writes.begin(),effect.whole_writes.end());
        result->nonstatic_writes.insert(effect.nonstatic_writes.begin(),effect.nonstatic_writes.end());
        result->sensitivity_reads.insert(result->sensitivity_reads.end(),effect.sensitivity_reads.begin(),effect.sensitivity_reads.end());
        for(const auto& part:effect.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        return result;
    }
    E random_expression(VeriUnaryExp* call) {
        needs_random=true;
        auto result=node("random",32);result->event_safe=false;result->procedural_only=true;result->random_state=true;
        const int op=call->op();result->signed_value=op==vtSYS_RANDOM||op==vtSYS_RANDOM_SEEDED;
        if(op==vtSYS_RANDOM)result->literal="s.random_legacy()";
        else if(op==vtSYS_URANDOM)result->literal="s.random_unsigned()";
        else if(op==vtSYS_URANDOM_SEEDED) {
            auto value=expr(veri_system_arguments(call->exp_child()).front());
            result=node("random",32,{value});result->event_safe=false;result->procedural_only=true;result->random_state=true;
            result->literal="s.random_unsigned("+emit(value,32)+")";
        } else if(op==vtSYS_URANDOM_RANGE) {
            std::vector<E> values;for(auto* arg:veri_system_arguments(call->exp_child()))values.push_back(expr(arg));
            result=node("random",32,values);result->event_safe=false;result->procedural_only=true;result->random_state=true;
            std::string code="([&](){auto random_max="+emit(values[0],32)+";";
            if(values.size()==2)code+="auto random_min="+emit(values[1],32)+";";
            result->literal=code+"return s.random_range(random_max"+(values.size()==2?",random_min":"")+");}())";
        } else {
            auto* seed=veri_system_arguments(call->exp_child()).front();
            auto target=lvalue(seed);
            if(target.parts.size()!=1||target.width<32||enum_identity(seed))fail(seed,"$random seed requires a whole integral variable of at least 32 bits");
            auto& part=target.parts.front();
            if(signals[part.signal].net||part.index||part.lo||part.width!=signals[part.signal].width)
                fail(seed,"$random seed requires a whole integral variable of at least 32 bits");
            ProcessIR effect;std::string code="([&](){";
            // $random's seed is an inout argument: evaluate the input before
            // drawing, then evaluate the output actual at copy-out. In
            // particular seed[i++] addresses two different elements in VCS.
            auto before=expr(seed);
            read(effect,before);
            code+="auto random_before="+emit(before)+";uint32_t random_seed=random_before.size(32).b?0:uint32_t(random_before.a);auto random_value=s.random_legacy(random_seed);";
            auto updated=node("saved",32);updated->signed_value=before->signed_value;updated->literal="V(random_seed,0,32)";
            write(effect,target,updated,false,false);
            for(const auto& inst:effect.instructions)code+=inst.code;
            result->literal=code+"return random_value;}())";
            result->selection_checks=effect.selection_checks;result->reads=effect.reads;result->touches=effect.touches;result->function_reads=effect.function_reads;result->partial_writes=effect.partial_writes;result->whole_writes=effect.whole_writes;result->nonstatic_writes=effect.nonstatic_writes;result->sensitivity_reads=effect.sensitivity_reads;
            for(const auto& write:effect.writes){result->writes.insert(write.signal);result->write_ranges.emplace(write.signal,write.lo,write.width);}
        }
        return result;
    }
    void assign(ProcessIR& p,VeriNode* lhs,E value,bool nba=false,bool drive=false,const std::string& delay={}) {
        if(lhs->detail_type()==veEXP_ARRAY&&veri_dynamic_string_value(static_cast<VeriArrayExp*>(lhs)->id())&&!veri_array_shape(static_cast<VeriArrayExp*>(lhs)->id()).unpacked) {
            auto* selected=static_cast<VeriArrayExp*>(lhs);
            if(nba||drive||!delay.empty())fail(lhs,"string character assignment requires blocking assignment without timing control");
            if(selected->range().size()!=1||static_cast<VeriRangeExp*>(selected->range().front())->rtype()!=vrSINGLE)
                fail(lhs,"string indexing requires one character index");
            if(value->packed_value)value=value->packed_value;
            if(value->text_value)fail(lhs,"string character assignment requires an integral value");
            auto index=expr(static_cast<VeriRangeExp*>(selected->range().front())->left());
            if(index->text_value)fail(lhs,"string index requires an integral value");
            auto position=node("fixed_cast",32,{index});position->signed_value=true;
            auto character=node("fixed_cast",8,{value});
            auto replacement=node("text_method",1,{position,character,expr(selected->id())});replacement->text_value=true;
            replacement->literal="return text_putc(text_arg2,text_arg0,text_arg1);";
            write(p,lvalue(selected->id()),replacement,false,false);return;
        }
        enum_assignment(lhs,value);
        auto target=lvalue(lhs);
        for(auto part:target.parts) if(signals[part.signal].net!=drive)
            fail(lhs,drive?"continuous driver requires a net":"procedural assignment to a net");
        write(p,target,value,nba,drive,delay);
    }
    // Evaluate a read-modify-write target's addresses once, then use the same
    // captured indices for both reading and writing. In particular, a function
    // in a memory/packed index must not run twice.
    void compound(ProcessIR& p,VeriNode* owner,VeriNode* lhs,E rhs,const std::string& op,E* result=nullptr,bool postfix=false) {
        if(veri_virtual_interface(lhs))fail(lhs,"virtual interface handles cannot be modified by integral updates");
        if(veri_string_value(lhs))fail(lhs,"string compound assignments and updates are not supported yet");
        const unsigned enum_id=enum_identity(lhs);
        if(enum_id&&owner->detail_type()!=vsSTMT_UPDATE&&owner->detail_type()!=veEXP_UNA)
            fail(owner,"compound assignment to enum requires an explicit enum cast");
        auto target=lvalue(lhs);std::string prefix="{";int sequence=0;
        for(auto& part:target.parts) {
            if(signals[part.signal].net)fail(lhs,"procedural assignment to a net");
            if(part.receiver_effect){read(p,part.receiver_effect);prefix+="(void)("+emit(part.receiver_effect)+");";part.receiver_effect={};}
            for(auto* address:{&part.virtual_handle,&part.associative_ref,&part.object,&part.word_index,&part.index})if(*address) {
                auto value=*address;read(p,value);
                auto saved=node(value->op=="container_ref"?"saved_ref":"saved",value->width);saved->real_width=value->real_width;saved->signed_value=value->signed_value;saved->object_type=value->object_type;
                saved->literal="update_index"+std::to_string(sequence++);
                prefix+="auto "+saved->literal+"="+emit(value)+";";*address=saved;
            }
        }
        E before;
        for(auto it=target.parts.rbegin();it!=target.parts.rend();++it) {
            const auto& part=*it;auto whole=part;whole.index={};whole.lo=0;whole.width=part.object_width;auto source=part.virtual_handle?virtual_part_read(part):part.associative_ref?associative_part_read(whole):part.object?object_read(whole):signal_expr(part.signal);
            if(part.word_index&&!part.object&&!part.associative_ref) {
                source=memories[size_t(part.memory)].dynamic?dynamic_read_expr(part.signal,part.word_index):node("memory",signals[part.signal].width,{part.word_index});
                if(!memories[size_t(part.memory)].dynamic)source->literal=memory_table(part.memory);
                for(int id:memories[size_t(part.memory)].words){source->reads.insert(id);source->direct_reads.insert(id);}
            }
            E selected=source;
            if(part.index&&part.view_width) {auto view=node("slice",part.view_width,{source});view->literal=std::to_string(part.view_lo)+","+std::to_string(part.view_width);source=view;}
            if(part.index) {
                selected=node("indexed_slice",part.width,{source,part.index});
                selected->literal=std::to_string(part.base)+","+std::to_string(part.width)+","+(part.descending?"true":"false");
            } else if(part.lo||part.width!=((part.object||part.associative_ref)?part.object_width:signals[part.signal].width)) {
                selected=node("slice",part.width,{source});selected->literal=std::to_string(part.lo)+","+std::to_string(part.width);
            }
            auto* declared_member=lhs->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(lhs):
                lhs->detail_type()==veEXP_ARRAY&&static_cast<VeriArrayExp*>(lhs)->id()->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(static_cast<VeriArrayExp*>(lhs)->id()):nullptr;
            if((part.object?part.object_two_state:signals[part.signal].two_state)||(declared_member&&declared_member->field()&&veri_two_state(declared_member->field()->symbol->net_type()))) {needs_two_state_cast=true;selected=node("two_state",selected->width,{selected});}
            before=before?node("concat",before->width+selected->width,{before,selected}):selected;
        }
        // Only a complete variable or complete memory word retains signedness.
        if(lhs->detail_type()==veEXP_PRI)before->signed_value=Variable{static_cast<VeriPrimaryExp*>(lhs)->var()}->is_signed()==IS_TRUE;
        else if(lhs->detail_type()==veEXP_MEMBER){before=node("cast",before->width,{before});before->signed_value=static_cast<VeriMemberExp*>(lhs)->is_signed()==IS_TRUE;}
        else if(lhs->detail_type()==veEXP_ARRAY) {
            auto* a=static_cast<VeriArrayExp*>(lhs);
            if(a->id()->detail_type()==veEXP_PRI) {
                Variable var{static_cast<VeriPrimaryExp*>(a->id())->var()};
                before->signed_value=var->range_depth()&&a->range().size()==size_t(var->range_depth())&&var->is_signed()==IS_TRUE;
            }
        }
        before->real_width=veri_real_width(lhs);const int real_target=before->real_width;
        const bool signed_target=before->signed_value;
        if(result) {
            read(p,before);prefix+="auto update_before="+emit(before)+";";
            before=node("saved",target.width);before->real_width=real_target;before->signed_value=signed_target;before->literal="update_before";
        }
        bool shift=op=="<<"||op==">>"||op==">>>";
        auto value=node(op,shift?target.width:std::max(target.width,rhs->width),{before,rhs});
        value->signed_value=shift?before->signed_value:before->signed_value&&rhs->signed_value;
        // The RHS still executes when a dynamic memory target is invalid.
        // Capture before the guarded store, retaining all read/write metadata.
        read(p,value);prefix+="auto update_value="+(result?"("+emit(value,target.width)+").size("+std::to_string(target.width)+")":emit(value,target.width))+";";
        auto captured=node("saved",target.width);captured->real_width=value->real_width;captured->literal="update_value";
        size_t instruction=p.instructions.size();write(p,target,captured,false,false);
        if(p.instructions.size()!=instruction+1)fail(owner,"internal compound assignment lowering error");
        auto code=prefix+p.instructions[instruction].code;
        if(result) {
            code+="return "+std::string(postfix?"update_before":"update_value")+";";
            auto effect=node("mutation",target.width);effect->real_width=real_target;effect->signed_value=signed_target;effect->enum_id=enum_id;
            effect->literal="([&]()"+code+"}())";
            effect->io_state=p.io_state;effect->random_state=p.random_state;effect->event_safe=p.event_safe;effect->selection_checks=p.selection_checks;effect->reads=p.reads;effect->touches=p.touches;effect->function_reads=p.function_reads;effect->partial_writes=p.partial_writes;effect->whole_writes=p.whole_writes;effect->nonstatic_writes=p.nonstatic_writes;effect->sensitivity_reads=p.sensitivity_reads;
            for(const auto& part:p.writes){effect->writes.insert(part.signal);effect->write_ranges.emplace(part.signal,part.lo,part.width);}
            *result=effect;
        } else {
            p.instructions[instruction].code=code+"}";
            if(p.instructions[instruction].integral_target>=0)
                p.instructions[instruction].integral_value=value;
        }
    }
    void finish_returns(ProcessIR& p) {
        auto transfers=std::move(p.returns.back());p.returns.pop_back();
        for(int jump:transfers.exits)p.instructions[jump].yes=int(p.instructions.size());
    }
    std::string events(const std::set<int>& ids) {
        std::string s="{"; for(int id:ids) s+="{"+sid(id)+",0},"; return s+"}";
    }
    std::string arm_wait_code(int process,int site) const {
        return "\n#ifdef DSIM_COMPILED_WAIT_ENABLED\ns.arm_wait_known<"+std::to_string(process)+","+
            std::to_string(site)+">();\n#else\ns.arm_wait("+runtime_wid(site)+");\n#endif\n";
    }
    std::string wait_code(int p,const std::string& events) {
        int site=int(wait_sites.size()); wait_sites.push_back({p,events,{},false,{},false});
        return arm_wait_code(p,site);
    }
    std::string wait_code(int p,const std::set<int>& ids) {
        auto code=wait_code(p,events(ids));
        auto& site=wait_sites.back();site.static_refs=true;
        for(int id:ids)site.refs.emplace_back(id,0);
        return code;
    }
    using BitIntervals=std::vector<std::pair<int,int>>; // Half-open, physical bit offsets.
    using SensitivityRanges=std::map<int,BitIntervals>;
    bool static_read_prefix(E e,int& signal,int& offset) {
        if(e->op=="signal") {signal=e->signal;offset=0;return e->reads.count(signal);}
        if(e->op=="slice") {
            int parent=0;
            if(!static_read_prefix(e->args[0],signal,parent))return false;
            offset=parent+std::stoi(e->literal);return true;
        }
        if((e->op=="cast"||e->op=="two_state")&&e->width==e->args[0]->width)
            return static_read_prefix(e->args[0],signal,offset);
        return false;
    }
    SensitivityRanges sensitivity_ranges(E e) {
        SensitivityRanges result;int id=-1,lo=0;
        if(static_read_prefix(e,id,lo)) {
            auto& ranges=result[id];
            const int first=std::max(0,lo),last=std::min(signals[id].width,lo+e->width);
            if(first<last)ranges.emplace_back(first,last);
            return result;
        }
        const auto append=[&](const E& value) {
            for(auto& [signal,ranges]:sensitivity_ranges(value)) {
                auto& target=result[signal];target.insert(target.end(),ranges.begin(),ranges.end());
            }
        };
        for(const auto& value:e->args)append(value);
        // Calls and mutation expressions contain lowered bodies outside args.
        for(const auto& value:e->sensitivity_reads)append(value);
        for(int signal:e->direct_reads)if(e->reads.count(signal))result[signal]={{0,signals[signal].width}};
        for(int signal:e->reads)if(!result.count(signal))result[signal]={{0,signals[signal].width}};
        for(int signal:e->function_reads)if(!result.count(signal))result[signal]={{0,signals[signal].width}};
        return result;
    }
    static BitIntervals merge_intervals(BitIntervals ranges) {
        std::sort(ranges.begin(),ranges.end());BitIntervals result;
        for(auto range:ranges) {
            if(range.first>=range.second)continue;
            if(result.empty()||result.back().second<range.first)result.push_back(range);
            else result.back().second=std::max(result.back().second,range.second);
        }
        return result;
    }
    void specialized_sensitivity(ProcessIR& p,int process,VeriNode* source) {
        auto deps=p.reads;deps.insert(p.function_reads.begin(),p.function_reads.end());
        if(needs_object_format&&contains_object_format(p.sensitivity_reads))fail(source,"class formatting in implicit sensitivity is not supported yet; use an explicit event control");
        std::set<int> selected;
        for(int id:p.partial_writes)if(!p.whole_writes.count(id)&&deps.count(id)) {
            if(p.nonstatic_writes.count(id))
                fail(source,"dynamic partial writes of a read variable in always_comb/always_latch require a static whole-variable write; dynamic bit-select sensitivity is not supported yet");
            selected.insert(id);
        }
        for(const auto& part:p.writes)deps.erase(part.signal);
        std::string expressions="{";
        if(!selected.empty()) {
            SensitivityRanges reads;
            for(const auto& value:p.sensitivity_reads)for(auto& [signal,ranges]:sensitivity_ranges(value))
                if(selected.count(signal))reads[signal].insert(reads[signal].end(),ranges.begin(),ranges.end());
            for(int id:selected) {
                if(!reads.count(id))reads[id]={{0,signals[id].width}};
                BitIntervals writes;
                for(const auto& part:p.writes)if(part.signal==id)writes.emplace_back(part.lo,part.lo+part.width);
                writes=merge_intervals(std::move(writes));
                for(auto range:merge_intervals(std::move(reads[id]))) {
                    int next=range.first;
                    const auto watch=[&](int first,int last) {
                        if(first>=last)return;
                        needs_expression_events=true;
                        expressions+="{[&](Sim& s){return slice(s.get("+sid(id)+"),"+std::to_string(first)+","+std::to_string(last-first)+");},{"+sid(id)+"},0,true},";
                    };
                    for(auto write:writes) {
                        if(write.second<=next)continue;
                        if(write.first>=range.second)break;
                        watch(next,std::min(write.first,range.second));next=std::max(next,write.second);
                    }
                    watch(next,range.second);
                }
            }
        }
        p.startup_wait=int(wait_sites.size());
        const auto code=wait_code(process,deps);
        if(expressions!="{")wait_sites.back().expressions=expressions+"}";
        add(p,"pc=0; "+code+" return;");
    }
    bool scalar_target(VeriNode* lhs) {
        if(lhs->detail_type()==veEXP_PRI) {
            Variable var{static_cast<VeriPrimaryExp*>(lhs)->var()};
            return !variable_scope(lhs,var)->packed.count(var->name());
        }
        if(lhs->detail_type()==veEXP_ARRAY) {
            auto* array=static_cast<VeriArrayExp*>(lhs);
            const auto& ranges=array->range();size_t unpacked=0;
            if(array->id()->detail_type()==veEXP_PRI) {
                auto* symbol=static_cast<VeriPrimaryExp*>(array->id())->var();
                if(variable(symbol)) {
                    Variable var{symbol};unpacked=size_t(var.range_depth());
                    if(veri_array_shape(symbol).dimensions.size()>unpacked+1)return ranges.size()==veri_array_shape(symbol).dimensions.size()&&static_cast<VeriRangeExp*>(ranges.back())->rtype()==vrSINGLE;
                    if(unpacked&&ranges.size()==unpacked)return !variable_scope(lhs,var)->packed.count(var.name());
                }
            }
            return ranges.size()==unpacked+1&&static_cast<VeriRangeExp*>(ranges.back())->rtype()==vrSINGLE;
        }
        return false;
    }
    void continuous_write(ProcessIR& p,const LValueIR& target,E value) {
        if(value->packed_value)value=value->packed_value;if(value->text_value)fail(nullptr,"continuous string assignments are not supported yet");
        for(auto part:target.parts)if(signals[part.signal].text_value)fail(nullptr,"continuous string assignments are not supported yet");
        if(net_target(target)) write(p,target,value,false,true);
        else {
            // A variable port connection is an implicit continuous assignment,
            // with ordinary variable conversion and no net resolution. Stage a
            // mixed concatenation once before updating either destination kind.
            read(p,value);
            const auto begin=p.instructions.size();
            add(p,"{auto port_value="+emit(value,target.width)+";");
            auto saved=node("saved",target.width);saved->literal="port_value";
            LValueIR nets,variables;nets.width=variables.width=target.width;
            for(auto part:target.parts)(signals[part.signal].net?nets:variables).parts.push_back(part);
            if(!nets.parts.empty())write(p,nets,saved,false,true);
            const auto first=p.writes.size();
            write(p,variables,saved,false,false);
            for(size_t i=first;i<p.writes.size();++i)p.writes[i].continuous=true;
            add(p,"}");
            std::string code;
            for(size_t i=begin;i<p.instructions.size();++i)code+=p.instructions[i].code;
            p.instructions.resize(begin);add(p,std::move(code));
        }
    }
    void continuous(VeriNode* lhs,E value,VeriNode* control=nullptr,const LValueIR* selected_target=nullptr) {
        if(value->procedural_only)throw std::runtime_error("output/inout function requires a procedural expression");
        ProcessIR p; int pidx=int(processes.size());
        uint64_t rise=0,fall=0,turnoff=0;
        if(control) {
            auto* d=static_cast<VeriDelayExp*>(control);
            rise=constant_delay_value(d->delay1());
            fall=d->delay2()?constant_delay_value(d->delay2()):rise;
            turnoff=d->delay3()?constant_delay_value(d->delay3()):std::min(rise,fall);
        }
        enum_assignment(lhs,value);
        auto target=selected_target?*selected_target:lvalue(lhs);const bool variables=!net_target(target);
        for(auto part:target.parts)if(part.index||part.word_index)fail(lhs,"variable selects in continuous driver targets are not supported yet");
        if(variables&&control) {
            auto* d=static_cast<VeriDelayExp*>(control);
            if(d->delay2()||d->delay3())fail(lhs,"continuous assignments containing variables require a single delay value");
        }
        if(rise||fall||turnoff) {
            needs_continuous_delay=true;needs_variable_continuous|=variables;
            std::string parts="{";
            for(auto part:target.parts)parts+="{"+sid(part.signal)+","+std::to_string(part.lo)+","+std::to_string(part.width)+","+std::to_string(part.rhs_lo)+","+std::to_string(signals[part.signal].net?driver++:-1)+"},";
            const auto channel=parallel_count?"cid["+std::to_string(continuous_channels.size())+"]":"continuous_channel"+std::to_string(continuous_channels.size());
            continuous_owners.push_back(pidx);
            for(auto part:target.parts){p.touches.insert(part.signal);part.continuous=!signals[part.signal].net;p.writes.push_back(part);}
            continuous_channels.push_back(std::string(parallel_count?"":"auto ")+channel+"=s.continuous_driver("+parts+"},"+std::to_string(target.width)+");\n");
            read(p,value);
            add(p,"s.drive_continuous("+channel+","+emit(value,target.width)+","+std::to_string(rise)+"ULL,"+std::to_string(fall)+"ULL,"+std::to_string(turnoff)+"ULL,"+((selected_target?selected_target->width==1:scalar_target(lhs))?"true":"false")+");");
        } else continuous_write(p,target,value);
        // Continuous drivers remain sensitive during their own output update.
        // Arm first so feedback nets can schedule the next delta evaluation.
        p.continuous_wait=int(wait_sites.size());
        Instruction wait;wait.code=wait_code(pidx,p.reads);
        p.instructions.insert(p.instructions.begin(),std::move(wait));
        add(p,"pc=0; return;");
        processes.push_back(std::move(p));
    }
    uint64_t constant_delay_value(VeriNode* operand) {
        std::string decimal;
        if(operand->detail_type()==veEXP_PRI) {
            auto* primary=static_cast<VeriPrimaryExp*>(operand);
            if(primary->time_literal()) {
                const auto literal=veri_time_literal(primary->str());
                auto scale=scope->time;scale.unit_fs=1;
                for(int i=0;i<literal.exponent;++i)scale.unit_fs*=10;
                try{return delay_ticks(literal.number,scale,precision_fs);}catch(const std::exception& error){fail(operand,error.what());}
            }
            if(primary->pri_type()==veNUM&&primary->str().find('\'')==std::string::npos)decimal=primary->str();
        }
        if(decimal.empty()) {
            auto e=expr(operand);
            if(!e->reads.empty()||e->op!="literal"||e->unknown||e->host_overflow)fail(operand,"delay must be a nonnegative constant literal or integral parameter");
            if(e->negative)fail(operand,"negative constant delays are not supported yet");
            if(e->real_width){auto* cached=static_cast<VeriExp*>(operand)->calc_value();if(!cached)fail(operand,"unresolved constant real delay");std::ostringstream text;text<<std::setprecision(17)<<cached->real_value();decimal=text.str();}
            else decimal=std::to_string(e->value);
        }
        decimal.erase(std::remove(decimal.begin(),decimal.end(),'_'),decimal.end());
        try{return delay_ticks(decimal,scope->time,precision_fs);}catch(const std::exception& error){fail(operand,error.what());}
    }
    std::string procedural_delay(ProcessIR& p,VeriNode* control) {
        if(control->detail_type()!=veEXP_DELAY)fail(control,"intra-assignment control requires a delay; event/repeat controls are not implemented");
        auto* d=static_cast<VeriDelayExp*>(control);
        if(d->delay2()||d->delay3())fail(control,"multi-value procedural delays are not supported");
        auto* operand=d->delay1();
        // A syntactic unary minus otherwise bypasses the literal fast path and
        // becomes an unsigned runtime delay. Keep constant-negative controls
        // within the explicit unsupported boundary.
        if(veri_elaboration_constant(operand)) {
            auto constant=veri_constant_value(static_cast<VeriExp*>(operand),0);
            if(constant&&constant->no_xz()==IS_TRUE&&constant->is_signed()==IS_TRUE&&constant->get_certain_bit(constant->bits()-1)==1)
                fail(operand,"negative constant delays are not supported yet");
        }
        // Preserve decimal real-literal rounding and the existing constant fast path.
        if(operand->detail_type()==veEXP_PRI) {
            auto* primary=static_cast<VeriPrimaryExp*>(operand);
            if(primary->pri_type()==veNUM&&primary->str().find('\'')==std::string::npos)
                return std::to_string(constant_delay_value(operand))+"ULL";
        }
        auto value=expr(operand);
        if(value->packed_value)value=value->packed_value;if(value->text_value)fail(operand,"string cannot be used as a delay");
        if(value->op=="literal"&&!value->unknown)
            return std::to_string(constant_delay_value(operand))+"ULL";
        read(p,value);
        needs_dynamic_delay=true;
        return "procedural_delay_ticks("+emit(value,value->signed_value?64:0)+","+std::to_string(scope->time.unit_fs/scope->time.precision_fs)+"ULL,"+std::to_string(scope->time.precision_fs/precision_fs)+"ULL)";
    }
    bool equivalent_elements(Variable a,Variable b,bool require_same_state=true,bool require_same_aggregate=true) const {
        auto type=[](Variable v){return v.integer()?vvINT:v.formal()?v.tf()->net_type():v.result()?v.fn()->func()->result_type():v.packed()->net_type();};
        const int at=type(a),bt=type(b);
        const auto av=veri_virtual_interface(a.node),bv=veri_virtual_interface(b.node);
        if(bool(av)!=bool(bv)||(av&&(av->name!=bv->name||av->view!=bv->view)))return false;
        return a.real_width()==b.real_width()&&(at==vvSTRING)==(bt==vvSTRING)&&a.dlen()==b.dlen()&&a.is_signed()==b.is_signed()&&(!require_same_state||a.two_state()==b.two_state())&&
            enum_identity(a.node)==enum_identity(b.node)&&class_type(a.node)==class_type(b.node)&&(!require_same_aggregate||veri_aggregate_type(a.node)==veri_aggregate_type(b.node))&&
            (!(veri_integral_atom(at)||veri_integral_atom(bt))||at==bt);
    }
    bool compatible_value_elements(Variable a,Variable b) const {
        // Value transfers may convert state representation. Ref bindings retain
        // exact element equivalence, since they alias the original descriptor.
        const int actual=class_type(a.node),expected=class_type(b.node);
        if(actual>=0||expected>=0)return actual>=0&&expected>=0&&class_compatible(actual,expected);
        // Packed aggregates transfer as integral values. Keep nominal aggregate
        // identity for unpacked structs and for ref bindings above; associative
        // index types are checked separately before copying their storage.
        auto* aa=veri_aggregate_type(a.node);auto* ba=veri_aggregate_type(b.node);
        const bool unpacked=(aa&&aa->unpacked_struct())||(ba&&ba->unpacked_struct());
        return equivalent_elements(a,b,false,unpacked);
    }
    std::vector<int> formal_words(const Callable& fn,size_t ordinal) const {
        Variable var{veri_formal_symbol(fn.formals[ordinal])};
        if(!var.range_depth()||var.dynamic())return {fn.scope->ids.at(var.name())};
        const auto& memory=memories.at(fn.scope->memories.at(var.name()));
        std::vector<int> words;words.reserve(memory.words.size());
        for(size_t i=0;i<memory.words.size();++i) {
            size_t offset=0;
            for(const auto& dim:memory.dimensions){size_t part=(i/size_t(dim.stride))%size_t(dim.count);offset+=(dim.descending?size_t(dim.count)-1-part:part)*size_t(dim.stride);}
            words.push_back(memory.words.at(offset));
        }
        return words;
    }
    bool array_formal(const Callable& fn,size_t i) const {return Variable{veri_formal_symbol(fn.formals[i])}.range_depth()!=0;}
    void check_array_argument(const ArrayCopyView& actual,Variable formal,VeriNode* where,bool reference=false) {
        if(actual.dimensions.size()!=size_t(formal.range_depth()))fail(where,"array argument rank mismatch");
        for(size_t d=0;d<actual.dimensions.size();++d) {
            int first,last,count;formal.get_range(unsigned(d+1),first,last,count);
            if(actual.dimensions[d].count!=count)fail(where,"array argument dimension size mismatch");
        }
        if(reference?!equivalent_elements(actual.variable,formal):!compatible_value_elements(actual.variable,formal))
            fail(where,reference?"array arguments require equivalent element types":"array arguments require compatible element types");
    }
    // Tables hold logical IDs, so accesses still resolve through the current
    // automatic frame. Dynamic prefix addresses are evaluated once per transfer.
    std::string array_argument_access(const ArrayCopyView& view,const std::string& offset) {
        if(view.offset) {
            const auto table="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(view.offsets);
            auto id="memory_words"+std::to_string(view.memory)+"["+offset+".a+"+table+"[i]]";
            return parallel_count?"sid["+id+"]":id;
        }
        const auto table="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(view.words);
        return parallel_count?"sid["+table+"[i]]":table+"[i]";
    }
    static bool reference_direction(int direction) {return direction==vpREF||direction==vpCONST_REF;}
    void writable(int id,VeriNode* where=nullptr) {
        if(const_property_signals.count(id))fail(where,"cannot modify static const class property "+signals.at(size_t(id)).name+" or pass it to a writable argument");
        if(readonly_signals.count(id))fail(where,"cannot modify const ref formal or pass it to a writable argument");
    }
    static bool equivalent_ref_containers(Variable source,Variable target) {
        return source.container_kind()==target.container_kind()&&
            (source.container_bound()==target.container_bound()||
             (target.container_kind()==vrQUEUE&&target.container_bound()<0));
    }
    E array_argument(VeriNode* actual,VeriNode* formal,bool reference,bool readonly=false) {
        Variable target{veri_formal_symbol(formal)};
        if(associative_kind(target.container_kind())&&!reference) {
            auto view=associative_view(actual);check_associative_transfer({target.node,-1,{}},view,actual);
            auto value=node("array_argument",target.dlen(),view.receiver?std::vector<E>{view.receiver}:std::vector<E>{});value->array_value=true;
            value->reads.insert(view.id);value->direct_reads.insert(view.id);value->touches.insert(view.id);
            for(const auto& key:view.prefix)read_effect(value,key);
            value->literal="s.associative_snapshot("+associative_reference(view)+")";
            if(auto effect=static_receiver_effect(actual)){read_effect(value,effect);value->literal="([&](){(void)("+emit(effect)+");return "+value->literal+";}())";}
            return value;
        }
        if(associative_kind(target.container_kind())&&reference) {
            auto view=associative_view(actual);
            if(view.id<0||!view.prefix.empty())fail(actual,"associative ref requires a whole associative array variable");
            Variable source{view.symbol};
            if(source.range_depth()!=target.range_depth())fail(actual,"associative ref requires matching rank and key types");
            for(unsigned axis=0;axis<unsigned(target.range_depth());++axis) {
                auto* a=veri_associative_key_type(source.node,axis);auto* b=veri_associative_key_type(target.node,axis);
                if(veri_array_container_kind(source.node,axis)!=veri_array_container_kind(target.node,axis)||
                   source.container_bound(axis)!=target.container_bound(axis)||bool(a)!=bool(b)||
                   (a&&!equivalent_elements(Variable{a},Variable{b})))
                    fail(actual,"associative ref requires matching rank and key types");
            }
            if(!equivalent_elements(source,target))fail(actual,"array arguments require equivalent element types");
            needs_associative_refs=true;
            auto value=node("array_argument",target.dlen(),view.receiver?std::vector<E>{view.receiver}:std::vector<E>{});
            value->reads.insert(view.id);value->direct_reads.insert(view.id);value->touches.insert(view.id);
            if(!readonly){writable(view.id,actual);value->writes.insert(view.id);value->nonstatic_writes.insert(view.id);value->write_ranges.emplace(view.id,0,signals[view.id].width);}
            if(view.receiver)value->literal="([&](){auto array_receiver="+emit(view.receiver)+";return std::vector<V>{V(s.object_associative_reference("+associative_reference(view,"array_receiver")+","+std::to_string(target.dlen())+"),0,32)};}())";
            else value->literal="std::vector<V>{V(s.reference_signal("+sid(view.id)+"),0,32)}";
            if(auto effect=static_receiver_effect(actual)){read_effect(value,effect);value->literal="([&](){(void)("+emit(effect)+");return "+value->literal+";}())";}
            value->event_safe=false;value->procedural_only=true;return value;
        }
        if(target.dynamic()) {
            if(!reference) {
                if(associative_kind(target.container_kind()))fail(actual,"associative array arguments are not supported yet");
                return array_values(actual,target);
            }
            auto object=object_queue_view(actual);
            if(object.id>=0) {
                auto* symbol=object.symbol;Variable source{symbol};
                if(source.range_depth()!=1||target.range_depth()!=1||!equivalent_ref_containers(source,target))
                    fail(actual,"ref array arguments require equivalent container types and bounds");
                if(!equivalent_elements(source,target))fail(actual,"array arguments require equivalent element types");
                needs_object_array_refs=true;
                if(source.container_bound()!=target.container_bound())needs_queue_ref_limits=true;
                auto value=node("array_argument",target.dlen(),{object.receiver});
                value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);value->touches.insert(objects_signal);
                if(!readonly){writable(objects_signal,actual);value->writes.insert(objects_signal);value->nonstatic_writes.insert(objects_signal);value->write_ranges.emplace(objects_signal,0,64);}
                value->literal="([&](){auto array_receiver="+emit(object.receiver)+";return std::vector<V>{V(s.object_array_reference("+object_queue_reference(object,"array_receiver")+","+std::to_string(target.dlen())+","+std::to_string(source.container_kind()==vrQUEUE?source.container_bound():-2)+"),0,32)};}())";
                value->event_safe=false;value->procedural_only=true;return value;
            }
            int id=dynamic_object(actual);auto* symbol=veri_array_element_symbol(actual);
            if(!variable(symbol))fail(actual,"array formal requires an unpacked array actual");
            Variable source{symbol};
            if(associative_kind(source.container_kind())||associative_kind(target.container_kind()))fail(actual,"associative array arguments are not supported yet");
            if(id<0||!equivalent_ref_containers(source,target))
                fail(actual,"ref array arguments require equivalent container types and bounds");
            if(!equivalent_elements(source,target))fail(actual,"array arguments require equivalent element types");
            auto value=node("array_argument",target.dlen());value->reads.insert(id);value->direct_reads.insert(id);value->touches.insert(id);
            if(source.container_bound()!=target.container_bound()) {
                needs_queue_ref_limits=true;
                value->literal="std::vector<V>{V(s.reference_queue_signal("+sid(id)+","+std::to_string(source.container_bound())+"),0,32)}";
            } else value->literal="std::vector<V>{V(s.reference_signal("+sid(id)+"),0,32)}";
            if(!readonly){writable(id,actual);value->writes.insert(id);value->nonstatic_writes.insert(id);value->write_ranges.emplace(id,0,signals[id].width);}
            value->event_safe=false;value->procedural_only=true;
            if(auto effect=static_receiver_effect(actual)){read_effect(value,effect);value->literal="([&](){(void)("+emit(effect)+");return "+value->literal+";}())";}
            return value;
        }
        if(veri_subroutine_call(actual)&&!reference) {
            auto shape=veri_array_shape(actual);
            if(shape.unpacked!=target.range_depth())fail(actual,"array argument rank mismatch");
            for(int d=0;d<shape.unpacked;++d) {
                int first,last,count;target.get_range(d+1,first,last,count);
                if(std::abs(int64_t(shape.dimensions[d].first)-shape.dimensions[d].second)+1!=count)fail(actual,"array argument dimension size mismatch");
            }
            return array_values(actual,target);
        }
        auto view=array_copy_view(actual);check_array_argument(view,target,actual,reference);
        const auto count=std::to_string(view.offset?view.offsets.size():view.words.size());
        auto value=node("array_argument",target.dlen(),view.offset?std::vector<E>{view.offset}:std::vector<E>{});
        const auto id=array_argument_access(view,"argument_offset");
        std::string code="([&](){";
        if(view.offset)code+="auto argument_offset="+emit(view.offset)+";";
        if(reference&&view.offset)code+="if(argument_offset.b)throw std::runtime_error(\"ref array prefix is unknown or out of range\");";
        code+="std::vector<V> argument_values("+count+");for(size_t i=0;i<"+count+";++i)argument_values[i]=";
        std::string load=reference?"V(s.reference_signal("+id+"),0,32)":"s.get("+id+")";
        if(view.offset&&!reference)load="argument_offset.b?"+std::string(target.two_state()?"V(0,0,":"V::x(")+std::to_string(target.dlen())+"):"+load;
        value->literal=code+load+";return argument_values;}())";
        for(int word:view.words) {
            value->reads.insert(word);value->direct_reads.insert(word);value->touches.insert(word);
            if(reference) {
                if(signals[word].net)fail(actual,"ref array actual must be variable storage");
                if(!readonly){writable(word,actual);value->writes.insert(word);value->nonstatic_writes.insert(word);value->write_ranges.emplace(word,0,signals[word].width);
                if(view.offset)value->partial_writes.insert(word);}
            }
        }
        if(reference){value->event_safe=false;value->procedural_only=true;}
        return value;
    }
    void array_copyout(ProcessIR& p,VeriNode* actual,const Callable& fn,size_t ordinal,bool caller_context=false) {
        Variable target{veri_formal_symbol(fn.formals[ordinal])};
        if(associative_kind(target.container_kind())) {
            auto destination=associative_view(actual);if(destination.id<0)fail(actual,"associative output requires an associative array variable");
            associative_assignment(p,destination,{target.node,formal_words(fn,ordinal).front(),{}},actual,caller_context);return;
        }
        if(target.dynamic()) {
            int id=dynamic_object(actual);
            if(id<0)fail(actual,"dynamic array copyout requires a whole dynamic array actual");
            if(associative_signals.count(id))fail(actual,"associative array arguments are not supported yet");
            if(!compatible_value_elements(Variable{veri_array_element_symbol(actual)},target))fail(actual,"array arguments require compatible element types");
            writable(id,actual);const int source=formal_words(fn,ordinal).front();
            read(p,signal_expr(source));p.touches.insert(source);p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
            if(caller_context)add(p,"{auto returned_values=s.dynamic_values("+sid(source)+");auto task_caller=s.task_output_context();"+replace_array_values(id,"returned_values")+"}");
            else add(p,replace_array_values(id,"s.dynamic_values("+sid(source)+")"));return;
        }
        auto view=array_copy_view(actual);check_array_argument(view,target,actual);
        const auto words=formal_words(fn,ordinal);const auto count=std::to_string(words.size());
        const auto source="array_copy_words"+std::to_string(array_copy_words.size());array_copy_words.push_back(words);
        const auto destination=array_argument_access(view,"argument_offset");
        std::string code="{std::vector<V> returned_values("+count+");for(size_t i=0;i<"+count+";++i)returned_values[i]=s.get("+(parallel_count?"sid[":"")+source+"[i]"+(parallel_count?"]":"")+");";
        if(caller_context)code+="auto task_caller=s.task_output_context();";
        if(view.offset){read(p,view.offset);code+="auto argument_offset="+emit(view.offset)+";if(!argument_offset.b)";}
        code+="for(size_t i=0;i<"+count+";++i)s.set("+destination+",returned_values[i]);}";
        for(int id:words){read(p,signal_expr(id));p.touches.insert(id);}
        for(int id:view.words){writable(id,actual);if(signals[id].net)fail(actual,"array output actual must be variable storage");p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});if(view.offset){p.partial_writes.insert(id);p.nonstatic_writes.insert(id);}}
        add(p,code);
    }
    E reference_argument(VeriNode* actual,VeriNode* formal,bool readonly=false) {
        if(class_type(actual)!=class_type(formal))fail(actual,"ref arguments require matching class handle types");
        auto* base=actual;
        if(actual->detail_type()==veEXP_ARRAY)base=static_cast<VeriArrayExp*>(actual)->id();
        auto* symbol=base->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(base)->var():
            base->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(base)->hierarchical_symbol():nullptr;
        if(!variable(symbol)||unpacked_value(actual))
            fail(actual,"ref requires a whole variable or unpacked array element");
        Variable a{symbol},f{veri_formal_symbol(formal)};
        if(actual->detail_type()==veEXP_ARRAY&&static_cast<VeriArrayExp*>(actual)->range().size()!=size_t(a.range_depth()))
            fail(actual,"ref does not support packed bit/part selections");
        if(a.dynamic())fail(actual,"ref to a dynamic array element is not supported yet");
        auto part=storage_part(actual);
        if(signals[part.signal].net)fail(actual,"ref actual must be a variable, not a net");
        if(!equivalent_elements(a,f))fail(actual,"ref requires equivalent argument types without value conversion");
        auto value=node("reference",32,part.word_index?std::vector<E>{part.word_index}:std::vector<E>{});
        if(part.virtual_handle) {
            read_effect(value,part.virtual_handle);value->op="reference";
            value->literal="([&](){auto vif_reference_handle="+emit(part.virtual_handle)+";if(vif_reference_handle.b||!vif_reference_handle.a)throw std::runtime_error(\"null virtual interface dereference\");switch(vif_reference_handle.a){";
            for(const auto& choice:part.virtual_targets) {
                value->literal+="case "+std::to_string(choice.first)+"ULL:return V(uint64_t("+sid(choice.second)+"),0,32);";
                value->reads.insert(choice.second);value->direct_reads.insert(choice.second);value->touches.insert(choice.second);
                if(!readonly){writable(choice.second,actual);value->writes.insert(choice.second);value->nonstatic_writes.insert(choice.second);value->write_ranges.emplace(choice.second,0,part.width);}
            }
            value->literal+="default:throw std::runtime_error(\"invalid virtual interface handle\");}}())";
        } else if(part.object) {
            if(part.word_index||part.index||part.lo||part.width!=part.object_width)fail(actual,"ref requires a whole scalar class property");
            if(part.object_const&&!readonly)fail(actual,"nonconst ref cannot bind a const class property");
            needs_object_scalar_refs=true;
            read_effect(value,part.object);value->op="reference";
            value->literal="V(s.object_scalar_reference("+emit(part.object)+","+std::to_string(part.object_type)+","+std::to_string(part.object_field)+","+sid(objects_signal)+","+(part.object_two_state?"true":"false")+","+std::to_string(part.object_real)+"),0,32)";
            value->reads.insert(objects_signal);value->direct_reads.insert(objects_signal);value->touches.insert(objects_signal);
            if(!readonly){writable(objects_signal,actual);value->writes.insert(objects_signal);value->nonstatic_writes.insert(objects_signal);value->partial_writes.insert(objects_signal);value->write_ranges.emplace(objects_signal,0,signals[objects_signal].width);}
        } else if(part.word_index) {
            const auto& memory=memories[size_t(part.memory)];
            if(memory.fixed_count)fail(actual,"ref to a compact fixed array element is not supported yet");
            value->literal="([&](){auto ref_index="+emit(part.word_index)+";auto ref_part=indexed_part(0,"+std::to_string(memory.words.size())+",ref_index,"+std::to_string(memory.base)+",1,false,0);if(!ref_part.width)throw std::runtime_error(\"ref array index is unknown or out of range\");return V(s.reference_signal("+(parallel_count?"sid[":"")+"memory_words"+std::to_string(part.memory)+"[ref_part.lo]"+(parallel_count?"]":"")+"),0,32);}())";
            for(int id:memory.words){value->reads.insert(id);value->direct_reads.insert(id);value->touches.insert(id);if(!readonly){writable(id,actual);value->writes.insert(id);value->nonstatic_writes.insert(id);value->write_ranges.emplace(id,0,signals[id].width);value->partial_writes.insert(id);}}
        } else {
            value->literal="V(s.reference_signal("+sid(part.signal)+"),0,32)";
            value->reads.insert(part.signal);value->direct_reads.insert(part.signal);value->touches.insert(part.signal);if(!readonly){writable(part.signal,actual);value->writes.insert(part.signal);value->nonstatic_writes.insert(part.signal);value->write_ranges.emplace(part.signal,0,part.width);}
        }
        value->event_safe=false;value->procedural_only=true;
        if(part.receiver_effect) {
            auto with_effect=std::make_shared<Expr>(*value);
            with_effect->literal="([&](){(void)("+emit(part.receiver_effect)+");return "+value->literal+";}())";
            auto combined=node("call",32,{part.receiver_effect,value});combined->op="reference";combined->literal=with_effect->literal;
            combined->event_safe=false;combined->procedural_only=true;return combined;
        }
        return value;
    }
    std::string reference_entry(const Callable& fn,const std::string& prefix,bool function=false) const {
        std::string code=function?"auto ref_guard=s.reference_activation({":"s.push_activation({";
        const auto& ids=function?fn.locals:fn.scope->activation_variables;
        for(int id:ids)if(automatic_signals.count(id)&&!reference_signals.count(id))code+=sid(id)+",";
        code+="},{";
        for(size_t i=0;i<fn.formals.size();++i)if(reference_direction(fn.directions[i])) {
            auto words=formal_words(fn,i);
            for(size_t k=0;k<words.size();++k)code+="{"+sid(words[k])+",int("+prefix+std::to_string(i)+(array_formal(fn,i)?"["+std::to_string(k)+"]":"")+".a)},";
        }
        return code+"});";
    }
    void declare_callable_variable(VeriNode* symbol) {
        register_ipc_type(symbol);
        Variable var{symbol};if(var.real_width())needs_real=true;
        if(veri_chandle_value(symbol)&&var.dynamic())fail(symbol,"chandle dynamic containers are not supported yet");
        if(auto* aggregate=veri_aggregate_type(symbol);var.dynamic()&&aggregate&&aggregate->unpacked_struct()&&associative_queue_type(symbol))fail(symbol,"associative queues of structs are not supported yet");
        if(var.dynamic()&&var.real_width())fail(symbol,"dynamic real containers are not supported yet");
        if(var.dynamic()&&var.range_depth()!=1&&!associative_kind(var.container_kind()))fail(symbol,"runtime containers require one unpacked dimension");
        if(var->dlen()<1||var->dlen()>1048576)fail(symbol,"unsupported subroutine variable range");
        auto nm=var->name();if(scope->ids.count(nm))return;
        scope->symbols[nm]=symbol;
        if(veri_string_value(symbol)&&var.dynamic()&&var.container_kind()!=vrQUEUE)
            fail(symbol,"string arrays in subroutine signatures currently require queues");
        if(veri_string_value(symbol)&&!var.range_depth()) {
            const int id=int(signals.size());scope->ids[nm]=id;
            signals.push_back({scope->path+"."+nm,1,0,false,false,false,true});
            needs_text=true;subroutine_signals.insert(id);
            if(scope->automatic_storage){automatic_signals.insert(id);scope->activation_variables.insert(id);}
            return;
        }
        auto* declared=veri_declared_type(symbol);
        bool packed=declared?(declared->vec_scalar()==vpVECTOR||declared->enum_type()||declared->aggregate_type()||veri_integral_atom(declared->net_type())):var.result()?(var.fn()->func()->integral_result()||var.fn()->func()->range()!=nullptr):
                    var.formal()?(veri_integral_atom(var.tf()->net_type())||static_cast<VeriTfDecl*>(symbol->father())->range()!=nullptr):true;
        if(var.dynamic()) {
            const int id=int(signals.size());scope->ids[nm]=id;
            signals.push_back({scope->path+"."+nm,var.dlen(),var.dend(),false,var.two_state(),false,false,var.real_width()});
            dynamic_signals.insert(id);subroutine_signals.insert(id);
            if(auto* aggregate=veri_aggregate_type(symbol);aggregate&&aggregate->unpacked_struct())container_aggregate_types[id]=aggregate_components(aggregate);
            if(veri_string_value(symbol)){if(var.container_kind()!=vrQUEUE)fail(symbol,"string arrays in subroutine signatures currently require queues");needs_text=true;string_element_signals.insert(id);}
            if(var.container_kind()==vrQUEUE)queue_bounds[id]=var.container_bound();
                    if(associative_queue_type(symbol))object_queue_storage=true;
            if(associative_kind(var.container_kind()))associative_signals.insert(id);
            if(var.container_kind()==vrASSOC_UINT)unsigned_associative_signals.insert(id);
            if(var.container_kind()==vrASSOC_CLASS)class_associative_signals.insert(id);
            if(var.container_kind()==vrASSOC_STRING){string_associative_signals.insert(id);needs_text=true;}
                    for(int axis=1;axis<var.range_depth();++axis)if(veri_array_container_kind(symbol,axis)==vrASSOC_STRING)needs_text=true;
            if(scope->automatic_storage){automatic_signals.insert(id);scope->activation_variables.insert(id);}
            scope->memories[nm]=int(memories.size());memories.push_back({0,{id},{{0,0,1,false}},true});
            if(var.dlen()>64)needs_wide=true;return;
        }
        if(var.range_depth()) {
            if(scope->memories.count(nm))return;
            MemoryIR memory{};int count=1;
            for(int depth=1;depth<=var.range_depth();++depth) {
                int first,last,size;var.get_range(unsigned(depth),first,last,size);
                if(std::min(first,last)<0||size<1||size>1048576||count>1048576/size)fail(symbol,"formal arrays require nonnegative fixed bounds with at most 1048576 elements");
                memory.dimensions.push_back({std::min(first,last),size,0,first>last});count*=size;
            }
            int stride=1;for(auto it=memory.dimensions.rbegin();it!=memory.dimensions.rend();++it){it->stride=stride;stride*=it->count;}
            memory.base=memory.dimensions.size()==1?memory.dimensions.front().base:0;
            for(int i=0;i<count;++i) {
                std::string word=nm;
                for(const auto& dim:memory.dimensions)word+="["+std::to_string(dim.base+(i/dim.stride)%dim.count)+"]";
                const int id=int(signals.size());signals.push_back({scope->path+"."+word,var.dlen(),var.dend(),false,var.two_state(),false,false,var.real_width()});
                signals[id].text_value=veri_string_value(symbol);needs_text|=signals[id].text_value;
                aggregate_default(id,veri_aggregate_type(symbol));
                scope->ids[word]=id;scope->symbols[word]=symbol;if(packed)scope->packed.insert(word);memory.words.push_back(id);subroutine_signals.insert(id);
                if(class_type(symbol)!=-1)object_signals[id]=class_type(symbol);
                if(scope->automatic_storage){automatic_signals.insert(id);scope->activation_variables.insert(id);}
            }
            scope->memories[nm]=int(memories.size());memories.push_back(std::move(memory));needs_indexed_select=true;
            if(var.dlen()>64)needs_wide=true;return;
        }
        int id=int(signals.size());scope->ids[nm]=id;
        if(packed)scope->packed.insert(nm);
        signals.push_back({scope->path+"."+nm,var->dlen(),var->dend(),false,var.two_state(),false,false,var.real_width()});
        aggregate_default(id,veri_aggregate_type(symbol));
        if(class_type(symbol)!=-1)object_signals[id]=class_type(symbol);
        subroutine_signals.insert(id);if(scope->automatic_storage){automatic_signals.insert(id);scope->activation_variables.insert(id);}if(var->dlen()>64)needs_wide=true;
    }
    void formal_declarations(VeriNode* n,Callable& fn) {
        if(!n)return;
        if(n->detail_type()==vsDECL_FUNC_PORT_LIST){for(auto* d:static_cast<VeriFuncPortList*>(n)->func_port())formal_declarations(d,fn);return;}
        if(n->detail_type()==vsDECL_TASK_PORT_LIST){for(auto* d:static_cast<VeriTaskPortList*>(n)->task_port())formal_declarations(d,fn);return;}
        if(n->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST){for(auto* d:static_cast<VeriFuncItemDeclList*>(n)->func_item())formal_declarations(d,fn);return;}
        if(n->detail_type()==vsDECL_TASK_ITEM_DECL_LIST){for(auto* d:static_cast<VeriTaskItemDeclList*>(n)->task_item())formal_declarations(d,fn);return;}
        if(n->detail_type()!=vsDECL_TF_DECL)return;
        auto* decl=static_cast<VeriTfDecl*>(n);
        for(auto* port:decl->port_ids()){fn.formals.push_back(port);fn.directions.push_back(decl->inout());}
    }
    void initialize_activation(ProcessIR& p,Scope* frame,const std::set<int>& inputs={}) {
        std::string code;
        for(int id:frame->activation_variables) {
            if(inputs.count(id))continue;
            p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
            if(event_value_signals.count(id)) {
                p.side_effect=true;p.selection_only_effects=false;p.event_safe=false;p.touches.insert(objects_signal);
                code+="s.set("+sid(id)+",V(uint64_t(s.named_event("+sid(objects_signal)+"))+1,0,64));";
            }
            else if(aggregate_defaults.count(id))code+="s.set("+sid(id)+","+emit(aggregate_defaults.at(id))+");";
            else if(associative_signals.count(id))code+="s.associative_delete("+sid(id)+",V(0),true,"+std::to_string(signals[id].width)+");";
            else if(dynamic_signals.count(id))code+="s.dynamic_replace("+sid(id)+",{},"+std::to_string(signals[id].width)+","+(signals[id].two_state?"true":"false")+");";
            else if(signals[id].real_width)code+="s.set("+sid(id)+",V::real(0,"+std::to_string(signals[id].real_width)+"));";
            else if(signals[id].text_value)code+="s.set("+sid(id)+",V::text(\"\"));";
            else code+="s.set("+sid(id)+","+(signals[id].two_state?"V(0,0,":"V::x(")+std::to_string(signals[id].width)+"));";
        }
        if(!code.empty())add(p,code);
        for(const auto& init:frame->activation_initializers) {
            if(init.value) {
                read(p,init.value);p.touches.insert(init.signal);p.writes.push_back({init.signal,0,signals[init.signal].width,0});
                add(p,"s.set("+sid(init.signal)+","+emit(init.value,signals[init.signal].width)+");");
            } else {
                const auto& source=*init.process;
                p.reads.insert(source.reads.begin(),source.reads.end());p.touches.insert(source.touches.begin(),source.touches.end());
                p.function_reads.insert(source.function_reads.begin(),source.function_reads.end());
                p.partial_writes.insert(source.partial_writes.begin(),source.partial_writes.end());
                p.whole_writes.insert(source.whole_writes.begin(),source.whole_writes.end());
                p.nonstatic_writes.insert(source.nonstatic_writes.begin(),source.nonstatic_writes.end());
                p.sensitivity_reads.insert(p.sensitivity_reads.end(),source.sensitivity_reads.begin(),source.sensitivity_reads.end());
                p.writes.insert(p.writes.end(),source.writes.begin(),source.writes.end());
                p.function_forks|=source.function_forks;p.io_state|=source.io_state;p.random_state|=source.random_state;p.side_effect|=source.side_effect;p.selection_only_effects&=source.selection_only_effects;p.selection_checks|=source.selection_checks;p.event_safe&=source.event_safe;
                for(const auto& inst:source.instructions)add(p,inst.code);
            }
        }
    }
    std::string activation_entry(Scope* frame) const {
        std::string code="s.push_activation({";
        for(int id:frame->activation_variables)code+=sid(id)+",";
        return code+"});";
    }
    bool activation_storage(Scope* frame) const {
        return !frame->activation_variables.empty();
    }
    std::set<int> callable_inputs(const Callable& fn) {
        std::set<int> inputs;
        if(fn.this_signal>=0)inputs.insert(fn.this_signal);
        for(size_t i=0;i<fn.formals.size();++i)if(fn.directions[i]!=vpOUT)
            for(int id:formal_words(fn,i))inputs.insert(id);
        return inputs;
    }
    VeriNode* constructor_skip=nullptr;
    VeriNode* first_constructor_statement(VeriNode* body) {
        if(!body)return nullptr;
        if(body->detail_type()==vsSTMT_SEQ_BLOCK)return first_constructor_statement(static_cast<VeriSeqBlock*>(body)->stmt_list());
        if(body->detail_type()==vsSTMT_STMT_LIST) {auto& list=static_cast<VeriStmtList*>(body)->stmt_list();return list.empty()?nullptr:first_constructor_statement(list.front());}
        return body;
    }
    void class_initializers(ProcessIR& p,VeriSeqBlock* definition) {
        const auto& fields=classes.at(definition).fields;
        const size_t inherited=definition->base_class()?classes.at(definition->base_class()).fields.size():0;
        for(size_t i=inherited;i<fields.size();++i)if(auto* init=fields[i].initializer) {
            if(Variable{fields[i].symbol}.container_kind()==vrQUEUE||Variable{fields[i].symbol}.container_kind()==vrOPEN) {
                object_queue_assignment(p,{fields[i].symbol,objects_signal,implicit_this(definition)},init);continue;
            }
            auto value=context_expr(init,fields[i].symbol);enum_assignment(fields[i].symbol,value);
            LValueIR target;target.parts.push_back(object_part(fields[i].symbol,implicit_this(definition)));target.parts.front().object_initializer=true;target.width=target.parts.front().width;write(p,target,value,false,false);
        }
    }
    // Constructor actuals have been copied in. Run the immediate base constructor
    // (explicit or implicit), then this class's initializers, then its body.
    void constructor_body(ProcessIR& p,VeriNode* body,VeriSeqBlock* definition,int pidx) {
        auto* first=first_constructor_statement(body);VeriNode* explicit_super=nullptr;
        if(first&&first->detail_type()==vsSTMT_CALL) {
            auto* call=static_cast<VeriCallerStmt*>(first)->caller();
            if(call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->super_reference()&&static_cast<VeriMemberExp*>(call)->member()=="new")explicit_super=first;
        }
        if(definition->base_class()) {
            if(explicit_super)statement(p,explicit_super,pidx);
            else {
                auto* binding=veri_bind_class_call(definition,definition->base_class(),"new",nullptr);
                auto value=function_call(binding,false,implicit_this(definition));read(p,value);add(p,"(void)("+emit(value)+");");
            }
        }
        class_initializers(p,definition);
        auto* outer=constructor_skip;constructor_skip=explicit_super;statement(p,body,pidx);constructor_skip=outer;
    }
    void recursive_signature(const Callable& fn,VeriNode* call) {
        if(fn.result_symbol&&Variable{fn.result_symbol}.range_depth())fail(call,"recursive functions require scalar input formals and scalar results");
        for(size_t i=0;i<fn.formals.size();++i)if(fn.directions[i]!=vpIN&&!reference_direction(fn.directions[i]))fail(call,"recursive functions require input/ref formals and scalar results: "+fn.scope->path+"."+Variable{veri_formal_symbol(fn.formals[i])}.name());
    }
    void initialize_class_statics(Scope* target) {
        auto* saved=scope;
        struct Restore {Scope*& value;Scope* saved;~Restore(){value=saved;}} restore{scope,saved};
        scope=target;
        for(auto* item:target->items)
            if((item->detail_type()==vsDECL_VAR||item->detail_type()==vsDECL_INT)&&static_cast<VeriDecl*>(item)->explicit_static()&&initialized_class_statics.insert(item).second)
                decl_init(item);
    }
    ClassIR& register_callable_class(VeriSeqBlock* definition,VeriNode* call) {
        auto found=classes.find(definition);if(found!=classes.end())return found->second;
        if(definition->generic_class())fail(call,"class method requires a concrete specialization: "+definition->label());
        // Binding a method body can create a specialization after the initial
        // class scan. Its names still belong to the declaration's lexical scope.
        auto* origin=definition->class_origin()?definition->class_origin():definition;
        auto contains=[&](Scope* candidate){return std::find(candidate->items.begin(),candidate->items.end(),origin)!=candidate->items.end();};
        Scope* lexical=nullptr;
        for(auto* candidate=scope;candidate;candidate=candidate->parent)if(contains(candidate)){lexical=candidate;break;}
        if(!lexical)for(const auto& candidate:scopes)if(contains(candidate.get())) {
            if(lexical&&lexical!=candidate.get())fail(call,"class specialization has an ambiguous lexical owner: "+definition->label());
            lexical=candidate.get();
        }
        if(!lexical)fail(call,"class specialization lexical owner is not elaborated: "+definition->label());
        auto* saved=scope;
        struct Restore {Scope*& value;Scope* saved;~Restore(){value=saved;}} restore{scope,saved};
        definition->ensure_class_elaborated();
        if(veri_parser->finish_deferred_semantics()!=OK)fail(call,"late class initialization binding failed: "+veri_parser->get_err_info());
        scope=lexical;register_class(definition);
        return classes.at(definition);
    }
    ClassIR& callable_class(VeriSeqBlock* definition,VeriNode* call) {
        auto found=classes.find(definition);if(found!=classes.end())return found->second;
        const size_t first=scopes.size();
        register_callable_class(definition,call);
        // Registration can also add base or nested classes. Initialize each new
        // class once, including any further classes found by its initializers.
        for(size_t i=first;i<scopes.size();++i)
            if(scopes[i]->class_definition&&!scopes[i]->subroutine)initialize_class_statics(scopes[i].get());
        return classes.at(definition);
    }
    Callable& callable(VeriNode* call,bool function,int process=-1) {
        auto saved_argument_values=std::move(argument_values);auto saved_argument_receiver=std::move(argument_receiver);
        struct RestoreArguments {Lower& lower;std::map<VeriNode*,E> values;E receiver;~RestoreArguments(){lower.argument_values=std::move(values);lower.argument_receiver=std::move(receiver);}} restore_arguments{*this,std::move(saved_argument_values),std::move(saved_argument_receiver)};
        argument_values.clear();argument_receiver={};

        if(!veri_call_hive(call)||veri_call_hive(call)->detail_type()!=(function?vsDECL_FUNC_DECL:vsDECL_TASK_DECL))fail(call,function?"expression requires a function":"statement requires a task");
        auto* declaration=veri_call_hive(call);
        auto nm=function?static_cast<VeriFuncDecl*>(declaration)->func_name():static_cast<VeriTaskDecl*>(declaration)->task_name();
        auto* owner=scope;
        if(call->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(call)->object_type())owner=callable_class(static_cast<VeriMultiExp*>(call)->object_type(),call).scope;
        else if(call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->class_owner()) {
            owner=callable_class(static_cast<VeriMemberExp*>(call)->class_owner(),call).scope;
        }
        else if(call->detail_type()==veEXP_MEMBER) {
            owner=nullptr;
            for(const auto& candidate:scopes)if(!candidate->procedural&&!candidate->generated&&candidate->mod==static_cast<VeriMemberExp*>(call)->call_instance()) {
                if(owner)fail(call,"ambiguous interface subroutine instance");owner=candidate.get();
            }
            if(!owner)fail(call,"interface subroutine instance was not elaborated");
        }
        auto* declared_class=declaration->scope()?veri_class_type(declaration->scope()->value("this")):nullptr;
        if(declared_class)owner=callable_class(declared_class,call).scope;
        for(;!declared_class&&call->detail_type()!=veEXP_MEMBER&&call->detail_type()!=veEXP_MULTI&&owner;owner=owner->parent) {
            bool found=false;
            for(auto* item:owner->items)if(item->detail_type()==declaration->detail_type()&&
                (function?static_cast<VeriFuncDecl*>(item)->func_name():static_cast<VeriTaskDecl*>(item)->task_name())==nm){found=true;break;}
            if(found||(owner->class_definition&&owner->class_definition->class_member(nm)))break;
        }
        if(owner&&owner->class_definition&&nm!="new") {
            for(auto* declaring=owner->class_definition;declaring;declaring=declaring->base_class()) {
                auto* symbol=declaring->scope()->value_same_level(nm);
                if(symbol&&(symbol->tok_type()==vtFUNC||symbol->tok_type()==vtTASK)) {owner=classes.at(declaring).scope;break;}
            }
        }
        if(declaration->birth_mod()->is_package()&&!(owner&&owner->class_definition)) {
            owner=package_scopes.at(declaration->birth_mod());
        }
        if(!owner)fail(call,"only lexical module/generate subroutine calls are supported");
        const auto identity=std::make_pair(owner,nm);
        if(active_subroutines.count(identity)) {
            if(!function&&shared_functions)for(auto& entry:callables)
                if(std::get<0>(entry.first)==owner&&std::get<1>(entry.first)==nm&&entry.second->compiling&&entry.second->task_process>=0)return *entry.second;
            if(!function)fail(call,"recursive tasks are not supported yet: "+owner->path+"."+nm+" (from "+scope->path+")");
            for(auto& entry:callables)if(std::get<0>(entry.first)==owner&&std::get<1>(entry.first)==nm&&entry.second->compiling) {
                auto& fn=*entry.second;
                recursive_signature(fn,call);
                if(shared_functions) {fn.recursive=true;return fn;}
                auto enclosing=std::find(compiling_functions.begin(),compiling_functions.end(),&fn);
                if(enclosing==compiling_functions.end())fail(call,"recursive function has no enclosing activation");
                for(++enclosing;enclosing!=compiling_functions.end();++enclosing) {
                    recursive_signature(**enclosing,call);
                    (*enclosing)->recursive_captures.insert(&fn);
                    (*enclosing)->recursive=true;
                }
                fn.recursive=true;needs_explicit_automatic=needs_process_control=true;return fn;
            }
            fail(call,"mutually recursive functions are not supported yet");
        }
        const bool automatic=(function?static_cast<VeriFuncDecl*>(declaration)->is_auto():static_cast<VeriTaskDecl*>(declaration)->is_auto())==IS_TRUE;
        if(owner->class_definition&&!automatic)fail(call,"class methods require automatic lifetime in this version");
        // A function AST inside an automatic task can be used by several task
        // activations. Give each enclosing call template its own private frame;
        // otherwise unrelated processes share function temporaries and merge
        // into a single scheduler partition.
        Scope* caller_frame=nullptr;
        if(automatic&&!shared_functions)for(auto* lexical=scope;lexical;lexical=lexical->parent)
            if(lexical->subroutine&&(!lexical->parent||!lexical->parent->subroutine)){caller_frame=lexical;break;}
        bool specialized_arguments=false;
        if(shared_functions)for(auto* formal:veri_subroutine_formals(declaration)) {
            auto* symbol=static_cast<VeriTfVar*>(veri_formal_symbol(formal));
            for(unsigned d=1;d<=unsigned(symbol->range_depth());++d)
                if(symbol->open_range(d)&&!symbol->dynamic_array())specialized_arguments=true;
        }
        const bool specialized=automatic&&(!shared_functions||specialized_arguments);
        auto key=std::make_tuple(owner,nm,specialized?call:nullptr,specialized?process:-1,caller_frame);auto existing=callables.find(key);
        Callable* static_template=nullptr;
        if(!shared_functions&&existing!=callables.end()&&std::any_of(existing->second->recursive_captures.begin(),existing->second->recursive_captures.end(),[](const auto* capture){return !capture->compiling;})) {
            if(!automatic)static_template=existing->second.get();
            retired_callables.push_back(std::move(existing->second));callables.erase(existing);existing=callables.end();
        }
        if(existing!=callables.end()) {
            if(existing->second->compiling)fail(call,"recursive subroutines are not supported yet");
            for(auto* capture:existing->second->recursive_captures) {
                auto enclosing=std::find(compiling_functions.begin(),compiling_functions.end(),capture);
                for(++enclosing;enclosing!=compiling_functions.end();++enclosing) {
                    recursive_signature(**enclosing,call);
                    (*enclosing)->recursive_captures.insert(capture);(*enclosing)->recursive=true;
                }
            }
            return *existing->second;
        }
        auto ptr=std::make_unique<Callable>();auto& fn=*ptr;callables[key]=std::move(ptr);fn.compiling=true;fn.recursive_id=recursive_function_next++;
        if(static_template)declaration=static_template->declaration;
        fn.declaration=declaration;
        auto* caller_scope=scope;
        // Rebuild captured code without reallocating a static function's shared
        // arguments, return variable, locals or declaration initializers.
        if(static_template) {
            scope=fn.scope=static_template->scope;fn.result=static_template->result;fn.result_symbol=static_template->result_symbol;
            fn.signed_result=static_template->signed_result;fn.formals=static_template->formals;fn.directions=static_template->directions;
            fn.rebuilding_static=true;
        } else scope=fn.scope=generated_scope(owner,automatic?nm+"$activation"+std::to_string(fn.recursive_id+1):nm);
        scope->procedural=true;scope->subroutine=true;scope->automatic_storage=automatic;
        scope->constructor_class=owner->class_definition&&nm=="new"?owner->class_definition:nullptr;
        scope->static_domain=owner;scope->static_wave_path=owner->wave_path;scope->static_wave_path.push_back(nm);
        scope->static_class_method=owner->class_definition&&static_cast<VeriDecl*>(declaration)->static_method();
        if(owner->class_definition&&!scope->static_class_method) {
            const int id=int(signals.size());fn.this_signal=id;scope->ids["this"]=id;
            scope->symbols["this"]=owner->class_definition->scope()->value_same_level("this");
            signals.push_back({scope->path+".this",64,0,false,true});object_signals[id]=int(owner->class_definition->idx());
            subroutine_signals.insert(id);automatic_signals.insert(id);scope->activation_variables.insert(id);scope->self=signal_expr(id);
            fn.has_references=true;needs_explicit_automatic=needs_process_control=true;
        }
        active_subroutines.insert(identity);
        if(function)compiling_functions.push_back(&fn);
        VeriNode *ports,*items;
        if(function) {
            auto* decl=static_cast<VeriFuncDecl*>(declaration);ports=decl->port_list();items=decl->item_decl();fn.body=decl->stmt();
            // The return symbol is registered in the enclosing parser scope.
            if(!decl->is_void()&&!static_template) {
                auto* ret=decl->scope()->value_within_module(nm);
                if(!ret||ret->tok_type()!=vtFUNC)fail(call,"unresolved function return symbol");
                Variable result_type{ret};
                if(associative_kind(result_type.container_kind()))fail(call,"associative array function returns are not supported yet");
                declare_callable_variable(ret);fn.result_symbol=ret;
                fn.result=result_type.range_depth()&&!result_type.dynamic()?memories.at(scope->memories.at(nm)).words.front():scope->ids.at(nm);
                fn.signed_result=result_type.is_signed()==IS_TRUE;
            }
        } else {
            auto* decl=static_cast<VeriTaskDecl*>(declaration);ports=decl->task_port();items=decl->item_decl();fn.body=decl->stmt();
        }
        if(!static_template){formal_declarations(ports,fn);formal_declarations(items,fn);}
        auto bound_arguments=veri_bind_arguments(call,fn.formals);
        for(size_t i=0;i<fn.formals.size();++i) {
            auto* symbol=static_cast<VeriTfVar*>(veri_formal_symbol(fn.formals[i]));
            if(!symbol->has_open_ranges())continue;
            if(!automatic)fail(fn.formals[i],"unsized array formals currently require an automatic subroutine");
            scope=bound_arguments[i].defaulted?fn.scope->parent:caller_scope;
            const bool dynamic_actual=unpacked_value(bound_arguments[i].value)&&veri_array_shape(bound_arguments[i].value).unbound;
            scope=fn.scope;
            if(dynamic_actual) {
                if(symbol->range_depth()!=1||!symbol->open_range(1))fail(fn.formals[i],"dynamic array formals require one unsized dimension");
                // Promotion must update the dimension metadata too: container_kind()
                // reads that entry once the parser has registered the unsized range.
                symbol->set_dimension_container(0,vrOPEN);continue;
            }
            if(reference_direction(fn.directions[i]))fail(fn.formals[i],"unsized ref formals require dynamic array storage; fixed arrays cannot bind");
            if(fn.directions[i]==vpOUT)fail(fn.formals[i],"unsized output arrays require dynamic allocation, which is not supported yet");
            scope=bound_arguments[i].defaulted?fn.scope->parent:caller_scope;
            auto actual=array_copy_view(bound_arguments[i].value,true);
            if(actual.dimensions.size()!=size_t(symbol->range_depth()))fail(bound_arguments[i].value,"array argument rank mismatch");
            for(unsigned d=1;d<=unsigned(symbol->range_depth());++d)
                if(symbol->open_range(d))symbol->bind_open_range(d,actual.dimensions[d-1].count);
            scope=fn.scope;
        }
        if(!static_template) {
            for(auto* formal:fn.formals)declare_callable_variable(veri_formal_symbol(formal));
            declarations(items);decl_init(items);
        } else {scope->activation_initializers.clear();decl_init(items,true);}
        for(size_t i=0;i<fn.formals.size();++i)if(reference_direction(fn.directions[i])) {
            if(!automatic)fail(fn.formals[i],"ref formals require an automatic subroutine");
            for(int id:formal_words(fn,i)){reference_signals.insert(id);if(fn.directions[i]==vpCONST_REF)readonly_signals.insert(id);fn.scope->activation_variables.erase(id);}
            fn.has_references=true;needs_explicit_automatic=needs_process_control=true;
        }
        if(!function&&shared_functions&&automatic) {
            fn.task_process=int(processes.size());processes.emplace_back();
            fn.task_group=int(fork_groups.size());fork_groups.push_back({-1,{fn.task_process},3});
            ProcessIR body;body.task_template=true;body.source_line=call->line();
            initialize_activation(body,fn.scope,callable_inputs(fn));
            auto outer_blocks=std::move(named_blocks);named_blocks.clear();
            auto outer_identity=std::move(disable_callable_identity);const int outer_ordinal=disable_block_ordinal;
            disable_callable_identity=nm;disable_block_ordinal=0;
            body.returns.push_back({-1,{}});statement(body,fn.body,fn.task_process);finish_returns(body);
            add(body,"s.leave_task();return;");
            processes[size_t(fn.task_process)]=std::move(body);
            disable_callable_identity=std::move(outer_identity);disable_block_ordinal=outer_ordinal;
            named_blocks=std::move(outer_blocks);
        }
        if(function) {
            fn.process.function=true;fn.process.returns.push_back({fn.result,{},enum_identity(call),fn.result_symbol});
            initialize_activation(fn.process,fn.scope,callable_inputs(fn));auto outer_blocks=std::move(named_blocks);named_blocks.clear();
            if(owner->class_definition&&nm=="new")constructor_body(fn.process,fn.body,owner->class_definition,-1);
            else if(static_cast<VeriFuncDecl*>(declaration)->dpi_import())dpi_function_body(fn,static_cast<VeriFuncDecl*>(declaration));
            else statement(fn.process,fn.body,-1);
            finish_returns(fn.process);named_blocks=std::move(outer_blocks);
            for(const auto& sc:scopes)for(auto* ancestor=sc.get();ancestor;ancestor=ancestor->parent)if(ancestor==fn.scope) {
                for(const auto& id:sc->ids)fn.locals.insert(id.second);break;
            }
            compiling_functions.pop_back();
        }
        if(function) {
            function_signals.insert(fn.locals.begin(),fn.locals.end());
            if(automatic)for(int id:fn.locals)if(automatic_signals.count(id))event_function_storage.insert(id);
        }
        active_subroutines.erase(identity);fn.compiling=false;scope=caller_scope;return fn;
    }
    // Cache private scalar automatic storage in host locals. The original
    // body is retained when an observer/force needs every intermediate store.
    // Per-variable guards publish even the exact state at a budget exception.
    std::string cached_function_locals(const Callable& fn,const std::string& original) {
        if(!fn.scope->automatic_storage||fn.recursive||fn.has_references||fn.locals.empty()||fn.locals.size()>16||
           fn.process.side_effect||fn.process.io_state||fn.process.random_state||fn.process.selection_checks||
           fn.process.timing_controls||!fn.process.array_values.empty())return original;
        for(int direction:fn.directions)if(direction!=vpIN)return original;
        for(int id:fn.locals) {
            const auto& signal=signals[size_t(id)];
            if(!automatic_signals.count(id)||signal.width>64||signal.net||signal.text_value||signal.named_event||
               dynamic_signals.count(id)||aggregate_state_masks.count(id))return original;
        }
        // This first implementation accepts only get/set/step in the lowered
        // body. Nested calls, arrays, native loops and other runtime effects
        // retain the existing path. Quoted fragments are never rewritten.
        if(original.find('"')!=std::string::npos||original.find('\'')!=std::string::npos)return original;
        for(size_t at=0;(at=original.find("s.",at))!=std::string::npos;at+=2)
            if(original.compare(at,6,"s.get(")&&original.compare(at,6,"s.set(")&&original.compare(at,7,"s.step("))return original;
        auto body=original;
        const auto replace=[&](const std::string& from,const std::string& to) {
            size_t at=0;while((at=body.find(from,at))!=std::string::npos){body.replace(at,from.size(),to);at+=to.size();}
        };
        std::string prefix="\n#ifndef DSIM_RTL_REFERENCE_FUNCTION_LOCALS\nif(s.function_locals_ready({";
        for(int id:fn.locals)prefix+=sid(id)+",";
        prefix+="})){// Cached automatic scalar function storage.\n";
        for(int id:fn.locals) {
            const auto suffix=std::to_string(id),value="local"+suffix+".value";
            replace("s.get("+sid(id)+")",value);
            replace("s.set("+sid(id)+",","local_set"+suffix+"(");
            prefix+="struct Local"+suffix+"{V& destination;V value;~Local"+suffix+"(){destination=std::move(value);}} local"+suffix+"{s.integral_loop_value("+sid(id)+"),s.get("+sid(id)+")};";
            prefix+="auto local_set"+suffix+"=[&](V value){"+value+"="+(signals[size_t(id)].two_state?"two_state_value(":"(")+"value.size("+std::to_string(signals[size_t(id)].width)+"));};";
        }
        if(body.find("s.set(")!=std::string::npos)return original;
        return prefix+body+"}\n#endif\n"+original;
    }
    E method_receiver(VeriNode* call) {
        if(call->detail_type()==veEXP_MEMBER&&!static_cast<VeriMemberExp*>(call)->scope_reference())return expr(static_cast<VeriMemberExp*>(call)->object());
        return implicit_this(call);
    }
    bool class_scope_call(VeriNode* call) {
        if(call->detail_type()==veEXP_MEMBER)return static_cast<VeriMemberExp*>(call)->scope_reference();
        if(call->detail_type()==veEXP_CALLER) {
            auto* caller=static_cast<VeriCallerExp*>(call)->caller();
            return caller->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(caller)->str().find("::")!=std::string::npos;
        }
        return false;
    }
    // Dispatch alternatives use the parser's ordinary lexical elaboration. Only
    // owned IR survives lowering; runtime selection uses the allocated class ID.
    std::map<std::pair<VeriNode*,VeriSeqBlock*>,VeriNode*> method_bindings;
    VeriSeqBlock* method_owner(VeriNode* call) {
        if(call->detail_type()==veEXP_MEMBER)return static_cast<VeriMemberExp*>(call)->class_owner();
        auto* hive=veri_call_hive(call);if(!hive||!hive->scope())return nullptr;
        return veri_class_type(hive->scope()->value("this"));
    }
    std::string method_name(VeriNode* call) {
        auto* hive=veri_call_hive(call);return hive->detail_type()==vsDECL_FUNC_DECL?static_cast<VeriFuncDecl*>(hive)->func_name():static_cast<VeriTaskDecl*>(hive)->task_name();
    }
    VeriNode* method_binding(VeriNode* call,VeriSeqBlock* owner) {
        auto key=std::make_pair(call,owner);auto found=method_bindings.find(key);if(found!=method_bindings.end())return found->second;
        VeriNode* args=nullptr;
        if(call->detail_type()==veEXP_MEMBER)args=static_cast<VeriMemberExp*>(call)->arguments();
        else if(call->detail_type()==veEXP_CALLER)args=static_cast<VeriCallerExp*>(call)->arg();
        auto* bound=veri_bind_class_call(call,owner,method_name(call),args,veri_call_hive(call));method_bindings.emplace(key,bound);return bound;
    }
    bool virtual_method(VeriNode* call) {
        auto* owner=method_owner(call);if(!owner)return false;
        const auto name=method_name(call);if(name=="new")return false;
        if(call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->super_reference())return false;
        bool is_virtual=false;
        for(auto* base=owner;base;base=base->base_class()) {
            auto* symbol=base->scope()->value_same_level(name);if(!symbol)continue;
            auto* declaration=symbol->tok_type()==vtFUNC?static_cast<VeriDecl*>(static_cast<VeriFunc*>(symbol)->func()):symbol->tok_type()==vtTASK?static_cast<VeriDecl*>(static_cast<VeriTask*>(symbol)->task()):nullptr;
            if(declaration&&declaration->virtual_method())is_virtual=true;
        }
        return is_virtual;
    }
    bool needs_closed_classes=false;
    std::vector<std::pair<int,VeriSeqBlock*>> virtual_targets(VeriNode* call) {
        auto* owner=method_owner(call);if(!owner||!virtual_method(call))return {};
        needs_closed_classes=true;
        const auto name=method_name(call);
        auto* static_type=call->detail_type()==veEXP_MEMBER?veri_class_type(static_cast<VeriMemberExp*>(call)->object()):owner;
        std::vector<std::pair<int,VeriSeqBlock*>> result;
        for(const auto& type:classes)if(!type.first->abstract_class()&&class_compatible(type.second.id,int(static_type->idx()))) {
            auto* selected=type.first;
            while(selected&&!selected->scope()->value_same_level(name))selected=selected->base_class();
            if(selected)result.emplace_back(type.second.id,selected);
        }
        // Allocation addresses differ across hosts; class identities are stable.
        std::sort(result.begin(),result.end(),[](const auto& a,const auto& b){return a.first<b.first;});
        return result;
    }
    E call_argument(const Callable& fn,const std::vector<VeriCallArgument>& args,size_t i,Scope* caller,
                    const std::string& prefix,E receiver={}) {
        // Default ASTs retain declaration/prototype symbol identities. Bind
        // their preceding formals to the caller's already converted, saved
        // values, never to stale callee storage or reevaluated actual ASTs.
        auto previous_values=std::move(argument_values);auto previous_receiver=std::move(argument_receiver);auto* previous_scope=scope;
        struct Restore {Lower& lower;Scope* scope;std::map<VeriNode*,E> values;E receiver;
            ~Restore(){lower.scope=scope;lower.argument_values=std::move(values);lower.argument_receiver=std::move(receiver);}}
            restore{*this,previous_scope,std::move(previous_values),std::move(previous_receiver)};
        argument_values=restore.values;argument_receiver=restore.receiver;
        scope=args[i].defaulted?fn.scope->parent:caller;
        if(args[i].defaulted) {
            argument_values.clear();argument_receiver=receiver;
            auto* signature=args[i].default_formal;
            auto prototypes=signature?veri_subroutine_formals(signature->father()->father()->father()):fn.formals;
            for(size_t j=0;j<i;++j) {
                auto* symbol=veri_formal_symbol(fn.formals[j]);Variable type{symbol};
                auto saved=node("saved",type.dlen());saved->signed_value=type.is_signed()==IS_TRUE;
                saved->enum_id=enum_identity(symbol);saved->text_value=veri_string_value(symbol);saved->real_width=veri_real_width(symbol);saved->object_type=class_type(symbol);saved->interface_type=veri_virtual_interface(symbol);
                saved->literal=prefix+std::to_string(j);
                if(reference_direction(fn.directions[j]))saved->literal="s.get(int("+saved->literal+".a))";
                if(fn.directions[j]==vpOUT)saved->op="argument_storage";
                if(type.range_depth())saved->array_value=true;
                argument_values[symbol]=saved;
                if(j<prototypes.size())argument_values[veri_formal_symbol(prototypes[j])]=saved;
            }
        }
        if(array_formal(fn,i))return array_argument(args[i].value,fn.formals[i],reference_direction(fn.directions[i]),fn.directions[i]==vpCONST_REF);
        if(reference_direction(fn.directions[i]))return reference_argument(args[i].value,fn.formals[i],fn.directions[i]==vpCONST_REF);
        auto* formal=veri_formal_symbol(fn.formals[i]);auto value=argument_context(args[i].value,formal);enum_assignment(formal,value);
        auto argument=node("argument",Variable{formal}.dlen(),{value});
        argument->signed_value=Variable{formal}.is_signed()==IS_TRUE;argument->enum_id=enum_identity(formal);
        argument->real_width=value->real_width;argument->text_value=value->text_value;argument->object_type=value->object_type;argument->interface_type=veri_virtual_interface(formal);
        const bool read_by_default=std::any_of(args.begin()+i+1,args.end(),[](const auto& a){return a.defaulted;});
        if(read_by_default&&Variable{formal}.two_state()&&!argument->real_width&&!argument->text_value&&argument->object_type==-1) {
            needs_two_state_cast=true;auto converted=node("two_state",argument->width,{argument});converted->signed_value=argument->signed_value;converted->enum_id=argument->enum_id;argument=converted;
        }
        const int id=fn.scope->ids.at(Variable{formal}.name());
        if(auto mask=aggregate_state_masks.find(id);read_by_default&&mask!=aggregate_state_masks.end()) {
            auto converted=node("call",argument->width,{argument,mask->second});converted->literal="return masked_two_state_value(call_arg0,call_arg1);";converted->signed_value=argument->signed_value;argument=converted;
        }
        return argument;
    }
    std::map<std::pair<VeriMemberExp*,VeriMod*>,VeriMemberExp*> interface_call_bindings;
    std::vector<std::pair<uint64_t,VeriMemberExp*>> interface_call_targets(VeriMemberExp* call) {
        const auto type=veri_virtual_interface(call->object());
        std::vector<std::pair<uint64_t,VeriMemberExp*>> targets;
        // Binding and lowering can grow scopes. Snapshot actual instances first.
        std::vector<std::pair<uint64_t,VeriMod*>> instances;
        for(size_t i=0;i<scopes.size();++i)if(!scopes[i]->parent&&scopes[i]->mod->is_interface()&&scopes[i]->mod->name()==type->name)
            instances.emplace_back(i+1,scopes[i]->mod);
        auto expected=veri_subroutine_formals(veri_call_hive(call));
        for(const auto& instance:instances) {
            const auto key=std::make_pair(call,instance.second);auto found=interface_call_bindings.find(key);
            auto* bound=found==interface_call_bindings.end()?veri_bind_interface_call(call,instance.second):found->second;
            interface_call_bindings.emplace(key,bound);
            auto actual=veri_subroutine_formals(veri_call_hive(bound));
            if(actual.size()!=expected.size())fail(call,"virtual interface subroutine signature does not match declared type");
            for(size_t i=0;i<actual.size();++i) {
                Variable a{veri_formal_symbol(actual[i])},e{veri_formal_symbol(expected[i])};
                if(!equivalent_elements(a,e)||a.range_depth()!=e.range_depth()||a.tf()->inout()!=e.tf()->inout())fail(call,"virtual interface subroutine signature does not match declared type");
            }
            targets.emplace_back(instance.first,bound);
        }
        if(targets.empty())fail(call,"virtual interface type has no elaborated compatible instance");return targets;
    }
    void interface_call_effects(E& result,const E& body) {
        result->reads.insert(body->reads.begin(),body->reads.end());result->writes.insert(body->writes.begin(),body->writes.end());
        result->function_reads.insert(body->function_reads.begin(),body->function_reads.end());result->touches.insert(body->touches.begin(),body->touches.end());
        result->partial_writes.insert(body->partial_writes.begin(),body->partial_writes.end());result->whole_writes.insert(body->whole_writes.begin(),body->whole_writes.end());
        result->nonstatic_writes.insert(body->nonstatic_writes.begin(),body->nonstatic_writes.end());result->sensitivity_reads.insert(result->sensitivity_reads.end(),body->sensitivity_reads.begin(),body->sensitivity_reads.end());
        result->write_ranges.insert(body->write_ranges.begin(),body->write_ranges.end());result->io_state|=body->io_state;result->random_state|=body->random_state;
        result->selection_checks|=body->selection_checks;result->function_forks|=body->function_forks;result->procedural_only|=body->procedural_only;result->event_safe&=body->event_safe;
        result->event_snapshot|=body->event_snapshot;result->interface_dereference|=body->interface_dereference;result->virtual_dispatch|=body->virtual_dispatch;
    }
    E interface_function_call(VeriMemberExp* call,bool value_required) {
        auto receiver=expr(call->object());auto targets=interface_call_targets(call);E result;
        const auto* declaration=static_cast<VeriFuncDecl*>(veri_call_hive(call));
        const int width=declaration->is_void()||veri_string_value(call)?1:veri_array_shape(call).unpacked?veri_array_element_width(call):veri_bit_width(call);
        for(const auto& target:targets) {
            auto body=function_call(target.second,value_required,{},false);
            if(body->width!=width)fail(call,"virtual interface function result does not match declared type");
            if(!result) {
                result=node("call",width,{receiver});result->array_value=body->array_value;result->text_value=body->text_value;result->real_width=body->real_width;
                result->signed_value=body->signed_value;result->enum_id=enum_identity(call);result->object_type=body->object_type;result->interface_type=body->interface_type;
                result->interface_dereference=true;
                result->literal="if(call_arg0.b||!call_arg0.a)throw std::runtime_error(\"null virtual interface subroutine receiver\");switch(call_arg0.a){";
            }
            result->literal+="case "+std::to_string(target.first)+"ULL:return "+emit(body)+";";interface_call_effects(result,body);
        }
        result->literal+="default:throw std::runtime_error(\"invalid virtual interface subroutine receiver\");}";return result;
    }
    void interface_task_call(ProcessIR& p,VeriMemberExp* call,int pidx) {
        auto value=expr(call->object());read(p,value);auto targets=interface_call_targets(call);
        const int capture=int(signals.size());signals.push_back({scope->path+".$interface_receiver"+std::to_string(capture),64,0,false,true});
        p.touches.insert(capture);p.writes.push_back({capture,0,64,0});
        add(p,"{auto interface_receiver="+emit(value)+";if(interface_receiver.b||!interface_receiver.a)throw std::runtime_error(\"null virtual interface subroutine receiver\");s.set("+sid(capture)+",interface_receiver);}");
        std::vector<int> exits;
        for(const auto& target:targets) {
            auto condition=node("literal",1);condition->literal="V(s.get("+sid(capture)+").a=="+std::to_string(target.first)+"ULL,0,1)";condition->reads.insert(capture);
            const int branch=add(p,"");p.instructions[branch].condition=condition;p.instructions[branch].yes=branch+1;
            task_call(p,target.second,pidx,false,false);exits.push_back(add(p,""));p.instructions[branch].no=int(p.instructions.size());
        }
        add(p,"throw std::runtime_error(\"invalid virtual interface subroutine receiver\");");
        for(int exit:exits)p.instructions[exit].yes=int(p.instructions.size());
    }
    E function_call(VeriNode* call,bool value_required=true,E receiver={},bool dispatch=true,const std::vector<E>* supplied=nullptr) {
        if(call->detail_type()==veEXP_MEMBER&&veri_virtual_interface(static_cast<VeriMemberExp*>(call)->object()))return interface_function_call(static_cast<VeriMemberExp*>(call),value_required);

        auto& fn=callable(call,true);auto args=veri_bind_arguments(call,fn.formals);
        const bool pure=static_cast<VeriDecl*>(veri_call_hive(call))->pure_virtual();
        const bool super=call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->super_reference();
        if(pure&&(!dispatch||super))fail(call,"pure virtual method has no implementation");
        if(value_required&&fn.result<0)fail(call,"void function has no value");
        auto* caller_scope=scope;
        const auto alias=!supplied&&std::any_of(args.begin(),args.end(),[](const auto& a){return a.defaulted;})?"default_arg"+std::to_string(argument_sequence++)+"_":std::string{};
        auto default_self=node("saved",64);default_self->literal=alias+"self";default_self->object_type=fn.this_signal>=0?object_signals.at(fn.this_signal):-1;
        std::vector<E> values;
        for(size_t i=0;i<args.size();++i) {
            if(supplied){values.push_back(supplied->at(i));continue;}
            if(fn.directions[i]==vpOUT){auto zero=node("literal",1);zero->literal="V(0,0,1)";values.push_back(zero);continue;}
            values.push_back(call_argument(fn,args,i,caller_scope,alias,fn.this_signal>=0?default_self:E{}));
        }
        scope=caller_scope;
        if(dispatch&&!class_scope_call(call)) {
            auto targets=virtual_targets(call);
            if(virtual_method(call)||pure) {
                auto self=receiver?receiver:method_receiver(call);
                auto result=node("call",fn.result<0?1:signals[fn.result].width,values);result->args.insert(result->args.begin(),self);result->receiver_argument=true;result->argument_alias_prefix=alias;
                result->interface_type=veri_virtual_interface(fn.result_symbol);
        result->array_value=fn.result_symbol&&Variable{fn.result_symbol}.range_depth();
                result->text_value=fn.result>=0&&signals[fn.result].text_value;result->real_width=fn.result>=0?signals[fn.result].real_width:0;result->signed_value=fn.signed_result;result->enum_id=enum_identity(call);
                if(!result->array_value&&fn.result>=0&&object_signals.count(fn.result))result->object_type=object_signals.at(fn.result);
                auto saved_self=node("saved",64);saved_self->literal="dispatch_self";saved_self->object_type=self->object_type;
                std::vector<E> saved;
                for(size_t i=0;i<values.size();++i){auto value=std::make_shared<Expr>(*values[i]);value->op=(values[i]->op=="reference"||values[i]->op=="array_argument")?values[i]->op:"saved";value->args.clear();value->literal="dispatch_arg"+std::to_string(i);value->reads.clear();value->writes.clear();saved.push_back(value);}
                result->virtual_dispatch=true;result->literal="auto dispatch_self=call_self;";
                for(size_t i=0;i<values.size();++i)result->literal+="auto dispatch_arg"+std::to_string(i)+"=call_arg"+std::to_string(i)+";";
                result->literal+="switch(s.object_type(dispatch_self)){";
                for(const auto& target:targets) {
                    auto* binding=target.second==method_owner(call)?call:method_binding(call,target.second);
                    auto body=function_call(binding,value_required,saved_self,false,&saved);
                    result->literal+="case "+std::to_string(target.first)+":return "+emit(body)+";";
                    result->reads.insert(body->reads.begin(),body->reads.end());result->writes.insert(body->writes.begin(),body->writes.end());
                    result->function_reads.insert(body->function_reads.begin(),body->function_reads.end());result->touches.insert(body->touches.begin(),body->touches.end());
                    result->partial_writes.insert(body->partial_writes.begin(),body->partial_writes.end());result->whole_writes.insert(body->whole_writes.begin(),body->whole_writes.end());
                    result->nonstatic_writes.insert(body->nonstatic_writes.begin(),body->nonstatic_writes.end());result->sensitivity_reads.insert(result->sensitivity_reads.end(),body->sensitivity_reads.begin(),body->sensitivity_reads.end());
                    result->write_ranges.insert(body->write_ranges.begin(),body->write_ranges.end());result->io_state|=body->io_state;result->random_state|=body->random_state;result->selection_checks|=body->selection_checks;
                    result->function_forks|=body->function_forks;result->procedural_only|=body->procedural_only;result->event_safe&=body->event_safe;
                }
                result->reads.insert(objects_signal);result->literal+="default:throw std::runtime_error(\"invalid virtual method receiver\");}";
                if(targets.empty())result->literal+=result->array_value?"return std::vector<V>{};":"return V(0,0,"+std::to_string(result->width)+");"; // Keep the generated lambda's V return type even without concrete descendants.
                return result;
            }
        }
        const bool static_object_call=fn.scope->static_class_method&&call->detail_type()==veEXP_MEMBER&&!static_cast<VeriMemberExp*>(call)->scope_reference();
        if(fn.this_signal>=0)values.insert(values.begin(),receiver?receiver:method_receiver(call));
        else if(static_object_call)values.insert(values.begin(),expr(static_cast<VeriMemberExp*>(call)->object()));
        auto result=node("call",fn.result<0?1:signals[fn.result].width,std::move(values));
        result->receiver_argument=fn.this_signal>=0||static_object_call;result->argument_alias_prefix=alias;
        result->interface_type=veri_virtual_interface(call);
        result->array_value=fn.result_symbol&&Variable{fn.result_symbol}.range_depth();
        if(!result->array_value&&fn.result>=0&&object_signals.count(fn.result))result->object_type=object_signals.at(fn.result);
        result->text_value=fn.result>=0&&signals[fn.result].text_value;result->real_width=fn.result>=0?signals[fn.result].real_width:0;
        if(fn.compiling&&!shared_functions) {
            const auto id=std::to_string(fn.recursive_id);
            result->literal="return recursive_self_"+id+"(recursive_self_"+id+",recursion_depth_"+id+"+1";
            if(fn.this_signal>=0)result->literal+=",call_self";
            for(size_t i=0;i<args.size();++i)result->literal+=",call_arg"+std::to_string(i);
            result->literal+=");";result->signed_value=fn.signed_result;result->procedural_only=true;result->event_safe=false;
            return result;
        }
        result->function_forks|=fn.process.function_forks;result->io_state|=fn.process.io_state;result->procedural_only|=fn.process.io_state||fn.process.function_forks;result->random_state|=fn.process.random_state;result->procedural_only|=fn.process.random_state;result->selection_checks|=fn.process.selection_checks;result->signed_value=fn.signed_result;result->enum_id=enum_identity(call);
        for(int id:fn.process.reads)if(!subroutine_signals.count(id))result->function_reads.insert(id);
        for(int id:fn.process.function_reads)if(!subroutine_signals.count(id))result->function_reads.insert(id);
        result->touches.insert(fn.process.touches.begin(),fn.process.touches.end());result->touches.insert(fn.locals.begin(),fn.locals.end());
        result->partial_writes.insert(fn.process.partial_writes.begin(),fn.process.partial_writes.end());
        result->whole_writes.insert(fn.process.whole_writes.begin(),fn.process.whole_writes.end());
        result->nonstatic_writes.insert(fn.process.nonstatic_writes.begin(),fn.process.nonstatic_writes.end());
        result->sensitivity_reads=fn.process.sensitivity_reads;
        for(const auto& part:fn.process.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        ProcessIR copy;
        for(size_t i=0;i<args.size();++i)if(fn.directions[i]!=vpIN&&!reference_direction(fn.directions[i])) {
            result->procedural_only=true;
            if(array_formal(fn,i)){scope=args[i].defaulted?fn.scope->parent:caller_scope;array_copyout(copy,args[i].value,fn,i);scope=caller_scope;continue;}
            auto* symbol=veri_formal_symbol(fn.formals[i]);int id=fn.scope->ids.at(Variable{symbol}->name());
            auto value=signal_expr(id);value->enum_id=enum_identity(symbol);value->interface_type=veri_virtual_interface(symbol);value->signed_value=Variable{symbol}->is_signed()==IS_TRUE;
            value->reads.clear();value->touches.insert(id);
            scope=args[i].defaulted?fn.scope->parent:caller_scope;assign(copy,args[i].value,value);scope=caller_scope;
        }
        result->io_state|=copy.io_state;result->random_state|=copy.random_state;result->selection_checks|=copy.selection_checks;result->reads.insert(copy.reads.begin(),copy.reads.end());result->touches.insert(copy.touches.begin(),copy.touches.end());
        result->function_reads.insert(copy.function_reads.begin(),copy.function_reads.end());
        result->partial_writes.insert(copy.partial_writes.begin(),copy.partial_writes.end());
        result->whole_writes.insert(copy.whole_writes.begin(),copy.whole_writes.end());
        result->nonstatic_writes.insert(copy.nonstatic_writes.begin(),copy.nonstatic_writes.end());
        result->sensitivity_reads.insert(result->sensitivity_reads.end(),copy.sensitivity_reads.begin(),copy.sensitivity_reads.end());
        for(const auto& part:copy.writes){result->writes.insert(part.signal);result->write_ranges.emplace(part.signal,part.lo,part.width);}
        if(shared_functions) {
            result->literal+="auto ref_guard=dsim_function_frame_"+std::to_string(fn.recursive_id)+"(s";
            for(size_t i=0;i<fn.formals.size();++i)if(reference_direction(fn.directions[i]))result->literal+=",call_arg"+std::to_string(i);
            result->literal+=");";
        } else if(!fn.recursive&&(fn.has_references||fn.process.function_forks||(!fn.scope->automatic_storage&&std::any_of(fn.locals.begin(),fn.locals.end(),[&](int id){return automatic_signals.count(id)!=0;}))))result->literal+=reference_entry(fn,"call_arg",true);
        if(fn.this_signal>=0) {
            result->literal+="(void)s.object_index(call_self,"+std::to_string(object_signals.at(fn.this_signal))+");s.set("+sid(fn.this_signal)+",call_self);";
            result->reads.insert(objects_signal);result->writes.insert(fn.this_signal);result->write_ranges.emplace(fn.this_signal,0,64);
        }
        for(size_t i=0;i<fn.formals.size();++i)if(fn.directions[i]!=vpOUT&&!reference_direction(fn.directions[i])) {
            if(array_formal(fn,i)) {
                auto words=formal_words(fn,i);
                if(Variable{veri_formal_symbol(fn.formals[i])}.dynamic()) {
                    int id=words.front();result->writes.insert(id);result->write_ranges.emplace(id,0,signals[id].width);
                    result->literal+=replace_array_values(id,"call_arg"+std::to_string(i));continue;
                }
                for(size_t k=0;k<words.size();++k){int id=words[k];result->writes.insert(id);result->write_ranges.emplace(id,0,signals[id].width);result->literal+="s.set("+sid(id)+",call_arg"+std::to_string(i)+"["+std::to_string(k)+"]);";}
                continue;
            }
            auto* symbol=veri_formal_symbol(fn.formals[i]);int id=fn.scope->ids.at(Variable{symbol}->name());
            result->writes.insert(id);result->write_ranges.emplace(id,0,signals[id].width);result->literal+="s.set("+sid(id)+",call_arg"+std::to_string(i)+");";
        }
        if(shared_functions) {
            result->literal+="auto call_result=dsim_function_body_"+std::to_string(fn.recursive_id)+"("+shared_function_arguments()+");";
            for(const auto& inst:copy.instructions)result->literal+=inst.code;
            result->literal+="return call_result;";
            result->procedural_only|=fn.recursive;
            result->event_safe&=!fn.recursive&&fn.scope->automatic_storage&&fn.process.event_safe&&!fn.process.side_effect;
            return result;
        }
        result->literal+="int pc=0;";
        for(int i=0;i<fn.process.repeat_counters;++i)result->literal+="uint64_t repeat"+std::to_string(i)+"=0;";
        for(size_t k=0;k<fn.process.array_values.size();++k)result->literal+="std::vector<V> array_value"+std::to_string(k)+"("+std::to_string(fn.process.array_values[k])+");";
        result->literal+="for(;;){s.step();switch(pc){";
        for(size_t i=0;i<fn.process.instructions.size();++i) {
            const auto& inst=fn.process.instructions[i];result->literal+="case "+std::to_string(i)+":{";
            result->literal+=integral_loop(fn.process,i);
            if(inst.condition)result->literal+="pc=("+emit(inst.condition)+").truth()==1?"+std::to_string(inst.yes)+":"+std::to_string(inst.no)+";continue;";
            else if(inst.yes>=0)result->literal+="pc="+std::to_string(inst.yes)+";continue;";
            else result->literal+=inst.code+"pc="+std::to_string(i+1)+";continue;";
            result->literal+="}";
        }
        std::string returned=fn.result<0?std::string("V(0,0,1)"):"s.get("+sid(fn.result)+")";
        if(result->array_value) {
            if(Variable{fn.result_symbol}.dynamic())returned="s.dynamic_values("+sid(fn.result)+")";
            else {
                returned="std::vector<V>{";
                const auto& memory=memories.at(fn.scope->memories.at(Variable{fn.result_symbol}.name()));
                for(size_t ordinal=0;ordinal<memory.words.size();++ordinal) {
                    size_t offset=0;
                    for(const auto& dim:memory.dimensions){auto part=(ordinal/size_t(dim.stride))%size_t(dim.count);offset+=(dim.descending?size_t(dim.count)-1-part:part)*size_t(dim.stride);}
                    returned+="s.get("+sid(memory.words.at(offset))+"),";
                }
                returned+="}";
            }
        }
        result->literal+="default:{auto call_result="+returned+";";
        for(const auto& inst:copy.instructions)result->literal+=inst.code;
        result->literal+="return call_result;}}}";
        result->literal=cached_function_locals(fn,result->literal);
        if(fn.recursive) {
            const auto id=std::to_string(fn.recursive_id);
            std::string body="auto recursive_body_"+id+"=[&](auto&& recursive_self_"+id+",unsigned recursion_depth_"+id;
            if(fn.this_signal>=0)body+=",V call_self";
            for(size_t i=0;i<fn.formals.size();++i)body+=std::string(array_formal(fn,i)?
                (associative_kind(Variable{veri_formal_symbol(fn.formals[i])}.container_kind())&&!reference_direction(fn.directions[i])?",auto call_arg":",std::vector<V> call_arg"):
                ",V call_arg")+std::to_string(i);
            body+=")->V{if(recursion_depth_"+id+">=1024)throw std::runtime_error(\"recursive function depth exceeds 1024\");"+reference_entry(fn,"call_arg",true)+result->literal+"};return recursive_body_"+id+"(recursive_body_"+id+",0";
            if(fn.this_signal>=0)body+=",call_self";
            for(size_t i=0;i<fn.formals.size();++i)body+=",call_arg"+std::to_string(i);
            result->literal=body+");";result->procedural_only=true;
        }
        // Event callbacks may initialize/write their private automatic frame,
        // but must not change externally visible state or persistent locals.
        result->event_safe&=fn.scope->automatic_storage&&fn.process.event_safe&&!fn.process.side_effect;
        for(int id:result->writes)if(!event_function_storage.count(id))result->event_safe=false;
        return result;
    }
    std::string shared_function_arguments(bool declaration=false) const {
        // Call sites are lowered before all DPI declarations have been seen.
        // Resolve their environment only after the complete design is lowered.
        if(!declaration)return "DSIM_SHARED_FUNCTION_ARGUMENTS";
        return std::string("Sim& s")+(needs_dpi?",DpiRuntime& dpi":"")+
            (wave_enabled?",WaveCapture& wave":"");
    }
    void emit_shared_functions(std::ostream& out) {
        if(!shared_functions)return;
        out<<"#define DSIM_SHARED_FUNCTION_ARGUMENTS s"<<(needs_dpi?",dpi":"")<<(wave_enabled?",wave":"")<<"\n";
        std::map<unsigned,const Callable*> functions;
        for(const auto& entry:callables)if(entry.second->process.function)functions.emplace(entry.second->recursive_id,entry.second.get());
        for(const auto& entry:functions) {
            const auto& fn=*entry.second;const auto id=std::to_string(entry.first);
            const bool array=fn.result_symbol&&Variable{fn.result_symbol}.range_depth();
            out<<"static "<<(array?"std::vector<V>":"V")<<" dsim_function_body_"<<id<<"("<<shared_function_arguments(true)<<");\n";
            out<<"static Sim::ReferenceActivation dsim_function_frame_"<<id<<"(Sim& s";
            for(size_t i=0;i<fn.formals.size();++i)if(reference_direction(fn.directions[i]))out<<(array_formal(fn,i)?",const std::vector<V>& call_arg":",V call_arg")<<i;
            out<<");\n";
        }
        for(const auto& entry:functions) {
            const auto& fn=*entry.second;const auto id=std::to_string(entry.first);
            out<<"static Sim::ReferenceActivation dsim_function_frame_"<<id<<"(Sim& s";
            for(size_t i=0;i<fn.formals.size();++i)if(reference_direction(fn.directions[i]))out<<(array_formal(fn,i)?",const std::vector<V>& call_arg":",V call_arg")<<i;
            auto frame=reference_entry(fn,"call_arg",true);
            frame.replace(0,std::string("auto ref_guard=").size(),"return ");
            out<<"){"<<frame<<"}\n";
            const bool array=fn.result_symbol&&Variable{fn.result_symbol}.range_depth();
            out<<"static "<<(array?"std::vector<V>":"V")<<" dsim_function_body_"<<id<<"("<<shared_function_arguments(true)<<"){\n";
            if(fn.recursive)out<<"auto depth=s.function_depth("<<entry.first<<");\n";
            out<<"int pc=0;";
            for(int i=0;i<fn.process.repeat_counters;++i)out<<"uint64_t repeat"<<i<<"=0;";
            for(size_t i=0;i<fn.process.array_values.size();++i)out<<"std::vector<V> array_value"<<i<<"("<<fn.process.array_values[i]<<");";
            out<<"for(;;){s.step();switch(pc){\n";
            for(size_t i=0;i<fn.process.instructions.size();++i) {
                const auto& inst=fn.process.instructions[i];out<<"case "<<i<<":{"<<integral_loop(fn.process,i);
                if(inst.condition)out<<"pc=("<<emit(inst.condition)<<").truth()==1?"<<inst.yes<<":"<<inst.no<<";continue;";
                else if(inst.yes>=0)out<<"pc="<<inst.yes<<";continue;";
                else out<<inst.code<<"pc="<<i+1<<";continue;";
                out<<"}\n";
            }
            out<<"default:return ";
            if(array) {
                if(Variable{fn.result_symbol}.dynamic())out<<"s.dynamic_values("<<fn.result<<")";
                else {
                    out<<"std::vector<V>{";
                    const auto& memory=memories.at(fn.scope->memories.at(Variable{fn.result_symbol}.name()));
                    for(size_t ordinal=0;ordinal<memory.words.size();++ordinal) {
                        size_t offset=0;
                        for(const auto& dim:memory.dimensions){auto part=(ordinal/size_t(dim.stride))%size_t(dim.count);offset+=(dim.descending?size_t(dim.count)-1-part:part)*size_t(dim.stride);}
                        out<<"s.get("<<memory.words.at(offset)<<"),";
                    }
                    out<<"}";
                }
            } else out<<(fn.result<0?"V(0,0,1)":"s.get("+std::to_string(fn.result)+")");
            out<<";}}}\n";
        }
    }
    E scalar_function_value(VeriNode* call) {
        auto value=function_call(call);
        if(value->array_value)fail(call,"unpacked array function value requires an array context");
        return value;
    }
    void task_call(ProcessIR& p,VeriNode* n,int pidx,bool discard=false,bool dispatch=true,E receiver={}) {
        if(n->detail_type()==veEXP_UNA&&static_cast<VeriUnaryExp*>(n)->op()==vtSYS_CAST) {
            auto value=dynamic_cast_expression(static_cast<VeriUnaryExp*>(n),!discard);read(p,value);add(p,"(void)("+emit(value)+");");return;
        }
        if(n->detail_type()==veEXP_MEMBER&&!veri_call_hive(n)) {
            auto* member=static_cast<VeriMemberExp*>(n);
            if(member->process_builtin()) {
                if(member->member()=="await") {
                    if(p.function||lowering_final||discard)fail(n,"process await requires a task statement outside functions/final");
                    auto* type=member->class_owner();register_class(type);
                    needs_process_handles=needs_random=needs_process_lifetime=needs_process_control=needs_explicit_automatic=true;
                    auto receiver=expr(member->object());read(p,receiver);++p.timing_controls;p.side_effect=true;p.selection_only_effects=false;
                    const auto next=std::to_string(p.instructions.size()+1);
                    add(p,"{auto awaited="+emit(receiver)+";pc="+next+";if(s.process_await(awaited,"+std::to_string(classes.at(type).id)+","+runtime_pid(pidx)+"))return;continue;}");return;
                }
                auto value=process_expression(member,!discard);read(p,value);add(p,"(void)("+emit(value)+");");return;
            }
            if(member->coverage_builtin()){auto value=coverage_expression(member,!discard);read(p,value);add(p,"(void)("+emit(value)+");");return;}
            if(member->ipc_builtin()){ipc_task(p,member,pidx,discard);return;}
            if(member->randomize_builtin()||member->random_control_builtin()) {
                auto value=member->randomize_builtin()?randomize_expression(member):random_control_expression(member,true);
                read(p,value);add(p,"(void)("+emit(value)+");");return;
            }
            if(veri_string_value(member->object())&&!veri_array_shape(member->object()).unpacked) {
                const auto& method=member->member();
                const bool putc=method=="putc";
                const bool convert=method=="itoa"||method=="hextoa"||method=="octtoa"||method=="bintoa";
                if(!putc&&!convert) {auto value=expr(n);read(p,value);add(p,"(void)("+emit(value)+");");return;}
                if(discard)fail(n,"void string method requires a statement without a value");
                needs_text=true;std::vector<E> args;
                for(auto* actual:veri_system_arguments(member->arguments())) {
                    auto value=expr(actual);if(value->packed_value)value=value->packed_value;
                    if(value->text_value)fail(n,"string method argument requires an integral value");
                    auto converted=node("fixed_cast",putc&&args.size()==1?8:32,{value});converted->signed_value=true;args.push_back(converted);
                }
                // Evaluate actuals left to right, then read the receiver. A
                // function actual may itself modify this same string through ref.
                auto target=lvalue(member->object());
                if(putc&&target.parts.size()==1&&target.parts.front().receiver_effect)args.push_back(signal_expr(target.parts.front().signal));
                else if(putc)args.push_back(expr(member->object()));
                auto value=node("text_method",1,args);value->text_value=true;
                value->literal=putc?"return text_putc(text_arg2,text_arg0,text_arg1);":"return text_"+method+"(text_arg0);";
                write(p,target,value,false,false);return;
            }
            if(veri_array_ordering(n)) {
                if(discard)fail(n,"void array ordering method cannot use void discard");
                array_ordering(p,member);return;
            }
            if(auto value=container_method(member,true)) {
                if(discard&&member->member()!="pop_back"&&member->member()!="pop_front"&&member->member()!="exists"&&member->member()!="size"&&member->member()!="num"&&member->member()!="first"&&member->member()!="last"&&member->member()!="next"&&member->member()!="prev")fail(n,"void container method cannot use void discard");
                read(p,value);add(p,"(void)("+emit(value)+");");return;
            }
            int id=dynamic_object(member->object());
            if(id<0||member->member()!="delete"||discard)fail(n,"only dynamic array delete() can be used as a method statement");
            if(auto effect=static_receiver_effect(member->object())){read(p,effect);add(p,"(void)("+emit(effect)+");");}
            writable(id,n);p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
            add(p,"s.dynamic_replace("+sid(id)+",{},"+std::to_string(signals[id].width)+","+(signals[id].two_state?"true":"false")+");");return;
        }
        if(n->detail_type()==veEXP_UNA&&veri_is_testbench_function(static_cast<VeriUnaryExp*>(n)->op())) {
            auto value=expr(n);read(p,value);add(p,"(void)("+emit(value)+");");return;
        }
        if(n->detail_type()==veEXP_UNA&&veri_is_random(static_cast<VeriUnaryExp*>(n)->op())) {
            if(!discard)fail(n,"random system function result must be consumed or discarded with void'(call)");
            auto value=expr(n);read(p,value);add(p,"(void)("+emit(value)+");");return;
        }
        if(n->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(n)->super_reference()&&static_cast<VeriMemberExp*>(n)->member()=="new") {
            auto* enclosing=n->father();while(enclosing&&enclosing->detail_type()!=vsDECL_FUNC_DECL)enclosing=enclosing->father();
            if(!enclosing||static_cast<VeriFuncDecl*>(enclosing)->func_name()!="new"||first_constructor_statement(static_cast<VeriFuncDecl*>(enclosing)->stmt())!=n->father())fail(n,"super.new must be the first statement of a constructor");
        }
        if(!veri_subroutine_call(n))fail(n,"task calls require parentheses");
        auto* call=n;
        if(veri_call_hive(call)&&veri_call_hive(call)->detail_type()==vsDECL_FUNC_DECL) {
            auto value=function_call(call,false);
            if(diagnostics&&!discard&&!static_cast<VeriFuncDecl*>(veri_call_hive(call))->is_void())std::cerr<<"dsim: line "<<call->line()<<": warning: function return value discarded; use void\'(call) explicitly\n";
            read(p,value);add(p,"(void)("+emit(value)+");");return;
        }
        if(discard)fail(n,"void discard requires a function call");
        if(lowering_final)fail(n,"final block requires functions without task calls");
        if(dispatch&&call->detail_type()==veEXP_MEMBER&&veri_virtual_interface(static_cast<VeriMemberExp*>(call)->object())) {
            if(p.function)fail(call,"functions require zero-time function calls, not tasks");
            interface_task_call(p,static_cast<VeriMemberExp*>(call),pidx);return;
        }
        if(p.function)fail(n,"functions require zero-time blocking statements without task calls");
        if(dispatch&&!class_scope_call(call)) {
            auto targets=virtual_targets(call);
            const bool pure=veri_call_hive(call)&&static_cast<VeriDecl*>(veri_call_hive(call))->pure_virtual();
            const bool super=call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->super_reference();
            if(pure&&super)fail(call,"pure virtual method has no implementation");
            if(virtual_method(call)||pure) {
                auto self=receiver?receiver:method_receiver(call);read(p,self);
                const int capture=int(signals.size());signals.push_back({scope->path+".$virtual_receiver"+std::to_string(capture),64,0,false,true});object_signals[capture]=self->object_type;
                add(p,"s.set("+sid(capture)+","+emit(self)+");");p.touches.insert(capture);p.writes.push_back({capture,0,64,0});p.reads.insert(objects_signal);
                std::vector<int> exits;
                for(const auto& target:targets) {
                    auto condition=node("literal",1);condition->literal="V(s.object_type(s.get("+sid(capture)+"))=="+std::to_string(target.first)+",0,1)";condition->reads.insert(capture);condition->reads.insert(objects_signal);
                    int branch=add(p,"");p.instructions[branch].condition=condition;p.instructions[branch].yes=branch+1;
                    auto* binding=target.second==method_owner(call)?call:method_binding(call,target.second);
                    task_call(p,binding,pidx,false,false,signal_expr(capture));exits.push_back(add(p,""));p.instructions[branch].no=int(p.instructions.size());
                }
                add(p,"throw std::runtime_error(\"invalid virtual task receiver\");");
                for(int exit:exits)p.instructions[exit].yes=int(p.instructions.size());
                return;
            }
        }
        if(veri_call_hive(call)&&static_cast<VeriDecl*>(veri_call_hive(call))->pure_virtual())fail(call,"pure virtual method has no implementation");
        auto& fn=callable(call,false,pidx);auto args=veri_bind_arguments(call,fn.formals);
        auto* caller_scope=scope;
        std::string code="{";
        if(fn.scope->static_class_method&&call->detail_type()==veEXP_MEMBER&&!static_cast<VeriMemberExp*>(call)->scope_reference()) {
            auto effect=expr(static_cast<VeriMemberExp*>(call)->object());read(p,effect);code+="(void)("+emit(effect)+");";
        }
        if(fn.this_signal>=0){auto self=receiver?receiver:method_receiver(call);read(p,self);p.reads.insert(objects_signal);code+="auto task_self="+emit(self)+";";}
        const auto alias=std::any_of(args.begin(),args.end(),[](const auto& a){return a.defaulted;})?"default_task"+std::to_string(argument_sequence++)+"_":std::string{};
        auto default_self=node("saved",64);default_self->literal=alias+"self";default_self->object_type=fn.this_signal>=0?object_signals.at(fn.this_signal):-1;
        if(fn.this_signal>=0&&!alias.empty())code+="const auto& "+alias+"self=task_self;";
        for(size_t i=0;i<args.size();++i)if(fn.directions[i]!=vpOUT) {
            auto value=call_argument(fn,args,i,caller_scope,alias,fn.this_signal>=0?default_self:E{});read(p,value);
            code+="auto task_arg"+std::to_string(i)+"="+emit(value)+";";
            if(!alias.empty())code+="const auto& "+alias+std::to_string(i)+"=task_arg"+std::to_string(i)+";";
        }
        const bool activation=fn.has_references||activation_storage(fn.scope);
        if(activation)code+=fn.has_references?reference_entry(fn,"task_arg"):activation_entry(fn.scope);
        if(fn.this_signal>=0){code+="(void)s.object_index(task_self,"+std::to_string(object_signals.at(fn.this_signal))+");s.set("+sid(fn.this_signal)+",task_self);";p.touches.insert(fn.this_signal);p.writes.push_back({fn.this_signal,0,64,0});}
        for(size_t i=0;i<args.size();++i)if(fn.directions[i]!=vpOUT&&!reference_direction(fn.directions[i])) {
            if(array_formal(fn,i)) {
                auto words=formal_words(fn,i);
                if(Variable{veri_formal_symbol(fn.formals[i])}.dynamic()) {
                    int id=words.front();p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
                    code+=replace_array_values(id,"task_arg"+std::to_string(i));continue;
                }
                for(size_t k=0;k<words.size();++k){int id=words[k];p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});code+="s.set("+sid(id)+",task_arg"+std::to_string(i)+"["+std::to_string(k)+"]);";}
                continue;
            }
            auto* symbol=veri_formal_symbol(fn.formals[i]);int id=fn.scope->ids.at(Variable{symbol}->name());
            p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
            code+="s.set("+sid(id)+",task_arg"+std::to_string(i)+".size("+std::to_string(signals[id].width)+"));";
        }
        add(p,code+"}");scope=fn.scope;
        if(activation)++p.activation_depth;
        if(fn.task_process>=0) {
            ++p.timing_controls;p.side_effect=true;p.selection_only_effects=false;
            const auto next=std::to_string(p.instructions.size()+1);
            add(p,"pc="+next+";s.enter_task("+std::to_string(fn.task_group)+");return;");
        } else {
        auto caller_reads=p.reads,caller_function_reads=p.function_reads;auto caller_sensitivity_reads=p.sensitivity_reads;
        const auto identity=std::make_pair(fn.scope->parent,static_cast<VeriTaskDecl*>(veri_call_hive(call))->task_name());
        active_subroutines.insert(identity);
        initialize_activation(p,fn.scope,callable_inputs(fn));
        auto outer_loops=std::move(p.loops);p.loops.clear();auto outer_blocks=std::move(named_blocks);named_blocks.clear();
        auto outer_identity=std::move(disable_callable_identity);const int outer_ordinal=disable_block_ordinal;
        disable_callable_identity=identity.second;disable_block_ordinal=0;
        p.returns.push_back({-1,{}});statement(p,fn.body,pidx);finish_returns(p);
        disable_callable_identity=std::move(outer_identity);disable_block_ordinal=outer_ordinal;
        p.loops=std::move(outer_loops);named_blocks=std::move(outer_blocks);
        active_subroutines.erase(identity);
        scope=caller_scope;p.reads=std::move(caller_reads);p.function_reads=std::move(caller_function_reads);p.sensitivity_reads=std::move(caller_sensitivity_reads);
        }
        scope=caller_scope;
        for(size_t i=0;i<args.size();++i)if(fn.directions[i]!=vpIN&&!reference_direction(fn.directions[i])) {
            if(array_formal(fn,i)){scope=args[i].defaulted?fn.scope->parent:caller_scope;array_copyout(p,args[i].value,fn,i,fn.task_process>=0);scope=caller_scope;continue;}
            auto* symbol=veri_formal_symbol(fn.formals[i]);int id=fn.scope->ids.at(Variable{symbol}->name());
            auto value=signal_expr(id);value->enum_id=enum_identity(symbol);value->interface_type=veri_virtual_interface(symbol);value->signed_value=Variable{symbol}->is_signed()==IS_TRUE;value->reads.clear();value->touches.insert(id);
            const auto first=p.instructions.size();
            if(fn.task_process>=0){value=std::make_shared<Expr>(*value);value->op="saved";value->literal="task_output";}
            scope=args[i].defaulted?fn.scope->parent:caller_scope;assign(p,args[i].value,value);scope=caller_scope;
            if(fn.task_process>=0)for(size_t j=first;j<p.instructions.size();++j)
                p.instructions[j].code="{auto task_output=s.get("+sid(id)+");auto task_caller=s.task_output_context();"+p.instructions[j].code+"}";
        }
        if(activation){--p.activation_depth;add(p,"");}
    }

    std::string selection_checks_code(VeriNode* n,int qualifier,const std::string& kind,bool fallback) {
        const auto name=qualifier==1?"unique":qualifier==2?"unique0":"priority";
        const auto message="DSIM selection: "+std::string(name)+" "+kind+" ";
        const auto location=" at "+scope->path+":"+std::to_string(n->line());
        std::string code;
        if(qualifier!=3)code+="if(matches>1)s.selection_report("+quote(escape_format_text(message+"overlap"+location))+");";
        if(qualifier!=2&&!fallback)code+="if(!matches)s.selection_report("+quote(escape_format_text(message+"no-match"+location))+");";
        return code;
    }
    int event_site(ProcessIR& p,VeriEventStmt* ev,int pidx,bool nba=false) {
        if(ev->event_list().size()==1)if(auto* syntax=veri_clocking_reference(ev->event_list().front())) {
            if(nba)fail(ev,"intra-assignment clocking event controls are not supported yet");
            auto found=clocking_ids.find(syntax);if(found==clocking_ids.end())fail(ev,"clocking event is outside the elaborated design");
            clocking_wait(p,pidx,found->second,"1");return -1;
        }
        if(ev->is_all()==IS_TRUE)fail(ev,"implicit sensitivity is not supported in intra-assignment event controls");
        const int next=int(p.instructions.size())+1;
        std::string list="{",expressions="{";bool complex=false;
        bool dynamic_named=false;
        std::vector<std::pair<int,int>> static_refs;
        for(auto* item:ev->event_list()) {
            VeriNode* operand=item;VeriNode* condition=nullptr;int edge=0;
            if(item->detail_type()==veEXP_EVENT) {
                auto* e=static_cast<VeriEventExp*>(item); operand=e->exp_child();
                edge=e->etype()==vtUPOSE?1:e->etype()==vtUNEGE?2:0;
                condition=e->condition();
            }
            int occurrence=-1;
            VeriNode* named=operand;bool query=false;
            if(operand->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(operand)->event_query()) {
                named=static_cast<VeriMemberExp*>(operand)->object();query=true;
            }
            if(auto event=instance_event(named)) {
                if(edge&&!query)fail(item,"named events do not permit edge qualifiers");
                if(nba)fail(item,"pending NBA controls on instance events are not supported yet");
                read(p,event);E guard;
                if(condition) {
                    guard=expr(condition);if(guard->packed_value)guard=guard->packed_value;
                    if(guard->text_value||!guard->event_safe||guard->procedural_only||!guard->writes.empty())fail(condition,"instance event iff condition requires an effect-free integral expression");
                    read(p,guard);
                }
                needs_expression_events=complex=dynamic_named=true;
                expressions+="{{},{},"+std::to_string(query?4+edge:3)+",true,"+(guard?"[&](Sim& s){return "+emit(guard)+";}":"{}")+",true,[&](Sim& s){return s.event_wait_id("+emit(event)+");}},";
                continue;
            }
            if(veri_event_symbol(operand)) {
                    if(edge)fail(item,"named events do not permit edge qualifiers");
                    int id=event_signal(operand);p.touches.insert(id);
                    if(!condition){list+="{"+sid(id)+",0},";continue;}
                    occurrence=id;
            }
            auto e=occurrence>=0?signal_expr(occurrence):expr(operand);
            if(nba&&e->event_snapshot)fail(operand,"array equality in pending NBA event controls is not supported yet");
            if(edge&&e->real_width)fail(operand,"edge event requires an integral operand");
            if(e->virtual_dispatch)fail(operand,"virtual function is not allowed in event/wait controls");
            if(edge&&e->text_value)fail(operand,"string event operands do not permit edge qualifiers");
            p.touches.insert(e->reads.begin(),e->reads.end());
            if(nba)for(int id:e->reads)if(automatic_signals.count(id)&&!event_function_storage.count(id))
                fail(operand,"automatic variables in pending NBA event controls are not supported yet");
            if(e->op=="event_triggered"&&e->args.empty()&&!condition) {
                list+="{"+sid(e->signal)+","+std::to_string(edge==2?4:3)+"},";continue;
            }
            if(e->op=="signal"&&!condition) {static_refs.emplace_back(e->signal,edge);list+="{"+sid(e->signal)+","+std::to_string(edge)+"},";continue;}
            bool function_event=false;
            auto safe=[&](const E& root) {
                std::vector<E> pending{root};
                while(!pending.empty()) {
                    auto value=pending.back();pending.pop_back();
                    function_event|=value->op=="call";
                    if(!value->event_safe||value->op=="mutation"||value->procedural_only||value->selection_checks)return false;
                    for(int id:value->writes)if(!event_function_storage.count(id))return false;
                    pending.insert(pending.end(),value->args.begin(),value->args.end());
                }
                return true;
            };
            if(!safe(e))fail(item,"event expressions with user function calls or side effects require an effect-free automatic function activation");
            read(p,e);
            E guard;
            if(condition) {
                guard=expr(condition);
                if(guard->packed_value)guard=guard->packed_value;if(guard->text_value)fail(condition,"string cannot be used as an iff condition");
                if(nba)for(int id:guard->reads)if(automatic_signals.count(id)&&!event_function_storage.count(id))
                    fail(condition,"automatic variables in pending NBA event controls are not supported yet");
                if(!safe(guard))fail(condition,"iff conditions with user function calls or side effects require an effect-free automatic function activation");
                // Guard reads constrain partitioning, but do not add
                // event watches: a guard-only change cannot wake us.
                read(p,guard);
            }
            needs_expression_events=complex=true;
            // Generated main owns the immutable ID map through engine.run().
            // Match process closures: share it instead of copying every
            // design signal ID into every expression callback.
            expressions+="{[&](Sim& s){return "+emit(e)+";},{";
            for(int id:e->reads)expressions+=sid(id)+",";
            // VCS takes a fresh baseline on entry for iff controls
            // and operands containing calls (unlike plain @expr).
            const bool automatic_operand=std::any_of(e->reads.begin(),e->reads.end(),[&](int id){return automatic_signals.count(id);});
            const bool heap_operand=(objects_signal>=0&&e->reads.count(objects_signal))||e->interface_dereference;
            const bool sample=occurrence<0&&(heap_operand||condition||function_event||scope->automatic_storage||automatic_operand||operand->detail_type()==veEXP_ARRAY||operand->detail_type()==veEXP_MEMBER);
            expressions+="},"+std::to_string(occurrence>=0?3:edge)+","+(sample?"true":"false")+
                (guard?",[&](Sim& s){return "+emit(guard)+";}":heap_operand||e->event_snapshot?",{}":"")+
                (heap_operand?",true":e->event_snapshot?",false":"")+(e->event_snapshot?",{},true":"")+"},";
        }
        if(nba){needs_expression_events=true;int id=int(event_nba_sites.size());event_nba_sites.push_back({pidx,list+"}",complex?expressions+"}":std::string(),false,{},false});return id;}
        if(next==1&&p.always_process&&!dynamic_named)p.startup_wait=int(wait_sites.size());
        auto code=wait_code(pidx,list+"}");
        wait_sites.back().refs=std::move(static_refs);wait_sites.back().static_refs=!complex&&!needs_named_events;
        if(complex)wait_sites.back().expressions=expressions+"}";
        add(p,"pc="+std::to_string(next)+"; "+code+" return;");return int(wait_sites.size())-1;
    }
    void event_wait(ProcessIR& p,VeriEventStmt* ev,int pidx) {event_site(p,ev,pidx);}
    void statement(ProcessIR& p,VeriNode* n,int pidx) {
        if(!n||n==constructor_skip) return;
        if(lowering_final&&(n->detail_type()==vsSTMT_NONBLOCKING||n->detail_type()==vsSTMT_PROC_TIME_CONTROL||
            n->detail_type()==vsSTMT_WAIT||n->detail_type()==vsSTMT_WAIT_FORK||n->detail_type()==vsSTMT_DISABLE_FORK||
            (n->detail_type()==vsSTMT_BLOCKING&&static_cast<VeriBlockStmt*>(n)->event())||
            n->detail_type()==vsSTMT_EVENT_TRIGGER||
            (n->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(n)->parallel_kind())))
            fail(n,"final block requires zero-time blocking statements without scheduling controls");
        bool function_system_task=false;
        if(n->detail_type()==vsSTMT_SYS_CALL) {
            const auto& task=static_cast<VeriSysCallerStmt*>(n)->caller();
            function_system_task=task=="$sformat"||task=="$swrite"||task=="$swriteh"||task=="$swriteb"||task=="$swriteo"||task=="$display"||task=="$write"||task=="$fdisplay"||task=="$fwrite"||task=="$finish"||task=="$stop";
        }
        if(p.function&&(n->detail_type()==vsSTMT_NONBLOCKING||n->detail_type()==vsSTMT_PROC_TIME_CONTROL||n->detail_type()==vsSTMT_WAIT||(n->detail_type()==vsSTMT_SYS_CALL&&!function_system_task)))
            fail(n,"functions require zero-time blocking statements without task calls");
        if(p.function&&n->detail_type()==vsSTMT_BLOCKING&&static_cast<VeriBlockStmt*>(n)->event())fail(n,"timing controls are not allowed in functions");
        switch(n->detail_type()) {
        case vsSTMT_CALL:task_call(p,static_cast<VeriCallerStmt*>(n)->caller(),pidx,static_cast<VeriCallerStmt*>(n)->discard());return;
        case vsSTMT_DUMMY:return;
        case vsSTMT_FORCE:case vsSTMT_RELEASE: {
            auto* action=static_cast<VeriActionStmt*>(n);
            if(p.function)fail(n,"force/release is not allowed in a function");
            auto target=lvalue(action->target());
            if(target.parts.size()!=1)fail(n,"force/release currently requires one whole static signal");
            auto part=target.parts.front();const int signal=part.signal;
            if(part.index||part.word_index||(part.memory>=0&&memories[size_t(part.memory)].dynamic)||part.lo||part.width!=signals[signal].width||automatic_signals.count(signal)||reference_signals.count(signal))
                fail(n,"force/release currently requires one whole static signal");
            writable(signal,n);p.touches.insert(signal);needs_force=true;
            if(n->detail_type()==vsSTMT_RELEASE){add(p,"s.release_value("+sid(signal)+");");return;}
            auto value=context_expr(action->value(),action->target());read(p,value);
            property_expression(action->value(),value);
            const int site=force_site_count++;
            add(p,"s.force_value("+sid(signal)+","+std::to_string(site)+","+emit(value,part.width)+");");
            if(!value->reads.empty()) {
                const int handler=int(processes.size());processes.emplace_back();ProcessIR refresh;
                refresh.source_line=n->line();refresh.touches.insert(signal);read(refresh,value);
                add(refresh,"if(s.force_active("+sid(signal)+","+std::to_string(site)+"))s.force_value("+sid(signal)+","+std::to_string(site)+","+emit(value,part.width)+");");
                add(refresh,"pc=0; "+wait_code(handler,value->reads)+" return;");
                processes[size_t(handler)]=std::move(refresh);
            }
            return;
        }
        case vsSTMT_WAIT_FORK:case vsSTMT_DISABLE_FORK: {
            if(p.function)fail(n,"fork control is not allowed in functions");
            if(p.always_kind!=akALWAYS)fail(n,"fork control is not allowed in always_comb/always_latch/always_ff");
            needs_process_control=true;
            if(n->detail_type()==vsSTMT_DISABLE_FORK)add(p,"s.disable_fork("+runtime_pid(pidx)+");");
            else {++p.timing_controls;const int next=int(p.instructions.size())+1;
                add(p,"pc="+std::to_string(next)+";if(s.wait_fork("+runtime_pid(pidx)+"))return;continue;");}
            return;
        }
        case vsSTMT_DISABLE: {
            const auto& label=static_cast<VeriDisableStmt*>(n)->label();
            auto found=std::find_if(named_blocks.rbegin(),named_blocks.rend(),[&](const auto& block){return block->label==label;});
            if(found==named_blocks.rend())fail(n,"disable requires a lexically enclosing named block (external/task/hierarchical targets are not supported yet)");
            if(p.function)(*found)->exits.push_back(add(p,""));
            else {
                needs_process_control=true;
                const auto target="s.fork_target_id("+(parallel_count?"did["+std::to_string((*found)->target)+"]":std::to_string((*found)->target))+")";
                add(p,"{int transfer=s.disable_block("+target+","+runtime_pid(pidx)+");if(transfer<0)return;pc=transfer;continue;}");
            }
            return;
        }
        case vsSTMT_BREAK:case vsSTMT_CONTINUE: {
            if(p.loops.empty())fail(n,"break/continue requires an enclosing procedural loop");
            int jump=add(p,"");
            (n->detail_type()==vsSTMT_BREAK?p.loops.back().breaks:p.loops.back().continues).push_back(jump);
            return;
        }
        case vsSTMT_RETURN: {
            if(p.returns.empty())fail(n,"return requires an enclosing function or task");
            auto* action=static_cast<VeriActionStmt*>(n);int result=p.returns.back().result;
            if(action->value()) {
                if(result<0)fail(n,p.function?"void functions cannot return a value":"tasks cannot return a value");
                auto* result_symbol=p.returns.back().symbol;
                if(result_symbol&&Variable{result_symbol}.range_depth()) {
                    array_assignment(p,result_symbol,action->value(),false,nullptr,pidx);
                    int jump=add(p,"");p.returns.back().exits.push_back(jump);return;
                }
                LValueIR target;target.width=signals[result].width;target.parts.push_back({result,0,target.width,0});
                auto value=signals[result].text_value?text_expression(action->value()):signals[result].real_width?expr(action->value()):packed_context(action->value(),target.width);
                if(object_signals.count(result)) {if(!class_compatible(value->object_type,object_signals.at(result)))fail(n,"function return requires a compatible class handle or null");}
                else if(value->object_type!=-1)fail(n,"class handle cannot be returned as an integral or string value");
                if(p.returns.back().enum_id&&p.returns.back().enum_id!=value->enum_id)fail(n,"enum return requires the same enum type or an explicit enum cast");
                write(p,target,value,false,false);
            }
            int jump=add(p,"");p.returns.back().exits.push_back(jump);return;
        }
        case vsSTMT_COMPOUND: {
            auto* action=static_cast<VeriActionStmt*>(n);
            static const std::map<int,std::string> ops={{vtBADD,"+"},{vtBSUB,"-"},{vtBMUL,"*"},{vtBDIV,"/"},{vtBMOD,"%"},
                {vtBSAND,"&"},{vtBSOR,"|"},{vtBSXOR,"^"},{vtBLLS,"<<"},{vtBLRS,">>"},{vtBALS,"<<"},{vtBARS,">>>"}};
            auto found=ops.find(action->op());if(found==ops.end())fail(n,"unsupported compound assignment operator");
            compound(p,n,action->target(),expr(action->value()),found->second);return;
        }
        case vsSTMT_UPDATE: {
            auto* update=static_cast<VeriUpdateStmt*>(n);
            auto one=node("literal",32);one->literal="V(1,0,32)";one->signed_value=true;
            compound(p,n,update->target(),one,update->delta()>0?"+":"-");return;
        }
        case vsSTMT_SEQ_BLOCK: {
            auto* b=static_cast<VeriSeqBlock*>(n);
            if(b->parallel_kind()) {
                if(p.function) {
                    if(b->parallel_kind()!=3)fail(n,"fork is not allowed in functions unless join_none is used");
                    p.function_forks=true;p.side_effect=true;p.selection_only_effects=false;p.event_safe=false;
                }
                if(p.always_kind!=akALWAYS)fail(n,"fork is not allowed in always_comb/always_latch/always_ff");
                if(b->parallel_kind()!=1) {
                    needs_process_control=true;
                }
                ++p.timing_controls;
            }
            auto* owner=scope;
            if(!b->label().empty()||b->decl_list()) {
                auto key=std::make_pair(owner,n);auto found=block_scopes.find(key);
                if(found!=block_scopes.end()) {
                    scope=found->second;
                    if(!compiling_functions.empty()&&compiling_functions.back()->rebuilding_static) {
                        scope->activation_initializers.clear();decl_init(b->decl_list(),true);
                    }
                }
                else {
                    auto label=b->label();
                    if(label.empty())label="$unm_blk_"+std::to_string(++owner->unnamed_blocks);
                    scope=generated_scope(owner,label);scope->procedural=true;
                    block_scopes[key]=scope;declarations(b->decl_list());decl_init(b->decl_list());
                }
            }
            const bool activation=scope!=owner&&activation_storage(scope)&&!p.function;
            if(activation){add(p,activation_entry(scope));++p.activation_depth;}
            if(scope!=owner)initialize_activation(p,scope);
            std::shared_ptr<NamedBlock> named;
            if(!b->label().empty()) {
                int target=-1;
                if(!p.function) {target=int(disable_targets.size());auto* lexical=owner;while(lexical->procedural&&lexical->parent)lexical=lexical->parent;
                    auto key=std::make_tuple(lexical,disable_callable_identity,disable_callable_identity.empty()?target:disable_block_ordinal++);
                    auto identity=disable_identities.emplace(key,int(disable_identities.size())).first->second;
                    disable_targets.push_back({pidx,int(p.instructions.size()),-1,identity,fork_groups.size(),fork_groups.size()});}
                named=std::make_shared<NamedBlock>(NamedBlock{b->label(),target,{}});named_blocks.push_back(named);
            }
            if(!b->parallel_kind())statement(p,b->stmt_list(),pidx);
            else {
                const int group=int(fork_groups.size());fork_groups.push_back({pidx,{},b->parallel_kind()});
                if(b->stmt_list())for(auto* branch:static_cast<VeriStmtList*>(b->stmt_list())->stmt_list()) {
                    const int child=int(processes.size()),ordinal=int(fork_groups[size_t(group)].children.size());
                    fork_groups[size_t(group)].children.push_back(child);processes.emplace_back();
                    ProcessIR child_process;child_process.fork_child=true;child_process.source_line=branch->line();
                    statement(child_process,branch,child);
                    const auto id="s.fork_group_id("+(parallel_count?"fid["+std::to_string(group)+"]":std::to_string(group))+")";
                    add(child_process,"pc=0;s.finish_fork("+id+","+std::to_string(ordinal)+");return;");
                    processes[size_t(child)]=std::move(child_process);
                }
                if(!fork_groups[size_t(group)].children.empty()) {
                    const int next=int(p.instructions.size())+1;
                    const auto id="s.fork_group_id("+(parallel_count?"fid["+std::to_string(group)+"]":std::to_string(group))+")";
                    if(p.function)add(p,"s.start_function_fork("+std::to_string(group)+");");
                    else add(p,"pc="+std::to_string(next)+";if(s.start_fork("+id+"))return;continue;");
                }
            }
            if(named) {
                for(int jump:named->exits)p.instructions[size_t(jump)].yes=int(p.instructions.size());
                if(named->target>=0) {
                    auto& target=disable_targets[size_t(named->target)];target.end=int(p.instructions.size());target.last_group=fork_groups.size();
                }
                named_blocks.pop_back();
            }
            if(activation){--p.activation_depth;add(p,"");}
            scope=owner;return;
        }
        case vsSTMT_STMT_LIST:for(auto* s:static_cast<VeriStmtList*>(n)->stmt_list()) statement(p,s,pidx);return;
        case vsSTMT_BLOCKING: {
            auto* a=static_cast<VeriBlockStmt*>(n);
            if(clocking_assignment(p,a->lval(),a->rval(),a->event(),false))return;
            if(veri_streaming(a->rval())&&a->event()&&a->event()->detail_type()!=veEXP_DELAY)
                fail(n,"direct stream RHS with intra-assignment event control is not supported yet; capture into a packed temporary first");
            if(event_assignment(p,a->lval(),a->rval(),false,a->event()))return;
            if(array_assignment(p,a->lval(),a->rval(),false,a->event(),pidx))return;
            if(a->event()) {
                if(p.always_kind!=akALWAYS)fail(n,"intra-assignment timing is not allowed in always_comb/always_latch/always_ff");
                auto* control=a->event();
                std::string counter;
                if(control->detail_type()==vsSTMT_LOOP) {
                    auto* loop=static_cast<VeriLoopStmt*>(control);
                    if(loop->kind()!=VeriLoopStmt::REPEAT)fail(control,"unsupported intra-assignment event repetition");
                    auto count=expr(loop->judge());if(count->packed_value)count=count->packed_value;if(count->text_value)fail(n,"string cannot be used as a repeat count");read(p,count);
                    counter="repeat"+std::to_string(p.repeat_counters++);
                    add(p,"{auto count="+emit(count)+";"+counter+"=repeat_count(count,"+(count->signed_value?"true":"false")+");}");
                    control=static_cast<VeriProcTimeContStmt*>(loop->content())->control();
                }
                const auto ticks=control->detail_type()==veEXP_DELAY?procedural_delay(p,control):std::string();
                auto target=lvalue(a->lval());for(const auto& part:target.parts)if(queue_bounds.count(part.signal)||associative_signals.count(part.signal))fail(n,"queue and associative element timed/NBA assignments are not supported yet");auto value=context_expr(a->rval(),a->lval());enum_assignment(a->lval(),value);read(p,value);
                auto name="delay_value"+std::to_string(p.delay_values++);
                add(p,name+"="+emit(value,target.width)+";");
                if(control->detail_type()==vsSTMT_EVENT) {
                    int test=-1;
                    if(!counter.empty())test=add(p,"");
                    event_wait(p,static_cast<VeriEventStmt*>(control),pidx);
                    if(test>=0) {
                        add(p,"--"+counter+";");int back=add(p,"");p.instructions[back].yes=test;
                        p.instructions[test].code="pc="+counter+"?"+std::to_string(test+1)+":"+std::to_string(back+1)+";continue;";
                    }
                } else {
                    if(control->detail_type()!=veEXP_DELAY)fail(control,"unsupported intra-assignment timing control");
                    int next=int(p.instructions.size())+1;
                    add(p,"pc="+std::to_string(next)+"; s.delay("+runtime_pid(pidx)+","+ticks+"); return;");
                }
                auto saved=node("saved",target.width);saved->literal=name;saved->real_width=value->real_width;saved->enum_id=value->enum_id;saved->text_value=value->text_value;saved->object_type=value->object_type;
                assign(p,a->lval(),saved);return;
            }
            assign(p,a->lval(),context_expr(a->rval(),a->lval())); return;
        }
        case vsSTMT_NONBLOCKING: {
            if(veri_event_symbol(static_cast<VeriBlockStmt*>(n)->lval()))fail(n,"event aliases require immediate blocking assignment");
            auto* a=static_cast<VeriNonBlockStmt*>(n);
            if(clocking_assignment(p,a->lval(),a->rval(),a->event(),true))return;
            if(veri_streaming(a->rval())&&a->event()&&a->event()->detail_type()!=veEXP_DELAY)
                fail(n,"direct stream RHS with intra-assignment event control is not supported yet; capture into a packed temporary first");
            if(array_assignment(p,a->lval(),a->rval(),true,a->event(),pidx))return;
            if(a->event()) {
                if(p.always_kind!=akALWAYS)fail(n,"intra-assignment timing is not allowed in always_comb/always_latch/always_ff");
                if(a->event()->detail_type()==veEXP_DELAY) {
                    auto ticks=procedural_delay(p,a->event());needs_delayed_nba=true;
                    assign(p,a->lval(),context_expr(a->rval(),a->lval()),true,false,ticks);return;
                }
                auto* control=a->event();std::string count="1";
                if(control->detail_type()==vsSTMT_LOOP) {
                    auto* loop=static_cast<VeriLoopStmt*>(control);auto value=expr(loop->judge());if(value->packed_value)value=value->packed_value;if(value->text_value)fail(n,"string cannot be used as a repeat count");read(p,value);
                    count="repeat_count("+emit(value)+","+(value->signed_value?"true":"false")+")";
                    control=static_cast<VeriProcTimeContStmt*>(loop->content())->control();
                }
                const int site=event_site(p,static_cast<VeriEventStmt*>(control),pidx,true);
                auto value=context_expr(a->rval(),a->lval());enum_assignment(a->lval(),value);
                write(p,lvalue(a->lval()),value,true,false,{},parallel_count?"nwid["+std::to_string(site)+"]":std::to_string(site),count);return;
            }
            assign(p,a->lval(),context_expr(a->rval(),a->lval()),true); return;
        }
        case vsSTMT_COND: {
            auto* c=static_cast<VeriCondStmt*>(n);
            if(c->wait_order()) {
                if(p.function)fail(n,"wait_order timing controls are not allowed in functions");
                if(p.always_kind!=akALWAYS)fail(n,"wait_order is not allowed in always_comb/always_latch/always_ff");
                std::string events="{";
                for(auto* operand:veri_system_arguments(c->if_exp())) {
                    int id=event_signal(operand);p.touches.insert(id);events+=sid(id)+",";
                }
                events+="}";needs_wait_order=true;++p.timing_controls;
                const int site=int(wait_sites.size());wait_sites.push_back({pidx,events,{},true,{},false});
                const int next=int(p.instructions.size())+1;
                add(p,"pc="+std::to_string(next)+";s.arm_wait("+runtime_wid(site)+");return;");
                int branch=add(p,"");statement(p,c->if_stmt(),pidx);int exit=add(p,"");
                int failure=int(p.instructions.size());
                if(c->else_stmt())statement(p,c->else_stmt(),pidx);
                else {p.side_effect=true;p.selection_only_effects=false;add(p,"throw std::runtime_error("+quote("wait_order failed at "+scope->path+":"+std::to_string(c->line()))+");");}
                p.instructions[branch].code="pc=s.wait_order_succeeded("+runtime_wid(site)+")?"+std::to_string(branch+1)+":"+std::to_string(failure)+";continue;";
                p.instructions[exit].yes=int(p.instructions.size());return;
            }
            if(!c->assertion_kind()&&c->else_stmt()&&c->else_stmt()->detail_type()==vsSTMT_COND&&
               static_cast<VeriCondStmt*>(c->else_stmt())->selection_qualifier())
                fail(c->else_stmt(),"selection qualifier after else requires a begin/end block");
            if(c->selection_qualifier()) {
                needs_selection_checks=true;p.selection_checks=true;p.side_effect=true;
                const int qualifier=c->selection_qualifier();
                std::vector<VeriCondStmt*> branches;VeriNode* fallback=nullptr;
                for(auto* branch=c;;) {
                    branches.push_back(branch);fallback=branch->else_stmt();
                    if(!fallback||fallback->detail_type()!=vsSTMT_COND||(static_cast<VeriCondStmt*>(fallback)->assertion_kind()||static_cast<VeriCondStmt*>(fallback)->wait_order()))break;
                    branch=static_cast<VeriCondStmt*>(fallback);
                    if(branch->selection_qualifier())fail(branch,"selection qualifier after else requires a begin/end block");
                }
                int dispatch=add(p,"");std::vector<int> exits;
                std::string code="int chosen=-1,matches=0;";
                for(size_t i=0;i<branches.size();++i) {
                    auto condition=expr(branches[i]->if_exp());if(condition->packed_value)condition=condition->packed_value;if(condition->text_value)fail(n,"string cannot be used as a boolean condition");read(p,condition);
                    code+="if("+std::string(qualifier==3?"chosen<0&&":"")+"("+emit(condition)+").truth()==1){if(chosen<0)chosen="+std::to_string(i)+";++matches;}";
                }
                code+=selection_checks_code(n,qualifier,"if",fallback!=nullptr);
                for(size_t i=0;i<branches.size();++i) {
                    code+="if(chosen=="+std::to_string(i)+"){pc="+std::to_string(p.instructions.size())+";continue;}";
                    statement(p,branches[i]->if_stmt(),pidx);exits.push_back(add(p,""));
                }
                code+="pc="+std::to_string(p.instructions.size())+";continue;";
                if(fallback)statement(p,fallback,pidx);
                for(int exit:exits)p.instructions[exit].yes=int(p.instructions.size());
                p.instructions[dispatch].code=std::move(code);return;
            }
            auto e=expr(c->if_exp());if(e->packed_value)e=e->packed_value;if(e->text_value)fail(n,"string cannot be used as a boolean condition"); read(p,e);
            int br=add(p,""); p.instructions[br].condition=e; p.instructions[br].yes=br+1;
            statement(p,c->if_stmt(),pidx); int jump=add(p,""); p.instructions[br].no=jump+1;
            if(c->else_stmt())statement(p,c->else_stmt(),pidx);
            else if(c->assertion_kind()==1||c->assertion_kind()==2) {
                p.side_effect=true;p.selection_only_effects=false;
                const std::string kind=c->assertion_kind()==1?"assert":"assume";
                const auto identity=scope->path+(c->assertion_label().empty()?"":"."+c->assertion_label());
                add(p,"s.print("+quote(escape_format_text("DSIM error: "+kind+" failed at "+identity+":"+std::to_string(c->line())))+",{},true);");
            }
            p.instructions[jump].yes=int(p.instructions.size()); return;
        }
        case vsSTMT_LOOP: {
            auto* loop=static_cast<VeriLoopStmt*>(n);
            if(loop->kind()==VeriLoopStmt::FOREACH) {
                auto* array=loop->init();auto* symbol=veri_array_element_symbol(array);
                if(!variable(symbol))fail(n,"foreach requires a variable array identifier");
                auto shape=veri_array_shape(array);auto associative=associative_view(array);auto queue=object_queue_view(array);
                const bool string_sequence=veri_dynamic_string_value(array)&&!shape.unpacked;
                const int object=queue.id>=0?queue.id:associative.id>=0?associative.id:dynamic_object(array);
                if(associative.id>=0) {
                    const auto& indices=loop->foreach_indices();
                    if(indices.size()>size_t(shape.unpacked))fail(n,"foreach has more indices than array dimensions");
                    for(auto& name:indices)if(name.empty())fail(n,"omitted multidimensional associative foreach indices are not supported yet");
                    std::vector<int> keys,valids,tests,advances;std::vector<AssociativeView> views;
                    for(size_t axis=0;axis<indices.size();++axis) {
                        int id=scope->ids.at(indices[axis]);
                        if(foreach_indices.count(id)){auto copy=signals[id];copy.name+="$associative_foreach";id=int(signals.size());signals.push_back(std::move(copy));scope->ids[indices[axis]]=id;if(scope->subroutine)subroutine_signals.insert(id);}
                        keys.push_back(id);foreach_indices.insert(id);automatic_signals.insert(id);
                        const int valid=int(signals.size());signals.push_back({scope->path+".$foreach_valid",1,0,false,true});valids.push_back(valid);automatic_signals.insert(valid);if(scope->subroutine)subroutine_signals.insert(valid);
                        p.touches.insert(id);p.touches.insert(valid);p.writes.push_back({id,0,signals[id].width,0});p.writes.push_back({valid,0,1,0});
                        auto view=associative;for(size_t previous=0;previous<axis;++previous)view.prefix.push_back(signal_expr(keys[previous]));views.push_back(view);
                        read(p,associative_reference_expr(view));
                    }
                    const bool activation=!p.function;
                    if(activation){needs_explicit_automatic=needs_process_control=true;std::string frame="s.push_activation({";for(int id:keys)frame+=sid(id)+",";for(int id:valids)frame+=sid(id)+",";add(p,frame+"});");++p.activation_depth;}
                    for(size_t axis=0;axis<keys.size();++axis) {
                        if(associative_queue_leaf(views[axis]))add(p,"s.set("+sid(keys[axis])+",V(0,0,32));s.set("+sid(valids[axis])+",V(s.associative_queue_size("+associative_reference(views[axis])+")>0,0,1));");
                        else add(p,"{V key;bool found=s.associative_cursor("+associative_reference(views[axis])+",key,0);if(found)s.set("+sid(keys[axis])+",key);s.set("+sid(valids[axis])+",V(found,0,1));}");
                        const int test=add(p,"");tests.push_back(test);p.instructions[test].condition=signal_expr(valids[axis]);p.instructions[test].yes=test+1;
                    }
                    p.loops.emplace_back();statement(p,loop->content(),pidx);auto transfers=std::move(p.loops.back());p.loops.pop_back();
                    advances.resize(keys.size());
                    for(size_t axis=keys.size();axis--;) {
                        if(associative_queue_leaf(views[axis]))advances[axis]=add(p,"{auto index=s.get("+sid(keys[axis])+").a+1;s.set("+sid(keys[axis])+",V(index,0,32));s.set("+sid(valids[axis])+",V(index<s.associative_queue_size("+associative_reference(views[axis])+"),0,1));}");
                        else advances[axis]=add(p,"{auto key=s.get("+sid(keys[axis])+");bool found=s.associative_cursor("+associative_reference(views[axis])+",key,2);if(found)s.set("+sid(keys[axis])+",key);s.set("+sid(valids[axis])+",V(found,0,1));}");
                        int back=add(p,"");p.instructions[back].yes=tests[axis];
                        if(axis+1<keys.size())p.instructions[tests[axis+1]].no=advances[axis];
                    }
                    const int end=int(p.instructions.size());p.instructions[tests[0]].no=end;
                    if(activation){--p.activation_depth;add(p,"");}
                    for(int jump:transfers.breaks)p.instructions[jump].yes=end;for(int jump:transfers.continues)p.instructions[jump].yes=advances.back();return;
                }
                if(object>=0||string_sequence) {
                    const auto& indices=loop->foreach_indices();
                    if(indices.size()!=1)fail(n,"dynamic foreach currently supports one unpacked index");
                    if(indices.front().empty())fail(n,"dynamic foreach requires an unpacked index");
                    int id=scope->ids.at(indices.front());
                    if(foreach_indices.count(id)){auto value=signals[id];value.name+="$dynamic_foreach";id=int(signals.size());signals.push_back(std::move(value));scope->ids[indices.front()]=id;if(scope->subroutine)subroutine_signals.insert(id);}
                    foreach_indices.insert(id);automatic_signals.insert(id);
                    p.touches.insert(id);p.writes.push_back({id,0,signals[id].width,0});
                    const bool assoc=associative.id>=0,text=assoc&&veri_array_container_kind(array)==vrASSOC_STRING;
                    std::vector<int> locals{id};int valid=-1;
                    auto local=[&](const char* suffix,int width) {
                        int value=int(signals.size());signals.push_back({scope->path+suffix,width,0,false,true});
                        automatic_signals.insert(value);if(scope->subroutine)subroutine_signals.insert(value);
                        p.touches.insert(value);p.writes.push_back({value,0,width,0});locals.push_back(value);return value;
                    };
                    if(assoc) {
                        valid=local(".$foreach_valid",1);read(p,signal_expr(object));
                        // The target expression participates in each cursor
                        // operation. A body may change its selected object;
                        // saving the entry receiver would visit the old map.
                        if(associative.receiver)read(p,associative.receiver);
                    }
                    const bool activation=!p.function;
                    if(activation){needs_explicit_automatic=needs_process_control=true;std::string frame="s.push_activation({";for(int value:locals)frame+=sid(value)+",";add(p,frame+"});");++p.activation_depth;}
                    const auto ref=assoc?associative_reference(associative):string_sequence?std::string():sid(object);
                    if(assoc)add(p,"{auto key="+std::string(text?"V::text(\"\")":"V(0,0,32)")+";bool found=s.associative_cursor("+ref+",key,0);s.set("+sid(id)+",key);s.set("+sid(valid)+",V(found,0,1));}");
                    else add(p,"s.set("+sid(id)+",V(0,0,32));");
                    auto size=string_sequence?node("text_method",32,{expr(array)}):queue.id>=0?node("container_method",32,{queue.receiver}):dynamic_size_expr(object);
                    if(string_sequence)size->literal="return text_len(text_arg0);";
                    if(queue.id>=0){size->signal=objects_signal;size->reads.insert(objects_signal);size->literal="return V(s.object_queue_size("+object_queue_reference(queue,"container_arg0")+"),0,32);";}
                    int test=add(p,"");auto condition=assoc?signal_expr(valid):node("<",1,{signal_expr(id),size});
                    read(p,condition);p.instructions[test].condition=condition;p.instructions[test].yes=test+1;
                    p.loops.emplace_back();statement(p,loop->content(),pidx);
                    auto transfers=std::move(p.loops.back());p.loops.pop_back();
                    int advance=add(p,assoc?"{auto key=s.get("+sid(id)+");bool found=s.associative_cursor("+ref+",key,2);if(found)s.set("+sid(id)+",key);s.set("+sid(valid)+",V(found,0,1));}":"s.set("+sid(id)+",V(s.get("+sid(id)+").a+1,0,32));");
                    int back=add(p,"");p.instructions[back].yes=test;
                    int end=int(p.instructions.size());p.instructions[test].no=end;
                    if(activation){--p.activation_depth;add(p,"");}
                    for(int jump:transfers.breaks)p.instructions[jump].yes=end;
                    for(int jump:transfers.continues)p.instructions[jump].yes=advance;
                    return;
                }
                if(veri_aggregate_type(array))fail(n,"foreach over packed aggregates is not supported yet");
                const auto& indices=loop->foreach_indices();
                if(indices.size()>shape.dimensions.size())fail(n,"foreach has more indices than array dimensions");
                uint64_t total=1;std::vector<uint64_t> sizes(indices.size(),1),strides(indices.size(),1);
                for(size_t d=indices.size();d-->0;)if(!indices[d].empty()) {
                    const auto bounds=shape.dimensions[d];sizes[d]=uint64_t(std::abs(int64_t(bounds.first)-bounds.second))+1;
                    strides[d]=total;if(sizes[d]>UINT64_MAX/total)fail(n,"foreach iteration count exceeds 64 bits");total*=sizes[d];
                }
                const auto counter="repeat"+std::to_string(p.repeat_counters++);
                std::string stores,advance,frame="s.push_activation({";
                for(size_t d=0;d<indices.size();++d)if(!indices[d].empty()) {
                    // Keep the lexical scope (and static body locals) shared.
                    // Each compiled process has a logical index; a loop frame
                    // gives overlapping invocations independent physical slots.
                    auto key=std::make_tuple(scope,indices[d],pidx);
                    auto slot=foreach_index_slots.find(key);int id=scope->ids.at(indices[d]);
                    if(slot!=foreach_index_slots.end())id=slot->second;
                    else {
                        if(foreach_indices.count(id)) {
                            auto copy=signals[id];copy.name+="$foreach"+std::to_string(pidx);
                            id=int(signals.size());signals.push_back(std::move(copy));
                            if(scope->subroutine)subroutine_signals.insert(id);
                        }
                        foreach_index_slots.emplace(key,id);
                    }
                    scope->ids[indices[d]]=id;foreach_indices.insert(id);automatic_signals.insert(id);
                    frame+=sid(id)+",";
                    p.touches.insert(id);p.writes.push_back({id,0,32,0});
                    const auto bounds=shape.dimensions[d];
                    // Widen before adding offsets, including an endpoint at INT_MAX.
                    stores+="s.set("+sid(id)+",V(uint64_t(int64_t("+std::to_string(bounds.first)+")"+
                        (bounds.first>bounds.second?"-":"+")+"int64_t((("+std::to_string(total)+"ull-"+counter+")/"+std::to_string(strides[d])+"ull)%"+std::to_string(sizes[d])+"ull)),0,32));";
                    // Nested loop increments run inside out, including the
                    // one-past-bound value retained by detached children.
                    advance="if((("+std::to_string(total)+"ull-"+counter+"+1ull)%"+std::to_string(strides[d])+"ull)==0)"
                        "s.set("+sid(id)+",V(s.get("+sid(id)+").a"+(bounds.first>=bounds.second?"-":"+")+"1ull,0,32));"+advance;
                }
                const bool activation=!p.function;
                if(activation){add(p,frame+"});");++p.activation_depth;}
                add(p,counter+"="+std::to_string(total)+"ull;");
                int test=add(p,"");
                add(p,stores);p.loops.emplace_back();statement(p,loop->content(),pidx);
                auto transfers=std::move(p.loops.back());p.loops.pop_back();
                // Without detached children the intermediate/terminal index
                // updates cannot be observed; retain the compact flat loop.
                int continuation=add(p,"\n#ifdef DSIM_DYNAMIC_FORK_ENABLED\n"+advance+"\n#endif\n--"+counter+";");
                int back=add(p,"");p.instructions[back].yes=test;int end=int(p.instructions.size());
                if(activation){--p.activation_depth;add(p,"");}
                p.instructions[test].code="pc="+counter+"?"+std::to_string(test+1)+":"+std::to_string(end)+";continue;";
                for(int jump:transfers.breaks)p.instructions[jump].yes=end;
                for(int jump:transfers.continues)p.instructions[jump].yes=continuation;
                return;
            }
            std::function<void(VeriNode*)> header=[&](VeriNode* h) {
                if(!h)return;
                if(h->detail_type()==vsSTMT_STMT_LIST) {
                    for(auto* step:static_cast<VeriStmtList*>(h)->stmt_list())header(step);
                } else if(h->detail_type()==vsSTMT_CALL) {
                    auto* call=static_cast<VeriCallerStmt*>(h)->caller();
                    auto* hive=veri_call_hive(call);
                    if(hive&&hive->detail_type()!=vsDECL_FUNC_DECL)fail(h,"for step requires a function call, not a task");
                    const auto controls=p.timing_controls;
                    statement(p,h,pidx);
                    if(p.timing_controls!=controls)fail(h,"blocking tasks are not allowed in for steps");
                } else if(h->detail_type()==vsSTMT_UPDATE||h->detail_type()==vsSTMT_COMPOUND)statement(p,h,pidx);
                else if(h->detail_type()==vsSTMT_BLOCKING) {
                    auto* a=static_cast<VeriBlockStmt*>(h);
                    if(a->event())fail(h,"timing controls are not allowed in for headers");
                    assign(p,a->lval(),context_expr(a->rval(),a->lval()));
                } else if(h->detail_type()==veEXP_ASSIGN) {
                    auto* a=static_cast<VeriAssignExp*>(h);assign(p,a->lval(),context_expr(a->rval(),a->lval()));
                } else fail(h,"for header requires blocking assignments or increment/decrement statements");
            };
            if(loop->kind()==VeriLoopStmt::FOR) header(loop->init());
            std::string counter;
            if(loop->kind()==VeriLoopStmt::REPEAT) {
                counter="repeat"+std::to_string(p.repeat_counters++);
                auto count=expr(loop->judge());if(count->packed_value)count=count->packed_value;if(count->text_value)fail(n,"string cannot be used as a repeat count"); read(p,count);
                add(p,"{auto count="+emit(count)+"; "+counter+"=repeat_count(count,"+(count->signed_value?"true":"false")+");}");
            }
            int start=int(p.instructions.size()),test=-1;
            if(loop->kind()!=VeriLoopStmt::DO_WHILE && loop->kind()!=VeriLoopStmt::FOREVER) {
                test=add(p,"");
                if(loop->kind()!=VeriLoopStmt::REPEAT) {
                    E condition;
                    if(loop->judge())condition=expr(loop->judge());
                    else {condition=node("literal",1);condition->literal="V(1,0,1)";}
                    if(condition->packed_value)condition=condition->packed_value;if(condition->text_value)fail(n,"string cannot be used as a boolean condition");read(p,condition);p.instructions[test].condition=condition;
                    p.instructions[test].yes=test+1;
                }
            }
            p.loops.emplace_back();
            statement(p,loop->content(),pidx);
            auto transfers=std::move(p.loops.back());p.loops.pop_back();
            int continuation=int(p.instructions.size());
            if(loop->kind()==VeriLoopStmt::FOR) header(loop->iter());
            if(loop->kind()==VeriLoopStmt::REPEAT) add(p,"--"+counter+";");
            if(loop->kind()==VeriLoopStmt::DO_WHILE) {
                auto condition=expr(loop->judge());if(condition->packed_value)condition=condition->packed_value;if(condition->text_value)fail(n,"string cannot be used as a boolean condition"); read(p,condition);
                test=add(p,""); p.instructions[test].condition=condition;
                p.instructions[test].yes=start; p.instructions[test].no=test+1;
            } else {
                int back=add(p,""); p.instructions[back].yes=start;
                if(test>=0) {
                    if(loop->kind()==VeriLoopStmt::REPEAT)
                        p.instructions[test].code="pc="+counter+"?"+std::to_string(test+1)+":"+std::to_string(back+1)+"; continue;";
                    else p.instructions[test].no=back+1;
                }
            }
            for(int jump:transfers.breaks)p.instructions[jump].yes=int(p.instructions.size());
            for(int jump:transfers.continues)p.instructions[jump].yes=continuation;
            return;
        }
        case vsSTMT_CASE: {
            auto* c=static_cast<VeriCaseStmt*>(n);
            auto* items=static_cast<VeriCaseItemList*>(c->item_list());
            auto selector=expr(c->switch_value());if(selector->packed_value)selector=selector->packed_value;
            const bool text_case=selector->text_value;
            if(text_case&&c->case_type()!=vcCASE)fail(n,"string case requires exact case matching");
            read(p,selector);
            int width=selector->width;bool signed_case=selector->signed_value;
            std::vector<std::pair<VeriNode*,std::vector<E>>> branches;
            for(auto* n:items->other_item()) {
                auto* item=static_cast<VeriCaseItem*>(n); std::vector<E> labels;
                if(c->case_type()==vcINSIDE)labels=inside_items(std::vector<VeriNode*>(item->label().begin(),item->label().end()));
                else for(auto* n:item->label())labels.push_back(expr(n));
                for(const auto& label:labels)if(selector->object_type==opaque_handle_type||label->object_type==opaque_handle_type) {
                    if(!class_compatible(selector->object_type,opaque_handle_type)||!class_compatible(label->object_type,opaque_handle_type))fail(n,"chandle case requires compatible handles or null");
                }
                for(auto& label:labels){if(!text_case&&label->packed_value)label=label->packed_value;if(label->text_value!=text_case)fail(n,"case selector and labels require compatible string or integral values");read(p,label);width=std::max(width,label->width);signed_case=signed_case&&label->signed_value;}
                branches.push_back({item->stmt(),std::move(labels)});
            }
            // Exact, known scalar labels form a host switch. Keep the first
            // branch and the number of distinct matching branches for unique
            // diagnostics (duplicate labels in one branch count only once).
            std::map<uint64_t,std::set<size_t>> constant_labels;
            bool constant_case=!text_case&&c->case_type()==vcCASE&&width<=64&&!branches.empty();
            const uint64_t case_mask=width>=64?UINT64_MAX:(uint64_t(1)<<width)-1;
            for(size_t i=0;i<branches.size()&&constant_case;++i)for(const auto& label:branches[i].second) {
                if(label->op!="literal"||!label->canonical_literal||label->unknown||label->width>64) {constant_case=false;break;}
                uint64_t value=label->value;
                if(signed_case&&label->negative&&label->width<64)value|=~((uint64_t(1)<<label->width)-1);
                constant_labels[value&case_mask].insert(i);
            }
            if(constant_case) {
                if(c->selection_qualifier()){needs_selection_checks=true;p.selection_checks=true;p.side_effect=true;}
                int dispatch=add(p,"");std::vector<int> exits;
                std::string code="auto selected="+emit_expression(selector,width,parallel_count!=0,signed_case)+";int chosen=-1,matches=0;\n#ifndef DSIM_RTL_REFERENCE_CASE_DISPATCH\n";
                code+="// Constant scalar case dispatch.\nif(!selected.b)switch(selected.a){";
                for(const auto& entry:constant_labels)code+="case "+std::to_string(entry.first)+"ULL:chosen="+std::to_string(*entry.second.begin())+";matches="+std::to_string(entry.second.size())+";break;";
                code+="default:break;}\n#else\n";
                for(size_t i=0;i<branches.size();++i) {
                    code+="if("+std::string(!c->selection_qualifier()||c->selection_qualifier()==3?"chosen<0&&":"")+"(";
                    bool first=true;
                    for(const auto& label:branches[i].second) {
                        if(!first)code+="||";first=false;
                        code+="case_match(selected,"+emit_expression(label,width,parallel_count!=0,signed_case)+",0)";
                    }
                    code+=")){if(chosen<0)chosen="+std::to_string(i)+";++matches;}";
                }
                code+="\n#endif\n";
                if(c->selection_qualifier())code+=selection_checks_code(n,c->selection_qualifier(),"case",items->default_item()!=nullptr);
                const auto selection=code;std::vector<int> targets;
                for(size_t i=0;i<branches.size();++i) {
                    targets.push_back(int(p.instructions.size()));
                    code+="if(chosen=="+std::to_string(i)+"){pc="+std::to_string(p.instructions.size())+";continue;}";
                    statement(p,branches[i].first,pidx);exits.push_back(add(p,""));
                }
                targets.push_back(int(p.instructions.size()));
                code+="pc="+std::to_string(p.instructions.size())+";continue;";
                if(items->default_item())statement(p,static_cast<VeriDefaultCaseItem*>(items->default_item())->stmt(),pidx);
                for(int exit:exits)p.instructions[exit].yes=int(p.instructions.size());
                p.instructions[dispatch].code=std::move(code);
                if(region_expression(selector)) {
                    p.instructions[dispatch].case_selection=selection;
                    p.instructions[dispatch].case_targets=std::move(targets);
                }
                return;
            }
            auto case_labels_match=[&](const std::vector<E>& labels,int mode,const std::string& join) {
                // VCS evaluates the comma list of the current item before
                // comparing it. An OR of calls would skip later side effects.
                const bool materialize=labels.size()>1&&std::any_of(labels.begin(),labels.end(),[](const E& e){return !e->writes.empty()||e->io_state||e->random_state;});
                std::string prefix,match;
                for(size_t i=0;i<labels.size();++i) {
                    std::string value=text_case?emit(labels[i]):emit_expression(labels[i],width,parallel_count!=0,signed_case);
                    if(materialize){auto local="case_label"+std::to_string(i);prefix+="auto "+local+"="+value+";";value=local;}
                    if(i)match+=join;
                    match+=text_case?"(selected.text_value()==("+value+").text_value())":"case_match(selected,"+value+","+std::to_string(mode)+")";
                }
                return materialize?"([&](){"+prefix+"return "+match+";}())":match;
            };
            if(c->selection_qualifier()) {
                needs_selection_checks=true;p.selection_checks=true;p.side_effect=true;
                const int qualifier=c->selection_qualifier();int dispatch=add(p,"");std::vector<int> exits;
                std::string code="auto selected="+emit_expression(selector,width,parallel_count!=0,signed_case)+";int chosen=-1,matches=0;";
                const int mode=c->case_type()==vcCASE?0:c->case_type()==vcCASEZ?1:2;
                for(size_t i=0;i<branches.size();++i) {
                    std::string match;
                    if(c->case_type()==vcINSIDE) {
                        auto saved=node("saved",width);saved->literal="selected";saved->signed_value=signed_case;
                        auto members=branches[i].second;members.insert(members.begin(),saved);
                        match="("+emit(node("inside",1,std::move(members)))+").truth()==1";
                    } else match=case_labels_match(branches[i].second,mode,"||");
                    code+="if("+std::string(qualifier==3?"chosen<0&&":"")+"("+match+")){if(chosen<0)chosen="+std::to_string(i)+";++matches;}";
                }
                const std::string kind=c->case_type()==vcCASE?"case":c->case_type()==vcCASEZ?"casez":c->case_type()==vcCASEX?"casex":"case inside";
                code+=selection_checks_code(n,qualifier,kind,items->default_item()!=nullptr);
                for(size_t i=0;i<branches.size();++i) {
                    code+="if(chosen=="+std::to_string(i)+"){pc="+std::to_string(p.instructions.size())+";continue;}";
                    statement(p,branches[i].first,pidx);exits.push_back(add(p,""));
                }
                code+="pc="+std::to_string(p.instructions.size())+";continue;";
                if(items->default_item())statement(p,static_cast<VeriDefaultCaseItem*>(items->default_item())->stmt(),pidx);
                for(int exit:exits)p.instructions[exit].yes=int(p.instructions.size());
                p.instructions[dispatch].code=std::move(code);return;
            }
            int dispatch=add(p,""); std::vector<int> exits;
            std::string code="auto selected="+emit_expression(selector,width,parallel_count!=0,signed_case)+"; ";
            int mode=c->case_type()==vcCASE?0:c->case_type()==vcCASEZ?1:2;
            for(auto& branch:branches) {
                if(c->case_type()==vcINSIDE) {
                    auto saved=node("saved",width);saved->literal="selected";saved->signed_value=signed_case;
                    auto members=branch.second;members.insert(members.begin(),saved);
                    code+="if(("+emit(node("inside",1,std::move(members)))+").truth()==1){pc="+std::to_string(p.instructions.size())+";continue;} ";
                    statement(p,branch.first,pidx);exits.push_back(add(p,""));continue;
                }
                code+="if("+case_labels_match(branch.second,mode," || ");
                code+="){pc="+std::to_string(p.instructions.size())+"; continue;} ";
                statement(p,branch.first,pidx); exits.push_back(add(p,""));
            }
            code+="pc="+std::to_string(p.instructions.size())+"; continue;";
            if(items->default_item()) statement(p,static_cast<VeriDefaultCaseItem*>(items->default_item())->stmt(),pidx);
            for(int exit:exits) p.instructions[exit].yes=int(p.instructions.size());
            p.instructions[dispatch].code=std::move(code); return;
        }
        case vsSTMT_EVENT_TRIGGER: {
            auto* trigger=static_cast<VeriActionStmt*>(n);auto event=instance_event(trigger->target());
            std::string source;
            if(event){read(p,event);source="s.event_wait_id("+emit(event)+")";p.touches.insert(objects_signal);}
            else {int id=event_signal(trigger->target());p.touches.insert(id);source=sid(id);}
            if(trigger->op()) {
                if(trigger->value()) {
                    auto ticks=procedural_delay(p,trigger->value());needs_delayed_nba=true;
                    add(p,"s.trigger_event_after("+source+","+ticks+");");
                } else add(p,"s.trigger_event_nba("+source+");");
            } else add(p,"s.trigger_event("+source+");");
            return;
        }
        case vsSTMT_WAIT: {
            if(p.always_kind!=akALWAYS)fail(n,"wait is not allowed in always_comb/always_latch/always_ff");
            auto* wait=static_cast<VeriProcTimeContStmt*>(n);
            auto condition=expr(wait->control());if(condition->virtual_dispatch)fail(n,"virtual function is not allowed in event/wait controls");if(condition->packed_value)condition=condition->packed_value;if(condition->text_value)fail(n,"string cannot be used as a boolean condition");read(p,condition);
            // Like an explicit event expression, function arguments determine
            // wake sensitivity. Body-only global reads remain in the process
            // dependency graph but do not wake this wait (VCS-compatible).
            auto dependencies=condition->reads;
            const auto check=int(p.instructions.size());
            // Recheck the level after every wake. Empty sensitivity blocks
            // permanently without polling or consuming simulation events.
            add(p,"if(("+emit(condition)+").truth()!=1){pc="+std::to_string(check)+";"+wait_code(pidx,dependencies)+"return;}");
            statement(p,wait->stmt(),pidx);return;
        }
        case vsSTMT_CYCLE_CONTROL: {
            auto* cycle=static_cast<VeriClocking*>(n);int clock=-1;
            for(auto* owner=scope;owner;owner=owner->parent)if(auto found=default_clockings.find(owner);found!=default_clockings.end()){clock=found->second;break;}
            if(clock<0)fail(n,"cycle delay requires a lexical default clocking");
            auto count=expr(cycle->children[0]);
            if(count->op!="literal"||count->unknown||count->negative||!count->value||count->host_overflow)fail(n,"clocking cycle count currently requires a positive integral constant");
            clocking_wait(p,pidx,clock,std::to_string(count->value)+"ULL");statement(p,cycle->children[1],pidx);return;
        }
        case vsSTMT_PROC_TIME_CONTROL: {
            auto* t=static_cast<VeriProcTimeContStmt*>(n); auto* c=t->control(); int next=int(p.instructions.size())+1;
            if(p.always_kind==akALWAYS_COMB||p.always_kind==akALWAYS_LATCH)
                fail(n,"timing controls are not allowed in always_comb/always_latch");
            if(p.always_kind==akALWAYS_FF&&(c->detail_type()!=vsSTMT_EVENT||p.timing_controls++))
                fail(n,"always_ff requires exactly one event control and no delays");
            if(c->detail_type()==veEXP_DELAY) {
                auto ticks=procedural_delay(p,c);
                add(p,"pc="+std::to_string(next)+"; s.delay("+runtime_pid(pidx)+","+ticks+"); return;");
            } else if(c->detail_type()==vsSTMT_EVENT) {
                auto* ev=static_cast<VeriEventStmt*>(c);
                if(ev->is_all()==IS_TRUE) {
                    // Compile the controlled statement first to infer its read set.
                    int wait=add(p,""); auto before=p.reads;const auto first_read=p.sensitivity_reads.size();p.reads.clear();
                    statement(p,t->stmt(),pidx); auto deps=p.reads;
                    if(needs_object_format&&contains_object_format({p.sensitivity_reads.begin()+first_read,p.sensitivity_reads.end()}))fail(ev,"class formatting in implicit sensitivity is not supported yet; use an explicit event control");
                    p.reads.insert(before.begin(),before.end());
                    if(wait==0&&p.always_process)p.startup_wait=int(wait_sites.size());
                    p.instructions[wait].code="pc="+std::to_string(next)+"; "+wait_code(pidx,deps)+" return;"; return;
                }
                event_wait(p,ev,pidx);
            } else fail(c,"unsupported timing control kind "+std::to_string(c->detail_type()));
            statement(p,t->stmt(),pidx); return;
        }
        case vsSTMT_SYS_CALL: {
            auto* call=static_cast<VeriSysCallerStmt*>(n); auto fn=call->caller();
            if(fn=="$sdf_annotate") {
                auto found=prepared_sdf_tasks.find({sdf_module_scope(scope),n});
                if(found==prepared_sdf_tasks.end())fail(n,"$sdf_annotate currently requires an unconditional time-zero initial prefix; dynamic/delayed annotation is not implemented");
                const auto& task=sdf_tasks.at(found->second);
                if(!task.logfile.empty()) {
                    needs_sdf_log=true;
                    p.io_state=true;p.side_effect=true;p.selection_only_effects=false;
                    add(p,"{std::ofstream log("+quote(task.logfile)+",std::ios::binary|std::ios::trunc);if(!log)throw std::runtime_error(\"cannot write SDF annotation log\");log<<"+quote(task.report)+";log.close();if(!log)throw std::runtime_error(\"failed writing SDF annotation log\");}");
                }
                return;
            }
            if(fn=="$readmemh"||fn=="$readmemb"||fn=="$writememh"||fn=="$writememb") {
                const bool writing=fn=="$writememh"||fn=="$writememb";
                std::vector<VeriNode*> args;
                if(call->arg()&&call->arg()->detail_type()==veEXP_MULTI)
                    for(auto* a:static_cast<VeriMultiExp*>(call->arg())->exp())args.push_back(a);
                if(args.size()<2||args.size()>4)fail(n,fn+" requires filename, memory and optional start/end indices");
                if(args[0]->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(args[0])->pri_type()!=veSTR)
                    fail(n,fn+" requires a constant string filename");
                auto filename=decode_string(static_cast<VeriPrimaryExp*>(args[0])->str(),args[0]);
                if(filename.empty()||filename.find('\0')!=std::string::npos)fail(n,"invalid memory filename");
                if(args[1]->detail_type()!=veEXP_PRI)fail(n,fn+" requires a whole memory target");
                auto* symbol=static_cast<VeriPrimaryExp*>(args[1])->var();
                if(!variable(symbol)||Variable{symbol}->range_depth()!=1)
                    fail(n,fn+" requires a one-dimensional unpacked variable array");
                Variable var{symbol};auto* sc=variable_scope(n,var);
                int memory=sc->memories.at(var->name());const auto& m=memories[size_t(memory)];
                if(m.dynamic&&!m.fixed_count)fail(n,"memory file operations on dynamic arrays are not supported yet");
                if(signals[m.words.front()].net)fail(n,"memory file initialization requires a variable array");
                std::string bounds;
                for(size_t i=2;i<4;++i) {
                    if(i<args.size()) {auto e=expr(args[i]);read(p,e);bounds+=",memory_bound("+emit(e)+")";}
                    else bounds+=","+std::to_string(i==2?m.base:m.base+(m.fixed_count?m.fixed_count:int(m.words.size()))-1);
                }
                for(int id:m.words) {
                    p.touches.insert(id);
                    if(writing)read(p,signal_expr(id));else p.writes.push_back({id,0,signals[id].width,0});
                }
                p.io_state=true;p.side_effect=true;p.selection_only_effects=false;
                needs_memory_io=true;
                if(var->dlen()>64)needs_wide=true;
                const std::string table=m.fixed_count?sid(m.words.front())+","+std::to_string(m.fixed_count)+","+std::to_string(m.base):memory_table(memory);
                add(p,std::string(writing?"write_":"read_")+(m.fixed_count?"fixed_memory(s,":"memory(s,")+table+","+quote(filename)+","+((fn=="$readmemh"||fn=="$writememh")?"16":"2")+","+std::to_string(var->dlen())+bounds+(m.fixed_count?","+std::string(signals[m.words.front()].two_state?"true":"false"):parallel_count?",sid.data()":"")+");");return;
            }
            if(fn=="$dumpfile"||fn=="$dumpvars"||fn=="$dumpoff"||fn=="$dumpon"||fn=="$dumpall") {
                if(parallel_count)fail(n,"dump tasks are not yet supported with --threads; use --wave-support and runtime --waveform for parallel capture");
                if(!wave_enabled)fail(n,"dump tasks require the waveform runtime");
                needs_dump_tasks=true;
                std::vector<VeriNode*> args;
                if(call->arg()) {
                    if(call->arg()->detail_type()!=veEXP_MULTI)fail(n,"invalid dump task arguments");
                    for(auto* a:static_cast<VeriMultiExp*>(call->arg())->exp())args.push_back(a);
                }
                if(fn=="$dumpfile") {
                    if(args.size()!=1||args[0]->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(args[0])->pri_type()!=veSTR)
                        fail(n,"$dumpfile requires one constant string filename");
                    auto filename=decode_string(static_cast<VeriPrimaryExp*>(args[0])->str(),args[0]);
                    if(filename.empty()||filename.find('\0')!=std::string::npos)fail(n,"$dumpfile requires a nonempty filename without NUL");
                    add(p,"s.wave_effect([&wave]{wave.dumpfile("+quote(filename)+");});");return;
                }
                if(fn=="$dumpvars") {
                    E depth=args.empty()?node("literal",32):expr(args[0]);
                    if(args.empty())depth->literal="V(0,0,32)";
                    if(depth->width>64)fail(n,"$dumpvars depth wider than 64 bits is not supported");
                    if(depth->op=="literal"&&(depth->unknown||depth->host_overflow||depth->value>10000))fail(n,"$dumpvars depth must be in 0..10000");
                    read(p,depth);std::string targets="{";
                    for(size_t i=1;i<args.size();++i)targets+=dump_target(args[i])+",";
                    if(args.size()<2) {
                        targets+="{{";for(const auto& part:scopes.front()->wave_path)targets+=quote(part)+",";
                        targets+="},\"\"},";
                    }
                    add(p,"s.wave_effect([&wave,time=s.now,depth="+emit(depth)+"]{wave.dumpvars(time,depth,"+targets+"});});");return;
                }
                if(!args.empty())fail(n,fn+" takes no arguments");
                add(p,"s.wave_effect([&wave,time=s.now]{wave.dump_control(time,"+std::string(fn=="$dumpoff"?"1":fn=="$dumpon"?"2":"4")+");});");return;
            }
            if(fn=="$fclose"||fn=="$fflush"||fn=="$fwrite"||fn=="$fdisplay") {
                needs_file_io=true;p.io_state=true;p.side_effect=true;p.selection_only_effects=false;p.event_safe=false;
                auto args=veri_system_arguments(call->arg());
                const bool writing=fn=="$fwrite"||fn=="$fdisplay";
                if(writing?args.size()<2:(args.size()>1||(args.empty()&&fn!="$fflush")))
                    fail(n,fn+" argument count mismatch");
                auto fd=args.empty()?node("literal",32):expr(args[0]);
                if(args.empty())fd->literal="V(0,0,32)";
                if(fd->text_value)fail(n,"file descriptor requires an integral value");
                read(p,fd);
                if(writing) {
                    auto value=formatted_value(args[1],{args.begin()+2,args.end()});read(p,value);
                    add(p,"{auto file_descriptor="+emit(fd)+";auto file_text="+emit(value)+";s.file_write(s.file_integer(file_descriptor),file_text.text_value()+"+(fn=="$fdisplay"?"std::string(1,'\\n')":"std::string()")+");}");
                } else add(p,std::string("s.")+(fn=="$fclose"?"file_close":"file_flush")+"(s.file_integer("+emit(fd)+"));");
                return;
            }
            if(fn=="$sformat"||fn=="$swrite"||fn=="$swriteh"||fn=="$swriteb"||fn=="$swriteo") {
                auto args=veri_system_arguments(call->arg());
                if(args.empty()||(fn=="$sformat"&&args.size()<2))fail(n,fn+" requires a target"+(fn=="$sformat"?" and format":""));
                auto value=fn=="$sformat"?formatted_value(args[1],{args.begin()+2,args.end()}):swrite_value({args.begin()+1,args.end()},fn=="$swrite"?'d':fn.back());
                auto target=lvalue(args[0]);
                for(const auto& part:target.parts)if(signals[part.signal].net)fail(args[0],fn+" requires a variable target");
                if(!veri_dynamic_string_value(args[0])) {
                    if(enum_identity(args[0]))fail(args[0],fn+" enum target is not supported");
                    auto packed=node("call",target.width,{value});packed->literal="return packed_text(call_arg0.text_value(),"+std::to_string(target.width)+");";value=packed;
                    if(target.width>64)needs_wide=true;
                }
                write(p,target,value,false,false);return;
            }
            if(fn=="$finish"||fn=="$stop") {
                p.side_effect=true;p.selection_only_effects=false;
                needs_global_finish=true;
                if(call->arg()) {
                    if(call->arg()->detail_type()!=veEXP_MULTI) fail(n,"unsupported "+fn+" argument");
                    auto& args=static_cast<VeriMultiExp*>(call->arg())->exp();
                    if(args.size()!=1) fail(n,"unsupported "+fn+" argument count");
                    auto e=expr(args.front());
                    if(e->op!="literal"||e->unknown||e->host_overflow||e->value>2) fail(n,fn+" argument must be 0, 1 or 2");
                }
                if(p.function||lowering_final||fn=="$stop") {
                    needs_termination_unwind=true;p.io_state=true;p.event_safe=false;
                    if(fn=="$stop"){needs_stop=true;add(p,"s.stop_simulation();");}
                    else add(p,"s.terminate_simulation();");
                    return;
                }
                add(p,"s.finished=true; return;"); return;
            }
            if(fn=="$timeformat") {
                p.side_effect=true;p.selection_only_effects=false;
                if(!call->arg()||call->arg()->detail_type()!=veEXP_MULTI)fail(n,"$timeformat requires four constant arguments");
                auto args=static_cast<VeriMultiExp*>(call->arg())->exp();
                if(args.size()!=4)fail(n,"$timeformat requires four constant arguments");
                auto integer=[&](VeriNode* a) {
                    bool negative=a->detail_type()==veEXP_UNA && static_cast<VeriUnaryExp*>(a)->op()==vtUSUB;
                    auto e=expr(negative?static_cast<VeriUnaryExp*>(a)->exp_child():a);
                    if(e->op!="literal"||e->unknown||e->host_overflow||e->value>1000)fail(a,"invalid constant $timeformat argument");
                    return negative?-int(e->value):int(e->value);
                };
                int units=integer(args.front());args.pop_front();int digits=integer(args.front());args.pop_front();
                auto* suffix=args.front();args.pop_front();
                if(suffix->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(suffix)->pri_type()!=veSTR)fail(suffix,"$timeformat suffix must be a constant string");
                auto text=decode_string(static_cast<VeriPrimaryExp*>(suffix)->str(),suffix);
                int width=integer(args.front());
                if(units < -15 || units>0 || digits<0 || digits>15 || width<0 || width>1000)fail(n,"$timeformat units/precision/width out of supported range");
                add(p,"s.timeformat("+std::to_string(units)+","+std::to_string(digits)+","+quote(text)+","+std::to_string(width)+");");return;
            }
            const bool severity=fn=="$fatal"||fn=="$error"||fn=="$warning"||fn=="$info";
            if(fn!="$display" && fn!="$write" && !severity) fail(n,"unsupported system task "+fn);
            p.side_effect=true;p.selection_only_effects=false;
            auto* a=call->arg();
            if((!a&&!severity)||(a&&a->detail_type()!=veEXP_MULTI)) fail(n,"display requires a constant format string");
            std::list<VeriNode*> args;if(a)args=static_cast<VeriMultiExp*>(a)->exp();
            if(fn=="$fatal"&&!args.empty()) {
                auto number=expr(args.front());
                if(number->op!="literal"||number->unknown||number->host_overflow||number->negative||number->value>2)
                    fail(n,"$fatal finish number must be a constant 0, 1 or 2");
                args.pop_front();
            }
            std::string decoded;
            if(!args.empty()) {
                auto* first=args.front();args.pop_front();
                if(first->detail_type()!=veEXP_PRI || static_cast<VeriPrimaryExp*>(first)->pri_type()!=veSTR)
                    fail(n,"display requires a constant format string");
                decoded=decode_string(static_cast<VeriPrimaryExp*>(first)->str(),first);
            }
            if(severity)decoded=escape_format_text("DSIM "+fn.substr(1)+": "+scope->path+":"+std::to_string(n->line())+": ")+decoded;
            // %m consumes no argument; hierarchy is fixed during elaboration.
            for(size_t i=0;i<decoded.size();++i)if(decoded[i]=='%') {
                if(++i>=decoded.size())break;
                if(decoded[i]=='m'||decoded[i]=='M') {
                    auto hierarchy=escape_format_text(scope->path);
                    decoded.replace(i-1,2,hierarchy);
                    i=i-1+hierarchy.size();
                    if(i) --i;
                }
            }
            size_t spec=0;
            for(size_t i=0;i<decoded.size();++i) if(decoded[i]=='%') {
                if(++i>=decoded.size()) fail(n,"incomplete format");
                if(decoded[i]=='%') continue;
                while(i<decoded.size() && decoded[i]>='0' && decoded[i]<='9') ++i;
                if(i<decoded.size()&&decoded[i]=='.'){++i;while(i<decoded.size()&&decoded[i]>='0'&&decoded[i]<='9')++i;}
                if(i>=decoded.size() || std::string("bdhxotscfFeEgG").find(decoded[i])==std::string::npos) fail(n,"supported formats: %b %d %h %x %o %t %s %c %f %e %g with numeric widths/real precision");
                if(std::string("fFeEgG").find(decoded[i])!=std::string::npos)needs_real=true;
                ++spec;
            }
            if(spec!=args.size()) fail(n,"format/argument count mismatch");
            std::vector<char> formats;
            for(size_t i=0;i<decoded.size();++i)if(decoded[i]=='%'){++i;if(decoded[i]=='%')continue;while(decoded[i]>='0'&&decoded[i]<='9')++i;if(decoded[i]=='.'){++i;while(decoded[i]>='0'&&decoded[i]<='9')++i;}formats.push_back(decoded[i]);}
            std::string vals="{",signs="{";bool signed_args=false;size_t argument_index=0;
            for(auto* a:args){auto e=expr(a);if(e->interface_namespace)fail(a,"interface namespace cannot be displayed as an integral value");if(formats.at(argument_index)!='s'&&e->packed_value)e=e->packed_value;if(e->text_value&&formats.at(argument_index)!='s')fail(a,"string display values require %s");++argument_index;read(p,e);vals+=emit(e)+",";signs+=(e->signed_value?"true,":"false,");signed_args|=e->signed_value;}
            add(p,"s.print("+quote(decoded)+","+vals+"},"+(fn!="$write"?"true":"false")+","+std::to_string(scope->time.unit_fs)+"ULL"+(signed_args?","+signs+"}":"")+");");
            if(fn=="$fatal")add(p,"throw std::runtime_error(\"$fatal terminated simulation\");");
            return;
        }
        default:fail(n,"unsupported statement kind "+std::to_string(n->detail_type()));
        }
    }
    void check_strength(VeriNode* owner,VeriNode* drive) {
        if(drive) {
            auto* d=static_cast<VeriDriveExp*>(drive);
            if(d->drive_from()!=DEFAULT_DRIVE_FROM || d->drive_to()!=DEFAULT_DRIVE_TO)
                fail(owner,"only strong drive strengths are supported yet");
        }
    }
    struct InstanceShape {
        std::string base;
        int first=0,step=1,count=1;
        bool array=false;
        std::string label(int ordinal) const {
            return base+(array?"["+std::to_string(int64_t(first)+int64_t(step)*ordinal)+"]":"");
        }
    };
    InstanceShape instance_shape(VeriNode* owner,VeriNode* instance_name) {
        InstanceShape shape;
        if(!instance_name)return shape; // unnamed primitive
        shape.base=name(instance_name);
        if(instance_name->detail_type()==veEXP_PRI)return shape;
        if(instance_name->detail_type()!=veEXP_ARRAY)fail(owner,"invalid instance name");
        auto& ranges=static_cast<VeriArrayExp*>(instance_name)->range();
        if(ranges.size()!=1)fail(owner,"instance arrays require one fixed range");
        auto* range=static_cast<VeriRangeExp*>(ranges.front());
        if(range->rtype()!=vrSEMI||!range->right())fail(owner,"instance arrays require two constant bounds");
        auto bound=[&](VeriNode* exp) {
            if(!veri_elaboration_constant(exp))fail(exp,"instance array bounds must be constant");
            auto value=veri_constant_value(static_cast<VeriExp*>(exp),0);
            if(!value||value->no_xz()!=IS_TRUE)fail(exp,"instance array bound is unknown");
            const bool sign=value->is_signed()==IS_TRUE;
            const int high=sign?value->get_certain_bit(std::min(31,value->bits()-1)):V0;
            if(!sign&&value->bits()>31&&value->get_certain_bit(31)!=V0)
                fail(exp,"instance array bound exceeds signed 32-bit range");
            for(int bit=32;bit<value->bits();++bit)if(value->get_certain_bit(bit)!=high)
                fail(exp,"instance array bound exceeds signed 32-bit range");
            int64_t result=0;const int bits=std::min(32,value->bits());
            for(int bit=0;bit<bits;++bit)if(value->get_certain_bit(bit)==V1)result|=int64_t(1)<<bit;
            if(sign&&value->get_certain_bit(bits-1)==V1)result-=int64_t(1)<<bits;
            return int(result);
        };
        shape.first=bound(range->left());const int last=bound(range->right());
        const int64_t count=std::abs(int64_t(shape.first)-last)+1;
        if(count>65536)fail(owner,"instance array exceeds 65536 instances");
        shape.array=true;shape.step=shape.first<=last?1:-1;shape.count=int(count);
        return shape;
    }
    LValueIR lvalue_slice(const LValueIR& value,int low,int width,VeriNode* owner) {
        if(low<0||width<1||low>value.width-width)fail(owner,"invalid instance port slice");
        LValueIR result;result.width=width;
        for(auto part:value.parts) {
            const int begin=std::max(low,part.rhs_lo),end=std::min(low+width,part.rhs_lo+part.width);
            if(begin>=end)continue;
            if(part.index||part.word_index)fail(owner,"variable selects in instance array output connections are not supported yet");
            part.lo+=begin-part.rhs_lo;part.width=end-begin;part.rhs_lo=begin-low;
            result.parts.push_back(part);
        }
        return result;
    }
    E value_slice(E value,int low,int width) {
        auto result=node("slice",width,{value});result->literal=std::to_string(low)+","+std::to_string(width);
        return result;
    }
    int instance_port_offset(int actual_width,int port_width,int count,int ordinal,VeriNode* owner) {
        if(actual_width==port_width)return 0; // one port value broadcasts to every instance
        if(int64_t(actual_width)!=int64_t(port_width)*count)
            fail(owner,"instance array connection width must equal one port or all instance ports");
        // Leftmost declared instance receives the most significant part.
        return (count-1-ordinal)*port_width;
    }
    void gate(VeriGateInstantiation* g) {
        if(g->gate_list().empty()) fail(g,"empty gate instance list");
        check_strength(g,g->drive_strength());
        std::string op; bool invert=false,tristate=false,enable_low=false;
        switch(g->gate_type()) {
        case vpAND:op="&";break;case vpNAND:op="&";invert=true;break;
        case vpOR:op="|";break;case vpNOR:op="|";invert=true;break;
        case vpXOR:op="^";break;case vpXNOR:op="^";invert=true;break;
        case vpBUF:break;case vpNOT:invert=true;break;
        case vpBUFFIF0:tristate=true;enable_low=true;break;
        case vpBUFFIF1:tristate=true;break;
        case vpNOTIF0:tristate=true;enable_low=true;invert=true;break;
        case vpNOTIF1:tristate=true;invert=true;break;
        default:fail(g,"unsupported gate primitive");
        }
        if(!tristate&&g->delay()&&static_cast<VeriDelayExp*>(g->delay())->delay3())
            fail(g,"logic gate primitives accept at most two delay values");
        for(auto* inst:g->gate_list()) {
            auto shape=instance_shape(inst,static_cast<VeriGateInstance*>(inst)->inst_name());
            auto* a=static_cast<VeriGateInstance*>(inst)->arg();
            if(!a || a->detail_type()!=veEXP_MULTI) fail(inst,"invalid gate arguments");
            auto list=static_cast<VeriMultiExp*>(a)->exp();
            if(list.size()<2 || (op.empty() && list.size()!=(tristate?3u:2u))) fail(inst,"unsupported gate port count");
            auto* lhs=list.front();list.pop_front();
            const auto whole_target=lvalue(lhs);
            if(!shape.array&&whole_target.width!=1)fail(lhs,"only scalar gate primitives are supported yet");
            for(int ordinal=0;ordinal<shape.count;++ordinal) {
                auto target=whole_target;
                if(shape.array)target=lvalue_slice(target,instance_port_offset(target.width,1,shape.count,ordinal,lhs),1,lhs);
                auto input_value=[&](VeriNode* input,bool enable=false) {
                    auto value=expr(input);
                    if(shape.array) {
                        if(!value->event_safe||value->selection_checks||value->procedural_only)
                            fail(input,"instance array terminal expressions must have no persistent side effects");
                        int offset=instance_port_offset(value->width,1,shape.count,ordinal,input);
                        if(value->width!=1)value=value_slice(value,offset,1);
                    } else if(value->width!=1)fail(input,enable?"gate enable must be scalar":"gate inputs must be scalar");
                    return value;
                };
                E control;
                if(tristate) {
                    control=input_value(list.back(),true);
                    if(enable_low)control=node("~",1,{control});
                }
                E e;auto last=list.end();if(tristate)--last;
                for(auto it=list.begin();it!=last;++it) {auto value=input_value(*it);e=e?node(op,1,{e,value}):value;}
                if(op.empty()) {
                    auto zero=node("literal",1);zero->literal="V(0)";
                    e=node("|",1,{e,zero}); // buf converts Z input to X.
                }
                if(invert)e=node("~",1,{e});
                if(tristate)e=node("mux",1,{control,e,node("fillz",1)});
                continuous(lhs,e,g->delay(),shape.array?&target:nullptr);
            }
        }
    }
    std::vector<VeriVar*> ports(VeriMod* m) {
        std::vector<VeriVar*> result;
        auto append=[&](VeriNode* n) {
            if(n->detail_type()==veEXP_ASSIGN) n=static_cast<VeriAssignExp*>(n)->lval();
            auto* v=m->scope()->value_same_level(name(n));
            if(!v || v->tok_type()!=vtVAR) fail(n,"unsupported module port declaration");
            result.push_back(static_cast<VeriVar*>(v));
        };
        if(!m->port()) return result;
        if(m->port()->detail_type()==vsDECL_PORT_DECL_LIST) {
            for(auto* d:static_cast<VeriPortDeclList*>(m->port())->port_list()) {
                if(d->detail_type()!=vsDECL_VAR) fail(d,"unsupported module port declaration");
                for(auto* v:static_cast<VeriVarDecl*>(d)->vars()) append(v);
            }
        } else if(m->port()->detail_type()==veEXP_MULTI) {
            for(auto* v:static_cast<VeriMultiExp*>(m->port())->exp()) append(v);
        } else fail(m->port(),"unsupported module port list");
        return result;
    }
    Scope* collect(VeriMod* m,const std::string& path,std::vector<std::string> wave_path={},bool defer_contents=false) {
        if(wave_path.empty())wave_path.push_back(m->name());
        auto created=std::make_unique<Scope>();created->mod=m;created->path=path;created->wave_path=std::move(wave_path);
        created->time={m->time_scale().unit_fs,m->time_scale().precision_fs};
        scopes.push_back(std::move(created));
        if(gate_design&&m->line()<=int(prefix_lines)&&m->name()==GateDesign::rtl_identifier(gate_design->top))
            scopes.back()->time=gate_design->top_time;
        Scope* current=scopes.back().get(); scope=current;
        declarations(m->port());
        auto* items=static_cast<VeriModuleItemList*>(m->item());
        append_items(current,items);
        if(!defer_contents)collect_contents(current);
        return current;
    }
    Scope* generated_scope(Scope* owner,const std::string& label) {
        auto path=owner->wave_path;path.push_back(label);
        if(!owner->child_names.insert(label).second)fail(owner->mod,"duplicate generate scope "+label);
        auto sc=std::make_unique<Scope>();sc->mod=owner->mod;sc->path=owner->path+"."+label;
        sc->wave_path=std::move(path);sc->time=owner->time;sc->parent=owner;sc->generated=true;sc->subroutine=owner->subroutine;sc->automatic_storage=owner->automatic_storage;
        sc->constructor_class=owner->constructor_class;
        sc->static_domain=owner->static_domain;
        if(!owner->static_wave_path.empty()){sc->static_wave_path=owner->static_wave_path;sc->static_wave_path.push_back(label);}
        auto* result=sc.get();scopes.push_back(std::move(sc));return result;
    }
    void append_items(Scope* owner,VeriNode* n) {
        if(!n)return;
        if(n->detail_type()==vsINST_GEN_ITEM_LIST) {
            for(auto* item:static_cast<VeriGenItemList*>(n)->item_list())append_items(owner,item);
        } else if(n->detail_type()==vsSTMT_MOD_ITEM_LIST) {
            for(auto* item:static_cast<VeriModuleItemList*>(n)->item_list())append_items(owner,item);
        } else owner->items.push_back(n);
    }
    void collect_generate(Scope* owner,VeriNode* n,int& ordinal) {
        const auto kind=n->detail_type();
        if(kind==vsINST_GEN_ITEM_LIST) {
            for(auto* item:static_cast<VeriGenItemList*>(n)->item_list())collect_generate(owner,item,ordinal);
            return;
        }
        if(kind==vsINST_DUMMY || kind==vsDECL_GENVAR)return;
        if(kind==vsINST_GEN_COND || kind==vsINST_GEN_CASE || kind==vsINST_GEN_BLOCK || kind==vsINST_GEN_LOOP) {
            const auto implicit="genblk"+std::to_string(++ordinal);
            if(kind==vsINST_GEN_LOOP) {
                auto* loop=static_cast<VeriGenLoop*>(n);size_t i=0;
                for(auto* body:loop->generated_content()) {
                    const auto label=(loop->label().empty()?implicit:loop->label())+"["+std::to_string(loop->generated_values().at(i++))+"]";
                    auto* child=generated_scope(owner,label);append_items(child,body);collect_contents(child);
                }
            } else {
                VeriNode* body=n;
                // Directly nested conditionals share the outer generate scope
                // (the usual if/else-if/case chain has no extra genblk level).
                while(body && (body->detail_type()==vsINST_GEN_COND || body->detail_type()==vsINST_GEN_CASE)) {
                    body=body->detail_type()==vsINST_GEN_COND?static_cast<VeriGenCond*>(body)->choice():static_cast<VeriGenCase*>(body)->choice();
                }
                if(!body || body->detail_type()==vsINST_DUMMY)return;
                auto label=implicit;
                if(body->detail_type()==vsINST_GEN_BLOCK) {
                    auto* block=static_cast<VeriGenBlock*>(body);
                    if(!block->label().empty())label=block->label();
                    body=block->item_list();
                }
                auto* child=generated_scope(owner,label);append_items(child,body);collect_contents(child);
            }
            return;
        }
        owner->items.push_back(n);
    }
    void collect_contents(Scope* current) {
        // First expand only selected branches, then register declarations before
        // lowering any expression or collecting connected child modules.
        auto original=std::move(current->items);current->items.clear();int ordinal=0;
        for(auto* n:original)collect_generate(current,n,ordinal);
        scope=current;
        for(auto* n:current->items)declarations(n);
        for(auto* n:current->items) if(n->detail_type()==vsINST_MOD_INSTANTIATION) {
            auto* group=static_cast<VeriModInstantiation*>(n);
            for(auto* entry:group->mod_list()) {
                auto* inst=static_cast<VeriModInstance*>(entry);
                if(!inst->inst_name())fail(inst,"module instance requires a name");
                auto shape=instance_shape(inst,inst->inst_name());
                if(!inst->hive()) fail(inst,"unresolved module "+group->mod_name());
                for(int ordinal=0;ordinal<shape.count;++ordinal) {
                    const auto label=shape.label(ordinal);
                    auto child_path=current->wave_path;child_path.push_back(label);
                    auto* child=collect(static_cast<VeriMod*>(inst->hive()),current->path+"."+label,std::move(child_path));
                    auto formal=ports(child->mod);
                    std::vector<VeriNode*> actual(formal.size(),nullptr);
                    std::vector<bool> connected(formal.size(),false);
                    if(inst->arg()) {
                        if(inst->arg()->detail_type()!=veEXP_MULTI) fail(inst,"unsupported port argument list");
                        size_t pos=0;bool named_seen=false,positional_seen=false;
                        for(auto* a:static_cast<VeriMultiExp*>(inst->arg())->exp()) {
                            if(a->detail_type()==veEXP_NAMED_PARAM) {
                                if(positional_seen)fail(a,"module connections cannot mix positional and named ports");
                                named_seen=true;
                                auto* named=static_cast<VeriNamedParamExp*>(a);
                                auto it=std::find_if(formal.begin(),formal.end(),[&](VeriVar* v){return v->name()==named->ref();});
                                if(it==formal.end()) fail(a,"unknown port "+named->ref());
                                if(connected[it-formal.begin()])fail(a,"duplicate module port "+named->ref());
                                auto* value=named->port_exp();
                                if(value && value->detail_type()==veEXP_MULTI && static_cast<VeriMultiExp*>(value)->multi_type()==vemCOMMA_EXP) {
                                    auto& list=static_cast<VeriMultiExp*>(value)->exp();
                                    if(list.size()!=1) fail(value,"named port requires one expression");
                                    value=list.front();
                                }
                                actual[it-formal.begin()]=value; connected[it-formal.begin()]=true;
                            } else {
                                if(named_seen)fail(a,"module connections cannot mix positional and named ports");
                                positional_seen=true;
                                if(pos>=formal.size()) fail(a,"too many positional ports");
                                connected[pos]=true; actual[pos++]=a;
                            }
                        }
                    }
                    for(size_t i=0;i<formal.size();++i) {
                        if(formal[i]->interface_port()) {
                            if(shape.array)fail(inst,"interface ports in module instance arrays are not supported yet");
                            if(!formal[i]->interface_instance())fail(inst,"unbound interface port");
                            continue;
                        }
                        if(shape.array&&formal[i]->range_depth())fail(inst,"unpacked ports in module instance arrays are not supported yet");
                        Binding binding{current,child,formal[i],actual[i],false,!connected[i],false,{},{}};
                        binding.instance_count=shape.count;binding.instance_ordinal=ordinal;binding.instance_array=shape.array;
                        bindings.push_back(std::move(binding));
                    }
                }
            }
        }
        scope=current;
    }
    void collapse_ports() {
        // Collapse equal-width whole nets before lowering expressions and sensitivities.
        // A pair of reciprocal continuous drivers would incorrectly retain old values.
        std::vector<int> parent(signals.size());
        for(size_t i=0;i<parent.size();++i) parent[i]=int(i);
        auto root=[&](int id) { while(parent[id]!=id) {parent[id]=parent[parent[id]]; id=parent[id];} return id; };
        for(auto& b:bindings) {
            if(b.port->range_depth()) {
                for(const auto& element:b.array_elements) {
                    int child=element.first,outer=element.second;
                    if(signals[child].net&&signals[outer].net) {
                        parent[root(child)]=root(outer);b.collapsed=true;
                    }
                }
                continue;
            }
            int child=b.child->ids.at(b.port->name());
            if(!b.actual || b.actual->detail_type()!=veEXP_PRI) continue;
            scope=b.parent;
            auto* p=static_cast<VeriPrimaryExp*>(b.actual);
            if(!p->var() || p->var()->tok_type()!=vtVAR) continue;
            int outer=signal(b.actual);
            if(b.instance_array)instance_port_offset(signals[outer].width,signals[child].width,b.instance_count,b.instance_ordinal,b.actual);
            if(signals[child].net && signals[outer].net && signals[child].width==signals[outer].width) {
                parent[root(child)]=root(outer); b.collapsed=true;
            }
        }
        std::vector<SignalIR> compact; std::map<int,int> canonical;
        for(auto& sc:scopes) for(auto& pair:sc->ids) {
            int original=pair.second, r=root(original);
            auto inserted=canonical.emplace(r,int(compact.size()));
            if(inserted.second) compact.push_back(signals[r]);
            pair.second=inserted.first->second;
        }
        std::set<int> dynamic_storage;
        if(objects_signal>=0) {
            auto entry=canonical.emplace(root(objects_signal),int(compact.size()));if(entry.second)compact.push_back(signals[root(objects_signal)]);objects_signal=entry.first->second;
        }
        std::map<int,int> object_storage;
        for(auto [id,type]:object_signals)object_storage.emplace(canonical.at(root(id)),type);
        object_signals=std::move(object_storage);
        std::set<int> constant_storage;
        for(int id:const_property_signals)constant_storage.insert(canonical.at(root(id)));
        const_property_signals=std::move(constant_storage);
        std::set<int> string_elements;
        for(int id:string_element_signals)string_elements.insert(canonical.at(root(id)));
        string_element_signals=std::move(string_elements);
        for(int id:dynamic_signals)dynamic_storage.insert(canonical.at(root(id)));
        dynamic_signals=std::move(dynamic_storage);
        std::set<int> associative_storage;
        for(int id:associative_signals)associative_storage.insert(canonical.at(root(id)));
        associative_signals=std::move(associative_storage);
        std::set<int> string_associative_storage;
        for(int id:string_associative_signals)string_associative_storage.insert(canonical.at(root(id)));
        string_associative_signals=std::move(string_associative_storage);
        std::set<int> unsigned_associative_storage;
        for(int id:unsigned_associative_signals)unsigned_associative_storage.insert(canonical.at(root(id)));
        unsigned_associative_signals=std::move(unsigned_associative_storage);
        std::set<int> class_associative_storage;
        for(int id:class_associative_signals)class_associative_storage.insert(canonical.at(root(id)));
        class_associative_signals=std::move(class_associative_storage);
        std::map<int,int> queue_storage;
        for(auto [id,bound]:queue_bounds)queue_storage.emplace(canonical.at(root(id)),bound);
        queue_bounds=std::move(queue_storage);
        for(auto& entry:static_variables)entry.second=canonical.at(root(entry.second));
        std::map<int,std::vector<std::string>> static_paths;
        for(const auto& entry:static_wave_paths)static_paths.emplace(canonical.at(root(entry.first)),entry.second);
        static_wave_paths=std::move(static_paths);
        // Declaration-time aggregate metadata uses the same physical IDs as
        // memories after port collapsing and deterministic signal ordering.
        for(auto* metadata:{&aggregate_defaults,&aggregate_state_masks}) {
            std::map<int,E> reordered;
            for(const auto& entry:*metadata)reordered.emplace(canonical.at(root(entry.first)),entry.second);
            *metadata=std::move(reordered);
        }
        {decltype(container_aggregate_types) reordered;for(const auto& entry:container_aggregate_types)reordered.emplace(canonical.at(root(entry.first)),entry.second);container_aggregate_types=std::move(reordered);}
        for(auto& memory:memories)for(auto& id:memory.words)id=canonical.at(root(id));
        for(auto& b:bindings)for(auto& element:b.array_elements) {
            element.first=canonical.at(root(element.first));
            element.second=canonical.at(root(element.second));
        }
        {std::set<int> reordered;for(int id:struct_string_signals)reordered.insert(canonical.at(root(id)));struct_string_signals=std::move(reordered);}
        signals=std::move(compact);
    }
    E signal_expr(int id) {
        E e=node("signal",signals[id].width); e->signal=id; e->reads.insert(id);e->direct_reads.insert(id);e->text_value=signals[id].text_value;e->real_width=signals[id].real_width;if(object_signals.count(id))e->object_type=object_signals.at(id); return e;
    }
    void port_driver(int id,E value,bool after_waiters=false) {
        if(value->interface_type)fail(nullptr,"unsupported primary: interface namespace or virtual handle requires a typed interface connection");
        value=numeric_context(value,signals[id].real_width,signals[id].width);
        if(value->packed_value)value=value->packed_value;
        if(value->text_value||signals[id].text_value)fail(nullptr,"string cannot be used as an integral port connection");
        if(value->procedural_only)throw std::runtime_error("output/inout function requires a procedural expression");
        ProcessIR p; p.startup_adapter=after_waiters; int pidx=int(processes.size()); read(p,value); p.touches.insert(id);
        PartIR target{id,0,signals[id].width,0};target.continuous=true;p.writes.push_back(target);
        p.continuous_wait=int(wait_sites.size());add(p,wait_code(pidx,p.reads));
        std::string args=sid(id)+",";
        if(signals[id].net) args+=std::to_string(driver++)+",";
        add(p,std::string(signals[id].net?"s.drive(":"s.set(")+args+emit(value,signals[id].width)+");");
        if(signals[id].net) {
            p.instructions.back().net_target=id;p.instructions.back().net_value=value;
        }
        add(p,"pc=0; return;"); processes.push_back(std::move(p));
    }
    void port_driver(const LValueIR& target,E value) {
        if(value->procedural_only)throw std::runtime_error("output/inout function requires a procedural expression");
        ProcessIR p; int pidx=int(processes.size());
        continuous_write(p,target,value);
        p.continuous_wait=int(wait_sites.size());
        Instruction wait;wait.code=wait_code(pidx,p.reads);
        p.instructions.insert(p.instructions.begin(),std::move(wait));
        add(p,"pc=0; return;"); processes.push_back(std::move(p));
    }
    void open_input(Scope* child,VeriVar* port,bool use_default) {
        scope=child; int id=child->ids.at(port->name());
        auto fallback=child->defaults.find(port->name());
        if(use_default && fallback!=child->defaults.end()) {
            if(veri_streaming(fallback->second))fail(fallback->second,"direct streaming module port defaults are not supported yet");
            auto value=expr(fallback->second);
            if(!value->reads.empty()) fail(fallback->second,"default input port value must be constant");
            port_driver(id,value);
        } else if(!signals[id].net) {
            E z=node("literal",signals[id].width);
            z->literal="V(0,mask("+std::to_string(z->width)+"),"+std::to_string(z->width)+")";
            initializers.push_back({id,z,{}});
        }
    }
    void prepare_array_port(Binding& b) {
        const auto& formal=memories.at(b.child->memories.at(b.port->name()));
        const auto direction=b.port->inout();
        if(direction!=vpIN&&direction!=vpOUT&&direction!=vpINOUT)fail(b.port,"unsupported array port direction");
        // Open arrays retain their element defaults: nets Z, variables X or 0.
        if(!b.actual)return;
        scope=b.parent;
        auto* base=b.actual;
        std::vector<VeriNode*> prefix;
        if(base->detail_type()==veEXP_ARRAY) {
            auto* array=static_cast<VeriArrayExp*>(base);base=array->id();
            for(auto* select:array->range()) {
                auto* range=static_cast<VeriRangeExp*>(select);
                if(range->rtype()!=vrSINGLE)fail(b.actual,"array port slices are not supported yet");
                prefix.push_back(range->left());
            }
        }
        if(base->detail_type()!=veEXP_PRI||!variable(static_cast<VeriPrimaryExp*>(base)->var()))
            fail(b.actual,"array port requires a static variable array or subarray");
        Variable actual{static_cast<VeriPrimaryExp*>(base)->var()};
        if(actual->range_depth()<=int(prefix.size()))fail(b.actual,"array port requires remaining unpacked dimensions");
        const auto& source=memories.at(variable_scope(base,actual)->memories.at(actual->name()));
        if(source.fixed_count||formal.fixed_count)fail(b.actual,"compact large memories cannot be connected to unpacked array ports yet");
        if(source.dimensions.size()-prefix.size()!=formal.dimensions.size())fail(b.actual,"array port rank mismatch");
        if(actual.dlen()!=b.port->dlen())fail(b.actual,"array port element width mismatch");
        if(enum_identity(actual.node)||enum_identity(b.port)||veri_aggregate_type(actual.node)||veri_aggregate_type(b.port))
            fail(b.actual,"enum and aggregate array port types are not supported yet");
        if(direction==vpINOUT&&!(actual->net_type()==vvWIRE||actual->net_type()==vvTRI))
            fail(b.actual,"inout array port requires net array actual");
        size_t offset=0;
        for(size_t d=0;d<prefix.size();++d) {
            auto* index=prefix[d];E value;
            if(!elaboration_expression(index))fail(index,"array port subarray indices must be constant and in range");
            if(index->tok_type()==vtEXP&&elaboration_expression(index)&&static_cast<VeriExp*>(index)->calc_value())value=number(static_cast<VeriExp*>(index)->calc_value());
            else value=expr(index);
            if(value->op!="literal"||value->unknown||value->host_overflow||value->negative)
                fail(index,"array port subarray indices must be constant and in range");
            const auto& dim=source.dimensions[d];
            if(value->value<uint64_t(dim.base)||value->value-uint64_t(dim.base)>=uint64_t(dim.count))
                fail(index,"array port subarray indices must be constant and in range");
            offset+=size_t(value->value-uint64_t(dim.base))*size_t(dim.stride);
        }
        for(size_t d=0;d<formal.dimensions.size();++d)
            if(formal.dimensions[d].count!=source.dimensions[d+prefix.size()].count)
                fail(b.actual,"array port dimension size mismatch");
        // Memory storage uses ascending numerical indices; port assignment uses
        // left-to-right declaration order independently at each dimension.
        for(size_t ordinal=0;ordinal<formal.words.size();++ordinal) {
            size_t child_offset=0,parent_offset=offset;
            for(size_t d=0;d<formal.dimensions.size();++d) {
                const auto& f=formal.dimensions[d];const auto& a=source.dimensions[d+prefix.size()];
                const auto element=(ordinal/size_t(f.stride))%size_t(f.count);
                child_offset+=(f.descending?size_t(f.count)-1-element:element)*size_t(f.stride);
                parent_offset+=(a.descending?size_t(a.count)-1-element:element)*size_t(a.stride);
            }
            const int child=formal.words.at(child_offset),parent=source.words.at(parent_offset);
            b.array_elements.push_back({child,parent});
        }
    }
    void connect_array_port(Binding& b) {
        auto* base=b.actual;
        if(base&&base->detail_type()==veEXP_ARRAY)base=static_cast<VeriArrayExp*>(base)->id();
        for(const auto& element:b.array_elements) {
            const int child=element.first,parent=element.second;
            if(b.port->inout()==vpIN) {
                Variable actual{static_cast<VeriPrimaryExp*>(base)->var()};
                auto value=signal_expr(parent);value->signed_value=actual.is_signed()==IS_TRUE;
                port_driver(child,value,veri_integral_atom(b.port->net_type())||veri_two_state(b.port->net_type()));
            } else if(b.port->inout()==vpOUT) {
                auto value=signal_expr(child);value->signed_value=b.port->is_signed()==IS_TRUE;
                LValueIR target;target.width=signals[parent].width;target.parts.push_back({parent,0,target.width,0});
                port_driver(target,value);
            } else fail(b.actual,"inout array port requires collapsed net elements");
        }
    }
    void connect_ports() {
        for(auto& b:bindings) {
            if(b.collapsed) continue;
            if(b.port->range_depth()){connect_array_port(b);continue;}
            scope=b.parent; int id=b.child->ids.at(b.port->name());
            if(veri_streaming(b.actual))fail(b.actual,"direct streaming module connections are not supported yet; capture into a packed temporary first");
            E input;int offset=0;
            if(b.actual&&b.instance_array) {
                input=expr(b.actual);
                if(!input->event_safe||input->selection_checks||input->procedural_only)
                    fail(b.actual,"instance array port expressions must have no persistent side effects");
                offset=instance_port_offset(input->width,signals[id].width,b.instance_count,b.instance_ordinal,b.actual);
            }
            auto actual_target=[&]() {
                auto target=lvalue(b.actual);
                return b.instance_array?lvalue_slice(target,offset,signals[id].width,b.actual):target;
            };
            if(b.actual && signals[id].net && lvalue_shape(b.actual)) {
                auto actual=lvalue(b.actual);
                bool variable=std::any_of(actual.parts.begin(),actual.parts.end(),[](const PartIR& part){return bool(part.index)||bool(part.word_index);});
                if(variable&&b.port->inout()!=vpIN)fail(b.actual,"variable selects in output/inout module port connections are not supported yet");
                if(!variable) {actual=actual_target();b.parts=actual.parts;}
                // Output concatenations are directional port adapters in VCS.
                // Input/inout nets preserve electrical connectivity, including
                // internally driven input ports coerced to inout by VCS.
                bool direct=b.actual->detail_type()!=veEXP_MULTI || b.port->inout()!=vpOUT;
                if(!variable && direct && net_target(actual) && actual.width==signals[id].width) {
                    for(auto part:actual.parts) for(int bit=0;bit<part.width;++bit)
                        bit_links.push_back({id,part.rhs_lo+bit,part.signal,part.lo+bit});
                    b.bit_connected=true; continue;
                }
            }
            if(b.port->inout()==vpIN) {
                if(b.actual) {
                    auto value=input?input:expr(b.actual);
                    if(b.instance_array&&value->width!=signals[id].width)value=value_slice(value,offset,signals[id].width);
                    port_driver(id,value,veri_integral_atom(b.port->net_type())||veri_two_state(b.port->net_type()));
                }
                else open_input(b.child,b.port,b.omitted);
            } else if(b.port->inout()==vpOUT) {
                if(!b.actual) continue;
                auto target=actual_target(); b.parts=target.parts;
                for(auto part:target.parts)if(part.index||part.word_index)fail(b.actual,"variable selects in module port connections are not supported yet");
                auto value=signal_expr(id);value->signed_value=b.port->is_signed()==IS_TRUE;port_driver(target,value);
            } else if(b.port->inout()==vpINOUT) {
                if(b.actual) fail(b.actual,"inout port requires equal-width net lvalues");
            } else fail(b.port,"unsupported port direction");
        }
    }
    void lower_scope() {
        auto* mod=scope->mod;
        if(gate_design && !scope->generated && mod->name()==GateDesign::rtl_identifier(gate_design->top)) {
            std::string bits="{";
            for(const auto& port:gate_design->ports) {
                int signal=scope->ids.at(GateDesign::rtl_identifier(port.name));
                for(int bit=int(port.nets.size())-1;bit>=0;--bit) {
                    if(bits.size()>1) bits+=",";
                    bits+="{"+sid(signal)+","+std::to_string(bit)+"}";
                }
            }
            if(gate_design->pin_nets.size()+1>size_t(std::numeric_limits<int>::max()-driver))
                throw std::runtime_error("gate driver ID overflow");
            std::string wave_args;
            if(wave_enabled) {wave_args=",wave,{";for(const auto& p:scope->wave_path)wave_args+=quote(p)+",";wave_args+="}";}
            gate_calls.push_back("install_gate(s,"+bits+"},"+std::to_string(driver)+wave_args+");\n");
            gate_touches.emplace_back();for(const auto& item:scope->ids)gate_touches.back().insert(item.second);
            gate_scopes.push_back(scope->path);
            driver+=int(gate_design->pin_nets.size()+1);
            return;
        }
        if(!scope->generated && mod->port() && mod->port()->detail_type()==vsDECL_PORT_DECL_LIST)
            for(auto* n:static_cast<VeriPortDeclList*>(mod->port())->port_list()) decl_init(n);
        for(auto* n:scope->items) decl_init(n);
        property_definitions.clear();
        for(auto* n:scope->items)if(n->detail_type()==vsSTMT_ALWAYS) {
            auto* body=static_cast<VeriAlwaysStmt*>(n)->stmt();auto* spec=property_body(body);
            if(spec&&spec->assertion_kind()==7) {
                if(mod->is_package())fail(spec,"package properties are not supported");
                if(veri_sequence_definition(spec->scope()->value_same_level(spec->property_name())))fail(spec,"property conflicts with a sequence: "+spec->property_name());
                if(scope->symbols.count(spec->property_name()))fail(spec,"property conflicts with a local declaration: "+spec->property_name());
                if(spec->property_delay()<0)fail(spec,"property aliases are not supported");
                if(!property_definitions.emplace(spec->property_name(),body).second)fail(spec,"duplicate property: "+spec->property_name());
            }
        }

        for(auto* n:scope->items) {
            switch(n->detail_type()) {
            case vsSTMT_SEQ_BLOCK:if(!static_cast<VeriSeqBlock*>(n)->class_declaration())fail(n,"unsupported module block");break;
            case vsSTMT_DUMMY:if(!mod->is_interface())fail(n,"unsupported dummy module item");break;
            case vsDECL_CLOCKING:case vsDECL_DEFAULT_CLOCKING:break;
            case vsDECL_TIME:case vsDECL_IMPORT:case vsDECL_EXPORT:case vsDECL_FUNC_DECL:case vsDECL_TASK_DECL:case vsDECL_VAR:case vsDECL_INT:case vsDECL_PARAM:case vsINST_MOD_INSTANTIATION:break;
            case vsSTMT_INIT:case vsSTMT_ALWAYS: {
                if(n->detail_type()==vsSTMT_ALWAYS&&lower_property(static_cast<VeriAlwaysStmt*>(n)->stmt()))break;
                ProcessIR p; int id=int(processes.size());processes.emplace_back(); bool always=n->detail_type()==vsSTMT_ALWAYS;
                auto* body=always?static_cast<VeriAlwaysStmt*>(n)->stmt():static_cast<VeriInitStmt*>(n)->stmt();
                p.final_process=!always&&static_cast<VeriInitStmt*>(n)->final_process();
                needs_final|=p.final_process;
                p.source_line=n->line();p.always_process=always;
                if(always)p.always_kind=static_cast<VeriAlwaysStmt*>(n)->always_kind();
                if(p.always_kind==akALWAYS_FF) {
                    if(body->detail_type()!=vsSTMT_PROC_TIME_CONTROL)
                        fail(n,"always_ff requires a leading explicit event control");
                    p.startup_wait=int(wait_sites.size());
                    auto* control=static_cast<VeriProcTimeContStmt*>(body)->control();
                    if(control->detail_type()!=vsSTMT_EVENT||static_cast<VeriEventStmt*>(control)->is_all()==IS_TRUE)
                        fail(n,"always_ff requires a leading explicit event control");
                }
                const auto sample_clock=always?procedural_sample_clock(body):std::make_pair(-1,0);
                if(sample_clock.first>=0) {
                    sampling_property=int(properties.size());sampling_context=4;lowering_samples.clear();
                }
                lowering_final=p.final_process;statement(p,body,id);lowering_final=false;
                if(sample_clock.first>=0) {
                    if(!lowering_samples.empty()) {
                        auto one=node("literal",1),zero=node("literal",1);one->literal="V(1)";zero->literal="V(0)";
                        properties.push_back({id,sample_clock.first,sample_clock.second,0,0,one,one,zero,std::move(lowering_samples),{}});
                        p.reads.insert(sample_clock.first);
                        for(const auto& sample:properties.back().samples){read(p,sample.value);read(p,sample.gate);}
                    }
                    sampling_property=-1;sampling_context=0;
                }
                if(p.always_kind==akALWAYS_COMB||p.always_kind==akALWAYS_LATCH) {
                    specialized_sensitivity(p,id,n);
                } else add(p,always?"pc=0; continue;":"return;");
                processes[size_t(id)]=std::move(p); break;
            }
            case vsSTMT_CONT_ASSIGN: {
                auto* a=static_cast<VeriContAssignStmt*>(n);
                check_strength(n,a->drive_strength());
                std::vector<VeriNode*> list;
                if(a->exp()->detail_type()==veEXP_MULTI) { for(auto* v:static_cast<VeriMultiExp*>(a->exp())->exp()) list.push_back(v); }
                else list.push_back(a->exp());
                for(auto* v:list) { if(v->detail_type()!=veEXP_ASSIGN) fail(v,"expected continuous assignment"); auto* e=static_cast<VeriAssignExp*>(v); continuous(e->lval(),context_expr(e->rval(),e->lval()),a->delay()); }
                break;
            }
            case vsINST_GATE_INSTANTIATION:gate(static_cast<VeriGateInstantiation*>(n));break;
            default:fail(n,"unsupported module item kind "+std::to_string(n->detail_type()));
            }
        }
    }
    void emit_initializer(std::ostream& out,const DeclarationInit& init) {
        if(init.value)out<<"s.set("<<sid(init.signal)<<","<<emit(init.value,signals[init.signal].width)<<");\n";
        else for(const auto& inst:init.process->instructions)out<<inst.code<<"\n";
    }
    void emit_initializers(std::ostream& out,bool text,size_t part=SIZE_MAX) {
        // Constant storage must be ready when a declaration initializer invokes
        // a constructor/function. Preserve source order among executable inits.
        for(bool constant:{true,false})for(const auto& init:initializers) {
            if(signals[size_t(init.signal)].text_value!=text||(part!=SIZE_MAX&&signal_owner[size_t(init.signal)]!=part))continue;
            const auto& e=init.value;
            const bool pure=e&&e->reads.empty()&&e->writes.empty()&&!e->io_state&&!e->random_state;
            if(pure==constant)emit_initializer(out,init);
        }
    }
    void plan_parallel() {
        PartitionGraph graph;
        for(size_t i=0;i<signals.size();++i)graph.node(0);
        for(const auto& p:processes)graph.node(std::max(size_t(1),p.instructions.size()));
        for(size_t i=0;i<gate_calls.size();++i)graph.node(std::max(size_t(1),gate_design->instances.size()));
        if(!clockings.empty()||!coverages.empty())for(size_t i=1;i<graph.size();++i)graph.edge(0,i,0);
        size_t effect=SIZE_MAX;
        for(size_t i=0;i<processes.size();++i) {
            size_t node=signals.size()+i;
            for(int id:processes[i].touches)graph.edge(node,size_t(id),0);
            if(processes[i].side_effect) {
                if(effect!=SIZE_MAX)graph.edge(effect,node,0);
                effect=node;
            }
        }
        // A function fork belongs to its runtime caller, potentially in any
        // domain. Nonlocal termination also needs a startup/finalization fence.
        // Keep these designs in one kernel until those boundaries span domains.
        if(function_forks_enabled()||needs_termination_unwind||needs_process_lifetime)for(size_t i=1;i<graph.size();++i)graph.edge(0,i,0);
        for(const auto& group:fork_groups)if(group.parent>=0)for(int child:group.children)
            graph.edge(signals.size()+size_t(group.parent),signals.size()+size_t(child),0);
        if(needs_process_control) {
            std::map<int,int> first;for(const auto& target:disable_targets) {
                auto found=first.emplace(target.identity,target.process);
                graph.edge(signals.size()+size_t(found.first->second),signals.size()+size_t(target.process),0);
            }
        }
        // Startup initialization runs inside the owning kernel before processes.
        // Keep every source (including function locals/effects) in that kernel.
        for(const auto& init:initializers) {
            auto connect=[&](const std::set<int>& ids){for(int id:ids)graph.edge(size_t(init.signal),size_t(id),0);};
            if(init.process)connect(init.process->touches);
            if(init.value) {
                connect(init.value->touches);connect(init.value->reads);
                connect(init.value->function_reads);connect(init.value->writes);
            }
        }
        // Startup RNG state and the legacy no-seed stream must have one owner.
        // Keep random initialization in the same partition as RNG processes.
        for(const auto& init:initializers)if((init.value&&(init.value->random_state||init.value->io_state))||(init.process&&(init.process->random_state||init.process->io_state))) {
            if(effect!=SIZE_MAX)graph.edge(effect,size_t(init.signal),0);
            effect=size_t(init.signal);
        }

        for(auto link:bit_links)graph.edge(size_t(link.a),size_t(link.b),0);
        for(size_t i=0;i<gate_calls.size();++i)
            for(int id:gate_touches[i])graph.edge(signals.size()+processes.size()+i,size_t(id),0);
        bool empty=graph.size()==0;if(empty)graph.node();
        parallel_plan=graph.plan(parallel_count);
        if(empty)parallel_plan.owner.clear();
        signal_owner.assign(parallel_plan.owner.begin(),parallel_plan.owner.begin()+signals.size());
        process_owner.assign(parallel_plan.owner.begin()+signals.size(),parallel_plan.owner.begin()+signals.size()+processes.size());
        gate_owner.assign(parallel_plan.owner.begin()+signals.size()+processes.size(),parallel_plan.owner.end());
    }
    void check_specialized_writers() {
        struct Writer {size_t process;PartIR part;};
        std::map<int,std::vector<Writer>> writers;
        for(size_t i=0;i<processes.size();++i)for(auto part:processes[i].writes)
            writers[part.signal].push_back({i,part});
        // Sweep static bit intervals. Keeping the furthest end per continuous
        // process permits repeated targets in one assignment without a quadratic
        // all-pairs scan for generated designs with many independent bit drivers.
        std::set<int> initialized;
        for(const auto& init:initializers) {
            initialized.insert(init.signal);
            if(init.process)for(const auto& part:init.process->writes)initialized.insert(part.signal);
        }
        for(auto& entry:writers) {
            const int id=entry.first;if(signals[id].net)continue;
            auto& list=entry.second;
            if(std::none_of(list.begin(),list.end(),[](const Writer& w){return w.part.continuous;}))continue;
            std::sort(list.begin(),list.end(),[](const Writer& a,const Writer& b){return a.part.lo<b.part.lo;});
            std::map<size_t,int> ends;
            std::set<std::pair<int,size_t>> furthest;
            int procedural_end=-1;
            for(const auto& writer:list) {
                const auto& part=writer.part;const int end=part.lo+part.width;
                auto other=furthest.rbegin();
                if(part.continuous&&other!=furthest.rend()&&other->second==writer.process)++other;
                if((other!=furthest.rend()&&other->first>part.lo)||
                   (part.continuous&&procedural_end>part.lo))
                    throw std::runtime_error("variable port driver conflicts with another writer: "+signals[id].name);
                if(part.continuous) {
                    if(initialized.count(id))throw std::runtime_error("variable port driver conflicts with declaration initialization: "+signals[id].name);
                    auto found=ends.find(writer.process);
                    if(found==ends.end()) {ends.emplace(writer.process,end);furthest.insert({end,writer.process});}
                    else if(end>found->second) {furthest.erase({found->second,writer.process});found->second=end;furthest.insert({end,writer.process});}
                } else procedural_end=std::max(procedural_end,end);
            }
        }
        for(size_t i=0;i<processes.size();++i) {
            const auto& p=processes[i];if(p.always_kind==akALWAYS)continue;
            auto error=[&](int signal) {
                throw std::runtime_error("line "+std::to_string(p.source_line)+": always_comb/always_latch/always_ff variable has another writer: "+signals[signal].name);
            };
            for(auto part:p.writes) {
                if(function_signals.count(part.signal))continue;
                for(const auto& other:writers.at(part.signal))if(other.process!=i&&
                    part.lo<other.part.lo+other.part.width&&other.part.lo<part.lo+part.width)error(part.signal);
                if(p.always_kind!=akALWAYS_FF&&initialized.count(part.signal))error(part.signal);
            }
        }
    }
    void specialize_net_drives() {
        // Whole-program proof: no other writer, connected bit, declaration
        // initializer or force/release can need a separate driver history.
        // Keep the same set(), wake order, PC and budget accounting. This pass
        // removes only resolution bookkeeping, never a process evaluation.
        if(gate_design||!gate_calls.empty()||parallel_count||serial_parallel_stats||needs_force||
           needs_wide||needs_text||dynamic_forks_enabled())return;
        std::vector<size_t> writers(signals.size());
        for(const auto& p:processes)for(const auto& part:p.writes)++writers[size_t(part.signal)];
        std::set<int> excluded;
        for(auto link:bit_links){excluded.insert(link.a);excluded.insert(link.b);}
        for(const auto& init:initializers) {
            excluded.insert(init.signal);
            if(init.process)for(const auto& part:init.process->writes)excluded.insert(part.signal);
        }
        for(auto& p:processes)for(auto& inst:p.instructions) {
            const int id=inst.net_target;
            if(id<0||!signals[size_t(id)].net||writers[size_t(id)]!=1||excluded.count(id))continue;
            const auto value=emit(inst.net_value,signals[size_t(id)].width);
            const auto args="("+sid(id)+","+value+");\n";
            // Identity copies keep the compact original call. Inlining a value
            // comparison into every short copy grows shared leaf handlers;
            // computed/narrowed nets benefit from a constant-width change exit.
            const bool identity=inst.net_value->op=="signal"&&inst.net_value->width==signals[size_t(id)].width;
            const auto store=identity?"s.set"+args:
                "#ifdef DSIM_TYPED_STORES_ENABLED\ns.set_sized<"+std::to_string(signals[size_t(id)].width)+">"+args+
                "#else\ns.set"+args+"#endif\n";
            inst.code="\n#ifndef DSIM_REFERENCE_STATIC_NET_DRIVES\n"+store+"#else\n"+inst.code+"\n#endif\n";
            if(!identity){++typed_net_store_count;typed_net_store_signals.push_back(id);}
            ++static_net_drive_count;
            static_net_drive_signals.push_back(id);
        }
    }
    bool region_expression(const E& e) const {
        if(!e||e->io_state||e->random_state||e->selection_checks||e->procedural_only||!e->writes.empty())return false;
        static const std::set<std::string> ops={"signal","literal","fill1","fillx","fillz","slice","indexed_slice","concat","replicate","mux","cast","two_state","fixed_cast","fixed_cast_2",
            "~","!","+","-","&","|","^","&&","||","===","!==","==","!=","==?","!=?","<",">","<=",">=","<<",">>",">>>","*","/","%"};
        return ops.count(e->op)&&std::all_of(e->args.begin(),e->args.end(),[&](const E& a){return region_expression(a);});
    }
    void plan_comb_regions() {
        comb_members.assign(processes.size(),{-1,-1});
        comb_leaves.assign(processes.size(),false);
        if(!compiled_waits()||needs_force||needs_continuous_delay||needs_variable_continuous||!properties.empty())return;
        std::vector<size_t> writers(signals.size());std::set<int> excluded;
        for(const auto& p:processes)for(const auto& part:p.writes)++writers[size_t(part.signal)];
        for(auto link:bit_links){excluded.insert(link.a);excluded.insert(link.b);}
        for(const auto& init:initializers) {
            excluded.insert(init.signal);
            if(init.process)for(const auto& part:init.process->writes)excluded.insert(part.signal);
        }
        const auto eligible=[&](size_t id) {
            const auto& p=processes[id];
            if(p.continuous_wait<0||p.instructions.size()!=3||p.startup_adapter||p.side_effect||p.writes.size()!=1||p.reads.empty())return false;
            const auto& body=p.instructions[1];const int target=body.net_target;
            if(target<0||!signals[size_t(target)].net||writers[size_t(target)]!=1||excluded.count(target)||p.reads.count(target)||!region_expression(body.net_value))return false;
            const auto& wait=wait_sites[size_t(p.continuous_wait)];
            return wait.static_refs&&!wait.ordered&&wait.expressions.empty()&&wait.process==int(id)&&
                std::all_of(wait.refs.begin(),wait.refs.end(),[](const auto& ref){return ref.second==0;});
        };
        for(size_t first=0;first<processes.size();) {
            if(!eligible(first)){++first;continue;}
            std::set<int> inputs=processes[first].reads;
            std::set<int> targets={processes[first].instructions[1].net_target};
            size_t last=first+1;
            const bool uniform=last<processes.size()&&eligible(last)&&processes[last].reads==processes[first].reads;
            // Preserve the established uniform cohorts. Sparse groups pay a
            // mask dispatch cost, so restrict them to copies with real shared
            // subscriptions; unrelated singleton inputs do not justify a group.
            if(!uniform&&processes[first].instructions[1].net_value->op!="signal"){++first;continue;}
            size_t shared_end=first+1;
            while(last<processes.size()&&last-first<16&&eligible(last)&&
                  processes[last].continuous_wait==processes[last-1].continuous_wait+1) {
                const auto& p=processes[last];const int target=p.instructions[1].net_target;
                if(!uniform&&p.instructions[1].net_value->op!="signal")break;
                if(uniform&&p.reads!=processes[first].reads)break;
                if(!uniform&&last+1<processes.size()&&eligible(last+1)&&p.reads==processes[last+1].reads)break;
                if(inputs.count(target)||std::any_of(p.reads.begin(),p.reads.end(),[&](int input){return targets.count(input);}))break;
                if(std::any_of(p.reads.begin(),p.reads.end(),[&](int input){return inputs.count(input);}))shared_end=last+1;
                inputs.insert(p.reads.begin(),p.reads.end());targets.insert(target);++last;
            }
            if(!uniform)last=shared_end;
            if(last-first>=2) {
                CombRegionIR region;const int id=int(comb_regions.size());
                for(size_t p=first;p<last;++p) {
                    for(int input:processes[p].reads){region.inputs.insert(input);region.subscribers[input]|=UINT64_C(1)<<region.members.size();}
                    comb_members[p]={id,int(region.members.size())};region.members.push_back(int(p));
                }
                comb_regions.push_back(std::move(region));
            }
            first=last;
        }
        // Standalone pure drivers need the same wait/store/return work as a
        // region member, without interpreting their PC on every activation.
        // Keep grouped members on their existing batch/fallback paths.
        for(size_t p=0;p<processes.size();++p)
            comb_leaves[p]=comb_members[p].first<0&&eligible(p);
    }
    bool bounded_initial(size_t id) const {
        const auto& p=processes[id];
        // Optimize recurring RTL normally. Only cap compilation work for very
        // large, forward-only initial programs, whose instructions execute once.
        if(p.always_process||p.function||p.fork_child||p.property_action||p.final_process||p.continuous_wait>=0||p.instructions.size()<4096||
           needs_process_control||dynamic_forks_enabled())return false;
        for(size_t i=0;i<p.instructions.size();++i) {
            const auto& inst=p.instructions[i];
            auto forward=[&](int target){return target>int(i)&&target<=int(p.instructions.size());};
            if(inst.condition&&(!forward(inst.yes)||!forward(inst.no)))return false;
            if(inst.yes>=0&&!forward(inst.yes))return false;
            for(int target:inst.case_targets)if(!forward(target))return false;
            // Suspension PCs also occur inside instruction code. Unknown or
            // backward transfers conservatively retain the ordinary compiler.
            for(size_t at=0;(at=inst.code.find("pc=",at))!=std::string::npos;) {
                at+=3;size_t target=0,start=at;
                while(at<inst.code.size()&&inst.code[at]>='0'&&inst.code[at]<='9') {
                    target=target*10+size_t(inst.code[at++]-'0');
                    if(target>p.instructions.size())return false;
                }
                if(at==start||!forward(int(target)))return false;
            }
        }
        return true;
    }
    void emit_bounded_initial(std::ostream& out,size_t id) {
        constexpr size_t chunk=256;
        const auto& code=processes[id].instructions;
        out<<"// Bounded compilation of a large acyclic initial process.\n"
              "for(;;){bool chunk_transfer=false;switch(unsigned(pc)/"<<chunk<<"){\n";
        for(size_t first=0;first<code.size();first+=chunk) {
            const size_t last=std::min(first+chunk,code.size());
            out<<"case "<<first/chunk<<":{auto invoke_chunk=[&]() __attribute__((noinline)){for(;;){"
               <<"if(pc<"<<first<<"||pc>="<<last<<"){chunk_transfer=true;return;}s.process_step();switch(pc){\n";
            for(size_t j=first;j<last;++j) {
                const auto& inst=code[j];out<<"case "<<j<<": { ";
                if(inst.condition)out<<"pc=("<<emit(inst.condition)<<").truth()==1?"<<inst.yes<<":"<<inst.no<<";continue;";
                else if(inst.yes>=0)out<<"pc="<<inst.yes<<";continue;";
                else out<<inst.code<<" pc="<<j+1<<";continue;";
                out<<"}\n";
            }
            out<<"default:return;}}};invoke_chunk();break;}\n";
        }
        // Preserve the original final/default PC step. Chunk transfers add no
        // scheduler event, process step, persistent state or checkpoint alias.
        out<<"default:s.process_step();return;}if(!chunk_transfer)return;}\n";
    }
    bool compiled_activation_eligible(size_t id,unsigned waits) const {
        if(!compiled_waits()||needs_force||needs_continuous_delay||needs_variable_continuous||!properties.empty())return false;
        const auto& p=processes[id];const auto& code=p.instructions;
        if(p.startup_wait<0||!p.always_process||(p.side_effect&&!p.selection_only_effects)||p.startup_adapter||p.continuous_wait>=0||
           p.repeat_counters||p.delay_values||!p.array_values.empty()||code.size()<3)return false;
        if(waits!=1)return false;
        const bool implicit=p.always_kind==akALWAYS_COMB||p.always_kind==akALWAYS_LATCH;
        if(implicit) {
            if(code.back().code!="pc=0; "+arm_wait_code(int(id),p.startup_wait)+" return;")return false;
        } else if(startup_pc(p)!=1||(code.back().code!="pc=0;continue;"&&code.back().code!="pc=0; continue;"))return false;
        // A forward-only CFG has a finite worst-case cost. Embedded control
        // transfers without explicit successors (loops, suspensions) keep the PC path.
        for(size_t i=implicit?0:1;i+1<code.size();++i) {
            const auto& inst=code[i];
            if(!inst.case_targets.empty()) {
                for(int target:inst.case_targets)if(target<=int(i)||target>=int(code.size()))return false;
            }
            else if(inst.condition) {if(!region_expression(inst.condition)||inst.yes<=int(i)||inst.no<=int(i)||inst.yes>=int(code.size())||inst.no>=int(code.size()))return false;}
            else if(inst.yes>=0) {if(inst.yes<=int(i)||inst.yes>=int(code.size()))return false;}
            else if(inst.code.find("pc=")!=std::string::npos||inst.code.find("continue;")!=std::string::npos||
                    inst.code.find("return;")!=std::string::npos||inst.code.find("s.step(")!=std::string::npos||
                    inst.code.find("integral_loop_steps")!=std::string::npos)return false;
        }
        return true;
    }
    void plan_compiled_activations() {
        activation_members.assign(processes.size(),false);
        std::vector<unsigned> counts(processes.size());
        for(const auto& site:wait_sites)++counts[size_t(site.process)];
        for(size_t id=0;id<processes.size();++id)activation_members[id]=compiled_activation_eligible(id,counts[id]);
    }
    bool compiled_activation(size_t id) const {return id<activation_members.size()&&activation_members[id];}
    void emit_compiled_activation(std::ostream& out,size_t id) {
        const auto& p=processes[id];
        const int entry=startup_pc(p);
        out<<"\n#ifdef DSIM_COMPILED_ACTIVATION_ENABLED\nif(pc=="<<entry<<"&&s.compiled_activation_fits("<<p.instructions.size()<<")){\n";
        for(size_t i=size_t(entry);i<p.instructions.size();++i) {
            const auto& inst=p.instructions[i];out<<"activation"<<i<<":{s.compiled_step();\n";
            if(i+1==p.instructions.size())out<<"goto activation_wait;";
            else if(!inst.case_targets.empty()) {
                out<<inst.case_selection<<"\nswitch(chosen){\n";
                for(size_t branch=0;branch+1<inst.case_targets.size();++branch)out<<"case "<<branch<<":goto activation"<<inst.case_targets[branch]<<";\n";
                out<<"default:goto activation"<<inst.case_targets.back()<<";}\n";
            }
            else if(inst.condition)out<<"if(("<<emit(inst.condition)<<").truth()==1)goto activation"<<inst.yes<<";else goto activation"<<inst.no<<";";
            else if(inst.yes>=0)out<<"goto activation"<<inst.yes<<";";
            else out<<inst.code<<"\ngoto activation"<<i+1<<";";
            out<<"}\n";
        }
        out<<"activation_wait:{"<<(entry?"s.compiled_step();\n":"\n")<<arm_wait_code(int(id),p.startup_wait)<<"return;}}\n#endif\n";
        out<<"#ifdef DSIM_COMPILED_ACTIVATION_ENABLED\n[&]() __attribute__((noinline,cold)) {\n#endif\n";
    }
    void emit_serial_waits(std::ostream& out) {
        for(size_t id=0;id<wait_sites.size();++id) {
            const auto& site=wait_sites[id];auto member=comb_members[size_t(site.process)];
            if(member.first>=0) {
                out<<"\n#ifdef DSIM_COMB_REGION_ENABLED\ns.add_wait_site("<<site.process<<",{});\n";
                if(member.second==0) {
                    const auto& region=comb_regions[size_t(member.first)];
                    const auto full=(UINT64_C(1)<<region.members.size())-1;
                    const bool masked=std::any_of(region.subscribers.begin(),region.subscribers.end(),[&](auto input){return input.second!=full;});
                    out<<(masked?"s.add_masked_comb_region({":"s.add_comb_region({");for(int p:region.members)out<<p<<",";
                    out<<"},{";for(auto input:region.subscribers) {if(masked)out<<"{"<<input.first<<","<<input.second<<"ULL},";else out<<input.first<<",";}
                    out<<(masked?"},[&](uint64_t mask){\n":"},[&](){\n");
                    const auto body=[&](size_t bit) {
                        const int p=region.members[bit];
                        out<<"s.arm_comb_member("<<member.first<<","<<bit<<","<<p<<","<<processes[size_t(p)].continuous_wait<<");\n";
                        out<<processes[size_t(p)].instructions[1].code<<"\n";
                    };
                    if(masked) {
                        // Input subscriber masks are known at compile time.
                        // Emit their shared hot paths without testing each bit;
                        // partial rearming still uses the general ordered path.
                        std::set<uint64_t> hot_masks;for(auto input:region.subscribers)if(__builtin_popcountll(input.second)>1)hot_masks.insert(input.second);
                        out<<"switch(mask){\n";
                        for(uint64_t mask:hot_masks){out<<"case "<<mask<<"ULL:{\n";for(size_t bit=0;bit<region.members.size();++bit)if(mask&(UINT64_C(1)<<bit))body(bit);out<<"return;}\n";}
                        out<<"default:break;}\n";
                    }
                    for(size_t bit=0;bit<region.members.size();++bit){if(masked)out<<"if(mask&"<<(UINT64_C(1)<<bit)<<"ULL){\n";body(bit);if(masked)out<<"}\n";}
                    out<<"});\n";
                }
                out<<"#else\n";
            }
            out<<"s."<<(site.ordered?"add_wait_order_site(":site.expressions.empty()?"add_wait_site(":"add_expression_wait_site(")<<site.process<<","<<site.events<<(site.expressions.empty()?"":","+site.expressions)<<");\n";
            if(member.first>=0)out<<"#endif\n";
        }
    }
    int startup_pc(const ProcessIR& p) const {
        return p.startup_wait>=0&&p.always_kind!=akALWAYS_COMB&&p.always_kind!=akALWAYS_LATCH?1:0;
    }
    void arm_entry_waits(std::ostream& out,size_t part=SIZE_MAX) {
        for(size_t i=0;i<processes.size();++i)if(startup_pc(processes[i])&&(part==SIZE_MAX||process_owner[i]==part))
            out<<arm_wait_code(int(i),processes[i].startup_wait);
    }
    void initialize_processes(std::ostream& out,size_t part=SIZE_MAX) {
        if(!properties.empty()||!clockings.empty())out<<"s.initialize_properties();\n";
        if(needs_random)for(size_t i=0;i<processes.size();++i)if(part==SIZE_MAX||process_owner[i]==part)
            out<<"s.seed_random_process("<<pid(int(i))<<","<<i<<"ull);\n";

        std::vector<int> dormant;
        for(size_t i=0;i<processes.size();++i)if(processes[i].startup_wait>=0&&
            (part==SIZE_MAX||process_owner[i]==part)) {
            dormant.push_back(int(i));
            if(!startup_pc(processes[i])) {
                out<<arm_wait_code(int(i),processes[i].startup_wait);
                out<<"s.delay("<<pid(int(i))<<",0);\n";
            }
        }
        for(size_t i=0;i<processes.size();++i)if((processes[i].fork_child||processes[i].property_action||processes[i].final_process||processes[i].task_template)&&(part==SIZE_MAX||process_owner[i]==part)) {
            dormant.push_back(int(i));
            if(processes[i].final_process)out<<"s.add_final_process("<<pid(int(i))<<");\n";
        }
        // Typed input variables receive their initial port copy after ordinary
        // event controls have armed. No added phase for designs without them.
        std::vector<int> adapters;
        for(size_t i=0;i<processes.size();++i)if(processes[i].startup_adapter&&
            (part==SIZE_MAX||process_owner[i]==part)) {
            adapters.push_back(int(i));dormant.push_back(int(i));
        }
        if(gate_design&&gate_design->sdf_jobs_enabled) {
            out<<"s.initialize_sdf_jobs_and_processes(";
            if(!dormant.empty()) {
                out<<"{";for(int id:dormant)out<<pid(id)<<",";out<<"}";
            }
            out<<");\n";
        } else if(part==SIZE_MAX&&!comb_regions.empty()) {
            out<<"\n#ifdef DSIM_COMB_REGION_ENABLED\nfor(int i=0;i<int(s.processes.size());++i){switch(i){\n";
            for(size_t id=0;id<comb_regions.size();++id) {
                const auto& region=comb_regions[id];
                out<<"case "<<region.members.front()<<":s.enqueue_comb_region("<<id<<");break;\n";
                for(size_t j=1;j<region.members.size();++j)out<<"case "<<region.members[j]<<":break;\n";
            }
            for(int id:dormant)out<<"case "<<pid(id)<<":break;\n";
            out<<"default:s.enqueue(i);break;}}\n#else\n";
            out<<"for(int i=0;i<int(s.processes.size());++i)";
            if(!dormant.empty()) {out<<"if(";for(size_t j=0;j<dormant.size();++j){if(j)out<<"&&";out<<"i!="<<pid(dormant[j]);}out<<")";}
            out<<"s.enqueue(i);\n#endif\n";
        } else {
            out<<"for(int i=0;i<int(s.processes.size());++i)";
            if(!dormant.empty()) {
                out<<"if(";for(size_t i=0;i<dormant.size();++i){if(i)out<<"&&";out<<"i!="<<pid(dormant[i]);}out<<")";
            }
            out<<(part==SIZE_MAX?" s.enqueue(i);\n":"s.enqueue(i);\n");
        }
        for(int id:adapters)out<<"s.enqueue("<<pid(id)<<");\n";
    }
    std::string lower_parallel() {
        plan_parallel();std::ostringstream out;
        const auto partitions=parallel_plan.loads.size();
        if(partitions==1) {
            // No concurrency is available. Lower again without ID maps or
            // transactions; gate topology/model data remain shared.
            Lower serial(top,gate_design,wave_enabled,timing,prefix_lines,0);
            if(sdf_task_handler)serial.set_sdf_task_handler([this](std::vector<SdfTask>& tasks) {
                if(tasks.size()!=sdf_tasks.size())throw std::runtime_error("SDF task identity changed during serial fallback");
                for(size_t i=0;i<tasks.size();++i)if(tasks[i].file!=sdf_tasks[i].file||tasks[i].target!=sdf_tasks[i].target)
                    throw std::runtime_error("SDF task target changed during serial fallback");
                tasks=sdf_tasks;
            });
            serial.serial_parallel_stats=true;serial.diagnostics=false;
            return serial.lower();
        }
        if(gate_design)out<<gate_design->cpp(precision_fs);
        emit_memories(out);
        out<<"using namespace dsim;\nint main(int argc,char** argv) { try {\n"
              "bool parallel_stats=false;uint64_t parallel_window=1024;std::vector<char*> options;options.push_back(argv[0]);\n"
              "std::vector<std::string> plusargs;\n"
              "for(int i=1;i<argc;++i)if(argv[i][0]=='+')plusargs.emplace_back(argv[i]+1);else if(std::string(argv[i])==\"--parallel-stats\")parallel_stats=true;"<<parallel_window_option()<<"else options.push_back(argv[i]);\n"
              "argc=int(options.size());options.push_back(nullptr);argv=options.data();\n";
        out<<"ConservativeSim engine("<<partitions<<",parallel_window);";
        if(needs_global_finish)out<<"engine.enable_global_finish();";
        out<<"\n";
        for(size_t i=0;i<partitions;++i)out<<"engine.partition();\n";
        out<<"std::vector<int> sid("<<signals.size()<<",-1),pid("<<processes.size()<<",-1),wid("<<wait_sites.size()<<",-1)";
        if(!properties.empty())out<<",qid("<<properties.size()<<",-1)";
        if(!event_nba_sites.empty())out<<",nwid("<<event_nba_sites.size()<<",-1)";
        if(!fork_groups.empty())out<<",fid("<<fork_groups.size()<<",-1)";
        if(needs_process_control)out<<",did("<<disable_targets.size()<<",-1)";
        out<<";\n";
        out<<"std::vector<uint32_t> cid("<<continuous_channels.size()<<");\n";
        if(wave_enabled) {
            out<<"ParallelWaveCapture global_wave(engine,argc,argv,"<<quote(time_unit_name(precision_fs))<<");\n";
            out<<"struct PartitionWave {ParallelWaveCapture& capture;size_t partition;bool enabled() const{return capture.enabled();} "
                 "void gate_net(int signal,const std::vector<std::string>& scope,const std::string& name){capture.declare(partition,signal,scope,name,0,0,true,false);}};\n";
        } else out<<"uint64_t event_limit=std::numeric_limits<uint64_t>::max(); if(argc==3 && std::string(argv[1])==\"--max-events\")event_limit=std::stoull(argv[2]);else if(argc!=1)throw std::runtime_error(\"usage: simv [--max-events N] [--parallel-stats]\");\n";
        std::set<int> declared_wave_signals;
        for(size_t part=0;part<partitions;++part) {
            out<<"{auto& s=engine.kernel("<<part<<");s.set_time_precision("<<precision_fs<<"ULL);\n";
            if(needs_plusargs)out<<"s.set_plusargs(plusargs);\n";
            if(wave_enabled)out<<"PartitionWave wave{global_wave,"<<part<<"};\n";
            else out<<"s.limit=event_limit;\n";
            for(size_t i=0;i<signals.size();++i)if(signal_owner[i]==part) {
                if(signals[i].text_value){out<<sid(int(i))<<"=s.signal_text(); // "<<quote(signals[i].name)<<"\n";continue;}
                if(signals[i].real_width){out<<sid(int(i))<<"=s.signal_real("<<signals[i].real_width<<");\n";continue;}out<<sid(int(i))<<"=s."<<(signals[i].named_event?"named_event(":signals[i].two_state?"signal_two_state(":"signal(")<<(signals[i].named_event?std::string():std::to_string(signals[i].width))<<(signals[i].named_event||signals[i].two_state?"":signals[i].net?",true":",false")<<"); // "<<quote(signals[i].name)<<"\n";}
            for(int id:unsigned_associative_signals)if(signal_owner[size_t(id)]==part)out<<"s.associative_set_unsigned("<<sid(id)<<");\n";
            for(int id:class_associative_signals)if(signal_owner[size_t(id)]==part)out<<"s.associative_set_class("<<sid(id)<<");\n";
            emit_aggregate_state_masks(out,part);emit_aggregate_types(out,part);
            if(wave_enabled)for(const auto& sc:scopes)for(const auto& pair:sc->ids)if(signal_owner[size_t(pair.second)]==part&&!automatic_signals.count(pair.second)&&!foreach_indices.count(pair.second)&&!signals[pair.second].named_event&&!signals[pair.second].text_value&&!dynamic_signals.count(pair.second)&&!object_signals.count(pair.second)&&!struct_string_signals.count(pair.second)&&(!static_wave_paths.count(pair.second)||declared_wave_signals.insert(pair.second).second)) {
                Variable var{sc->symbols.at(pair.first)};
                out<<"global_wave.declare("<<part<<","<<sid(pair.second)<<",{";
                for(const auto& p:static_wave_paths.count(pair.second)?static_wave_paths.at(pair.second):sc->wave_path)out<<quote(p)<<",";
                out<<"},"<<quote(pair.first)<<","<<var->dstart()<<","<<var->dend()<<","<<(signals[pair.second].net?"true":"false")<<","<<(sc->packed.count(pair.first)?"true":"false")<<");\n";
            }
            for(auto link:bit_links)if(signal_owner[size_t(link.a)]==part)
                out<<"s.connect_net("<<sid(link.a)<<","<<link.abit<<","<<sid(link.b)<<","<<link.bbit<<");\n";
            for(size_t i=0;i<continuous_channels.size();++i)if(process_owner[size_t(continuous_owners[i])]==part)out<<continuous_channels[i];
            for(size_t i=0;i<processes.size();++i)if(process_owner[i]==part) {
                const bool bounded=bounded_initial(i);
                if(bounded)out<<"\n#if defined(__clang__) && !defined(DSIM_OPTIMIZE_LARGE_INITIAL)\n#pragma clang optimize off\n#endif\n";
                out<<pid(int(i))<<"=s.process([&,pc="<<startup_pc(processes[i]);
                for(int k=0;k<processes[i].repeat_counters;++k)out<<",repeat"<<k<<"=uint64_t(0)";
                for(int k=0;k<processes[i].delay_values;++k)out<<",delay_value"<<k<<"=V()";
                for(size_t k=0;k<processes[i].array_values.size();++k)out<<",array_value"<<k<<"=std::vector<V>("<<processes[i].array_values[k]<<")";
                out<<"]() mutable {";
                if(bounded) {
                    emit_bounded_initial(out,i);out<<"});\n#if defined(__clang__) && !defined(DSIM_OPTIMIZE_LARGE_INITIAL)\n#pragma clang optimize on\n#endif\n";
                    continue;
                }
                if(needs_process_control)out<<"if(int transfer=s.take_process_transfer("<<runtime_pid(int(i))<<");transfer>=0)pc=transfer;";
                out<<"for(;;){s.process_step();";
                if(needs_process_control)out<<"s.process_location("<<runtime_pid(int(i))<<",pc);";
                out<<"switch(pc){\n";
                for(size_t j=0;j<processes[i].instructions.size();++j) {
                    const auto& inst=processes[i].instructions[j];out<<"case "<<j<<": { ";
                    if(dynamic_forks_enabled())out<<"s.activation_depth("<<inst.activation_depth<<");";
                    out<<integral_loop(processes[i],j);
                    if(inst.condition)out<<"pc=("<<emit(inst.condition)<<").truth()==1?"<<inst.yes<<":"<<inst.no<<";continue;";
                    else if(inst.yes>=0)out<<"pc="<<inst.yes<<";continue;";
                    else out<<inst.code<<" pc="<<j+1<<";continue;";
                    out<<"}\n";
                }
                out<<"default:return;}}});\n";
            }
            for(size_t i=0;i<wait_sites.size();++i)if(process_owner[size_t(wait_sites[i].process)]==part)
                out<<wid(int(i))<<"=s."<<(wait_sites[i].ordered?"add_wait_order_site(":wait_sites[i].expressions.empty()?"add_wait_site(":"add_expression_wait_site(")<<pid(wait_sites[i].process)<<","<<wait_sites[i].events<<(wait_sites[i].expressions.empty()?"":","+wait_sites[i].expressions)<<");\n";
            for(size_t i=0;i<event_nba_sites.size();++i)if(process_owner[size_t(event_nba_sites[i].process)]==part) {
                const auto& site=event_nba_sites[i];out<<"nwid["<<i<<"]=s.add_event_nba_site("<<site.events<<(site.expressions.empty()?"":","+site.expressions)<<");\n";
            }
            for(size_t i=0;i<fork_groups.size();++i)if(process_owner[size_t(fork_groups[i].parent)]==part) {
                out<<"fid["<<i<<"]=s.add_fork_group("<<pid(fork_groups[i].parent)<<",{";
                for(int child:fork_groups[i].children)out<<pid(child)<<",";
                out<<"},"<<fork_groups[i].kind<<");\n";
            }
            if(needs_process_control)for(size_t i=0;i<disable_targets.size();++i)if(process_owner[size_t(disable_targets[i].process)]==part) {
                const auto& target=disable_targets[i];out<<"did["<<i<<"]=s.add_disable_target("<<pid(target.process)<<","<<target.end<<",{";
                for(size_t group=target.first_group;group<target.last_group;++group)if(disable_group(target,group))out<<"fid["<<group<<"],";
                out<<"},"<<target.identity<<","<<target.begin<<");\n";
            }
            configure_dynamic_forks(out);
            for(size_t i=0;i<gate_calls.size();++i)if(gate_owner[i]==part)out<<gate_calls[i];
            emit_properties(out,part);
            out<<"s.finish_connections();\n";
            if(gate_design&&gate_design->timing)out<<"s.initialize_module_paths();\n";
            emit_initializers(out,true,part);
            arm_entry_waits(out,part);emit_aggregate_defaults(out,part);
            emit_initializers(out,false,part);
            for(size_t i=0;i<continuous_channels.size();++i)if(process_owner[size_t(continuous_owners[i])]==part)
                out<<"s.initialize_continuous(cid["<<i<<"]);\n";
            initialize_processes(out,part);
            out<<"}\n";
        }
        if(wave_enabled)out<<"global_wave.start();\n";
        out<<"engine.run();\n";
        if(wave_enabled)out<<"global_wave.close();\n";
        out<<"if(parallel_stats)std::cerr<<\"PARALLEL {\\\"partitions\\\":\"<<engine.partition_count()<<\",\\\"windows\\\":\"<<engine.stats.windows<<\",\\\"messages\\\":\"<<engine.stats.messages<<\"}\\n\";\n";
        out<<"return 0;}catch(const std::exception& e){std::cerr<<\"dsim runtime: \"<<e.what()<<'\\n';return 1;}}\n";
        return out.str();
    }
public:
    bool parallel_execution() const {return parallel_count&&parallel_plan.loads.size()>1;}
    bool dynamic_arrays_enabled() const {return object_queue_storage||object_associative_storage||!dynamic_signals.empty();}
    bool queues_enabled() const {return object_queue_storage||!queue_bounds.empty();}
    bool associative_enabled() const {return object_associative_storage||!associative_signals.empty();}
    bool process_handles_enabled() const {return needs_process_handles;}
    bool process_lifetime_enabled() const {return needs_process_lifetime;}
    bool ipc_enabled() const {return needs_ipc;}
    bool objects_enabled() const {return objects_signal>=0;}
    bool dump_tasks() const {return needs_dump_tasks;}
    bool replication() const {return needs_replication;}
    bool mixed_state_values() const {return !aggregate_state_masks.empty()||aggregate_storage_enabled();}
    bool coverage_enabled() const {return !coverages.empty();}
    bool real_values() const {return needs_real;}
    bool two_state_values() const {return needs_two_state_cast||std::any_of(signals.begin(),signals.end(),[](const SignalIR& s){return s.two_state;});}
    bool text_values() const {return needs_text;}
    bool aggregate_storage_enabled() const {return !container_aggregate_types.empty()||!object_aggregate_types.empty();}
    bool struct_string_values() const {return needs_struct_strings;}
    bool scan_enabled() const {return needs_scan;}
    bool file_io_enabled() const {return needs_file_io;}
    bool plusargs_enabled() const {return needs_plusargs;}
    bool final_processes_enabled() const {return needs_final;}
    bool wide_values() const {return needs_wide;}
    bool compact_nba_storage() const {return !needs_parts_nba;}
    bool typed_stores() const {return typed_net_store_count!=0;}
    bool delayed_nba_updates() const {return needs_delayed_nba||!clockings.empty();}
    bool expression_events_enabled() const {return needs_expression_events;}
    bool event_nba_enabled() const {return !event_nba_sites.empty();}
    bool function_forks_enabled() const {return std::any_of(fork_groups.begin(),fork_groups.end(),[](const auto& group){return group.parent<0;});}
    bool fork_join_enabled() const {return !fork_groups.empty()||needs_process_control;}
    bool dynamic_forks_enabled() const {return needs_explicit_automatic||std::any_of(fork_groups.begin(),fork_groups.end(),[](const auto& group){return group.kind!=1;});}
    void configure_dynamic_forks(std::ostream& out) const {
        if(!dynamic_forks_enabled())return;
        out<<"s.enable_dynamic_forks();\n";
    }
    bool process_control_enabled() const {return needs_process_control;}
    bool array_stream_enabled() const {return needs_array_stream;}
    bool shared_tasks_enabled() const {return std::any_of(processes.begin(),processes.end(),[](const auto& p){return p.task_template;});}
    bool disable_group(const DisableIR& target,size_t group) const {
        // Lowering a call can discover separate task/function templates inside
        // the lexical interval. Task templates are call sites, not descendants
        // of this block. Follow actual fork ownership instead of interval alone.
        int parent=fork_groups[group].parent;
        if(parent<0)return !std::any_of(fork_groups[group].children.begin(),fork_groups[group].children.end(),[&](int child){return processes[size_t(child)].task_template;});
        while(parent>=0) {
            if(parent==target.process)return true;
            int ancestor=-1;
            for(const auto& item:fork_groups)if(std::find(item.children.begin(),item.children.end(),parent)!=item.children.end()){ancestor=item.parent;break;}
            parent=ancestor;
        }
        return false;
    }
    bool termination_unwind_enabled() const {return needs_termination_unwind;}
    bool stop_enabled() const {return needs_stop;}
    bool associative_refs_enabled() const {return needs_associative_refs;}
    bool wait_order_enabled() const {return needs_wait_order;}
    bool string_replication_enabled() const {return needs_string_replication;}
    bool event_aliases_enabled() const {return needs_event_aliases;}
    bool named_events_enabled() const {return needs_named_events;}
    bool clocking_enabled() const {return !clockings.empty();}
    bool concurrent_properties() const {return !properties.empty()||!clockings.empty();}
    bool sequence_antecedents() const {return std::any_of(properties.begin(),properties.end(),[](const PropertyIR& p){return p.antecedent_stages!=0;});}
    bool selection_checks() const {return needs_selection_checks;}
    bool random_functions() const {return needs_random;}
    bool constraint_functions() const {return needs_constraints;}
    bool vector_system_functions() const {return needs_vector_system;}
    bool dynamic_delays() const {return needs_dynamic_delay;}
    bool memory_io() const {return needs_memory_io;}
    bool indexed_selects() const {return needs_indexed_select;}
    bool continuous_delays() const {return needs_continuous_delay;}
    bool force_enabled() const {return needs_force;}
    bool variable_continuous() const {return needs_variable_continuous;}
    bool compiled_waits() const {
        return clockings.empty()&&!gate_design&&!parallel_count&&!needs_wide&&!needs_text&&!needs_process_control&&
            !dynamic_forks_enabled()&&fork_groups.empty()&&!needs_expression_events&&!needs_named_events&&
            event_nba_sites.empty()&&!wait_sites.empty()&&
            std::all_of(wait_sites.begin(),wait_sites.end(),[](const WaitIR& site){
                return site.static_refs&&!site.ordered&&site.expressions.empty();
            });
    }
    bool compiled_activations() const {for(size_t id=0;id<processes.size();++id)if(compiled_activation(id))return true;return false;}
    bool combinational_regions() const {return !comb_regions.empty();}
    bool combinational_leaves() const {return std::any_of(comb_leaves.begin(),comb_leaves.end(),[](bool leaf){return leaf;});}
    bool masked_combinational_regions() const {
        for(const auto& region:comb_regions) {
            const auto full=(UINT64_C(1)<<region.members.size())-1;
            for(auto input:region.subscribers)if(input.second!=full)return true;
        }
        return false;
    }
    explicit Lower(VeriMod* m,const GateDesign* gate,bool wave,const TimingConfig& times,size_t prefix,size_t threads):top(m),gate_design(gate),wave_enabled(wave),timing(times),prefix_lines(prefix),parallel_count(threads) {}
    void set_compact_memories(bool enabled) {compact_memories=enabled;}
    void set_shared_functions(bool enabled) {shared_functions=enabled;if(enabled)needs_explicit_automatic=needs_process_control=true;}
    bool sdf_annotation_logs() const {return needs_sdf_log;}
    void set_sdf_task_handler(SdfTaskHandler handler) {sdf_task_handler=std::move(handler);}
    std::string report() {
        std::ostringstream out;
        out<<"{\n  \"schema\": \"dsim.elaboration.v1\",\n  \"frontend\": \"rtl\",\n  \"top\": "<<json_quote(top->name())
           <<",\n  \"global_precision_fs\": "<<precision_fs<<",\n  \"sdf_static_tasks\": "<<sdf_tasks.size()<<",\n  \"signal_count\": "<<signals.size()<<",\n  \"process_count\": "<<processes.size()
           <<",\n  \"typed_net_store_candidates\": "<<typed_net_store_count<<",\n  \"typed_net_store_signals\": [";
        for(size_t i=0;i<typed_net_store_signals.size();++i){if(i)out<<',';out<<typed_net_store_signals[i];}
        out<<"],\n  \"static_net_drives\": "<<static_net_drive_count<<",\n  \"static_net_drive_signals\": [";
        for(size_t i=0;i<static_net_drive_signals.size();++i){if(i)out<<',';out<<static_net_drive_signals[i];}
        out<<"],\n  \"compiled_activations\":[";
        bool first_activation=true;
        for(size_t id=0;id<processes.size();++id)if(compiled_activation(id)){if(!first_activation)out<<',';first_activation=false;out<<id;}
        out<<"],\n  \"comb_leaves\": [";
        bool first_leaf=true;
        for(size_t p=0;p<comb_leaves.size();++p)if(comb_leaves[p]){if(!first_leaf)out<<',';first_leaf=false;out<<p;}
        out<<"],\n  \"comb_regions\": [";
        for(size_t id=0;id<comb_regions.size();++id) {
            if(id)out<<',';const auto& region=comb_regions[id];out<<"{\"members\":[";
            for(size_t j=0;j<region.members.size();++j){if(j)out<<',';out<<region.members[j];}
            out<<"],\"inputs\":[";bool first=true;for(int input:region.inputs){if(!first)out<<',';first=false;out<<input;}
            out<<"],\"subscribers\":[";first=true;
            for(auto input:region.subscribers){if(!first)out<<',';first=false;out<<"{\"signal\":"<<input.first<<",\"mask\":"<<input.second<<"}";}
            out<<"]}";
        }
        out<<"],\n  \"scopes\": [";
        bool first_scope=true;
        for(auto& sc:scopes) {
            if(!first_scope) out<<",";
            first_scope=false;
            out<<"\n    {\"path\": "<<json_quote(sc->path)<<", \"module\": "<<json_quote(sc->mod->name())
               <<", \"line\": "<<sc->mod->line()<<", \"time_unit_fs\": "<<sc->time.unit_fs<<", \"time_precision_fs\": "<<sc->time.precision_fs<<", \"parameters\": {";
            bool first_param=true;
            auto params=[&](VeriNode* decl) {
                if(!decl || decl->detail_type()!=vsDECL_PARAM) return;
                for(auto* a:static_cast<VeriParamDecl*>(decl)->vars()) {
                    if(a->detail_type()!=veEXP_ASSIGN) fail(a,"unsupported parameter declaration");
                    auto nm=name(static_cast<VeriAssignExp*>(a)->lval());
                    auto* symbol=static_cast<VeriPrimaryExp*>(static_cast<VeriAssignExp*>(a)->lval())->var();
                    if(!symbol || symbol->tok_type()!=vtPARAM) fail(a,"missing parameter symbol "+nm);
                    auto* value=static_cast<VeriParam*>(symbol)->get_val();
                    if(!value) fail(a,"unresolved parameter "+nm);
                    std::string bits;
                    for(int i=value->bits()-1;i>=0;--i) {
                        int bit=value->get_certain_bit(i); bits+=bit==VX?'x':bit==VZ?'z':bit?'1':'0';
                    }
                    if(!first_param) out<<",";
                    first_param=false;
                    const auto* declaration=static_cast<VeriParamDecl*>(decl);
                    out<<json_quote(nm)<<": {\"width\": "<<value->bits()
                       <<", \"signed\": "<<(value->is_signed()==IS_TRUE?"true":"false")
                       <<", \"two_state\": "<<(veri_two_state(declaration->data_type())?"true":"false")
                       <<", \"bits\": "<<json_quote(bits)<<"}";
                }
            };
            if(!sc->generated && sc->mod->param()) {
                if(sc->mod->param()->detail_type()==vsDECL_PARAM_DECL_LIST)
                    for(auto* d:static_cast<VeriParamDeclList*>(sc->mod->param())->param_list()) params(d);
                else params(sc->mod->param());
            }
            for(auto* d:sc->items) params(d);
            out<<"}, \"signals\": {"; bool first_signal=true;
            for(auto& entry:sc->ids) {
                if(!first_signal) out<<",";
                first_signal=false;
                Variable var{sc->symbols.at(entry.first)};
                out<<json_quote(entry.first)<<": {\"id\": "<<entry.second<<", \"width\": "<<(signals[entry.second].text_value?"null":std::to_string(var->dlen()))
                   <<", \"lsb\": "<<var->dend()<<", \"signed\": "<<(var->is_signed()==IS_TRUE?"true":"false")<<", \"net\": "<<(signals[entry.second].net?"true":"false")<<", \"two_state\": "<<(signals[entry.second].two_state?"true":"false");
                if(signals[entry.second].text_value)out<<", \"string\": true";
                if(signals[entry.second].named_event)out<<", \"named_event\": true";
                out<<"}";
            }
            out<<"}}";
        }
        out<<"\n  ],\n  \"ports\": ["; bool first_port=true;
        for(auto& b:bindings) {
            if(!first_port) out<<",";
            first_port=false;
            out<<"\n    {\"scope\": "<<json_quote(b.child->path)<<", \"parent_scope\": "<<json_quote(b.parent->path)<<", \"port\": "<<json_quote(b.port->name())
               <<", \"direction\": "<<json_quote(b.port->inout()==vpIN?"input":b.port->inout()==vpOUT?"output":"inout")
               <<", \"signal_id\": "<<(b.port->range_depth()?"null":std::to_string(b.child->ids.at(b.port->name())))
               <<", \"binding\": "<<json_quote(!b.actual?(b.omitted && b.child->defaults.count(b.port->name())?"default":"open"):b.collapsed?"collapsed_net":b.bit_connected?"connected_bits":b.port->range_depth()?"array_adapter":"adapter")<<", \"actual_parts\": [";
            bool first_part=true;
            for(auto part:b.parts) {
                if(!first_part) out<<",";
                first_part=false;
                out<<"{\"signal\": "<<part.signal<<", \"lo\": "<<part.lo<<", \"width\": "<<part.width<<", \"rhs_lo\": "<<part.rhs_lo<<"}";
            }
            out<<"]";
            if(b.port->range_depth()) {
                out<<", \"array_elements\": [";bool first=true;
                for(auto [formal,actual]:b.array_elements) {
                    if(!first)out<<",";first=false;
                    out<<"{\"signal_id\":"<<formal<<",\"actual_signal_id\":"<<actual<<"}";
                }
                out<<"]";
            }
            out<<"}";
        }
        out<<"\n  ],\n  \"net_bit_connections\": [";
        bool first_link=true;
        for(auto link:bit_links) {
            if(!first_link) out<<",";
            first_link=false;
            out<<"\n    {\"a\": "<<link.a<<", \"abit\": "<<link.abit<<", \"b\": "<<link.b<<", \"bbit\": "<<link.bbit<<"}";
        }
        out<<"\n  ]";
        if(parallel_count) {
            out<<",\n  \"parallel\": {\"scope\":\"whole-program\",\"backend\":\"independent-domains\",\"requested_workers\":"<<parallel_count
               <<",\"execution\":\""<<(parallel_execution()?"conservative-kernels":"serial-fallback")<<"\""
               <<",\"global_finish_transactions\":"<<(parallel_execution()&&needs_global_finish?"true":"false")
               <<",\"partitions\":"<<parallel_plan.loads.size()<<",\"zero_delay_domains\":"<<parallel_plan.domains
               <<",\"cut_edges\":0,\"atomic_gate_scopes\":"<<gate_calls.size()<<",\"signal_owner\":[";
            for(size_t i=0;i<signal_owner.size();++i){if(i)out<<',';out<<signal_owner[i];}
            out<<"],\"process_owner\":[";
            for(size_t i=0;i<process_owner.size();++i){if(i)out<<',';out<<process_owner[i];}
            out<<"],\"loads\":[";
            for(size_t i=0;i<parallel_plan.loads.size();++i){if(i)out<<',';out<<parallel_plan.loads[i];}
            out<<"]}";
        }
        if(gate_design) {
            out<<",\n  \"gate_design\": "<<gate_design->report()<<",\n  \"gate_scopes\": [";
            for(size_t i=0;i<gate_scopes.size();++i) { if(i) out<<","; out<<json_quote(gate_scopes[i]); }
            out<<"]";
        }
        out<<"\n}\n"; return out.str();
    }
    bool queue_ref_limits_enabled() const {return needs_queue_ref_limits;}
    bool object_array_refs_enabled() const {return needs_object_array_refs;}
    bool object_scalar_refs_enabled() const {return needs_object_scalar_refs;}
    bool object_format_enabled() const {return needs_object_format;}
    bool dpi_enabled() const {return needs_dpi;}
    void set_dpi_libraries(const std::vector<std::string>& libraries){dpi_libraries=libraries;}
    std::string dpi_header() const {
        std::string header="#pragma once\n#include \"svdpi.h\"\n#ifdef __cplusplus\nextern \"C\" {\n#endif\n";
        for(const auto& item:dpi_prototypes)header+=item.second+";\n";
        return header+"#ifdef __cplusplus\n}\n#endif\n";
    }
    std::vector<VeriSeqBlock*> class_seeds;
    bool discovered_late_classes=false;
    std::vector<VeriSeqBlock*> class_definitions() const {
        std::vector<VeriSeqBlock*> result;
        for(const auto& entry:classes)result.push_back(entry.first);
        std::sort(result.begin(),result.end(),[](auto* a,auto* b){return a->idx()<b->idx();});
        return result;
    }
    std::string lower() {
        // File-level classes need a canonical lexical home before any module
        // can register a derived class. Preserve existing collection order for
        // designs without compilation-unit declarations.
        const bool unit_types=!veri_parser->compilation_declarations().empty();
        auto* top_scope=collect(top,top->name(),{},unit_types);
        // Package timescales contribute before choosing the global tick.
        for(auto* package:veri_parser->packages())package_scopes.emplace(package,collect(package,package->name()));
        for(auto* owner:veri_parser->compilation_declarations())collect(owner,"$unit");
        if(unit_types)collect_contents(top_scope);
        // Method binding may instantiate types after an earlier virtual call
        // was lowered. A retry registers the discovered class universe before
        // any initializer or statement builds its dispatch alternatives.
        for(auto* definition:class_seeds) {
            if(definition->ipc_kind()||definition->process_type()) {scope=top_scope;register_class(definition);}
            else register_callable_class(definition,definition);
        }
        const size_t initial_class_count=classes.size();
        prepare_sdf_tasks();
        detect_dpi();
        prepare_sequences();
        for(auto& b:bindings)if(b.port->range_depth())prepare_array_port(b);
        collapse_ports(); connect_ports();
        precision_fs=scopes.front()->time.precision_fs;
        for(const auto& sc:scopes)precision_fs=std::min(precision_fs,sc->time.precision_fs);
        if(auto declared=VeriParser::get_instance()->time_precision_fs())precision_fs=std::min(precision_fs,declared);
        if(timing.declared_precision_fs)precision_fs=std::min(precision_fs,timing.declared_precision_fs);
        bool active_gate=gate_design&&std::any_of(scopes.begin(),scopes.end(),[&](const auto& sc) {
            return sc->mod->name()==GateDesign::rtl_identifier(gate_design->top);
        });
        if(active_gate&&gate_design->structural_precision_fs)
            precision_fs=std::min(precision_fs,gate_design->structural_precision_fs);
        if(active_gate&&gate_design->timing)precision_fs=std::min(precision_fs,gate_design->timing->precision_fs);
        prepare_dpi();
        prepare_clockings();
        prepare_coverages();
        // Statement lowering can append static lexical scopes. The owning
        // pointees remain stable; do not iterate the vector with invalidated iterators.
        for(size_t i=0;i<scopes.size();++i) {
            scope=scopes[i].get();
            if(scope->class_definition&&!scope->subroutine) {
                initialize_class_statics(scope);
            }
        }
        for(size_t i=0;i<scopes.size();++i) {
            scope=scopes[i].get();if(!scope->procedural)lower_scope();
        }
        discovered_late_classes=needs_closed_classes&&classes.size()!=initial_class_count;
        if(discovered_late_classes)return {}; // Emit only the closed class universe.
        for(const auto& p:processes)for(const auto& inst:p.instructions)if(inst.condition&&inst.condition->text_value)fail(nullptr,"string cannot be used as a boolean condition");
        check_specialized_writers();
        if(parallel_count)return lower_parallel();
        specialize_net_drives();
        plan_comb_regions();
        plan_compiled_activations();
        std::ostringstream out;
        if(gate_design) out<<gate_design->cpp(precision_fs,!serial_parallel_stats);
        emit_memories(out);
        if(needs_dpi)out<<"static_assert(sizeof(uintptr_t)<=sizeof(uint64_t),\"DPI pointer exceeds handle storage\");\n";
        out<<dpi_definitions;
        out<<"using namespace dsim;\n";
        emit_shared_functions(out);
        out<<"int main(int argc,char** argv) { try {\nSim s;\n";
        out<<"std::vector<std::string> plusargs;std::vector<char*> runtime_options{argv[0]};\n"
              "for(int i=1;i<argc;++i)if(argv[i][0]=='+')plusargs.emplace_back(argv[i]+1);else runtime_options.push_back(argv[i]);\n"
              "argc=int(runtime_options.size());runtime_options.push_back(nullptr);argv=runtime_options.data();\n";
        emit_dpi_setup(out);
        if(needs_plusargs)out<<"s.set_plusargs(plusargs);\n";
        if(serial_parallel_stats)out<<"// Single partition argument adapter.\n"
            "bool parallel_stats=false;uint64_t parallel_window=1024;std::vector<char*> options;options.push_back(argv[0]);\n"
            "for(int i=1;i<argc;++i)if(std::string(argv[i])==\"--parallel-stats\")parallel_stats=true;"<<parallel_window_option()<<"else options.push_back(argv[i]);\n"
            "argc=int(options.size());options.push_back(nullptr);argv=options.data();\n"
            "// End single partition argument adapter.\n";
        out<<"s.set_time_precision("<<precision_fs<<"ULL);\n";
        if(wave_enabled)out<<"WaveCapture wave(s,argc,argv,"<<quote(time_unit_name(precision_fs))<<(needs_dump_tasks?",true":"")<<");\n";
        else out<<"if(argc==3 && std::string(argv[1])==\"--max-events\") s.limit=std::stoull(argv[2]); else if(argc!=1) throw std::runtime_error(\"usage: simv [--max-events N]\");\n";
        for(size_t i=0;i<signals.size();) {
            const auto& signal=signals[i];size_t end=i+1;
            // Array elements retain distinct signals and registration order.
            // Emit repeated registrations as a loop, so native optimizers do
            // not see hundreds of thousands of identical inlined call sites.
            for(;end<signals.size();++end) {
                const auto& next=signals[end];
                if(signal.width!=next.width||signal.net!=next.net||signal.two_state!=next.two_state||
                   signal.real_width!=next.real_width||signal.text_value!=next.text_value||signal.named_event!=next.named_event)break;
            }
            const auto call=signal.real_width?"s.signal_real("+std::to_string(signal.real_width)+")":
                signal.text_value?std::string("s.signal_text()"):
                "s."+std::string(signal.named_event?"named_event(":signal.two_state?"signal_two_state(":"signal(")+
                (signal.named_event?std::string():std::to_string(signal.width))+
                (signal.named_event||signal.two_state?"":signal.net?",true":",false")+")";
            if(end-i>=8)out<<"for(size_t registration=0;registration<"<<end-i<<";++registration){"<<call<<";} // signals "<<i<<".."<<end-1<<"\n";
            else for(size_t item=i;item<end;++item)out<<call<<"; // "<<quote(signals[item].name)<<"\n";
            i=end;
        }
        for(const auto& memory:memories)if(memory.fixed_count) {
            const int id=memory.words.front();
            out<<"s.fixed_array("<<sid(id)<<","<<memory.fixed_count<<","<<signals[id].width<<","<<(signals[id].two_state?"true":"false")<<");\n";
        }
        for(int id:unsigned_associative_signals)out<<"s.associative_set_unsigned("<<sid(id)<<");\n";
        for(int id:class_associative_signals)out<<"s.associative_set_class("<<sid(id)<<");\n";
        emit_aggregate_state_masks(out);emit_aggregate_types(out);
        out<<dpi_bindings;
        if(wave_enabled) {
            out<<"if(wave.enabled()) {\n";
            std::set<int> declared_wave_signals;
            for(const auto& sc:scopes)for(const auto& pair:sc->ids)if(!automatic_signals.count(pair.second)&&!foreach_indices.count(pair.second)&&!signals[pair.second].named_event&&!signals[pair.second].text_value&&!dynamic_signals.count(pair.second)&&!object_signals.count(pair.second)&&!struct_string_signals.count(pair.second)&&(!static_wave_paths.count(pair.second)||declared_wave_signals.insert(pair.second).second)) {
                Variable var{sc->symbols.at(pair.first)};
                out<<"wave.declare("<<pair.second<<",{";
                for(const auto& p:static_wave_paths.count(pair.second)?static_wave_paths.at(pair.second):sc->wave_path)out<<quote(p)<<",";
                out<<"},"<<quote(pair.first)<<","<<var->dstart()<<","<<var->dend()<<","<<(signals[pair.second].net?"true":"false")<<","<<(sc->packed.count(pair.first)?"true":"false")<<");\n";
            }
            out<<"}\n";
        }
        for(auto link:bit_links) out<<"s.connect_net("<<link.a<<","<<link.abit<<","<<link.b<<","<<link.bbit<<");\n";
        for(const auto& channel:continuous_channels)out<<channel;
        for(size_t i=0;i<processes.size();++i) {
            const bool bounded=bounded_initial(i);
            if(bounded)out<<"\n#if defined(__clang__) && !defined(DSIM_OPTIMIZE_LARGE_INITIAL)\n#pragma clang optimize off\n#endif\n";
            out<<"s.process([&,pc="<<startup_pc(processes[i]);
            for(int k=0;k<processes[i].repeat_counters;++k) out<<",repeat"<<k<<"=uint64_t(0)";
            for(int k=0;k<processes[i].delay_values;++k) out<<",delay_value"<<k<<"=V()";
            for(size_t k=0;k<processes[i].array_values.size();++k)out<<",array_value"<<k<<"=std::vector<V>("<<processes[i].array_values[k]<<")";
            out<<"]() mutable {";
            if(bounded) {
                emit_bounded_initial(out,i);out<<"});\n#if defined(__clang__) && !defined(DSIM_OPTIMIZE_LARGE_INITIAL)\n#pragma clang optimize on\n#endif\n";
                continue;
            }
            if(compiled_activation(i))emit_compiled_activation(out,i);
            if(comb_leaves[i]) {
                // A partial execution retains its original PC. Only reserve a
                // whole activation when all three instruction steps fit.
                out<<"\n#ifdef DSIM_COMB_LEAF_ENABLED\nif(pc==0&&s.begin_comb_leaf()){\n";
                out<<arm_wait_code(int(i),processes[i].continuous_wait);
                out<<processes[i].instructions[1].code<<"\nreturn;}\n#endif\n";
                // GCC otherwise loses get() inlining in these larger closures.
                // Keep the partial-PC interpreter cold, capturing the same
                // owning closure state by reference only for this invocation.
                out<<"#if defined(DSIM_COMB_LEAF_ENABLED) && defined(__GNUC__) && !defined(__clang__)\n[&]() __attribute__((noinline,cold)) {\n#endif\n";
            }
            if(needs_process_control)out<<"if(int transfer=s.take_process_transfer("<<runtime_pid(int(i))<<");transfer>=0)pc=transfer;";
            out<<" for(;;) { s.process_step(); ";
            if(needs_process_control)out<<"s.process_location("<<runtime_pid(int(i))<<",pc);";
            out<<"switch(pc) {\n";
            auto& instructions=processes[i].instructions;
            for(size_t j=0;j<instructions.size();++j) {
                auto& inst=instructions[j]; out<<"case "<<j<<": { ";
                if(dynamic_forks_enabled())out<<"s.activation_depth("<<inst.activation_depth<<");";
                out<<integral_loop(processes[i],j);
                if(inst.condition) out<<"pc=("<<emit(inst.condition)<<").truth()==1?"<<inst.yes<<":"<<inst.no<<"; continue;";
                else if(inst.yes>=0) out<<"pc="<<inst.yes<<"; continue;";
                else {
                    if(j==0&&comb_members[i].first>=0) {
                        out<<"\n#ifdef DSIM_COMB_REGION_ENABLED\ns.arm_comb_member("<<comb_members[i].first<<","<<comb_members[i].second<<","<<i<<","<<processes[i].continuous_wait<<");\n#else\n"<<inst.code<<"\n#endif\n";
                    } else out<<inst.code;
                    out<<" pc="<<j+1<<"; continue;";
                }
                out<<" }\n";
            }
            out<<"default:";if(needs_process_lifetime)out<<"s.complete_process("<<runtime_pid(int(i))<<");";out<<" return; } }";
            if(comb_leaves[i])out<<"\n#if defined(DSIM_COMB_LEAF_ENABLED) && defined(__GNUC__) && !defined(__clang__)\n}();\n#endif\n";
            if(compiled_activation(i))out<<"\n#ifdef DSIM_COMPILED_ACTIVATION_ENABLED\n}();\n#endif\n";
            out<<" });\n";
        }
        emit_serial_waits(out);
        if(combinational_leaves()) {
            out<<"#ifdef DSIM_COMB_LEAF_BATCH_ENABLED\n"
                 "auto leaf_batch=std::make_shared<uint32_t>(0);\n"
                 "auto leaf_context=s.compiled_context(leaf_batch);\n"
                 "*leaf_batch=s.compiled_handler(leaf_context,[](Sim& s,void* context,uint32_t payload){\n"
                 "s.compiled_leaf_batch(*static_cast<uint32_t*>(context),payload,[&](uint32_t process){switch(process){\n";
            for(size_t i=0;i<processes.size();++i)if(comb_leaves[i]) {
                out<<"case "<<i<<": {\n"
                   <<arm_wait_code(int(i),processes[i].continuous_wait)<<processes[i].instructions[1].code
                   <<"\nbreak;}\n";
            }
            out<<"default: throw std::runtime_error(\"invalid compiled leaf\");}});});\n";
            for(size_t i=0;i<processes.size();++i)if(comb_leaves[i])out<<"s.bind_comb_leaf("<<i<<",*leaf_batch);\n";
            out<<"#endif\n";
        }
        for(const auto& site:event_nba_sites)out<<"s.add_event_nba_site("<<site.events<<(site.expressions.empty()?"":","+site.expressions)<<");\n";
        for(const auto& group:fork_groups) {
            out<<"s.add_fork_group("<<group.parent<<",{";for(int child:group.children)out<<child<<",";out<<"},"<<group.kind<<");\n";
        }
        if(needs_process_control)for(const auto& target:disable_targets) {
            out<<"s.add_disable_target("<<target.process<<","<<target.end<<",{";
            for(size_t group=target.first_group;group<target.last_group;++group)if(disable_group(target,group))out<<group<<",";
            out<<"},"<<target.identity<<","<<target.begin<<");\n";
        }
        configure_dynamic_forks(out);
        for(const auto& call:gate_calls) out<<call;
        emit_clockings(out);
        emit_coverages(out);
        emit_properties(out);
        out<<"s.finish_connections();\n";
        if(gate_design&&gate_design->timing)out<<"s.initialize_module_paths();\n";
        if(needs_termination_unwind)out<<"try {\n";
        emit_initializers(out,true);
        arm_entry_waits(out);emit_aggregate_defaults(out);
        emit_initializers(out,false);
        for(size_t i=0;i<continuous_channels.size();++i)out<<"s.initialize_continuous(continuous_channel"<<i<<");\n";
        if(needs_termination_unwind)out<<"} catch(const SimulationTermination&) {s.suppress_finalization();}\n";
        if(wave_enabled)out<<"wave.start();\n";
        initialize_processes(out);
        out<<"s.run();\n";
        if(wave_enabled)out<<"wave.close();\n";
        if(serial_parallel_stats)out<<"if(parallel_stats)std::cerr<<\"PARALLEL {\\\"partitions\\\":1,\\\"windows\\\":0,\\\"messages\\\":0}\\n\"; // Single partition statistics.\n";
        out<<"return 0;\n} catch(const std::exception& e) { std::cerr<<\"dsim runtime: \"<<e.what()<<'\\n'; return 1; } }\n";
        return out.str();
    }
};
}
static std::string compile_rtl_once(const std::string& source,const std::string& top,const std::string& runtime,std::string* elaboration,const GateDesign* gate,const std::string& waveform,const TimingConfig& timing,const std::string& path_runtime,const std::string& wide_runtime,bool ieee_continuous_delays,bool time_wheel,size_t threads,const std::string& parallel_runtime,bool systemverilog,const std::string& dpi_runtime,const std::vector<std::string>& dpi_libraries,std::string* dpi_header,const std::string& constraint_runtime,SdfTaskHandler sdf_tasks,bool compact_memories,bool shared_functions) {
    if(gate && gate->timing && path_runtime.empty())throw std::runtime_error("missing compiled path runtime");
    auto* parser=VeriParser::get_instance();
    auto stub=gate?gate->stub():std::string();
    const auto prefix=std::count(stub.begin(),stub.end(),'\n');
    Src_mgr::get_instance()->set_src(stub+source+std::string(1,'\0'));
    Src_mgr::get_instance()->set_fname("dsim-input.v");
    if(parser->init()!=OK) throw std::runtime_error("parser initialization failed");
    parser->set_top_module(top);
    parser->set_systemverilog(systemverilog);
    parser->set_time_resolver([timing,prefix](int line) {
        VeriTimeScale result{timing.defaults.unit_fs,timing.defaults.precision_fs,false};
        if(line<=prefix)return result;
        const auto original=size_t(line-prefix);
        auto it=std::upper_bound(timing.modules.begin(),timing.modules.end(),original,
            [](size_t n,const ModuleTimeScale& m){return n<m.line;});
        if(it!=timing.modules.begin()) {
            const auto& entry=*std::prev(it);
            result={entry.scale.unit_fs,entry.scale.precision_fs,entry.directive};
        }
        return result;
    });
    if(parser->parse()!=OK) throw std::runtime_error((::verilog_first_error_line?"line "+std::to_string(::verilog_first_error_line)+": syntax error; ":std::string())+"Verilog parse/semantic analysis failed:\n"+parser->get_err_info());
    auto* mod=parser->module(parser->get_top_module()); if(!mod) throw std::runtime_error("top module not found: "+parser->get_top_module());
    if(compact_memories&&(!waveform.empty()||threads))throw std::runtime_error("--compact-memories requires serial simulation without waveform support");
    if(shared_functions&&threads)throw std::runtime_error("--shared-functions requires serial simulation");
    std::unique_ptr<Lower> completed;
    std::vector<VeriSeqBlock*> class_seeds;
    std::string result;
    for(unsigned pass=0;;++pass) {
        if(pass==64)throw std::runtime_error("class specialization closure exceeds 64 lowering passes");
        auto attempt=std::make_unique<Lower>(mod,gate,!waveform.empty(),timing,std::count(stub.begin(),stub.end(),'\n'),threads);
        attempt->set_shared_functions(shared_functions);
        attempt->set_compact_memories(compact_memories);
        attempt->set_sdf_task_handler(sdf_tasks);
        attempt->set_dpi_libraries(dpi_libraries);
        attempt->class_seeds=class_seeds;
        result=attempt->lower();
        if(!attempt->discovered_late_classes) {completed=std::move(attempt);break;}
        auto discovered=attempt->class_definitions();
        if(discovered.size()<=class_seeds.size())throw std::runtime_error("class specialization closure did not converge");
        class_seeds=std::move(discovered);
    }
    auto& lower=*completed;
    if(gate&&gate->timing&&path_runtime.empty())throw std::runtime_error("missing compiled path runtime");
    if(lower.constraint_functions()) {
        if(constraint_runtime.empty())throw std::runtime_error("missing constraint solver runtime");
        result=(constraint_runtime.rfind("#pragma once\n",0)==0?constraint_runtime.substr(13):constraint_runtime)+"\n"+result;
    }
    if(dpi_header)*dpi_header=lower.dpi_header();
    if(lower.dpi_enabled()&&dpi_runtime.empty())throw std::runtime_error("missing compiled DPI runtime");
    const bool execute_parallel=lower.parallel_execution();
    if(elaboration) {
        *elaboration=lower.report();
        if(time_wheel)elaboration->insert(elaboration->rfind('}'),",\"time_queue\":\"near-far\"\n");
        if(lower.continuous_delays())elaboration->insert(elaboration->rfind('}'),
            std::string(",\"continuous_delay_mode\":\"")+(ieee_continuous_delays?"ieee":"vcs")+"\"\n");
    }
    std::string selected_runtime=runtime;
    if(lower.wide_values()) {
        if(wide_runtime.empty())throw std::runtime_error("missing compiled multiword value runtime");
        const std::string include="#include \"wide_value.hpp\"";auto at=selected_runtime.find(include);
        if(at==std::string::npos)throw std::runtime_error("missing multiword runtime include marker");
        selected_runtime.replace(at,include.size(),wide_runtime.rfind("#pragma once\n",0)==0?wide_runtime.substr(13):wide_runtime);
    }
    return std::string(lower.object_scalar_refs_enabled()?"#define DSIM_OBJECT_SCALAR_REFS_ENABLED 1\n":"")+std::string(lower.array_stream_enabled()?"#define DSIM_ARRAY_STREAM_ENABLED 1\n":"")+std::string(lower.shared_tasks_enabled()?"#define DSIM_SHARED_TASKS_ENABLED 1\n":"")+std::string(lower.process_lifetime_enabled()?"#define DSIM_PROCESS_LIFETIME_ENABLED 1\n":"")+std::string(lower.associative_refs_enabled()?"#define DSIM_ASSOCIATIVE_REFS_ENABLED 1\n":"")+std::string(lower.stop_enabled()?"#define DSIM_STOP_ENABLED 1\n":"")+std::string(lower.termination_unwind_enabled()?"#define DSIM_TERMINATION_UNWIND_ENABLED 1\n":"")+std::string(shared_functions?"#define DSIM_SHARED_FUNCTIONS_ENABLED 1\n":"")+std::string(lower.sdf_annotation_logs()?"#include <fstream>\n":"")+std::string(lower.aggregate_storage_enabled()?"#define DSIM_AGGREGATE_STORAGE_ENABLED 1\n":"")+std::string(lower.coverage_enabled()?"#define DSIM_COVERAGE_ENABLED 1\n":"")+std::string(lower.clocking_enabled()?"#define DSIM_CLOCKING_ENABLED 1\n":"")+std::string(lower.struct_string_values()?"#define DSIM_STRUCT_STRING_ENABLED 1\n":"")+std::string(lower.process_handles_enabled()?"#define DSIM_PROCESS_HANDLES_ENABLED 1\n":"")+std::string(lower.ipc_enabled()?"#define DSIM_IPC_ENABLED 1\n":"")+std::string(lower.constraint_functions()?"#define DSIM_CONSTRAINT_ENABLED 1\n":"")+std::string(lower.real_values()?"#define DSIM_REAL_ENABLED 1\n":"")+std::string(lower.dpi_enabled()?"#define DSIM_DPI_ENABLED 1\n":"")+std::string(lower.typed_stores()&&!lower.object_scalar_refs_enabled()&&!lower.real_values()&&!gate&&!lower.wide_values()&&!lower.text_values()&&!lower.force_enabled()&&!lower.two_state_values()&&!lower.mixed_state_values()?"#if !defined(DSIM_REFERENCE_TYPED_STORES) && !defined(DSIM_REFERENCE_SCALAR_STORES) && (defined(__clang__) || defined(DSIM_EXPERIMENTAL_TYPED_STORES))\n#define DSIM_TYPED_STORES_ENABLED 1\n#endif\n":"")+std::string(lower.compiled_activations()?"#if !defined(DSIM_REFERENCE_COMPILED_ACTIVATION) && (defined(__clang__) || defined(DSIM_EXPERIMENTAL_COMPILED_ACTIVATION))\n#define DSIM_COMPILED_ACTIVATION_ENABLED 1\n#endif\n":"")+std::string(lower.combinational_leaves()?"#if !defined(DSIM_REFERENCE_COMB_LEAVES)\n#define DSIM_COMB_LEAF_ENABLED 1\n#if !defined(DSIM_REFERENCE_LEAF_BATCH) && (defined(__clang__) || defined(DSIM_EXPERIMENTAL_LEAF_BATCH))\n#define DSIM_COMB_LEAF_BATCH_ENABLED 1\n#endif\n#endif\n":"")+std::string(lower.masked_combinational_regions()?"#if !defined(DSIM_REFERENCE_COMB_REGIONS) && !defined(DSIM_DISABLE_WAIT_REARM_CACHE)\n#define DSIM_MASKED_COMB_REGION_ENABLED 1\n#endif\n":"")+std::string(lower.combinational_regions()?"#if !defined(DSIM_REFERENCE_COMB_REGIONS) && !defined(DSIM_DISABLE_WAIT_REARM_CACHE)\n#define DSIM_COMB_REGION_ENABLED 1\n#endif\n":"")+std::string(lower.compiled_waits()?"#if defined(DSIM_EXPERIMENTAL_COMPILED_WAIT) && !defined(DSIM_REFERENCE_COMPILED_WAIT) && !defined(DSIM_DISABLE_WAIT_REARM_CACHE)\n#define DSIM_COMPILED_WAIT_ENABLED 1\n#endif\n":"")+std::string(!gate&&!lower.real_values()&&!lower.wide_values()&&!lower.text_values()&&lower.compact_nba_storage()?"#define DSIM_COMPACT_NBA_STORAGE 1\n":"")+std::string(lower.mixed_state_values()?"#define DSIM_MIXED_STATE_ENABLED 1\n":"")+std::string(lower.force_enabled()?"#define DSIM_FORCE_ENABLED 1\n":"")+std::string(lower.concurrent_properties()?"#define DSIM_PROPERTY_ENABLED 1\n":"")+std::string(lower.sequence_antecedents()?"#define DSIM_PROPERTY_ANTECEDENT_ENABLED 1\n":"")+std::string(lower.text_values()?"#define DSIM_STRING_ENABLED 1\n":"")+std::string(lower.string_replication_enabled()?"#define DSIM_STRING_REPLICATION_ENABLED 1\n":"")+std::string(lower.final_processes_enabled()?"#define DSIM_FINAL_ENABLED 1\n":"")+std::string(lower.scan_enabled()?"#define DSIM_SCAN_ENABLED 1\n":"")+std::string(lower.file_io_enabled()?"#define DSIM_FILE_IO_ENABLED 1\n":"")+std::string(lower.plusargs_enabled()?"#define DSIM_PLUSARGS_ENABLED 1\n":"")+std::string(lower.random_functions()?"#define DSIM_RANDOM_ENABLED 1\n":"")+std::string(lower.dynamic_arrays_enabled()?"#define DSIM_DYNAMIC_ARRAYS_ENABLED 1\n":"")+std::string(lower.queues_enabled()?"#define DSIM_QUEUES_ENABLED 1\n":"")+std::string(lower.associative_enabled()?"#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1\n":"")+std::string(lower.objects_enabled()?"#define DSIM_OBJECTS_ENABLED 1\n":"")+std::string(lower.object_format_enabled()?"#define DSIM_OBJECT_FORMAT_ENABLED 1\n":"")+std::string(lower.object_array_refs_enabled()?"#define DSIM_OBJECT_ARRAY_REFS_ENABLED 1\n":"")+std::string(lower.queue_ref_limits_enabled()?"#define DSIM_QUEUE_REF_LIMITS_ENABLED 1\n":"")+std::string(lower.dynamic_forks_enabled()?"#define DSIM_DYNAMIC_FORK_ENABLED 1\n":"")+std::string(lower.function_forks_enabled()?"#define DSIM_FUNCTION_FORKS_ENABLED 1\n":"")+std::string(lower.process_control_enabled()?"#define DSIM_PROCESS_CONTROL_ENABLED 1\n":"")+std::string(lower.fork_join_enabled()?"#define DSIM_FORK_JOIN_ENABLED 1\n":"")+std::string(lower.event_nba_enabled()?"#define DSIM_EVENT_NBA_ENABLED 1\n":"")+std::string(lower.expression_events_enabled()?"#define DSIM_EXPRESSION_EVENTS_ENABLED 1\n":"")+std::string(lower.wait_order_enabled()?"#define DSIM_WAIT_ORDER_ENABLED 1\n":"")+std::string(lower.named_events_enabled()?"#define DSIM_NAMED_EVENTS_ENABLED 1\n":"")+std::string(lower.event_aliases_enabled()?"#define DSIM_EVENT_ALIASES_ENABLED 1\n":"")+std::string(lower.variable_continuous()?"#define DSIM_CONTINUOUS_VARIABLE_ENABLED 1\n":"")+std::string(lower.selection_checks()?"#define DSIM_SELECTION_CHECKS_ENABLED 1\n":"")+std::string(lower.vector_system_functions()?"#define DSIM_VECTOR_SYSTEM_FUNCTIONS 1\n":"")+std::string(lower.two_state_values()?"#define DSIM_TWO_STATE_ENABLED 1\n":"")+std::string(lower.memory_io()?"#define DSIM_MEMORY_IO_ENABLED 1\n":"")+std::string(lower.indexed_selects()?"#define DSIM_INDEXED_SELECT_ENABLED 1\n":"")+std::string(execute_parallel?"#define DSIM_PARALLEL_ENABLED 1\n":"")+std::string(lower.replication()?"#define DSIM_REPLICATION_ENABLED 1\n":"")+std::string(lower.dump_tasks()?"#define DSIM_DUMP_TASKS_ENABLED 1\n":"")+std::string(time_wheel?"#define DSIM_TIME_WHEEL_ENABLED 1\n":"")+std::string(gate?"#include <array>\n":"")+"// Generated by dsim 0.13.0. Compile with C++17.\n"+std::string(gate?"#define DSIM_COMPACT_GATES 1\n":"")+std::string(gate&&gate->batch_enabled?"#define DSIM_BATCH_ENABLED 1\n":"")+std::string(gate&&gate->scalar_timing_enabled?"#define DSIM_SCALAR_TIMING_ENABLED 1\n":"")+std::string(gate&&gate->sdf_jobs_enabled?"#define DSIM_SDF_JOBS_ENABLED 1\n":"")+std::string((gate&&gate->timing)||lower.continuous_delays()?"#define DSIM_TIMING_ENABLED 1\n":"")+std::string(gate&&gate->timing?"#define DSIM_PATH_ENABLED 1\n":"")+std::string(gate&&gate->timing&&gate->timing->conditional_paths?"#define DSIM_CONDITIONAL_PATH_ENABLED 1\n":"")+std::string(lower.continuous_delays()?"#define DSIM_CONTINUOUS_DELAY_ENABLED 1\n":"")+std::string(lower.continuous_delays()&&ieee_continuous_delays?"#define DSIM_CONTINUOUS_DELAY_IEEE_MODE 1\n":"")+std::string(gate&&gate->timing&&!gate->timing->checks.empty()?"#define DSIM_CHECKS_ENABLED 1\n":"")+std::string(waveform.empty()?"":"#define DSIM_WAVE_ENABLED 1\n")+std::string(lower.wide_values()?"#define DSIM_WIDE_VALUES 1\n":"")+std::string(lower.delayed_nba_updates()?"#define DSIM_DELAYED_NBA_ENABLED 1\n":"")+std::string(lower.dynamic_delays()?"#define DSIM_DYNAMIC_DELAY_ENABLED 1\n":"")+(selected_runtime.rfind("#pragma once\n",0)==0?selected_runtime.substr(13):selected_runtime)+"\n"+path_runtime+"\n"+waveform+(execute_parallel&&!parallel_runtime.empty()?"\n"+parallel_runtime:std::string())+"\n"+(lower.dpi_enabled()?dpi_runtime:std::string())+"\n"+result;
}
std::string compile_rtl(const std::string& source,const std::string& top,const std::string& runtime,std::string* elaboration,const GateDesign* gate,const std::string& waveform,const TimingConfig& timing,const std::string& path_runtime,const std::string& wide_runtime,bool ieee_continuous_delays,bool time_wheel,size_t threads,const std::string& parallel_runtime,bool systemverilog,const std::string& dpi_runtime,const std::vector<std::string>& dpi_libraries,std::string* dpi_header,const std::string& constraint_runtime,SdfTaskHandler sdf_tasks,bool compact_memories,bool shared_functions) {
    try {
        return compile_rtl_once(source,top,runtime,elaboration,gate,waveform,timing,path_runtime,wide_runtime,ieee_continuous_delays,time_wheel,threads,parallel_runtime,systemverilog,dpi_runtime,dpi_libraries,dpi_header,constraint_runtime,sdf_tasks,compact_memories,shared_functions);
    } catch(const InlineExpansionLimit&) {
        if(shared_functions||threads||gate)throw;
        // The failed lowering is destroyed before parser init clears its AST.
        // Retry once with the existing shared-body backend. No design names,
        // library paths or source rewriting participate in this decision.
        std::cerr<<"dsim: inline function budget exceeded; using shared function bodies\n";
        return compile_rtl_once(source,top,runtime,elaboration,gate,waveform,timing,path_runtime,wide_runtime,ieee_continuous_delays,time_wheel,threads,parallel_runtime,systemverilog,dpi_runtime,dpi_libraries,dpi_header,constraint_runtime,sdf_tasks,compact_memories,true);
    }
}
}
