/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_exp.cpp
 * Summary  : verilog syntax analyzer :: expression
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */

#include <assert.h>
#include <iterator>
#include <stdexcept>

#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_symbol_table.hpp"

#include "veri_num.hpp"
#include "veri_tfmg.hpp"
#include "veri_inst.hpp"

#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_str.hpp"

#include "veri_module.hpp"
#include "veri_parser.hpp"

namespace rtl
{
void veri_declare_implicit_wire(VeriNode* node,VeriSymbolTable* context) {
  if(!node||node->detail_type()!=veEXP_PRI||context->table_type()!=vMOD_SCOPE)return;
  auto* id=static_cast<VeriPrimaryExp*>(node);
  if(id->pri_type()!=veVAR||context->value_within_module(id->str()))return;
  auto* owner=node->father();while(owner&&owner->tok_type()!=vtMOD)owner=owner->father();
  if(!owner)return;
  auto* module=static_cast<VeriMod*>(owner);
  auto* name=new VeriPrimaryExp(veri_parser->next_id(),id->line(),id->col(),id->str(),veVAR,module);
  auto* declaration=new VeriVarDecl(veri_parser->next_id(),id->line(),id->col(),vpNO_IO,vvWIRE,IS_FALSE,vpSCALAR,nullptr,nullptr,nullptr,module);
  veri_parser->insert_node(name);veri_parser->insert_node(declaration);
  declaration->vars().push_back(name);name->set_father(declaration);
  auto* items=static_cast<VeriModuleItemList*>(module->item());
  declaration->set_father(items);items->item_list().push_back(declaration);
  veri_bind_semantic(declaration,context);
}
static VeriNode* member_result(VeriNode* node) {
  if(!node||node->tok_type()!=vtEXP||node->detail_type()!=veEXP_MEMBER)return nullptr;
  if(auto* result=static_cast<VeriMemberExp*>(node)->array_result())return result;
  auto* hive=static_cast<VeriMemberExp*>(node)->hive();
  if(!hive||hive->detail_type()!=vsDECL_FUNC_DECL)return nullptr;
  auto* fn=static_cast<VeriFuncDecl*>(hive);
  return fn->is_void()?nullptr:fn->scope()->value_within_module(fn->func_name());
}
bool veri_chandle_value(VeriNode* n) {
  if(!n)return false;
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->net_type()==vvCHANDLE;
  if(n->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(n)->net_type()==vvCHANDLE;
  if(n->tok_type()==vtFUNC)return static_cast<VeriFunc*>(n)->func()->result_type()==vvCHANDLE;
  if(n->tok_type()!=vtEXP)return false;
  switch(n->detail_type()) {
    case veEXP_PRI:return veri_chandle_value(static_cast<VeriPrimaryExp*>(n)->var());
    case veEXP_ARRAY:return veri_chandle_value(static_cast<VeriArrayExp*>(n)->id());
    case veEXP_CALLER:{auto* h=veri_call_hive(n);return h&&h->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(h)->result_type()==vvCHANDLE;}
    case veEXP_MEMBER:{if(auto* r=member_result(n))return veri_chandle_value(r);auto* m=static_cast<VeriMemberExp*>(n);return veri_chandle_value(m->class_member()?m->class_member():m->hierarchical_symbol());}
    case veEXP_BIN:return static_cast<VeriBinaryExp*>(n)->op()==vtCAST_CHANDLE;
    case veEXP_QUES:{auto* q=static_cast<VeriQuesExp*>(n);return veri_chandle_value(q->choice1())||veri_chandle_value(q->choice2());}
    default:return false;
  }
}
int veri_real_width(VeriNode* n) {
  if(!n)return 0;
  int type=0;
  if(n->tok_type()==vtSYS_VAR)return static_cast<VeriSysVar*>(n)->name()=="$realtime"?64:0;
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)type=static_cast<VeriVar*>(n)->net_type();
  else if(n->tok_type()==vtTFVAR)type=static_cast<VeriTfVar*>(n)->net_type();
  else if(n->tok_type()==vtFUNC)type=static_cast<VeriFunc*>(n)->func()->result_type();
  else if(n->tok_type()==vtNUM)return static_cast<VeriNum*>(n)->real_width();
  else if(n->tok_type()==vtPARAM)return static_cast<VeriParam*>(n)->get_val()->real_width();
  else if(n->tok_type()==vtEXP) {
    if(auto* cached=static_cast<VeriExp*>(n)->calc_value())if(cached->real_width())return cached->real_width();
    switch(n->detail_type()) {
      case veEXP_PRI:return veri_real_width(static_cast<VeriPrimaryExp*>(n)->var());
      case veEXP_ARRAY:return veri_real_width(static_cast<VeriArrayExp*>(n)->id());
      case veEXP_MEMBER:{auto* m=static_cast<VeriMemberExp*>(n);if(m->coverage_builtin()&&(m->member()=="get_coverage"||m->member()=="get_inst_coverage"))return 64;return veri_real_width(m->called()?member_result(n):m->class_member());}
      case veEXP_CALLER:{auto* hive=static_cast<VeriCallerExp*>(n)->hive();if(hive&&hive->detail_type()==vsDECL_FUNC_DECL){auto* f=static_cast<VeriFuncDecl*>(hive);return veri_real(f->result_type())?veri_type_width(f->result_type()):0;}return 0;}
      case veEXP_UNA:{auto* u=static_cast<VeriUnaryExp*>(n);if(u->op()==vtSYS_ITOR||u->op()==vtSYS_BITSTOREAL)return 64;if(u->op()==vtSYS_BITSTOSHORTREAL)return 32;return u->op()==vtUADD||u->op()==vtUSUB?veri_real_width(u->exp_child()):0;}
      case veEXP_BIN:{auto* b=static_cast<VeriBinaryExp*>(n);if(b->op()==vtCAST_REAL)return 64;if(b->op()==vtCAST_SHORTREAL)return 32;if(veri_is_cast(b->op()))return 0;return b->op()==vtBADD||b->op()==vtBSUB||b->op()==vtBMUL||b->op()==vtBDIV||b->op()==vtBPOW?std::max(veri_real_width(b->lval()),veri_real_width(b->rval())):0;}
      case veEXP_QUES:{auto* q=static_cast<VeriQuesExp*>(n);return std::max(veri_real_width(q->choice1()),veri_real_width(q->choice2()));}
      default:return 0;
    }
  }
  return veri_real(type)?veri_type_width(type):0;
}
static bool string_kind(VeriNode* n,bool literals) {
  if(!n)return false;
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->net_type()==vvSTRING;
  if(n->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(n)->net_type()==vvSTRING;
  if(n->tok_type()==vtFUNC)return static_cast<VeriFunc*>(n)->func()->result_type()==vvSTRING;
  if(n->tok_type()==vtPARAM)return static_cast<VeriParam*>(n)->get_val()->string_type();
  if(n->tok_type()!=vtEXP)return false;
  if(n->detail_type()==veEXP_PRI){auto* p=static_cast<VeriPrimaryExp*>(n);return (literals&&p->pri_type()==veSTR)||string_kind(p->var(),literals);}
  if(n->detail_type()==veEXP_ARRAY){auto* a=static_cast<VeriArrayExp*>(n);return string_kind(a->id(),literals)&&veri_array_shape(a->id()).unpacked>0&&a->range().size()==size_t(veri_array_shape(a->id()).unpacked);}
  if(n->detail_type()==veEXP_CALLER){auto* declaration=static_cast<VeriCallerExp*>(n)->hive();return declaration&&declaration->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(declaration)->result_type()==vvSTRING;}
  if(n->detail_type()==veEXP_MEMBER){if(auto* ret=member_result(n))return string_kind(ret,literals);auto* m=static_cast<VeriMemberExp*>(n);if(m->process_builtin()&&m->member()=="get_randstate")return true;if(m->hierarchical_symbol())return string_kind(m->hierarchical_symbol(),literals);if(m->field())return string_kind(m->field()->symbol,literals);return (m->method_type()&&m->member()=="name")||((m->member()=="pop_front"||m->member()=="pop_back")&&string_kind(m->object(),literals))||(string_kind(m->object(),literals)&&(m->member()=="substr"||m->member()=="toupper"||m->member()=="tolower"));}
  if(n->detail_type()==veEXP_UNA&&(static_cast<VeriUnaryExp*>(n)->op()==vtSYS_SFORMATF||static_cast<VeriUnaryExp*>(n)->op()==vtSYS_TYPENAME))return true;
  if(n->detail_type()==veEXP_BIN&&static_cast<VeriBinaryExp*>(n)->op()==vtCAST_STRING)return true;
  if(n->detail_type()==veEXP_QUES){auto* q=static_cast<VeriQuesExp*>(n);return string_kind(q->choice1(),literals)||string_kind(q->choice2(),literals);}
  if(n->detail_type()==veEXP_MCONCAT) {
    auto* repeat=static_cast<VeriMultiConcatExp*>(n);
    return string_kind(repeat->exp2(),literals)||(!literals&&!veri_elaboration_constant(repeat->exp1())&&string_kind(repeat->exp2(),true));
  }
  if(n->detail_type()==veEXP_MULTI){auto* m=static_cast<VeriMultiExp*>(n);if(m->multi_type()!=vemCONCAT_EXP)return false;for(auto* item:m->exp())if(string_kind(item,literals))return true;}
  return false;
}

bool veri_string_value(VeriNode* n){return string_kind(n,true);}
bool veri_dynamic_string_value(VeriNode* n){return string_kind(n,false);}

std::vector<VeriNode*> veri_system_arguments(VeriNode* expression) {
  if(!expression)return {};
  if(expression->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(expression)->multi_type()==vemCOMMA_EXP) {
    auto& items=static_cast<VeriMultiExp*>(expression)->exp();return {items.begin(),items.end()};
  }
  return {expression};
}

int veri_array_reduction_name(const std::string& name) {
  if(name=="sum")return vtBADD;if(name=="product")return vtBMUL;
  if(name=="and")return vtBSAND;if(name=="or")return vtBSOR;if(name=="xor")return vtBSXOR;return 0;
}
int veri_array_reduction(VeriNode* n) {
  if(!n||n->tok_type()!=vtEXP||n->detail_type()!=veEXP_MEMBER)return 0;
  auto* method=static_cast<VeriMemberExp*>(n);if(method->hive()||method->class_owner())return 0;const int op=veri_array_reduction_name(method->member());
  return op&&veri_array_shape(method->object()).unpacked?op:0;
}
bool veri_array_locator(VeriNode* n) {
  if(!n||n->tok_type()!=vtEXP||n->detail_type()!=veEXP_MEMBER)return false;
  auto* m=static_cast<VeriMemberExp*>(n);
  if(m->hive()||m->class_owner()||!veri_array_shape(m->object()).unpacked)return false;
  const auto& name=m->member();
  return name=="unique"||name=="unique_index"||name=="find"||name=="find_index"||
    name=="find_first"||name=="find_first_index"||name=="find_last"||name=="find_last_index"||name=="min"||name=="max";
}
bool veri_array_ordering(VeriNode* n) {
  if(!n||n->tok_type()!=vtEXP||n->detail_type()!=veEXP_MEMBER)return false;
  auto* m=static_cast<VeriMemberExp*>(n);
  if(m->hive()||m->class_owner()||!veri_array_shape(m->object()).unpacked)return false;
  return m->member()=="sort"||m->member()=="rsort"||m->member()=="reverse";
}
VeriNode* veri_event_symbol(VeriNode* expression) {
  if(!expression)return nullptr;
  auto* symbol=expression;
  if(expression->tok_type()==vtEXP&&expression->detail_type()==veEXP_PRI)symbol=static_cast<VeriPrimaryExp*>(expression)->var();
  else if(expression->tok_type()==vtEXP&&expression->detail_type()==veEXP_MEMBER) {
    auto* member=static_cast<VeriMemberExp*>(expression);
    if(member->called())return nullptr;
    symbol=member->class_member()?member->class_member():member->hierarchical_symbol();
  }
  return symbol&&symbol->tok_type()==vtVAR&&static_cast<VeriVar*>(symbol)->net_type()==vvEVENT?symbol:nullptr;
}
VeriNode* veri_array_element_symbol(VeriNode* object) {
  if(!object)return nullptr;
  if(object->detail_type()==veEXP_MEMBER)
    if(auto* result=static_cast<VeriMemberExp*>(object)->array_result())return result;
  if(object->detail_type()==veEXP_ARRAY)object=static_cast<VeriArrayExp*>(object)->id();
  if(auto* result=member_result(object))return result;
  if(object->detail_type()==veEXP_CALLER) {
    auto* hive=static_cast<VeriCallerExp*>(object)->hive();
    if(hive&&hive->detail_type()==vsDECL_FUNC_DECL) {
      auto* fn=static_cast<VeriFuncDecl*>(hive);return fn->scope()->value_within_module(fn->func_name());
    }
  }
  auto* symbol=object->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(object)->var():object->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(object)->hierarchical_symbol():object;
  return symbol&&(symbol->tok_type()==vtVAR||symbol->tok_type()==vtINT||symbol->tok_type()==vtTFVAR||symbol->tok_type()==vtFUNC)?symbol:nullptr;
}
VeriVar* veri_associative_key_type(VeriNode* symbol,unsigned axis) {
  if(!symbol)return nullptr;
  if(symbol->tok_type()==vtEXP) {
    if(symbol->detail_type()==veEXP_ARRAY) {auto* a=static_cast<VeriArrayExp*>(symbol);return veri_associative_key_type(a->id(),axis+a->range().size());}
    return veri_associative_key_type(veri_array_element_symbol(symbol),axis);
  }
  if(symbol->tok_type()==vtVAR||symbol->tok_type()==vtTYPE)return static_cast<VeriVar*>(symbol)->associative_key_type(axis);
  if(symbol->tok_type()==vtINT)return static_cast<VeriInt*>(symbol)->associative_key_type(axis);
  if(symbol->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(symbol)->associative_key_type(axis);
  if(symbol->tok_type()==vtFUNC)return veri_associative_key_type(static_cast<VeriFunc*>(symbol)->func()->resolved_type(),axis);
  return nullptr;
}
bool veri_queue_slice(VeriNode* expression) {
  if(!expression||expression->tok_type()!=vtEXP||expression->detail_type()!=veEXP_ARRAY)return false;
  auto* array=static_cast<VeriArrayExp*>(expression);
  if(array->range().size()!=1||static_cast<VeriRangeExp*>(array->range().front())->rtype()!=vrSEMI)return false;
  auto* symbol=veri_array_element_symbol(expression);
  return symbol&&veri_array_container_kind(symbol,0)==vrQUEUE&&veri_array_shape(symbol).unpacked==1;
}
int veri_array_container_kind(VeriNode* symbol,unsigned axis) {
  if(!symbol)return vrSINGLE;
  if(symbol->tok_type()==vtEXP) {
    if(symbol->detail_type()==veEXP_ARRAY) {auto* a=static_cast<VeriArrayExp*>(symbol);return veri_array_container_kind(a->id(),axis+(veri_queue_slice(symbol)?0:a->range().size()));}
    return veri_array_container_kind(veri_array_element_symbol(symbol),axis);
  }
  if(symbol->tok_type()==vtFUNC)return veri_array_container_kind(static_cast<VeriFunc*>(symbol)->func()->resolved_type(),axis);
  if(symbol->tok_type()==vtVAR||symbol->tok_type()==vtTYPE)return static_cast<VeriVar*>(symbol)->container_kind(axis);
  if(symbol->tok_type()==vtINT)return static_cast<VeriInt*>(symbol)->container_kind(axis);
  if(symbol->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(symbol)->container_kind(axis);
  return vrSINGLE;
}

namespace {
VeriNode* queue_pop_element(VeriNode* node) {
  if(!node||node->tok_type()!=vtEXP||node->detail_type()!=veEXP_MEMBER)return nullptr;
  auto* member=static_cast<VeriMemberExp*>(node);
  if(!member->called()||(member->member()!="pop_front"&&member->member()!="pop_back"))return nullptr;
  auto* symbol=veri_array_element_symbol(member->object());
  if(!symbol)return nullptr;
  const int kind=veri_array_container_kind(symbol);
  return kind==vrQUEUE&&veri_array_shape(member->object()).unpacked==1?symbol:nullptr;
}
}
int veri_array_element_width(VeriNode* object) {
  auto* symbol=veri_array_element_symbol(object);
  if(symbol){if(symbol->tok_type()==vtFUNC)return static_cast<VeriFunc*>(symbol)->dlen();if(symbol->tok_type()==vtVAR)return static_cast<VeriVar*>(symbol)->dlen();if(symbol->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(symbol)->dlen();return 32;}
  throw std::runtime_error("array reduction requires unpacked integral storage");
}

// Shared by bare references and the independent packed-select binding path.
static VeriVar* reduction_binding(VeriNode* expression,const std::string& name) {
  for(auto* child=expression,*parent=expression->father();parent;child=parent,parent=parent->father()) {
    if(parent->tok_type()!=vtEXP||parent->detail_type()!=veEXP_MEMBER)continue;
    auto* method=static_cast<VeriMemberExp*>(parent);
    if(method->with_expression()==child&&method->iterator()&&method->iterator_name()==name)return method->iterator();
  }
  return nullptr;
}

// Packed declaration chains keep source dimensions while storage stays linear.
static std::vector<std::pair<int,int>> packed_dimensions(VeriNode* symbol,int first,int last) {
  VeriNode* range=nullptr;
  if(symbol->tok_type()==vtFUNC)range=static_cast<VeriFunc*>(symbol)->func()->range();
  else if(symbol->father()&&symbol->father()->tok_type()==vtDECL) {
    auto* declaration=symbol->father();
    if(declaration->detail_type()==vsDECL_VAR) {
      auto* variable=static_cast<VeriVarDecl*>(declaration);range=variable->range();
      if(!range&&variable->resolved_type()) {
        auto* type=variable->resolved_type();return packed_dimensions(type,type->dstart(),type->dend());
      }
    }
    else if(declaration->detail_type()==vsDECL_TF_DECL)range=static_cast<VeriTfDecl*>(declaration)->range();
    else if(declaration->detail_type()==vsDECL_PARAM)range=static_cast<VeriParamDecl*>(declaration)->range();
  }
  if(range&&static_cast<VeriRangeExp*>(range)->packed_next())return static_cast<VeriRangeExp*>(range)->packed_dimensions();
  return {{first,last}};
}

static bool interface_instance_value(VeriNode* symbol) {
  if(!symbol||symbol->tok_type()!=vtMOD_INST)return false;
  auto* instance=static_cast<VeriModInstance*>(static_cast<VeriModInst*>(symbol)->instance());
  auto* declaration=static_cast<VeriModInstantiation*>(instance->father());return declaration->inst_mod()&&declaration->inst_mod()->is_interface();
}
// Metadata only: indices and function operands are bound, never evaluated.
VeriArrayShape veri_array_shape(VeriNode* n) {
  auto bad=[&]()->VeriArrayShape {throw std::runtime_error("line "+std::to_string(n?n->line():0)+": unsupported array query operand");};
  auto packed=[](int left,int right)->VeriArrayShape {VeriArrayShape s;s.dimensions.push_back({left,right});return s;};
  auto checked_range=[&](VeriRangeExp* r)->VeriArrayShape {
    if(r->rtype()!=vrSEMI||r->not_calc()==IS_TRUE||!veri_elaboration_constant(r->left())||!veri_elaboration_constant(r->right()))return bad();
    for(auto* bound:{r->left(),r->right()}) {
      auto v=veri_constant_value(static_cast<VeriExp*>(bound),0);if(!v||v->no_xz()!=IS_TRUE)return bad();
      const int sign=v->bits()>31?v->get_certain_bit(31):V0;
      if(v->is_signed()!=IS_TRUE&&sign==V1)return bad();
      for(int bit=32;bit<v->bits();++bit)if(v->get_certain_bit(bit)!=(v->is_signed()==IS_TRUE?sign:V0))return bad();
    }
    if(std::abs(int64_t(r->range_from())-r->range_to())+1>1048576)return bad();
    return packed(r->range_from(),r->range_to());
  };
  if(!n)return bad();
  if(interface_instance_value(n))return packed(63,0);
  if(n->tok_type()!=vtTFVAR)if(auto* type=veri_declared_type(n))return veri_array_shape(type);
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE) {
    auto* v=static_cast<VeriVar*>(n);VeriArrayShape s;s.unpacked=v->range_depth();
    for(int d=1;d<=s.unpacked;++d){int a,b,width;v->get_range(d,a,b,width);s.dimensions.push_back({a,b});if(v->dynamic_array())s.unbound=true;}
    if(v->vec_scalar()==vpVECTOR||veri_integral_atom(v->net_type())||v->aggregate_type()||v->enum_type()){auto dimensions=packed_dimensions(v,v->dstart(),v->dend());s.dimensions.insert(s.dimensions.end(),dimensions.begin(),dimensions.end());}
    return s;
  }
  if(n->tok_type()==vtINT) {
    auto* v=static_cast<VeriInt*>(n);VeriArrayShape s;s.unpacked=v->range_depth();
    for(int d=1;d<=s.unpacked;++d){int a,b,width;v->get_range(d,a,b,width);s.dimensions.push_back({a,b});if(v->dynamic_array())s.unbound=true;}
    s.dimensions.push_back({31,0});return s;
  }
  if(n->tok_type()==vtTFVAR) {
    auto* v=static_cast<VeriTfVar*>(n);auto* d=static_cast<VeriTfDecl*>(v->father());
    VeriArrayShape shape;shape.unpacked=v->range_depth();shape.unbound=v->unbound_ranges()||v->dynamic_array();
    for(int depth=1;depth<=shape.unpacked;++depth){int first,last,count;v->get_range(depth,first,last,count);shape.dimensions.push_back({first,last});}
    if(d->resolved_type()) {
      auto element=veri_array_shape(d->resolved_type());
      shape.dimensions.insert(shape.dimensions.end(),element.dimensions.begin()+element.unpacked,element.dimensions.end());
    } else if(veri_integral_atom(v->net_type())||d->range()){auto dimensions=packed_dimensions(v,v->dstart(),v->dend());shape.dimensions.insert(shape.dimensions.end(),dimensions.begin(),dimensions.end());}
    return shape;
  }
  if(n->tok_type()==vtFUNC) {
    auto* f=static_cast<VeriFunc*>(n);if(f->func()->is_void())return bad();VeriArrayShape shape;if(f->func()->integral_result()||f->func()->range())shape.dimensions=packed_dimensions(f,f->dstart(),f->dend());return shape;
  }
  if(n->tok_type()==vtPARAM) {
    auto* v=static_cast<VeriParam*>(n);if(v->enum_type())return veri_array_shape(v->enum_type());
    if(!v->father()||v->father()->detail_type()!=vsDECL_PARAM)return bad();
    auto* d=static_cast<VeriParamDecl*>(v->father());
    if(d->range()){VeriArrayShape shape;shape.dimensions=packed_dimensions(v,v->dstart(),v->dend());return shape;}
    if(d->typed()&&!veri_integral_atom(d->data_type()))return {};
    return packed(veri_bit_width(n)-1,0);
  }
  if(n->tok_type()==vtGENVAR||n->tok_type()==vtSYS_VAR)return packed(veri_bit_width(n)-1,0);
  if(n->tok_type()!=vtEXP)return bad();
  switch(n->detail_type()) {
    case veEXP_PRI: {
      auto* p=static_cast<VeriPrimaryExp*>(n);if(p->pri_type()==veVAR)return veri_array_shape(p->var());
      if(p->pri_type()!=veNUM&&p->pri_type()!=veSTR)return bad();return packed(veri_bit_width(n)-1,0);
    }
    case veEXP_MEMBER:{if(auto* ret=member_result(n))return veri_array_shape(ret);auto* m=static_cast<VeriMemberExp*>(n);if(m->clocking_source())return veri_array_shape(m->clocking_source());if(m->coverage_builtin())return packed(63,0);if(m->process_builtin())return packed(m->member()=="self"?63:31,0);if(m->random_value_builtin()||m->ipc_value_builtin())return packed(31,0);if(m->hierarchical_symbol())return veri_array_shape(m->hierarchical_symbol());if(veri_array_reduction(n)){if(m->with_expression())return veri_array_shape(m->with_expression());auto element=veri_array_shape(m->object());element.dimensions.erase(element.dimensions.begin(),element.dimensions.begin()+element.unpacked);element.unpacked=0;element.unbound=false;return element;}if(veri_array_shape(m->object()).unbound)return packed(31,0);if(m->event_query())return packed(0,0);if(veri_string_value(m->object())&&!veri_string_value(m))return packed(m->member()=="getc"?7:31,0);if(m->method_type())return m->member()=="num"?packed(31,0):veri_array_shape(m->method_type());auto* f=m->field();return f?veri_array_shape(f->symbol):bad();}
    case veEXP_ARRAY: {
      auto* a=static_cast<VeriArrayExp*>(n);if(veri_dynamic_string_value(a->id())&&!veri_array_shape(a->id()).unpacked)return packed(7,0);auto shape=veri_array_shape(a->id());
      if(veri_queue_slice(n))return shape;
      for(auto* item:a->range()) {
        auto* r=static_cast<VeriRangeExp*>(item);if(shape.dimensions.empty())return bad();
        if(r->rtype()!=vrSINGLE){if(shape.unpacked)return bad();return packed(veri_bit_width(n)-1,0);}
        shape.dimensions.erase(shape.dimensions.begin());if(shape.unpacked)--shape.unpacked;
        shape.unbound=false;for(int d=0;d<shape.unpacked;++d)if(shape.dimensions[d]==std::make_pair(0,-1))shape.unbound=true;
      }
      return shape;
    }
    case veEXP_UNA: {
      auto* u=static_cast<VeriUnaryExp*>(n);
      if(u->op()==vtSYS_QUERY_TYPE) {
        if(u->exp_child()->detail_type()==veEXP_RANGE)return checked_range(static_cast<VeriRangeExp*>(u->exp_child()));
        auto* value=static_cast<VeriExp*>(u->exp_child())->calc_value();if(!value)return bad();int w=value->get_first_int();return w==1?VeriArrayShape():packed(w-1,0);
      }
      break;
    }
    case veEXP_CALLER: {
      auto* c=static_cast<VeriCallerExp*>(n);
      if(c->caller()->detail_type()!=veEXP_PRI)return bad();
      auto* f=c->scope()->value_within_module(static_cast<VeriPrimaryExp*>(c->caller())->str());
      if(!f||f->tok_type()!=vtFUNC)return bad();return veri_array_shape(f);
    }
    case veEXP_BIN: {
      auto* b=static_cast<VeriBinaryExp*>(n);
      if(veri_is_cast(b->op())&&b->lval()->detail_type()==veEXP_PRI) {
        auto* p=static_cast<VeriPrimaryExp*>(b->lval());if(p->var()&&p->var()->tok_type()==vtTYPE)return veri_array_shape(p->var());
      }
      break;
    }
    default:break;
  }
  // Integral arithmetic/concatenation results have a normalized packed range.
  return packed(veri_bit_width(n)-1,0);
}

int veri_array_query(int op,const VeriArrayShape& shape,int dimension,bool& valid) {
  if(op==vtSYS_DIMENSIONS)return int(shape.dimensions.size());
  if(op==vtSYS_UNPACKED_DIMENSIONS)return shape.unpacked;
  if(dimension<1||size_t(dimension)>shape.dimensions.size()){valid=false;return 0;}
  const auto bounds=shape.dimensions[size_t(dimension-1)];int a=bounds.first,b=bounds.second;
  switch(op) {
    case vtSYS_LEFT:return a;case vtSYS_RIGHT:return b;
    case vtSYS_LOW:return std::min(a,b);case vtSYS_HIGH:return std::max(a,b);
    case vtSYS_INCREMENT:return a>=b?1:-1;
    case vtSYS_SIZE: {
      int64_t size=std::abs(int64_t(a)-b)+1;
      if(size>2147483647)throw std::runtime_error("array query size exceeds supported int range");return int(size);
    }
    default:valid=false;return 0;
  }
}

// Width introspection does not evaluate the operand or create runtime reads.
int veri_bit_width(VeriNode* n) {
  auto bad=[&]()->int {throw std::runtime_error("line "+std::to_string(n?n->line():0)+": unsupported $bits operand");};
  auto bounded=[&](int64_t width)->int {
    if(width<1||width>2147483647)throw std::runtime_error("line "+std::to_string(n->line())+": $bits result exceeds supported positive int range");
    return int(width);
  };
  if(!n||veri_dynamic_string_value(n))return bad();
  if(int width=veri_real_width(n))return width;
  auto range_width=[&](VeriRangeExp* range)->int {
    if(range->rtype()==vrSINGLE)return 1;
    if(range->rtype()==vrRAN_ADD||range->rtype()==vrRAN_SUB) {
      auto count=veri_constant_value(static_cast<VeriExp*>(range->right()),0);
      if(!veri_elaboration_constant(range->right())||!count||count->no_xz()!=IS_TRUE)return bad();
      for(int bit=21;bit<count->bits();++bit)if(count->get_certain_bit(bit)!=V0)return bad();
      int count_value=count->get_first_int();return bounded(count_value);
    }
    if(range->not_calc()==IS_TRUE)return bad();
    return bounded(std::abs(int64_t(range->range_from())-range->range_to())+1);
  };
  if(interface_instance_value(n))return 64;
  if(n->tok_type()==vtNUM)return static_cast<VeriNum*>(n)->bits();
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE) {
    auto* var=static_cast<VeriVar*>(n);int64_t width=var->dlen();
    for(int d=1;d<=var->range_depth();++d){int a,b,bits;var->get_range(d,a,b,bits);width=bounded(width*bits);}
    return bounded(width);
  }
  if(n->tok_type()==vtTFVAR) {
    auto* var=static_cast<VeriTfVar*>(n);int64_t width=var->dlen();
    for(int d=1;d<=var->range_depth();++d){int first,last,count;var->get_range(d,first,last,count);width=bounded(width*count);}
    return bounded(width);
  }
  if(n->tok_type()==vtFUNC){auto* f=static_cast<VeriFunc*>(n);return f->func()->is_void()?bad():f->func()->resolved_type()?veri_bit_width(f->func()->resolved_type()):f->dlen();}
  if(n->tok_type()==vtPARAM){auto* v=static_cast<VeriParam*>(n)->get_val();return v?v->bits():bad();}
  if(n->tok_type()==vtINT) {
    auto* var=static_cast<VeriInt*>(n);int64_t width=32;
    for(int d=1;d<=var->range_depth();++d){int a,b,bits;var->get_range(d,a,b,bits);width=bounded(width*bits);}
    return int(width);
  }
  if(n->tok_type()==vtGENVAR)return 32;
  if(n->tok_type()==vtSYS_VAR)return 64;
  if(n->tok_type()!=vtEXP)return bad();
  switch(n->detail_type()) {
    case veEXP_PRI: {
      auto* p=static_cast<VeriPrimaryExp*>(n);
      if(p->pri_type()==veQUEUE_LAST)return 32;
      if(p->pri_type()==veSTR)return p->calc_value()?p->calc_value()->bits():bad();
      if(p->pri_type()==veNUM) {
        return p->calc_value()?p->calc_value()->bits():bad();
      }
      if(p->pri_type()!=veVAR)return bad();
      return veri_bit_width(p->var());
    }
    case veEXP_MEMBER:{if(auto* ret=member_result(n))return veri_bit_width(ret);auto* m=static_cast<VeriMemberExp*>(n);if(m->clocking_source())return veri_bit_width(m->clocking_source());if(m->process_builtin())return m->member()=="self"?64:32;if(m->random_value_builtin()||m->ipc_value_builtin())return 32;if(m->hierarchical_symbol())return veri_bit_width(m->hierarchical_symbol());if(veri_array_reduction(n))return m->with_expression()?veri_bit_width(m->with_expression()):veri_array_element_width(m->object());if(veri_array_shape(m->object()).unbound)return m->member()=="pop_front"||m->member()=="pop_back"?veri_array_element_width(m->object()):32;if(m->event_query())return 1;if(veri_string_value(m->object()))return m->member()=="getc"?8:32;if(m->method_type())return m->member()=="num"?32:m->method_type()->dlen();auto* f=m->field();return f?f->symbol->dlen():bad();}
    case veEXP_ARRAY: {
      auto* array=static_cast<VeriArrayExp*>(n);auto* id=array->id();VeriNode* symbol=nullptr;
      if(veri_dynamic_string_value(id)&&!veri_array_shape(id).unpacked)return 8;
      if(id->detail_type()==veEXP_PRI)symbol=static_cast<VeriPrimaryExp*>(id)->var();
      int depth=0,width=veri_bit_width(id);
      if(symbol&&(symbol->tok_type()==vtVAR||symbol->tok_type()==vtINT||symbol->tok_type()==vtTFVAR)) {
        auto* var=symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol):nullptr;
        auto* integer=symbol->tok_type()==vtINT?static_cast<VeriInt*>(symbol):nullptr;
        auto* formal=symbol->tok_type()==vtTFVAR?static_cast<VeriTfVar*>(symbol):nullptr;
        depth=var?var->range_depth():integer?integer->range_depth():formal->range_depth();
        int consumed=0;
        for(auto* item:array->range()) {
          if(consumed>=depth)break;
          if(static_cast<VeriRangeExp*>(item)->rtype()!=vrSINGLE)return bad();
          int a,b,bits;if(var)var->get_range(consumed+1,a,b,bits);else if(integer)integer->get_range(consumed+1,a,b,bits);else formal->get_range(consumed+1,a,b,bits);
          width/=bits;++consumed;
        }
      }
      auto shape=veri_array_shape(id);
      if(shape.dimensions.size()>size_t(depth+1)) {
        if(array->range().size()>shape.dimensions.size())return bad();
        int64_t result=1;size_t dimension=0;
        for(auto* item:array->range()) {
          auto* range=static_cast<VeriRangeExp*>(item);
          if(range->rtype()!=vrSINGLE) {
            if(dimension<size_t(shape.unpacked)||dimension+1!=array->range().size())return bad();
            result=range_width(range);
          }
          ++dimension;
        }
        for(;dimension<shape.dimensions.size();++dimension)
          result=bounded(result*(std::abs(int64_t(shape.dimensions[dimension].first)-shape.dimensions[dimension].second)+1));
        return bounded(result);
      }
      if(array->range().size()>size_t(depth+1))return bad();
      if(array->range().size()>size_t(depth))return range_width(static_cast<VeriRangeExp*>(array->range().back()));
      return width;
    }
    case veEXP_UNA: {
      auto* u=static_cast<VeriUnaryExp*>(n);const int op=u->op();
      if(veri_is_real_function(op))return op==vtSYS_ITOR||op==vtSYS_REALTOBITS||op==vtSYS_BITSTOREAL?64:32;
      if(op==vtSYS_CAST||veri_is_random(op)||veri_is_testbench_function(op))return 32;
      if(veri_is_sampled(op))return op==vtSYS_SAMPLED||op==vtSYS_PAST?veri_bit_width(veri_system_arguments(u->exp_child()).front()):1;
      if(veri_is_system_unary(op))return op==vtSYS_ISUNKNOWN||op==vtSYS_ONEHOT||op==vtSYS_ONEHOT0?1:32;
      return op==vtUADD||op==vtUSUB||op==vtUNEG||(op>=vtUPREINC&&op<=vtUPOSTDEC)?veri_bit_width(u->exp_child()):1;
    }
    case veEXP_BIN: {
      auto* b=static_cast<VeriBinaryExp*>(n);int op=b->op();
      if(veri_streaming(n))return veri_bit_width(b->rval());
      if(veri_is_cast(op)){auto* v=static_cast<VeriExp*>(n)->calc_value();if(v)return v->bits();auto w=veri_constant_value(static_cast<VeriExp*>(b->lval()),0);return w?bounded(w->get_first_int()):bad();}
      if((op>=vtBLT&&op<=vtBCIEQ)||op==vtBWLEQ||op==vtBWLNEQ||op==vtBINSIDE||op==vtBDAND||op==vtBDOR)return 1;
      if((op>=vtBLRS&&op<=vtBALS)||op==vtBPOW)return veri_bit_width(b->lval());
      return std::max(veri_bit_width(b->lval()),veri_bit_width(b->rval()));
    }
    case veEXP_QUES:{auto* q=static_cast<VeriQuesExp*>(n);return std::max(veri_bit_width(q->choice1()),veri_bit_width(q->choice2()));}
    case veEXP_SIGN:return veri_bit_width(static_cast<VeriSignExp*>(n)->exp());
    case veEXP_UNSIGN:return veri_bit_width(static_cast<VeriUnsignExp*>(n)->exp());
    case veEXP_MULTI: {
      auto* m=static_cast<VeriMultiExp*>(n);if(m->multi_type()!=vemCONCAT_EXP)return bad();
      int64_t width=0;for(auto* p:m->exp())width=bounded(width+veri_bit_width(p));return bounded(width);
    }
    case veEXP_MCONCAT: {
      auto* m=static_cast<VeriMultiConcatExp*>(n);auto c=veri_constant_value(static_cast<VeriExp*>(m->exp1()),0);
      if(!veri_elaboration_constant(m->exp1())||!c||c->no_xz()!=IS_TRUE)return bad();
      return bounded(int64_t(c->get_first_int())*veri_bit_width(m->exp2()));
    }
    case veEXP_CALLER: {
      auto* call=static_cast<VeriCallerExp*>(n);auto* hive=call->hive();
      if(call->caller()->detail_type()==veEXP_PRI) {
        auto* symbol=call->scope()->value_within_module(static_cast<VeriPrimaryExp*>(call->caller())->str());
        if(symbol&&symbol->tok_type()==vtFUNC)return veri_bit_width(symbol);
      }
      if(!hive||hive->detail_type()!=vsDECL_FUNC_DECL||static_cast<VeriFuncDecl*>(hive)->is_void())return bad();
      auto* ret=static_cast<VeriFuncDecl*>(hive)->ret_value();return ret?ret->dlen():bad();
    }
    default:return bad();
  }
}

VeriVar* veri_declared_type(VeriNode* n) {
  if(!n)return nullptr;
  if(auto* ret=member_result(n))return veri_declared_type(ret);
  if(n->tok_type()==vtTFVAR)return static_cast<VeriTfDecl*>(n->father())->resolved_type();
  if(n->tok_type()==vtFUNC)return static_cast<VeriFunc*>(n)->func()->resolved_type();
  if(n->tok_type()==vtPARAM&&n->father()&&n->father()->detail_type()==vsDECL_PARAM)
    return static_cast<VeriParamDecl*>(n->father())->resolved_type();
  if(n->tok_type()==vtEXP&&n->detail_type()==veEXP_CALLER) {
    auto* call=static_cast<VeriCallerExp*>(n);
    if(call->caller()->detail_type()==veEXP_PRI)
      return veri_declared_type(call->scope()->value_within_module(static_cast<VeriPrimaryExp*>(call->caller())->str()));
  }
  return nullptr;
}

VeriVar* veri_aggregate_type(VeriNode* n) {
  if(!n)return nullptr;
  if(auto* element=queue_pop_element(n))return veri_aggregate_type(element);
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->aggregate_type();
  if(auto* type=veri_declared_type(n))return type->aggregate_type();
  if(n->tok_type()!=vtEXP)return nullptr;
  switch(n->detail_type()) {
    case veEXP_PRI:return veri_aggregate_type(static_cast<VeriPrimaryExp*>(n)->var());
    case veEXP_MEMBER:{auto* m=static_cast<VeriMemberExp*>(n);if(m->hierarchical_symbol())return veri_aggregate_type(m->hierarchical_symbol());auto* f=m->field();return f?f->symbol->aggregate_type():nullptr;}
    case veEXP_ARRAY:{auto* a=static_cast<VeriArrayExp*>(n);auto* symbol=veri_array_element_symbol(a->id());if(!symbol)return nullptr;
      auto shape=veri_array_shape(symbol);return shape.unpacked&&a->range().size()==size_t(shape.unpacked)?veri_aggregate_type(symbol):nullptr;}
    case veEXP_BIN:{auto* b=static_cast<VeriBinaryExp*>(n);if(!veri_is_cast(b->op())||b->lval()->detail_type()!=veEXP_PRI)return nullptr;
      auto* p=static_cast<VeriPrimaryExp*>(b->lval());return p->var()&&p->var()->tok_type()==vtTYPE?veri_aggregate_type(p->var()):nullptr;}
    case veEXP_QUES:{auto* q=static_cast<VeriQuesExp*>(n);auto* type=veri_aggregate_type(q->choice1());return type==veri_aggregate_type(q->choice2())?type:nullptr;}
    default:return nullptr;
  }
}

VeriVar* veri_enum_type(VeriNode* n) {
  if(!n)return nullptr;
  if(auto* element=queue_pop_element(n))return veri_enum_type(element);
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->enum_type();
  if(n->tok_type()==vtPARAM)return static_cast<VeriParam*>(n)->enum_type();
  if(auto* type=veri_declared_type(n))return type->enum_type();
  if(n->tok_type()!=vtEXP)return nullptr;
  switch(n->detail_type()) {
    case veEXP_MEMBER:{auto* m=static_cast<VeriMemberExp*>(n);if(m->process_builtin()&&m->member()=="status")return veri_enum_type(m->class_owner()->class_member("state"));if(m->hierarchical_symbol())return veri_enum_type(m->hierarchical_symbol());if(veri_array_reduction(n))return nullptr;if(m->event_query())return nullptr;if(m->method_type())return m->member()=="num"||m->member()=="name"?nullptr:m->method_type();auto* f=m->field();return f?f->symbol->enum_type():nullptr;}
    case veEXP_PRI:return veri_enum_type(static_cast<VeriPrimaryExp*>(n)->var());
    case veEXP_ARRAY: {
      auto* a=static_cast<VeriArrayExp*>(n);
      auto* symbol=veri_array_element_symbol(a->id());if(!symbol)return nullptr;
      auto shape=veri_array_shape(symbol);
      return a->range().size()==size_t(shape.unpacked)?veri_enum_type(symbol):nullptr;
    }
    case veEXP_BIN: {
      auto* b=static_cast<VeriBinaryExp*>(n);
      if(!veri_is_cast(b->op())||b->lval()->detail_type()!=veEXP_PRI)return nullptr;
      auto* p=static_cast<VeriPrimaryExp*>(b->lval());
      return p->var()&&p->var()->tok_type()==vtTYPE?veri_enum_type(p->var()):nullptr;
    }
    case veEXP_QUES: {
      auto* q=static_cast<VeriQuesExp*>(n);auto* a=veri_enum_type(q->choice1());
      return a==veri_enum_type(q->choice2())?a:nullptr;
    }
    case veEXP_UNA: {
      auto* u=static_cast<VeriUnaryExp*>(n);
      return u->op()>=vtUPREINC&&u->op()<=vtUPOSTDEC?veri_enum_type(u->exp_child()):nullptr;
    }
    default:return nullptr;
  }
}

bool veri_streaming(VeriNode* n) {
  if(!n||n->tok_type()!=vtEXP||n->detail_type()!=veEXP_BIN)return false;
  const int op=static_cast<VeriBinaryExp*>(n)->op();return op==vtSTREAM_LEFT||op==vtSTREAM_RIGHT;
}
int veri_stream_slice(VeriNode* n) {
  auto* size=static_cast<VeriBinaryExp*>(n)->lval();
  if(!veri_elaboration_constant(size))return 0;
  auto value=veri_constant_value(static_cast<VeriExp*>(size),0);
  if(!value||value->no_xz()!=IS_TRUE)return 0;
  if(value->is_signed()==IS_TRUE&&value->get_certain_bit(value->bits()-1)==V1)return 0;
  for(int bit=21;bit<value->bits();++bit)if(value->get_certain_bit(bit)!=V0)return 0;
  const int count=value->get_first_int();return count>=1&&count<=1048576?count:0;
}

bool veri_elaboration_constant(VeriNode* n) {
  if(!n||n->tok_type()!=vtEXP)return false;
  switch(n->detail_type()) {
    case veEXP_CALLER:return static_cast<VeriCallerExp*>(n)->calc_value()!=nullptr;
    case veEXP_PRI: {
      auto* p=static_cast<VeriPrimaryExp*>(n);
      if(p->pri_type()==veSTR)return true;
      if(p->pri_type()==veNUM)return true;
      return p->pri_type()==veVAR&&p->var()&&(p->var()->tok_type()==vtPARAM||p->var()->tok_type()==vtGENVAR||p->var()->tok_type()==vtTYPE);
    }
    case veEXP_MULTI: {
      auto* m=static_cast<VeriMultiExp*>(n);if(m->multi_type()!=vemCONCAT_EXP&&m->multi_type()!=vemINSIDE_SET&&m->multi_type()!=vemINSIDE_RANGE)return false;
      for(auto* p:m->exp())if(!veri_elaboration_constant(p))return false;return true;
    }
    case veEXP_MCONCAT: {auto* m=static_cast<VeriMultiConcatExp*>(n);return veri_elaboration_constant(m->exp1())&&veri_elaboration_constant(m->exp2());}
    case veEXP_ARRAY: {
      auto* a=static_cast<VeriArrayExp*>(n);if(!veri_elaboration_constant(a->id()))return false;
      for(auto* p:a->range()) {
        auto* r=static_cast<VeriRangeExp*>(p);if(!veri_elaboration_constant(r->left())||(r->right()&&!veri_elaboration_constant(r->right())))return false;
      }
      return true;
    }
    case veEXP_MEMBER:{auto* m=static_cast<VeriMemberExp*>(n);if(m->class_member()&&m->class_member()->tok_type()==vtPARAM)return m->scope_reference();if(m->clocking_owner()||m->hive()||m->hierarchical_symbol())return false;if(veri_array_reduction(n))return false;if(veri_array_shape(m->object()).unbound)return false;if(m->event_query())return false;if(m->method_type()&&m->member()=="name")return false;if(m->method_type()&&(m->member()=="num"||((m->member()=="first"||m->member()=="last")&&m->object()->detail_type()==veEXP_PRI)))return true;return veri_elaboration_constant(m->object())&&(!m->arguments()||veri_elaboration_constant(m->arguments()));}
    case veEXP_UNA: {auto* u=static_cast<VeriUnaryExp*>(n);
      if(u->op()==vtSYS_QUERY_TYPE||u->op()==vtSYS_TYPENAME)return true;
      if(u->op()==vtSYS_BITS&&veri_array_shape(u->exp_child()).unbound)return false;
      if(veri_is_array_query(u->op())) {auto args=veri_system_arguments(u->exp_child());return !veri_array_shape(args[0]).unbound&&(args.size()==1||veri_elaboration_constant(args[1]));}
      if(u->op()==vtSYS_COUNTBITS){for(auto* a:veri_system_arguments(u->exp_child()))if(!veri_elaboration_constant(a))return false;return true;}
      if(u->op()==vtSYS_BITS&&veri_dynamic_string_value(u->exp_child()))return false;
      return u->op()==vtSYS_BITS||u->op()==vtSYS_RANGE_BITS||((u->op()<vtUPREINC||veri_is_system_unary(u->op())||veri_is_real_function(u->op()))&&veri_elaboration_constant(u->exp_child()));}
    case veEXP_BIN: {auto* b=static_cast<VeriBinaryExp*>(n);return veri_elaboration_constant(b->lval())&&veri_elaboration_constant(b->rval());}
    case veEXP_SIGN:return veri_elaboration_constant(static_cast<VeriSignExp*>(n)->exp());
    case veEXP_UNSIGN:return veri_elaboration_constant(static_cast<VeriUnsignExp*>(n)->exp());
    case veEXP_QUES: {auto* q=static_cast<VeriQuesExp*>(n);return veri_elaboration_constant(q->ques())&&veri_elaboration_constant(q->choice1())&&veri_elaboration_constant(q->choice2());}
    default:return false;
  }
}

int
VeriExp::check_primary_not_other( VeriPrimaryExp *pexp )
{
  if( pexp->var() == NULL )
    return OK;

  switch( pexp->var()->tok_type() )
  {
    case vtMOD_INST:if(interface_instance_value(pexp->var()))return OK;
      veri_err->append_err(ERR_ERROR,pexp,vSEC_PRI_NOT_OTHER);return vSEC_PRI_NOT_OTHER;
    case vtVAR :
      if( static_cast<VeriVar *>(pexp->var())->range_depth() != 0 )
      {
        veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
        return vSEC_PRI_NOT_OTHER;
      }
      return OK;
      break;

    case vtTFVAR :
    case vtPARAM :
    case vtGENVAR :
    case vtFUNC :
    case vtSYS_VAR :
      return OK; break;

    case vtINT :
      if( static_cast<VeriInt *>(pexp->var())->range_depth() != 0 )
      {
        veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
        return vSEC_PRI_NOT_OTHER;
      }
      return OK;
      break;

      return OK; break;

    default:
      veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
      return vSEC_PRI_NOT_OTHER;
  }
}

    /*************************
     * Dummy-Port Expression *
     *************************/

void
VeriDummyPort::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriDummyPort::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriDummyPort::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection

  return OK;
}

int
VeriDummyPort::check_child_validation( void )
{
  return OK;
}

int
VeriDummyPort::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriDummyPort::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriDummyPort::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDummyPort *tmp = new VeriDummyPort( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

    /*****************************
     * Port-Reference Expression *
     *****************************/

void
VeriPortRefExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriPortRefExp::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return vNOT_KNOWN_ERR;
}

int
VeriPortRefExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _port_ref );
  ofile << dot_str_tail( tok_type() );

  // connection

  return vNOT_KNOWN_ERR;
}

int
VeriPortRefExp::check_child_validation( void )
{
  return vNOT_KNOWN_ERR;
}

int
VeriPortRefExp::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return vNOT_KNOWN_ERR;
}

int
VeriPortRefExp::push_for_replacement( NodeVec& /*mstack*/ )
{
  return vNOT_KNOWN_ERR;
}

int
VeriPortRefExp::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriPortRefExp *tmp = new VeriPortRefExp( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

    /******************************
     * Named-Parameter Expression *
     ******************************/

void
VeriNamedParamExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriNamedParamExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _port_exp );
  iqueue.push( depth );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriNamedParamExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_var_conn( _ref, _port_ref );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _port_exp );

  if( _port_ref != NULL )
    ofile << dot_str_symbol_conn( idx(), _port_ref );

  return OK;
}

int
VeriNamedParamExp::check_child_validation( void )
{
  if( _port_exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_NAMED_PARAM_EXP );
    return vCHILD_TYPE_NAMED_PARAM_EXP;
  }
   
  if( _port_exp->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, _port_exp->line(),
                         _port_exp->col(), vCHILD_TYPE_NAMED_PARAM_EXP );
    return vCHILD_TYPE_NAMED_PARAM_EXP;
  }

  return OK;
}

int
VeriNamedParamExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return do_nothing( );
      break;
  }
}

int
VeriNamedParamExp::push_children( NodeVec& mstack )
{
  if( _port_exp != NULL )
  {
    //_port_exp->clean_up( );
    _port_exp->set_is_decl( is_decl() );
    _port_exp->set_is_trash( is_trash() );
    _port_exp->set_scope( scope() );
    mstack.push_back( _port_exp );
  }

  return OK;
}

int
VeriNamedParamExp::do_nothing( void )
{
  return OK;
}

int
VeriNamedParamExp::push_for_replacement( NodeVec& mstack )
{
  if( _port_exp != NULL )
    mstack.push_back( _port_exp );
  return OK;
}

int
VeriNamedParamExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriNamedParamExp *tmp = new VeriNamedParamExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  if( _port_exp != NULL )
  {
    tmp->_port_exp = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /**********************
     * Primary Expression *
     **********************/

void
VeriPrimaryExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriPrimaryExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( iqueue.front() + 1 );
  }
  return OK;
}

int
VeriPrimaryExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_primary_type( _pri_type );
  ofile << dot_str_name( _str );
  ofile << dot_str_tail( tok_type() );

  // connection
  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  if( _var != NULL )
    ofile << dot_str_symbol_conn( idx(), _var );

  return OK;
}

int
VeriPrimaryExp::check_child_validation( void )
{
  return OK;
}

int
VeriPrimaryExp::process_node_2nd( NodeVec& /*mstack*/, String& help_info )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = process_id( help_info );
      if( re == vSEARCH_DECL )
        set_pstatus( vSEARCH_DECL_S );
      else
        set_pstatus( vEND_S );
      return re;
      break;

    case vSEARCH_DECL_S :
      re = process_id( help_info );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return OK;
      break;
  }
}

int
VeriPrimaryExp::process_id( String& help_info )
{
  int re = OK;
  IVec dummy_dimen;
  switch( _pri_type )
  {
    case veQUEUE_LAST: {
      set_signed(IS_TRUE);
      bool indexed=false;
      for(auto* parent=father();parent;parent=parent->father()) {
        if(parent->detail_type()==veEXP_RANGE){indexed=true;break;}
        if(parent->tok_type()==vtSTMT||parent->tok_type()==vtDECL)break;
      }
      if(!indexed)throw std::runtime_error("queue last index $ requires a queue subscript");
      return OK;
    }
    case veVAR :
      if( is_decl() == IS_FALSE )
      {
        if( _str == "$time" || _str == "$realtime" )
        {
          // Runtime time is a system value, never a user-symbol lookup or constant.
          _var = new VeriSysVar( veri_parser->next_id(), line(), col(), _str, birth_mod() );
          veri_parser->insert_node( _var );
          _var->set_scope( scope() );
          return OK;
        }
        if(auto* item=reduction_binding(this,_str)){_var=item;set_signed(item->is_signed());return OK;}
        _var = scope()->value_within_module( _str );
        // Only the selected root is a globally addressable instance. Other
        // module definitions remain types, never arbitrary instance aliases.
        if(!_var && _str==veri_parser->get_top_module()) {
          if(father()&&father()->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(father())->object()==this)
            _var=veri_parser->module(_str);
          else throw std::runtime_error("line "+std::to_string(line())+": module definition is not a value: "+_str);
        }
        if( _var == NULL )
        {
          if( pstatus() == vSTART_S )
          {
            help_info = _str;
            return vSEARCH_DECL;
          }
          else
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_SYMBOL_NOT_FOUND, " '"+_str+"'" );
            return vSEC_SYMBOL_NOT_FOUND;
          }
        }
        else
        {
          switch( _var->tok_type( ) )
          {
            case vtMOD:
              if(_var==veri_parser->module(veri_parser->get_top_module())&&father()&&
                 father()->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(father())->object()==this)return OK;
              throw std::runtime_error("line "+std::to_string(line())+": module definition is not a value: "+_str);
            case vtSTMT:
              if(_var->detail_type()==vsDECL_CLOCKING)return OK;
              if(veri_sequence_definition(_var)) {
                if(!veri_sequence_term(this))throw std::runtime_error("sequence identifier requires a standalone sequence term: "+_str);
                return OK;
              }
              veri_err->append_err(ERR_ERROR,this,vSEC_SYMBOL_MIS_MATCH," '"+_str+"'");
              return vSEC_SYMBOL_MIS_MATCH;
            case vtTYPE: {
              auto* parent=father();
              if(parent&&parent->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(parent)->multi_type()==vemCOMMA_EXP&&static_cast<VeriMultiExp*>(parent)->exp().front()==this)parent=parent->father();
              bool type_query=parent&&parent->detail_type()==veEXP_UNA&&(static_cast<VeriUnaryExp*>(parent)->op()==vtSYS_TYPENAME||static_cast<VeriUnaryExp*>(parent)->op()==vtSYS_BITS||veri_is_array_query(static_cast<VeriUnaryExp*>(parent)->op()));
              if(!type_query&&(!parent||parent->detail_type()!=veEXP_BIN||(!veri_is_cast(static_cast<VeriBinaryExp*>(parent)->op())&&!veri_streaming(parent))||static_cast<VeriBinaryExp*>(parent)->lval()!=this))
                throw std::runtime_error("line "+std::to_string(line())+": type name is not a value: "+_str);
              auto* type=static_cast<VeriVar*>(_var);
              auto* width=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
              veri_parser->insert_node(width);width->set_father(this);width->set_scope(scope());
              const auto text=std::to_string(type->dlen());width->parse(text.c_str(),text.size());set_calc_value(width);
              return OK;
            }
            case vtMOD_INST:
              {auto* instance=static_cast<VeriModInstance*>(static_cast<VeriModInst*>(_var)->instance());
               auto* declaration=static_cast<VeriModInstantiation*>(instance->father());
               if(declaration->inst_mod()&&declaration->inst_mod()->is_interface())return OK;}
              if(father()&&father()->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(father())->object()==this)return OK;
              {auto* parent=father();while(parent&&(parent->detail_type()==veEXP_MULTI||parent->detail_type()==veEXP_NAMED_PARAM))parent=parent->father();
               if(parent&&parent->detail_type()==vsINST_MOD_INSTANCE)return OK;}
              // Only the second $sdf_annotate argument denotes an instance.
              // Keep module namespaces invalid in all ordinary value contexts.
              {auto* list=father();auto* parent=list?list->father():nullptr;
               if(list&&list->detail_type()==veEXP_MULTI&&parent&&parent->detail_type()==vsSTMT_SYS_CALL&&
                  static_cast<VeriSysCallerStmt*>(parent)->caller()=="$sdf_annotate") {
                   const auto& args=static_cast<VeriMultiExp*>(list)->exp();
                   if(args.size()>1&&*std::next(args.begin())==this)return OK;
               }}
              throw std::runtime_error("line "+std::to_string(line())+": module instance is a namespace, not a value: "+_str);
            case vtPARAM  : case vtVAR : case vtTFVAR : case vtINT :
            case vtGENVAR : case vtFUNC :
              break;

            default:
              _var = NULL;
              veri_err->append_err( ERR_ERROR, this, vSEC_SYMBOL_MIS_MATCH, " '"+_str+"'" );
              return vSEC_SYMBOL_MIS_MATCH;
              break;
          }
        }

        // Static subroutine symbols describe runtime storage, not constants.
        // Folding their initial numeric cache can reject valid wide arithmetic.
        if(_var->tok_type()==vtTFVAR||_var->tok_type()==vtFUNC||(_var->tok_type()==vtVAR&&static_cast<VeriVar*>(_var)->interface_port()))return OK;
        VeriNum *val = NULL;
        switch( _var->tok_type() )
        {
          case vtPARAM :
          {
            VeriParam *param = static_cast<VeriParam *>(_var);
            val = param->get_val();
            break;
          }

          case vtTFVAR :
          {
            VeriTfVar *tfvar = static_cast<VeriTfVar *>(_var);
            val = tfvar->get_val();
            break;
          }

          case vtVAR :
//            val = (static_cast<VeriVar *>(_var))->get_one_num( dummy_dimen,
//                                                               IS_TRUE, 0, 0 );
            break;

          case vtINT :
            val = (static_cast<VeriInt *>(_var))->get_one_num( dummy_dimen,
                                                               IS_TRUE, 0, 0 );
            break;

          case vtGENVAR :
            val = (static_cast<VeriGenVar *>(_var))->get_val();
            break;

          case vtFUNC :
            val = (static_cast<VeriFunc *>(_var))->get_val();
            break;

          default:
            break;
        }

        if( val == NULL )
          return OK;

        set_calc_value( val );
        val->set_father( this );
        val->set_scope( scope( ) );
        return OK;
      }
      break;
      
    case veSTR: {
      // Dump target paths also use veSTR with an unquoted encoded payload.
      // They are structural metadata, not source-language string literals.
      if(_str.size()<2||_str.front()!='"'||_str.back()!='"')return OK;
      // A literal retains a packed integral value in numeric contexts. Dynamic
      // string contexts are selected independently by the compiler.
      const auto bytes=veri_decode_string(_str.substr(1,_str.size()-2));
      if(bytes.size()>131072)throw std::runtime_error("line "+std::to_string(line())+": string literal exceeds 1048576 packed bits");
      const int width=std::max(8,int(bytes.size())*8);
      std::string bits;for(unsigned char c:bytes)for(int bit=7;bit>=0;--bit)bits+=((c>>bit)&1)?'1':'0';
      if(bits.empty())bits="00000000";
      const auto literal=std::to_string(width)+"'b"+bits;
      VeriNum* num=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
      veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());
      re=num->parse(literal.c_str(),literal.size());if(re!=OK)return re;
      set_calc_value(num);return OK;
    }

    case veNUM:
    {
      // VeriNum keeps IEEE real constants distinct from packed integers.
      VeriNum *num = new VeriNum( veri_parser->next_id(),
                                  line(), col(), birth_mod() );
      veri_parser->insert_node( num );
      num->set_father( this );
      num->set_scope( scope( ) );
      // The scanner accepts SV unbased '0/'1; preserve a one-bit value in
      // the AST. Simulation backends apply their context-dependent fill width.
      const String numeric_text = (_str == "'0") ? "1'b0" : (_str == "'1") ? "1'b1" : (_str == "'x" || _str == "'X") ? "1'bx" : (_str == "'z" || _str == "'Z") ? "1'bz" : _str;
      if(time_literal()) {
        if(!birth_mod())throw std::runtime_error("time literal has no defining time scope");
        num->set_real(veri_time_value(numeric_text,birth_mod()->time_scale()));re=OK;
      } else re = num->parse( numeric_text.c_str(), numeric_text.size() );

      if( is_signed() == IS_TRUE )
        num->set_signed( ); // ?

      if( re != OK )
      {
        veri_err->append_err( ERR_ERROR, line(), col(), re );
        veri_parser->toss_node( num->idx() );
        return re;
      }
      set_calc_value( num );
      break;
    }

    default:
      break;
  }

  return OK;
}

int
VeriPrimaryExp::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriPrimaryExp::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriPrimaryExp *tmp = new VeriPrimaryExp( idx, this );

  // begin replacement
  *inl = tmp;
  return OK;
}

    /********************
     * Unary Expression *
     ********************/

void
VeriUnaryExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriUnaryExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _exp );
  iqueue.push( depth );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriUnaryExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_op( _op );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriUnaryExp::check_child_validation( void )
{
  if( _exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_UNA_EXP );
    return vCHILD_TYPE_UNA_EXP;
  }
   
  if((_op==vtSYS_RANGE_BITS||_op==vtSYS_QUERY_TYPE)&&_exp->detail_type()==veEXP_RANGE)return OK;
  if( _exp->tok_type() == vtEXP )
  {
    switch( _exp->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_ASSIGN  :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, _exp->line(),
                              _exp->col(), vCHILD_TYPE_UNA_EXP );
        return vCHILD_TYPE_UNA_EXP;

      case veEXP_CALLER  :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(_exp);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, _exp->line(),
                              _exp->col(), vCHILD_TYPE_UNA_EXP );
          return vCHILD_TYPE_UNA_EXP;
        }
        else
          return OK;
        break;
      }

      case veEXP_MINTY :
      {
        veri_err->append_err( ERR_ERROR, _exp->line(),
                            _exp->col(), vCHILD_TYPE_UNA_EXP );
        return vCHILD_TYPE_UNA_EXP;
        break;
      }

      case veEXP_MULTI :
      {
        VeriNode *save_exp = _exp;
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_exp);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
          case vemASSIGN_PATTERN :
            return OK;

          case vemCOMMA_EXP :
          {
            _exp = mexp->exp().back();
            int re = check_child_validation();
            _exp = save_exp;
            return re;
            break;
          }

          case vemEVENT_EXP :
          case vemPORT_EXP :
          case vemPORT_INST_EXP :
          default :
            return vCHILD_TYPE_UNA_EXP;
        }
        break;
      }

      default:
        return OK;
    }
  }
  veri_err->append_err( ERR_ERROR, line(),
                        col(), vCHILD_TYPE_UNA_EXP );
  return vCHILD_TYPE_UNA_EXP;
}

int
VeriUnaryExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_unary_op( );
      break;
  }
}

int
VeriUnaryExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_exp->clean_up( );
  _exp->set_is_trash( is_trash() );
  _exp->set_scope( scope() );
  static_cast<VeriExp *>(_exp)->set_signed( is_signed() );
  mstack.push_back( _exp );

  return OK;
}

int
VeriUnaryExp::process_unary_op( void )
{
  if(veri_is_real_function(_op)) {
    set_signed(_op==vtSYS_ITOR||_op==vtSYS_RTOI?IS_TRUE:IS_FALSE);
    auto source=veri_constant_value(static_cast<VeriExp*>(_exp),0);if(!source)return OK;
    auto* value=new VeriNum(veri_parser->next_id(),source.get());
    veri_parser->insert_node(value);value->set_father(this);value->set_scope(scope());
    if(_op==vtSYS_ITOR){value->truncate_assign(32);value->set_signed();value->set_real(value->real_value());}
    else if(_op==vtSYS_RTOI)value->real_to_integral(32,true);
    else if(_op==vtSYS_REALTOBITS||_op==vtSYS_SHORTREALTOBITS) {
      value->set_real(value->real_value(),_op==vtSYS_REALTOBITS?64:32);
      uint64_t bits=uint64_t(value->val()[0]);if(value->real_width()==64)bits|=uint64_t(value->val()[1])<<32;
      std::string digits;for(int bit=value->real_width();bit-->0;)digits+=(bits>>bit)&1?'1':'0';
      const auto text=std::to_string(digits.size())+"'b"+digits;value->parse(text.c_str(),text.size());
    } else {
      uint64_t bits=0;const int width=_op==vtSYS_BITSTOREAL?64:32;
      value->truncate_assign(width);
      for(int bit=0;bit<std::min(width,value->bits());++bit)if(value->get_certain_bit(bit)==V1)bits|=uint64_t(1)<<bit;
      if(width==64){double decoded;std::memcpy(&decoded,&bits,8);value->set_real(decoded);}
      else {uint32_t packed=uint32_t(bits);float decoded;std::memcpy(&decoded,&packed,4);value->set_real(decoded,32);}
    }
    set_calc_value(value);return OK;
  }
  if(_op==vtSYS_TYPENAME) {
    const auto text=veri_type_name(_exp);
    if(text.size()>131072)throw std::runtime_error("$typename result exceeds supported string size");
    std::string bits;
    for(unsigned char c:text)for(int bit=7;bit>=0;--bit)bits+=((c>>bit)&1)?'1':'0';
    const auto literal=std::to_string(std::max(size_t(8),bits.size()))+"'b"+(bits.empty()?"00000000":bits);
    auto* value=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
    veri_parser->insert_node(value);value->set_father(this);value->set_scope(scope());
    if(value->parse(literal.c_str(),literal.size())!=OK)throw std::runtime_error("invalid $typename result");
    value->to_string_value();set_calc_value(value);set_signed(IS_FALSE);return OK;
  }
  if(_op==vtSYS_CAST) {set_signed(IS_TRUE);return OK;}
  if(veri_is_testbench_function(_op)) {set_signed(_op==vtSYS_SFORMATF?IS_FALSE:IS_TRUE);return OK;}
  if(veri_is_sampled(_op)) {
    auto args=veri_system_arguments(_exp);
    set_signed((_op==vtSYS_SAMPLED||_op==vtSYS_PAST)?static_cast<VeriExp*>(args.front())->is_signed():IS_FALSE);
    return OK; // Clock history is runtime state, including constant operands.
  }
  if(veri_is_random(_op)) {
    set_signed(_op==vtSYS_RANDOM||_op==vtSYS_RANDOM_SEEDED?IS_TRUE:IS_FALSE);
    return OK; // Runtime state must never become an elaboration constant.
  }
  if(_op==vtSYS_QUERY_TYPE) {veri_array_shape(this);return OK;}
  if(_op==vtSYS_COUNTBITS||veri_is_array_query(_op)) {
    auto args=veri_system_arguments(_exp);int result=0;bool valid=true;
    if(_op==vtSYS_COUNTBITS) {
      if(!veri_elaboration_constant(this))return OK;
      unsigned selected=0;
      for(size_t i=1;i<args.size();++i){auto v=veri_constant_value(static_cast<VeriExp*>(args[i]),0);if(!v)return OK;selected|=1u<<v->get_certain_bit(0);}
      auto value=veri_constant_value(static_cast<VeriExp*>(args[0]),0);if(!value)return OK;
      for(int bit=0;bit<value->bits();++bit)if(selected&(1u<<value->get_certain_bit(bit)))++result;
    } else {
      auto shape=veri_array_shape(args[0]);if(shape.unbound)return OK;int dimension=1;
      if(args.size()==2) {
        if(!veri_elaboration_constant(args[1]))return OK;
        auto v=veri_constant_value(static_cast<VeriExp*>(args[1]),0);if(!v)return OK;
        // Preserve the full self-sized value: high bits must not alias a valid dimension.
        valid=v->no_xz()==IS_TRUE;
        for(int bit=31;bit<v->bits();++bit)if(v->get_certain_bit(bit)!=V0)valid=false;
        dimension=valid?v->get_first_int():0;
      }
      if(valid)result=veri_array_query(_op,shape,dimension,valid);
    }
    auto* num=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
    veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());
    const auto text=valid?"32'sd"+std::to_string(uint32_t(result)):std::string("32'bx");
    num->parse(text.c_str(),text.size());num->set_signed();set_calc_value(num);return OK;
  }
  if(veri_is_system_unary(_op)) {
    int result=0;bool boolean=_op==vtSYS_ISUNKNOWN||_op==vtSYS_ONEHOT||_op==vtSYS_ONEHOT0;
    if(_op==vtSYS_BITS){
      if(veri_real_width(_exp)||veri_chandle_value(_exp))throw std::runtime_error("$bits requires a bit-stream type");
      if(veri_dynamic_string_value(_exp)) {
        return OK; // Dynamic data types do not make $bits an elaboration constant.
      } else {if(veri_array_shape(_exp).unbound)return OK;result=veri_bit_width(_exp);}
    }
    else if(_op==vtSYS_RANGE_BITS) {
      auto* range=static_cast<VeriRangeExp*>(_exp);
      if(range->rtype()!=vrSEMI||range->not_calc()==IS_TRUE||!veri_elaboration_constant(range->left())||!veri_elaboration_constant(range->right()))
        throw std::runtime_error("line "+std::to_string(line())+": $bits data-type range must be constant");
      for(auto* bound:{range->left(),range->right()}) {
        auto value=veri_constant_value(static_cast<VeriExp*>(bound),0);
        if(!value||value->no_xz()!=IS_TRUE)throw std::runtime_error("$bits data-type bound must be a known int");
        const int high=value->bits()>31?value->get_certain_bit(31):V0;
        if(value->is_signed()!=IS_TRUE&&high==V1)throw std::runtime_error("$bits data-type bound exceeds supported int range");
        for(int bit=32;bit<value->bits();++bit)if(value->get_certain_bit(bit)!=(value->is_signed()==IS_TRUE?high:V0))
          throw std::runtime_error("$bits data-type bound exceeds supported int range");
      }
      int64_t width=std::abs(int64_t(range->range_from())-range->range_to())+1;
      if(width>1048576)throw std::runtime_error("line "+std::to_string(line())+": $bits data-type range exceeds supported width");
      result=int(width);
    } else {
      if(!veri_elaboration_constant(_exp))return OK;
      auto value=veri_constant_value(static_cast<VeriExp*>(_exp),0);if(!value)return OK;
      int ones=0,highest=-1;bool unknown=false;
      for(int bit=0;bit<value->bits();++bit) {
        const int v=value->get_certain_bit(bit);unknown|=v==VX||v==VZ;
        if(v==V1){++ones;highest=bit;}
      }
      if(_op==vtSYS_ISUNKNOWN)result=unknown;
      else if(_op==vtSYS_COUNTONES)result=ones;
      else if(_op==vtSYS_ONEHOT)result=ones==1;
      else if(_op==vtSYS_ONEHOT0)result=ones<=1;
      else result=unknown?-1:highest<0?0:highest+(ones>1);
    }
    auto* num=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
    veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());
    const auto text=result<0?std::string("32'bx"):std::to_string(boolean?1:32)+(boolean?"'b":"'sd")+std::to_string(result);
    // Boolean digits are 0/1; integer result is a signed, self-determined int.
    num->parse(text.c_str(),text.size());if(!boolean)num->set_signed();set_calc_value(num);return OK;
  }
  // Mutation is runtime work. Bind its operand without changing static parser
  // values or publishing a speculative constant for the expression result.
  if(_op==vtUPREINC||_op==vtUPREDEC||_op==vtUPOSTINC||_op==vtUPOSTDEC)return OK;
  VeriExp * exp = static_cast<VeriExp *>(_exp);

  int re = OK;
  if( exp->detail_type( ) == veEXP_PRI )
  {
    re = check_primary_not_other( static_cast<VeriPrimaryExp *>(exp) );
    if( re != OK )
      return re;
  }

  if( exp->calc_value() != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );

    int re = num->unary_operation( _op );
    if( re != OK )
    {
      veri_err->append_err( ERR_ERROR, _exp, re );
      veri_parser->toss_node( num->idx() );
      return re;
    }
    set_calc_value( num );
  }
  return OK;
}

int
VeriUnaryExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp );
  return OK;
}

int
VeriUnaryExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriUnaryExp *tmp = new VeriUnaryExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  tmp->_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************
     * Event Expression *
     ********************/

void
VeriEventExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx( ) );
  set_calc_value( NULL );
}

int
VeriEventExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  if( _exp != NULL )
  {
    mqueue.push( _exp );
    iqueue.push( depth );
  }
  if(_condition) { mqueue.push(_condition);iqueue.push(depth); }
  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriEventExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_op( _etype );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp );
  if(_condition)ofile << dot_str_conn(idx(),_condition);

  return OK;
}

int
VeriEventExp::check_child_validation( void )
{
  if( _exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_EVENT_EXP );
    return vCHILD_TYPE_EVENT_EXP;
  }

  if( _exp->tok_type() == vtEXP && (!_condition || _condition->tok_type()==vtEXP) )
    return OK;
  veri_err->append_err( ERR_ERROR, _exp->line(),
                        _exp->col(), vCHILD_TYPE_EVENT_EXP );
  return vCHILD_TYPE_EVENT_EXP;
}

int
VeriEventExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return check_sensitivity_list( );
      break;
  }
}

int
VeriEventExp::push_children( NodeVec& mstack )
{
  if( _exp != NULL )
  {
    //_exp->clean_up( );
    _exp->set_scope( scope() );
    _exp->set_is_trash( is_trash() );
    mstack.push_back( _exp );
  }
  if(_condition) {
    _condition->set_scope(scope());_condition->set_is_trash(is_trash());
    mstack.push_back(_condition);
  }
  return OK;
}

int
VeriEventExp::check_sensitivity_list( void )
{
  /* TODO */
  return OK;
}

int
VeriEventExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp );
  if(_condition)mstack.push_back(_condition);
  return OK;
}

int
VeriEventExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriEventExp *tmp = new VeriEventExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  if(_condition) {
    tmp->_condition=*(--itl);(*itl)->set_father(tmp);node_list.erase(itl);itl=inl;
  }
  tmp->_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************
     * Array Expression *
     ********************/

static int unfold_subroutine(VeriNode* call,VeriNode* tf,VeriSymbolTable* lexical_scope,VeriNode::NodeVec& mstack,VeriNode*& hive) {
  // Reject recursive expansion before cloning, rather than exhausting memory.
  for(auto* ancestor=call->father();ancestor;ancestor=ancestor->father()) {
    bool same=ancestor->detail_type()==tf->detail_type();
    if(same&&tf->detail_type()==vsDECL_FUNC_DECL)
      same=static_cast<VeriFuncDecl*>(ancestor)->func_name()==static_cast<VeriFuncDecl*>(tf)->func_name();
    else if(same&&tf->detail_type()==vsDECL_TASK_DECL)
      same=static_cast<VeriTaskDecl*>(ancestor)->task_name()==static_cast<VeriTaskDecl*>(tf)->task_name();
    else same=false;
    // Different classes may define identically named methods/constructors.
    // Only the same lexical class can constitute recursive expansion.
    if(same&&ancestor->scope()&&tf->scope()&&veri_class_type(ancestor->scope()->value("this"))!=veri_class_type(tf->scope()->value("this")))same=false;
    if(same&&ancestor->birth_mod()==tf->birth_mod()) {
      // Bind a recursive call to the enclosing declaration. Functions and
      // resumable tasks own runtime activation frames; cloning either body
      // again here would turn the call graph into an infinite syntax tree.
      hive=ancestor;
      veri_bind_arguments(call,veri_subroutine_formals(hive));
      return OK;
    }
  }
  auto& binding=veri_parser->subroutine_binding(tf,lexical_scope);
  if(binding) {
    hive=binding;
    // Reusing the body must still validate this call's own actual list.
    veri_bind_arguments(call,veri_subroutine_formals(hive));
    return OK;
  }
  VeriNode::NodeVec node_vec;

  VeriNode::NodeVec tstack;
  tstack.reserve( 397 );
  tstack.push_back( tf );

  while( !tstack.empty( ) )
  {
    tf = tstack.back( );
    tstack.pop_back( );
    node_vec.push_back( tf );
    tf->push_for_replacement( tstack );
  }

  VeriNode::NodeList node_list( node_vec.rbegin(), node_vec.rend() );
  node_vec.clear();
  VeriNode::NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
  {
    tf = *inl;
    tf->replace_node( veri_parser->next_id(), node_list, inl );
    veri_parser->insert_node( *inl );
    tstack.push_back( *inl );
  }

  mstack.push_back( call );

  hive = tstack.back();
  binding=hive;
  hive->set_father( call );
  hive->set_scope(lexical_scope);
  mstack.push_back( hive );

  tstack.clear();
  return OK;
}

VeriMemberExp* veri_bind_class_call(VeriNode* source,VeriSeqBlock* owner,const std::string& name,VeriNode* arguments,VeriNode* prototype) {
  auto* symbol=owner->scope()->value_same_level(name);
  if(!symbol&&name!="new")throw std::runtime_error("invalid class call binding: "+name);
  if(symbol&&symbol->tok_type()!=vtFUNC&&symbol->tok_type()!=vtTASK)throw std::runtime_error("invalid class call binding: "+name);
  auto* object=veri_parser->gen_primary("this",source->line(),source->col(),veVAR);
  static_cast<VeriPrimaryExp*>(object)->set_var(owner->scope()->value_same_level("this"));
  auto* call=static_cast<VeriMemberExp*>(veri_parser->gen_member(object,name.c_str(),source->line(),source->col()));
  call->set_scope(source->scope());call->bind_class_call(owner,symbol,arguments);call->set_argument_prototype(prototype);
  VeriNode::NodeVec stack;std::string help;int status=OK;
  if(symbol) {
    auto* declaration=symbol->tok_type()==vtFUNC?static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task());
    status=unfold_subroutine(call,declaration,owner->scope(),stack,call->bound_hive());
  } else {
    auto* constructor=new VeriFuncDecl(veri_parser->next_id(),source->line(),source->col(),IS_TRUE,IS_FALSE,-1,nullptr,"new",nullptr,nullptr,nullptr,owner->birth_mod());
    veri_parser->insert_node(constructor);constructor->set_father(call);constructor->set_scope(owner->scope());call->bound_hive()=constructor;stack.push_back(constructor);
  }
  while(status==OK&&!stack.empty()) {
    auto* node=stack.back();stack.pop_back();status=node->process_node_2nd(stack,help);
    if(status==vSEARCH_DECL)status=node->process_node_2nd(stack,help);
  }
  if(status!=OK)throw std::runtime_error("class method elaboration failed: "+name+"\n"+veri_parser->get_err_info());
  return call;
}

VeriMemberExp* veri_bind_interface_call(VeriMemberExp* source,VeriMod* instance) {
  auto* symbol=instance->scope()->value_same_level(source->member());
  if(!symbol||(symbol->tok_type()!=vtFUNC&&symbol->tok_type()!=vtTASK))throw std::runtime_error("invalid interface subroutine binding: "+source->member());
  auto* object=veri_parser->gen_primary("$interface_dispatch",source->line(),source->col(),veVAR);
  auto* call=static_cast<VeriMemberExp*>(veri_parser->gen_member(object,source->member().c_str(),source->line(),source->col()));
  call->set_scope(source->scope());call->bind_interface_call(instance,source->arguments(),source->interface_prototype());
  auto* declaration=symbol->tok_type()==vtFUNC?static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task());
  if(symbol->tok_type()==vtFUNC)call->set_signed(static_cast<VeriFuncDecl*>(declaration)->is_signed());
  VeriNode::NodeVec pending;std::string help;int status=unfold_subroutine(call,declaration,instance->scope(),pending,call->bound_hive());
  while(status==OK&&!pending.empty()) {
    auto* node=pending.back();pending.pop_back();status=node->process_node_2nd(pending,help);
    if(status==vSEARCH_DECL)status=node->process_node_2nd(pending,help);
  }
  if(status!=OK)throw std::runtime_error("interface subroutine elaboration failed: "+source->member()+"\n"+veri_parser->get_err_info());
  return call;
}

VeriSeqBlock* veri_class_type(VeriNode* n) {
  if(!n)return nullptr;
  if(auto* element=queue_pop_element(n))return veri_class_type(element);
  if(n->detail_type()==veEXP_PRI)return veri_class_type(static_cast<VeriPrimaryExp*>(n)->var());
  if(n->detail_type()==veEXP_ARRAY)return veri_class_type(static_cast<VeriArrayExp*>(n)->id());
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->class_type();
  if(n->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(n)->class_type();
  if(n->tok_type()==vtFUNC) {
    auto* type=static_cast<VeriFunc*>(n)->func()->resolved_type();return type?type->class_type():nullptr;
  }
  if(n->detail_type()==veEXP_CALLER) {
    auto* hive=veri_call_hive(n);
    if(hive&&hive->detail_type()==vsDECL_FUNC_DECL) {auto* type=static_cast<VeriFuncDecl*>(hive)->resolved_type();return type?type->class_type():nullptr;}
  }
  if(n->detail_type()==veEXP_MEMBER) {
    auto* m=static_cast<VeriMemberExp*>(n);
    if(m->coverage_builtin()&&!m->called()&&m->coverage_point()>=0)return m->class_owner();
    if(m->process_builtin()&&m->member()=="self")return m->class_owner();
    if(m->called()&&m->hive()&&m->hive()->detail_type()==vsDECL_FUNC_DECL) {auto* type=static_cast<VeriFuncDecl*>(m->hive())->resolved_type();return type?type->class_type():nullptr;}
    if(m->field())return veri_class_type(m->field()->symbol);
    return veri_class_type(m->class_member()?m->class_member():m->hierarchical_symbol());
  }
  if(n->detail_type()==veEXP_MULTI)return static_cast<VeriMultiExp*>(n)->object_type();
  return nullptr;
}

void VeriMemberExp::clean_up() {
  _class_owner=nullptr;_class_member=nullptr;_coverage_point=-1;_clocking_owner=nullptr;_clocking_source=nullptr;
  _hive=nullptr;_call_instance=nullptr;_interface_prototype=nullptr;_argument_prototype=nullptr;
  set_pstatus(vSTART_S);_field=nullptr;_method_type=nullptr;_event_query=false;_hierarchical_symbol=nullptr;_interface_reference=false;_interface_writable=false;_interface_view_instance=nullptr;
  if(_iterator)veri_parser->toss_node(_iterator->idx());_iterator=nullptr;_iterator_name="item";
  if(_array_result)veri_parser->toss_node(_array_result->idx());_array_result=nullptr;
  if(calc_value())veri_parser->toss_node(calc_value()->idx());set_calc_value(nullptr);
}
int VeriMemberExp::push_dot_children(NodeQueue& nodes,IQueue& levels) {nodes.push(_object);levels.push(levels.front()+1);if(_arguments){nodes.push(_arguments);levels.push(levels.front()+1);}if(_with){nodes.push(_with);levels.push(levels.front()+1);}return OK;}
int VeriMemberExp::pretty_dot_label(Ofstream& out,int depth) {
  out<<dot_str_rank(idx(),depth)<<dot_str_head(idx())<<dot_str_tok_type(tok_type())<<dot_str_tail(tok_type())<<dot_str_conn(idx(),_object);return OK;
}
int VeriMemberExp::process_node_2nd(NodeVec& stack,String&) {
  if(_hive)return OK;
  if(pstatus()==vSTART_S) {
    if(scope_randomize()) {
      set_signed(IS_TRUE);
      set_pstatus(vEND_S);
      if(_with){_with->set_scope(scope());stack.push_back(_with);}
      if(_arguments){_arguments->set_scope(scope());stack.push_back(_arguments);}
      return OK;
    }
    if(_with_constraint||(_called&&_member=="randomize")) {
      set_pstatus(vCALL_S);stack.push_back(this);
      _object->set_scope(scope());stack.push_back(_object);return OK;
    }
    set_pstatus(_with?vSEARCH_DECL_S:vEND_S);stack.push_back(this);
    if(_arguments&&!_with){_arguments->set_scope(scope());_arguments->set_is_trash(is_trash());stack.push_back(_arguments);}
    _object->set_scope(scope());_object->set_is_trash(is_trash());stack.push_back(_object);return OK;
  }
  if(pstatus()==vCALL_S&&(_with_constraint||(_called&&_member=="randomize"))) {
    auto* owner=veri_class_type(_object);
    if(!owner) {
      if(_with_constraint)throw std::runtime_error("randomize with requires a class object");
      // A user interface method may also be named randomize. Its arguments
      // retain ordinary caller-scope binding.
      set_pstatus(vEND_S);stack.push_back(this);
      if(_arguments){_arguments->set_scope(scope());stack.push_back(_arguments);}
      return OK;
    }
    if(_scope_reference)throw std::runtime_error("randomize requires an object method call");
    owner->ensure_class_elaborated();_class_owner=owner;set_signed(IS_TRUE);set_pstatus(vEND_S);
    // Members take precedence; unresolved names fall through to the call scope.
    auto* context=scope()->append_scope("$randomize"+std::to_string(idx()),vNAMED_BLOCK_SCOPE);
    context->set_class_base(owner->scope());context->set_class_owner(owner);
    if(_with){_with->set_scope(context);stack.push_back(_with);}
    if(_arguments){_arguments->set_scope(context);stack.push_back(_arguments);}
    return OK;
  }
  if(pstatus()==vSEARCH_DECL_S) {
    if(!veri_parser->systemverilog())throw std::runtime_error("array with clauses require SystemVerilog mode");
    if((!veri_array_reduction(this)&&!veri_array_locator(this)&&(!veri_array_ordering(this)||_member=="reverse"))||veri_array_shape(_object).unpacked!=1)throw std::runtime_error("line "+std::to_string(line())+": with clause requires a one-dimensional array method: "+_member);
    auto args=veri_system_arguments(_arguments);
    if(args.size()>1||(!args.empty()&&(args[0]->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(args[0])->pri_type()!=veVAR)))
      throw std::runtime_error("array reduction iterator argument must be one identifier");
    _iterator_name=args.empty()?"item":static_cast<VeriPrimaryExp*>(args[0])->str();
    auto* symbol=veri_array_element_symbol(_object);
    if(!symbol)throw std::runtime_error("array with clause requires integral storage");
    const int sign=symbol->tok_type()==vtFUNC?static_cast<VeriFunc*>(symbol)->func()->is_signed():symbol->tok_type()==vtINT?IS_TRUE:symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->is_signed():static_cast<VeriTfVar*>(symbol)->is_signed();
    const int start=symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->dstart():symbol->tok_type()==vtTFVAR?static_cast<VeriTfVar*>(symbol)->dstart():31;
    const int end=symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->dend():symbol->tok_type()==vtTFVAR?static_cast<VeriTfVar*>(symbol)->dend():0;
    const int type=symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->net_type():symbol->tok_type()==vtTFVAR?static_cast<VeriTfVar*>(symbol)->net_type():vvLOGIC;
    auto shape=veri_array_shape(_object);
    _iterator=new VeriVar(veri_parser->next_id(),line(),col(),_iterator_name,vpNO_IO,type,sign,shape.dimensions.size()>size_t(shape.unpacked)?vpVECTOR:vpSCALAR,0,0,start,end,nullptr,nullptr,0,birth_mod());
    _iterator->set_class_type(veri_class_type(symbol));_iterator->set_enum_type(veri_enum_type(symbol));_iterator->set_aggregate_type(veri_aggregate_type(symbol));
    veri_parser->insert_node(_iterator);_iterator->set_father(symbol->father());_iterator->set_scope(scope());
    set_pstatus(vEND_S);stack.push_back(this);_with->set_scope(scope());_with->set_is_trash(is_trash());stack.push_back(_with);return OK;
  }
  VeriNode* receiver=_object->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(_object)->var():
      _object->detail_type()==veEXP_MEMBER?static_cast<VeriMemberExp*>(_object)->hierarchical_symbol():nullptr;
  if(auto* clock=veri_clocking_reference(_object)) {
    if(_called||_scope_reference||_with)throw std::runtime_error("clocking member is not a method: "+_member);
    if(clock->pstatus()==vSTART_S)veri_bind_semantic(clock,clock->scope());
    for(auto* port:clock->ports())if(port->name==_member) {
      _clocking_owner=clock;_clocking_source=port->children[0];
      set_signed(static_cast<VeriExp*>(_clocking_source)->is_signed());return OK;
    }
    throw std::runtime_error("unknown clocking member: "+_member);
  }
  if(_called&&_member=="rand_mode"&&!_arguments&&veri_array_shape(_object).unpacked)
    throw std::runtime_error("rand_mode query requires a singular property");
  if(_called&&_object->detail_type()==veEXP_PRI&&_member=="rand_mode"&&receiver&&
     (receiver->tok_type()==vtVAR||receiver->tok_type()==vtINT)&&static_cast<VeriDecl*>(receiver->father())->rand_property()) {
    if(auto* owner=veri_class_type(scope()->value("this"))) {
      if(veri_system_arguments(_arguments).size()>1)throw std::runtime_error("random control argument count mismatch");
      _class_owner=owner;_class_member=receiver;set_signed(IS_TRUE);return OK;
    }
  }
  if(_called&&_object->detail_type()==veEXP_MEMBER&&(_member=="rand_mode"||_member=="constraint_mode")) {
    auto* target=static_cast<VeriMemberExp*>(_object);auto* symbol=target->class_member();
    if(symbol&&target->class_owner()) {
      if(veri_system_arguments(_arguments).size()>1)throw std::runtime_error("random control argument count mismatch");
      if(_member=="rand_mode"&&((symbol->tok_type()!=vtVAR&&symbol->tok_type()!=vtINT)||!static_cast<VeriDecl*>(symbol->father())->rand_property()))
        throw std::runtime_error("rand_mode requires a rand property");
      if(_member=="constraint_mode"&&symbol->detail_type()!=vsDECL_CONSTRAINT)
        throw std::runtime_error("constraint_mode requires a constraint name");
      _class_owner=target->class_owner();set_signed(IS_TRUE);return OK;
    }
  }
  auto* object_storage=veri_array_element_symbol(_object);
  const bool array_receiver=object_storage&&veri_array_shape(_object).unpacked;
  auto* scoped_type=_scope_reference&&_object->detail_type()==veEXP_TYPE?static_cast<VeriTypeExp*>(_object)->resolve(scope()):nullptr;
  if(auto* owner=scoped_type?scoped_type->class_type():array_receiver?nullptr:veri_class_type(_object)) {
    owner->ensure_class_elaborated();
    if(owner->process_type()&&(_called||_member=="self"||_member=="status"||_member=="get_randstate")) {
      const bool valid=_member=="self"||_member=="status"||_member=="get_randstate"||_member=="set_randstate"||_member=="srandom"||_member=="kill"||_member=="await"||_member=="suspend"||_member=="resume";
      if(!valid)throw std::runtime_error("unknown process method: "+_member);
      if(_with||(_scope_reference&&_member!="self"))throw std::runtime_error("process method requires an object receiver: "+_member);
      if(!_called)set_call(nullptr);
      if(veri_system_arguments(_arguments).size()!=size_t(_member=="srandom"||_member=="set_randstate"))throw std::runtime_error("process method argument count mismatch: "+_member);
      if(_member=="self") {
        bool executable=false;
        for(auto* parent=father();parent;parent=parent->father()) {
          if(parent->detail_type()==vsSTMT_INIT||parent->detail_type()==vsDECL_FUNC_DECL||parent->detail_type()==vsDECL_TASK_DECL||
             (parent->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(parent)->class_declaration())){executable=true;break;}
        }
        if(!executable)throw std::runtime_error("process::self requires a procedural context");
      }
      _class_owner=owner;set_signed(_member=="status"?IS_TRUE:IS_FALSE);return OK;
    }
    if(owner->coverage_type()) {
      if(_with||_scope_reference)throw std::runtime_error("covergroup requires an object method call");
      if(!_called) {
        auto* metadata=static_cast<VeriClocking*>(static_cast<VeriModuleItemList*>(owner->decl_list())->item_list().front());
        int index=0;
        for(int kind:{vsDECL_COVERPOINT,vsDECL_COVER_CROSS})if(metadata->children[1])for(auto* item:static_cast<VeriModuleItemList*>(metadata->children[1])->item_list())if(item->detail_type()==kind) {
          auto* point=static_cast<VeriClocking*>(item);auto name=point->name;
          if(name.empty()&&kind==vsDECL_COVERPOINT&&point->children[0]->detail_type()==veEXP_PRI)name=static_cast<VeriPrimaryExp*>(point->children[0])->str();
          if(name==_member){_class_owner=owner;_coverage_point=index;return OK;}++index;
        }
        throw std::runtime_error("unknown coverpoint/cross: "+_member);
      }
      const bool query=_member=="get_coverage"||_member=="get_inst_coverage";
      if(_object->detail_type()==veEXP_MEMBER) {
        auto* point=static_cast<VeriMemberExp*>(_object);if(point->coverage_point()>=0&&!point->called()) {
          if(!query)throw std::runtime_error("coverpoint/cross only supports coverage queries");_coverage_point=point->coverage_point();
        }
      }
      if(!query&&_member!="sample"&&_member!="start"&&_member!="stop"&&_member!="set_inst_name")throw std::runtime_error("unknown covergroup method: "+_member);
      if(veri_system_arguments(_arguments).size()!=size_t(_member=="set_inst_name"))throw std::runtime_error("covergroup method argument count mismatch: "+_member);
      _class_owner=owner;set_signed(IS_FALSE);return OK;
    }
    if(owner->ipc_kind()) {
      if(!_called||_scope_reference||_with)throw std::runtime_error("IPC requires an object method call");
      const auto count=veri_system_arguments(_arguments).size();
      const bool mailbox=owner->ipc_kind()==1;
      const bool valid=mailbox?(_member=="num"||_member=="put"||_member=="get"||_member=="peek"||_member=="try_put"||_member=="try_get"||_member=="try_peek"):
        (_member=="put"||_member=="get"||_member=="try_get");
      if(!valid)throw std::runtime_error("unknown IPC method: "+_member);
      if(mailbox?count!=size_t(_member!="num"):count>1)throw std::runtime_error("IPC method argument count mismatch");
      _class_owner=owner;set_signed(IS_TRUE);return OK;
    }
    if(_member=="randomize"||_member=="srandom"||_member=="rand_mode"||_member=="constraint_mode") {
      if(!_called||_scope_reference)throw std::runtime_error("randomize requires an object method call");
      if(_member!="randomize"&&veri_system_arguments(_arguments).size()!=1)throw std::runtime_error("object random control requires one argument; query an individual property or constraint");
      _class_owner=owner;set_signed(IS_TRUE);return OK;
    }
    if(_with)throw std::runtime_error("class methods do not support an array with clause");
    _class_owner=owner;
    if(_member=="new"&&super_reference()&&!owner->scope()->value_same_level("new")) {
      auto* constructor=new VeriFuncDecl(veri_parser->next_id(),line(),col(),IS_TRUE,IS_FALSE,-1,nullptr,"new",nullptr,nullptr,nullptr,owner->birth_mod());
      veri_parser->insert_node(constructor);constructor->set_father(this);constructor->set_scope(owner->scope());_hive=constructor;stack.push_back(this);stack.push_back(constructor);return OK;
    }
    _class_member=owner->class_member(_member);
    if(!_class_member)throw std::runtime_error("line "+std::to_string(line())+": unknown class member: "+_member);
    if(_class_member->detail_type()==vsDECL_CONSTRAINT) {
      if(_called)throw std::runtime_error("constraint is not a method");return OK;
    }
    veri_check_class_access(_class_member,scope());
    if(_class_member->tok_type()==vtTYPE) {
      if(!_scope_reference||_called||!father()||
         !((father()->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(father())->scope_reference())||
           (father()->detail_type()==veEXP_UNA&&static_cast<VeriUnaryExp*>(father())->op()==vtSYS_TYPENAME)))
        throw std::runtime_error("line "+std::to_string(line())+": type name is not a value: "+_member);
      _hierarchical_symbol=_class_member;return OK;
    }
    if(!_called&&(_class_member->tok_type()==vtFUNC||_class_member->tok_type()==vtTASK))set_call(nullptr);
    if(_called) {
      auto* symbol=_class_member;
      if((_member=="new"&&!super_reference())|| (symbol->tok_type()!=vtFUNC&&symbol->tok_type()!=vtTASK))throw std::runtime_error("class member is not a callable method: "+_member);
      auto* declaration=symbol->tok_type()==vtFUNC?static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task());
      if(symbol->tok_type()==vtFUNC)set_signed(static_cast<VeriFuncDecl*>(declaration)->is_signed());
      for(auto* declaring=owner;declaring;declaring=declaring->base_class())if(declaring->scope()->value_same_level(_member)==symbol){_class_owner=declaring;break;}
      return unfold_subroutine(this,declaration,_class_owner->scope(),stack,_hive);
    }
    if(_class_member->tok_type()==vtPARAM) {
      _hierarchical_symbol=_class_member;
      set_signed(static_cast<VeriParam*>(_class_member)->is_signed());
      // Parameter values own their semantic copies, including in cloned class
      // specializations. Never treat this constant as an object field.
      auto* value=static_cast<VeriParam*>(_class_member)->get_val();
      value->set_father(this);value->set_scope(scope());set_calc_value(value);return OK;
    }
    if(_class_member->tok_type()!=vtVAR&&_class_member->tok_type()!=vtINT)throw std::runtime_error("class member requires a method call: "+_member);
    _hierarchical_symbol=_class_member;set_signed(_class_member->tok_type()==vtINT?IS_TRUE:static_cast<VeriVar*>(_class_member)->is_signed());return OK;
  }
  VeriMod* interface_target=nullptr;std::string interface_view;
  if(auto type=veri_virtual_interface(_object)) {interface_target=type->prototype;interface_view=type->view;
  }
  if(receiver&&receiver->tok_type()==vtVAR&&static_cast<VeriVar*>(receiver)->interface_port()) {
    auto* port=static_cast<VeriVar*>(receiver);interface_target=port->interface_instance();interface_view=port->interface_modport();
    if(!interface_target)throw std::runtime_error("unbound interface port: "+port->name());
  }
  if(interface_target||(receiver&&(receiver->tok_type()==vtMOD_INST||receiver->tok_type()==vtMOD))) {
    if(_with)throw std::runtime_error("hierarchical calls do not support a with clause");
    auto* target=interface_target;
    if(receiver&&receiver->tok_type()==vtMOD)target=static_cast<VeriMod*>(receiver);
    if(!target) {
      auto* symbol=static_cast<VeriModInst*>(receiver);
      auto* instance=static_cast<VeriModInstance*>(symbol->instance());
      auto* declaration=static_cast<VeriModInstantiation*>(instance->father());
      // An absent source module has no elaborated hive. Report that cause
      // before a member lookup can misdiagnose an unpacked-array reference.
      if(!declaration->inst_mod())
        throw std::runtime_error("line "+std::to_string(instance->line())+": unresolved module "+declaration->mod_name()+
          " (instance "+symbol->name()+"); include its RTL source in the compilation or file list");
      target=static_cast<VeriMod*>(instance->hive());
    }
    if(!target||!target->scope())throw std::runtime_error("hierarchical instance is not elaborated: "+_member);
    if(target->is_interface()) {
      _interface_reference=true;_interface_writable=true;
      if(!interface_view.empty()) {
        auto view=target->modports().find(interface_view);
        if(view==target->modports().end())throw std::runtime_error("unknown modport: "+interface_view);
        auto member=view->second.find(_member);
        if(member==view->second.end())throw std::runtime_error("member "+_member+" is not visible via modport "+interface_view);
        _interface_writable=member->second!=vpIN&&member->second!=vpCONST_REF;
      } else if(target->modports().count(_member)) {_interface_view_instance=target;return OK;}
    }
    auto* symbol=target->scope()->value_same_level(_member);
    if(_called) {
      if(!target->is_interface())throw std::runtime_error("hierarchical module task/function calls are not supported yet");
      if(!symbol||(symbol->tok_type()!=vtFUNC&&symbol->tok_type()!=vtTASK))throw std::runtime_error("interface member is not a subroutine: "+_member);
      if(!interface_view.empty()&&target->modports().at(interface_view).at(_member)!=vpIMPORT)
        throw std::runtime_error("subroutine requires a modport import: "+_member);
      VeriNode* declaration=symbol->tok_type()==vtFUNC?static_cast<VeriNode*>(static_cast<VeriFunc*>(symbol)->func()):static_cast<VeriNode*>(static_cast<VeriTask*>(symbol)->task());
      if(symbol->tok_type()==vtFUNC)set_signed(static_cast<VeriFuncDecl*>(declaration)->is_signed());
      _call_instance=target;
      _interface_prototype=target->modport_prototype(interface_view,_member);
      return unfold_subroutine(this,declaration,target->scope(),stack,_hive);
    }
    _hierarchical_symbol=symbol;
    if(!_hierarchical_symbol)throw std::runtime_error("line "+std::to_string(line())+": unknown hierarchical member "+_member);
    if(_hierarchical_symbol->detail_type()!=vsDECL_CLOCKING&&_hierarchical_symbol->tok_type()!=vtMOD_INST&&_hierarchical_symbol->tok_type()!=vtPARAM&&_hierarchical_symbol->tok_type()!=vtVAR&&_hierarchical_symbol->tok_type()!=vtINT)
      throw std::runtime_error("unsupported hierarchical member type: "+_member);
    if(_hierarchical_symbol->tok_type()==vtVAR)set_signed(static_cast<VeriVar*>(_hierarchical_symbol)->is_signed());
    else if(_hierarchical_symbol->tok_type()==vtINT)set_signed(IS_TRUE);
    else if(_hierarchical_symbol->tok_type()==vtPARAM)set_signed(static_cast<VeriParam*>(_hierarchical_symbol)->is_signed());
    return OK;
  }
  {
    if(veri_event_symbol(_object)) {
      if(_member!="triggered"||_called)
        throw std::runtime_error("line "+std::to_string(line())+": event supports only triggered without arguments");
      _event_query=true;set_signed(IS_FALSE);return OK;
    }
  }
  if(veri_array_ordering(this)) {
    if(!veri_parser->systemverilog())throw std::runtime_error("array ordering methods require SystemVerilog mode");
    if(veri_array_shape(_object).unpacked!=1)throw std::runtime_error("array ordering requires one remaining unpacked dimension");
    const int kind=veri_array_container_kind(_object);
    if(kind==vrASSOC_INT||kind==vrASSOC_UINT||kind==vrASSOC_STRING||kind==vrASSOC_CLASS)
      throw std::runtime_error("array ordering does not support associative arrays");
    if(_arguments&&!_with)throw std::runtime_error("array ordering arguments require a with clause");
    if(_with&&_member=="reverse")throw std::runtime_error("reverse does not accept a with clause");
    set_signed(IS_FALSE);return OK;
  }
  if(veri_array_locator(this)) {
    if(!veri_parser->systemverilog())throw std::runtime_error("array locator methods require SystemVerilog mode");
    if(veri_array_shape(_object).unpacked!=1)throw std::runtime_error("array locator requires one remaining unpacked dimension");
    if(_arguments&&!_with)throw std::runtime_error("array locator arguments require a with clause");
    if(_member.rfind("find",0)==0&&!_with)throw std::runtime_error("array find methods require a with clause");
    auto* symbol=veri_array_element_symbol(_object);
    if(!symbol)throw std::runtime_error("array locator requires unpacked array storage");
    const bool index=_member.find("index")!=std::string::npos;
    const int kind=veri_array_container_kind(_object);
    if(index&&kind==vrASSOC_STRING)throw std::runtime_error("string-index locator result queues are not supported yet");
    auto* key=index?veri_associative_key_type(_object):nullptr;
    const bool class_index=index&&kind==vrASSOC_CLASS;
    const int width=index?(key?key->dlen():32):veri_array_element_width(_object);
    const int sign=index?(key?key->is_signed():kind==vrASSOC_UINT||class_index?IS_FALSE:IS_TRUE):symbol->tok_type()==vtINT?IS_TRUE:symbol->tok_type()==vtFUNC?static_cast<VeriFunc*>(symbol)->func()->is_signed():symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->is_signed():static_cast<VeriTfVar*>(symbol)->is_signed();
    const int type=index?(key?key->net_type():vvINT2):symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->net_type():symbol->tok_type()==vtTFVAR?static_cast<VeriTfVar*>(symbol)->net_type():vvLOGIC;
    _array_result=new VeriVar(veri_parser->next_id(),line(),col(),"$locator_result",vpNO_IO,type,sign,vpVECTOR,0,0,width-1,0,nullptr,nullptr,0,birth_mod());
    veri_parser->insert_node(_array_result);_array_result->set_father(this);_array_result->set_scope(scope());
    _array_result->set_container(vrQUEUE);_array_result->add_range(0,-1);
    if(key)_array_result->infer_associative_index(key);
    if(!index){_array_result->set_class_type(veri_class_type(symbol));_array_result->set_enum_type(veri_enum_type(symbol));_array_result->set_aggregate_type(veri_aggregate_type(symbol));}
    set_signed(sign);return OK;
  }
  if(veri_array_reduction(this)) {
    if(!veri_parser->systemverilog())throw std::runtime_error("array reduction methods require SystemVerilog mode");
    if(_arguments&&!_with)throw std::runtime_error("array reduction methods accept no arguments without a with clause");
    if(veri_array_shape(_object).unpacked!=1)throw std::runtime_error("array reduction requires one remaining unpacked dimension");
    auto* symbol=veri_array_element_symbol(_object);
    if(!symbol)throw std::runtime_error("array reduction requires unpacked integral storage");
    set_signed(symbol->tok_type()==vtFUNC?static_cast<VeriFunc*>(symbol)->func()->is_signed():symbol->tok_type()==vtINT?IS_TRUE:symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->is_signed():static_cast<VeriTfVar*>(symbol)->is_signed());
    return OK;
  }
  if(veri_string_value(_object)&&!veri_array_shape(_object).unpacked) {
    if(_object->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(_object)->pri_type()==veSTR)throw std::runtime_error("line "+std::to_string(line())+": string method receiver requires a variable or method expression");
    const auto args=veri_system_arguments(_arguments);
    const bool parse=_member=="atoi"||_member=="atohex"||_member=="atooct"||_member=="atobin";
    const bool convert=_member=="itoa"||_member=="hextoa"||_member=="octtoa"||_member=="bintoa";
    const size_t count=(_member=="substr"||_member=="putc")?2:(_member=="getc"||_member=="compare"||_member=="icompare"||convert)?1:0;
    if(_member!="len"&&_member!="getc"&&_member!="substr"&&_member!="toupper"&&_member!="tolower"&&_member!="compare"&&_member!="icompare"&&_member!="putc"&&!parse&&!convert)
      throw std::runtime_error("line "+std::to_string(line())+": unsupported string method "+_member);
    if(args.size()!=count)throw std::runtime_error("line "+std::to_string(line())+": string method argument count mismatch");
    set_signed(_member=="len"||_member=="getc"||_member=="compare"||_member=="icompare"||parse?IS_TRUE:IS_FALSE);return OK;
  }
  if(auto* symbol=veri_array_element_symbol(_object)) {
    const int kind=veri_array_container_kind(_object);
    if((kind==vrQUEUE||kind==vrASSOC_INT||kind==vrASSOC_UINT||kind==vrASSOC_STRING||kind==vrASSOC_CLASS)&&veri_array_shape(_object).unpacked) {
      const auto args=veri_system_arguments(_arguments);const bool queue=kind==vrQUEUE;
      int count=-1;
      if(_member=="size"||(!queue&&_member=="num")||(queue&&(_member=="pop_front"||_member=="pop_back")))count=0;
      if((queue&&(_member=="push_front"||_member=="push_back"))||(!queue&&(_member=="exists"||_member=="first"||_member=="last"||_member=="next"||_member=="prev")))count=1;
      if(queue&&_member=="insert")count=2;
      if(_member=="delete")count=int(args.size())<=1?int(args.size()):-1;
      if(!_called||count<0||int(args.size())!=count)
        throw std::runtime_error("line "+std::to_string(line())+": invalid "+std::string(queue?"queue":"associative array")+" method or argument count: "+_member);
      const bool pop=_member=="pop_front"||_member=="pop_back";
      set_signed(pop?(symbol->tok_type()==vtFUNC?static_cast<VeriFunc*>(symbol)->func()->is_signed():symbol->tok_type()==vtINT?IS_TRUE:symbol->tok_type()==vtVAR?static_cast<VeriVar*>(symbol)->is_signed():static_cast<VeriTfVar*>(symbol)->is_signed()):IS_TRUE);
      return OK;
    }
  }
  if(veri_array_shape(_object).unbound) {
    if((_member!="size"&&_member!="delete")||!_called||_arguments)
      throw std::runtime_error("line "+std::to_string(line())+": dynamic array supports only size() and delete() without arguments");
    set_signed(IS_TRUE);return OK;
  }
  if(auto* type=veri_enum_type(_object)) {
    auto error=[&](const std::string& text){throw std::runtime_error("line "+std::to_string(line())+": enum method "+text);};
    bool iterate=_member=="next"||_member=="prev";
    if(!iterate&&_member!="first"&&_member!="last"&&_member!="num"&&_member!="name")
      error("unknown method "+_member);
    auto args=veri_system_arguments(_arguments);
    if(args.size()>(iterate?1u:0u))error(_member+" has too many arguments");
    _method_type=type;set_signed(_member=="num"?IS_TRUE:type->is_signed());
    auto& values=type->enum_values();if(values.empty())error("has no resolved members");
    if(_member=="name"){set_signed(IS_FALSE);return OK;}
    const VeriNum* selected=nullptr;std::unique_ptr<VeriNum> owned;
    if(_member=="first")selected=values.front();
    else if(_member=="last")selected=values.back();
    else if(_member=="num") {
      owned.reset(new VeriNum(0,line(),col(),birth_mod()));auto text=std::to_string(values.size());owned->parse(text.c_str(),text.size());selected=owned.get();
    } else if(veri_elaboration_constant(this)) {
      auto value=veri_constant_value(static_cast<VeriExp*>(_object),0);
      uint32_t count=1;
      if(!args.empty()) {
        auto amount=veri_constant_value(static_cast<VeriExp*>(args[0]),32);if(!amount)return OK;
        count=0;for(int bit=0;bit<32;++bit){int v=amount->get_certain_bit(bit);if(v==V1||v==VX)count|=uint32_t(1)<<bit;}
      }
      if(!value)return OK;
      for(size_t i=0;i<values.size();++i) {
        bool equal=value->bits()==values[i]->bits();
        for(int b=0;equal&&b<value->bits();++b)equal=value->get_certain_bit(b)==values[i]->get_certain_bit(b);
        if(equal){size_t delta=count%values.size();selected=values[(_member=="next"?i+delta:i+values.size()-delta)%values.size()];break;}
      }
      if(!selected) {
        owned.reset(new VeriNum(0,line(),col(),birth_mod()));std::string text=std::to_string(type->dlen())+"'b"+std::string(size_t(type->dlen()),veri_two_state(type->net_type())?'0':'x');
        owned->parse(text.c_str(),text.size());selected=owned.get();
      }
    }
    if(selected) {
      auto* result=new VeriNum(veri_parser->next_id(),selected);veri_parser->insert_node(result);
      if(is_signed()==IS_TRUE)result->set_signed();else result->set_unsigned();
      result->set_father(this);result->set_scope(scope());set_calc_value(result);
    }
    return OK;
  }
  if(_called)throw std::runtime_error("line "+std::to_string(line())+": method call requires an enum receiver");
  auto* type=veri_aggregate_type(_object);
  if(!type)throw std::runtime_error("line "+std::to_string(line())+": member base is not a packed aggregate");
  for(const auto& f:type->packed_fields())if(f.name==_member){_field=&f;break;}
  if(!_field)throw std::runtime_error("line "+std::to_string(line())+": unknown packed member "+_member);
  set_signed(_field->symbol->is_signed());
  if(veri_elaboration_constant(_object))if(auto* value=static_cast<VeriExp*>(_object)->calc_value()) {
    std::string bits=std::to_string(_field->symbol->dlen())+"'b";
    for(int i=_field->symbol->dlen()-1;i>=0;--i) {int b=value->get_certain_bit(i+_field->offset);bits+=b==V0?'0':b==V1?'1':b==VX?'x':'z';}
    auto* result=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());veri_parser->insert_node(result);
    result->parse(bits.c_str(),bits.size());if(is_signed()==IS_TRUE)result->set_signed();
    if(veri_two_state(_field->symbol->net_type()))result->to_two_state();
    result->set_father(this);result->set_scope(scope());set_calc_value(result);
  }
  return OK;
}
int VeriMemberExp::replace_node(Uint id,NodeList& nodes,NodeList::iterator& current) {
  auto it=current;VeriNode* args=nullptr;VeriNode* mapping=nullptr;
  if(_with){mapping=*(--it);nodes.erase(it);it=current;}
  if(_arguments){args=*(--it);nodes.erase(it);it=current;}
  auto* object=*(--it);
  auto* node=new VeriMemberExp(id,line(),col(),object,_member,birth_mod());
  node->_scope_reference=_scope_reference;
  if(_called)node->set_call(args);
  if(mapping){if(_with_constraint)node->set_with_constraint(mapping);else node->set_with(mapping);}
  object->set_father(node);nodes.erase(it);*current=node;return OK;
}

void
VeriArrayExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  _range_from.clear();
  _range_to.clear();
  _not_calc = IS_TRUE;
  _is_whole = IS_TRUE;
  _dstart   = 0;
  _dend     = 0;
  _dimen.clear( );
}

int
VeriArrayExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  mqueue.push( _id );
  iqueue.push( depth );

  NodeList::iterator it = _range.begin();
  for( ; it != _range.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriArrayExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_range( _range_from, _range_to );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _id );

  NodeList::iterator it = _range.begin();
  for( ; it != _range.end(); ++it )
    ofile << dot_str_conn( idx(), *it );
  
  return OK;
}

int
VeriArrayExp::check_child_validation( void )
{
  if(_id&&_id->detail_type()==veEXP_MEMBER)return OK;
  if( _id != NULL && _id->detail_type() == veEXP_PRI )
  {
    VeriPrimaryExp *pid = static_cast<VeriPrimaryExp *>(_id);
    if( pid->pri_type() == veVAR )
    {
      NodeList::iterator it = _range.begin();
      for( ; it != _range.end(); ++it )
      {
        if( (*it)->detail_type() != veEXP_RANGE )
        {
          veri_err->append_err( ERR_ERROR, _id->line(),
                      _id->col(), vCHILD_TYPE_ARRAY_EXP );
          return vCHILD_TYPE_ARRAY_EXP;
        }
      }
      return OK;
    }
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_ARRAY_EXP );
  return vCHILD_TYPE_ARRAY_EXP;
}

int
VeriArrayExp::process_node_2nd( NodeVec& mstack, String& help_info )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vARRAY_S );
      return re;
      break;

    case vARRAY_S:
      if( is_decl() == IS_TRUE )
        return calc_range( );
      else
      {
        for(auto* item:_range) {
          auto* range=static_cast<VeriRangeExp*>(item);
          if(range->rtype()==vrQUEUE) {
            auto* last=veri_parser->gen_primary("$",range->line(),range->col(),veQUEUE_LAST);
            range->set_left(last);last->set_father(range);last->set_scope(scope());
            static_cast<VeriExp*>(last)->set_signed(IS_TRUE);range->set_rtype(range->right()?vrSEMI:vrSINGLE);
          } else if(range->rtype()>=vrOPEN)
            throw std::runtime_error("runtime container dimensions require a declaration");
        }
        re = type_deduction( help_info );
        if( re == vSEARCH_DECL )
          set_pstatus( vSEARCH_DECL_S );
        else
          set_pstatus( vEND_S );
        return re;
      }
      break;

    case vSEARCH_DECL_S :
      re = type_deduction( help_info );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return OK;
      break;
  }
}

int
VeriArrayExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _range.rbegin();
  for( ; it != _range.rend(); ++it )
  {
    //(*it)->clean_up( );
    static_cast<VeriExp *>(*it)->set_signed( is_signed() );
    (*it)->set_scope( scope( ) );
    (*it)->set_is_trash( is_trash() );
    mstack.push_back( *it );
  }

  //_id->clean_up( );
  _id->set_is_trash( is_trash() );
  _id->set_is_decl( _id->detail_type()==veEXP_PRI?IS_TRUE:IS_FALSE );
  _id->set_scope( scope() );
  mstack.push_back( _id );

  return OK;
}

int
VeriArrayExp::calc_range( void )
{
  VeriPrimaryExp * pexp = static_cast<VeriPrimaryExp *>(_id);
  _name = pexp->str();

  VeriRangeExp *range_exp = NULL;
  _not_calc = IS_FALSE;
  _range_from.clear();
  _range_to.clear();
  NodeList::iterator it = _range.begin();
  for( ; it != _range.end(); ++it )
  {
    range_exp = static_cast<VeriRangeExp *>(*it);
    if( range_exp->not_calc( ) == IS_FALSE )
    {
      // Dimension 1 is the leftmost unpacked dimension, matching subscripts,
      // array queries and foreach. Reversing these lists swaps array axes.
      int first=range_exp->range_from(),last=range_exp->range_to();
      if(range_exp->rtype()>=vrOPEN) {
        first=0;last=-1;
      } else if(range_exp->rtype()==vrSINGLE) {
        if(first<=0)throw std::runtime_error("line "+std::to_string(line())+": unpacked array size must be positive");
        last=first-1;first=0;
      } else if(range_exp->rtype()!=vrSEMI)throw std::runtime_error("line "+std::to_string(line())+": unpacked declaration requires fixed bounds");
      _range_from.push_back(first);
      _range_to.push_back(last);
    }
    else
      _not_calc = IS_TRUE;
  }

  if( _not_calc == IS_TRUE )
  {
    veri_err->append_err( ERR_ERROR, this, vSEC_ARRAY_DECL_RANGE_UNKNOWN );
    return vSEC_ARRAY_DECL_RANGE_UNKNOWN;
  }

  return OK;
}

int
VeriArrayExp::type_deduction( String& help_info )
{
  if(_id->detail_type()==veEXP_MEMBER){_not_calc=IS_TRUE;return OK;}
  VeriPrimaryExp *pid = static_cast<VeriPrimaryExp *>(_id);
  _name = pid->str();
  VeriNode *symbol = reduction_binding(this,pid->str());
  if(!symbol)symbol=scope()->value_within_module( pid->str() );
  if( symbol == NULL )
  {
    if( pstatus( ) == vARRAY_S )
    {
      help_info = _name;
      return vSEARCH_DECL;
    }
    else
    {
      veri_err->append_err( ERR_ERROR, _id, vSEC_SYMBOL_NOT_FOUND );
      return vSEC_SYMBOL_NOT_FOUND;
    }
  }
  else
  {
    switch( symbol->tok_type( ) )
    {
      case vtVAR : case vtINT : case vtTFVAR : case vtFUNC : case vtPARAM : case vtGENVAR :
        pid->set_var( symbol );
        break;

      default:
        veri_err->append_err( ERR_ERROR, _id, vSEC_SYMBOL_MIS_MATCH );
        return vSEC_SYMBOL_MIS_MATCH;
        break;
    }
  }

  pid->set_var( symbol );
  if(veri_queue_slice(this)){_not_calc=IS_TRUE;return OK;}
  if(veri_dynamic_string_value(symbol)&&!veri_array_shape(symbol).unpacked) {
    if(_range.size()!=1||static_cast<VeriRangeExp*>(_range.front())->rtype()!=vrSINGLE)
      throw std::runtime_error("line "+std::to_string(line())+": string indexing requires one character index");
    _not_calc=IS_TRUE;return OK;
  }
  if(symbol->tok_type()==vtPARAM||symbol->tok_type()==vtGENVAR) {
    if(_range.size()!=1)throw std::runtime_error("line "+std::to_string(line())+": constant parameter selects require one packed dimension");
    auto shape=veri_array_shape(symbol);
    if(shape.dimensions.size()!=1)throw std::runtime_error("line "+std::to_string(line())+": parameter select requires an integral packed value");
    auto* range=static_cast<VeriRangeExp*>(_range.front());
    for(auto* bound:{range->left(),range->right()})if(bound&&(!veri_elaboration_constant(bound)||!static_cast<VeriExp*>(bound)->calc_value())) {_not_calc=IS_TRUE;return OK;}
    _not_calc=IS_FALSE;
    auto* source=symbol->tok_type()==vtPARAM?static_cast<VeriParam*>(symbol)->get_val():static_cast<VeriGenVar*>(symbol)->get_val();
    if(!source){_not_calc=IS_TRUE;return OK;}
    const bool unknown_index=static_cast<VeriExp*>(range->left())->calc_value()->no_xz()!=IS_TRUE;
    int first=range->range_from(),last=range->range_to();
    if(range->rtype()==vrSINGLE)last=first;
    const auto axis=shape.dimensions.front();
    if(range->rtype()==vrRAN_ADD||range->rtype()==vrRAN_SUB) {
      const int count=last;
      if(count<1||count>1048576)throw std::runtime_error("indexed parameter select requires a positive width <=1048576");
      const int64_t other=int64_t(first)+(range->rtype()==vrRAN_ADD?count-1:1-count);
      if(other<INT32_MIN||other>INT32_MAX)throw std::runtime_error("indexed parameter select exceeds supported index range");
      last=int(other);if((first>last)!=(axis.first>axis.second))std::swap(first,last);
    }
    if(range->rtype()==vrSEMI&&first!=last&&((first>last)!=(axis.first>axis.second)))
      throw std::runtime_error("line "+std::to_string(line())+": constant part select direction does not match its packed range");
    const int64_t width=std::abs(int64_t(first)-last)+1;
    if(width>1048576)throw std::runtime_error("parameter select exceeds supported width");
    String text=std::to_string(width)+"'b";
    const int direction=first<=last?1:-1;
    for(int64_t index=first;;index+=direction) {
      const int64_t offset=axis.first>=axis.second?index-axis.second:axis.second-index;
      const int value=unknown_index||offset<0||offset>=source->bits()?VX:source->get_certain_bit(int(offset));
      text+=value==VX?'x':value==VZ?'z':value==V1?'1':'0';if(index==last)break;
    }
    auto* result=new VeriNum(veri_parser->next_id(),line(),col(),birth_mod());
    result->parse(text.c_str(),text.size());result->set_father(this);result->set_scope(scope());
    veri_parser->insert_node(result);set_calc_value(result);return OK;
  }
  if(reduction_binding(this,pid->str())==symbol){_not_calc=IS_TRUE;return OK;}
  // Packed formals and the function result are runtime storage. Their
  // ranges are checked by lowering; never publish a stale parser value.
  if(symbol->tok_type()==vtTFVAR||symbol->tok_type()==vtFUNC){
    if(veri_array_shape(symbol).dimensions.empty())
      throw std::runtime_error("line "+std::to_string(line())+": packed select requires a vector, not a scalar subroutine variable");
    _not_calc=IS_TRUE;return OK;
  }
  if(symbol->tok_type()==vtVAR) {
    auto* var=static_cast<VeriVar*>(symbol);
    if(veri_array_shape(symbol).dimensions.size()>size_t(var->range_depth()+1)){
      _not_calc=IS_TRUE;return OK;
    }
  }
  if( _not_calc == IS_TRUE )
    return OK;

  unsigned int last, i;
  int dlen;
  NodeList::iterator it = _range.begin();
  VeriRangeExp *range_exp = NULL;

  switch( pid->var()->tok_type() )
  {
    case vtVAR :
    {
      VeriVar *var = static_cast<VeriVar *>(pid->var() );
      if( var->range_depth() == 0 )
      {
        _not_calc = IS_TRUE;
        veri_err->append_err( ERR_ERROR, pid, vSEC_VAR_RANGE_OVERLOAD );
        return vSEC_VAR_RANGE_OVERLOAD;
      }
      
      last = _range.size() - var->range_depth( );
      if( last != 0 && last != 1 )
      {
        _not_calc = IS_TRUE;
        veri_err->append_err( ERR_ERROR, pid, vSEC_VAR_RANGE_OVERLOAD );
        return vSEC_VAR_RANGE_OVERLOAD;
      }

      for( i = 0; i < _range.size() - last; ++i, ++it )
      {
        var->get_range( i+1, _dstart, _dend, dlen );
        range_exp = static_cast<VeriRangeExp *>(*it);
        if( range_exp->rtype() != vrSINGLE )
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_ARRAY_DECL_RANGE_UNKNOWN );
          return vSEC_ARRAY_DECL_RANGE_UNKNOWN;
        }
        else if(    (    range_exp->range_from() <= _dend
                      && range_exp->range_from() >= _dstart )
                 || (    range_exp->range_from() >= _dend
                      && range_exp->range_from() <= _dstart ) )
        {
          // this is ok
          _dimen.push_back( range_exp->range_from( ) );
        }
        else
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_TYPE_MISMATCH );
          return vSEC_TYPE_MISMATCH;
        }
      }
      
      if( last == 1 )
      {
        _is_whole = IS_FALSE;
        var->get_range( i+1, _dstart, _dend, dlen );
        range_exp = static_cast<VeriRangeExp *>(*it);
        if(      range_exp->rtype() != vrSINGLE
            && (    (    range_exp->range_from() <= _dend
                      && range_exp->range_from() >= _dstart
                      && range_exp->range_to()   <= _dend
                      && range_exp->range_to()   >= _dstart )
                 || (    range_exp->range_from() >= _dend
                      && range_exp->range_from() <= _dstart
                      && range_exp->range_to()   >= _dend
                      && range_exp->range_to()   <= _dstart ) ) )
        {
          _dstart = range_exp->range_from();
          _dend   = range_exp->range_to();
        }
        else if(      range_exp->rtype() == vrSINGLE
                 && (    (    range_exp->range_from() <= _dend
                           && range_exp->range_from() >= _dstart )
                      || (    range_exp->range_from() >= _dend
                           && range_exp->range_from() <= _dstart ) ) )
        {
          _dstart = range_exp->range_from();
          _dend   = range_exp->range_from();
        }
        else
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_TYPE_MISMATCH );
          return vSEC_TYPE_MISMATCH;
        }
      }
//      set_calc_value( var->get_one_num( dimen, _is_whole, _dstart, _dend );
      break;
    }
  
    case vtINT :
    {
      VeriInt *int_var = static_cast<VeriInt *>(pid->var() );
      if( int_var->range_depth() == 0 )
      {
        _not_calc = IS_TRUE;
        veri_err->append_err( ERR_ERROR, pid, vSEC_VAR_RANGE_OVERLOAD );
        return vSEC_VAR_RANGE_OVERLOAD;
      }
      
      last = _range.size() - int_var->range_depth( );
      if( last != 0 && last != 1 )
      {
        _not_calc = IS_TRUE;
        veri_err->append_err( ERR_ERROR, pid, vSEC_VAR_RANGE_OVERLOAD );
        return vSEC_VAR_RANGE_OVERLOAD;
      }

      for( i = 0; i < _range.size() - last; ++i, ++it )
      {
        int_var->get_range( i+1, _dstart, _dend, dlen );
        range_exp = static_cast<VeriRangeExp *>(*it);
        if( range_exp->rtype() != vrSINGLE )
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_ARRAY_DECL_RANGE_UNKNOWN );
          return vSEC_ARRAY_DECL_RANGE_UNKNOWN;
        }
        else if(    (    range_exp->range_from() <= _dend
                      && range_exp->range_from() >= _dstart )
                 || (    range_exp->range_from() >= _dend
                      && range_exp->range_from() <= _dstart ) )
        {
          // this is ok
          _dimen.push_back( range_exp->range_from() );
        }
        else
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_TYPE_MISMATCH );
          return vSEC_TYPE_MISMATCH;
        }
      }
      
      if( last == 1 )
      {
        _is_whole = IS_FALSE;
        int_var->get_range( i+1, _dstart, _dend, dlen );
        range_exp = static_cast<VeriRangeExp *>(*it);
        if(      range_exp->rtype() != vrSINGLE
            && (    (    range_exp->range_from() <= _dend
                      && range_exp->range_from() >= _dstart
                      && range_exp->range_to()   <= _dend
                      && range_exp->range_to()   >= _dstart )
                 || (    range_exp->range_from() >= _dend
                      && range_exp->range_from() <= _dstart
                      && range_exp->range_to()   >= _dend
                      && range_exp->range_to()   <= _dstart ) ) )
        {
          _dstart = range_exp->range_from( );
          _dend   = range_exp->range_to( );
        }
        else if(      range_exp->rtype() == vrSINGLE
                 && (    (    range_exp->range_from() <= _dend
                           && range_exp->range_from() >= _dstart )
                      || (    range_exp->range_from() >= _dend
                           && range_exp->range_from() <= _dstart ) ) )
        {
          _dstart = range_exp->range_from();
          _dend   = range_exp->range_from();
        }
        else
        {
          _not_calc = IS_TRUE;
          veri_err->append_err( ERR_ERROR, _id, vSEC_TYPE_MISMATCH );
          return vSEC_TYPE_MISMATCH;
        }
      }

      set_calc_value( int_var->get_one_num( _dimen, _is_whole, _dstart, _dend ) );
      break;
    }

    default:
      veri_err->append_err( ERR_ERROR, pid, vSEC_ARRAY_NOT_OTHER );
      return vSEC_ARRAY_NOT_OTHER;
      break;
  }
  
  return OK;
}

int
VeriArrayExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _id );

  NodeList::iterator it = _range.begin();
  for( ; it != _range.end(); ++it )
    mstack.push_back( *it );
  
  return OK;
}

int
VeriArrayExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriArrayExp *tmp = new VeriArrayExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  NodeList::iterator it = _range.begin();
  for( ; it != _range.end(); ++it )
  {
    tmp->_range.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_id = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*********************
     * Caller Expression *
     *********************/

void
VeriCallerExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  _hive = NULL;
}

int
VeriCallerExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  mqueue.push( _caller );
  iqueue.push( depth );

  if( _arg != NULL )
  {
    mqueue.push( _arg );
    iqueue.push( depth );
  }
  
  if( _hive != NULL )
  {
    mqueue.push( _hive );
    iqueue.push( depth );
  }

  if( calc_value( ) != NULL )
  {
    mqueue.push( calc_value( ) );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriCallerExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _caller );
  ofile << dot_str_conn( idx(), _arg );
  ofile << dot_str_conn( idx(), _hive );
  ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriCallerExp::check_child_validation( void )
{
  if( _caller == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_CALL_EXP );
    return vCHILD_TYPE_CALL_EXP;
  }

  switch( _caller->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ARRAY :
      break;

    default:
      veri_err->append_err( ERR_ERROR, _caller->line(),
                _caller->col(), vCHILD_TYPE_CALL_EXP );
      return vCHILD_TYPE_CALL_EXP;
      break;
  }

  if( _arg != NULL )
  {
    if( _arg->detail_type() != veEXP_MULTI )
    {
      veri_err->append_err( ERR_ERROR, _arg->line(),
                _arg->col(), vCHILD_TYPE_CALL_EXP );
      return vCHILD_TYPE_CALL_EXP;
    }
    else
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_arg);
      switch( mexp->multi_type() )
      {
        case vemCOMMA_EXP:
        case vemPORT_EXP:
        case vemPORT_INST_EXP :
          break;

        default:
          veri_err->append_err( ERR_ERROR, _arg->line(),
                       _arg->col(), vCHILD_TYPE_CALL_EXP );
          return vCHILD_TYPE_CALL_EXP;
      }
    }
  }

  return OK;
}

int
VeriCallerExp::check_func_call_child_validation( void )
{
  if( _caller == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_CALL_EXP );
    return vCHILD_TYPE_CALL_EXP;
  }

  if( _caller->detail_type() != veEXP_PRI )
  {
    veri_err->append_err( ERR_ERROR, _caller->line(),
                    _caller->col(), vCHILD_TYPE_CALL_EXP );
    return vCHILD_TYPE_CALL_EXP;
  }

  if( _arg != NULL )
  {
    if( _arg->detail_type() != veEXP_MULTI )
    {
      veri_err->append_err( ERR_ERROR, _arg->line(),
                    _arg->col(), vCHILD_TYPE_CALL_EXP );
      return vCHILD_TYPE_CALL_EXP;
    }
    else
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_arg);
      if( mexp->multi_type() != vemCOMMA_EXP )
      {
        veri_err->append_err( ERR_ERROR, _arg->line(),
                       _arg->col(), vCHILD_TYPE_CALL_EXP );
        return vCHILD_TYPE_CALL_EXP;
      }
    }
  }

  return OK;
}

int
VeriCallerExp::process_node_2nd( NodeVec& mstack, String& help_info )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      set_pstatus( vCALL_S );
      return push_children( mstack );
      break;

    case vCALL_S:
      re = unfolding( mstack, help_info );
      if( re == vSEARCH_DECL )
        set_pstatus( vSEARCH_DECL_S );
      else
        set_pstatus( vEND_S );
      return re;
      break;

    case vSEARCH_DECL_S :
      re = unfolding( mstack, help_info );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return get_ret_value( );
      break;
  }
}

int
VeriCallerExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  if( _arg != NULL )
  {
    //_arg->clean_up( );
    _arg->set_scope( scope() );
    static_cast<VeriExp *>(_arg)->set_signed( is_signed() );
    mstack.push_back( _arg );
  }

  //_caller->clean_up( );
  _caller->set_is_decl( IS_TRUE );
  _caller->set_scope( scope() );
  mstack.push_back( _caller );

  return OK;
}

int
VeriCallerExp::unfolding( NodeVec& mstack, String& help_info )
{
  if( _hive != NULL )
    return vSEC_CALLER_REUNFOLD;

  VeriNode *tf = NULL;
  switch( _caller->detail_type() )
  {
    case veEXP_PRI:
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(_caller);
      _caller_name = pexp->str();
      tf = scope()->value(pexp->str());
      if(!tf) {
        // A constant parameter may call a module function whose declaration
        // occurs later in the source. Bind that declaration on demand in its
        // lexical module; do not reorder unrelated typedefs or imports.
        auto* owner=father();while(owner&&owner->tok_type()!=vtMOD)owner=owner->father();
        if(owner) {
          auto* module=static_cast<VeriMod*>(owner);
          if(module->item())for(auto* item:static_cast<VeriModuleItemList*>(module->item())->item_list())
            if(item->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(item)->func_name()==_caller_name) {
              if(item->pstatus()!=vSTART_S)throw std::runtime_error("line "+std::to_string(line())+": cyclic function declaration dependency: "+_caller_name);
              veri_bind_semantic(item,module->scope());tf=module->scope()->value_same_level(_caller_name);break;
            }
        }
      }
      if( tf == NULL )
      {
        if( pstatus( ) == vCALL_S )
        {
          help_info = _caller_name;
          return vSEARCH_DECL;
        }
        else
        {
          veri_err->append_err( ERR_ERROR, _caller, vSEC_TF_NOT_FOUND, " '"+_caller_name+"'" );
          return vSEC_TF_NOT_FOUND;
        }
      }
      break;
    }

    case veEXP_ARRAY:
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(_caller);
      _caller_name = aexp->name();
      tf = scope()->value(aexp->name());
      if( tf == NULL )
      {
        if( pstatus( ) == vCALL_S )
        {
          help_info = _caller_name;
          return vSEARCH_DECL;
        }
        else
        {
          veri_err->append_err( ERR_ERROR, _caller, vSEC_TF_NOT_FOUND, " '"+_caller_name+"'" );
          return vSEC_TF_NOT_FOUND;
        }
      }
      break;
    }

    default:
      break;
  }

  if(auto* sequence=veri_sequence_definition(tf)) {
    if(_caller->detail_type()!=veEXP_PRI)throw std::runtime_error("indexed sequence calls are not supported yet");
    if(!veri_sequence_term(this))throw std::runtime_error("sequence call requires a standalone sequence term: "+_caller_name);
    if(_arg&&!static_cast<VeriMultiExp*>(_arg)->exp().empty())throw std::runtime_error("sequence actual arguments are not supported yet: "+_caller_name);
    // Unlike a function hive, this is a non-owning symbol binding. It must not
    // be expanded or enter the caller's clone/cleanup traversal.
    static_cast<VeriPrimaryExp*>(_caller)->set_var(sequence);
    return OK;
  }
  switch( tf->tok_type( ) )
  {
    case vtTASK :
      tf = (static_cast<VeriTask *>(tf))->task();
      break;

    case vtFUNC :
      tf = (static_cast<VeriFunc *>(tf))->func();
      break;

    default:
      veri_err->append_err( ERR_ERROR, tf, vSEC_TF_NOT_FOUND );
      return vSEC_SYMBOL_NOT_FOUND;
      break;
  }

  // Qualified class calls must bind their body in the declaring class, even
  // when invoked from a module or another class with identically named fields.
  auto* context=tf->birth_mod()->is_package()?tf->birth_mod()->scope():scope();
  if(tf->scope()&&veri_class_type(tf->scope()->value("this")))context=tf->scope();
  return unfold_subroutine(this,tf,context,mstack,_hive);
}

int
VeriCallerExp::get_ret_value( void )
{
  // Only a separate interpreter with a private, pure argument environment
  // may publish a constant. Never reuse speculative runtime symbol values.
  auto value=veri_constant_function(this);
  if(value) {
    auto* number=new VeriNum(veri_parser->next_id(),value.get());
    number->set_father(this);number->set_scope(scope());veri_parser->insert_node(number);set_calc_value(number);
  }
  return OK;
}

int
VeriCallerExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _caller );

  if( _arg != NULL )
    mstack.push_back( _arg );

  return OK;
}

int
VeriCallerExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCallerExp *tmp = new VeriCallerExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  if( _arg != NULL )
  {
    tmp->_arg = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_caller = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*********************
     * Binary Expression *
     *********************/

void
VeriBinaryExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriBinaryExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _left );
  mqueue.push( _right );
  iqueue.push( depth );
  iqueue.push( depth );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriBinaryExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_op( _op );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _left );
  ofile << dot_str_conn( idx(), _right );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriBinaryExp::check_child_validation( VeriNode *child )
{
  if(_op==vtBINSIDE&&child==_right&&child&&child->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(child)->multi_type()==vemINSIDE_SET)return OK;
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_ASSIGN  :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, child->line(),
                       child->col(), vCHILD_TYPE_BIN_EXP );
        return vCHILD_TYPE_BIN_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                       child->col(), vCHILD_TYPE_BIN_EXP );
          return vCHILD_TYPE_BIN_EXP;
        }
        break;
      }

      case veEXP_MINTY :
      {
        veri_err->append_err( ERR_ERROR, child->line(),
                     child->col(), vCHILD_TYPE_BIN_EXP );
        return vCHILD_TYPE_BIN_EXP;
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                       child->col(), vCHILD_TYPE_BIN_EXP );
            return vCHILD_TYPE_BIN_EXP;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_BIN_EXP );
  return vCHILD_TYPE_BIN_EXP;
}

int
VeriBinaryExp::check_child_validation( void )
{
  int re;
  re = check_child_validation( _left  );
  if( re != OK )
    return re;

  re = check_child_validation( _right );
  if( re != OK )
    return re;
  return OK;
}

int
VeriBinaryExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      switch( _op )
      {
        case vtBDOR :
        case vtBDAND :
          re = push_short_cut_left( mstack );
          set_pstatus( vSHORT_CUT_S );
          return re;
          break;

        default:
          re = push_children( mstack );
          set_pstatus( vEND_S );
          return re;
      }
      break;

    case vSHORT_CUT_S :
      re = process_short_cut_left( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_binary_op( );
      break;
  }
}

int
VeriBinaryExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_right->clean_up( );
  _right->set_is_trash( is_trash() );
  _right->set_scope( scope() );
  mstack.push_back( _right );

  //_left->clean_up( );
  _left->set_is_trash( is_trash() );
  _left->set_scope( scope() );
  mstack.push_back( _left );
  return OK;
}

int
VeriBinaryExp::push_short_cut_left( NodeVec& mstack )
{
  mstack.push_back( this );

  //_left->clean_up( );
  _left->set_is_trash( is_trash() );
  _left->set_scope( scope() );
  mstack.push_back( _left );

  return OK;
}

int
VeriBinaryExp::process_short_cut_left( NodeVec& mstack )
{
  // Short circuit execution belongs to the generated program, not name binding.
  mstack.push_back(this);_right->set_is_trash(is_trash());_right->set_scope(scope());mstack.push_back(_right);return OK;
}

int
VeriBinaryExp::process_binary_op( void )
{
  VeriExp * left  = static_cast<VeriExp *>(_left);
  VeriExp * right = static_cast<VeriExp *>(_right);

  int re = OK;

  if(veri_streaming(this)) {
    set_signed(IS_FALSE);
    if(!veri_stream_slice(this))throw std::runtime_error("stream slice size must be a known positive integral constant in 1..1048576");
    if(veri_elaboration_constant(right)) {
      auto value=veri_constant_value(this,0);
      if(value){auto* number=new VeriNum(veri_parser->next_id(),value.get());veri_parser->insert_node(number);number->set_father(this);number->set_scope(scope());set_calc_value(number);}
    }
    return OK;
  }

  if(veri_is_cast(_op)) {
    if(left->detail_type()==veEXP_PRI) {
      auto* symbol=static_cast<VeriPrimaryExp*>(left)->var();
      if(symbol&&symbol->tok_type()==vtTYPE) {
        auto* type=static_cast<VeriVar*>(symbol);
        // Unpacked casts retain the complete destination descriptor. Folding
        // into the element width would discard the stream and its array shape.
        if(type->range_depth()) {set_signed(type->is_signed());return OK;}
        _op=type->net_type()==vvCHANDLE?vtCAST_CHANDLE:type->net_type()==vvSTRING?vtCAST_STRING:veri_real(type->net_type())?(type->net_type()==vvSHORTREAL?vtCAST_SHORTREAL:vtCAST_REAL):veri_two_state(type->net_type())?(type->is_signed()==IS_TRUE?vtCAST_SIGNED2:vtCAST_UNSIGNED2)
                                              :(type->is_signed()==IS_TRUE?vtCAST_SIGNED4:vtCAST_UNSIGNED4);
      }
    }
    if(_op==vtCAST_CHANDLE) {set_signed(IS_FALSE);return OK;}
    if(_op==vtCAST_STRING) {
      set_signed(IS_FALSE);
      if(auto value=veri_constant_value(right,0)) {
        value->to_string_value();auto* number=new VeriNum(veri_parser->next_id(),value.get());
        veri_parser->insert_node(number);number->set_father(this);number->set_scope(scope());set_calc_value(number);
      }
      return OK;
    }
    auto size=veri_constant_value(left,0);
    bool valid=veri_elaboration_constant(left)&&size&&size->no_xz()==IS_TRUE;
    if(valid&&size->is_signed()==IS_TRUE&&size->get_certain_bit(size->bits()-1)==V1)valid=false;
    if(valid) {
      for(int bit=21;bit<size->bits();++bit)if(size->get_certain_bit(bit)!=V0)valid=false;
    }
    const int width=valid?size->get_first_int():0;
    if(!valid||width<1||width>1048576) {
      veri_err->append_err(ERR_ERROR,this,vCAST_WIDTH_INVALID);return vCAST_WIDTH_INVALID;
    }
    auto value=veri_constant_value(right,veri_real_width(right)||_op==vtCAST_REAL||_op==vtCAST_SHORTREAL?0:width);
    if(value) {
      if(value->string_type())throw std::runtime_error("string to numeric casts are not supported yet");
      if(_op==vtCAST_REAL||_op==vtCAST_SHORTREAL)value->set_real(value->real_value(),width);
      else value->truncate_assign(width);
      if(_op==vtCAST_SIGNED4||_op==vtCAST_SIGNED2)value->set_signed();
      if(_op==vtCAST_UNSIGNED4||_op==vtCAST_UNSIGNED2)value->set_unsigned();
      if(_op==vtCAST_SIGNED2||_op==vtCAST_UNSIGNED2)value->to_two_state();
      auto* num=new VeriNum(veri_parser->next_id(),value.get());
      veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());set_calc_value(num);
    }
    return OK;
  }

  if(_op==vtBINSIDE) {
    if(veri_elaboration_constant(this)) {
      auto value=veri_inside_constant(this);
      if(value){auto* number=new VeriNum(veri_parser->next_id(),value.get());veri_parser->insert_node(number);number->set_father(this);number->set_scope(scope());set_calc_value(number);}
    }
    return OK;
  }

  // Whole unpacked values have element/shape semantics, not scalar string or
  // integral semantics. Leave compatibility and storage checks to lowering.
  const auto unpacked=[](VeriNode* value) {
    auto* symbol=veri_array_element_symbol(value);
    return symbol&&veri_array_shape(value).unpacked!=0;
  };
  if(unpacked(left)||unpacked(right)) {
    const bool equality=_op==vtBLEQ||_op==vtBLIEQ||_op==vtBCEQ||_op==vtBCIEQ;
    if(!equality)throw std::runtime_error("unpacked arrays support equality operators only");
    if(!unpacked(left)||!unpacked(right))
      throw std::runtime_error("array equality requires two unpacked array values");
    set_signed(IS_FALSE);return OK;
  }

  // A constant string must obey the same operand rules as a runtime string.
  // String literals may join either the integral or the string domain, whereas
  // an integer expression requires an explicit conversion to enter the latter.
  if(veri_dynamic_string_value(left)||veri_dynamic_string_value(right)) {
    const bool compare=_op==vtBLEQ||_op==vtBLIEQ||_op==vtBCEQ||_op==vtBCIEQ||
                       _op==vtBLT||_op==vtBLE||_op==vtBGT||_op==vtBGE;
    if(!veri_string_value(left)||!veri_string_value(right))
      throw std::runtime_error("mixed string and integral operands require an explicit conversion");
    if(!compare)throw std::runtime_error("unsupported string operator (comparison required)");
  }

  // type check
  if( left->detail_type( ) == veEXP_PRI )
  {
    re = check_primary_not_other( static_cast<VeriPrimaryExp*>(left) );
    if( re != OK )
      return re;
  }

  if( right->detail_type( ) == veEXP_PRI )
  {
    re = check_primary_not_other( static_cast<VeriPrimaryExp*>(right) );
    if( re != OK )
      return re;
  }

  if( right->calc_value( ) != NULL && _op == vtBDOR )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), right->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );

    num->unary_operation( vtUOR );
    if( right->calc_value()->one_bit_value( ) == V1 )
    {
      set_calc_value( num );
      return OK;
    }
    veri_parser->toss_node( num->idx() );
  }
  else if( right->calc_value( ) != NULL && _op == vtBDAND )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), right->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );

    num->unary_operation( vtUOR );
    if( right->calc_value()->one_bit_value( ) == V0 )
    {
      set_calc_value( num );
      return OK;
    }
    veri_parser->toss_node( num->idx() );
  }

  if( left->calc_value() != NULL && right->calc_value() != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), left->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );

    re = num->binary_operation( _op, right->calc_value() );
    if( re != OK )
    {
      veri_err->append_err( ERR_ERROR, right, re );
      veri_parser->toss_node( num->idx() );
      return re;
    }
    set_calc_value( num );
  }
  return OK;
}

int
VeriBinaryExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _left );
  mstack.push_back( _right );
  return OK;
}

int
VeriBinaryExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriBinaryExp *tmp = new VeriBinaryExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  tmp->_right = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_left = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*********************
     * Assign Expression *
     *********************/

void
VeriAssignExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriAssignExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _lval );
  mqueue.push( _rval );
  iqueue.push( depth );
  iqueue.push( depth );
  return OK;
}

int
VeriAssignExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _lval );
  ofile << dot_str_conn( idx(), _rval );

  return OK;
}

int
VeriAssignExp::check_child_validation( VeriNode *child )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, child->line(),
                    child->col(), vCHILD_TYPE_ASSIGN_EXP );
        return vCHILD_TYPE_ASSIGN_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                    child->col(), vCHILD_TYPE_ASSIGN_EXP );
          return vCHILD_TYPE_ASSIGN_EXP;
        }
        else
          return OK;
        break;
      }

      case veEXP_MINTY :
      {
        veri_err->append_err( ERR_ERROR, child->line(),
                  child->col(), vCHILD_TYPE_ASSIGN_EXP );
        return vCHILD_TYPE_ASSIGN_EXP;
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemDYNAMIC_NEW :
          case vemASSIGN_PATTERN :
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                        child->col(), vCHILD_TYPE_ASSIGN_EXP );
            return vCHILD_TYPE_ASSIGN_EXP;
        }
        break;
      }

      default:
        return OK;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_ASSIGN_EXP );
  return vCHILD_TYPE_ASSIGN_EXP;
}

int
VeriAssignExp::check_child_validation( void )
{
  if( _lval != NULL && _rval != NULL )
  {
    bool is_concat_lval = false;
    if( _lval->detail_type() == veEXP_MULTI )
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_lval);
      if( mexp->multi_type() == vemCONCAT_EXP )
        is_concat_lval = true;
    }

    if(    _lval->detail_type() != veEXP_PRI
        && _lval->detail_type() != veEXP_MEMBER
        && _lval->detail_type() != veEXP_ARRAY
        && !is_concat_lval && !veri_streaming(_lval) )
    {
      veri_err->append_err( ERR_ERROR, _lval->line(),
                  _lval->col(), vCHILD_TYPE_ASSIGN_EXP );
      return vCHILD_TYPE_ASSIGN_EXP;
    }

    if( is_decl()!=IS_TRUE && _lval->detail_type() == veEXP_ARRAY )
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(_lval);
      VeriRangeExp *rexp = NULL;
      NodeList& range = aexp->range();
      NodeList::reverse_iterator it = range.rbegin();

      if( aexp->range().size() == (range.size() + 1) )
        ++it;
      else if( aexp->range().size() != range.size() )
      {
        veri_err->append_err( ERR_ERROR, _lval->line(),
                    _lval->col(), vCHILD_TYPE_ASSIGN_EXP );
        return vCHILD_TYPE_ASSIGN_EXP;
      }

      for( ++it; it != range.rend(); ++it )
      {
        if( (*it) == NULL || (*it)->detail_type() != veEXP_RANGE )
        {
          veri_err->append_err( ERR_ERROR, _lval->line(),
                      _lval->col(), vCHILD_TYPE_ASSIGN_EXP );
          return vCHILD_TYPE_ASSIGN_EXP;
        }
        rexp = static_cast<VeriRangeExp *>(*it);
        if( rexp->rtype() != vrSINGLE && !(rexp->rtype()==vrQUEUE&&!rexp->right()) )
        {
          veri_err->append_err( ERR_ERROR, (*it)->line(),
                      (*it)->col(), vCHILD_TYPE_ASSIGN_EXP );
          return vCHILD_TYPE_ASSIGN_EXP;
        }
      }
    }

    if( _rval->tok_type() != vtEXP )
    {
      veri_err->append_err( ERR_ERROR, _rval->line(),
                  _rval->col(), vCHILD_TYPE_ASSIGN_EXP );
      return vCHILD_TYPE_ASSIGN_EXP;
    }

    return check_child_validation( _rval );
  }
  
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_ASSIGN_EXP );
  return vCHILD_TYPE_ASSIGN_EXP;
}

int
VeriAssignExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      // assuming no array-initialization
      return process_assign_op( );
      break;
  }
}

int
VeriAssignExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_rval->clean_up( );
  _rval->set_is_trash( is_trash() );
  _rval->set_scope( scope() );
  mstack.push_back( _rval );

  //_lval->clean_up( );
  _lval->set_is_decl( is_decl() );
  _lval->set_is_trash( is_trash() );
  _lval->set_scope( scope() );
  mstack.push_back( _lval );
  return OK;
}

int
VeriAssignExp::process_assign_op( void )
{
  // A declaration registers its symbol after evaluating the initializer.
  // Its left side is not an existing procedural assignment target yet.
  if( is_decl() == IS_TRUE || veri_streaming(_lval) )
    return OK;

  VeriExp * lval = static_cast<VeriExp *>(_lval);
  VeriExp * rval = static_cast<VeriExp *>(_rval);

  if( rval->calc_value() != NULL )
  {
    VeriPrimaryExp *pexp = NULL;
    VeriArrayExp   *aexp = NULL;

    IVec dummy_dimen;

    switch( lval->detail_type( ) )
    {
      case veEXP_PRI :
      {
        pexp = static_cast<VeriPrimaryExp *>(lval);
        if( pexp->var() == NULL )
          return vSEC_SYMBOL_NOT_FOUND;
         
        int re = check_primary_not_other( pexp );
        if( re != OK )
          return re;

        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
          {
            VeriVar *var = static_cast<VeriVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            if(veri_real_width(var))num->set_real(num->real_value(),veri_real_width(var));else num->truncate_assign( var->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            break;
          }

          case vtTFVAR :
          {
            VeriTfVar *tfvar = static_cast<VeriTfVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            if(veri_real_width(tfvar))num->set_real(num->real_value(),veri_real_width(tfvar));else num->truncate_assign( tfvar->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            tfvar->set_val( num );
            break;
          }

          case vtFUNC :
          {
            VeriFunc *func_ret = static_cast<VeriFunc *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            if(veri_real_width(func_ret))num->set_real(num->real_value(),veri_real_width(func_ret));else num->truncate_assign( func_ret->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            func_ret->set_val( num );
            break;
          }

          case vtPARAM :
          {
            VeriParam *param = static_cast<VeriParam *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( param->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            param->set_val( num );
            break;
          }
          
          case vtINT :
          {
            VeriInt *int_var = static_cast<VeriInt *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( 32 );
            num->set_father( this );
            num->set_scope( scope() );
            int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            break;
          }

          case vtGENVAR :
          {
            VeriGenVar *genvar = static_cast<VeriGenVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( 32 );
            num->set_father( this );
            num->set_scope( scope() );
            genvar->set_val( num );
            break;
          }

          default:
            return vSEC_SYMBOL_NOT_FOUND;
            break;
        }
        break;
      }

      case veEXP_MEMBER:return OK;
      case veEXP_ARRAY :
      {
        aexp = static_cast<VeriArrayExp *>(lval);
        if(aexp->id()&&aexp->id()->detail_type()==veEXP_MEMBER)return OK;
        if(    aexp->id() == NULL
            || aexp->id()->detail_type() != veEXP_PRI )
          return vSEC_TYPE_MISMATCH;
        
        if( aexp->not_calc() == IS_TRUE )
          return OK;

        pexp = static_cast<VeriPrimaryExp *>(aexp->id());
        if( pexp->var() == NULL )
          return vSEC_TYPE_MISMATCH;

        int dlen = abs(aexp->dend() - aexp->dstart()) + 1;
        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
          {
            VeriVar *var = static_cast<VeriVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( dlen );
            num->set_father( this );
            num->set_scope( scope() );
            var->set_one_num( aexp->dimen(), aexp->is_whole(),
                              aexp->dstart(), aexp->dend(), num );
            break;
          }

          case vtINT :
          {
            VeriInt *int_var = static_cast<VeriInt *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( 32 );
            num->set_father( this );
            num->set_scope( scope() );
            int_var->set_one_num( aexp->dimen(), aexp->is_whole(),
                                  aexp->dstart(), aexp->dend(), num );
            break;
          }

          default:
            break;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }

  return OK;
}

int
VeriAssignExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _lval );
  mstack.push_back( _rval );
  return OK;
}

int
VeriAssignExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriAssignExp *tmp = new VeriAssignExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  tmp->_rval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_lval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*************************************
     * Multiple-Concatenation Expression *
     *************************************/

void
VeriMultiConcatExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriMultiConcatExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _exp1 );
  mqueue.push( _exp2 );
  iqueue.push( depth );
  iqueue.push( depth );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriMultiConcatExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp1 );
  ofile << dot_str_conn( idx(), _exp2 );

  return OK;
}

int
VeriMultiConcatExp::check_child_validation( void )
{
  if(    _exp1 != NULL && _exp1->tok_type() == vtEXP
      && _exp2 != NULL && _exp2->tok_type() == vtEXP )
  {
    switch( _exp1->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_MULTI   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, _exp1->line(),
                      _exp1->col(), vCHILD_TYPE_MCONCAT_EXP );
        return vCHILD_TYPE_MCONCAT_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(_exp1);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, _exp1->line(),
                      _exp1->col(), vCHILD_TYPE_MCONCAT_EXP );
          return vCHILD_TYPE_MCONCAT_EXP;
        }
        else
          return OK;
        break;
      }

      default:
        return OK;
    }

    if( _exp2->detail_type() != veEXP_MULTI )
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_exp2);
      if( mexp->multi_type() == vemCONCAT_EXP )
        return OK;
      veri_err->append_err( ERR_ERROR, _exp2->line(),
                     _exp2->col(), vCHILD_TYPE_MCONCAT_EXP );
      return vCHILD_TYPE_MCONCAT_EXP;
    }
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MCONCAT_EXP );
  return vCHILD_TYPE_MCONCAT_EXP;
}

int
VeriMultiConcatExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_mconcat( );
      break;
  }
}

int
VeriMultiConcatExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_exp2->clean_up( );
  _exp2->set_is_trash( is_trash( ) );
  _exp2->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp2)->set_signed( is_signed() );
  mstack.push_back( _exp2 );

  //_exp1->clean_up( );
  _exp1->set_is_trash( is_trash( ) );
  _exp1->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp1)->set_signed( is_signed() );
  mstack.push_back( _exp1 );

  return OK;
}

int
VeriMultiConcatExp::process_mconcat( void )
{
  return OK;
}

int
VeriMultiConcatExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp1 );
  mstack.push_back( _exp2 );
  return OK;
}

int
VeriMultiConcatExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriMultiConcatExp *tmp = new VeriMultiConcatExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  tmp->_exp2 = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_exp1 = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************
     * Range Expression *
     ********************/

void
VeriRangeExp::clean_up( void )
{
  if(_named_index_type)_rtype=vrSINGLE;
  _named_index_type=false;_associative_key_type=nullptr;
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  _vleft  = RANGE_DEFAULT;
  _vright = RANGE_DEFAULT;
  _not_calc = IS_TRUE;
  _packed_width=0;
}

int
VeriRangeExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _left );
  iqueue.push( depth );
  if( _right != NULL )
  {
    mqueue.push( _right );
    iqueue.push( depth );
  }
  if(_packed_next){mqueue.push(_packed_next);iqueue.push(depth);}
  return OK;
}

int
VeriRangeExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );

  IList  range_from( 1, _vleft );
  IList  range_to( 1, _vright );

  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_range_type( _rtype );
  ofile << dot_str_range( range_from, range_to ); 
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _left );
  ofile << dot_str_conn( idx(), _right );

  return OK;
}

int
VeriRangeExp::check_child_validation( VeriNode *child )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, child->line(),
                  child->col(), vCHILD_TYPE_RANGE_EXP );
        return vCHILD_TYPE_RANGE_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                  child->col(), vCHILD_TYPE_RANGE_EXP );
          return vCHILD_TYPE_RANGE_EXP;
        }
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP  :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                     child->col(), vCHILD_TYPE_RANGE_EXP );
            return vCHILD_TYPE_RANGE_EXP;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_RANGE_EXP );
  return vCHILD_TYPE_RANGE_EXP;
}

int
VeriRangeExp::check_child_validation( void )
{
  int re;
  re = check_child_validation( _left  );
  if( re != OK )
    return re;

  if( _right != NULL )
    return check_child_validation( _right );

  if( _right == NULL && _rtype != vrSINGLE && _rtype < vrOPEN )
    return check_child_validation( _right );

  return OK;
}

int
VeriRangeExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return assign_range( );
      break;
  }
}

int
VeriRangeExp::push_children( NodeVec& mstack )
{
  // In an unpacked declaration [ClassType] is an index type, never a
  // value expression. Bind afresh in the current specialization's scope.
  if(_rtype==vrSINGLE&&father()&&father()->detail_type()==veEXP_ARRAY&&father()->is_decl()==IS_TRUE&&
     _left->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(_left)->pri_type()==veVAR) {
    const auto& name=static_cast<VeriPrimaryExp*>(_left)->str();
    auto* candidate=scope()->value_within_module(name);
    if((candidate&&candidate->tok_type()==vtTYPE)||(!candidate&&name=="process")) {
      auto* type=veri_resolve_type(scope(),name);
      auto* aggregate=type->aggregate_type();
      if(type->range_depth()||(aggregate&&aggregate->unpacked_struct())||veri_real(type->net_type())||type->net_type()==vvCHANDLE)
        throw std::runtime_error("associative index type requires a supported singular integral, enum, class or string type: "+name+" at line "+std::to_string(line()));
      if(type->class_binding()) {_associative_key_type=type;_rtype=vrASSOC_CLASS;}
      else if(type->net_type()==vvSTRING)_rtype=vrASSOC_STRING;
      else {_associative_key_type=type;_rtype=type->is_signed()==IS_TRUE?vrASSOC_INT:vrASSOC_UINT;}
      _named_index_type=true;_not_calc=IS_FALSE;return OK;
    }
  }
  mstack.push_back( this );
  if(_packed_next){_packed_next->set_is_trash(is_trash());_packed_next->set_scope(scope());mstack.push_back(_packed_next);}

  if( _right != NULL )
  {
    //_right->clean_up( );
    _right->set_is_trash( is_trash( ) );
    _right->set_scope( scope( ) );
    static_cast<VeriExp *>(_right)->set_signed( is_signed() );
    mstack.push_back( _right );
  }

  //_left->clean_up( );
  _left->set_is_trash( is_trash( ) );
  _left->set_scope( scope( ) );
  static_cast<VeriExp *>(_left)->set_signed( is_signed() );
  mstack.push_back( _left );

  return OK;
}

int
VeriRangeExp::assign_range( void )
{
  VeriExp * left  = static_cast<VeriExp *>(_left);
  VeriExp * right = static_cast<VeriExp *>(_right);

  if(veri_real_width(_left)||veri_real_width(_right))throw std::runtime_error("range or index requires integral operands");
  if( left->calc_value() != NULL )
  {
    _vleft = left->calc_value()->get_first_int();
    _not_calc = IS_FALSE;
  }

  if( right != NULL && right->calc_value() != NULL )
  {
    _vright = right->calc_value()->get_first_int();
    _not_calc = IS_FALSE;
  }
  if(_rtype==vrQUEUE&&_right) {
    auto bound=veri_constant_value(static_cast<VeriExp*>(_right),0);
    if(!veri_elaboration_constant(_right)||!bound||bound->no_xz()!=IS_TRUE||
       bound->get_first_int()<0||bound->get_first_int()>1048575)
      throw std::runtime_error("queue upper bound must be a constant in 0..1048575");
    for(int bit=20;bit<bound->bits();++bit)if(bound->get_certain_bit(bit)!=V0)
      throw std::runtime_error("queue upper bound must be a constant in 0..1048575");
  }
  if(_packed_next) {
    int64_t width=1;
    for(auto* item=this;item;item=item->_packed_next) {
      if(item->rtype()!=vrSEMI||!item->right()||!veri_elaboration_constant(item->left())||!veri_elaboration_constant(item->right()))
        throw std::runtime_error("line "+std::to_string(line())+": packed dimensions require two constant bounds");
      for(auto* bound:{item->left(),item->right()}) {
        auto value=veri_constant_value(static_cast<VeriExp*>(bound),0);
        if(!value||value->no_xz()!=IS_TRUE)
          throw std::runtime_error("line "+std::to_string(line())+": packed dimension bound is unknown");
        // Existing indexing ABI uses signed 32-bit bounds.
        const int sign=value->is_signed()==IS_TRUE?value->get_certain_bit(std::min(31,value->bits()-1)):V0;
        if(value->is_signed()!=IS_TRUE&&value->bits()>31&&value->get_certain_bit(31)!=V0)
          throw std::runtime_error("line "+std::to_string(line())+": packed dimension bound exceeds signed 32-bit range");
        for(int bit=32;bit<value->bits();++bit)if(value->get_certain_bit(bit)!=sign)
          throw std::runtime_error("line "+std::to_string(line())+": packed dimension bound exceeds signed 32-bit range");
      }
      width*=std::abs(int64_t(item->_vleft)-item->_vright)+1;
      if(width>1048576)throw std::runtime_error("line "+std::to_string(line())+": packed dimensions exceed 1048576 bits");
    }
    _packed_width=int(width);_not_calc=IS_FALSE;
  }
  return OK;
}

int
VeriRangeExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _left );
  if( _right != NULL )
    mstack.push_back( _right );
  if(_packed_next)mstack.push_back(_packed_next);
  return OK;
}

int
VeriRangeExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriRangeExp *tmp = new VeriRangeExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  if(_packed_next){tmp->_packed_next=static_cast<VeriRangeExp*>(*(--itl));(*itl)->set_father(tmp);node_list.erase(itl);itl=inl;}

  if( _right != NULL )
  {
    tmp->_right = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_left = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /************************
     * Mintypmax Expression *
     ************************/

void
VeriMintypmaxExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  memset( _re, 0, sizeof(int) * 3 );
  _not_calc = IS_TRUE;
}

int
VeriMintypmaxExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _exp[0] );
  mqueue.push( _exp[1] );
  mqueue.push( _exp[2] );
  iqueue.push( depth );
  iqueue.push( depth );
  iqueue.push( depth );

  if( calc_value( ) != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriMintypmaxExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp[0] );
  ofile << dot_str_conn( idx(), _exp[1] );
  ofile << dot_str_conn( idx(), _exp[2] );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriMintypmaxExp::check_child_validation( VeriNode *child )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, child->line(),
                      child->col(), vCHILD_TYPE_MINTY_EXP );
        return vCHILD_TYPE_MINTY_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                        child->col(), vCHILD_TYPE_MINTY_EXP );
          return vCHILD_TYPE_MINTY_EXP;
        }
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP  :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                          child->col(), vCHILD_TYPE_MINTY_EXP );
            return vCHILD_TYPE_MINTY_EXP;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MINTY_EXP );
  return vCHILD_TYPE_MINTY_EXP;
}

int
VeriMintypmaxExp::check_child_validation( void )
{
  int re;
  for( int i = 0; i < 3; ++i )
  {
    re = check_child_validation( _exp[i] );
    if( re != OK )
      return re;
  }
  return OK;
}

int
VeriMintypmaxExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_mintypmax( );
      break;
  }
}

int
VeriMintypmaxExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_exp[2]->clean_up( );
  _exp[2]->set_is_trash( is_trash( ) );
  _exp[2]->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp[2])->set_signed( is_signed() );
  mstack.push_back( _exp[2] );

  //_exp[1]->clean_up( );
  _exp[1]->set_is_trash( is_trash( ) );
  _exp[1]->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp[1])->set_signed( is_signed() );
  mstack.push_back( _exp[1] );

  //_exp[0]->clean_up( );
  _exp[0]->set_is_trash( is_trash( ) );
  _exp[0]->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp[0])->set_signed( is_signed() );
  mstack.push_back( _exp[0] );

  return OK;
}

int
VeriMintypmaxExp::process_mintypmax( void )
{
  VeriExp * exp = NULL;

  exp = static_cast<VeriExp* >(_exp[0]);

  _not_calc = IS_FALSE;

  if( exp->calc_value( ) != NULL )
    _re[0] = exp->calc_value()->get_first_int( );
  else
    _not_calc = IS_TRUE;

  exp = static_cast<VeriExp* >(_exp[1]);
  if( exp->calc_value( ) != NULL )
    _re[1] = exp->calc_value()->get_first_int( );
  else
    _not_calc = IS_TRUE;

  exp = static_cast<VeriExp* >(_exp[2]);
  if( exp->calc_value( ) != NULL )
    _re[2] = exp->calc_value()->get_first_int( );
  else
    _not_calc = IS_TRUE;

 return OK;
}

int
VeriMintypmaxExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp[0] );
  mstack.push_back( _exp[1] );
  mstack.push_back( _exp[2] );
  return OK;
}

int
VeriMintypmaxExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriMintypmaxExp *tmp = new VeriMintypmaxExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  tmp->_exp[2] = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_exp[1] = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_exp[0] = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /***********************
     * Question Expression *
     ***********************/

void
VeriQuesExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  _choice = 0;
}

int
VeriQuesExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _ques );
  mqueue.push( _choice1 );
  mqueue.push( _choice2 );
  iqueue.push( depth );
  iqueue.push( depth );
  iqueue.push( depth );

  if( calc_value( ) != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriQuesExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _ques );
  ofile << dot_str_conn( idx(), _choice1 );
  ofile << dot_str_conn( idx(), _choice2 );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriQuesExp::check_child_validation( VeriNode *child )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
      case veEXP_DUMMY_PORT :
        veri_err->append_err( ERR_ERROR, child->line(),
                      child->col(), vCHILD_TYPE_QUES_EXP );
        return vCHILD_TYPE_QUES_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                        child->col(), vCHILD_TYPE_QUES_EXP );
          return vCHILD_TYPE_QUES_EXP;
        }
        break;
      }

      case veEXP_MINTY :
      {
        veri_err->append_err( ERR_ERROR, child->line(),
                     child->col(), vCHILD_TYPE_QUES_EXP );
        return vCHILD_TYPE_QUES_EXP;
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP  :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                          child->col(), vCHILD_TYPE_QUES_EXP );
            return vCHILD_TYPE_QUES_EXP;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_QUES_EXP );
  return vCHILD_TYPE_QUES_EXP;
}

int
VeriQuesExp::check_child_validation( void )
{
  int re;
  re = check_child_validation( _ques );
  if( re != OK )
    return re;
  
  re = check_child_validation( _choice1 );
  if( re != OK )
    return re;

  return check_child_validation( _choice2 );
}

int
VeriQuesExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_condition( mstack );
      set_pstatus( vIF_S );
      return re;
      break;

    case vIF_S :
      re = choose_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return get_answer( );
      break;
  }
}

int
VeriQuesExp::push_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_ques->clean_up( );
  _ques->set_is_trash( is_trash( ) );
  _ques->set_scope( scope( ) );
  static_cast<VeriExp *>(_ques)->set_signed( is_signed() );
  mstack.push_back( _ques );

  return OK;
}

int
VeriQuesExp::choose_children( NodeVec& mstack )
{
  // Resolve both runtime branches, even when a cached condition is constant.
  // Lowering chooses which function calls actually execute at runtime.
  _choice=0;
  auto* condition=static_cast<VeriExp*>(_ques);
  if(condition->calc_value()) {
    VeriNum value(0,condition->calc_value());
    if(value.real_width())_choice=value.real_value()!=0?1:2;
    else value.unary_operation(vtUOR);
    if(!value.real_width()){if(value.one_bit_value()==V1)_choice=1;else if(value.one_bit_value()==V0)_choice=2;}
  }
  mstack.push_back(this);
  for(auto* child:{_choice2,_choice1}) {
    child->set_is_trash(is_trash());child->set_scope(scope());
    static_cast<VeriExp*>(child)->set_signed(is_signed());mstack.push_back(child);
  }
  return OK;
}

int
VeriQuesExp::get_answer( void )
{
  const bool string_result=veri_dynamic_string_value(_choice1)||veri_dynamic_string_value(_choice2);
  if(string_result&&(!veri_string_value(_choice1)||!veri_string_value(_choice2)))
    throw std::runtime_error("mixed string and integral conditional branches require an explicit conversion");
  auto* condition=static_cast<VeriExp*>(_ques)->calc_value();
  auto* a=static_cast<VeriExp*>(_choice1)->calc_value();
  auto* b=static_cast<VeriExp*>(_choice2)->calc_value();
  if(!condition||(_choice==1&&!a)||(_choice==2&&!b)||(_choice==0&&(!a||!b)))return OK;
  if(string_result) {
    auto* num=new VeriNum(veri_parser->next_id(),_choice==2?b:a);
    if(_choice==0&&a->string_value()!=b->string_value())num->parse("8'b0",4);
    num->to_string_value();veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());set_calc_value(num);return OK;
  }
  const int real_width=std::max(a?a->real_width():0,b?b->real_width():0);
  if(real_width){auto* chosen=_choice==2?b:a;auto* num=new VeriNum(veri_parser->next_id(),chosen?chosen:b);num->set_real(_choice==0?0:chosen->real_value(),real_width);veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());set_calc_value(num);return OK;}
  const int width=a&&b?std::max(a->bits(),b->bits()):(_choice==1?a:b)->bits();
  const bool sign=a&&b?a->is_signed()==IS_TRUE&&b->is_signed()==IS_TRUE:(_choice==1?a:b)->is_signed()==IS_TRUE;
  VeriNum left(0,a?a:b),right(0,b?b:a);
  if(!sign){left.set_unsigned();right.set_unsigned();}
  left.truncate_assign(width);right.truncate_assign(width);
  auto* num=new VeriNum(veri_parser->next_id(),_choice==2?&right:&left);
  if(_choice==0) {
    String text=std::to_string(width)+(sign?"'sb":"'b");
    for(int bit=width-1;bit>=0;--bit) {
      const int x=left.get_certain_bit(bit),y=right.get_certain_bit(bit);
      text+=x!=y?'x':x==VX?'x':x==VZ?'x':x?'1':'0';
    }
    const int result=num->parse(text.c_str(),text.size());
    if(result!=OK){delete num;return result;}
  }
  veri_parser->insert_node(num);num->set_father(this);num->set_scope(scope());set_calc_value(num);
  return OK;
}

int
VeriQuesExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _ques );
  mstack.push_back( _choice1 );
  mstack.push_back( _choice2 );
  return OK;
}

int
VeriQuesExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriQuesExp *tmp = new VeriQuesExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  tmp->_choice2 = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_choice1 = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_ques = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /***********************
     * Multiple Expression *
     ***********************/

void
VeriMultiExp::clean_up( void )
{
  _object_type=nullptr;_object_constructor=nullptr;
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriMultiExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  NodeList::iterator it = _exp.begin();
  for( ; it != _exp.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriMultiExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_multi_exp_type( _multi_type );
  ofile << dot_str_tail( tok_type() );

  // connection
  NodeList::iterator it = _exp.begin();
  for( ; it != _exp.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriMultiExp::check_child_validation( VeriNode *child )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_DUMMY_PORT :
      case veEXP_NAMED_PARAM :
        _multi_type = vemPORT_INST_EXP;
        break;

      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
        veri_err->append_err( ERR_ERROR, child->line(),
                     child->col(), vCHILD_TYPE_MULTI_EXP );
        return vCHILD_TYPE_MULTI_EXP;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(),
                     child->col(), vCHILD_TYPE_MULTI_EXP );
          return vCHILD_TYPE_MULTI_EXP;
        }
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        switch( mexp->multi_type() )
        {
          case vemOBJECT_NEW :
          case vemNULL :
          case vemCONCAT_EXP :
          case vemASSIGN_PATTERN :
            return OK;

          case vemCOMMA_EXP :
            return check_child_validation( mexp->exp().back() );
            break;

          case vemEVENT_EXP :
          case vemPORT_EXP  :
          case vemPORT_INST_EXP :
          default :
            veri_err->append_err( ERR_ERROR, child->line(),
                         child->col(), vCHILD_TYPE_MULTI_EXP );
            return vCHILD_TYPE_MULTI_EXP;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MULTI_EXP );
  return vCHILD_TYPE_MULTI_EXP;
}

int
VeriMultiExp::check_child_validation( void )
{
  if(_multi_type==vemCONCAT_EXP&&_exp.empty())return OK;
  if(_multi_type==vemDYNAMIC_NEW||_multi_type==vemOBJECT_NEW||_multi_type==vemNULL||_multi_type==vemINSIDE_SET||_multi_type==vemINSIDE_RANGE||
     (_multi_type>=vemASSIGN_PATTERN&&_multi_type<=vemPATTERN_REPEAT)) {
    for(auto* item:_exp)if(!item||item->tok_type()!=vtEXP)return vCHILD_TYPE_MULTI_EXP;
    return OK;
  }
  if( _exp.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MULTI_EXP );
    return vCHILD_TYPE_MULTI_EXP;
  }

  NodeList::iterator it = _exp.begin();
  int re;

  switch( _multi_type )
  {
    case vemCOMMA_EXP :
      for( ; it != _exp.end(); ++it )
      {
        if( *it == NULL || (*it)->tok_type() != vtEXP )
        {
          veri_err->append_err( ERR_ERROR, (*it)->line(),
                      (*it)->col(), vCHILD_TYPE_MULTI_EXP );
          return vCHILD_TYPE_MULTI_EXP;
        }
        else
        {
          re = check_child_validation( *it );
          if( re != OK )
            return re;
        }
      }
      break;

    case vemEVENT_EXP :
      for( ; it != _exp.end(); ++it )
      {
        if( *it == NULL || (*it)->tok_type() != vtEXP )
          return vCHILD_TYPE_MULTI_EXP;
      }
      return OK;
      break;

    case vemCONCAT_EXP :
      for( ; it != _exp.end(); ++it )
      {
        if( *it == NULL || (*it)->tok_type() != vtEXP )
        {
          veri_err->append_err( ERR_ERROR, (*it)->line(),
                        (*it)->col(), vCHILD_TYPE_MULTI_EXP );
          return vCHILD_TYPE_MULTI_EXP;
        }
        else
        {
          switch( (*it)->detail_type() )
          {
            case veEXP_MULTI:
            {
              VeriMultiExp *mexp = static_cast<VeriMultiExp *>(*it);
              if( mexp->multi_type() != vemCONCAT_EXP )
              {
                veri_err->append_err( ERR_ERROR, (*it)->line(),
                           (*it)->col(), vCHILD_TYPE_MULTI_EXP );
                return vCHILD_TYPE_MULTI_EXP;
              }
              break;
            }

            case veEXP_CALLER : case veEXP_MEMBER : case veEXP_PRI    :  case veEXP_ARRAY  : case veEXP_UNA :
            case veEXP_SIGN   :  case veEXP_BIN    : case veEXP_MINTY : case veEXP_MCONCAT :
            case veEXP_UNSIGN :  case veEXP_QUES   :
              break;

            default:
              veri_err->append_err( ERR_ERROR, (*it)->line(),
                           (*it)->col(), vCHILD_TYPE_MULTI_EXP );
              return vCHILD_TYPE_MULTI_EXP;
          }
        }
      }
      break;

    case vemPORT_EXP :
      for( ; it != _exp.end(); ++it )
      {
        if( *it == NULL || (*it)->detail_type() != veEXP_NAMED_PARAM )
        {
          veri_err->append_err( ERR_ERROR, (*it)->line(),
                           (*it)->col(), vCHILD_TYPE_MULTI_EXP );
          return vCHILD_TYPE_MULTI_EXP;
        }
      }
      break;

    case vemPORT_INST_EXP :
      for(;it!=_exp.end();++it) {
        re=check_child_validation(*it);
        if(re!=OK)return re;
      }
      return OK;

    default:
      veri_err->append_err( ERR_ERROR, (*it)->line(),
                        (*it)->col(), vCHILD_TYPE_MULTI_EXP );
      return vCHILD_TYPE_MULTI_EXP;
      break;
  }
  return OK;
}

int
VeriMultiExp::check_last_child_validation( void )
{
  if(_multi_type==vemCONCAT_EXP&&_exp.empty())return OK;
  if(_multi_type==vemDYNAMIC_NEW||_multi_type==vemINSIDE_SET||_multi_type==vemINSIDE_RANGE||
     (_multi_type>=vemASSIGN_PATTERN&&_multi_type<=vemPATTERN_REPEAT)) {
    for(auto* item:_exp)if(!item||item->tok_type()!=vtEXP)return vCHILD_TYPE_MULTI_EXP;
    return OK;
  }
  if( _exp.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MULTI_EXP );
    return vCHILD_TYPE_MULTI_EXP;
  }

  VeriNode *last = _exp.back();
  if( last == NULL || last->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_MULTI_EXP );
    return vCHILD_TYPE_MULTI_EXP;
  }

  int re;
  switch( _multi_type )
  {
    case vemCOMMA_EXP :
      re = check_child_validation( last );
      if( re != OK )
        return re;
    break;

    case vemEVENT_EXP :
      break;

    case vemCONCAT_EXP :
      switch( last->detail_type() )
      {
        case veEXP_MULTI:
        {
          VeriMultiExp *mexp = static_cast<VeriMultiExp *>(last);
          if( mexp->multi_type() != vemCONCAT_EXP )
          {
            veri_err->append_err( ERR_ERROR, last->line(),
                            last->col(), vCHILD_TYPE_MULTI_EXP );
            return vCHILD_TYPE_MULTI_EXP;
          }
          break;
        }

        case veEXP_PRI  : case veEXP_UNA   : case veEXP_BIN  :
        case veEXP_MEMBER : case veEXP_QUES : case veEXP_ARRAY : case veEXP_SIGN :
        case veEXP_CALLER : case veEXP_UNSIGN : case veEXP_MINTY : case veEXP_MCONCAT :
          break;

        default:
          veri_err->append_err( ERR_ERROR, line(),
                                col(), vCHILD_TYPE_MULTI_EXP );
          return vCHILD_TYPE_MULTI_EXP;
      }
      break;

    case vemPORT_EXP :
      if( last->detail_type() != veEXP_NAMED_PARAM )
      {
        veri_err->append_err( ERR_ERROR, last->line(),
                            last->col(), vCHILD_TYPE_MULTI_EXP );
        return vCHILD_TYPE_MULTI_EXP;
      }
      break;

    case vemPORT_INST_EXP :
      return check_child_validation(last);

    default:
      veri_err->append_err( ERR_ERROR, line(),
                            col(), vCHILD_TYPE_MULTI_EXP );
      return vCHILD_TYPE_MULTI_EXP;
      break;
  }
  return OK;
}

int
VeriMultiExp::check_pure_event_multi( void )
{
  if( _exp.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_MULTI_EXP );
    return vCHILD_TYPE_MULTI_EXP;
  }

  NodeList::iterator it = _exp.begin();
  for( ; it != _exp.end(); ++it )
  {
    if( (*it) == NULL || (*it)->tok_type() != vtEXP )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(),
                          (*it)->col(), vCHILD_TYPE_MULTI_EXP );
      return vCHILD_TYPE_MULTI_EXP;
    }
  }
  return OK;
}

bool VeriMemberExp::process_builtin() const {return _class_owner&&_class_owner->process_type()&&_called;}

bool VeriMemberExp::ipc_builtin() const {return _class_owner&&_class_owner->ipc_kind();}
bool VeriMemberExp::coverage_builtin() const {return _class_owner&&_class_owner->coverage_type();}
bool VeriMemberExp::ipc_value_builtin() const {
  return ipc_builtin()&&(_member=="num"||_member=="try_get"||_member=="try_peek"||_member=="try_put");
}

int
VeriMultiExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  if(_multi_type==vemOBJECT_NEW&&pstatus()!=vSTART_S&&!_object_type) {
    VeriNode* target=nullptr;
    auto* parent=father();
    if(parent&&parent->detail_type()==vsSTMT_BLOCKING)target=static_cast<VeriBlockStmt*>(parent)->lval();
    else if(parent&&parent->detail_type()==vsSTMT_FUNC_BLOCKING)target=static_cast<VeriFuncBlockAssignStmt*>(parent)->lval();
    else if(parent&&parent->detail_type()==vsSTMT_NONBLOCKING)target=static_cast<VeriNonBlockStmt*>(parent)->lval();
    if(target)_object_type=veri_class_type(target);
    if(parent&&parent->detail_type()==veEXP_ASSIGN) {
      target=static_cast<VeriAssignExp*>(parent)->lval();_object_type=veri_class_type(target);
      if(!_object_type&&parent->father()&&parent->father()->detail_type()==vsDECL_VAR) {
        auto* type=static_cast<VeriVarDecl*>(parent->father())->resolved_type();_object_type=type?type->class_type():nullptr;
      }
    }
    if(!_object_type)throw std::runtime_error("line "+std::to_string(line())+": new requires a class-typed assignment context");
    _object_type->ensure_class_elaborated();
    if(_object_type->process_type())throw std::runtime_error("process cannot be constructed with new; use process::self()");
    auto* symbol=_object_type->scope()->value_same_level("new");
    if(symbol) {
      veri_check_class_access(symbol,scope());
      if(symbol->tok_type()!=vtFUNC)throw std::runtime_error("class constructor must be a function");
      return unfold_subroutine(this,static_cast<VeriFunc*>(symbol)->func(),_object_type->scope(),mstack,_object_constructor);
    }
    if(_object_type->ipc_kind()){if(_exp.size()>1)throw std::runtime_error("IPC constructor accepts at most one argument");}
    else if(!_exp.empty())throw std::runtime_error("class without a constructor accepts no arguments");
  }
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return get_answer( );
      break;
  }
}

int
VeriMultiExp::push_children( NodeVec& mstack )
{
  if( _multi_type == vemCOMMA_EXP || _multi_type == vemOBJECT_NEW )
    mstack.push_back(this);
  NodeList::reverse_iterator it = _exp.rbegin();
  for( ; it != _exp.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_trash( is_trash( ) );
    (*it)->set_scope( scope( ) );
    static_cast<VeriExp *>(*it)->set_signed( is_signed() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriMultiExp::get_answer( void )
{
  if(_multi_type==vemOBJECT_NEW||_multi_type==vemNULL||_multi_type==vemDYNAMIC_NEW)return OK;
  if( _exp.empty() ) return OK;
  VeriExp *exp = static_cast<VeriExp *>(_exp.back());
  if( exp->calc_value( ) != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );
    set_calc_value( num );
  }
  return OK;
}

int
VeriMultiExp::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _exp.begin();
  for( ; it != _exp.end(); ++it )
    mstack.push_back( *it );
  return OK;
}

int
VeriMultiExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriMultiExp *tmp = new VeriMultiExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  NodeList::iterator it = _exp.begin();
  for( ; it != _exp.end(); ++it )
  {
    tmp->_exp.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /********************
     * Delay Expression *
     ********************/

void
VeriDelayExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );

  memset( _delay, 0, sizeof(int) * 9 );
  _not_calc = IS_TRUE;
}

int
VeriDelayExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _delay1 != NULL )
  {
    mqueue.push( _delay1 );
    iqueue.push( depth );
  }
  if( _delay2 != NULL )
  {
    mqueue.push( _delay2 );
    iqueue.push( depth );
  }
  if( _delay3 != NULL )
  {
    mqueue.push( _delay3 );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriDelayExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _delay1 );
  ofile << dot_str_conn( idx(), _delay2 );
  ofile << dot_str_conn( idx(), _delay3 );

  return OK;
}

int
VeriDelayExp::check_child_validation( VeriNode *child )
{
  if( child == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_DELAY_EXP );
    return vCHILD_TYPE_DELAY_EXP;
  }

  switch( child->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ARRAY :
    case veEXP_MEMBER :
    case veEXP_CALLER :
    case veEXP_SIGN :
    case veEXP_UNSIGN :
    case veEXP_UNA :
    case veEXP_BIN :
    case veEXP_QUES :
    case veEXP_MULTI :
    case veEXP_MCONCAT :
      break;

    default:
      veri_err->append_err( ERR_ERROR, child->line(),
                          child->col(), vCHILD_TYPE_DELAY_EXP );
      return vCHILD_TYPE_DELAY_EXP;
      break;
  }
  return OK;
}

int
VeriDelayExp::check_child_validation( void )
{
  if( _delay1 == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_DELAY_EXP );
    return vCHILD_TYPE_DELAY_EXP;
  }

  int re;

  re = check_child_validation( _delay1 );
  if( re != OK )
    return re;

  if( _delay2 != NULL )
  {
    re = check_child_validation( _delay2 );
    if( re != OK )
      return re;
  }

  if( _delay3 != NULL )
    re = check_child_validation( _delay3 );

  return re;
}

int
VeriDelayExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return get_delay_val( );
      break;
  }
}

int
VeriDelayExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  if( _delay3 != NULL )
  {
    //_delay3->clean_up( );
    _delay3->set_is_trash( is_trash( ) );
    _delay3->set_scope( scope( ) );
    static_cast<VeriExp *>(_delay3)->set_signed( is_signed() );
    mstack.push_back( _delay3 );
  }

  if( _delay2 != NULL )
  {
    //_delay2->clean_up( );
    _delay2->set_is_trash( is_trash( ) );
    _delay2->set_scope( scope( ) );
    static_cast<VeriExp *>(_delay2)->set_signed( is_signed() );
    mstack.push_back( _delay2 );
  }

  if( _delay1 != NULL )
  {
    //_delay1->clean_up( );
    _delay1->set_is_trash( is_trash( ) );
    _delay1->set_scope( scope( ) );
    static_cast<VeriExp *>(_delay1)->set_signed( is_signed() );
    mstack.push_back( _delay1 );
  }

  return OK;
}

int
VeriDelayExp::delay_num( void ) const
{
  int num = 0;
  if( _delay1 != NULL ) ++num; else return num;
  if( _delay2 != NULL ) ++num; else return num;
  if( _delay3 != NULL ) ++num; else return num;

  return num;
}

/*
 * assuming delay_exp is not null
 */
int
VeriDelayExp::get_one_val( VeriExp *delay_exp, int idx )
{
  if( delay_exp->detail_type( ) == veEXP_MINTY )
  {
    VeriMintypmaxExp *pmax
      = static_cast<VeriMintypmaxExp *>(delay_exp);

    if( pmax->not_calc( ) == IS_TRUE )
    {
      _not_calc = IS_TRUE;
      veri_err->append_err( ERR_ERROR, delay_exp, vSEC_DELAY_NOT_CALC );
      return vSEC_DELAY_NOT_CALC;
    }
    else
    {
      _delay[(idx-1)*3+0] = pmax->re1();
      _delay[(idx-1)*3+1] = pmax->re2();
      _delay[(idx-1)*3+2] = pmax->re3();
    }
  }
  else
  {
    if( delay_exp->calc_value( ) == NULL )
    {
      // Keep the expression for compiled procedural evaluation. The legacy
      // integer cache cannot represent variable delays or real literals;
      // constant-only contexts are checked by their consuming frontend.
      _not_calc = IS_TRUE;
      return OK;
    }
    else
      _delay[(idx-1)*3+0] = delay_exp->calc_value()->get_first_int();
  }

  return OK;
}

int
VeriDelayExp::get_delay_val( void )
{
  VeriExp * delay1 = static_cast<VeriExp *>(_delay1);
  VeriExp * delay2 = static_cast<VeriExp *>(_delay2);
  VeriExp * delay3 = static_cast<VeriExp *>(_delay3);

  _not_calc = IS_FALSE;
  if( delay1 != NULL ) get_one_val( delay1, 1 );
  if( delay2 != NULL ) get_one_val( delay2, 2 );
  if( delay3 != NULL ) get_one_val( delay3, 3 );

  return OK;
}

int
VeriDelayExp::push_for_replacement( NodeVec& mstack )
{
  if( _delay1 != NULL ) mstack.push_back( _delay1 );
  if( _delay2 != NULL ) mstack.push_back( _delay2 );
  if( _delay3 != NULL ) mstack.push_back( _delay3 );
  return OK;
}

int
VeriDelayExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDelayExp *tmp = new VeriDelayExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;

  if( _delay3 != NULL )
  {
    tmp->_delay3 = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _delay2 != NULL )
  {
    tmp->_delay2 = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_delay1 = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************
     * Drive Expression *
     ********************/

void
VeriDriveExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriDriveExp::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriDriveExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_drive_from( _drive_from );
  ofile << dot_str_drive_to( _drive_to );
  ofile << dot_str_tail( tok_type() );

  // connection
  
  return OK;
}

int
VeriDriveExp::check_child_validation( void )
{
  if( _drive_from == vpHIGHZ1 && _drive_to == vpHIGHZ0 )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_DRIVE_EXP );
    return vCHILD_TYPE_DRIVE_EXP;
  }

  if( _drive_from == vpHIGHZ0 && _drive_to == vpHIGHZ1 )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_DRIVE_EXP );
    return vCHILD_TYPE_DRIVE_EXP;
  }
  return OK;
}

int
VeriDriveExp::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriDriveExp::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriDriveExp::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDriveExp *tmp = new VeriDriveExp( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

    /*********************
     * Signed Expression *
     *********************/

void
VeriSignExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriSignExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  mqueue.push( _exp );
  iqueue.push( iqueue.front() + 1 );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( iqueue.front() + 1 );
  }
  return OK;
}

int
VeriSignExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriSignExp::check_child_validation( void )
{
  if( _exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_SIGN_FUNC_EXP );
    return vCHILD_TYPE_SIGN_FUNC_EXP;
  }
   
  if( _exp->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, _exp->line(),
                          _exp->col(), vCHILD_TYPE_SIGN_FUNC_EXP );
    return vCHILD_TYPE_SIGN_FUNC_EXP;
  }
  return OK;
}

int
VeriSignExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_sign( );
      break;
  }
}

int
VeriSignExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_exp->clean_up( );
  _exp->set_is_trash( is_trash( ) );
  _exp->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp)->set_signed( is_signed() );
  mstack.push_back( _exp );
  return OK;
}

int
VeriSignExp::process_sign( void )
{
  VeriExp *exp = static_cast<VeriExp *>(_exp);
  if( exp->calc_value() != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_signed( );
    num->set_father( this );
    num->set_scope( scope( ) );
    set_calc_value( num );
  }
  return OK;
}

int
VeriSignExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp );
  return OK;
}

int
VeriSignExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriSignExp *tmp = new VeriSignExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  tmp->_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /***********************
     * Unsigned Expression *
     ***********************/

void
VeriUnsignExp::clean_up( void )
{
  set_pstatus( vSTART_S );
  if( calc_value() != NULL )
    veri_parser->toss_node( calc_value()->idx() );
  set_calc_value( NULL );
}

int
VeriUnsignExp::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  mqueue.push( _exp );
  iqueue.push( iqueue.front() + 1 );

  if( calc_value() != NULL )
  {
    mqueue.push( calc_value() );
    iqueue.push( iqueue.front() + 1 );
  }
  return OK;
}

int
VeriUnsignExp::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _exp );

  if( calc_value() != NULL )
    ofile << dot_str_conn( idx(), calc_value() );

  return OK;
}

int
VeriUnsignExp::check_child_validation( void )
{
  if( _exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_UNSIGN_FUNC_EXP );
    return vCHILD_TYPE_UNSIGN_FUNC_EXP;
  }
   
  if( _exp->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, _exp->line(),
                          _exp->col(), vCHILD_TYPE_UNSIGN_FUNC_EXP );
    return vCHILD_TYPE_UNSIGN_FUNC_EXP;
  }
  return OK;
}

int
VeriUnsignExp::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return process_unsign( );
      break;
  }
}

int
VeriUnsignExp::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_exp->clean_up( );
  _exp->set_is_trash( is_trash( ) );
  _exp->set_scope( scope( ) );
  static_cast<VeriExp *>(_exp)->set_signed( is_signed() );
  mstack.push_back( _exp );
  return OK;
}

int
VeriUnsignExp::process_unsign( void )
{
  VeriExp *exp = static_cast<VeriExp *>(_exp);
  if( exp->calc_value() != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_unsigned( );
    num->set_father( this );
    num->set_scope( scope( ) );
    set_calc_value( num );
  }
  return OK;
}

int
VeriUnsignExp::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _exp );
  return OK;
}

int
VeriUnsignExp::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriUnsignExp *tmp = new VeriUnsignExp( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  tmp->_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

};
