/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : general_err.hpp
 * Summary  : token definitions of general errors
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */
#ifndef ERR_GENERAL_ERR_HPP_
#define ERR_GENERAL_ERR_HPP_

namespace rtl
{

/*
 * general tokens for error definitions
 */
enum GENERAL_ERR_TOK
{
  NOT_EXIST = -1,
  NONE   = 0,
  OK     = 0,
  ERR    = 5050,
  WARN   = 5051,
  FATEL  = 5049
};

enum ERR_LEVEL
{
  ERR_DEBUG   = 0,
  ERR_ALL     = 1,
  ERR_COMM    = 2,
  ERR_WARN    = 3,
  ERR_ERROR   = 4,
  ERR_FATEL   = 5,
};

/*
 *  general tokens for boolin substitution
 *    : for robust programming
 */
enum BOOLIN
{
  IS_TRUE  = 0,
  IS_FALSE = 1,
};

};

#endif // ERR_GENERAL_ERR_HPP_
