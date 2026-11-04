/* 
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : verilog_token.hpp
 * Summary  : token definitions of verilog parser & pre-processer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

#ifndef TOKEN_VERILOG_TOKEN_HPP_
#define TOKEN_VERILOG_TOKEN_HPP_

#ifndef RANGE_DEFAULT
#define RANGE_DEFAULT 0
#endif

#ifndef DEFAULT_DRIVE_FROM
#define DEFAULT_DRIVE_FROM vpSTRONG1
#endif

#ifndef DEFAULT_DRIVE_TO
#define DEFAULT_DRIVE_TO vpSTRONG0
#endif

enum VERI_RADIX
{
  vBIN =  2,
  vOCT =  8,
  vDEC = 10,
  vHEX = 16,
};

enum VERI_NUM_DIGIT   ///<possible value for each element of _val
{
  V0   = 0,
  V1   = 1,
  VX   = 2,
  VZ   = 3,
};

enum VERI_SCOPE_TYPE
{
  vMOD_SCOPE = 1,
  vTASK_SCOPE = 2,
  vFUNC_SCOPE = 3,
  vNAMED_BLOCK_SCOPE = 4,
};

enum VERI_SEQUENCE_RET
{
  vSEARCH_LABEL = 11,
  vSEARCH_DECL  = 22,
};

enum VERI_SEC_PARSE_STATUS
{
  vSTART_S = 0,

  vGET_CALL_EXP_S = 1,

  vIF_S         = 2,
  vSHORT_CUT_S  = 3,
  vCALL_S       = 4,
  vSEARCH_DECL_S= 5,
  vARRAY_S      = 6,
  vDECL_S       = 7,
  vENUM_VARS_S  = 8,

  vEND_S        = 10,

};

enum VERI_SYMBOL_TABLE_RETURN
{
  vsMATCH     = 1,
  vsMISMATCH  = 2,
  vsNOT_FOUND = 3,
};

enum VERI_PARSE_HINT
{
  vhNONE = 0,

  vhPARSE_DECL  = 4,
  vhPARSE_GET   = 5,
  vhPARSE_LABEL = 6,

  vhPARSE_CALC  = 10,
  vhPARSE_HIDE  = 11,
  vhPARSE_ERR   = 12,
};

/*
 * operator
 */
enum VERI_OP
{
  /* unary */
  vtUADD  = 11,   // +
  vtUSUB  = 12,   // -
  vtUNEG  = 13,   // ~
  vtUAND  = 14,   // &
  vtUOR   = 15,   // |
  vtUNAND = 16,   // ~&
  vtUNOR  = 17,   // ~|
  vtUXNOR = 18,   // ~^
  vtUNOT  = 19,   // !
  vtUXOR  = 20,   // ^
  vtUPOSE = 21,   // posedge
  vtUNEGE = 22,   // negedge
  vtUPREINC = 60, vtUPREDEC = 61, vtUPOSTINC = 62, vtUPOSTDEC = 63,

  // Explicit cast nodes use the binary AST: constant width and operand.
  vtCAST_SIZE = 64, vtCAST_SIGNED4 = 65, vtCAST_UNSIGNED4 = 66,
  vtCAST_SIGNED2 = 67, vtCAST_UNSIGNED2 = 68,

  // Self-determined integer/vector system functions.
  vtSYS_BITS=70, vtSYS_CLOG2=71, vtSYS_ISUNKNOWN=72,
  vtSYS_COUNTONES=73, vtSYS_ONEHOT=74, vtSYS_ONEHOT0=75,
  vtSYS_RANGE_BITS=76, // Internal packed data-type range query.
  vtSYS_COUNTBITS=77, vtSYS_DIMENSIONS=78, vtSYS_UNPACKED_DIMENSIONS=79,
  vtSYS_LEFT=80, vtSYS_RIGHT=81, vtSYS_LOW=82, vtSYS_HIGH=83,
  vtSYS_INCREMENT=84, vtSYS_SIZE=85, vtSYS_QUERY_TYPE=86,

  vtBWLEQ=87, vtBWLNEQ=88, vtBINSIDE=89, vtSTREAM_LEFT=90, vtSTREAM_RIGHT=91,
  vtSYS_RANDOM=92, vtSYS_URANDOM=93, vtSYS_URANDOM_RANGE=94,
  vtSYS_RANDOM_SEEDED=95, vtSYS_URANDOM_SEEDED=96,
  vtSYS_SAMPLED=97, vtSYS_PAST=98, vtSYS_ROSE=99, vtSYS_FELL=100,
  vtSYS_STABLE=101, vtSYS_CHANGED=102,

  vtSYS_SFORMATF=103, vtSYS_TEST_PLUSARGS=104, vtSYS_VALUE_PLUSARGS=105,
  vtSYS_FOPEN=106, vtSYS_FGETC=107, vtSYS_UNGETC=108, vtSYS_FEOF=109,
  vtSYS_FGETS=110, vtSYS_FTELL=111, vtSYS_FSEEK=112, vtSYS_REWIND=113, vtSYS_SSCANF=114, vtSYS_FSCANF=115, vtSYS_FREAD=116,
  vtSYS_CAST=117,
  vtCAST_REAL=118, vtCAST_SHORTREAL=119,
  vtSYS_ITOR=120, vtSYS_RTOI=121, vtSYS_REALTOBITS=122, vtSYS_BITSTOREAL=123,
  vtSYS_SHORTREALTOBITS=124, vtSYS_BITSTOSHORTREAL=125,
  vtCAST_STRING=126, vtCAST_CHANDLE=127,
  vtSYS_TYPENAME=128,

  /* binary */
  vtBPOW  = 23,   // **
  vtBNAND = 24,   // ~&
  vtBNOR  = 25,   // ~|
  vtBXNOR = 26,   // ~^
  vtBMOD  = 27,   // %
  vtBMUL  = 28,   // *
  vtBDIV  = 29,   // /
  vtBADD  = 30,   // +
  vtBSUB  = 31,   // -
  vtBLRS  = 32,   // >>
  vtBLLS  = 33,   // <<
  vtBARS  = 34,   // >>>
  vtBALS  = 35,   // <<<
  vtBLT   = 36,   // <
  vtBGT   = 37,   // >
  vtBLE   = 38,   // <=
  vtBGE   = 39,   // >=
  vtBLEQ  = 40,   // ==
  vtBLIEQ = 41,   // !=
  vtBCEQ  = 42,   // ===
  vtBCIEQ = 43,   // !==
  vtBSAND = 44,   // &
  vtBSXOR = 45,   // ^
  vtBSOR  = 46,   // |
  vtBDAND = 47,   // &&
  vtBDOR  = 48,   // ||

  vtASSIGN = 49,

  vtMULTI_CONCAT = 50,
  
  /* ternery */
  vtQUES  = 58,
  vtSEMI  = 59,
};

inline bool veri_is_file_function(int op) { return (op>=vtSYS_FOPEN && op<=vtSYS_REWIND) || op==vtSYS_FREAD; }
inline bool veri_is_testbench_function(int op) { return op>=vtSYS_SFORMATF && op<=vtSYS_FREAD; }
inline bool veri_is_random(int op) { return op>=vtSYS_RANDOM && op<=vtSYS_URANDOM_SEEDED; }
inline bool veri_is_sampled(int op) { return op>=vtSYS_SAMPLED && op<=vtSYS_CHANGED; }

inline bool veri_is_cast(int op) { return (op>=vtCAST_SIZE && op<=vtCAST_UNSIGNED2)||op==vtCAST_REAL||op==vtCAST_SHORTREAL||op==vtCAST_STRING||op==vtCAST_CHANDLE; }
inline bool veri_is_real_function(int op) {return op>=vtSYS_ITOR&&op<=vtSYS_BITSTOSHORTREAL;}

inline bool veri_is_array_query(int op) { return op>=vtSYS_DIMENSIONS && op<=vtSYS_SIZE; }
inline bool veri_is_system_unary(int op) { return op>=vtSYS_BITS && op<=vtSYS_QUERY_TYPE; }

enum VERI_MULTI_EXP_TYPE
{
  vemCONCAT_EXP     = 1,
  vemCOMMA_EXP      = 2,
  vemEVENT_EXP      = 3,
  vemPORT_EXP       = 4,
  vemPORT_INST_EXP  = 5,
  vemINSIDE_SET=6, vemINSIDE_RANGE=7, vemDYNAMIC_NEW=8,
  vemOBJECT_NEW=13, vemNULL=14,
  vemASSIGN_PATTERN=9, vemPATTERN_DEFAULT=10, vemPATTERN_INDEX=11,
  vemPATTERN_REPEAT=12,
};

enum VERI_PRI_EXP_TYPE
{
  veVAR    = 1,
  veSTR    = 2,
  veNUM    = 3,
  veQUEUE_LAST = 4,
};

enum VERI_RANGE_EXP_TYPE
{
  vrSINGLE  = 1,
  vrSEMI    = 2,
  vrRAN_ADD = 3,
  vrRAN_SUB = 4,
  vrOPEN    = 5, // Unsized unpacked formal dimension; never an expression select.
  vrQUEUE = 6, vrASSOC_INT = 7, vrASSOC_STRING = 8, vrASSOC_UINT = 9, vrASSOC_CLASS = 10,
};

/*
 * verilog token type
 */
enum VERI_TOK_TYPE
{
  vtDECL    = 11,
  vtINST    = 12,
  vtSTMT    = 13,
  vtEXP     = 14,

  vtSYS_VAR = 15,
  vtVAR     = 16,
  vtPARAM   = 17,
  vtLABEL   = 18,
  vtINT     = 19,
  vtGENVAR  = 20,
  vtTFVAR   = 21,
  vtTYPE    = 22, // Elaborated named integral type; no runtime storage.

  vtNUM     = 25,
  vtSTR     = 26,
  vtMOD     = 27,

  vtFUNC      = 35,
  vtTASK      = 36,
  vtMOD_INST  = 37,
  vtGATE_INST = 38,
};

enum VERI_CALL_TYPE
{
  vtTASK_CALL    = 1,
  vtFUNC_CALL    = 2,
};

/*
 * verilog vector_scalar
 */
enum VERI_VECTOR_OR_SCALAR
{
  vpVECTOR = 0,
  vpSCALAR = 1,
};

/*
 * verilog inout
 */
enum VERI_INOUT
{
  vpNO_IO = 0,
  vpIN    = 1,
  vpOUT   = 2,
  vpINOUT = 3,
  vpREF   = 4, // Subroutine alias, never a module port direction.
  vpCONST_REF = 5, // Read-only subroutine alias.
  vpIMPORT = 6, // Modport named subroutine import; not a signal direction.
};

/*
 * verilog drive type
 */
enum VERI_DRIVE_STRENGTH
{
  vpSTRONG0 = 0,
  vpSTRONG1 = 1,
  vpPULL0   = 2,
  vpPULL1   = 3,
  vpWEAK0   = 4,
  vpWEAK1   = 5,
  vpHIGHZ0  = 6,
  vpHIGHZ1  = 7,
  vpSUPPLY0 = 8,
  vpSUPPLY1 = 9,
};

/*
 * verilog gate type
 */
enum VERI_GATE_TYPE
{
  vpBUFFIF0 = 10,
  vpBUFFIF1 = 11,
  vpNOTIF0  = 12,
  vpNOTIF1  = 13,
  vpAND     = 14,
  vpNAND    = 15,
  vpOR      = 16,
  vpNOR     = 17,
  vpXOR     = 18,
  vpXNOR    = 19,
  vpBUF     = 20,
  vpNOT     = 21,
};

/**
 * SystemVerilog always block kind
 */
enum VERI_ALWAYS_KIND
{
  akALWAYS      = 0,   /* traditional Verilog always */
  akALWAYS_COMB = 1,   /* SystemVerilog always_comb */
  akALWAYS_FF   = 2,   /* SystemVerilog always_ff */
  akALWAYS_LATCH= 3,   /* SystemVerilog always_latch */
};

/**
 * verilog variable type
 */
enum VERI_VAR_TYPE
{
  vvNONE    =  0,
  vvSUPPLY0 = 10,
  vvSUPPLY1 = 11,
  vvTRI     = 12,
  vvTRIAND  = 13,
  vvTRIOR   = 14,
  vvTRI0    = 15,
  vvTRI1    = 16,
  vvWIRE    = 17,
  vvWAND    = 18,
  vvWOR     = 19,
  vvREG     = 20,
  vvINT     = 21,
  vvTIME    = 22,
  vvTRIREG  = 23,
  vvPARAM   = 25,
  vvLOGIC   = 26,
  vvBIT     = 27,
  vvBYTE    = 28,
  vvSHORTINT= 29,
  vvLONGINT = 30,
  vvSTRING  = 36,   /* dynamically sized byte string, never an integral width */
  vvCLASS   = 37,   /* typed object handle; 64 bits is its storage, not an integral type */
  vvREAL = 38, vvSHORTREAL = 39, vvREALTIME = 40,
  vvCHANDLE = 41, /* opaque nullable C pointer, never integral */
  vvEVENT   = 35,   /* static named synchronization object */
  vvINT2    = 34,   /* SystemVerilog two-state int; vvINT retains integer */
  vvENUM    = 31,   /* RESERVED: not yet implemented in lexer/grammar */
  vvSTRUCT  = 32,   /* RESERVED: not yet implemented in lexer/grammar */
  vvTYPEDEF = 33,   /* RESERVED: not yet implemented in lexer/grammar */
};

inline bool veri_two_state(int type) {
  return type==vvBIT||type==vvBYTE||type==vvSHORTINT||type==vvINT2||type==vvLONGINT||type==vvCLASS||type==vvCHANDLE;
}
inline bool veri_real(int type) {return type==vvREAL||type==vvSHORTREAL||type==vvREALTIME;}
inline bool veri_integral_atom(int type) {
  return type==vvINT||type==vvTIME||type==vvBYTE||type==vvSHORTINT||type==vvINT2||type==vvLONGINT;
}
inline int veri_type_width(int type) {
  return type==vvBYTE?8:type==vvSHORTINT?16:(type==vvINT||type==vvINT2||type==vvSHORTREAL)?32:(type==vvTIME||type==vvLONGINT||type==vvCLASS||type==vvCHANDLE||type==vvREAL||type==vvREALTIME)?64:1;
}

enum VERI_EXP_TYPE
{
  veEXP_PRI         =  1,
  veEXP_UNA         =  2,
  veEXP_BIN         =  3,
  veEXP_MINTY       =  4,
  veEXP_QUES        =  5,
  veEXP_MULTI       =  6,
  veEXP_RANGE       =  7,
  veEXP_CALLER      =  8,
  veEXP_ARRAY       =  9,
  veEXP_EVENT       = 10,
  veEXP_ASSIGN      = 11,
  veEXP_MCONCAT     = 12,
  veEXP_DELAY       = 13,
  veEXP_DRIVE       = 14,

  veEXP_PORT_REF    = 15,
  veEXP_NAMED_PARAM = 16,

  veEXP_SIGN        = 17,
  veEXP_UNSIGN      = 18,
  veEXP_DUMMY_PORT  = 19,
  veEXP_MEMBER      = 20,
  veEXP_TYPE        = 21,
  veEXP_CONSTRAINT_FOREACH = 22,
};



enum VERI_STMT_TYPE
{
  vsSTMT_DUMMY             = 20,
  vsSTMT_BLOCKING          = 21,
  vsSTMT_CASE              = 22,
  vsSTMT_COND              = 23,
  vsSTMT_DISABLE           = 24,
  vsSTMT_EVENT             = 25,
  vsSTMT_LOOP              = 26,
  vsSTMT_NONBLOCKING       = 27,
  vsSTMT_PAR_BLOCK         = 28,
  vsSTMT_PROC_CONT_ASSIGN  = 29,
  vsSTMT_PROC_TIME_CONTROL = 30,
  vsSTMT_SEQ_BLOCK         = 31,
  vsSTMT_WAIT              = 32,
  vsSTMT_BREAK             = 38,
  vsSTMT_CONTINUE          = 39,
  vsSTMT_UPDATE            = 40,
  vsSTMT_COMPOUND          = 41,
  vsSTMT_RETURN            = 42,
  vsSTMT_EVENT_TRIGGER     = 43,
  vsSTMT_WAIT_FORK         = 44,
  vsSTMT_DISABLE_FORK      = 45,
  vsSTMT_FORCE             = 46,
  vsSTMT_RELEASE           = 47,

  vsSTMT_FUNC_BLOCKING     = 33,
  vsSTMT_FUNC_CASE         = 34,
  vsSTMT_FUNC_COND         = 35,
  vsSTMT_FUNC_LOOP         = 36,
  vsSTMT_FUNC_SEQ_BLOCK    = 37,

  vsSTMT_FUNC_DEFAULT_CASE_ITEM = 48,
  vsSTMT_FUNC_CASE_ITEM         = 49,
  vsSTMT_FUNC_CASE_ITEM_LIST    = 50,
  vsSTMT_FUNC_CASE_STMT         = 51,

  vsSTMT_DEFAULT_CASE_ITEM = 52,
  vsSTMT_CASE_ITEM         = 53,
  vsSTMT_CASE_ITEM_LIST    = 54,

  vsSTMT_SYS_CALL          = 57,
  vsSTMT_CALL              = 58,
  vsSTMT_STMT_LIST         = 59,
  vsSTMT_FUNC_STMT_LIST    = 61,

  vsSTMT_CONT_ASSIGN       = 62,
  vsSTMT_INIT              = 63,
  vsSTMT_ALWAYS            = 64,
  
  vsSTMT_MOD_ITEM_LIST     = 65,
  vsSTMT_BLOCK_ITEM_DECL_LIST = 66,
};

enum VERI_INST_TYPE
{
  vsINST_DUMMY                 = 69,
  vsINST_GEN_DEFAULT_CASE_ITEM = 70,
  vsINST_GEN_CASE_ITEM         = 71,
  vsINST_GEN_CASE_ITEM_LIST    = 72,
  vsINST_GEN_ITEM_LIST         = 73,

  vsINST_GEN_BLOCK             = 74,
  vsINST_GEN_COND              = 75,

  vsINST_MOD_INSTANCE          = 76,
  vsINST_GATE_INSTANCE         = 77,
  vsINST_MOD_INSTANTIATION     = 78,
  vsINST_GATE_INSTANTIATION    = 79,

  vsINST_GEN_CASE              = 80,
  vsINST_GEN_LOOP              = 81,
};

enum VERI_DECL_TYPE
{
  vsDECL_TF_DECL              = 86,
  vsDECL_TASK_PORT_LIST       = 87,
  vsDECL_FUNC_PORT_LIST       = 88,
  vsDECL_TASK_ITEM_DECL_LIST  = 89,
  vsDECL_BLOCK_ITEM_DECL_LIST = 90,
  vsDECL_FUNC_ITEM_DECL_LIST  = 91,
  vsDECL_TASK_DECL            = 92,
  vsDECL_FUNC_DECL            = 93,
  vsDECL_VAR                  = 94,
  vsDECL_PARAM                = 95,
  vsDECL_INT                  = 96,
  vsDECL_GENVAR               = 97,
  vsDECL_PARAM_DECL_LIST      = 98,
  vsDECL_PORT_DECL_LIST       = 99,
  vsDECL_IMPORT               = 100,
  vsDECL_EXPORT               = 101,
  vsDECL_CONSTRAINT           = 102,
  vsDECL_TIME                 = 103,
  vsDECL_CLOCKING             = 104,
  vsDECL_CLOCKING_ITEM        = 105,
  vsDECL_DEFAULT_CLOCKING     = 106,
  vsSTMT_CYCLE_CONTROL       = 107,
  vsDECL_COVERAGE             = 108,
  vsDECL_COVERPOINT           = 109,
  vsDECL_COVER_BIN            = 110,
  vsDECL_COVER_RANGE          = 111,
  vsDECL_COVER_OPTION         = 112,
  vsDECL_COVER_CROSS          = 113,
};

enum VERI_CASE_STMT_TYPE
{
  vcCASE  = 1,
  vcCASEZ = 2,
  vcCASEX = 3,
  vcINSIDE = 4,
};

enum VERI_STMT_FUNC_FLAG
{
  vsFUNC      = 1,
  vsNONE_FUNC = 2,
  vsBOTH      = 3,
};

/*
 * verilog abstract-syntax-tree node enumerator
 */
/*
enum VERI_AST
{
  vtVERILOG_SYNTHESIS_UNIT              = 4300,
  vtSOURCE_TEXT                         = 4301,
  vtMODULE_DECLARATION                  = 4302,
  vtMODULE_PORT_PART                    = 4303,
  vtMODULE_ITEM_LIST                    = 4304,
  vtPARAM_DECL_LIST                     = 4305,
  vtPORT_DECLARATION                    = 4306,
  vtIN_OR_OUT                           = 4307,
  vtPORT_TYPE_LIST                      = 4308,
  vtPORT_TYPE                           = 4309,
  vtMODULE_ITEM                         = 4310,
  vtMODULE_OR_GEN_ITEM                  = 4311,
  vtMODULE_OR_GEN_ITEM_DECLARATION      = 4312,
  vtPARAM_DECLARATION                   = 4313,
  vtSPECPARAM_DECLARATION               = 4314,
  vtPARAM_DECLARATOR                    = 4315,
  vtGENVAR_DECLARATION                  = 4316,
  vtINT_DECLARATION                     = 4317,
  vtNET_DECLARATION                     = 4318,
  vtVECTOR_OR_SCALAR                    = 4319,
  vtREG_DECLARATION                     = 4320,
  vtNET_DECL_A                          = 4321,
  vtNET_DECL_B                          = 4322,
  vtNET_TYPE                            = 4323,
  vtDRIVE_STRENGTH                      = 4324,
  vtSTRENGTH0                           = 4325,
  vtSTRENGTH1                           = 4326,
  vtSPECPARAM_ASSIGNMENT_LIST           = 4327,
  vtSPECPARAM_ASSIGNMENT                = 4328,
  vtFUNC_DECLARATION                    = 4329,
  vtFUNC_ITEM_DECLARATION               = 4330,
  vtFUNC_PORT_LIST                      = 4331,
  vtFUNC_ITEM_DECL_LIST                 = 4332,
  vtBLOCK_ITEM_DECL_LIST                = 4333,
  vtFUNC_DECLARATOR                     = 4334,
  vtTASK_DECLARATION                    = 4335,
  vtTASK_ITEM_DECL_LIST                 = 4336,
  vtTASK_ITEM_DECLARATION               = 4337,
  vtTASK_PORT_LIST                      = 4338,
  vtTF_DECLARATION                      = 4339,
  vtTF_PORT_DECLARATOR                  = 4340,
  vtBLOCK_ITEM_DECLARATION              = 4341,
  vtGATE_INSTANTIATION                  = 4342,
  vtGATE_INST_LIST                      = 4343,
  vtGATE_INSTANCE                       = 4344,
  vtGATETYPE                            = 4345,
  vtMODULE_INSTANTIATION                = 4346,
  vtPARAM_VAL_ASSIGNMENT                = 4347,
  vtNAMED_PARAM_ASSIGNMENT              = 4348,
  vtMODULE_INSTANCE                     = 4349,
  vtMODULE_INST_LIST                    = 4350,
  vtINSTANCE_NAME                       = 4351,
  vtNAMED_PARAM_ASSIGNMENT_LIST         = 4352,
  vtGENERATED_INSTANTIATION             = 4353,
  vtGEN_ITEM_OR_NULL                    = 4354,
  vtGEN_ITEM                            = 4355,
  vtGEN_ITEM_LIST                       = 4356,
  vtGEN_COND_STATEMENT                  = 4357,
  vtGENVAR_CASE_ITEM                    = 4358,
  vtGEN_LOOP_STATEMENT                  = 4359,
  vtGEN_BLOCK                           = 4360,
  vtGEN_CASE_STATEMENT                  = 4361,
  vtGENVAR_CASE_ITEM_LIST               = 4362,
  vtCONTINUOUS_ASSIGN                   = 4363,
  vtBLOCKING_ASSIGNMENT                 = 4364,
  vtNONBLOCKING_ASSIGNMENT              = 4365,
  vtFUNC_STMT_OR_NULL                   = 4366,
  vtFUNC_SEQ_BLOCK                      = 4367,
  vtSEQ_BLOCK                           = 4368,
  vtFUNC_STMT_LIST                      = 4369,
  vtSTMT_LIST                           = 4370,
  vtSTATEMENT                           = 4371,
  vtSTMT_OR_NULL                        = 4372,
  vtFUNC_STATEMENT                      = 4373,
  vtEVENT_CONTROL                       = 4374,
  vtDISABLE_STATEMENT                   = 4375,
  vtPROCEDURAL_TIMING_CONTROL_STATEMENT = 4376,
  vtCOND_STATEMENT                      = 4377,
  vtFUNC_COND_STATEMENT                 = 4378,
  vtCASE_STATEMENT                      = 4379,
  vtCASE_ITEM                           = 4380,
  vtCASE_ITEM_LIST                      = 4381,
  vtFUNC_CASE_STATEMENT                 = 4382,
  vtFUNC_CASE_ITEM                      = 4383,
  vtFUNC_CASE_ITEM_LIST                 = 4384,
  vtFUNC_LOOP_STATEMENT                 = 4385,
  vtLOOP_STATEMENT                      = 4386,
  vtSYS_TASK_ENABLE                     = 4387,
  vtTASK_ENABLE                         = 4388,
  vtSPECIFY_BLOCK                       = 4389,
  vtCONCAT                              = 4390,
  vtMULTI_CONCAT                        = 4391,
  vtEXPRESSION                          = 4392,
  vtUNARY_EXPRESSION                    = 4393,
  vtPOW_EXPRESSION                      = 4394,
  vtMULTIPLICATIVE_EXPRESSION           = 4395,
  vtADDITIVE_EXPRESSION                 = 4396,
  vtSHIFT_EXPRESSION                    = 4397,
  vtRELATIONAL_EXPRESSION               = 4398,
  vtEQUALITY_EXPRESSION                 = 4399,
  vtAND_EXPRESSION                      = 4400,
  vtXOR_EXPRESSION                      = 4401,
  vtBIT_OR_EXPRESSION                   = 4402,
  vtLOGICAL_AND_EXPRESSION              = 4403,
  vtLOGICAL_OR_EXPRESSION               = 4404,
  vtCONDITIONAL_EXPRESSION              = 4405,
  vtMINTYPMAX_EXPRESSION                = 4406,
  vtPRIMARY                             = 4407,

  vtGEN_LOOP_ID                         = 4408,
  vtGEN_BLOCK_ID                        = 4409,
  vtFUNC_SEQ_BLOCK_ID                   = 4410,
  vtSEQ_BLOCK_ID                        = 4411,
  vtRANGE                               = 4412,
  vtPOSTFIX_EXPRESSION                  = 4413,
  vtASSIGNMENT_EXPRESSION               = 4414,
  vtDELAY3                              = 4415,
  vtATTR_INST_LIST                      = 4416,
  vtATTR_INSTANCE                       = 4417,
  vtUNARY_OPERATOR                      = 4418,
  vtLINE_COMPILER_DIRECTIVE             = 4419,
  vtUDP_DECLARATION                     = 4420,
};                                           
*/                                             
#endif // TOKEN_VERILOG_TOKEN_HPP_           

