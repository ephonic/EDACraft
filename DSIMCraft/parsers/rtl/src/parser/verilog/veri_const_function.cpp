// Bounded, side-effect-free interpretation for integral constant functions.
// Runtime symbol values are never used as an elaboration-time environment.
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_num.hpp"
#include "veri_tfmg.hpp"
#include "veri_var.hpp"
#include "veri_symbol_table.hpp"
#include <algorithm>
#include <map>
#include <memory>
namespace rtl {
namespace {
using Number=std::unique_ptr<VeriNum>;
Number copy(const VeriNum* n) {return n?Number(new VeriNum(0,n)):Number();}
// Packed width is not a type test: handles, null and unpacked values have
// runtime semantics even when the surrounding comparison returns one bit.
bool integral_domain(VeriNode* n) {
  if(!n||veri_string_value(n)||veri_class_type(n)||veri_chandle_value(n)||veri_real_width(n))return false;
  if(n->tok_type()==vtEXP) {
    if(n->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(n)->multi_type()==vemNULL)return false;
    if(n->detail_type()==veEXP_BIN) {
      auto* b=static_cast<VeriBinaryExp*>(n);
      if(!integral_domain(b->lval())||!integral_domain(b->rval()))return false;
    }
    if(n->detail_type()==veEXP_QUES) {
      auto* q=static_cast<VeriQuesExp*>(n);
      if(!integral_domain(q->ques())||!integral_domain(q->choice1())||!integral_domain(q->choice2()))return false;
    }
  }
  return !veri_array_shape(n).unpacked;
}
struct ConstantFunction {
  std::map<VeriNode*,Number> locals;
  VeriNode* result=nullptr;
  unsigned budget=100000;
  bool returned=false,valid=true;
  bool tick(){if(!budget){valid=false;return false;}--budget;return true;}
  Number resize(Number n,int width,bool sign) {
    if(n){if(sign)n->set_signed();else n->set_unsigned();n->truncate_assign(width);}return n;
  }
  Number value(VeriNode* n,int context=0,int signed_context=-1) {
    if(!n||!tick()||n->tok_type()!=vtEXP||!integral_domain(n))return {};
    if(n->detail_type()!=veEXP_PRI&&n->detail_type()!=veEXP_UNA&&n->detail_type()!=veEXP_BIN&&n->detail_type()!=veEXP_QUES)return {};
    auto* exp=static_cast<VeriExp*>(n);int width=std::max(context,veri_bit_width(n));
    if(width<1||width>1048576)return {};
    bool sign=exp->is_signed()==IS_TRUE&&signed_context!=0;
    switch(n->detail_type()) {
      case veEXP_PRI: {
        auto* p=static_cast<VeriPrimaryExp*>(n);
        if(p->pri_type()==veNUM)return veri_constant_value(p,context,signed_context);
        auto found=locals.find(p->var());
        if(found!=locals.end())return resize(copy(found->second.get()),width,sign);
        if(p->var()&&(p->var()->tok_type()==vtPARAM||p->var()->tok_type()==vtGENVAR))
          return veri_constant_value(p,context,signed_context);
        return {};
      }
      case veEXP_UNA: {
        auto* u=static_cast<VeriUnaryExp*>(n);int op=u->op();
        // Sampled/random/system calls cannot observe runtime state here.
        if(veri_is_system_unary(op))return {};
        const bool reduce=op!=vtUADD&&op!=vtUSUB&&op!=vtUNEG;
        auto a=value(u->exp_child(),reduce?0:width,reduce?-1:int(sign));
        if(!a||a->unary_operation(op)!=OK)return {};
        return resize(std::move(a),width,sign);
      }
      case veEXP_BIN: {
        auto* b=static_cast<VeriBinaryExp*>(n);int op=b->op();
        bool comparison=(op>=vtBLT&&op<=vtBCIEQ)||op==vtBWLEQ||op==vtBWLNEQ;
        bool logical=op==vtBDAND||op==vtBDOR,shift=op>=vtBLRS&&op<=vtBALS,power=op==vtBPOW;
        int operands=comparison?std::max(veri_bit_width(b->lval()),veri_bit_width(b->rval())):width;
        bool operand_sign=comparison?(static_cast<VeriExp*>(b->lval())->is_signed()==IS_TRUE&&static_cast<VeriExp*>(b->rval())->is_signed()==IS_TRUE):sign;
        auto a=value(b->lval(),logical?0:operands,logical?-1:int(operand_sign));
        auto c=value(b->rval(),logical||shift||power?0:operands,logical||shift||power?-1:int(operand_sign));
        if(!a||!c||a->binary_operation(op,c.get())!=OK)return {};
        return resize(std::move(a),width,sign);
      }
      case veEXP_QUES: {
        auto* q=static_cast<VeriQuesExp*>(n);auto condition=value(q->ques());if(!condition)return {};
        condition->unary_operation(vtUOR);int bit=condition->get_certain_bit(0);
        if(bit==V1)return value(q->choice1(),width,int(sign));
        if(bit==V0)return value(q->choice2(),width,int(sign));
        return {};
      }
      default:return {};
    }
  }
  void declare(VeriNode* node) {
    if(!node||!valid)return;
    switch(node->detail_type()) {
      case vsDECL_FUNC_PORT_LIST:for(auto* p:static_cast<VeriFuncPortList*>(node)->func_port())declare(p);return;
      case vsDECL_FUNC_ITEM_DECL_LIST:for(auto* p:static_cast<VeriFuncItemDeclList*>(node)->func_item())declare(p);return;
      case vsDECL_BLOCK_ITEM_DECL_LIST:for(auto* p:static_cast<VeriBlockItemDeclList*>(node)->block_item())declare(p);return;
      case vsDECL_TF_DECL: {
        auto* d=static_cast<VeriTfDecl*>(node);
        for(auto* p:d->port_ids()) {
          auto* symbol=veri_formal_symbol(p);
          if(!integral_domain(symbol)||symbol->tok_type()!=vtTFVAR||static_cast<VeriTfVar*>(symbol)->range_depth()||static_cast<VeriTfVar*>(symbol)->inout()!=vpIN){valid=false;return;}
          locals.emplace(symbol,Number());
        }
        return;
      }
      case vsDECL_VAR:case vsDECL_INT: {
        auto& variables=node->detail_type()==vsDECL_VAR?static_cast<VeriVarDecl*>(node)->vars():static_cast<VeriIntDecl*>(node)->vars();
        for(auto* p:variables) {
          auto* lhs=p->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(p)->lval():p;
          if(lhs->detail_type()!=veEXP_PRI){valid=false;return;}
          auto* symbol=static_cast<VeriPrimaryExp*>(lhs)->var();
          if(!integral_domain(symbol)){valid=false;return;}
          locals.emplace(symbol,Number());
          if(p->detail_type()==veEXP_ASSIGN)store(lhs,static_cast<VeriAssignExp*>(p)->rval());
        }
        return;
      }
      case vsDECL_PARAM:return;
      default:valid=false;
    }
  }
  void store(VeriNode* target,VeriNode* rhs) {
    if(!target||target->detail_type()!=veEXP_PRI||!integral_domain(target)){valid=false;return;}
    auto* symbol=static_cast<VeriPrimaryExp*>(target)->var();auto found=locals.find(symbol);
    if(found==locals.end()){valid=false;return;} // No writes outside this call.
    auto n=value(rhs,veri_bit_width(target));if(!n){valid=false;return;}found->second=std::move(n);
  }
  void execute(VeriNode* n) {
    if(!n||!valid||returned||!tick())return;
    switch(n->detail_type()) {
      case vsSTMT_DUMMY:return;
      case veEXP_ASSIGN:store(static_cast<VeriAssignExp*>(n)->lval(),static_cast<VeriAssignExp*>(n)->rval());return;
      case vsSTMT_BLOCKING: {auto* b=static_cast<VeriBlockStmt*>(n);if(b->event()){valid=false;return;}store(b->lval(),b->rval());return;}
      case vsSTMT_STMT_LIST:for(auto* p:static_cast<VeriStmtList*>(n)->stmt_list())execute(p);return;
      case vsSTMT_SEQ_BLOCK: {auto* b=static_cast<VeriSeqBlock*>(n);declare(b->decl_list());execute(b->stmt_list());return;}
      case vsSTMT_COND: {
        auto* c=static_cast<VeriCondStmt*>(n);auto cond=value(c->if_exp());if(!cond){valid=false;return;}
        cond->unary_operation(vtUOR);execute(cond->get_certain_bit(0)==V1?c->if_stmt():c->else_stmt());return;
      }
      case vsSTMT_LOOP: {
        auto* loop=static_cast<VeriLoopStmt*>(n);
        if(loop->kind()!=VeriLoopStmt::FOR&&loop->kind()!=VeriLoopStmt::WHILE&&loop->kind()!=VeriLoopStmt::DO_WHILE){valid=false;return;}
        if(loop->kind()==VeriLoopStmt::FOR)execute(loop->init());
        bool first=true;
        while(valid&&!returned&&tick()) {
          if(!(first&&loop->kind()==VeriLoopStmt::DO_WHILE)&&loop->judge()) {
            auto condition=value(loop->judge());if(!condition){valid=false;return;}
            condition->unary_operation(vtUOR);if(condition->get_certain_bit(0)!=V1)break;
          }
          first=false;execute(loop->content());if(loop->kind()==VeriLoopStmt::FOR)execute(loop->iter());
        }
        return;
      }
      case vsSTMT_UPDATE: {
        auto* update=static_cast<VeriUpdateStmt*>(n);auto* target=update->target();
        if(target->detail_type()!=veEXP_PRI){valid=false;return;}
        auto found=locals.find(static_cast<VeriPrimaryExp*>(target)->var());
        if(found==locals.end()||!found->second){valid=false;return;}
        VeriNum one(0,0,0,n->birth_mod());one.parse("32'd1",5);
        found->second->binary_operation(update->delta()>0?vtBADD:vtBSUB,&one);return;
      }
      case vsSTMT_RETURN: {
        auto* action=static_cast<VeriActionStmt*>(n);
        auto v=value(action->value(),veri_bit_width(result));if(!v){valid=false;return;}
        locals[result]=std::move(v);returned=true;return;
      }
      default:valid=false;return;
    }
  }
};
}
std::unique_ptr<VeriNum> veri_constant_function(VeriCallerExp* call) {
  
  if(!call->hive()||call->hive()->detail_type()!=vsDECL_FUNC_DECL)return {};
  auto* declaration=static_cast<VeriFuncDecl*>(call->hive());if(declaration->is_void()||declaration->result_type()==vvSTRING||declaration->result_type()==vvCHANDLE)return {};
  auto* result=declaration->scope()->value_within_module(declaration->func_name());
  if(!integral_domain(result))return {};
  ConstantFunction evaluator;evaluator.declare(declaration->port_list());evaluator.declare(declaration->item_decl());
  if(!evaluator.valid){return {};}
  std::vector<VeriNode*> formals;
  // Preserve declaration order, independent of symbol pointer ordering.
  auto collect=[&](VeriNode* list) {
    if(!list||list->detail_type()!=vsDECL_FUNC_PORT_LIST)return;
    for(auto* d:static_cast<VeriFuncPortList*>(list)->func_port())if(d->detail_type()==vsDECL_TF_DECL)
      for(auto* p:static_cast<VeriTfDecl*>(d)->port_ids())formals.push_back(p);
  };
  collect(declaration->port_list());
  if(!declaration->port_list()&&declaration->item_decl())
    for(auto* d:static_cast<VeriFuncItemDeclList*>(declaration->item_decl())->func_item())if(d->detail_type()==vsDECL_TF_DECL)
      for(auto* p:static_cast<VeriTfDecl*>(d)->port_ids())formals.push_back(p);
  auto arguments=veri_bind_arguments(call,formals);
  for(size_t i=0;i<arguments.size();++i) {
    if(!veri_elaboration_constant(arguments[i].value)){return {};}
    auto n=veri_constant_value(static_cast<VeriExp*>(arguments[i].value),veri_bit_width(veri_formal_symbol(formals[i])));
    if(!n){return {};}evaluator.locals[veri_formal_symbol(formals[i])]=std::move(n);
  }
  evaluator.result=result;
  evaluator.locals.emplace(evaluator.result,Number());evaluator.execute(declaration->stmt());
  if(!evaluator.valid)return {};
  auto found=evaluator.locals.find(evaluator.result);return found==evaluator.locals.end()?Number():std::move(found->second);
}
}
