/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_inst.hpp
 * Summary  : verilog syntax analyzer true node class : instantiation
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.1.28
 */

#ifndef PARSER_VERILOG_VERI_INST_HPP_
#define PARSER_VERILOG_VERI_INST_HPP_

#include "veri_node.hpp"

#include <vector>
#include <string>
#include <list>
#include <set>

namespace rtl
{

class VeriGateInstantiation;

/*
 * class VeriInst :
 *     Verilog syntax analyzer true node : instantiation
 */
class VeriInst : public VeriNode
{
  public:
    VeriInst( Uint idx, int line, int col, int inst_type,
             VeriMod *mod )
      :  VeriNode( idx, vtINST, inst_type, line, col, mod )
    {}

    virtual ~VeriInst() {};

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
    VeriInst( Uint idx, const VeriInst *inst_copy )
      :  VeriNode( idx, inst_copy )
    {}

    int check_child_exp_validation( VeriNode *child, int flag );
};

/*
 * class VeriDummyInst :
 *     Verilog syntax analyzer true node : Dummy statement
 */
class VeriDummyInst : public VeriInst
{
  public:
    VeriDummyInst( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_DUMMY, mod )
    {};

    virtual ~VeriDummyInst( void ) { clear(); };

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
    VeriDummyInst( Uint idx, const VeriDummyInst *copy )
      : VeriInst( idx, copy )
    {}

  private:
};

class VeriModInstance : public VeriInst
{
  public:
    VeriModInstance( Uint idx, int line, int col,
                     VeriNode *inst_name, VeriNode *arg, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_MOD_INSTANCE, mod )
      , _name("")
      , _inst_name( inst_name )
      , _arg( arg )
      , _hive( NULL )
    {}

    virtual ~VeriModInstance() { clear(); }

    // accessors
    VeriNode * inst_name( void ) { return _inst_name; }
    VeriNode * arg      ( void ) { return _arg;       }
    VeriNode * hive     ( void ) { return _hive;       }

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
    int reg_mod_inst( );

    int push_children( NodeVec& mstack );
    int unfolding( NodeVec& mstack );

  protected:
    VeriModInstance( Uint idx, const VeriModInstance *copy )
      :  VeriInst( idx, copy )
      , _name(copy->_name)
      , _inst_name( NULL )
      , _arg( NULL )
      , _hive( NULL )
    {}

  private:
    String     _name;
    VeriNode * _inst_name;
    VeriNode * _arg;
    
    VeriNode * _hive; // after instantiated

    NodeList   _ports;
};

class VeriModInstantiation : public VeriInst
{
  public:
    VeriModInstantiation( Uint idx, int line, int col, CString& mod_name,
                          VeriNode *param, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_MOD_INSTANTIATION, mod )
      , _mod_name( mod_name )
      , _param( param )
      , _inst_mod( NULL )
    {}

    virtual ~VeriModInstantiation() { clear(); }

    // accessors
    CString&   mod_name( void ) const { return _mod_name; }
    VeriNode * param   ( void ) { return _param;    }
    NodeList & mod_list( void ) { return _mod_list; }
    VeriMod  * inst_mod( void ) { return _inst_mod; }

    // mutators
    void append_mod_inst( VeriNode * mod ) { _mod_list.push_back( mod ); }
    void set_inst_mod( VeriMod * mod ) { _inst_mod = mod; }

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
    VeriModInstantiation( Uint idx, const VeriModInstantiation *copy )
      :  VeriInst( idx, copy )
      , _mod_name( copy->_mod_name )
      , _param( NULL )
      , _inst_mod( copy->_inst_mod )
    {}

  private:
    String    _mod_name;
    VeriNode *_param;
    NodeList  _mod_list;
    VeriMod  *_inst_mod;
};

class VeriGateInstance : public VeriInst
{
  public:
    VeriGateInstance( Uint idx, int line, int col,
                      VeriNode *inst_name, VeriNode *arg, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GATE_INSTANCE, mod )
      , _inst_name( inst_name )
      , _name( "" )
      , _arg( arg )
      , _hive( NULL )
    {}

    virtual ~VeriGateInstance() { clear(); }

    // accessors
    VeriNode * inst_name( void ) { return _inst_name; }
    VeriNode * arg      ( void ) { return _arg;       }

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
    int reg_gate_inst( void );

    int push_children( NodeVec& mstack );
    int do_nothing( void );

  protected:
    VeriGateInstance( Uint idx, const VeriGateInstance *copy )
      :  VeriInst( idx, copy )
      , _inst_name( NULL )
      , _name( copy->_name )
      , _arg( NULL )
      , _hive( NULL )
    {}

  private:
    VeriNode * _inst_name;
    String     _name;
    VeriNode * _arg;

    VeriNode * _hive; // after instantiated
};

class VeriGateInstantiation : public VeriInst
{
  public:
    VeriGateInstantiation( Uint idx, int line, int col, int gate_type,
                          VeriNode *drive, VeriNode *delay, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GATE_INSTANTIATION, mod )
      , _gate_type( gate_type )
      , _drive_strength( drive )
      , _delay( delay )
    {}

    virtual ~VeriGateInstantiation() { clear(); }

    // accessors
    int        gate_type( void ) { return _gate_type; }
    NodeList & gate_list( void ) { return _gate_list; }
    VeriNode * delay    ( void ) { return _delay;     }
    VeriNode * drive_strength( void ) { return _drive_strength;    }

    void append_gate( VeriNode * gate ) { _gate_list.push_back( gate ); }

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
    VeriGateInstantiation( Uint idx, const VeriGateInstantiation *copy )
      :  VeriInst( idx, copy )
      , _gate_type( copy->_gate_type )
      , _drive_strength( NULL )
      , _delay( NULL )
    {}

  private:
    int       _gate_type;
    VeriNode *_drive_strength;
    VeriNode *_delay;
    NodeList  _gate_list;
};

/*
 * class VeriGenLoop :
 *     Verilog syntax analyzer true node : Generated-Loop statement
 *   Generated Loop statement has 5 children
 *     1, initialization expression
 *     2, judge expression
 *     3, iteration expression
 *     4, content statement
 */
class VeriGenLoop : public VeriInst
{
  public:
    VeriGenLoop( Uint idx, int line, int col, VeriNode *init, VeriNode *judge,
                 VeriNode *iter, CString& gen_label, int label_line,
                 int label_col, VeriNode *content, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_LOOP, mod )
      , _init( init )
      , _judge( judge )
      , _iter( iter )
      , _label( gen_label )
      , _label_line( label_line )
      , _label_col( label_col )
      , _content( content )
      , _is_target( IS_FALSE )
      , _inline_genvar(false)
    {
    };

    virtual ~VeriGenLoop( void ) { clear(); };

    // accessors
    VeriNode * init   ( void ) { return _init;    }
    VeriNode * judge  ( void ) { return _judge;   }
    VeriNode * iter   ( void ) { return _iter;    }
    VeriNode * content( void ) { return _content; }
    CString  & label  ( void ) { return _label;   }
    void set_inline_genvar(bool value) { _inline_genvar=value; }
    // Completed second-round iterations. The original content() is a
    // disposable template and must not be consumed after elaboration.
    const NodeList& generated_content() const { return _gen_content; }
    const std::vector<int>& generated_values() const { return _gen_values; }
    const String& generated_variable() const { return _gen_variable; }

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
    int push_start_and_condition( NodeVec& mstack );
    int decide_loop( NodeVec& mstack );
    int repeat_loop( void );

    int clear_content( void );

  protected:
    VeriGenLoop( Uint idx, const VeriGenLoop *copy )
      :  VeriInst( idx, copy )
      , _init( NULL )
      , _judge( NULL )
      , _iter( NULL )
      , _label( copy->_label )
      , _label_line( copy->_label_line )
      , _label_col( copy->_label_col )
      , _content( NULL )
      , _is_target( IS_FALSE )
      , _inline_genvar(copy->_inline_genvar)
    {}

    int check_child_validation_assign( VeriNode *child );

  private:
    VeriNode *_init;
    VeriNode *_judge;
    VeriNode *_iter;

    String    _label;
    int       _label_line;
    int       _label_col;
    VeriNode *_content;
    VeriNode* _syntax_content=nullptr; // Pool-owned, never elaborated in place.

    int       _is_target;
    bool      _inline_genvar;

    NodeList  _gen_iter;
    NodeList  _gen_judge;
    NodeList  _gen_content;
    std::vector<int> _gen_values;
    std::set<int> _gen_seen;
    String _gen_variable;
};

class VeriDefaultGenCaseItem : public VeriInst
{
  friend class VeriGenCase;

  public:
    VeriDefaultGenCaseItem( Uint idx, int line, int col, VeriNode *stmt,
             VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_DEFAULT_CASE_ITEM, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriDefaultGenCaseItem( void ) { clear(); }

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
    VeriDefaultGenCaseItem( Uint idx, const VeriDefaultGenCaseItem *copy )
      :  VeriInst( idx, copy )
      , _stmt( NULL )
    {}

  private:
    VeriNode *_stmt;
};

class VeriGenCaseItem : public VeriInst
{
  friend class VeriGenCaseItemList;
  friend class VeriGenCase;

  public:
    VeriGenCaseItem( Uint idx, int line, int col,
                     VeriNode *stmt, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_CASE_ITEM, mod )
      , _stmt( stmt )
    {}

    virtual ~VeriGenCaseItem( void ) { clear(); }

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
    VeriGenCaseItem( Uint idx, const VeriGenCaseItem *copy )
      :  VeriInst( idx, copy )
      , _stmt( NULL )
    {}

  private:
    NodeList  _label;
    VeriNode *_stmt;
};

class VeriGenCaseItemList : public VeriInst
{
  friend class VeriGenCase;

  public:
    VeriGenCaseItemList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_CASE_ITEM_LIST, mod )
      , _default_item( NULL )
    {}

    virtual ~VeriGenCaseItemList( void ) { clear(); }

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
    VeriGenCaseItemList( Uint idx, const VeriGenCaseItemList *copy )
      :  VeriInst( idx, copy )
      , _default_item( NULL )
    {}

  private:
    VeriNode *_default_item;
    NodeList  _other_item;

};

class VeriGenCase : public VeriInst
{
  public:
    VeriGenCase( Uint idx, int line, int col,
                 VeriNode *switch_value, VeriNode * item_list,
                      VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_CASE, mod )
      , _case_type( vcCASE )
      , _switch( switch_value )
      , _item_list( item_list )
      , _choice( NULL )
    {}

    virtual ~VeriGenCase( void ) { clear(); }

    // accessors
    int case_type( void ) const { return vcCASE; }
    VeriNode * switch_value( void ) { return _switch; }
    VeriNode * item_list( void ) { return _item_list; }
    VeriNode * choice() const { return _choice; }

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
    VeriGenCase( Uint idx, const VeriGenCase *copy )
      :  VeriInst( idx, copy )
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

class VeriGenCond : public VeriInst
{
  public:
    VeriGenCond( Uint idx, int line, int col, VeriNode *if_exp,
                  VeriNode *if_stmt, VeriNode *else_stmt,
                       VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_COND, mod )
      , _if_exp( if_exp )
      , _if_stmt( if_stmt )
      , _else_stmt( else_stmt )
      , _choice( NULL )
    {}

    virtual ~VeriGenCond( void ) { clear(); }

    // accessors
    VeriNode * if_exp   ( void ) { return _if_exp; }
    VeriNode * if_stmt  ( void ) { return _if_stmt; }
    VeriNode * else_stmt( void ) { return _else_stmt; }
    VeriNode * choice() const { return _choice; }

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
    VeriGenCond( Uint idx, const VeriGenCond *copy )
      :  VeriInst( idx, copy )
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

class VeriGenBlock : public VeriInst
{
  public:
    VeriGenBlock( Uint idx, int line, int col, CString& label,
                  int label_line, int label_col,
                  VeriNode *item_list, VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_BLOCK, mod )
      , _label( label )
      , _label_line( label_line )
      , _label_col( label_col )
      , _item_list( item_list )
    {}

    virtual ~VeriGenBlock( void ) { clear(); }

    // accessors
    CString  & label( void ) { return _label; }
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
    int process_label( void );
    int push_children( NodeVec& mstack );
    int end_label( void );

  protected:
    VeriGenBlock( Uint idx, const VeriGenBlock *copy )
      :  VeriInst( idx, copy )
      , _label( copy->_label )
      , _label_line( copy->_label_line )
      , _label_col( copy->_label_col )
      , _item_list( NULL )
    {}

  private:
    String     _label;
    int        _label_line;
    int        _label_col;
    VeriNode * _item_list;
};

class VeriGenItemList : public VeriInst
{
  public:
    VeriGenItemList( Uint idx, int line, int col,
             VeriMod *mod )
      :  VeriInst( idx, line, col, vsINST_GEN_ITEM_LIST, mod )
    {}

    virtual ~VeriGenItemList( void ) { clear(); }

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
    VeriGenItemList( Uint idx, const VeriGenItemList *copy )
      :  VeriInst( idx, copy )
    {}

  private:
    NodeList _item_list;
};

};
#endif // PARSER_VERILOG_VERI_INST_HPP_
