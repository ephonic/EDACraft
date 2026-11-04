/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_hash_define.cpp
 * Summary  : verilog pre-processer define class hash container functions.
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include "general_err.hpp"
#include "veri_hash_define.hpp"  

#ifdef  debug_hash33_
#include <iostream>
using std::cout;
using std::endl;
#endif

namespace rtl
{

int
VeriDefHash::hash_create( Uint size )
{
  clear();
  _size      = size;
  _hash_list = new VeriHNode*[size];
  for( Uint i = 0 ; i < size ; ++i )
  {
    _hash_list[i] = NULL;
  }
  return OK;
}  

int
VeriDefHash::hash_insert( CString& name, VeriDef *data)
{
  if( _size == 0 || _hash_list == NULL )
    hash_create(100);

  VeriHNode *p;
  Uint hash_key = hash_key33( name ) % _size;  
  int  same = IS_FALSE;

  if(hash_key >= _size)  
    return NOT_EXIST;  

  p = _hash_list[hash_key];

  if( p == NULL )
  {
    _hash_list[hash_key] = new VeriHNode;
    _hash_list[hash_key]->_name = name;  
    _hash_list[hash_key]->_data = data;  
    _hash_list[hash_key]->_next = NULL;  
  }
  else
  {
    VeriHNode *tail = NULL;
    while( p != NULL )
    {
      if( hash_cmp33( p->_name.c_str() , name.c_str() ) )
      {
        if( p->_data != data )
          delete p->_data;
        p->_data = data;
        same = IS_TRUE;
        break;
      }
      tail = p;
      p = p->_next;
    }
    if( same == IS_FALSE )
    {
      tail->_next = new VeriHNode;
      tail->_next->_name = name;  
      tail->_next->_data = data;  
      tail->_next->_next = NULL;  
    }
  }
  return OK;  
}

int
VeriDefHash::hash_delete( CString& name )
{
  if( _size == 0 || _hash_list == NULL )
    return NOT_EXIST;

  VeriHNode *p;  
  VeriHNode *q;  
  Uint hash_key = hash_key33( name ) % _size;  
      
  p = _hash_list[hash_key];
  q = _hash_list[hash_key];
  if( hash_key >= _size || NULL == p )
  {
    return NOT_EXIST;
  }

  while(p != NULL)
  {  
    if( hash_cmp33( p->_name.c_str() , name.c_str() ))
    {
      if(p != q)
      {
        q->_next = p->_next;
        delete p;
        p = NULL;
        break;
      }
      else
      {
        _hash_list[hash_key] = p->_next;
        delete p;
        break;
      }
    }  
    q = p;  
    p = p->_next;  
  }
  return OK;  
}

VeriDef*
VeriDefHash::hash_value( CString& name )
{
  if( _size == 0 || _hash_list == NULL )
    return NULL;

  Uint hash_key = hash_key33( name ) % _size;  
  VeriHNode *p = _hash_list[hash_key];  

  if(hash_key >= _size || NULL == p )  
  {
    return NULL;
  }

  while(p != NULL )
  {
    if( hash_cmp33( p->_name.c_str() , name.c_str() ))
    {
      return p->_data;
    }
    p = p->_next;  
  }  
  return NULL;
}  

void
VeriDefHash::clear( void )
{
  VeriHNode *p;  
  VeriHNode *q;  
  if( _hash_list != NULL )
  {
    for( Uint i = 0 ; i < _size ; ++i )
    {
      p = _hash_list[i];
      if( p != NULL )
      {
        while(p != NULL)
        {
          q = p;  
          p = p->_next;
          delete q;
        }
      }
    }
    delete[] _hash_list;
  }
  _hash_list = NULL;
  _size = 0;
}

void
VeriDefHash::clean_up( void )
{
  VeriHNode *p;  
  VeriHNode *q;  
  if( _hash_list != NULL )
  {
    for( Uint i = 0 ; i < _size ; ++i )
    {
      p = _hash_list[i];
      if( p != NULL )
      {
        while(p != NULL)
        {
          q = p;  
          p = p->_next;
          delete q;
        }
        _hash_list[i] = NULL;
      } // end if(p)
    } // end for
  } // end if( _hash_list != NULL )
}

#ifdef debug_hash33_
void
VeriDefHash::hash_print( void )
{
  int count = 0;  
  VeriHNode *p;  
  for( Uint i = 0 ; i < _size ; ++i )
  {
    p = _hash_list[i];  
    while(p != NULL)
    {
      count++;  
      p = p->_next;  
    }
    cout << "node " << i << " = " << count << endl;
    count = 0;  
  }
}
#endif

};
