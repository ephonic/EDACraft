/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_define.cpp
 * Summary  : verilog pre-processer define class functions
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include "general_err.hpp"
#include "veri_err_token.hpp"
#include "verilog_token.hpp"
#include "veri_preproc_tokens_status.hpp"

#include "veri_define.hpp"

namespace rtl
{

VeriDef::VeriDef( void ):
  _type(0),
  _num_vars(0),
  _name(""),
  _vars(NULL),
  _contents_string(),
  _contents_vars(),
  _var2idx()
{
}

VeriDef::~VeriDef( void )
{
  if( _vars )
  {
    delete[] _vars;
    _vars = NULL;
  }
  _name.clear();
  _contents_string.clear();
  _contents_vars.clear();
  _var2idx.clear();
}

void
VeriDef::clean_up( void )
{
  _contents_string.clear();
  _contents_vars.clear();
}

void
VeriDef::clear( void )
{
  // clear stuff after init()
  _contents_string.clear();
  _contents_vars.clear();

  // clear stuff in init() process
  if( _vars )
  {
    delete[] _vars;
    _vars = NULL;
  }
  _name.clear();
  _var2idx.clear();
}

int
VeriDef::init(int type, CString& name, const SVector& vars)
{
  _type     = type;
  _name     = name;

  if( type >= 2 )  // has variables
  {
    _num_vars = vars.size();
    _vars     = new String[_num_vars];

    DefVarRec rec;
    for( int i = 0 ; i < _num_vars ; ++i )
    {
      _vars[i] = vars[i];
      rec = _var2idx.insert( DefVarMap::value_type( vars[i], i ) );
      if ( !rec.second )
      {
        clear();
        return vDEFINE_VAR_DUPLICATED;
      }
    }
  }
  return OK;
}

int
VeriDef::parse(const VPPTVector& toks)
{
  if( _type == 0 || _type == 2 ) // no definitions
    return OK;
  else if( _type == 3 )  // the mose complicated type
  {
    String content = "";
    VPPTVector::const_iterator iccptv = toks.begin();
    DefVarMap::const_iterator idvm;
    int idx;

    for( ; iccptv != toks.end(); ++iccptv )
    {
      if( iccptv->id() == vtCOMM )
        continue;
      if( iccptv->id() == vtIDENT )
      {
        idvm = _var2idx.find( iccptv->s() );
        if( idvm != _var2idx.end() )
        {
          idx = idvm->second;
          _contents_string.push_back(content);
          _contents_vars.push_back(idx);
          content = "";
        }
        else
          content += iccptv->s();
      }
      else
        content += iccptv->s();
    }
    if( !content.empty() )
    {
      _contents_string.push_back(content);
      _contents_vars.push_back(NOT_EXIST);
    }
    return OK;
  }
  else if( _type == 1 )
  {
    String content = "";
    VPPTVector::const_iterator iccptv = toks.begin();

    for( ; iccptv != toks.end(); ++iccptv )
    {
      if( iccptv->id() == vtCOMM )
        continue;
      content.append( iccptv->s() );
    }

    if( !content.empty() )
    {
      _contents_string.push_back(content);
      _contents_vars.push_back(NOT_EXIST);
    }
    return OK;
  }
  return vPRE_NOT_KNOWN_ERR;
}

std::string
VeriDef::get_result(const VPPTVector& in)
{
  if( _type == 0 || _type == 2 )  // no definitions
    return "";

  String re = "";
  SVector::const_iterator cisv = _contents_string.begin();
  IVector::const_iterator ciiv = _contents_vars.begin();

  if( _type == 1 )
  {
    for( ;
         cisv != _contents_string.end() && ciiv != _contents_vars.end();
         ++cisv, ++ciiv
       )
    {
      re = re + (*cisv);
      if( *ciiv != NOT_EXIST )
        re += _name;
    }
    return re;
  }
  else if( _type == 3 )
  {
    for( ;
         cisv != _contents_string.end() && ciiv != _contents_vars.end();
         ++cisv, ++ciiv
       )
    {
      re = re + (*cisv);
      if( *ciiv != NOT_EXIST )
        re += in[*ciiv].s();
    }
    return re;
  }
  else
    return "";
}

};
