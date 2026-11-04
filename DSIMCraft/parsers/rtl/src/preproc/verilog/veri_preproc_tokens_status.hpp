/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : veri_preproc_tokens_status.hpp
 * Summary  : token definitions of verilog pre-processer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef PREPROC_VERILOG_VERI_PREPROC_TOKENS_STATUS_
#define PREPROC_VERILOG_VERI_PREPROC_TOKENS_STATUS_

namespace rtl
{

/*
 * for general purpose
 */
enum VERI_PRE_PARSER_TOKEN
{
  vtUNKNOWN   = 3000,
  vtIDENT     = 3001,

  vtDIGIT     = 3002,
  vtSTR       = 3003,
  vtWHITE     = 3004,
  vtNL        = 3005,
  vtSTR_ERR   = 3007,
  vtCOMM      = 3008,
  vtCOMM_ERR  = 3009,
  vtLINE      = 3010,
  vtTRAN      = 3011,

  vtLB        = 3012,
  vtRB        = 3013,
  vtLBB       = 3014,
  vtRBB       = 3015,
  vtCOMMA     = 3016,
  vtADD       = 3017,
  vtSUB       = 3018,
  vtDOT       = 3019,
  vtCOLON     = 3020,
  vtMOD       = 3021,
  vtLOGIC_EQ  = 3022,
  vtLOGIC_NEG = 3023,
  vtLOGIC_INEQ= 3024,
  vtCASE_EQ   = 3033,
  vtCASE_INEQ = 3034,
  vtDELAY     = 3036,
  vtANDAND    = 3037,
  vtAND       = 3038,
  vtPOW       = 3039,
  vtMUL       = 3040,
  vtLE        = 3041,
  vtLT        = 3042,
  vtGE        = 3043,
  vtGT        = 3044,
  vtLOGIC_LS  = 3045,
  vtLOGIC_RS  = 3046,
  vtARITH_LS  = 3047,
  vtARITH_RS  = 3048,
  vtXORN      = 3049,
  vtXOR       = 3050,
  vtOROR      = 3051,
  vtOR        = 3052,
  vtXNOR_REDUC= 3053,
  vtNAND_REDUC= 3054,
  vtNOR_REDUC = 3055,
  vtNEG_B     = 3056,
};

/*
 *  status enum for pre-processer lexical tokens
 */
enum veri_preprocesser_status
{
  vpSTART      = 4000,

  vpUNDEF_0    = 4001,
  vpINCLUDE_0  = 4005,
  vpLINE_0     = 4010,

  vpDEFINE_0   = 4011,
  vpDEFINE_1   = 4012,
  vpDEFINE_2   = 4013,
  vpDEFINE_3   = 4014,
  vpDEFINE_4   = 4015,
  vpDEFINE_5   = 4016,

  vpDEF_ANTI_0 = 4017,
  vpDEF_ANTI_1 = 4018,
  vpDEF_ANTI_2 = 4019,
  vpDEF_ANTI_3 = 4020,

  vpUNCONN_DRIVE_0 = 4025,
  vpTIMESCALE_0    = 4027,
  vpNON_CONN_DRIVE_0    = 4040,
  vpDEFAULT_NETTYPE_0   = 4041,
  vpCELL_DEF_0          = 4042,

  vpIFDEF_0             = 4030,
  vpIFNDEF_0            = 4031,
  vpIF_SUCC_0           = 4032,
  vpIF_FAIL_0           = 4033,
  vpIF_SKIP_0           = 4034,
};

/*
 *  status enum for pre-processer syntax parser, if and file flags 
 */
enum veri_if_status
{
  vpNORMAL  = 3,
  vpIF_SUCC = 4,
  vpIF_FAIL = 5,
  vpIF_SKIP = 6,

  vpAC_ENDIF = 7,
  vpAC_ELSIF = 8,
  vpAC_ELSE  = 9,
};

/*
 *  tokens enum for pre-processer syntax parser
 */
enum verilog_preprocesser_token
{
  vpUNDEF             = 2101,
  vpINCLUDE           = 2102,
  vpLINE              = 2103,
  vpENDIF             = 2104,
  vpRESET_ALL         = 2105,
  vpELSE              = 2106,
  vpELIF              = 2107,
  vpDEFINE            = 2108,
  vpUNCONN_DRIVE      = 2109,
  vpEND_CELL_DEF      = 2110,
  vpTIMESCALE         = 2111,
  vpIFDEF             = 2112,
  vpIFNDEF            = 2113,
  vpNON_CONN_DRIVE    = 2114,
  vpDEFAULT_NETTYPE   = 2115,
  vpCELL_DEF          = 2116,

  vpDEF_VAR           = 2117,
};

/*
 *  status enum for pre-processer lexical parser 
 */
enum veri_token_status
{
  vtSTART    = 30000,

  vtNEG_0    = 30001, 
  vtSTR_0    = 30002,
  vtDELAY_0  = 30003,
  vtAND_0    = 30005,
  vtMUL_0    = 30009,
  vtCOMM_0   = 30011,
  vtLESS_0   = 30012,
  vtEQ_0     = 30013,
  vtGREAT_0  = 30014,
  vtIDENT_0  = 30015,
  vtIDENT_1  = 30016,
  vtANTI_0   = 30017,
  vtXOR_0    = 30018,
  vtP_0      = 30019,
  vtOR_0     = 30020,
  vtREV_0    = 30021,
  vtDIGIT_0  = 30022,

  vtSTR_1    = 30030,
  vtNEG_1    = 30031,
  vtCOMM_1   = 30032,
  vtCOMM_2   = 30033,
  vtCOMM_3   = 30034,
  vtCOMM_4   = 30035,
  vtLESS_1   = 30036,
  vtEQ_1     = 30037,
  vtGREAT_1  = 30038,
  vtP_1      = 30039,
  vtP_2      = 30040,
};

};

#endif // PREPROC_VERILOG_VERI_PREPROC_TOKENS_STATUS_
