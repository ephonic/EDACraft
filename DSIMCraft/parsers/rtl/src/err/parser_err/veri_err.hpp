/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_err.hpp
 * Summary  : error processer class for verilog syntax-analyzer 
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef ERR_PARSER_ERR_VERI_ERR_HPP_
#define ERR_PARSER_ERR_VERI_ERR_HPP_

#include <string>
#include <vector>
#include <list>
#include <sstream>

#include "singleton.hpp"

namespace rtl
{

using pavio_singleton :: Singleton;

class VeriNode;
class VeriMod;

/*
 * class VeriErr : Verilog pre-processer error handler
 *
 *   This class handles verilog pre-processer error collecting, organizing,
 * and output.
 *
 *   Has no init() function.
 *   Has void clean_up() function to clear inner data, back to status after
 * initialization or init() if has.
 *
 *   Use void append_err( ... ) to append one err record.
 *   Use const std::string& get_err_info( void ) to get all error information
 * in std::string type.
 *   Use bool has_err( void ) to determine whether there is error detected.
 *   
 *   Has some other functions to manipulate class behaviors.
 */
class VeriErr : public Singleton<VeriErr>
{
  friend class Singleton<VeriErr>;

  typedef std::string                String;
  typedef const String               CString;
  typedef std::list<String>          SList;
  typedef std::list<int>             IList;
  typedef std::stringstream          StringStream;

  public:
    void set_report_level( int l ) { _err_level = l; }

    // self-explanative
    int has_err( void ) const { return _has_err; }

    // self-explanative
    CString& get_err_info( void ) const { return _err_info; }

    // file manipulation
    void include_file( int line, CString& fname );
    void exclude_file( void );
    void back_to_file( int line );
    void reset_file( void );

    // second parse of syntax analysis

    void append_err( int level, int line, int col, VeriMod *mod,
                     VeriNode *extra, int err, CString& other );
    void append_err( int level, int line, int col, VeriMod *mod,
                     VeriNode *extra, int err )
    { append_err( level, line, col, mod, extra, err, _dummy ); }

    void append_err( int level, VeriNode *node, int err )
    { append_err( level, node, err, _dummy ); }
    void append_err( int level, VeriNode *node, int err, CString& other );

    // only for first parse of syntax analysis
    void append_err( int level, int line, int col, int err )
    {  append_err( level, line, col, err, _dummy ); }
    void append_err( int level, int line, int col, int err, CString& other);

    // clear inner states and error results, back to status after
    // initialization.
    void clean_up( void ) { clear(); };

  protected:  
    // dispatch error information into string
    void append_error_message(int level, int line, int col,
                              int err, CString& other );

    void append_file_message( );

    void append_mod_file( VeriMod *mod );

    // self-explanative
    String int2string( int in )
    {
      StringStream f;
      f << in;
      return f.str();
    }

    // clear everything, back to status after
    // construction.
    void clear( void );

  private:
     VeriErr( void );
    ~VeriErr( void );
 
    int     _err_level;
    String  _err_info; // error information in string-form
    SList   _fnames;
    IList   _flines;

    int     _fname_flag;  // if has file name not written
    int     _has_err;

    String  _dummy;
};

extern rtl::VeriErr * veri_err;

};

#endif // ERR_PARSER_ERR_VERI_ERR_HPP_
