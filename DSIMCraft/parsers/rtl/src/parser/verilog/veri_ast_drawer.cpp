/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_ast_drawer.cpp
 * Summary  : verilog abstract syntax tree drawer functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang   ( 11212020059@fudan.edu.cn )
              Chelsy Huang ( 09300720330@fudan.edu.cn )
 * Date     : 2012.12.10
 */
#include <cstdlib>

#include "general_err.hpp"
#include "verilog_token.hpp"
#include "veri_symbol_table.hpp"

#include "veri_ast_drawer.hpp"

namespace rtl
{

void
VeriAstDrawer::init( CString& dir, CString& fname )
{
  _depth = 0;
  _dir   = dir;
  _fname = fname + ".dot";
}

void
VeriAstDrawer::prep_for_drawing( void )
{
  _ofile.open( (_dir + _fname).c_str() );

  _ofile << "digraph " << _fname.substr( 0, _fname.size() - 4 );
  _ofile << "\n{\n";
  _ofile << "  node [ shape = plaintext ];\n";
  _ofile << "  compound = true;\n";
//  _ofile << "  splines = false;\n";
}

void
VeriAstDrawer::draw_ast( VeriNode *head )
{
  if( !_ofile.good() )
    return;

  int depth = 0;
  
  NodeQueue nqueue;
  IQueue    iqueue;

  VeriNode *tmp;

  iqueue.push( depth );
  nqueue.push( head );

  while( !nqueue.empty() )
  {
    // fetch & process
    tmp   = nqueue.front();
    depth = iqueue.front();
    if( _depth <= depth )
      _depth = depth;

    tmp->pretty_dot_label( _ofile, depth );
    tmp->push_dot_children( nqueue, iqueue );

    // pop
    nqueue.pop();
    iqueue.pop();
  }
}

void
VeriAstDrawer::draw_symbol( SymbolTable *table_head )
{
  if( !_ofile.good( ) )
    return;

  SymbolTableQueue tables;
  SymbolTable *cur_table;
  tables.push( table_head );

  _depth += 3;

  while( !tables.empty( ) )
  {
    cur_table = tables.front( );

    cur_table->pretty_dot_output( _ofile, ++_depth );
    cur_table->push_more_table( tables );

    tables.pop( );
  }
}

void
VeriAstDrawer::end_drawing( void )
{
  if( !_ofile.good( ) )
    return;

  append_rank_edge( _depth );
  _ofile << "}";
  _ofile.close();
}

void
VeriAstDrawer::generate_jpg( void )
{
  String cmd = "dot -Tjpg " + _fname + " -o " + _fname + ".jpg\n";
  system(cmd.c_str());
}

void
VeriAstDrawer::append_rank_edge( int depth )
{
  int i;
  for( i = 0 ; i <= depth ; ++i )
  {
    _ofile << "  -" << int2string(i);
    _ofile << " [ shape = plaintext, label = \"" << int2string(i);
    _ofile << "\" ];\n";
  }

  for( i = 0 ; i < depth ; ++i)
    _ofile << "  -" << int2string(i) << "-> -" << int2string(i+1) << "\n";
}

void
VeriAstDrawer::clear( void )
{
  _fname = "";
}

}

