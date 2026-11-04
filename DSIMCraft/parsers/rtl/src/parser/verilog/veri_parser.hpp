/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_parser.hpp
 * Summary  : verilog syntax analyzer class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PARSER_VERILOG_VERI_PARSER_HPP_
#define PARSER_VERILOG_VERI_PARSER_HPP_

#include "singleton.hpp"

#include <string>
#include <sstream>
#include <vector>
#include <list>
#include <map>
#include <functional>
#include "veri_time.hpp"

#include "veri_node_pool.hpp"

#include "veri_node.hpp"
#include "veri_node_pool.hpp"
#include "veri_ast_node.hpp"
#include "veri_err_token.hpp"
#include "veri_ast_drawer.hpp"

extern int verilogparse( void );

namespace rtl
{

using pavio_singleton::Singleton;

class Cfg_mgr;
class Src_mgr;

class VeriVar;
class VeriSeqBlock;
class VeriMod;
class VeriSymbolTable;
class VeriModInstance;
class VeriGateInstance;
class VeriModContainer;
class VeriVarContainer;
class VeriNum;
class VeriErr;

/*
 * class VeriParser :
 *     verilog syntax-analyzer class deals with verilog HDL source code
 *   syntax-analysis.
 *
 *     Need to call int init() before parse.
 *     Need to call int parse() to parse source code.
 *     Has void clean_up() function to clean up inner data, back to status after
 *   init().
 *   
 */

// M: VeriMod* , P: VeriParser*
#define FOREACH_ALL_MODULES(M, P) for(auto (M) : (P)->get_modules()->all_modules())

class VeriParser : public Singleton<VeriParser>
{
  friend class Singleton<VeriParser>;

  typedef VeriModContainer          ModContainer;
  typedef VeriVarContainer          VarContainer;
  typedef VeriAstDrawer             AstDrawer;
  typedef VeriNodePool              NodePool;

  typedef std::string               String;
  typedef const String              CString;
  typedef std::list<String>         SList;
  typedef std::list<int>            IList;
  typedef unsigned int              Uint;
  typedef std::vector<Uint>         UVec;

  typedef std::vector< VeriNode * > NodeVec;
  typedef std::list< VeriNode * >   NodeList;
  typedef std::map< String, VeriNode * >    NodeMap;

  public:
    // initialize before using
    int init( void );
    int init( bool clear_mods );

    // set top module
    void set_top_module( CString& mod_name ) { _top_mod_name = mod_name; _infer_top=mod_name.empty(); }
    void set_systemverilog(bool enabled) { _systemverilog=enabled; }
    bool systemverilog() const { return _systemverilog; }
    void set_time_resolver(std::function<VeriTimeScale(int)> value) { _time_resolver=std::move(value); }
    uint64_t time_precision_fs() const { return _time_precision_fs; }
    VeriNode* gen_time_literal(const char* text,int line,int col);
    VeriNode* gen_time_declaration(int line,int col,const char* unit,const char* precision);
    void compilation_time(VeriNode* declaration);
    void resolve_time_scope(VeriMod* mod,VeriNode* items);
    // IS_FALSE means inherited lifetime; distinguish an explicit static override.
    static constexpr int explicit_static_lifetime = 2;
    void set_default_subroutine_automatic(bool enabled) { _default_subroutine_automatic=enabled; }
    void begin_class() {_class_lifetimes.push_back(_default_subroutine_automatic);_default_subroutine_automatic=true;}
    void end_class() {_default_subroutine_automatic=_class_lifetimes.back();_class_lifetimes.pop_back();}
    VeriVar* process_type(VeriNode* arguments=nullptr);
    VeriVar* ipc_type(const std::string& name,VeriNode* arguments,VeriSymbolTable* context);
    VeriNode* gen_class(int line,int col,const char* name,VeriNode* items,const char* closing);
    VeriNode* gen_covergroup(int line,int col,const char* name,VeriNode* event,VeriNode* items,const char* closing);
    VeriNode* gen_type_expression(int line,int col,const char* name,int builtin,int sign,VeriNode* range=nullptr,VeriNode* arguments=nullptr);
    VeriNode* gen_type_parameter(int line,int col,const char* name,VeriNode* value);
    VeriNode* gen_class_value_parameter(int line,int col,int sign,int type,VeriNode* range,VeriNode* variable);
    VeriNode* append_class_parameter(VeriNode* list,VeriNode* parameter);
    VeriNode* qualify_class_access(VeriNode* declaration,bool local);
    VeriNode* qualify_const_property(VeriNode* declaration);
    VeriNode* qualify_rand_property(VeriNode* declaration,bool cyclic=false);
    VeriNode* gen_constraint(const char* name,int line,int col,VeriNode* body);
    VeriNode* gen_constraint_foreach(int line,int col,VeriNode* array,VeriNode* indices,VeriNode* body);
    void resolve_extern_methods();
    VeriNode* qualify_extern(VeriNode* declaration);
    VeriNode* qualify_virtual(VeriNode* declaration);
    VeriNode* qualify_static_method(VeriNode* declaration);
    VeriNode* gen_constructor(int line,int col,VeriNode* ports,VeriNode* items,VeriNode* stmt);

    // get top module
    CString& get_top_module( void ) { return  _top_mod_name; }

    // get all modules
    ModContainer* get_modules( void ) { return _mods; }

    // parse from src_mgr :: code
    int parse( void );
    // Executable initializers/bodies may use the completed class declarations.
    // This is semantic ordering only; runtime initialization order is unchanged.
    void defer_semantic(VeriNode* node) { _deferred_semantics.push_back(node); }
    int finish_deferred_semantics();
    // Semantic bodies are independent of actual values. Runtime activations
    // remain separate in lowering; this cache only shares resolved syntax.
    VeriNode*& subroutine_binding(VeriNode* declaration,VeriSymbolTable* context) {
      return _subroutine_bindings[{declaration,context}];
    }
    
    // back to status after initialization
    void clean_up( void );

    // dump syntree to dot file
    void dump_ast( CString& dir );

    // get Verilog-module by name
    VeriMod *module( CString& name );
    VeriMod *package(CString& name) const;
    const std::vector<VeriMod*>& packages() const { return _package_order; }
    const std::vector<VeriMod*>& compilation_declarations() const { return _compilation_declarations; }
    VeriNode* gen_package(int line,int col,const char* name,VeriNode* items,const char* end_name=NULL);
    void compilation_import(VeriNode* node);
    void compilation_declaration(VeriNode* node);
    VeriNode* qualify_dpi_import(VeriNode* declaration,const char* language,const char* alias,int property);
    VeriNode* gen_dpi_export(int line,int col,const char* language,const char* alias,const char* name,bool task);
    VeriNode* gen_import(int line,int col,const char* name,const char* member,bool exporting=false);

    CString& get_err_info( void ) const { return _err->get_err_info( ); }
    int has_err( void ) const { return _err->has_err( ); }

  public: // open for lex
    int  get_cur_length(       ) const { return _length;  }
    void set_cur_length(int i  )       { _length = (i >= 0 ? i : 0); }
    void set_cur_s     (char *s)       { _s = s;          }
    char * get_s       (       ) const { return _s;       }

  public: // open for yacc

    /* expression */
    VeriNode* gen_dummy_port( int line, int col );
    VeriNode* gen_port_ref( int line, int col, const char *port_name );
    VeriNode* gen_primary( const char *str, int line, int col, int primary_type );
    VeriNode* gen_dump_target( VeriNode *prefix, const char *component, int line, int col );
    VeriNode* gen_array_type_query(const char* name,int type,int line,int col,VeriNode* range,VeriNode* dimension=NULL);
    VeriNode* gen_range  ( VeriNode *left, int rtype, VeriNode *right );
    VeriNode* gen_array  ( VeriNode *id, VeriNode *range );
    VeriNode* gen_caller ( VeriNode *name, VeriNode *call_exp );
    VeriNode* gen_type_cast(int type,int signing,int line,int col,VeriNode* operand);
    VeriNode* gen_unary  ( int op, int line, int col, VeriNode *exp1 );
    VeriNode* gen_conditional_event(VeriNode *event, VeriNode *condition, int line, int col);
    VeriNode* gen_binary ( VeriNode *exp1, int op, int line, int col,
                           VeriNode *exp2, bool declaration=false );
    VeriNode* gen_mintypmax( VeriNode *exp1, int line, int col,
                            VeriNode *exp2, VeriNode *exp3 );
    VeriNode* gen_ques_exp( VeriNode *ques, int line, int col,
                            VeriNode *choice1, VeriNode *choice2 );
    VeriNode* gen_multi  ( VeriNode *exp1, VeriNode *exp2,
                           int mtype, int line, int col );
    VeriNode* gen_inside_set(VeriNode* first);
    VeriNode* gen_pattern(int kind, VeriNode* first, VeriNode* second=nullptr);
    VeriNode* gen_empty_pattern(int line,int col);
    VeriNode* gen_empty_concat(int line,int col);
    VeriNode* gen_pattern_field(const char* name,VeriNode* value,int line,int col);
    VeriNode* gen_concat_exp( VeriNode *mexp );

    VeriNode* gen_delay_exp( int line, int col, VeriNode *d1, VeriNode *dextra, VeriNode *dthird = NULL );
    VeriNode* gen_drive_exp( int line, int col, int drive_from, int drive_to);

    VeriNode* gen_signed_exp( int line, int col, VeriNode *exp );
    VeriNode* gen_unsigned_exp( int line, int col, VeriNode *exp );

    /* statement */
    VeriNode* gen_loop_stmt( int line, int col, VeriNode *init,
                             VeriNode *judge, VeriNode *iter,
                             VeriNode *content, int kind = 0 );
    VeriNode* gen_func_loop_stmt( int line, int col, VeriNode *init,
                             VeriNode *judge, VeriNode *iter,
                             VeriNode *content );
    VeriNode* gen_default_case_item( int line, int col, VeriNode *item );
    VeriNode* gen_case_item( VeriNode *label, VeriNode *item );
    VeriNode* gen_case_item_list( VeriNode *item );
    VeriNode* append_case_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_case_stmt( int line, int col, int case_type,
                             VeriNode *switch_value, VeriNode *item );

    VeriNode* gen_func_default_case_item( int line, int col, VeriNode *item );
    VeriNode* gen_func_case_item( VeriNode *label, VeriNode *item );
    VeriNode* gen_func_case_stmt( int line, int col, int case_type,
                                  VeriNode *switch_value, VeriNode *item );
    VeriNode* gen_func_case_item_list( VeriNode *item );
    VeriNode* append_func_case_item_list( VeriNode *list, VeriNode *item );

    VeriNode* gen_func_cond_stmt( int line, int col, VeriNode *if_exp,
                                  VeriNode *if_stmt, VeriNode *else_stmt );
    VeriNode* gen_cond_stmt( int line, int col, VeriNode *if_exp,
                             VeriNode *if_stmt, VeriNode *else_stmt, bool ordered=false );

    VeriNode* gen_proc_timing_control_stmt( VeriNode *event_control,
                                          VeriNode *statement, bool level_sensitive = false );
    VeriNode* gen_disable_stmt( const char *label, int line, int col );
    VeriNode* gen_clocking(int line,int col,int kind,const std::string& name,
                          const NodeVec& children={},int direction=0,bool step=false);
    VeriNode* gen_event_stmt( int line, int col, int is_all,
                              VeriNode *event_list );

    VeriNode* gen_func_blocking_assign_stmt( VeriNode *assign_exp );
    VeriNode* gen_sys_caller_stmt( int line, int col, const char *name,
                                   VeriNode *call_exp );

    VeriNode* gen_dummy_stmt( int line, int col );
    VeriNode* gen_foreach(int line,int col,VeriNode* array,VeriNode* indices,VeriNode* body);
    VeriNode* gen_loop_jump(int line,int col,bool continuing);
    VeriNode* gen_action_stmt(int line,int col,int kind,VeriNode* target,VeriNode* value,int op);
    VeriNode* gen_update_stmt(int line,int col,VeriNode* target,int delta);
    VeriNode* gen_inline_for(int line,int col,VeriNode* init,VeriNode* judge,VeriNode* iter,VeriNode* body,int type=0,int is_signed=IS_TRUE,const char* type_name=nullptr,VeriNode* type_expression=nullptr);
    VeriNode* gen_seq_block_stmt( int line, int col, const char *name,
                                  int label_line, int label_col,
                                  VeriNode *decl_list, VeriNode *stmt_list );
    VeriNode* gen_func_seq_block_stmt( int line, int col, const char *name,
                                      int label_line, int label_col,
                                      VeriNode *decl_list, VeriNode *stmt_list );

    VeriNode* gen_stmt_list( VeriNode *item );
    VeriNode* append_stmt_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_func_stmt_list( VeriNode *item );
    VeriNode* append_func_stmt_list( VeriNode *list, VeriNode *item );

    VeriNode* gen_mod_item_list( VeriNode *item );
    VeriNode* append_mod_item_list( VeriNode *list, VeriNode *item );

    VeriNode* gen_block_or_non_or_caller_stmt( VeriNode *node );
    VeriNode* gen_blocking_stmt( VeriNode *lval, VeriNode *event,
                                 VeriNode *rval );
    VeriNode* gen_non_blocking_stmt( VeriNode *lval, VeriNode *event,
                                     VeriNode *rval );

    VeriNode* gen_continuous_assign_stmt( int line, int col,
                            VeriNode *delay, VeriNode *drive, VeriNode *exp );

    VeriNode* gen_init_stmt( int line, int col, VeriNode *stmt );
    void begin_bind(const char* target);
    void end_bind(VeriNode* instance);
    void resolve_bindings();
    VeriNode* gen_always_stmt( int line, int col, VeriNode *stmt,
                               int always_kind = akALWAYS );

    /* instantiation */
    VeriNode* gen_dummy_inst( int line, int col );
    VeriNode* gen_gen_loop_stmt( int line, int col, VeriNode *init,
                             VeriNode *judge, VeriNode *iter,
                             const char * label, int label_line,
                             int label_col, VeriNode *content );

    VeriNode* gen_default_gen_case_item( int line, int col, VeriNode *item );
    VeriNode* gen_gen_case_item( VeriNode *label, VeriNode *item );
    VeriNode* gen_gen_case_item_list( VeriNode *item );
    VeriNode* append_gen_case_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_gen_case_stmt( int line, int col,
                             VeriNode *switch_value, VeriNode *item );

    VeriNode* gen_gen_cond_stmt( int line, int col, VeriNode *if_exp,
                                 VeriNode *if_stmt, VeriNode *else_stmt );
    VeriNode* gen_gen_item_list( VeriNode *item );
    VeriNode* append_gen_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_gen_block_stmt( int line, int col, const char *name,
                                  int label_line, int label_col,
                                  VeriNode *item_list );

    VeriNode* gen_mod_instantiation( int line, int col, const char * mod_name,
                                     VeriNode *param, VeriNode *list );
    VeriNode* gen_gate_instantiation( int line, int col, 
                                int gate_type, VeriNode *drive,
                                VeriNode *delay, VeriNode *list );

    VeriModInstance* gen_mod_instance( VeriNode *mod_isnt );
    VeriGateInstance* gen_gate_instance( VeriNode *gate_inst, bool unnamed = false );

    /* declaration */
    VeriNode* gen_tf_declaration( int line, int col, int inout, int type,
                                  int is_signed, VeriNode *range,
                                  VeriNode *port_ids );
    VeriNode* gen_tp_list( VeriNode *port );
    VeriNode* append_tp_list( VeriNode *list, VeriNode *port );
    VeriNode* gen_fp_list( VeriNode *port );
    VeriNode* append_fp_list( VeriNode *list, VeriNode *port );
    VeriNode* gen_task_item_list( VeriNode *item );
    VeriNode* append_task_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_block_item_list( VeriNode *item );
    VeriNode* append_block_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_func_item_list( VeriNode *item );
    VeriNode* append_func_item_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_param_decl_list( VeriNode *item );
    VeriNode* append_param_decl_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_port_decl_list( VeriNode *item );
    VeriNode* append_port_decl_list( VeriNode *list, VeriNode *item );
    VeriNode* gen_task_decl( int line, int col, int is_auto, const char *tname,
                             VeriNode *task_port, VeriNode *task_item,
                             VeriNode *stmt );
    VeriNode* gen_func_decl( int line, int col, int is_auto, int is_signed,
                             int is_int, VeriNode *range, const char *name,
                             VeriNode *port_list, VeriNode *item_decl,
                             VeriNode *stmt );
    VeriNode* gen_virtual_interface_type(int line,int col,const char* name,const char* view);
    VeriVar* virtual_interface_type(int line,int col,const std::string& name,const std::string& view,VeriSymbolTable* context);
    VeriNode* gen_named_var_decl(int line,int col,const char* type,VeriNode* list);
    VeriNode* gen_member(VeriNode* object,const char* member,int line,int col);
    VeriNode* gen_packed_type(int line,int col,int kind,int signing,VeriNode* fields,const char* alias);
    VeriNode* gen_enum(int line,int col,int type,int signing,VeriNode* range,const char* alias,VeriNode* members,const char* base_name=NULL);
    VeriNode* gen_enum_variables(int line,int col,int type,int signing,VeriNode* range,VeriNode* members,VeriNode* variables,const char* base_name=NULL);
    VeriNode* gen_typedef(int line,int col,int type,int signing,VeriNode* range,const char* alias,const char* base_name=NULL);
    VeriNode* gen_typedef_declarator(int line,int col,int type,int signing,VeriNode* range,VeriNode* declarator,const char* base_name=NULL);
    VeriNode* gen_var_decl( int line, int col, int inout, int type,
                            int is_signed, int vector_scalar, VeriNode *drive,
                            VeriNode *range, VeriNode *delay, VeriNode * list );
    VeriNode* gen_param_decl( int line, int col, int is_signed, int is_int,
                              int is_local, VeriNode *range, VeriNode *list );
    VeriNode* gen_int_decl( int line, int col, VeriNode *list );
    VeriNode* gen_genvar_decl( int line, int col, VeriNode *list );

    VeriNode* gen_mod( int line, int col, const char *name, VeriNode *param,
                       VeriNode *port, VeriNode *item_list, bool interface_kind=false, VeriNode* header_imports=NULL );
    VeriNode* gen_interface_port(int line,int col,const char* type,const char* view,const char* name);
    void begin_modport(const char* name);
    void modport_member(const char* name,int direction=-1);
    VeriNode* modport_prototype(VeriNode* declaration,bool explicit_import);

  private:
    std::string _active_modport;
    struct Binding {String target;VeriNode* instance;VeriMod* owner;};
    std::vector<Binding> _bindings;
    VeriMod* _binding_saved_mod=nullptr;
    NodeList _binding_saved_instances;
    int _modport_direction=0;

  public: // error manipulation
    void include_file( int line, CString& fname )
    {
      _err->include_file( line, fname );
      _fname.push_back( fname );
      _fline.push_back( line );
    }

    void exclude_file( )
    {
      _err->exclude_file( );
      if( _fname.size() > 1 )
        _fname.pop_back();
      if( _fline.size() > 1 )
        _fline.pop_back();
    }

    void back_to_file( int line )
    {
      _err->back_to_file( line );
      if( _fname.empty() )
        _fname.push_back( "" );
      if( _fline.empty() )
        _fline.push_back( line );
      _fline.back() = line;
    }

    void append_err( int lvl, int line, int col, int err );

  public:  // node pool manipulation

    Uint next_id   ( void    ) { return _node_pool.next_id( ); }
    int  toss_node ( Uint id ) { return _node_pool.toss_node( id ); }

    int  insert_node ( VeriNode *node )
    { return _node_pool.insert( node ); }

  protected:
    int clear_syntree( void );

    int append_module( VeriMod *mod );
    int prep_for_new_mod( void );

    String int2string(int n)
    {
      std::stringstream f;
      f << n;
      return f.str();
    }

  public:
    // back to status after construction
    void clear( void );

  private:
    VeriParser();
    ~VeriParser();

    // manager ptrs
    Cfg_mgr  *_cmgr;
    Src_mgr  *_smgr;
    VeriErr  *_err;
    SList     _fname;
    IList     _fline;
    String    _top_mod_name;
    bool _infer_top=false;
    bool _systemverilog=true;
    std::function<VeriTimeScale(int)> _time_resolver;
    uint64_t _compilation_unit_fs=0,_compilation_precision_fs=0,_time_precision_fs=0;
    bool _compilation_item_seen=false;
    std::vector<VeriNode*> _compilation_times;
    bool _default_subroutine_automatic=false;
    std::vector<bool> _class_lifetimes;
    std::vector<VeriNode*> _deferred_semantics;
    std::map<std::pair<String,String>,VeriVar*> _virtual_interface_types;
    std::map<std::pair<VeriNode*,VeriSymbolTable*>,VeriNode*> _subroutine_bindings;

    NodeList  _mod_instantiations;

    // for flex and bison
    char     *_s;
    Uint      _length;
    VeriMod  *_mod;

    // data lib
    ModContainer *_mods;
    std::map<String,VeriMod*> _packages;
    std::vector<VeriMod*> _package_order;
    std::vector<VeriNode*> _source_declarations;
    std::vector<VeriNode*> _compilation_items;
    // Declaration owners are private lexical units, never public packages or
    // module instances. Views borrow their symbol tables; only import views
    // are owned directly by the parser.
    std::vector<VeriMod*> _compilation_declarations;
    std::vector<VeriSymbolTable*> _compilation_import_scopes;
    std::vector<VeriSymbolTable*> _compilation_scopes;
    VeriSymbolTable* _builtin_scope=nullptr;
    std::map<std::string,VeriSeqBlock*> _ipc_types;
    NodePool      _node_pool;

    // utilities
    AstDrawer     _drawer;
};

};

extern rtl::VeriParser *veri_parser;

#endif // PARSER_VERILOG_VERI_PARSER_HPP_
