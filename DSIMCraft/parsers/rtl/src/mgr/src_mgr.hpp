/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : src_mgr.hpp
 * Summary  : class Src_mgr will hold verilog synthesis configurations
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#ifndef MGR_SRC_MGR_HPP_
#define MGR_SRC_MGR_HPP_

#include "singleton.hpp"

#include <string>

#include "general_err.hpp"

namespace rtl
{

  using pavio_singleton::Singleton;

/* 
 * class Src_mgr :
 *     source code manager, holds source code for each time processing 
 *
 *       Has void clean_up( void ) function to clear inner data, back to status
 *     after initialization or init() if has.
 *
 *   contents :
 *     source code in std::string type
 *
 */
class Src_mgr : public Singleton<Src_mgr>
{
  friend class Singleton<Src_mgr>;

  typedef std::string   String;
  typedef const String  CString;

  public:
    Src_mgr( void )  {};
    ~Src_mgr( void ) {};

    // self-explanative mutators
    void set_src( CString& str ) { _src = str; }
    void set_fname( CString& fname ) { _fname = fname; }

    // self-explanative accessors
    char* src( void ) const { return (char*)_src.c_str(); }
    int src_len( void ) const { return _src.size(); }
    CString& fname( void ) const { return _fname; }

    // clear inner data, back to status after initialization.
    void clean_up( void ) { clear(); };

  protected:
    
    // clear everything, back to status after construction.
    void clear( void );

  private:
    String _fname;
    String _src;
};

};

#endif // MGR_SRC_MGR_HPP_

