// Static SystemVerilog type names. Keep reflection independent of runtime values.
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_var.hpp"
#include "veri_tfmg.hpp"
#include "veri_num.hpp"
#include "veri_symbol_table.hpp"
#include "veri_module.hpp"
#include <algorithm>
#include <stdexcept>

namespace rtl {
namespace {
std::string qualified(VeriNode* symbol,const std::string& name) {
  std::string prefix;
  for(auto* scope=symbol->scope();scope;scope=scope->floater()) {
    if(auto* owner=scope->class_owner()) {
      auto text=owner->type_name();prefix=text.substr(6)+"::"+prefix;break;
    }
    if(!scope->name().empty()) {
      auto* mod=symbol->birth_mod();
      const bool lexical_namespace=scope->table_type()==vMOD_SCOPE&&(!mod||mod->is_package()||mod->is_compilation_unit());
      prefix=scope->name()+(lexical_namespace?"::":".")+prefix;
    }
  }
  return prefix+name;
}
std::string builtin(int type,bool sign) {
  switch(type) {
    case vvINT2:return sign?"int":"int unsigned";
    case vvINT:return sign?"integer":"integer unsigned";
    case vvBYTE:return sign?"byte":"byte unsigned";
    case vvSHORTINT:return sign?"shortint":"shortint unsigned";
    case vvLONGINT:return sign?"longint":"longint unsigned";
    case vvTIME:return sign?"time signed":"time";
    case vvREAL:case vvREALTIME:return "real";
    case vvSHORTREAL:return "shortreal";
    case vvSTRING:return "string";
    case vvCHANDLE:return "chandle";
    case vvEVENT:return "event";
    default:return std::string(type==vvBIT?"bit":type==vvREG?"reg":"logic")+(sign?" signed":"");
  }
}
std::string dimension(std::pair<int,int> d) {return "["+std::to_string(d.first)+":"+std::to_string(d.second)+"]";}
std::string array_suffix(VeriNode* node,const VeriArrayShape& shape,unsigned consumed=0) {
  std::string result;
  for(int axis=0;axis<shape.unpacked;++axis) {
    const int kind=veri_array_container_kind(node,axis+consumed);
    if(result.empty())result="$";
    if(kind==vrQUEUE) {
      int bound=-1;
      if(node->tok_type()==vtVAR||node->tok_type()==vtTYPE)bound=static_cast<VeriVar*>(node)->container_bound(axis+consumed);
      else if(node->tok_type()==vtTFVAR)bound=static_cast<VeriTfVar*>(node)->container_bound(axis+consumed);
      result+=bound<0?"[$]":"[$:"+std::to_string(bound)+"]";
    } else if(kind==vrOPEN)result+="[]";
    else if(kind==vrASSOC_STRING)result+="[string]";
    else if(kind==vrASSOC_INT||kind==vrASSOC_UINT||kind==vrASSOC_CLASS) {
      auto* key=veri_associative_key_type(node,axis+consumed);
      if(!key&&kind==vrASSOC_CLASS)throw std::runtime_error("unresolved $typename class index type");
      result+="["+(key?veri_type_name(key):kind==vrASSOC_INT?std::string("int"):std::string("int unsigned"))+"]";
    } else result+=dimension(shape.dimensions[axis]);
  }
  return result;
}
std::string symbol_name(VeriNode* n) {
  int type=vvINT2;bool sign=true;VeriVar* var=nullptr;
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE) {var=static_cast<VeriVar*>(n);type=var->net_type();sign=var->is_signed()==IS_TRUE;}
  else if(n->tok_type()==vtTFVAR) {auto* v=static_cast<VeriTfVar*>(n);type=v->net_type();sign=v->is_signed()==IS_TRUE;}
  else if(n->tok_type()==vtFUNC) {
    auto* fn=static_cast<VeriFunc*>(n);auto* decl=fn->func();
    if(decl->is_void())return "void";
    if(decl->resolved_type())return veri_type_name(decl->resolved_type());
    type=decl->result_type();sign=decl->is_signed()==IS_TRUE;
  } else if(n->tok_type()==vtPARAM) {
    auto* decl=static_cast<VeriParamDecl*>(n->father());
    if(decl->resolved_type())return veri_type_name(decl->resolved_type());
    if(decl->typed()) {type=decl->data_type();sign=decl->is_signed()==IS_TRUE;}
    else throw std::runtime_error("$typename of an untyped parameter is not supported yet");
  } else if(n->tok_type()==vtINT)type=vvINT;
  else if(n->tok_type()!=vtGENVAR)throw std::runtime_error("unsupported $typename symbol");
  auto shape=veri_array_shape(n);std::string result;
  if(auto* cls=veri_class_type(n))result=cls->type_name();
  else if(auto* enumeration=veri_enum_type(n))result="enum "+qualified(enumeration,enumeration->name());
  else if(auto* aggregate=veri_aggregate_type(n)) {
    const bool is_union=aggregate->father()&&aggregate->father()->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(aggregate->father())->aggregate_kind()==2;
    result=std::string(is_union?"union ":"struct ")+qualified(aggregate,aggregate->name());
  }
  else {
    if(type==vvCLASS)throw std::runtime_error("$typename requires a resolved class type");
    result=builtin(type,sign);
    if(!veri_integral_atom(type))
      for(size_t axis=shape.unpacked;axis<shape.dimensions.size();++axis)result+=dimension(shape.dimensions[axis]);
  }
  return result+array_suffix(n,shape);
}
}
std::string VeriSeqBlock::type_name() const {
  if(!_class_origin)return "class "+qualified(_class_symbol,_label);
  auto result="class "+qualified(_class_origin->class_symbol(),_class_origin->label())+"#(";
  for(size_t i=0;i<_class_parameter_order.size();++i) {
    if(i)result+=",";
    auto* symbol=_class_bindings.at(_class_parameter_order[i]);
    if(symbol->tok_type()==vtTYPE)result+=veri_type_name(symbol);
    else {
      auto* number=static_cast<VeriParam*>(symbol)->get_val();
      if(number->string_type()) {
        const auto value=number->string_value();
        for(unsigned char c:value)if(c<32||c=='"'||c=='\\')
          throw std::runtime_error("$typename of escaped class string parameters is not supported yet");
        result+='"'+value+'"';
      }
      else if(number->real_width())throw std::runtime_error("$typename of real class parameters is not supported yet");
      else {
        if(number->no_xz()!=IS_TRUE)throw std::runtime_error("$typename of unknown class parameters is not supported yet");
        const bool negative=number->is_signed()==IS_TRUE&&number->get_certain_bit(number->bits()-1)==V1;
        std::vector<unsigned> bits(number->bits());unsigned carry=negative?1:0;
        for(int bit=0;bit<number->bits();++bit) {unsigned value=(number->get_certain_bit(bit)==V1)^negative;value+=carry;bits[bit]=value&1;carry=value>>1;}
        std::string decimal="0";
        for(int bit=number->bits();bit-->0;) {unsigned add=bits[bit];for(size_t digit=decimal.size();digit-->0;) {unsigned value=(decimal[digit]-'0')*2+add;decimal[digit]=char('0'+value%10);add=value/10;}if(add)decimal.insert(decimal.begin(),char('0'+add));}
        result+=(negative?"-":"")+decimal;
      }
    }
  }
  return result+")";
}
std::string veri_type_name(VeriNode* n) {
  if(!n)throw std::runtime_error("unresolved $typename operand");
  if(n->tok_type()!=vtEXP)return symbol_name(n);
  switch(n->detail_type()) {
    case veEXP_TYPE:return veri_type_name(static_cast<VeriTypeExp*>(n)->resolved_type());
    case veEXP_PRI:{auto* p=static_cast<VeriPrimaryExp*>(n);
      if(p->pri_type()==veVAR)return veri_type_name(p->var());
      auto* value=p->calc_value();if(!value)break;
      if(value->real_width())return "real";
      if(p->pri_type()==veNUM&&p->str().find('\'')==std::string::npos)return "int";
      return std::string(value->no_xz()==IS_TRUE?"bit":"logic")+(value->is_signed()==IS_TRUE?" signed":"")+dimension({value->bits()-1,0});
    }
    case veEXP_CALLER:{auto* call=static_cast<VeriCallerExp*>(n);auto* hive=veri_call_hive(n);
      if(hive&&hive->detail_type()==vsDECL_FUNC_DECL) {
        auto* f=static_cast<VeriFuncDecl*>(hive);if(f->is_void())return "void";
        if(f->resolved_type())return veri_type_name(f->resolved_type());
        return veri_type_name(call->scope()->value_within_module(f->func_name()));
      }
      break;
    }
    case veEXP_MEMBER:{auto* m=static_cast<VeriMemberExp*>(n);
      if(m->class_member())return veri_type_name(m->class_member());
      if(m->hierarchical_symbol())return veri_type_name(m->hierarchical_symbol());
      if(m->field())return veri_type_name(m->field()->symbol);
      break;
    }
    case veEXP_ARRAY:{auto* a=static_cast<VeriArrayExp*>(n);auto original=veri_array_shape(a->id());auto shape=veri_array_shape(n);
      auto name=veri_type_name(a->id());
      // Only strip dimensions of the outer value; $unit and packed dimensions
      // inside a class's parameter list are part of its canonical type name.
      size_t suffix=std::string::npos;unsigned parentheses=0;bool quoted=false,escaped=false;
      for(size_t i=0;i<name.size();++i) {
        const char c=name[i];
        if(quoted){if(escaped)escaped=false;else if(c=='\\')escaped=true;else if(c=='"')quoted=false;continue;}
        if(c=='"')quoted=true;else if(c=='(')++parentheses;else if(c==')'&&parentheses)--parentheses;
        else if(c=='['&&!parentheses&&i&&name[i-1]=='$'){suffix=i-1;break;}
      }
      if(suffix!=std::string::npos)name.resize(suffix);
      unsigned consumed=std::min(size_t(original.unpacked),a->range().size());
      if(a->range().size()>size_t(original.unpacked)) {
        auto* symbol=veri_array_element_symbol(a->id());int type=vvLOGIC;
        if(symbol&&(symbol->tok_type()==vtVAR||symbol->tok_type()==vtTYPE))type=static_cast<VeriVar*>(symbol)->net_type();
        else if(symbol&&symbol->tok_type()==vtTFVAR)type=static_cast<VeriTfVar*>(symbol)->net_type();
        else if(symbol&&symbol->tok_type()==vtFUNC)type=static_cast<VeriFunc*>(symbol)->func()->result_type();
        if(type==vvSTRING)throw std::runtime_error("$typename of string character selections is not supported yet");
        name=type==vvREG?"reg":veri_two_state(type)?"bit":"logic";
        auto* last=static_cast<VeriRangeExp*>(a->range().back());
        if(last->rtype()==vrSEMI&&!shape.dimensions.empty())shape.dimensions.front()={last->range_from(),last->range_to()};
        for(size_t axis=shape.unpacked;axis<shape.dimensions.size();++axis)name+=dimension(shape.dimensions[axis]);
      }
      return name+array_suffix(a->id(),shape,consumed);
    }
    case veEXP_UNA:if(static_cast<VeriUnaryExp*>(n)->op()==vtSYS_TYPENAME)return "string";break;
    default:break;
  }
  if(veri_dynamic_string_value(n))return "string";
  throw std::runtime_error("line "+std::to_string(n->line())+": unsupported $typename expression");
}
} // namespace rtl
