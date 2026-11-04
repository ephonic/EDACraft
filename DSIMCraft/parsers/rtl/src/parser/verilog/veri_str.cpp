/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_str.cpp
 * Summary  : verilog syntax string representation
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include "veri_err_token.hpp"
#include "veri_str.hpp"

namespace rtl
{

void
VeriStr::clean_up( void )
{
}

int
VeriStr::push_dot_children( NodeQueue& /*mqueue*/, IQueue& /*iqueue*/ )
{
  return OK;
}

int
VeriStr::pretty_dot_label( Ofstream& , int depth )
{
  return depth;
}

int
VeriStr::check_child_validation( void )
{
  return OK;
}

int
VeriStr::process_node_2nd( NodeVec& /*mstack*/, String& /*help_info*/ )
{
  return OK;
}

int
VeriStr::push_for_replacement( NodeVec& /*mstack*/ )
{
  return OK;
}

int
VeriStr::replace_node( Uint /*idx*/, NodeList& /*node_list*/,
                          NodeList::iterator& /*inl*/)
{
  return OK;
}


};

