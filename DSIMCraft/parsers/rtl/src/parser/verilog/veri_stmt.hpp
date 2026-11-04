/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_stmt.hpp
 * Summary  : verilog syntax analyzer true node class : statement
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_STMT_HPP_
#define PARSER_VERILOG_VERI_STMT_HPP_

#include "veri_node.hpp"
#include "veri_stmt.hpp"

#include <vector>
#include <string>
#include <list>
#include <map>

namespace rtl
{
class VeriVar;
// Syntax children are owned by the parser registry and cloned in order.
// Source bindings stay in the surrounding lexical scope, never a rewritten TB.
class VeriClocking;

/*
 * class VeriStmt :
 *     Verilog syntax analyzer true node : Statement
 */
class VeriStmt : public VeriNode
{
  public:
    VeriStmt( Uint idx, int stmt_type, int func_task_flag, int line, int col,
             VeriMod *mod )
      :  VeriNode( idx, vtSTMT, stmt_type, line, col, mod )
      , _func_task_flag( func_task_flag )
    {}

    virtual ~VeriStmt( void ) {};

    // accessors
    int func_task_flag( void ) const { return _func_task_flag; }
    int is_dummy( void ) const
    {
      if( detail_type() == vsSTMT_DUMMY )
        return IS_TRUE;
      return IS_FALSE;
    }

    // mutators
    void set_func_task_flag( int flag ) { _func_task_flag = flag; }

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
    VeriStmt( Uint idx, const VeriStmt *stmt_copy )
      :  VeriNode( idx, stmt_copy )
      , _func_task_flag( stmt_copy->_func_task_flag )
    {}

    int check_func_child_exp_validation( VeriNode *child, int flag );
    int check_child_stmt( VeriNode * child, int flag );

  private:
    int  _func_task_flag;
};

/*
 * class VeriDummyExp :
 *     Verilog syntax analyzer true node : Dummy statement
 */
class VeriDummyStmt : public VeriStmt
{
  public:
    // Empty statements and loop transfers are leaf nodes; retain their kind
    // through module/generate cloning using the base-node detail field.
    VeriDummyStmt( Uint idx, int line, int col,
             VeriMod *mod, int kind = vsSTMT_DUMMY )
      :  VeriStmt( idx, kind, vsBOTH, line, col, mod )
    {};

    virtual ~VeriDummyStmt( void ) { clear(); };

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
    VeriDummyStmt( Uint idx, const VeriDummyStmt *copy )
      :  VeriStmt( idx, copy )
    {}

  private:
};

// Time declarations are owned leaf nodes; scalar metadata survives every clone.
class VeriClocking : public VeriDummyStmt {
 public:
  VeriClocking(Uint id,int line,int col,VeriMod* mod,int kind,const String& name,
               const NodeVec& children={},int direction=0,bool step=false)
    :VeriDummyStmt(id,line,col,mod,kind),name(name),children(children),direction(direction),step(step) {
    for(auto* child:children)if(child)child->set_father(this);
  }
  String name;
  NodeVec children;
  int direction; // input=vpIN, output=vpOUT; empty name denotes a default skew.
  bool step,default_clock=false;
  int process_node_2nd(NodeVec&,String&) override;
  int push_dot_children(NodeQueue&,IQueue&) override;
  int push_for_replacement(NodeVec&) override;
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
  std::vector<VeriClocking*> ports() const;
};
VeriClocking* veri_clocking_reference(VeriNode*);

class VeriTimeDecl : public VeriDummyStmt {
 public:
  VeriTimeDecl(Uint id,int line,int col,VeriMod* mod,uint64_t unit,uint64_t precision)
    :VeriDummyStmt(id,line,col,mod,vsDECL_TIME),unit_fs(unit),precision_fs(precision) {}
  int replace_node(Uint id,NodeList&,NodeList::iterator& current) override {
    *current=new VeriTimeDecl(id,line(),col(),birth_mod(),unit_fs,precision_fs);return OK;
  }
  uint64_t unit_fs,precision_fs;
};

// Lexical package directives have no runtime effects. Imports survive cloning.
class VeriImportStmt : public VeriDummyStmt {
 public:
  VeriImportStmt(Uint idx,int line,int col,VeriMod* mod,const String& package,const String& member,bool exporting=false)
    : VeriDummyStmt(idx,line,col,mod,exporting?vsDECL_EXPORT:vsDECL_IMPORT),_package(package),_member(member) {}
  int process_node_2nd(NodeVec&,String&) override;
  void append(const VeriImportStmt& other) { _additional.push_back({other._package,other._member}); }
  int replace_node(Uint idx,NodeList&,NodeList::iterator& inl) override {
    auto* copy=new VeriImportStmt(idx,line(),col(),birth_mod(),_package,_member,detail_type()==vsDECL_EXPORT);
    copy->_additional=_additional;*inl=copy;return OK;
  }
 private:
  String _package,_member;
  std::vector<std::pair<String,String>> _additional;
};

// DPI exports own syntax independently of package import/export bindings.
class VeriDpiExportStmt : public VeriDummyStmt {
 public:
  VeriDpiExportStmt(Uint id,int line,int col,VeriMod* mod,const String& name,const String& c_name,bool task)
    :VeriDummyStmt(id,line,col,mod,vsDECL_EXPORT),_name(name),_c_name(c_name),_task(task) {}
  const String& name() const {return _name;}
  const String& c_name() const {return _c_name;}
  bool task() const {return _task;}
  int process_node_2nd(NodeVec&,String&) override {set_pstatus(vEND_S);return OK;}
  int replace_node(Uint id,NodeList&,NodeList::iterator& i) override {
    *i=new VeriDpiExportStmt(id,line(),col(),birth_mod(),_name,_c_name,_task);return OK;
  }
 private:
  String _name,_c_name;bool _task;
};

// Runtime statements with optional expression children. Never evaluate or
// prune them during parser binding; the compiled process owns their effects.
class VeriActionStmt : public VeriStmt {
 public:
  VeriActionStmt(Uint idx,int line,int col,int kind,VeriNode* target,VeriNode* value,int op,VeriMod* mod)
   : VeriStmt(idx,kind,vsBOTH,line,col,mod),_target(target),_value(value),_op(op) {}
  VeriNode* target() const {return _target;}
  VeriNode* value() const {return _value;}
  int op() const {return _op;}
  void clean_up() override {set_pstatus(vSTART_S);}
  int check_child_validation() override;
  int push_dot_children(NodeQueue&,IQueue&) override;
  int pretty_dot_label(Ofstream&,int) override;
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec&) override;
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  VeriNode* _target;
  VeriNode* _value;
  int _op;
};

// Increment/decrement used as a statement (the expression result is discarded).
class VeriUpdateStmt : public VeriStmt {
 public:
  VeriUpdateStmt(Uint idx,int line,int col,VeriNode* target,int delta,VeriMod* mod)
   : VeriStmt(idx,vsSTMT_UPDATE,vsNONE_FUNC,line,col,mod),_target(target),_delta(delta) {}
  VeriNode* target() const {return _target;}
  int delta() const {return _delta;}
  void clean_up() override {set_pstatus(vSTART_S);}
  int check_child_validation() override;
  int push_dot_children(NodeQueue&,IQueue&) override;
  int pretty_dot_label(Ofstream&,int) override;
  int process_node_2nd(NodeVec&,String&) override;
  int push_for_replacement(NodeVec&) override;
  int replace_node(Uint,NodeList&,NodeList::iterator&) override;
 private:
  VeriNode* _target;
  int _delta;
};

/*
 * class VeriLoopStmt :
 *     Verilog syntax analyzer true node : Loop statement
 *   Loop statement has four children
 *     1, initialization expression
 *     2, judge expression
 *     3, iteration expression
 *     4, content statement
 */
class VeriLoopStmt : public VeriStmt
{
  public:
    enum Kind { FOR, WHILE, DO_WHILE, REPEAT, FOREVER, FOREACH };
    VeriLoopStmt( Uint idx, int line, int col, VeriNode *init, VeriNode *judge,
                  VeriNode *iter, VeriNode *content, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_LOOP, vsNONE_FUNC, line, col, mod )
      , _init( init )
      , _judge( judge )
      , _iter( iter )
      , _content( content )
    {
    };

    virtual ~VeriLoopStmt( void ) { clear(); };

    // accessors
    VeriNode * init   ( void ) { return _init;    }
    VeriNode * judge  ( void ) { return _judge;   }
    VeriNode * iter   ( void ) { return _iter;    }
    VeriNode * content( void ) { return _content; }
    Kind kind() const { return _kind; }
    void set_kind(Kind kind) { _kind = kind; }
    NodeList & gen_content( void ) { return _gen_content; }
    const std::vector<std::string>& foreach_indices() const {return _foreach_indices;}
    void set_foreach_indices(const std::vector<std::string>& indices) {_foreach_indices=indices;}

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
    int push_start_and_condition( NodeVec& mstack );
    int decide_loop( NodeVec& mstack );
    int repeat_loop( void );
    int clear_content( void );

  protected:
    VeriLoopStmt( Uint idx, const VeriLoopStmt *copy )
      :  VeriStmt( idx, copy )
      , _kind( copy->_kind )
      , _foreach_indices(copy->_foreach_indices)
      , _init( NULL )
      , _judge( NULL )
      , _iter( NULL )
      , _content( NULL )
    {}

   int check_child_validation_assign( VeriNode *child, bool function_step=false );

  private:
    Kind _kind = FOR;
    std::vector<std::string> _foreach_indices;
    VeriNode *_init;
    VeriNode *_judge;
    VeriNode *_iter;
    VeriNode *_content;

    NodeList  _gen_iter;
    NodeList  _gen_judge;
    NodeList  _gen_content;
};

/*
 * class VeriFuncLoopStmt :
 *     Verilog syntax analyzer true node : Function Loop statement
 *   Function Loop statement has four children
 *     1, initialization expression
 *     2, judge expression
 *     3, iteration expression
 *     4, content  function-statement
 */
class VeriFuncLoopStmt : public VeriStmt
{
  public:
    VeriFuncLoopStmt( Uint idx, int line, int col, VeriNode *init,
                      VeriNode *judge, VeriNode *iter,
                      VeriNode *content,
                           VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_LOOP, vsFUNC, line, col, mod )
      , _init( init )
      , _judge( judge )
      , _iter( iter )
      , _content( content )
    {
    };

    virtual ~VeriFuncLoopStmt( void ) { clear(); };

    // accessors
    VeriNode * init   ( void ) { return _init;    }
    VeriNode * judge  ( void ) { return _judge;   }
    VeriNode * iter   ( void ) { return _iter;    }
    VeriNode * content( void ) { return _content; }

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
    int push_start_and_condition( NodeVec& mstack );
    int decide_loop( NodeVec& mstack );
    int repeat_loop( void );
    int clear_content( void );

  protected:
    VeriFuncLoopStmt( Uint idx, const VeriFuncLoopStmt *copy )
      :  VeriStmt( idx, copy )
      , _init( NULL )
      , _judge( NULL )
      , _iter( NULL )
      , _content( NULL )
    {}

   int check_child_validation_assign( VeriNode *child );

  private:
    VeriNode *_init;
    VeriNode *_judge;
    VeriNode *_iter;
    VeriNode *_content;

    NodeList  _gen_iter;
    NodeList  _gen_judge;
    NodeList  _gen_content;
};

class VeriFuncDefaultCaseItem : public VeriStmt
{
  friend class VeriFuncCaseStmt;

  public:
    VeriFuncDefaultCaseItem( Uint idx, int line, int col, VeriNode *stmt,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_DEFAULT_CASE_ITEM, vsFUNC, line, col, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriFuncDefaultCaseItem( void ) { clear(); }

    // accessors
    VeriNode * stmt( void ) { return _stmt; }

    // mutators
    void set_stmt( VeriNode *node ) { _stmt = node; }

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
    int push_stmt( NodeVec& mstack );

  protected:
    VeriFuncDefaultCaseItem( Uint idx, const VeriFuncDefaultCaseItem *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
    {}

  private:
    VeriNode *_stmt;
};

class VeriFuncCaseItem : public VeriStmt
{
  friend class VeriFuncCaseStmt;
  friend class VeriFuncCaseItemList;

  public:
    VeriFuncCaseItem( Uint idx, int line, int col,
                      VeriNode *stmt, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_CASE_ITEM, vsFUNC, line, col, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriFuncCaseItem( void ) { clear(); }

    // accessors
    NodeList & label( void ) { return _label; }
    VeriNode * stmt ( void ) { return _stmt;  }

    // mutators
    void append_label( VeriNode *node ) { _label.push_back( node ); }
    void set_stmt ( VeriNode *node ) { _stmt  = node; }

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
    int push_labels( NodeVec& mstack );
    int push_stmt( NodeVec& mstack );

  protected:
    VeriFuncCaseItem( Uint idx, const VeriFuncCaseItem *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
    {}

  private:
    NodeList  _label;
    VeriNode *_stmt;
};

class VeriFuncCaseItemList : public VeriStmt
{
  friend class VeriFuncCaseStmt;

  public:
    VeriFuncCaseItemList( Uint idx, int line, int col ,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_CASE_ITEM_LIST, vsFUNC, line, col, mod )
      , _default_item( NULL )
    {}

    virtual ~VeriFuncCaseItemList( void ) { clear(); }

    // accessors
    VeriNode* default_item( void ) { return _default_item; }
    NodeList& other_item  ( void ) { return _other_item;   }

    // mutators
    int  set_default( VeriNode * node );
    void append_item( VeriNode * node ) { _other_item.push_back( node ); }

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
    int push_labels( NodeVec& mstack );

  protected:
    VeriFuncCaseItemList( Uint idx, const VeriFuncCaseItemList *copy )
      :  VeriStmt( idx, copy )
      , _default_item( NULL )
    {}

  private:
    VeriNode *_default_item;
    NodeList  _other_item;

};

class VeriFuncCaseStmt : public VeriStmt
{
  public:
    VeriFuncCaseStmt( Uint idx, int line, int col, int case_type,
                      VeriNode *switch_value, VeriNode * item_list,
                           VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_CASE_STMT, vsFUNC, line, col, mod )
      , _case_type( case_type )
      , _switch( switch_value )
      , _item_list( item_list )
      , _choice( NULL )
    {}

    virtual ~VeriFuncCaseStmt( void ) { clear(); }

    // accessors
    int case_type( void ) const { return _case_type; }
    VeriNode * switch_value( void ) { return _switch; }
    VeriNode * item_list( void ) { return _item_list; }

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
    int push_conditions( NodeVec& mstack );
    int prep_all_labels( void );
    int decide_case( NodeVec& mstack );

  protected:
    VeriFuncCaseStmt( Uint idx, const VeriFuncCaseStmt *copy )
      :  VeriStmt( idx, copy )
      , _case_type( copy->_case_type )
      , _switch( NULL )
      , _item_list( NULL )
      , _choice( NULL )
    {}

  private:
    int        _case_type;
    VeriNode * _switch;
    VeriNode * _item_list;

    NodeList   _all_labels;
    NodeList   _all_exps;

    VeriNode * _choice;
};

class VeriDefaultCaseItem : public VeriStmt
{
  friend class VeriCaseStmt;

  public:
    VeriDefaultCaseItem( Uint idx, int line, int col, VeriNode *stmt,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_DEFAULT_CASE_ITEM, vsNONE_FUNC, line, col, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriDefaultCaseItem( void ) { clear(); }

    // accessors
    VeriNode * stmt( void ) { return _stmt; }

    // mutators
    void set_stmt( VeriNode *node ) { _stmt = node; }

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
    int push_stmt( NodeVec& mstack );

  protected:
    VeriDefaultCaseItem( Uint idx, const VeriDefaultCaseItem *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
    {}

  private:
    VeriNode *_stmt;
};

class VeriCaseItem : public VeriStmt
{
  friend class VeriCaseItemList;
  friend class VeriCaseStmt;

  public:
    VeriCaseItem( Uint idx, int line, int col,
                  VeriNode *stmt, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_CASE_ITEM, vsNONE_FUNC, line, col, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriCaseItem( void ) { clear(); }

    // accessors
    NodeList & label( void ) { return _label; }
    VeriNode * stmt ( void ) { return _stmt;  }

    // mutators
    void append_label( VeriNode *node ) { _label.push_back( node ); }
    void set_stmt ( VeriNode *node ) { _stmt  = node; }

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
    int push_labels( NodeVec& mstack );
    int push_stmt( NodeVec& mstack );

  protected:
    VeriCaseItem( Uint idx, const VeriCaseItem *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
    {}

  private:
    NodeList  _label;
    VeriNode *_stmt;
};

class VeriCaseItemList : public VeriStmt
{
  friend class VeriCaseStmt;

  public:
    VeriCaseItemList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_CASE_ITEM_LIST, vsNONE_FUNC, line, col, mod )
      , _default_item( NULL )
    {}

    virtual ~VeriCaseItemList( void ) { clear(); }

    // accessors
    VeriNode* default_item( void ) { return _default_item; }
    NodeList& other_item  ( void ) { return _other_item;   }

    // mutators
    int  set_default( VeriNode * node );
    void append_item( VeriNode * node ) { _other_item.push_back( node ); }

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
    int push_labels( NodeVec& mstack );

  protected:
    VeriCaseItemList( Uint idx, const VeriCaseItemList *copy )
      :  VeriStmt( idx, copy )
      , _default_item( NULL )
    {}

  private:
    VeriNode *_default_item;
    NodeList  _other_item;

};

class VeriCaseStmt : public VeriStmt
{
  public:
    VeriCaseStmt( Uint idx, int line, int col, int case_type,
                  VeriNode *switch_value, VeriNode * item_list,
                  VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_CASE, vsNONE_FUNC, line, col, mod )
      , _case_type( case_type )
      , _switch( switch_value )
      , _item_list( item_list )
      , _choice( NULL )
      , _selection_qualifier(0)
    {}

    virtual ~VeriCaseStmt( void ) { clear(); }

    // accessors
    int selection_qualifier() const { return _selection_qualifier; }
    void set_selection_qualifier(int qualifier) { _selection_qualifier=qualifier; }
    int case_type( void ) const { return _case_type; }
    VeriNode * switch_value( void ) { return _switch; }
    VeriNode * item_list( void ) { return _item_list; }

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
    int push_conditions( NodeVec& mstack );
    int prep_all_labels( void );
    int decide_case( NodeVec& mstack );

  protected:
    VeriCaseStmt( Uint idx, const VeriCaseStmt *copy )
      :  VeriStmt( idx, copy )
      , _case_type( copy->_case_type )
      , _switch( NULL )
      , _item_list( NULL )
      , _choice( NULL )
      , _selection_qualifier(copy->_selection_qualifier)
    {}

  private:
    int        _case_type;
    VeriNode * _switch;
    VeriNode * _item_list;

    NodeList   _all_labels;
    NodeList   _all_exps;

    int _selection_qualifier; // 0: ordinary, 1: unique, 2: unique0, 3: priority
    VeriNode * _choice;
};

class VeriFuncCondStmt : public VeriStmt
{
  public:
    VeriFuncCondStmt( Uint idx, int line, int col, VeriNode *if_exp,
                      VeriNode *if_stmt, VeriNode *else_stmt,
                           VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_COND, vsFUNC, line, col, mod )
      , _if_exp( if_exp )
      , _if_stmt( if_stmt )
      , _else_stmt( else_stmt )
      , _choice( NULL )
    {}

    virtual ~VeriFuncCondStmt( void ) { clear(); }

    // accessors
    VeriNode * if_exp   ( void ) { return _if_exp; }
    VeriNode * if_stmt  ( void ) { return _if_stmt; }
    VeriNode * else_stmt( void ) { return _else_stmt; }

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

  protected:
    VeriFuncCondStmt( Uint idx, const VeriFuncCondStmt *copy )
      :  VeriStmt( idx, copy )
      , _if_exp( NULL )
      , _if_stmt( NULL )
      , _else_stmt( NULL )
      , _choice( NULL )
    {}

  private:
    VeriNode * _if_exp;
    VeriNode * _if_stmt;
    VeriNode * _else_stmt;

    VeriNode * _choice;
};

class VeriCondStmt : public VeriStmt
{
  public:
    VeriCondStmt( Uint idx, int line, int col, VeriNode *if_exp,
                  VeriNode *if_stmt, VeriNode *else_stmt,
                       VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_COND, vsNONE_FUNC, line, col, mod )
      , _if_exp( if_exp )
      , _if_stmt( if_stmt )
      , _else_stmt( else_stmt )
      , _choice( NULL )
      , _selection_qualifier(0)
      , _wait_order(false)
      , _assertion_kind(0)
    {}

    virtual ~VeriCondStmt( void ) { clear(); }

    // accessors
    int selection_qualifier() const { return _selection_qualifier; }
    void set_selection_qualifier(int qualifier) { _selection_qualifier=qualifier; }
    VeriNode * if_exp   ( void ) { return _if_exp; }
    VeriNode * if_stmt  ( void ) { return _if_stmt; }
    VeriNode * else_stmt( void ) { return _else_stmt; }

    // Simple immediate assertions share branch traversal and preserve their
    // verification identity through parameterized module/generate cloning.
    bool wait_order() const { return _wait_order; }
    void set_wait_order() { _wait_order=true; }

    int assertion_kind() const { return _assertion_kind; }
    void set_assertion_kind(int kind) { _assertion_kind=kind; }
    const std::string& assertion_label() const { return _assertion_label; }
    void set_assertion_label(const std::string& label) { _assertion_label=label; }
    // Concurrent property specifications retain ordinary owned expression/branch
    // traversal. Metadata is copied with each elaborated instance.
    bool property_cycle_delay() const { return _property_cycle_delay; }
    void set_property_cycle_delay() { _property_cycle_delay=true; }
    bool property_repetition() const { return _property_repetition; }
    void set_property_repetition() { _property_repetition=true; }
    bool property_group() const { return _property_group; }
    void set_property_group() { _property_group=true; }
    bool property_term() const { return _property_term; }
    void set_property_term() { _property_term=true; }
    int property_delay() const { return _property_delay; }
    void set_property_delay(int delay) { _property_delay=delay; }
    const std::string& property_name() const { return _property_name; }
    void set_property_name(const std::string& name) { _property_name=name; }
    void set_else_stmt(VeriNode* node) { _else_stmt=node; }


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

  protected:
    VeriCondStmt( Uint idx, const VeriCondStmt *copy )
      :  VeriStmt( idx, copy )
      , _if_exp( NULL )
      , _if_stmt( NULL )
      , _else_stmt( NULL )
      , _choice( NULL )
      , _selection_qualifier(copy->_selection_qualifier)
      , _wait_order(copy->_wait_order)
      , _assertion_kind(copy->_assertion_kind)
      , _assertion_label(copy->_assertion_label)
      , _property_cycle_delay(copy->_property_cycle_delay)
      , _property_repetition(copy->_property_repetition)
      , _property_group(copy->_property_group)
      , _property_term(copy->_property_term)
      , _property_delay(copy->_property_delay)
      , _property_name(copy->_property_name)
    {}

  private:
    VeriNode * _if_exp;
    VeriNode * _if_stmt;
    VeriNode * _else_stmt;

    int _selection_qualifier; // 0: ordinary, 1: unique, 2: unique0, 3: priority
    VeriNode * _choice;
    bool _wait_order;
    int _assertion_kind; // 0: if, 1..3: immediate, 4..6: concurrent, 7: property declaration, 8: sequence declaration
    std::string _assertion_label;
    bool _property_cycle_delay=false;
    bool _property_repetition=false;
    bool _property_group=false;
    bool _property_term=false;
    int _property_delay=-1;
    std::string _property_name;
};

class VeriProcTimeContStmt : public VeriStmt
{
  public:
    VeriProcTimeContStmt( Uint idx, int line, int col, VeriNode *control,
                          VeriNode *stmt,
                               VeriMod *mod, bool level_sensitive = false )
      :  VeriStmt( idx, level_sensitive ? vsSTMT_WAIT : vsSTMT_PROC_TIME_CONTROL, vsNONE_FUNC, line, col, mod )
      , _control( control )
      , _stmt( stmt )
    {}

    virtual ~VeriProcTimeContStmt( void ) { clear(); }

    // accessors
    VeriNode * control( void ) { return _control; }
    VeriNode * stmt   ( void ) { return _stmt; }

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
    VeriProcTimeContStmt( Uint idx, const VeriProcTimeContStmt *copy )
      :  VeriStmt( idx, copy )
      , _control( NULL )
      , _stmt( NULL )
    {}

  private:
    VeriNode * _control;
    VeriNode * _stmt;
};

class VeriDisableStmt : public VeriStmt
{
  public:
    VeriDisableStmt( Uint idx, int line, int col, CString& label,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_DISABLE, vsBOTH, line, col, mod )
      , _label( label )
      , _break_stmt( NULL )
    {}

    virtual ~VeriDisableStmt( void ) { clear(); }

    // accessors
    CString& label( void ) const { return _label; }
    VeriNode * break_stmt( void ) { return _break_stmt; }

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
    VeriDisableStmt( Uint idx, const VeriDisableStmt *copy )
      :  VeriStmt( idx, copy )
      , _label( copy->_label )
      , _break_stmt( NULL )
    {}

  private:
    String     _label;
    VeriNode * _break_stmt;
};

class VeriEventStmt : public VeriStmt
{
  public:
    VeriEventStmt( Uint idx, int line, int col, int is_all, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_EVENT, vsBOTH, line, col, mod )
      , _is_all( is_all )
    {}

    virtual ~VeriEventStmt( void ) { clear(); }

    // accessors
    int is_all( void ) const { return _is_all; }
    NodeList & event_list( void ) { return _event_list; }

    // mutators
    void append_event( VeriNode *node ) { _event_list.push_back( node ); }

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
    VeriEventStmt( Uint idx, const VeriEventStmt *copy )
      :  VeriStmt( idx, copy )
      , _is_all( copy->_is_all )
    {}

  private:
    int      _is_all;
    NodeList _event_list;
};

class VeriSysCallerStmt : public VeriStmt
{
  public:
    VeriSysCallerStmt( Uint idx, int line, int col,
                       CString& caller, VeriNode *arg,
                            VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_SYS_CALL, vsBOTH, line, col, mod )
      , _caller( caller )
      , _arg( arg )
    {}

    virtual ~VeriSysCallerStmt( void ) { clear(); }

    // accessors
    CString& caller( void ) const { return _caller; }
    VeriNode * arg ( void ) const { return _arg;    }

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
    int process_sys_call( void );

  protected:
    VeriSysCallerStmt( Uint idx, const VeriSysCallerStmt *copy )
      :  VeriStmt( idx, copy )
      , _caller( copy->_caller )
      , _arg( NULL )
    {}

  private:
    String    _caller;
    VeriNode *_arg;
};

class VeriCallerStmt : public VeriStmt
{
  public:
    VeriCallerStmt( Uint idx, int line, int col, VeriNode *caller,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_CALL, vsBOTH, line, col, mod )
      , _caller( caller )
    {}

    virtual ~VeriCallerStmt( void ) { clear(); }

    // accessors
    VeriNode * caller( void ) const { return _caller; }
    bool discard() const { return _discard; }
    void set_discard() { _discard=true; }

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
    int process_caller( void );

  protected:
    VeriCallerStmt( Uint idx, const VeriCallerStmt *copy )
      :  VeriStmt( idx, copy )
      , _caller( NULL )
      , _discard(copy->_discard)
    {}

  private:
    VeriNode *_caller;
    bool _discard=false;
};

class VeriSeqBlock : public VeriStmt
{
  public:
    VeriSeqBlock( Uint idx, int line, int col, CString& label, int label_line,
                  int label_col, VeriNode *decl_list, VeriNode *stmt_list,
                  VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_SEQ_BLOCK, vsNONE_FUNC, line, col , mod)
      , _label( label )
      , _label_line( label_line )
      , _label_col( label_col )
      , _decl_list( decl_list )
      , _stmt_list( stmt_list )
    {}

    virtual ~VeriSeqBlock( void ) { clear(); }

    // Class declarations reuse an owned lexical block, never a static instance.
    // The type symbol is semantic state and is rebuilt for each module clone.
    bool class_declaration() const {return _class_declaration;}
    void set_class_declaration() {_class_declaration=true;}
    bool coverage_type() const {return _coverage_type;}
    void set_coverage_type() {_coverage_type=true;}
    // Native IPC classes retain canonical identity independently of user scopes.
    int ipc_kind() const {return _ipc_kind;} // 1: mailbox, 2: semaphore
    VeriVar* ipc_payload() const {return _ipc_payload;} // null: dynamic mailbox
    void set_ipc_type(int kind,VeriVar* payload) {_ipc_kind=kind;_ipc_payload=payload;}
    bool process_type() const {return _process_type;}
    void set_process_type() {_process_type=true;}
    bool abstract_class() const {return _abstract_class;}
    void set_abstract_class(bool value) {_abstract_class=value;}
    VeriVar* class_symbol() const {return _class_symbol;}
    void set_base_name(const std::string& name) {_base_name=name;}
    VeriSeqBlock* base_class() const {return _base_class;}
    VeriNode* class_member(const std::string& name);
    // Resolve a forward type on demand without substituting a new type identity.
    void ensure_class_elaborated();
    bool generic_class() const {return _class_parameters&&!_class_origin;}
    void set_class_parameters(VeriNode* value) {_class_parameters=value;if(value)value->set_father(this);}
    void set_base_type(VeriNode* value) {_base_type=value;if(value)value->set_father(this);}
    VeriSeqBlock* class_origin() const {return _class_origin;}
    std::string type_name() const;
    const std::map<std::string,VeriSeqBlock*>& specializations() const {return _specializations;}
    VeriVar* specialize(VeriNode* arguments,VeriSymbolTable* context);
    void register_class_symbol();

    // 0: begin/end; 1: fork/join; 2: join_any; 3: join_none.
    int parallel_kind() const { return _parallel_kind; }
    void set_parallel_kind(int kind) { _parallel_kind=kind; }

    // accessors
    CString  & label    ( void ) { return _label; }
    VeriNode * decl_list( void ) { return _decl_list; }
    VeriNode * stmt_list( void ) { return _stmt_list; }

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
    int process_label( void );
    int push_children( NodeVec& mstack );
    int end_label( void );

  protected:
    VeriSeqBlock( Uint idx, const VeriSeqBlock *copy )
      :  VeriStmt( idx, copy )
      , _label( copy->_label )
      , _label_line( copy->_label_line )
      , _label_col( copy->_label_col )
      , _decl_list( NULL )
      , _stmt_list( NULL )
      , _parallel_kind( copy->_parallel_kind )
      , _class_declaration(copy->_class_declaration)
      , _coverage_type(copy->_coverage_type)
      , _abstract_class(copy->_abstract_class)
      , _base_name(copy->_base_name)
    {}

  private:
    String     _label;
    int        _label_line;
    int        _label_col;
    VeriNode * _decl_list;
    VeriNode * _stmt_list;
    int _parallel_kind=0;
    bool _class_declaration=false;
    bool _coverage_type=false;
    bool _abstract_class=false;
    bool _process_type=false;
    int _ipc_kind=0;
    VeriVar* _ipc_payload=nullptr;
    VeriVar* _class_symbol=nullptr;
    std::string _base_name;
    VeriSeqBlock* _base_class=nullptr;
    VeriNode* _class_parameters=nullptr;
    VeriNode* _base_type=nullptr;
    VeriSeqBlock* _class_origin=nullptr;
    std::map<std::string,VeriNode*> _class_bindings;
    std::vector<std::string> _class_parameter_order;
    std::map<std::string,VeriSeqBlock*> _specializations;
    unsigned _class_state=0; // 0: pending, 1: elaborating, 2: complete; never cloned.
};

class VeriFuncSeqBlock : public VeriStmt
{
  public:
    VeriFuncSeqBlock( Uint idx, int line, int col, CString& label,
                      int label_line, int label_col, VeriNode *decl_list,
                      VeriNode *stmt_list, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_SEQ_BLOCK, vsFUNC, line, col, mod )
      , _label( label )
      , _label_line( label_line )
      , _label_col( label_col )
      , _decl_list( decl_list )
      , _stmt_list( stmt_list )
    {}

    virtual ~VeriFuncSeqBlock( void ) { clear(); }

    // accessors
    CString  & label    ( void ) { return _label; }
    VeriNode * decl_list( void ) { return _decl_list; }
    VeriNode * stmt_list( void ) { return _stmt_list; }

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
    int process_label( void );
    int push_children( NodeVec& mstack );
    int end_label( void );

  protected:
    VeriFuncSeqBlock( Uint idx, const VeriFuncSeqBlock *copy )
      :  VeriStmt( idx, copy )
      , _label( copy->_label )
      , _label_line( copy->_label_line )
      , _label_col( copy->_label_col )
      , _decl_list( NULL )
      , _stmt_list( NULL )
    {}

  private:
    String     _label;
    int        _label_line;
    int        _label_col;
    VeriNode * _decl_list;
    VeriNode * _stmt_list;
};

class VeriStmtList : public VeriStmt
{
  public:
    VeriStmtList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_STMT_LIST, vsNONE_FUNC, line, col, mod )
    {}

    virtual ~VeriStmtList( void ) { clear(); }

    // accessors
    NodeList & stmt_list( void ) { return _stmt_list; }

    // mutators
    void append_stmt( VeriNode * node ) { _stmt_list.push_back( node ); }

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
    VeriStmtList( Uint idx, const VeriStmtList *copy )
      :  VeriStmt( idx, copy )
    {}

  private:
    NodeList _stmt_list;
};

class VeriFuncStmtList : public VeriStmt
{
  public:
    VeriFuncStmtList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_STMT_LIST, vsFUNC, line, col, mod )
    {}

    virtual ~VeriFuncStmtList( void ) { clear(); }

    // accessors
    NodeList & stmt_list( void ) { return _stmt_list; }

    // mutators
    void append_stmt( VeriNode * node ) { _stmt_list.push_back( node ); }

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
    VeriFuncStmtList( Uint idx, const VeriFuncStmtList *copy )
      :  VeriStmt( idx, copy )
    {}

  private:
    NodeList _stmt_list;
};

class VeriFuncBlockAssignStmt : public VeriStmt
{
  typedef std::vector<int> IVec;

  public:
    VeriFuncBlockAssignStmt( Uint idx, int line, int col, VeriNode *lval,
                             VeriNode *rval, VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_FUNC_BLOCKING, vsBOTH, line, col, mod )
      , _lval( lval )
      , _rval( rval )
    {}

    virtual ~VeriFuncBlockAssignStmt( void ) { clear(); }

    // accessors
    VeriNode * lval( void ) { return _lval; }
    VeriNode * rval( void ) { return _rval; }

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
    int process_func_blocking_assign( void );

  protected:
    VeriFuncBlockAssignStmt( Uint idx, const VeriFuncBlockAssignStmt *copy )
      :  VeriStmt( idx, copy )
      , _lval( NULL )
      , _rval( NULL )
    {}

  private:
    VeriNode * _lval;
    VeriNode * _rval;
};

class VeriBlockStmt : public VeriStmt
{
  typedef std::vector<int> IVec;

  public:
    VeriBlockStmt( Uint idx, int line, int col,
                   VeriNode *lval, VeriNode *event, VeriNode *rval,
                        VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_BLOCKING, vsNONE_FUNC, line, col, mod )
      , _lval( lval )
      , _event( event )
      , _rval( rval )
    {}

    virtual ~VeriBlockStmt( void ) { clear(); }

    // accessors
    VeriNode * lval( void ) { return _lval; } 
    VeriNode * rval( void ) { return _rval; } 
    VeriNode * event( void ) { return _event; }

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
    int process_blocking_assignment( void );

  protected:
    VeriBlockStmt( Uint idx, const VeriBlockStmt *copy )
      :  VeriStmt( idx, copy )
      , _lval( NULL )
      , _event( NULL )
      , _rval( NULL )
    {}

  private:
    VeriNode * _lval;
    VeriNode * _event;
    VeriNode * _rval;
};

class VeriNonBlockStmt : public VeriStmt
{
  typedef std::vector<int> IVec;

  public:
    VeriNonBlockStmt( Uint idx, int line, int col,
                      VeriNode *lval, VeriNode *event, VeriNode *rval,
                           VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_NONBLOCKING, vsNONE_FUNC, line, col, mod )
      , _lval( lval )
      , _event( event )
      , _rval( rval )
    {}

    virtual ~VeriNonBlockStmt( void ) { clear(); }

    // accessors
    VeriNode * lval( void ) { return _lval; } 
    VeriNode * rval( void ) { return _rval; } 
    VeriNode * event( void ) { return _event; } 

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
    int process_non_blocking_assignment( void );

  protected:
    VeriNonBlockStmt( Uint idx, const VeriNonBlockStmt *copy )
      :  VeriStmt( idx, copy )
      , _lval( NULL )
      , _event( NULL )
      , _rval( NULL )
    {}

  private:
    VeriNode * _lval;
    VeriNode * _event;
    VeriNode * _rval;
};

/*
 * Expression should be Assignment-Expression
 * Delay should be Delay-Expression
 * Drive-Strength should be Drive-Expression
 */
class VeriContAssignStmt : public VeriStmt
{
  public:
    VeriContAssignStmt( Uint idx, int line, int col,
                        VeriNode *delay, VeriNode *drive, VeriNode *exp,
                             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_CONT_ASSIGN, vsNONE_FUNC, line, col, mod )
      , _delay( delay )
      , _drive_strength( drive )
      , _exp( exp )
    {}

    virtual ~VeriContAssignStmt( void ) { clear(); }

    // accessors
    VeriNode * exp  ( void ) { return _exp; } 
    VeriNode * delay( void ) { return _delay; } 
    VeriNode * drive_strength( void ) { return _drive_strength; } 

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
    VeriContAssignStmt( Uint idx, const VeriContAssignStmt *copy )
      :  VeriStmt( idx, copy )
      , _delay( NULL )
      , _drive_strength( NULL )
      , _exp( NULL )
    {}

  private:
    VeriNode *_delay;
    VeriNode *_drive_strength;
    VeriNode *_exp;
};

class VeriInitStmt : public VeriStmt
{
  public:
    VeriInitStmt( Uint idx, int line, int col, VeriNode *stmt,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_INIT, vsNONE_FUNC, line, col, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriInitStmt( void ) { clear(); }

    // accessors
    VeriNode * stmt( void ) { return _stmt; } 

    bool final_process() const { return _final_process; }
    void set_final_process() { _final_process=true; }

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
    VeriInitStmt( Uint idx, const VeriInitStmt *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
      , _final_process(copy->_final_process)
    {}

  private:
    VeriNode *_stmt;
    bool _final_process=false;
};

class VeriAlwaysStmt : public VeriStmt
{
  public:
    VeriAlwaysStmt( Uint idx, int line, int col, VeriNode *stmt,
             VeriMod *mod, int always_kind = akALWAYS )
      :  VeriStmt( idx, vsSTMT_ALWAYS, vsNONE_FUNC, line, col, mod )
      , _stmt( stmt )
      , _always_kind( always_kind )
    {}

    virtual ~VeriAlwaysStmt( void ) { clear(); }

    // accessors
    VeriNode * stmt( void ) { return _stmt; }
    int always_kind( void ) const { return _always_kind; }
    void set_always_kind( int kind ) { _always_kind = kind; } 

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
    VeriAlwaysStmt( Uint idx, const VeriAlwaysStmt *copy )
      :  VeriStmt( idx, copy )
      , _stmt( NULL )
      , _always_kind( copy->_always_kind )
    {}

  private:
    VeriNode *_stmt;
    int       _always_kind;
};

class VeriModuleItemList : public VeriStmt
{
  public:
    VeriModuleItemList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriStmt( idx, vsSTMT_MOD_ITEM_LIST, vsNONE_FUNC, line, col, mod )
    {}

    virtual ~VeriModuleItemList() { clear(); }

    // accessors
    NodeList & item_list( void ) { return _item_list; }

    // mutators
    void append_item( VeriNode * node ) { _item_list.push_back( node ); }

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
    VeriModuleItemList( Uint idx, const VeriModuleItemList *copy )
      :  VeriStmt( idx, copy )
    {}

  private:
    NodeList _item_list;
};

// Sequence symbols point to their owned declaration; references never own or
// clone that declaration. Register all names before binding any list operand.
VeriCondStmt* veri_sequence_definition(VeriNode*);
bool veri_sequence_term(VeriNode*);
void veri_register_sequences(const VeriNode::NodeList&,VeriSymbolTable*);
void veri_bind_forward_classes(const VeriNode::NodeList&);

};
#endif // PARSER_VERILOG_VERI_STMT_HPP_
