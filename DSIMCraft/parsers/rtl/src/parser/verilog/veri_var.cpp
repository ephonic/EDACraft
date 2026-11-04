/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_var.hpp
 * Summary  : verilog syntax analyzer true node class : variable
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#include "veri_node.hpp"
#include "veri_num.hpp"
#include "veri_var.hpp"

#include "veri_symbol_table.hpp"
#include "veri_parser.hpp"

namespace rtl
{

     /*********************
      *  System-Variable  *
      *********************/

void
VeriSysVar::clean_up( void )
{
}

int
VeriSysVar::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriSysVar::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  return OK;
}

int
VeriSysVar::check_child_validation( void )
{
  return OK;
}

int
VeriSysVar::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriSysVar::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriSysVar::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

     /*************
      *  Variable *
      *************/

void
VeriVar::clear( void )
{
  if( _val != NULL )
    delete[] _val;
  _val = NULL;
}

void
VeriVar::clean_up( void )
{
  if( _val != NULL )
  {
    for( int i = 0; i < _total_cnt; ++i )
    {
      if( _val[i] != NULL )
        veri_parser->toss_node( _val[i]->idx() );
      _val[i] = NULL;
    }
    delete[] _val;
  }
  _val = NULL;
}

int
VeriVar::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriVar::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  IList range_from, range_to;
  SymbolRanges::iterator it = _range.begin();

  range_from.push_back( _dstart );
  range_to.push_back( _dend );
  for( ; it != _range.end(); ++it)
  {
    range_from.push_back( it->from );
    range_to.push_back( it->to );
  }

  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_in_out( _inout );
  ofile << dot_str_var_type( _net_type );
  ofile << dot_str_is_tf( "SIGN", _is_signed );
  ofile << dot_str_vector_scalar( _vec_scalar );
  ofile << dot_str_drive_from( _drive_from );
  ofile << dot_str_drive_to( _drive_to );
  ofile << dot_str_range( range_from, range_to );
  ofile << dot_str_tail( tok_type() );

  // connection
//  ofile << dot_str_symbol_back_conn( idx(), _val[0] );
  ofile << dot_str_symbol_back_conn( idx(), _decl );

  return OK;
}

int
VeriVar::check_child_validation( void )
{
  return OK;
}

int
VeriVar::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriVar::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriVar::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

void
VeriVar::get_range( unsigned int depth, int& start, int& end, int& bits )
{
  if( depth == 0 )
  {
    start = 0;
    end   = 0;
    bits  = 0;
  }
  else if( depth > _range.size() )
  {
    start = -1;
    end   = -1;
    bits  =  1;
  }
  else
  {
    start = _range[depth-1].from;
    end   = _range[depth-1].to;
    bits  = _range[depth-1].bits;
  }
}

int
VeriVar::calc_dimen_cnt( int start_lvl )
{
  int cnt = 1;
  for( unsigned int i = start_lvl; i < _range.size() - 1; ++i )
    cnt *= _range[i].bits; 
  return cnt;
}

int
VeriVar::determin_idx( const IVec& dimen )
{
  int idx = 0;
  for( unsigned int i = 0; i < dimen.size(); ++i )
    idx += abs(dimen[i] - _range[i].from) * calc_dimen_cnt(i+1);
  return idx;
}

VeriNum *
VeriVar::get_one_num( const IVec& dimen, int is_whole, int dstart, int dend )
{
  if( dimen.size() != _range.size() )
    return NULL;

  int idx = determin_idx( dimen );
  if( idx >= _total_cnt )
    return NULL;

  VeriNum *num = NULL;
  if( _val[idx] == NULL )
  {
    num = new VeriNum( veri_parser->next_id(), line(), col(), birth_mod() );
    num->set_father( father() );
    num->set_scope( scope( ) );
    num->set_signed( );
    num->init_val( _is_signed, _dlen );

    veri_parser->insert_node( num );
    _val[idx] = num;
  }

  num = new VeriNum( veri_parser->next_id(), _val[idx]);
  num->set_father( father() );
  num->set_scope( scope( ) );
  veri_parser->insert_node( num );
  num->replace_value( is_whole, _dstart, dstart, dend, _val[idx] );
  return num;
}

int
VeriVar::set_one_num( const IVec& dimen, int is_whole, int dstart, int dend,
                      VeriNum *val )
{
  if( dimen.size() != _range.size() )
    return vSEC_VAR_RANGE_OVERLOAD;

  int idx = determin_idx( dimen );
  if( idx >= _total_cnt )
    return vSEC_VAR_RANGE_OVERLOAD;

  if( _val[idx] != NULL )
    veri_parser->toss_node( _val[idx]->idx() );

  _val[idx] = new VeriNum( veri_parser->next_id(), val );
  _val[idx]->set_father( father() );
  _val[idx]->set_scope( scope( ) );
  veri_parser->insert_node( _val[idx] );
  _val[idx]->refresh_value( is_whole, _dstart, dstart, dend, val );
  return OK;
}

     /**************
      *  TF-VAR    *
      **************/

void
VeriTfVar::clean_up( void )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx( ) );
  _val = NULL;
}

int
VeriTfVar::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriTfVar::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  IList range_from, range_to;
  range_from.push_back( _dstart );
  range_to.push_back( _dend );

  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_var_type( _net_type );
  ofile << dot_str_range( range_from, range_to );
  ofile << dot_str_tail( tok_type() );

  // connection
//  ofile << dot_str_symbol_back_conn( idx(), _val );
  ofile << dot_str_symbol_back_conn( idx(), _decl );

  return OK;
}

int
VeriTfVar::check_child_validation( void )
{
  return OK;
}

int
VeriTfVar::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriTfVar::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriTfVar::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

VeriNum *
VeriTfVar::get_val( void )
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
VeriTfVar::set_val( VeriNum *val )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx() );

  _val = new VeriNum( veri_parser->next_id( ), val );
  _val->set_father( father() );
  _val->set_scope( scope( ) );
  veri_parser->insert_node( _val );
}


     /**************
      *  Parameter *
      **************/

void
VeriParam::clean_up( void )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx( ) );
  _val = NULL;
}

int
VeriParam::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriParam::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  IList range_from, range_to;
  range_from.push_back( _dstart );
  range_to.push_back( _dend );

  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_is_tf( "INT", _is_int );
  ofile << dot_str_is_tf( "LOCAL", _is_local );
  ofile << dot_str_is_tf( "SIGN", _is_signed );
  ofile << dot_str_range( range_from, range_to );
  ofile << dot_str_tail( tok_type() );

  // connection
//  ofile << dot_str_symbol_back_conn( idx(), _val );
  ofile << dot_str_symbol_back_conn( idx(), _decl );

  return OK;
}

int
VeriParam::check_child_validation( void )
{
  return OK;
}

int
VeriParam::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriParam::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriParam::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

VeriNum *
VeriParam::get_val( void )
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
VeriParam::set_val( VeriNum *val )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx() );

  _val = new VeriNum( veri_parser->next_id( ), val );
  _val->set_father( father() );
  _val->set_scope( scope( ) );
  veri_parser->insert_node( _val );
}

     /*************
      *  Integer  *
      *************/

void
VeriInt::clear( void )
{
  if( _val != NULL )
    delete[] _val;
  _val = NULL;
}

void
VeriInt::clean_up( void )
{
  if( _val != NULL )
  {
    for( int i = 0; i < _total_cnt; ++i )
    {
      if( _val[i] != NULL )
        veri_parser->insert_node( _val[i] );
      _val[i] = NULL;
    }
    delete[] _val;
  }
  _val = NULL;
}

int
VeriInt::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriInt::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  IList range_from, range_to;
  SymbolRanges::iterator it = _range.begin();

  for( ; it != _range.end(); ++it)
  {
    range_from.push_back( it->from );
    range_to.push_back( it->to );
  }

  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_range( range_from, range_to );
  ofile << dot_str_tail( tok_type() );

  // connection
//  ofile << dot_str_symbol_back_conn( idx(), _val[0] );
  ofile << dot_str_symbol_back_conn( idx(), _decl );

  return OK;
}

int
VeriInt::check_child_validation( void )
{
  return OK;
}

int
VeriInt::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriInt::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriInt::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

void
VeriInt::get_range( unsigned int depth, int& start, int& end, int& bits )
{
  if( depth == 0 )
  {
    start = 0;
    end   = 0;
    bits  = 0;
  }
  else if( depth > _range.size() )
  {
    start = -1;
    end   = -1;
    bits  =  1;
  }
  else
  {
    start = _range[depth-1].from;
    end   = _range[depth-1].to;
    bits  = _range[depth-1].bits;
  }
}

int
VeriInt::calc_dimen_cnt( int start_lvl )
{
  int cnt = 1;
  for( unsigned int i = start_lvl; i < _range.size() - 1; ++i )
    cnt *= _range[i].bits; 
  return cnt;
}

int
VeriInt::determin_idx( const IVec& dimen )
{
  int idx = 0;
  for( unsigned int i = 0; i < dimen.size(); ++i )
    idx += abs(dimen[i] - _range[i].from) * calc_dimen_cnt(i+1);
  return idx;
}


VeriNum *
VeriInt::get_one_num( const IVec& dimen, int is_whole, int dstart, int dend )
{
  if( dimen.size() != _range.size() )
    return NULL;

  int idx = determin_idx( dimen );
  if( idx >= _total_cnt )
    return NULL;

  VeriNum *num = NULL;
  if( _val[idx] == NULL )
  {
    num = new VeriNum( veri_parser->next_id(), line(), col(), birth_mod() );
    num->set_father( father() );
    num->set_scope( scope( ) );
    num->init_val( IS_TRUE, 32 );
    veri_parser->insert_node( num );
    _val[idx] = num;
  }

  num = new VeriNum( veri_parser->next_id(), _val[idx]);
  num->set_father( father() );
  num->set_scope( scope( ) );
  veri_parser->insert_node( num );
  num->replace_value( is_whole, 0, dstart, dend, _val[idx] );
  return num;
}

int
VeriInt::set_one_num( const IVec& dimen, int is_whole, int dstart, int dend,
                      const VeriNum *val )
{
  if( dimen.size() != _range.size() )
    return vSEC_VAR_RANGE_OVERLOAD;

  int idx = determin_idx( dimen );
  if( idx >= _total_cnt )
    return vSEC_VAR_RANGE_OVERLOAD;

  if( _val[idx] != NULL )
    veri_parser->toss_node( _val[idx]->idx() );

  _val[idx] = new VeriNum( veri_parser->next_id(), val );
  _val[idx]->set_father( father() );
  _val[idx]->set_scope( scope( ) );
  veri_parser->insert_node( _val[idx] );
  _val[idx]->refresh_value( is_whole, 0, dstart, dend, val );
  return OK;
}

     /**********
      * GenVar *
      **********/

void
VeriGenVar::clean_up( void )
{
  if( _val != NULL )
    delete _val;
  _val = NULL;
}

int
VeriGenVar::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriGenVar::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
//  ofile << dot_str_symbol_back_conn( idx(), _val );
  ofile << dot_str_symbol_back_conn( idx(), _decl );

  return OK;
}

int
VeriGenVar::check_child_validation( void )
{
  return OK;
}

int
VeriGenVar::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriGenVar::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriGenVar::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

VeriNum *
VeriGenVar::get_val( void )
{
  VeriNum *num = NULL;
  if( _val == NULL )
  {
    num = new VeriNum( veri_parser->next_id(), line(), col(), birth_mod() );
    num->set_father( father() );
    num->set_scope( scope( ) );
    num->init_val( IS_TRUE, 32 );
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
VeriGenVar::set_val( VeriNum *val )
{
  if( _val != NULL )
    veri_parser->toss_node( _val->idx() );

  _val = new VeriNum ( veri_parser->next_id(), val );
  _val->set_signed(); // genvar is a signed integer, regardless of RHS type.
  _val->set_father( father() );
  _val->set_scope( scope( ) );
  veri_parser->insert_node( _val );
}

     /**************
      *  Label-ID  *
      *************/

void
VeriLabelId::clean_up( void )
{
}

int
VeriLabelId::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriLabelId::pretty_dot_label( Ofstream& ofile, int depth )
{
  // rank
  ofile << dot_str_rank( idx(), depth );
  
  // content
  ofile << dot_str_head( idx() );
  ofile << dot_str_tok_type( tok_type() );
  if( scope() != NULL )  ofile << dot_str_scope( scope()->depth() );
  ofile << dot_str_name( _name );
  ofile << dot_str_tail( tok_type() );

  // connection
  ofile << dot_str_symbol_back_conn( idx(), _label_block );

  return OK;
}

int
VeriLabelId::check_child_validation( void )
{
  return OK;
}

int
VeriLabelId::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriLabelId::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriLabelId::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}

};
