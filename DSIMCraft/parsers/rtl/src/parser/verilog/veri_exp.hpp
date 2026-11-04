/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_node.hpp
 * Summary  : verilog syntax analyzer true node class : expression
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_EXP_HPP_
#define PARSER_VERILOG_VERI_EXP_HPP_

#include "general_err.hpp"
#include "veri_node.hpp"

#include <string>
#include <list>
#include <cstring>
#include <memory>
#include <vector>
#include <utility>
#include <stdexcept>

namespace rtl
{

bool veri_string_value(VeriNode*);
bool veri_dynamic_string_value(VeriNode*);
bool veri_chandle_value(VeriNode*);
int veri_real_width(VeriNode*);
// Static type query: never lower or execute the operand as a runtime value.
std::string veri_type_name(VeriNode*);

class VeriNum;
class VeriVar;
class VeriSeqBlock;
class VeriPrimaryExp;
class VeriCallerExp;
class VeriMemberExp;
class VeriClocking;
VeriMemberExp* veri_bind_interface_call(VeriMemberExp* source,VeriMod* instance);
VeriMemberExp* veri_bind_class_call(VeriNode* source,VeriSeqBlock* owner,const std::string& name,VeriNode* arguments,VeriNode* prototype=nullptr);
class VeriBinaryExp;
struct VeriPackedField;
struct VeriVirtualInterface;

/*
 * class VeriExp :
 *     Verilog syntax analyzer true node : Expression
 */
class VeriExp : public VeriNode
{
  public:
    VeriExp( Uint idx, int exp_type, int line, int col,
             VeriMod *mod )
      :  VeriNode( idx, vtEXP, exp_type, line, col, mod )
      , _calc_value( NULL )
      , _is_signed( IS_FALSE )
    {}

    virtual ~VeriExp() {};

    // accessors
    VeriNum * calc_value( void ) { return _calc_value; }
    short is_signed( void ) { return _is_signed; }

    // mutators
    void set_calc_value( VeriNum *result ) { _calc_value = result; }
    void set_signed( short is_signed ) { _is_signed = is_signed; }

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
    VeriExp( Uint idx, const VeriExp *exp_copy )
      :  VeriNode( idx, exp_copy )
      , _calc_value( NULL )
      , _is_signed( exp_copy->_is_signed )
    {}

    int check_primary_not_other( VeriPrimaryExp *pexp );

  private:
    VeriNum *_calc_value;
    short    _is_signed;
};

// Owned type syntax, including nested parameterized class applications.
class VeriTypeExp : public VeriExp {
 public:
  VeriTypeExp(Uint id,int line,int col,VeriMod* mod,const std::string& name,int builtin,int sign,VeriNode* range,VeriNode* arguments)
   :VeriExp(id,veEXP_TYPE,line,col,mod),_name(name),_builtin(builtin),_sign(sign),_range(range),_arguments(arguments) {}
  const std::string& name() const {return _name;}
  void set_virtual_interface(const std::string& view) {_virtual_interface=true;_interface_view=view;}
  std::string syntax_key() const {return _name+":"+std::to_string(_builtin)+":"+std::to_string(_sign)+(_virtual_interface?":virtual:"+_interface_view:"");}
  VeriVar* resolve(VeriSymbolTable* context);
  VeriVar* resolved_type() const {return _resolved;}
  void clean_up() override {set_pstatus(vSTART_S);set_calc_value(nullptr);_resolved=nullptr;}
  int check_child_validation() override {return OK;}
  int push_dot_children(NodeQueue&,IQueue&) override;
  int pretty_dot_label(Ofstream&,int) override {return OK;}
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec&) override;
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  std::string _name,_interface_view;
  bool _virtual_interface=false;
  int _builtin,_sign;
  VeriNode* _range;
  VeriNode* _arguments;
  VeriVar* _resolved=nullptr;
};
std::shared_ptr<VeriVirtualInterface> veri_virtual_interface(VeriNode* node);
VeriVar* veri_resolve_type(VeriSymbolTable* context,const std::string& name,VeriNode* arguments=nullptr);
VeriNode* veri_clone_syntax(VeriNode* node);
void veri_bind_semantic(VeriNode* node,VeriSymbolTable* context);
void veri_declare_implicit_wire(VeriNode* node,VeriSymbolTable* context);

// A quantified constraint, with its own lexical indices and owned syntax.
// It is not a procedural loop and never allocates scheduler instructions.
class VeriConstraintForeach : public VeriExp {
 public:
  VeriConstraintForeach(Uint id,int line,int col,VeriMod* mod,VeriNode* array,
      VeriNode* declarations,VeriNode* body,const std::vector<std::string>& names)
   :VeriExp(id,veEXP_CONSTRAINT_FOREACH,line,col,mod),_array(array),
    _declarations(declarations),_body(body),_names(names) {
    for(auto* child:{array,declarations,body})if(child)child->set_father(this);
  }
  VeriNode* array() const {return _array;}
  VeriNode* body() const {return _body;}
  const std::vector<std::string>& names() const {return _names;}
  VeriSymbolTable* index_scope() const {return _index_scope;}
  void clean_up() override {_index_scope=nullptr;set_pstatus(vSTART_S);set_calc_value(nullptr);}
  int check_child_validation() override {return OK;}
  int pretty_dot_label(Ofstream&,int) override {return OK;}
  int push_dot_children(NodeQueue&,IQueue&) override;
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec&) override;
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  VeriNode *_array,*_declarations,*_body;
  std::vector<std::string> _names;
  VeriSymbolTable* _index_scope=nullptr;
};

std::unique_ptr<VeriNum> veri_constant_function(VeriCallerExp* call);

// Context-aware constant evaluation shared by declarations and explicit casts.
std::unique_ptr<VeriNum> veri_constant_value(VeriExp* expression,int context,int sign_context=-1);
std::unique_ptr<VeriNum> veri_inside_constant(VeriBinaryExp* expression);
struct VeriArrayShape {
  std::vector<std::pair<int,int> > dimensions;
  int unpacked=0;
  bool unbound=false;
};
std::vector<VeriNode*> veri_system_arguments(VeriNode* expression);
VeriArrayShape veri_array_shape(VeriNode* expression);
int veri_array_query(int op,const VeriArrayShape& shape,int dimension,bool& valid);
// Array methods keep the member AST and existing clone/cleanup ownership.
int veri_array_reduction_name(const std::string& name);
int veri_array_reduction(VeriNode* expression);
bool veri_array_locator(VeriNode* expression);
bool veri_array_ordering(VeriNode* expression);
VeriNode* veri_array_element_symbol(VeriNode* object);
bool veri_queue_slice(VeriNode* expression);
// Scalar event identity metadata, including instance and hierarchical members.
VeriNode* veri_event_symbol(VeriNode* expression);
int veri_array_element_width(VeriNode* object);
VeriVar* veri_associative_key_type(VeriNode* symbol,unsigned axis=0);
int veri_array_container_kind(VeriNode* symbol,unsigned axis=0);
bool veri_streaming(VeriNode* expression);
int veri_stream_slice(VeriNode* expression);
int veri_bit_width(VeriNode* expression);
bool veri_elaboration_constant(VeriNode* expression);
VeriVar* veri_enum_type(VeriNode* expression);
VeriVar* veri_declared_type(VeriNode* node);
VeriVar* veri_aggregate_type(VeriNode* expression);
VeriSeqBlock* veri_class_type(VeriNode* expression);

class VeriDummyPort : public VeriExp
{
  public:
    VeriDummyPort( Uint idx, int line, int col, VeriMod *mod )
      :  VeriExp( idx, veEXP_DUMMY_PORT, line, col, mod )
    {}

    virtual ~VeriDummyPort( ) { clear(); }

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
    VeriDummyPort( Uint idx, const VeriDummyPort *copy )
      :  VeriExp( idx, copy )
    {}

};

/*
 * class VeriPortRefExp :
 *     Verilog syntax analyzer true node : Port-Reference-Expression
 */
class VeriPortRefExp : public VeriExp
{
  public:
    VeriPortRefExp( Uint idx, int line, int col, CString& port_ref,
             VeriMod *mod )
      :  VeriExp( idx, veEXP_PORT_REF, line, col, mod )
      , _port_ref( port_ref )
    {}

    virtual ~VeriPortRefExp( ) { clear(); }

    // accessors
    CString& port_ref( void ) const { return _port_ref; }

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
    VeriPortRefExp( Uint idx, const VeriPortRefExp *copy )
      :  VeriExp( idx, copy )
      , _port_ref( copy->_port_ref )
    {}

  private:
    String  _port_ref;
};

/*
 * class VeriNamedParamExp :
 *     Verilog syntax analyzer true node : Named-Parameter-Expression
 */
class VeriNamedParamExp : public VeriExp
{
  public:
    VeriNamedParamExp( Uint idx, int line, int col,
                       CString& ref, VeriNode *port_exp, VeriMod *mod )
      :  VeriExp( idx, veEXP_NAMED_PARAM, line, col, mod )
      , _ref( ref )
      , _port_ref( NULL )
      , _port_exp( port_exp )
    {}

    virtual ~VeriNamedParamExp( ) { clear(); }

    // accessors
    CString  & ref( void ) const { return _ref; }
    VeriNode * port_ref( void ) { return _port_ref; }
    VeriNode * port_exp( void ) { return _port_exp; }
    void set_port_ref( VeriNode *node ) { _port_ref = node; }
    bool implicit() const { return _implicit; }
    void set_implicit() { _implicit=true; }

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
    int do_nothing( void );

  protected:
    VeriNamedParamExp( Uint idx, const VeriNamedParamExp *copy )
      :  VeriExp( idx, copy )
      , _ref( copy->_ref )
      , _implicit(copy->_implicit)
      , _port_ref( NULL )
      , _port_exp( NULL )
    {}

  private:
    String    _ref;
    bool _implicit=false;
    VeriNode *_port_ref;
    VeriNode *_port_exp;
};

/*
 * class VeriPrimaryExp :
 *     Verilog syntax analyzer true node : Primary-expression
 *   Primary-expression has one expression child, no operator contained
 */
class VeriPrimaryExp : public VeriExp
{
  typedef std::vector<int> IVec;

  public:
    VeriPrimaryExp( Uint idx, int line, int col,
                    CString& str, int primary_type, VeriMod *mod )
      : VeriExp( idx, veEXP_PRI, line, col, mod )
      , _str( str  )
      , _var( NULL )
      , _pri_type( primary_type )
    {}

    virtual ~VeriPrimaryExp() { clear(); }

    // accessors
    CString&   str( void ) const { return _str; }
    int        pri_type( void ) const { return _pri_type; }
    bool time_literal() const { return _time_literal; }
    void set_time_literal() { _time_literal=true; }
    VeriNode * var( void ) { return _var; }

    // mutators
    void set_var( VeriNode *var ) { _var = var; }

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
    int process_id( String& help_info );

  protected:
    VeriPrimaryExp( Uint idx, const VeriPrimaryExp *copy )
      :  VeriExp( idx, copy )
      , _str( copy->_str )
      , _var( NULL )
      , _pri_type( copy->_pri_type )
      , _time_literal(copy->_time_literal)
    {}

  private:
    String    _str;
    bool _time_literal=false;
    VeriNode *_var;
    int       _pri_type;
};

/*
 * class VeriUnaryExp :
 *     Verilog syntax analyzer true node : Unary-expression
 *   Unary-expression has one expression child, one operator child
 */
class VeriUnaryExp : public VeriExp
{
  public:
    VeriUnaryExp( Uint idx, int line, int col, int op, VeriNode *exp,
             VeriMod *mod )
      : VeriExp( idx, veEXP_UNA, line, col, mod )
      , _op( op )
      , _exp( exp )
    {}

    virtual ~VeriUnaryExp() { clear(); }

    // accessors
    VeriNode * exp_child( void ) { return _exp; }
    int op( void ) const { return _op;  }

    // mutators
    void set_exp_child( VeriNode *exp ) { _exp = exp; }
    void set_op ( int op  ) { _op  = op;  }

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
    int process_unary_op( void );

  protected:
    VeriUnaryExp( Uint idx, const VeriUnaryExp *copy )
      :  VeriExp( idx, copy )
      , _op( copy->_op )
      , _exp( NULL )
    {}

  private:
    int        _op;
    VeriNode  *_exp;
};

/*
 * class VeriEventExp :
 *     Verilog syntax analyzer true node : Event-expression
 *   Event-expression has one expression child, one event-edge type
 *     1, event-edge could be pos-edge, neg-edge, or none
 *     2, optional iff condition is evaluated only on an event
 */
class VeriEventExp : public VeriExp
{
  public:
    VeriEventExp( Uint idx, int line, int col, int etype, VeriNode *exp,
             VeriMod *mod )
      : VeriExp( idx, veEXP_EVENT, line, col, mod )
      , _etype( etype )
      , _exp( exp )
      , _condition( NULL )
    {}

    virtual ~VeriEventExp() { clear(); }

    // accessors
    VeriNode * exp_child( void ) { return _exp; }
    int etype( void ) { return _etype;  }
    VeriNode * condition( void ) { return _condition; }

    // mutators
    void set_exp_child( VeriNode *exp ) { _exp = exp; }
    void set_etype ( int etype  ) { _etype  = etype;  }
    void set_condition( VeriNode *condition ) { _condition = condition; }

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
    int check_sensitivity_list( void );

  protected:
    VeriEventExp( Uint idx, const VeriEventExp *copy )
      :  VeriExp( idx, copy )
      , _etype( copy->_etype )
      , _exp( NULL )
      , _condition( NULL )
    {}

  private:
    int        _etype;
    VeriNode  *_exp;
    VeriNode  *_condition;
};


/*
 * class VeriArrayExp :
 *     Verilog syntax analyzer true node : Array-expression
 *   Array-expression has two expression children :
 *       1, primary->var
 *       2, range list ( making array-expression recursive )
 */
class VeriMemberExp : public VeriExp {
 public:
  VeriMemberExp(Uint idx,int line,int col,VeriNode* object,const std::string& member,VeriMod* mod)
    :VeriExp(idx,veEXP_MEMBER,line,col,mod),_object(object),_member(member){}
  VeriNode* object() const {return _object;}
  const VeriPackedField* field() const {return _field;}
  const std::string& member() const {return _member;}
  bool called() const {return _called;}
  bool scope_reference() const {return _scope_reference;}
  void set_scope_reference() {_scope_reference=true;}
  void set_call(VeriNode* args) { _called=true;_arguments=args;if(args)args->set_father(this); }
  VeriNode* arguments() const {return _arguments;}
  VeriNode* with_expression() const {return _with;}
  void set_with(VeriNode* expression) {if(_with)throw std::runtime_error("duplicate array with clause");_with=expression;expression->set_father(this);}
  void set_with_constraint(VeriNode* expression) {set_with(expression);_with_constraint=true;}
  bool with_constraint() const {return _with_constraint;}
  bool scope_randomize() const {return _scope_reference&&_object->detail_type()==veEXP_TYPE&&static_cast<VeriTypeExp*>(_object)->name()=="std"&&_member=="randomize";}
  bool process_builtin() const;
  bool ipc_builtin() const;
  bool coverage_builtin() const;
  int coverage_point() const {return _coverage_point;}
  bool ipc_value_builtin() const;
  bool randomize_builtin() const {return _member=="randomize"&&(scope_randomize()||_class_owner);}
  bool random_control_builtin() const {return _class_owner&&(_member=="srandom"||_member=="rand_mode"||_member=="constraint_mode");}
  bool random_value_builtin() const {return randomize_builtin()||(random_control_builtin()&&_member!="srandom"&&!_arguments);}
  VeriVar* iterator() const {return _iterator;}
  VeriVar* array_result() const {return _array_result;}
  const std::string& iterator_name() const {return _iterator_name;}
  VeriVar* method_type() const {return _method_type;}
  bool event_query() const {return _event_query;}
  VeriNode* hierarchical_symbol() const {return _hierarchical_symbol;}
  VeriClocking* clocking_owner() const {return _clocking_owner;}
  VeriNode* clocking_source() const {return _clocking_source;}
  VeriNode* hive() const {return _hive;}
  VeriSeqBlock* class_owner() const {return _class_owner;}
  bool super_reference() const {return _object->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(_object)->str()=="super";}
  VeriNode* class_member() const {return _class_member;}
  void bind_class_call(VeriSeqBlock* owner,VeriNode* member,VeriNode* args) {_class_owner=owner;_class_member=member;_arguments=args;_called=true;}
  VeriNode*& bound_hive() {return _hive;}
  VeriMod* call_instance() const {return _call_instance;}
  void bind_interface_call(VeriMod* instance,VeriNode* args,VeriNode* prototype) {_call_instance=instance;_arguments=args;_interface_prototype=prototype;_called=true;_interface_reference=true;}
  VeriNode* interface_prototype() const {return _interface_prototype;}
  bool class_argument_prototype() const {return _argument_prototype!=nullptr;}
  VeriNode* argument_prototype() const {return _argument_prototype?_argument_prototype:_interface_prototype;}
  void set_argument_prototype(VeriNode* declaration) {_argument_prototype=declaration;}
  bool interface_reference() const {return _interface_reference;}
  bool interface_writable() const {return _interface_writable;}
  VeriMod* interface_view_instance() const {return _interface_view_instance;}
  void clean_up() override;
  int check_child_validation() override {return OK;}
  int push_dot_children(NodeQueue&,IQueue&) override;
  int pretty_dot_label(Ofstream&,int) override;
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec& stack) override {stack.push_back(_object);if(_arguments)stack.push_back(_arguments);if(_with)stack.push_back(_with);return OK;}
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  VeriNode* _object;
  std::string _member;
  const VeriPackedField* _field=nullptr;
  bool _called=false;
  bool _scope_reference=false;
  VeriNode* _arguments=nullptr;
  VeriVar* _method_type=nullptr;
  bool _event_query=false;
  VeriNode* _hierarchical_symbol=nullptr;
  VeriClocking* _clocking_owner=nullptr;
  VeriNode* _clocking_source=nullptr;
  VeriNode* _hive=nullptr; // Semantic clone/binding, excluded from syntax cloning.
  VeriSeqBlock* _class_owner=nullptr;
  int _coverage_point=-1;
  VeriNode* _class_member=nullptr;
  VeriMod* _call_instance=nullptr;
  VeriNode* _argument_prototype=nullptr;
  VeriNode* _interface_prototype=nullptr; // Canonical actual-interface signature, not owned.
  bool _interface_reference=false, _interface_writable=false;
  VeriMod* _interface_view_instance=nullptr;
  VeriNode* _with=nullptr;
  bool _with_constraint=false;
  VeriVar* _iterator=nullptr;
  VeriVar* _array_result=nullptr;
  std::string _iterator_name="item";
};

class VeriArrayExp : public VeriExp
{
  typedef std::vector<int> IVec;

  public:
    VeriArrayExp( Uint idx, int line, int col, VeriNode *id, VeriMod *mod )
      : VeriExp( idx, veEXP_ARRAY, line, col, mod )
      , _id( id )
      , _name("")
      , _not_calc(IS_TRUE)
    {}
  
    virtual ~VeriArrayExp() { clear(); }
  
    // accessors
    VeriNode * id   ( void ) { return _id;    }
    NodeList & range( void ) { return _range; }

    CString  & name( void ) { return _name;  }
    int        range_depth( void ) const { return _range.size(); }
    int        not_calc( void ) const { return _not_calc; }
    int        is_whole( void ) const { return _is_whole; }
    int        dstart  ( void ) const { return _dstart;   }
    int        dend    ( void ) const { return _dend;     }
    const IVec & dimen ( void ) const { return _dimen;    }

    IList    & range_from( void ) { return _range_from; }
    IList    & range_to  ( void ) { return _range_to;   }
  
    // mutators
    void append_range( VeriNode *range ) { _range.push_back( range ); }
  
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
    int calc_range( void );
    int type_deduction( String& help_info );

  protected:
    VeriArrayExp( Uint idx, const VeriArrayExp *copy )
      :  VeriExp( idx, copy )
      , _id( NULL )
      , _name( copy->_name )
      , _not_calc(IS_TRUE)
    {}

  private:
    VeriNode  *_id;
    String     _name;
    NodeList   _range;
    IList      _range_from;
    IList      _range_to;

    int        _not_calc;
    int        _is_whole;
    int        _dstart;
    int        _dend;
    IVec       _dimen;
};


/*
 * class VeriCallerExp :
 *     Verilog syntax analyzer true node : Caller-expression
 *   Caller-expression has two expression children :
 *       1, caller : array identifier expression
 *       2, arg    : augument list ( must be MultiExp )
 */
class VeriCallerExp : public VeriExp
{
  public:
    VeriCallerExp( Uint idx, int line, int col, VeriNode *caller, VeriNode *arg,
             VeriMod *mod )
      : VeriExp( idx, veEXP_CALLER, line, col, mod )
      , _caller_name( "" )
      , _caller( caller )
      , _arg( arg )
      , _call_type( NONE )
      , _hive( NULL )
    {}
  
    virtual ~VeriCallerExp() { clear(); }
  
    // accessors
    VeriNode * caller( void ) { return _caller; }
    VeriNode * arg   ( void ) { return _arg; }
    VeriNode * hive  ( void ) { return _hive; }
    int call_type( void ) { return _call_type; }
  
    // mutators
    void set_caller( VeriNode *exp ) { _caller = exp; }
    void set_arg   ( VeriNode *exp ) { _arg    = exp; }
    void set_call_type( int type   ) { _call_type = type; }
  
    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );
    
    int check_func_call_child_validation( void );
  
  protected:
    int push_children( NodeVec& mstack );
    int unfolding( NodeVec& mstack, String& help_info );
    int get_ret_value( void );

  protected:
    VeriCallerExp( Uint idx, const VeriCallerExp *copy )
      :  VeriExp( idx, copy )
      , _caller_name( copy->_caller_name )
      , _caller( NULL )
      , _arg( NULL )
      , _call_type( copy->_call_type )
      , _hive( NULL )
    {}

  private:
    String     _caller_name;
    VeriNode  *_caller;
    VeriNode  *_arg;
    int        _call_type;

    VeriNode  *_hive;

    NodeList   _ports;
};

/*
 * class VeriBinaryExp :
 *     Verilog syntax analyzer true node : Binary-expression
 *   Binary-expression has two expression children, one operator child
 */
class VeriBinaryExp : public VeriExp
{
  public:
    VeriBinaryExp( Uint idx, int line, int col,
                   VeriNode *left, int op, VeriNode *right,
                        VeriMod *mod )
      : VeriExp( idx, veEXP_BIN, line, col, mod )
      , _left( left )
      , _op( op )
      , _right( right )
    {}

    virtual ~VeriBinaryExp() { clear(); }

    // accessors
    VeriNode * lval( void ) { return _left; }
    int          op( void ) { return _op;   }
    VeriNode * rval( void ) { return _right; }

    // mutators
    void set_lval( VeriNode *exp ) { _left  = exp; }
    void set_op  ( int op )        { _op    = op;  }
    void set_rval( VeriNode *exp ) { _right = exp; }

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
    int process_binary_op( void );

    int push_short_cut_left( NodeVec& mstack );
    int process_short_cut_left( NodeVec& mstack );

  protected:
    VeriBinaryExp( Uint idx, const VeriBinaryExp *copy )
      :  VeriExp( idx, copy )
      , _left( NULL )
      , _op( copy->_op )
      , _right( NULL )
    {}

    int check_child_validation( VeriNode *child );

  private:
    VeriNode *_left;
    int       _op;
    VeriNode *_right;
};

/*
 * class VeriAssignExp :
 *     Verilog syntax analyzer true node : Assign-expression
 *   Assign-expression has two expression children
 *     1, left-value should be primary->var
 *     2, right-value should be expression
 */
class VeriAssignExp : public VeriExp
{
  typedef std::vector<int> IVec;

  public:
    VeriAssignExp( Uint idx, int line, int col,
                   VeriNode *lval, VeriNode *rval,
                        VeriMod *mod )
      : VeriExp( idx, veEXP_ASSIGN, line, col, mod )
      , _lval( lval )
      , _rval( rval )
    {}

    virtual ~VeriAssignExp() { clear(); }

    // accessors
    VeriNode * lval( void ) { return _lval; }
    VeriNode * rval( void ) { return _rval; }

    // mutators
    void set_lval( VeriNode *exp ) { _lval = exp; }
    void set_rval( VeriNode *exp ) { _rval = exp; }

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
    int check_child_validation( VeriNode *child );

    int push_children( NodeVec& mstack );
    int process_assign_op( void );

  protected:
    VeriAssignExp( Uint idx, const VeriAssignExp *copy )
      :  VeriExp( idx, copy )
      , _lval( NULL )
      , _rval( NULL )
    {}

  private:
    VeriNode *_lval;
    VeriNode *_rval;
};

/*
 * class VeriMultiConcatExp :
 *     Verilog syntax analyzer true node : MultiConcat-expression
 *   MultiConcat-expression has two expression children
 *     1, first expression is single constant expression
 *     2, second expression is multi-expression( concat type )
 */
class VeriMultiConcatExp : public VeriExp
{
  public:
    VeriMultiConcatExp( Uint idx, int line, int col,
                   VeriNode *exp1, VeriNode *exp2,
                        VeriMod *mod )
      : VeriExp( idx, veEXP_MCONCAT, line, col, mod )
      , _exp1( exp1 )
      , _exp2( exp2 )
    {}

    virtual ~VeriMultiConcatExp() { clear(); }

    // accessors
    VeriNode * exp1( void ) { return _exp1; }
    VeriNode * exp2( void ) { return _exp2; }

    // mutators
    void set_exp1( VeriNode *exp ) { _exp1 = exp; }
    void set_exp2( VeriNode *exp ) { _exp2 = exp; }

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
    int process_mconcat( void );

  protected:
    VeriMultiConcatExp( Uint idx, const VeriMultiConcatExp *copy )
      :  VeriExp( idx, copy )
      , _exp1( NULL )
      , _exp2( NULL )
    {}

  private:
    VeriNode *_exp1;
    VeriNode *_exp2;
};

/*
 * class VeriRangeExp :
 *     Verilog syntax analyzer true node : Range-expression
 *   Range-expression has two expression children, one operator child
 */
class VeriRangeExp : public VeriExp
{
  public:
    VeriRangeExp( Uint idx, int line, int col,
                   VeriNode *left, int rtype, VeriNode *right,
                        VeriMod *mod )
      : VeriExp( idx, veEXP_RANGE, line, col, mod )
      , _left( left )
      , _rtype( rtype )
      , _right( right )
      , _vleft( RANGE_DEFAULT )
      , _vright( RANGE_DEFAULT )
      , _not_calc( IS_TRUE )
    {}

    virtual ~VeriRangeExp() { clear(); }

    // accessors
    VeriNode * left ( void ) { return _left; }
    VeriNode * right( void ) { return _right; }

    int        rtype( void ) const { return _rtype; }
    VeriVar* associative_key_type() const {return _associative_key_type;}

    int   range_from( void ) const { return _packed_next?_packed_width-1:_vleft; }
    int   range_to  ( void ) const { return _packed_next?0:_vright;}
    int   not_calc  ( void ) const { return _not_calc; }
    VeriRangeExp* packed_next() const { return _packed_next; }
    void append_packed(VeriRangeExp* next) {
      auto* last=this;while(last->_packed_next)last=last->_packed_next;
      last->_packed_next=next;next->set_father(last);
    }
    std::vector<std::pair<int,int>> packed_dimensions() const {
      std::vector<std::pair<int,int>> result;
      for(auto* item=this;item;item=item->_packed_next)result.push_back({item->_vleft,item->_vright});
      return result;
    }

    // mutators
    void set_left ( VeriNode *exp ) { _left  = exp;   }
    void set_rtype( int rtype     ) { _rtype = rtype; }
    void set_right( VeriNode *exp ) { _right = exp;   }

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
    int assign_range( void );

  protected:
    VeriRangeExp( Uint idx, const VeriRangeExp *copy )
      :  VeriExp( idx, copy )
      , _left( NULL )
      , _rtype( copy->_named_index_type?vrSINGLE:copy->_rtype )
      , _right( NULL )
      , _vleft( RANGE_DEFAULT )
      , _vright( RANGE_DEFAULT )
      , _not_calc( IS_TRUE )
    {}

   int check_child_validation( VeriNode *child );

  private:
    VeriNode *_left;
    int       _rtype;
    VeriVar* _associative_key_type=nullptr;
    bool _named_index_type=false;
    VeriNode *_right;
    int       _vleft;
    int       _vright;
    int       _not_calc;
    VeriRangeExp* _packed_next=nullptr;
    int _packed_width=0;
};

/*
 * class VeriMintypmaxExp :
 *     Verilog syntax analyzer true node : Mintypmax-expression
 *   Mintypmax-expression has three expression children, two operator children
 *     !, there are only 2-types of ternary expression
 *         1, mintypmax expression
 */
class VeriMintypmaxExp : public VeriExp
{
  public:
    VeriMintypmaxExp( Uint idx, int line, int col,
                      VeriNode *exp1, VeriNode *exp2, VeriNode *exp3,
                      VeriMod *mod )
      : VeriExp( idx, veEXP_MINTY, line, col, mod )
      , _not_calc( IS_TRUE )
    {
      _exp[0] = exp1;
      _exp[1] = exp2;
      _exp[2] = exp3;
      _re[0] = _re[1] = _re[2] = 0;
    }

    virtual ~VeriMintypmaxExp() { clear(); }

    // accessors
    VeriNode * exp_child1( void ) { return _exp[0]; }
    VeriNode * exp_child2( void ) { return _exp[1]; }
    VeriNode * exp_child3( void ) { return _exp[2]; }
    int re1( void ) const { return _re[0]; }
    int re2( void ) const { return _re[1]; }
    int re3( void ) const { return _re[2]; }
    int not_calc( void ) const { return _not_calc; }

    // mutators
    void set_exp_child1( VeriNode *exp ) { _exp[0] = exp; }
    void set_exp_child2( VeriNode *exp ) { _exp[1] = exp; }
    void set_exp_child3( VeriNode *exp ) { _exp[2] = exp; }

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
    int process_mintypmax( void );

  protected:
    VeriMintypmaxExp( Uint idx, const VeriMintypmaxExp *copy )
      :  VeriExp( idx, copy )
      , _not_calc( IS_TRUE )
    {
      _exp[0] = NULL;
      _exp[1] = NULL;
      _exp[2] = NULL;
      _re[0] = _re[1] = _re[2] = 0;
    }

   int check_child_validation( VeriNode *child );

  private:
    VeriNode *_exp[3];
    int       _re[3];
    int       _not_calc;
};

/*
 * class VeriQuesExp :
 *     Verilog syntax analyzer true node : Ques-expression
 *   Ques-expression has three expression children, two operator children
 *     !, there are only 2-types of ternary expression
 *         1, mintypmax expression
 */
class VeriQuesExp : public VeriExp
{
  public:
    VeriQuesExp( Uint idx, int line, int col, VeriNode *ques,
                 VeriNode *choice1, VeriNode *choice2, VeriMod *mod )
      : VeriExp( idx, veEXP_QUES, line, col, mod )
      , _ques( ques )
      , _choice1( choice1 )
      , _choice2( choice2 )
      , _choice(0)
    { }

    virtual ~VeriQuesExp() { clear(); }

    // accessors
    VeriNode * ques( void ) { return _ques; }
    VeriNode * choice1( void ) { return _choice1; }
    VeriNode * choice2( void ) { return _choice2; }

    VeriNode * choice ( void )
    {
      switch( _choice )
      {
        case 1 : return _choice1;
        case 2 : return _choice2;
        default : return NULL;
      }
    }

    // mutators
    void set_ques   ( VeriNode *exp ) { _ques = exp; }
    void set_choice1( VeriNode *exp ) { _choice1 = exp; }
    void set_choice2( VeriNode *exp ) { _choice2 = exp; }

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
    int push_condition( NodeVec& mstack );
    int choose_children( NodeVec& mstack );
    int get_answer( void );

  protected:
    VeriQuesExp( Uint idx, const VeriQuesExp *copy )
      :  VeriExp( idx, copy )
      , _ques(NULL)
      , _choice1(NULL)
      , _choice2(NULL)
      , _choice(0)
    { }

   int check_child_validation( VeriNode *child );

  private:
    VeriNode *_ques;
    VeriNode *_choice1;
    VeriNode *_choice2;
    int       _choice;
};

/*
 * class VeriMultiExp :
 *     Verilog syntax analyzer true node : Multi-expression
 *   Multi-expression has multi-exp-type, multiple-expression children
 */
class VeriMultiExp : public VeriExp
{
  public:
    VeriMultiExp( Uint idx, int mul_type, int line, int col, VeriMod *mod )
      : VeriExp( idx, veEXP_MULTI, line, col, mod )
      , _multi_type( mul_type )
      , _exp_num( 0 )
    {}

    virtual ~VeriMultiExp() { clear(); }

    // accessors
    NodeList& exp( void ) { return _exp; }
    int  multi_type( void ) const { return _multi_type; }
    int  exp_num( void ) const { return _exp_num; }
    VeriSeqBlock* object_type() const {return _object_type;}
    VeriNode* hive() const {return _object_constructor;}

    // mutators
    void set_multi_type( int type ) { _multi_type = type; }
    void append_child( VeriNode *n ) { _exp.push_back( n ); ++_exp_num; }

    int check_pure_event_multi( void );

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
    int get_answer( void );

  protected:
    VeriMultiExp( Uint idx, const VeriMultiExp *copy )
      :  VeriExp( idx, copy )
      , _multi_type( copy->_multi_type )
      , _exp_num( copy->_exp_num )
    {}

   int check_child_validation( VeriNode *child );

  private:
    int      _multi_type;
    int      _exp_num;
    VeriSeqBlock* _object_type=nullptr;
    VeriNode* _object_constructor=nullptr;
    NodeList _exp;
};

/*
 * class VeriDelayExp :
 *     Verilog syntax analyzer true node : Delay-expression
 *   Delay-expression has 2 or 3 children.
 *   Each children is Primary-expression or Mintypmax-expression
 */
class VeriDelayExp : public VeriExp
{
  public:
    VeriDelayExp( Uint idx, int line, int col, VeriNode *delay1,
                  VeriNode *delay2, VeriNode *delay3, VeriMod *mod )
      : VeriExp( idx, veEXP_DELAY, line, col, mod )
      , _delay1( delay1 )
      , _delay2( delay2 )
      , _delay3( delay3 )
      , _not_calc( IS_TRUE )
    {
      memset( _delay, 0, sizeof(int) * 9 );
    }

    VeriDelayExp( Uint idx1, Uint idx2, int line, int col, VeriMod *mod )
      : VeriExp( idx1, veEXP_DELAY, line, col, mod )
      , _delay2( NULL )
      , _delay3( NULL )
      , _not_calc( IS_TRUE )
    {
      _delay1 = new VeriPrimaryExp( idx2, line, col, "0", veNUM, mod );
      memset( _delay, 0, sizeof(int) * 9 );
    }

    virtual ~VeriDelayExp() { clear(); }

    // accessors
    VeriNode * delay1( void ) { return _delay1; }
    VeriNode * delay2( void ) { return _delay2; }
    VeriNode * delay3( void ) { return _delay3; }

    int delay_num( void ) const ;
    void delay_value( int (&delay)[9] )
    { memcpy( delay, _delay, sizeof(int) * 9 ); }

    virtual void clean_up( void );
    virtual int  check_child_validation( void );

    virtual int  push_dot_children( NodeQueue& mqueue, IQueue& iqueue );
    virtual int  pretty_dot_label( Ofstream& ofile, int depth );

    // 2nd round parse
    virtual int  process_node_2nd( NodeVec& mstack, String& help_info );
    virtual int  push_for_replacement( NodeVec& mstack );
    virtual int  replace_node( Uint idx, NodeList& node_list,
                               NodeList::iterator& inl );

    int  check_child_validation( VeriNode *child );

  protected:
    int push_children( NodeVec& mstack );
    int get_delay_val( void );
    int get_one_val( VeriExp *delay_exp, int idx );

  protected:
    VeriDelayExp( Uint idx, const VeriDelayExp *copy )
      :  VeriExp( idx, copy )
      , _delay1( NULL )
      , _delay2( NULL )
      , _delay3( NULL )
      , _not_calc( IS_TRUE )
    {
      memset( _delay, 0, sizeof(int) * 9 );
    }

  private:
    VeriNode * _delay1;
    VeriNode * _delay2;
    VeriNode * _delay3;
    int        _delay[9];
    int        _not_calc;
};

class VeriDriveExp : public VeriExp
{
  public:
    VeriDriveExp( Uint idx, int line, int col, int drive_from, int drive_to,
             VeriMod *mod )
      : VeriExp( idx, veEXP_DRIVE, line, col, mod )
      , _drive_from( drive_from )
      , _drive_to( drive_to )
    {}

    VeriDriveExp( Uint idx, int line, int col, VeriMod *mod )
      : VeriExp( idx, veEXP_DRIVE, line, col, mod )
      , _drive_from( DEFAULT_DRIVE_FROM )
      , _drive_to( DEFAULT_DRIVE_TO )
    {}

    virtual ~VeriDriveExp() { clear(); }

    // accessors
    int drive_from( void ) { return _drive_from; }
    int drive_to( void ) { return _drive_to; }

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
    VeriDriveExp( Uint idx, const VeriDriveExp *copy )
      :  VeriExp( idx, copy )
      , _drive_from( copy->_drive_from )
      , _drive_to( copy->_drive_to )
    {}

  private:
    int _drive_from;
    int _drive_to;
};

class VeriSignExp : public VeriExp
{
  public:
    VeriSignExp( Uint idx, int line, int col, VeriNode *exp,
             VeriMod *mod )
      : VeriExp( idx, veEXP_SIGN, line, col, mod )
      , _exp( exp )
    {}

    virtual ~VeriSignExp() { clear(); }

    // accessors
    VeriNode *exp( void ) { return _exp; }

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
    int process_sign( void );

  protected:
    VeriSignExp( Uint idx, const VeriSignExp *copy )
      :  VeriExp( idx, copy )
      , _exp( NULL )
    {}

  private:
    VeriNode *_exp;
};

class VeriUnsignExp : public VeriExp
{
  public:
    VeriUnsignExp( Uint idx, int line, int col, VeriNode *exp,
             VeriMod *mod )
      : VeriExp( idx, veEXP_UNSIGN, line, col, mod )
      , _exp( exp )
    {}

    virtual ~VeriUnsignExp() { clear(); }

    // accessors
    VeriNode *exp( void ) { return _exp; }

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
    int process_unsign( void );

  protected:
    VeriUnsignExp( Uint idx, const VeriUnsignExp *copy )
      :  VeriExp( idx, copy )
      , _exp( NULL )
    {}

  private:
    VeriNode *_exp;
};

};
#endif // PARSER_VERILOG_VERI_EXP_HPP_
