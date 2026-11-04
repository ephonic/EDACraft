/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_hash_define.hpp
 * Summary  : verilog pre-processer define class hash container
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PREPROC_VERILOG_VERI_HASH_DEFINE_HPP_
#define PREPROC_VERILOG_VERI_HASH_DEFINE_HPP_

#include <string.h>

#include <string>

#include "veri_define.hpp"

namespace rtl
{

/*
 * class VeriDefHash :
 *     verilog pre-processer definition hash-container contains definitions
 *   in hash_char33 algorithm.
 *
 *     Needs to call int hash_create( Uint size ) before using.
 *     Has void clean_up() function to clean up inner data, back to status after
 *   hash_create().
 */
class VeriDefHash{
  typedef unsigned int   Uint;
  typedef std::string    String;
  typedef const String   CString;

  friend class VeriPreProc;

  public:
    VeriDefHash( void )
      :
        _size(0),
        _hash_list(NULL)
    {};

    ~VeriDefHash( void )
    {
      clear();
    };

    // for initialization, create space for hash container
    int hash_create( Uint size );

    // data will be deleted in destruction function
    int hash_insert( CString& name, VeriDef *data );

    // delete data by your self
    int hash_delete( CString& name );

    // no memory change
    VeriDef* hash_value( CString& name );

    // clean up inner data, back to status after hash_create()
    void clean_up( void );

    // for debug usage, print out hash container load information to stdout
    void hash_print( void );

  protected:
    // hash compare33 algorithm, string comparison function
    bool hash_cmp33( const char *src, const char *des )
    {
      return ( 0 == strcmp(src, des));
    }

    // calculate idx for hash_cmp33 algorithm
    Uint hash_key33( CString& name )
    {
      const char *p = name.c_str();
      Uint  nhash = 5381;
      while( (*p) != '\0' )
      {
        nhash += (nhash << 5) + *p;
        ++p;
      }
      return nhash;
    }

    // clean up everything, back to status after construcion
    void clear( void );

  private:
    /*
     * inner structure for containing one definition hash container node
     */
    class VeriHNode{
      public:
        VeriHNode()
          :
            _name(""),
            _data(NULL),
            _next(NULL)
        {};

        ~VeriHNode()
        {
          if( _data )
            delete _data;
          _data = NULL;
        }
     
        String     _name;
        VeriDef   *_data;  
        VeriHNode *_next;  
    };

    Uint         _size;
    VeriHNode  **_hash_list;  
};  

};

#endif // PREPROC_VERILOG_VERI_HASH_DEFINE_HPP_
