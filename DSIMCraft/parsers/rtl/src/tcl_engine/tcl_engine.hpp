/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : tcl_engine.hpp
 * Summary  : tcl command line engine class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#ifndef PAVIO_TCL_ENGINE_HPP_
#define PAVIO_TCL_ENGINE_HPP_

#include "singleton.hpp"

#include <tcl.h>

#include <string>
#include <sstream>
#include <vector>
#include <map>

#include "tcl_token.hpp"

namespace p_tcl_engine
{

using pavio_singleton::Singleton;

/*
 * class TclEngine :
 *     Tcl command line engine class.
 *     call init() before using.
 *     call eval() to use tcl engine, return result in std::string type.
 */
class TclEngine : public Singleton<TclEngine>
{
  friend class Singleton<TclEngine>;

  struct CmdRec;

  typedef std::string              String;
  typedef unsigned int             Uint;
  typedef const String             CString;
  typedef std::vector<String>      SVector;
  typedef std::map<String,CmdRec>  CmdLib;
  typedef std::map<String,int>     SIMap;
  typedef unsigned long long       Ulong;

  private:
    struct CmdRec
    {
      String  _name;
      int     _min_var;
      int     _max_var;
      String  _var;
      String  _comment;

      CmdRec( CString& name, int min_var, int max_var,
              CString& var, CString& comment ):
        _name( name ),
        _min_var( min_var ),
        _max_var( max_var ),
        _var( var ),
        _comment( comment )
        {}
    };

    class CmpCmdRec
    {
      bool operator()( const CmdRec& a, const CmdRec& b ) const
      {
        const bool& re =    (a._name  < b._name) \
                   || (a._name == b._name && a._min_var < b._min_var) \
                   || (a._min_var == b._min_var && a._max_var < b._max_var) \
                   || (a._max_var == b._max_var && a._var < b._var) \
                   || (a._var == b._var && a._comment < b._comment);
        return re;
      }
    };

  public:
    // initialize before anyother function-call
    String init( void ); 

    // execute command : expr
    String eval(CString& expr);
    String eval_file(const char* fname);

    // get expression, dir indicates direction
    CString& get_expr( int dir ) const;

    // for keyboard::TAB usage or others
    String match(CString& in) const;
    void multi_match(CString& in, SVector& ret) const;

    // return all history
    String get_history() const;

    // accessors
    CString& script_name( void ) const { return _script_name; }
    int      LINE       ( void ) const { return _LINE;        }
    String   cmd_list   ( int is_complete ) const;
    String   posix_ls   ( CString& dname ) const;

    int min_func_var( CString& name ) const
    {
      CmdLib::const_iterator it = _cmd_lib.find(name);
      if( it == _cmd_lib.end() )
        return 0;
      else
        return it->second._min_var + 1;
    }

    int max_func_var( CString& name ) const
    {
      CmdLib::const_iterator it = _cmd_lib.find(name);
      if( it == _cmd_lib.end() )
        return 0;
      else
        return it->second._max_var + 1;
    }

    // mutators
    void set_script_name( CString& name ) { _script_name = name; }
    void set_LINE( int line ) { _LINE = line; }

    void get_detail(String& re, CString& func_name,
                    int err_ret, int other = 0 ) const
    {
      get_script_name(re);
      get_script_line(re);
      get_func(re,func_name);
      append_err_msg(err_ret, re, other);
    }

  protected:

    void clear( void );

    // register every user-input command in history
    void register_history( CString& expr );

    // command library manipulations
    void init_command_lib( void );
    void register_commands( void );
    void del_reg_cmd( void );
    void add_reg_cmd( CString& name, int min_var, int max_var,
                      CString& var, CString& comment );

    int cal_match_ratio( const char* in, int length1,
                         const char* pattern, int length2 ) const;

    // for keyboard::up & down usage, caller is public::get_expr()
    String& get_last_expr() const;
    String& get_next_expr() const;

    // number judging
    int is_double( CString& in ) const;
    int is_complex( CString& in , float& out1 , float& out2 ) const;

    // string processing
    String erase_white(CString& in) const;

    Uint get_num_of_line( int min_width , int max_width ) const;
    Uint get_largest_width( const SVector& in ) const;
    Uint get_largest_width( CString* in, int num ) const;

    String append_white( Uint max_length, CString& in ) const;

    void norm_string( const SVector& in, Uint num_of_line,
                      Uint max_width, String& out ) const;
    void norm_string( CString* in, Uint len, Uint num_of_line,
                      Uint max_width, String& out ) const;
    void norm_svector( Uint max_width , SVector& in ) const;

    int  cmd_history_idx_adjust(int n, int num) const;

    void organize_output( const SVector& in, String& out ) const;
    void organize_output( CString* in, int num, String& out ) const;

  protected:

    // trivial stuff
    Ulong convert(CString& in) const
    {
	    std::stringstream f;
	    f << in;
	    Ulong ret;
	    f >> ret;
	    return ret;
    }

    String convert(int in) const
    {
	    std::stringstream f;
	    f << in;
	    String ret;
	    f >> ret;
	    return ret;
    }

    // error processing
    void append_err_msg( int err, String& ret, int other ) const;
    void get_script_name( String& re ) const
    {
      if(!_script_name.empty())
      {
        re.append( "Script file: " );
        re.append( _script_name );
        re.append( " , " );
      }
    }

    void get_script_line( String& re ) const
    {
      if( _LINE != 0 )
      {
        re.append( "Line: " );
        re.append(convert(_LINE));
        re.append( " , ");
      }
    }

    void get_func( String& re , CString& func_name) const
    {
      re.append( "Function : " );
      re.append( func_name );
      re.append( " , ");
    }

  private:
    TclEngine( void );
    ~TclEngine( void );

    Tcl_Interp *_interp;   ///< tcl command line linux handler ptr
    CmdLib      _cmd_lib;  ///< command library
    SVector     _cmd_slib; ///< command names

    // output config
    Uint  _line_width;            ///< width in char count
    Uint  _min_char_tab;          ///< minimum whitespace between two string
    Uint  _cmd_name_max_width;    ///< maximun name width
    Uint  _cmd_var_max_width;     ///< maximun varriable information width
    Uint  _cmd_comment_max_width; ///< maximun comment width
    int   _hide_file;             ///< hidden file

    // history part
    mutable int _cmd_shift;
    mutable int _cmd_index;
    int     _num_history;
    String* _cmds;

    // script handler
    String  _script_name;
    int     _LINE;
};

};
#endif // PAVIO_TCL_ENGINE_HPP_
