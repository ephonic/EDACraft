/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_define.hpp
 * Summary  : verilog pre-processer define class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PREPROC_VERILOG_VERI_DEFINE_HPP_
#define PREPROC_VERILOG_VERI_DEFINE_HPP_

#include <string>
#include <vector>
#include <map>

#include "veri_pretoken.hpp"

namespace rtl
{

/*
 * class VeriDef : 
 *     verilog pre-processer define class.
 *     parse, process, and anti-parse definitions & macros for verilog HDL
 *   source file.
 *
 *     Needs to call int init() function after constructer.
 *     Has void clean_up( void ) function to clean up inner data, back to status
 *   after init().
 *
 * status:
 *   0 for `define a
 *   1 for `define a        { sth... } 
 *   2 for `define a(b,...)
 *   3 for `define a(b,...) { sth... }
 */

class VeriDef
{
  typedef std::string             String;
  typedef const String            CString;
  typedef std::vector<String>     SVector;
  typedef std::vector<int>        IVector;
  typedef std::vector<VPPtok>     VPPTVector;
  typedef std::map<String, int>   DefVarMap;
  typedef std::pair<DefVarMap::iterator, bool> DefVarRec;

  public:
    VeriDef( void );
    ~VeriDef( void );

    // for macros' declaration
    int init(int type, CString& name, const SVector& vars);

    // clean up inner data, back to status after init()
    void clean_up( void );
    
    // feed tokens in vector mode, for macro's definition
    int parse(const VPPTVector& toks);
    
    // self-explanative, fded tokens in vector mode
    String get_result(const VPPTVector& in);
    
    // accessors
    int      type( void ) const { return _type; }
    CString& name( void ) const { return _name; }

  protected:

    // clean up everything, back to status after construction. 
    void clear( void );

  private:
    int        _type;
    int        _num_vars;
    String     _name;
    String    *_vars;
    SVector    _contents_string;
    IVector    _contents_vars;
    DefVarMap  _var2idx;
};

};

#endif // PREPROC_VERILOG_VERI_DEFINE_HPP_
