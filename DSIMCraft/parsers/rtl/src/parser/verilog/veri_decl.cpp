/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_decl.cpp
 * Summary  : verilog syntax analyzer :: declaration
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */

#include <assert.h>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <cstdint>

#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_symbol_table.hpp"

#include "veri_num.hpp"
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_tfmg.hpp"

#include "veri_module.hpp"

#include "veri_parser.hpp"

#include <cmath>
#include <iterator>

namespace rtl
{
void VeriVarDecl::infer_foreach_index(bool text,bool unsigned_key,VeriVar* key) {
  _net_type=key?key->net_type():text?vvSTRING:vvINT2;
  _is_signed=key?key->is_signed():text||unsigned_key?IS_FALSE:IS_TRUE;
}


namespace {
using String=std::string;
using ParameterNumber=std::unique_ptr<VeriNum>;
// Register signatures before local declarations, whose types and initializers
// can require the completed enclosing class (including adopted extern bodies).
// Call-site clones still bind all declarations immediately in their activation.
void push_subroutine_items(VeriNode* items,VeriSymbolTable* context,
                          VeriNode::NodeVec& stack,bool activation) {
  items->set_is_decl(IS_TRUE);items->set_is_trash(IS_TRUE);items->set_scope(context);
  if(activation){stack.push_back(items);return;}
  auto& declarations=items->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST?
      static_cast<VeriFuncItemDeclList*>(items)->func_item():
      static_cast<VeriTaskItemDeclList*>(items)->task_item();
  // Non-ANSI signatures retain the prefix through the last formal. Preserve
  // lexical order when queuing the remaining local types and variables.
  auto locals=declarations.begin();
  for(auto it=declarations.begin();it!=declarations.end();++it)
    if((*it)->detail_type()==vsDECL_TF_DECL)locals=std::next(it);
  for(auto* declaration:declarations) {
    declaration->set_is_decl(IS_TRUE);declaration->set_is_trash(IS_TRUE);
    declaration->set_scope(context);
  }
  for(auto it=locals;it!=declarations.end();++it)veri_parser->defer_semantic(*it);
  for(auto it=locals;it!=declarations.begin();)stack.push_back(*--it);
}
VeriVar* signature_type(VeriNode* declaration,const std::string& name,VeriSymbolTable* context=nullptr) {
  if(name.empty())return nullptr;
  auto* node=veri_resolve_type(context?context:declaration->scope(),name);
  if(!node||node->tok_type()!=vtTYPE)
    throw std::runtime_error("line "+std::to_string(declaration->line())+": unknown integral type "+name);
  return static_cast<VeriVar*>(node);
}
// Symbols carry all unpacked dimensions in declaration order. The type
// remains canonical for element identity; its ranges are copied, never owned
// through pointers into another specialization or a previous parser run.
template<class Symbol> void validate_container_dimensions(Symbol* symbol,unsigned rank=0) {
  if(!rank)rank=symbol->range_depth();
  bool dynamic=false,associative_prefix=true,supported=true;
  for(int axis=0;unsigned(axis)<rank;++axis) {
    const int kind=symbol->container_kind(axis);dynamic|=kind>=vrOPEN;
    const bool associative=kind==vrASSOC_INT||kind==vrASSOC_UINT||kind==vrASSOC_STRING||kind==vrASSOC_CLASS;
    supported&=associative_prefix&&(associative||(kind==vrQUEUE&&unsigned(axis)+1==rank));
    associative_prefix&=associative;
  }
  if(rank>1&&dynamic&&!supported)
    throw std::runtime_error("line "+std::to_string(symbol->line())+": mixed runtime container dimensions are not supported: "+symbol->name());
}
template<class Symbol> void append_type_ranges(Symbol* symbol,VeriVar* type) {
  if(!type)return;
  const unsigned offset=symbol->range_depth();
  for(int depth=1;depth<=type->range_depth();++depth) {
    int first,last,count;type->get_range(depth,first,last,count);symbol->add_range(first,last);
    symbol->set_dimension_container(offset+depth-1,type->container_kind(depth-1),type->associative_key_type(depth-1));
    symbol->set_dimension_bound(offset+depth-1,type->container_bound(depth-1));
  }
  if(type->dynamic_array()&&!offset)symbol->set_container(type->container_kind(),type->container_bound());
  validate_container_dimensions(symbol);
}
template<class Symbol,class Ranges> void bind_container_dimensions(Symbol* symbol,const Ranges& ranges) {
  unsigned axis=0;
  for(auto* item:ranges) {
    auto* range=static_cast<VeriRangeExp*>(item);const int kind=range->rtype();
    const bool open_formal=symbol->tok_type()==vtTFVAR&&kind==vrOPEN;
    symbol->set_dimension_container(axis,open_formal?vrSINGLE:kind,range->associative_key_type());
    symbol->set_dimension_bound(axis++,kind==vrQUEUE&&range->right()?range->range_to():-1);
  }
  validate_container_dimensions(symbol,ranges.size());
}
std::pair<int,bool> parameter_shape(VeriExp* expression) {
  auto* cached=expression->calc_value();
  if(!cached)return {0,false};
  if(expression->detail_type()==veEXP_QUES) {
    auto* q=static_cast<VeriQuesExp*>(expression);
    auto a=parameter_shape(static_cast<VeriExp*>(q->choice1())),b=parameter_shape(static_cast<VeriExp*>(q->choice2()));
    return {std::max(a.first,b.first),a.second&&b.second};
  }
  if(expression->detail_type()==veEXP_BIN) {
    auto* b=static_cast<VeriBinaryExp*>(expression);const int op=b->op();
    if(veri_streaming(expression))return {cached->bits(),false};
    if(veri_is_cast(op))return {cached->bits(),cached->is_signed()==IS_TRUE};
    if((op>=vtBLT&&op<=vtBCIEQ)||op==vtBWLEQ||op==vtBWLNEQ||op==vtBINSIDE||op==vtBDAND||op==vtBDOR)return {1,false};
    auto a=parameter_shape(static_cast<VeriExp*>(b->lval())),right=parameter_shape(static_cast<VeriExp*>(b->rval()));
    if((op>=vtBLRS&&op<=vtBALS)||op==vtBPOW)return a;
    return {std::max(a.first,right.first),a.second&&right.second};
  }
  if(expression->detail_type()==veEXP_UNA) {
    auto* u=static_cast<VeriUnaryExp*>(expression);const int op=u->op();
    if(veri_is_system_unary(op))return {cached->bits(),cached->is_signed()==IS_TRUE};
    if(op!=vtUADD&&op!=vtUSUB&&op!=vtUNEG)return {1,false};
    return parameter_shape(static_cast<VeriExp*>(u->exp_child()));
  }
  return {cached->bits(),cached->is_signed()==IS_TRUE};
}
} // namespace
std::unique_ptr<VeriNum> veri_inside_constant(VeriBinaryExp* expression) {
  auto* list=static_cast<VeriMultiExp*>(expression->rval());
  std::vector<VeriExp*> operands{static_cast<VeriExp*>(expression->lval())};
  for(auto* item:list->exp()) {
    if(item->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(item)->multi_type()==vemINSIDE_RANGE)
      for(auto* bound:static_cast<VeriMultiExp*>(item)->exp())operands.push_back(static_cast<VeriExp*>(bound));
    else operands.push_back(static_cast<VeriExp*>(item));
  }
  int width=1;bool sign=true;
  for(auto* operand:operands){if(!operand->calc_value())return {};auto shape=parameter_shape(operand);width=std::max(width,shape.first);sign=sign&&shape.second;}
  auto left=veri_constant_value(operands.front(),width,int(sign));if(!left)return {};
  ParameterNumber result(new VeriNum(0,expression->line(),expression->col(),expression->birth_mod()));
  result->parse("1'b0",4);
  for(auto* item:list->exp()) {
    ParameterNumber match;
    if(item->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(item)->multi_type()==vemINSIDE_RANGE) {
      auto& bounds=static_cast<VeriMultiExp*>(item)->exp();
      auto low=veri_constant_value(static_cast<VeriExp*>(bounds.front()),width,int(sign));
      auto high=veri_constant_value(static_cast<VeriExp*>(bounds.back()),width,int(sign));if(!low||!high)return {};
      match.reset(new VeriNum(0,left.get()));ParameterNumber upper(new VeriNum(0,left.get()));
      if(match->binary_operation(vtBGE,low.get())!=OK||upper->binary_operation(vtBLE,high.get())!=OK||match->binary_operation(vtBDAND,upper.get())!=OK)return {};
    } else {
      auto right=veri_constant_value(static_cast<VeriExp*>(item),width,int(sign));if(!right)return {};
      match.reset(new VeriNum(0,left.get()));if(match->binary_operation(vtBWLEQ,right.get())!=OK)return {};
    }
    if(result->binary_operation(vtBDOR,match.get())!=OK)return {};
  }
  return result;
}
std::unique_ptr<VeriNum> veri_constant_value(VeriExp* expression,int context,int sign_context) {
  if(veri_streaming(expression)) {
    auto* stream=static_cast<VeriBinaryExp*>(expression);const int chunk=veri_stream_slice(expression);
    if(!chunk)return {};
    auto input=veri_constant_value(static_cast<VeriExp*>(stream->rval()),0);if(!input)return {};
    const int width=input->bits();if(context&&context<width)throw std::runtime_error("stream packing destination is smaller than source");
    std::string digits(width,'0');
    for(int bit=0;bit<width;++bit) {
      const int start=(bit/chunk)*chunk,span=std::min(chunk,width-start);
      const int destination=stream->op()==vtSTREAM_LEFT?width-start-span+bit-start:bit;
      int value=input->get_certain_bit(bit);digits[width-1-destination]=value==VX?'x':value==VZ?'z':value==V1?'1':'0';
    }
    if(context>width)digits.append(context-width,'0');
    ParameterNumber value(new VeriNum(0,expression->line(),expression->col(),expression->birth_mod()));
    const auto text=std::to_string(digits.size())+"'b"+digits;
    if(value->parse(text.c_str(),text.size())!=OK)return {};value->set_unsigned();return value;
  }
  if(expression->detail_type()==veEXP_BIN&&static_cast<VeriBinaryExp*>(expression)->op()==vtBINSIDE) {
    auto value=veri_inside_constant(static_cast<VeriBinaryExp*>(expression));if(value)value->truncate_assign(std::max(1,context));return value;
  }
  if(expression->detail_type()==veEXP_MULTI||expression->detail_type()==veEXP_MCONCAT) {
    std::string digits;
    const bool string_concat=veri_dynamic_string_value(expression);
    auto append=[&](VeriNode* item)->bool {
      if(string_concat&&!veri_string_value(item))
        throw std::runtime_error("string concatenation requires string operands or an explicit cast");
      auto value=veri_constant_value(static_cast<VeriExp*>(item),0);if(!value)return false;
      if(digits.size()+size_t(value->bits())>1048576)return false;
      for(int bit=value->bits()-1;bit>=0;--bit){int v=value->get_certain_bit(bit);digits+=v==VX?'x':v==VZ?'z':v==V1?'1':'0';}
      return true;
    };
    if(expression->detail_type()==veEXP_MULTI) {
      auto* m=static_cast<VeriMultiExp*>(expression);if(m->multi_type()!=vemCONCAT_EXP)return {};
      for(auto* item:m->exp())if(!append(item))return {};
    } else {
      auto* m=static_cast<VeriMultiConcatExp*>(expression);
      auto count=veri_constant_value(static_cast<VeriExp*>(m->exp1()),0);
      if(!count||count->no_xz()!=IS_TRUE)return {};
      for(int bit=21;bit<count->bits();++bit)if(count->get_certain_bit(bit)!=V0)return {};
      int n=count->get_first_int();if(n<1||n>1048576||!append(m->exp2())||digits.empty()||size_t(n)>1048576/digits.size())return {};
      const auto item=digits;for(int i=1;i<n;++i)digits+=item;
    }
    if(digits.empty())return {};
    ParameterNumber value(new VeriNum(0,expression->line(),expression->col(),expression->birth_mod()));
    const auto text=std::to_string(digits.size())+"'b"+digits;
    if(value->parse(text.c_str(),text.size())!=OK)return {};
    value->truncate_assign(std::max(context,int(digits.size())));
    if(string_concat)value->to_string_value();return value;
  }
  auto* cached=expression->calc_value();
  if(!cached)return {};
  if(cached->real_width()||cached->string_type())return ParameterNumber(new VeriNum(0,cached));
  const auto shape=parameter_shape(expression);
  const int width=std::max(context,shape.first);
  if(width<1||width>1048576)return {};
  const bool sign=shape.second&&sign_context!=0;
  auto resize=[&](ParameterNumber value,int size,bool is_signed) {
    if(value){if(is_signed)value->set_signed();else value->set_unsigned();value->truncate_assign(size);}
    return value;
  };
  if(expression->detail_type()==veEXP_PRI) {
    auto* primary=static_cast<VeriPrimaryExp*>(expression);
    const auto& text=primary->str();
    if(primary->pri_type()==veNUM&&text.size()==2&&text[0]=='\'') {
      String fill=std::to_string(width)+"'b"+String(width,text[1]);
      auto value=ParameterNumber(new VeriNum(0,cached));
      if(value->parse(fill.c_str(),fill.size())!=OK)return {};
      return value;
    }
  }
  if(expression->detail_type()==veEXP_UNA) {
    auto* unary=static_cast<VeriUnaryExp*>(expression);const int op=unary->op();
    if(veri_is_system_unary(op))return resize(ParameterNumber(new VeriNum(0,cached)),width,sign);
    const bool reduction=op!=vtUADD&&op!=vtUSUB&&op!=vtUNEG;
    auto value=veri_constant_value(static_cast<VeriExp*>(unary->exp_child()),reduction?0:width,reduction?-1:int(sign));
    if(!value||value->unary_operation(op)!=OK)return {};
    return resize(std::move(value),width,sign);
  }
  if(expression->detail_type()==veEXP_BIN) {
    auto* binary=static_cast<VeriBinaryExp*>(expression);const int op=binary->op();
    if(veri_is_cast(op))return resize(ParameterNumber(new VeriNum(0,cached)),width,sign);
    auto* a=static_cast<VeriExp*>(binary->lval());auto* b=static_cast<VeriExp*>(binary->rval());
    if(!a->calc_value()||!b->calc_value())return resize(ParameterNumber(new VeriNum(0,cached)),width,sign);
    const bool logical=op==vtBDAND||op==vtBDOR;
    const bool compare=(op>=vtBLT&&op<=vtBCIEQ)||op==vtBWLEQ||op==vtBWLNEQ;
    const bool shift=op>=vtBLRS&&op<=vtBALS;
    const bool power=op==vtBPOW;
    const int operand_width=compare?std::max(parameter_shape(a).first,parameter_shape(b).first):width;
    const bool common_sign=(compare?parameter_shape(a).second&&parameter_shape(b).second:sign);
    auto left=veri_constant_value(a,logical?0:operand_width,logical?-1:int(common_sign));
    auto right=veri_constant_value(b,logical||shift||power?0:operand_width,logical||shift||power?-1:int(common_sign));
    if(!left||!right||left->binary_operation(op,right.get())!=OK)return {};
    return resize(std::move(left),width,sign);
  }
  if(expression->detail_type()==veEXP_QUES) {
    auto* conditional=static_cast<VeriQuesExp*>(expression);
    auto cond=veri_constant_value(static_cast<VeriExp*>(conditional->ques()),0);
    auto left=veri_constant_value(static_cast<VeriExp*>(conditional->choice1()),width,int(sign));
    auto right=veri_constant_value(static_cast<VeriExp*>(conditional->choice2()),width,int(sign));
    if(!cond||!left||!right)return resize(ParameterNumber(new VeriNum(0,cached)),width,sign);
    cond->unary_operation(vtUOR);const int truth=cond->get_certain_bit(0);
    if(truth==V1)return left;if(truth==V0)return right;
    String bits=std::to_string(width)+(sign?"'sb":"'b");
    for(int i=width-1;i>=0;--i){int a=left->get_certain_bit(i),b=right->get_certain_bit(i);bits+=a!=b?'x':a==VX?'x':a==VZ?'x':a?'1':'0';}
    if(left->parse(bits.c_str(),bits.size())!=OK)return {};return left;
  }
  // Concatenations, selects, casts and system functions are self-determined boundaries.
  return resize(ParameterNumber(new VeriNum(0,cached)),width,sign);
}


// Declarators keep their unpacked ranges; call sites bind the element symbol.
VeriNode* veri_formal_symbol(VeriNode* formal) {
  if(formal&&formal->detail_type()==veEXP_ARRAY)formal=static_cast<VeriArrayExp*>(formal)->id();
  if(formal&&formal->detail_type()==veEXP_PRI)return static_cast<VeriPrimaryExp*>(formal)->var();
  return formal;
}

VeriNode* veri_call_hive(VeriNode* call) {
  if(call&&call->detail_type()==veEXP_MULTI)return static_cast<VeriMultiExp*>(call)->hive();
  if(call&&call->detail_type()==veEXP_CALLER)return static_cast<VeriCallerExp*>(call)->hive();
  if(call&&call->detail_type()==veEXP_MEMBER)return static_cast<VeriMemberExp*>(call)->hive();
  return nullptr;
}
bool veri_subroutine_call(VeriNode* call) {
  return call&&(call->detail_type()==veEXP_CALLER||
    ((call->detail_type()==veEXP_MEMBER||call->detail_type()==veEXP_MULTI)&&veri_call_hive(call)));
}
std::vector<VeriNode*> veri_subroutine_formals(VeriNode* declaration) {
  std::vector<VeriNode*> pending,result;
  if(declaration->detail_type()==vsDECL_FUNC_DECL) {
    auto* f=static_cast<VeriFuncDecl*>(declaration);pending={f->item_decl(),f->port_list()};
  } else {auto* t=static_cast<VeriTaskDecl*>(declaration);pending={t->item_decl(),t->task_port()};}
  while(!pending.empty()) {
    auto* node=pending.back();pending.pop_back();if(!node)continue;
    if(node->detail_type()==vsDECL_TF_DECL) {
      for(auto* port:static_cast<VeriTfDecl*>(node)->port_ids())result.push_back(port);
    } else {
      VeriNode::NodeList* children=nullptr;
      if(node->detail_type()==vsDECL_FUNC_PORT_LIST)children=&static_cast<VeriFuncPortList*>(node)->func_port();
      else if(node->detail_type()==vsDECL_TASK_PORT_LIST)children=&static_cast<VeriTaskPortList*>(node)->task_port();
      else if(node->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST)children=&static_cast<VeriFuncItemDeclList*>(node)->func_item();
      else if(node->detail_type()==vsDECL_TASK_ITEM_DECL_LIST)children=&static_cast<VeriTaskItemDeclList*>(node)->task_item();
      if(children)for(auto it=children->rbegin();it!=children->rend();++it)pending.push_back(*it);
    }
  }
  return result;
}
// Bind without evaluating: both semantic clones and lowering use the same map.
std::vector<VeriCallArgument> veri_bind_arguments(VeriNode* call,const std::vector<VeriNode*>& formals) {
  auto bad=[&](const std::string& message) {throw std::runtime_error("line "+std::to_string(call->line())+": "+message);};
  std::map<std::string,size_t> names;
  std::vector<VeriNode*> defaults,default_sources;
  std::vector<VeriNode*> prototype;
  const bool class_prototype=call->detail_type()==veEXP_MEMBER&&static_cast<VeriMemberExp*>(call)->class_argument_prototype();
  if(call->detail_type()==veEXP_MEMBER)if(auto* declaration=static_cast<VeriMemberExp*>(call)->argument_prototype()) {
    prototype=veri_subroutine_formals(declaration);
    if(prototype.size()!=formals.size())bad("modport prototype argument count mismatch");
  }
  for(size_t i=0;i<formals.size();++i) {
    VeriNode* symbol=veri_formal_symbol(formals[i]);
    if(!symbol||symbol->tok_type()!=vtTFVAR){bad("unresolved subroutine formal");return {};}
    const auto& name=static_cast<VeriTfVar*>(class_prototype?veri_formal_symbol(prototype[i]):symbol)->name();names[name]=i;
    // Class virtual calls bind names/defaults to the static signature.
    // Modport calls bind names to the implementation, but defaults belong
    // to the selected modport's prototype, including per-view overrides.
    auto* source=prototype.empty()?symbol:veri_formal_symbol(prototype[i]);
    defaults.push_back(static_cast<VeriTfDecl*>(source->father())->default_argument(static_cast<VeriTfVar*>(source)->name()));
    default_sources.push_back(source);
  }
  std::vector<VeriCallArgument> result(formals.size(),{nullptr,false});std::vector<bool> bound(formals.size(),false);
  size_t position=0;bool named=false;
  auto* arguments=call->detail_type()==veEXP_CALLER?static_cast<VeriCallerExp*>(call)->arg():
    call->detail_type()==veEXP_MULTI?(static_cast<VeriMultiExp*>(call)->exp().empty()?nullptr:static_cast<VeriMultiExp*>(call)->exp().front()):static_cast<VeriMemberExp*>(call)->arguments();
  if(arguments) {
    std::vector<VeriNode*> actuals{arguments};
    if(arguments->detail_type()==veEXP_MULTI) {
      auto* list=static_cast<VeriMultiExp*>(arguments);
      if(list->multi_type()==vemCOMMA_EXP||list->multi_type()==vemPORT_EXP||list->multi_type()==vemPORT_INST_EXP)
        actuals.assign(list->exp().begin(),list->exp().end());
    }
    for(auto* value:actuals) {
      size_t index=position;
      if(value->detail_type()==veEXP_NAMED_PARAM) {
        named=true;auto* arg=static_cast<VeriNamedParamExp*>(value);
        if(arg->implicit())bad("named subroutine arguments require parentheses");
        auto found=names.find(arg->ref());if(found==names.end())bad("unknown subroutine argument "+arg->ref());
        index=found->second;value=arg->port_exp();
        if(value&&value->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(value)->multi_type()==vemCOMMA_EXP) {
          const auto& expressions=static_cast<VeriMultiExp*>(value)->exp();
          if(expressions.size()!=1)bad("named subroutine argument requires one expression");
          value=expressions.front();
        }
      } else {
        if(named)bad("positional argument follows named subroutine argument");
        if(position>=formals.size())bad("too many subroutine arguments");
        ++position;
      }
      if(bound[index])bad("duplicate subroutine argument");bound[index]=true;
      if(value&&value->detail_type()==veEXP_DUMMY_PORT)value=nullptr;
      result[index]={value,false};
    }
  }
  for(size_t i=0;i<result.size();++i)if(!result[i].value) {
    if(!defaults[i])bad("missing subroutine argument without a default: "+static_cast<VeriTfVar*>(veri_formal_symbol(formals[i]))->name());
    result[i]={defaults[i],true,default_sources[i]};
  }
  return result;
}

    /****************************
     * Tf-Declaration Statement *
     ****************************/

void
VeriTfDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
  _resolved_type = nullptr;
}

int
VeriTfDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;

  if( _range != NULL )
  {
    mqueue.push( _range );
    iqueue.push( depth );
  }

  for(const auto& d:_defaults){mqueue.push(d.second);iqueue.push(depth);}
  NodeList::iterator it = _port_ids.begin();
  for( ; it != _port_ids.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriTfDecl::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_var_type( _net_type );
  ofile << dot_str_in_out( _inout );
  ofile << dot_str_is_tf( "SIGNED", _is_signed );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _range );
  NodeList::iterator it = _port_ids.begin();
  for( ; it != _port_ids.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriTfDecl::check_child_validation( void )
{
  if((veri_integral_atom(_net_type)||veri_real(_net_type)||_net_type==vvCHANDLE)&&_range) {
    veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_TF_DECL);
    return vCHILD_TYPE_TF_DECL;
  }

  if( _range != NULL )
  {
    if( _range->detail_type() != veEXP_RANGE )
    {
      veri_err->append_err( ERR_ERROR, _range->line(), _range->col(),
                            vCHILD_TYPE_TF_DECL );
      return vCHILD_TYPE_TF_DECL;
    }
  }

  NodeList::iterator it = _port_ids.begin();
  for( ; it != _port_ids.end(); ++it )
  {
    if( (*it)->detail_type() != veEXP_PRI && (*it)->detail_type() != veEXP_ARRAY )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(),
                            (*it)->col(), vCHILD_TYPE_TF_DECL );
      return vCHILD_TYPE_TF_DECL;
    }
  }

  return OK;
}

int
VeriTfDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vDECL_S );
      return re;
      break;

    case vDECL_S:
      re = declare_tf_symbol( );
      set_pstatus( vEND_S );
      if(re==OK)for(auto* port:_port_ids) {
        auto* symbol=static_cast<VeriTfVar*>(veri_formal_symbol(port));
        auto* value=default_argument(symbol->name());if(!value)continue;
        // Defaults see preceding formals, then the enclosing declaration
        // scope. Their own name, later formals and body locals are absent.
        auto* context=scope()->floater()->append_scope("$default"+std::to_string(value->idx()),vNAMED_BLOCK_SCOPE);
        for(auto* preceding:veri_subroutine_formals(father()->father())) {
          auto* prior=veri_formal_symbol(preceding);if(prior==symbol)break;
          if(prior&&prior->tok_type()==vtTFVAR)context->insert(static_cast<VeriTfVar*>(prior)->name(),prior);
        }
        value->set_scope(context);value->set_is_decl(IS_FALSE);value->set_is_trash(IS_TRUE);
        // Declaring a default must not expand a runtime call before enclosing
        // forward classes/signatures are complete. Activation clones bind
        // their defaults immediately in the same preceding-formal context.
        auto* routine=father()->father();
        if(veri_subroutine_call(routine->father()))mstack.push_back(value);
        else veri_parser->defer_semantic(value);
      }
      return re;
      break;

    default:
      return OK;
      break;
  }
}

int
VeriTfDecl::push_children( NodeVec& mstack )
{
  _resolved_type=_type_expression?static_cast<VeriTypeExp*>(_type_expression)->resolve(scope()):signature_type(this,_type_name);
  if(_resolved_type){_net_type=_resolved_type->net_type();_is_signed=_resolved_type->is_signed();}
  if(!_defaults.empty()&&(!father()||(father()->detail_type()!=vsDECL_FUNC_PORT_LIST&&father()->detail_type()!=vsDECL_TASK_PORT_LIST)))
    throw std::runtime_error("line "+std::to_string(line())+": formal defaults require ANSI declarations");
  mstack.push_back( this );

  NodeList::reverse_iterator it = _port_ids.rbegin();
  for( ; it != _port_ids.rend(); ++it )
  {
    //(*it)->clean_up();
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }

  if( _range != NULL )
  {
    //_range->clean_up();
    _range->set_is_trash( IS_TRUE );
    _range->set_scope( scope() );
    mstack.push_back( _range );
  }
  return OK;
}

int
VeriTfDecl::declare_tf_symbol( void )
{
  int dstart = _resolved_type?_resolved_type->dstart():veri_type_width(_net_type)-1;
  int dend   = _resolved_type?_resolved_type->dend():0;

  if( _range != NULL )
  {
    VeriRangeExp *range = static_cast<VeriRangeExp *>(_range);
    dstart = range->range_from();
    dend   = range->range_to();
  }

  VeriPrimaryExp *pexp = NULL;
  VeriTfVar *symbol = NULL;
  NodeList::iterator inl = _port_ids.begin();
  for( ; inl != _port_ids.end(); ++inl )
  {
    auto* declarator=*inl;
    auto* array=declarator->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(declarator):nullptr;
    pexp = static_cast<VeriPrimaryExp *>(array?array->id():declarator);
    symbol = reg_tfvar_symbol( (*inl)->line(), (*inl)->col(),
                              pexp->str(), dstart, dend, *inl );
    if(!symbol)return vTF_PORT_REDEFINE;
    if(array) {
      auto last=array->range_to().begin();
      auto dimension=array->range().begin();
      for(int first:array->range_from()) {
        auto* range=static_cast<VeriRangeExp*>(*dimension++);
        if(dimension==std::next(array->range().begin())){symbol->set_container(range->rtype(),range->rtype()==vrQUEUE&&range->right()?range->range_to():-1);symbol->set_associative_key_type(range->associative_key_type());}
        const bool open=range->rtype()==vrOPEN;
        symbol->add_range(first,*last++,open);
      }
    }
    if(array)bind_container_dimensions(symbol,array->range());
    append_type_ranges(symbol,_resolved_type);
    pexp->set_var( symbol );
  }

  return OK;
}

VeriTfVar *
VeriTfDecl::reg_tfvar_symbol( int line, int col, CString& name, int dstart,
                              int dend, VeriNode *decl )
{
  VeriNode * node = scope()->value_same_level( name );
  if( node != NULL )
  {
    veri_err->append_err( ERR_ERROR, decl, vTF_PORT_REDEFINE );
    return NULL;
  }

  VeriNum *init = NULL;
  init = new VeriNum( veri_parser->next_id(), decl->line(),
                      decl->col(), birth_mod());
  init->init_val( _is_signed, abs(dend-dstart)+1 );
  init->set_father( decl );
  veri_parser->insert_node( init );

  VeriTfVar * var = new VeriTfVar( veri_parser->next_id(), line, col,
                                   name, _inout, _net_type, _is_signed,
                                   decl, dstart, dend, init, birth_mod() );
  if(_resolved_type)var->set_class_type_from(_resolved_type);
  veri_parser->insert_node( var );

  var->set_father( this );
  var->set_scope( scope() );

  scope()->insert( name, var );
  return var;
}

int
VeriTfDecl::push_for_replacement( NodeVec& mstack )
{
  if(_type_expression)mstack.push_back(_type_expression);
  if( _range != NULL )
    mstack.push_back( _range );

  for(const auto& d:_defaults)mstack.push_back(d.second);
  NodeList::iterator it = _port_ids.begin();
  for( ; it != _port_ids.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriTfDecl::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriTfDecl *tmp = new VeriTfDecl( idx, this );

  // begin replacement
  NodeList::iterator it = _port_ids.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _port_ids.end(); ++it )
  {
    tmp->_port_ids.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  for(auto d=_defaults.rbegin();d!=_defaults.rend();++d) {
    itl=inl;--itl;tmp->_defaults[d->first]=*itl;(*itl)->set_father(tmp);node_list.erase(itl);
  }
  itl=inl;
  if( _range != NULL )
  {
    tmp->_range = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  if(_type_expression){itl=inl;--itl;tmp->_type_expression=*itl;(*itl)->set_father(tmp);node_list.erase(itl);}
  *inl = tmp;
  return OK;
}

    /****************************
     * Task-Port-List Statement *
     ****************************/

void
VeriTaskPortList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriTaskPortList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _task_port.begin();
  for( ; it != _task_port.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return _task_port.size();
}

int
VeriTaskPortList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _task_port.begin();
  for( ; it != _task_port.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriTaskPortList::check_child_validation( void )
{
  return OK;
}

int
VeriTaskPortList::check_last_child_validation( void )
{
  VeriNode * last = _task_port.back();

  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),col(), vCHILD_TYPE_TASK_PORT_LIST );
    return vCHILD_TYPE_TASK_PORT_LIST;
  }
   
  if( last->detail_type() != vsDECL_TF_DECL )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_TASK_PORT_LIST );
    return vCHILD_TYPE_TASK_PORT_LIST;
  }
  return OK;
}

int
VeriTaskPortList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriTaskPortList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _task_port.rbegin();
  for( ; it != _task_port.rend(); ++it )
  {
    //(*it)->clean_up();
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriTaskPortList::do_nothing( void )
{
  return OK;
}

int
VeriTaskPortList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _task_port.begin();
  for( ; it != _task_port.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriTaskPortList::replace_node( Uint idx, NodeList& node_list,
                                NodeList::iterator& inl)
{
  // spawn duplicant
  VeriTaskPortList *tmp = new VeriTaskPortList( idx, this );

  // begin replacement
  NodeList::iterator it = _task_port.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _task_port.end(); ++it )
  {
    tmp->_task_port.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************
     * Func-Port-List Statement *
     ****************************/

void
VeriFuncPortList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncPortList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _func_port.begin();
  for( ; it != _func_port.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return _func_port.size();
}

int
VeriFuncPortList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _func_port.begin();
  for( ; it != _func_port.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriFuncPortList::check_child_validation( void )
{
  return OK;
}

int
VeriFuncPortList::check_last_child_validation( void )
{
  VeriNode * last = _func_port.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),col(), vCHILD_TYPE_FUNC_PORT_LIST );
    return vCHILD_TYPE_FUNC_PORT_LIST;
  }

  if( last->detail_type() != vsDECL_TF_DECL )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_FUNC_PORT_LIST );
    return vCHILD_TYPE_FUNC_PORT_LIST;
  }

  VeriTfDecl *tf = static_cast<VeriTfDecl *>(last);
  if( tf->inout() != vpIN && tf->inout() != vpOUT && tf->inout() != vpINOUT && tf->inout() != vpREF && tf->inout() != vpCONST_REF )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_FUNC_PORT_LIST );
    return vCHILD_TYPE_FUNC_PORT_LIST;
  }

  return OK;
}

int
VeriFuncPortList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriFuncPortList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _func_port.rbegin();
  for( ; it != _func_port.rend(); ++it )
  {
    //(*it)->clean_up();
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriFuncPortList::do_nothing( void )
{
  return OK;
}

int
VeriFuncPortList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _func_port.begin();
  for( ; it != _func_port.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriFuncPortList::replace_node( Uint idx, NodeList& node_list,
                                NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncPortList *tmp = new VeriFuncPortList( idx, this );

  // begin replacement
  NodeList::iterator it = _func_port.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _func_port.end(); ++it )
  {
    tmp->_func_port.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************************
     * Task-Item-Declaration-List Statement *
     ****************************************/

void
VeriTaskItemDeclList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriTaskItemDeclList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _task_item.begin();
  for( ; it != _task_item.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return _task_item.size();
}

int
VeriTaskItemDeclList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _task_item.begin();
  for( ; it != _task_item.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriTaskItemDeclList::check_child_validation( void )
{
  return OK;
}

int
VeriTaskItemDeclList::check_last_child_validation( void )
{
  VeriNode * last = _task_item.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_TASK_ITEM_DECL_LIST );
    return vCHILD_TYPE_TASK_ITEM_DECL_LIST;
  }
   
  if( last->tok_type() != vtDECL && last->detail_type()!=vsDECL_IMPORT )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_TASK_ITEM_DECL_LIST );
    return vCHILD_TYPE_TASK_ITEM_DECL_LIST;
  }
  return OK;
}

int
VeriTaskItemDeclList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriTaskItemDeclList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _task_item.rbegin();
  for( ; it != _task_item.rend(); ++it )
  {
    //(*it)->clean_up();
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriTaskItemDeclList::do_nothing( void )
{
  return OK;
}

int
VeriTaskItemDeclList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _task_item.begin();
  for( ; it != _task_item.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriTaskItemDeclList::replace_node( Uint idx, NodeList& node_list,
                                    NodeList::iterator& inl)
{
  // spawn duplicant
  VeriTaskItemDeclList *tmp = new VeriTaskItemDeclList( idx, this );

  // begin replacement
  NodeList::iterator it = _task_item.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _task_item.end(); ++it )
  {
    tmp->_task_item.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /*****************************************
     * Block-Item-Declaration-List Statement *
     *****************************************/

void
VeriBlockItemDeclList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriBlockItemDeclList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _block_item.begin();
  for( ; it != _block_item.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriBlockItemDeclList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _block_item.begin();
  for( ; it != _block_item.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriBlockItemDeclList::check_child_validation( void )
{
  return OK;
}

int
VeriBlockItemDeclList::check_last_child_validation( void )
{
  VeriNode * last = _block_item.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_BLOCK_ITEM_DECL_LIST );
    return vCHILD_TYPE_BLOCK_ITEM_DECL_LIST;
  }
  if( last->tok_type() != vtDECL && last->detail_type()!=vsDECL_IMPORT )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_BLOCK_ITEM_DECL_LIST );
    return vCHILD_TYPE_BLOCK_ITEM_DECL_LIST;
  }
  return OK;
}

int
VeriBlockItemDeclList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriBlockItemDeclList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _block_item.rbegin();
  for( ; it != _block_item.rend(); ++it )
  {
    //(*it)->clean_up();
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriBlockItemDeclList::do_nothing( void )
{
  return OK;
}

int
VeriBlockItemDeclList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _block_item.begin();
  for( ; it != _block_item.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriBlockItemDeclList::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriBlockItemDeclList *tmp = new VeriBlockItemDeclList( idx, this );

  // begin replacement
  NodeList::iterator it = _block_item.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _block_item.end(); ++it )
  {
    tmp->_block_item.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /********************************************
     * Function-Item-Declaration-List Statement *
     ********************************************/

void
VeriFuncItemDeclList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncItemDeclList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _func_item.begin();
  for( ; it != _func_item.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriFuncItemDeclList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _func_item.begin();
  for( ; it != _func_item.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriFuncItemDeclList::check_child_validation( void )
{
  return OK;
}

int
VeriFuncItemDeclList::check_last_child_validation( void )
{
  VeriNode * last = _func_item.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_FUNC_ITEM_DECL_LIST );
    return vCHILD_TYPE_FUNC_ITEM_DECL_LIST;
  }
  if( last->tok_type() != vtDECL && last->detail_type()!=vsDECL_IMPORT )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                          last->col(), vCHILD_TYPE_FUNC_ITEM_DECL_LIST );
    return vCHILD_TYPE_FUNC_ITEM_DECL_LIST;
  }
  return OK;
}

int
VeriFuncItemDeclList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriFuncItemDeclList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _func_item.rbegin();
  for( ; it != _func_item.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriFuncItemDeclList::do_nothing( void )
{
  return OK;
}

int
VeriFuncItemDeclList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _func_item.begin();
  for( ; it != _func_item.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriFuncItemDeclList::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncItemDeclList *tmp = new VeriFuncItemDeclList( idx, this );

  // begin replacement
  NodeList::iterator it = _func_item.begin();
  NodeList::iterator itl = inl; 
  for( ; it != _func_item.end(); ++it )
  {
    tmp->_func_item.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /********************
     * Task-Declaration *
     ********************/

void
VeriTaskDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
  _act_port_num = 0;
  _act_ports.clear();
}

int
VeriTaskDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;

  if( _task_port != NULL )
  {
    mqueue.push( _task_port );
    iqueue.push( depth );
  }
  if( _item_decl != NULL )
  {
    mqueue.push( _item_decl );
    iqueue.push( depth );
  }

  mqueue.push( _stmt );
  iqueue.push( depth );

  if(extern_header()){mqueue.push(extern_header());iqueue.push(depth);}
  return OK;
}

int
VeriTaskDecl::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _task_name );
  ofile << dot_str_is_tf( "AUTO", _is_auto );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _task_port );
  ofile << dot_str_conn( idx(), _item_decl );
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriTaskDecl::check_child_validation( void )
{
  if( _task_name.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_TASK_DECL );
    return vCHILD_TYPE_TASK_DECL;
  }

  if( _task_port != NULL )
  {
    if( _task_port->detail_type() != vsDECL_TASK_PORT_LIST )
    {
      veri_err->append_err( ERR_ERROR, _task_port->line(),
                            _task_port->col(), vCHILD_TYPE_TASK_DECL );
      return vCHILD_TYPE_TASK_DECL;
    }
  }

  if( _item_decl != NULL )
  {
    if( _item_decl->tok_type() != vtDECL )
    {
      veri_err->append_err( ERR_ERROR, _item_decl->line(),
                            _item_decl->col(), vCHILD_TYPE_TASK_DECL );
      return vCHILD_TYPE_TASK_DECL;
    }
  }

  if( _stmt == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_TASK_DECL );
    return vCHILD_TYPE_TASK_DECL;
  }
   
  if( _stmt->tok_type() != vtSTMT )
  {
    veri_err->append_err( ERR_ERROR, _stmt->line(),
                          _stmt->col(), vCHILD_TYPE_TASK_DECL );
    return vCHILD_TYPE_TASK_DECL;
  }

  return OK;
}

int
VeriTaskDecl::search_for_symbol( NodeVec& /*seq*/, String& /*help_info*/ )
{
  return reg_task_symbol( );
}

int
VeriTaskDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_ports( mstack );
      set_pstatus( vGET_CALL_EXP_S );
      return re;
      break;

    case vGET_CALL_EXP_S :
      re = get_call_exp( );
      if( re != OK ) return re;

      if(    father() != NULL
          && !veri_subroutine_call(father()) )
      {
        set_pstatus( vEND_S );
        return reg_task_symbol( );
      }
      else
      {
        set_pstatus( vEND_S );
        return push_contents( mstack );
      }
      break;

    default:
      return finish_scope( );
      break;
  }
}

int
VeriTaskDecl::reg_task_symbol( void )
{
  if(!modport_prototype().empty())return OK;
  VeriNode * node_out = scope()->floater()->value_same_level( _task_name );
  VeriNode * node = scope()->value_same_level( _task_name );
  if( node != NULL || node_out != NULL )
  {
    if( node && node_out && node->tok_type( ) == vtTASK && node_out->tok_type( ) == vtTASK )
    {
      VeriTask *task     = static_cast<VeriTask *>(node);
      VeriTask *task_out = static_cast<VeriTask *>(node_out);
      
      if( task->task() != this || task_out->task() != this )
      {
        veri_err->append_err( ERR_ERROR, this, vTASK_REDEFINE );
        return vTASK_REDEFINE;
      }
      else
        return OK;
    }
    else
    {
      veri_err->append_err( ERR_ERROR, this, vTASK_REDEFINE );
      return vTASK_REDEFINE;
    }
  }

  VeriTask * symbol = new VeriTask( veri_parser->next_id(), line(), col(),
                                    _task_name, this, birth_mod() ); 
  veri_parser->insert_node( symbol );
  symbol->set_father( this );
  symbol->set_scope( scope() );

  scope()->insert( _task_name, symbol );
  scope()->floater()->insert( _task_name, symbol );
  return OK;
}

int
VeriTaskDecl::push_ports( NodeVec& mstack )
{
  mstack.push_back( this );

  set_scope( scope()->append_scope( modport_prototype().empty()?_task_name:
    "$modport$"+modport_prototype()+"$"+_task_name, vTASK_SCOPE ) );

  if( _item_decl != NULL )
  {
    push_subroutine_items(_item_decl,scope(),mstack,veri_subroutine_call(father()));
  }

  if( _task_port != NULL )
  {
    //_task_port->clean_up( );
    _task_port->set_is_decl( IS_TRUE );
    _task_port->set_is_trash( IS_TRUE );
    _task_port->set_scope( scope() );
    mstack.push_back( _task_port );
  }

  return OK;
}

int
VeriTaskDecl::get_call_exp( void )
{
  if(!veri_subroutine_call(father()))return OK;
  int result=prep_ports_for_check_type();if(result!=OK)return result;
  auto* caller=father();
  veri_bind_arguments(caller,std::vector<VeriNode*>(_act_ports.begin(),_act_ports.end()));
  // Runtime conversion/copy-in/out belongs to lowering. Do not assign actual
  // parser values into formals or require dynamic array indices to be constant.
  return OK;
}

int
VeriTaskDecl::prep_ports_for_check_type( void )
{
  if(_task_port==NULL && _item_decl==NULL)return OK;
  if( _task_port != NULL )
  {
    if( _task_port->detail_type( ) != vsDECL_TASK_PORT_LIST )
      return vSEC_CALLER_PORT_MISMATCH;

    VeriTaskPortList * port_list
      = static_cast<VeriTaskPortList *>(_task_port);
    NodeList &tf_decl_list = port_list->task_port();

    NodeList::iterator idecl = tf_decl_list.begin();
    NodeList::iterator iport;

    VeriPrimaryExp *pexp = NULL;
    for( ; idecl != tf_decl_list.end(); ++idecl )
    {
      NodeList &port_ids = (static_cast<VeriTfDecl *>(*idecl))->port_ids();
      iport = port_ids.begin();
      for( ; iport != port_ids.end(); ++iport )
      {
        auto* port=*iport;
        pexp = static_cast<VeriPrimaryExp *>(port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port);
        if( pexp->var() == NULL && pexp->calc_value( ) == NULL )
        {
          veri_err->append_err( ERR_ERROR, this, vSEC_CALLER_PORT_NOT_COMPLETE );
          return vSEC_CALLER_PORT_NOT_COMPLETE;
        }
        _act_ports.push_back( pexp->var() );
        _act_port_num++;
      }
    }
  }
  else
  {
    if( _item_decl->detail_type( ) != vsDECL_TASK_ITEM_DECL_LIST )
      return OK;

    VeriTaskItemDeclList * item_list
      = static_cast<VeriTaskItemDeclList *>(_item_decl);
    NodeList &decl_list = item_list->task_item();

    NodeList::iterator idecl = decl_list.begin();
    NodeList::iterator iport;

    VeriPrimaryExp *pexp = NULL;
    for( ; idecl != decl_list.end(); ++idecl )
    {
      if( (*idecl)->detail_type( ) == vsDECL_TF_DECL )
      {
        NodeList &port_ids = (static_cast<VeriTfDecl *>(*idecl))->port_ids();
        iport = port_ids.begin();
        for( ; iport != port_ids.end(); ++iport )
        {
          auto* port=*iport;
        pexp = static_cast<VeriPrimaryExp *>(port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port);
          if( pexp->var() == NULL && pexp->calc_value( ) == NULL )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_CALLER_PORT_NOT_COMPLETE );
            return vSEC_CALLER_PORT_NOT_COMPLETE;
          }
          _act_ports.push_back( pexp->var() );
          _act_port_num++;
        }
      }
    }
  }
  return OK;
}

/*
 *  exp and var should not be null, garanteed by caller
 */
int
VeriTaskDecl::check_type_ref( VeriExp *exp, VeriNode *port, int no_assign )
{
  int re = OK;

  VeriVar    * var      = NULL;
  VeriTfVar  * tfvar    = NULL;
  VeriParam  * param    = NULL;
  VeriInt    * int_var  = NULL;
  VeriGenVar * genvar   = NULL;
  VeriVar    * svar     = NULL;
  VeriParam  * sparam   = NULL;
  VeriTfVar  * stfvar   = NULL;
  VeriInt    * sint_var = NULL;
  VeriGenVar * sgenvar  = NULL;

  switch( port->tok_type( ) )
  {
    case vtVAR    : var     = static_cast<VeriVar    *>(port); break;
    case vtTFVAR  : tfvar   = static_cast<VeriTfVar  *>(port); break;
    case vtPARAM  : param   = static_cast<VeriParam  *>(port); break;
    case vtINT    : int_var = static_cast<VeriInt    *>(port); break;
    case vtGENVAR : genvar  = static_cast<VeriGenVar *>(port); break;
    default : return vSEC_CALLER_PORT_MISMATCH;
  }

  IVec dummy_dimen;

  switch( exp->detail_type( ) )
  {
    case veEXP_PRI :
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(exp);
      if( pexp->var( ) == NULL )
      {
        if( pexp->pri_type( ) == veNUM )
        {
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
        }
        return OK;
        break;
      }

      switch( pexp->var()->tok_type( ) )
      {
        case vtVAR :
          svar = static_cast<VeriVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != svar->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != svar->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && svar->range_depth( ) == 0 )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtTFVAR :
          stfvar = static_cast<VeriTfVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtPARAM :
          sparam = static_cast<VeriParam *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtINT :
          sint_var = static_cast<VeriInt *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != sint_var->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && sint_var->range_depth( ) == 0 )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != sint_var->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && sint_var->range_depth( ) == 0 )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtGENVAR :
          sgenvar = static_cast<VeriGenVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        default:
          break;
      }
      break;
    }

    case veEXP_UNA :
    case veEXP_BIN :
    case veEXP_SIGN :
    case veEXP_UNSIGN :
    case veEXP_MCONCAT :
    {
      switch( port->tok_type( ) )
      {
        case vtVAR :
        {
          if( var->range_depth( ) == 0 )
          {
            return OK;
          }
          else
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          break;
        }

        case vtTFVAR :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            tfvar->set_val( num );
          }
          return OK;
          break;

        case vtPARAM :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            param->set_val( num );
          }
          return OK;
          break;
        
        case vtGENVAR :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            genvar->set_val( num );
          }
          return OK;
          break;

        case vtINT :
          if( var->range_depth( ) == 0 )
          {
            if( no_assign == IS_FALSE )
            {
              VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
              veri_parser->insert_node( num );
              num->set_father( tfvar );
              int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            }
            return OK;
          }
          else
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          break;

        default:
          return vSEC_CALLER_PORT_MISMATCH;
      }
      break;
    }

    case veEXP_ARRAY :
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(exp);
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(aexp->id());

      if( pexp->var() != NULL )
        return vSEC_CALLER_PORT_MISMATCH;

      switch( port->tok_type( ) )
      {
        case vtPARAM : case vtGENVAR :
          veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
          return vSEC_CALLER_PORT_MISMATCH;

        case vtVAR :
          if( aexp->range_depth( ) > var->range_depth( ) )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;
        
        case vtINT :
          if( aexp->range_depth( ) > int_var->range_depth( ) )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          else
          {
            if( no_assign == IS_FALSE )
            {
              VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
              veri_parser->insert_node( num );
              num->set_father( tfvar );
              int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            }
            return OK;
          }
          break;
      }
      return OK;
      break;
    }

    case veEXP_NAMED_PARAM :
    {
      VeriNamedParamExp * nexp = static_cast<VeriNamedParamExp *>(exp);
      switch( port->tok_type( ) )
      {
        case vtVAR :
          if( var->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;

        case vtTFVAR :
          if( tfvar->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
         break;

        case vtPARAM :
          if( param->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
         break;
        
        case vtGENVAR :
          if( genvar->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;

        case vtINT :
          if( int_var->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;
      }

      VeriExp *inner_exp = static_cast<VeriExp *>(nexp->port_exp());
      return check_type_ref( inner_exp, port, IS_FALSE );
      break;
    }

    case veEXP_CALLER :
    {
      VeriCallerExp *cexp = static_cast<VeriCallerExp *>(exp);
      if( cexp->call_type() == vtTASK_CALL )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
        return vSEC_CALLER_PORT_MISMATCH;
      }
      else
      {
        assert( cexp->hive()->detail_type() == vsDECL_FUNC_DECL );
        VeriFuncDecl *func = static_cast<VeriFuncDecl *>(cexp->hive());
        if( func->ret_value() != NULL )
        {
          VeriFunc *ret_value = func->ret_value();
          switch( port->tok_type( ) )
          {
            case vtVAR :
            {
              if( var->range_depth( ) == 0 )
              {
                return OK;
              }
              else
              {
                veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
                return vSEC_CALLER_PORT_MISMATCH;
              }
              break;
            }

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                param->set_val( num );
              }
              return OK;
              break;
            
            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( var->range_depth( ) == 0 )
              {
                if( no_assign == IS_FALSE )
                {
                  VeriNum *num = new VeriNum( veri_parser->next_id(),
                                              ret_value->get_val( ) );
                  veri_parser->insert_node( num );
                  num->set_father( tfvar );
                  int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
                }
                return OK;
              }
              else
              {
                veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
                return vSEC_CALLER_PORT_MISMATCH;
              }
              break;

            default:
              return vSEC_CALLER_PORT_MISMATCH;
          }
        }
        else
        {
           veri_err->append_err( ERR_ERROR, exp, vSEC_FUNC_NO_RET );
           return vSEC_FUNC_NO_RET;
        }
      }
    }
    break;

    case veEXP_MINTY :
    {
      VeriMintypmaxExp *pmax = static_cast<VeriMintypmaxExp *>(exp);
      VeriExp *exp1 = static_cast<VeriExp *>(pmax->exp_child1( ) );
      VeriExp *exp2 = static_cast<VeriExp *>(pmax->exp_child2( ) );
      VeriExp *exp3 = static_cast<VeriExp *>(pmax->exp_child3( ) );

      re = check_type_ref( exp1, port, IS_TRUE );
      if( re != OK )
        return re;

      re = check_type_ref( exp2, port, IS_TRUE );
      if( re != OK )
        return re;
         
      return check_type_ref( exp3, port, IS_TRUE );
      break;
    }

    case veEXP_QUES :
    {
      VeriQuesExp *ques = static_cast<VeriQuesExp *>(exp);
      VeriExp  *choice  = static_cast<VeriExp *>(ques->choice ( ) );
      VeriExp  *choice1 = static_cast<VeriExp *>(ques->choice1( ) );
      VeriExp  *choice2 = static_cast<VeriExp *>(ques->choice2( ) );

      if( choice != NULL )
        return check_type_ref( choice, port, IS_FALSE );
      else
      {
        re = check_type_ref( choice1, port, IS_TRUE );
        if( re != OK )
          return re;
           
        return check_type_ref( choice2, port, IS_TRUE );
      }
      break;
    }

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(exp);
      NodeList & exp_list = mexp->exp();
      NodeList::iterator it = exp_list.begin();
      for( ; it != exp_list.end(); ++it )
      {
        re = check_type_ref( static_cast<VeriExp *>(*it), port, IS_TRUE );
        if( re != OK )
          return re;
      }
      return OK;
      break;
    }

    default:
      return OK;
      break;
  }
  return OK;
}

int
VeriTaskDecl::push_contents( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_is_trash( IS_TRUE );
  _stmt->set_scope( scope() );
  mstack.push_back( _stmt );

  return OK;
}

int
VeriTaskDecl::finish_scope( void )
{
  scope()->finish_scope();
  return OK;
}

int
VeriTaskDecl::push_for_replacement( NodeVec& mstack )
{
  if( _task_port != NULL )
    mstack.push_back( _task_port );

  if( _item_decl != NULL )
    mstack.push_back( _item_decl );

  mstack.push_back( _stmt );

  if(extern_header())mstack.push_back(extern_header());
  return OK;
}

int
VeriTaskDecl::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriTaskDecl *tmp = new VeriTaskDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  if(extern_header()){--itl;tmp->set_extern_header(*itl);node_list.erase(itl);itl=inl;}
  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _item_decl != NULL )
  {
    tmp->_item_decl = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _task_port != NULL )
  {
    tmp->_task_port = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /************************
     * Function-Declaration *
     ************************/

int VeriFuncDecl::result_type() const {
  return _resolved_type?_resolved_type->net_type():_is_int==IS_TRUE?vvINT:_is_int==2?vvTIME:_is_int>=100?_is_int-100:vvREG;
}

void
VeriFuncDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
  _resolved_type = nullptr;
  _ret = NULL;
  _act_ports.clear();
  _act_port_num = 0;
}

int
VeriFuncDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  if( _range     != NULL )
  {
    mqueue.push( _range     );
    iqueue.push( depth     );
  }

  if( _port_list != NULL )
  {
    mqueue.push( _port_list );
    iqueue.push( depth     );
  }

  if( _item_decl != NULL )
  {
    mqueue.push( _item_decl );
    iqueue.push( depth     );
  }

  mqueue.push( _stmt );
  iqueue.push( depth );
  if(extern_header()){mqueue.push(extern_header());iqueue.push(depth);}
  return OK;
}

int
VeriFuncDecl::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _func_name );
  ofile << dot_str_is_tf( "AUTO", _is_auto );
  ofile << dot_str_is_tf( "SIGNED", _is_signed );
  ofile << dot_str_is_tf( "INT", _is_int );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _range );
  ofile << dot_str_conn( idx(), _port_list );
  ofile << dot_str_conn( idx(), _item_decl );
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriFuncDecl::check_child_validation( void )
{
  if((integral_result()||is_void())&&_range) {
    veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_FUNC_DECL);
    return vCHILD_TYPE_FUNC_DECL;
  }

  if( _func_name.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_FUNC_DECL );
    return vCHILD_TYPE_FUNC_DECL;
  }

  if( _range != NULL )
  {
    if( _range->detail_type() != veEXP_RANGE )
    {
      veri_err->append_err( ERR_ERROR, _range->line(),
                          _range->col(), vCHILD_TYPE_FUNC_DECL );
      return vCHILD_TYPE_FUNC_DECL;
    }

    VeriRangeExp *rexp = static_cast<VeriRangeExp *>(_range);
    if(rexp->rtype() != vrSEMI )
    {
      veri_err->append_err( ERR_ERROR, _range->line(),
                          _range->col(), vCHILD_TYPE_FUNC_DECL );
      return vCHILD_TYPE_FUNC_DECL;
    }
  }

  if( _port_list != NULL )
  {
    if( _port_list->detail_type() != vsDECL_FUNC_PORT_LIST )
    {
      veri_err->append_err( ERR_ERROR, _port_list->line(),
                          _port_list->col(), vCHILD_TYPE_FUNC_DECL );
      return vCHILD_TYPE_FUNC_DECL;
    }
  }

  if( _item_decl != NULL )
  {
    if( _item_decl->tok_type() != vtDECL )
    {
      veri_err->append_err( ERR_ERROR, _item_decl->line(),
                          _item_decl->col(), vCHILD_TYPE_FUNC_DECL );
      return vCHILD_TYPE_FUNC_DECL;
    }
  }

  if( _stmt == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_FUNC_DECL );
    return vCHILD_TYPE_FUNC_DECL;
  }
   
  if( _stmt->tok_type() != vtSTMT )
  {
    veri_err->append_err( ERR_ERROR, _stmt->line(),
                          _stmt->col(), vCHILD_TYPE_FUNC_DECL );
    return vCHILD_TYPE_FUNC_DECL;
  }

  return OK;
}

int
VeriFuncDecl::search_for_symbol( NodeVec& /*seq*/, String& /*help_info*/ )
{
  return reg_func_symbol( );
}

int
VeriFuncDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_ports( mstack );
      set_pstatus( vGET_CALL_EXP_S );
      return re;
      break;

    case vGET_CALL_EXP_S :
      re = get_call_exp( );
      if( re != OK ) return re;

      if(    father() != NULL
          && !veri_subroutine_call(father()) )
      {
        set_pstatus( vEND_S );
        return reg_func_symbol( );
      }
      else
      {
        set_pstatus( vEND_S );
        return push_contents( mstack );
      }
      break;

    default:
      return finish_scope( );
      break;
  }
}

int
VeriFuncDecl::reg_func_symbol( void )
{
  if(!modport_prototype().empty())return OK;
  VeriNode * node_out = scope()->floater()->value_same_level( _func_name );
  VeriNode * node = scope()->value_same_level( _func_name );

  if( node != NULL || node_out != NULL )
  {
    if( node && node_out && node->tok_type( ) == vtFUNC && node_out->tok_type( ) == vtFUNC )
    {
      VeriFunc *func     = static_cast<VeriFunc *>(node);
      VeriFunc *func_out = static_cast<VeriFunc *>(node_out);
      
      if( func->func() != this || func_out->func() != this )
      {
        veri_err->append_err( ERR_ERROR, this, vFUNC_REDEFINE );
        return vFUNC_REDEFINE;
      }
    }
    else
    {
      veri_err->append_err( ERR_ERROR, this, vFUNC_REDEFINE );
      return vFUNC_REDEFINE;
    }
  }

  int dstart = _resolved_type?_resolved_type->dstart():veri_type_width(result_type())-1;
  int dend   = _resolved_type?_resolved_type->dend():0;

  if( _range != NULL )
  {
    VeriRangeExp *range = static_cast<VeriRangeExp *>(_range);
    dstart = range->range_from();
    dend   = range->range_to();
  }

  VeriNum *init = new VeriNum( veri_parser->next_id( ), line(),
                               col(), birth_mod() );

  init->init_val( _is_signed, abs(dend-dstart)+1 );

  init->set_father( this );
  veri_parser->insert_node( init );

  VeriFunc * symbol = new VeriFunc( veri_parser->next_id(), line(), col(),
                                    _func_name, this, dstart, dend,
                                    _is_signed, _is_auto, init,
                                    birth_mod() ); 
  veri_parser->insert_node( symbol );
  symbol->set_father( this );
  symbol->set_scope( scope() );

  if( node == NULL && node_out == NULL )
  {
    scope()->insert( _func_name, symbol );
    scope()->floater()->insert( _func_name, symbol );
  }
  else
  {
    assert( node != NULL && node_out != NULL );
    veri_parser->toss_node( node->idx( ) );
    scope()->replace_value_same_level( _func_name, symbol );
    scope()->floater()->replace_value_same_level( _func_name, symbol );
  }

  return OK;
}

int
VeriFuncDecl::push_ports( NodeVec& mstack )
{
  auto* result_context=scope();
  const bool external_definition=father()&&father()->detail_type()==vsDECL_FUNC_DECL&&
    static_cast<VeriFuncDecl*>(father())->extern_header()==this;
  if(external_definition) {
    VeriSeqBlock* cls=nullptr;
    for(auto* context=scope();context;context=context->floater())if(context->class_owner()){cls=context->class_owner();break;}
    if(!cls)throw std::runtime_error("extern method return type has no class context");
    // The return type precedes C::method, so unqualified types/bounds see the
    // enclosing scope. C::T still denotes this class/specialization (8.24/8.25.1).
    result_context=cls->scope()->floater()->append_scope("$extern_return_"+_func_name,vNAMED_BLOCK_SCOPE);
    result_context->set_class_owner(cls);
  }
  _resolved_type=_type_expression?static_cast<VeriTypeExp*>(_type_expression)->resolve(result_context):signature_type(this,_type_name,result_context);
  if(_resolved_type)_is_signed=_resolved_type->is_signed();
  mstack.push_back( this );

  set_scope( scope()->append_scope( modport_prototype().empty()?_func_name:
    "$modport$"+modport_prototype()+"$"+_func_name, vFUNC_SCOPE ) );

  if( _item_decl != NULL )
  {
    push_subroutine_items(_item_decl,scope(),mstack,veri_subroutine_call(father()));
  }

  if( _port_list != NULL )
  {
    //_port_list->clean_up( );
    _port_list->set_is_decl( IS_TRUE );
    _port_list->set_is_trash( IS_TRUE );
    _port_list->set_scope( scope( ) );
    mstack.push_back( _port_list );
  }

  if( _range != NULL )
  {
    //_range->clean_up( );
    _range->set_is_decl( IS_TRUE );
    _range->set_is_trash( IS_TRUE );
    _range->set_scope( external_definition?result_context:scope() );
    mstack.push_back( _range );
  }

  return OK;
}

int
VeriFuncDecl::get_call_exp( void )
{
  if(!veri_subroutine_call(father()))return OK;
  int result=prep_ports_for_check_type();if(result!=OK)return result;
  auto* caller=father();
  veri_bind_arguments(caller,std::vector<VeriNode*>(_act_ports.begin(),_act_ports.end()));
  // Runtime conversion/copy-in/out belongs to lowering. Do not assign actual
  // parser values into formals or require dynamic array indices to be constant.
  return OK;
}

int
VeriFuncDecl::prep_ports_for_check_type( void )
{
  if(_port_list==NULL && _item_decl==NULL)return OK;
  if( _port_list != NULL )
  {
    if( _port_list->detail_type( ) != vsDECL_FUNC_PORT_LIST )
      return OK;

    VeriFuncPortList * port_list
      = static_cast<VeriFuncPortList *>(_port_list);
    NodeList &tf_decl_list = port_list->func_port();

    NodeList::iterator idecl = tf_decl_list.begin();
    NodeList::iterator iport;

    VeriPrimaryExp *pexp = NULL;
    for( ; idecl != tf_decl_list.end(); ++idecl )
    {
      NodeList &port_ids = (static_cast<VeriTfDecl *>(*idecl))->port_ids();
      iport = port_ids.begin();
      for( ; iport != port_ids.end(); ++iport )
      {
        auto* port=*iport;
        pexp = static_cast<VeriPrimaryExp *>(port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port);
        if( pexp->var() == NULL && pexp->calc_value( ) == NULL )
        {
          veri_err->append_err( ERR_ERROR, this, vSEC_CALLER_PORT_NOT_COMPLETE );
          return vSEC_CALLER_PORT_NOT_COMPLETE;
        }
         _act_ports.push_back( pexp->var() );
        _act_port_num++;
      }
    }
  }
  else
  {
    if( _item_decl->detail_type( ) != vsDECL_FUNC_ITEM_DECL_LIST )
      return OK;

    VeriFuncItemDeclList * item_list
      = static_cast<VeriFuncItemDeclList *>(_item_decl);
    NodeList &decl_list = item_list->func_item();

    NodeList::iterator idecl = decl_list.begin();
    NodeList::iterator iport;

    VeriPrimaryExp *pexp = NULL;
    for( ; idecl != decl_list.end(); ++idecl )
    {
      if( (*idecl)->detail_type( ) == vsDECL_TF_DECL )
      {
        NodeList &port_ids = (static_cast<VeriTfDecl *>(*idecl))->port_ids();
        iport = port_ids.begin();
        for( ; iport != port_ids.end(); ++iport )
        {
          auto* port=*iport;
        pexp = static_cast<VeriPrimaryExp *>(port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port);
          if( pexp->var() == NULL && pexp->calc_value( ) == NULL )
          {
            veri_err->append_err( ERR_ERROR, this, vSEC_CALLER_PORT_NOT_COMPLETE );
            return vSEC_CALLER_PORT_NOT_COMPLETE;
          }
          _act_ports.push_back( pexp->var() );
          _act_port_num++;
        }
      }
    }
  }

  return OK;
}

/*
 *  exp and var should not be null, garanteed by caller
 */
int
VeriFuncDecl::check_type_ref( VeriExp *exp, VeriNode *port, int no_assign )
{
  int re = OK;

  VeriVar    * var      = NULL;
  VeriTfVar  * tfvar    = NULL;
  VeriParam  * param    = NULL;
  VeriInt    * int_var  = NULL;
  VeriGenVar * genvar   = NULL;

  VeriVar    * svar     = NULL;
  VeriParam  * sparam   = NULL;
  VeriTfVar  * stfvar   = NULL;
  VeriInt    * sint_var = NULL;
  VeriGenVar * sgenvar  = NULL;

  switch( port->tok_type( ) )
  {
    case vtVAR    : var     = static_cast<VeriVar    *>(port); break;
    case vtTFVAR  : tfvar   = static_cast<VeriTfVar  *>(port); break;
    case vtPARAM  : param   = static_cast<VeriParam  *>(port); break;
    case vtINT    : int_var = static_cast<VeriInt    *>(port); break;
    case vtGENVAR : genvar  = static_cast<VeriGenVar *>(port); break;
    default : return vSEC_CALLER_PORT_MISMATCH;
  }

  IVec dummy_dimen;

  switch( exp->detail_type( ) )
  {
    case veEXP_PRI :
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(exp);
      if( pexp->var( ) == NULL )
      {
        if( pexp->pri_type( ) == veNUM )
        {
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(), pexp->calc_value() );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
        }
        return OK;
        break;
      }

      switch( pexp->var()->tok_type( ) )
      {
        case vtVAR :
          svar = static_cast<VeriVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != svar->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( svar->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != svar->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && svar->range_depth( ) == 0 )
              {
                VeriNum *num = svar->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtTFVAR :
          stfvar = static_cast<VeriTfVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = stfvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtPARAM :
          sparam = static_cast<VeriParam *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sparam->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtINT :
          sint_var = static_cast<VeriInt *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != sint_var->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && sint_var->range_depth( ) == 0 )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( sint_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != sint_var->range_depth( ) )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE && sint_var->range_depth( ) == 0 )
              {
                VeriNum *num = sint_var->get_one_num( dummy_dimen, IS_TRUE, 0, 0 );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        case vtGENVAR :
          sgenvar = static_cast<VeriGenVar *>(pexp->var());
          switch( port->tok_type( ) )
          {
            case vtVAR :
              if( var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                param->set_val( num );
              }
              return OK;
              break;

            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( int_var->range_depth( ) != 0 )
              {
                veri_err->append_err( ERR_ERROR, this, vSEC_MOD_PORT_MISMATCH );
                return vSEC_MOD_PORT_MISMATCH;
              }
              else if( no_assign == IS_FALSE )
              {
                VeriNum *num = sgenvar->get_val( );
                veri_parser->insert_node( num );
                num->set_scope( exp->scope( ) );
                num->set_father( port );
                int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
              }
              return OK;
              break;
          }
          break;

        default:
          break;
      }
      break;
    }

    case veEXP_UNA :
    case veEXP_BIN :
    case veEXP_SIGN :
    case veEXP_UNSIGN :
    case veEXP_MCONCAT :
    {
      switch( port->tok_type( ) )
      {
        case vtVAR :
        {
          if( var->range_depth( ) == 0 )
          {
            return OK;
          }
          else
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          break;
        }

        case vtTFVAR :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            tfvar->set_val( num );
          }
          return OK;
          break;

        case vtPARAM :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            param->set_val( num );
          }
          return OK;
          break;
        
        case vtGENVAR :
          if( no_assign == IS_FALSE )
          {
            VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
            veri_parser->insert_node( num );
            num->set_father( tfvar );
            genvar->set_val( num );
          }
          return OK;
          break;

        case vtINT :
          if( var->range_depth( ) == 0 )
          {
            if( no_assign == IS_FALSE )
            {
              VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
              veri_parser->insert_node( num );
              num->set_father( tfvar );
              int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            }
            return OK;
          }
          else
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          break;

        default:
          return vSEC_CALLER_PORT_MISMATCH;
      }
      break;
    }

    case veEXP_ARRAY :
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(exp);
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(aexp->id());

      if( pexp->var() != NULL )
        return vSEC_CALLER_PORT_MISMATCH;

      switch( port->tok_type( ) )
      {
        case vtPARAM : case vtGENVAR :
          veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
          return vSEC_CALLER_PORT_MISMATCH;

        case vtVAR :
          if( aexp->range_depth( ) > var->range_depth( ) )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;
        
        case vtINT :
          if( aexp->range_depth( ) > int_var->range_depth( ) )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          else
          {
            if( no_assign == IS_FALSE )
            {
              VeriNum *num = new VeriNum( veri_parser->next_id(), exp->calc_value( ) );
              veri_parser->insert_node( num );
              num->set_father( tfvar );
              int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            }
            return OK;
          }
          break;
      }
      return OK;
      break;
    }

    case veEXP_NAMED_PARAM :
    {
      VeriNamedParamExp * nexp = static_cast<VeriNamedParamExp *>(exp);
      switch( port->tok_type( ) )
      {
        case vtVAR :
          if( var->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;

        case vtTFVAR :
          if( tfvar->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
         break;

        case vtPARAM :
          if( param->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
         break;
        
        case vtGENVAR :
          if( genvar->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;

        case vtINT :
          if( int_var->name( ) != nexp->ref() )
          {
            veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
            return vSEC_CALLER_PORT_MISMATCH;
          }
          return OK;
          break;
      }

      VeriExp *inner_exp = static_cast<VeriExp *>(nexp->port_exp());
      return check_type_ref( inner_exp, port, IS_FALSE );
      break;
    }

    case veEXP_CALLER :
    {
      VeriCallerExp *cexp = static_cast<VeriCallerExp *>(exp);
      if( cexp->call_type() == vtTASK_CALL )
      {
        veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
        return vSEC_CALLER_PORT_MISMATCH;
      }
      else
      {
        assert( cexp->hive()->detail_type() == vsDECL_FUNC_DECL );
        VeriFuncDecl *func = static_cast<VeriFuncDecl *>(cexp->hive());
        if( func->ret_value() != NULL )
        {
          VeriFunc *ret_value = func->ret_value();
          switch( port->tok_type( ) )
          {
            case vtVAR :
            {
              if( var->range_depth( ) == 0 )
              {
                return OK;
              }
              else
              {
                veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
                return vSEC_CALLER_PORT_MISMATCH;
              }
              break;
            }

            case vtTFVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                tfvar->set_val( num );
              }
              return OK;
              break;

            case vtPARAM :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                param->set_val( num );
              }
              return OK;
              break;
            
            case vtGENVAR :
              if( no_assign == IS_FALSE )
              {
                VeriNum *num = new VeriNum( veri_parser->next_id(),
                                            ret_value->get_val( ) );
                veri_parser->insert_node( num );
                num->set_father( tfvar );
                genvar->set_val( num );
              }
              return OK;
              break;

            case vtINT :
              if( var->range_depth( ) == 0 )
              {
                if( no_assign == IS_FALSE )
                {
                  VeriNum *num = new VeriNum( veri_parser->next_id(),
                                              ret_value->get_val( ) );
                  veri_parser->insert_node( num );
                  num->set_father( tfvar );
                  int_var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
                }
                return OK;
              }
              else
              {
                veri_err->append_err( ERR_ERROR, exp, vSEC_CALLER_PORT_MISMATCH );
                return vSEC_CALLER_PORT_MISMATCH;
              }
              break;

            default:
              return vSEC_CALLER_PORT_MISMATCH;
          }
        }
        else
        {
           veri_err->append_err( ERR_ERROR, exp, vSEC_FUNC_NO_RET );
           return vSEC_FUNC_NO_RET;
        }
      }
    }
    break;

    case veEXP_MINTY :
    {
      VeriMintypmaxExp *pmax = static_cast<VeriMintypmaxExp *>(exp);
      VeriExp *exp1 = static_cast<VeriExp *>(pmax->exp_child1( ) );
      VeriExp *exp2 = static_cast<VeriExp *>(pmax->exp_child2( ) );
      VeriExp *exp3 = static_cast<VeriExp *>(pmax->exp_child3( ) );

      re = check_type_ref( exp1, port, IS_TRUE );
      if( re != OK )
        return re;

      re = check_type_ref( exp2, port, IS_TRUE );
      if( re != OK )
        return re;
         
      return check_type_ref( exp3, port, IS_TRUE );
      break;
    }

    case veEXP_QUES :
    {
      VeriQuesExp *ques = static_cast<VeriQuesExp *>(exp);
      VeriExp  *choice  = static_cast<VeriExp *>(ques->choice ( ) );
      VeriExp  *choice1 = static_cast<VeriExp *>(ques->choice1( ) );
      VeriExp  *choice2 = static_cast<VeriExp *>(ques->choice2( ) );

      if( choice != NULL )
        return check_type_ref( choice, port, IS_FALSE );
      else
      {
        re = check_type_ref( choice1, port, IS_TRUE );
        if( re != OK )
          return re;
           
        return check_type_ref( choice2, port, IS_TRUE );
      }
      break;
    }

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(exp);
      NodeList & exp_list = mexp->exp();
      NodeList::iterator it = exp_list.begin();
      for( ; it != exp_list.end(); ++it )
      {
        re = check_type_ref( static_cast<VeriExp *>(*it), port, IS_TRUE );
        if( re != OK )
          return re;
      }
      return OK;
      break;
    }

    default:
      return OK;
      break;
  }
  return OK;
}


int
VeriFuncDecl::push_contents( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  if(_stmt) {
    _stmt->set_is_trash(IS_TRUE);_stmt->set_scope(scope());mstack.push_back(_stmt);
  }

  return OK;
}

int
VeriFuncDecl::finish_scope( void )
{
  scope()->finish_scope();
  return OK;
}

int
VeriFuncDecl::push_for_replacement( NodeVec& mstack )
{
  if(_type_expression)mstack.push_back(_type_expression);
  if( _range != NULL )
    mstack.push_back( _range );

  if( _port_list != NULL )
    mstack.push_back( _port_list );

  if( _item_decl != NULL )
    mstack.push_back( _item_decl );

  mstack.push_back( _stmt );

  if(extern_header())mstack.push_back(extern_header());
  return OK;
}

int
VeriFuncDecl::replace_node( Uint idx, NodeList& node_list,
                            NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncDecl *tmp = new VeriFuncDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl;
  if(extern_header()){--itl;tmp->set_extern_header(*itl);node_list.erase(itl);itl=inl;}

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _item_decl != NULL )
  {
    tmp->_item_decl = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _port_list != NULL )
  {
    tmp->_port_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _range != NULL )
  {
    tmp->_range = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  if(_type_expression){itl=inl;--itl;tmp->_type_expression=*itl;(*itl)->set_father(tmp);node_list.erase(itl);}
  *inl = tmp;
  return OK;
}

    /************************
     * Variable-Declaration *
     ************************/

void
VeriVarDecl::clean_up( void )
{
  _resolved_type=NULL;
  _declared_type=NULL;
  _forward_definition=nullptr;
  _forward_alias=nullptr;_completes_forward_alias=false;
  _type_override=nullptr;
  _enum_active=NULL;_enum_previous=NULL;_enum_values.clear();
  set_pstatus( vSTART_S );
}

int
VeriVarDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;

  if( _drive != NULL )
  {
    mqueue.push( _drive );
    iqueue.push( depth );
  }

  if( _range != NULL )
  {
    mqueue.push( _range );
    iqueue.push( depth );
  }

  if( _delay != NULL )
  {
    mqueue.push( _delay );
    iqueue.push( depth );
  }

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriVarDecl::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_in_out( _inout );
  ofile << dot_str_var_type( _net_type );
  ofile << dot_str_is_tf( "SIGNED", _is_signed );
  ofile << dot_str_vector_scalar( _vec_scalar );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _drive );
  ofile << dot_str_conn( idx(), _range );
  ofile << dot_str_conn( idx(), _delay );
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriVarDecl::check_child_validation( void )
{
  // Integral ports have fixed packed widths. Input variables are copied by
  // the compiler; variable inout ports remain invalid.
  if((veri_integral_atom(_net_type)&&_range)||(veri_two_state(_net_type)&&_inout==vpINOUT)||(_net_type==vvINT&&_inout==vpINOUT)||(_net_type==vvTIME&&_inout==vpINOUT)) {
    veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_VAR_DECL);
    return vCHILD_TYPE_VAR_DECL;
  }
  if(_net_type==vvREG&&(_inout==vpIN||_inout==vpINOUT)) {
    veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_VAR_DECL);
    return vCHILD_TYPE_VAR_DECL;
  }

  if( _drive != NULL )
  {
    if( _drive->detail_type() != veEXP_DRIVE )
    {
      veri_err->append_err( ERR_ERROR, _drive->line(),
                           _drive->col(), vCHILD_TYPE_VAR_DECL );
      return vCHILD_TYPE_VAR_DECL;
    }
  }

  if( _range != NULL )
  {
    if( _range->detail_type() != veEXP_RANGE )
    {
      veri_err->append_err( ERR_ERROR, _range->line(),
                           _range->col(), vCHILD_TYPE_VAR_DECL );
      return vCHILD_TYPE_VAR_DECL;
    }
  }

  if( _delay != NULL )
  {
    if( _delay->detail_type() != veEXP_DELAY )
    {
      veri_err->append_err( ERR_ERROR, _delay->line(),
                           _delay->col(), vCHILD_TYPE_VAR_DECL );
      return vCHILD_TYPE_VAR_DECL;
    }
  }

  return OK;
}

int
VeriVarDecl::check_last_child_validation( void )
{
  VeriNode * last = _vars.back();
  if(_net_type==vvEVENT&&last&&last->detail_type()!=veEXP_PRI)
    throw std::runtime_error("line "+std::to_string(line())+": event arrays and aliases/initializers are not supported yet");
  if( last != NULL )
  {
    switch( last->detail_type() )
    {
      case veEXP_PRI :
      case veEXP_ARRAY:
      case veEXP_ASSIGN :
        return OK;
        break;

      default:
        veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_VAR_DECL );
        return vCHILD_TYPE_VAR_DECL;
        break;
    }
  }

  veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_VAR_DECL );
  return vCHILD_TYPE_VAR_DECL;
}

int
VeriVarDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      _next_variable=_vars.begin();
      re = push_children( mstack );
      set_pstatus( vDECL_S );
      return re;
      break;

    case vDECL_S :
      if(sequential_variables()) {
        if(_next_variable==_vars.end())return OK;
        re=declare_var_symbols(*_next_variable);
        if(re!=OK)return re;
        if(++_next_variable!=_vars.end()) {
          mstack.push_back(this);push_variable(mstack,*_next_variable);
        }
        return OK;
      }
      if(!_declared_type) {
        re=declare_var_symbols();
        if(re!=OK)return re;
      }
      return is_enum()?process_enum_members(mstack):OK;
      break;

    case vENUM_VARS_S:
      // Enum labels must bind before any initializer. Variables in a single
      // declaration then bind in order, so a later initializer can use a prior
      // variable while every variable retains this declaration's type identity.
      if(_next_variable==_vars.end())return OK;
      re=declare_var_symbols(*_next_variable);
      if(re!=OK)return re;
      if(++_next_variable!=_vars.end()) {
        mstack.push_back(this);push_variable(mstack,*_next_variable);
      } else set_pstatus(vEND_S);
      return OK;

    default :
      return do_nothing( );
      break;
  }
}

int
VeriVarDecl::push_children( NodeVec& mstack )
{
  if(_type_override||_type_expression) {
    _resolved_type=_type_override?_type_override:static_cast<VeriTypeExp*>(_type_expression)->resolve(scope());
    _net_type=_resolved_type->net_type();_is_signed=_resolved_type->is_signed();_vec_scalar=_resolved_type->vec_scalar();
  } else if(_type_parameter) {
    throw std::runtime_error("missing class type parameter actual/default");
  } else if(named_type()) {
    auto* node=veri_resolve_type(scope(),_type_name);
    if(!node||node->tok_type()!=vtTYPE)
      throw std::runtime_error("line "+std::to_string(line())+": unknown integral type "+_type_name);
    _resolved_type=static_cast<VeriVar*>(node);
    _net_type=_resolved_type->net_type();_is_signed=_resolved_type->is_signed();_vec_scalar=_resolved_type->vec_scalar();
  }
  if(_net_type==vvSTRING&&(_range||(_packed_field&&!_unpacked_field)||is_enum()||_inout!=vpNO_IO))
    throw std::runtime_error("line "+std::to_string(line())+": string packed dimensions, packed fields, enum bases and module ports are not supported");
  if(_net_type==vvCHANDLE&&(_range||_packed_field||is_enum()||_inout!=vpNO_IO))
    throw std::runtime_error("chandle packed dimensions, packed fields, enum bases and module ports are not supported");
  if(veri_real(_net_type)&&(_range||_packed_field||is_enum()))
    throw std::runtime_error("real type cannot have packed dimensions, packed fields or enum base");
  if(is_enum()&&_resolved_type&&(_resolved_type->enum_type()||_resolved_type->aggregate_type()))
    throw std::runtime_error("line "+std::to_string(line())+": enum base must be an integral non-enum type");
  if(is_aggregate()) {
    auto* fields=scope()->append_scope("$packed"+std::to_string(idx()),vNAMED_BLOCK_SCOPE);
    mstack.push_back(this);
    for(auto it=_packed_members.rbegin();it!=_packed_members.rend();++it) {
      auto* decl=static_cast<VeriVarDecl*>(*it);decl->set_packed_field(_aggregate_kind==3);
      decl->set_scope(fields);mstack.push_back(decl);
    }
    return OK;
  }
  _enum_next=_enum_members.begin();_enum_active=NULL;_enum_previous=NULL;_enum_values.clear();
  mstack.push_back( this );

  if(sequential_variables()) {
    if(_next_variable!=_vars.end())push_variable(mstack,*_next_variable);
  } else if(!is_enum()||_is_typedef) {
    for(auto it=_vars.rbegin();it!=_vars.rend();++it)push_variable(mstack,*it);
  }

  if( _delay != NULL )
  {
    //_delay->clean_up( );
    _delay->set_is_trash( IS_TRUE );
    _delay->set_scope( scope() );
    mstack.push_back( _delay );
  }

  if( _range != NULL )
  {
    //_range->clean_up( );
    _range->set_is_trash( IS_TRUE );
    _range->set_scope( scope() );
    mstack.push_back( _range );
  }

  if( _drive != NULL )
  {
    //_drive->clean_up( );
    _drive->set_is_trash( IS_TRUE );
    _drive->set_scope( scope() );
    mstack.push_back( _drive );
  }

  return OK;
}

namespace {
bool defer_runtime_initializer(VeriNode* declaration,VeriNode* entry,VeriSeqBlock* type=nullptr) {
  if(entry->detail_type()!=veEXP_ASSIGN)return false;
  auto* list=declaration->father();
  if(!list||(list->detail_type()!=vsSTMT_MOD_ITEM_LIST&&list->detail_type()!=vsINST_GEN_ITEM_LIST))return false;
  auto* owner=list->father();
  const bool property=owner&&owner->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(owner)->class_declaration();
  if(property||type)return true;
  // Integral/string initializers can invoke forward classes too. Delay call
  // binding until declarations/signatures are ready, while retaining eager
  // constant initialization (including net declaration assignments).
  VeriNode::NodeVec pending{static_cast<VeriAssignExp*>(entry)->rval()};
  while(!pending.empty()) {
    auto* child=pending.back();pending.pop_back();
    if(child->detail_type()==veEXP_CALLER||child->detail_type()==veEXP_MEMBER)return true;
    child->push_for_replacement(pending);
  }
  return false;
}
}
void VeriVarDecl::push_variable(NodeVec& mstack,VeriNode* node) {
  // Resolve each declarator, then register it before analyzing the next RHS.
  node->set_is_decl(IS_TRUE);node->set_is_trash(IS_TRUE);node->set_scope(scope());
  static_cast<VeriExp*>(node)->set_signed(_is_signed);
  if(defer_runtime_initializer(this,node,_resolved_type?_resolved_type->class_type():nullptr)) {
    veri_parser->defer_semantic(node);
    auto* lhs=static_cast<VeriAssignExp*>(node)->lval();
    if(lhs->detail_type()==veEXP_ARRAY){lhs->set_is_decl(IS_TRUE);lhs->set_is_trash(IS_TRUE);lhs->set_scope(scope());mstack.push_back(lhs);}
  }
  else mstack.push_back(node);
}

VeriVar *
VeriVarDecl::reg_var_symbol( int line, int col, CString& name, short drive_from,
                             short drive_to, int dstart, int dend,
                             IList& range_from, IList& range_to,
                             VeriNode *decl, VeriNum **init, int total_cnt )
{
  // The symbol owns the pointer array only when a new symbol is created.
  // Individual numeric nodes are owned by the parser's node pool.
  std::unique_ptr<VeriNum*[]> pending_init(init);
  VeriNode * node = scope()->value_same_level( name );
  if( node != NULL )
  {
    switch( node->tok_type() )
    {
      case vtFUNC     : case vtTASK      :
      case vtMOD_INST : case vtGATE_INST :
        veri_err->append_err( ERR_ERROR, decl, vVAR_TFMG_REDEFINE );
        return NULL;
        break;

      case vtSYS_VAR  : case vtVAR : case vtPARAM :
      case vtGENVAR   : case vtINT : case vtTFVAR :
      {
        // Only legacy non-ANSI ports have a separate data declaration.
        // ANSI headers already declare the complete object. Merge at most once.
        if(node->tok_type()==vtVAR && birth_mod()->port() &&
           birth_mod()->port()->detail_type()!=vsDECL_PORT_DECL_LIST) {
          auto* existing=static_cast<VeriVar*>(node);
          const bool old_port=existing->inout()!=vpNO_IO,new_port=_inout!=vpNO_IO;
          if(old_port!=new_port && !existing->port_redeclared() &&
             decl->detail_type()!=veEXP_ASSIGN && existing->dstart()==dstart && existing->dend()==dend &&
             existing->range_depth()==int(range_from.size()) &&
             (_net_type==existing->net_type() ||
              ((_net_type==vvREG || existing->net_type()==vvREG) &&
               (old_port?existing->inout():_inout)==vpOUT))) {
            bool same=true;auto from=range_from.begin(),to=range_to.begin();
            for(int depth=1;depth<=existing->range_depth();++depth,++from,++to) {
              int first,last,bits;existing->get_range(depth,first,last,bits);
              if(first!=*from || last!=*to)same=false;
            }
            if(same) {
              if(new_port)existing->set_inout(_inout);
              if(_net_type==vvREG)existing->set_net_type(vvREG);
              existing->set_port_redeclared();return existing;
            }
          }
        }
        veri_err->append_err( ERR_ERROR, decl, vVAR_VAR_REDEFINE );
        return NULL;
        break;
      }

      default:
        veri_err->append_err( ERR_ERROR, decl, vVAR_UNKNOWN_REDEFINE );
        return NULL;
        break;
    }
  }

  VeriVar * var = new VeriVar( veri_parser->next_id(), line, col,
                               name, _inout, _net_type, _is_signed, _vec_scalar,
                               drive_from, drive_to, dstart, dend,
                               decl, init, total_cnt, birth_mod() );
  if(interface_port())var->set_interface_port(_interface_type,_interface_modport);
  pending_init.release();
  veri_parser->insert_node( var );

  var->set_father( this );
  var->set_scope( scope() );

  auto* array_decl=decl;
  if(array_decl->detail_type()==veEXP_ASSIGN)array_decl=static_cast<VeriAssignExp*>(array_decl)->lval();
  if(array_decl->detail_type()==veEXP_ARRAY) {
    const auto& ranges=static_cast<VeriArrayExp*>(array_decl)->range();
    if(!ranges.empty()) {
      auto* range=static_cast<VeriRangeExp*>(ranges.front());
      var->set_container(range->rtype(),range->rtype()==vrQUEUE&&range->right()?range->range_to():-1);
      var->set_associative_key_type(range->associative_key_type());
      bind_container_dimensions(var,ranges);
    }
  }
  IList::iterator irf = range_from.begin();
  IList::iterator irt = range_to.begin();

  for( ; irf != range_from.end(); ++irf, ++irt )
    var->add_range( *irf, *irt );

  append_type_ranges(var,_resolved_type);
  if(_resolved_type) {var->set_class_type_from(_resolved_type);var->set_enum_type(_resolved_type->enum_type());var->set_aggregate_type(_resolved_type->aggregate_type());}
  if(is_enum()&&!_is_typedef)var->set_enum_type(_declared_type);
  scope()->insert( name, var );
  return var;
}

int
VeriVarDecl::declare_var_symbols( VeriNode* declaration )
{
  short drive_from = DEFAULT_DRIVE_FROM;
  short drive_to   = DEFAULT_DRIVE_TO;
  int   dstart     = veri_type_width(_net_type)-1;
  int   dend       = RANGE_DEFAULT;
  if(_resolved_type) {dstart=_resolved_type->dstart();dend=_resolved_type->dend();}

  IList vec_range_from;
  IList vec_range_to;

  if( _drive != NULL )
  {
    VeriDriveExp *drive = static_cast<VeriDriveExp *>(_drive);
    drive_from = drive->drive_from( );
    drive_to   = drive->drive_to( );
  }

  if( _range != NULL )
  {
    VeriRangeExp *range = static_cast<VeriRangeExp *>(_range);
    dstart = range->range_from();
    dend   = range->range_to();
  }

  if(_is_typedef||_packed_field||is_enum()) {
    if(_range) {
      auto* range=static_cast<VeriRangeExp*>(_range);
      if(range->rtype()!=vrSEMI||!range->right())
        throw std::runtime_error("line "+std::to_string(line())+": typedef packed range requires two constant bounds");
      for(auto* bound:{range->left(),range->right()}) {
        auto value=veri_constant_value(static_cast<VeriExp*>(bound),0);
        bool valid=veri_elaboration_constant(bound)&&value&&value->no_xz()==IS_TRUE;
        if(valid) {
          const int sign=value->is_signed()==IS_TRUE?value->get_certain_bit(std::min(31,value->bits()-1)):V0;
          if(value->is_signed()!=IS_TRUE&&value->bits()>31&&value->get_certain_bit(31)!=V0)valid=false;
          for(int bit=32;bit<value->bits();++bit)if(value->get_certain_bit(bit)!=sign)valid=false;
        }
        if(!valid)throw std::runtime_error("line "+std::to_string(line())+": typedef bounds must be known integral constants within the signed 32-bit range");
      }
    }
    if(std::abs(int64_t(dstart)-dend)+1>1048576)
      throw std::runtime_error("line "+std::to_string(line())+": typedef packed range must contain 1..1048576 bits");
  }
  std::vector<VeriPackedField> layout;
  if(is_aggregate()) {
    layout=packed_layout();
    int width=0;bool two=true;
    for(const auto& f:layout) {width=std::max(width,f.offset+f.symbol->dlen());two=two&&veri_two_state(f.symbol->net_type());}
    dstart=width-1;dend=0;_vec_scalar=vpVECTOR;_net_type=two?vvBIT:vvLOGIC;
  }
  if(_is_typedef || (is_enum()&&!_declared_type)) {
    auto* declarator=_vars.front();
    auto* array=_is_typedef&&declarator->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(declarator):nullptr;
    auto* id=_is_typedef?static_cast<VeriPrimaryExp*>(array?array->id():declarator):nullptr;
    if(_forward_class&&!_forward_definition&&!_forward_alias)
      throw std::runtime_error("line "+std::to_string(line())+": forward class has no definition in the same scope: "+id->str());
    auto* previous=id?scope()->value_same_level(id->str()):nullptr;
    if(_forward_class&&previous&&previous->tok_type()==vtTYPE&&
       (_forward_alias?bool(static_cast<VeriVar*>(previous)->class_binding()):veri_class_type(previous)==_forward_definition)) {
      _declared_type=static_cast<VeriVar*>(previous);id->set_var(previous);return OK;
    }
    if(previous&&_completes_forward_alias&&previous->tok_type()==vtTYPE) {
      auto* prior=static_cast<VeriVar*>(previous);
      auto* declaration=prior->father();
      if(declaration&&declaration->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(declaration)->forward_class()) {
        if(!_resolved_type||array||_range||is_enum()||is_aggregate())
          throw std::runtime_error("forward class typedef requires a scalar class type");
        prior->complete_forward_class_type(_resolved_type);
        _declared_type=prior;id->set_var(prior);return OK;
      }
    }
    if(previous)
      throw std::runtime_error("line "+std::to_string(line())+": duplicate type or symbol "+id->str());
    auto* type=new VeriVar(veri_parser->next_id(),line(),col(),id?id->str():"",vpNO_IO,_net_type,_is_signed,_vec_scalar,
                          drive_from,drive_to,dstart,dend,this,NULL,0,birth_mod(),vtTYPE);
    veri_parser->insert_node(type);type->set_scope(scope());type->set_father(this);
    _declared_type=type;
    if(array) {
      auto last=array->range_to().begin();
      for(int first:array->range_from())type->add_range(first,*last++);
      if(!array->range().empty()) {
        auto* range=static_cast<VeriRangeExp*>(array->range().front());
        type->set_container(range->rtype(),range->rtype()==vrQUEUE&&range->right()?range->range_to():-1);
        type->set_associative_key_type(range->associative_key_type());
        bind_container_dimensions(type,array->range());
      }

    }
    append_type_ranges(type,_resolved_type);
    if(_resolved_type)type->set_class_type_from(_resolved_type);
    if(_forward_class) {
      if(_forward_definition)type->set_class_type(_forward_definition);
      else type->set_forward_class_type();
    }
    type->set_enum_type(is_enum()?type:_resolved_type?_resolved_type->enum_type():nullptr);
    type->set_aggregate_type(is_aggregate()?type:_resolved_type?_resolved_type->aggregate_type():nullptr);
    type->packed_fields()=std::move(layout);
    if(_aggregate_kind==3)type->set_unpacked_struct();
    if(id) {scope()->insert(id->str(),type);id->set_var(type);}
    // An anonymous identity is owned without a lookup name. Keep _resolved_type
    // as the base type: pointing it back at this declaration creates a cycle
    // when packed dimensions follow the declaration's base type chain.
    return OK;
  }

  int             total_cnt  = 1;
  VeriPrimaryExp *pri_exp    = NULL;
  VeriArrayExp   *array_exp  = NULL;
  VeriAssignExp  *assign_exp = NULL;
  VeriNum       **init       = NULL;
  VeriExp        *lval       = NULL;
  VeriExp        *rval       = NULL;
  VeriVar        *symbol     = NULL;

  IList::iterator iil;
  NodeList::iterator inl = _vars.begin();
  for( ; inl != _vars.end(); ++inl )
  {
    auto* entry=declaration?declaration:*inl;
    switch( entry->detail_type() )
    {
      case veEXP_PRI :
        pri_exp = static_cast<VeriPrimaryExp *>(entry);

        init = new VeriNum*[total_cnt];
        init[0] = new VeriNum( veri_parser->next_id(), pri_exp->line(),
                               pri_exp->col(), birth_mod());
        init[0]->init_val( _is_signed, abs(dend-dstart)+1 );

        init[0]->set_father( pri_exp );
        veri_parser->insert_node( init[0] );

        symbol = reg_var_symbol( entry->line(), entry->col(), pri_exp->str(),
                                  drive_from, drive_to, dstart, dend,
                                  vec_range_from, vec_range_to,
                                  entry, init, total_cnt );

        pri_exp->set_var( symbol );
        break;

      case veEXP_ARRAY :
      {
        array_exp = static_cast<VeriArrayExp *>(entry);
        if( array_exp->not_calc( ) == IS_TRUE )
        {
          veri_err->append_err( ERR_ERROR, array_exp, vSEC_VAR_RANGE_NOT_CALC );
          return vSEC_VAR_RANGE_NOT_CALC;
        }

        IList &irange_from = array_exp->range_from();
        IList &irange_to   = array_exp->range_to();
        IList::iterator iil = irange_from.begin();
        for( ; iil != irange_from.end(); ++iil )
          vec_range_from.push_back( *iil );
        for( iil = irange_to.begin(); iil != irange_to.end(); ++iil )
          vec_range_to.push_back( *iil );

        init = new VeriNum*[total_cnt];
        init[0] = new VeriNum( veri_parser->next_id(), array_exp->line(),
                               array_exp->col(), birth_mod());
        init[0]->init_val( _is_signed, abs(dend-dstart)+1 );
        init[0]->set_father( pri_exp );
        veri_parser->insert_node( init[0] );

        symbol = reg_var_symbol( entry->line(), entry->col(),
                                 array_exp->name(), drive_from, drive_to,
                                 dstart, dend, vec_range_from, vec_range_to,
                                 entry, init, total_cnt );
        pri_exp = static_cast<VeriPrimaryExp *>(array_exp->id());
        pri_exp->set_var( symbol );

        vec_range_from.clear();
        vec_range_to.clear();

        break;
      }

      case veEXP_ASSIGN :
        assign_exp = static_cast<VeriAssignExp *>(entry);
        lval = static_cast<VeriExp *>(assign_exp->lval());
        rval = static_cast<VeriExp *>(assign_exp->rval());

        if( lval->detail_type() == veEXP_PRI )
        {
          init = new VeriNum*[total_cnt];
          init[0] = new VeriNum( veri_parser->next_id(), rval->calc_value());
          init[0]->truncate_assign( abs(dend-dstart)+1 );
          init[0]->set_father( this );
          init[0]->set_scope( scope() );
          veri_parser->insert_node( init[0] );

          pri_exp = static_cast<VeriPrimaryExp *>(lval);
          symbol = reg_var_symbol( entry->line(), entry->col(),
                                    pri_exp->str(), 
                                    drive_from, drive_to, dstart, dend,
                                    vec_range_from, vec_range_to, entry,
                                    init, total_cnt );
          pri_exp->set_var( symbol );
          init = NULL;
        }
        else if( lval->detail_type( ) == veEXP_ARRAY )
        {
          array_exp = static_cast<VeriArrayExp *>(lval);
          if( array_exp->not_calc() == IS_TRUE )
          {
            veri_err->append_err( ERR_ERROR, array_exp,
                                  vSEC_VAR_RANGE_NOT_CALC );
            return vSEC_VAR_RANGE_NOT_CALC;
          }

          IList &irange_from = array_exp->range_from();
          IList &irange_to   = array_exp->range_to();
          IList::iterator iil = irange_from.begin();
          for( ; iil != irange_from.end(); ++iil )
            vec_range_from.push_back( *iil );
          for( iil = irange_to.begin(); iil != irange_to.end(); ++iil )
            vec_range_to.push_back( *iil );

          /* TODO: calculate total cnt for initialization */
          /* pseudo down heer */
          init = new VeriNum*[total_cnt];
          init[0] = new VeriNum( veri_parser->next_id(), rval->calc_value() );
          init[0]->set_father( this );
          init[0]->set_scope( scope() );
          veri_parser->insert_node( init[0] );

          symbol = reg_var_symbol( entry->line(), entry->col(),
                                    array_exp->name(),
                                    drive_from, drive_to, dstart, dend,
                                    vec_range_from, vec_range_to, entry,
                                    init, total_cnt );
          pri_exp = static_cast<VeriPrimaryExp *>(array_exp->id());
          pri_exp->set_var( symbol );

          init = NULL;
          total_cnt = 1;
          vec_range_from.clear();
          vec_range_to.clear();
        }
        break;

      default:
        break;
    }
    if(declaration)break;
  }
  return OK;
}

namespace {
// Unsized numbers/parameters may be range checked in the enum base. An
// explicitly sized expression wider than the base requires an explicit cast.
bool enum_unsized_value(VeriExp* e) {
  switch(e->detail_type()) {
    case veEXP_PRI: {
      auto* p=static_cast<VeriPrimaryExp*>(e);
      if(p->pri_type()==veNUM)return p->str().find('\'')==String::npos||p->str()[0]=='\'';
      return p->var()&&p->var()->tok_type()==vtPARAM;
    }
    case veEXP_UNA:return enum_unsized_value(static_cast<VeriExp*>(static_cast<VeriUnaryExp*>(e)->exp_child()));
    case veEXP_BIN: {
      auto* b=static_cast<VeriBinaryExp*>(e);
      if(veri_is_cast(b->op()))return false;
      return enum_unsized_value(static_cast<VeriExp*>(b->lval()))||enum_unsized_value(static_cast<VeriExp*>(b->rval()));
    }
    case veEXP_QUES: {
      auto* q=static_cast<VeriQuesExp*>(e);
      return enum_unsized_value(static_cast<VeriExp*>(q->choice1()))||enum_unsized_value(static_cast<VeriExp*>(q->choice2()));
    }
    default:return false;
  }
}
}

std::vector<VeriPackedField> VeriVarDecl::packed_layout() {
  std::vector<VeriPackedField> fields;int total=0,union_width=0;
  for(auto* node:_packed_members) {
    auto* decl=static_cast<VeriVarDecl*>(node);
    for(auto* field:decl->vars()) {
      if(field->detail_type()!=veEXP_PRI)
        throw std::runtime_error("line "+std::to_string(field->line())+": packed member must be a variable without initializer or unpacked dimensions");
      auto* id=static_cast<VeriPrimaryExp*>(field);
      auto* symbol=id->var()&&id->var()->tok_type()==vtVAR?static_cast<VeriVar*>(id->var()):nullptr;
      if(!symbol)throw std::runtime_error("packed member symbol is missing");
      if(_aggregate_kind!=3&&symbol->aggregate_type()&&symbol->aggregate_type()->unpacked_struct())
        throw std::runtime_error("unpacked struct cannot be a packed aggregate member");
      const int width=symbol->dlen();
      if(width<1||width>1048576||(_aggregate_kind!=2&&total>1048576-width))
        throw std::runtime_error("packed aggregate width must be within 1..1048576");
      if(_aggregate_kind==2&&union_width&&union_width!=width)
        throw std::runtime_error("packed union members must have equal widths");
      union_width=width;fields.push_back({id->str(),0,symbol});total+=_aggregate_kind!=2?width:0;
    }
  }
  if(fields.empty())throw std::runtime_error("packed aggregate must contain members");
  if(_aggregate_kind!=2)for(auto& f:fields){total-=f.symbol->dlen();f.offset=total;}
  return fields;
}

int VeriVarDecl::process_enum_members(NodeVec& mstack) {
  const int width=_declared_type->dlen();
  const bool sign=_is_signed==IS_TRUE;
  auto error=[&](const std::string& text) {
    throw std::runtime_error("line "+std::to_string(_enum_active?_enum_active->line():line())+": enum "+text);
  };
  if(_enum_active) {
    auto* member=_enum_active;
    auto* id=static_cast<VeriPrimaryExp*>(member->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(member)->lval():member);
    ParameterNumber value;
    if(member->detail_type()==veEXP_ASSIGN) {
      auto* expression=static_cast<VeriExp*>(static_cast<VeriAssignExp*>(member)->rval());
      if(!veri_elaboration_constant(expression))error("member requires an integral elaboration constant");
      auto natural=veri_constant_value(expression,0);
      if(!natural||natural->real_width())error("member requires an integral elaboration constant");
      const bool unsized=enum_unsized_value(expression);
      if(!unsized&&natural->bits()>width)error("sized member is wider than the base type");
      value=veri_constant_value(expression,width);
      if(!value)error("member requires an integral elaboration constant");
      const bool negative=natural->is_signed()==IS_TRUE&&natural->get_certain_bit(natural->bits()-1)==V1;
      // A signed initializer may be converted to an unsigned enum when its
      // full representation fits the base (e.g. int -1 into bit[31:0]).
      // Unsized negative values still cannot discard bits in a narrower base.
      if(negative&&!sign&&unsized&&natural->bits()>width)
        error("member is outside the unsigned base range");
      if(natural->no_xz()==IS_TRUE&&natural->bits()>width) {
        const int expected=negative?V1:V0;
        for(int bit=sign?width-1:width;bit<natural->bits();++bit)
          if(natural->get_certain_bit(bit)!=expected)error("member is outside the base range");
      }
      if(veri_two_state(_net_type)&&value->no_xz()!=IS_TRUE)error("two-state base cannot contain X/Z labels");
    } else {
      value=ParameterNumber(new VeriNum(0,line(),col(),birth_mod()));
      if(_enum_previous) {
        if(_enum_previous->no_xz()!=IS_TRUE)error("implicit member cannot follow X/Z");
        bool maximum=true;
        for(int bit=0;bit<width;++bit)
          if(_enum_previous->get_certain_bit(bit)!=(sign&&bit==width-1?V0:V1))maximum=false;
        if(maximum)error("implicit member overflows the base range");
        value=ParameterNumber(new VeriNum(0,_enum_previous));
        VeriNum one(0,line(),col(),birth_mod());const String text="1";
        one.parse(text.c_str(),text.size());
        if(value->binary_operation(vtBADD,&one)!=OK)error("implicit increment failed");
      } else {
        const String text="0";value->parse(text.c_str(),text.size());
      }
    }
    value->truncate_assign(width);
    if(sign)value->set_signed();else value->set_unsigned();
    String key;
    for(int bit=0;bit<width;++bit)key+=char('0'+value->get_certain_bit(bit));
    if(!_enum_values.insert(key).second)error("duplicate member value");
    if(scope()->value_same_level(id->str()))error("duplicate member or symbol "+id->str());
    auto* stored=new VeriNum(veri_parser->next_id(),value.get());
    veri_parser->insert_node(stored);stored->set_father(this);stored->set_scope(scope());
    auto* symbol=new VeriParam(veri_parser->next_id(),id->line(),id->col(),id->str(),100+_net_type,IS_TRUE,_is_signed,
                              member,_declared_type->dstart(),_declared_type->dend(),stored,birth_mod());
    symbol->set_enum_type(_declared_type);symbol->set_no_override();
    veri_parser->insert_node(symbol);symbol->set_scope(scope());symbol->set_father(this);
    scope()->insert(id->str(),symbol);id->set_var(symbol);
    _declared_type->enum_values().push_back(stored);
    _declared_type->enum_names().push_back(id->str());
    _enum_previous=stored;_enum_active=NULL;
  }
  if(_enum_next==_enum_members.end()) {
    set_pstatus(_is_typedef?vEND_S:vENUM_VARS_S);
    if(!_is_typedef&&_next_variable!=_vars.end()) {
      mstack.push_back(this);push_variable(mstack,*_next_variable);
    }
    return OK;
  }
  _enum_active=*_enum_next++;
  mstack.push_back(this);
  if(_enum_active->detail_type()==veEXP_ASSIGN) {
    auto* value=static_cast<VeriAssignExp*>(_enum_active)->rval();
    value->set_scope(scope());value->set_is_trash(IS_TRUE);mstack.push_back(value);
  }
  return OK;
}

int
VeriVarDecl::do_nothing( void )
{
  return OK;
}

int
VeriVarDecl::push_for_replacement( NodeVec& mstack )
{
  if(_type_expression)mstack.push_back(_type_expression);
  if( _drive != NULL )
    mstack.push_back( _drive );

  if( _range != NULL )
    mstack.push_back( _range );

  if( _delay != NULL )
    mstack.push_back( _delay );

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    mstack.push_back( *it );

  for(auto* member:_enum_members)mstack.push_back(member);
  for(auto* member:_packed_members)mstack.push_back(member);
  return OK;
}

int
VeriVarDecl::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriVarDecl *tmp = new VeriVarDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  for(auto* member:_packed_members) {
    (void)member;tmp->_packed_members.push_front(*(--itl));
    (*itl)->set_father(tmp);node_list.erase(itl);itl=inl;
  }
  for(auto* member:_enum_members) {
    (void)member;
    tmp->_enum_members.push_front(*(--itl));
    (*itl)->set_father(tmp);node_list.erase(itl);itl=inl;
  }

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    tmp->_vars.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _delay != NULL )
  {
    tmp->_delay = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _range != NULL )
  {
    tmp->_range = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _drive != NULL )
  {
    tmp->_drive = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  if(_type_expression) {
    itl=inl;--itl;tmp->_type_expression=*itl;(*itl)->set_father(tmp);node_list.erase(itl);
  }
  *inl = tmp;
  return OK;
}

    /*************************
     * Parameter-Declaration *
     *************************/

int VeriParamDecl::data_type() const {
  return _resolved_type?_resolved_type->net_type():_is_int==IS_TRUE?vvINT:_is_int>=100?_is_int-100:vvNONE;
}

void
VeriParamDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
  _resolved_type = nullptr;
  _class_arguments.clear();
  _active_param = NULL;
}

int
VeriParamDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  
  if( _range != NULL )
  {
    mqueue.push( _range );
    iqueue.push( depth );
  }

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriParamDecl::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_is_tf( "SIGNED", _is_signed );
  ofile << dot_str_is_tf( "INT", _is_int );
  ofile << dot_str_is_tf( "LOCAL", _is_local );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _range );
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriParamDecl::check_child_validation( void )
{
  if(veri_integral_atom(data_type())&&_range) {
    veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_PARAM_DECL);
    return vCHILD_TYPE_PARAM_DECL;
  }
  if( _range != NULL )
  {
    if( _range->detail_type() != veEXP_RANGE )
    {
      veri_err->append_err( ERR_ERROR, _range->line(),
                          _range->col(), vCHILD_TYPE_PARAM_DECL );
      return vCHILD_TYPE_PARAM_DECL;
    }
  }

  return OK;
}

int
VeriParamDecl::check_last_child_validation( void )
{
  VeriNode * last = _vars.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_PARAM_DECL );
    return vCHILD_TYPE_PARAM_DECL;
  }

  if( last->detail_type() != veEXP_ASSIGN )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_PARAM_DECL );
    return vCHILD_TYPE_PARAM_DECL;
  }
  return OK;
}

int
VeriParamDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vDECL_S );
      return re;
      break;

    case vDECL_S:
      if( _active_param != NULL )
      {
        re = declare_param_symbols();
        _active_param = NULL;
        if( re != OK ) return re;
      }
      if( _next_param == _vars.end() )
      {
        set_pstatus(vEND_S);
        return OK;
      }
      // Register each parameter before evaluating the next default, e.g.
      // parameter W=8, V=W+1. Overrides bypass the unused default expression.
      _active_param = *_next_param++;
      _active_param->set_is_decl(IS_TRUE);
      _active_param->set_is_trash(IS_TRUE);
      _active_param->set_scope(scope());
      static_cast<VeriExp *>(_active_param)->set_signed(_is_signed);
      mstack.push_back(this);
      if( override_expression(_active_param) == NULL )
        mstack.push_back(_active_param);
      return OK;

    default:
      return do_nothing( );
      break;
  }
}

int
VeriParamDecl::push_children( NodeVec& mstack )
{
  _resolved_type=signature_type(this,_type_name);
  if(_resolved_type)_is_signed=_resolved_type->is_signed();
  mstack.push_back( this );
  _active_param = NULL;
  _next_param = _vars.begin();

  if( _range != NULL )
  {
    //_range->clean_up( );
    _range->set_is_trash( IS_TRUE );
    _range->set_scope( scope() );
    mstack.push_back( _range );
  }

  return OK;
}

VeriExp *
VeriParamDecl::override_expression( VeriNode *node )
{
  if( _is_local == IS_TRUE )return NULL;
  auto* name=node->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp *>(node)->lval():node;
  if(name->detail_type()!=veEXP_PRI)return NULL;
  auto actual=_class_arguments.find(static_cast<VeriPrimaryExp *>(name)->str());
  if(actual!=_class_arguments.end())return actual->second;
  if(node->detail_type()!=veEXP_ASSIGN)return NULL;
  VeriNode* module = father();
  while( module != NULL && module->tok_type() != vtMOD )
    module = module->father();
  if( module == NULL ) return NULL;
  return static_cast<VeriMod *>(module)->parameter_override_expression(
    static_cast<VeriPrimaryExp *>(name)->str());
}

VeriNum *
VeriParamDecl::override_value( VeriNode *node ) {
  auto* expression=override_expression(node);
  return expression?expression->calc_value():NULL;
}

VeriParam *
VeriParamDecl::reg_param_symbol( int line, int col, VeriNode *decl,
                                 CString& name, int dstart, int dend,
                                 VeriNum  *init )
{
  VeriNode * node = scope()->value_same_level( name );
  if( node != NULL )
  {
    switch( node->tok_type() )
    {
      case vtPARAM:
      {
        VeriParam *tparam = static_cast<VeriParam *>(node);
        if( tparam->is_head_override() == IS_TRUE )
        {
          tparam->set_is_int( _is_int );
          tparam->set_is_local( _is_local );
          tparam->set_is_signed( _is_signed );
          tparam->set_dstart( dstart );
          tparam->set_dend( dend );
          tparam->set_dlen( abs(dend - dstart)+1 );
          tparam->set_val(init);
          tparam->set_father(this);
          return tparam;
        }
        else
        {
          veri_err->append_err( ERR_ERROR, decl, vPARAM_VAR_REDEFINE );
          return NULL;
        }
        break;
      }

      case vtFUNC     : case vtTASK      :
      case vtMOD_INST : case vtGATE_INST :
        veri_err->append_err( ERR_ERROR, decl, vPARAM_TFMG_REDEFINE );
        return NULL;
        break;

      case vtSYS_VAR  : case vtVAR : case vtTFVAR :
      case vtGENVAR   : case vtINT :
        veri_err->append_err( ERR_ERROR, decl, vPARAM_VAR_REDEFINE );
        return NULL;
        break;

      default:
        veri_err->append_err( ERR_ERROR, decl, vPARAM_UNKNOWN_REDEFINE );
        return NULL;
        break;
    }
  }

  VeriParam * param = new VeriParam( veri_parser->next_id(), line, col,
                                     name, _is_int, _is_local, init->is_signed(),
                                     decl, dstart, dend, init, birth_mod() );
  veri_parser->insert_node( param );
  param->set_father( this );
  param->set_scope( scope() );

  scope()->insert( name, param );
  return param;
}

int
VeriParamDecl::declare_param_symbols( void )
{
  int dstart = _resolved_type?_resolved_type->dstart():typed()?veri_type_width(data_type())-1:0;
  int dend   = _resolved_type?_resolved_type->dend():0;

  if( _range != NULL )
  {
    VeriRangeExp *range = static_cast<VeriRangeExp *>(_range);
    if(!veri_elaboration_constant(range->left())||!veri_elaboration_constant(range->right()))
      throw std::runtime_error("parameter packed range requires constant bounds");
    dstart = range->range_from();
    dend   = range->range_to();
  }

  VeriPrimaryExp *pexp = NULL;
  VeriAssignExp  *aexp = NULL;
  VeriExp        *rval = NULL;
  VeriNum        *init = NULL;
  VeriParam      *symbol = NULL;

  NodeList active(1, _active_param);
  NodeList::iterator inl = active.begin();
  for( ; inl != active.end(); ++inl )
  {
    if( (*inl)->detail_type() == veEXP_ASSIGN || (*inl)->detail_type() == veEXP_PRI )
    {
      aexp = (*inl)->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp *>(*inl):nullptr;
      auto* name=aexp?aexp->lval():*inl;
      rval = aexp?static_cast<VeriExp *>(aexp->rval()):override_expression(*inl);
      if(!rval)throw std::runtime_error("missing class parameter: "+static_cast<VeriPrimaryExp*>(name)->str());
      VeriNum *value = override_value(*inl);
      if( value == NULL ) value = rval->calc_value();

      auto* source=override_expression(*inl);
      if(!source)source=rval;
      // Concatenations have a dedicated constant evaluator and need not have
      // a legacy cached value. This also covers packed typed parameter defaults.
      if(    name->detail_type() == veEXP_PRI
          && (value != NULL || veri_elaboration_constant(source)) )
      {
        const int width=abs(dend-dstart)+1;
        auto evaluated=veri_constant_value(source,(_range||typed())&&data_type()!=vvSTRING?width:0);
        if(!evaluated) {
          veri_err->append_err(ERR_ERROR,rval,vCHILD_TYPE_PARAM_DECL);
          return vCHILD_TYPE_PARAM_DECL;
        }
        init = new VeriNum( veri_parser->next_id(), evaluated.get() );
        if(data_type()==vvSTRING) {
          if(!veri_string_value(source))throw std::runtime_error("string parameter initializer requires a string value or explicit cast");
          init->to_string_value();dstart=init->bits()-1;dend=0;
        } else if(evaluated->string_type()&&typed()) {
          throw std::runtime_error("string parameter value requires a string parameter type");
        } else if(veri_real(data_type())) {
          init->set_real(init->real_value(),veri_type_width(data_type()));
        } else if(_range||typed()) {
          init->truncate_assign(width);
          if(_is_signed==IS_TRUE)init->set_signed();else init->set_unsigned();
        } else { dstart=init->bits()-1;dend=0; if(_is_signed==IS_TRUE)init->set_signed(); }
        if(_resolved_type&&_resolved_type->enum_type()&&veri_enum_type(source)!=_resolved_type->enum_type())
          throw std::runtime_error("line "+std::to_string(source->line())+": enum parameter requires the same enum type or an explicit enum cast");
        if(veri_two_state(data_type()))init->to_two_state();
        init->set_father( this );
        init->set_scope( scope() );
        veri_parser->insert_node( init );

        pexp = static_cast<VeriPrimaryExp *>(name);
        symbol = reg_param_symbol( (*inl)->line(), (*inl)->col(), *inl,
                                   pexp->str(), dstart, dend, init );
        pexp->set_var( symbol );
        if( symbol == NULL ) return vPARAM_PARAM_REDEFINE;
        symbol->set_enum_type(_resolved_type?_resolved_type->enum_type():!typed()&&!_range?veri_enum_type(source):nullptr);

        init = NULL;
      }
      else
      {
        veri_err->append_err(ERR_ERROR, *inl, vSEC_MOD_PARAM_MISMATCH);
        return vSEC_MOD_PARAM_MISMATCH;
      }
    }
  }
  return OK;
}

int
VeriParamDecl::do_nothing( void )
{
  return OK;
}

int
VeriParamDecl::push_for_replacement( NodeVec& mstack )
{
  if( _range != NULL )
    mstack.push_back( _range );

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriParamDecl::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriParamDecl *tmp = new VeriParamDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    tmp->_vars.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _range != NULL )
  {
    tmp->_range = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /***********************
     * Integer-Declaration *
     ***********************/

void
VeriIntDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriIntDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;

  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriIntDecl::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriIntDecl::check_child_validation( void )
{
  return OK;
}

int
VeriIntDecl::check_last_child_validation( void )
{
  VeriNode * last = _vars.back();
  if( last != NULL )
  {
    switch( last->detail_type() )
    {
      case veEXP_PRI :
      case veEXP_ARRAY:
      case veEXP_ASSIGN :
        return OK;
        break;

      default:
        veri_err->append_err( ERR_ERROR, last->line(),
                              last->col(), vCHILD_TYPE_INT_DECL );
        return vCHILD_TYPE_INT_DECL;
        break;
    }
  }

  veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_INT_DECL );
  return vCHILD_TYPE_INT_DECL;
}

int
VeriIntDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  switch( pstatus() )
  {
    case vSTART_S:
      _next_variable = _vars.begin();
      set_pstatus( vDECL_S );
      return _next_variable == _vars.end() ? OK : push_children( mstack );
    case vDECL_S:
    {
      int re = declare_int_symbols( *_next_variable );
      if( re != OK ) return re;
      ++_next_variable;
      return _next_variable == _vars.end() ? OK : push_children( mstack );
    }
    default:
      return do_nothing();
  }
}

int
VeriIntDecl::push_children( NodeVec& mstack )
{
  // Analyze and register each declarator before the following initializer.
  mstack.push_back( this );
  VeriNode *node = *_next_variable;
  node->set_is_decl( IS_TRUE );
  node->set_is_trash( IS_TRUE );
  node->set_scope( scope() );
  if(defer_runtime_initializer(this,node)) {
    veri_parser->defer_semantic(node);
    auto* lhs=static_cast<VeriAssignExp*>(node)->lval();
    if(lhs->detail_type()==veEXP_ARRAY){lhs->set_is_decl(IS_TRUE);lhs->set_is_trash(IS_TRUE);lhs->set_scope(scope());mstack.push_back(lhs);}
  }
  else mstack.push_back(node);
  return OK;
}

VeriInt *
VeriIntDecl::reg_int_symbol( int line, int col, VeriNode *decl, CString& name,
                             IList& range_from, IList& range_to, VeriNum **init,
                             int total_cnt )
{
  std::unique_ptr<VeriNum*[]> pending_init(init);
  VeriNode * node = scope()->value_same_level( name );
  if( node != NULL )
  {
    switch( node->tok_type() )
    {
      case vtFUNC     : case vtTASK      :
      case vtMOD_INST : case vtGATE_INST :
        veri_err->append_err( ERR_ERROR, decl, vINT_TFMG_REDEFINE );
        return NULL;
        break;

      case vtSYS_VAR  : case vtVAR : case vtPARAM :
      case vtGENVAR   : case vtINT : case vtTFVAR :
        veri_err->append_err( ERR_ERROR, decl, vINT_VAR_REDEFINE );
        return NULL;
        break;

      default:
        veri_err->append_err( ERR_ERROR, decl, vINT_UNKNOWN_REDEFINE );
        return NULL;
        break;
    }
  }

  VeriInt * int_var = new VeriInt( veri_parser->next_id(), line, col,
                                   name, decl, init, total_cnt, birth_mod() );
  pending_init.release();
  int_var->set_father( this );
  int_var->set_scope( scope() );
  veri_parser->insert_node( int_var );

  auto* array_decl=decl;
  if(array_decl->detail_type()==veEXP_ASSIGN)array_decl=static_cast<VeriAssignExp*>(array_decl)->lval();
  if(array_decl->detail_type()==veEXP_ARRAY) {
    const auto& ranges=static_cast<VeriArrayExp*>(array_decl)->range();
    if(!ranges.empty()) {
      auto* range=static_cast<VeriRangeExp*>(ranges.front());
      int_var->set_container(range->rtype(),range->rtype()==vrQUEUE&&range->right()?range->range_to():-1);
        int_var->set_associative_key_type(range->associative_key_type());
      bind_container_dimensions(int_var,ranges);
    }
  }
  IList::iterator irf = range_from.begin();
  IList::iterator irt = range_to.begin();

  for( ; irf != range_from.end(); ++irf, ++irt )
    int_var->add_range( *irf, *irt );

  scope()->insert( name, int_var );
  return int_var;
}

int
VeriIntDecl::declare_int_symbols( VeriNode *declaration )
{
  IList vec_range_from;
  IList vec_range_to;

  VeriPrimaryExp *pri_exp    = NULL;
  VeriArrayExp   *array_exp  = NULL;
  VeriAssignExp  *assign_exp = NULL;
  VeriNum       **init       = NULL;
  VeriExp        *lval       = NULL;
  VeriExp        *rval       = NULL;
  VeriInt        *symbol     = NULL;

  IList::iterator iil;
  int total_cnt = 1;
  switch( declaration->detail_type() )
    {
      case veEXP_PRI :
        pri_exp = static_cast<VeriPrimaryExp *>(declaration);

        init = new VeriNum*[total_cnt];
        init[0] = new VeriNum( veri_parser->next_id(), pri_exp->line(),
                               pri_exp->col(), birth_mod());
        init[0]->init_val( IS_TRUE, 32 );
        init[0]->set_father( pri_exp );
        veri_parser->insert_node( init[0] );

        symbol = reg_int_symbol( declaration->line(), declaration->col(), declaration,
                                  pri_exp->str(), vec_range_from,
                                  vec_range_to, init, total_cnt );
        pri_exp->set_var( symbol );
        break;

      case veEXP_ARRAY :
      {
        array_exp = static_cast<VeriArrayExp *>(declaration);
        if( array_exp->not_calc() == IS_TRUE )
        {
          veri_err->append_err( ERR_ERROR, array_exp, vSEC_VAR_RANGE_NOT_CALC );
          return vSEC_VAR_RANGE_NOT_CALC;
        }

        IList &irange_from = array_exp->range_from();
        IList &irange_to   = array_exp->range_to();
        IList::iterator iil = irange_from.begin();
        for( ; iil != irange_from.end(); ++iil )
          vec_range_from.push_back( *iil );
        for( iil = irange_to.begin(); iil != irange_to.end(); ++iil )
          vec_range_to.push_back( *iil );

        init = new VeriNum*[total_cnt];
        init[0] = new VeriNum( veri_parser->next_id(), array_exp->line(),
                               array_exp->col(), birth_mod());
        init[0]->init_val( IS_TRUE, 32 );
        init[0]->set_father( pri_exp );
        veri_parser->insert_node( init[0] );

        symbol = reg_int_symbol( declaration->line(), declaration->col(),
                                 declaration, array_exp->name(),
                                 vec_range_from, vec_range_to,
                                 init, total_cnt );
        pri_exp = static_cast<VeriPrimaryExp *>(array_exp->id());
        pri_exp->set_var( symbol );

        vec_range_from.clear();
        vec_range_to.clear();

        break;
      }

      case veEXP_ASSIGN :
        assign_exp = static_cast<VeriAssignExp *>(declaration);
        lval = static_cast<VeriExp *>(assign_exp->lval());
        rval = static_cast<VeriExp *>(assign_exp->rval());

        if( lval->detail_type() == veEXP_PRI )
        {
          init = new VeriNum*[total_cnt];
          init[0] = new VeriNum( veri_parser->next_id(), rval->calc_value());
          if( !rval->calc_value() || rval->calc_value()->bits() == 0 )
            init[0]->init_val( IS_TRUE, 32 );
          else init[0]->truncate_assign( 32 );
          init[0]->set_father( this );
          veri_parser->insert_node( init[0] );

          pri_exp = static_cast<VeriPrimaryExp *>(lval);
          symbol = reg_int_symbol( declaration->line(), declaration->col(),
                                    declaration, pri_exp->str(),
                                    vec_range_from, vec_range_to,
                                    init, total_cnt );
          pri_exp->set_var( symbol );
          init = NULL;
        }
        else if( lval->detail_type( ) == veEXP_ARRAY )
        {
          array_exp = static_cast<VeriArrayExp *>(lval);
          if( array_exp->not_calc() == IS_TRUE )
          {
            veri_err->append_err( ERR_ERROR, array_exp,
                                  vSEC_VAR_RANGE_NOT_CALC );
            return vSEC_VAR_RANGE_NOT_CALC;
          }

          IList &irange_from = array_exp->range_from();
          IList &irange_to   = array_exp->range_to();
          IList::iterator iil = irange_from.begin();
          for( ; iil != irange_from.end(); ++iil )
            vec_range_from.push_back( *iil );
          for( iil = irange_to.begin(); iil != irange_to.end(); ++iil )
            vec_range_to.push_back( *iil );

          /* TODO: calculate total cnt for initialization */
          /* pseudo down heer */
          init = new VeriNum*[total_cnt];
          init[0] = new VeriNum( veri_parser->next_id(), rval->calc_value() );
          if( init[0]->bits() == 0 ) init[0]->init_val( IS_TRUE, 32 );
          init[0]->set_father( this );
          veri_parser->insert_node( init[0] );

          symbol = reg_int_symbol( declaration->line(), declaration->col(),
                                    declaration, array_exp->name(),
                                     vec_range_from, vec_range_to,
                                     init, total_cnt );
          pri_exp = static_cast<VeriPrimaryExp *>(array_exp->id());
          pri_exp->set_var( symbol );

          init = NULL;
          total_cnt = 1;
          vec_range_from.clear();
          vec_range_to.clear();
        }
        break;

      default:
        break;
    }
  return OK;
}

int
VeriIntDecl::do_nothing( void )
{
  return OK;
}

int
VeriIntDecl::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriIntDecl::replace_node( Uint idx, NodeList& node_list,
                           NodeList::iterator& inl)
{
  // spawn duplicant
  VeriIntDecl *tmp = new VeriIntDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    tmp->_vars.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /**********************
     * GenVar-Declaration *
     **********************/

void
VeriGenVarDecl::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenVarDecl::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriGenVarDecl::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriGenVarDecl::check_child_validation( void )
{
  return OK;
}

int
VeriGenVarDecl::check_last_child_validation( void )
{
  VeriNode * last = _vars.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GENVAR_DECL );
    return vCHILD_TYPE_GENVAR_DECL;
  }

  if(    last->detail_type() != veEXP_PRI
      && last->detail_type() != veEXP_ASSIGN )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_GENVAR_DECL );
    return vCHILD_TYPE_GENVAR_DECL;
  }
  return OK;
}

int
VeriGenVarDecl::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_children( mstack );
      set_pstatus( vDECL_S );
      return re;
      break;

    case vDECL_S:
      return declare_genvar_symbols( );
      break;

    default:
      return do_nothing( );
      break;
  }
}

int
VeriGenVarDecl::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _vars.rbegin();
  for( ; it != _vars.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }

  return OK;
}

VeriGenVar *
VeriGenVarDecl::reg_genvar_symbol( int line, int col, VeriNode *decl,
                                   CString& name, VeriNum *init )
{
  VeriNode * node = scope()->value_same_level( name );
  if( node != NULL )
  {
    switch( node->tok_type() )
    {
      case vtPARAM:
      {
        veri_err->append_err( ERR_ERROR, decl, vGENVAR_VAR_REDEFINE );
        return NULL;
        break;
      }

      case vtFUNC     : case vtTASK      :
      case vtMOD_INST : case vtGATE_INST :
        veri_err->append_err( ERR_ERROR, decl, vGENVAR_TFMG_REDEFINE );
        return NULL;
        break;

      case vtSYS_VAR  : case vtVAR : case vtTFVAR :
      case vtGENVAR   : case vtINT :
        veri_err->append_err( ERR_ERROR, decl, vGENVAR_VAR_REDEFINE );
        return NULL;
        break;

      default:
        veri_err->append_err( ERR_ERROR, decl, vGENVAR_UNKNOWN_REDEFINE );
        return NULL;
        break;
    }
  }

  VeriGenVar * genvar = new VeriGenVar( veri_parser->next_id(), line, col,
                                     name, decl, init, birth_mod() );
  genvar->set_father( this );
  genvar->set_scope( scope() );
  veri_parser->insert_node( genvar );
  scope()->insert( name, genvar );
  return genvar;
}

int
VeriGenVarDecl::declare_genvar_symbols( void )
{
  VeriPrimaryExp *pexp = NULL;
  VeriAssignExp  *aexp = NULL;
  VeriExp        *rval = NULL;
  VeriGenVar     *symbol = NULL;
  VeriNum        *init = NULL;

  NodeList::iterator inl = _vars.begin();
  for( ; inl != _vars.end(); ++inl )
  {
    if( (*inl)->detail_type() == veEXP_ASSIGN )
    {
      aexp = static_cast<VeriAssignExp *>(*inl);
      rval = static_cast<VeriExp *>(aexp->rval());

      if(    aexp->lval()->detail_type() == veEXP_PRI
          && rval->calc_value()  != NULL )
      {
        pexp = static_cast<VeriPrimaryExp *>(aexp->lval());

        init = new VeriNum( veri_parser->next_id(), rval->calc_value() );
        init->set_father( this );
        init->set_scope( scope() );
        veri_parser->insert_node( init );

        symbol = reg_genvar_symbol( (*inl)->line(), (*inl)->col(),
                                     *inl, pexp->str(), init );
        pexp->set_var( symbol );
      }
    }
    else if( (*inl)->detail_type() == veEXP_PRI )
    {
      pexp = static_cast<VeriPrimaryExp *>(*inl);

      init = new VeriNum( veri_parser->next_id(), pexp->line(), pexp->col(), birth_mod());
      init->init_val( IS_TRUE, 32 );
      init->set_father( pexp );
      veri_parser->insert_node( init );

      symbol = reg_genvar_symbol( (*inl)->line(), (*inl)->col(),
                                   *inl, pexp->str(), init );
      pexp->set_var( symbol );
    }
  }
  return OK;
}

int
VeriGenVarDecl::do_nothing( void )
{
  return OK;
}

int
VeriGenVarDecl::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriGenVarDecl::replace_node( Uint idx, NodeList& node_list,
                              NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenVarDecl *tmp = new VeriGenVarDecl( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  NodeList::iterator it = _vars.begin();
  for( ; it != _vars.end(); ++it )
  {
    tmp->_vars.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}


    /****************************************
     * Parameter-Declaration-List Statement *
     ****************************************/

void
VeriParamDeclList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriParamDeclList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _param_list.begin();
  for( ; it != _param_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriParamDeclList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _param_list.begin();
  for( ; it != _param_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriParamDeclList::check_child_validation( void )
{
  return OK;
}

int
VeriParamDeclList::check_last_child_validation( void )
{
  VeriNode * last = _param_list.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_PARAM_DECL_LIST );
    return vCHILD_TYPE_PARAM_DECL_LIST;
  }

  if( last->detail_type() != vsDECL_PARAM )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_PARAM_DECL_LIST );
    return vCHILD_TYPE_PARAM_DECL_LIST;
  }
  return OK;
}

int
VeriParamDeclList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriParamDeclList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _param_list.rbegin();
  for( ; it != _param_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriParamDeclList::do_nothing( void )
{
  return OK;
}

int
VeriParamDeclList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _param_list.begin();
  for( ; it != _param_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriParamDeclList::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriParamDeclList *tmp = new VeriParamDeclList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  NodeList::iterator it = _param_list.begin();
  for( ; it != _param_list.end(); ++it )
  {
    tmp->_param_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************************
     * Port-Declaration-List Statement *
     ****************************************/

void
VeriPortDeclList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriPortDeclList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front() + 1;
  NodeList::iterator it = _port_list.begin();
  for( ; it != _port_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriPortDeclList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _port_list.begin();
  for( ; it != _port_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriPortDeclList::check_child_validation( void )
{
  return OK;
}

int
VeriPortDeclList::check_last_child_validation( void )
{
  VeriNode * last = _port_list.back();
  if( last == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_PORT_DECL_LIST );
    return vCHILD_TYPE_PORT_DECL_LIST;
  }
   
  if( last->detail_type() != vsDECL_VAR )
  {
    veri_err->append_err( ERR_ERROR, last->line(),
                        last->col(), vCHILD_TYPE_PORT_DECL_LIST );
    return vCHILD_TYPE_PORT_DECL_LIST;
  }
  return OK;
}

int
VeriPortDeclList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriPortDeclList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _port_list.rbegin();
  for( ; it != _port_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriPortDeclList::do_nothing( void )
{
  return OK;
}

int
VeriPortDeclList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _port_list.begin();
  for( ; it != _port_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriPortDeclList::replace_node( Uint idx, NodeList& node_list,
                                     NodeList::iterator& inl)
{
  // spawn duplicant
  VeriPortDeclList *tmp = new VeriPortDeclList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 
  NodeList::iterator it = _port_list.begin();
  for( ; it != _port_list.end(); ++it )
  {
    tmp->_port_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

};


void rtl::VeriFuncDecl::adopt_extern_body(VeriFuncDecl* definition) {
  // Non-ANSI formal declarations belong to the signature. Keep them out of
  // the adopted local declarations because the prototype owns actual formals.
  if(!definition->_port_list&&definition->_item_decl&&definition->_item_decl->detail_type()==vsDECL_FUNC_ITEM_DECL_LIST) {
    auto& items=static_cast<VeriFuncItemDeclList*>(definition->_item_decl)->func_item();
    for(auto it=items.begin();it!=items.end();) {
      if((*it)->detail_type()!=vsDECL_TF_DECL){++it;continue;}
      definition->_port_list=definition->_port_list?veri_parser->append_fp_list(definition->_port_list,*it):veri_parser->gen_fp_list(*it);
      it=items.erase(it);
    }
    if(items.empty())definition->_item_decl=nullptr;
  }
  _stmt=definition->_stmt;_item_decl=definition->_item_decl;
  definition->_stmt=veri_parser->gen_dummy_stmt(definition->line(),definition->col());definition->_item_decl=nullptr;
  if(_stmt)_stmt->set_father(this);if(_item_decl)_item_decl->set_father(this);
  set_extern_header(definition);
}
void rtl::VeriTaskDecl::adopt_extern_body(VeriTaskDecl* definition) {
  // Non-ANSI formal declarations belong to the signature. Keep them out of
  // the adopted local declarations because the prototype owns actual formals.
  if(!definition->_task_port&&definition->_item_decl&&definition->_item_decl->detail_type()==vsDECL_TASK_ITEM_DECL_LIST) {
    auto& items=static_cast<VeriTaskItemDeclList*>(definition->_item_decl)->task_item();
    for(auto it=items.begin();it!=items.end();) {
      if((*it)->detail_type()!=vsDECL_TF_DECL){++it;continue;}
      definition->_task_port=definition->_task_port?veri_parser->append_tp_list(definition->_task_port,*it):veri_parser->gen_tp_list(*it);
      it=items.erase(it);
    }
    if(items.empty())definition->_item_decl=nullptr;
  }
  _stmt=definition->_stmt;_item_decl=definition->_item_decl;
  definition->_stmt=veri_parser->gen_dummy_stmt(definition->line(),definition->col());definition->_item_decl=nullptr;
  if(_stmt)_stmt->set_father(this);if(_item_decl)_item_decl->set_father(this);
  set_extern_header(definition);
}
