/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_tfmg.hpp
 * Summary  : verilog syntax analyzer true node class :
 *            1, task
 *            2, function
 *            3, gate_instance
 *            4, mod_instance
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2013.3.8
 */

#ifndef PARSER_VERILOG_VERI_TFMG_HPP_
#define PARSER_VERILOG_VERI_TFMG_HPP_

#include "veri_node.hpp"

#include <vector>
#include <string>

namespace rtl
{

class VeriNum;
class VeriTaskDecl;
class VeriFuncDecl;
class VeriGateInstantiation;
class VeriModInstantiation;

class VeriTask : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;
  typedef std::ofstream Ofstream;

  public:
    VeriTask( Uint idx, int line, int col, CString& name,
              VeriTaskDecl * task, VeriMod *mod )
      :  VeriNode( idx, vtTASK, vtTASK, line, col, mod )
      ,  _name(name)
      ,  _task(task)
    {}

    virtual ~VeriTask() { clear(); }

    // accessors
    VeriTaskDecl * task( void ) { return _task; }

    // mutators
    void set_task( VeriTaskDecl * task ) { _task = task; }

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
    VeriTask() {};

  private:
    String         _name;
    VeriTaskDecl * _task;
};


class VeriFunc : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;
  typedef std::ofstream Ofstream;

  public:
    VeriFunc( Uint idx, int line, int col, CString& name,
              VeriFuncDecl * func, int dstart, int dend,
              int is_signed, int is_auto, VeriNum *val,
              VeriMod *mod )
      :  VeriNode( idx, vtFUNC, vtFUNC, line, col, mod )
      ,  _name(name)
      ,  _func(func)
      ,  _is_signed(is_signed)
      ,  _is_auto(is_auto)
      ,  _dstart(dstart)
      ,  _dend(dend)
      ,  _dlen(abs(dend-dstart)+1)
      ,  _val(val)
    {}

    virtual ~VeriFunc() { clear(); }

    // accessors
    VeriFuncDecl * func( void ) { return _func; }

    VeriNum *get_val( void );

    int   dstart( void ) const { return _dstart; }
    int   dend  ( void ) const { return _dend;   }
    int   dlen  ( void ) const { return _dlen;   }

    // mutators
    void set_func( VeriFuncDecl * func ) { _func = func; }
    void set_dstart( int v ) { _dstart = v; }
    void set_dend( int v ) { _dend = v; }
    void set_dlen( int v ) { _dlen = v; }

    void set_val( VeriNum *val );

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
    VeriFunc() {};

    int calc_dimen_cnt( int start_lvl );

  private:
    String         _name;
    VeriFuncDecl * _func;

    int    _is_signed;
    int    _is_auto;
    int    _dstart;
    int    _dend;
    int    _dlen;

    VeriNum   *_val;
};

class VeriGateInst : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;
  typedef std::ofstream Ofstream;

  public:
    VeriGateInst( Uint idx, int line, int col, CString& name,
              VeriNode * instance, VeriGateInstantiation *gate,
              IList& dimen, VeriMod *mod )
      :  VeriNode( idx, vtGATE_INST, vtGATE_INST, line, col, mod )
      ,  _name(name)
      ,  _dimen( dimen.begin(), dimen.end() )
      ,  _instance( instance )
      ,  _gate( gate )
    {
    }

    virtual ~VeriGateInst() { clear(); }

    // accessors
    VeriNode * instance( void ) { return _instance; }
    VeriGateInstantiation * gate( void ) { return _gate; }

    // mutators
    void set_instance( VeriNode * node ) { _instance = node; }
    void set_gate( VeriGateInstantiation * gate ) { _gate = gate; }

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
    VeriGateInst() {};

  private:
    String     _name;
    IList      _dimen;
    VeriNode * _instance;
    VeriGateInstantiation * _gate;
};

class VeriModInst : public VeriNode
{
  typedef std::string  String;
  typedef const String CString;
  typedef std::ofstream Ofstream;

  public:
    VeriModInst( Uint idx, int line, int col, CString& name,
                 VeriNode * instance, VeriModInstantiation *mod_inst,
                 const IList& dimen, VeriMod *mod )
      :  VeriNode( idx, vtMOD_INST, vtMOD_INST, line, col, mod )
      ,  _name(name)
      ,  _dimen( dimen.begin(), dimen.end() )
      ,  _instance( instance )
      ,  _mod( mod_inst )
    {}

    virtual ~VeriModInst() { clear(); }

    // accessors
    CString& name( void ) const { return _name; }
    VeriNode * instance( void ) { return _instance; }
    VeriModInstantiation * mod( void ) { return _mod; }

    // mutators
    void set_instance( VeriNode * node ) { _instance = node; }
    void set_mod( VeriModInstantiation * mod ) { _mod = mod; }

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
    VeriModInst() {};

  private:
    String     _name;
    IList      _dimen;
    VeriNode * _instance;
    VeriModInstantiation * _mod;
};


};
#endif // PARSER_VERILOG_VERI_TFMG_HPP_
