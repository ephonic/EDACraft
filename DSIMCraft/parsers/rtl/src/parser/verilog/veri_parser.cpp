/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_parser.cpp
 * Summary  : verilog syntax-analyzer functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include <assert.h>
#include <algorithm>
#include <stdexcept>
#include <iostream>
#include <vector>
#include <set>

#include <cstdlib>
#include <cstring>

#include "verilog_yacc.hpp"

extern int veriloglex_destroy( void );

#include "general_err.hpp"
#include "veri_err_token.hpp"
#include "verilog_token.hpp"

#include "cfg_mgr.hpp"
#include "src_mgr.hpp"

#include "veri_ast_node.hpp"
#include "veri_err.hpp"

#include "veri_node.hpp"
#include "veri_decl.hpp"
#include "veri_exp.hpp"
#include "veri_inst.hpp"
#include "veri_stmt.hpp"
#include "veri_module.hpp"

#include "veri_symbol_table.hpp"
#include "veri_mod_container.hpp"
#include "veri_parser.hpp"

rtl::VeriParser *veri_parser = NULL;

extern int verilog_syntax_errors;
extern int verilog_first_error_line;
extern int veri_lno;
extern int veri_col;

namespace rtl
{

#define debug_verilog_parser_

VeriParser::VeriParser()
  : _top_mod_name("")
  , _s(NULL)
  , _length(0)
  , _mod(NULL)
  , _mods(NULL)
{
  _cmgr = Cfg_mgr::get_instance();
  _smgr = Src_mgr::get_instance();
  _err  = VeriErr::get_instance();

  veri_parser = this;
}

VeriParser::~VeriParser()
{
  clear();
}

int
VeriParser::init( void )
{
  clear();
  _s      = _smgr->src();
  _length = _smgr->src_len();
  _fname.push_back( _smgr->fname() );
  _fline.push_back( 0 );

  _node_pool.clear();
  _node_pool.init( _cmgr->node_pool_size(), _cmgr->node_pool_hash_mod() );

  _err->clean_up();

  // Reset Flex scanner state so the next parse starts fresh.
  veriloglex_destroy();
  ::veri_lno = 1;
  ::veri_col = 0;

  _top_mod_name.clear();
  _infer_top=false;
  _systemverilog=true;
  _time_resolver={};_compilation_unit_fs=_compilation_precision_fs=_time_precision_fs=0;
  _compilation_item_seen=false;_compilation_times.clear();
  _default_subroutine_automatic=false;_class_lifetimes.clear();

  _mods = new ModContainer;
  _mods->init( _cmgr->module_container_size() );
  return OK;
}

void
VeriParser::clean_up( void )
{
  _virtual_interface_types.clear();
  _subroutine_bindings.clear();
  _deferred_semantics.clear();
  for(auto* package:_package_order)delete package;
  _package_order.clear();_packages.clear();
  for(auto* owner:_compilation_declarations)delete owner;
  _compilation_declarations.clear();
  for(auto* scope:_compilation_import_scopes)delete scope;
  _compilation_import_scopes.clear();
  _compilation_scopes.clear();_compilation_items.clear();_source_declarations.clear();
  delete _builtin_scope;_builtin_scope=nullptr;_ipc_types.clear();
  _fname.clear();
  _fline.clear();
  _top_mod_name.clear();
  _infer_top=false;
  _systemverilog=true;
  _time_resolver={};_compilation_unit_fs=_compilation_precision_fs=_time_precision_fs=0;
  _compilation_item_seen=false;_compilation_times.clear();
  _default_subroutine_automatic=false;_class_lifetimes.clear();
  _mod_instantiations.clear();

  _s          = NULL;
  _length     = 0;

  _node_pool.clean_up();

  for(auto& binding:_bindings)delete binding.owner;
  if(_binding_saved_mod){delete _binding_saved_mod;_mod=nullptr;}
  _bindings.clear();_binding_saved_mod=nullptr;_binding_saved_instances.clear();

  _err->clean_up();
  if( _mods != NULL )
    _mods->clean_up( );

  clear_syntree();
}

void
VeriParser::clear( void )
{
  _subroutine_bindings.clear();
  // A failed semantic pass can leave borrowed nodes in the pending queue.
  // Drop them before releasing their owning AST, as clean_up() already does.
  _deferred_semantics.clear();
  for(auto* package:_package_order)delete package;
  _package_order.clear();_packages.clear();
  for(auto* owner:_compilation_declarations)delete owner;
  _compilation_declarations.clear();
  for(auto* scope:_compilation_import_scopes)delete scope;
  _compilation_import_scopes.clear();
  _compilation_scopes.clear();_compilation_items.clear();_source_declarations.clear();
  delete _builtin_scope;_builtin_scope=nullptr;_ipc_types.clear();
  _fname.clear();
  _fline.clear();
  _top_mod_name.clear();
  _infer_top=false;
  _systemverilog=true;
  _time_resolver={};_compilation_unit_fs=_compilation_precision_fs=_time_precision_fs=0;
  _compilation_item_seen=false;_compilation_times.clear();
  _default_subroutine_automatic=false;_class_lifetimes.clear();
  _mod_instantiations.clear();

  _s          = NULL;
  _length     = 0;

  _node_pool.clear();
  for(auto& binding:_bindings)delete binding.owner;
  if(_binding_saved_mod){delete _binding_saved_mod;_mod=nullptr;}
  _bindings.clear();_binding_saved_mod=nullptr;_binding_saved_instances.clear();
  _err->clean_up();

  if( _mods != NULL )
    delete _mods;
  _mods = NULL;

  clear_syntree();
}

int
VeriParser::parse( void )
{
  _mod = new VeriMod( _node_pool.next_id( ) );
  _mod_instantiations.clear();

  _err->reset_file( );
  _err->include_file( 0, _fname.back() );

  ::verilog_syntax_errors = 0;
  ::verilog_first_error_line = 0;
  int re = verilogparse( );
  if (::verilog_syntax_errors != 0) re = ERR;
  if(_binding_saved_mod) {
    _mod=_binding_saved_mod;_binding_saved_mod=nullptr;
    _mod_instantiations=std::move(_binding_saved_instances);
  }
  if( _mod != NULL )
    delete _mod;
  _mod = NULL;

  if( _err->has_err( ) == IS_TRUE ) {
    return ERR;
  }

  if( re != OK ) return re;
  resolve_extern_methods();
  resolve_bindings();
  // Packages own one shared lexical scope, independent of module instances.
  // Elaborate in declaration order; imports of later packages are rejected.
  for(auto* declaration:_source_declarations) {
    if(declaration->detail_type()==vsDECL_IMPORT) {
      auto* symbols=new VeriSymbolTable;
      symbols->init(_cmgr->symbol_table_size(),"$unit");symbols->set_compilation_unit();
      _compilation_import_scopes.push_back(symbols);
      if(!_compilation_scopes.empty())symbols->inherit_imports(_compilation_scopes.back());
      _compilation_scopes.push_back(symbols);
      declaration->set_scope(symbols);NodeVec stack;String help;
      const int status=declaration->process_node_2nd(stack,help);
      if(status!=OK)return status;
      continue;
    }
    auto* package=static_cast<VeriMod*>(declaration);
    package->init(_cmgr->symbol_table_size());
    NodeVec stack;String help;
    if(package->is_compilation_unit()) {
      auto* symbols=package->scope();symbols->set_compilation_unit();
      if(!_compilation_scopes.empty())symbols->inherit_imports(_compilation_scopes.back());
      _compilation_scopes.push_back(symbols);
      package->item()->set_scope(symbols);stack.push_back(package->item());
    } else stack.push_back(package);
    while(!stack.empty()) {
      auto* node=stack.back();stack.pop_back();
      int status=node->process_node_2nd(stack,help);
      if(status==vSEARCH_DECL)status=node->process_node_2nd(stack,help);
      if(status!=OK)return status;
    }
    if(!package->is_compilation_unit())package->scope()->finalize_exports();
  }
  for(auto* module:_mods->all_modules()) {
    const auto count=module->compilation_item_count();
    if(count)module->set_compilation_scope(_compilation_scopes.at(count-1));
  }
  if(_infer_top) {
    const auto roots=_mods->root_modules();
    if(roots.size()==1)_top_mod_name=roots.front();
    else if(std::find(roots.begin(),roots.end(),"top")!=roots.end())_top_mod_name="top";
    else {
      std::string names;for(const auto& root:roots){if(!names.empty())names+=", ";names+=root;}
      throw std::runtime_error(roots.empty()?"cannot infer a top module; use --top":
          "multiple top modules ("+names+"); select one with --top");
    }
  }
  // Callers collecting syntax from multiple files do not select a top yet.
  if( _top_mod_name.empty() ) return OK;
  re = _mods->parse_modules( _top_mod_name );
  if( re != OK ) return re;
  re = finish_deferred_semantics();
  if(re!=OK)return re;
  for(auto* symbols:_compilation_scopes)symbols->finalize_compilation_imports();
  return _err->has_err() == IS_TRUE ? ERR : OK;
}

int VeriParser::finish_deferred_semantics() {
  for(size_t i=0;i<_deferred_semantics.size();++i) {
    NodeVec stack{_deferred_semantics[i]};String help;
    while(!stack.empty()) {
      auto* node=stack.back();stack.pop_back();
      int status=node->process_node_2nd(stack,help);
      if(status==vSEARCH_DECL)status=node->process_node_2nd(stack,help);
      if(status!=OK)return status;
    }
  }
  _deferred_semantics.clear();
  return _err->has_err() == IS_TRUE ? ERR : OK;
}

int
VeriParser::append_module( VeriMod *mod )
{
  VeriMod * t = _mods->module( mod->name() );
  if( t != NULL )
  {
    String other = "'"+mod->name()+"'; previous declaration ["+int2string(t->line())+" : "+int2string(t->col())+"]";
    _err->append_err( ERR_ERROR, mod->line(), mod->col(),
                      vMOD_MODULE_REDEFINE, other );
    delete _mod;
    _mod = NULL;
    return vMOD_MODULE_REDEFINE;
  }
  else
    _mods->insert( mod->name(), _mod );

  const char* trace_module_append = std::getenv("FSYN_TRACE_MODULE_APPEND");
  if( trace_module_append && *trace_module_append != '\0' )
    std::cerr << "[fsyn] parser append module: " << mod->name()
              << std::endl;

  return OK;
}

VeriMod *
VeriParser::module( CString& name )
{
  return _mods->module( name );
}

VeriMod* VeriParser::package(CString& name) const {
  auto found=_packages.find(name);return found==_packages.end()?NULL:found->second;
}

VeriNode* VeriParser::gen_package(int line,int col,const char* name,VeriNode* items,const char* end_name) {
  if(_packages.count(name))throw std::runtime_error("duplicate package: "+String(name));
  if(end_name&&String(end_name)!=name)throw std::runtime_error("endpackage name does not match package: "+String(name));
  auto* package=_mod;package->set_line(line);package->set_col(col);package->set_name(name);package->set_package();
  resolve_time_scope(package,items);_compilation_item_seen=true;
  package->set_fname(_fname,_fline);package->set_item(items);
  if(items) {
    items->set_father(package);
    for(auto* item:static_cast<VeriModuleItemList*>(items)->item_list()) {
      const auto kind=item->detail_type();
      if(kind==vsDECL_TIME||kind==vsDECL_PARAM||kind==vsDECL_IMPORT||kind==vsDECL_EXPORT||kind==vsDECL_FUNC_DECL||kind==vsDECL_TASK_DECL)continue;
      if(kind==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(item)->class_declaration())continue;
      if(kind==vsDECL_VAR) {
        auto* declaration=static_cast<VeriVarDecl*>(item);
        if(!declaration->is_typedef()&&(declaration->inout()!=vpNO_IO||declaration->net_type()==vvWIRE||declaration->net_type()==vvTRI))
          throw std::runtime_error("line "+std::to_string(item->line())+": package variables cannot be nets or module ports");
        continue;
      }
      if(kind==vsDECL_INT)continue;
      throw std::runtime_error("line "+std::to_string(item->line())+": unsupported package item; expected declarations, imports, exports or subroutines");
    }
  }
  _packages.emplace(name,package);_package_order.push_back(package);_source_declarations.push_back(package);
  prep_for_new_mod();return package;
}

void VeriParser::compilation_import(VeriNode* node) {
  _compilation_item_seen=true;
  if(node->detail_type()==vsDECL_FUNC_DECL)throw std::runtime_error("compilation-unit DPI imports are not supported yet; declare the import in a package or module");
  // The placeholder module will be discarded; the parser owns this import.
  node->set_birth_mod(nullptr);
  _compilation_items.push_back(node);_source_declarations.push_back(node);
}

void VeriParser::compilation_declaration(VeriNode* node) {
  if(!systemverilog())throw std::runtime_error("compilation-unit declarations require SystemVerilog");
  if(node->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(node)->forward_class())
    throw std::runtime_error("compilation-unit forward class declarations are not supported yet");
  auto* owner=_mod;owner->set_name("$unit");owner->set_compilation_unit();
  owner->set_line(node->line());owner->set_col(node->col());owner->set_fname(_fname,_fline);
  auto* items=gen_mod_item_list(node);owner->set_item(items);items->set_father(owner);
  resolve_time_scope(owner,items);_compilation_item_seen=true;
  _compilation_declarations.push_back(owner);_source_declarations.push_back(owner);
  // Modules capture the number of preceding lexical events, including types.
  _compilation_items.push_back(owner);
  prep_for_new_mod();
}

VeriNode* VeriParser::gen_import(int line,int col,const char* name,const char* member,bool exporting) {
  auto* node=new VeriImportStmt(next_id(),line,col,_mod,name,member,exporting);insert_node(node);return node;
}

int
VeriParser::prep_for_new_mod( void )
{
  _default_subroutine_automatic=false;_class_lifetimes.clear();
  _mod = new VeriMod( _node_pool.next_id( ) );
  _mod_instantiations.clear();
  return OK;
}

/*
VeriNode *
VeriParser::gen_sys_var( const char *name, int line, int col )
{
  VeriNode * node = new VeriSysVar( _node_pool.next_id( ), line, col, name );
  _node_pool.insert( node );
  return node;
}
*/

VeriNode *
VeriParser::gen_dummy_port( int line, int col )
{
  VeriDummyPort * port = new VeriDummyPort( _node_pool.next_id( ), line, col, _mod );
  _node_pool.insert( port );
  return port;
}

VeriNode *
VeriParser::gen_port_ref( int line, int col, const char *port_name)
{
//  if( port_ref == NULL || port_ref->detail_type() != veEXP_PRI )
//  {
//    return port_ref;
//  }

//  VeriPrimaryExp * pexp = static_cast<VeriPrimaryExp *>(port_ref);
//  VeriPortRefExp * ref = new VeriPortRefExp( _node_pool.next_id( ), line, col,
//                                             pexp->str(), _mod );
//  _node_pool.insert( ref );
  VeriPortRefExp * ref = new VeriPortRefExp( _node_pool.next_id( ), line, col,
                                             port_name, _mod );
  _node_pool.insert( ref );

  return ref;
}

VeriNode *
VeriParser::gen_primary( const char *str, int line, int col, int primary_type )
{
  String iname = "";
  if( str != NULL )
    iname = str;

  VeriExp * exp
    = new VeriPrimaryExp( _node_pool.next_id( ), line, col,
                          iname, primary_type, _mod );
  _node_pool.insert( exp );
  return exp;
}

VeriNode* VeriParser::gen_time_literal(const char* text,int line,int col) {
  if(!systemverilog())throw std::runtime_error("time literals require SystemVerilog");
  auto* node=static_cast<VeriPrimaryExp*>(gen_primary(text,line,col,veNUM));
  node->set_time_literal();return node;
}
VeriNode* VeriParser::gen_time_declaration(int line,int col,const char* unit,const char* precision) {
  auto* node=new VeriTimeDecl(next_id(),line,col,_mod,unit?veri_time_unit(unit):0,precision?veri_time_unit(precision):0);
  insert_node(node);return node;
}
namespace {
void merge_time_declaration(uint64_t& target,uint64_t value,bool late,int line) {
  if(!value)return;
  if(target && target!=value)throw std::runtime_error("line "+std::to_string(line)+": repeated time declaration must match its previous value");
  if(!target && late)throw std::runtime_error("line "+std::to_string(line)+": time declaration must precede other items in its time scope");
  target=value;
}
}
void VeriParser::compilation_time(VeriNode* node) {
  auto* declaration=static_cast<VeriTimeDecl*>(node);
  merge_time_declaration(_compilation_unit_fs,declaration->unit_fs,_compilation_item_seen,node->line());
  merge_time_declaration(_compilation_precision_fs,declaration->precision_fs,_compilation_item_seen,node->line());
  if(_compilation_unit_fs && _compilation_precision_fs>_compilation_unit_fs)
    throw std::runtime_error("compilation-unit time precision must not be coarser than its time unit");
  if(declaration->precision_fs)_time_precision_fs=_time_precision_fs?std::min(_time_precision_fs,declaration->precision_fs):declaration->precision_fs;
  node->set_birth_mod(nullptr);_compilation_times.push_back(node);
}
void VeriParser::resolve_time_scope(VeriMod* mod,VeriNode* items) {
  auto result=_time_resolver?_time_resolver(mod->line()):VeriTimeScale{};
  if(!result.directive) {
    if(_compilation_unit_fs)result.unit_fs=_compilation_unit_fs;
    if(_compilation_precision_fs)result.precision_fs=_compilation_precision_fs;
  }
  uint64_t unit=0,precision=0;bool late=false;
  if(items)for(auto* item:static_cast<VeriModuleItemList*>(items)->item_list()) {
    if(item->detail_type()!=vsDECL_TIME){late=true;continue;}
    auto* declaration=static_cast<VeriTimeDecl*>(item);
    merge_time_declaration(unit,declaration->unit_fs,late,item->line());
    merge_time_declaration(precision,declaration->precision_fs,late,item->line());
  }
  if(unit)result.unit_fs=unit;
  if(precision)result.precision_fs=precision;
  if(result.precision_fs>result.unit_fs)
    throw std::runtime_error("line "+std::to_string(mod->line())+": time precision must not be coarser than its time unit");
  mod->set_time_scale(result);
  _time_precision_fs=_time_precision_fs?std::min(_time_precision_fs,result.precision_fs):result.precision_fs;
}

VeriNode *
VeriParser::gen_dump_target( VeriNode *prefix, const char *component, int line, int col )
{
  // Dump selections are elaboration names, not value expressions. Store exact
  // identifier components, including escaped dots, without variable lookup.
  // Whitespace cannot occur in an identifier, so unit separator is unambiguous.
  String path = prefix ? static_cast<VeriPrimaryExp *>(prefix)->str() : String();
  path += '\x1f';
  path += component;
  return gen_primary(path.c_str(), line, col, veSTR);
}

VeriNode *
VeriParser::gen_range( VeriNode *left, int rtype, VeriNode *right )
{
  VeriExp * exp
    = new VeriRangeExp( _node_pool.next_id( ), left->line(), left->col(),
                        left, rtype, right, _mod );
  _node_pool.insert( exp );
  left->set_father( exp );
  if( right != NULL )
    right->set_father( exp );
  return exp;
}

VeriNode *
VeriParser::gen_array( VeriNode *id, VeriNode *range )
{
  VeriArrayExp *array = NULL;
  if( id->tok_type() == vtEXP && range->tok_type() == vtEXP )
  {
    switch( id->detail_type() )
    {
      case veEXP_ARRAY :
        if( range->detail_type() == veEXP_RANGE )
        {
          static_cast<VeriArrayExp *>(id)->append_range( range );
          range->set_father( id );
        }
        array = static_cast<VeriArrayExp *>(id);
        break;

      case veEXP_MEMBER :
      case veEXP_PRI :
        array = new VeriArrayExp( _node_pool.next_id( ), id->line(),
                                  id->col(), id, _mod );
        _node_pool.insert( array );
        id->set_father( array );

        if( range->detail_type() == veEXP_RANGE )
        {
          array->append_range( range );
          range->set_father( array );
        }

        break;

      default:
        break;
    }
  }
  return array;
}

VeriNode* VeriParser::gen_array_type_query(const char* name,int type,int line,int col,VeriNode* range,VeriNode* dimension) {
  const std::string text(name);
  if(veri_real(type))throw std::runtime_error("size/range query requires a bit-stream or array type");
  if(text!="$dimensions"&&text!="$unpacked_dimensions"&&text!="$left"&&text!="$right"&&text!="$low"&&text!="$high"&&text!="$increment"&&text!="$size")
    throw std::runtime_error("only $bits and array queries accept a data type");
  if(range&&veri_integral_atom(type))throw std::runtime_error("packed dimensions require bit/logic/reg data type");
  const auto width=std::to_string(veri_type_width(type));
  auto* descriptor=gen_unary(vtSYS_QUERY_TYPE,line,col,range?range:gen_primary(width.c_str(),line,col,veNUM));
  VeriNode* args=descriptor;
  if(dimension)args=gen_multi(descriptor,dimension,vemCOMMA_EXP,line,col);
  return gen_caller(gen_primary(name,line,col,veVAR),args);
}

VeriNode *
VeriParser::gen_caller( VeriNode *name, VeriNode *call_exp )
{
  if(name&&name->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(name)->multi_type()==vemDYNAMIC_NEW) {
    auto* allocation=static_cast<VeriMultiExp*>(name);
    if(!call_exp||allocation->exp().size()!=1)throw std::runtime_error("new[] requires exactly one initializer array");
    allocation->append_child(call_exp);call_exp->set_father(allocation);return allocation;
  }
  if(name&&name->detail_type()==veEXP_MEMBER) {
    auto* member=static_cast<VeriMemberExp*>(name);
    if(member->called())throw std::runtime_error("enum method result is not callable");
    member->set_call(call_exp);return member;
  }
  if(name&&name->detail_type()==veEXP_PRI) {
    const auto& text=static_cast<VeriPrimaryExp*>(name)->str();
    const auto separator=text.rfind("::");
    if(systemverilog()&&separator!=std::string::npos&&text.substr(separator+2)=="self"&&!package(text.substr(0,separator))) {
      // Resolve the prefix semantically, so process typedefs and user classes
      // named process retain their lexical type identity.
      auto prefix=text.substr(0,separator);
      auto* receiver=gen_type_expression(name->line(),name->col(),prefix.c_str(),-1,0);
      auto* call=static_cast<VeriMemberExp*>(gen_member(receiver,"self",name->line(),name->col()));
      call->set_scope_reference();call->set_call(call_exp);return call;
    }
    if(systemverilog()&&(text=="std::randomize"||text=="randomize")) {
      const bool scoped=text=="std::randomize"||_class_lifetimes.empty();
      auto* receiver=scoped?gen_type_expression(name->line(),name->col(),"std",-1,0):gen_primary("this",name->line(),name->col(),veVAR);
      auto* call=static_cast<VeriMemberExp*>(gen_member(receiver,"randomize",name->line(),name->col()));
      if(scoped)call->set_scope_reference();call->set_call(call_exp);return call;
    }
    if(text=="$cast") {
      if(!systemverilog())throw std::runtime_error("$cast requires SystemVerilog mode");
      if(veri_system_arguments(call_exp).size()!=2)throw std::runtime_error("$cast requires exactly two arguments");
      return gen_unary(vtSYS_CAST,name->line(),name->col(),call_exp);
    }
    if(text=="$fread") {
      const auto count=veri_system_arguments(call_exp).size();
      if(count<2||count>4)throw std::runtime_error(text+" argument count mismatch");
      return gen_unary(vtSYS_FREAD,name->line(),name->col(),call_exp);
    }
    if(text=="$sscanf"||text=="$fscanf") {
      if(veri_system_arguments(call_exp).size()<2)throw std::runtime_error(text+" argument count mismatch");
      return gen_unary(text=="$sscanf"?vtSYS_SSCANF:vtSYS_FSCANF,name->line(),name->col(),call_exp);
    }
    const int file_op=text=="$fopen"?vtSYS_FOPEN:text=="$fgetc"?vtSYS_FGETC:
        text=="$ungetc"?vtSYS_UNGETC:text=="$feof"?vtSYS_FEOF:
        text=="$fgets"?vtSYS_FGETS:text=="$ftell"?vtSYS_FTELL:
        text=="$fseek"?vtSYS_FSEEK:text=="$rewind"?vtSYS_REWIND:0;
    if(file_op) {
      auto args=veri_system_arguments(call_exp);
      const size_t count=file_op==vtSYS_FSEEK?3:file_op==vtSYS_FGETS||file_op==vtSYS_UNGETC?2:1;
      if(args.size()!=count&&!(file_op==vtSYS_FOPEN&&args.size()==2))
        throw std::runtime_error(text+" argument count mismatch");
      return gen_unary(file_op,name->line(),name->col(),call_exp);
    }
    if(text=="$sformatf"||text=="$test$plusargs"||text=="$value$plusargs") {
      auto args=veri_system_arguments(call_exp);
      if(args.empty()||(text=="$test$plusargs"&&args.size()!=1)||(text=="$value$plusargs"&&args.size()!=2))
        throw std::runtime_error(text+" argument count mismatch");
      return gen_unary(text=="$sformatf"?vtSYS_SFORMATF:text=="$test$plusargs"?vtSYS_TEST_PLUSARGS:vtSYS_VALUE_PLUSARGS,name->line(),name->col(),call_exp);
    }
    const int sampled=text=="$sampled"?vtSYS_SAMPLED:text=="$past"?vtSYS_PAST:
        text=="$rose"?vtSYS_ROSE:text=="$fell"?vtSYS_FELL:
        text=="$stable"?vtSYS_STABLE:text=="$changed"?vtSYS_CHANGED:0;
    if(sampled) {
      if(!systemverilog())throw std::runtime_error(text+" requires SystemVerilog mode");
      auto args=veri_system_arguments(call_exp);
      if(args.empty()||args.size()>(sampled==vtSYS_PAST?3u:1u))
        throw std::runtime_error(text+(sampled==vtSYS_PAST?" requires one to three arguments; explicit sampling clocks are not supported":" requires exactly one argument; explicit sampling clocks are not supported"));
      return gen_unary(sampled,name->line(),name->col(),call_exp);
    }
    if(text=="$random"||text=="$urandom"||text=="$urandom_range") {
      if(text!="$random"&&!systemverilog())throw std::runtime_error("line "+std::to_string(name->line())+": "+text+" requires SystemVerilog mode");
      auto args=veri_system_arguments(call_exp);
      const bool range=text=="$urandom_range";
      if((range&&(args.empty()||args.size()>2))||(!range&&args.size()>1))
        throw std::runtime_error("line "+std::to_string(name->line())+": "+text+(range?" requires one or two arguments":" accepts at most one seed argument"));
      const int op=range?vtSYS_URANDOM_RANGE:text=="$random"?(args.empty()?vtSYS_RANDOM:vtSYS_RANDOM_SEEDED):(args.empty()?vtSYS_URANDOM:vtSYS_URANDOM_SEEDED);
      // Keep the unary AST's nonnull child clone/cleanup contract. The opcode
      // distinguishes the zero-argument form from an explicit zero seed.
      return gen_unary(op,name->line(),name->col(),call_exp?call_exp:gen_primary("0",name->line(),name->col(),veNUM));
    }
    int op=text=="$itor"?vtSYS_ITOR:text=="$rtoi"?vtSYS_RTOI:
           text=="$realtobits"?vtSYS_REALTOBITS:text=="$bitstoreal"?vtSYS_BITSTOREAL:
           text=="$shortrealtobits"?vtSYS_SHORTREALTOBITS:text=="$bitstoshortreal"?vtSYS_BITSTOSHORTREAL:
           text=="$typename"?vtSYS_TYPENAME:text=="$bits"?vtSYS_BITS:text=="$clog2"?vtSYS_CLOG2:
           text=="$isunknown"?vtSYS_ISUNKNOWN:text=="$countones"?vtSYS_COUNTONES:
           text=="$onehot"?vtSYS_ONEHOT:text=="$onehot0"?vtSYS_ONEHOT0:
           text=="$countbits"?vtSYS_COUNTBITS:text=="$dimensions"?vtSYS_DIMENSIONS:
           text=="$unpacked_dimensions"?vtSYS_UNPACKED_DIMENSIONS:text=="$left"?vtSYS_LEFT:
           text=="$right"?vtSYS_RIGHT:text=="$low"?vtSYS_LOW:text=="$high"?vtSYS_HIGH:
           text=="$increment"?vtSYS_INCREMENT:text=="$size"?vtSYS_SIZE:0;
    if(op) {
      if(op==vtSYS_COUNTBITS||veri_is_array_query(op)) {
        auto args=veri_system_arguments(call_exp);
        const bool dimensions=op==vtSYS_DIMENSIONS||op==vtSYS_UNPACKED_DIMENSIONS;
        if((op==vtSYS_COUNTBITS&&args.size()<2)||(veri_is_array_query(op)&&(args.empty()||args.size()>(dimensions?1u:2u))))
          throw std::runtime_error("line "+std::to_string(name->line())+": "+text+(op==vtSYS_COUNTBITS?" requires a value and at least one control bit":dimensions?" requires exactly one argument":" requires one or two arguments"));
        return gen_unary(op,name->line(),name->col(),call_exp);
      }
      if(call_exp&&call_exp->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(call_exp)->multi_type()==vemCOMMA_EXP) {
        auto& items=static_cast<VeriMultiExp*>(call_exp)->exp();
        if(items.size()!=1)throw std::runtime_error("line "+std::to_string(name->line())+": "+text+" requires exactly one argument");
        call_exp=items.front();
      }
      if(!call_exp)throw std::runtime_error("line "+std::to_string(name->line())+": "+text+" requires exactly one argument");
      return gen_unary(op,name->line(),name->col(),call_exp);
    }
  }
  VeriExp *exp = NULL;
  VeriMultiExp *arg = NULL;
  if(     name->tok_type() != vtEXP
      || (call_exp != NULL && call_exp->tok_type() != vtEXP) )
  { /* not okay */;}
  else
  {
    if( call_exp != NULL )
    {
      switch( call_exp->detail_type() )
      {
        case veEXP_NAMED_PARAM :
          arg = new VeriMultiExp( _node_pool.next_id( ),
                                  vemPORT_EXP, call_exp->line(),
                                  call_exp->col(), _mod );
          _node_pool.insert( arg );
          arg->append_child( call_exp );
          call_exp->set_father( arg );
          break;

        case veEXP_CALLER :
        case veEXP_QUES :
        case veEXP_MEMBER :
        case veEXP_TYPE :
        case veEXP_PRI :
        case veEXP_UNA :
        case veEXP_ARRAY :
        case veEXP_BIN :
        case veEXP_MCONCAT :
        case veEXP_SIGN :
        case veEXP_UNSIGN :
          arg = new VeriMultiExp( _node_pool.next_id( ),
                                  vemCOMMA_EXP, call_exp->line(),
                                  call_exp->col(), _mod );
          _node_pool.insert( arg );
          arg->append_child( call_exp );
          call_exp->set_father( arg );
          break;

        case veEXP_MULTI :
        {
          VeriMultiExp * mexp = static_cast<VeriMultiExp *>(call_exp);
          switch( mexp->multi_type() )
          {
            case vemCOMMA_EXP :
            case vemPORT_EXP :
            case vemPORT_INST_EXP :
              arg = static_cast<VeriMultiExp *>(call_exp);
              break;

            default:
              // A multi-expression can itself be one argument (null, new,
              // concatenation, assignment pattern, inside, ...). Only actual
              // comma/connection lists are argument lists. Never drop values.
              arg=new VeriMultiExp(_node_pool.next_id(),vemCOMMA_EXP,call_exp->line(),call_exp->col(),_mod);
              _node_pool.insert(arg);arg->append_child(call_exp);call_exp->set_father(arg);
              break;
          }
          break;
        }

        default:
          break;
      }
    }
    switch( name->detail_type())
    {
      case veEXP_PRI :
      case veEXP_ARRAY :
        exp = new VeriCallerExp( _node_pool.next_id( ),
                                 name->line(), name->col(),
                                 name, arg, _mod );
        _node_pool.insert( exp );
        name->set_father( exp );
        break;

      case veEXP_PORT_REF :
      {
        VeriPortRefExp *npexp = static_cast<VeriPortRefExp *>(name);
        exp = new VeriNamedParamExp( _node_pool.next_id( ),
                                    name->line(), name->col(),
                                    npexp->port_ref(), arg, _mod );
        _node_pool.insert( exp );
        break;
      }

      default:
        break;
    }
  }
  if(arg&&exp)arg->set_father(exp);
  return exp;
}

VeriNode *
VeriParser::gen_type_cast(int type,int signing,int line,int col,VeriNode* operand)
{
  const std::string width=std::to_string(veri_type_width(type));
  auto* size=gen_primary(width.c_str(),line,col,veNUM);
  const int op=type==vvSTRING?vtCAST_STRING:veri_real(type)?(type==vvSHORTREAL?vtCAST_SHORTREAL:vtCAST_REAL):veri_two_state(type)?(signing==IS_TRUE?vtCAST_SIGNED2:vtCAST_UNSIGNED2)
                                  :(signing==IS_TRUE?vtCAST_SIGNED4:vtCAST_UNSIGNED4);
  return gen_binary(size,op,line,col,operand);
}

VeriNode *
VeriParser::gen_unary( int op, int line, int col, VeriNode *exp1 )
{
  if(op==vtSYS_TYPENAME&&!systemverilog())throw std::runtime_error("$typename requires SystemVerilog mode");
  VeriExp *exp = NULL;
  int re;
  switch( op )
  {
    /* normal unary expression */
    case vtUADD  :  case vtUSUB  :  case vtUNEG  :  case vtUAND  :
    case vtUOR   :  case vtUNAND :  case vtUNOR  :  case vtUXNOR :
    case vtUNOT  :  case vtUXOR  :
    case vtSYS_RANDOM:case vtSYS_URANDOM:case vtSYS_URANDOM_RANGE:
    case vtSYS_RANDOM_SEEDED:case vtSYS_URANDOM_SEEDED:
    case vtSYS_SAMPLED:case vtSYS_PAST:case vtSYS_ROSE:case vtSYS_FELL:
    case vtSYS_STABLE:case vtSYS_CHANGED:
    case vtSYS_FOPEN:case vtSYS_FGETC:case vtSYS_UNGETC:case vtSYS_FEOF:
    case vtSYS_FGETS:case vtSYS_FTELL:case vtSYS_FSEEK:case vtSYS_REWIND:
    case vtSYS_SSCANF:case vtSYS_FSCANF:case vtSYS_FREAD:case vtSYS_CAST:
    case vtSYS_SFORMATF:case vtSYS_TEST_PLUSARGS:case vtSYS_VALUE_PLUSARGS:
    case vtSYS_BITS:case vtSYS_CLOG2:case vtSYS_ISUNKNOWN:case vtSYS_COUNTONES:
    case vtSYS_TYPENAME:
    case vtSYS_ONEHOT:case vtSYS_ONEHOT0:case vtSYS_RANGE_BITS:
    case vtSYS_COUNTBITS:case vtSYS_DIMENSIONS:case vtSYS_UNPACKED_DIMENSIONS:
    case vtSYS_LEFT:case vtSYS_RIGHT:case vtSYS_LOW:case vtSYS_HIGH:
    case vtSYS_INCREMENT:case vtSYS_SIZE:case vtSYS_QUERY_TYPE:
    case vtSYS_ITOR:case vtSYS_RTOI:case vtSYS_REALTOBITS:case vtSYS_BITSTOREAL:
    case vtSYS_SHORTREALTOBITS:case vtSYS_BITSTOSHORTREAL:
    case vtUPREINC : case vtUPREDEC : case vtUPOSTINC : case vtUPOSTDEC :
      exp = new VeriUnaryExp( _node_pool.next_id( ), line, col, op, exp1, _mod );
      _node_pool.insert( exp );
      re = exp->check_child_validation();
      if( re == OK && exp1 != NULL )
        exp1->set_father( exp );
      break;

    /* event expression */
    case vtUPOSE :  case vtUNEGE :
      exp = new VeriEventExp( _node_pool.next_id( ), line, col, op, exp1, _mod );
      _node_pool.insert( exp );
      re = exp->check_child_validation();
      if( re == OK && exp1 != NULL )
        exp1->set_father( exp );
      break;

    default:
      break;
  }
  return exp;
}

VeriNode *VeriParser::gen_conditional_event(VeriNode *event, VeriNode *condition, int line, int col)
{
  VeriEventExp *node;
  if(event->detail_type()==veEXP_EVENT) {
    node=static_cast<VeriEventExp*>(event);
    if(node->condition())throw std::runtime_error("line "+std::to_string(line)+": duplicate iff qualifier");
  } else {
    node=new VeriEventExp(_node_pool.next_id(),line,col,0,event,_mod);
    _node_pool.insert(node);event->set_father(node);
  }
  node->set_condition(condition);condition->set_father(node);
  return node;
}

VeriNode *
VeriParser::gen_binary( VeriNode *exp1, int op,
                        int line, int col, VeriNode *exp2, bool declaration )
{
  if((op==vtSTREAM_LEFT||op==vtSTREAM_RIGHT)&&!systemverilog())
    throw std::runtime_error("streaming concatenation requires SystemVerilog mode");
  VeriExp *exp = NULL;
  int re;
  switch( op )
  {
    /* normal binary expression */
    case vtBPOW  :  case vtBNAND :  case vtBNOR  :  case vtBXNOR :
    case vtBMOD  :  case vtBMUL  :  case vtBDIV  :  case vtBADD  :
    case vtBSUB  :  case vtBLRS  :  case vtBLLS  :  case vtBARS  :
    case vtBALS  :  case vtBLT   :  case vtBGT   :  case vtBLE   :
    case vtBGE   :  case vtBLEQ  :  case vtBLIEQ :  case vtBCEQ  :
    case vtBCIEQ :  case vtBSAND :  case vtBSXOR :  case vtBSOR  :
    case vtBDAND :  case vtBDOR  :
    case vtSTREAM_LEFT:case vtSTREAM_RIGHT:
    case vtBWLEQ: case vtBWLNEQ: case vtBINSIDE:
    case vtCAST_SIZE:case vtCAST_SIGNED4:case vtCAST_UNSIGNED4:case vtCAST_SIGNED2:case vtCAST_UNSIGNED2:
    case vtCAST_REAL:case vtCAST_SHORTREAL:case vtCAST_STRING:
      exp = new VeriBinaryExp( _node_pool.next_id( ), line, col, exp1, op, exp2, _mod );
      _node_pool.insert( exp );
      re  = exp->check_child_validation();
      if( re == OK )
      {
        exp1->set_father( exp );
        exp2->set_father( exp );
      }
      break;

    /* assign expression */
    case vtASSIGN:
      exp = new VeriAssignExp( _node_pool.next_id( ), line, col, exp1, exp2, _mod );
      exp->set_is_decl(declaration?IS_TRUE:IS_FALSE);
      _node_pool.insert( exp );
      re  = exp->check_child_validation();
      if( re == OK )
      {
        exp1->set_father( exp );
        exp2->set_father( exp );
      }
      break;

    /* multiple concatenation is added here */
    case vtMULTI_CONCAT:
      exp = new VeriMultiConcatExp( _node_pool.next_id( ), line, col, exp1, exp2, _mod );
      _node_pool.insert( exp );
      re  = exp->check_child_validation();
      if( re == OK )
      {
        exp1->set_father( exp );
        exp2->set_father( exp );
      }
      break;

    default:
      break;
  }
  return exp;
}

VeriNode *
VeriParser::gen_mintypmax( VeriNode *exp1, int line, int col,
                         VeriNode *exp2, VeriNode *exp3 )
{
  VeriExp *exp = new VeriMintypmaxExp( _node_pool.next_id( ), line, col,
                                     exp1, exp2, exp3, _mod );
  _node_pool.insert( exp );
  int re = exp->check_child_validation();
  if( re == OK )
  {
    exp1->set_father( exp );
    exp2->set_father( exp );
    exp3->set_father( exp );
  }

  return exp;
}

VeriNode *
VeriParser::gen_ques_exp( VeriNode *ques, int line, int col,
                         VeriNode *choice1, VeriNode *choice2 )
{
  VeriExp *exp = new VeriQuesExp( _node_pool.next_id( ), line, col,
                                  ques, choice1, choice2, _mod );
  _node_pool.insert( exp );
  int re = exp->check_child_validation();
  if( re == OK )
  {
    ques->set_father( exp );
    choice1->set_father( exp );
    choice2->set_father( exp );
  }

  return exp;
}

VeriNode *
VeriParser::gen_multi( VeriNode *exp1, VeriNode *exp2,
                       int mtype, int line, int col )
{
  if(mtype==vemDYNAMIC_NEW||mtype==vemOBJECT_NEW||mtype==vemNULL) {
    auto* result=new VeriMultiExp(_node_pool.next_id(),mtype,line,col,_mod);_node_pool.insert(result);
    if(exp1){result->append_child(exp1);exp1->set_father(result);}
    if(exp2){result->append_child(exp2);exp2->set_father(result);}return result;
  }
  assert( exp1->tok_type() == vtEXP && exp2->tok_type() == vtEXP );

  if(mtype==vemCOMMA_EXP) {
    // Preserve a flat call/connection list when positional and named entries mix.
    const bool list=exp1->detail_type()==veEXP_MULTI &&
      (static_cast<VeriMultiExp*>(exp1)->multi_type()==vemCOMMA_EXP ||
       static_cast<VeriMultiExp*>(exp1)->multi_type()==vemPORT_EXP ||
       static_cast<VeriMultiExp*>(exp1)->multi_type()==vemPORT_INST_EXP);
    const int prior=list?static_cast<VeriMultiExp*>(exp1)->multi_type():vemCOMMA_EXP;
    const bool first_named=exp1->detail_type()==veEXP_NAMED_PARAM || (list&&prior==vemPORT_EXP);
    const bool second_named=exp2->detail_type()==veEXP_NAMED_PARAM;
    const bool port=first_named||second_named||(list&&prior==vemPORT_INST_EXP)||
      exp1->detail_type()==veEXP_DUMMY_PORT||exp2->detail_type()==veEXP_DUMMY_PORT;
    if(port) {
      mtype=first_named&&second_named?vemPORT_EXP:vemPORT_INST_EXP;
      if(list)static_cast<VeriMultiExp*>(exp1)->set_multi_type(mtype);
    }
  }

  if( mtype == vemCOMMA_EXP
      && ( exp1->detail_type() == veEXP_EVENT
           || exp2->detail_type() == veEXP_EVENT ) )
  {
    // Verilog event controls allow either @(a or b) or @(a, b).
    // Normalize comma-separated event controls to the event-list form.
    mtype = vemEVENT_EXP;
  }

  int re;
  VeriMultiExp * mexp = NULL;
  if( exp1->detail_type() == veEXP_MULTI
      && static_cast<VeriMultiExp *>(exp1)->multi_type() == mtype )
  {
    mexp = static_cast<VeriMultiExp *>(exp1);
    mexp->append_child( exp2 );
    re = mexp->check_last_child_validation( );
    if( re == OK )
      exp2->set_father( mexp );
    return mexp;
  }
  else
  {
    mexp = new VeriMultiExp( _node_pool.next_id( ), mtype, line, col, _mod );
    _node_pool.insert( mexp );
    mexp->append_child( exp1 );
    mexp->append_child( exp2 );
    re = mexp->check_child_validation();
    if( re == OK )
    {
      exp1->set_father( mexp );
      exp2->set_father( mexp );
    }
    return mexp;
  }
}

VeriNode *
VeriParser::gen_pattern(int kind,VeriNode* first,VeriNode* second) {
  if(!systemverilog())throw std::runtime_error("assignment patterns require SystemVerilog mode");
  // Always allocate: a nested pattern must remain a single list entry.
  auto* list=new VeriMultiExp(_node_pool.next_id(),kind,first->line(),first->col(),_mod);
  _node_pool.insert(list);list->append_child(first);first->set_father(list);
  if(second){list->append_child(second);second->set_father(list);}return list;
}

VeriNode* VeriParser::gen_empty_pattern(int line,int col) {
  if(!systemverilog())throw std::runtime_error("assignment patterns require SystemVerilog mode");
  auto* node=new VeriMultiExp(next_id(),vemASSIGN_PATTERN,line,col,_mod);
  insert_node(node);return node;
}

VeriNode* VeriParser::gen_empty_concat(int line,int col) {
  if(!systemverilog())throw std::runtime_error("empty queue literals require SystemVerilog mode");
  auto* node=new VeriMultiExp(next_id(),vemCONCAT_EXP,line,col,_mod);
  insert_node(node);return node;
}

VeriNode *
VeriParser::gen_pattern_field(const char* name,VeriNode* value,int line,int col) {
  auto* field=new VeriNamedParamExp(_node_pool.next_id(),line,col,String(name),value,_mod);
  _node_pool.insert(field);value->set_father(field);return field;
}

VeriNode *
VeriParser::gen_inside_set(VeriNode* first) {
  auto* list=new VeriMultiExp(_node_pool.next_id(),vemINSIDE_SET,first->line(),first->col(),_mod);
  _node_pool.insert(list);list->append_child(first);first->set_father(list);return list;
}

VeriNode *
VeriParser::gen_concat_exp( VeriNode *mexp )
{
  VeriMultiExp *mul_exp = NULL;
  if( mexp->tok_type() == vtEXP )
  {
    if( mexp->detail_type() == veEXP_MULTI )
    {
      mul_exp = static_cast<VeriMultiExp *>(mexp);
      mul_exp->set_multi_type( vemCONCAT_EXP );
    }
    else
    {
      mul_exp = new VeriMultiExp( _node_pool.next_id( ), vemCONCAT_EXP,
                                  mexp->line(), mexp->col(), _mod );
      _node_pool.insert( mul_exp );
      mul_exp->append_child( mexp );
      int re = mul_exp->check_last_child_validation( );
      if( re == OK )
        mexp->set_father( mul_exp );
    }
  }
  return mul_exp;
}

VeriNode *
VeriParser::gen_delay_exp( int line, int col, VeriNode *d1, VeriNode *dextra, VeriNode *dthird )
{
  // Every procedural delay expression stays a single expression, including
  // unary/selected/concatenated operands. The old switch returned NULL for
  // unary minus and dereferenced it while building the timing statement.
  if (d1 == NULL)
    throw std::runtime_error("line " + std::to_string(line) + ": unsupported delay expression");
  // Parenthesized comma expressions already form an ordered list in this
  // grammar. Unpack it here instead of adding ambiguous delay-list productions.
  if (dextra == NULL && dthird == NULL && d1->detail_type() == veEXP_MULTI) {
    VeriMultiExp *multi = static_cast<VeriMultiExp *>(d1);
    if (multi->multi_type() == vemCOMMA_EXP) {
      const NodeList &items = multi->exp();
      if (items.empty() || items.size() > 3)
        throw std::runtime_error("line " + std::to_string(line) + ": delay requires one to three values");
      NodeList::const_iterator it = items.begin();
      d1 = *it++;
      if (it != items.end()) dextra = *it++;
      if (it != items.end()) dthird = *it;
    }
  }
  VeriDelayExp *delay = new VeriDelayExp(_node_pool.next_id(), line, col,
                                        d1, dextra, dthird, _mod);
  _node_pool.insert(delay);
  d1->set_father(delay);
  if (dextra != NULL) dextra->set_father(delay);
  if (dthird != NULL) dthird->set_father(delay);
  delay->check_child_validation();

  return delay;
}

VeriNode *
VeriParser::gen_drive_exp( int line, int col, int drive_from, int drive_to)
{
  VeriDriveExp * drive = new VeriDriveExp( _node_pool.next_id( ), line, col,
                                           drive_from, drive_to, _mod  );
  _node_pool.insert( drive );

  drive->check_child_validation( );
  return drive;
}

VeriNode *
VeriParser::gen_signed_exp( int line, int col, VeriNode *exp )
{
  VeriSignExp * sign = new VeriSignExp( _node_pool.next_id( ), line, col,
                                        exp, _mod );
  _node_pool.insert( sign );

  int re = sign->check_child_validation( );
  if( re == OK )
    exp->set_father( sign );
  return sign;
}

VeriNode *
VeriParser::gen_unsigned_exp( int line, int col, VeriNode *exp )
{
  VeriUnsignExp * unsign = new VeriUnsignExp( _node_pool.next_id( ),
                                              line, col, exp, _mod );
  _node_pool.insert( unsign );

  int re = unsign->check_child_validation( );
  if( re == OK )
    exp->set_father( unsign );

  return unsign;
}

VeriNode *
VeriParser::gen_loop_stmt( int line, int col, VeriNode *init,
                           VeriNode *judge, VeriNode *iter,
                           VeriNode *content, int kind )
{
  VeriLoopStmt * stmt = new VeriLoopStmt( _node_pool.next_id( ), line, col, init,
                                       judge, iter, content, _mod );
  stmt->set_kind(static_cast<VeriLoopStmt::Kind>(kind));
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if( init   != NULL ) init  ->set_father( stmt );
    if( judge  != NULL ) judge ->set_father( stmt );
    if( iter   != NULL ) iter  ->set_father( stmt );
    if( content!= NULL ) content->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_func_loop_stmt( int line, int col, VeriNode *init,
                                VeriNode *judge, VeriNode *iter,
                                VeriNode *content )
{
  VeriStmt * stmt = new VeriFuncLoopStmt( _node_pool.next_id( ), line, col, init,
                                           judge, iter, content, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    init ->set_father( stmt );
    judge->set_father( stmt );
    iter ->set_father( stmt );
    content->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_gen_loop_stmt( int line, int col, VeriNode *init,
                               VeriNode *judge, VeriNode *iter,
                               const char *label, int label_line,
                               int label_col, VeriNode *content )
{
  // Generate steps do not use the value of a postfix/prefix update. Normalize
  // both to the existing assignment elaborator, with distinct identifier ASTs.
  if(auto* update=dynamic_cast<VeriUnaryExp*>(iter)) {
    const int op=update->op();
    if(op>=vtUPREINC&&op<=vtUPOSTDEC) {
      auto* operand=dynamic_cast<VeriPrimaryExp*>(update->exp_child());
      if(!operand||operand->pri_type()!=veVAR)
        throw std::runtime_error("line "+std::to_string(line)+": generate update requires a genvar identifier");
      auto* read=gen_primary(operand->str().c_str(),operand->line(),operand->col(),veVAR);
      auto* one=gen_primary("1",line,col,veNUM);
      auto* value=gen_binary(read,(op==vtUPREINC||op==vtUPOSTINC)?vtBADD:vtBSUB,line,col,one);
      iter=gen_binary(operand,vtASSIGN,line,col,value);
    }
  }
  String ilabel = "";
  if( label != NULL )
    ilabel = label;

  // Normalize empty bodies to the same owned list shape as nonempty loops.
  if( !content ) content=gen_gen_item_list(gen_dummy_inst(line,col));
  VeriInst * stmt = new VeriGenLoop( _node_pool.next_id( ), line, col, init,
                                     judge, iter, ilabel, label_line,
                                     label_col, content, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    init ->set_father( stmt );
    judge->set_father( stmt );
    iter ->set_father( stmt );
    content->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_default_case_item( int line, int col, VeriNode *item )
{
  VeriStmt * stmt = new VeriDefaultCaseItem( _node_pool.next_id( ),
                                             line, col, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_func_default_case_item( int line, int col, VeriNode *item )
{
  VeriStmt * stmt = new VeriFuncDefaultCaseItem( _node_pool.next_id( ),
                                                 line, col, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_default_gen_case_item( int line, int col, VeriNode *item )
{
  VeriInst * stmt = new VeriDefaultGenCaseItem( _node_pool.next_id( ),
                                                line, col, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_case_item( VeriNode *label, VeriNode *item )
{
  VeriCaseItem * stmt = new VeriCaseItem( _node_pool.next_id( ),
                                          label->line(),
                                          label->col(), item, _mod );
  _node_pool.insert( stmt );

  switch( label->detail_type() )
  {
    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(label);
      // A concatenation is one case expression. Only a comma expression
      // denotes multiple alternative labels for the same branch.
      if( mexp->multi_type() != vemCOMMA_EXP && mexp->multi_type() != vemINSIDE_SET )
      {
        stmt->append_label( label );
        label->set_father( stmt );
        break;
      }
      NodeList &labels = mexp->exp();
      NodeList::iterator it = labels.begin();
      for( ; it != labels.end(); ++it )
      {
        stmt->append_label( *it );
        (*it)->set_father( stmt );
      }
      break;
    }

    case veEXP_MEMBER : case veEXP_ARRAY  : case veEXP_PRI : case veEXP_UNA : case veEXP_BIN :
    case veEXP_CALLER : case veEXP_MCONCAT : case veEXP_QUES :
    case veEXP_SIGN   : case veEXP_UNSIGN : case veEXP_MINTY :
      stmt->append_label( label );
      label->set_father( stmt );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_func_case_item( VeriNode *label, VeriNode *item )
{
  VeriFuncCaseItem * stmt = new VeriFuncCaseItem( _node_pool.next_id( ),
                                                   label->line(),
                                                   label->col(), item, _mod );
  _node_pool.insert( stmt );

  switch( label->detail_type() )
  {
    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(label);
      // A concatenation is one case expression. Only a comma expression
      // denotes multiple alternative labels for the same branch.
      if( mexp->multi_type() != vemCOMMA_EXP && mexp->multi_type() != vemINSIDE_SET )
      {
        stmt->append_label( label );
        label->set_father( stmt );
        break;
      }
      NodeList &labels = mexp->exp();
      NodeList::iterator it = labels.begin();
      for( ; it != labels.end(); ++it )
      {
        stmt->append_label( *it );
        (*it)->set_father( stmt );
      }
      break;
    }

    case veEXP_MEMBER : case veEXP_ARRAY  : case veEXP_PRI : case veEXP_UNA : case veEXP_BIN :
    case veEXP_CALLER : case veEXP_MCONCAT : case veEXP_QUES :
    case veEXP_SIGN   : case veEXP_UNSIGN : case veEXP_MINTY :
      stmt->append_label( label );
      label->set_father( stmt );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_gen_case_item( VeriNode *label, VeriNode *item )
{
  VeriGenCaseItem * stmt = new VeriGenCaseItem( _node_pool.next_id( ),
                                                 label->line(),
                                                 label->col(), item, _mod );
  _node_pool.insert( stmt );

  switch( label->detail_type() )
  {
    case veEXP_MULTI :
    {
      VeriMultiExp *mexp = static_cast<VeriMultiExp *>(label);
      // A concatenation is one case expression. Only a comma expression
      // denotes multiple alternative labels for the same branch.
      if( mexp->multi_type() != vemCOMMA_EXP && mexp->multi_type() != vemINSIDE_SET )
      {
        stmt->append_label( label );
        label->set_father( stmt );
        break;
      }
      NodeList &labels = mexp->exp();
      NodeList::iterator it = labels.begin();
      for( ; it != labels.end(); ++it )
      {
        stmt->append_label( *it );
        (*it)->set_father( stmt );
      }
      break;
    }

    case veEXP_MEMBER : case veEXP_ARRAY  : case veEXP_PRI : case veEXP_UNA : case veEXP_BIN :
    case veEXP_CALLER : case veEXP_MCONCAT : case veEXP_QUES :
    case veEXP_SIGN   : case veEXP_UNSIGN : case veEXP_MINTY :
      stmt->append_label( label );
      label->set_father( stmt );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_func_case_item_list( VeriNode *item )
{
  VeriFuncCaseItemList * stmt
    = new VeriFuncCaseItemList( _node_pool.next_id( ), item->line(),
                                item->col(), _mod );
  _node_pool.insert( stmt );

  switch( item->detail_type() )
  {
    case vsSTMT_FUNC_DEFAULT_CASE_ITEM:
      stmt->set_default( item );
      break;

    case vsSTMT_FUNC_CASE_ITEM:
      stmt->append_item( item );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_case_item_list( VeriNode *item )
{
  VeriCaseItemList * stmt
    = new VeriCaseItemList( _node_pool.next_id( ), item->line(),
                             item->col(), _mod);
  _node_pool.insert( stmt );

  switch( item->detail_type() )
  {
    case vsSTMT_DEFAULT_CASE_ITEM:
      stmt->set_default( item );
      break;

    case vsSTMT_CASE_ITEM:
      stmt->append_item( item );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_gen_case_item_list( VeriNode *item )
{
  VeriGenCaseItemList * stmt
    = new VeriGenCaseItemList( _node_pool.next_id( ), item->line(),
                                item->col(), _mod);
  _node_pool.insert( stmt );

  switch( item->detail_type() )
  {
    case vsINST_GEN_DEFAULT_CASE_ITEM:
      stmt->set_default( item );
      break;

    case vsINST_GEN_CASE_ITEM:
      stmt->append_item( item );
      break;

    default:
      break;
  }

  int re = stmt->check_child_validation();
  if( re == OK )
    item ->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::append_func_case_item_list( VeriNode *list, VeriNode *item )
{
  if( list->detail_type() == vsSTMT_FUNC_CASE_ITEM_LIST )
  {
    VeriFuncCaseItemList *item_list
      = static_cast<VeriFuncCaseItemList *>(list);

    if( item->detail_type( ) == vsSTMT_FUNC_CASE_ITEM )
      item_list->append_item( item );
    else if( item->detail_type( ) == vsSTMT_FUNC_DEFAULT_CASE_ITEM )
      item_list->set_default( item );

    item_list->check_last_child_validation( );
    int re = item_list->check_last_child_validation( );
    if( re == OK )
      item->set_father( list );
    return list;
  }
  
  return list;
}

VeriNode *
VeriParser::append_case_item_list( VeriNode *list, VeriNode *item )
{
  if( list->detail_type() == vsSTMT_CASE_ITEM_LIST )
  {
    VeriCaseItemList *item_list
      = static_cast<VeriCaseItemList *>(list);

    if( item->detail_type( ) == vsSTMT_CASE_ITEM )
      item_list->append_item( item );
    else if( item->detail_type( ) == vsSTMT_DEFAULT_CASE_ITEM )
      item_list->set_default( item );

    item_list->check_last_child_validation( );
    int re = item_list->check_last_child_validation( );
    if( re == OK )
      item->set_father( list );
    return list;
  }
 
  return list;
}

VeriNode *
VeriParser::append_gen_case_item_list( VeriNode *list, VeriNode *item )
{
  if( list->detail_type() == vsINST_GEN_CASE_ITEM_LIST )
  {
    VeriGenCaseItemList *item_list
      = static_cast<VeriGenCaseItemList *>(list);

    if( item->detail_type( ) == vsINST_GEN_CASE_ITEM )
      item_list->append_item( item );
    else if( item->detail_type( ) == vsINST_GEN_DEFAULT_CASE_ITEM )
      item_list->set_default( item );

    item_list->check_last_child_validation( );
    int re = item_list->check_last_child_validation( );
    if( re == OK )
      item->set_father( list );
    return list;
  }
  
  return list;
}

VeriNode *
VeriParser::gen_func_case_stmt( int line, int col, int case_type,
                                VeriNode *switch_value, VeriNode *item )
{
  VeriStmt * stmt
    = new VeriFuncCaseStmt( _node_pool.next_id( ), line, col, case_type,
                            switch_value, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    switch_value->set_father( stmt );
    item->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_case_stmt( int line, int col, int case_type,
                           VeriNode *switch_value, VeriNode *item )
{
  VeriStmt * stmt = new VeriCaseStmt( _node_pool.next_id( ),
                                       line, col, case_type,
                                       switch_value, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    switch_value->set_father( stmt );
    item->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_gen_case_stmt( int line, int col,
                               VeriNode *switch_value, VeriNode *item )
{
  VeriInst * stmt = new VeriGenCase( _node_pool.next_id( ), line, col,
                                     switch_value, item, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    switch_value->set_father( stmt );
    item->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_func_cond_stmt( int line, int col, VeriNode *if_exp,
                                VeriNode *if_stmt, VeriNode *else_stmt )
{
  VeriStmt * stmt
    = new VeriFuncCondStmt( _node_pool.next_id( ), line, col, if_exp,
                             if_stmt, else_stmt, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if_exp->set_father( stmt );
    if_stmt->set_father( stmt );
    if( else_stmt != NULL )
      else_stmt->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_cond_stmt( int line, int col, VeriNode *if_exp,
                           VeriNode *if_stmt, VeriNode *else_stmt, bool ordered )
{
  VeriStmt * stmt = new VeriCondStmt( _node_pool.next_id( ),
                                       line, col, if_exp,
                                       if_stmt, else_stmt, _mod );
  if(ordered)static_cast<VeriCondStmt*>(stmt)->set_wait_order();
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if_exp->set_father( stmt );
    if_stmt->set_father( stmt );
    if( else_stmt != NULL )
      else_stmt->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_gen_cond_stmt( int line, int col, VeriNode *if_exp,
                               VeriNode *if_stmt, VeriNode *else_stmt )
{
  VeriInst * stmt = new VeriGenCond( _node_pool.next_id( ),
                                      line, col, if_exp,
                                      if_stmt, else_stmt, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if_exp->set_father( stmt );
    if_stmt->set_father( stmt );
    if( else_stmt != NULL )
      else_stmt->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_proc_timing_control_stmt( VeriNode *event_control,
                                          VeriNode *statement, bool level_sensitive )
{
  VeriStmt * stmt = new VeriProcTimeContStmt( _node_pool.next_id( ),
                                              event_control->line(),
                                              event_control->col(),
                                              event_control,
                                              statement, _mod, level_sensitive );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    event_control->set_father( stmt );
    statement->set_father( stmt );
  }
  return stmt;
}

VeriNode *
VeriParser::gen_disable_stmt( const char *label, int line, int col )
{
  VeriStmt * stmt = new VeriDisableStmt( _node_pool.next_id( ),
                                          line, col, label, _mod );
  _node_pool.insert( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_event_stmt( int line, int col, int is_all, VeriNode *event_list)
{
  int re = OK;
  VeriEventStmt * stmt = new VeriEventStmt( _node_pool.next_id( ),
                                             line, col, is_all, _mod );
  _node_pool.insert( stmt );

  if( event_list != NULL )
  {
    if( event_list->tok_type() == vtEXP )
    {
      switch( event_list->detail_type() )
      {
        case veEXP_PRI:
        case veEXP_MEMBER:
        case veEXP_EVENT:
          stmt->append_event( event_list );
          event_list->set_father( stmt );
          break;

        case veEXP_MULTI:
        {
          VeriMultiExp *mexp = static_cast<VeriMultiExp * >(event_list);
          if(mexp->multi_type()==vemCONCAT_EXP||mexp->multi_type()==vemASSIGN_PATTERN) {
            stmt->append_event(event_list);event_list->set_father(stmt);break;
          }
          re = mexp->check_pure_event_multi();
          if( re == OK )
          {
            NodeList &list = mexp->exp();
            NodeList::iterator it = list.begin();
            for( ; it != list.end(); ++it )
            {
              stmt->append_event( *it );
              (*it)->set_father( stmt );
            }
          }
          break;
        }

        default:
          stmt->append_event(event_list);event_list->set_father(stmt);break;
      }
    }
    else
      return NULL;
  }

  return stmt;
}

VeriNode *
VeriParser::gen_func_blocking_assign_stmt( VeriNode *assign_exp )
{
  assert( assign_exp->detail_type() == veEXP_ASSIGN );

  VeriAssignExp * aexp = static_cast<VeriAssignExp *>(assign_exp);

  VeriStmt * stmt = new VeriFuncBlockAssignStmt( _node_pool.next_id( ),
                                                 assign_exp->line(),
                                                 assign_exp->col(),
                                                 aexp->lval(),
                                                 aexp->rval(), _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation( );
  if( re == OK )
    assign_exp->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_sys_caller_stmt( int line, int col, const char * name,
                            VeriNode *call_exp )
{
  const std::string file_name(name);
  if(file_name=="$cast")return gen_block_or_non_or_caller_stmt(gen_caller(gen_primary(name,line,col,veVAR),call_exp));
  if(file_name=="$sscanf"||file_name=="$fscanf"||file_name=="$fopen"||file_name=="$fgetc"||file_name=="$ungetc"||file_name=="$feof"||file_name=="$fgets"||file_name=="$ftell"||file_name=="$fseek"||file_name=="$rewind")
    return gen_block_or_non_or_caller_stmt(gen_caller(gen_primary(name,line,col,veVAR),call_exp));
  if(std::string(name)=="$sformatf"||std::string(name)=="$test$plusargs"||std::string(name)=="$value$plusargs")
    return gen_block_or_non_or_caller_stmt(gen_caller(gen_primary(name,line,col,veVAR),call_exp));
  int re = OK;
  VeriMultiExp * arg = NULL;
  if( call_exp != NULL )
  {
    switch( call_exp->detail_type() )
    {
      case veEXP_MEMBER :
      case veEXP_PRI :
      case veEXP_UNA :
      case veEXP_ARRAY :
      case veEXP_SIGN :
      case veEXP_UNSIGN :
      case veEXP_BIN :
      case veEXP_MCONCAT :
        arg = new VeriMultiExp( _node_pool.next_id( ),
                                 vemCOMMA_EXP, call_exp->line(),
                                 call_exp->col(), _mod );
        _node_pool.insert( arg );
        arg->append_child( call_exp );
        call_exp->set_father( arg );
        break;

      case veEXP_CALLER :
      {
        VeriCallerExp * caller = static_cast<VeriCallerExp *>(call_exp);
        if( caller->call_type() == vtTASK_CALL )
        {
          arg = new VeriMultiExp( _node_pool.next_id( ),
                                   vemCOMMA_EXP, call_exp->line(),
                                   call_exp->col(), _mod );
          _node_pool.insert( arg );
          arg->append_child( call_exp );
          call_exp->set_father( arg );
        }
        break;
      }

      case veEXP_MULTI :
      {
        VeriMultiExp * mexp = static_cast<VeriMultiExp *>(call_exp);
        // Empty positional arguments are valid in $sdf_annotate. The common
        // expression builder marks such a list as a port list; preserve it as
        // a system-task argument list instead of silently dropping all args.
        if(file_name=="$sdf_annotate"&&mexp->multi_type()==vemPORT_INST_EXP)
          mexp->set_multi_type(vemCOMMA_EXP);
        if(    mexp->multi_type() == vemCOMMA_EXP
            || mexp->multi_type() == vemCONCAT_EXP )
          arg = mexp;
        break;
      }

      default:
        break;
    }
  }

  VeriStmt * stmt
    = new VeriSysCallerStmt( _node_pool.next_id( ), line, col, name, arg, _mod );
  _node_pool.insert( stmt );
  re = stmt->check_child_validation();
  if( re == OK && arg != NULL )
    arg->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::gen_dummy_stmt( int line, int col )
{
  VeriStmt * stmt
    = new VeriDummyStmt( _node_pool.next_id( ), line, col, _mod );
  _node_pool.insert( stmt );
  return stmt;
}

VeriNode* VeriParser::gen_foreach(int line,int col,VeriNode* array,VeriNode* indices,VeriNode* body) {
  NodeList items;
  if(indices->detail_type()==veEXP_MULTI)items=static_cast<VeriMultiExp*>(indices)->exp();else items.push_back(indices);
  std::vector<std::string> names;std::set<std::string> used;VeriNode* declarations=NULL;
  for(auto* item:items) {
    if(item->detail_type()!=veEXP_PRI || static_cast<VeriPrimaryExp*>(item)->pri_type()!=veVAR)
      throw std::runtime_error("line "+std::to_string(line)+": foreach iterator must be an identifier or omitted");
    auto* p=static_cast<VeriPrimaryExp*>(item);std::string name=p->str();
    if(!name.empty()) {
      if((array->detail_type()==veEXP_PRI&&name==static_cast<VeriPrimaryExp*>(array)->str())||!used.insert(name).second)throw std::runtime_error("line "+std::to_string(line)+": foreach indices must be distinct from each other and the array");
      auto* decl=gen_var_decl(line,col,vpNO_IO,vvINT2,IS_TRUE,vpSCALAR,NULL,NULL,NULL,gen_primary(name.c_str(),line,col,veVAR));
      declarations=declarations?append_block_item_list(declarations,decl):gen_block_item_list(decl);
    }
    names.push_back(name);
  }
  if(used.empty())throw std::runtime_error("line "+std::to_string(line)+": foreach requires at least one index");
  auto* loop=static_cast<VeriLoopStmt*>(gen_loop_stmt(line,col,array,NULL,NULL,body,VeriLoopStmt::FOREACH));
  loop->set_foreach_indices(names);
  auto* block=static_cast<VeriSeqBlock*>(gen_seq_block_stmt(line,col,NULL,-1,-1,declarations,gen_stmt_list(loop)));
  return block;
}

VeriNode* VeriParser::gen_loop_jump(int line,int col,bool continuing) {
  auto* node=new VeriDummyStmt(_node_pool.next_id(),line,col,_mod,continuing?vsSTMT_CONTINUE:vsSTMT_BREAK);
  _node_pool.insert(node);return node;
}
VeriNode* VeriParser::gen_action_stmt(int line,int col,int kind,VeriNode* target,VeriNode* value,int op) {
  auto* node=new VeriActionStmt(_node_pool.next_id(),line,col,kind,target,value,op,_mod);
  _node_pool.insert(node);node->check_child_validation();
  if(target)target->set_father(node);if(value)value->set_father(node);return node;
}
VeriNode* VeriParser::gen_update_stmt(int line,int col,VeriNode* target,int delta) {
  auto* node=new VeriUpdateStmt(_node_pool.next_id(),line,col,target,delta,_mod);
  _node_pool.insert(node);node->check_child_validation();target->set_father(node);return node;
}
VeriNode* VeriParser::gen_inline_for(int line,int col,VeriNode* init,VeriNode* judge,VeriNode* iter,VeriNode* body,int type,int is_signed,const char* type_name,VeriNode* type_expression) {
  // Fresh declaration nodes prevent a shared AST child between the declaration
  // and its per-entry initialization. Symbol binding happens in the new block.
  NodeList declarators;
  if(init->detail_type()==veEXP_MULTI)declarators=static_cast<VeriMultiExp*>(init)->exp();
  else declarators.push_back(init);
  VeriNode* decls=NULL;VeriNode* steps=NULL;VeriNode* named_variables=NULL;
  for(auto* declaration:declarators) {
    auto* lhs=declaration->detail_type()==veEXP_ASSIGN?static_cast<VeriAssignExp*>(declaration)->lval():declaration;
    if(lhs->detail_type()!=veEXP_PRI) {
      veri_err->append_err(ERR_ERROR,line,col,vCHILD_TYPE_LOOP_STMT);return gen_dummy_stmt(line,col);
    }
    auto* pri=static_cast<VeriPrimaryExp*>(lhs);
    auto* fresh=gen_primary(pri->str().c_str(),pri->line(),pri->col(),veVAR);
    if(type_name) {
      if(declaration->detail_type()!=veEXP_ASSIGN)
        throw std::runtime_error("for variable declaration requires an initializer");
      named_variables=named_variables?gen_multi(named_variables,fresh,vemCOMMA_EXP,line,col):fresh;
    } else {
      auto* decl=type?gen_var_decl(line,col,vpNO_IO,type,is_signed,vpSCALAR,NULL,NULL,NULL,fresh):gen_int_decl(line,col,fresh);
      // IEEE 1800 12.7.1: loop-declared variables are automatic even in a
      // static task or a module initial block.
      static_cast<VeriDecl*>(decl)->set_explicit_automatic();
      decls=decls?append_block_item_list(decls,decl):gen_block_item_list(decl);
    }
    VeriNode* assignment=declaration;
    if(declaration->detail_type()!=veEXP_ASSIGN)
      assignment=gen_binary(lhs,vtASSIGN,line,col,gen_primary("32'b0",line,col,veNUM));
    auto* step=gen_block_or_non_or_caller_stmt(assignment);
    steps=steps?append_stmt_list(steps,step):gen_stmt_list(step);
  }
  if(type_name) {
    auto* decl=static_cast<VeriVarDecl*>(gen_named_var_decl(line,col,type_name,named_variables));
    decl->set_type_expression(type_expression);
    decl->set_explicit_automatic();
    decls=gen_block_item_list(decl);
  }
  auto* loop=gen_loop_stmt(line,col,steps,judge,iter,body);
  return gen_seq_block_stmt(line,col,NULL,-1,-1,decls,gen_stmt_list(loop));
}

VeriNode *
VeriParser::gen_dummy_inst( int line, int col )
{
  VeriInst * inst
    = new VeriDummyInst( _node_pool.next_id( ), line, col, _mod );
  _node_pool.insert( inst );
  return inst;
}

VeriNode *
VeriParser::gen_gen_block_stmt( int line, int col, const char *name,
                                int label_line, int label_col,
                                VeriNode *item_list )
{
  VeriPrimaryExp *pexp = NULL;

  String iname = "";
  if( name != NULL )
    iname = name;

  VeriGenBlock * stmt = new VeriGenBlock( _node_pool.next_id( ), line, col,
                                          iname, label_line, label_col,
                                          item_list, _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if(item_list) item_list->set_father( stmt );
    if( pexp != NULL )
      pexp->set_father( stmt );
  }

  return stmt;
}

VeriNode* VeriParser::gen_class(int line,int col,const char* name,VeriNode* items,const char* closing) {
  if(items)for(auto* item:static_cast<VeriModuleItemList*>(items)->item_list())
    if(item->detail_type()==vsDECL_TIME)throw std::runtime_error("time declarations are not allowed in a class");
  if(closing&&std::string(name)!=closing)throw std::runtime_error("class closing label does not match: "+std::string(name));
  auto* node=new VeriSeqBlock(_node_pool.next_id(),line,col,name,line,col,items,nullptr,_mod);
  node->set_class_declaration();_node_pool.insert(node);
  if(items)items->set_father(node);
  end_class();return node;
}

VeriNode *
VeriParser::gen_seq_block_stmt( int line, int col, const char *name,
                                int label_line, int label_col,
                                VeriNode *decl_list, VeriNode *stmt_list )
{
  String iname = "";
  if( name != NULL )
    iname = name;

  VeriStmt * stmt = new VeriSeqBlock( _node_pool.next_id( ), line, col, iname,
                                       label_line, label_col,
                                      decl_list, stmt_list, _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if( decl_list != NULL ) decl_list->set_father( stmt );
    if( stmt_list != NULL ) stmt_list->set_father( stmt );
  }

  return stmt;
}

VeriNode *
VeriParser::gen_func_seq_block_stmt( int line, int col, const char *name,
                                     int label_line, int label_col,
                                     VeriNode *decl_list, VeriNode *stmt_list )
{
  String iname = "";
  if( name != NULL )
    iname = name;

  VeriStmt * stmt = new VeriFuncSeqBlock( _node_pool.next_id( ), line, col,
                                           iname, label_line, label_col,
                                           decl_list, stmt_list, _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation();
  if( re == OK )
  {
    if( decl_list != NULL ) decl_list->set_father( stmt );
    if( stmt_list != NULL ) stmt_list->set_father( stmt );
  }

  return stmt;
}

VeriNode *
VeriParser::gen_stmt_list( VeriNode *item )
{
  VeriStmtList * stmt = new VeriStmtList( _node_pool.next_id( ),
                                          item->line(), item->col(), _mod );
  _node_pool.insert( stmt );
  stmt->append_stmt( item );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::append_stmt_list( VeriNode *list, VeriNode *stmt )
{
  switch( list->detail_type() )
  {
    case vsSTMT_STMT_LIST :
    {
      VeriStmtList *item_list = static_cast<VeriStmtList *>(list);
      item_list->append_stmt( stmt );
      int re = item_list->check_last_child_validation( );
      if( re == OK )
        stmt->set_father( list );
      break;
    }

    case vsSTMT_DUMMY :
      break;

    default:
      break;
  }
  return list;
}

VeriNode *
VeriParser::gen_mod_item_list( VeriNode *item )
{
  VeriModuleItemList * stmt = new VeriModuleItemList( _node_pool.next_id( ),
                                                      item->line(),
                                                      item->col(), _mod );
  _node_pool.insert( stmt );
  stmt->append_item( item );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::append_mod_item_list( VeriNode *list, VeriNode *item )
{
  if( list->detail_type() == vsSTMT_MOD_ITEM_LIST )
  {
    VeriModuleItemList *item_list
      = static_cast<VeriModuleItemList *>(list);
    item_list->append_item( item );
    int re = item_list->check_last_child_validation( );
    if( re == OK )
      item->set_father( list );
  }

  return list;
}

VeriNode *
VeriParser::gen_func_stmt_list( VeriNode *item )
{
  VeriFuncStmtList * stmt
    = new VeriFuncStmtList( _node_pool.next_id( ),
                             item->line(), item->col() , _mod);
  _node_pool.insert( stmt );
  stmt->append_stmt( item );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::append_func_stmt_list( VeriNode *list, VeriNode *item )
{
  switch( list->detail_type() )
  {
    case vsSTMT_FUNC_STMT_LIST :
    {
      VeriFuncStmtList *item_list
        = static_cast<VeriFuncStmtList *>(list);
      item_list->append_stmt( item );
      int re = item_list->check_last_child_validation( );
      if( re == OK )
        item->set_father( list );

      break;
    }

    case vsSTMT_DUMMY :
      break;

    default:
      break;
  }
  return list;
}

VeriNode *
VeriParser::gen_gen_item_list( VeriNode *item )
{
  VeriGenItemList * stmt
    = new VeriGenItemList( _node_pool.next_id( ), item->line(),
                            item->col(), _mod );
  _node_pool.insert( stmt );
  stmt->append_item( item );

  int re = stmt->check_child_validation();
  if( re == OK )
    item->set_father( stmt );

  return stmt;
}

VeriNode *
VeriParser::append_gen_item_list( VeriNode *list, VeriNode *item )
{
  switch( list->detail_type() )
  {
    case vsINST_GEN_ITEM_LIST :
    {
      VeriGenItemList *item_list
        = static_cast<VeriGenItemList *>(list);
      item_list->append_item( item );
      int re = item_list->check_last_child_validation( );
      if( re == OK )
        item->set_father( list );
      break;
    }

    case vsINST_DUMMY :
      break;

    default:
      break;
  }
  return list;
}

VeriNode *
VeriParser::gen_block_or_non_or_caller_stmt( VeriNode *node )
{
  if( node == NULL || node->tok_type() != vtEXP )
    return node;

  int re;
  VeriStmt * stmt = NULL;
  switch( node->detail_type() )
  {
    case veEXP_PRI:
      if(static_cast<VeriPrimaryExp*>(node)->pri_type()==veVAR)
        return gen_block_or_non_or_caller_stmt(gen_caller(node,NULL));
      throw std::runtime_error("line "+std::to_string(node->line())+": expression statement requires a call, assignment or update");
    case veEXP_UNA : {
      auto* update=static_cast<VeriUnaryExp*>(node);int op=update->op();
      if(op==vtUPREINC||op==vtUPREDEC||op==vtUPOSTINC||op==vtUPOSTDEC)
        return gen_update_stmt(node->line(),node->col(),update->exp_child(),op==vtUPREINC||op==vtUPOSTINC?1:-1);
      if(op==vtSYS_CAST||veri_is_random(op)||veri_is_testbench_function(op)) {
        auto* call=new VeriCallerStmt(_node_pool.next_id(),node->line(),node->col(),node,_mod);
        _node_pool.insert(call);node->set_father(call);return call;
      }
      return node;
    }
    case veEXP_MEMBER :
    case veEXP_CALLER :
      stmt = new VeriCallerStmt( _node_pool.next_id( ), node->line(),
                                 node->col(), node, _mod );
      _node_pool.insert( stmt );
      re = stmt->check_child_validation( );
      if( re == OK )
        node->set_father( stmt );
     break;

    case veEXP_ASSIGN :
    {
      VeriAssignExp * assign = static_cast< VeriAssignExp *>(node);
      stmt = new VeriBlockStmt( _node_pool.next_id( ),
                                 node->line(), node->col(),
                                 assign->lval(), NULL, assign->rval(), _mod );
      _node_pool.insert( stmt );
      re = stmt->check_child_validation( );
      if( re == OK )
      {
        assign->lval()->set_father( stmt );
        assign->rval()->set_father( stmt );
      }
     break;
    }

    case veEXP_BIN :
    {
      VeriBinaryExp * bexp = static_cast< VeriBinaryExp *>(node);
      if( bexp->op() == vtBLE )
      {
        // Direct nonblocking assignment: lval <= rval
        stmt = new VeriNonBlockStmt( _node_pool.next_id( ),
                                      node->line(), node->col(),
                                      bexp->lval(), NULL, bexp->rval(), _mod );
        _node_pool.insert( stmt );
        re = stmt->check_child_validation( );
        if( re == OK )
        {
          bexp->lval()->set_father( stmt );
          bexp->rval()->set_father( stmt );
        }
      }
      else
      {
        // Walk the left chain of binary expressions to find innermost vtBLE.
        // Pattern: ((lval <= a) OP1 b) OP2 c  →  lval <= ((a OP1 b) OP2 c)
        // Handles: c <= a == b, c <= a && b && c, c <= a | b, etc.
        // Collect the chain: each element is (op, right_child)
        struct OpRHS { int op; VeriNode *rhs; int line; int col; };
        std::vector<OpRHS> chain;
        VeriNode * cur = bexp;
        VeriBinaryExp * ble_node = NULL;
        while( cur && cur->tok_type() == vtEXP && cur->detail_type() == veEXP_BIN )
        {
          VeriBinaryExp * be = static_cast< VeriBinaryExp *>(cur);
          if( be->op() == vtBLE )
          {
            ble_node = be;
            break;
          }
          chain.push_back({ be->op(), be->rval(), be->line(), be->col() });
          cur = be->lval();
        }
        if( ble_node )
        {
          // Rebuild RHS bottom-up: start with ble_node->rval(), then
          // apply each (op, rhs) from the chain.
          VeriNode * new_rhs = ble_node->rval();
          for( int i = (int)chain.size() - 1; i >= 0; --i )
          {
            auto * new_bin = new VeriBinaryExp(
              _node_pool.next_id(), chain[i].line, chain[i].col,
              new_rhs, chain[i].op, chain[i].rhs, _mod );
            _node_pool.insert( new_bin );
            new_rhs = new_bin;
          }
          stmt = new VeriNonBlockStmt( _node_pool.next_id( ),
                                        node->line(), node->col(),
                                        ble_node->lval(), NULL, new_rhs, _mod );
          _node_pool.insert( stmt );
          re = stmt->check_child_validation( );
          if( re == OK )
          {
            ble_node->lval()->set_father( stmt );
            new_rhs->set_father( stmt );
          }
        }
        else
        {
          return node;
        }
      }
      break;
    }

    case veEXP_QUES :
    {
      // Ternary conditional: cond ? t : f
      // If cond is vtBLE, restructure as nonblocking: lval <= (cmp ? t : f)
      VeriQuesExp * qexp = static_cast< VeriQuesExp *>(node);
      VeriNode * q = qexp->ques();
      if( q && q->tok_type() == vtEXP && q->detail_type() == veEXP_BIN )
      {
        VeriBinaryExp * ble = static_cast< VeriBinaryExp *>(q);
        if( ble->op() == vtBLE )
        {
          VeriNode * new_rhs = new VeriQuesExp(
            _node_pool.next_id(), node->line(), node->col(),
            ble->rval(), qexp->choice1(), qexp->choice2(), _mod );
          _node_pool.insert( new_rhs );
          stmt = new VeriNonBlockStmt( _node_pool.next_id( ),
                                        node->line(), node->col(),
                                        ble->lval(), NULL, new_rhs, _mod );
          _node_pool.insert( stmt );
          re = stmt->check_child_validation( );
          if( re == OK )
          {
            ble->lval()->set_father( stmt );
            new_rhs->set_father( stmt );
          }
        }
      }
      if( !stmt )
        return node;
      break;
    }

    default:
      break;
  }
  if(!stmt)throw std::runtime_error("line "+std::to_string(node->line())+": unsupported expression statement");
  return stmt;
}

VeriNode *
VeriParser::gen_blocking_stmt( VeriNode *lval,
                               VeriNode *event, VeriNode *rval )
{
  VeriStmt * stmt = new VeriBlockStmt( _node_pool.next_id( ),
                                        lval->line(), lval->col(),
                                        lval, event, rval, _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation( );
  if( re == OK )
  {
    lval->set_father( stmt );
    rval->set_father( stmt );
    if( event != NULL )
      event->set_father( stmt );
  }

  return stmt;
}

VeriNode *
VeriParser::gen_non_blocking_stmt( VeriNode *lval, VeriNode *event,
                                   VeriNode *rval )
{
  if( !lval || !rval ) {
    return new VeriDummyStmt( _node_pool.next_id( ), 0, 0, _mod );
  }
  VeriStmt * stmt = new VeriNonBlockStmt( _node_pool.next_id( ),
                                           lval->line(), lval->col(),
                                           lval, event, rval, _mod );
  _node_pool.insert( stmt );
  int re = stmt->check_child_validation( );
  if( re == OK )
  {
    lval->set_father( stmt );
    rval->set_father( stmt );
    if( event != NULL )
      event->set_father( stmt );
  }

  return stmt;
}

VeriNode *
VeriParser::gen_continuous_assign_stmt( int line, int col,
                        VeriNode *delay, VeriNode *drive, VeriNode *exp )
{
  VeriDelayExp  * idelay = NULL;
  VeriDriveExp  * idrive = NULL;
  VeriStmt * stmt   = NULL;
  
  if( delay == NULL )
  {
    idelay = new VeriDelayExp( _node_pool.next_id( ),
                               _node_pool.next_id( ),
                               line, col, _mod );
    _node_pool.insert( idelay->delay1() );
    _node_pool.insert( idelay );
  }
  else
    idelay = static_cast<VeriDelayExp *>(delay);

  if( drive == NULL )
  {
    idrive = new VeriDriveExp( _node_pool.next_id( ), line, col, _mod );
    _node_pool.insert( idrive );
  }
  else
    idrive = static_cast<VeriDriveExp *>(drive);

  VeriMultiExp *mexp = NULL;
  if( exp->detail_type() != veEXP_MULTI )
  {
    mexp = new VeriMultiExp( _node_pool.next_id( ), vemCOMMA_EXP,
                             exp->line(), exp->col(), _mod );
    _node_pool.insert( mexp );
    mexp->append_child( exp );
    exp->set_father( mexp );
  }
  else
    mexp = static_cast<VeriMultiExp *>(exp);

  stmt = new VeriContAssignStmt( _node_pool.next_id( ), line, col,
                                  idelay, idrive, mexp, _mod );
  _node_pool.insert( stmt );

  int re = stmt->check_child_validation();
  if( re == OK )
  {
    idelay->set_father( stmt );
    idrive->set_father( stmt );
    mexp->set_father( stmt );
  }

  return stmt;
}

void VeriParser::begin_bind(const char* target) {
  if(_binding_saved_mod)throw std::runtime_error("nested bind directives are not supported");
  _binding_saved_mod=_mod;_binding_saved_instances=std::move(_mod_instantiations);
  _mod_instantiations.clear();_mod=new VeriMod(_node_pool.next_id());
  _mod->set_name(target);_mod->set_fname(_fname,_fline);
  _bindings.push_back({target,nullptr,_mod});
}
void VeriParser::end_bind(VeriNode* instance) {
  if(!instance||instance->detail_type()!=vsINST_MOD_INSTANTIATION)
    throw std::runtime_error("bind requires a module instantiation");
  _bindings.back().instance=instance;_mod=_binding_saved_mod;_binding_saved_mod=nullptr;
  _mod_instantiations=std::move(_binding_saved_instances);
}
void VeriParser::resolve_bindings() {
  for(auto& binding:_bindings) {
    auto* target=module(binding.target);
    if(!target||target->is_interface()||target->is_package())
      throw std::runtime_error("bind target must name a declared module type: "+binding.target);
    if(!binding.instance)throw std::runtime_error("incomplete bind directive");
    // Bind actuals are resolved in the target's lexical/hierarchical scope,
    // including declarations appearing after the file-scope directive.
    VeriNode::NodeQueue nodes;VeriNode::IQueue depths;std::set<VeriNode*> seen;
    nodes.push(binding.instance);depths.push(0);
    while(!nodes.empty()) {
      auto* node=nodes.front();
      if(node&&seen.insert(node).second){node->set_birth_mod(target);node->push_dot_children(nodes,depths);}
      nodes.pop();depths.pop();
    }
    _mod=target;
    if(target->item())append_mod_item_list(target->item(),binding.instance);
    else target->set_item(gen_mod_item_list(binding.instance));
    target->item()->set_father(target);target->add_bound_instance(binding.instance);
    _mods->add_mod_conn(target,NodeList{binding.instance});_mod=nullptr;
  }
}

VeriNode *
VeriParser::gen_init_stmt( int line, int col, VeriNode *stmt )
{
  VeriStmt * init = new VeriInitStmt( _node_pool.next_id( ),
                                       line, col, stmt, _mod );
  _node_pool.insert( init );
  int re = init->check_child_validation( );
  if( re == OK )
    stmt->set_father( init );
  return init;
}

VeriNode *
VeriParser::gen_always_stmt( int line, int col, VeriNode *stmt,
                                 int always_kind )
{
  VeriStmt * always = new VeriAlwaysStmt( _node_pool.next_id( ),
                                           line, col, stmt, _mod,
                                           always_kind );
  _node_pool.insert( always );
  int re = always->check_child_validation( );
  if( re == OK )
    stmt->set_father( always );

  return always;
}

VeriModInstance *
VeriParser::gen_mod_instance( VeriNode *mod_inst )
{
  if( mod_inst == NULL || mod_inst->detail_type() != veEXP_CALLER )
    return NULL;
  
  VeriCallerExp * call_exp = static_cast<VeriCallerExp *>(mod_inst);
  VeriModInstance * stmt
    = new VeriModInstance( _node_pool.next_id( ),
                            mod_inst->line(), mod_inst->col(),
                            call_exp->caller(), call_exp->arg(), _mod );
  _node_pool.insert( stmt );
  call_exp->caller()->set_father( stmt );
  if( call_exp->arg() != NULL )
    call_exp->arg()->set_father( stmt );
  return stmt;
}

VeriNode *
VeriParser::gen_mod_instantiation( int line, int col, const char * mod_name,
                                   VeriNode *param, VeriNode *list )
{
  if( list == NULL || list->tok_type() != vtEXP )
    return NULL;

  // A named variable declaration and an unparameterized module instance
  // share their identifier prefix. Their declarators have distinct AST kinds.
  {
    VeriNode* first=list;
    if(first->detail_type()==veEXP_MULTI) {
      auto& entries=static_cast<VeriMultiExp*>(first)->exp();
      if(!entries.empty())first=entries.front();
    }
    if(first->detail_type()==veEXP_PRI||first->detail_type()==veEXP_ARRAY||first->detail_type()==veEXP_ASSIGN) {
      auto* declaration=static_cast<VeriVarDecl*>(gen_named_var_decl(line,col,mod_name,list));
      if(param)declaration->set_type_expression(gen_type_expression(line,col,mod_name,-1,0,nullptr,param));
      return declaration;
    }
  }
  String name = "";
  if( mod_name != NULL )
    name = mod_name;

  if( param != NULL && param->detail_type() != veEXP_MULTI )
  {
    VeriMultiExp *mexp = new VeriMultiExp( _node_pool.next_id( ), vemCOMMA_EXP,
                                           param->line(), param->col(), _mod );
    _node_pool.insert( mexp );
    mexp->append_child( param );
    param->set_father( mexp );
    param = mexp;
  }

  VeriModInstantiation * mod
    = new VeriModInstantiation( _node_pool.next_id( ), line, col,
                                 name, param, _mod );
  _node_pool.insert( mod );
  int re = mod->check_child_validation( );
  if( re == OK )
  {
    if( param != NULL )
      param->set_father( mod );
  }

  _mod_instantiations.push_back( mod );

  VeriModInstance * mod_inst = NULL;
  switch( list->detail_type() )
  {
    case veEXP_CALLER :
      mod_inst = gen_mod_instance( list );
      if( mod_inst != NULL )
      {
        mod->append_mod_inst( mod_inst );
        mod_inst->set_father( mod );
      }
      break;

    case veEXP_MULTI :
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      switch( mexp->multi_type() )
      {
        case vemCOMMA_EXP :
        case vemPORT_EXP :
        case vemPORT_INST_EXP :
        {
          NodeList &caller_list = mexp->exp();
          NodeList::iterator it = caller_list.begin();
          for( ; it != caller_list.end(); ++it )
          {
            mod_inst = gen_mod_instance( *it );
            if( mod_inst != NULL )
            {
              mod->append_mod_inst( mod_inst );
              mod_inst->set_father( mod );
            }
          }
          break;
        }

        default:
          return NULL;
      }
      break;
    }

    default:
      break;
  }
  return mod;
}

VeriGateInstance *
VeriParser::gen_gate_instance( VeriNode *gate_inst, bool unnamed )
{
  if( gate_inst == NULL )
    return NULL;

  if( unnamed )
  {
    // Parentheses identify the complete terminal group, even when it has
    // only one terminal (the compiler will diagnose its invalid arity).
    VeriNode *args = gate_inst;
    if( args->detail_type() != veEXP_MULTI
        || static_cast<VeriMultiExp *>(args)->multi_type() != vemCOMMA_EXP )
    {
      VeriMultiExp *ports = new VeriMultiExp(_node_pool.next_id(), vemCOMMA_EXP,
                                              args->line(), args->col(), _mod);
      _node_pool.insert(ports);
      ports->append_child(args);
      args->set_father(ports);
      args = ports;
    }
    VeriGateInstance *instance = new VeriGateInstance(_node_pool.next_id(),
                                  gate_inst->line(), gate_inst->col(), NULL, args, _mod);
    _node_pool.insert(instance);
    args->set_father(instance);
    return instance;
  }

  VeriCallerExp * call_exp = NULL;
  VeriMultiExp  * multi_exp = NULL;

  VeriGateInstance *stmt = NULL;
  switch( gate_inst->detail_type() )
  {
    case veEXP_CALLER :
      call_exp = static_cast<VeriCallerExp *>(gate_inst);
      stmt = new VeriGateInstance( _node_pool.next_id( ), gate_inst->line(),
                                   gate_inst->col(), call_exp->caller(), 
                                   call_exp->arg(), _mod );
      _node_pool.insert( stmt );
      gate_inst->set_father( stmt );
      call_exp->caller()->set_father( stmt );
      call_exp->arg()->set_father( stmt );
      break;

    case veEXP_PRI :
      stmt = new VeriGateInstance( _node_pool.next_id( ), gate_inst->line(),
                                   gate_inst->col(), gate_inst,
                                   NULL, _mod );
      _node_pool.insert( stmt );
      gate_inst->set_father( stmt );
      break;

    case veEXP_MULTI :
      multi_exp = static_cast<VeriMultiExp *>(gate_inst);
      switch( multi_exp->multi_type() )
      {
        case vemCOMMA_EXP : case vemPORT_EXP :
          stmt = new VeriGateInstance( _node_pool.next_id( ), gate_inst->line(),
                                       gate_inst->col(), NULL, 
                                       gate_inst, _mod );
          _node_pool.insert( stmt );
          gate_inst->set_father( stmt );
          break;

        default:
          break;
      }
      break;

    default:
      break;
  }
  
  return stmt;
}

VeriNode *
VeriParser::gen_gate_instantiation( int line, int col, 
                            int gate_type, VeriNode *drive,
                            VeriNode *delay, VeriNode *list )
{
  VeriDelayExp * idelay = NULL;
  VeriDriveExp * idrive = NULL;
  
  if( delay == NULL )
  {
    idelay = new VeriDelayExp( _node_pool.next_id( ),
                               _node_pool.next_id( ),
                                line, col, _mod );
    _node_pool.insert( idelay->delay1() );
    _node_pool.insert( idelay );
  }
  else
    idelay = static_cast<VeriDelayExp *>(delay);

  if( drive == NULL )
  {
    idrive = new VeriDriveExp( _node_pool.next_id( ), line, col, _mod );
    _node_pool.insert( idrive );
  }
  else
    idrive = static_cast<VeriDriveExp *>(drive);

  VeriGateInstantiation * gate
    = new VeriGateInstantiation( _node_pool.next_id( ),
                                  line, col, gate_type,
                                  idrive, idelay, _mod );
  _node_pool.insert( gate );
  int re = gate->check_child_validation();
  if( re != OK )
    return gate;
  else
  {
    idelay->set_father( gate );
    idrive->set_father( gate );
  }

  if( list != NULL && list->detail_type() == vsSTMT_MOD_ITEM_LIST )
  {
    // The grammar supplies already separated instances. The temporary list
    // is pool-owned; only the final gate group participates in semantics.
    for(VeriNode *node : static_cast<VeriModuleItemList *>(list)->item_list())
    {
      if(node->detail_type() != vsINST_GATE_INSTANCE)
        throw std::runtime_error("invalid primitive instance group");
      gate->append_gate(static_cast<VeriGateInstance *>(node));
      node->set_father(gate);
    }
    return gate;
  }

  if( list == NULL || list->tok_type() != vtEXP )
    return gate;

  VeriGateInstance *gate_inst = NULL;
  switch( list->detail_type() )
  {
    case veEXP_MEMBER : case veEXP_ARRAY  : case veEXP_PRI : case veEXP_UNA : case veEXP_BIN :
    case veEXP_CALLER : case veEXP_MCONCAT : case veEXP_QUES :
    case veEXP_SIGN   : case veEXP_UNSIGN : case veEXP_MINTY :
      gate_inst = gen_gate_instance( list );
      if( gate_inst != NULL )
      {
        gate->append_gate( gate_inst );
        gate_inst->set_father( gate );
      }
      break;

    case veEXP_MULTI :
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      NodeList & exp_list = mexp->exp();
      NodeList::iterator it = exp_list.begin();
      for( ; it != exp_list.end(); ++it )
      {
        gate_inst = gen_gate_instance( *it );
        if( gate_inst != NULL )
        {
          gate->append_gate( gate_inst );
          gate_inst->set_father( gate );
        }
      }
      break;
    }

    default:
      break;
  }
  return gate;
}

VeriNode *
VeriParser::gen_tf_declaration( int line, int col, int inout, int type,
                                  int is_signed, VeriNode *range,
                                  VeriNode *port_ids )
{
  VeriTfDecl * tf_decl = new VeriTfDecl( _node_pool.next_id( ),
                                          line, col, inout,
                                          type, is_signed, range, _mod );
  _node_pool.insert( tf_decl );

  std::vector<VeriNode*> ports;
  if(port_ids->detail_type()==veEXP_MULTI&&static_cast<VeriMultiExp*>(port_ids)->multi_type()==vemCOMMA_EXP)
    for(auto* port:static_cast<VeriMultiExp*>(port_ids)->exp())ports.push_back(port);
  else ports.push_back(port_ids);
  for(auto* port:ports) {
    if(port->detail_type()==veEXP_ASSIGN) {
      auto* assignment=static_cast<VeriAssignExp*>(port);port=assignment->lval();
      auto* id=port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port;
      if(id->detail_type()!=veEXP_PRI)throw std::runtime_error("formal default requires a variable identifier");
      tf_decl->set_default(static_cast<VeriPrimaryExp*>(id)->str(),assignment->rval());
    }
    if(port->detail_type()!=veEXP_PRI&&port->detail_type()!=veEXP_ARRAY)throw std::runtime_error("unsupported subroutine formal declarator");
    tf_decl->append_port(port);port->set_father(tf_decl);
  }

  int re = tf_decl->check_child_validation();
  if( re == OK )
  {
    if( range != NULL )
      range->set_father( tf_decl );
  }
  return tf_decl;
}

VeriNode *
VeriParser::gen_tp_list( VeriNode *port )
{
  VeriTaskPortList * tp_list
    = new VeriTaskPortList( _node_pool.next_id( ), port->line(), port->col(), _mod );
  _node_pool.insert( tp_list );

  tp_list->append_port( port );
  int re = tp_list->check_last_child_validation();
  if( re == OK )
    port->set_father( tp_list );

  return tp_list;
}

VeriNode *
VeriParser::append_tp_list( VeriNode *list, VeriNode *port )
{
  VeriTaskPortList * tp_list
    = static_cast<VeriTaskPortList *>(list);
  tp_list->append_port( port );

  int re = tp_list->check_last_child_validation();
  if( re == OK )
    port->set_father( list );
  return tp_list;
}

VeriNode *
VeriParser::gen_fp_list( VeriNode *port )
{
  VeriFuncPortList * fp_list
    = new VeriFuncPortList( _node_pool.next_id( ),
                             port->line(), port->col(), _mod );
  _node_pool.insert( fp_list );

  fp_list->append_port( port );
  int re = fp_list->check_last_child_validation();
  if( re == OK )
    port->set_father( fp_list );
  return fp_list;
}

VeriNode *
VeriParser::append_fp_list( VeriNode *list, VeriNode *port )
{
  VeriFuncPortList * fp_list
    = static_cast< VeriFuncPortList *>(list);
  fp_list->append_port( port );

  int re = fp_list->check_last_child_validation();
  if( re == OK )
    port->set_father( list );
  return fp_list;
}

VeriNode *
VeriParser::gen_task_item_list( VeriNode *item )
{
  VeriTaskItemDeclList * list
    = new VeriTaskItemDeclList( _node_pool.next_id( ),
                                 item->line(), item->col(), _mod );
  _node_pool.insert( list );
  list->append_item( item );

  int re = list->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::append_task_item_list( VeriNode *list, VeriNode *item )
{
  VeriTaskItemDeclList * tlist
    = static_cast<VeriTaskItemDeclList *>(list);
  tlist->append_item( item );

  int re = tlist->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::gen_block_item_list( VeriNode *item )
{
  VeriBlockItemDeclList * list
    = new VeriBlockItemDeclList( _node_pool.next_id( ),
                                  item->line(), item->col(), _mod );
  _node_pool.insert( list );
  list->append_item( item );

  int re = list->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::append_block_item_list( VeriNode *list, VeriNode *item )
{
  VeriBlockItemDeclList * tlist
    = static_cast<VeriBlockItemDeclList *>(list);
  tlist->append_item( item );

  int re = tlist->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::gen_func_item_list( VeriNode *item )
{
  VeriFuncItemDeclList * list
    = new VeriFuncItemDeclList( _node_pool.next_id( ),
                                 item->line(), item->col(), _mod );
  _node_pool.insert( list );
  list->append_item( item );

  int re = list->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::append_func_item_list( VeriNode *list, VeriNode *item )
{
  VeriFuncItemDeclList * tlist
    = static_cast<VeriFuncItemDeclList *>(list);
  tlist->append_item( item );

  int re = tlist->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::gen_param_decl_list( VeriNode *item )
{
  VeriParamDeclList * list
    = new VeriParamDeclList( _node_pool.next_id( ),
                              item->line(), item->col(), _mod );
  _node_pool.insert( list );
  list->append_param( item );

  int re = list->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::append_param_decl_list( VeriNode *list, VeriNode *item )
{
  VeriParamDeclList * tlist
    = static_cast<VeriParamDeclList *>(list);
  tlist->append_param( item );

  int re = tlist->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::gen_port_decl_list( VeriNode *item )
{
  VeriPortDeclList * list
    = new VeriPortDeclList( _node_pool.next_id( ),
                             item->line(), item->col(), _mod );
  _node_pool.insert( list );
  list->append_port( item );

  int re = list->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::append_port_decl_list( VeriNode *list, VeriNode *item )
{
  VeriPortDeclList * tlist
    = static_cast<VeriPortDeclList *>(list);
  tlist->append_port( item );

  int re = tlist->check_last_child_validation();
  if( re == OK )
    item->set_father( list );
  return list;
}

VeriNode *
VeriParser::gen_task_decl( int line, int col, int is_auto, const char *tname,
                         VeriNode *task_port, VeriNode *task_item,
                         VeriNode *stmt )
{
  if(tname&&tname[0]!='\\'&&std::string(tname).find("::")!=std::string::npos&&is_auto==explicit_static_lifetime)
    throw std::runtime_error("extern method definition cannot have static lifetime");
  is_auto = is_auto==explicit_static_lifetime ? IS_FALSE :
      (is_auto==IS_TRUE || _default_subroutine_automatic ? IS_TRUE : IS_FALSE);
  String iname = "";
  if( tname != NULL ) iname = tname;

  VeriTaskDecl *decl
    = new VeriTaskDecl( _node_pool.next_id( ), line, col, iname, is_auto,
                        task_port, task_item, stmt, _mod );
  _node_pool.insert( decl );

  int re = decl->check_child_validation();
  if( re == OK )
  {
    if( task_port != NULL ) task_port->set_father( decl );
    if( task_item != NULL ) task_item->set_father( decl );
    stmt->set_father( decl );
  }
  return decl;
}

VeriNode* VeriParser::gen_constructor(int line,int col,VeriNode* ports,VeriNode* items,VeriNode* stmt) {
  if(_class_lifetimes.empty())throw std::runtime_error("constructor declaration requires a class");
  return gen_func_decl(line,col,IS_TRUE,IS_FALSE,-1,NULL,"new",ports,items,stmt);
}

VeriNode *
VeriParser::gen_func_decl( int line, int col, int is_auto, int is_signed,
                         int is_int, VeriNode *range, const char *name,
                         VeriNode *port_list, VeriNode *item_decl,
                         VeriNode *stmt )
{
  if(name&&name[0]!='\\'&&std::string(name).find("::")!=std::string::npos&&is_auto==explicit_static_lifetime)
    throw std::runtime_error("extern method definition cannot have static lifetime");
  is_auto = is_auto==explicit_static_lifetime ? IS_FALSE :
      (is_auto==IS_TRUE || _default_subroutine_automatic ? IS_TRUE : IS_FALSE);
  // Qualified new uses the ordinary identifier token outside the class.
  if(name&&name[0]!='\\'&&std::string(name).size()>=5&&std::string(name).substr(std::string(name).size()-5)=="::new") {
    if(is_int!=IS_FALSE||range||is_signed==IS_TRUE)throw std::runtime_error("extern constructor cannot declare a return type");
    is_int=-1;
  }
  // Result kinds include packed bit; check_child_validation diagnoses atom ranges.
  
  String iname = "";
  if( name != NULL )
    iname = name;

  VeriDecl * func = new VeriFuncDecl( _node_pool.next_id( ), line, col,
                                       is_auto, is_signed, is_int, range,
                                       iname, port_list, item_decl,
                                       stmt, _mod);
  _node_pool.insert( func );
  int re = func->check_child_validation();
  if( re == OK )
  {
    if( port_list != NULL )
      port_list->set_father( func );
    if(item_decl) item_decl->set_father( func );
    if(stmt) stmt->set_father( func );
  }
  return func;
}

VeriNode* VeriParser::gen_named_var_decl(int line,int col,const char* type,VeriNode* list) {
  auto* node=gen_var_decl(line,col,vpNO_IO,vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,list);
  if(node&&node->detail_type()==vsDECL_VAR)static_cast<VeriVarDecl*>(node)->set_type_name(type?type:"");
  return node;
}

VeriNode* VeriParser::gen_member(VeriNode* object,const char* member,int line,int col) {
  const std::string name(member);
  if(!name.empty()&&name.front()!='\\')if(auto at=name.find("::");at!=std::string::npos) {
    auto* prefix=static_cast<VeriMemberExp*>(gen_member(object,name.substr(0,at).c_str(),line,col));
    prefix->set_scope_reference();
    return gen_member(prefix,name.substr(at+2).c_str(),line,col);
  }
  auto* node=new VeriMemberExp(next_id(),line,col,object,member,_mod);
  insert_node(node);object->set_father(node);return node;
}
VeriNode* VeriParser::gen_packed_type(int line,int col,int kind,int signing,VeriNode* fields,const char* alias) {
  auto* decl=static_cast<VeriVarDecl*>(gen_typedef(line,col,vvLOGIC,signing,NULL,alias));
  decl->set_aggregate(kind);
  for(auto* field:static_cast<VeriBlockItemDeclList*>(fields)->block_item())decl->append_packed_member(field);
  return decl;
}
VeriNode* VeriParser::gen_enum(int line,int col,int type,int signing,VeriNode* range,const char* alias,VeriNode* members,const char* base_name) {
  auto* decl=static_cast<VeriVarDecl*>(gen_typedef(line,col,type,signing,range,alias,base_name));
  if(members->detail_type()==veEXP_MULTI) {
    auto* list=static_cast<VeriMultiExp*>(members);
    for(auto* member:list->exp())decl->append_enum_member(member);
  } else decl->append_enum_member(members);
  return decl;
}

VeriNode* VeriParser::gen_enum_variables(int line,int col,int type,int signing,VeriNode* range,VeriNode* members,VeriNode* variables,const char* base_name) {
  auto* decl=static_cast<VeriVarDecl*>(gen_var_decl(line,col,vpNO_IO,type,signing,vpSCALAR,NULL,range,NULL,variables));
  if(base_name)decl->set_type_name(base_name);
  if(members->detail_type()==veEXP_MULTI)
    for(auto* member:static_cast<VeriMultiExp*>(members)->exp())decl->append_enum_member(member);
  else decl->append_enum_member(members);
  return decl;
}

VeriNode* VeriParser::gen_typedef(int line,int col,int type,int signing,VeriNode* range,const char* alias,const char* base_name) {
  auto* id=gen_primary(alias,line,col,veVAR);
  return gen_typedef_declarator(line,col,type,signing,range,id,base_name);
}

VeriNode* VeriParser::gen_typedef_declarator(int line,int col,int type,int signing,VeriNode* range,VeriNode* declarator,const char* base_name) {
  auto* node=gen_var_decl(line,col,vpNO_IO,type,signing,vpSCALAR,NULL,range,NULL,declarator);
  auto* decl=static_cast<VeriVarDecl*>(node);decl->set_typedef();
  if(base_name)decl->set_type_name(base_name);
  return node;
}

VeriNode *
VeriParser::gen_var_decl( int line, int col, int inout, int type,
                          int is_signed, int vector_scalar, VeriNode *drive,
                          VeriNode *range, VeriNode *delay, VeriNode * list )
{
  if( list == NULL || list->tok_type() != vtEXP )
    return list;

  int re;
  if( range != NULL )
    vector_scalar = vpVECTOR;

  VeriVarDecl * var = new VeriVarDecl( _node_pool.next_id( ),
                                       line, col, inout, type,
                                       is_signed, vector_scalar, drive,
                                       range, delay, _mod );
  _node_pool.insert( var );
  re = var->check_child_validation( );
  if( re == OK )
  {
    if( drive != NULL ) drive->set_father( var );
    if( range != NULL ) range->set_father( var );
    if( delay != NULL ) delay->set_father( var );
  }

  switch( list->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ASSIGN :
    case veEXP_ARRAY :
      var->append_var( list );
      re = var->check_last_child_validation( );
      if( re == OK )
        list->set_father( var );
        
      break;

    case veEXP_MULTI:
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      if( mexp->multi_type() == vemCOMMA_EXP )
      {
        NodeList & vlist = mexp->exp();
        NodeList::iterator it = vlist.begin();
        for( ; it != vlist.end(); ++it )
        {
          var->append_var( *it );
          re = var->check_last_child_validation( );
          if( re == OK )
            (*it)->set_father( var );
        }
      }
      break;
    }

    default:
      break;
  }
  return var;
}

VeriNode *
VeriParser::gen_param_decl( int line, int col, int is_signed, int is_int,
                          int is_local, VeriNode *range, VeriNode *list )
{
  if( list == NULL || list->tok_type() != vtEXP )
    return list;

  int re;
  VeriParamDecl * var = new VeriParamDecl( _node_pool.next_id( ),
                                            line, col, is_signed,
                                            is_int, is_local, range, _mod );
  _node_pool.insert( var );
  re = var->check_child_validation( );
  if( re == OK )
  {
    if( range != NULL )
      range->set_father( var );
  }

  switch( list->detail_type() )
  {
    case veEXP_ASSIGN:
      var->append_var( list );
      re = var->check_last_child_validation( );
      if( re == OK )
        list->set_father( var );
      break;

    case veEXP_MULTI:
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      if( mexp->multi_type() == vemCOMMA_EXP )
      {
        NodeList & vlist = mexp->exp();
        NodeList::iterator it = vlist.begin();
        for( ; it != vlist.end(); ++it )
        {
          var->append_var( *it );
          re = var->check_last_child_validation( );
          if( re == OK )
            (*it)->set_father( var );
        }
      }
      break;
    }

    default:
      veri_err->append_err(ERR_ERROR,list,vCHILD_TYPE_PARAM_DECL);
      break;
  }
  return var;
}

VeriNode *
VeriParser::gen_int_decl( int line, int col, VeriNode *list )
{
  if( list == NULL || list->tok_type() != vtEXP )
    return list;

  int re;
  VeriIntDecl * int_decl = new VeriIntDecl( _node_pool.next_id( ),
                                            line, col, _mod );
  _node_pool.insert( int_decl );

  switch( list->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ARRAY :
    case veEXP_ASSIGN:
      int_decl->append_var( list );
      re = int_decl->check_last_child_validation( );
      if( re == OK )
        list->set_father( int_decl );
      break;

    case veEXP_MULTI:
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      if( mexp->multi_type() == vemCOMMA_EXP )
      {
        NodeList & vlist = mexp->exp();
        NodeList::iterator it = vlist.begin();
        for( ; it != vlist.end(); ++it )
        {
          int_decl->append_var( *it );
          re = int_decl->check_last_child_validation( );
          if( re == OK )
            (*it)->set_father( int_decl );
        }
      }
      break;
    }

    default:
      break;
  }
  return int_decl;
}

VeriNode *
VeriParser::gen_genvar_decl( int line, int col, VeriNode *list )
{
  if( list == NULL || list->tok_type() != vtEXP )
    return list;

  int re;
  VeriGenVarDecl * genvar = new VeriGenVarDecl( _node_pool.next_id( ),
                                                 line, col, _mod );
  _node_pool.insert( genvar );

  switch( list->detail_type() )
  {
    case veEXP_PRI :
    case veEXP_ARRAY :
    case veEXP_ASSIGN:
      genvar->append_var( list );
      re = genvar->check_last_child_validation( );
      if( re == OK )
        list->set_father( genvar );
      break;

    case veEXP_MULTI:
    {
      VeriMultiExp * mexp = static_cast<VeriMultiExp *>(list);
      if( mexp->multi_type() == vemCOMMA_EXP )
      {
        NodeList & vlist = mexp->exp();
        NodeList::iterator it = vlist.begin();
        for( ; it != vlist.end(); ++it )
        {
          genvar->append_var( *it );
          re = genvar->check_last_child_validation( );
          if( re == OK )
            (*it)->set_father( genvar );
        }
      }
      break;
    }

    default:
      break;
  }
  return genvar;
}

VeriNode* VeriParser::gen_interface_port(int line,int col,const char* type,const char* view,const char* name) {
  auto* decl=static_cast<VeriVarDecl*>(gen_var_decl(line,col,vpNO_IO,vvLOGIC,IS_FALSE,vpSCALAR,NULL,NULL,NULL,gen_primary(name,line,col,veVAR)));
  decl->set_interface_port(type,view?view:"");return decl;
}
void VeriParser::begin_modport(const char* name) {
  if(!_mod)prep_for_new_mod();
  if(!_mod->modports().emplace(name,std::map<String,int>{}).second)throw std::runtime_error("duplicate modport: "+std::string(name));
  _active_modport=name;_modport_direction=0;
}
void VeriParser::modport_member(const char* name,int direction) {
  if(direction!=-1)_modport_direction=direction;
  if(!_mod->modports().at(_active_modport).emplace(name,_modport_direction).second)throw std::runtime_error("duplicate modport member: "+std::string(name));
}
VeriNode* VeriParser::modport_prototype(VeriNode* declaration,bool explicit_import) {
  if(!explicit_import&&_modport_direction!=vpIMPORT)
    throw std::runtime_error("modport subroutine prototype requires import");
  auto* decl=static_cast<VeriDecl*>(declaration);
  const auto& name=decl->detail_type()==vsDECL_FUNC_DECL?
    static_cast<VeriFuncDecl*>(decl)->func_name():static_cast<VeriTaskDecl*>(decl)->task_name();
  modport_member(name.c_str(),vpIMPORT);
  decl->set_modport_prototype(_active_modport);
  return declaration;
}

VeriNode *
VeriParser::gen_mod( int line, int col, const char *name, VeriNode *param,
                       VeriNode *port, VeriNode *item_list, bool interface_kind, VeriNode* header_imports )
{
  if( _mod == NULL )
    prep_for_new_mod( );

  if(interface_kind)_mod->set_interface();
  else if(!_mod->modports().empty())throw std::runtime_error("modport declaration requires an interface");
  _mod->set_line( line );
  _mod->set_col( col );
  resolve_time_scope(_mod,item_list);_compilation_item_seen=true;

  String iname = "";
  if( name != NULL ) iname = name;
  _mod->set_name( iname );

  if( _top_mod_name.empty() && !_infer_top && !interface_kind )
    _top_mod_name = iname;

  if(    port != NULL
      && port->tok_type( ) == vtEXP
      && port->detail_type( ) != veEXP_MULTI )
  {
    VeriMultiExp *mexp = new VeriMultiExp( _node_pool.next_id( ), vemCOMMA_EXP,
                                           port->line(), port->col(), _mod );
    _node_pool.insert( mexp );
    mexp->append_child( port );
    port->set_father( mexp );
    port = mexp;
  }

  _mod->set_compilation_item_count(_compilation_items.size());
  _mod->set_header_imports(header_imports);
  if(header_imports)header_imports->set_father(_mod);
  _mod->set_param( param );
  _mod->set_port( port );
  _mod->set_item( item_list );
  _mod->addModInstantiated();

  _mod->set_fname( _fname, _fline );

  if( param != NULL ) param->set_father( _mod );
  if( port != NULL ) port->set_father( _mod );
  if( item_list != NULL ) item_list->set_father( _mod );

  int append_re = append_module( _mod );
  if( append_re == OK && _mod != NULL )
    _mods->add_mod_conn( _mod, _mod_instantiations );

  prep_for_new_mod( );
  
  return _mod;
}

int
VeriParser::clear_syntree( void )
{
  _node_pool.clean_up( );
  return OK;
}

void
VeriParser::dump_ast( CString& dir )
{
  _mods->dump_all_modules( dir, &_drawer );
}

void
VeriParser::append_err( int lvl, int line, int col, int err )
{
  String other = "";
  _err->append_err( lvl, line, col, err, other );
}

};

rtl::VeriNode* rtl::VeriParser::qualify_class_access(VeriNode* declaration,bool local) {
  if(_class_lifetimes.empty())throw std::runtime_error("class access qualifiers require a class declaration");
  if(declaration->detail_type()!=vsDECL_VAR&&declaration->detail_type()!=vsDECL_INT&&declaration->detail_type()!=vsDECL_FUNC_DECL&&declaration->detail_type()!=vsDECL_TASK_DECL)
    throw std::runtime_error("class access qualifier requires a property or method");
  if(declaration->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(declaration)->is_typedef())
    throw std::runtime_error("class access qualifier requires a property or method");
  auto* decl=static_cast<VeriDecl*>(declaration);
  if(decl->class_access()!=VeriDecl::PUBLIC)throw std::runtime_error("duplicate or conflicting class access qualifiers");
  decl->set_class_access(local?VeriDecl::LOCAL:VeriDecl::PROTECTED);return declaration;
}

rtl::VeriNode* rtl::VeriParser::qualify_const_property(VeriNode* declaration) {
  if((declaration->detail_type()!=vsDECL_VAR&&declaration->detail_type()!=vsDECL_INT)||
     (declaration->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(declaration)->is_typedef()))
    throw std::runtime_error("const requires a variable declaration");
  auto* decl=static_cast<VeriDecl*>(declaration);
  if(decl->const_property())throw std::runtime_error("duplicate const qualifier");
  decl->set_const_property();return declaration;
}

rtl::VeriNode* rtl::VeriParser::qualify_virtual(VeriNode* declaration) {
  if(_class_lifetimes.empty())throw std::runtime_error("virtual methods require a class declaration");
  if(declaration->detail_type()!=vsDECL_FUNC_DECL&&declaration->detail_type()!=vsDECL_TASK_DECL)throw std::runtime_error("virtual requires a class method");
  if(static_cast<VeriDecl*>(declaration)->virtual_method())throw std::runtime_error("duplicate virtual class qualifier");
  if(declaration->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(declaration)->func_name()=="new")throw std::runtime_error("constructors cannot be virtual");
  static_cast<VeriDecl*>(declaration)->set_virtual_method();return declaration;
}

rtl::VeriNode* rtl::VeriParser::qualify_static_method(VeriNode* declaration) {
  if(declaration->detail_type()==vsDECL_VAR||declaration->detail_type()==vsDECL_INT) {
    if(declaration->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(declaration)->is_typedef())throw std::runtime_error("static requires a class property or method");
    auto* decl=static_cast<VeriDecl*>(declaration);
    if(decl->explicit_static())throw std::runtime_error("duplicate static class qualifier");
    decl->set_explicit_static();return declaration;
  }
  if(_class_lifetimes.empty())throw std::runtime_error("static methods require a class declaration");
  if(declaration->detail_type()!=vsDECL_FUNC_DECL&&declaration->detail_type()!=vsDECL_TASK_DECL)throw std::runtime_error("static requires a class property or method");
  if(declaration->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(declaration)->func_name()=="new")throw std::runtime_error("constructors cannot be static");
  if(static_cast<VeriDecl*>(declaration)->static_method())throw std::runtime_error("duplicate static class qualifier");
  static_cast<VeriDecl*>(declaration)->set_static_method();return declaration;
}

rtl::VeriNode* rtl::VeriParser::qualify_dpi_import(VeriNode* declaration,const char* language,const char* alias,int property) {
  if(std::string(language)!="\"DPI-C\"")throw std::runtime_error("only DPI-C linkage is supported");
  if(!_class_lifetimes.empty())throw std::runtime_error("DPI imports require module, interface, package or compilation-unit scope");
  if(declaration->detail_type()!=vsDECL_FUNC_DECL)throw std::runtime_error("DPI imported tasks are not supported yet");
  auto* function=static_cast<VeriFuncDecl*>(declaration);
  function->set_dpi_import(alias?alias:function->func_name(),property);return declaration;
}
rtl::VeriNode* rtl::VeriParser::gen_dpi_export(int line,int col,const char* language,const char* alias,const char* name,bool task) {
  if(std::string(language)!="\"DPI-C\"")throw std::runtime_error("only DPI-C linkage is supported");
  if(!_class_lifetimes.empty())throw std::runtime_error("DPI exports cannot declare class members");
  auto* node=new VeriDpiExportStmt(next_id(),line,col,_mod,name,alias?alias:name,task);insert_node(node);return node;
}
