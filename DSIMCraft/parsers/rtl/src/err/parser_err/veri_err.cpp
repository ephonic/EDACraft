/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_pp_err.cpp
 * Summary  : error processer class functions for verilog syntax-analyzer 
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#include <iostream>
#include "general_err.hpp"
#include "veri_err_token.hpp"

#include "veri_module.hpp"
#include "veri_err.hpp"

namespace rtl
{

VeriErr *veri_err = NULL;

VeriErr::VeriErr( void )
  : _err_level( ERR_ALL )
  , _err_info("")
  , _fname_flag(IS_FALSE)
  , _has_err( IS_FALSE )
  , _dummy("")
{
  veri_err = this;
}

VeriErr::~VeriErr( void )
{
  clear();
}

void
VeriErr::clear( void )
{
  _fnames.clear();
  _flines.clear();
  _err_info.clear();
  _has_err = IS_FALSE;
  _fname_flag = IS_FALSE;
}

void
VeriErr::reset_file( void )
{
  _fnames.clear();
  _flines.clear();
  _fname_flag = IS_FALSE;
}

void
VeriErr::include_file( int line, CString& fname )
{
  _fnames.push_back( fname );
  _flines.push_back( line  );
  _fname_flag = IS_TRUE;
}

void
VeriErr::exclude_file( )
{
  if( !_fnames.empty() )
    _fnames.pop_back( );
  if( !_flines.empty() )
    _flines.pop_back( );
  if( !_fnames.empty() )
    _fname_flag = IS_TRUE;
}

void
VeriErr::back_to_file( int line )
{
  if( _flines.empty() )
    _flines.push_back( line );
  else
    _flines.back() = line;
  _fname_flag = IS_TRUE;
}

void
VeriErr::append_file_message( )
{
  SList::iterator is = _fnames.begin();
  IList::iterator it = _flines.begin();

  for( ; is != _fnames.end(); ++is, ++it )
  {
    _err_info += "  in file : " + (*is);
    _err_info += " : [" + int2string(*it) + "]\n";
  }
}

void
VeriErr::append_mod_file( VeriMod *mod )
{
  const SList& fname = mod->fname();
  const IList& fline = mod->fline();

  SList::const_iterator is = fname.begin();
  IList::const_iterator it = fline.begin();

  for( ; is != fname.end(); ++is, ++it )
  {
    _err_info += "  in file : " + (*is);
    _err_info += " : [" + int2string(*it) + "]\n";
  }
}

// mutual errors
void
VeriErr::append_err( int level, int line, int col, VeriMod *mod,
                     VeriNode *extra, int err, CString& other )
{
  append_mod_file( mod );
  String tmp;
  if( extra != NULL )
    tmp = int2string(extra->line()) + " " + int2string( extra->col() );
  append_error_message( level, line, col, err, other + tmp );
}

// for first parse of syntax analysis only
void
VeriErr::append_err( int level, int line, int col, int err, CString& other )
{
  if( _fname_flag == IS_TRUE )
  {
    append_file_message( );
    _fname_flag = IS_FALSE;
  }

  append_error_message(level, line, col, err, other);
}

// after first parse of syntax analysis
void
VeriErr::append_err( int level, VeriNode *node, int err, CString& other )
{
  append_mod_file( node->birth_mod() );
  append_error_message( level, node->line(), node->col(), err, other );
}

void
VeriErr::append_error_message(int level, int line, int col,
                           int err, CString& other)
{
  // dispatch oprand-code for error level
  if( level < _err_level )
    return;

  if( level >= ERR_ERROR )
  {
    _has_err = IS_TRUE;
  }

  switch( level )
  {
    case ERR_DEBUG : _err_info += " debug"; break;
    case ERR_COMM  : _err_info += " comment"; break;
    case ERR_WARN  : _err_info += " warning"; break;
    case ERR_ERROR : _err_info += " error"; break;
    case ERR_FATEL : _err_info += " fatel"; break;

    default:
      _err_info += " unknown"; break;
  }

  _err_info += "[" + int2string(err) + "]";
  _err_info += "[" + int2string(line) + " : " + int2string(col) + "]: ";

  // dispatch error type for detail information
  switch( err )
  {
    case vMOD_MODULE_NOT_USED: _err_info += "module is outside the selected top hierarchy"; break;
    case vMOD_MODULE_INST_CYCLIC: _err_info += "cyclic module instantiation involving"; break;
    case vMOD_MODULE_REDEFINE: _err_info += "duplicate module definition"; break;
    case vMOD_TOP_MODULE_MISSING: _err_info += "top module not found"; break;
    case vFUNC_REDEFINE: case vTASK_REDEFINE:
    case vVAR_VAR_REDEFINE: case vVAR_TFMG_REDEFINE: case vVAR_UNKNOWN_REDEFINE:
    case vINT_TFMG_REDEFINE: case vINT_UNKNOWN_REDEFINE:
    case vGENVAR_VAR_REDEFINE: case vGENVAR_PARAM_REDEFINE: case vGENVAR_TFMG_REDEFINE: case vGENVAR_UNKNOWN_REDEFINE:
    case vPARAM_VAR_REDEFINE: case vPARAM_PARAM_REDEFINE: case vPARAM_TFMG_REDEFINE: case vPARAM_UNKNOWN_REDEFINE:
    case vGATE_INST_REDEFINE: case vMOD_INST_REDEFINE: case vLABEL_REDEFINE: case vTF_PORT_REDEFINE:
    case vINT_VAR_REDEFINE: _err_info += "variable name is redefined or conflicts with an imported symbol"; break;
    case vSEC_SYMBOL_NOT_FOUND: _err_info += "identifier is unknown or not visible in this scope"; break;
    case vSEC_TF_NOT_FOUND: _err_info += "task/function is unknown or not supported"; break;
    case vSEC_SYMBOL_MIS_MATCH: _err_info += "identifier does not name a supported value in this expression"; break;
    case vSEC_CALLER_REUNFOLD: _err_info += "recursive or repeated function expansion cannot be elaborated"; break;
    case vSEC_MOD_PORT_MISMATCH: _err_info += "invalid module port declaration or unresolved declaration dependency"; break;
    case vSEC_CALLER_PORT_MISMATCH: case vSEC_CALLER_PORT_NOT_COMPLETE: _err_info += "task/function argument count or type does not match its formal ports"; break;
    case vSEC_CONST_VALUE_NOT_CALC: _err_info += "expression requires a supported elaboration-time constant"; break;
    case vSEC_RANGE_CANNOT_CALC: case vSEC_VAR_RANGE_NOT_CALC: _err_info += "declaration range requires known integral constant bounds"; break;
    case vSEC_PRI_NOT_OTHER: case vSEC_ARRAY_NOT_OTHER: _err_info += "expression requires an integral value, not an unpacked array or declaration"; break;
    case vSEC_MOD_PARAM_MISMATCH:
      _err_info += "invalid, duplicate or nonconstant module parameter override";
      break;
      /* verilog number error flag */
    case vCAST_WIDTH_INVALID: _err_info += "cast width must be an integral constant in 1..1048576"; break;
    case vNUNKNOWN                : _err_info += ""; break;
    case vNINVAL_CHAR             : _err_info += ""; break;
    case vNCHOPPED                : _err_info += ""; break;
    case vNNEW_FAIL               : _err_info += ""; break;
    case vNBITS_TOO_LARGE         : _err_info += ""; break;
    case vNDOUBLE_TWOS_COMP       : _err_info += ""; break;
    case vNDEC_X_Z                : _err_info += ""; break;
    case vNRADIX_UNKNOWN          : _err_info += ""; break;
    case vNFORMAT                 : _err_info += ""; break;
    case vNNUMBER_OUT_BITS        : _err_info += ""; break;
    case vNUNARY_OP_NOT_FOUND     : _err_info += ""; break;
    case vNBINARY_OP_NOT_FOUND    : _err_info += ""; break;
    case vNVALUE_USED_WITHOUT_INIT: _err_info += ""; break;
    case vNARITH_OP_XZ            : _err_info += ""; break;
    case vNLOGIC_OP_NALIGN        : _err_info += ""; break;
    case vNSHIFT_ROUND_TOO_LARGE  : _err_info += ""; break;
    case vNOP_NOT_SUPPORT         : _err_info += ""; break;

    /* expression children type error */
    case vCHILD_TYPE_PRI_EXP      : _err_info += ""; break;
    case vCHILD_TYPE_UNA_EXP      : _err_info += ""; break;
    case vCHILD_TYPE_BIN_EXP      : _err_info += "invalid operands for binary expression"; break;
    case vCHILD_TYPE_RANGE_EXP    : _err_info += ""; break;
    case vCHILD_TYPE_MULTI_EXP    : _err_info += "invalid operand in concatenation or argument list"; break;
    case vCHILD_TYPE_CALL_EXP     : _err_info += ""; break;
    case vCHILD_TYPE_ARRAY_EXP    : _err_info += "invalid array identifier or select expression"; break;
    case vCHILD_TYPE_EVENT_EXP    : _err_info += ""; break;
    case vCHILD_TYPE_ASSIGN_EXP   : _err_info += ""; break;
    case vCHILD_TYPE_MCONCAT_EXP  : _err_info += ""; break;

    case vCHILD_TYPE_DELAY_EXP    : _err_info += ""; break;
    case vCHILD_TYPE_DRIVE_EXP    : _err_info += ""; break;

    case vCHILD_TYPE_NAMED_PARAM_EXP : _err_info += ""; break;
    case vCHILD_TYPE_SIGN_FUNC_EXP   : _err_info += ""; break;
    case vCHILD_TYPE_UNSIGN_FUNC_EXP : _err_info += ""; break;

    /* statement children type error */
    case vCHILD_TYPE_BLOCK_STMT             : _err_info += ""; break;
    case vCHILD_TYPE_CASE_STMT              : _err_info += ""; break;
    case vCHILD_TYPE_COND_STMT              : _err_info += ""; break;
    case vCHILD_TYPE_DISABLE_STMT           : _err_info += ""; break;
    case vCHILD_TYPE_EVENT_STMT             : _err_info += ""; break;
    case vCHILD_TYPE_LOOP_STMT              : _err_info += ""; break;
    case vCHILD_TYPE_NON_BLOCK_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_PAR_BLOCK_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_PROC_CONT_ASSIGN_STMT  : _err_info += ""; break;
    case vCHILD_TYPE_PROC_TIME_CONTROL_STMT : _err_info += ""; break;
    case vCHILD_TYPE_SEQ_BLOCK_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_WAIT_STMT              : _err_info += ""; break;

    case vCHILD_TYPE_DEFAULT_CASE_ITEM      : _err_info += ""; break;
    case vCHILD_TYPE_CASE_ITEM              : _err_info += ""; break;
    case vCHILD_TYPE_CASE_ITEM_LIST         : _err_info += ""; break;

    case vCHILD_TYPE_FUNC_BLOCK_STMT        : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_CASE_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_COND_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_LOOP_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_SEQ_BLOCK_STMT    : _err_info += ""; break;

    case vCHILD_TYPE_FUNC_DEFAULT_CASE_ITEM : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_CASE_ITEM         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_CASE_ITEM_LIST    : _err_info += ""; break;

    case vCHILD_TYPE_SYS_CALL_STMT          : _err_info += ""; break;
    case vCHILD_TYPE_CALL_STMT              : _err_info += ""; break;

    case vCHILD_TYPE_STMT_LIST_STMT         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_STMT_LIST_STMT    : _err_info += ""; break;
    case vCHILD_TYPE_CONT_ASSIGN_STMT       : _err_info += ""; break;
    case vCHILD_TYPE_INIT_STMT              : _err_info += ""; break;
    case vCHILD_TYPE_ALWAYS_STMT            : _err_info += ""; break;

    /* Instantiation type error */
    case vCHILD_TYPE_GEN_BLOCK              : _err_info += ""; break;
    case vCHILD_TYPE_GEN_COND               : _err_info += ""; break;
    case vCHILD_TYPE_GEN_DEFAULT_CASE       : _err_info += ""; break;
    case vCHILD_TYPE_GEN_CASE_ITEM          : _err_info += ""; break;
    case vCHILD_TYPE_GEN_CASE_ITEM_LIST     : _err_info += ""; break;

    case vCHILD_TYPE_GEN_ITEM_LIST          : _err_info += ""; break;

    case vCHILD_TYPE_MOD_INSTANCE           : _err_info += ""; break;
    case vCHILD_TYPE_MOD_INSTANTIATION      : _err_info += ""; break;
    case vCHILD_TYPE_GATE_INSTANTIATION     : _err_info += ""; break;

    case vCHILD_TYPE_GEN_LOOP               : _err_info += ""; break;
    case vCHILD_TYPE_GEN_CASE               : _err_info += ""; break;

    /* declaration type error */
    case vCHILD_TYPE_TF_DECL                : _err_info += ""; break;
    case vCHILD_TYPE_TASK_PORT_LIST         : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_PORT_LIST         : _err_info += ""; break;
    case vCHILD_TYPE_TASK_DECL              : _err_info += ""; break;
    case vCHILD_TYPE_TASK_ITEM_DECL_LIST    : _err_info += ""; break;
    case vCHILD_TYPE_BLOCK_ITEM_DECL_LIST   : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_ITEM_DECL_LIST    : _err_info += ""; break;
    case vCHILD_TYPE_VAR_DECL               : _err_info += ""; break;
    case vCHILD_TYPE_PARAM_DECL             : _err_info += "parameter initializer requires a supported integral constant expression"; break;
    case vCHILD_TYPE_PARAM_DECL_LIST        : _err_info += ""; break;
    case vCHILD_TYPE_FUNC_DECL              : _err_info += ""; break;
    case vCHILD_TYPE_PORT_DECL_LIST         : _err_info += ""; break;


    case vSEC_LOOP_JUDGE_FAILURE: _err_info += "generate loop requires a known constant condition and bounded genvar iteration"; break;
    case vSEC_IF_COND_NOT_CALC: _err_info += "generate if requires a known constant condition"; break;
    case vSEC_CASE_COND_NOT_CALC: _err_info += "generate case requires a constant selector"; break;
    case vSEC_CASE_LABEL_NOT_CALC: _err_info += "generate case label must be constant"; break;
    case vNOT_KNOWN_ERR: default:
      _err_info += "invalid or unsupported Verilog construct";
      break;
  }

  if(!other.empty())_err_info += " " + other;
  _err_info += "\n";
}

};
