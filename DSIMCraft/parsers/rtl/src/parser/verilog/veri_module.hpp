/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_module.hpp
 * Summary  : verilog syntax analyzer :: module
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.12.20
 */

#ifndef PARSER_VERILOG_VERI_MODULE_
#define PARSER_VERILOG_VERI_MODULE_

#include <cstdlib>
#include <string>
#include <list>
#include <fstream>
#include <map>

#include "veri_node.hpp"
#include "veri_symbol_table.hpp"
#include "veri_time.hpp"

namespace rtl
{

class VeriExp;
class VeriNum;
class VeriDecl;
class VeriGateInstantiation;
class VeriModInstantiation;

/*
 * class VeriMod :
 *     Verilog syntax-analyzer Module class.
 *
 *     call init before using.
 */
// I/P: VeriNode* , M: VeriMod*
#define FOREACH_ITEMS_OF_MODULE(I, M) for(auto (I) : ((rtl::VeriModuleItemList*)((M)->item()))->item_list())
#define FOREACH_PORTS_OF_MODULE(P, M) for(auto (P) : ((rtl::VeriMultiExp*)((M)->port()))->exp())
#define FOREACH_INSTS_OF_MODULE(I, M) for(auto (I) : ((M)->modInstantiated()))

class VeriMod : public VeriNode
{
  typedef VeriSymbolTable                SymbolTable;
  typedef std::list< String >            SList;
  typedef std::map< String, VeriNode * > NodeMap;
  typedef std::vector<int>               IVec;

  public:
    VeriMod( Uint idx )
      :  VeriNode( idx, vtMOD, vtMOD, 0, 0, this )
      , _mod_name("")
      , _param(NULL)
      , _port(NULL)
      , _item(NULL)
      , _act_port_num( 0 )
      , _symbols(NULL)
    {}

    ~VeriMod( void ) { clear(); };
 
    void init( int symbol_table_size );

    // assessors
    CString& name ( void ) const { return _mod_name; }
    using Modports = std::map<String, std::map<String, int>>;
    bool is_interface() const { return _is_interface; }
    void set_interface() { _is_interface=true; }
    Modports& modports() { return _modports; }
    const Modports& modports() const { return _modports; }
    VeriNode* modport_prototype(const String& view,const String& name) const {
      auto v=_modport_prototypes.find(view);if(v==_modport_prototypes.end())return nullptr;
      auto p=v->second.find(name);return p==v->second.end()?nullptr:p->second;
    }
    bool has_interface_ports() const;
    int bind_interface_ports();
    bool is_package() const { return _is_package; }
    bool is_compilation_unit() const { return _is_compilation_unit; }
    void set_compilation_unit() { _is_compilation_unit=true; }
    const VeriTimeScale& time_scale() const { return _time_scale; }
    void set_time_scale(const VeriTimeScale& value) { _time_scale=value; }
    void set_package() { _is_package=true; }
    const SList& fname( void ) const { return _fname; }
    const IList& fline( void ) const { return _fline; }
    size_t compilation_item_count() const { return _compilation_item_count; }
    void set_compilation_item_count(size_t count) { _compilation_item_count=count; }
    void set_compilation_scope(SymbolTable* symbols) { _compilation_scope=symbols; }
    VeriNode* header_imports() const { return _header_imports; }
    VeriNode * param( void ) { return _param; }
    VeriNode * port( void ) { return _port; }
    VeriNode * item( void ) { return _item; }
    const NodeList& modInstantiated( void ) { return _modInstantiated; }
    VeriExp *parameter_override_expression( CString& name ) const {
      auto it=_parameter_override_expressions.find(name);
      return it==_parameter_override_expressions.end()?NULL:it->second;
    }
    VeriNum *parameter_override( CString& name ) const {
      auto it = _parameter_overrides.find(name);
      return it == _parameter_overrides.end() ? NULL : it->second;
    }

    // mutators for lists to be output to dfg
    void set_name ( CString&  name  ) { _mod_name = name; }
    void set_fname( const SList& fnames, const IList& flines  );
    void set_header_imports(VeriNode* imports) { _header_imports=imports; }
    void set_param( VeriNode *param ) { _param = param; }
    void set_port ( VeriNode *port  ) { _port  = port;  }
    void set_item ( VeriNode *item  ) { _item  = item;  }
    void addModInstantiated ( void );
    void add_bound_instance(VeriNode* node) { _modInstantiated.push_back(node); }

    SymbolTable *symbol_table( void ) { return _symbols; }

    // clear inner data, back to status after initialization
    virtual void clear( void );

    // clear inner data, back to status after construction
    virtual void clean_up( void );

    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

  protected:
    int push_everything( NodeVec& mstack );
    int prepare_parameter_overrides( void );

    int prep_ports_for_map( void );
    int check_type_ref( VeriExp *exp, VeriVar *port );
    int map_ports( void );

    int finish_scope( void );

  protected:
    VeriMod( Uint idx, const VeriMod *copy )
      :  VeriNode( idx, copy )
      , _mod_name( copy->_mod_name )
      , _time_scale(copy->_time_scale)
      , _is_interface(copy->_is_interface)
      , _compilation_item_count(copy->_compilation_item_count)
      , _compilation_scope(copy->_compilation_scope)
      , _modports(copy->_modports)
      , _fname( copy->_fname.begin(), copy->_fname.end() )
      , _fline( copy->_fline.begin(), copy->_fline.end() )
      , _param( NULL )
      , _port( NULL )
      , _item( NULL )
      , _act_port_num( 0 )
      , _symbols( NULL )
    {
    }

  private:
    String       _mod_name;
    VeriTimeScale _time_scale;
    bool _is_package=false;
    bool _is_compilation_unit=false;
    bool _is_interface=false;
    Modports _modports;
    // Non-owning semantic index; rebuilt from this clone's owned declarations.
    std::map<String,std::map<String,VeriNode*>> _modport_prototypes;
    SList        _fname;
    IList        _fline;

    // Non-owning lexical parent, independent of hierarchical instance scopes.
    size_t _compilation_item_count=0;
    SymbolTable* _compilation_scope=nullptr;

    // Header imports belong to each module/interface clone, never its parent.
    VeriNode* _header_imports=nullptr;

    // syntax tree
    VeriNode    *_param;
    VeriNode    *_port;
    VeriNode    *_item;
    NodeList    _modInstantiated;
    std::map<String, VeriNum *> _parameter_overrides;
    std::map<String, VeriExp *> _parameter_override_expressions;

    NodeList  _act_ports;
    int       _act_port_num;

    // variable container
    SymbolTable *_symbols;
};

};

#endif // PARSER_VERILOG_VERI_MODULE_
