/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_tfmg.hpp
 * Summary  : verilog syntax analyzer true node class :
 *            1, task
 *            2, function
 *            3, gate_instance
 *            4, module_instance
 *
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.3.8
 */

#include "veri_num.hpp"

#include "veri_tfmg.hpp"
#include "veri_decl.hpp"

#include "veri_symbol_table.hpp"
#include "veri_parser.hpp"

namespace rtl
{

     /*********
      *  Task *
      *********/

void
VeriTask::clean_up( void )
{
}

int
VeriTask::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriTask::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_symbol_back_conn( idx(), _task );

  return OK;
}

int
VeriTask::check_child_validation( void )
{
  return OK;
}

int
VeriTask::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriTask::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriTask::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

     /*************
      *  Function *
      *************/

void
VeriFunc::clean_up( void )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx( ) );
  _val = NULL;
}

int
VeriFunc::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriFunc::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_symbol_back_conn( idx(), _func );

  return OK;
}

int
VeriFunc::check_child_validation( void )
{
  return OK;
}

int
VeriFunc::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriFunc::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriFunc::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

VeriNum *
VeriFunc::get_val( void )
{
  VeriNum *num = NULL;
  if( _val == NULL )
  {
    num = new VeriNum( veri_parser->next_id(), line(), col(), birth_mod() );
    num->set_father( father() );
    num->set_scope( scope( ) );
    num->init_val( _is_signed, _dlen );
    veri_parser->insert_node( num );
    _val = num;
  }
  
  num = new VeriNum( veri_parser->next_id(), _val );
  num->set_father( father() );
  num->set_scope( scope( ) );
  veri_parser->insert_node( num );
  return num;
}

void
VeriFunc::set_val( VeriNum *val )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx() );

  _val = new VeriNum( veri_parser->next_id( ), val );
  _val->set_father( father() );
  _val->set_scope( scope( ) );
  veri_parser->insert_node( _val );
}

     /******************
      *  Gate-Instance *
      ******************/

void
VeriGateInst::clean_up( void )
{
}

int
VeriGateInst::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriGateInst::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_symbol_back_conn( idx(), _instance );

  return OK;
}

int
VeriGateInst::check_child_validation( void )
{
  return OK;
}

int
VeriGateInst::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriGateInst::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriGateInst::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

     /********************
      *  Module-Instance *
      ********************/

void
VeriModInst::clean_up( void )
{
}

int
VeriModInst::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriModInst::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  ofile << dot_str_detail_type( detail_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_symbol_back_conn( idx(), _instance );

  return OK;
}

int
VeriModInst::check_child_validation( void )
{
  return OK;
}

int
VeriModInst::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriModInst::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriModInst::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

};
