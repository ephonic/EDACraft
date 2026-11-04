/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_node.hpp
 * Summary  : verilog syntax analyzer true node class : declaration
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_DECL_HPP_
#define PARSER_VERILOG_VERI_DECL_HPP_

#include "veri_node.hpp"
#include "veri_stmt.hpp"

#include <vector>
#include <string>
#include <set>
#include <map>

namespace rtl
{
struct VeriPackedField;

class VeriExp;
class VeriCallerExp;
struct VeriCallArgument {
  VeriNode* value;bool defaulted;VeriNode* default_formal;
  VeriCallArgument(VeriNode* value=nullptr,bool defaulted=false,VeriNode* source=nullptr)
    :value(value),defaulted(defaulted),default_formal(source){}
};
VeriNode* veri_formal_symbol(VeriNode* formal);
VeriNode* veri_call_hive(VeriNode* call);
bool veri_subroutine_call(VeriNode* call);
std::vector<VeriNode*> veri_subroutine_formals(VeriNode* declaration);
std::vector<VeriCallArgument> veri_bind_arguments(VeriNode* call,const std::vector<VeriNode*>& formals);
class VeriVar;
void veri_validate_extern_methods(VeriSeqBlock* definition);
class VeriNum;
class VeriVar;
class VeriTfVar;
class VeriParam;
class VeriGenVar;
class VeriInt;
class VeriFunc;

/*
 * class VeriDecl :
 *     Verilog syntax analyzer true node : declaration
 */
class VeriDecl : public VeriNode
{
  public:
    VeriDecl( Uint idx, int line, int col, int decl_type,
              VeriMod *mod )
      :  VeriNode( idx, vtDECL, decl_type, line, col, mod )
      , _decl_status( vSTART_S )
    {}

    virtual ~VeriDecl() {};

    int decl_status( void ) { return _decl_status; }
    void set_decl_status( int s ) { _decl_status = s; }
    enum ClassAccess { PUBLIC, LOCAL, PROTECTED };
    ClassAccess class_access() const {return _class_access;}
    void set_class_access(ClassAccess access) {_class_access=access;}
    bool extern_method() const {return _extern_method;}
    void set_extern_method() {_extern_method=true;}
    VeriNode* extern_header() const {return _extern_header;}
    void set_extern_header(VeriNode* header) {_extern_header=header;if(header)header->set_father(this);}
    bool dpi_import() const {return !_dpi_name.empty();}
    const std::string& dpi_name() const {return _dpi_name;}
    int dpi_property() const {return _dpi_property;}
    void set_dpi_import(const std::string& name,int property) {_dpi_name=name;_dpi_property=property;}
    bool virtual_method() const {return _virtual_method;}
    void set_virtual_method() {_virtual_method=true;}
    bool static_method() const {return _static_method;}
    void set_static_method() {_static_method=true;}
    bool pure_virtual() const {return _pure_virtual;}
    void set_pure_virtual() {_virtual_method=true;_pure_virtual=true;}
    bool explicit_automatic() const { return _explicit_automatic; }
    void set_explicit_automatic() { _explicit_automatic=true; }
    bool explicit_static() const { return _explicit_static; }
    bool const_property() const { return _const_property; }
    void set_const_property() { _const_property=true; }
    bool rand_property() const { return _rand_property; }
    bool randc_property() const { return _randc_property; }
    void set_rand_property(bool cyclic=false) { _rand_property=true;_randc_property=cyclic; }
    void set_explicit_static() { _explicit_static=true; }
    const std::string& modport_prototype() const { return _modport_prototype; }
    void set_modport_prototype(const std::string& view) { _modport_prototype=view; }

    virtual void clean_up( void ) = 0;
    virtual int  check_child_validation( void ) = 0;

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue ) = 0;
    virtual int  pretty_dot_label( Ofstream& ofile, int depth ) = 0;

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info ) = 0;
    virtual int  push_for_replacement( NodeVec& mstack ) = 0;
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl ) = 0;

  protected:
    VeriDecl( Uint idx, const VeriDecl *decl_copy )
      :  VeriNode( idx, decl_copy )
      , _extern_method(decl_copy->_extern_method)
      , _dpi_name(decl_copy->_dpi_name)
      , _dpi_property(decl_copy->_dpi_property)
      , _class_access(decl_copy->_class_access)
      , _virtual_method(decl_copy->_virtual_method)
      , _pure_virtual(decl_copy->_pure_virtual)
      , _static_method(decl_copy->_static_method)
      , _explicit_automatic(decl_copy->_explicit_automatic)
      , _explicit_static(decl_copy->_explicit_static)
      , _const_property(decl_copy->_const_property)
      , _rand_property(decl_copy->_rand_property)
      , _randc_property(decl_copy->_randc_property)
      , _modport_prototype(decl_copy->_modport_prototype)
    {}

  private:
    int   _decl_status;
    bool _extern_method=false;
    VeriNode* _extern_header=nullptr;
    std::string _dpi_name;
    int _dpi_property=0; // 0 ordinary, 1 pure, 2 context
    ClassAccess _class_access=PUBLIC;
    bool _virtual_method=false;
    bool _pure_virtual=false;
    bool _static_method=false;
    bool _explicit_automatic=false;
    bool _explicit_static=false;
    bool _const_property=false;
    bool _rand_property=false;
    bool _randc_property=false;
    std::string _modport_prototype;
};

// A constraint is owned syntax, separate from procedural statements/methods.
// Bind after all class properties have been registered (including forward uses).
class VeriConstraintDecl : public VeriDecl {
 public:
  VeriConstraintDecl(Uint id,int line,int col,VeriMod* mod,const std::string& name,VeriNode* body)
   :VeriDecl(id,line,col,vsDECL_CONSTRAINT,mod),_name(name),_body(body) {if(body)body->set_father(this);}
  const std::string& name() const {return _name;}
  VeriNode* body() const {return _body;}
  void bind();
  void clean_up() override {_bound=false;set_pstatus(vSTART_S);}
  int check_child_validation() override {return OK;}
  int pretty_dot_label(Ofstream&,int) override {return OK;}
  int push_dot_children(NodeQueue&,IQueue&) override;
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec& stack) override {if(_body)stack.push_back(_body);return OK;}
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  std::string _name;
  VeriNode* _body;
  bool _bound=false;
};

class VeriTfDecl : public VeriDecl
{
  public:
    VeriTfDecl( Uint idx, int line, int col, int inout, int net_type,
                int is_signed, VeriNode *range, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_TF_DECL, mod )
      , _net_type( net_type )
      , _inout( inout )
      , _is_signed( is_signed )
      , _range( range )
    {}

    virtual ~VeriTfDecl() { clear(); }

    // accessors
    void set_type_name(const std::string& name) { _type_name=name; }
    const std::string& type_name() const {return _type_name;}
    void set_type_expression(VeriNode* value) {_type_expression=value;if(value)value->set_father(this);}
    VeriVar* resolved_type() const { return _resolved_type; }
    int net_type ( void ) { return _net_type;  }
    int inout    ( void ) { return _inout;     }
    void set_inout(int direction) {_inout=direction;}
    int is_signed( void ) { return _is_signed; }
    VeriNode * range( void ) { return _range;  }
    NodeList & port_ids( void ) { return _port_ids; }
    VeriNode* default_argument(const std::string& name) const { auto i=_defaults.find(name);return i==_defaults.end()?nullptr:i->second; }
    void set_default(const std::string& name,VeriNode* value) { _defaults[name]=value;value->set_father(this); }

    // mutators
    void append_port( VeriNode *node ) { _port_ids.push_back( node ); }

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
    int push_children( NodeVec& mstack );
    int declare_tf_symbol( void );

    VeriTfVar * reg_tfvar_symbol( int line, int col, CString& name,
                              int dstart, int dend, VeriNode *var );

  protected:
    VeriTfDecl( Uint idx, const VeriTfDecl *copy )
      :  VeriDecl( idx, copy )
      , _type_name(copy->_type_name)
      , _net_type( copy->_net_type )
      , _inout( copy->_inout )
      , _is_signed( copy->_is_signed )
      , _range( NULL )
    {}

  private:
    VeriNode* _type_expression=nullptr;
    std::string _type_name;
    VeriVar* _resolved_type=nullptr; // Lexical binding, resolved again in each clone.
    int       _net_type;
    int       _inout;
    int       _is_signed;
    VeriNode *_range;
    NodeList  _port_ids;
    std::map<std::string,VeriNode*> _defaults;
};

class VeriTaskPortList : public VeriDecl
{
  public:
    VeriTaskPortList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_TASK_PORT_LIST, mod )
    {}

    virtual ~VeriTaskPortList() { clear(); }

    // accessors
    NodeList & task_port( void ) { return _task_port; }

    // mutators
    void append_port( VeriNode * node ) { _task_port.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriTaskPortList( Uint idx, const VeriTaskPortList *copy )
      : VeriDecl( idx, copy )
    {}

  private:
    NodeList _task_port;
};

class VeriFuncPortList : public VeriDecl
{
  public:
    VeriFuncPortList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_FUNC_PORT_LIST, mod )
    {}

    virtual ~VeriFuncPortList() { clear(); }

    // accessors
    NodeList & func_port( void ) { return _func_port; }

    // mutators
    void append_port( VeriNode * node ) { _func_port.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriFuncPortList( Uint idx, const VeriFuncPortList *copy )
      : VeriDecl( idx, copy )
    {}

  private:
    NodeList _func_port;
};

class VeriTaskItemDeclList : public VeriDecl
{
  public:
    VeriTaskItemDeclList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_TASK_ITEM_DECL_LIST, mod )
    {}

    virtual ~VeriTaskItemDeclList() { clear(); }

    // accessors
    NodeList & task_item( void ) { return _task_item; }

    // mutators
    void append_item( VeriNode * node ) { _task_item.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriTaskItemDeclList( Uint idx, const VeriTaskItemDeclList *copy )
      : VeriDecl( idx, copy )
    {}

  private:
    NodeList _task_item;
};

class VeriBlockItemDeclList : public VeriDecl
{
  public:
    VeriBlockItemDeclList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_BLOCK_ITEM_DECL_LIST, mod )
    {}

    virtual ~VeriBlockItemDeclList() { clear(); }

    // accessors
    NodeList & block_item( void ) { return _block_item; }

    // mutators
    void append_item( VeriNode * node ) { _block_item.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriBlockItemDeclList( Uint idx, const VeriBlockItemDeclList *copy )
      : VeriDecl( idx, copy )
    {}

  private:
    NodeList _block_item;
};

class VeriFuncItemDeclList : public VeriDecl
{
  public:
    VeriFuncItemDeclList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_FUNC_ITEM_DECL_LIST, mod )
    {}

    virtual ~VeriFuncItemDeclList() { clear(); }

    // accessors
    NodeList & func_item( void ) { return _func_item; }

    // mutators
    void append_item( VeriNode * node ) { _func_item.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriFuncItemDeclList( Uint idx, const VeriFuncItemDeclList *copy )
      : VeriDecl( idx, copy )
    {}

  private:
    NodeList _func_item;
};

class VeriTaskDecl : public VeriDecl
{
  typedef std::vector<int> IVec;

  public:
    VeriTaskDecl( Uint idx, int line, int col, CString& task_name,
                  int is_auto, VeriNode *task_port, VeriNode *item_decl,
                  VeriNode *stmt,
                       VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_TASK_DECL, mod )
      , _task_name( task_name )
      , _is_auto( is_auto )
      , _task_port( task_port )
      , _item_decl( item_decl )
      , _stmt( stmt )
      , _act_port_num( 0 )
    {}

    virtual ~VeriTaskDecl() { clear(); }

    // accessors
    CString& task_name( void ) { return _task_name; }
    void set_method_name(const std::string& name) {_task_name=name;}
    void adopt_extern_body(VeriTaskDecl* definition);
    int      is_auto  ( void ) { return _is_auto; }

    VeriNode *task_port( void ) { return _task_port; }
    VeriNode *item_decl( void ) { return _item_decl; }
    VeriNode *stmt     ( void ) { return _stmt; }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    virtual int  search_for_symbol( NodeVec& seq, String& help_info );

  protected:
    int reg_task_symbol( void );

    int push_ports( NodeVec& mstack );

    int get_call_exp( void );
    int prep_ports_for_check_type( void );
    int check_type_ref( VeriExp *exp, VeriNode *port, int no_assign );

    int push_contents( NodeVec& mstack );
    
    int finish_scope( void );

  protected:
    VeriTaskDecl( Uint idx, const VeriTaskDecl *copy )
      :  VeriDecl( idx, copy )
      , _task_name( copy->_task_name )
      , _is_auto( copy->_is_auto )
      , _task_port( NULL )
      , _item_decl( NULL )
      , _stmt( NULL )
      , _act_port_num( 0 )
    {}

  private:
    String    _task_name;
    int       _is_auto;
    VeriNode *_task_port;
    VeriNode *_item_decl;
    VeriNode *_stmt;

    NodeList  _act_ports;
    int       _act_port_num;
};

/*
 * range cannot co-exist with integer
 */
class VeriFuncDecl : public VeriDecl
{
  typedef std::vector<int> IVec;

  public:
    VeriFuncDecl( Uint idx, int line, int col, int is_auto, int is_signed,
                  int is_int, VeriNode *range, CString& func_name,
                  VeriNode *port_list, VeriNode *item_decl, VeriNode *stmt,
                  VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_FUNC_DECL, mod )
      , _is_auto( is_auto )
      , _is_signed( is_signed )
      , _is_int( is_int )
      , _range( range )
      , _func_name( func_name )
      , _port_list( port_list )
      , _item_decl( item_decl )
      , _stmt( stmt )
      , _ret( NULL )
      , _act_port_num( 0 )
    {}

    virtual ~VeriFuncDecl() { clear(); }

    // accessors
    void set_type_name(const std::string& name) { _type_name=name; }
    const std::string& type_name() const {return _type_name;}
    void set_type_expression(VeriNode* value) {_type_expression=value;if(value)value->set_father(this);}
    VeriVar* resolved_type() const { return _resolved_type; }
    CString&  func_name( void ) { return _func_name; }
    void set_method_name(const std::string& name) {_func_name=name;}
    void adopt_extern_body(VeriFuncDecl* definition);
    int       is_auto  ( void ) { return dpi_import()?IS_TRUE:_is_auto;   }
    int       is_signed( void ) { return _is_signed; }
    // Legacy is_int accessor keeps its boolean meaning. The stored result
    // kind is IS_FALSE packed, IS_TRUE integer, 2 time and survives AST cloning.
    int       is_int   ( void ) { return _is_int==IS_TRUE?IS_TRUE:IS_FALSE; }
    bool      is_void() const { return _is_int==-1; }
    int       result_type( void ) const;
    int       integral_result( void ) const { return veri_integral_atom(result_type()); }

    VeriNode *range    ( void ) { return _range;     }
    VeriNode *port_list( void ) { return _port_list; }
    VeriNode *item_decl( void ) { return _item_decl; }
    VeriNode *stmt     ( void ) { return _stmt; }
    VeriFunc *ret_value( void ) { return _ret; }
    bool dpi_packed_result() const {return _range!=nullptr;}

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    virtual int  search_for_symbol( NodeVec& seq, String& help_info );

  protected:
    int reg_func_symbol( void );

    int push_ports( NodeVec& mstack );

    int get_call_exp( void );
    int prep_ports_for_check_type( void );
    int check_type_ref( VeriExp *exp, VeriNode *port, int no_assign );
    
    int push_contents( NodeVec& mstack );

    int collect_ret_value( void );
    int finish_scope( void );

  protected:
    VeriFuncDecl( Uint idx, const VeriFuncDecl *copy )
      :  VeriDecl( idx, copy )
      , _type_name(copy->_type_name)
      , _is_auto( copy->_is_auto )
      , _is_signed( copy->_is_signed )
      , _is_int( copy->_is_int )
      , _range( NULL )
      , _func_name( copy->_func_name )
      , _port_list( NULL )
      , _item_decl( NULL )
      , _stmt( NULL )
      , _ret( NULL )
      , _act_port_num( 0 )
    {}

  private:
    VeriNode* _type_expression=nullptr;
    std::string _type_name;
    VeriVar* _resolved_type=nullptr; // Lexical binding, resolved again in each clone.
    int       _is_auto;
    int       _is_signed;
    int       _is_int;
    VeriNode *_range;
    String    _func_name;
    VeriNode *_port_list;
    VeriNode *_item_decl;
    VeriNode *_stmt;

    VeriFunc *_ret;

    NodeList  _act_ports;
    int       _act_port_num;
};

class VeriVarDecl : public VeriDecl
{
  public:
    VeriVarDecl( Uint idx, int line, int col, short inout, short net_type,
                 short is_signed, short vector_scalar, VeriNode *drive,
                 VeriNode *range, VeriNode *delay, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_VAR, mod )
      , _inout( inout )
      , _net_type( net_type )
      , _is_signed( is_signed )
      , _vec_scalar( vector_scalar )
      , _drive( drive )
      , _range( range )
      , _delay( delay )
    {}

    virtual ~VeriVarDecl() { clear(); }

    // accessors
    short inout        ( void ) { return _inout; }
    short net_type     ( void ) { return _net_type; }
    short is_signed    ( void ) { return _is_signed; }
    short vector_scalar( void ) { return _vec_scalar; }
    VeriNode* drive( void ) { return _drive; }
    VeriNode* range( void ) { return _range; }
    VeriNode* delay( void ) { return _delay; }
    NodeList& vars( void ) { return _vars; }
    bool interface_port() const { return !_interface_type.empty(); }
    const std::string& interface_type() const { return _interface_type; }
    const std::string& interface_modport() const { return _interface_modport; }
    void set_interface_port(const std::string& type,const std::string& view) { _interface_type=type;_interface_modport=view; }
    bool is_typedef() const { return _is_typedef; }
    bool forward_class() const { return _forward_class; }
    void set_forward_class() { _forward_class=true; }
    void bind_forward_class(VeriSeqBlock* definition) { _forward_definition=definition; }
    void bind_forward_alias(VeriVarDecl* definition) {_forward_alias=definition;}
    void set_completes_forward_alias(bool value) {_completes_forward_alias=value;}
    bool type_parameter() const {return _type_parameter;}
    void set_type_parameter() {_type_parameter=true;}
    void set_type_expression(VeriNode* expression) {_type_expression=expression;if(expression)expression->set_father(this);}
    void set_type_override(VeriVar* type) {_type_override=type;}
    bool is_enum() const { return !_enum_members.empty(); }
    bool is_aggregate() const { return _aggregate_kind!=0; }
    int aggregate_kind() const { return _aggregate_kind; }
    void set_aggregate(int kind) { _aggregate_kind=kind; }
    void append_packed_member(VeriNode* node) { _packed_members.push_back(node);node->set_father(this); }
    void set_packed_field(bool unpacked=false) { _packed_field=true; _unpacked_field=unpacked; }
    NodeList& enum_members() { return _enum_members; }
    void append_enum_member(VeriNode* member) { _enum_members.push_back(member); member->set_father(this); }
    bool named_type() const { return !_type_name.empty(); }
    VeriVar* resolved_type() const { return _resolved_type; }
    void set_typedef() { _is_typedef=true; }
    void set_type_name(const std::string& name) { _type_name=name; }


    // Foreach's implicit index type is determined after its array is bound.
    void infer_foreach_index(bool text,bool unsigned_key=false,VeriVar* key=nullptr);
    // mutators
    void append_var( VeriNode *node ) { _vars.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int    check_last_child_validation( void );

  protected:
    VeriVar * reg_var_symbol( int line, int col, CString& name,
                              short drive_from, short drive_to,
                              int dstart, int dend,
                              IList& range_from, IList& range_to,
                              VeriNode *var, VeriNum **init, int total_cnt );

    int push_children( NodeVec& mstack );

    int declare_var_symbols( VeriNode* declaration = nullptr );
    void push_variable(NodeVec& mstack,VeriNode* node);
    bool sequential_variables() const { return !is_aggregate()&&!is_enum()&&!_is_typedef; }
    int process_enum_members(NodeVec& mstack);
    std::vector<VeriPackedField> packed_layout();
    int do_nothing( void );

  protected:
    VeriVarDecl( Uint idx, const VeriVarDecl *copy )
      :  VeriDecl( idx, copy )
      , _interface_type(copy->_interface_type)
      , _interface_modport(copy->_interface_modport)
      , _is_typedef(copy->_is_typedef)
      , _forward_class(copy->_forward_class)
      , _type_parameter(copy->_type_parameter)
      , _aggregate_kind(copy->_aggregate_kind)
      , _packed_field(copy->_packed_field)
      , _unpacked_field(copy->_unpacked_field)
      , _type_name(copy->_type_name)
      , _inout( copy->_inout )
      , _net_type( copy->_net_type )
      , _is_signed( copy->_is_signed )
      , _vec_scalar( copy->_vec_scalar )
      , _drive( NULL )
      , _range( NULL )
      , _delay( NULL )
    {}

  private:
    std::string _interface_type, _interface_modport;
    bool _is_typedef=false;
    bool _forward_class=false;
    bool _type_parameter=false;
    VeriNode* _type_expression=nullptr;
    VeriVar* _type_override=nullptr; // Semantic actual, never copied into syntax clones.
    VeriSeqBlock* _forward_definition=nullptr; // Rebound in each cloned lexical list.
    VeriVarDecl* _forward_alias=nullptr; // Rebound with the lexical list.
    bool _completes_forward_alias=false;
    int _aggregate_kind=0;
    bool _packed_field=false, _unpacked_field=false;
    NodeList _packed_members;
    std::string _type_name;
    VeriVar* _resolved_type=nullptr; // Rebound per scope/instance, never cloned.
    VeriVar* _declared_type=nullptr;
    NodeList _enum_members;
    NodeList::iterator _enum_next;
    VeriNode* _enum_active=nullptr;
    VeriNum* _enum_previous=nullptr;
    std::set<std::string> _enum_values;
    short     _inout;
    short     _net_type;
    short     _is_signed;
    short     _vec_scalar;
    VeriNode *_drive;
    VeriNode *_range;
    VeriNode *_delay;
    NodeList  _vars;
    NodeList::iterator _next_variable;
};

class VeriParamDecl : public VeriDecl
{
  public:
    VeriParamDecl( Uint idx, int line, int col, short is_signed, short is_int,
                   short is_local, VeriNode *range, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_PARAM, mod )
      , _is_signed( is_signed )
      , _is_int( is_int )
      , _is_local( is_local )
      , _range( range )
    {}

    virtual ~VeriParamDecl() { clear(); }

    // accessors
    void set_type_name(const std::string& name) { _type_name=name; }
    const std::string& type_name() const { return _type_name; }
    void set_class_argument(const std::string& name,VeriExp* value) {_class_arguments[name]=value;}
    VeriVar* resolved_type() const { return _resolved_type; }
    short is_signed( void ) { return _is_signed; }
    short is_local ( void ) { return _is_local; }
    short is_int   ( void ) { return _is_int; }
    int data_type() const;
    bool typed() const { return data_type()!=vvNONE; }
    VeriNode* range( void ) { return _range; }
    NodeList& vars ( void ) { return _vars; }

    // mutators
    void append_var( VeriNode *node ) { _vars.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int    check_last_child_validation( void );

  protected:
    VeriParam * reg_param_symbol( int line, int col, VeriNode *decl,
                                  CString& name, int dstart, int dend,
                                  VeriNum  *init );

    int push_children( NodeVec& mstack );

    int declare_param_symbols( void );
    VeriNum *override_value( VeriNode *assignment );
    VeriExp *override_expression( VeriNode *assignment );
    int do_nothing( void );

  protected:
    VeriParamDecl( Uint idx, const VeriParamDecl *copy )
      :  VeriDecl( idx, copy )
      , _type_name(copy->_type_name)
      , _is_signed( copy->_is_signed )
      , _is_int( copy->_is_int )
      , _is_local( copy->_is_local )
      , _range( NULL )
    {}

  private:
    std::map<std::string,VeriExp*> _class_arguments;
    std::string _type_name;
    VeriVar* _resolved_type=nullptr; // Lexical binding, resolved again in each clone.
    short     _is_signed;
    short     _is_int;
    short     _is_local;
    VeriNode *_range;
    NodeList  _vars;
    NodeList::iterator _next_param;
    VeriNode *_active_param = NULL;
};

class VeriIntDecl : public VeriDecl
{
  public:
    VeriIntDecl( Uint idx, int line, int col, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_INT, mod )
    {}

    virtual ~VeriIntDecl() { clear(); }

    // accessors
    NodeList& vars ( void ) { return _vars; }

    // mutators
    void append_var( VeriNode *node ) { _vars.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int    check_last_child_validation( void );

  protected:
    VeriInt * reg_int_symbol( int line, int col, VeriNode *decl,
                              CString& name, IList& range_from,
                              IList& range_to, VeriNum **init,
                              int total_cnt );

    int push_children( NodeVec& mstack );

    int declare_int_symbols( VeriNode *declaration );
    int do_nothing( void );

  protected:
    VeriIntDecl( Uint idx, const VeriIntDecl *copy )
      :  VeriDecl( idx, copy )
    {}

  private:
    NodeList  _vars;
    NodeList::iterator _next_variable;
};

class VeriGenVarDecl : public VeriDecl
{
  public:
    VeriGenVarDecl( Uint idx, int line, int col, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_GENVAR, mod )
    {}

    virtual ~VeriGenVarDecl() { clear(); }

    // accessors
    NodeList& vars ( void ) { return _vars; }

    // mutators
    void append_var( VeriNode *node ) { _vars.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int    check_last_child_validation( void );

  protected:
    VeriGenVar * reg_genvar_symbol( int line, int col, VeriNode *decl,
                                    CString& name, VeriNum *init );

    int push_children( NodeVec& mstack );

    int declare_genvar_symbols( void );
    int do_nothing( void );

  protected:
    VeriGenVarDecl( Uint idx, const VeriGenVarDecl *copy )
      :  VeriDecl( idx, copy )
    {}

  private:
    NodeList  _vars;
};

class VeriParamDeclList : public VeriDecl
{
  public:
    VeriParamDeclList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_PARAM_DECL_LIST, mod )
    {}

    virtual ~VeriParamDeclList() { clear(); }

    // accessors
    NodeList & param_list( void ) { return _param_list; }

    // mutators
    void append_param( VeriNode * node ) { _param_list.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriParamDeclList( Uint idx, const VeriParamDeclList *copy )
      :  VeriDecl( idx, copy )
    {}

  private:
    NodeList _param_list;
};

class VeriPortDeclList : public VeriDecl
{
  public:
    VeriPortDeclList( Uint idx, int line, int col, VeriMod *mod )
      :  VeriDecl( idx, line, col, vsDECL_PORT_DECL_LIST, mod )
    {}

    virtual ~VeriPortDeclList() { clear(); }

    // accessors
    NodeList & port_list( void ) { return _port_list; }

    // mutators
    void append_port( VeriNode * node ) { _port_list.push_back( node ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int check_last_child_validation( void );

  protected:
    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriPortDeclList( Uint idx, const VeriPortDeclList *copy )
      :  VeriDecl( idx, copy )
    {}

  private:
    NodeList _port_list;
};

};
#endif // PARSER_VERILOG_VERI_DECL_HPP_
