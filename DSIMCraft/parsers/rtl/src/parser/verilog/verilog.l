%{
/*
 * Copyright (c) 2012 Fudan University ICCAD Lab
 * All rights reserved.
 *
 * Filename : verilog.l
 * Summary  : verilog syntax analyzer
 *
 * Version  : 1 ( Creation )
 * Author   : Pavio Yang ( 11212020059@fudan.edu.cn )
 * Date     : 2012.10.28
 */

//#define YYDEBUG 1

#include <cstdio>
#include <cstring>
#include <ctype.h>
#include <string>
#include <unordered_set>
#include <vector>
#include <unistd.h>
#include <iostream>
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "verilog_yacc.hpp"

// Words without grammar productions still remain reserved in SV mode.
static bool unsupported_sv_keyword(const std::string& word) {
  static const std::unordered_set<std::string> keywords = {
    "accept_on",
    "alias",
    "before",
    "bins",
    "binsof",
    "checker",
    "constraint",
    "covergroup",
    "coverpoint",
    "cross",
    "dist",
    "endchecker",
    "endgroup",
    "endprogram",
    "eventually",
    "expect",
    "extends",
    "first_match",
    "global",
    "ignore_bins",
    "illegal_bins",
    "implements",
    "implies",
    "interconnect",
    "intersect",
    "let",
    "matches",
    "nettype",
    "nexttime",
    "program",
    "pure",
    "rand",
    "randc",
    "randcase",
    "randsequence",
    "reject_on",
    "restrict",
    "s_always",
    "s_eventually",
    "s_nexttime",
    "s_until",
    "s_until_with",
    "shortreal",
    "soft",
    "solve",
    "strong",
    "super",
    "sync_accept_on",
    "sync_reject_on",
    "tagged",
    "throughout",
    "timeprecision",
    "timeunit",
    "until",
    "until_with",
    "untyped",
    "virtual",
    "weak",
    "wildcard",
    "within",
  };
  return keywords.count(word)!=0;
}

int yylex();
void count( void );
void count_line( void );
void count_comment( void );
void yyerror( char * );
static int declaration_after_comma();
                    
void determin_line_cd( void );

int veriloglex_destroy( void );
int veri_col = 0;
int veri_lno = 1;
int just_end = 0;
static bool veri_dump_arguments = false;
static unsigned veri_dump_parentheses = 0;
#define YY_USER_INIT { veri_dump_arguments = false; veri_dump_parentheses = 0; }

int veri_include_line;
int veri_include_directive;
std::string veri_include_fname;

int verilog_parser_input( char *buf, int max )
{
  using rtl::VeriParser;
  int cur_len = veri_parser->get_cur_length();
  if( cur_len == 0 )
    return 0;

  if( max > cur_len )
    max = cur_len;

  memcpy( buf, veri_parser->get_s(), max );
  veri_parser->set_cur_s( veri_parser->get_s() + max );
  veri_parser->set_cur_length( cur_len - max );
  return max;
}

void verilog_parser_output( char * /*s*/, int /*size*/ )
{
}

#undef YY_INPUT
#define YY_INPUT(b, r, m)  ( r = verilog_parser_input(b,m) )

#undef YY_OUTPUT
#define YY_OUTPUT(str, size) (verilog_parser_output(str, size))

#define GET_CONTENT (veriloglval.symbol.content = strdup(yytext))
#define SV_KEYWORD(token) (veri_parser->systemverilog()?(token):(GET_CONTENT,vIDENT))

//%option prefix="verilog"
//%option nodefault
//%option batch
%}

D   [0-9_]
PD  [0-9]
L   [a-zA-Z_]
AL  [a-zA-Z_$]
H   [a-fA-F0-9_]
E   [Ee][+-]?{D}+
WHITE [ \t\b\r\f\n]
SPACE [ \t\b\r\f]
NONWHITE [^ \t\b\r\f\n]
NONID [^0-9_a-zA-Z$]


S    [sS]
BASE [hHoOdDbB]
XD   [0-9_a-fA-FXZxz?]
XPD  [0-9a-fA-FXZxz?]

%x _LINE_A_
%x _LINE_B_
%x _LINE_C_

%x _OMIT_
%x _COMMENT_

%x _DUMMY_PORT_A
%x _DUMMY_PORT_B
%x _DUMMY_PORT_C
%x _DUMMY_PORT_D

%%

    /*     Important */
"\0"               { return MY_EOF; } // Keep yytext valid until Bison finishes error reporting.

<INITIAL>"`line"   { count_line(); BEGIN _LINE_A_;         }

<_LINE_A_>{PD}+    {
                     count_line();
                     veri_include_line = atoi(yytext);
                     BEGIN _LINE_B_;
                   }

<_LINE_B_>\"([^\"\\\n]|\\[^\n])*\"  {
                     count_line();
                     veri_include_fname = yytext;
                     BEGIN _LINE_C_;
                   }

<_LINE_C_>{PD}+{SPACE}*"\n" {
                     count_line();
                     veri_include_directive = atoi(yytext);
                     determin_line_cd();
                     BEGIN INITIAL;
                   }

<_LINE_A_>[\f\r\t\b ]+ { count(); }
<_LINE_B_>[\f\r\t\b ]+ { count(); }
<_LINE_C_>[\f\r\t\b ]+ { count(); }

<_LINE_A_>"\n" { count(); veri_lno++; BEGIN INITIAL; }
<_LINE_B_>"\n" { count(); veri_lno++; BEGIN INITIAL; }

<_LINE_A_>.    { BEGIN INITIAL; }
<_LINE_B_>.    { BEGIN INITIAL; }
<_LINE_C_>.    { BEGIN INITIAL; }

    /* general stuff */
<*>"//"[^\n]*   { count_comment(); }
<INITIAL>"/*"   { count_comment(); BEGIN _COMMENT_; }
<_COMMENT_>"*/" { count_comment(); BEGIN INITIAL; }
<_COMMENT_>\n   { count_comment(); }
<_COMMENT_>.    { count_comment(); }
<*>"\n"         { count(); veri_lno++;    }
<*>{SPACE}      { count();                }

    /* concat operators */
"{"     { count(); return '{';  }
"}"     { count(); return '}';  }

    /* Operators */
"("{WHITE}*"*"{WHITE}*")"   { count(); return vEVENT_ALL; }
"("{WHITE}*","              { yyless(1); count();
                              BEGIN _DUMMY_PORT_A; return '(' ;
                            }
","{WHITE}*","              { yyless(1); count();
	                              BEGIN _DUMMY_PORT_A; return ',';
                            }
","{WHITE}*")"              { yyless(1); count();
                              BEGIN _DUMMY_PORT_C; return ',';
                            }

<_DUMMY_PORT_A>{WHITE}*","  { yyless(strlen(yytext)-1); count();
                              BEGIN _DUMMY_PORT_B; return vDUMMY_PORT;
                            }

<_DUMMY_PORT_B>","{WHITE}*"," { yyless(1); count(); BEGIN _DUMMY_PORT_A; return ','; }
<_DUMMY_PORT_B>","{WHITE}*")" { yyless(1); count(); BEGIN _DUMMY_PORT_C; return ','; }
<_DUMMY_PORT_B>","          { count(); BEGIN INITIAL; return ','; }

<_DUMMY_PORT_C>{WHITE}*")"  { yyless(strlen(yytext)-1); count();
                              BEGIN _DUMMY_PORT_D; return vDUMMY_PORT;
                            }

<_DUMMY_PORT_D>")"          { count(); BEGIN INITIAL; return ')'; }


"+"     { count(); return '+';  }
"-"     { count(); return '-';  }
"*"     { count(); return '*';  }
"/"     { count(); return '/';  }
"%"     { count(); return '%';  }
">"     { count(); return '>';  }
"<"     { count(); return '<';  }
"!"     { count(); return '!';  }
"~"     { count(); return '~';  }
"&"     { count(); return '&';  }
"|"     { count(); return '|';  }
"^"     { count(); return '^';  }
"?"     { count(); return '?';  }
"$"     { count(); return '$';  }
"="     { count(); return '=';  }

":"     { count(); return ':';  }
"::"    { count(); return vSCOPE; }
"##"    { count(); return vCYCLEDELAY; }
"#"     { count(); return '#';  }
"["{WHITE}*"*" { count(); for(int i=0;yytext[i];++i)if(yytext[i]=='\n')++veri_lno; return vSVA_REPEAT; }
"["     { count(); return '[';  }
"]"     { count(); return ']';  }
"("     { count(); if(veri_dump_arguments)++veri_dump_parentheses; return '(';  }
")"     { count(); if(veri_dump_arguments && (!veri_dump_parentheses || !--veri_dump_parentheses))veri_dump_arguments=false; return ')';  }
";"     { count(); veri_dump_arguments=false; return ';';  }
","     { const int token=veri_parser->systemverilog()?declaration_after_comma():',';count();return token; }
"."     { count(); return '.';  }
"@"     { count(); return '@';  }
"'"[ \t\r\n]*"{" { count(); for(int i=0;yytext[i];++i)if(yytext[i]=='\n')++veri_lno; return vPATTERN_OPEN; }
"'"     { count(); return '\''; }

"+="    { count(); return vADD_EQ; }
"-="    { count(); return vSUB_EQ; }
"*="    { count(); return vMUL_EQ; }
"/="    { count(); return vDIV_EQ; }
"%="    { count(); return vMOD_EQ; }
"&="    { count(); return vAND_EQ; }
"|="    { count(); return vOR_EQ; }
"^="    { count(); return vXOR_EQ; }
"<<="   { count(); return vLS_EQ; }
">>="   { count(); return vRS_EQ; }
"<<<="  { count(); return vALS_EQ; }
">>>="  { count(); return vARS_EQ; }
"return" { count(); return SV_KEYWORD(vRETURN); }
"++"    { count(); return vINCR;       }
"--"    { count(); return vDECR;       }
"break" { count(); return SV_KEYWORD(vBREAK);     }
"continue" { count(); return SV_KEYWORD(vCONTINUE); }
"&&"    { count(); return vANDAND;    }
"||"    { count(); return vOROR;      }
"<="    { count(); return vLE;        }
">="    { count(); return vGE;        }
"<<"    { count(); return vLOGIC_LS;  }
">>"    { count(); return vLOGIC_RS;  }
"=="    { count(); return vLOGIC_EQ;  }
"!="    { count(); return vLOGIC_INEQ;}
"^~"    { count(); return vXNOR;      }
"~^"    { count(); return vXNOR;      }
"~&"    { count(); return vNAND;      }
"~|"    { count(); return vNOR;       }
"**"    { count(); return vPOW;       }
"->>"   { count(); return vNBA_TRIGGER;      }
"->"    { count(); return vTRIGGER;          }
"=>"    { count(); return vNOT_SUPPORTED;    }
"*>"    { count(); return vNOT_SUPPORTED;    }
"+:"    { count(); return vRANGE_ADD; }
"-:"    { count(); return vRANGE_SUB; }
"(*"    { count(); return vATTR_L;   }
"*)"    { count(); return vATTR_R;   }

"==?"   { count(); return vWILD_EQ; }
"!=?"   { count(); return vWILD_NE; }
"==="   { count(); return vCASE_EQ;   }
"!=="   { count(); return vCASE_INEQ; }
"<<<"   { count(); return vARITH_LS;  }
">>>"   { count(); return vARITH_RS;  }
"&&&"   { count(); return vNOT_SUPPORTED; }

   /*     Keywords */

","{WHITE}*{L}({AL}|{PD})*({WHITE}*"::"{WHITE}*{L}({AL}|{PD})*)+{WHITE}+{L}({AL}|{PD})* {
  std::string text(yytext,yyleng);auto word=text.substr(text.find_last_of(" \t\b\r\f\n")+1);
  const bool expression=word=="inside"||word=="or"||word=="iff"||word=="with"||word=="dist"||word=="matches";
  yyless(1);count();return veri_parser->systemverilog()&&!expression?vPORT_DELIM:',';
}
","{WHITE}*{L}({AL}|{PD})*{WHITE}*"."{WHITE}*{L}({AL}|{PD})*{WHITE}+{L}({AL}|{PD})* { yyless(1);count();return veri_parser->systemverilog()?vPORT_DELIM:','; }
","{WHITE}*("logic"|"bit"|"reg"){WHITE}*("signed"|"unsigned")?{WHITE}*"[" { yyless(1);count();return veri_parser->systemverilog()?vPORT_DELIM:','; }
","{WHITE}*{L}({AL}|{PD})*{WHITE}+{L}({AL}|{PD})* {
  std::string text(yytext,yyleng);auto start=text.find_first_not_of(" \t\r\n",1);auto end=text.find_first_of(" \t\r\n",start);auto type=text.substr(start,end-start);
  int token=',';
  if(type=="input"||type=="output"||type=="inout")token=vPORT_DELIM;
  else if(type=="parameter"||type=="localparam"||type=="type")token=vPARAM_DELIM;
  else if(veri_parser->systemverilog()) {
    auto* mod=veri_parser->module(type);
    if(type=="const"||type=="ref"||type=="interface"||(mod&&mod->is_interface()))token=vPORT_DELIM;
    else if(type!="import"&&type!="export"&&type!="function"&&type!="task"&&type!="clocking"&&type!="posedge"&&type!="negedge"&&type!="edge") {
      // Two adjacent identifiers after a comma start a typed declaration.
      // Expression/event operators following an operand keep the ordinary comma.
      auto next=text.find_first_not_of(" \t\r\n",end);auto word=text.substr(next);
      if(word!="inside"&&word!="or"&&word!="iff"&&word!="with"&&word!="dist"&&word!="matches")token=vPORT_DELIM;
    }
  }
  yyless(1);count();return token;
}
","{WHITE}*"interface"{NONID} { yyless(1);count();return veri_parser->systemverilog()?vPORT_DELIM:','; }
","{WHITE}*"input"{NONID}   { yyless(1); count(); return vPORT_DELIM;  }
","{WHITE}*"inout"{NONID}   { yyless(1); count(); return vPORT_DELIM;  }
","{WHITE}*"const"{NONID}   { yyless(1); count(); return veri_parser->systemverilog()?vPORT_DELIM:','; }
","{WHITE}*"ref"{NONID}     { yyless(1); count(); return veri_parser->systemverilog()?vPORT_DELIM:','; }
","{WHITE}*"output"{NONID}  { yyless(1); count(); return vPORT_DELIM;  }
","{WHITE}*"parameter"{NONID}  { yyless(1); count(); return vPARAM_DELIM; }
","{WHITE}*"localparam"{NONID} { yyless(1); count(); return vPARAM_DELIM; }

"specify"               { count(); BEGIN _OMIT_;   }
<_OMIT_>"endspecify"    { count(); BEGIN INITIAL;  }

"clocking" { count(); return SV_KEYWORD(vCLOCKING); }
"covergroup" { count(); return SV_KEYWORD(vCOVERGROUP); }
"endgroup" { count(); return SV_KEYWORD(vENDGROUP); }
"coverpoint" { count(); return SV_KEYWORD(vCOVERPOINT); }
"cross" { count(); return SV_KEYWORD(vCROSS); }
"bins" { count(); return SV_KEYWORD(vBINS); }
"ignore_bins" { count(); return SV_KEYWORD(vIGNORE_BINS); }
"illegal_bins" { count(); return SV_KEYWORD(vILLEGAL_BINS); }
"endclocking" { count(); return SV_KEYWORD(vENDCLOCKING); }
"1step" { count(); return SV_KEYWORD(vSTEP); }
"interface" { count(); return SV_KEYWORD(vINTERFACE); }
"endinterface" { count(); return SV_KEYWORD(vENDINTERFACE); }
"modport" { count(); return SV_KEYWORD(vMODPORT); }

"always_comb"   { count(); return SV_KEYWORD(vALWAYS_COMB); }
"always_ff"     { count(); return SV_KEYWORD(vALWAYS_FF);   }
"always_latch"  { count(); return SV_KEYWORD(vALWAYS_LATCH);}
"always"        { count(); return vALWAYS;    }
"and"           { count(); return vAND_ASCII; }
"assign"        { count(); return vASSIGN;    }
"automatic"     { count(); return vAUTO;      }
"static"        { count(); return SV_KEYWORD(vSTATIC);    }
"begin"         { count(); return vBEGIN;     }
"bit"           { count(); return SV_KEYWORD(vBIT);       }
"byte"          { count(); return SV_KEYWORD(vBYTE);      }
"buf"           { count(); return vBUF_ASCII; }
"bufif0"        { count(); return vBUFIF_A;   }
"bufif1"        { count(); return vBUFIF_B;   }
"inside"        { count(); return SV_KEYWORD(vINSIDE); }
"with"          { count(); return SV_KEYWORD(vWITH); }
"var"           { count(); return SV_KEYWORD(vVAR_PORT); }
"case"          { count(); return vCASE;      }
"casex"         { count(); return vCASEX;     }
"casez"         { count(); return vCASEZ;     }
"cell"          { count(); return vCELL;      }
"cmos"          { count(); return vNOT_SUPPORTED;      }
"config"        { count(); return vCONFIG;    }
"deassign"      { count(); return vNOT_SUPPORTED;  }
"default"       { count(); return vDEFAULT;   }
"defparam"      { count(); return vNOT_SUPPORTED;  }
"design"        { count(); return vDESIGN;    }
"disable"       { count(); return vDISABLE;   }
"do"            { count(); return SV_KEYWORD(vDO);        }
"edge"          { count(); return vNOT_SUPPORTED;      }
"property"      { count(); return SV_KEYWORD(vPROPERTY); }
"endproperty"   { count(); return SV_KEYWORD(vENDPROPERTY); }
"sequence"      { count(); return SV_KEYWORD(vSEQUENCE); }
"endsequence"   { count(); return SV_KEYWORD(vENDSEQUENCE); }
"|->"           { count(); return vOVERLAP; }
"|=>"           { count(); return vNONOVERLAP; }
"assert"        { count(); return SV_KEYWORD(vASSERT); }
"assume"        { count(); return SV_KEYWORD(vASSUME); }
"cover"         { count(); return SV_KEYWORD(vCOVER); }
"else"          { count(); return vELSE;      }
"end"           { count(); return vEND;       }
"endcase"       { count(); return vENDCASE;   }
"endconfig"     { count(); return vENDCONFIG; }
"endfunction"   { count(); return vENDFUNC;   }
"endgenerate"   { count(); return vENDGEN;    }
"endmodule"     { count(); return vENDMODULE; }
"endprimitive"  { count(); return vNOT_SUPPORTED;    }
"endtable"      { count(); return vNOT_SUPPORTED;  }
"endtask"       { count(); return vENDTASK;   }
"string"        { count(); return SV_KEYWORD(vSTRING_TYPE); }
"chandle" { count(); return SV_KEYWORD(vCHANDLE); }
"event"         { count(); return vEVENT;             }
"for"           { count(); return vFOR;       }
"force"         { count(); return vFORCE;     }
"forever"       { count(); return vFOREVER;   }
"foreach"       { count(); return SV_KEYWORD(vFOREACH);   }
"fork"          { count(); return vFORK;      }
"function"      { count(); return vFUNC;      }
"generate"      { count(); return vGEN;       }
"genvar"        { count(); return vGENVAR;    }
"highz0"        { count(); return vHIGHZ_A;   }
"highz1"        { count(); return vHIGHZ_B;   }
"unique"        { count(); return SV_KEYWORD(vUNIQUE);    }
"unique0"       { count(); return SV_KEYWORD(vUNIQUE0);   }
"priority"      { count(); return SV_KEYWORD(vPRIORITY);  }
"if"            { count(); return vIF;        }
"ifnone"        { count(); return vNOT_SUPPORTED;    }
"-incdir"       { count(); return vINC_DIR;   }
"initial"       { count(); return vINIT;      }
"final"         { count(); return SV_KEYWORD(vFINAL); }
"bind"          { count(); return SV_KEYWORD(vBIND); }
"inout"         { count(); return vINOUT;     }
"input"         { count(); return vINPUT;     }
"ref"           { count(); return SV_KEYWORD(vREF);       }
"new"           { count(); return SV_KEYWORD(vNEW);       }
"class"         { count(); return SV_KEYWORD(vCLASS);     }
"endclass"      { count(); return SV_KEYWORD(vENDCLASS);  }
"null"          { count(); return SV_KEYWORD(vNULL);      }
"this"          { count(); return SV_KEYWORD(vTHIS);      }
"super"         { count(); return SV_KEYWORD(vSUPER);     }
"extends"       { count(); return SV_KEYWORD(vEXTENDS);   }
"virtual"       { count(); return SV_KEYWORD(vVIRTUAL);   }
"pure"          { count(); return SV_KEYWORD(vPURE);      }
"extern" { count(); return SV_KEYWORD(vEXTERN); }
"context"       { count(); return SV_KEYWORD(vCONTEXT);   }
"local"         { count(); return SV_KEYWORD(vLOCAL);     }
"protected"     { count(); return SV_KEYWORD(vPROTECTED); }
"const"         { count(); return SV_KEYWORD(vCONST);     }
"rand"          { count(); return SV_KEYWORD(vRAND);      }
"randc"         { count(); return SV_KEYWORD(vRANDC);     }
"constraint"    { count(); return SV_KEYWORD(vCONSTRAINT); }
"instance"      { count(); return vINSTANCE;  }
"int"           { count(); return SV_KEYWORD(vINT2);       }
"integer"       { count(); return vINT;       }
"join"          { count(); return vJOIN;      }
"join_any"      { count(); return SV_KEYWORD(vJOIN_ANY);  }
"join_none"     { count(); return SV_KEYWORD(vJOIN_NONE); }
"large"         { count(); return vNOT_SUPPORTED;     }
"liblist"       { count(); return vLIBLIST;   }
"library"       { count(); return vLIB;       }
"logic"         { count(); return SV_KEYWORD(vLOGIC);     }
"typedef"       { count(); return SV_KEYWORD(vTYPEDEF);   }
"type"          { count(); return SV_KEYWORD(vTYPE); }
"enum"          { count(); return SV_KEYWORD(vENUM);      }
"struct"        { count(); return SV_KEYWORD(vSTRUCT);    }
"union"         { count(); return SV_KEYWORD(vUNION);     }
"packed"        { count(); return SV_KEYWORD(vPACKED);    }
"package"       { count(); return SV_KEYWORD(vPACKAGE); }
"endpackage"    { count(); return SV_KEYWORD(vENDPACKAGE); }
"import"        { count(); return SV_KEYWORD(vIMPORT); }
"export"        { count(); return SV_KEYWORD(vEXPORT); }
"longint"       { count(); return SV_KEYWORD(vLONGINT);   }
"localparam"    { count(); return vLOCAL_PARAM;  }
"macromodule"   { count(); return vNOT_SUPPORTED; }
"medium"        { count(); return vNOT_SUPPORTED;    }
"module"        { count(); return vMODULE;    }
"nand"          { count(); return vNAND_ASCII;}
"negedge"       { count(); return vNEGEDGE;   }
"nmos"          { count(); return vNOT_SUPPORTED;      }
"nor"           { count(); return vNOR_ASCII; }
"not"           { count(); return vNOT_ASCII; }
"notif0"        { count(); return vNOTIF_A;   }
"notif1"        { count(); return vNOTIF_B;   }
"or"            { count(); return vOR_ASCII;  }
"output"        { count(); return vOUTPUT;    }
"parameter"     { count(); return vPARAMETER; }
"pmos"          { count(); return vNOT_SUPPORTED;      }
"posedge"       { count(); return vPOSEDGE;   }
"iff"           { count(); return SV_KEYWORD(vIFF);       }
"primitive"     { count(); return vNOT_SUPPORTED; }
"pull0"         { count(); return vPULL_A;    }
"pull1"         { count(); return vPULL_B;    }
"pulldown"      { count(); return vNOT_SUPPORTED;  }
"pullup"        { count(); return vNOT_SUPPORTED;    }
"noshowcancelled"     { count(); return vNOT_SUPPORTED;  }
"pulsestyle_onevent"  { count(); return vNOT_SUPPORTED;  }
"pulsestyle_ondetect" { count(); return vNOT_SUPPORTED; }
"rcmos"         { count(); return vNOT_SUPPORTED;     }
"real"          { count(); return vREAL; }
"shortreal"     { count(); return SV_KEYWORD(vSHORTREAL); }
"realtime"      { count(); return vREALTIME; }
"reg"           { count(); return vREG;       }
"release"       { count(); return vRELEASE;   }
"repeat"        { count(); return vREPEAT;    }
"rnmos"         { count(); return vNOT_SUPPORTED;     }
"rpmos"         { count(); return vNOT_SUPPORTED;     }
"rtran"         { count(); return vNOT_SUPPORTED;     }
"rtranif0"      { count(); return vNOT_SUPPORTED; }
"rtranif1"      { count(); return vNOT_SUPPORTED; }
"scalared"      { count(); return vSCALARED;  }
"shortint"      { count(); return SV_KEYWORD(vSHORTINT);  }
"showcancelled" { count(); return vNOT_SUPPORTED;  }
"signed"        { count(); return vSIGNED;    }
"small"         { count(); return vNOT_SUPPORTED;     }
"specparam"     { count(); return vSPEC_PARAM;}
"strong0"       { count(); return vSTRONG_A;  }
"strong1"       { count(); return vSTRONG_B;  }
"supply0"       { count(); return vSUPPLY_A;  }
"supply1"       { count(); return vSUPPLY_B;  }
"table"         { count(); return vNOT_SUPPORTED;     }
"task"          { count(); return vTASK;      }
"time"          { count(); return vTIME;      }
"timeunit"      { count(); return SV_KEYWORD(vTIMEUNIT); }
"timeprecision" { count(); return SV_KEYWORD(vTIMEPRECISION); }
"void"          { count(); return SV_KEYWORD(vVOID);      }
"tran"          { count(); return vNOT_SUPPORTED;      }
"tranif0"       { count(); return vNOT_SUPPORTED;  }
"tranif1"       { count(); return vNOT_SUPPORTED;  }
"tri"           { count(); return vTRI;       }
"tri0"          { count(); return vNOT_SUPPORTED;     }
"tri1"          { count(); return vNOT_SUPPORTED;     }
"triand"        { count(); return vTRIAND;    }
"trior"         { count(); return vTRIOR;     }
"trireg"        { count(); return vNOT_SUPPORTED;    }
"unsigned"      { count(); return SV_KEYWORD(vUNSIGNED);  }
"use"           { count(); return vUSE;       }
"vectored"      { count(); return vVECTORED;  }
"wait"          { count(); return vWAIT;               }
"wait_order"    { count(); return SV_KEYWORD(vWAIT_ORDER);         }
"wand"          { count(); return vWAND;      }
"weak0"         { count(); return vWEAK_A;    }
"weak1"         { count(); return vWEAK_B;    }
"while"         { count(); return vWHILE;     }
"wire"          { count(); return vWIRE;      }
"wor"           { count(); return vWOR;       }
"xnor"          { count(); return vXNOR_ASCII;}
"xor"           { count(); return vXOR_ASCII; }

   /* System Parts */
"PATHPULSE$" { count(); return vPATHPULSE;     }
"$signed"    { count(); return vSIGN_FUNC;     }
"$unsigned"  { count(); return vUNSIGN_FUNC;   }
"$setup"     { count(); return vNOT_SUPPORTED; }
"$hold"      { count(); return vNOT_SUPPORTED; }
"$setuphold" { count(); return vNOT_SUPPORTED; }
"$recovery"  { count(); return vNOT_SUPPORTED; }
"$removal"   { count(); return vNOT_SUPPORTED; }
"$recrem"    { count(); return vNOT_SUPPORTED; }
"$skew"      { count(); return vNOT_SUPPORTED; }
"$timeskew"  { count(); return vNOT_SUPPORTED; }
"$fullskew"  { count(); return vNOT_SUPPORTED; }
"$period"    { count(); return vNOT_SUPPORTED; }
"$width"     { count(); return vNOT_SUPPORTED; }
"$nochange"  { count(); return vNOT_SUPPORTED; }

   /* identifiers */
\"([^\"\\\n]|\\[^\n])*\"            { count(); GET_CONTENT; return vSTR;       }

"$dumpvars" { count(); veri_dump_arguments=true; veri_dump_parentheses=0; GET_CONTENT; return vDUMPVARS; }
"$random"|"$urandom"|"$urandom_range" { count(); GET_CONTENT; return vRANDOM_FUNC; }
"$"{L}({AL}|{PD})* { count(); GET_CONTENT; return vSYS_IDENT; }

"`"{L}({AL}|{PD})* { count();
                       veriloglval.symbol.content = strdup(yytext + 1);
                       return vIDENT; }

{L}({AL}|{PD})*({WHITE}*"::"{WHITE}*{L}({AL}|{PD})*)+ {
  count();std::string name;
  for(int i=0;yytext[i];++i)if(!isspace(static_cast<unsigned char>(yytext[i])))name+=yytext[i];else if(yytext[i]=='\n')++veri_lno;
  if(veri_parser->systemverilog()) {
    for(size_t begin=0;begin<name.size();) {
      const auto split=name.find("::",begin);
      if(unsupported_sv_keyword(name.substr(begin,split==std::string::npos?split:split-begin)))return vNOT_SUPPORTED;
      if(split==std::string::npos)break;begin=split+2;
    }
  }
  veriloglval.symbol.content=strdup(name.c_str());return vIDENT;
}
{L}({AL}|{PD})*    { count(); if(veri_parser->systemverilog() && unsupported_sv_keyword(yytext))return vNOT_SUPPORTED; GET_CONTENT; return vIDENT; }

"\\"{NONWHITE}+    { count(); GET_CONTENT; return vIDENT;     }

{PD}{D}*("."{PD}{D}*)?(fs|ps|ns|us|ms|s) { count(); GET_CONTENT; return vTIME_LITERAL; }
{PD}{D}*"."{PD}{D}*({E})? { count(); GET_CONTENT; return vNUMBER; }
{PD}{D}*{E}               { count(); GET_CONTENT; return vNUMBER; }

{PD}?{D}+          { count(); GET_CONTENT; return vNUMBER;    }

({PD}?{D}*)?"'"{S}?{BASE}{SPACE}*{XD}+ { count(); GET_CONTENT; return vNUMBER; }

"'"[01xXzZ]              { count(); GET_CONTENT; return vNUMBER; }

<_OMIT_>.    { count(); }

.            { count(); return ' '; }

%%

namespace {
bool lookahead_space(char c) {return c=='\b'||isspace(static_cast<unsigned char>(c));}
bool lookahead_trivia(const char*& p,const char* end) {
  for(;;) {
    while(p<end&&lookahead_space(*p))++p;
    if(end-p<2||p[0]!='/')return true;
    if(p[1]=='/') {p+=2;while(p<end&&*p&&*p!='\n')++p;}
    else if(p[1]=='*') {
      p+=2;while(end-p>=2&&!(p[0]=='*'&&p[1]=='/'))++p;
      if(end-p<2)return false;p+=2;
    } else return true;
  }
}
std::string lookahead_identifier(const char*& p,const char* end) {
  if(p==end)return {};
  const char* begin=p;
  if(*p=='\\') {++p;while(p<end&&*p&&!lookahead_space(*p))++p;}
  else {
    if(!isalpha(static_cast<unsigned char>(*p))&&*p!='_')return {};
    while(p<end&&(isalnum(static_cast<unsigned char>(*p))||*p=='_'||*p=='$'))++p;
  }
  return std::string(begin,p);
}
// Match arbitrary nesting without consuming Flex input or copying a parameter
// list. Strings, escaped identifiers and comments cannot close a delimiter.
bool lookahead_balanced(const char*& p,const char* end) {
  std::vector<char> closing;
  while(p<end&&*p) {
    if(!lookahead_trivia(p,end)||p==end||!*p)return false;
    const char c=*p++;
    if(c=='"') {
      bool closed=false;
      while(p<end&&*p) {
        const char next=*p++;
        if(next=='\\') {if(p<end&&*p)++p;else return false;}
        else if(next=='"') {closed=true;break;}
      }
      if(!closed)return false;
    } else if(c=='\\') {while(p<end&&*p&&!lookahead_space(*p))++p;}
    else if(c=='('||c=='['||c=='{')closing.push_back(c=='('?')':c=='['?']':'}');
    else if(c==')'||c==']'||c=='}') {
      if(closing.empty()||closing.back()!=c)return false;
      closing.pop_back();if(closing.empty())return true;
    }
  }
  return false;
}
bool lookahead_expression_word(const std::string& word) {
  return word=="inside"||word=="or"||word=="iff"||word=="with"||word=="dist"||word=="matches";
}
}

static int declaration_after_comma() {
  // Flex may have refilled or moved its buffer. Map its current token back to
  // the immutable parser input, including bytes not yet read into the buffer.
  // This avoids unput overflow and does not alter token locations or line state.
  const auto buffered=yy_n_chars-(yytext-YY_CURRENT_BUFFER_LVALUE->yy_ch_buf);
  const char* p=veri_parser->get_s()-buffered+1;
  const char* end=veri_parser->get_s()+veri_parser->get_cur_length();
  if(!lookahead_trivia(p,end))return ',';
  const auto first=lookahead_identifier(p,end);if(first.empty())return ',';
  if(first=="parameter"||first=="localparam"||first=="type")return vPARAM_DELIM;
  if(first=="input"||first=="output"||first=="inout"||first=="ref"||first=="const"||first=="interface")return vPORT_DELIM;
  if(first=="import"||first=="export"||first=="function"||first=="task"||first=="clocking"||first=="posedge"||first=="negedge"||first=="edge")return ',';
  if(!lookahead_trivia(p,end))return ',';
  while(end-p>=2&&p[0]==':'&&p[1]==':') {
    p+=2;if(!lookahead_trivia(p,end)||lookahead_identifier(p,end).empty()||!lookahead_trivia(p,end))return ',';
  }
  if(p<end&&*p=='#') {
    ++p;if(!lookahead_trivia(p,end)||p==end||*p!='('||!lookahead_balanced(p,end)||!lookahead_trivia(p,end))return ',';
  }
  if(p<end&&*p=='.') {
    ++p;if(!lookahead_trivia(p,end)||lookahead_identifier(p,end).empty()||!lookahead_trivia(p,end))return ',';
  }
  const char* qualifier=p;const auto sign=lookahead_identifier(qualifier,end);
  if(sign=="signed"||sign=="unsigned") {p=qualifier;if(!lookahead_trivia(p,end))return ',';}
  while(p<end&&*p=='[') {
    if(!lookahead_balanced(p,end)||!lookahead_trivia(p,end))return ',';
  }
  const auto name=lookahead_identifier(p,end);
  return !name.empty()&&!lookahead_expression_word(name)?vPORT_DELIM:',';
}

int yywrap(void)
{
  return 1;
}

void count(void)
{
  int i;

  for (i = 0; yytext[i] != '\0'; i++)
  {
    if (yytext[i] == '\n')
      veri_col = 0;
    else
      veri_col++;
  }
  veriloglval.symbol.col = veri_col;
  veriloglval.symbol.line = veri_lno;

//  ECHO;
}

void count_line(void)
{
  int i;

  for (i = 0; yytext[i] != '\0'; i++)
  {
    if (yytext[i] == '\n')
      veri_col = 0;
    else
      veri_col++;
  }

//  ECHO;
}

void count_comment(void)
{
  int i;

  for (i = 0; yytext[i] != '\0'; i++)
  {
    if (yytext[i] == '\n')
    {
      veri_col = 0;
      veri_lno++;
    }
    else
      veri_col++;
  }
}

void determin_line_cd( )
{
  switch( veri_include_directive )
  {
    case 0:
      if( just_end == 1 )
      {
        veri_parser->back_to_file( veri_include_line );
        just_end = 0;
      }
      break;

    case 1:  // enter new included file
      veri_parser->include_file( veri_lno, veri_include_fname );
      break;

    case 2:  // end of included file
      veri_parser->exclude_file( );
      just_end = 1;
      break;

    default:
      break;
  }
  veri_lno = veri_include_line;
}
