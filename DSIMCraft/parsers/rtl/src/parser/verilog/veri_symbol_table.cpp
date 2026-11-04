/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_var_container.cpp
 * Summary  : verilog syntax analyzer :: variable container functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */
#include "general_err.hpp"

#include "veri_node.hpp"
#include "veri_symbol_table.hpp"
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "veri_exp.hpp"
#include "veri_stmt.hpp"
#include <algorithm>
#include <stdexcept>

#ifdef DEBUG_PARSER
#include <iostream>
using std::cout;
using std::endl;
#endif

namespace rtl
{

int
VeriSymbolTable::init( Uint size, CString& mod_name )
{
  if( size == 0 )
    return OK;

  return hash_create( size, 0, NULL, mod_name, vMOD_SCOPE );
}

int
VeriSymbolTable::hash_create( Uint size, int depth, SymbolTable *floater,
                              CString& name, int table_type )
{
  if( size != 0 )
  {
    _depth   = depth;
    // Most lexical scopes contain only a few names. Inheriting the global
    // 524287-bucket setting for every function used megabytes per scope.
    _size    = std::min(size,Uint(31));
    _symbol_count = 0;
    _name    = name;
    _table_type = table_type;
    _floater = floater;
    _hash_list = new Symbol*[_size];
    for( Uint i = 0 ; i < _size ; ++i )
      _hash_list[i] = NULL;
    return OK;
  }
  else
    return ERR;
}

void
VeriSymbolTable::clean_up( void )
{
  _symbol_count=0;
  _class_base=nullptr;_class_owner=nullptr;
  _compilation_scope=nullptr;_previous_imports=nullptr;
  _compilation_unit=false;_pending_import_bindings.clear();
  _wildcard_imports.clear();_explicit_imports.clear();_wildcard_bindings.clear();
  _import_sources.clear();_export_packages.clear();_explicit_exports.clear();
  _pending_exports.clear();_export_all=false;
  if( !_deeper.empty() )
  { 
    ContList::iterator it = _deeper.begin();
    for( ; it != _deeper.end(); ++it )
      delete *it;
    _deeper.clear();
  }

  Symbol *p;
  Symbol *q;
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
          q->_next = NULL;
          q->_data = NULL;
          delete q;
          q = NULL;
        }
      }
      _hash_list[i] = NULL;
    }
  }
}

VeriSymbolTable *
VeriSymbolTable::append_scope( CString& name, int table_type )
{
  if( _size != 0 )
  {
    SymbolTable *deeper = new SymbolTable;
    deeper->hash_create( _size, _depth + 1, this, name, table_type );
    _deeper.push_back( deeper );
    return deeper;
  }
  else
    return NULL;
}

VeriSymbolTable *
VeriSymbolTable::finish_scope( void )
{
  int symbol_cnt = 0;

  Symbol *p = NULL;
  Symbol *q = NULL;

  if( _hash_list != NULL )
  {
    for( Uint i = 0 ; i < _size ; ++i )
    {
      p = _hash_list[i];
      if( p != NULL )
      {
        symbol_cnt = 1;
        break;
      }
    }
    if(     symbol_cnt == 0 )
//        || _table_type == vTASK_SCOPE
//        || _table_type == vFUNC_SCOPE )
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
            q->_next = NULL;
            q->_data = NULL;
            delete q;
            q = NULL;
          }
        }
        _hash_list[i] = NULL;
      }
    }
  }
  return _floater;
}

int
VeriSymbolTable::insert( CString& name, VeriNode* data)
{
  if(!name.empty()&&name.front()!='\\'&&name.find("::")!=String::npos)throw std::runtime_error("qualified name cannot be declared: "+name);
  if(_explicit_imports.count(name))throw std::runtime_error("declaration conflicts with explicit package import: "+name);
  if(_wildcard_bindings.count(name))throw std::runtime_error("declaration conflicts with used wildcard package import: "+name);
  if(_symbol_count>=_size&&_size<(1u<<30))grow();
  Symbol *p, *q;
  Uint hash_key = hash_key33( name.c_str() ) % _size;

  if(hash_key > _size)
    return NOT_EXIST;
  p = _hash_list[hash_key];

  if( p == NULL )
  {
    p = new Symbol;
    p->_name = name;
    p->_data = data;
    p->_next = NULL;
    _hash_list[hash_key] = p;
  }
  else
  {
    while( p != NULL )
    {
      if( hash_cmp33( p->_name.c_str() , name.c_str() ) ) // duplicated
        return ERR;

      q = p;
      p = p->_next;
    }
    p = new Symbol;
    p->_name = name;
    p->_data = data;
    p->_next = NULL;
    q->_next = p;
  }
  ++_symbol_count;
  return OK;
}

void VeriSymbolTable::grow() {
  const Uint size=_size*2+1;
  auto** buckets=new Symbol*[size]();
  for(Uint i=0;i<_size;++i) {
    auto* symbol=_hash_list[i];
    while(symbol) {
      auto* next=symbol->_next;
      const Uint key=hash_key33(symbol->_name.c_str())%size;
      symbol->_next=buckets[key];buckets[key]=symbol;symbol=next;
    }
  }
  delete[] _hash_list;_hash_list=buckets;_size=size;
}

int
VeriSymbolTable::hash_delete( CString& name )
{
  Symbol *p;
  Symbol *q;
  Uint hash_key = hash_key33( name.c_str() ) % _size;

  p = _hash_list[hash_key];
  q = p;

  if( hash_key > _size || NULL == p )
    return NOT_EXIST;

  while( p != NULL )
  {
    if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
    {
      if(_symbol_count)--_symbol_count;
      if(p != q)
      {
        q->_next = p->_next;
        delete p;
        p = NULL;
        break;
      }
      else
      {
        _hash_list[hash_key] = p->_next;
        delete p;
        break;
      }
    }
    q = p;
    p = p->_next;
  }

  return OK;
}

VeriNode *
VeriSymbolTable::value( CString& name )
{
  if(!name.empty()&&name.front()!='\\'&&name.find("::")!=String::npos)return value_within_module(name);
#ifdef DEBUG_PARSER
//  cout << "symbal_table::value(name) : " << name << endl;
#endif

  const Uint hash_key = hash_key33( name.c_str() );

  Symbol  *p = NULL;
  SymbolTable *ptr = this;

  while( 1 )
  {
    if( ptr->_hash_list != NULL )
    {
      p = ptr->_hash_list[hash_key % ptr->_size];
      while( p != NULL )
      {
        if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
          return p->_data;
        p = p->_next;
      }
    }

    if(ptr->_class_base)if(auto* member=ptr->_class_base->class_member(name)) {
      // A local base member is absent from derived lexical lookup. Continue
      // outwards so an enclosing declaration of the same name can be found.
      if(!veri_local_class_member(member)){veri_check_class_access(member,this);return member;}
    }
    if(auto* imported=ptr->imported_value(name))return imported;
    if(ptr->_compilation_scope)if(auto* symbol=ptr->_compilation_scope->value(name))return symbol;
    if( ptr->_floater != NULL )
      ptr = ptr->_floater;
    else
      break;
  }
  return NULL;
}

VeriNode *
VeriSymbolTable::value_same_level( CString& name )
{
  auto imported=_explicit_imports.find(name);
  if(imported!=_explicit_imports.end())return imported->second;
  auto binding=_wildcard_bindings.find(name);
  if(binding!=_wildcard_bindings.end())return binding->second;
#ifdef DEBUG_PARSER
//  cout << "symbal_table::value_within_module(name) : " << name << endl;
#endif

  Uint hash_key = hash_key33( name.c_str() ) % _size;

  if(hash_key > _size)
    return NULL;

  Symbol  *p = NULL;

  if( _hash_list != NULL )
  {
    p = _hash_list[hash_key];
    while( p != NULL )
    {
      if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
        return p->_data;
      p = p->_next;
    }
  }
  
  return NULL;
}

int
VeriSymbolTable::replace_value_same_level( CString& name, VeriNode *data )
{
#ifdef DEBUG_PARSER
//  cout << "symbal_table::value_within_module(name) : " << name << endl;
#endif

  Uint hash_key = hash_key33( name.c_str() ) % _size;

  if(hash_key > _size)
    return ERR;

  Symbol  *p = NULL;

  if( _hash_list != NULL )
  {
    p = _hash_list[hash_key];
    while( p != NULL )
    {
      if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
      {
        p->_data = data;
        return OK;
      }
      p = p->_next;
    }
  }
  
  return ERR;
}

VeriNode *
VeriSymbolTable::value_within_module( CString& name )
{
  const auto separator=!name.empty()&&name.front()=='\\'?String::npos:name.find("::");
  if(separator!=String::npos) {
    auto* package=veri_parser->package(name.substr(0,separator));
    auto* symbol=package&&package->scope()?package->scope()->package_value(name.substr(separator+2)):nullptr;
    if(symbol)return symbol;
    // Resolve a class namespace lexically, preserving the declaration's symbol
    // identity (including inherited properties and canonical specializations).
    auto prefix=name.substr(0,separator),rest=name.substr(separator+2);
    if(package) {
      auto next=rest.find("::");
      if(next==String::npos)throw std::runtime_error("package member not found: "+name);
      symbol=package->scope()->package_value(rest.substr(0,next));rest=rest.substr(next+2);
    } else {
      // An unadorned self-class prefix inside a class/out-of-block declaration
      // denotes its current specialization, not the default specialization.
      for(auto* context=this;context;context=context->floater())if(auto* cls=context->class_owner()) {
        if((cls->class_origin()?cls->class_origin()->label():cls->label())==prefix){symbol=cls->class_symbol();break;}
      }
      if(!symbol)symbol=value_within_module(prefix);
      if(!symbol&&prefix=="process")symbol=VeriParser::get_instance()->process_type();
    }
    if(!symbol||symbol->tok_type()!=vtTYPE)throw std::runtime_error("unknown or not yet declared package: "+prefix);
    auto* owner=veri_class_type(symbol);
    if(!owner)throw std::runtime_error("scope resolution requires a class type: "+prefix);
    if(owner->generic_class())owner=owner->specialize(nullptr,this)->class_type();
    while(owner) {
      owner->ensure_class_elaborated();auto next=rest.find("::");
      symbol=owner->class_member(rest.substr(0,next));
      if(!symbol)throw std::runtime_error("class member not found: "+name);
      veri_check_class_access(symbol,this);
      if(next==String::npos)return symbol;
      owner=symbol->tok_type()==vtTYPE?veri_class_type(symbol):nullptr;rest=rest.substr(next+2);
    }
    throw std::runtime_error("scope resolution requires a class type: "+name);
    return symbol;
  }
#ifdef DEBUG_PARSER
//  cout << "symbal_table::value_within_module(name) : " << name << endl;
#endif

  const Uint hash_key = hash_key33( name.c_str() );

  Symbol  *p = NULL;
  SymbolTable *ptr = this;

  while( 1 )
  {
    if( ptr->_hash_list != NULL )
    {
      p = ptr->_hash_list[hash_key % ptr->_size];
      while( p != NULL )
      {
        if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
          return p->_data;
        p = p->_next;
      }
    }

    if(ptr->_class_base)if(auto* member=ptr->_class_base->class_member(name)) {
      // A local base member is absent from derived lexical lookup. Continue
      // outwards so an enclosing declaration of the same name can be found.
      if(!veri_local_class_member(member)){veri_check_class_access(member,this);return member;}
    }
    if(auto* imported=ptr->imported_value(name))return imported;
    if(ptr->_compilation_scope)if(auto* symbol=ptr->_compilation_scope->value(name))return symbol;
    if( ptr->_table_type != vMOD_SCOPE && ptr->_floater != NULL )
      ptr = ptr->_floater;
    else
      break;
  }
  return NULL;
}

VeriNode* VeriSymbolTable::package_value(CString& name) {
  if(_explicit_imports.count(name)||_wildcard_bindings.count(name)) {
    if(_export_all||_explicit_exports.count(name))return value_same_level(name);
    const auto sources=_import_sources.find(name);
    if(sources!=_import_sources.end())for(auto* source:sources->second)
      if(std::find(_export_packages.begin(),_export_packages.end(),source->_name)!=_export_packages.end())
        return value_same_level(name);
    return NULL;
  }
  auto* symbol=value_same_level(name);
  return symbol&&symbol->tok_type()!=vtMOD?symbol:NULL;
}

void VeriSymbolTable::inherit_imports(SymbolTable* previous) {
  // Borrow canonical declarations without copying their ASTs or owning their
  // class scopes. Later views cannot mutate an earlier declaration point.
  for(Uint i=0;i<previous->_size;++i)
    for(auto* symbol=previous->_hash_list[i];symbol;symbol=symbol->_next)
      if(insert(symbol->_name,symbol->_data)!=OK)
        throw std::runtime_error("duplicate compilation-unit declaration: "+symbol->_name);
  _wildcard_imports=previous->_wildcard_imports;
  _explicit_imports=previous->_explicit_imports;
  _import_sources=previous->_import_sources;
  _previous_imports=previous;
}

VeriNode* VeriSymbolTable::prior_import_binding(CString& name) {
  auto it=_wildcard_bindings.find(name);
  if(it!=_wildcard_bindings.end())return it->second;
  return _previous_imports?_previous_imports->prior_import_binding(name):nullptr;
}

void VeriSymbolTable::finalize_compilation_imports() {
  // Module elaboration follows hierarchy order, while $unit binding follows
  // source order. An ambiguous later view may be resolved by an earlier
  // module that was elaborated afterwards. Provisional choices never become
  // real wildcard bindings and may not resolve another ambiguous lookup.
  for(const auto& pending:_pending_import_bindings) {
    auto* prior=_previous_imports?_previous_imports->prior_import_binding(pending.first):nullptr;
    if(prior!=pending.second)throw std::runtime_error("ambiguous wildcard package import: "+pending.first);
  }
  if(_previous_imports)for(const auto& entry:_explicit_imports) {
    auto* prior=_previous_imports->prior_import_binding(entry.first);
    if(prior&&prior!=entry.second)throw std::runtime_error("conflicting explicit package import after used wildcard: "+entry.first);
  }
  if(_previous_imports)for(Uint i=0;i<_size;++i)
    for(auto* symbol=_hash_list[i];symbol;symbol=symbol->_next) {
      auto* prior=_previous_imports->prior_import_binding(symbol->_name);
      if(prior&&prior!=symbol->_data)
        throw std::runtime_error("compilation-unit declaration conflicts with used wildcard package import: "+symbol->_name);
    }
}

VeriNode* VeriSymbolTable::imported_value(CString& name) {
  auto explicit_import=_explicit_imports.find(name);
  if(explicit_import!=_explicit_imports.end())return explicit_import->second;
  auto binding=_wildcard_bindings.find(name);
  if(binding!=_wildcard_bindings.end())return binding->second;
  if(_previous_imports)if(auto* prior=_previous_imports->prior_import_binding(name))return prior;
  VeriNode* result=NULL;bool ambiguous=false;
  std::vector<SymbolTable*> sources;
  for(auto* package:_wildcard_imports)if(auto* symbol=package->package_value(name)) {
    if(result&&result!=symbol) {
      if(!_compilation_unit)throw std::runtime_error("ambiguous wildcard package import: "+name);
      ambiguous=true;
    }
    if(!result)result=symbol;
    sources.push_back(package);
  }
  if(ambiguous) {_pending_import_bindings[name]=result;return result;}
  if(result) {_wildcard_bindings.emplace(name,result);_import_sources[name]=std::move(sources);}
  return result;
}

void VeriSymbolTable::import_package(SymbolTable* package,CString& member) {
  if(member=="*") {
    if(std::find(_wildcard_imports.begin(),_wildcard_imports.end(),package)==_wildcard_imports.end())_wildcard_imports.push_back(package);
    resolve_exports(false);
    return;
  }
  auto* symbol=package->package_value(member);
  if(!symbol)throw std::runtime_error("package member not found in import: "+member);
  if(auto* local=value_same_level(member))if(local!=symbol)throw std::runtime_error("conflicting explicit package import: "+member);
  _explicit_imports[member]=symbol;
  auto& sources=_import_sources[member];
  if(std::find(sources.begin(),sources.end(),package)==sources.end())sources.push_back(package);
  resolve_exports(false);
}

void VeriSymbolTable::export_package(CString& name,CString& member) {
  if(name=="*") {_export_all=true;return;}
  if(member=="*") {
    // A wildcard export is a filter on imports, not an import or lookup. It
    // may precede the import and need not name a package that is imported.
    if(std::find(_export_packages.begin(),_export_packages.end(),name)==_export_packages.end())
      _export_packages.push_back(name);
    return;
  }
  _pending_exports.emplace_back(name,member);
  resolve_exports(false);
}

void VeriSymbolTable::resolve_exports(bool final) {
  for(auto it=_pending_exports.begin();it!=_pending_exports.end();) {
    auto* definition=veri_parser->package(it->first);
    auto* package=definition?definition->scope():NULL;
    const auto& name=it->second;
    auto sources=_import_sources.find(name);
    const bool actual=sources!=_import_sources.end()&&
      std::find(sources->second.begin(),sources->second.end(),package)!=sources->second.end();
    const bool candidate=std::find(_wildcard_imports.begin(),_wildcard_imports.end(),package)!=_wildcard_imports.end();
    if(!actual&&!candidate) {
      if(final)throw std::runtime_error("export requires an import from the named package: "+it->first+"::"+name);
      ++it;continue;
    }
    auto* target=package->package_value(name);
    if(!target)throw std::runtime_error("package member not found in export: "+it->first+"::"+name);
    auto* local=value_same_level(name);
    if(local&&local!=target)throw std::runtime_error("export conflicts with declaration: "+name);
    // Like a direct import, an explicit export selects its named package even
    // if other unused wildcard candidates have the same spelling.
    _explicit_imports[name]=target;
    // An already bound declaration can be reached through another path to the
    // same original declaration. Do not copy or allocate a second symbol.
    auto& paths=_import_sources[name];
    if(std::find(paths.begin(),paths.end(),package)==paths.end())paths.push_back(package);
    _explicit_exports[name]=target;
    it=_pending_exports.erase(it);
  }
}

void VeriSymbolTable::finalize_exports() {resolve_exports(true);}

void 
VeriSymbolTable::clear()
{
  clean_up();
  delete[] _hash_list;
  _hash_list = NULL;
}

int
VeriSymbolTable::pretty_dot_output( Ofstream& ofile, int depth )
{
  Symbol *p;
  if( _hash_list == NULL )
    return OK;

  for( Uint i = 0 ; i < _size ; ++i )
  {
    p = _hash_list[i];
    while( p != NULL )
    {
      if(      p->_data->tok_type( ) != vtMOD
          && ( p->_data->tok_type( ) != vtTASK || _table_type != vTASK_SCOPE )
          && ( p->_data->tok_type( ) != vtFUNC || _table_type != vFUNC_SCOPE )
        )
      {
        p->_data->pretty_dot_label( ofile, depth );
      }
      p = p->_next;
    }
  }
  return OK;
}

int
VeriSymbolTable::push_more_table( SymbolTableQueue & queue )
{
  ContList::iterator it = _deeper.begin();
  for( ; it != _deeper.end(); ++it )
    queue.push( *it );

  return OK;
}

#ifdef debug_VeriSymbolTable
void VeriSymbolTable::hash_print( )
{
  hash_print_recur( 0 );
}

void
VeriSymbolTable::hash_print_recur( int depth )
{
  int count = 0;
  Symbol *p;
  int j, k;

  cout << endl;
  for( j = 0 ; j < depth ; ++j )
    cout << "  ";
  cout << "type hash_table summarization : " << endl;

  for( j = 0 ; j < depth ; ++j )
    cout << "  ";
  cout << "size is " << _size << endl;

  for( Uint i = 0 ; i < _size ; ++i )
  {
    p = _hash_list[i];
    while( p != NULL )
    {
      count++;
      for( j = 0 ; j < depth ; ++j )
        cout << "  ";
    //  if( p->data()->id() == ctype_FUNC )
    //  {
    //    cout << "func::";
    //    k = -6;
    //  }
    //  else
    //    k = 0;

    //  cout << p->_name;
    //  k += 35 - p->_name.size() - depth * 2;
      for( j = 0 ; j < k ; ++j )
        cout << " ";
      p = p->_next;
    }
    if( count > 0 )
    {
      for( j = 0 ; j < depth ; ++j )
        cout << "  ";
      cout << "node " << i << " = " << count << endl;
    }
    count = 0;
  }
  ContList::iterator ictl = _deeper.begin();
  for( ; ictl != _deeper.end() ; ++ictl )
    ictl->hash_print_recur( depth + 1 );
}
#endif

};
