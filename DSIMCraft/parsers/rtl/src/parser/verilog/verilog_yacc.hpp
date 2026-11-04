/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison interface for Yacc-like parsers in C

   Copyright (C) 1984, 1989-1990, 2000-2015, 2018-2021 Free Software Foundation,
   Inc.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <https://www.gnu.org/licenses/>.  */

/* As a special exception, you may create a larger work that contains
   part or all of the Bison parser skeleton and distribute that work
   under terms of your choice, so long as that work isn't itself a
   parser generator using the skeleton or a modified version thereof
   as a parser skeleton.  Alternatively, if you modify or redistribute
   the parser skeleton itself, you may (at your option) remove this
   special exception, which will cause the skeleton and the resulting
   Bison output files to be licensed under the GNU General Public
   License without this special exception.

   This special exception was added by the Free Software Foundation in
   version 2.2 of Bison.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

#ifndef YY_VERILOG_PARSERS_RTL_SRC_PARSER_VERILOG_VERILOG_YACC_HPP_INCLUDED
# define YY_VERILOG_PARSERS_RTL_SRC_PARSER_VERILOG_VERILOG_YACC_HPP_INCLUDED
/* Debug traces.  */
#ifndef YYDEBUG
# define YYDEBUG 0
#endif
#if YYDEBUG
extern int verilogdebug;
#endif

/* Token kinds.  */
#ifndef YYTOKENTYPE
# define YYTOKENTYPE
  enum yytokentype
  {
    YYEMPTY = -2,
    YYEOF = 0,                     /* "end of file"  */
    YYerror = 256,                 /* error  */
    YYUNDEF = 257,                 /* "invalid token"  */
    vINSIDE = 258,                 /* vINSIDE  */
    vWILD_EQ = 259,                /* vWILD_EQ  */
    vWILD_NE = 260,                /* vWILD_NE  */
    vSVA_REPEAT = 261,             /* vSVA_REPEAT  */
    MY_EOF = 262,                  /* MY_EOF  */
    vPORT_DELIM = 263,             /* vPORT_DELIM  */
    vPARAM_DELIM = 264,            /* vPARAM_DELIM  */
    vEVENT_ALL = 265,              /* vEVENT_ALL  */
    vDUMMY_PORT = 266,             /* vDUMMY_PORT  */
    vSIGN_FUNC = 267,              /* vSIGN_FUNC  */
    vUNSIGN_FUNC = 268,            /* vUNSIGN_FUNC  */
    vNOT_SUPPORTED = 269,          /* vNOT_SUPPORTED  */
    vALWAYS = 270,                 /* vALWAYS  */
    vALWAYS_COMB = 271,            /* vALWAYS_COMB  */
    vALWAYS_FF = 272,              /* vALWAYS_FF  */
    vALWAYS_LATCH = 273,           /* vALWAYS_LATCH  */
    vFINAL = 274,                  /* vFINAL  */
    vBIND = 275,                   /* vBIND  */
    vAND_ASCII = 276,              /* vAND_ASCII  */
    vASSIGN = 277,                 /* vASSIGN  */
    vAUTO = 278,                   /* vAUTO  */
    vBEGIN = 279,                  /* vBEGIN  */
    vBIT = 280,                    /* vBIT  */
    vBUF_ASCII = 281,              /* vBUF_ASCII  */
    vBUFIF_A = 282,                /* vBUFIF_A  */
    vSTATIC = 283,                 /* vSTATIC  */
    vBYTE = 284,                   /* vBYTE  */
    vUNIQUE = 285,                 /* vUNIQUE  */
    vUNIQUE0 = 286,                /* vUNIQUE0  */
    vPRIORITY = 287,               /* vPRIORITY  */
    vBUFIF_B = 288,                /* vBUFIF_B  */
    vCASE = 289,                   /* vCASE  */
    vCASEX = 290,                  /* vCASEX  */
    vCASEZ = 291,                  /* vCASEZ  */
    vCELL = 292,                   /* vCELL  */
    vCONFIG = 293,                 /* vCONFIG  */
    vDEFAULT = 294,                /* vDEFAULT  */
    vDESIGN = 295,                 /* vDESIGN  */
    vDISABLE = 296,                /* vDISABLE  */
    vDO = 297,                     /* vDO  */
    vELSE = 298,                   /* vELSE  */
    vEND = 299,                    /* vEND  */
    vENDCASE = 300,                /* vENDCASE  */
    vENDCONFIG = 301,              /* vENDCONFIG  */
    vENDFUNC = 302,                /* vENDFUNC  */
    vENDGEN = 303,                 /* vENDGEN  */
    vENDMODULE = 304,              /* vENDMODULE  */
    vENDSPEC = 305,                /* vENDSPEC  */
    vENDTASK = 306,                /* vENDTASK  */
    vFOR = 307,                    /* vFOR  */
    vFUNC = 308,                   /* vFUNC  */
    vGEN = 309,                    /* vGEN  */
    vGENVAR = 310,                 /* vGENVAR  */
    vHIGHZ_A = 311,                /* vHIGHZ_A  */
    vHIGHZ_B = 312,                /* vHIGHZ_B  */
    vIF = 313,                     /* vIF  */
    vREPEAT = 314,                 /* vREPEAT  */
    vFOREVER = 315,                /* vFOREVER  */
    vFOREACH = 316,                /* vFOREACH  */
    vPATTERN_OPEN = 317,           /* vPATTERN_OPEN  */
    vNEW = 318,                    /* vNEW  */
    vCLASS = 319,                  /* vCLASS  */
    vENDCLASS = 320,               /* vENDCLASS  */
    vNULL = 321,                   /* vNULL  */
    vTHIS = 322,                   /* vTHIS  */
    vSUPER = 323,                  /* vSUPER  */
    vEXTENDS = 324,                /* vEXTENDS  */
    vVIRTUAL = 325,                /* vVIRTUAL  */
    vPURE = 326,                   /* vPURE  */
    vLOCAL = 327,                  /* vLOCAL  */
    vPROTECTED = 328,              /* vPROTECTED  */
    vCONTEXT = 329,                /* vCONTEXT  */
    vEXTERN = 330,                 /* vEXTERN  */
    vINC_DIR = 331,                /* vINC_DIR  */
    vINIT = 332,                   /* vINIT  */
    vINOUT = 333,                  /* vINOUT  */
    vINPUT = 334,                  /* vINPUT  */
    vINSTANCE = 335,               /* vINSTANCE  */
    vINT = 336,                    /* vINT  */
    vINT2 = 337,                   /* vINT2  */
    vREAL = 338,                   /* vREAL  */
    vSHORTREAL = 339,              /* vSHORTREAL  */
    vREALTIME = 340,               /* vREALTIME  */
    vLIBLIST = 341,                /* vLIBLIST  */
    vLIB = 342,                    /* vLIB  */
    vLOCAL_PARAM = 343,            /* vLOCAL_PARAM  */
    vMODULE = 344,                 /* vMODULE  */
    vNAND_ASCII = 345,             /* vNAND_ASCII  */
    vNEGEDGE = 346,                /* vNEGEDGE  */
    vNOR_ASCII = 347,              /* vNOR_ASCII  */
    vNOT_ASCII = 348,              /* vNOT_ASCII  */
    vNOTIF_A = 349,                /* vNOTIF_A  */
    vNOTIF_B = 350,                /* vNOTIF_B  */
    vOR_ASCII = 351,               /* vOR_ASCII  */
    vOUTPUT = 352,                 /* vOUTPUT  */
    vPARAMETER = 353,              /* vPARAMETER  */
    vPOSEDGE = 354,                /* vPOSEDGE  */
    vPULL_A = 355,                 /* vPULL_A  */
    vPULL_B = 356,                 /* vPULL_B  */
    vREG = 357,                    /* vREG  */
    vSHORTINT = 358,               /* vSHORTINT  */
    vTRIAND = 359,                 /* vTRIAND  */
    vTRIOR = 360,                  /* vTRIOR  */
    vSCALARED = 361,               /* vSCALARED  */
    vSIGNED = 362,                 /* vSIGNED  */
    vSPECIFY = 363,                /* vSPECIFY  */
    vSPEC_PARAM = 364,             /* vSPEC_PARAM  */
    vVOID = 365,                   /* vVOID  */
    vSTRONG_A = 366,               /* vSTRONG_A  */
    vSTRONG_B = 367,               /* vSTRONG_B  */
    vSUPPLY_A = 368,               /* vSUPPLY_A  */
    vSUPPLY_B = 369,               /* vSUPPLY_B  */
    vTASK = 370,                   /* vTASK  */
    vTIME = 371,                   /* vTIME  */
    vTRI = 372,                    /* vTRI  */
    vUSE = 373,                    /* vUSE  */
    vUNSIGNED = 374,               /* vUNSIGNED  */
    vVECTORED = 375,               /* vVECTORED  */
    vWAND = 376,                   /* vWAND  */
    vWEAK_A = 377,                 /* vWEAK_A  */
    vWEAK_B = 378,                 /* vWEAK_B  */
    vWHILE = 379,                  /* vWHILE  */
    vWIRE = 380,                   /* vWIRE  */
    vWOR = 381,                    /* vWOR  */
    vTYPE = 382,                   /* vTYPE  */
    vTYPEDEF = 383,                /* vTYPEDEF  */
    vENUM = 384,                   /* vENUM  */
    vSTRUCT = 385,                 /* vSTRUCT  */
    vUNION = 386,                  /* vUNION  */
    vPACKED = 387,                 /* vPACKED  */
    vFORCE = 388,                  /* vFORCE  */
    vRELEASE = 389,                /* vRELEASE  */
    vLONGINT = 390,                /* vLONGINT  */
    vXNOR_ASCII = 391,             /* vXNOR_ASCII  */
    vXOR_ASCII = 392,              /* vXOR_ASCII  */
    vIDENT = 393,                  /* vIDENT  */
    vLOGIC = 394,                  /* vLOGIC  */
    vNUMBER = 395,                 /* vNUMBER  */
    vTIME_LITERAL = 396,           /* vTIME_LITERAL  */
    vTIMEUNIT = 397,               /* vTIMEUNIT  */
    vTIMEPRECISION = 398,          /* vTIMEPRECISION  */
    vSYS_IDENT = 399,              /* vSYS_IDENT  */
    vDUMPVARS = 400,               /* vDUMPVARS  */
    vCONCAT_IDENT = 401,           /* vCONCAT_IDENT  */
    vUNSIGNED_NUM = 402,           /* vUNSIGNED_NUM  */
    vARITH_LS = 403,               /* vARITH_LS  */
    vARITH_RS = 404,               /* vARITH_RS  */
    vANDAND = 405,                 /* vANDAND  */
    vXNOR = 406,                   /* vXNOR  */
    vNAND = 407,                   /* vNAND  */
    vNOR = 408,                    /* vNOR  */
    vPOW = 409,                    /* vPOW  */
    vOROR = 410,                   /* vOROR  */
    vLE = 411,                     /* vLE  */
    vGE = 412,                     /* vGE  */
    vLOGIC_LS = 413,               /* vLOGIC_LS  */
    vLOGIC_RS = 414,               /* vLOGIC_RS  */
    vLOGIC_EQ = 415,               /* vLOGIC_EQ  */
    vLOGIC_INEQ = 416,             /* vLOGIC_INEQ  */
    vCASE_EQ = 417,                /* vCASE_EQ  */
    vCASE_INEQ = 418,              /* vCASE_INEQ  */
    vATTR_L = 419,                 /* vATTR_L  */
    vATTR_R = 420,                 /* vATTR_R  */
    vPRIMITIVE = 421,              /* vPRIMITIVE  */
    vENDPRI = 422,                 /* vENDPRI  */
    vSTR = 423,                    /* vSTR  */
    vFILE = 424,                   /* vFILE  */
    vRANGE_ADD = 425,              /* vRANGE_ADD  */
    vRANGE_SUB = 426,              /* vRANGE_SUB  */
    vPATHPULSE = 427,              /* vPATHPULSE  */
    vBREAK = 428,                  /* vBREAK  */
    vCONTINUE = 429,               /* vCONTINUE  */
    vINCR = 430,                   /* vINCR  */
    vDECR = 431,                   /* vDECR  */
    vRETURN = 432,                 /* vRETURN  */
    vASSERT = 433,                 /* vASSERT  */
    vASSUME = 434,                 /* vASSUME  */
    vCOVER = 435,                  /* vCOVER  */
    vADD_EQ = 436,                 /* vADD_EQ  */
    vSUB_EQ = 437,                 /* vSUB_EQ  */
    vMUL_EQ = 438,                 /* vMUL_EQ  */
    vDIV_EQ = 439,                 /* vDIV_EQ  */
    vMOD_EQ = 440,                 /* vMOD_EQ  */
    vAND_EQ = 441,                 /* vAND_EQ  */
    vOR_EQ = 442,                  /* vOR_EQ  */
    vXOR_EQ = 443,                 /* vXOR_EQ  */
    vLS_EQ = 444,                  /* vLS_EQ  */
    vRS_EQ = 445,                  /* vRS_EQ  */
    vALS_EQ = 446,                 /* vALS_EQ  */
    vARS_EQ = 447,                 /* vARS_EQ  */
    vWAIT = 448,                   /* vWAIT  */
    vWAIT_ORDER = 449,             /* vWAIT_ORDER  */
    vEVENT = 450,                  /* vEVENT  */
    vTRIGGER = 451,                /* vTRIGGER  */
    vNBA_TRIGGER = 452,            /* vNBA_TRIGGER  */
    vREF = 453,                    /* vREF  */
    vCONST = 454,                  /* vCONST  */
    vRAND = 455,                   /* vRAND  */
    vRANDC = 456,                  /* vRANDC  */
    vCONSTRAINT = 457,             /* vCONSTRAINT  */
    vCLOCKING = 458,               /* vCLOCKING  */
    vENDCLOCKING = 459,            /* vENDCLOCKING  */
    vSTEP = 460,                   /* vSTEP  */
    vIFF = 461,                    /* vIFF  */
    vCOVERGROUP = 462,             /* vCOVERGROUP  */
    vENDGROUP = 463,               /* vENDGROUP  */
    vCOVERPOINT = 464,             /* vCOVERPOINT  */
    vCROSS = 465,                  /* vCROSS  */
    vBINS = 466,                   /* vBINS  */
    vIGNORE_BINS = 467,            /* vIGNORE_BINS  */
    vILLEGAL_BINS = 468,           /* vILLEGAL_BINS  */
    LOWER_THAN_ELSE = 469,         /* LOWER_THAN_ELSE  */
    INTEGRAL_DEFAULT = 470,        /* INTEGRAL_DEFAULT  */
    LOWER_THAN_A = 471,            /* LOWER_THAN_A  */
    LOWER_THAN_B = 472,            /* LOWER_THAN_B  */
    LOWER_THAN_C = 473,            /* LOWER_THAN_C  */
    UOR = 474,                     /* UOR  */
    UAND = 475,                    /* UAND  */
    UNEG = 476,                    /* UNEG  */
    UNAND = 477,                   /* UNAND  */
    UNOR = 478,                    /* UNOR  */
    UXNOR = 479,                   /* UXNOR  */
    UXOR = 480,                    /* UXOR  */
    ULNOT = 481,                   /* ULNOT  */
    UADD = 482,                    /* UADD  */
    UMINUS = 483,                  /* UMINUS  */
    vFORK = 484,                   /* vFORK  */
    vJOIN = 485,                   /* vJOIN  */
    vJOIN_ANY = 486,               /* vJOIN_ANY  */
    vJOIN_NONE = 487,              /* vJOIN_NONE  */
    vWITH = 488,                   /* vWITH  */
    vVAR_PORT = 489,               /* vVAR_PORT  */
    vRANDOM_FUNC = 490,            /* vRANDOM_FUNC  */
    vPACKAGE = 491,                /* vPACKAGE  */
    vENDPACKAGE = 492,             /* vENDPACKAGE  */
    vIMPORT = 493,                 /* vIMPORT  */
    vSCOPE = 494,                  /* vSCOPE  */
    vSTRING_TYPE = 495,            /* vSTRING_TYPE  */
    vCHANDLE = 496,                /* vCHANDLE  */
    vPROPERTY = 497,               /* vPROPERTY  */
    vENDPROPERTY = 498,            /* vENDPROPERTY  */
    vOVERLAP = 499,                /* vOVERLAP  */
    vNONOVERLAP = 500,             /* vNONOVERLAP  */
    vCYCLEDELAY = 501,             /* vCYCLEDELAY  */
    vSEQUENCE = 502,               /* vSEQUENCE  */
    vENDSEQUENCE = 503,            /* vENDSEQUENCE  */
    vINTERFACE = 504,              /* vINTERFACE  */
    vENDINTERFACE = 505,           /* vENDINTERFACE  */
    vMODPORT = 506,                /* vMODPORT  */
    vEXPORT = 507                  /* vEXPORT  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
union YYSTYPE
{
#line 147 "parsers/rtl/src/parser/verilog/verilog.y"

  class VeriNode *tok;
  int operation;

  struct
  {
    int   col;
    int   line;
    char *content;
  }symbol;

  struct { int col; int line; char *content; bool abstract_class; }class_spec;

  struct
  {
    int  col;
    int  line;
    int  extra[3];
    class VeriNode *node[3];
  }extra_tok;

#line 338 "parsers/rtl/src/parser/verilog/verilog_yacc.hpp"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE veriloglval;


int verilogparse (void);


#endif /* !YY_VERILOG_PARSERS_RTL_SRC_PARSER_VERILOG_VERILOG_YACC_HPP_INCLUDED  */
