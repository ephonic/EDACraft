/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_mod_container.cpp
 * Summary  : verilog syntax analyzer :: module container functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */

#include "general_err.hpp"
#include "veri_err_token.hpp"
#include <iostream>

#include "veri_err.hpp"
#include "veri_module.hpp"
#include "veri_inst.hpp"
#include "veri_ast_drawer.hpp"

#include "veri_mod_container.hpp"

#include "cfg_mgr.hpp"

#define debug_verilog_mod_container_
#ifdef  debug_verilog_mod_container_
#include <iostream>
using std::cout;
using std::endl;
#endif

namespace rtl
{

int
VeriModContainer::init( Uint size )
{
  if( size != 0 )
  {
    _size = size;
    _hash_list = new VeriModNode*[size];
    for( Uint i = 0 ; i < size ; ++i )
      _hash_list[i] = NULL;
    return OK;
  }
  else
    return ERR;
}

int
VeriModContainer::insert( CString& name, VeriMod *data )
{
  VeriModNode *p;
  Uint hash_key = hash_key33( name ) % _size;

#ifdef debug_inner_VeriModContainer
  cout << "VeriModContainer insert start : " << name;
  cout << " to key : " << hash_key << ", data : " << data << endl;
#endif

  if(hash_key > _size)
    return ERR;
  p = _hash_list[hash_key];

  ModDagNode *tnode;
  ModDagMap::iterator imdg = _mods_in_graph.find( name );
  if( p == NULL )
  {
    if( imdg == _mods_in_graph.end() )
    {
      tnode = new ModDagNode( name, data );
      _mods_in_graph.insert( ModDagMap::value_type( name, tnode ) );
    }
    else if( imdg->second->_mod == NULL )
    {
      imdg->second->_mod = data;
    }

    _hash_list[hash_key] = new VeriModNode( name, data, NULL );
#ifdef debug_inner_VeriModContainer
    cout << "VeriModContainer insert match not found : " << name;
    cout << " data : " << data << endl;
#endif
    _modules.push_back( data );
    return OK;
  }
  else
  {
    while( p != NULL )
    {
      if( hash_cmp33( p->_name, name ) )
        return ERR;

      if( p->_next == NULL )
        break;
      p = p->_next;
    }

    if( imdg == _mods_in_graph.end() )
    {
      tnode = new ModDagNode( name, data );
      _mods_in_graph.insert( ModDagMap::value_type( name, tnode ) );
    }
    else if( imdg->second->_mod == NULL )
    {
      imdg->second->_mod = data;
    }
    p->_next = new VeriModNode( name, data, NULL );
    _modules.push_back( data );
    return OK;
  }
}

int
VeriModContainer::add_mod_conn( VeriMod *mod, const NodeList &inst_node )
{
  NodeList::const_iterator it = inst_node.begin();

  ModDagMap::iterator imdm = _mods_in_graph.find( mod->name() );

  ModDagNode *tnode = NULL;
  ModDagNode *snode = NULL;

  if( imdm == _mods_in_graph.end() )
  {
    tnode = new ModDagNode( mod->name(), mod );
    _mods_in_graph.insert( ModDagMap::value_type( mod->name(), tnode ) );
  }
  else
  {
    tnode = imdm->second;
    if( tnode->_mod == NULL )
      tnode->_mod = mod;
    else if( tnode->_mod != mod )
    {
      veri_err->append_err( ERR_ERROR, mod, vMOD_MODULE_REDEFINE );
      return vMOD_MODULE_REDEFINE;
    }
  }

  for( ; it != inst_node.end(); ++it )
  {
    CString &mod_name = (static_cast<VeriModInstantiation *>(*it))->mod_name();
    imdm = tnode->_children.find( mod_name );
    if( imdm == tnode->_children.end() )
    {
      imdm = _mods_in_graph.find( mod_name );
      if( imdm == _mods_in_graph.end() )
      {
        snode = new ModDagNode( mod_name, NULL );
        _mods_in_graph.insert( ModDagMap::value_type( mod_name, snode ) );
      }
      else
        snode = imdm->second;

      tnode->_children.insert( ModDagMap::value_type( mod_name, snode ) );
      snode->_into_this++;
    }
    else
      snode = imdm->second;

    snode->_inst.push_back( *it );
  }

  return OK;
}

int
VeriModContainer::parse_modules( CString& top_module )
{
  ModDagMap::iterator it = _mods_in_graph.find( top_module );
  if( it == _mods_in_graph.end() )
  {
    veri_err->append_err( ERR_ERROR, 0, 0, vMOD_TOP_MODULE_MISSING, " '"+top_module+"'");
    return vMOD_TOP_MODULE_MISSING;
  }

  if(it->second->_mod->is_interface())throw std::runtime_error("top must be a module, not an interface");
  _top_module = it->second;

  Cfg_mgr *cmgr = Cfg_mgr::get_instance();
  _top_module->_mod->init( cmgr->symbol_table_size() );

  int re = summarize_modules( );
  if( re != OK )
    return re;

  re = exclude_irrelevant( );
  if( re != OK )
    return re;

  re = check_cycle( );
  if( re != OK )
    return re;

  re = parse_modules( );
  if( re != OK )
    return re;

  return OK;
}

std::vector<VeriModContainer::String> VeriModContainer::root_modules() const
{
  std::vector<String> roots;
  for(const auto& item:_mods_in_graph)
    if(item.second->_mod && !item.second->_mod->is_interface() && item.second->_into_this==0)roots.push_back(item.first);
  return roots;
}

int
VeriModContainer::summarize_modules( )
{
  ModDagMap::iterator it = _mods_in_graph.begin();
  NodeList::iterator in;

  VeriModInstantiation *mod_inst = NULL;
  for( ; it != _mods_in_graph.end(); ++it )
  {
    in = it->second->_inst.begin();
    if( it->second->_mod == NULL )
    {
      for( ; in != it->second->_inst.end(); ++in )
        veri_err->append_err( ERR_WARN, *in, vMOD_MODULE_MISSING );
      continue;
    }
    else
    {
      for( ; in != it->second->_inst.end(); ++in )
      {
        mod_inst = static_cast<VeriModInstantiation *>(*in);
        mod_inst->set_inst_mod( it->second->_mod );
      }
    }
  }

  return OK;
}

std::vector< VeriModContainer::String >
VeriModContainer::missing_modules( void )
{
  std::vector<String> missing;
  ModDagMap::iterator it = _mods_in_graph.begin();
  for( ; it != _mods_in_graph.end(); ++it )
  {
    if( it->second->_mod == NULL )
    {
      missing.push_back( it->first );
    }
  }
  return missing;
}

int
VeriModContainer::exclude_irrelevant( )
{
  if( _top_module == NULL )
    return vMOD_TOP_MODULE_MISSING;

  ModDagVec stack;
  ModDagMap::iterator it;

  stack.reserve( _mods_in_graph.size() );
  stack.push_back( _top_module );
  ModDagNode *tmp = NULL;
  while( !stack.empty() )
  {
    tmp = stack.back();
    stack.pop_back();
    tmp->_used = IS_TRUE;
    for( it = tmp->_children.begin(); it != tmp->_children.end(); ++it )
    {
      if( it->second->_used == IS_FALSE )
        stack.push_back( it->second );
    }
  }

  ModDagMap tmap;
  for( it = _mods_in_graph.begin(); it != _mods_in_graph.end(); ++it )
  {
    if( it->second->_used == IS_TRUE )
      tmap.insert( ModDagMap::value_type( it->first, it->second ) );
    else
      _mods_not_used.insert( ModDagMap::value_type( it->first, it->second ) );
  }

  _mods_in_graph.clear();
  for( it = tmap.begin(); it != tmap.end(); ++it )
  {
    it->second->_used = IS_FALSE;
    _mods_in_graph.insert( ModDagMap::value_type( it->first, it->second ) );
  }

  for( it = _mods_not_used.begin(); it != _mods_not_used.end(); ++it )
    if( it->second->_mod != NULL )
      veri_err->append_err( ERR_WARN, it->second->_mod, vMOD_MODULE_NOT_USED );

  return OK;
}

int
VeriModContainer::check_cycle( )
{
  // exclude_irrelevant() removes parents outside the selected hierarchy.
  // Their incoming edges must not keep reachable shared children blocked.
  for(const auto& entry:_mods_in_graph)entry.second->_into_this=0;
  for(const auto& entry:_mods_in_graph)
    for(const auto& child:entry.second->_children)++child.second->_into_this;
  // setup bucket
  ModDagMap::iterator it = _mods_in_graph.begin();
  for( ; it != _mods_in_graph.end(); ++it )
    bucket_push( it->second->_into_this, it->second->_name, it->second );

  // check cycle
  ModDagNode *tmp = NULL;
  while( 1 )
  {
    tmp = bucket_get_zero();
    if( tmp == NULL )
      break;

    for( it = tmp->_children.begin(); it != tmp->_children.end(); ++it )
    {
      bucket_erase( it->second->_into_this, it->second->_name );
      it->second->_into_this--;
      bucket_push( it->second->_into_this, it->second->_name, it->second );
    }
    bucket_erase( 0, tmp->_name );
  }

  // check result
  int num = bucket_elem_num( );
  if( num > 0 )
  {
    veri_err->append_err( ERR_ERROR, 0, 0, vMOD_MODULE_INST_CYCLIC,
                         bucket_all_elem() );
    _mod_bucket.clear();
    return vMOD_MODULE_INST_CYCLIC;
  }

  _mod_bucket.clear();
  return OK;
}

/*
 * search declaration context-non-free feature only supports searching
 * function and task definitions, and ignore any logic-relativity-harzards.
 */
int
VeriModContainer::parse_modules( void )
{
  NodeVec stack;
  stack.push_back(_top_module->_mod);
  String help;
  while( !stack.empty() )
  {
    VeriNode* node = stack.back();
    stack.pop_back();
    int re = node->process_node_2nd(stack, help);
    // The node's retry state reports an unresolved symbol as an error.
    // Never silently accept a traversal stopped at a lookup request.
    if( re == vSEARCH_DECL ) re = node->process_node_2nd(stack, help);
    if( re != OK ) return re;
  }
  return OK;
}

int
VeriModContainer::hash_delete( CString& name )
{
  VeriModNode *p;
  VeriModNode *q;
  Uint hash_key = hash_key33( name ) % _size;

  p = _hash_list[hash_key];
  q = _hash_list[hash_key];
  if( hash_key > _size || NULL == p )
    return NOT_EXIST;

  while( p != NULL )
  {
    if( hash_cmp33( p->_name, name)){
      if(p != q)
      {
        q->_next = p->_next;
        delete p->_data;
        delete p;
        p = NULL;
        break;
      }
      else
      {
        delete p->_data;
        delete p;
        _hash_list[hash_key] = NULL;
        break;
      }
    }
    q = p;
    p = p->_next;
  }

  return OK;
}

VeriMod*
VeriModContainer::module( CString& name )
{
  Uint hash_key = hash_key33( name ) % _size;
  VeriModNode *p = _hash_list[hash_key];
  if(hash_key > _size || NULL == p )
    return NULL;

  while( p != NULL )
  {
    if( hash_cmp33( p->_name, name) )
    {
#ifdef debug_inner_VeriModContainer
      cout << "VeriModContainer hash_value : " << name << " " << p->data() << endl;
#endif
      return p->_data;
    }
    p = p->_next;
  }
  return NULL;
}

int
VeriModContainer::dump_all_modules( CString& dir, VeriAstDrawer *drawer )
{
  drawer->init( dir, _top_module->_mod->name() );
  drawer->prep_for_drawing( );
  drawer->draw_ast( _top_module->_mod );
  drawer->draw_symbol( _top_module->_mod->symbol_table( ) );
  drawer->end_drawing( );
  
  return OK;
}

void
VeriModContainer::clear( void )
{
  VeriModNode *p;
  VeriModNode *q;
  if( _hash_list != NULL )
  {
    for( Uint i = 0 ; i < _size ; ++i )
    {
      p = _hash_list[i];
      if( p != NULL )
      {
        while( p != NULL )
        {
          q = p;
          p = p->_next;
          delete q->_data;
          delete q;
          q = NULL;
        }
      }
    }
    delete[] _hash_list;
  }
  _hash_list = NULL;

  clear_mod_graph( _mods_in_graph );
  clear_mod_graph( _mods_not_used );
  _mod_bucket.clear();
  _modules.clear();
  _top_module = NULL;
}

void
VeriModContainer::clean_up( void )
{
  VeriModNode *p;  
  VeriModNode *q;  
  if( _hash_list != NULL )
  {
    for( Uint i = 0 ; i < _size ; ++i )
    {
      p = _hash_list[i];
      if( p != NULL )
      {
        while(p != NULL)
        {
          q = p;  
          p = p->_next;
          delete q->_data;
          delete q;
        }
      } // end if(p)
    } // end for
  } // end if( _hash_list != NULL )

  clear_mod_graph( _mods_in_graph );
  clear_mod_graph( _mods_not_used );
  _mod_bucket.clear();
  delete[] _hash_list;
  _hash_list = NULL;
  _size = 0;
  _top_module = NULL;
  _modules.clear();
}

void
VeriModContainer::clear_mod_graph( ModDagMap& map )
{
  ModDagMap::iterator it = map.begin();
  for( ; it != map.end(); ++it )
    delete it->second;
  map.clear();
}

#ifdef debug_VeriModContainer
void
VeriModContainer::hash_print( void )
{
  int count = 0;
  VeriModNode *p;

  cout << endl;
  cout << "VeriModContainer hash_table summarization : " << endl;
  cout << "size is " << _size << endl;

  for( Uint i = 0 ; i < _size ; ++i )
  {
    p = _hash_list[i];
    while(p){
      count++;
      cout << p->_name << "\t\t\t";
      p = p->_next;
    }
    if( count > 0 )
    {
      cout << "node " << i << " = " << count << endl;
    }
    count = 0;
  }
}
#endif

};
