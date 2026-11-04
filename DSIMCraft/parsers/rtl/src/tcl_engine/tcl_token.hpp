/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : tcl_token.hpp
 * Summary  : token definitions of tcl-command line engine 
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef TCL_ENGINE_TCL_TOKEN_
#define TCL_ENGINE_TCL_TOKEN_

namespace p_tcl_engine
{

/*
 * tcl engine expression finding direction
 */
enum TCL_ENGINE_DIR
{
  pTCL_UP   = 0,
  pTCL_DOWN = 1,
};

/*
 * tcl command line engine error tokens
 */
enum TCL_ENGINE_ERR
{
  pTCL_WRONG_ARGUMENT          = 10012,
  pTCL_WRONG_ARGUMENT_TYPE     = 10013,
  pTCL_OP_ERROR                = 10014,
  pTCL_OP_UNKNOWN_ERROR        = 10015,
  pTCL_DIR_OPEN                = 10016,
  pTCL_DIV_0_ERROR             = 10020,
};

enum TCL_BOOL
{
  OK       = 0,
  IS_TRUE  = 1,
  IS_FALSE = 0,
};

};
#endif // TCL_ENGINE_TCL_TOKEN_
