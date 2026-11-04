/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_var_container.hpp
 * Summary  : verilog syntax analyzer :: variable container
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.11.20
 */
#ifndef PARSER_VERILOG_VERI_VAR_CONTAINER_
#define PARSER_VERILOG_VERI_VAR_CONTAINER_

#include <string>
#include <cstring>
#include <list>
#include <map>
#include <fstream>

#include "veri_var.hpp"

namespace rtl
{
class VeriDecl;
class VeriSeqBlock;

/*
 * class VeriSymbolTable :
 *     Verilog syntax-analyzer class deals with variable check, mapping
 *   optimization and other related operations.
 *
 *     Need to call int init() before processing?
 *     Has void clean_up() function to clean up inner data, back to status after
 *   init().
 */
class VeriSymbolTable
{
  typedef VeriSymbolTable   SymbolTable;

  typedef std::string        String;
  typedef const String       CString;
  typedef unsigned int       Uint;
  typedef std::ofstream      Ofstream;
  typedef std::vector< VeriNode * > NodeVec;
  typedef std::list< SymbolTable * > ContList;
  typedef std::queue< SymbolTable *> SymbolTableQueue;

  private:
    class Symbol
    {
      public:
        Symbol( void ) : _name(""), _data(NULL), _next(NULL) {}
        ~Symbol( void )
        {
          _data = NULL;
          _next = NULL;
        }

        String     _name;
        VeriNode  *_data;
        Symbol    *_next;
    };

  public:
    VeriSymbolTable( void )
      : _size(0)
      , _hash_list(NULL)
      , _name("")
      , _table_type(vMOD_SCOPE)
      , _depth(0)
      , _deeper()
      , _floater(NULL)
    {};

    VeriSymbolTable( const VeriSymbolTable * copy )
      : _size(copy->_size>31?31:copy->_size)
      , _hash_list(NULL)
      , _name(copy->_name)
      , _table_type(copy->_table_type)
      , _depth(copy->_depth)
      , _deeper()
      , _floater(copy->_floater)
    {
      _hash_list = new Symbol*[_size];
      for( Uint i = 0 ; i < _size ; ++i )
        _hash_list[i] = NULL;
     
      _floater->_deeper.push_back( this );
    };

    ~VeriSymbolTable()
    {
      clear();
    };

    // initialization for hash bucket, designating size
    int init( Uint size, CString& mod_name );

    int depth( void ) const { return _depth; }
    int table_type() const { return _table_type; }
    const String& name() const { return _name; }

    SymbolTable * floater( void ) { return _floater; }

    // enter a new scope, deeper one
    SymbolTable * append_scope( CString& name, int table_type );

    // finish current scope
    SymbolTable * finish_scope( void );

    // copy scope
    SymbolTable * copy_scope( const SymbolTable *scope );

    // insert one node in current scope
    int insert( CString& name, VeriNode * data );

    // look for node in current and all the above scope
    VeriNode* value( CString& name );
    VeriNode* value_same_level( CString& name );
    VeriNode* class_member(CString& name) {auto* own=value_same_level(name);return own?own:_class_base?_class_base->class_member(name):nullptr;}
    void set_class_base(SymbolTable* base) {_class_base=base;}
    VeriSeqBlock* class_owner() const {return _class_owner;}
    void set_class_owner(VeriSeqBlock* owner) {_class_owner=owner;}
    VeriNode* value_within_module( CString& name );
    void set_compilation_scope(SymbolTable* scope) { _compilation_scope=scope; }
    void inherit_imports(SymbolTable* previous);
    void set_compilation_unit() { _compilation_unit=true; }
    void finalize_compilation_imports();
    void import_package(SymbolTable* package,CString& member);
    void export_package(CString& package,CString& member);
    void finalize_exports();
    VeriNode* package_value(CString& name);

    // clear inner data, back to status after init
    void clean_up( void );

    // clear inner data, back to status after construction
    void clear( void );

    int  replace_value_same_level( CString& name, VeriNode *data );

    // for debug usage
    void hash_print( void );

    int pretty_dot_output( Ofstream& ofile, int depth );
    int push_more_table( SymbolTableQueue & queue );

  protected:
    // basic creation function
    int hash_create( Uint size, int depth, SymbolTable *floater,
                     CString& name, int table_type );

    bool hash_cmp33( const char *src, const char *des )
    {
      return ( 0 == strcmp(src, des));
    }

    Uint hash_key33( const char *name )
    {
      const char *p = name;
      Uint  nhash = 5381;
      while( (*p) != '\0' )
      {
        nhash += (nhash << 5) + *p;
        ++p;
      }
      return nhash;
    }

    // node deletion is not supported in parser
    int hash_delete( CString& name );

    // not supported
    void hash_print_recur( int depth );

  private:
    Uint          _size;
    Uint          _symbol_count=0;
    Symbol      **_hash_list;  
    void grow();

    String        _name;
    int           _table_type;
    int           _depth;

    ContList      _deeper;
    SymbolTable  *_floater;
    SymbolTable* _class_base=nullptr;
    VeriSeqBlock* _class_owner=nullptr;
    SymbolTable* _compilation_scope=nullptr;
    SymbolTable* _previous_imports=nullptr;
    bool _compilation_unit=false;
    std::map<String,VeriNode*> _pending_import_bindings;
    VeriNode* prior_import_binding(CString& name);
    // Non-owning package scopes. Wildcards remain lazy so local declarations
    // can shadow them and two packages exporting the same name are diagnosed.
    std::vector<SymbolTable*> _wildcard_imports;
    std::map<String,VeriNode*> _explicit_imports;
    std::map<String,VeriNode*> _wildcard_bindings;
    // Preserve the importing package path as well as the canonical declaration:
    // an export may name only a package from which this scope imports it.
    std::map<String,std::vector<SymbolTable*>> _import_sources;
    std::vector<String> _export_packages;
    std::map<String,VeriNode*> _explicit_exports;
    std::vector<std::pair<String,String>> _pending_exports;
    bool _export_all=false;
    void resolve_exports(bool final);
    VeriNode* imported_value(CString& name);
};  

// Access belongs to the declaration's lexical class, never its receiver's type.
// Raw layout/override lookup remains unrestricted; source references call this.
VeriDecl* veri_class_member_declaration(VeriNode* symbol);
bool veri_local_class_member(VeriNode* symbol);
void veri_check_class_access(VeriNode* symbol,VeriSymbolTable* context);

};

#endif // PARSER_VERILOG_VERI_VAR_CONTAINER_
