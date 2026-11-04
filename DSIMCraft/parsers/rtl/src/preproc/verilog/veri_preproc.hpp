/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_preproc.hpp
 * Summary  : verilog pre-processer class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 * todo     : add esc_identifier, remove (8 *) attr_spec
 */

#ifndef PREPROC_VERILOG_VERI_PREPROC_HPP_
#define PREPROC_VERILOG_VERI_PREPROC_HPP_

#include "singleton.hpp"

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>

#include <string>
#include <vector>
#include <list>
#include <map>
#include <sstream>

#include "veri_pretoken.hpp"
#include "veri_define.hpp"
#include "veri_hash_define.hpp"

namespace rtl
{

#define _DEBUG_VERI_PROPROC_

using pavio_singleton::Singleton;

class Cfg_mgr;
class Src_mgr;
class VeriErr;

/*
 * class VeriPreProc :
 *     verilog pre-processer class deals with verilog HDL source code
 *   pre-processing operation.
 *
 *     Need to call int init() before parse.
 *     Need to call int parse() to parse source code.
 *     Has void clean_up() function to clean up inner data, back to status after
 *   init().
 *   
 */
class VeriPreProc : public Singleton<VeriPreProc> 
{
  friend class Singleton<VeriPreProc>;

  typedef std::string            String;
  typedef const String           CString;
  typedef unsigned int           Uint;
  typedef unsigned char          Uchar;
  typedef unsigned long long     Ulong;
  typedef std::vector<String>    SVector;
  typedef std::vector<int>       IVector;
  typedef std::vector<Uint>      UVector;
  typedef std::list<char * >     CPList;
  typedef std::map<String,Uint>  SUMap;
  typedef struct stat            Stat;
  typedef std::vector<Stat>      StVector;
  typedef std::vector<VPPtok>    VPPtVec;

  public:
    // call init before parse, return err-code
    int init( CString& fname );
    int init( CString& fname,
              const SVector& sys_dirs, const SVector& quote_dirs);

    int append_quote_dir( CString& dir );

    // self-explanative, return err-code
    int parse( void );

    // self-explanative functions to have error information
    int has_err( void ) const;
    CString& get_err_info( void ) const;

    // self-explanative
    CString& get_result( void ) const { return _output; }

    // Query an active object-like macro after preprocessing.  Parser clients
    // use this to recover object macros that the legacy token FSM can leave
    // unexpanded in some concatenation contexts.
    bool get_object_macro(const std::string& name, std::string& value);
    
    // clean up inner data, back to status after init().
    void clean_up( void );

  protected:

    // lexical token fsm function
    int get_next_tok( void );

    // syntax token fsm function
    //   if_flag : vpBORMAL, vpIF_SUCC, vpIF_FAIL, vpIF_SKIP
    //   across  : vpAC_ELSIF, vpAC_ELSE, vpAC_ENDIF
    int parse_recursivly(int if_flag, int &across );

    // search include file in user-defined directory
    String search_file_quote(CString& name);
    String search_file_sys(CString& name);

    // self-explanative, append included file in position for processing
    int  append_include_quote(Uint /*plot_line */, CString& fname);
    int  append_include_sys(Uint /*plot_line */, CString& fname);

    // compiler directive `line processing output
    void append_include_head(CString& fname);
    int  append_file_data(CString& fname);
    void append_line_info_tail(Uint lineno);
    void append_include_tail( Uint lineno );

    // cache file in input char * ptr ( _cur_s )
    int  cache_file( CString& fname );

    // manipulating pre-processing context recursivly
    void save_context( void );
    void change_context( void );
    void get_context( void );
    void end_file( void );

    int after_parse( void );

    int cnt_one_line( CString& content, int start );

    // perfect hash function to find keywordz-index for pre-processing
    Uint perfect_hash(register const char *str, register Uint len)
    {
      return (   len
               + _asso_values[(unsigned char)str[1]]
               + _asso_values[(unsigned char)str[0]]
          );
    }

    // using perfect hash function to determine keywordz identity
    int in_word_set (register const char *str, register Uint len);

    String int2string(int n)
    {
      std::stringstream f;
      f << n;
      return f.str();
    }

    void cpystring( const char *src, Uint length, Uint start, String& s )
    {
      Uint i;
      char *str = new char[length + 1];
      for( i = 0 ; i < length ; ++i )
        str[i] = src[start + i];
      str[i] = '\0';
      s = str;
      delete[] str;
    }

  public:
    // clear everything, back to status before construction.
    void clear();

  private:
    VeriPreProc( void );
    ~VeriPreProc( void );

    Cfg_mgr  *_cmgr;        ///< global configuration manager pointer
    Src_mgr  *_smgr;        ///< global source-code manager pointer

    String    _parse_name;  ///< parsed file name
    SVector   _fname;       ///< parsed file name in stack container
    StVector  _file_st;     ///< parsed file status in stack container
    CPList    _input;       ///< parsed file char * ptr in stack container

    VPPtVec   _toks;        ///< parsing tokens
    IVector   _status;      ///< self-explanative
    UVector   _linenos;     ///< self-explanative
    UVector   _cur_pos;     ///< self-explanative
    UVector   _pre_pos;     ///< self-explanative

    int       _cur_status;  
    String    _cur_name;
    Stat      _cur_st;      ///< current file status
    char     *_cur_s;       ///< current char * ptr
    Uint      _cur_length;
    Uint      _cur_line;
    Uint      _cur_col;
    Uint      _cpos;
    Uint      _ppos;
    VPPtok    _cur_tok;

    SVector   _quoted_dirs; ///< user defined included file searching directory
    SVector   _sys_dirs;    ///< default included file searching directory

    SUMap     _include_headers; ///< for include header double-inclusion-check

    String    _output;     ///< processed source code, for output to src-mgr
    int       _file_depth; ///< included file depth 
    VeriErr  *_err;        ///< processed error information

    VeriDefHash _define_hash;  ///< macros container

    // perfect hash part
    Uchar   _asso_values[256];
    String  _word_list[31];
    int     _total_keywords;
    Uint    _min_word_length;
    Uint    _max_word_length;
    int     _min_hash_value;
    int     _max_hash_value;
};

};

#endif // PREPROC_VERILOG_VERI_PREPROC_HPP_
