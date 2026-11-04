/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_pretoken.hpp
 * Summary  : verilog pre-processer define class
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PREPROC_VERILOG_VERI_PRETOKEN_HPP_
#define PREPROC_VERILOG_VERI_PRETOKEN_HPP_

#include <string>

#include "general_err.hpp"

namespace rtl
{

/*
 * class VPPtok :
 *     verilog pre-processer token
 */
class VPPtok
{
  typedef std::string    String;
  typedef const String   CString;
  public:
     VPPtok()
       :
         _s(""),
         _id(NONE),
         _type(0),
         _val(0)
     {};

     VPPtok( int id, CString& s, int type, int val ):
       _s(s),
       _id(id),
       _type(type),
       _val(val)
    {}

    ~VPPtok() { clear(); };

    // accessors
    int      id   () const { return _id;   }
    CString& s    () const { return _s;    }
    int      type () const { return _type; }
    int      val  () const { return _val;  }

    // mutators
    void set_id   (int id     ) { _id    = id;   }
    void set_s    (CString& s ) { _s     = s;    }
    void set_type (int type   ) { _type  = type; }
    void set_val  (int val    ) { _val   = val;  }

    // mutate a whole structure
    void set( int id, CString& s, int type, int val );

    void clear()
    {
      _s    = "";
      _id   = 0;
      _type = 0;
      _val  = 0;
    }

  protected:

  private:
    String  _s;
    int     _id;
    int     _type;
    int     _val;
};

};

#endif // PREPROC_VERILOG_VERI_PRETOKEN_HPP_
