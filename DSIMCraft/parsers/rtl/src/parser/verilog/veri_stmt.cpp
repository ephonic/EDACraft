/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_stmt.cpp
 * Summary  : verilog syntax analyzer :: statement
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */
#include <assert.h>
#include <map>
#include <set>

#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_symbol_table.hpp"

#include "veri_num.hpp"
#include "veri_exp.hpp"
#include "veri_stmt.hpp"
#include "veri_decl.hpp"

#include "veri_tfmg.hpp"

#include "veri_module.hpp"
#include "veri_parser.hpp"

namespace rtl
{

VeriCondStmt* veri_sequence_definition(VeriNode* node) {
  if(node&&node->detail_type()==vsSTMT_ALWAYS)node=static_cast<VeriAlwaysStmt*>(node)->stmt();
  if(!node||node->detail_type()!=vsSTMT_COND)return nullptr;
  auto* sequence=static_cast<VeriCondStmt*>(node);
  return sequence->assertion_kind()==8?sequence:nullptr;
}
bool veri_sequence_term(VeriNode* node) {
  auto* parent=node->father();
  return parent&&parent->detail_type()==vsSTMT_COND&&
    static_cast<VeriCondStmt*>(parent)->property_term()&&static_cast<VeriCondStmt*>(parent)->if_exp()==node;
}
void veri_register_sequences(const VeriNode::NodeList& items,VeriSymbolTable* symbols) {
  for(auto* item:items)if(auto* sequence=veri_sequence_definition(item)) {
    const auto& name=sequence->property_name();
    if(auto* previous=symbols->value_same_level(name))
      throw std::runtime_error((veri_sequence_definition(previous)?"duplicate sequence: ":"sequence conflicts with local declaration: ")+name);
    if(symbols->insert(name,sequence)!=OK)throw std::runtime_error("cannot declare sequence: "+name);
  }
}
void veri_bind_forward_classes(const VeriNode::NodeList& items) {
  // Non-owning edges are rebuilt from this lexical list after every clone.
  std::map<std::string,VeriSeqBlock*> definitions;
  for(auto* item:items)if(item->detail_type()==vsSTMT_SEQ_BLOCK) {
    auto* definition=static_cast<VeriSeqBlock*>(item);
    if(definition->class_declaration()&&!definitions.emplace(definition->label(),definition).second)
      throw std::runtime_error("duplicate class declaration: "+definition->label());
  }
  std::map<std::string,VeriVarDecl*> aliases;
  for(auto* item:items)if(item->detail_type()==vsDECL_VAR) {
    auto* declaration=static_cast<VeriVarDecl*>(item);
    declaration->set_completes_forward_alias(false);
    if(!declaration->is_typedef()||declaration->forward_class())continue;
    auto* name=declaration->vars().front();
    if(name->detail_type()==veEXP_ARRAY)name=static_cast<VeriArrayExp*>(name)->id();
    aliases.emplace(static_cast<VeriPrimaryExp*>(name)->str(),declaration);
  }
  for(auto* item:items)if(item->detail_type()==vsDECL_VAR) {
    auto* declaration=static_cast<VeriVarDecl*>(item);
    if(!declaration->forward_class())continue;
    const auto& name=static_cast<VeriPrimaryExp*>(declaration->vars().front())->str();
    auto found=definitions.find(name);
    declaration->bind_forward_class(found==definitions.end()?nullptr:found->second);
    auto alias=aliases.find(name);
    auto* target=found==definitions.end()&&alias!=aliases.end()?alias->second:nullptr;
    declaration->bind_forward_alias(target);
    if(target)target->set_completes_forward_alias(true);
  }
}

int VeriImportStmt::process_node_2nd(NodeVec&,String&) {
  if(detail_type()==vsDECL_EXPORT) {
    if(!birth_mod()||!birth_mod()->is_package()||scope()!=birth_mod()->scope())
      throw std::runtime_error("export declarations require package scope");
    scope()->export_package(_package,_member);
    for(const auto& extra:_additional)scope()->export_package(extra.first,extra.second);
    set_pstatus(vEND_S);return OK;
  }
  auto bind=[&](const String& name,const String& member) {
    auto* package=veri_parser->package(name);
    if(!package||!package->scope())throw std::runtime_error("line "+std::to_string(line())+": unknown or not yet declared package in import: "+name);
    if(package==birth_mod())throw std::runtime_error("package cannot import itself: "+name);
    scope()->import_package(package->scope(),member);
  };
  bind(_package,_member);for(const auto& extra:_additional)bind(extra.first,extra.second);
  set_pstatus(vEND_S);return OK;
}

int
VeriStmt::check_func_child_exp_validation( VeriNode *child, int flag )
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
        veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
        return flag;

      case veEXP_CALLER :
      {
        /* task caller shall not be here */;
        VeriCallerExp *cexp = static_cast<VeriCallerExp *>(child);
        if( cexp->call_type() == vtTASK_CALL )
        {
          veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
          return flag;
        }
        break;
      }

      case veEXP_MINTY :
        veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
        return flag;
        break;

      case veEXP_MULTI :
      {
        VeriMultiExp *mexp = static_cast<VeriMultiExp *>(child);
        if( mexp->multi_type() != vemCONCAT_EXP && mexp->multi_type() != vemDYNAMIC_NEW && mexp->multi_type() != vemASSIGN_PATTERN && mexp->multi_type() != vemOBJECT_NEW && mexp->multi_type() != vemNULL )
        {
          veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
          return flag;
        }
        break;
      }

      default:
        break;
    }
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), flag );
  return flag;
}

int
VeriStmt::check_child_stmt( VeriNode * child, int flag )
{
  if( child != NULL && child->tok_type() == vtSTMT )
  {
    VeriStmt *stmt = static_cast<VeriStmt *>(child);

    if( stmt->func_task_flag() == vsBOTH || func_task_flag() == vsBOTH )
      return OK;

    if( stmt->func_task_flag() == func_task_flag() )
      return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), flag );
  return flag;
}

    /*******************
     * Dummy-Statement *
     *******************/

void
VeriDummyStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriDummyStmt::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriDummyStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriDummyStmt::check_child_validation( void )
{
  return OK;
}

int
VeriDummyStmt::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriDummyStmt::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriDummyStmt::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDummyStmt *tmp = new VeriDummyStmt( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

int VeriActionStmt::check_child_validation() {
  if((!_target||_target->tok_type()==vtEXP)&&(!_value||_value->tok_type()==vtEXP))return OK;
  veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_LOOP_STMT);return vCHILD_TYPE_LOOP_STMT;
}
int VeriActionStmt::push_dot_children(NodeQueue& nodes,IQueue& depths) {
  for(auto* child:{_target,_value})if(child){nodes.push(child);depths.push(depths.front()+1);}return OK;
}
int VeriActionStmt::pretty_dot_label(Ofstream& out,int depth) {
  out<<dot_str_rank(idx(),depth)<<dot_str_head(idx())<<dot_str_tok_type(tok_type())
     <<dot_str_detail_type(detail_type())<<dot_str_tail(tok_type());
  if(_target)out<<dot_str_conn(idx(),_target);if(_value)out<<dot_str_conn(idx(),_value);return OK;
}
int VeriActionStmt::process_node_2nd(NodeVec& stack,String&) {
  for(auto* child:{_value,_target})if(child){child->set_scope(scope());stack.push_back(child);}return OK;
}
int VeriActionStmt::push_for_replacement(NodeVec& stack) {
  if(_target)stack.push_back(_target);if(_value)stack.push_back(_value);return OK;
}
int VeriActionStmt::replace_node(Uint id,NodeList& nodes,NodeList::iterator& current) {
  auto* copy=new VeriActionStmt(id,line(),col(),detail_type(),NULL,NULL,_op,birth_mod());
  copy->set_scope(scope());copy->set_func_task_flag(func_task_flag());
  // Replacement visits target first, then value, so pop in reverse order.
  if(_value){auto child=current;--child;copy->_value=*child;(*child)->set_father(copy);nodes.erase(child);}
  if(_target){auto child=current;--child;copy->_target=*child;(*child)->set_father(copy);nodes.erase(child);}
  *current=copy;return OK;
}

int VeriUpdateStmt::check_child_validation() {
  if(_target&&_target->tok_type()==vtEXP)return OK;
  veri_err->append_err(ERR_ERROR,line(),col(),vCHILD_TYPE_LOOP_STMT);
  return vCHILD_TYPE_LOOP_STMT;
}
int VeriUpdateStmt::push_dot_children(NodeQueue& nodes,IQueue& depths) {
  nodes.push(_target);depths.push(depths.front()+1);return OK;
}
int VeriUpdateStmt::pretty_dot_label(Ofstream& out,int depth) {
  out<<dot_str_rank(idx(),depth)<<dot_str_head(idx())<<dot_str_tok_type(tok_type())
     <<dot_str_detail_type(detail_type())<<dot_str_tail(tok_type())<<dot_str_conn(idx(),_target);return OK;
}
int VeriUpdateStmt::process_node_2nd(NodeVec& stack,String&) {
  _target->set_scope(scope());stack.push_back(_target);return OK;
}
int VeriUpdateStmt::push_for_replacement(NodeVec& stack) {stack.push_back(_target);return OK;}
int VeriUpdateStmt::replace_node(Uint id,NodeList& nodes,NodeList::iterator& current) {
  auto child=current;--child;
  auto* copy=new VeriUpdateStmt(id,line(),col(),*child,_delta,birth_mod());
  copy->set_scope(scope());copy->set_func_task_flag(func_task_flag());
  (*child)->set_father(copy);nodes.erase(child);*current=copy;return OK;
}

    /******************
     * Loop-Statement *
     ******************/

void
VeriLoopStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriLoopStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  mqueue.push( _init );
  mqueue.push( _judge );
  iqueue.push( depth );
  iqueue.push( depth );

  NodeList::iterator i1 = _gen_iter.begin();
  NodeList::iterator i2 = _gen_judge.begin();
  NodeList::iterator i3 = _gen_content.begin();

  for( ; i1 != _gen_iter.end(); ++i1, ++i2, ++i3 )
  {
    mqueue.push( *i1 );
    mqueue.push( *i2 );
    mqueue.push( *i3 );
    iqueue.push( depth );
    iqueue.push( depth );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriLoopStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _init );
  ofile << dot_str_conn( idx(), _judge );

  NodeList::iterator i1 = _gen_iter.begin();
  NodeList::iterator i2 = _gen_judge.begin();
  NodeList::iterator i3 = _gen_content.begin();

  for( ; i1 != _gen_iter.end(); ++i1, ++i2, ++i3 )
  {
    ofile << dot_str_conn( idx(), *i1 );
    ofile << dot_str_conn( idx(), *i2 );
    ofile << dot_str_conn( idx(), *i3 );
  }

  return OK;
}

int
VeriLoopStmt::check_child_validation_assign( VeriNode *child, bool function_step )
{
  if( child == NULL )
    return OK;
  if( child->detail_type() == veEXP_ASSIGN || child->detail_type() == vsSTMT_COMPOUND || child->detail_type() == vsSTMT_UPDATE || child->detail_type() == vsSTMT_BLOCKING )
    return OK;
  if(function_step&&child->detail_type()==vsSTMT_CALL)return OK;
  if(child->detail_type()==vsSTMT_STMT_LIST) {
    for(auto* step:static_cast<VeriStmtList*>(child)->stmt_list())
      if(check_child_validation_assign(step,function_step)!=OK)return vCHILD_TYPE_LOOP_STMT;
    return OK;
  }
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_LOOP_STMT );
  return vCHILD_TYPE_LOOP_STMT;
}

int
VeriLoopStmt::check_child_validation( void )
{
  if(kind()==FOREACH) {
    if(!_init||(_init->detail_type()!=veEXP_PRI&&_init->detail_type()!=veEXP_MEMBER))return vCHILD_TYPE_LOOP_STMT;
    return VeriStmt::check_child_stmt(_content,vCHILD_TYPE_LOOP_STMT);
  }
  int re;
  re = check_child_validation_assign( _init );
  if( re != OK )
    return re;

  re = (kind() == FOREVER || (kind()==FOR && !_judge)) ? OK : VeriStmt::check_func_child_exp_validation( _judge, vCHILD_TYPE_LOOP_STMT );
  if( re != OK )
    return re;

  re = check_child_validation_assign( _iter, true );
  if( re != OK )
    return re;

  re = VeriStmt::check_child_stmt( _content, vCHILD_TYPE_LOOP_STMT );
  if( re != OK )
    return re;

  return OK;
}

int
VeriLoopStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  if(kind()==FOREACH) {
    if(pstatus()==vSTART_S) {
      set_pstatus(vEND_S);mstack.push_back(this);_init->set_scope(scope());mstack.push_back(_init);return OK;
    }
    auto* source=veri_array_element_symbol(_init);
    unsigned axis=0;
    for(const auto& name:_foreach_indices) {
      const int kind=veri_array_container_kind(_init,axis);auto* key=veri_associative_key_type(_init,axis++);
      if(name.empty())continue;
      const bool text=kind==vrASSOC_STRING;
      auto* symbol=scope()->value_same_level(name);
      if(!symbol||symbol->tok_type()!=vtVAR)throw std::runtime_error("unresolved foreach index");
      auto* var=static_cast<VeriVar*>(symbol);var->set_net_type(text?vvSTRING:vvINT2);var->set_is_signed(text||kind==vrASSOC_UINT?IS_FALSE:IS_TRUE);
      if(key)var->infer_associative_index(key);
      static_cast<VeriVarDecl*>(var->father())->infer_foreach_index(text,kind==vrASSOC_UINT,key);
    }
    if(_content){_content->set_scope(scope());mstack.push_back(_content);}return OK;
  }

  // Procedural control is executed by the simulator, not elaboration.
  // Bind every branch once; generate constructs have separate AST classes.
  if( _iter != NULL )
  {
    _iter->set_scope( scope() );
    mstack.push_back( _iter );
  }
  if( _content != NULL )
  {
    _content->set_scope( scope() );
    mstack.push_back( _content );
  }
  if( _judge != NULL )
  {
    _judge->set_scope( scope() );
    mstack.push_back( _judge );
  }
  if( _init != NULL )
  {
    _init->set_scope( scope() );
    mstack.push_back( _init );
  }
  return OK;
}

int
VeriLoopStmt::push_start_and_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_judge->clean_up( );
  _judge->set_scope( scope( ) );
  mstack.push_back( _judge );
  
  //_init->clean_up( );
  _init->set_scope( scope( ) );
  mstack.push_back( _init );

  return OK;
}

int
VeriLoopStmt::repeat_loop( void )
{
  NodeVec  node_vec;
  VeriNode *tmp;
  NodeVec tstack;
  tstack.reserve( 397 );

  tstack.push_back( this );
  while( !tstack.empty( ) )
  {
    tmp = tstack.back( );
    tstack.pop_back( );
    node_vec.push_back( tmp );
    tmp->push_for_replacement( tstack );
  }

  NodeList node_list( node_vec.rbegin(), node_vec.rend() );
  node_vec.clear();
  NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
  {
    tmp = *inl;
    tmp->replace_node( veri_parser->next_id(), node_list, inl );
    veri_parser->insert_node( *inl );
  }

  VeriNode *last = *(--inl);
  assert( last->detail_type( ) == detail_type( ) );

  VeriFuncLoopStmt *loop = static_cast<VeriFuncLoopStmt *>(last);

  _iter    = loop->iter();
  _judge   = loop->judge();
  _content = loop->content();

  veri_parser->toss_node( last->idx() );
  return OK;
}

int
VeriLoopStmt::clear_content( void )
{
  VeriNode *tmp = _content;
  NodeVec   node_vec;
  NodeVec   tstack;
  tstack.reserve( 3997 );

  tstack.push_back( tmp );
  while( !tstack.empty( ) )
  {
    tmp = tstack.back( );
    tstack.pop_back( );
    node_vec.push_back( tmp );
    tmp->push_for_replacement( tstack );
  }

  NodeList node_list( node_vec.rbegin(), node_vec.rend() );
  node_vec.clear();
  NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
    veri_parser->toss_node( (*inl)->idx() );
  return OK;
}

int
VeriLoopStmt::decide_loop( NodeVec& mstack )
{
  VeriExp *judge_exp = static_cast<VeriExp *>(_judge);
  if( judge_exp->calc_value( ) != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), judge_exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );
    num->unary_operation( vtUOR );
    int re = num->one_bit_value( );

    switch( re )
    {
      case V1 :
        veri_parser->toss_node( num->idx() );

        mstack.push_back( this );

        repeat_loop( );

        //_judge->clean_up( );
        _judge->set_scope( scope( ) );
        mstack.push_back( _judge );

        //_iter->clean_up( );
        _iter->set_scope( scope( ) );
        mstack.push_back( _iter );

        //_content->clean_up( );
        _content->set_scope( scope( ) );
        mstack.push_back( _content );

        _gen_iter.push_back( _iter );
        _gen_judge.push_back( _judge );
        _gen_content.push_back( _content );

        return OK;
        break;

      case V0 :
        clear_content( );
        veri_parser->toss_node( num->idx() );
        return OK;
        break;

      default:
        clear_content( );
        veri_parser->toss_node( num->idx() );
        veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
        return vSEC_LOOP_JUDGE_FAILURE;
        break;
    }
    return OK;
  }
  else
  {
    clear_content( );
    veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
    return vSEC_LOOP_JUDGE_FAILURE;
  }
}

int
VeriLoopStmt::push_for_replacement( NodeVec& mstack )
{
  // Only FOR has initialization and iteration; FOREVER has no condition.
  // Module instantiation clones this tree before its semantic traversal.
  if( _init != NULL ) mstack.push_back( _init );
  if( _judge != NULL ) mstack.push_back( _judge );
  if( _iter != NULL ) mstack.push_back( _iter );
  mstack.push_back( _content );

  return OK;
}

int
VeriLoopStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriLoopStmt *tmp = new VeriLoopStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_content = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _iter != NULL )
  {
    tmp->_iter = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _judge != NULL )
  {
    tmp->_judge = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _init != NULL )
  {
    tmp->_init = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /***************************
     * Function-Loop-Statement * 
     ***************************/

void
VeriFuncLoopStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncLoopStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  mqueue.push( _init );
  mqueue.push( _judge );
  iqueue.push( depth );
  iqueue.push( depth );

  NodeList::iterator i1 = _gen_iter.begin();
  NodeList::iterator i2 = _gen_judge.begin();
  NodeList::iterator i3 = _gen_content.begin();

  for( ; i1 != _gen_iter.end(); ++i1, ++i2, ++i3 )
  {
    mqueue.push( *i1 );
    mqueue.push( *i2 );
    mqueue.push( *i3 );
    iqueue.push( depth );
    iqueue.push( depth );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriFuncLoopStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _init );
  ofile << dot_str_conn( idx(), _judge );

  NodeList::iterator i1 = _gen_iter.begin();
  NodeList::iterator i2 = _gen_judge.begin();
  NodeList::iterator i3 = _gen_content.begin();

  for( ; i1 != _gen_iter.end(); ++i1, ++i2, ++i3 )
  {
    ofile << dot_str_conn( idx(), *i1 );
    ofile << dot_str_conn( idx(), *i2 );
    ofile << dot_str_conn( idx(), *i3 );
  }

  return OK;
}

int
VeriFuncLoopStmt::check_child_validation_assign( VeriNode *child )
{
  if( child != NULL && child->detail_type() == veEXP_ASSIGN )
    return OK;
  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_LOOP_STMT );
  return vCHILD_TYPE_LOOP_STMT;
}

int
VeriFuncLoopStmt::check_child_validation( void )
{
  int re;
  re = check_child_validation_assign( _init );
  if( re != OK )
    return re;

  re = VeriStmt::check_func_child_exp_validation( _judge,
                             vCHILD_TYPE_FUNC_LOOP_STMT );
  if( re != OK )
    return re;

  re = check_child_validation_assign( _iter );
  if( re != OK )
    return re;

  re = VeriStmt::check_child_stmt( _content, vCHILD_TYPE_FUNC_LOOP_STMT );
  if( re != OK )
    return re;

  return OK;
}

int
VeriFuncLoopStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_start_and_condition( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return decide_loop( mstack );
      break;
  }
}

int
VeriFuncLoopStmt::push_start_and_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_judge->clean_up( );
  _judge->set_scope( scope( ) );
  mstack.push_back( _judge );
  
  //_init->clean_up( );
  _init->set_scope( scope( ) );
  mstack.push_back( _init );

  return OK;
}

int
VeriFuncLoopStmt::repeat_loop( void )
{
  NodeVec  node_vec;
  VeriNode *tmp;
  NodeVec tstack;
  tstack.reserve( 397 );

  tstack.push_back( this );
  while( !tstack.empty( ) )
  {
    tmp = tstack.back( );
    tstack.pop_back( );
    node_vec.push_back( tmp );
    tmp->push_for_replacement( tstack );
  }

  NodeList node_list( node_vec.rbegin(), node_vec.rend() );
  node_vec.clear();
  NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
  {
    tmp = *inl;
    tmp->replace_node( veri_parser->next_id(), node_list, inl );
    veri_parser->insert_node( *inl );
  }

  VeriNode *last = *(--inl);
  assert( last->detail_type( ) == detail_type( ) );

  VeriFuncLoopStmt *loop = static_cast<VeriFuncLoopStmt *>(last);

  _iter    = loop->iter();
  _judge   = loop->judge();
  _content = loop->content();

  veri_parser->toss_node( last->idx() );
  return OK;
}

int
VeriFuncLoopStmt::clear_content( void )
{
  VeriNode *tmp = _content;
  NodeVec   node_vec;
  NodeVec   tstack;
  tstack.reserve( 3997 );

  tstack.push_back( tmp );
  while( !tstack.empty( ) )
  {
    tmp = tstack.back( );
    tstack.pop_back( );
    node_vec.push_back( tmp );
    tmp->push_for_replacement( tstack );
  }

  NodeList node_list( node_vec.rbegin(), node_vec.rend() );
  node_vec.clear();
  NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
    veri_parser->toss_node( (*inl)->idx() );
  return OK;
}

int
VeriFuncLoopStmt::decide_loop( NodeVec& mstack )
{
  VeriExp *judge_exp = static_cast<VeriExp *>(_judge);
  if( judge_exp->calc_value( ) != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), judge_exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );
    num->unary_operation( vtUOR );
    int re = num->one_bit_value( );

    switch( re )
    {
      case V1 :
        veri_parser->toss_node( num->idx() );

        mstack.push_back( this );

        repeat_loop( );

        //_judge->clean_up( );
        _judge->set_scope( scope( ) );
        mstack.push_back( _judge );

        //_iter->clean_up( );
        _iter->set_scope( scope( ) );
        mstack.push_back( _iter );

        //_content->clean_up( );
        _content->set_scope( scope( ) );
        mstack.push_back( _content );

        _gen_iter.push_back( _iter );
        _gen_judge.push_back( _judge );
        _gen_content.push_back( _content );

        return OK;
        break;

      case V0 :
        clear_content( );
        veri_parser->toss_node( num->idx() );
        return OK;
        break;

      default:
        clear_content( );
        veri_parser->toss_node( num->idx() );
        veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
        return vSEC_LOOP_JUDGE_FAILURE;
        break;
    }
    return OK;
  }
  else
  {
    clear_content( );
    veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
    return vSEC_LOOP_JUDGE_FAILURE;
  }
}

int
VeriFuncLoopStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _init );
  mstack.push_back( _judge );
  mstack.push_back( _iter );
  mstack.push_back( _content );

  return OK;
}

int
VeriFuncLoopStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncLoopStmt *tmp = new VeriFuncLoopStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_content = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_iter = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_judge = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_init = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /****************************************
     * Function-Default-Case-Item Statement *
     ****************************************/

void
VeriFuncDefaultCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncDefaultCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriFuncDefaultCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriFuncDefaultCaseItem::check_child_validation( void )
{
  return VeriStmt::check_child_stmt( _stmt, vCHILD_TYPE_FUNC_DEFAULT_CASE_ITEM );
}

int
VeriFuncDefaultCaseItem::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriFuncDefaultCaseItem::push_stmt( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriFuncDefaultCaseItem::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _stmt );
  return OK;
}

int
VeriFuncDefaultCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncDefaultCaseItem *tmp = new VeriFuncDefaultCaseItem( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************************
     * Function-Case-Item Statement *
     ********************************/

void
VeriFuncCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  {
    mqueue.push( *it ); 
    iqueue.push( depth );
  }

  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriFuncCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriFuncCaseItem::check_child_validation( void )
{
  int re;
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  { 
    re = VeriStmt::check_func_child_exp_validation( *it, vCHILD_TYPE_FUNC_CASE_ITEM );
    if( re != OK )
      return re;
  }

  return VeriStmt::check_child_stmt( _stmt,  vCHILD_TYPE_FUNC_CASE_ITEM );
}

int
VeriFuncCaseItem::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriFuncCaseItem::push_labels( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _label.rbegin();
  for( ; it != _label.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it ); 
  }

  return OK;
}

int
VeriFuncCaseItem::push_stmt( NodeVec& mstack )
{
  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriFuncCaseItem::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
    mstack.push_back( *it ); 
  mstack.push_back( _stmt );
  return OK;
}

int
VeriFuncCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncCaseItem *tmp = new VeriFuncCaseItem( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  {
    tmp->_label.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /*************************************
     * Function-Case-Item-List Statement *
     *************************************/

int
VeriFuncCaseItemList::set_default( VeriNode * node )
{
  if( _default_item == NULL )
  {
    _default_item = node;
    return OK;
  }
  else
    return vCHILD_TYPE_FUNC_CASE_ITEM_LIST;
}

void
VeriFuncCaseItemList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncCaseItemList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _default_item != NULL )
  {
    mqueue.push( _default_item );
    iqueue.push( depth );
  }

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriFuncCaseItemList::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _default_item );
  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriFuncCaseItemList::check_child_validation( void )
{
  int re;
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsSTMT_FUNC_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(), _default_item->col(),
                            vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
      return vCHILD_TYPE_FUNC_CASE_ITEM_LIST;
    }
  }

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    re = VeriStmt::check_child_stmt( *it, vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
    if( re != OK )
      return re;

    if( (*it)->detail_type() != vsSTMT_FUNC_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                            vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
      return vCHILD_TYPE_FUNC_CASE_ITEM_LIST;
    }
  }
  return OK;
}

int
VeriFuncCaseItemList::check_last_child_validation( void )
{
  int re;
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsSTMT_FUNC_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(), _default_item->col(),
                            vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
      return vCHILD_TYPE_FUNC_CASE_ITEM_LIST;
    }
  }

  VeriNode * item = _other_item.back();
  re = VeriStmt::check_child_stmt( item, vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
  if( re != OK )
    return re;

  if( item->detail_type() != vsSTMT_FUNC_CASE_ITEM )
  {
    veri_err->append_err( ERR_ERROR, item->line(), item->col(),
                          vCHILD_TYPE_FUNC_CASE_ITEM_LIST );
    return vCHILD_TYPE_FUNC_CASE_ITEM_LIST;
  }

  return OK;
}

int
VeriFuncCaseItemList::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriFuncCaseItemList::push_labels( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _other_item.rbegin();
  for( ; it != _other_item.rend(); ++it )
  {
    //(*it)->clear( );
    (*it)->set_scope( scope( ) );
    (static_cast<VeriFuncCaseItem*>(*it))->push_labels( mstack );
  }

  return OK;
}

int
VeriFuncCaseItemList::push_for_replacement( NodeVec& mstack )
{
  if( _default_item != NULL )
    mstack.push_back( _default_item );

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
    mstack.push_back( *it );
  return OK;
}

int
VeriFuncCaseItemList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncCaseItemList *tmp = new VeriFuncCaseItemList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    tmp->_other_item.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _default_item != NULL )
  {
    tmp->_default_item = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /***************************
     * Function-Case Statement *
     ***************************/

void
VeriFuncCaseStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncCaseStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _switch );
  iqueue.push( depth );
//  mqueue.push( _item_list );
//  iqueue.push( depth );
  mqueue.push( _choice );
  iqueue.push( depth );
  return OK;
}

int
VeriFuncCaseStmt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_case_type( _case_type );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _switch );
  ofile << dot_str_conn( idx(), _item_list );

  return OK;
}

int
VeriFuncCaseStmt::check_child_validation( void )
{
  int re;
  re = VeriStmt::check_func_child_exp_validation( _switch, vCHILD_TYPE_FUNC_CASE_STMT );
  if( re != OK )
    return re;

  if(    _item_list != NULL
      && _item_list->detail_type() == vsSTMT_FUNC_CASE_ITEM_LIST )
    return OK;

  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_FUNC_CASE_STMT );
  return vCHILD_TYPE_FUNC_CASE_STMT;
}

int
VeriFuncCaseStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_conditions( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return decide_case( mstack );
      break;
  }
}

int
VeriFuncCaseStmt::push_conditions( NodeVec& mstack )
{
  mstack.push_back( this );

  VeriFuncCaseItemList *item_list
    = static_cast<VeriFuncCaseItemList *>(_item_list);
  item_list->push_labels( mstack );

  //_switch->clean_up( );
  _switch->set_scope( scope( ) );
  mstack.push_back( _switch );

  return OK;
}

int
VeriFuncCaseStmt::prep_all_labels( void )
{
  VeriFuncCaseItemList *item_list
    = static_cast<VeriFuncCaseItemList *>(_item_list);

  VeriFuncCaseItem *item = NULL;
  NodeList &items = item_list->other_item( );
  NodeList::iterator it = items.begin();
  NodeList::iterator il;
  for( ; it != items.end(); ++it )
  {
    item = static_cast<VeriFuncCaseItem *>(*it);
    NodeList &labels = item->label( );
    for( il = labels.begin(); il != labels.end(); ++il )
    {
      _all_labels.push_back( *il );
      _all_exps.push_back( item->stmt( ) );
    }
  }
  return OK;
}

int
VeriFuncCaseStmt::decide_case( NodeVec& mstack )
{
  VeriExp *switch_exp = static_cast<VeriExp *>(_switch);
  if( switch_exp->calc_value( ) == NULL )
  {
    veri_err->append_err( ERR_ERROR, _switch, vSEC_CASE_COND_NOT_CALC );
    return vSEC_CASE_COND_NOT_CALC;
  }

  VeriFuncCaseItemList *item_list
    = static_cast<VeriFuncCaseItemList *>(_item_list);

  VeriFuncDefaultCaseItem *default_item
    = static_cast<VeriFuncDefaultCaseItem *>(item_list->default_item( ) );

  prep_all_labels( );

  int re = V0;
  NodeList::iterator ilabel = _all_labels.begin();
  NodeList::iterator iexp   = _all_exps.begin();

  int found_match = IS_FALSE;
  VeriNum *judge_val = NULL;
  VeriNum *label_val = NULL;
  for( ; ilabel != _all_labels.end(); ++ilabel, ++iexp )
  {
    judge_val = new VeriNum( veri_parser->next_id(), switch_exp->calc_value() );
    veri_parser->insert_node( judge_val );
    judge_val->set_father( this );
    judge_val->set_scope( scope( ) );
    label_val = static_cast<VeriExp *>(*ilabel)->calc_value( );
    if( label_val == NULL )
    {
      veri_err->append_err( ERR_ERROR, *ilabel, vSEC_CASE_LABEL_NOT_CALC );
      return vSEC_CASE_LABEL_NOT_CALC;
    }

    re = judge_val->upward_case_eq( label_val );
    veri_parser->toss_node( judge_val->idx() );
    if( re == V1 )
    {
      found_match = IS_TRUE;

      //(*iexp)->clean_up( );
      (*iexp)->set_scope( scope( ) );
      mstack.push_back( *iexp );

      _choice = *iexp;
      break;
    }
  }

  if( found_match == IS_FALSE && default_item != NULL )
    default_item->push_stmt( mstack );

  return OK;
}

int
VeriFuncCaseStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _switch );
  mstack.push_back( _item_list );
  return OK;
}

int
VeriFuncCaseStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncCaseStmt *tmp = new VeriFuncCaseStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_item_list = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_switch = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*******************************
     * Default-Case-Item Statement *
     *******************************/

void
VeriDefaultCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriDefaultCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriDefaultCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriDefaultCaseItem::check_child_validation( void )
{
  return VeriStmt::check_child_stmt( _stmt, vCHILD_TYPE_DEFAULT_CASE_ITEM );
}

int
VeriDefaultCaseItem::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriDefaultCaseItem::push_stmt( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriDefaultCaseItem::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _stmt );
  return OK;
}

int
VeriDefaultCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDefaultCaseItem *tmp = new VeriDefaultCaseItem( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /***********************
     * Case-Item Statement *
     ***********************/

void
VeriCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  {
    mqueue.push( *it ); 
    iqueue.push( depth );
  }

  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriCaseItem::check_child_validation( void )
{
  int re;
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  { 
    if((*it)->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(*it)->multi_type()==vemINSIDE_RANGE) {
      for(auto* bound:static_cast<VeriMultiExp*>(*it)->exp()) {
        re=VeriStmt::check_func_child_exp_validation(bound,vCHILD_TYPE_CASE_ITEM);if(re!=OK)return re;
      }
      continue;
    }
    re = VeriStmt::check_func_child_exp_validation( *it, vCHILD_TYPE_CASE_ITEM );
    if( re != OK )
      return re;
  }

  return VeriStmt::check_child_stmt( _stmt,  vCHILD_TYPE_CASE_ITEM );
}

int
VeriCaseItem::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );

  NodeList::reverse_iterator it = _label.rbegin();
  for( ; it != _label.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it ); 
  }

  return OK;
}

int
VeriCaseItem::push_labels( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _label.rbegin();
  for( ; it != _label.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it ); 
  }

  return OK;
}

int
VeriCaseItem::push_stmt( NodeVec& mstack )
{
  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}


int
VeriCaseItem::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
    mstack.push_back( *it ); 
  mstack.push_back( _stmt );
  return OK;
}

int
VeriCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCaseItem *tmp = new VeriCaseItem( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  {
    tmp->_label.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************
     * Case-Item-List Statement *
     ****************************/

int
VeriCaseItemList::set_default( VeriNode * node )
{
  if( _default_item == NULL )
  {
    _default_item = node;
    return OK;
  }
  else
    return vCHILD_TYPE_CASE_ITEM_LIST;
}

void
VeriCaseItemList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriCaseItemList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _default_item != NULL )
  {
    mqueue.push( _default_item );
    iqueue.push( depth );
  }

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriCaseItemList::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _default_item );
  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriCaseItemList::check_child_validation( void )
{
  int re;
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsSTMT_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(), _default_item->col(),
                            vCHILD_TYPE_CASE_ITEM_LIST );
      return vCHILD_TYPE_CASE_ITEM_LIST;
    }
  }

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    re = VeriStmt::check_child_stmt( *it, vCHILD_TYPE_CASE_ITEM_LIST );
    if( re != OK )
      return re;

    if( (*it)->detail_type() != vsSTMT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                            vCHILD_TYPE_CASE_ITEM_LIST );
      return vCHILD_TYPE_CASE_ITEM_LIST;
    }
  }
  return OK;
}

int
VeriCaseItemList::check_last_child_validation( void )
{
  int re;
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsSTMT_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(), _default_item->col(),
                            vCHILD_TYPE_CASE_ITEM_LIST );
      return vCHILD_TYPE_CASE_ITEM_LIST;
    }
  }

  VeriNode * item = _other_item.back();
  re = VeriStmt::check_child_stmt( item, vCHILD_TYPE_CASE_ITEM_LIST );
  if( re != OK )
    return re;

  if( item->detail_type() != vsSTMT_CASE_ITEM )
  {
    veri_err->append_err( ERR_ERROR, item->line(), item->col(),
                          vCHILD_TYPE_CASE_ITEM_LIST );
    return vCHILD_TYPE_CASE_ITEM_LIST;
  }

  return OK;
}

int
VeriCaseItemList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  if( _default_item != NULL )
  {
    //_default_item->clean_up( );
    _default_item->set_scope( scope( ) );
    mstack.push_back( _default_item );
  }

  NodeList::reverse_iterator it = _other_item.rbegin();
  for( ; it != _other_item.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriCaseItemList::push_labels( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _other_item.rbegin();
  for( ; it != _other_item.rend(); ++it )
  {
    //(*it)->clear( );
    (*it)->set_scope( scope( ) );
    (static_cast<VeriCaseItem*>(*it))->push_labels( mstack );
  }

  return OK;
}

int
VeriCaseItemList::push_for_replacement( NodeVec& mstack )
{
  if( _default_item != NULL )
    mstack.push_back( _default_item );

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
    mstack.push_back( *it );
  return OK;
}

int
VeriCaseItemList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCaseItemList *tmp = new VeriCaseItemList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    tmp->_other_item.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _default_item != NULL )
  {
    tmp->_default_item = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /******************
     * Case Statement *
     ******************/

void
VeriCaseStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriCaseStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  if( _choice == NULL )
  {
    mqueue.push( _switch );
    iqueue.push( depth );
    mqueue.push( _item_list );
    iqueue.push( depth );
  }
  else
  {
    mqueue.push( _choice );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriCaseStmt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_case_type( _case_type );
  ofile << dot_str_tail( tok_type() );

  // connection
  if( _choice == NULL )
  {
    ofile << dot_str_conn( idx(), _switch );
    ofile << dot_str_conn( idx(), _item_list );
  }
  else
    ofile << dot_str_conn( idx(), _choice );

  return OK;
}

int
VeriCaseStmt::check_child_validation( void )
{
  int re;
  re = VeriStmt::check_func_child_exp_validation( _switch, vCHILD_TYPE_CASE_STMT );
  if( re != OK )
    return re;

  if(    _item_list != NULL
      && _item_list->detail_type() == vsSTMT_CASE_ITEM_LIST )
    return OK;

  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_CASE_STMT );
  return vCHILD_TYPE_CASE_STMT;
}

int
VeriCaseStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  // Procedural control is executed by the simulator, not elaboration.
  // Bind every branch once; generate constructs have separate AST classes.
  if( _item_list != NULL )
  {
    _item_list->set_scope( scope() );
    mstack.push_back( _item_list );
  }
  if( _switch != NULL )
  {
    _switch->set_scope( scope() );
    mstack.push_back( _switch );
  }
  return OK;
}

int
VeriCaseStmt::push_conditions( NodeVec& mstack )
{
  mstack.push_back( this );

  VeriCaseItemList *item_list
    = static_cast<VeriCaseItemList *>(_item_list);
  item_list->push_labels( mstack );

  //_switch->clean_up( );
  _switch->set_scope( scope( ) );
  mstack.push_back( _switch );

  return OK;
}

int
VeriCaseStmt::prep_all_labels( void )
{
  VeriCaseItemList *item_list
    = static_cast<VeriCaseItemList *>(_item_list);

  VeriCaseItem *item = NULL;
  NodeList &items = item_list->other_item( );
  NodeList::iterator it = items.begin();
  NodeList::iterator il;
  for( ; it != items.end(); ++it )
  {
    item = static_cast<VeriCaseItem *>(*it);
    NodeList &labels = item->label( );
    for( il = labels.begin(); il != labels.end(); ++il )
    {
      _all_labels.push_back( *il );
      _all_exps.push_back( item->stmt( ) );
    }
  }
  return OK;
}

int
VeriCaseStmt::decide_case( NodeVec& mstack )
{
  _item_list->set_scope(scope());mstack.push_back(_item_list);return OK;
}

int
VeriCaseStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _switch );
  mstack.push_back( _item_list );
  return OK;
}

int
VeriCaseStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCaseStmt *tmp = new VeriCaseStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_item_list = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_switch = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /**********************************
     * Function-Conditional Statement *
     **********************************/

void
VeriFuncCondStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncCondStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _if_exp );
  iqueue.push( depth );

  if( _choice != NULL )
  {
    mqueue.push( _choice );
    iqueue.push( depth );
  }
  else
  {
    mqueue.push( _if_stmt );
    iqueue.push( depth );

    if( _else_stmt != NULL )
    {
      mqueue.push( _else_stmt );
      iqueue.push( depth );
    }
  }
  return OK;
}

int
VeriFuncCondStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  if( _choice != NULL )
  {
    ofile << dot_str_conn( idx(), _if_exp );
    ofile << dot_str_conn( idx(), _choice );
  }
  else
  {
    ofile << dot_str_conn( idx(), _if_exp );
    ofile << dot_str_conn( idx(), _if_stmt );
    ofile << dot_str_conn( idx(), _else_stmt );
  }

  return OK;
}

int
VeriFuncCondStmt::check_child_validation( void )
{
  int re;
  re = VeriStmt::check_func_child_exp_validation( _if_exp, vCHILD_TYPE_FUNC_COND_STMT );
  if( re != OK )
    return re;

  re = VeriStmt::check_child_stmt( _if_stmt, vCHILD_TYPE_FUNC_COND_STMT );
  if( re != OK )
    return re;

  if( _else_stmt != NULL )
  {
    re = VeriStmt::check_child_stmt( _else_stmt, vCHILD_TYPE_FUNC_COND_STMT );
    if( re != OK )
      return re;
  }

  return OK;
}

int
VeriFuncCondStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = push_condition( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return choose_children( mstack );
      break;
  }
}

int
VeriFuncCondStmt::push_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_if_exp->clean_up( );
  _if_exp->set_scope( scope( ) );
  mstack.push_back( _if_exp );

  return OK;
}

int
VeriFuncCondStmt::choose_children( NodeVec& mstack )
{
  VeriExp *if_exp = static_cast<VeriExp *>(_if_exp);
  
  if( if_exp->calc_value( ) != NULL )
  {
    VeriNum *num = new VeriNum( veri_parser->next_id(), if_exp->calc_value() );
    veri_parser->insert_node( num );
    num->set_father( this );
    num->set_scope( scope( ) );
    num->unary_operation( vtUOR );
    int re = num->one_bit_value( );

    switch( re )
    {
      case V0 :
        if( _else_stmt != NULL )
        {
          //_else_stmt->clean_up( );
          _else_stmt->set_scope( scope( ) );
          mstack.push_back( _else_stmt );

          _choice = _else_stmt;
        }
        return OK;
        break;

      case V1 :
        //_if_stmt->clean_up( );
        _if_stmt->set_scope( scope( ) );
        mstack.push_back( _if_stmt );

        _choice = _if_stmt;
        return OK;
        break;

      default:
        veri_err->append_err( ERR_ERROR, _if_exp, vSEC_IF_COND_NOT_CALC );
        return vSEC_IF_COND_NOT_CALC;
        break;
    }
  }

  veri_err->append_err( ERR_ERROR, _if_exp, vSEC_IF_COND_NOT_CALC );
  return vSEC_IF_COND_NOT_CALC;

  return OK;
}

int
VeriFuncCondStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _if_exp );
  mstack.push_back( _if_stmt );

  if( _else_stmt != NULL )
    mstack.push_back( _else_stmt );

  return OK;
}

int
VeriFuncCondStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncCondStmt *tmp = new VeriFuncCondStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _else_stmt != NULL )
  {
    tmp->_else_stmt = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_if_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_if_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*************************
     * Conditional Statement *
     *************************/

void
VeriCondStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriCondStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _choice == NULL )
  {
    mqueue.push( _if_exp );
    mqueue.push( _if_stmt );
    iqueue.push( depth );
    iqueue.push( depth );

    if( _else_stmt != NULL )
    {
      mqueue.push( _else_stmt );
      iqueue.push( depth );
    }
  }
  else
  {
    mqueue.push( _if_exp );
    iqueue.push( depth );

    mqueue.push( _choice );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriCondStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  if( _choice == NULL )
  {
    ofile << dot_str_conn( idx(), _if_exp );
    ofile << dot_str_conn( idx(), _if_stmt );
    ofile << dot_str_conn( idx(), _else_stmt );
  }
  else
  {
    ofile << dot_str_conn( idx(), _if_exp );
    ofile << dot_str_conn( idx(), _choice );
  }

  return OK;
}

int
VeriCondStmt::check_child_validation( void )
{
  int re=OK;
  if(_wait_order) {
    for(auto* event:veri_system_arguments(_if_exp)) {
      re=VeriStmt::check_func_child_exp_validation(event,vCHILD_TYPE_COND_STMT);
      if(re!=OK)return re;
    }
  } else
    re = VeriStmt::check_func_child_exp_validation( _if_exp, vCHILD_TYPE_COND_STMT );
  if( re != OK )
    return re;

  re = VeriStmt::check_child_stmt( _if_stmt, vCHILD_TYPE_COND_STMT );
  if( re != OK )
    return re;

  if( _else_stmt != NULL )
  {
    re = VeriStmt::check_child_stmt( _else_stmt, vCHILD_TYPE_COND_STMT );
    if( re != OK )
      return re;
  }

  return OK;
}

int
VeriCondStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  // Procedural control is executed by the simulator, not elaboration.
  // Bind every branch once; generate constructs have separate AST classes.
  if( _else_stmt != NULL )
  {
    _else_stmt->set_scope( scope() );
    mstack.push_back( _else_stmt );
  }
  if( _if_stmt != NULL )
  {
    _if_stmt->set_scope( scope() );
    mstack.push_back( _if_stmt );
  }
  if( _if_exp != NULL )
  {
    _if_exp->set_scope( scope() );
    mstack.push_back( _if_exp );
  }
  return OK;
}

int
VeriCondStmt::push_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_if_exp->clean_up( );
  _if_exp->set_scope( scope( ) );
  mstack.push_back( _if_exp );

  return OK;
}

int
VeriCondStmt::choose_children( NodeVec& mstack )
{
  if(_else_stmt){_else_stmt->set_scope(scope());mstack.push_back(_else_stmt);}
  _if_stmt->set_scope(scope());mstack.push_back(_if_stmt);return OK;
}

int
VeriCondStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _if_exp );
  mstack.push_back( _if_stmt );

  if( _else_stmt != NULL )
    mstack.push_back( _else_stmt );

  return OK;
}

int
VeriCondStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCondStmt *tmp = new VeriCondStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _else_stmt != NULL )
  {
    tmp->_else_stmt = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_if_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_if_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /**************************************
     * Procedual-Timing-Control Statement *
     **************************************/

void
VeriProcTimeContStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriProcTimeContStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _control );
  mqueue.push( _stmt );
  iqueue.push( depth );
  iqueue.push( depth );
  return OK;
}

int
VeriProcTimeContStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _control );
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriProcTimeContStmt::check_child_validation( void )
{
  if (detail_type() == vsSTMT_WAIT) {
    int re = check_func_child_exp_validation(_control, vCHILD_TYPE_PROC_TIME_CONTROL_STMT);
    return re == OK ? VeriStmt::check_child_stmt(_stmt, vCHILD_TYPE_PROC_TIME_CONTROL_STMT) : re;
  }
  if (_control == NULL ||
      !((_control->tok_type() == vtSTMT && _control->detail_type() == vsSTMT_EVENT) ||
        (_control->tok_type() == vtEXP && _control->detail_type() == veEXP_DELAY)))
    return vCHILD_TYPE_PROC_TIME_CONTROL_STMT;
  return VeriStmt::check_child_stmt(_stmt, vCHILD_TYPE_PROC_TIME_CONTROL_STMT);
}

int
VeriProcTimeContStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriProcTimeContStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );

  //_control->clean_up( );
  _control->set_scope( scope( ) );
  mstack.push_back( _control );
  
  return OK;
}

int
VeriProcTimeContStmt::do_nothing( void )
{
  return OK;
}

int
VeriProcTimeContStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _control );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriProcTimeContStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriProcTimeContStmt *tmp = new VeriProcTimeContStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  tmp->_control = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*********************
     * Disable Statement *
     *********************/

void
VeriDisableStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriDisableStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  if(_break_stmt) {mqueue.push( _break_stmt );iqueue.push( depth );}
  return OK;
}

int
VeriDisableStmt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  if( _break_stmt == NULL )
  {
    ofile << dot_str_name( _label );
    ofile << dot_str_tail( tok_type() );
  }
  else
  {
    ofile << dot_str_var_conn( _label, _break_stmt );
    ofile << dot_str_tail( tok_type() );
  }

  // connection
  
  return OK;
}

int
VeriDisableStmt::check_child_validation( void )
{
  return OK;
}

int
VeriDisableStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriDisableStmt::push_children( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriDisableStmt::do_nothing( void )
{
  return OK;
}

int
VeriDisableStmt::push_for_replacement( NodeVec& mstack )
{
  if(_break_stmt)mstack.push_back( _break_stmt );
  return OK;
}

int
VeriDisableStmt::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDisableStmt *tmp = new VeriDisableStmt( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

    /*******************
     * Event Statement *
     *******************/

void
VeriEventStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriEventStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  NodeList::iterator it = _event_list.begin();
  int depth = iqueue.front( ) + 1;
  for( ; it != _event_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriEventStmt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_is_tf( "ALL", _is_all );
  ofile << dot_str_tail( tok_type() );

  // connection
  NodeList::iterator it = _event_list.begin();
  for( ; it != _event_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriEventStmt::check_child_validation( void )
{
  if( _is_all != IS_TRUE && _event_list.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(),
                          col(), vCHILD_TYPE_EVENT_STMT );
    return vCHILD_TYPE_EVENT_STMT;
  }

  NodeList::iterator it = _event_list.begin();
  for( ; it != _event_list.end(); ++it )
  {
    if( (*it)->detail_type() != veEXP_PRI )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(),
                            (*it)->col(), vCHILD_TYPE_EVENT_STMT );
      return vCHILD_TYPE_EVENT_STMT;
    }
  }

  return OK;
}

int
VeriEventStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriEventStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _event_list.rbegin();
  for( ; it != _event_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it );
  }

  return OK;
}

int
VeriEventStmt::do_nothing( void )
{
  return OK;
}

int
VeriEventStmt::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _event_list.begin();
  for( ; it != _event_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriEventStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriEventStmt *tmp = new VeriEventStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _event_list.begin();
  for( ; it != _event_list.end(); ++it )
  {
    tmp->_event_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /***************************
     * System-Caller Statement *
     ***************************/

void
VeriSysCallerStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriSysCallerStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  if( _arg != NULL )
  {
    int depth = iqueue.front( ) + 1;
    mqueue.push( _arg );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriSysCallerStmt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _caller );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _arg );

  return OK;
}

int
VeriSysCallerStmt::check_child_validation( void )
{
  if( _caller.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_SYS_CALL_STMT );
    return vCHILD_TYPE_SYS_CALL_STMT;
  }

  if( _arg != NULL )
  {
    if( _arg->detail_type() == veEXP_MULTI )
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_arg);
      if( mexp->multi_type() != vemCOMMA_EXP )
      {
        veri_err->append_err( ERR_ERROR, _arg->line(), _arg->col(),
                              vCHILD_TYPE_SYS_CALL_STMT );
        return vCHILD_TYPE_SYS_CALL_STMT;
      }
    }
    else
    {
      veri_err->append_err( ERR_ERROR, _arg->line(), _arg->col(),
                            vCHILD_TYPE_SYS_CALL_STMT );
      return vCHILD_TYPE_SYS_CALL_STMT;
    }
  }
  return OK;
}

int
VeriSysCallerStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      return process_sys_call( );
      break;
  }
}

int
VeriSysCallerStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  if( _arg != NULL )
  {
    //_arg->clean_up( );
    _arg->set_scope( scope( ) );
    mstack.push_back( _arg );
  }

  return OK;
}

int
VeriSysCallerStmt::process_sys_call( void )
{
  return OK;
}

int
VeriSysCallerStmt::push_for_replacement( NodeVec& mstack )
{
  if( _arg != NULL )
    mstack.push_back( _arg );

  return OK;
}

int
VeriSysCallerStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriSysCallerStmt *tmp = new VeriSysCallerStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _arg != NULL )
  {
    tmp->_arg = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /********************
     * Caller Statement *
     ********************/

void
VeriCallerStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriCallerStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _caller );
  iqueue.push( depth );
  return OK;
}

int
VeriCallerStmt::pretty_dot_label( Ofstream& ofile, int depth )
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

  return OK;
}

int
VeriCallerStmt::check_child_validation( void )
{
  return _caller->check_child_validation( );
}

int
VeriCallerStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      return process_caller( );
      break;
  }
}

int
VeriCallerStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  if( _caller != NULL )
  {
    //_caller->clean_up( );
    _caller->set_scope( scope( ) );
    mstack.push_back( _caller );
  }

  return OK;
}

int
VeriCallerStmt::process_caller( void )
{
  return OK;
}

int
VeriCallerStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _caller );
  return OK;
}

int
VeriCallerStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriCallerStmt *tmp = new VeriCallerStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_caller = *(--itl);
    (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*****************************
     * Sequetial-Block Statement *
     *****************************/

void
VeriSeqBlock::clean_up( void )
{
  _class_symbol=nullptr;_base_class=nullptr;_class_state=0;
  _class_origin=nullptr;_class_bindings.clear();_specializations.clear();
  set_pstatus( vSTART_S );
}

int
VeriSeqBlock::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _decl_list != NULL )
  {
    mqueue.push( _decl_list );
    iqueue.push( depth );
  }

  if( _stmt_list != NULL )
  {
    mqueue.push( _stmt_list );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriSeqBlock::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _decl_list );
  ofile << dot_str_conn( idx(), _stmt_list );

  return OK;
}

int
VeriSeqBlock::check_child_validation( void )
{
  int re;

  if( _decl_list != NULL )
  {
    if( _decl_list->detail_type() != (_class_declaration?vsSTMT_MOD_ITEM_LIST:vsDECL_BLOCK_ITEM_DECL_LIST) )
    {
      veri_err->append_err( ERR_ERROR, _decl_list->line(), _decl_list->col(),
                            vCHILD_TYPE_SEQ_BLOCK_STMT );
      return vCHILD_TYPE_SEQ_BLOCK_STMT;
    }

    re = _decl_list->check_child_validation();
    if( re != OK )
      return re;
  }

  if( _stmt_list != NULL )
  {
    if( _stmt_list->detail_type() != vsSTMT_STMT_LIST )
    {
      veri_err->append_err( ERR_ERROR, _stmt_list->line(), _stmt_list->col(),
                            vCHILD_TYPE_SEQ_BLOCK_STMT );
      return vCHILD_TYPE_SEQ_BLOCK_STMT;
    }

    re = VeriStmt::check_child_stmt( _stmt_list,
                                     vCHILD_TYPE_SEQ_BLOCK_STMT );
    if( re != OK )
      return re;
  }
  return OK;
}

int
VeriSeqBlock::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  if(_class_declaration&&_class_state==2)return OK;
  switch( pstatus( ) )
  {
    case vSTART_S :
      if(generic_class()){register_class_symbol();_class_state=2;set_pstatus(vEND_S);return OK;}
      if(_class_declaration)_class_state=1;
      process_label( );
      set_pstatus( vEND_S );
      if(_class_declaration)mstack.push_back(this);
      return push_children( mstack );
      break;

    default:
      if(_class_declaration){
        veri_validate_extern_methods(this);_class_state=2;
        if(_decl_list)for(auto* item:static_cast<VeriModuleItemList*>(_decl_list)->item_list())
          if(item->detail_type()==vsDECL_CONSTRAINT)static_cast<VeriConstraintDecl*>(item)->bind();
      }
      return end_label( );
      break;
  }
}

int
VeriSeqBlock::process_label( void )
{
  if(_class_declaration) {
    register_class_symbol();
    set_scope(scope()->append_scope(_label,vNAMED_BLOCK_SCOPE));
    scope()->set_class_owner(this);
    for(const auto& binding:_class_bindings)scope()->insert(binding.first,binding.second);
    if(!_base_name.empty()||_base_type) {
      const auto& name=_base_type?static_cast<VeriTypeExp*>(_base_type)->name():_base_name;
      auto* declared=scope()->value_within_module(name);
      if(!declared||declared->tok_type()!=vtTYPE||!veri_class_type(declared))
        throw std::runtime_error("extends requires a previously declared class: "+name);
      auto* symbol=_base_type?static_cast<VeriTypeExp*>(_base_type)->resolve(scope()):veri_resolve_type(scope(),_base_name);
      _base_class=veri_class_type(symbol);
      if(_base_class&&_base_class->process_type())throw std::runtime_error("cannot extend the built-in process class");
      if(!_base_class)throw std::runtime_error("extends requires a previously declared class: "+_base_name);
      std::set<VeriSeqBlock*> ancestors{this};
      for(auto* base=_base_class;base;base=base->base_class())
        if(!ancestors.insert(base).second)throw std::runtime_error("cyclic class inheritance: "+_label);
      _base_class->ensure_class_elaborated();
    }
    if(_base_class) {
      scope()->set_class_base(_base_class->scope());
      // Even an implicit constructor calls super.new. A local constructor
      // therefore makes its class inextensible.
      veri_check_class_access(_base_class->scope()->value_same_level("new"),scope());
      auto* base=new VeriVar(veri_parser->next_id(),line(),col(),"super",vpNO_IO,vvCLASS,IS_FALSE,vpSCALAR,0,0,63,0,this,nullptr,0,birth_mod());
      veri_parser->insert_node(base);base->set_class_type(_base_class);base->set_scope(scope());base->set_father(this);scope()->insert("super",base);
    }
    auto* self=new VeriVar(veri_parser->next_id(),line(),col(),"this",vpNO_IO,vvCLASS,IS_FALSE,vpSCALAR,0,0,63,0,this,nullptr,0,birth_mod());
    veri_parser->insert_node(self);self->set_class_type(this);self->set_scope(scope());self->set_father(this);scope()->insert("this",self);
    return OK;
  }
  if( _label.empty() && _decl_list != NULL )
    set_scope( scope()->append_scope( "", vNAMED_BLOCK_SCOPE ) );
  if( !_label.empty() )
  {
    set_scope( scope()->append_scope( _label, vNAMED_BLOCK_SCOPE ) );
    VeriLabelId * label_id = new VeriLabelId(  veri_parser->next_id(),
                                              _label_line, _label_col,
                                              _label, this, birth_mod() );
    veri_parser->insert_node( label_id );
    scope()->insert( _label, label_id );
  }
  return OK;
}

void VeriSeqBlock::register_class_symbol() {
    auto* previous=scope()->value_same_level(_label);
    if(previous&&(previous->tok_type()!=vtTYPE||veri_class_type(previous)!=this))
      throw std::runtime_error("duplicate class declaration: "+_label);
    if(previous)_class_symbol=static_cast<VeriVar*>(previous);
    else {
      _class_symbol=new VeriVar(veri_parser->next_id(),line(),col(),_label,vpNO_IO,vvCLASS,IS_FALSE,vpSCALAR,0,0,63,0,this,nullptr,0,birth_mod(),vtTYPE);
      veri_parser->insert_node(_class_symbol);_class_symbol->set_class_type(this);_class_symbol->set_scope(scope());_class_symbol->set_father(this);
      scope()->insert(_label,_class_symbol);
    }
 }

void VeriSeqBlock::ensure_class_elaborated() {
  if(_class_state)return;
  NodeVec stack{this};String help;
  while(!stack.empty()) {
    auto* node=stack.back();stack.pop_back();
    int status=node->process_node_2nd(stack,help);
    if(status==vSEARCH_DECL)status=node->process_node_2nd(stack,help);
    if(status!=OK)throw std::runtime_error("class elaboration failed: "+_label+"\n"+veri_parser->get_err_info());
  }
}

int
VeriSeqBlock::push_children( NodeVec& mstack )
{
  if( _stmt_list != NULL )
  {
    //_stmt_list->clean_up( );
    _stmt_list->set_scope( scope( ) );
    mstack.push_back( _stmt_list );
  }

  if( _decl_list != NULL )
  {
    //_decl_list->clean_up( );
    _decl_list->set_scope( scope( ) );
    mstack.push_back( _decl_list );
  }
  return OK;
}

int
VeriSeqBlock::end_label( void )
{
  if( !_label.empty() || _decl_list != NULL )
    scope()->finish_scope( );
  return OK;
}

int
VeriSeqBlock::push_for_replacement( NodeVec& mstack )
{
  if(_class_parameters)mstack.push_back(_class_parameters);
  if(_base_type)mstack.push_back(_base_type);
  if( _decl_list != NULL )
    mstack.push_back( _decl_list );

  if( _stmt_list != NULL )
    mstack.push_back( _stmt_list );

  return OK;
}

int
VeriSeqBlock::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriSeqBlock *tmp = new VeriSeqBlock( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _stmt_list != NULL )
  {
    tmp->_stmt_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _decl_list != NULL )
  {
    tmp->_decl_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if(_base_type){itl=inl;--itl;tmp->_base_type=*itl;(*itl)->set_father(tmp);node_list.erase(itl);}
  if(_class_parameters){itl=inl;--itl;tmp->_class_parameters=*itl;(*itl)->set_father(tmp);node_list.erase(itl);}
  *inl = tmp;
  return OK;
}

    /**************************************
     * Function-Sequetial-Block Statement *
     *************************************/

void
VeriFuncSeqBlock::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncSeqBlock::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _decl_list != NULL )
  {
    mqueue.push( _decl_list );
    iqueue.push( depth );
  }

  if( _stmt_list != NULL )
  {
    mqueue.push( _stmt_list );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriFuncSeqBlock::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _decl_list );
  ofile << dot_str_conn( idx(), _stmt_list );

  return OK;
}

int
VeriFuncSeqBlock::check_child_validation( void )
{
  int re;
  if( _decl_list != NULL )
  {
    if( _decl_list->detail_type() != vsSTMT_BLOCK_ITEM_DECL_LIST )
    {
      veri_err->append_err( ERR_ERROR, _decl_list->line(), _decl_list->col(),
                            vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT );
      return vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT;
    }

    re = _decl_list->check_child_validation();
    if( re != OK )
      return re;
  }

  if( _stmt_list != NULL )
  {
    if( _stmt_list->detail_type() != vsSTMT_FUNC_STMT_LIST )
    {
      veri_err->append_err( ERR_ERROR, _stmt_list->line(), _stmt_list->col(),
                            vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT );
      return vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT;
    }

    return VeriStmt::check_child_stmt( _stmt_list,
                                       vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT );
  }
  return OK;
}

int
VeriFuncSeqBlock::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  switch( pstatus( ) )
  {
    case vSTART_S :
      process_label( );
      set_pstatus( vEND_S );
      return push_children( mstack );
      break;

    default:
      return end_label( );
      break;
  }
}

int
VeriFuncSeqBlock::process_label( void )
{
  if( !_label.empty() )
  {
    set_scope( scope()->append_scope( _label, vNAMED_BLOCK_SCOPE ) );
    VeriLabelId * label_id = new VeriLabelId(  veri_parser->next_id(),
                                              _label_line, _label_col,
                                              _label, this, birth_mod() );
    veri_parser->insert_node( label_id );
    scope()->insert( _label, label_id );
  }
  return OK;
}

int
VeriFuncSeqBlock::push_children( NodeVec& mstack )
{
  if( _stmt_list != NULL )
  {
    //_stmt_list->clean_up( );
    _stmt_list->set_scope( scope( ) );
    mstack.push_back( _stmt_list );
  }

  if( _decl_list != NULL )
  {
    //_decl_list->clean_up( );
    _decl_list->set_scope( scope( ) );
    mstack.push_back( _decl_list );
  }
  return OK;
}

int
VeriFuncSeqBlock::end_label( void )
{
  if( !_label.empty() )
    scope()->finish_scope( );
  return OK;
}

int
VeriFuncSeqBlock::push_for_replacement( NodeVec& mstack )
{
  if( _decl_list != NULL )
    mstack.push_back( _decl_list );

  if( _stmt_list != NULL )
    mstack.push_back( _stmt_list );

  return OK;
}

int
VeriFuncSeqBlock::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncSeqBlock *tmp = new VeriFuncSeqBlock( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _stmt_list != NULL )
  {
    tmp->_stmt_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _decl_list != NULL )
  {
    tmp->_decl_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************
     * Statement-List Statement *
     ****************************/

void
VeriStmtList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriStmtList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriStmtList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriStmtList::check_child_validation( void )
{
  int re;
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    re = VeriStmt::check_child_stmt( *it, vCHILD_TYPE_STMT_LIST_STMT );
    if( re != OK )
      return re;
  }
  return OK;
}

int
VeriStmtList::check_last_child_validation( void )
{
  VeriNode * node = _stmt_list.back();
  return VeriStmt::check_child_stmt( node, vCHILD_TYPE_STMT_LIST_STMT );
}

int
VeriStmtList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriStmtList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _stmt_list.rbegin();
  for( ; it != _stmt_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriStmtList::do_nothing( void )
{
  return OK;
}

int
VeriStmtList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriStmtList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriStmtList *tmp = new VeriStmtList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    tmp->_stmt_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /*************************************
     * Function-Statement-List Statement *
     *************************************/

void
VeriFuncStmtList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncStmtList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriFuncStmtList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriFuncStmtList::check_child_validation( void )
{
  int re;
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    re = VeriStmt::check_child_stmt( *it, vCHILD_TYPE_FUNC_STMT_LIST_STMT );
    if( re != OK )
      return re;
  }
  return OK;
}

int
VeriFuncStmtList::check_last_child_validation( void )
{
  VeriNode * node = _stmt_list.back();
  return VeriStmt::check_child_stmt( node, vCHILD_TYPE_FUNC_STMT_LIST_STMT );
}

int
VeriFuncStmtList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriFuncStmtList::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _stmt_list.rbegin();
  for( ; it != _stmt_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }
  return OK;
}

int
VeriFuncStmtList::do_nothing( void )
{
  return OK;
}

int
VeriFuncStmtList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriFuncStmtList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncStmtList *tmp = new VeriFuncStmtList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _stmt_list.begin();
  for( ; it != _stmt_list.end(); ++it )
  {
    tmp->_stmt_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /******************************************
     * Function-Blocking-Assignment Statement *
     ******************************************/

void
VeriFuncBlockAssignStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriFuncBlockAssignStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _lval );
  mqueue.push( _rval );
  iqueue.push( depth );
  iqueue.push( depth );
  return OK;
}

int
VeriFuncBlockAssignStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriFuncBlockAssignStmt::check_child_validation( void )
{
  if(    _lval == NULL || _rval == NULL
      || _lval->tok_type() != vtEXP
      || _rval->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_FUNC_BLOCK_STMT );
    return  vCHILD_TYPE_FUNC_BLOCK_STMT;
  }

  int re = VeriStmt::check_func_child_exp_validation( _rval,
                                        vCHILD_TYPE_FUNC_BLOCK_STMT );
  if( re != OK )
    return re;

  switch( _lval->detail_type() )
  {
    case veEXP_BIN:
      if(veri_streaming(_lval))break;
      veri_err->append_err(ERR_ERROR,_lval->line(),_lval->col(),vCHILD_TYPE_FUNC_BLOCK_STMT);
      return vCHILD_TYPE_FUNC_BLOCK_STMT;

    case veEXP_PRI :
    case veEXP_MEMBER :
    case veEXP_ARRAY :
      break;

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_lval);
      if( mexp->multi_type() != vemCONCAT_EXP )
      {
        veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_FUNC_BLOCK_STMT );
        return vCHILD_TYPE_FUNC_BLOCK_STMT;
      }
      break;
    }

    default:
      veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_FUNC_BLOCK_STMT );
      return vCHILD_TYPE_FUNC_BLOCK_STMT;
  }

  return OK;
}

int
VeriFuncBlockAssignStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      return process_func_blocking_assign( );
      break;
  }
}

int
VeriFuncBlockAssignStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_rval->clean_up( );
  _rval->set_scope( scope() );
  mstack.push_back( _rval );

  //_lval->clean_up( );
  _lval->set_scope( scope() );
  mstack.push_back( _lval );
  return OK;
}

int
VeriFuncBlockAssignStmt::process_func_blocking_assign( void )
{
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
         
        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
            if( static_cast<VeriVar *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          case vtGENVAR :
          case vtPARAM :
          case vtTFVAR :
          case vtFUNC :
            break;
       
          case vtINT :
            if( static_cast<VeriInt *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          default:
            veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
            return vSEC_PRI_NOT_OTHER;
        }

        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
          {
            VeriVar *var = static_cast<VeriVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( var->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            var->set_one_num( dummy_dimen, IS_TRUE, 0, 0, num );
            break;
          }

          case vtFUNC :
          {
            VeriFunc *func_ret = static_cast<VeriFunc *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( func_ret->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            func_ret->set_val( num );
            break;
          }

          case vtTFVAR :
          {
            VeriTfVar *tfvar = static_cast<VeriTfVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( tfvar->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            tfvar->set_val( num );
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
VeriFuncBlockAssignStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _lval );
  mstack.push_back( _rval );
  return OK;
}

int
VeriFuncBlockAssignStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriFuncBlockAssignStmt *tmp = new VeriFuncBlockAssignStmt( idx, this );

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

    /*********************************
     * Blocking-Assignment Statement *
     *********************************/

void
VeriBlockStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriBlockStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _lval );
  iqueue.push( depth );

  if( _event != NULL )
  {
    mqueue.push( _event );
    iqueue.push( depth );
  }

  mqueue.push( _rval );
  iqueue.push( depth );
  return OK;
}

int
VeriBlockStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _event );
  ofile << dot_str_conn( idx(), _rval );

  return OK;
}

int
VeriBlockStmt::check_child_validation( void )
{
  if(    _lval == NULL || _rval == NULL
      || _lval->tok_type() != vtEXP
      || _rval->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_BLOCK_STMT );
    return  vCHILD_TYPE_BLOCK_STMT;
  }

  int re = VeriStmt::check_func_child_exp_validation( _rval,
                                          vCHILD_TYPE_BLOCK_STMT );
  if( re != OK )
    return re;

  switch( _lval->detail_type() )
  {
    case veEXP_BIN:
      if(veri_streaming(_lval))break;
      veri_err->append_err(ERR_ERROR,_lval->line(),_lval->col(),vCHILD_TYPE_BLOCK_STMT);
      return vCHILD_TYPE_BLOCK_STMT;

    case veEXP_PRI :
    case veEXP_MEMBER :
    case veEXP_ARRAY :
      break;

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_lval);
      if( mexp->multi_type() != vemCONCAT_EXP )
      {
        veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_BLOCK_STMT );
        return vCHILD_TYPE_BLOCK_STMT;
      }
      break;
    }

    default:
      veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_BLOCK_STMT );
      return vCHILD_TYPE_BLOCK_STMT;
  }

  if( _event != NULL )
  {
    if( _event->detail_type() != vsSTMT_EVENT && _event->detail_type() != veEXP_DELAY
        && !(_event->detail_type()==vsSTMT_LOOP&&static_cast<VeriLoopStmt*>(_event)->kind()==VeriLoopStmt::REPEAT) )
    {
      veri_err->append_err( ERR_ERROR, _event->line(), _event->col(),
                            vCHILD_TYPE_BLOCK_STMT );
      return vCHILD_TYPE_BLOCK_STMT;
    }
  }
  return OK;
}

int
VeriBlockStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      return process_blocking_assignment( );
      break;
  }
}

int
VeriBlockStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_rval->clean_up( );
  _rval->set_scope( scope( ) );
  mstack.push_back( _rval );

  if( _event != NULL )
  {
    //_event->clean_up( );
    _event->set_scope( scope( ) );
    mstack.push_back( _event );
  }

  //_lval->clean_up( );
  _lval->set_scope( scope( ) );
  mstack.push_back( _lval );

  return OK;
}

int
VeriBlockStmt::process_blocking_assignment( void )
{
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
         
        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
            if( static_cast<VeriVar *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          case vtGENVAR :
          case vtPARAM :
          case vtTFVAR :
          case vtFUNC :
            break;
       
          case vtINT :
            if( static_cast<VeriInt *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          default:
            veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
            return vSEC_PRI_NOT_OTHER;
        }

        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
            break;

          case vtFUNC :
          {
            VeriFunc *func_ret = static_cast<VeriFunc *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( func_ret->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            func_ret->set_val( num );
            break;
          }

          case vtTFVAR :
          {
            VeriTfVar *tfvar = static_cast<VeriTfVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( tfvar->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            tfvar->set_val( num );
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
  }
  return OK;
}

int
VeriBlockStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _lval );

  if( _event != NULL )
    mstack.push_back( _event );

  mstack.push_back( _rval );

  return OK;
}

int
VeriBlockStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriBlockStmt *tmp = new VeriBlockStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_rval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _event != NULL )
  {
    tmp->_event = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_lval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /*************************************
     * Non-Blocking-Assignment Statement *
     *************************************/

void
VeriNonBlockStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriNonBlockStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _lval );
  iqueue.push( depth );

  if( _event != NULL )
  {
    mqueue.push( _event );
    iqueue.push( depth );
  }

  mqueue.push( _rval );
  iqueue.push( depth );
  return OK;
}

int
VeriNonBlockStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _event );
  ofile << dot_str_conn( idx(), _rval );

  return OK;
}

int
VeriNonBlockStmt::check_child_validation( void )
{
  if(    _lval == NULL || _rval == NULL
      || _lval->tok_type() != vtEXP
      || _rval->tok_type() != vtEXP )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_NON_BLOCK_STMT );
    return  vCHILD_TYPE_NON_BLOCK_STMT;
  }

  int re = VeriStmt::check_func_child_exp_validation( _rval,
                                          vCHILD_TYPE_NON_BLOCK_STMT );
  if( re != OK )
    return re;

  switch( _lval->detail_type() )
  {
    case veEXP_BIN:
      if(veri_streaming(_lval))break;
      veri_err->append_err(ERR_ERROR,_lval->line(),_lval->col(),vCHILD_TYPE_NON_BLOCK_STMT);
      return vCHILD_TYPE_NON_BLOCK_STMT;

    case veEXP_PRI :
    case veEXP_MEMBER :
    case veEXP_ARRAY :
      break;

    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(_lval);
      if( mexp->multi_type() != vemCONCAT_EXP )
      {
        veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_NON_BLOCK_STMT );
        return vCHILD_TYPE_NON_BLOCK_STMT;
      }
      break;
    }

    default:
      veri_err->append_err( ERR_ERROR, _lval->line(), _lval->col(),
                            vCHILD_TYPE_NON_BLOCK_STMT );
      return vCHILD_TYPE_NON_BLOCK_STMT;
  }

  if( _event != NULL )
  {
    if( _event->detail_type() != vsSTMT_EVENT
        && _event->detail_type() != veEXP_DELAY
        && !(_event->detail_type()==vsSTMT_LOOP&&static_cast<VeriLoopStmt*>(_event)->kind()==VeriLoopStmt::REPEAT) )
    {
      veri_err->append_err( ERR_ERROR, _event->line(), _event->col(),
                            vCHILD_TYPE_NON_BLOCK_STMT );
      return vCHILD_TYPE_NON_BLOCK_STMT;
    }
  }
  return OK;
}

int
VeriNonBlockStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      return process_non_blocking_assignment( );
      break;
  }
}

int
VeriNonBlockStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_rval->clean_up( );
  _rval->set_scope( scope( ) );
  mstack.push_back( _rval );

  if( _event != NULL )
  {
    //_event->clean_up( );
    _event->set_scope( scope( ) );
    mstack.push_back( _event );
  }

  //_lval->clean_up( );
  _lval->set_scope( scope( ) );
  mstack.push_back( _lval );

  return OK;
}

int
VeriNonBlockStmt::process_non_blocking_assignment( void )
{
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
         
        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
            if( static_cast<VeriVar *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          case vtGENVAR :
          case vtPARAM :
          case vtTFVAR :
          case vtFUNC :
            break;
       
          case vtINT :
            if( static_cast<VeriInt *>(pexp->var())->range_depth() != 0 )
            {
              veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
              return vSEC_PRI_NOT_OTHER;
            }
            break;
       
          default:
            veri_err->append_err( ERR_ERROR, pexp, vSEC_PRI_NOT_OTHER );
            return vSEC_PRI_NOT_OTHER;
        }

        switch( pexp->var()->tok_type( ) )
        {
          case vtVAR :
            break;

          case vtFUNC :
          {
            VeriFunc *func_ret = static_cast<VeriFunc *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( func_ret->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            func_ret->set_val( num );
            break;
          }

          case vtTFVAR :
          {
            VeriTfVar *tfvar = static_cast<VeriTfVar *>(pexp->var());
            VeriNum *num = new VeriNum( veri_parser->next_id(),
                                        rval->calc_value() );
            veri_parser->insert_node( num );
            num->truncate_assign( tfvar->dlen() );
            num->set_father( this );
            num->set_scope( scope() );
            tfvar->set_val( num );
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
  }
  return OK;
}

int
VeriNonBlockStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _lval );

  if( _event != NULL )
    mstack.push_back( _event );

  mstack.push_back( _rval );
  return OK;
}

int
VeriNonBlockStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriNonBlockStmt *tmp = new VeriNonBlockStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_rval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _event != NULL )
  {
    tmp->_event = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_lval = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /***********************************
     * Continuous-Assignment Statement *
     ***********************************/

void
VeriContAssignStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriContAssignStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _delay != NULL )
  {
    mqueue.push( _delay );
    iqueue.push( depth );
  }

  if( _drive_strength != NULL )
  {
    mqueue.push( _drive_strength );
    iqueue.push( depth );
  }

  mqueue.push( _exp );
  iqueue.push( depth );
  return OK;
}

int
VeriContAssignStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _delay );
  ofile << dot_str_conn( idx(), _drive_strength );
  ofile << dot_str_conn( idx(), _exp );

  return OK;
}

int
VeriContAssignStmt::check_child_validation( void )
{
  if(    _delay == NULL
      || _drive_strength == NULL
      || _exp == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_CONT_ASSIGN_STMT );
    return vCHILD_TYPE_CONT_ASSIGN_STMT;
  }
      
  if( _delay->detail_type() != veEXP_DELAY )
  {
    veri_err->append_err( ERR_ERROR, _delay->line(), _delay->col(),
                          vCHILD_TYPE_CONT_ASSIGN_STMT );
    return vCHILD_TYPE_CONT_ASSIGN_STMT;
  }

  if( _drive_strength->detail_type() != veEXP_DRIVE )
  {
    veri_err->append_err( ERR_ERROR, _drive_strength->line(),
                          _drive_strength->col(),
                          vCHILD_TYPE_CONT_ASSIGN_STMT );
    return vCHILD_TYPE_CONT_ASSIGN_STMT;
  }

  if( _exp->detail_type() != veEXP_MULTI )
  {
    veri_err->append_err( ERR_ERROR, _exp->line(), _exp->col(),
                          vCHILD_TYPE_CONT_ASSIGN_STMT );
    return vCHILD_TYPE_CONT_ASSIGN_STMT;
  }

  return OK;
}

int
VeriContAssignStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriContAssignStmt::push_children( NodeVec& mstack )
{
  NodeVec assignments{_exp};
  while(!assignments.empty()) {
    auto* item=assignments.back();assignments.pop_back();
    if(item->detail_type()==veEXP_MULTI)
      for(auto* assignment:static_cast<VeriMultiExp*>(item)->exp())assignments.push_back(assignment);
    else if(item->detail_type()==veEXP_ASSIGN)
      veri_declare_implicit_wire(static_cast<VeriAssignExp*>(item)->lval(),scope());
  }
  mstack.push_back( this );

  //_exp->clean_up( );
  _exp->set_scope( scope( ) );
  mstack.push_back( _exp );

  if( _drive_strength != NULL )
  {
    //_drive_strength->clean_up( );
    _drive_strength->set_scope( scope( ) );
    mstack.push_back( _drive_strength );
  }

  if( _delay != NULL )
  {
    //_delay->clean_up( );
    _delay->set_scope( scope( ) );
    mstack.push_back( _delay );
  }

  return OK;
}

int
VeriContAssignStmt::do_nothing( void )
{
  return OK;
}

int
VeriContAssignStmt::push_for_replacement( NodeVec& mstack )
{
  if( _drive_strength != NULL )
    mstack.push_back( _drive_strength );

  if( _delay != NULL )
    mstack.push_back( _delay );

  mstack.push_back( _exp );

  return OK;
}

int
VeriContAssignStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriContAssignStmt *tmp = new VeriContAssignStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_exp = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );
  itl = inl;

  if( _delay != NULL )
  {
    tmp->_delay = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _drive_strength != NULL )
  {
    tmp->_drive_strength = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /****************************
     * Initialization Statement *
     ****************************/

void
VeriInitStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriInitStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriInitStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriInitStmt::check_child_validation( void )
{
  return VeriStmt::check_child_stmt( _stmt, vCHILD_TYPE_INIT_STMT );
}

int
VeriInitStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriInitStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );

  return OK;
}

int
VeriInitStmt::do_nothing( void )
{
  return OK;
}

int
VeriInitStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _stmt );
  return OK;
}

int
VeriInitStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriInitStmt *tmp = new VeriInitStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************
     * Always Statement *
     ********************/

void
VeriAlwaysStmt::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriAlwaysStmt::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriAlwaysStmt::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _stmt );

  return OK;
}

int
VeriAlwaysStmt::check_child_validation( void )
{
  return VeriStmt::check_child_stmt( _stmt, vCHILD_TYPE_ALWAYS_STMT );
}

int
VeriAlwaysStmt::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriAlwaysStmt::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );

  return OK;
}

int
VeriAlwaysStmt::do_nothing( void )
{
  return OK;
}

int
VeriAlwaysStmt::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _stmt );
  return OK;
}

int
VeriAlwaysStmt::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriAlwaysStmt *tmp = new VeriAlwaysStmt( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /******************************
     * Module-Item-List Statement *
     ******************************/

void
VeriModuleItemList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriModuleItemList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriModuleItemList::pretty_dot_label( Ofstream& ofile, int depth )
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
  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriModuleItemList::check_child_validation( void )
{
  return OK;
}

int
VeriModuleItemList::check_last_child_validation( void )
{
  return OK;
}

int
VeriModuleItemList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriModuleItemList::push_children( NodeVec& mstack )
{
  for(auto* item:_item_list)if(item->detail_type()==vsDECL_CLOCKING) {
    auto* clock=static_cast<VeriClocking*>(item);clock->set_scope(scope());
    auto* old=scope()->value_same_level(clock->name);
    if(old&&old!=clock)throw std::runtime_error("duplicate clocking declaration: "+clock->name);
    if(!old&&scope()->insert(clock->name,clock)!=OK)throw std::runtime_error("cannot declare clocking: "+clock->name);
  }
  veri_bind_forward_classes(_item_list);
  veri_register_sequences(_item_list,scope());
  mstack.push_back( this );


  NodeList::reverse_iterator it = _item_list.rbegin();
  for( ; it != _item_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_scope( scope( ) );
    // Runtime bodies can reference declarations and instances appearing later,
    // including an absolute path through a sibling hierarchy. Bind them after
    // the complete selected hierarchy has been elaborated, never in text order.
    if((*it)->detail_type()==vsSTMT_ALWAYS||(*it)->detail_type()==vsSTMT_INIT) {
      veri_parser->defer_semantic(*it);continue;
    }
    mstack.push_back( *it );
  }

  return OK;
}

int
VeriModuleItemList::do_nothing( void )
{
  return OK;
}

int
VeriModuleItemList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriModuleItemList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriModuleItemList *tmp = new VeriModuleItemList( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
  {
    tmp->_item_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

};

rtl::VeriNode* rtl::VeriSeqBlock::class_member(const std::string& name) {auto* own=scope()->value_same_level(name);return own?own:_base_class?_base_class->class_member(name):nullptr;}
