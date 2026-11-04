/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_inst.cpp
 * Summary  : verilog syntax analyzer :: instantiation
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */
#include <assert.h>

#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_symbol_table.hpp"
#include "veri_tfmg.hpp"

#include "veri_num.hpp"
#include "veri_exp.hpp"
#include "veri_stmt.hpp"
#include "veri_decl.hpp"
#include "veri_inst.hpp"
#include "veri_var.hpp"

#include "veri_module.hpp"
#include "veri_parser.hpp"

namespace rtl
{

int
VeriInst::check_child_exp_validation( VeriNode *child, int flag )
{
  if( child != NULL && child->tok_type() == vtEXP )
  {
    switch( child->detail_type() )
    {
      case veEXP_DUMMY_PORT :
      case veEXP_EVENT   :
      case veEXP_RANGE   :
      case veEXP_PORT_REF :
      case veEXP_NAMED_PARAM :
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
      {
        veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
        return flag;
        break;
      }

      case veEXP_MULTI :
        // A concatenation is one expression; a comma list is not.
        if( static_cast<VeriMultiExp *>(child)->multi_type() != vemCONCAT_EXP )
        {
          veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );
          return flag;
        }
        break;

      default:
        break;
    }
    return OK;
  }
  
  if( child == NULL )
    veri_err->append_err( ERR_ERROR, line(), col(), flag );
  else
    veri_err->append_err( ERR_ERROR, child->line(), child->col(), flag );

  return flag;
}

    /*******************
     * Dummy-Statement *
     *******************/

void
VeriDummyInst::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriDummyInst::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriDummyInst::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriDummyInst::check_child_validation( void )
{
  return OK;
}

int
VeriDummyInst::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriDummyInst::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriDummyInst::replace_node( Uint idx, NodeList& /*node_list*/,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDummyInst *tmp = new VeriDummyInst( idx, this );

  // begin replacement

  *inl = tmp;
  return OK;
}

    /*******************
     * Module-Instance *
     *******************/

void
VeriModInstance::clean_up( void )
{
  set_pstatus( vSTART_S );

  _hive = NULL;
}

int
VeriModInstance::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  mqueue.push( _inst_name );
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

  return OK;
}

int
VeriModInstance::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _inst_name );
  ofile << dot_str_conn( idx(), _arg );
  ofile << dot_str_conn( idx(), _hive );

  return OK;
}

int
VeriModInstance::check_child_validation( void )
{
  if( _inst_name == NULL )
  {
    veri_err->append_err( ERR_ERROR, _inst_name->line(),
                    _inst_name->col(), vCHILD_TYPE_MOD_INSTANCE );
    return vCHILD_TYPE_MOD_INSTANCE;
  }

  switch( _inst_name->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ARRAY :
      break;

    default:
      veri_err->append_err( ERR_ERROR, _inst_name->line(),
                    _inst_name->col(), vCHILD_TYPE_MOD_INSTANCE );
      return vCHILD_TYPE_MOD_INSTANCE;
  }

  if( _arg != NULL )
  {
    if( _arg->detail_type() != veEXP_MULTI )
    {
      veri_err->append_err( ERR_ERROR, _arg->line(),
                    _arg->col(), vCHILD_TYPE_MOD_INSTANCE );
      return vCHILD_TYPE_MOD_INSTANCE;
    }

    VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_arg);
    switch( mexp->multi_type() )
    {
      case vemCOMMA_EXP :
      case vemPORT_EXP :
      case vemPORT_INST_EXP :
        break;

      default:
        veri_err->append_err( ERR_ERROR, _arg->line(),
                    _arg->col(), vCHILD_TYPE_MOD_INSTANCE );
        return vCHILD_TYPE_MOD_INSTANCE;
        break;
    }
  }

  return OK;
}

int
VeriModInstance::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
      re = reg_mod_inst( );
      if( re != OK ) return re;
      return unfolding( mstack );
      break;
  }
}

int
VeriModInstance::push_children( NodeVec& mstack )
{
  // Bare terminal identifiers implicitly declare scalar wires. Keep this
  // restricted to module scope; unknown names in procedural expressions,
  // hierarchy, parameter overrides and terminal selects remain errors.
  if(_arg&&scope()->table_type()==vMOD_SCOPE) {
    for(auto* argument:static_cast<VeriMultiExp*>(_arg)->exp()) {
      if(argument->detail_type()==veEXP_NAMED_PARAM)argument=static_cast<VeriNamedParamExp*>(argument)->port_exp();
      if(argument&&argument->detail_type()==veEXP_MULTI) {
        auto& values=static_cast<VeriMultiExp*>(argument)->exp();
        if(values.size()!=1)continue;argument=values.front();
      }
      veri_declare_implicit_wire(argument,scope());
    }
  }
  mstack.push_back( this );

  if( _arg != NULL )
  {
    //_arg->clean_up( );
    _arg->set_scope( scope() );
    mstack.push_back( _arg );
  }

  //_inst_name->clean_up( );
  _inst_name->set_is_decl( IS_TRUE );
  _inst_name->set_is_trash( IS_TRUE );
  _inst_name->set_scope( scope() );
  mstack.push_back( _inst_name );

  return OK;
}

int
VeriModInstance::reg_mod_inst( )
{
  IList dimen;
  switch( _inst_name->detail_type() )
  {
    case veEXP_PRI :
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(_inst_name);
      _name = pexp->str();
      break;
    }

    case veEXP_ARRAY :
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(_inst_name);
      _name = aexp->name();
      break;
    }

    default:
      break;
  }

  /* TODO: array module instantiations, means modulea d1[1](a,b,c), d1[2](b,c,d)... */
  VeriNode * node = scope()->value_within_module( _name );
  if( node != NULL )
  {
    veri_err->append_err( ERR_ERROR, this, vMOD_INST_REDEFINE );
    return vMOD_INST_REDEFINE;
  }

  VeriModInstantiation *mod_inst_father
    = static_cast<VeriModInstantiation *>(father());

  VeriModInst * symbol = new VeriModInst( veri_parser->next_id(),
                                          line(), col(),
                                          _name, this, mod_inst_father,
                                          dimen, birth_mod() ); 
  veri_parser->insert_node( symbol );
  symbol->set_scope( scope( ) );
  symbol->set_father( this );

  scope()->insert( _name, symbol );
  return OK;
}

int
VeriModInstance::unfolding( NodeVec& mstack )
{
  if( _hive != NULL )
    return vSEC_MOD_REINSTANTIATED;

  VeriModInstantiation *mod_inst
    = static_cast<VeriModInstantiation *>(father());
  if( mod_inst->inst_mod() == NULL )
    return OK;

  NodeVec post_order;
  NodeVec BFS_order;

  BFS_order.reserve( 3997 );
  if(mod_inst->inst_mod()->is_interface()&&_inst_name&&_inst_name->detail_type()==veEXP_ARRAY)
    throw std::runtime_error("interface instance arrays are not supported yet");
  BFS_order.push_back( mod_inst->inst_mod() );
  VeriNode *tmp = mod_inst->inst_mod();

  while( !BFS_order.empty( ) )
  {
    tmp = BFS_order.back( );
    BFS_order.pop_back( );
    post_order.push_back( tmp );
    tmp->push_for_replacement( BFS_order );
  }

  NodeList node_list( post_order.rbegin(), post_order.rend() );
  post_order.clear();
  NodeList::iterator inl = node_list.begin();
  for( ; inl != node_list.end(); ++inl )
  {
    tmp = *inl;
    tmp->replace_node( veri_parser->next_id(), node_list, inl );
    veri_parser->insert_node( *inl );
    BFS_order.push_back( *inl );
  }

  _hive = BFS_order.back();
  _hive->set_father( this );
  BFS_order.clear();

  mstack.push_back( _hive );
  _hive->set_scope( scope( ) );

  return OK;
}

int
VeriModInstance::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _inst_name );

  if( _arg != NULL )
    mstack.push_back( _arg );
  return OK;
}

int
VeriModInstance::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriModInstance *tmp = new VeriModInstance( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _arg != NULL )
  {
    tmp->_arg = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  tmp->_inst_name = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /************************
     * Module-Instantiation *
     ************************/

void
VeriModInstantiation::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriModInstantiation::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _param != NULL )
  {
    mqueue.push( _param );
    iqueue.push( depth );
  }

  NodeList::iterator it = _mod_list.begin();
  for( ; it != _mod_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }

  return OK;
}

int
VeriModInstantiation::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _mod_name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _param );
  NodeList::iterator it = _mod_list.begin();
  for( ; it != _mod_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriModInstantiation::check_child_validation( void )
{
  if( _mod_name.empty() )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_MOD_INSTANTIATION );
    return vCHILD_TYPE_MOD_INSTANTIATION;
  }

  if( _param != NULL )
  {
    if( _param->detail_type() != veEXP_MULTI )
    {
      veri_err->append_err( ERR_ERROR, _param->line(), _param->col(),
                            vCHILD_TYPE_MOD_INSTANTIATION );
      return vCHILD_TYPE_MOD_INSTANTIATION;
    }
    VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_param);
    switch( mexp->multi_type() )
    {
      case vemCOMMA_EXP :
      case vemPORT_EXP :
      case vemPORT_INST_EXP :
        break;

      default:
        veri_err->append_err( ERR_ERROR, _param->line(), _param->col(),
                            vCHILD_TYPE_MOD_INSTANTIATION );
        return vCHILD_TYPE_MOD_INSTANTIATION;
    }
  }

  NodeList::iterator it = _mod_list.begin();
  for( ; it != _mod_list.end(); ++it )
  {
    if( *it == NULL )
    {
      veri_err->append_err( ERR_ERROR, line(), col(),
                            vCHILD_TYPE_MOD_INSTANTIATION );
      return vCHILD_TYPE_MOD_INSTANTIATION;
    }
    else if ( (*it)->detail_type() != vsINST_MOD_INSTANCE )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                          vCHILD_TYPE_MOD_INSTANTIATION );
      return vCHILD_TYPE_MOD_INSTANTIATION;
    }
  }
  return OK;
}

int
VeriModInstantiation::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriModInstantiation::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  NodeList::reverse_iterator it = _mod_list.rbegin();
  for( ; it != _mod_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }

  if( _param != NULL )
  {
    //_param->clean_up( );
    _param->set_is_decl( IS_TRUE );
    _param->set_scope( scope( ) );
    mstack.push_back( _param );
  }

  return OK;
}

int
VeriModInstantiation::do_nothing( void )
{
  return OK;
}

int
VeriModInstantiation::push_for_replacement( NodeVec& mstack )
{
  if( _param != NULL )
    mstack.push_back( _param );

  NodeList::iterator it = _mod_list.begin();
  for( ; it != _mod_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriModInstantiation::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriModInstantiation *tmp = new VeriModInstantiation( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _mod_list.begin();
  for( ; it != _mod_list.end(); ++it )
  {
    tmp->_mod_list.push_front( *(--itl) );
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _param != NULL )
  {
    tmp->_param = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /*****************
     * Gate-Instance *
     *****************/

void
VeriGateInstance::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGateInstance::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _inst_name != NULL )
  {
    mqueue.push( _inst_name );
    iqueue.push( depth );
  }

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

  return OK;
}

int
VeriGateInstance::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _inst_name );
  ofile << dot_str_conn( idx(), _arg );
  ofile << dot_str_conn( idx(), _hive );

  return OK;
}

int
VeriGateInstance::check_child_validation( void )
{
  if( _inst_name != NULL )
  {
    if( _inst_name->tok_type() != vtEXP )
    {
      veri_err->append_err( ERR_ERROR, _inst_name->line(),
                      _inst_name->col(), vCHILD_TYPE_GATE_INSTANCE );
      return vCHILD_TYPE_GATE_INSTANCE;
    }
    switch( _inst_name->detail_type() )
    {
      case veEXP_PRI :
      case veEXP_ARRAY :
        break;
   
      default:
        veri_err->append_err( ERR_ERROR, _inst_name->line(),
                      _inst_name->col(), vCHILD_TYPE_GATE_INSTANCE );
        return vCHILD_TYPE_GATE_INSTANCE;
    }
  }

  if( _arg != NULL )
  {
    if( _arg->detail_type() != veEXP_MULTI )
    {
      veri_err->append_err( ERR_ERROR, _arg->line(),
                    _arg->col(), vCHILD_TYPE_GATE_INSTANCE );
      return vCHILD_TYPE_GATE_INSTANCE;
    }

    VeriMultiExp * mexp = static_cast<VeriMultiExp *>(_arg);
    switch( mexp->multi_type() )
    {
      case vemCOMMA_EXP :
      case vemPORT_EXP :
      case vemPORT_INST_EXP :
        break;

      default:
        veri_err->append_err( ERR_ERROR, _arg->line(),
                    _arg->col(), vCHILD_TYPE_GATE_INSTANCE );
        return vCHILD_TYPE_GATE_INSTANCE;
        break;
    }
  }

  if( _arg == NULL && _inst_name == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GATE_INSTANCE );
    return vCHILD_TYPE_GATE_INSTANCE;
  }

  return OK;
}

int
VeriGateInstance::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGateInstance::push_children( NodeVec& mstack )
{
  mstack.push_back( this );

  if( _arg != NULL )
  {
    //_arg->clean_up( );
    _arg->set_scope( scope( ) );
    mstack.push_back( _arg );
  }

  if( _inst_name != NULL )
  {
    //_inst_name->clean_up( );
    _inst_name->set_is_decl( IS_TRUE );
    _inst_name->set_is_trash( IS_TRUE );
    _inst_name->set_scope( scope( ) );
    mstack.push_back( _inst_name );
  }

  return OK;
}

int
VeriGateInstance::reg_gate_inst( void )
{
  IList dimen;
  switch( _inst_name->detail_type() )
  {
    case veEXP_PRI :
    {
      VeriPrimaryExp *pexp = static_cast<VeriPrimaryExp *>(_inst_name);
      _name = pexp->str();
      break;
    }

    case veEXP_ARRAY :
    {
      VeriArrayExp *aexp = static_cast<VeriArrayExp *>(_inst_name);
      _name = aexp->name();
      break;
    }

    default:
      break;
  }

  VeriNode * node = scope()->value_within_module( _name );
  if( node != NULL )
  {
    veri_err->append_err( ERR_ERROR, this, vGATE_INST_REDEFINE );
    return vGATE_INST_REDEFINE;
  }

  VeriGateInstantiation *gate_inst_father
    = static_cast<VeriGateInstantiation *>(father());

  VeriGateInst * symbol = new VeriGateInst( veri_parser->next_id(),
                                            line(), col(), _name,
                                            this, gate_inst_father,
                                            dimen, birth_mod() ); 
  veri_parser->insert_node( symbol );
  symbol->set_scope( scope( ) );
  symbol->set_father( this );
  scope()->insert( _name, symbol );
  return OK;
}

int
VeriGateInstance::do_nothing( void )
{
  return OK;
}

int
VeriGateInstance::push_for_replacement( NodeVec& mstack )
{
  if( _inst_name != NULL )
    mstack.push_back( _inst_name );

  if( _arg != NULL )
    mstack.push_back( _arg );

  return OK;
}

int
VeriGateInstance::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGateInstance *tmp = new VeriGateInstance( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _arg != NULL )
  {
    tmp->_arg = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  if( _inst_name != NULL )
  {
    tmp->_inst_name = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /**********************
     * Gate-Instantiation *
     **********************/

void
VeriGateInstantiation::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGateInstantiation::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  if( _drive_strength != NULL )
  {
    mqueue.push( _drive_strength );
    iqueue.push( depth );
  }

  if( _delay != NULL )
  {
    mqueue.push( _delay );
    iqueue.push( depth );
  }

  NodeList::iterator it = _gate_list.begin();
  for( ; it != _gate_list.end(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriGateInstantiation::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_gate_type( _gate_type );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _drive_strength );
  ofile << dot_str_conn( idx(), _delay );
  NodeList::iterator it = _gate_list.begin();
  for( ; it != _gate_list.end(); ++it )
    ofile << dot_str_conn( idx(), *it );

  return OK;
}

int
VeriGateInstantiation::check_child_validation( void )
{
  if( _delay == NULL || _drive_strength == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_GATE_INSTANTIATION );
    return vCHILD_TYPE_GATE_INSTANTIATION;
  }

  if( _delay->detail_type() != veEXP_DELAY )
  {
    veri_err->append_err( ERR_ERROR, _delay->line(), _delay->col(),
                          vCHILD_TYPE_GATE_INSTANTIATION );
    return vCHILD_TYPE_GATE_INSTANTIATION;
  }

  if( _drive_strength->detail_type() != veEXP_DRIVE )
  {
    veri_err->append_err( ERR_ERROR, _drive_strength->line(),
                          _drive_strength->col(),
                          vCHILD_TYPE_GATE_INSTANTIATION );
    return vCHILD_TYPE_GATE_INSTANTIATION;
  }

  /* gate_list : TODO */
  return OK;
}

int
VeriGateInstantiation::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGateInstantiation::push_children( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _gate_list.rbegin();
  for( ; it != _gate_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_decl( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }

  if( _delay != NULL )
  {
    //_delay->clean_up( );
    _delay->set_scope( scope( ) );
    mstack.push_back( _delay );
  }

  if( _drive_strength != NULL )
  {
    //_drive_strength->clean_up( );
    _drive_strength->set_scope( scope( ) );
    mstack.push_back( _drive_strength );
  }

  return OK;
}

int
VeriGateInstantiation::do_nothing( void )
{
  return OK;
}

int
VeriGateInstantiation::push_for_replacement( NodeVec& mstack )
{
  if( _drive_strength != NULL )
    mstack.push_back( _drive_strength );

  if( _delay != NULL )
    mstack.push_back( _delay );

  NodeList::iterator it = _gate_list.begin();
  for( ; it != _gate_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriGateInstantiation::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGateInstantiation *tmp = new VeriGateInstantiation( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  NodeList::iterator it = _gate_list.begin();
  for( ; it != _gate_list.end(); ++it )
  {
    tmp->_gate_list.push_front( *(--itl) );
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

  if( _drive_strength != NULL )
  {
    tmp->_drive_strength = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
  }

  *inl = tmp;
  return OK;
}

    /****************************
     * Generated-Loop-Statement *
     ****************************/

void
VeriGenLoop::clean_up( void )
{
  set_pstatus( vSTART_S );
  _is_target = IS_FALSE;
}

int
VeriGenLoop::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
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
VeriGenLoop::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _label );
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
VeriGenLoop::check_child_validation_assign( VeriNode *child )
{
  if( child == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GEN_LOOP );
    return vCHILD_TYPE_GEN_LOOP;
  }
    
  if( child->detail_type() != veEXP_ASSIGN )
  {
    veri_err->append_err( ERR_ERROR, child->line(), child->col(),
                        vCHILD_TYPE_GEN_LOOP );
    return vCHILD_TYPE_GEN_LOOP;
  }

  return OK;
}

int
VeriGenLoop::check_child_validation( void )
{
  int re;
  re = check_child_validation_assign( _init );
  if( re != OK )
    return re;

  re = VeriInst::check_child_exp_validation( _judge, vCHILD_TYPE_GEN_LOOP );
  if( re != OK )
    return re;

  re = check_child_validation_assign( _iter );
  if( re != OK )
    return re;

  if( _content == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GEN_LOOP );
    return vCHILD_TYPE_GEN_LOOP;
  }

  if( _content->tok_type() != vtINST )
  {
    veri_err->append_err( ERR_ERROR, _content->line(), _content->col(),
                        vCHILD_TYPE_GEN_LOOP );
    return vCHILD_TYPE_GEN_LOOP;
  }
  return OK;
}

int
VeriGenLoop::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
{
  int re;
  switch( pstatus( ) )
  {
    case vSTART_S :
      re = process_label( );
      if( re != OK )
      {
        scope()->finish_scope( );
        return re;
      }

      push_start_and_condition( mstack );
      set_pstatus( vEND_S );
      return re;
      break;

    default:
      return decide_loop( mstack );
      break;
  }
}

int
VeriGenLoop::process_label( void )
{
  _syntax_content=_content;
  set_scope( scope()->append_scope( _label, vNAMED_BLOCK_SCOPE ) );

  VeriLabelId * label_id = new VeriLabelId( veri_parser->next_id(),
                                            _label_line, _label_col,
                                            _label, this, birth_mod() );
  veri_parser->insert_node( label_id );
  scope()->insert( _label, label_id );
  if( _inline_genvar ) {
    auto* init=static_cast<VeriAssignExp*>(_init);
    auto* id=static_cast<VeriPrimaryExp*>(init->lval());
    auto* var=new VeriGenVar(veri_parser->next_id(),id->line(),id->col(),
                            id->str(),this,NULL,birth_mod());
    var->set_father(this);var->set_scope(scope());
    veri_parser->insert_node(var);scope()->insert(id->str(),var);
  }
  return OK;
}

int
VeriGenLoop::push_start_and_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_judge->clean_up( );
  _judge->set_is_trash( IS_TRUE );
  _judge->set_scope( scope( ) );
  mstack.push_back( _judge );
  
  //_init->clean_up( );
  _init->set_is_trash( IS_TRUE );
  _init->set_scope( scope( ) );
  mstack.push_back( _init );

  return OK;
}

int
VeriGenLoop::repeat_loop( void )
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

  VeriGenLoop *loop = static_cast<VeriGenLoop *>(last);

  _iter    = loop->iter();
  _judge   = loop->judge();
  _content = loop->content();
  // The temporary loop shell is about to be released. Its live children
  // belong to this loop; leaving their father on that shell corrupts upward
  // lookup when the node pool flushes its deferred deletion queue.
  _iter->set_father(this);_judge->set_father(this);
  if(_content)_content->set_father(this);

  veri_parser->toss_node( last->idx() );
  return OK;
}

int
VeriGenLoop::clear_content( void )
{
  // _content is also retained in _gen_content after a completed iteration.
  // The raw template and generated bodies remain owned by the node pool and
  // are released together at parser cleanup, never while still referenced.
  return OK;
}

int
VeriGenLoop::decide_loop( NodeVec& mstack )
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

        {
        // Capture the signed 32-bit genvar before the iteration expression
        // changes its shared symbol. Each cloned body needs its own value.
        VeriNode *lhs = _init;
        if( VeriAssignExp *assign = dynamic_cast<VeriAssignExp *>(_init) )
          lhs = assign->lval();
        else if( VeriBinaryExp *binary = dynamic_cast<VeriBinaryExp *>(_init) )
          if( binary->op() == vtASSIGN ) lhs = binary->lval();
        VeriPrimaryExp *primary = dynamic_cast<VeriPrimaryExp *>(lhs);
        VeriGenVar *variable = primary ? dynamic_cast<VeriGenVar *>(primary->var()) : NULL;
        VeriNum *current=variable?variable->get_val():NULL;
        if( !current || current->no_xz() != IS_TRUE ||
            _gen_values.size() >= 100000 || !_gen_seen.insert(current->get_first_int()).second )
        {
          scope()->finish_scope();
          veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
          return vSEC_LOOP_JUDGE_FAILURE;
        }
        _gen_variable = variable->name();
        _gen_values.push_back( current->get_first_int() );

        mstack.push_back( this );

        repeat_loop( );

        //_judge->clean_up( );
        _judge->set_scope( scope( ) );
        mstack.push_back( _judge );

        //_iter->clean_up( );
        _iter->set_is_trash( IS_TRUE );
        _iter->set_scope( scope( ) );
        mstack.push_back( _iter );

        //_content->clean_up( );
        if( _content ) _content->set_is_trash( IS_TRUE );
        // Every iteration is a distinct lexical scope. Reusing the loop's
        // table makes local declarations in later copies redefine the first.
        if( _content ) {
          _content->set_scope( scope()->append_scope(
              "[" + std::to_string(_gen_values.back()) + "]", vNAMED_BLOCK_SCOPE ) );
          mstack.push_back( _content );
        }

        _gen_iter.push_back( _iter );
        _gen_judge.push_back( _judge );
        _gen_content.push_back( _content );

        return OK;
        }
        break;

      case V0 :
        clear_content( );
        veri_parser->toss_node( num->idx() );
        scope()->finish_scope();
        return OK;
        break;

      default:
        clear_content( );
        veri_parser->toss_node( num->idx() );
        scope()->finish_scope();
        veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
        return vSEC_LOOP_JUDGE_FAILURE;
        break;
    }
    return OK;
  }
  else
  {
    clear_content( );
    scope()->finish_scope();
    veri_err->append_err( ERR_ERROR, this, vSEC_LOOP_JUDGE_FAILURE );
    return vSEC_LOOP_JUDGE_FAILURE;
  }
}

int
VeriGenLoop::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _init );
  mstack.push_back( _judge );
  mstack.push_back( _iter );
  if( _syntax_content )mstack.push_back(_syntax_content);
  else if( _content ) mstack.push_back( _content );

  return OK;
}

int
VeriGenLoop::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenLoop *tmp = new VeriGenLoop( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _content ) {
    tmp->_content = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

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
     * Default-Generate-Case-Item Statement *
     ****************************************/

void
VeriDefaultGenCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriDefaultGenCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _stmt );
  iqueue.push( depth );
  return OK;
}

int
VeriDefaultGenCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriDefaultGenCaseItem::check_child_validation( void )
{
  if( _stmt == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                        vCHILD_TYPE_GEN_DEFAULT_CASE );
    return vCHILD_TYPE_GEN_DEFAULT_CASE;
  }
   
  if( _stmt->tok_type() != vtINST )
  {
    veri_err->append_err( ERR_ERROR, _stmt->line(), _stmt->col(),
                        vCHILD_TYPE_GEN_DEFAULT_CASE );
    return vCHILD_TYPE_GEN_DEFAULT_CASE;
  }
  return OK;
}

int
VeriDefaultGenCaseItem::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriDefaultGenCaseItem::push_stmt( NodeVec& mstack )
{
  mstack.push_back( this );

  //_stmt->clean_up( );
  _stmt->set_is_trash( IS_TRUE );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriDefaultGenCaseItem::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _stmt );
  return OK;
}

int
VeriDefaultGenCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriDefaultGenCaseItem *tmp = new VeriDefaultGenCaseItem( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  tmp->_stmt = *(--itl);
  (*itl)->set_father( tmp );
  node_list.erase( itl );

  *inl = tmp;
  return OK;
}

    /********************************
     * Generate-Case-Item Statement *
     ********************************/

void
VeriGenCaseItem::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenCaseItem::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
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
VeriGenCaseItem::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriGenCaseItem::check_child_validation( void )
{
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
  { 
    if( *it == NULL )
    {
      veri_err->append_err( ERR_ERROR, line(), col(),
                            vCHILD_TYPE_GEN_CASE_ITEM );
      return vCHILD_TYPE_GEN_CASE_ITEM;
    }
    if( (*it)->tok_type() != vtEXP )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                            vCHILD_TYPE_GEN_CASE_ITEM );
      return vCHILD_TYPE_GEN_CASE_ITEM;
    }
  }

  if( _stmt == NULL )
  {
    veri_err->append_err( ERR_ERROR, _label.back()->line(),
                          _label.back()->col(),
                          vCHILD_TYPE_GEN_CASE_ITEM );
    return vCHILD_TYPE_GEN_CASE_ITEM;
  }
    
  if( _stmt->tok_type() != vtINST )
  {
    veri_err->append_err( ERR_ERROR, _stmt->line(), _stmt->col(),
                        vCHILD_TYPE_GEN_CASE_ITEM );
    return vCHILD_TYPE_GEN_CASE_ITEM;
  }

  return OK;
}

int
VeriGenCaseItem::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriGenCaseItem::push_labels( NodeVec& mstack )
{
  NodeList::reverse_iterator it = _label.rbegin();
  for( ; it != _label.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope( ) );
    mstack.push_back( *it ); 
  }

  return OK;
}

int
VeriGenCaseItem::push_stmt( NodeVec& mstack )
{
  //_stmt->clean_up( );
  _stmt->set_is_trash( IS_TRUE );
  _stmt->set_scope( scope( ) );
  mstack.push_back( _stmt );
  return OK;
}

int
VeriGenCaseItem::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _label.begin();
  for( ; it != _label.end(); ++it )
    mstack.push_back( *it ); 

  mstack.push_back( _stmt );
  return OK;
}

int
VeriGenCaseItem::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenCaseItem *tmp = new VeriGenCaseItem( idx, this );

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
     * Generate-Case-Item-List Statement *
     *************************************/

int
VeriGenCaseItemList::set_default( VeriNode * node )
{
  if( _default_item == NULL )
  {
    _default_item = node;
    return OK;
  }
  else
    return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
}

void
VeriGenCaseItemList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenCaseItemList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _default_item != NULL )
  {
    mqueue.push( _default_item );
    iqueue.push( depth );
  }

  NodeList::reverse_iterator it = _other_item.rbegin();
  for( ; it != _other_item.rend(); ++it )
  {
    mqueue.push( *it );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriGenCaseItemList::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriGenCaseItemList::check_child_validation( void )
{
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsINST_GEN_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(),
                            _default_item->col(),
                            vCHILD_TYPE_GEN_CASE_ITEM_LIST );
      return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
    }
  }

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    if( *it == NULL )
    {
      veri_err->append_err( ERR_ERROR, line(), col(),
                            vCHILD_TYPE_GEN_CASE_ITEM_LIST );
      return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
    }
    if( (*it)->detail_type() != vsINST_GEN_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                        vCHILD_TYPE_GEN_CASE_ITEM_LIST );
      return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
    }
  }
  return OK;
}

int
VeriGenCaseItemList::check_last_child_validation( void )
{
  if( _default_item != NULL )
  {
    if( _default_item->detail_type() != vsINST_GEN_DEFAULT_CASE_ITEM )
    {
      veri_err->append_err( ERR_ERROR, _default_item->line(),
                            _default_item->col(),
                            vCHILD_TYPE_GEN_CASE_ITEM_LIST );
      return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
    }
  }

  VeriNode * item = _other_item.back();
  if( item == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_GEN_CASE_ITEM_LIST );
    return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
  }

  if( item->detail_type() != vsINST_GEN_CASE_ITEM )
  {
    veri_err->append_err( ERR_ERROR, item->line(), item->col(),
                        vCHILD_TYPE_GEN_CASE_ITEM_LIST );
    return vCHILD_TYPE_GEN_CASE_ITEM_LIST;
  }
  return OK;
}

int
VeriGenCaseItemList::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriGenCaseItemList::push_labels( NodeVec& mstack )
{
  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
  {
    //(*it)->clear( );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope( ) );
    (static_cast<VeriGenCaseItem*>(*it))->push_labels( mstack );
  }

  return OK;
}

int
VeriGenCaseItemList::push_for_replacement( NodeVec& mstack )
{
  if( _default_item != NULL )
    mstack.push_back( _default_item );

  NodeList::iterator it = _other_item.begin();
  for( ; it != _other_item.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriGenCaseItemList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenCaseItemList *tmp = new VeriGenCaseItemList( idx, this );

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
     * Generate-Case Statement *
     ***************************/

void
VeriGenCase::clean_up( void )
{
  set_pstatus( vSTART_S );
  _all_labels.clear( );
  _all_exps.clear( );
}

int
VeriGenCase::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
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
VeriGenCase::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _choice );

  return OK;
}

int
VeriGenCase::check_child_validation( void )
{
  int re;
  re = VeriInst::check_child_exp_validation( _switch, vCHILD_TYPE_GEN_CASE );
  if( re != OK )
    return re;

  if(    _item_list != NULL
      && _item_list->detail_type() == vsINST_GEN_CASE_ITEM_LIST )
    return OK;

  veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GEN_CASE );
  return vCHILD_TYPE_GEN_CASE;
}

int
VeriGenCase::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGenCase::push_conditions( NodeVec& mstack )
{
  mstack.push_back( this );

  VeriGenCaseItemList *item_list
    = static_cast<VeriGenCaseItemList *>(_item_list);
  item_list->set_scope(scope());
  item_list->push_labels( mstack );

  //_switch->clean_up( );
  _switch->set_is_trash( IS_TRUE );
  _switch->set_scope( scope( ) );
  mstack.push_back( _switch );

  return OK;
}

int
VeriGenCase::prep_all_labels( void )
{
  VeriGenCaseItemList *item_list
    = static_cast<VeriGenCaseItemList *>(_item_list);

  VeriGenCaseItem *item = NULL;
  NodeList &items = item_list->other_item( );
  NodeList::iterator it = items.begin();
  NodeList::iterator il;
  for( ; it != items.end(); ++it )
  {
    item = static_cast<VeriGenCaseItem *>(*it);
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
VeriGenCase::decide_case( NodeVec& mstack )
{
  VeriExp *switch_exp = static_cast<VeriExp *>(_switch);
  if( switch_exp->calc_value( ) == NULL )
  {
    veri_err->append_err( ERR_ERROR, _switch, vSEC_CASE_COND_NOT_CALC );
    return vSEC_CASE_COND_NOT_CALC;
  }

  VeriGenCaseItemList *item_list
    = static_cast<VeriGenCaseItemList *>(_item_list);

  VeriDefaultGenCaseItem *default_item
    = static_cast<VeriDefaultGenCaseItem *>(item_list->default_item( ) );

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
      (*iexp)->set_is_trash( IS_TRUE );
      (*iexp)->set_scope( scope( ) );
      mstack.push_back( *iexp );

      _choice = *iexp;
      break;
    }
  }

  if( found_match == IS_FALSE && default_item != NULL )
  {
    _choice = default_item->stmt();
    default_item->set_scope(scope());
    default_item->push_stmt( mstack );
  }

  return OK;
}

int
VeriGenCase::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _switch );
  mstack.push_back( _item_list );

  return OK;
}

int
VeriGenCase::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenCase *tmp = new VeriGenCase( idx, this );

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
     * Generate-Conditional Statement *
     **********************************/

void
VeriGenCond::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenCond::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;
  mqueue.push( _if_exp );
  iqueue.push( depth );

  if( _choice != NULL )
  {
    mqueue.push( _choice );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriGenCond::pretty_dot_label( Ofstream& ofile, int depth )
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
  ofile << dot_str_conn( idx(), _if_exp );
//  ofile << dot_str_conn( idx(), _if_stmt );
//  ofile << dot_str_conn( idx(), _else_stmt );
  ofile << dot_str_conn( idx(), _choice );

  return OK;
}

int
VeriGenCond::check_child_validation( void )
{
  int re;
  re = VeriInst::check_child_exp_validation( _if_exp, vCHILD_TYPE_GEN_COND );
  if( re != OK )
    return re;

  if( _if_stmt == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(), vCHILD_TYPE_GEN_COND );
    return vCHILD_TYPE_GEN_COND;
  }

  /* generate conditional body can be instantiation or continuous assign */
  if( _if_stmt->tok_type() != vtINST &&
      _if_stmt->tok_type() != vsSTMT_CONT_ASSIGN )
  {
    veri_err->append_err( ERR_ERROR, _if_stmt->line(), _if_stmt->col(),
                          vCHILD_TYPE_GEN_COND );
    return vCHILD_TYPE_GEN_COND;
  }

  if( _else_stmt != NULL )
  {
    if( _else_stmt->tok_type() != vtINST &&
        _else_stmt->tok_type() != vsSTMT_CONT_ASSIGN )
    {
      veri_err->append_err( ERR_ERROR, _else_stmt->line(), _else_stmt->col(),
                            vCHILD_TYPE_GEN_COND );
      return vCHILD_TYPE_GEN_COND;
    }
  }

  return OK;
}

int
VeriGenCond::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGenCond::push_condition( NodeVec& mstack )
{
  mstack.push_back( this );

  //_if_exp->clean_up( );
  _if_exp->set_is_trash( is_trash( ) );
  _if_exp->set_scope( scope( ) );
  mstack.push_back( _if_exp );

  return OK;
}

int
VeriGenCond::choose_children( NodeVec& mstack )
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
          _else_stmt->set_is_trash( is_trash( ) );
          _else_stmt->set_scope( scope( ) );
          mstack.push_back( _else_stmt );

          _choice = _else_stmt;
        }
        return OK;
        break;

      case V1 :
        //_if_stmt->clean_up( );
        _if_stmt->set_is_trash( is_trash( ) );
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
VeriGenCond::push_for_replacement( NodeVec& mstack )
{
  mstack.push_back( _if_exp );
  mstack.push_back( _if_stmt );

  if( _else_stmt != NULL )
    mstack.push_back( _else_stmt );

  return OK;
}

int
VeriGenCond::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenCond *tmp = new VeriGenCond( idx, this );

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

    /******************************
     * Generation-Block Statement *
     ******************************/

void
VeriGenBlock::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenBlock::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
{
  int depth = iqueue.front( ) + 1;

  if( _item_list != NULL )
  {
    mqueue.push( _item_list );
    iqueue.push( depth );
  }
  return OK;
}

int
VeriGenBlock::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _label );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_conn( idx(), _item_list );

  return OK;
}

int
VeriGenBlock::check_child_validation( void )
{
  if( _item_list != NULL )
  {
    if( _item_list->detail_type() != vsINST_GEN_ITEM_LIST )
    {
      veri_err->append_err( ERR_ERROR, _item_list->line(), _item_list->col(),
                          vCHILD_TYPE_GEN_BLOCK );
      return vCHILD_TYPE_GEN_BLOCK;
    }
  }
  return OK;
}

int
VeriGenBlock::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGenBlock::process_label( void )
{
  // Unnamed blocks also introduce a lexical scope.
  set_scope( scope()->append_scope( _label, vNAMED_BLOCK_SCOPE ) );
  if( !_label.empty() )
  {
    VeriLabelId * label_id = new VeriLabelId( veri_parser->next_id(),
                                            _label_line, _label_col,
                                            _label, this, birth_mod() );
    veri_parser->insert_node( label_id );
    scope()->insert( _label, label_id );
  }
  return OK;
}

int
VeriGenBlock::push_children( NodeVec& mstack )
{
  if( _item_list != NULL )
  {
    //_item_list->clean_up( );
    _item_list->set_is_trash( IS_TRUE );
    _item_list->set_scope( scope( ) );
    mstack.push_back( _item_list );
  }
  return OK;
}

int
VeriGenBlock::end_label( void )
{
  scope()->finish_scope( );
  return OK;
}

int
VeriGenBlock::push_for_replacement( NodeVec& mstack )
{
  if( _item_list != NULL )
    mstack.push_back( _item_list );

  return OK;
}

int
VeriGenBlock::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenBlock *tmp = new VeriGenBlock( idx, this );

  // begin replacement
  NodeList::iterator itl = inl; 

  if( _item_list != NULL )
  {
    tmp->_item_list = *(--itl);
    (*itl)->set_father( tmp );
    node_list.erase( itl );
    itl = inl;
  }

  *inl = tmp;
  return OK;
}

    /**************************************
     * Generated-Statement-List Statement *
     **************************************/

void
VeriGenItemList::clean_up( void )
{
  set_pstatus( vSTART_S );
}

int
VeriGenItemList::push_dot_children( NodeQueue& mqueue, IQueue& iqueue )
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
VeriGenItemList::pretty_dot_label( Ofstream& ofile, int depth )
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
VeriGenItemList::check_child_validation( void )
{
  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
  {
    if( *it == NULL )
    {
      veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_GEN_ITEM_LIST );
      return vCHILD_TYPE_GEN_ITEM_LIST;
    }
    switch( (*it)->tok_type() )
    {
      case vtDECL :
      case vtINST :
      case vtSTMT :
        break;

      default:
        veri_err->append_err( ERR_ERROR, (*it)->line(), (*it)->col(),
                          vCHILD_TYPE_GEN_ITEM_LIST );
        return vCHILD_TYPE_GEN_ITEM_LIST;
    }
  }
  return OK;
}

int
VeriGenItemList::check_last_child_validation( void )
{
  VeriNode * node = _item_list.back();
  if( node == NULL )
  {
    veri_err->append_err( ERR_ERROR, line(), col(),
                          vCHILD_TYPE_GEN_ITEM_LIST );
    return vCHILD_TYPE_GEN_ITEM_LIST;

  }

  switch( node->tok_type() )
  {
    case vtDECL :
    case vtINST :
    case vtSTMT :
      break;

    default:
      veri_err->append_err( ERR_ERROR, node->line(), node->col(),
                        vCHILD_TYPE_GEN_ITEM_LIST );
      return vCHILD_TYPE_GEN_ITEM_LIST;
  }
  return OK;
}

int
VeriGenItemList::process_node_2nd( NodeVec& mstack, String& /*help_info*/ )
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
VeriGenItemList::push_children( NodeVec& mstack )
{
  veri_bind_forward_classes(_item_list);
  veri_register_sequences(_item_list,scope());
  NodeList::reverse_iterator it = _item_list.rbegin();
  for( ; it != _item_list.rend(); ++it )
  {
    //(*it)->clean_up( );
    (*it)->set_is_trash( IS_TRUE );
    (*it)->set_scope( scope() );
    mstack.push_back( *it );
  }

  return OK;
}

int
VeriGenItemList::do_nothing( void )
{
  return OK;
}

int
VeriGenItemList::push_for_replacement( NodeVec& mstack )
{
  NodeList::iterator it = _item_list.begin();
  for( ; it != _item_list.end(); ++it )
    mstack.push_back( *it );

  return OK;
}

int
VeriGenItemList::replace_node( Uint idx, NodeList& node_list,
                          NodeList::iterator& inl)
{
  // spawn duplicant
  VeriGenItemList *tmp = new VeriGenItemList( idx, this );

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
