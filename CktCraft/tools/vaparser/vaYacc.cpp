/* A Bison parser, made by GNU Bison 3.8.2.  */

/* Bison implementation for Yacc-like parsers in C

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

/* C LALR(1) parser skeleton written by Richard Stallman, by
   simplifying the original so-called "semantic" parser.  */

/* DO NOT RELY ON FEATURES THAT ARE NOT DOCUMENTED in the manual,
   especially those whose name start with YY_ or yy_.  They are
   private implementation details that can be changed or removed.  */

/* All symbols defined below should begin with yy or YY, to avoid
   infringing on user name space.  This should be done even for local
   variables, as they might otherwise be expanded by user macros.
   There are some unavoidable exceptions within include files to
   define necessary library symbols; they are noted "INFRINGES ON
   USER NAME SPACE" below.  */

/* Identify Bison output, and Bison version.  */
#define YYBISON 30802

/* Bison version string.  */
#define YYBISON_VERSION "3.8.2"

/* Skeleton name.  */
#define YYSKELETON_NAME "yacc.c"

/* Pure parsers.  */
#define YYPURE 0

/* Push parsers.  */
#define YYPUSH 0

/* Pull parsers.  */
#define YYPULL 1


/* Substitute the variable and function names.  */
#define yyparse         verilogparse
#define yylex           veriloglex
#define yyerror         verilogerror
#define yydebug         verilogdebug
#define yynerrs         verilognerrs
#define yylval          veriloglval
#define yychar          verilogchar

/* First part of user prologue.  */
#line 3 "vaYacc.y"

#define YYDEBUG 1
//#define YYPARSE_PARAM myadmsmain
#include "vaParser.h"

    using std::list;
    using std::cerr;

    string __curFile;
    int __curLine;
    int __curPos;

    int __modDdtNum;

    list<nature*> __natureList;
    list<discipline*> __disList;
    list<module*> __moduleList;
    list<attribute*> __attrList;

    //**Begin global points
    discipline *gDiscipline = NULL;
    module *gModule = NULL;
    string *gNatureAccess = NULL;
    double *gNatureAbsTol = NULL;
    string *gNatureUnits  = NULL;
    string *gNatureidt    = NULL;
    string *gNatureddt    = NULL;
    source *gSource = NULL;
    list<string> gNodeList;
    list<yaccVal*> gCaseList;
    list<list<yaccVal*>*> gCaseStack;   // case 嵌套栈（宏展开 case 里还有 case）
    list<int> gCaseFlagStack;
    vector<string> gBlockNameStack;              // 命名块 begin : name 栈
    vector<map<string,string> > gBlockLocalStack; // 每层的局部变量名映射(原名→唯一名)
    int gBlockMangleCounter = 0;
    attribute* __globalAttr;
    int  gNodeDirection;//1:input 2:output 3:inout
    list<string> gBranchList;
    analogFun *gAnalogfunction = NULL;
    int gVariableType; //1:int 2:real 3:string
    int gCaseFlag = 0; // 0: first case, 1: other cases
    list<string> gVariableList;
    range *gRange;
    list<statement> gStateList;
    map<string, string> gAttribute;
    //list<string> gDerivSetZero;
    map<string, bitset<BIT_> > gOutsideZero;
    //**End global points

    nature* GetNature(const string str)
    {
        using std::iterator;
        typedef list<nature*>::iterator LNiterator;
        LNiterator iter = __natureList.begin();
        while(iter != __natureList.end()){
            if((*iter)->_name == str){
                return *iter;
            }
            ++iter;
        }
        return NULL;
    }


#line 143 "vaYacc.cpp"

# ifndef YY_CAST
#  ifdef __cplusplus
#   define YY_CAST(Type, Val) static_cast<Type> (Val)
#   define YY_REINTERPRET_CAST(Type, Val) reinterpret_cast<Type> (Val)
#  else
#   define YY_CAST(Type, Val) ((Type) (Val))
#   define YY_REINTERPRET_CAST(Type, Val) ((Type) (Val))
#  endif
# endif
# ifndef YY_NULLPTR
#  if defined __cplusplus
#   if 201103L <= __cplusplus
#    define YY_NULLPTR nullptr
#   else
#    define YY_NULLPTR 0
#   endif
#  else
#   define YY_NULLPTR ((void*)0)
#  endif
# endif

#include "vaYacc.hpp"
/* Symbol kind.  */
enum yysymbol_kind_t
{
  YYSYMBOL_YYEMPTY = -2,
  YYSYMBOL_YYEOF = 0,                      /* "end of file"  */
  YYSYMBOL_YYerror = 1,                    /* error  */
  YYSYMBOL_YYUNDEF = 2,                    /* "invalid token"  */
  YYSYMBOL_PREC_IF_THEN = 3,               /* PREC_IF_THEN  */
  YYSYMBOL_tk_from = 4,                    /* tk_from  */
  YYSYMBOL_tk_branch = 5,                  /* tk_branch  */
  YYSYMBOL_tk_number = 6,                  /* tk_number  */
  YYSYMBOL_tk_nature = 7,                  /* tk_nature  */
  YYSYMBOL_tk_aliasparameter = 8,          /* tk_aliasparameter  */
  YYSYMBOL_tk_output = 9,                  /* tk_output  */
  YYSYMBOL_tk_anystring = 10,              /* tk_anystring  */
  YYSYMBOL_tk_dollar_ident = 11,           /* tk_dollar_ident  */
  YYSYMBOL_tk_or = 12,                     /* tk_or  */
  YYSYMBOL_tk_aliasparam = 13,             /* tk_aliasparam  */
  YYSYMBOL_tk_if = 14,                     /* tk_if  */
  YYSYMBOL_tk_analog = 15,                 /* tk_analog  */
  YYSYMBOL_tk_parameter = 16,              /* tk_parameter  */
  YYSYMBOL_tk_discipline = 17,             /* tk_discipline  */
  YYSYMBOL_tk_char = 18,                   /* tk_char  */
  YYSYMBOL_tk_anytext = 19,                /* tk_anytext  */
  YYSYMBOL_tk_for = 20,                    /* tk_for  */
  YYSYMBOL_tk_while = 21,                  /* tk_while  */
  YYSYMBOL_tk_real = 22,                   /* tk_real  */
  YYSYMBOL_tk_op_shr = 23,                 /* tk_op_shr  */
  YYSYMBOL_tk_case = 24,                   /* tk_case  */
  YYSYMBOL_tk_potential = 25,              /* tk_potential  */
  YYSYMBOL_tk_endcase = 26,                /* tk_endcase  */
  YYSYMBOL_tk_inf = 27,                    /* tk_inf  */
  YYSYMBOL_tk_exclude = 28,                /* tk_exclude  */
  YYSYMBOL_tk_ground = 29,                 /* tk_ground  */
  YYSYMBOL_tk_endmodule = 30,              /* tk_endmodule  */
  YYSYMBOL_tk_begin = 31,                  /* tk_begin  */
  YYSYMBOL_tk_enddiscipline = 32,          /* tk_enddiscipline  */
  YYSYMBOL_tk_domain = 33,                 /* tk_domain  */
  YYSYMBOL_tk_ident = 34,                  /* tk_ident  */
  YYSYMBOL_tk_op_shl = 35,                 /* tk_op_shl  */
  YYSYMBOL_tk_string = 36,                 /* tk_string  */
  YYSYMBOL_tk_integer = 37,                /* tk_integer  */
  YYSYMBOL_tk_module = 38,                 /* tk_module  */
  YYSYMBOL_tk_endattribute = 39,           /* tk_endattribute  */
  YYSYMBOL_tk_else = 40,                   /* tk_else  */
  YYSYMBOL_tk_end = 41,                    /* tk_end  */
  YYSYMBOL_tk_inout = 42,                  /* tk_inout  */
  YYSYMBOL_tk_and = 43,                    /* tk_and  */
  YYSYMBOL_tk_bitwise_equr = 44,           /* tk_bitwise_equr  */
  YYSYMBOL_tk_default = 45,                /* tk_default  */
  YYSYMBOL_tk_function = 46,               /* tk_function  */
  YYSYMBOL_tk_input = 47,                  /* tk_input  */
  YYSYMBOL_tk_beginattribute = 48,         /* tk_beginattribute  */
  YYSYMBOL_tk_endnature = 49,              /* tk_endnature  */
  YYSYMBOL_tk_endfunction = 50,            /* tk_endfunction  */
  YYSYMBOL_tk_flow = 51,                   /* tk_flow  */
  YYSYMBOL_52_ = 52,                       /* ';'  */
  YYSYMBOL_53_ = 53,                       /* '='  */
  YYSYMBOL_54_ = 54,                       /* '('  */
  YYSYMBOL_55_ = 55,                       /* ')'  */
  YYSYMBOL_56_ = 56,                       /* ','  */
  YYSYMBOL_57_ = 57,                       /* '['  */
  YYSYMBOL_58_ = 58,                       /* ':'  */
  YYSYMBOL_59_ = 59,                       /* ']'  */
  YYSYMBOL_60_ = 60,                       /* '-'  */
  YYSYMBOL_61_ = 61,                       /* '+'  */
  YYSYMBOL_62_ = 62,                       /* '@'  */
  YYSYMBOL_63_ = 63,                       /* '<'  */
  YYSYMBOL_64_ = 64,                       /* '#'  */
  YYSYMBOL_65___ = 65,                     /* '_'  */
  YYSYMBOL_66_ = 66,                       /* '?'  */
  YYSYMBOL_67_ = 67,                       /* '~'  */
  YYSYMBOL_68_ = 68,                       /* '^'  */
  YYSYMBOL_69_ = 69,                       /* '|'  */
  YYSYMBOL_70_ = 70,                       /* '&'  */
  YYSYMBOL_71_ = 71,                       /* '!'  */
  YYSYMBOL_72_ = 72,                       /* '>'  */
  YYSYMBOL_73_ = 73,                       /* '*'  */
  YYSYMBOL_74_ = 74,                       /* '/'  */
  YYSYMBOL_75_ = 75,                       /* '%'  */
  YYSYMBOL_YYACCEPT = 76,                  /* $accept  */
  YYSYMBOL_R_admsParse = 77,               /* R_admsParse  */
  YYSYMBOL_R_l_admsParse = 78,             /* R_l_admsParse  */
  YYSYMBOL_R_s_admsParse = 79,             /* R_s_admsParse  */
  YYSYMBOL_R_discipline_member = 80,       /* R_discipline_member  */
  YYSYMBOL_R_discipline_name = 81,         /* R_discipline_name  */
  YYSYMBOL_R_l_discipline_assignment = 82, /* R_l_discipline_assignment  */
  YYSYMBOL_R_s_discipline_assignment = 83, /* R_s_discipline_assignment  */
  YYSYMBOL_R_discipline_naturename = 84,   /* R_discipline_naturename  */
  YYSYMBOL_R_nature_member = 85,           /* R_nature_member  */
  YYSYMBOL_R_l_nature_assignment = 86,     /* R_l_nature_assignment  */
  YYSYMBOL_R_s_nature_assignment = 87,     /* R_s_nature_assignment  */
  YYSYMBOL_R_d_attribute_0 = 88,           /* R_d_attribute_0  */
  YYSYMBOL_R_d_attribute = 89,             /* R_d_attribute  */
  YYSYMBOL_R_l_attribute = 90,             /* R_l_attribute  */
  YYSYMBOL_R_s_attribute = 91,             /* R_s_attribute  */
  YYSYMBOL_R_d_module = 92,                /* R_d_module  */
  YYSYMBOL_93_1 = 93,                      /* $@1  */
  YYSYMBOL_R_modulebody = 94,              /* R_modulebody  */
  YYSYMBOL_R_netlist = 95,                 /* R_netlist  */
  YYSYMBOL_R_l_instance = 96,              /* R_l_instance  */
  YYSYMBOL_R_d_terminal = 97,              /* R_d_terminal  */
  YYSYMBOL_R_l_terminal_0 = 98,            /* R_l_terminal_0  */
  YYSYMBOL_R_l_terminal = 99,              /* R_l_terminal  */
  YYSYMBOL_R_s_terminal = 100,             /* R_s_terminal  */
  YYSYMBOL_R_l_declaration = 101,          /* R_l_declaration  */
  YYSYMBOL_R_s_declaration_withattribute = 102, /* R_s_declaration_withattribute  */
  YYSYMBOL_R_d_attribute_global = 103,     /* R_d_attribute_global  */
  YYSYMBOL_R_s_declaration = 104,          /* R_s_declaration  */
  YYSYMBOL_R_s_param_declaration = 105,    /* R_s_param_declaration  */
  YYSYMBOL_R_d_node = 106,                 /* R_d_node  */
  YYSYMBOL_R_node_type = 107,              /* R_node_type  */
  YYSYMBOL_R_l_terminalnode = 108,         /* R_l_terminalnode  */
  YYSYMBOL_R_l_node = 109,                 /* R_l_node  */
  YYSYMBOL_R_s_terminalnode = 110,         /* R_s_terminalnode  */
  YYSYMBOL_R_s_node = 111,                 /* R_s_node  */
  YYSYMBOL_R_d_branch = 112,               /* R_d_branch  */
  YYSYMBOL_R_l_branchalias = 113,          /* R_l_branchalias  */
  YYSYMBOL_R_s_branchalias = 114,          /* R_s_branchalias  */
  YYSYMBOL_R_s_branch = 115,               /* R_s_branch  */
  YYSYMBOL_R_d_analogfunction = 116,       /* R_d_analogfunction  */
  YYSYMBOL_R_d_analogfunction_proto = 117, /* R_d_analogfunction_proto  */
  YYSYMBOL_R_d_analogfunction_name = 118,  /* R_d_analogfunction_name  */
  YYSYMBOL_R_l_analogfunction_declaration = 119, /* R_l_analogfunction_declaration  */
  YYSYMBOL_R_s_analogfunction_declaration = 120, /* R_s_analogfunction_declaration  */
  YYSYMBOL_R_l_analogfunction_input_variable = 121, /* R_l_analogfunction_input_variable  */
  YYSYMBOL_R_l_analogfunction_output_variable = 122, /* R_l_analogfunction_output_variable  */
  YYSYMBOL_R_l_analogfunction_inout_variable = 123, /* R_l_analogfunction_inout_variable  */
  YYSYMBOL_R_l_analogfunction_integer_variable = 124, /* R_l_analogfunction_integer_variable  */
  YYSYMBOL_R_l_analogfunction_real_variable = 125, /* R_l_analogfunction_real_variable  */
  YYSYMBOL_R_variable_type = 126,          /* R_variable_type  */
  YYSYMBOL_R_d_variable_end = 127,         /* R_d_variable_end  */
  YYSYMBOL_R_l_parameter = 128,            /* R_l_parameter  */
  YYSYMBOL_R_l_variable = 129,             /* R_l_variable  */
  YYSYMBOL_R_d_aliasparameter = 130,       /* R_d_aliasparameter  */
  YYSYMBOL_R_d_aliasparameter_token = 131, /* R_d_aliasparameter_token  */
  YYSYMBOL_R_s_parameter = 132,            /* R_s_parameter  */
  YYSYMBOL_R_s_variable = 133,             /* R_s_variable  */
  YYSYMBOL_R_s_parameter_name = 134,       /* R_s_parameter_name  */
  YYSYMBOL_R_s_variable_name = 135,        /* R_s_variable_name  */
  YYSYMBOL_R_s_parameter_range = 136,      /* R_s_parameter_range  */
  YYSYMBOL_R_l_interval = 137,             /* R_l_interval  */
  YYSYMBOL_R_s_interval = 138,             /* R_s_interval  */
  YYSYMBOL_R_d_interval = 139,             /* R_d_interval  */
  YYSYMBOL_R_interval_seg = 140,           /* R_interval_seg  */
  YYSYMBOL_R_interval_inf = 141,           /* R_interval_inf  */
  YYSYMBOL_R_interval_sup = 142,           /* R_interval_sup  */
  YYSYMBOL_R_analog = 143,                 /* R_analog  */
  YYSYMBOL_R_analogcode = 144,             /* R_analogcode  */
  YYSYMBOL_R_analogcode_atomic = 145,      /* R_analogcode_atomic  */
  YYSYMBOL_R_analogcode_block = 146,       /* R_analogcode_block  */
  YYSYMBOL_R_analogcode_block_atevent = 147, /* R_analogcode_block_atevent  */
  YYSYMBOL_R_l_analysis = 148,             /* R_l_analysis  */
  YYSYMBOL_R_s_analysis = 149,             /* R_s_analysis  */
  YYSYMBOL_R_d_block = 150,                /* R_d_block  */
  YYSYMBOL_151_2 = 151,                    /* $@2  */
  YYSYMBOL_R_d_block_begin = 152,          /* R_d_block_begin  */
  YYSYMBOL_R_l_blockitem = 153,            /* R_l_blockitem  */
  YYSYMBOL_R_d_blockvariable = 154,        /* R_d_blockvariable  */
  YYSYMBOL_R_l_blockvariable = 155,        /* R_l_blockvariable  */
  YYSYMBOL_R_s_blockvariable = 156,        /* R_s_blockvariable  */
  YYSYMBOL_R_d_contribution = 157,         /* R_d_contribution  */
  YYSYMBOL_R_contribution = 158,           /* R_contribution  */
  YYSYMBOL_R_source = 159,                 /* R_source  */
  YYSYMBOL_R_d_while = 160,                /* R_d_while  */
  YYSYMBOL_R_d_for = 161,                  /* R_d_for  */
  YYSYMBOL_R_d_case = 162,                 /* R_d_case  */
  YYSYMBOL_163_3 = 163,                    /* $@3  */
  YYSYMBOL_R_l_case_item = 164,            /* R_l_case_item  */
  YYSYMBOL_R_s_case_item = 165,            /* R_s_case_item  */
  YYSYMBOL_R_s_instance = 166,             /* R_s_instance  */
  YYSYMBOL_R_instance_module_name = 167,   /* R_instance_module_name  */
  YYSYMBOL_R_l_instance_parameter = 168,   /* R_l_instance_parameter  */
  YYSYMBOL_R_s_instance_parameter = 169,   /* R_s_instance_parameter  */
  YYSYMBOL_R_s_assignment = 170,           /* R_s_assignment  */
  YYSYMBOL_R_s_assignment_name = 171,      /* R_s_assignment_name  */
  YYSYMBOL_R_d_conditional = 172,          /* R_d_conditional  */
  YYSYMBOL_R_s_expression = 173,           /* R_s_expression  */
  YYSYMBOL_R_l_callfunction_expression = 174, /* R_l_callfunction_expression  */
  YYSYMBOL_R_l_expression = 175,           /* R_l_expression  */
  YYSYMBOL_R_s_function_expression = 176,  /* R_s_function_expression  */
  YYSYMBOL_R_expression = 177,             /* R_expression  */
  YYSYMBOL_R_e_conditional = 178,          /* R_e_conditional  */
  YYSYMBOL_R_e_bitwise_equ = 179,          /* R_e_bitwise_equ  */
  YYSYMBOL_R_e_bitwise_xor = 180,          /* R_e_bitwise_xor  */
  YYSYMBOL_R_e_bitwise_or = 181,           /* R_e_bitwise_or  */
  YYSYMBOL_R_e_bitwise_and = 182,          /* R_e_bitwise_and  */
  YYSYMBOL_R_e_logical_or = 183,           /* R_e_logical_or  */
  YYSYMBOL_R_e_logical_and = 184,          /* R_e_logical_and  */
  YYSYMBOL_R_e_comp_equ = 185,             /* R_e_comp_equ  */
  YYSYMBOL_R_e_comp = 186,                 /* R_e_comp  */
  YYSYMBOL_R_e_bitwise_shift = 187,        /* R_e_bitwise_shift  */
  YYSYMBOL_R_e_arithm_add = 188,           /* R_e_arithm_add  */
  YYSYMBOL_R_e_arithm_mult = 189,          /* R_e_arithm_mult  */
  YYSYMBOL_R_e_unary = 190,                /* R_e_unary  */
  YYSYMBOL_R_e_atomic = 191                /* R_e_atomic  */
};
typedef enum yysymbol_kind_t yysymbol_kind_t;




#ifdef short
# undef short
#endif

/* On compilers that do not define __PTRDIFF_MAX__ etc., make sure
   <limits.h> and (if available) <stdint.h> are included
   so that the code can choose integer types of a good width.  */

#ifndef __PTRDIFF_MAX__
# include <limits.h> /* INFRINGES ON USER NAME SPACE */
# if defined __STDC_VERSION__ && 199901 <= __STDC_VERSION__
#  include <stdint.h> /* INFRINGES ON USER NAME SPACE */
#  define YY_STDINT_H
# endif
#endif

/* Narrow types that promote to a signed type and that can represent a
   signed or unsigned integer of at least N bits.  In tables they can
   save space and decrease cache pressure.  Promoting to a signed type
   helps avoid bugs in integer arithmetic.  */

#ifdef __INT_LEAST8_MAX__
typedef __INT_LEAST8_TYPE__ yytype_int8;
#elif defined YY_STDINT_H
typedef int_least8_t yytype_int8;
#else
typedef signed char yytype_int8;
#endif

#ifdef __INT_LEAST16_MAX__
typedef __INT_LEAST16_TYPE__ yytype_int16;
#elif defined YY_STDINT_H
typedef int_least16_t yytype_int16;
#else
typedef short yytype_int16;
#endif

/* Work around bug in HP-UX 11.23, which defines these macros
   incorrectly for preprocessor constants.  This workaround can likely
   be removed in 2023, as HPE has promised support for HP-UX 11.23
   (aka HP-UX 11i v2) only through the end of 2022; see Table 2 of
   <https://h20195.www2.hpe.com/V2/getpdf.aspx/4AA4-7673ENW.pdf>.  */
#ifdef __hpux
# undef UINT_LEAST8_MAX
# undef UINT_LEAST16_MAX
# define UINT_LEAST8_MAX 255
# define UINT_LEAST16_MAX 65535
#endif

#if defined __UINT_LEAST8_MAX__ && __UINT_LEAST8_MAX__ <= __INT_MAX__
typedef __UINT_LEAST8_TYPE__ yytype_uint8;
#elif (!defined __UINT_LEAST8_MAX__ && defined YY_STDINT_H \
       && UINT_LEAST8_MAX <= INT_MAX)
typedef uint_least8_t yytype_uint8;
#elif !defined __UINT_LEAST8_MAX__ && UCHAR_MAX <= INT_MAX
typedef unsigned char yytype_uint8;
#else
typedef short yytype_uint8;
#endif

#if defined __UINT_LEAST16_MAX__ && __UINT_LEAST16_MAX__ <= __INT_MAX__
typedef __UINT_LEAST16_TYPE__ yytype_uint16;
#elif (!defined __UINT_LEAST16_MAX__ && defined YY_STDINT_H \
       && UINT_LEAST16_MAX <= INT_MAX)
typedef uint_least16_t yytype_uint16;
#elif !defined __UINT_LEAST16_MAX__ && USHRT_MAX <= INT_MAX
typedef unsigned short yytype_uint16;
#else
typedef int yytype_uint16;
#endif

#ifndef YYPTRDIFF_T
# if defined __PTRDIFF_TYPE__ && defined __PTRDIFF_MAX__
#  define YYPTRDIFF_T __PTRDIFF_TYPE__
#  define YYPTRDIFF_MAXIMUM __PTRDIFF_MAX__
# elif defined PTRDIFF_MAX
#  ifndef ptrdiff_t
#   include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  endif
#  define YYPTRDIFF_T ptrdiff_t
#  define YYPTRDIFF_MAXIMUM PTRDIFF_MAX
# else
#  define YYPTRDIFF_T long
#  define YYPTRDIFF_MAXIMUM LONG_MAX
# endif
#endif

#ifndef YYSIZE_T
# ifdef __SIZE_TYPE__
#  define YYSIZE_T __SIZE_TYPE__
# elif defined size_t
#  define YYSIZE_T size_t
# elif defined __STDC_VERSION__ && 199901 <= __STDC_VERSION__
#  include <stddef.h> /* INFRINGES ON USER NAME SPACE */
#  define YYSIZE_T size_t
# else
#  define YYSIZE_T unsigned
# endif
#endif

#define YYSIZE_MAXIMUM                                  \
  YY_CAST (YYPTRDIFF_T,                                 \
           (YYPTRDIFF_MAXIMUM < YY_CAST (YYSIZE_T, -1)  \
            ? YYPTRDIFF_MAXIMUM                         \
            : YY_CAST (YYSIZE_T, -1)))

#define YYSIZEOF(X) YY_CAST (YYPTRDIFF_T, sizeof (X))


/* Stored state numbers (used for stacks). */
typedef yytype_int16 yy_state_t;

/* State numbers in computations.  */
typedef int yy_state_fast_t;

#ifndef YY_
# if defined YYENABLE_NLS && YYENABLE_NLS
#  if ENABLE_NLS
#   include <libintl.h> /* INFRINGES ON USER NAME SPACE */
#   define YY_(Msgid) dgettext ("bison-runtime", Msgid)
#  endif
# endif
# ifndef YY_
#  define YY_(Msgid) Msgid
# endif
#endif


#ifndef YY_ATTRIBUTE_PURE
# if defined __GNUC__ && 2 < __GNUC__ + (96 <= __GNUC_MINOR__)
#  define YY_ATTRIBUTE_PURE __attribute__ ((__pure__))
# else
#  define YY_ATTRIBUTE_PURE
# endif
#endif

#ifndef YY_ATTRIBUTE_UNUSED
# if defined __GNUC__ && 2 < __GNUC__ + (7 <= __GNUC_MINOR__)
#  define YY_ATTRIBUTE_UNUSED __attribute__ ((__unused__))
# else
#  define YY_ATTRIBUTE_UNUSED
# endif
#endif

/* Suppress unused-variable warnings by "using" E.  */
#if ! defined lint || defined __GNUC__
# define YY_USE(E) ((void) (E))
#else
# define YY_USE(E) /* empty */
#endif

/* Suppress an incorrect diagnostic about yylval being uninitialized.  */
#if defined __GNUC__ && ! defined __ICC && 406 <= __GNUC__ * 100 + __GNUC_MINOR__
# if __GNUC__ * 100 + __GNUC_MINOR__ < 407
#  define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN                           \
    _Pragma ("GCC diagnostic push")                                     \
    _Pragma ("GCC diagnostic ignored \"-Wuninitialized\"")
# else
#  define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN                           \
    _Pragma ("GCC diagnostic push")                                     \
    _Pragma ("GCC diagnostic ignored \"-Wuninitialized\"")              \
    _Pragma ("GCC diagnostic ignored \"-Wmaybe-uninitialized\"")
# endif
# define YY_IGNORE_MAYBE_UNINITIALIZED_END      \
    _Pragma ("GCC diagnostic pop")
#else
# define YY_INITIAL_VALUE(Value) Value
#endif
#ifndef YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
# define YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
# define YY_IGNORE_MAYBE_UNINITIALIZED_END
#endif
#ifndef YY_INITIAL_VALUE
# define YY_INITIAL_VALUE(Value) /* Nothing. */
#endif

#if defined __cplusplus && defined __GNUC__ && ! defined __ICC && 6 <= __GNUC__
# define YY_IGNORE_USELESS_CAST_BEGIN                          \
    _Pragma ("GCC diagnostic push")                            \
    _Pragma ("GCC diagnostic ignored \"-Wuseless-cast\"")
# define YY_IGNORE_USELESS_CAST_END            \
    _Pragma ("GCC diagnostic pop")
#endif
#ifndef YY_IGNORE_USELESS_CAST_BEGIN
# define YY_IGNORE_USELESS_CAST_BEGIN
# define YY_IGNORE_USELESS_CAST_END
#endif


#define YY_ASSERT(E) ((void) (0 && (E)))

#if !defined yyoverflow

/* The parser invokes alloca or malloc; define the necessary symbols.  */

# ifdef YYSTACK_USE_ALLOCA
#  if YYSTACK_USE_ALLOCA
#   ifdef __GNUC__
#    define YYSTACK_ALLOC __builtin_alloca
#   elif defined __BUILTIN_VA_ARG_INCR
#    include <alloca.h> /* INFRINGES ON USER NAME SPACE */
#   elif defined _AIX
#    define YYSTACK_ALLOC __alloca
#   elif defined _MSC_VER
#    include <malloc.h> /* INFRINGES ON USER NAME SPACE */
#    define alloca _alloca
#   else
#    define YYSTACK_ALLOC alloca
#    if ! defined _ALLOCA_H && ! defined EXIT_SUCCESS
#     include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
      /* Use EXIT_SUCCESS as a witness for stdlib.h.  */
#     ifndef EXIT_SUCCESS
#      define EXIT_SUCCESS 0
#     endif
#    endif
#   endif
#  endif
# endif

# ifdef YYSTACK_ALLOC
   /* Pacify GCC's 'empty if-body' warning.  */
#  define YYSTACK_FREE(Ptr) do { /* empty */; } while (0)
#  ifndef YYSTACK_ALLOC_MAXIMUM
    /* The OS might guarantee only one guard page at the bottom of the stack,
       and a page size can be as small as 4096 bytes.  So we cannot safely
       invoke alloca (N) if N exceeds 4096.  Use a slightly smaller number
       to allow for a few compiler-allocated temporary stack slots.  */
#   define YYSTACK_ALLOC_MAXIMUM 4032 /* reasonable circa 2006 */
#  endif
# else
#  define YYSTACK_ALLOC YYMALLOC
#  define YYSTACK_FREE YYFREE
#  ifndef YYSTACK_ALLOC_MAXIMUM
#   define YYSTACK_ALLOC_MAXIMUM YYSIZE_MAXIMUM
#  endif
#  if (defined __cplusplus && ! defined EXIT_SUCCESS \
       && ! ((defined YYMALLOC || defined malloc) \
             && (defined YYFREE || defined free)))
#   include <stdlib.h> /* INFRINGES ON USER NAME SPACE */
#   ifndef EXIT_SUCCESS
#    define EXIT_SUCCESS 0
#   endif
#  endif
#  ifndef YYMALLOC
#   define YYMALLOC malloc
#   if ! defined malloc && ! defined EXIT_SUCCESS
void *malloc (YYSIZE_T); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
#  ifndef YYFREE
#   define YYFREE free
#   if ! defined free && ! defined EXIT_SUCCESS
void free (void *); /* INFRINGES ON USER NAME SPACE */
#   endif
#  endif
# endif
#endif /* !defined yyoverflow */

#if (! defined yyoverflow \
     && (! defined __cplusplus \
         || (defined YYSTYPE_IS_TRIVIAL && YYSTYPE_IS_TRIVIAL)))

/* A type that is properly aligned for any stack member.  */
union yyalloc
{
  yy_state_t yyss_alloc;
  YYSTYPE yyvs_alloc;
};

/* The size of the maximum gap between one aligned stack and the next.  */
# define YYSTACK_GAP_MAXIMUM (YYSIZEOF (union yyalloc) - 1)

/* The size of an array large to enough to hold all stacks, each with
   N elements.  */
# define YYSTACK_BYTES(N) \
     ((N) * (YYSIZEOF (yy_state_t) + YYSIZEOF (YYSTYPE)) \
      + YYSTACK_GAP_MAXIMUM)

# define YYCOPY_NEEDED 1

/* Relocate STACK from its old location to the new one.  The
   local variables YYSIZE and YYSTACKSIZE give the old and new number of
   elements in the stack, and YYPTR gives the new location of the
   stack.  Advance YYPTR to a properly aligned location for the next
   stack.  */
# define YYSTACK_RELOCATE(Stack_alloc, Stack)                           \
    do                                                                  \
      {                                                                 \
        YYPTRDIFF_T yynewbytes;                                         \
        YYCOPY (&yyptr->Stack_alloc, Stack, yysize);                    \
        Stack = &yyptr->Stack_alloc;                                    \
        yynewbytes = yystacksize * YYSIZEOF (*Stack) + YYSTACK_GAP_MAXIMUM; \
        yyptr += yynewbytes / YYSIZEOF (*yyptr);                        \
      }                                                                 \
    while (0)

#endif

#if defined YYCOPY_NEEDED && YYCOPY_NEEDED
/* Copy COUNT objects from SRC to DST.  The source and destination do
   not overlap.  */
# ifndef YYCOPY
#  if defined __GNUC__ && 1 < __GNUC__
#   define YYCOPY(Dst, Src, Count) \
      __builtin_memcpy (Dst, Src, YY_CAST (YYSIZE_T, (Count)) * sizeof (*(Src)))
#  else
#   define YYCOPY(Dst, Src, Count)              \
      do                                        \
        {                                       \
          YYPTRDIFF_T yyi;                      \
          for (yyi = 0; yyi < (Count); yyi++)   \
            (Dst)[yyi] = (Src)[yyi];            \
        }                                       \
      while (0)
#  endif
# endif
#endif /* !YYCOPY_NEEDED */

/* YYFINAL -- State number of the termination state.  */
#define YYFINAL  20
/* YYLAST -- Last index in YYTABLE.  */
#define YYLAST   632

/* YYNTOKENS -- Number of terminals.  */
#define YYNTOKENS  76
/* YYNNTS -- Number of nonterminals.  */
#define YYNNTS  116
/* YYNRULES -- Number of rules.  */
#define YYNRULES  254
/* YYNSTATES -- Number of states.  */
#define YYNSTATES  502

/* YYMAXUTOK -- Last valid token kind.  */
#define YYMAXUTOK   306


/* YYTRANSLATE(TOKEN-NUM) -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex, with out-of-bounds checking.  */
#define YYTRANSLATE(YYX)                                \
  (0 <= (YYX) && (YYX) <= YYMAXUTOK                     \
   ? YY_CAST (yysymbol_kind_t, yytranslate[YYX])        \
   : YYSYMBOL_YYUNDEF)

/* YYTRANSLATE[TOKEN-NUM] -- Symbol number corresponding to TOKEN-NUM
   as returned by yylex.  */
static const yytype_int8 yytranslate[] =
{
       0,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,    71,     2,    64,     2,    75,    70,     2,
      54,    55,    73,    61,    56,    60,     2,    74,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,    58,    52,
      63,    53,    72,    66,    62,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,    57,     2,    59,    68,    65,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,    69,     2,    67,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     2,     2,     2,     2,
       2,     2,     2,     2,     2,     2,     1,     2,     3,     4,
       5,     6,     7,     8,     9,    10,    11,    12,    13,    14,
      15,    16,    17,    18,    19,    20,    21,    22,    23,    24,
      25,    26,    27,    28,    29,    30,    31,    32,    33,    34,
      35,    36,    37,    38,    39,    40,    41,    42,    43,    44,
      45,    46,    47,    48,    49,    50,    51
};

#if YYDEBUG
/* YYRLINE[YYN] -- Source line where rule number YYN was defined.  */
static const yytype_int16 yyrline[] =
{
       0,   240,   240,   245,   248,   253,   256,   259,   265,   272,
     279,   282,   287,   295,   303,   315,   323,   354,   357,   362,
     375,   411,   423,   454,   456,   461,   468,   475,   480,   483,
     488,   498,   497,   522,   524,   527,   530,   535,   538,   541,
     544,   547,   552,   555,   560,   570,   572,   577,   580,   585,
     601,   604,   609,   612,   619,   626,   629,   632,   635,   638,
     641,   644,   650,   653,   658,   663,   667,   691,   697,   703,
     711,   714,   719,   722,   727,   750,   769,   774,   777,   782,
     789,   814,   838,   847,   854,   859,   867,   872,   875,   880,
     883,   886,   889,   892,   897,   901,   907,   911,   917,   921,
     927,   931,   937,   941,   947,   951,   955,   961,   975,   978,
     983,   986,   991,   997,  1000,  1005,  1022,  1030,  1061,  1067,
    1074,  1076,  1081,  1084,  1090,  1094,  1098,  1112,  1116,  1120,
    1124,  1128,  1135,  1138,  1144,  1148,  1155,  1159,  1164,  1171,
    1186,  1194,  1200,  1207,  1212,  1217,  1234,  1238,  1242,  1246,
    1288,  1292,  1296,  1303,  1307,  1313,  1317,  1322,  1332,  1335,
    1340,  1345,  1349,  1353,  1358,  1357,  1371,  1379,  1383,  1403,
    1410,  1417,  1426,  1429,  1434,  1438,  1444,  1453,  1597,  1638,
    1687,  1721,  1765,  1764,  1844,  1849,  1857,  1886,  1914,  1945,
    1950,  1956,  1959,  1964,  1969,  1996,  2004,  2010,  2019,  2051,
    2112,  2118,  2123,  2131,  2136,  2145,  2151,  2157,  2161,  2199,
    2203,  2207,  2213,  2217,  2223,  2227,  2233,  2237,  2243,  2247,
    2253,  2257,  2263,  2267,  2271,  2277,  2281,  2285,  2289,  2293,
    2299,  2303,  2307,  2313,  2317,  2321,  2327,  2331,  2335,  2339,
    2345,  2349,  2353,  2360,  2366,  2372,  2380,  2409,  2413,  2421,
    2473,  2482,  2486,  2531,  2847
};
#endif

/** Accessing symbol of state STATE.  */
#define YY_ACCESSING_SYMBOL(State) YY_CAST (yysymbol_kind_t, yystos[State])

#if YYDEBUG || 0
/* The user-facing name of the symbol whose (internal) number is
   YYSYMBOL.  No bounds checking.  */
static const char *yysymbol_name (yysymbol_kind_t yysymbol) YY_ATTRIBUTE_UNUSED;

/* YYTNAME[SYMBOL-NUM] -- String name of the symbol SYMBOL-NUM.
   First, the terminals, then, starting at YYNTOKENS, nonterminals.  */
static const char *const yytname[] =
{
  "\"end of file\"", "error", "\"invalid token\"", "PREC_IF_THEN",
  "tk_from", "tk_branch", "tk_number", "tk_nature", "tk_aliasparameter",
  "tk_output", "tk_anystring", "tk_dollar_ident", "tk_or", "tk_aliasparam",
  "tk_if", "tk_analog", "tk_parameter", "tk_discipline", "tk_char",
  "tk_anytext", "tk_for", "tk_while", "tk_real", "tk_op_shr", "tk_case",
  "tk_potential", "tk_endcase", "tk_inf", "tk_exclude", "tk_ground",
  "tk_endmodule", "tk_begin", "tk_enddiscipline", "tk_domain", "tk_ident",
  "tk_op_shl", "tk_string", "tk_integer", "tk_module", "tk_endattribute",
  "tk_else", "tk_end", "tk_inout", "tk_and", "tk_bitwise_equr",
  "tk_default", "tk_function", "tk_input", "tk_beginattribute",
  "tk_endnature", "tk_endfunction", "tk_flow", "';'", "'='", "'('", "')'",
  "','", "'['", "':'", "']'", "'-'", "'+'", "'@'", "'<'", "'#'", "'_'",
  "'?'", "'~'", "'^'", "'|'", "'&'", "'!'", "'>'", "'*'", "'/'", "'%'",
  "$accept", "R_admsParse", "R_l_admsParse", "R_s_admsParse",
  "R_discipline_member", "R_discipline_name", "R_l_discipline_assignment",
  "R_s_discipline_assignment", "R_discipline_naturename",
  "R_nature_member", "R_l_nature_assignment", "R_s_nature_assignment",
  "R_d_attribute_0", "R_d_attribute", "R_l_attribute", "R_s_attribute",
  "R_d_module", "$@1", "R_modulebody", "R_netlist", "R_l_instance",
  "R_d_terminal", "R_l_terminal_0", "R_l_terminal", "R_s_terminal",
  "R_l_declaration", "R_s_declaration_withattribute",
  "R_d_attribute_global", "R_s_declaration", "R_s_param_declaration",
  "R_d_node", "R_node_type", "R_l_terminalnode", "R_l_node",
  "R_s_terminalnode", "R_s_node", "R_d_branch", "R_l_branchalias",
  "R_s_branchalias", "R_s_branch", "R_d_analogfunction",
  "R_d_analogfunction_proto", "R_d_analogfunction_name",
  "R_l_analogfunction_declaration", "R_s_analogfunction_declaration",
  "R_l_analogfunction_input_variable",
  "R_l_analogfunction_output_variable",
  "R_l_analogfunction_inout_variable",
  "R_l_analogfunction_integer_variable",
  "R_l_analogfunction_real_variable", "R_variable_type",
  "R_d_variable_end", "R_l_parameter", "R_l_variable",
  "R_d_aliasparameter", "R_d_aliasparameter_token", "R_s_parameter",
  "R_s_variable", "R_s_parameter_name", "R_s_variable_name",
  "R_s_parameter_range", "R_l_interval", "R_s_interval", "R_d_interval",
  "R_interval_seg", "R_interval_inf", "R_interval_sup", "R_analog",
  "R_analogcode", "R_analogcode_atomic", "R_analogcode_block",
  "R_analogcode_block_atevent", "R_l_analysis", "R_s_analysis",
  "R_d_block", "$@2", "R_d_block_begin", "R_l_blockitem",
  "R_d_blockvariable", "R_l_blockvariable", "R_s_blockvariable",
  "R_d_contribution", "R_contribution", "R_source", "R_d_while", "R_d_for",
  "R_d_case", "$@3", "R_l_case_item", "R_s_case_item", "R_s_instance",
  "R_instance_module_name", "R_l_instance_parameter",
  "R_s_instance_parameter", "R_s_assignment", "R_s_assignment_name",
  "R_d_conditional", "R_s_expression", "R_l_callfunction_expression",
  "R_l_expression", "R_s_function_expression", "R_expression",
  "R_e_conditional", "R_e_bitwise_equ", "R_e_bitwise_xor",
  "R_e_bitwise_or", "R_e_bitwise_and", "R_e_logical_or", "R_e_logical_and",
  "R_e_comp_equ", "R_e_comp", "R_e_bitwise_shift", "R_e_arithm_add",
  "R_e_arithm_mult", "R_e_unary", "R_e_atomic", YY_NULLPTR
};

static const char *
yysymbol_name (yysymbol_kind_t yysymbol)
{
  return yytname[yysymbol];
}
#endif

#define YYPACT_NINF (-317)

#define yypact_value_is_default(Yyn) \
  ((Yyn) == YYPACT_NINF)

#define YYTABLE_NINF (-24)

#define yytable_value_is_error(Yyn) \
  0

/* YYPACT[STATE-NUM] -- Index in YYTABLE of the portion describing
   STATE-NUM.  */
static const yytype_int16 yypact[] =
{
      18,    12,    28,    75,   119,    95,  -317,  -317,  -317,    58,
    -317,  -317,    69,  -317,    62,  -317,   127,  -317,   111,  -317,
    -317,  -317,   114,   147,   -20,  -317,   169,   178,   169,    19,
    -317,   211,  -317,  -317,  -317,    24,  -317,  -317,  -317,   184,
     193,   202,  -317,  -317,  -317,   194,    83,   208,   212,  -317,
    -317,  -317,   234,   539,   246,  -317,  -317,  -317,  -317,   245,
     248,  -317,   255,  -317,  -317,  -317,   432,   130,   270,   288,
     288,   270,   270,  -317,  -317,  -317,  -317,   294,  -317,    71,
     539,  -317,   580,  -317,  -317,  -317,   296,  -317,  -317,    32,
     300,  -317,   304,   311,  -317,   282,  -317,   270,   234,   314,
     298,    78,   297,   299,   303,   306,   307,    38,  -317,   -12,
     139,   318,  -317,  -317,  -317,   270,  -317,   417,  -317,   270,
     291,  -317,  -317,  -317,   310,   100,  -317,   309,   300,   113,
    -317,   270,   315,  -317,   270,   122,  -317,   134,  -317,  -317,
    -317,   517,  -317,   311,  -317,  -317,  -317,   323,   288,  -317,
     270,   140,  -317,   330,   337,   338,   339,   340,   377,  -317,
     149,  -317,   270,   324,   311,   322,   326,  -317,   138,  -317,
    -317,    37,   369,   103,   369,   369,   347,   348,  -317,   348,
     332,  -317,   354,   367,  -317,   367,   367,  -317,  -317,   351,
     374,  -317,  -317,   373,  -317,   462,   356,   352,  -317,   369,
     369,   403,   113,  -317,   300,  -317,  -317,   369,  -317,  -317,
     288,  -317,   311,  -317,  -317,   296,  -317,   150,  -317,   158,
    -317,   159,  -317,   161,  -317,   166,  -317,   362,   300,  -317,
    -317,   381,   355,  -317,   382,   388,   392,  -317,   379,  -317,
     101,   369,   375,   369,   369,    22,    22,  -317,   195,  -317,
    -317,    23,   376,   366,   372,   433,   404,    65,    52,     3,
     196,   204,  -317,  -317,   393,   318,   397,   395,   402,   217,
     407,   410,  -317,   226,   398,   167,  -317,   168,   185,   369,
     422,  -317,  -317,  -317,   369,  -317,   405,   412,  -317,  -317,
      33,  -317,  -317,  -317,   434,  -317,   438,  -317,   440,  -317,
     443,  -317,   447,  -317,  -317,   270,   451,   229,  -317,  -317,
     431,  -317,   435,  -317,   369,   369,   369,   437,  -317,  -317,
    -317,  -317,  -317,   441,   369,   369,   369,   421,   369,   369,
     369,   369,   369,   442,   452,   128,   173,   369,   369,   369,
     369,   369,   369,   369,   517,   369,   517,  -317,  -317,   466,
    -317,  -317,   494,  -317,   500,  -317,   367,  -317,  -317,  -317,
    -317,   517,  -317,   454,   507,   198,   198,  -317,    33,  -317,
    -317,  -317,  -317,  -317,  -317,   463,   465,   482,   355,   382,
     382,   231,  -317,  -317,   233,   458,  -317,  -317,  -317,   376,
      96,   369,   366,   372,   433,   404,    65,   369,   369,   369,
       3,   369,     3,   196,   196,   204,   204,  -317,  -317,  -317,
     480,   469,  -317,   256,   468,  -317,   239,  -317,   472,  -317,
     477,   369,   467,   400,   400,  -317,  -317,  -317,  -317,  -317,
    -317,   369,   473,  -317,  -317,   431,  -317,   369,  -317,  -317,
     369,   376,    52,    52,     3,     3,   517,   103,   488,    39,
    -317,   115,  -317,   478,   494,   526,  -317,  -317,  -317,   265,
     129,  -317,   437,   129,   479,   288,  -317,    -8,  -317,   487,
     517,  -317,  -317,  -317,   517,  -317,  -317,   476,  -317,  -317,
    -317,   329,   329,  -317,   241,   517,  -317,  -317,  -317,  -317,
     331,   183,  -317,   188,   491,  -317,  -317,  -317,  -317,  -317,
    -317,  -317
};

/* YYDEFACT[STATE-NUM] -- Default reduction number in state STATE-NUM.
   Performed when YYTABLE does not specify something else to do.  Zero
   means the default is an error.  */
static const yytype_uint8 yydefact[] =
{
      23,     0,     0,     0,     0,     2,     3,     6,     7,     0,
      24,     5,     0,     9,     0,    26,     0,    27,     0,    28,
       1,     4,     0,     0,     0,    17,     0,     0,     0,     0,
      10,     0,    25,    29,    31,     0,    16,    18,    15,     0,
       0,     0,     8,    11,    30,     0,     0,     0,     0,    12,
      14,    13,    45,    33,     0,    19,    21,    22,    49,     0,
      46,    47,     0,   113,    68,   114,    23,     0,    23,     0,
     190,    23,    23,    69,    67,    61,    54,     0,    35,    38,
      34,    50,     0,    52,    57,    55,     0,    56,    60,     0,
       0,    59,     0,    37,    42,     0,    20,    23,     0,     0,
       0,     0,     0,     0,     0,     0,   197,     0,   152,     0,
       0,    24,   139,   140,   141,    23,   153,    23,   143,    23,
       0,   146,   148,   147,     0,     0,   145,   118,     0,     0,
     108,    23,     0,   105,    23,     0,    72,     0,   106,   104,
      32,    23,   190,    39,    43,    36,    51,     0,     0,    53,
      23,     0,    70,     0,     0,     0,     0,     0,    23,    87,
       0,   110,    23,     0,    40,     0,     0,    48,     0,    76,
     151,     0,     0,     0,     0,     0,     0,     0,    86,     0,
       0,   156,     0,     0,   166,     0,     0,   142,   197,     0,
       0,   154,   161,     0,   167,    23,     0,     0,   144,     0,
       0,     0,     0,   107,     0,    63,   115,     0,    75,    65,
       0,    66,    41,    74,    64,     0,    96,     0,   102,     0,
     100,     0,    98,     0,    94,     0,    88,     0,     0,    58,
     116,     0,     0,    44,     0,     0,   245,   248,   250,   247,
     249,     0,     0,     0,     0,     0,     0,   201,     0,   200,
     206,   207,   209,   212,   214,   216,   218,   220,   222,   225,
     230,   233,   236,   240,     0,     0,     0,     0,     0,     0,
       0,     0,    83,     0,   174,     0,   172,     0,     0,     0,
     164,   163,   168,   176,     0,   194,     0,     0,    62,   109,
     120,    73,    71,    90,     0,    93,     0,    92,     0,    91,
       0,    89,     0,    82,   111,    23,     0,     0,   191,    79,
      81,    77,     0,   246,     0,     0,     0,     0,   150,   242,
     241,   244,   243,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,     0,     0,     0,     0,     0,     0,
       0,     0,     0,     0,    23,     0,    23,   182,   179,     0,
      85,    84,     0,   157,     0,   170,     0,   171,   169,   195,
     162,    23,   177,     0,     0,     0,     0,   117,   121,   122,
      97,   103,   101,    99,    95,     0,     0,     0,     0,     0,
       0,     0,   203,   205,     0,     0,   254,   149,   202,   210,
       0,     0,   213,   215,   217,   219,   221,     0,     0,     0,
     226,     0,   228,   231,   232,   235,   234,   237,   238,   239,
     198,     0,   180,     0,     0,   160,     0,   158,     0,   173,
      23,     0,     0,     0,     0,   124,   131,   125,   126,   123,
     112,     0,     0,   192,    78,    80,   252,     0,   253,   251,
       0,   211,   223,   224,   227,   229,    23,     0,    23,     0,
     184,     0,   178,     0,     0,     0,   165,   196,   119,     0,
       0,   134,   200,     0,     0,     0,   204,   208,   199,     0,
      23,   188,   183,   185,    23,   155,   159,     0,   135,   133,
     132,     0,     0,   193,     0,    23,   187,   186,   175,   137,
       0,     0,   136,     0,     0,   181,   138,   127,   128,   129,
     130,   189
};

/* YYPGOTO[NTERM-NUM].  */
static const yytype_int16 yypgoto[] =
{
    -317,  -317,  -317,   540,  -317,  -317,  -317,   520,   525,  -317,
    -317,   532,    10,   -53,  -317,   541,  -317,  -317,  -317,   483,
     -75,  -317,  -317,  -317,   459,  -317,   484,  -317,   485,  -317,
    -317,  -317,  -317,   -68,   343,   350,  -317,   182,   187,  -317,
    -317,  -317,    51,  -317,   413,  -317,  -317,  -317,  -317,  -317,
     503,  -139,   444,  -317,  -317,  -317,   370,   349,  -317,   -81,
    -317,  -317,   210,   214,   120,   160,   108,   513,  -115,  -317,
     424,  -317,  -317,   143,   486,  -317,  -317,   237,  -317,   117,
     238,  -317,  -317,  -317,  -317,  -317,  -317,  -317,  -317,   151,
     -63,  -317,  -317,   221,  -165,  -106,  -317,  -168,  -317,    -3,
     170,  -188,  -317,  -309,  -314,   275,   276,   274,   277,   278,
     -91,  -316,   -17,   -11,  -220,    98
};

/* YYDEFGOTO[NTERM-NUM].  */
static const yytype_int16 yydefgoto[] =
{
       0,     4,     5,     6,     7,    14,    29,    30,    39,     8,
      24,    25,   110,    10,    18,    19,    11,    45,    77,    78,
      79,    53,    59,    60,    61,    80,    81,    82,    83,    84,
      85,    86,   151,   137,   152,   136,    87,   310,   311,   100,
      88,    89,   180,   158,   159,   225,   217,   223,   221,   219,
      90,   205,   129,   160,    91,    92,   130,   161,   131,   132,
     367,   368,   369,   425,   481,   460,   491,    93,   112,   113,
     114,   115,   416,   417,   116,   361,   117,   195,   187,   275,
     276,   118,   119,   120,   121,   122,   123,   413,   449,   450,
      94,    95,   307,   308,   124,   125,   126,   461,   248,   451,
     382,   249,   250,   251,   252,   253,   254,   255,   256,   257,
     258,   259,   260,   261,   262,   263
};

/* YYTABLE[YYPACT[STATE-NUM]] -- What to do in state STATE-NUM.  If
   positive, shift that token.  If negative, reduce the rule whose
   number is the opposite.  If YYTABLE_NINF, syntax error.  */
static const yytype_int16 yytable[] =
{
      76,   135,   194,   247,   264,   189,   267,   268,   266,   162,
       9,   389,   286,   111,    23,     9,   144,   390,   164,   400,
     402,   229,   181,   319,   320,     1,   337,    76,   236,    36,
      46,   285,   237,   238,    47,     2,   325,   365,   338,   290,
     239,   153,   182,   236,    26,   236,    12,   237,   238,   237,
     238,    42,    27,   317,   154,   239,   240,   239,    48,   327,
     177,   366,    13,   288,   111,   472,     3,   325,   212,   155,
      28,   240,   178,   240,   156,   179,   241,   441,   133,   157,
     282,   138,   139,   444,   448,   445,   141,    26,   111,   326,
     327,   241,   242,   241,    15,    27,    22,   243,   244,   243,
     244,   144,     1,    23,   245,   142,   245,   166,   246,    16,
     246,   359,     2,    28,    17,   335,   362,    54,   333,    20,
     265,   407,   408,   409,   336,   190,   383,   383,   385,   196,
     170,   467,   171,   -23,   236,    55,   334,   188,   237,   238,
     325,   206,   111,     3,   208,    16,   239,   162,    34,   144,
      32,     3,    68,   199,   440,   315,   388,   200,   316,   189,
     213,   183,   240,   327,   127,   203,    71,    72,   190,   204,
     184,   437,   230,   474,   209,   185,   186,   411,   210,   236,
      31,   399,   241,   237,   238,   479,   211,   480,   243,   244,
     210,   239,   214,   234,   235,   245,   215,   426,   428,   246,
      35,   203,   293,    38,   236,   228,   294,   240,   237,   238,
     295,   297,    40,   299,   296,   298,   239,   300,   301,   355,
     357,    44,   302,   356,   356,   383,   401,   241,   270,   410,
     271,   412,   240,   243,   244,   462,    49,   358,   497,   319,
     245,   356,   498,   499,   246,    50,   194,   500,    52,   383,
     323,   324,   423,   457,    51,   424,   339,   340,   243,   244,
      56,   383,   236,   464,    57,   245,   237,   238,    58,   246,
     320,   236,   348,   349,   239,   237,   238,   341,   342,   343,
     352,   353,   469,   239,   377,   378,   436,   437,   438,   437,
     240,   111,   478,   111,   453,   454,   494,   210,    96,   240,
      97,   448,   277,   278,    98,   282,   442,   443,   111,    99,
     241,   381,   384,   492,   492,   375,   243,   244,     3,   241,
     403,   404,   134,   245,   140,   243,   244,   246,   405,   406,
     150,   468,   245,   471,   127,   236,   246,   236,   163,   237,
     238,   237,   238,   321,   322,   142,   165,   239,   168,   239,
     169,   172,   188,   173,   197,   486,   489,   174,   496,   487,
     175,   176,   198,   240,   216,   240,   201,   111,   207,   107,
     495,   218,   220,   222,   224,   236,   232,   231,   233,   237,
     238,   269,   178,   241,   272,   241,   153,   239,   273,   243,
     490,   243,   244,   111,   265,   111,   245,   484,   245,   154,
     246,   274,   246,   240,   279,   184,   236,   280,   283,   287,
     237,   238,   303,   284,   155,   305,   309,   111,   239,   156,
     306,   111,   312,   241,   157,     3,   313,   318,   101,   243,
     244,   102,   111,   314,   240,   329,   245,   103,   104,   109,
     246,   105,   330,   101,   328,   331,   102,   332,   344,   345,
     346,   106,   103,   104,   241,   354,   105,   347,   192,   350,
     459,   244,   351,   360,   363,     3,   106,   245,   370,   108,
     364,   246,   371,   101,   372,   193,   102,   373,   107,   109,
       3,   374,   103,   104,   108,   376,   105,   379,   101,   391,
     380,   102,   386,   387,   109,   397,   106,   103,   104,   101,
     414,   105,   102,   281,   415,   398,   418,   421,   103,   104,
       3,   106,   105,   422,   108,   430,   432,   439,   456,   431,
     446,   447,   106,   452,   109,     3,   458,   465,   101,   108,
     455,   102,   477,   475,   483,   488,     3,   103,   104,   109,
     108,   105,   485,   501,    62,    21,   470,    63,    64,    43,
     109,   106,    65,    41,    66,    67,    37,   167,   292,    33,
     291,    68,   435,   145,   146,     3,   434,   149,    69,   108,
     128,   226,   202,    70,   289,    71,    72,   304,   429,   109,
     427,    73,   227,   482,   463,    62,    74,     3,    63,    64,
     493,    75,   143,    65,   419,   147,    67,   476,   420,   433,
     473,   191,    68,   392,   394,   393,     0,   466,   395,    69,
     396,     0,     0,     0,   148,     0,    71,    72,     0,     0,
       0,     0,    73,     0,     0,     0,     0,    74,     0,     0,
       0,     0,    75
};

static const yytype_int16 yycheck[] =
{
      53,    69,   117,   171,   172,   111,   174,   175,   173,    90,
       0,   325,   200,    66,    34,     5,    79,   326,    93,   335,
     336,   160,    34,   243,   244,     7,    23,    80,     6,    49,
       6,   199,    10,    11,    10,    17,    44,     4,    35,   207,
      18,     9,    54,     6,    25,     6,    34,    10,    11,    10,
      11,    32,    33,   241,    22,    18,    34,    18,    34,    67,
      22,    28,    34,   202,   117,    26,    48,    44,   143,    37,
      51,    34,    34,    34,    42,    37,    54,   391,    68,    47,
     195,    71,    72,   399,    45,   401,    15,    25,   141,    66,
      67,    54,    55,    54,    19,    33,    38,    60,    61,    60,
      61,   164,     7,    34,    67,    34,    67,    97,    71,    34,
      71,   279,    17,    51,    39,    63,   284,    34,    53,     0,
     173,   341,   342,   343,    72,   115,   314,   315,   316,   119,
      52,   440,    54,    38,     6,    52,    71,    34,    10,    11,
      44,   131,   195,    48,   134,    34,    18,   228,    34,   212,
      39,    48,    22,    53,    58,    54,   324,    57,    57,   265,
     150,    22,    34,    67,    34,    52,    36,    37,   158,    56,
      31,    56,   162,    58,    52,    36,    37,   345,    56,     6,
      53,    53,    54,    10,    11,    56,    52,    58,    60,    61,
      56,    18,    52,    55,    56,    67,    56,   365,   366,    71,
      53,    52,    52,    34,     6,    56,    56,    34,    10,    11,
      52,    52,    34,    52,    56,    56,    18,    56,    52,    52,
      52,    10,    56,    56,    56,   413,    53,    54,   177,   344,
     179,   346,    34,    60,    61,   423,    52,    52,    55,   459,
      67,    56,    59,    55,    71,    52,   361,    59,    54,   437,
      55,    56,    54,   421,    52,    57,    60,    61,    60,    61,
      52,   449,     6,   431,    52,    67,    10,    11,    34,    71,
     490,     6,    55,    56,    18,    10,    11,    73,    74,    75,
      54,    55,   447,    18,    55,    56,    55,    56,    55,    56,
      34,   344,    27,   346,    55,    56,    55,    56,    52,    34,
      55,    45,   185,   186,    56,   420,   397,   398,   361,    54,
      54,   314,   315,   481,   482,   305,    60,    61,    48,    54,
     337,   338,    34,    67,    30,    60,    61,    71,   339,   340,
      34,   446,    67,   448,    34,     6,    71,     6,    34,    10,
      11,    10,    11,   245,   246,    34,    64,    18,    34,    18,
      52,    54,    34,    54,    63,   470,    27,    54,    27,   474,
      54,    54,    52,    34,    34,    34,    57,   420,    53,    46,
     485,    34,    34,    34,    34,     6,    54,    53,    52,    10,
      11,    34,    34,    54,    52,    54,     9,    18,    34,    60,
      61,    60,    61,   446,   447,   448,    67,   465,    67,    22,
      71,    34,    71,    34,    53,    31,     6,    34,    52,     6,
      10,    11,    50,    61,    37,    34,    34,   470,    18,    42,
      65,   474,    34,    54,    47,    48,    34,    52,    11,    60,
      61,    14,   485,    54,    34,    69,    67,    20,    21,    62,
      71,    24,    70,    11,    68,    12,    14,    43,    55,    52,
      55,    34,    20,    21,    54,    57,    24,    55,    41,    52,
      60,    61,    52,    41,    59,    48,    34,    67,    34,    52,
      58,    71,    34,    11,    34,    58,    14,    34,    46,    62,
      48,    34,    20,    21,    52,    34,    24,    56,    11,    68,
      55,    14,    55,    52,    62,    53,    34,    20,    21,    11,
      34,    24,    14,    41,    10,    53,     6,    53,    20,    21,
      48,    34,    24,     6,    52,    52,    34,    59,    41,    54,
      40,    52,    34,    55,    62,    48,    59,    54,    11,    52,
      58,    14,     6,    55,    55,    59,    48,    20,    21,    62,
      52,    24,    55,    52,     5,     5,    58,     8,     9,    29,
      62,    34,    13,    28,    15,    16,    24,    98,   215,    18,
     210,    22,   380,    80,    80,    48,   379,    82,    29,    52,
      67,   158,   128,    34,   204,    36,    37,   228,   368,    62,
     366,    42,   158,   463,   424,     5,    47,    48,     8,     9,
     482,    52,    79,    13,   356,    15,    16,   454,   361,   378,
     449,   115,    22,   328,   330,   329,    -1,   437,   331,    29,
     332,    -1,    -1,    -1,    34,    -1,    36,    37,    -1,    -1,
      -1,    -1,    42,    -1,    -1,    -1,    -1,    47,    -1,    -1,
      -1,    -1,    52
};

/* YYSTOS[STATE-NUM] -- The symbol kind of the accessing symbol of
   state STATE-NUM.  */
static const yytype_uint8 yystos[] =
{
       0,     7,    17,    48,    77,    78,    79,    80,    85,    88,
      89,    92,    34,    34,    81,    19,    34,    39,    90,    91,
       0,    79,    38,    34,    86,    87,    25,    33,    51,    82,
      83,    53,    39,    91,    34,    53,    49,    87,    34,    84,
      34,    84,    32,    83,    10,    93,     6,    10,    34,    52,
      52,    52,    54,    97,    34,    52,    52,    52,    34,    98,
      99,   100,     5,     8,     9,    13,    15,    16,    22,    29,
      34,    36,    37,    42,    47,    52,    89,    94,    95,    96,
     101,   102,   103,   104,   105,   106,   107,   112,   116,   117,
     126,   130,   131,   143,   166,   167,    52,    55,    56,    54,
     115,    11,    14,    20,    21,    24,    34,    46,    52,    62,
      88,    89,   144,   145,   146,   147,   150,   152,   157,   158,
     159,   160,   161,   162,   170,   171,   172,    34,   126,   128,
     132,   134,   135,    88,    34,   109,   111,   109,    88,    88,
      30,    15,    34,   143,   166,    95,   102,    15,    34,   104,
      34,   108,   110,     9,    22,    37,    42,    47,   119,   120,
     129,   133,   135,    34,    96,    64,    88,   100,    34,    52,
      52,    54,    54,    54,    54,    54,    54,    22,    34,    37,
     118,    34,    54,    22,    31,    36,    37,   154,    34,   171,
      88,   150,    41,    58,   144,   153,    88,    63,    52,    53,
      57,    57,   128,    52,    56,   127,    88,    53,    88,    52,
      56,    52,    96,    88,    52,    56,    34,   122,    34,   125,
      34,   124,    34,   123,    34,   121,   120,   146,    56,   127,
      88,    53,    54,    52,    55,    56,     6,    10,    11,    18,
      34,    54,    55,    60,    61,    67,    71,   173,   174,   177,
     178,   179,   180,   181,   182,   183,   184,   185,   186,   187,
     188,   189,   190,   191,   173,    89,   170,   173,   173,    34,
     118,   118,    52,    34,    34,   155,   156,   155,   155,    53,
      34,    41,   144,    52,    61,   173,   177,     6,   127,   132,
     173,   111,   110,    52,    56,    52,    56,    52,    56,    52,
      56,    52,    56,    50,   133,    34,    65,   168,   169,    34,
     113,   114,    34,    34,    54,    54,    57,   177,    52,   190,
     190,   191,   191,    55,    56,    44,    66,    67,    68,    69,
      70,    12,    43,    53,    71,    63,    72,    23,    35,    60,
      61,    73,    74,    75,    55,    52,    55,    55,    55,    56,
      52,    52,    54,    55,    57,    52,    56,    52,    52,   173,
      41,   151,   173,    59,    58,     4,    28,   136,   137,   138,
      34,    34,    34,    34,    34,    88,    34,    55,    56,    56,
      55,   175,   176,   177,   175,   177,    55,    52,   173,   180,
     179,    68,   181,   182,   183,   184,   185,    53,    53,    53,
     187,    53,   187,   188,   188,   189,   189,   190,   190,   190,
     144,   173,   144,   163,    34,    10,   148,   149,     6,   156,
     153,    53,     6,    54,    57,   139,   173,   139,   173,   138,
      52,    54,    34,   169,   114,   113,    55,    56,    55,    59,
      58,   180,   186,   186,   187,   187,    40,    52,    45,   164,
     165,   175,    55,    55,    56,    58,    41,   173,    59,    60,
     141,   173,   177,   141,   173,    54,   176,   179,   144,   170,
      58,   144,    26,   165,    58,    55,   149,     6,    27,    56,
      58,   140,   140,    55,   109,    55,   144,   144,    59,    27,
      61,   142,   173,   142,    55,   144,    27,    55,    59,    55,
      59,    52
};

/* YYR1[RULE-NUM] -- Symbol kind of the left-hand side of rule RULE-NUM.  */
static const yytype_uint8 yyr1[] =
{
       0,    76,    77,    78,    78,    79,    79,    79,    80,    81,
      82,    82,    83,    83,    83,    84,    85,    86,    86,    87,
      87,    87,    87,    88,    88,    89,    89,    89,    90,    90,
      91,    93,    92,    94,    94,    94,    94,    95,    95,    95,
      95,    95,    96,    96,    97,    98,    98,    99,    99,   100,
     101,   101,   102,   102,   103,   104,   104,   104,   104,   104,
     104,   104,   105,   105,   106,   106,   106,   107,   107,   107,
     108,   108,   109,   109,   110,   111,   112,   113,   113,   114,
     115,   115,   116,   117,   117,   117,   118,   119,   119,   120,
     120,   120,   120,   120,   121,   121,   122,   122,   123,   123,
     124,   124,   125,   125,   126,   126,   126,   127,   128,   128,
     129,   129,   130,   131,   131,   132,   133,   134,   135,   135,
     136,   136,   137,   137,   138,   138,   138,   139,   139,   139,
     139,   139,   140,   140,   141,   141,   142,   142,   142,   143,
     144,   144,   145,   145,   145,   145,   145,   145,   145,   145,
     145,   145,   145,   146,   146,   147,   147,   147,   148,   148,
     149,   150,   150,   150,   151,   150,   152,   153,   153,   154,
     154,   154,   155,   155,   156,   156,   157,   158,   159,   159,
     160,   161,   163,   162,   164,   164,   165,   165,   165,   166,
     167,   168,   168,   169,   170,   170,   170,   171,   172,   172,
     173,   174,   174,   175,   175,   176,   177,   178,   178,   179,
     179,   179,   180,   180,   181,   181,   182,   182,   183,   183,
     184,   184,   185,   185,   185,   186,   186,   186,   186,   186,
     187,   187,   187,   188,   188,   188,   189,   189,   189,   189,
     190,   190,   190,   190,   190,   191,   191,   191,   191,   191,
     191,   191,   191,   191,   191
};

/* YYR2[RULE-NUM] -- Number of symbols on the right-hand side of rule RULE-NUM.  */
static const yytype_int8 yyr2[] =
{
       0,     2,     1,     1,     2,     1,     1,     1,     4,     1,
       1,     2,     3,     3,     3,     1,     4,     1,     2,     4,
       5,     4,     4,     0,     1,     3,     2,     2,     1,     2,
       3,     0,     7,     0,     1,     1,     2,     1,     1,     2,
       2,     3,     1,     2,     5,     0,     1,     1,     3,     1,
       1,     2,     1,     2,     1,     1,     1,     1,     3,     1,
       1,     1,     4,     3,     3,     3,     3,     1,     1,     1,
       1,     3,     1,     3,     2,     2,     3,     1,     3,     1,
       6,     4,     4,     4,     5,     5,     1,     1,     2,     3,
       3,     3,     3,     3,     1,     3,     1,     3,     1,     3,
       1,     3,     1,     3,     2,     2,     2,     1,     1,     3,
       1,     3,     6,     1,     1,     2,     2,     4,     1,     6,
       0,     1,     1,     2,     2,     2,     2,     5,     5,     5,
       5,     1,     1,     1,     1,     2,     1,     1,     2,     2,
       1,     1,     2,     1,     2,     1,     1,     1,     1,     5,
       4,     2,     1,     1,     2,     7,     2,     4,     1,     3,
       1,     2,     4,     3,     0,     6,     2,     1,     2,     3,
       3,     3,     1,     3,     1,     6,     3,     4,     6,     4,
       5,     9,     0,     7,     1,     2,     3,     3,     2,    10,
       1,     1,     3,     5,     3,     4,     6,     1,     5,     7,
       1,     1,     3,     1,     3,     1,     1,     1,     5,     1,
       3,     4,     1,     3,     1,     3,     1,     3,     1,     3,
       1,     3,     1,     4,     4,     1,     3,     4,     3,     4,
       1,     3,     3,     1,     3,     3,     1,     3,     3,     3,
       1,     2,     2,     2,     2,     1,     2,     1,     1,     1,
       1,     4,     4,     4,     3
};


enum { YYENOMEM = -2 };

#define yyerrok         (yyerrstatus = 0)
#define yyclearin       (yychar = YYEMPTY)

#define YYACCEPT        goto yyacceptlab
#define YYABORT         goto yyabortlab
#define YYERROR         goto yyerrorlab
#define YYNOMEM         goto yyexhaustedlab


#define YYRECOVERING()  (!!yyerrstatus)

#define YYBACKUP(Token, Value)                                    \
  do                                                              \
    if (yychar == YYEMPTY)                                        \
      {                                                           \
        yychar = (Token);                                         \
        yylval = (Value);                                         \
        YYPOPSTACK (yylen);                                       \
        yystate = *yyssp;                                         \
        goto yybackup;                                            \
      }                                                           \
    else                                                          \
      {                                                           \
        yyerror (YY_("syntax error: cannot back up")); \
        YYERROR;                                                  \
      }                                                           \
  while (0)

/* Backward compatibility with an undocumented macro.
   Use YYerror or YYUNDEF. */
#define YYERRCODE YYUNDEF


/* Enable debugging if requested.  */
#if YYDEBUG

# ifndef YYFPRINTF
#  include <stdio.h> /* INFRINGES ON USER NAME SPACE */
#  define YYFPRINTF fprintf
# endif

# define YYDPRINTF(Args)                        \
do {                                            \
  if (yydebug)                                  \
    YYFPRINTF Args;                             \
} while (0)




# define YY_SYMBOL_PRINT(Title, Kind, Value, Location)                    \
do {                                                                      \
  if (yydebug)                                                            \
    {                                                                     \
      YYFPRINTF (stderr, "%s ", Title);                                   \
      yy_symbol_print (stderr,                                            \
                  Kind, Value); \
      YYFPRINTF (stderr, "\n");                                           \
    }                                                                     \
} while (0)


/*-----------------------------------.
| Print this symbol's value on YYO.  |
`-----------------------------------*/

static void
yy_symbol_value_print (FILE *yyo,
                       yysymbol_kind_t yykind, YYSTYPE const * const yyvaluep)
{
  FILE *yyoutput = yyo;
  YY_USE (yyoutput);
  if (!yyvaluep)
    return;
  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  YY_USE (yykind);
  YY_IGNORE_MAYBE_UNINITIALIZED_END
}


/*---------------------------.
| Print this symbol on YYO.  |
`---------------------------*/

static void
yy_symbol_print (FILE *yyo,
                 yysymbol_kind_t yykind, YYSTYPE const * const yyvaluep)
{
  YYFPRINTF (yyo, "%s %s (",
             yykind < YYNTOKENS ? "token" : "nterm", yysymbol_name (yykind));

  yy_symbol_value_print (yyo, yykind, yyvaluep);
  YYFPRINTF (yyo, ")");
}

/*------------------------------------------------------------------.
| yy_stack_print -- Print the state stack from its BOTTOM up to its |
| TOP (included).                                                   |
`------------------------------------------------------------------*/

static void
yy_stack_print (yy_state_t *yybottom, yy_state_t *yytop)
{
  YYFPRINTF (stderr, "Stack now");
  for (; yybottom <= yytop; yybottom++)
    {
      int yybot = *yybottom;
      YYFPRINTF (stderr, " %d", yybot);
    }
  YYFPRINTF (stderr, "\n");
}

# define YY_STACK_PRINT(Bottom, Top)                            \
do {                                                            \
  if (yydebug)                                                  \
    yy_stack_print ((Bottom), (Top));                           \
} while (0)


/*------------------------------------------------.
| Report that the YYRULE is going to be reduced.  |
`------------------------------------------------*/

static void
yy_reduce_print (yy_state_t *yyssp, YYSTYPE *yyvsp,
                 int yyrule)
{
  int yylno = yyrline[yyrule];
  int yynrhs = yyr2[yyrule];
  int yyi;
  YYFPRINTF (stderr, "Reducing stack by rule %d (line %d):\n",
             yyrule - 1, yylno);
  /* The symbols being reduced.  */
  for (yyi = 0; yyi < yynrhs; yyi++)
    {
      YYFPRINTF (stderr, "   $%d = ", yyi + 1);
      yy_symbol_print (stderr,
                       YY_ACCESSING_SYMBOL (+yyssp[yyi + 1 - yynrhs]),
                       &yyvsp[(yyi + 1) - (yynrhs)]);
      YYFPRINTF (stderr, "\n");
    }
}

# define YY_REDUCE_PRINT(Rule)          \
do {                                    \
  if (yydebug)                          \
    yy_reduce_print (yyssp, yyvsp, Rule); \
} while (0)

/* Nonzero means print parse trace.  It is left uninitialized so that
   multiple parsers can coexist.  */
int yydebug;
#else /* !YYDEBUG */
# define YYDPRINTF(Args) ((void) 0)
# define YY_SYMBOL_PRINT(Title, Kind, Value, Location)
# define YY_STACK_PRINT(Bottom, Top)
# define YY_REDUCE_PRINT(Rule)
#endif /* !YYDEBUG */


/* YYINITDEPTH -- initial size of the parser's stacks.  */
#ifndef YYINITDEPTH
# define YYINITDEPTH 200
#endif

/* YYMAXDEPTH -- maximum size the stacks can grow to (effective only
   if the built-in stack extension method is used).

   Do not make this value too large; the results are undefined if
   YYSTACK_ALLOC_MAXIMUM < YYSTACK_BYTES (YYMAXDEPTH)
   evaluated with infinite-precision integer arithmetic.  */

#ifndef YYMAXDEPTH
# define YYMAXDEPTH 10000
#endif






/*-----------------------------------------------.
| Release the memory associated to this symbol.  |
`-----------------------------------------------*/

static void
yydestruct (const char *yymsg,
            yysymbol_kind_t yykind, YYSTYPE *yyvaluep)
{
  YY_USE (yyvaluep);
  if (!yymsg)
    yymsg = "Deleting";
  YY_SYMBOL_PRINT (yymsg, yykind, yyvaluep, yylocationp);

  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  YY_USE (yykind);
  YY_IGNORE_MAYBE_UNINITIALIZED_END
}


/* Lookahead token kind.  */
int yychar;

/* The semantic value of the lookahead symbol.  */
YYSTYPE yylval;
/* Number of syntax errors so far.  */
int yynerrs;




/*----------.
| yyparse.  |
`----------*/

int
yyparse (void)
{
    yy_state_fast_t yystate = 0;
    /* Number of tokens to shift before error messages enabled.  */
    int yyerrstatus = 0;

    /* Refer to the stacks through separate pointers, to allow yyoverflow
       to reallocate them elsewhere.  */

    /* Their size.  */
    YYPTRDIFF_T yystacksize = YYINITDEPTH;

    /* The state stack: array, bottom, top.  */
    yy_state_t yyssa[YYINITDEPTH];
    yy_state_t *yyss = yyssa;
    yy_state_t *yyssp = yyss;

    /* The semantic value stack: array, bottom, top.  */
    YYSTYPE yyvsa[YYINITDEPTH];
    YYSTYPE *yyvs = yyvsa;
    YYSTYPE *yyvsp = yyvs;

  int yyn;
  /* The return value of yyparse.  */
  int yyresult;
  /* Lookahead symbol kind.  */
  yysymbol_kind_t yytoken = YYSYMBOL_YYEMPTY;
  /* The variables used to return semantic value and location from the
     action routines.  */
  YYSTYPE yyval;



#define YYPOPSTACK(N)   (yyvsp -= (N), yyssp -= (N))

  /* The number of symbols on the RHS of the reduced rule.
     Keep to zero when no symbol should be popped.  */
  int yylen = 0;

  YYDPRINTF ((stderr, "Starting parse\n"));

  yychar = YYEMPTY; /* Cause a token to be read.  */

  goto yysetstate;


/*------------------------------------------------------------.
| yynewstate -- push a new state, which is found in yystate.  |
`------------------------------------------------------------*/
yynewstate:
  /* In all cases, when you get here, the value and location stacks
     have just been pushed.  So pushing a state here evens the stacks.  */
  yyssp++;


/*--------------------------------------------------------------------.
| yysetstate -- set current state (the top of the stack) to yystate.  |
`--------------------------------------------------------------------*/
yysetstate:
  YYDPRINTF ((stderr, "Entering state %d\n", yystate));
  YY_ASSERT (0 <= yystate && yystate < YYNSTATES);
  YY_IGNORE_USELESS_CAST_BEGIN
  *yyssp = YY_CAST (yy_state_t, yystate);
  YY_IGNORE_USELESS_CAST_END
  YY_STACK_PRINT (yyss, yyssp);

  if (yyss + yystacksize - 1 <= yyssp)
#if !defined yyoverflow && !defined YYSTACK_RELOCATE
    YYNOMEM;
#else
    {
      /* Get the current used size of the three stacks, in elements.  */
      YYPTRDIFF_T yysize = yyssp - yyss + 1;

# if defined yyoverflow
      {
        /* Give user a chance to reallocate the stack.  Use copies of
           these so that the &'s don't force the real ones into
           memory.  */
        yy_state_t *yyss1 = yyss;
        YYSTYPE *yyvs1 = yyvs;

        /* Each stack pointer address is followed by the size of the
           data in use in that stack, in bytes.  This used to be a
           conditional around just the two extra args, but that might
           be undefined if yyoverflow is a macro.  */
        yyoverflow (YY_("memory exhausted"),
                    &yyss1, yysize * YYSIZEOF (*yyssp),
                    &yyvs1, yysize * YYSIZEOF (*yyvsp),
                    &yystacksize);
        yyss = yyss1;
        yyvs = yyvs1;
      }
# else /* defined YYSTACK_RELOCATE */
      /* Extend the stack our own way.  */
      if (YYMAXDEPTH <= yystacksize)
        YYNOMEM;
      yystacksize *= 2;
      if (YYMAXDEPTH < yystacksize)
        yystacksize = YYMAXDEPTH;

      {
        yy_state_t *yyss1 = yyss;
        union yyalloc *yyptr =
          YY_CAST (union yyalloc *,
                   YYSTACK_ALLOC (YY_CAST (YYSIZE_T, YYSTACK_BYTES (yystacksize))));
        if (! yyptr)
          YYNOMEM;
        YYSTACK_RELOCATE (yyss_alloc, yyss);
        YYSTACK_RELOCATE (yyvs_alloc, yyvs);
#  undef YYSTACK_RELOCATE
        if (yyss1 != yyssa)
          YYSTACK_FREE (yyss1);
      }
# endif

      yyssp = yyss + yysize - 1;
      yyvsp = yyvs + yysize - 1;

      YY_IGNORE_USELESS_CAST_BEGIN
      YYDPRINTF ((stderr, "Stack size increased to %ld\n",
                  YY_CAST (long, yystacksize)));
      YY_IGNORE_USELESS_CAST_END

      if (yyss + yystacksize - 1 <= yyssp)
        YYABORT;
    }
#endif /* !defined yyoverflow && !defined YYSTACK_RELOCATE */


  if (yystate == YYFINAL)
    YYACCEPT;

  goto yybackup;


/*-----------.
| yybackup.  |
`-----------*/
yybackup:
  /* Do appropriate processing given the current state.  Read a
     lookahead token if we need one and don't already have one.  */

  /* First try to decide what to do without reference to lookahead token.  */
  yyn = yypact[yystate];
  if (yypact_value_is_default (yyn))
    goto yydefault;

  /* Not known => get a lookahead token if don't already have one.  */

  /* YYCHAR is either empty, or end-of-input, or a valid lookahead.  */
  if (yychar == YYEMPTY)
    {
      YYDPRINTF ((stderr, "Reading a token\n"));
      yychar = yylex ();
    }

  if (yychar <= YYEOF)
    {
      yychar = YYEOF;
      yytoken = YYSYMBOL_YYEOF;
      YYDPRINTF ((stderr, "Now at end of input.\n"));
    }
  else if (yychar == YYerror)
    {
      /* The scanner already issued an error message, process directly
         to error recovery.  But do not keep the error token as
         lookahead, it is too special and may lead us to an endless
         loop in error recovery. */
      yychar = YYUNDEF;
      yytoken = YYSYMBOL_YYerror;
      goto yyerrlab1;
    }
  else
    {
      yytoken = YYTRANSLATE (yychar);
      YY_SYMBOL_PRINT ("Next token is", yytoken, &yylval, &yylloc);
    }

  /* If the proper action on seeing token YYTOKEN is to reduce or to
     detect an error, take that action.  */
  yyn += yytoken;
  if (yyn < 0 || YYLAST < yyn || yycheck[yyn] != yytoken)
    goto yydefault;
  yyn = yytable[yyn];
  if (yyn <= 0)
    {
      if (yytable_value_is_error (yyn))
        goto yyerrlab;
      yyn = -yyn;
      goto yyreduce;
    }

  /* Count tokens shifted since error; after three, turn off error
     status.  */
  if (yyerrstatus)
    yyerrstatus--;

  /* Shift the lookahead token.  */
  YY_SYMBOL_PRINT ("Shifting", yytoken, &yylval, &yylloc);
  yystate = yyn;
  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  *++yyvsp = yylval;
  YY_IGNORE_MAYBE_UNINITIALIZED_END

  /* Discard the shifted token.  */
  yychar = YYEMPTY;
  goto yynewstate;


/*-----------------------------------------------------------.
| yydefault -- do the default action for the current state.  |
`-----------------------------------------------------------*/
yydefault:
  yyn = yydefact[yystate];
  if (yyn == 0)
    goto yyerrlab;
  goto yyreduce;


/*-----------------------------.
| yyreduce -- do a reduction.  |
`-----------------------------*/
yyreduce:
  /* yyn is the number of a rule to reduce with.  */
  yylen = yyr2[yyn];

  /* If YYLEN is nonzero, implement the default value of the action:
     '$$ = $1'.

     Otherwise, the following line sets YYVAL to garbage.
     This behavior is undocumented and Bison
     users should not rely upon it.  Assigning to YYVAL
     unconditionally makes the parser a bit smaller, and it avoids a
     GCC warning that YYVAL may be used uninitialized.  */
  yyval = yyvsp[1-yylen];


  YY_REDUCE_PRINT (yyn);
  switch (yyn)
    {
  case 2: /* R_admsParse: R_l_admsParse  */
#line 241 "vaYacc.y"
          {
          }
#line 1735 "vaYacc.cpp"
    break;

  case 3: /* R_l_admsParse: R_s_admsParse  */
#line 246 "vaYacc.y"
          {
          }
#line 1742 "vaYacc.cpp"
    break;

  case 4: /* R_l_admsParse: R_l_admsParse R_s_admsParse  */
#line 249 "vaYacc.y"
          {
          }
#line 1749 "vaYacc.cpp"
    break;

  case 5: /* R_s_admsParse: R_d_module  */
#line 254 "vaYacc.y"
          {
          }
#line 1756 "vaYacc.cpp"
    break;

  case 6: /* R_s_admsParse: R_discipline_member  */
#line 257 "vaYacc.y"
          {
          }
#line 1763 "vaYacc.cpp"
    break;

  case 7: /* R_s_admsParse: R_nature_member  */
#line 260 "vaYacc.y"
          {
          }
#line 1770 "vaYacc.cpp"
    break;

  case 8: /* R_discipline_member: tk_discipline R_discipline_name R_l_discipline_assignment tk_enddiscipline  */
#line 266 "vaYacc.y"
          {
            __disList.push_back(gDiscipline);
            //delete gDiscipline;
          }
#line 1779 "vaYacc.cpp"
    break;

  case 9: /* R_discipline_name: tk_ident  */
#line 273 "vaYacc.y"
          {
            gDiscipline = new discipline;
            gDiscipline->_name = ((yyvsp[0]._lexval))->_str;
          }
#line 1788 "vaYacc.cpp"
    break;

  case 10: /* R_l_discipline_assignment: R_s_discipline_assignment  */
#line 280 "vaYacc.y"
          {
          }
#line 1795 "vaYacc.cpp"
    break;

  case 11: /* R_l_discipline_assignment: R_l_discipline_assignment R_s_discipline_assignment  */
#line 283 "vaYacc.y"
          {
          }
#line 1802 "vaYacc.cpp"
    break;

  case 12: /* R_s_discipline_assignment: tk_potential R_discipline_naturename ';'  */
#line 288 "vaYacc.y"
          {
            gDiscipline->_potential = GetNature(((yyvsp[-1]._yaccval))->_str);
            if(gDiscipline->_potential == NULL){
                vaMessageError("can't find nature definition\n", (yyvsp[-1]._yaccval));
            }
            delete (yyvsp[-1]._yaccval);
          }
#line 1814 "vaYacc.cpp"
    break;

  case 13: /* R_s_discipline_assignment: tk_flow R_discipline_naturename ';'  */
#line 296 "vaYacc.y"
          {
            gDiscipline->_flow = GetNature(((yyvsp[-1]._yaccval))->_str);
            if(gDiscipline->_flow == NULL){
                vaMessageError("can't find nature definition\n", (yyvsp[-1]._yaccval));
            }
            delete (yyvsp[-1]._yaccval);
          }
#line 1826 "vaYacc.cpp"
    break;

  case 14: /* R_s_discipline_assignment: tk_domain tk_ident ';'  */
#line 304 "vaYacc.y"
          {
            string mylexval2 = ((yyvsp[-1]._lexval))->_str;
            if(mylexval2 == "discrete")
              gDiscipline->_domain = 0;
            else if(mylexval2 == "continuous")
              gDiscipline->_domain = 1;
            else
              vaMessageError("domain: bad value given - should be either 'discrete' or 'continuous'\n",(yyvsp[-1]._lexval));
          }
#line 1840 "vaYacc.cpp"
    break;

  case 15: /* R_discipline_naturename: tk_ident  */
#line 316 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
            ((yyval._yaccval))->_str = ((yyvsp[0]._lexval))->_str;
            ((yyval._yaccval))->_lex = *((yyvsp[0]._lexval));
          }
#line 1850 "vaYacc.cpp"
    break;

  case 16: /* R_nature_member: tk_nature tk_ident R_l_nature_assignment tk_endnature  */
#line 324 "vaYacc.y"
          {
            string mylexval2 = ((yyvsp[-2]._lexval))->_str;
            nature *mynature = NULL;
            if(gNatureAccess) 
              mynature = pushBackNature(__natureList, *gNatureAccess);
            else
              vaMessageError("attribute 'access' in nature definition not found\n",(yyvsp[-2]._lexval));
            mynature->_name = mylexval2;
            if(gNatureidt != NULL)
              mynature->_idt = *gNatureidt;
            if(gNatureddt != NULL) 
              mynature->_ddt = *gNatureddt;
            if(gNatureUnits != NULL)
              mynature->_units = *gNatureUnits;
            if(gNatureAbsTol != NULL)
              mynature->_abstol = *gNatureAbsTol;

            delete gNatureAccess;
            delete gNatureAbsTol;
            delete gNatureUnits;
            delete gNatureidt;
            delete gNatureddt;
            gNatureAccess = NULL;
            gNatureAbsTol = NULL;
            gNatureUnits = NULL;
            gNatureidt = NULL;
            gNatureddt = NULL;
          }
#line 1883 "vaYacc.cpp"
    break;

  case 17: /* R_l_nature_assignment: R_s_nature_assignment  */
#line 355 "vaYacc.y"
          {
          }
#line 1890 "vaYacc.cpp"
    break;

  case 18: /* R_l_nature_assignment: R_l_nature_assignment R_s_nature_assignment  */
#line 358 "vaYacc.y"
          {
          }
#line 1897 "vaYacc.cpp"
    break;

  case 19: /* R_s_nature_assignment: tk_ident '=' tk_number ';'  */
#line 363 "vaYacc.y"
          {
            string mylexval3=((yyvsp[-1]._lexval))->_str;
            if(((yyvsp[-3]._lexval))->_str == "abstol")
            {
              if(gNatureAbsTol)
                vaMessageError("nature attribute defined more than once\n",(yyvsp[-3]._lexval));
              gNatureAbsTol = new double;
              *gNatureAbsTol = string2double(mylexval3);
            }
            else
              vaMessageError("unknown nature attribute\n",(yyvsp[-3]._lexval));
          }
#line 1914 "vaYacc.cpp"
    break;

  case 20: /* R_s_nature_assignment: tk_ident '=' tk_number tk_ident ';'  */
#line 376 "vaYacc.y"
          {
            string mylexval3=((yyvsp[-2]._lexval))->_str;
            string mylexval4=((yyvsp[-1]._lexval))->_str;
            double myunit = 1.0;
            if(((yyvsp[-4]._lexval))->_str == "abstol")
            {
              if(gNatureAbsTol)
                vaMessageError("nature attribute defined more than once\n",(yyvsp[-4]._lexval));
              //gNatureAbsTol = adms_number_new(mylexval3);
            }
            else
              vaMessageError("unknown nature attribute\n",(yyvsp[-4]._lexval));
            if(0) { }
            else if((mylexval4 == "E")) myunit = 1e18;
            else if((mylexval4 == "P")) myunit = 1e15;
            else if((mylexval4 == "T")) myunit = 1e12;
            else if((mylexval4 == "G")) myunit = 1e9;
            else if((mylexval4 == "M")) myunit = 1e6;
            else if((mylexval4 == "k")) myunit = 1e3;
            else if((mylexval4 == "h")) myunit = 100;
            else if((mylexval4 == "D")) myunit = 10;
            else if((mylexval4 == "d")) myunit = 0.1;
            else if((mylexval4 == "c")) myunit = 0.01;
            else if((mylexval4 == "m")) myunit = 1e-3;
            else if((mylexval4 == "u")) myunit = 1e-6;
            else if((mylexval4 == "n")) myunit = 1e-9;
            else if((mylexval4 == "A")) myunit = 1e-10;
            else if((mylexval4 == "p")) myunit = 1e-12;
            else if((mylexval4 == "f")) myunit = 1e-15;
            else if((mylexval4 == "a")) myunit = 1e-18;
            else
              vaMessageError("can not convert symbol to valid unit\n",(yyvsp[-1]._lexval));
            gNatureAbsTol = new double;
            *gNatureAbsTol = myunit * string2double(mylexval3);
          }
#line 1954 "vaYacc.cpp"
    break;

  case 21: /* R_s_nature_assignment: tk_ident '=' tk_anystring ';'  */
#line 412 "vaYacc.y"
          {
            if(((yyvsp[-3]._lexval))->_str == "units")
            {
              if(gNatureUnits)
                vaMessageError("nature attribute defined more than once\n",(yyvsp[-3]._lexval));
              gNatureUnits = new string;
              *gNatureUnits = ((yyvsp[-1]._lexval))->_str;
            }
            else
              vaMessageError("unknown nature attribute\n",(yyvsp[-3]._lexval));
          }
#line 1970 "vaYacc.cpp"
    break;

  case 22: /* R_s_nature_assignment: tk_ident '=' tk_ident ';'  */
#line 424 "vaYacc.y"
          {
            string mylexval3 = ((yyvsp[-1]._lexval))->_str;
            if(((yyvsp[-3]._lexval))->_str == "access")
            {
              if(gNatureAccess)
                vaMessageError("nature attribute defined more than once\n",(yyvsp[-3]._lexval));
              gNatureAccess = new string;
              *gNatureAccess = mylexval3;
            }
            else if(((yyvsp[-3]._lexval))->_str == "idt_nature")
            {
              if(gNatureidt)
                vaMessageError("idt_nature attribute defined more than once\n",(yyvsp[-3]._lexval));
              gNatureidt = new string;
              *gNatureidt = mylexval3;
            }
            else if(((yyvsp[-3]._lexval))->_str == "ddt_nature")
            {
              if(gNatureddt)
                vaMessageError("ddt_nature attribute defined more than once\n",(yyvsp[-3]._lexval));
              gNatureddt = new string;
              *gNatureddt = mylexval3;
            }
            else
              vaMessageError("unknown nature attribute\n",(yyvsp[-3]._lexval));
          }
#line 2001 "vaYacc.cpp"
    break;

  case 23: /* R_d_attribute_0: %empty  */
#line 454 "vaYacc.y"
          {
          }
#line 2008 "vaYacc.cpp"
    break;

  case 24: /* R_d_attribute_0: R_d_attribute  */
#line 457 "vaYacc.y"
          {
          }
#line 2015 "vaYacc.cpp"
    break;

  case 25: /* R_d_attribute: tk_beginattribute R_l_attribute tk_endattribute  */
#line 462 "vaYacc.y"
          {
              attribute* myattr = new attribute;
              myattr->_attrlist = gAttribute;
              __attrList.push_back(myattr);
              gAttribute.clear();
          }
#line 2026 "vaYacc.cpp"
    break;

  case 26: /* R_d_attribute: tk_beginattribute tk_anytext  */
#line 469 "vaYacc.y"
          {
            string mylexval2 = ((yyvsp[0]._lexval))->_str;
            attribute* myattribute = new attribute;
            (myattribute->_attrlist)["ibm"] = mylexval2;
            __attrList.push_back(myattribute);
          }
#line 2037 "vaYacc.cpp"
    break;

  case 27: /* R_d_attribute: tk_beginattribute tk_endattribute  */
#line 476 "vaYacc.y"
          {
          }
#line 2044 "vaYacc.cpp"
    break;

  case 28: /* R_l_attribute: R_s_attribute  */
#line 481 "vaYacc.y"
          {
          }
#line 2051 "vaYacc.cpp"
    break;

  case 29: /* R_l_attribute: R_l_attribute R_s_attribute  */
#line 484 "vaYacc.y"
          {
          }
#line 2058 "vaYacc.cpp"
    break;

  case 30: /* R_s_attribute: tk_ident '=' tk_anystring  */
#line 489 "vaYacc.y"
          {
            string mylexval1 = ((yyvsp[-2]._lexval))->_str;
            string mylexval3 = ((yyvsp[0]._lexval))->_str;
            gAttribute[mylexval1] = mylexval3;
          }
#line 2068 "vaYacc.cpp"
    break;

  case 31: /* $@1: %empty  */
#line 498 "vaYacc.y"
          {
            string mylexval3=((yyvsp[0]._lexval))->_str;
            gModule = pushBackModule(__moduleList, mylexval3);
            gModule->_head = new variableblock;
            gModule->_head->_prev = NULL;
            gModule->_head->_next = NULL;
            gModule->_head->_right = NULL;
            gModule->_current = gModule->_head;
            LoadSystemFunction(gModule->_analogFun);
            __modDdtNum = 0;

            if(__attrList.size() != 0){
                gModule->_attr = __attrList.back();
                __attrList.pop_back();
            }
          }
#line 2089 "vaYacc.cpp"
    break;

  case 32: /* R_d_module: R_d_attribute_0 tk_module tk_ident $@1 R_d_terminal R_modulebody tk_endmodule  */
#line 515 "vaYacc.y"
          {
            //adms_slist_inreverse(&gModule->_assignment);
              gModule->_ddtnum = __modDdtNum;
          }
#line 2098 "vaYacc.cpp"
    break;

  case 33: /* R_modulebody: %empty  */
#line 522 "vaYacc.y"
          {
          }
#line 2105 "vaYacc.cpp"
    break;

  case 34: /* R_modulebody: R_l_declaration  */
#line 525 "vaYacc.y"
          {
          }
#line 2112 "vaYacc.cpp"
    break;

  case 35: /* R_modulebody: R_netlist  */
#line 528 "vaYacc.y"
          {
          }
#line 2119 "vaYacc.cpp"
    break;

  case 36: /* R_modulebody: R_l_declaration R_netlist  */
#line 531 "vaYacc.y"
          {
          }
#line 2126 "vaYacc.cpp"
    break;

  case 37: /* R_netlist: R_analog  */
#line 536 "vaYacc.y"
          {
          }
#line 2133 "vaYacc.cpp"
    break;

  case 38: /* R_netlist: R_l_instance  */
#line 539 "vaYacc.y"
          {
          }
#line 2140 "vaYacc.cpp"
    break;

  case 39: /* R_netlist: R_l_instance R_analog  */
#line 542 "vaYacc.y"
          {
          }
#line 2147 "vaYacc.cpp"
    break;

  case 40: /* R_netlist: R_analog R_l_instance  */
#line 545 "vaYacc.y"
          {
          }
#line 2154 "vaYacc.cpp"
    break;

  case 41: /* R_netlist: R_l_instance R_analog R_l_instance  */
#line 548 "vaYacc.y"
          {
          }
#line 2161 "vaYacc.cpp"
    break;

  case 42: /* R_l_instance: R_s_instance  */
#line 553 "vaYacc.y"
          {
          }
#line 2168 "vaYacc.cpp"
    break;

  case 43: /* R_l_instance: R_l_instance R_s_instance  */
#line 556 "vaYacc.y"
          {
          }
#line 2175 "vaYacc.cpp"
    break;

  case 44: /* R_d_terminal: '(' R_l_terminal_0 ')' R_d_attribute_0 ';'  */
#line 561 "vaYacc.y"
          {
            if(__attrList.size() != 0){
                gModule->_attr = __attrList.back();
                __attrList.pop_back();
            }
          }
#line 2186 "vaYacc.cpp"
    break;

  case 45: /* R_l_terminal_0: %empty  */
#line 570 "vaYacc.y"
          {
          }
#line 2193 "vaYacc.cpp"
    break;

  case 46: /* R_l_terminal_0: R_l_terminal  */
#line 573 "vaYacc.y"
          {
          }
#line 2200 "vaYacc.cpp"
    break;

  case 47: /* R_l_terminal: R_s_terminal  */
#line 578 "vaYacc.y"
          {
          }
#line 2207 "vaYacc.cpp"
    break;

  case 48: /* R_l_terminal: R_l_terminal ',' R_s_terminal  */
#line 581 "vaYacc.y"
          {
          }
#line 2214 "vaYacc.cpp"
    break;

  case 49: /* R_s_terminal: tk_ident  */
#line 586 "vaYacc.y"
          {
            string mylexval1 = ((yyvsp[0]._lexval))->_str;
            vector<terminal>::iterator iter = gModule->_port.begin();
            while(iter != gModule->_port.end()){
                if(iter->_name == mylexval1)
                vaMessageError("Redefinition of port name.\n", (yyvsp[0]._lexval));
                ++iter;
            }
            terminal myterm;
            myterm._name = mylexval1;
            myterm._type = 0;
            (gModule->_port).push_back(myterm);
          }
#line 2232 "vaYacc.cpp"
    break;

  case 50: /* R_l_declaration: R_s_declaration_withattribute  */
#line 602 "vaYacc.y"
          {
          }
#line 2239 "vaYacc.cpp"
    break;

  case 51: /* R_l_declaration: R_l_declaration R_s_declaration_withattribute  */
#line 605 "vaYacc.y"
          {
          }
#line 2246 "vaYacc.cpp"
    break;

  case 52: /* R_s_declaration_withattribute: R_s_declaration  */
#line 610 "vaYacc.y"
          {
          }
#line 2253 "vaYacc.cpp"
    break;

  case 53: /* R_s_declaration_withattribute: R_d_attribute_global R_s_declaration  */
#line 613 "vaYacc.y"
          {
              delete __globalAttr;
              __globalAttr = NULL;
          }
#line 2262 "vaYacc.cpp"
    break;

  case 54: /* R_d_attribute_global: R_d_attribute  */
#line 620 "vaYacc.y"
          {
              __globalAttr = __attrList.back();
              __attrList.pop_back();
          }
#line 2271 "vaYacc.cpp"
    break;

  case 55: /* R_s_declaration: R_d_node  */
#line 627 "vaYacc.y"
          {
          }
#line 2278 "vaYacc.cpp"
    break;

  case 56: /* R_s_declaration: R_d_branch  */
#line 630 "vaYacc.y"
          {
          }
#line 2285 "vaYacc.cpp"
    break;

  case 57: /* R_s_declaration: R_s_param_declaration  */
#line 633 "vaYacc.y"
          {
	  }
#line 2292 "vaYacc.cpp"
    break;

  case 58: /* R_s_declaration: R_variable_type R_l_variable R_d_variable_end  */
#line 636 "vaYacc.y"
          {
          }
#line 2299 "vaYacc.cpp"
    break;

  case 59: /* R_s_declaration: R_d_aliasparameter  */
#line 639 "vaYacc.y"
          {
          }
#line 2306 "vaYacc.cpp"
    break;

  case 60: /* R_s_declaration: R_d_analogfunction  */
#line 642 "vaYacc.y"
          {
          }
#line 2313 "vaYacc.cpp"
    break;

  case 61: /* R_s_declaration: ';'  */
#line 645 "vaYacc.y"
          {
          }
#line 2320 "vaYacc.cpp"
    break;

  case 62: /* R_s_param_declaration: tk_parameter R_variable_type R_l_parameter R_d_variable_end  */
#line 651 "vaYacc.y"
        {
	}
#line 2327 "vaYacc.cpp"
    break;

  case 63: /* R_s_param_declaration: tk_parameter R_l_parameter R_d_variable_end  */
#line 654 "vaYacc.y"
        {
	}
#line 2334 "vaYacc.cpp"
    break;

  case 64: /* R_d_node: R_node_type R_l_terminalnode ';'  */
#line 659 "vaYacc.y"
          {
              R_d_node(gNodeList, gNodeDirection, (void*)(yyvsp[-2]._yaccval), true);
              delete (yyvsp[-2]._yaccval);
          }
#line 2343 "vaYacc.cpp"
    break;

  case 65: /* R_d_node: tk_ground R_l_node ';'  */
#line 664 "vaYacc.y"
          {
              R_d_node(gNodeList, -1, (void*)(yyvsp[-2]._lexval), false);
          }
#line 2351 "vaYacc.cpp"
    break;

  case 66: /* R_d_node: tk_ident R_l_node ';'  */
#line 668 "vaYacc.y"
          {
              string mylexval1=((yyvsp[-2]._lexval))->_str;
              list<discipline*>::iterator it = __disList.begin();
              while(it != __disList.end()){
                  if((*it)->_name == mylexval1){
                      break;
                  }
                  ++it;
              }
              if(it == __disList.end())
                  vaMessageError("Unknow net type.", (yyvsp[-2]._lexval));
              list<string>::iterator iter = gNodeList.begin();
              net mynet;
              mynet._disp = *it;
              while(iter != gNodeList.end()){
                  mynet._name = *iter;
                  gModule->_net.push_back(mynet);
                  ++iter;
              }
              gNodeList.clear(); 
          }
#line 2377 "vaYacc.cpp"
    break;

  case 67: /* R_node_type: tk_input  */
#line 692 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
            (yyval._yaccval)->_lex = *((yyvsp[0]._lexval));
            gNodeDirection = 1;
          }
#line 2387 "vaYacc.cpp"
    break;

  case 68: /* R_node_type: tk_output  */
#line 698 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
            (yyval._yaccval)->_lex = *((yyvsp[0]._lexval));
            gNodeDirection = 2;
          }
#line 2397 "vaYacc.cpp"
    break;

  case 69: /* R_node_type: tk_inout  */
#line 704 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
            (yyval._yaccval)->_lex = *((yyvsp[0]._lexval));
            gNodeDirection = 3;
          }
#line 2407 "vaYacc.cpp"
    break;

  case 70: /* R_l_terminalnode: R_s_terminalnode  */
#line 712 "vaYacc.y"
          {
          }
#line 2414 "vaYacc.cpp"
    break;

  case 71: /* R_l_terminalnode: R_l_terminalnode ',' R_s_terminalnode  */
#line 715 "vaYacc.y"
          {
          }
#line 2421 "vaYacc.cpp"
    break;

  case 72: /* R_l_node: R_s_node  */
#line 720 "vaYacc.y"
          {
          }
#line 2428 "vaYacc.cpp"
    break;

  case 73: /* R_l_node: R_l_node ',' R_s_node  */
#line 723 "vaYacc.y"
          {
          }
#line 2435 "vaYacc.cpp"
    break;

  case 74: /* R_s_terminalnode: tk_ident R_d_attribute_0  */
#line 728 "vaYacc.y"
          {
            string mylexval1 = ((yyvsp[-1]._lexval))->_str;
            vector<terminal>::iterator iter;
            iter = gModule->_port.begin();
            while(iter != gModule->_port.end()){
                if(iter->_name == mylexval1) break;
                ++iter;
            }
            if(iter == (gModule->_port).end()){
                vaMessageError("terminal not found\n", (yyvsp[-1]._lexval));
            }
            if(iter->_type != 0)
                vaMessageError("Redefinition terminal.\n", (yyvsp[-1]._lexval));

            gNodeList.push_back(mylexval1);
            if(__attrList.size() != 0){
                delete __attrList.back();
                __attrList.pop_back();
            };
          }
#line 2460 "vaYacc.cpp"
    break;

  case 75: /* R_s_node: tk_ident R_d_attribute_0  */
#line 751 "vaYacc.y"
          {
            string mylexval1 = ((yyvsp[-1]._lexval))->_str;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval1)
                    vaMessageError("Redefinition of net.\n", (yyvsp[-1]._lexval));
                ++iter;
            }
            gNodeList.push_back(mylexval1);
            if(__attrList.size() != 0){
                delete __attrList.back();
                __attrList.pop_back();
            };

          }
#line 2480 "vaYacc.cpp"
    break;

  case 76: /* R_d_branch: tk_branch R_s_branch ';'  */
#line 770 "vaYacc.y"
          {
          }
#line 2487 "vaYacc.cpp"
    break;

  case 77: /* R_l_branchalias: R_s_branchalias  */
#line 775 "vaYacc.y"
          {
          }
#line 2494 "vaYacc.cpp"
    break;

  case 78: /* R_l_branchalias: R_l_branchalias ',' R_s_branchalias  */
#line 778 "vaYacc.y"
          {
          }
#line 2501 "vaYacc.cpp"
    break;

  case 79: /* R_s_branchalias: tk_ident  */
#line 783 "vaYacc.y"
          {
            string mylexval1 = ((yyvsp[0]._lexval))->_str;
            gBranchList.push_back(mylexval1);
          }
#line 2510 "vaYacc.cpp"
    break;

  case 80: /* R_s_branch: '(' tk_ident ',' tk_ident ')' R_l_branchalias  */
#line 790 "vaYacc.y"
          {
            string mylexval2 = ((yyvsp[-4]._lexval))->_str;
            string mylexval4 = ((yyvsp[-2]._lexval))->_str;
            int flag = 0;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval2) flag |= 1;
                else if(iter->_name == mylexval4) flag |= 2;
                ++iter;
            }
            if(flag != 3){
                vaMessageError("Node used in branch never declared.\n", (yyvsp[-4]._lexval));
            }
            branch mybranch;
            mybranch._type = 2;
            mybranch._pnode = mylexval2;
            mybranch._nnode = mylexval4;
            list<string>::iterator it = gBranchList.begin();
            while(it != gBranchList.end()){
                (gModule->_branchAlias)[*it] = mybranch;
                ++it;
            }
            gBranchList.clear();
          }
#line 2539 "vaYacc.cpp"
    break;

  case 81: /* R_s_branch: '(' tk_ident ')' R_l_branchalias  */
#line 815 "vaYacc.y"
          {
            string mylexval2 = ((yyvsp[-2]._lexval))->_str;
            int flag = 0;
            vector<net>::iterator iter = gModule->_net.begin();
            while(iter != gModule->_net.end()){
                if(iter->_name == mylexval2) flag |= 1;
                ++iter;
            }
            if(flag == 0)
                vaMessageError("Node never declared.\n", (yyvsp[-2]._lexval));
            branch mybranch;
            mybranch._type = 1;
            mybranch._pnode = mylexval2;
            list<string>::iterator it = gBranchList.begin();
            while(it != gBranchList.end()){
                (gModule->_branchAlias)[*it] = mybranch;
                ++it;
            }
            gBranchList.clear();
          }
#line 2564 "vaYacc.cpp"
    break;

  case 82: /* R_d_analogfunction: R_d_analogfunction_proto R_l_analogfunction_declaration R_analogcode_block tk_endfunction  */
#line 839 "vaYacc.y"
          {
            //gAnalogfunction->_state = GetCalState($3);
	    gAnalogfunction->_state._steps = (yyvsp[-1]._yaccval)->_state;
	    gAnalogfunction->_state._tree = (yyvsp[-1]._yaccval)->_tree;
            gAnalogfunction = NULL;
          }
#line 2575 "vaYacc.cpp"
    break;

  case 83: /* R_d_analogfunction_proto: tk_analog tk_function R_d_analogfunction_name ';'  */
#line 848 "vaYacc.y"
          {
              gAnalogfunction = analogFunctionNew(gModule, ((yyvsp[-1]._yaccval))->_str);
              if(gAnalogfunction == NULL)
                  vaMessageError("analog function name already defined.\n", (yyvsp[-1]._yaccval));
              gAnalogfunction->_type = 2;
          }
#line 2586 "vaYacc.cpp"
    break;

  case 84: /* R_d_analogfunction_proto: tk_analog tk_function tk_integer R_d_analogfunction_name ';'  */
#line 855 "vaYacc.y"
          {
              gAnalogfunction = analogFunctionNew(gModule, ((yyvsp[-1]._yaccval))->_str);
              gAnalogfunction->_type = 1;
          }
#line 2595 "vaYacc.cpp"
    break;

  case 85: /* R_d_analogfunction_proto: tk_analog tk_function tk_real R_d_analogfunction_name ';'  */
#line 860 "vaYacc.y"
          {
              gAnalogfunction = analogFunctionNew(gModule, ((yyvsp[-1]._yaccval))->_str);
              gAnalogfunction->_type = 2;
          }
#line 2604 "vaYacc.cpp"
    break;

  case 86: /* R_d_analogfunction_name: tk_ident  */
#line 868 "vaYacc.y"
          {
          }
#line 2611 "vaYacc.cpp"
    break;

  case 87: /* R_l_analogfunction_declaration: R_s_analogfunction_declaration  */
#line 873 "vaYacc.y"
          {
          }
#line 2618 "vaYacc.cpp"
    break;

  case 88: /* R_l_analogfunction_declaration: R_l_analogfunction_declaration R_s_analogfunction_declaration  */
#line 876 "vaYacc.y"
          {
          }
#line 2625 "vaYacc.cpp"
    break;

  case 89: /* R_s_analogfunction_declaration: tk_input R_l_analogfunction_input_variable ';'  */
#line 881 "vaYacc.y"
          {
          }
#line 2632 "vaYacc.cpp"
    break;

  case 90: /* R_s_analogfunction_declaration: tk_output R_l_analogfunction_output_variable ';'  */
#line 884 "vaYacc.y"
          {
          }
#line 2639 "vaYacc.cpp"
    break;

  case 91: /* R_s_analogfunction_declaration: tk_inout R_l_analogfunction_inout_variable ';'  */
#line 887 "vaYacc.y"
          {
          }
#line 2646 "vaYacc.cpp"
    break;

  case 92: /* R_s_analogfunction_declaration: tk_integer R_l_analogfunction_integer_variable ';'  */
#line 890 "vaYacc.y"
          {
          }
#line 2653 "vaYacc.cpp"
    break;

  case 93: /* R_s_analogfunction_declaration: tk_real R_l_analogfunction_real_variable ';'  */
#line 893 "vaYacc.y"
          {
          }
#line 2660 "vaYacc.cpp"
    break;

  case 94: /* R_l_analogfunction_input_variable: tk_ident  */
#line 898 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 1);
          }
#line 2668 "vaYacc.cpp"
    break;

  case 95: /* R_l_analogfunction_input_variable: R_l_analogfunction_input_variable ',' tk_ident  */
#line 902 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 1);
          }
#line 2676 "vaYacc.cpp"
    break;

  case 96: /* R_l_analogfunction_output_variable: tk_ident  */
#line 908 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 2);
          }
#line 2684 "vaYacc.cpp"
    break;

  case 97: /* R_l_analogfunction_output_variable: R_l_analogfunction_output_variable ',' tk_ident  */
#line 912 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 2);
          }
#line 2692 "vaYacc.cpp"
    break;

  case 98: /* R_l_analogfunction_inout_variable: tk_ident  */
#line 918 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 3);
          }
#line 2700 "vaYacc.cpp"
    break;

  case 99: /* R_l_analogfunction_inout_variable: R_l_analogfunction_inout_variable ',' tk_ident  */
#line 922 "vaYacc.y"
          {
              AddFunctionVariable(gAnalogfunction, (yyvsp[0]._lexval), 3);
          }
#line 2708 "vaYacc.cpp"
    break;

  case 100: /* R_l_analogfunction_integer_variable: tk_ident  */
#line 928 "vaYacc.y"
          {
              (gAnalogfunction->_var[(yyvsp[0]._lexval)->_str])._type = 1;
          }
#line 2716 "vaYacc.cpp"
    break;

  case 101: /* R_l_analogfunction_integer_variable: R_l_analogfunction_integer_variable ',' tk_ident  */
#line 932 "vaYacc.y"
          {
              (gAnalogfunction->_var[(yyvsp[0]._lexval)->_str])._type = 1;
          }
#line 2724 "vaYacc.cpp"
    break;

  case 102: /* R_l_analogfunction_real_variable: tk_ident  */
#line 938 "vaYacc.y"
          {
              (gAnalogfunction->_var[(yyvsp[0]._lexval)->_str])._type = 2;
          }
#line 2732 "vaYacc.cpp"
    break;

  case 103: /* R_l_analogfunction_real_variable: R_l_analogfunction_real_variable ',' tk_ident  */
#line 942 "vaYacc.y"
          {
              (gAnalogfunction->_var[(yyvsp[0]._lexval)->_str])._type = 2;
          }
#line 2740 "vaYacc.cpp"
    break;

  case 104: /* R_variable_type: tk_integer R_d_attribute_0  */
#line 948 "vaYacc.y"
          {
            gVariableType = 1;
          }
#line 2748 "vaYacc.cpp"
    break;

  case 105: /* R_variable_type: tk_real R_d_attribute_0  */
#line 952 "vaYacc.y"
          {
            gVariableType = 2;
          }
#line 2756 "vaYacc.cpp"
    break;

  case 106: /* R_variable_type: tk_string R_d_attribute_0  */
#line 956 "vaYacc.y"
          {
            gVariableType = 3;
          }
#line 2764 "vaYacc.cpp"
    break;

  case 107: /* R_d_variable_end: ';'  */
#line 962 "vaYacc.y"
          {
              variable myvar;
              myvar._type = gVariableType;
              list<string>::iterator iter = gVariableList.begin();
              while(iter != gVariableList.end()){
                  myvar._name = *iter;
                  (gModule->_variable).push_back(myvar);
                  ++iter;
              }
              gVariableList.clear();
          }
#line 2780 "vaYacc.cpp"
    break;

  case 108: /* R_l_parameter: R_s_parameter  */
#line 976 "vaYacc.y"
          {
          }
#line 2787 "vaYacc.cpp"
    break;

  case 109: /* R_l_parameter: R_l_parameter ',' R_s_parameter  */
#line 979 "vaYacc.y"
          {
          }
#line 2794 "vaYacc.cpp"
    break;

  case 110: /* R_l_variable: R_s_variable  */
#line 984 "vaYacc.y"
          {
          }
#line 2801 "vaYacc.cpp"
    break;

  case 111: /* R_l_variable: R_l_variable ',' R_s_variable  */
#line 987 "vaYacc.y"
          {
          }
#line 2808 "vaYacc.cpp"
    break;

  case 112: /* R_d_aliasparameter: R_d_aliasparameter_token tk_ident '=' tk_ident R_d_attribute_0 ';'  */
#line 992 "vaYacc.y"
          {
              vaMessageError("Parameters alias not support now.", (yyvsp[-4]._lexval));
          }
#line 2816 "vaYacc.cpp"
    break;

  case 113: /* R_d_aliasparameter_token: tk_aliasparameter  */
#line 998 "vaYacc.y"
          {
          }
#line 2823 "vaYacc.cpp"
    break;

  case 114: /* R_d_aliasparameter_token: tk_aliasparam  */
#line 1001 "vaYacc.y"
          {
          }
#line 2830 "vaYacc.cpp"
    break;

  case 115: /* R_s_parameter: R_s_parameter_name R_d_attribute_0  */
#line 1006 "vaYacc.y"
          {
              if(__attrList.size() != 0){
                parameter* myparam = &((gModule->_param).back());
                myparam->_attr = __attrList.back();
                __attrList.pop_back();
                if((myparam->_attr->_attrlist)[string("type")] == "instance")
                    myparam->_type = 1;
                else myparam->_type = 0;
              }
              else {
                (gModule->_param.back())._attr = NULL;
                (gModule->_param.back())._type = 0;
              }
          }
#line 2849 "vaYacc.cpp"
    break;

  case 116: /* R_s_variable: R_s_variable_name R_d_attribute_0  */
#line 1023 "vaYacc.y"
          {
              if(__attrList.size() != 0){
                  __attrList.pop_back();
              }
          }
#line 2859 "vaYacc.cpp"
    break;

  case 117: /* R_s_parameter_name: R_s_variable_name '=' R_s_expression R_s_parameter_range  */
#line 1031 "vaYacc.y"
          {
              parameter myparam;
              myparam._name = gVariableList.back();
              if(gRange != NULL){
                  myparam._range = gRange;
              }else{
                  myparam._range = NULL;
              }
              myparam._defvalue = ((yyvsp[-1]._yaccval))->_value;
              // 非纯数字默认值（如 VSAT1 = VSAT）：保存表达式文本，
              // codegen 以参数成员名重写后作为成员初始化表达式
              {
                  const string& dv = ((yyvsp[-1]._yaccval)->_state).front()._describ;
                  bool pureNum = !dv.empty();
                  for (char c : dv) {
                      if (!(isdigit(c) || c=='.' || c=='e' || c=='E' || c=='+' || c=='-' || c==' ')) {
                          pureNum = false; break;
                      }
                  }
                  myparam._defexpr = pureNum ? string() : dv;
              }
              if(!AddParameter(gModule, myparam._name)){
                  vaMessageError("Redefine of parameter.", (yyvsp[-3]._yaccval));
              }
              gModule->_param.push_back(myparam);
              gRange = NULL;
              gVariableList.clear();
          }
#line 2892 "vaYacc.cpp"
    break;

  case 118: /* R_s_variable_name: tk_ident  */
#line 1062 "vaYacc.y"
          {
              string tmp = (yyvsp[0]._lexval)->_str;
              gVariableList.push_back((yyvsp[0]._lexval)->_str);
              delete (yyvsp[0]._lexval);
          }
#line 2902 "vaYacc.cpp"
    break;

  case 119: /* R_s_variable_name: tk_ident '[' tk_number ':' tk_number ']'  */
#line 1068 "vaYacc.y"
          {
              vaMessageError("Array not support now.", (yyvsp[-5]._lexval));
          }
#line 2910 "vaYacc.cpp"
    break;

  case 120: /* R_s_parameter_range: %empty  */
#line 1074 "vaYacc.y"
          {
          }
#line 2917 "vaYacc.cpp"
    break;

  case 121: /* R_s_parameter_range: R_l_interval  */
#line 1077 "vaYacc.y"
          {
          }
#line 2924 "vaYacc.cpp"
    break;

  case 122: /* R_l_interval: R_s_interval  */
#line 1082 "vaYacc.y"
          {
          }
#line 2931 "vaYacc.cpp"
    break;

  case 123: /* R_l_interval: R_l_interval R_s_interval  */
#line 1085 "vaYacc.y"
          {
	    //              vaMessageError("Muti interval describe of parameter not support now.", $2);
          }
#line 2939 "vaYacc.cpp"
    break;

  case 124: /* R_s_interval: tk_from R_d_interval  */
#line 1091 "vaYacc.y"
          {
              gRange->_type = 1;
          }
#line 2947 "vaYacc.cpp"
    break;

  case 125: /* R_s_interval: tk_exclude R_d_interval  */
#line 1095 "vaYacc.y"
          {
              gRange->_type = 2;
          }
#line 2955 "vaYacc.cpp"
    break;

  case 126: /* R_s_interval: tk_exclude R_s_expression  */
#line 1099 "vaYacc.y"
          {
            // `exclude 0.0`（无 from 区间）：gRange 尚未分配，先建再标型，
            // 否则空指针解引用（BSIM-CMG 的参数形式）。
            if(gRange == NULL){
                gRange = new range;
                gRange->_binf = true;
                gRange->_einf = true;
            }
            gRange->_type = 2;
          }
#line 2970 "vaYacc.cpp"
    break;

  case 127: /* R_d_interval: '(' R_interval_inf R_interval_seg R_interval_sup ')'  */
#line 1113 "vaYacc.y"
          {
              R_interval((yyvsp[-3]._yaccval), (yyvsp[-1]._yaccval), gRange, 1,1);
          }
#line 2978 "vaYacc.cpp"
    break;

  case 128: /* R_d_interval: '(' R_interval_inf R_interval_seg R_interval_sup ']'  */
#line 1117 "vaYacc.y"
          {
              R_interval((yyvsp[-3]._yaccval), (yyvsp[-1]._yaccval), gRange, 1,2);
          }
#line 2986 "vaYacc.cpp"
    break;

  case 129: /* R_d_interval: '[' R_interval_inf R_interval_seg R_interval_sup ')'  */
#line 1121 "vaYacc.y"
          {
              R_interval((yyvsp[-3]._yaccval), (yyvsp[-1]._yaccval), gRange, 2,1);
          }
#line 2994 "vaYacc.cpp"
    break;

  case 130: /* R_d_interval: '[' R_interval_inf R_interval_seg R_interval_sup ']'  */
#line 1125 "vaYacc.y"
          {
              R_interval((yyvsp[-3]._yaccval), (yyvsp[-1]._yaccval), gRange, 2,2);
          }
#line 3002 "vaYacc.cpp"
    break;

  case 131: /* R_d_interval: R_s_expression  */
#line 1129 "vaYacc.y"
          {
              vaMessageError("expression interval not support now.", (yyvsp[0]._yaccval));
          }
#line 3010 "vaYacc.cpp"
    break;

  case 132: /* R_interval_seg: ':'  */
#line 1136 "vaYacc.y"
        {
	}
#line 3017 "vaYacc.cpp"
    break;

  case 133: /* R_interval_seg: ','  */
#line 1139 "vaYacc.y"
        {
	}
#line 3024 "vaYacc.cpp"
    break;

  case 134: /* R_interval_inf: R_s_expression  */
#line 1145 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3032 "vaYacc.cpp"
    break;

  case 135: /* R_interval_inf: '-' tk_inf  */
#line 1149 "vaYacc.y"
          {
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = "inf";
          }
#line 3041 "vaYacc.cpp"
    break;

  case 136: /* R_interval_sup: R_s_expression  */
#line 1156 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3049 "vaYacc.cpp"
    break;

  case 137: /* R_interval_sup: tk_inf  */
#line 1160 "vaYacc.y"
          {
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = "inf";
          }
#line 3058 "vaYacc.cpp"
    break;

  case 138: /* R_interval_sup: '+' tk_inf  */
#line 1165 "vaYacc.y"
          {
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = "inf";
          }
#line 3067 "vaYacc.cpp"
    break;

  case 139: /* R_analog: tk_analog R_analogcode  */
#line 1172 "vaYacc.y"
          {
              //gModule->_analog=adms_analog_new(YY($2));
              list<statement>::iterator iter;
	      if((yyvsp[0]._yaccval) != NULL)
		{
		  iter = (yyvsp[0]._yaccval)->_state.begin();
		  while(iter != (yyvsp[0]._yaccval)->_state.end()){
		    gModule->_main._steps.push_back(*iter);
		    ++iter;
		  }
		}
          }
#line 3084 "vaYacc.cpp"
    break;

  case 140: /* R_analogcode: R_analogcode_atomic  */
#line 1187 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              while(gStateList.size() != 0){
                  (yyval._yaccval)->_state.push_front(gStateList.back());
                  gStateList.pop_back();
              }
          }
#line 3096 "vaYacc.cpp"
    break;

  case 141: /* R_analogcode: R_analogcode_block  */
#line 1195 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3104 "vaYacc.cpp"
    break;

  case 142: /* R_analogcode_atomic: R_d_attribute_0 R_d_blockvariable  */
#line 1201 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
          }
#line 3115 "vaYacc.cpp"
    break;

  case 143: /* R_analogcode_atomic: R_d_contribution  */
#line 1208 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
              //($$->_state.front())._describ += ";";
          }
#line 3124 "vaYacc.cpp"
    break;

  case 144: /* R_analogcode_atomic: R_s_assignment ';'  */
#line 1213 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[-1]._yaccval);
              ((yyval._yaccval)->_state.front())._describ += ";";
          }
#line 3133 "vaYacc.cpp"
    break;

  case 145: /* R_analogcode_atomic: R_d_conditional  */
#line 1218 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
              statement mystat;
              mystat._mode = 4;
              mystat._type = false;
              map<string, bitset<BIT_> >::iterator iter;
              if(gOutsideZero.size() > 0){
                iter = gOutsideZero.begin();
                while(gOutsideZero.end() != iter){
                  mystat._describ = GetZeroDerivation(iter->first, iter->second);
                  (yyval._yaccval)->_state.push_front(mystat);
                  ++iter;
                }
              }
              gOutsideZero.clear();
          }
#line 3154 "vaYacc.cpp"
    break;

  case 146: /* R_analogcode_atomic: R_d_while  */
#line 1235 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3162 "vaYacc.cpp"
    break;

  case 147: /* R_analogcode_atomic: R_d_case  */
#line 1239 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3170 "vaYacc.cpp"
    break;

  case 148: /* R_analogcode_atomic: R_d_for  */
#line 1243 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 3178 "vaYacc.cpp"
    break;

  case 149: /* R_analogcode_atomic: tk_dollar_ident '(' R_l_callfunction_expression ')' ';'  */
#line 1247 "vaYacc.y"
          {
            //modified by ly
	    if((yyvsp[-4]._lexval)->_str == "$strobe")
	      {
		(yyval._yaccval) = new yaccVal;
		statement mystat;
		map<string, int>::iterator piter;
		mystat._param = ((yyvsp[-2]._yaccval)->_state).front()._param;
		mystat._describ = "printf(" + ((yyvsp[-2]._yaccval)->_state).front()._describ;
		list<statement>::iterator iter = (yyvsp[-2]._yaccval)->_state.begin();
		++iter;
		while(iter != (yyvsp[-2]._yaccval)->_state.end()) {
		  mystat._describ +=  ", " + (*iter)._describ;
		  piter = (*iter)._param.begin();
		  while(piter != (*iter)._param.end())
		    {
		      mystat._param.insert(*piter);
		      ++piter;
		    }
		  ++iter;
		}
		mystat._describ += ");";
		
		mystat._mode = 1;
		((yyval._yaccval)->_state).push_back(mystat);
	      }
	    else if((yyvsp[-4]._lexval)->_str == "$finish")
	      {
		(yyval._yaccval) = new yaccVal;
		statement mystat;
		mystat._describ = "exit(" + ((yyvsp[-2]._yaccval)->_state).front()._describ + ");";
		mystat._mode = 1;
		((yyval._yaccval)->_state).push_back(mystat);
	      }
	    else
	      {
		R_analogcode_tk_ident((yyval._yaccval), (yyvsp[-4]._lexval)->_str + "(" + (yyvsp[-2]._yaccval)->_str + ");");
		((yyval._yaccval)->_state.front())._describ += ";";
	      }
	    SetVariableType(gModule, (yyvsp[-4]._lexval)->_str, 0);
          }
#line 3224 "vaYacc.cpp"
    break;

  case 150: /* R_analogcode_atomic: tk_dollar_ident '(' ')' ';'  */
#line 1289 "vaYacc.y"
          {
              R_analogcode_tk_ident((yyval._yaccval), (yyvsp[-3]._lexval)->_str + "();");
          }
#line 3232 "vaYacc.cpp"
    break;

  case 151: /* R_analogcode_atomic: tk_dollar_ident ';'  */
#line 1293 "vaYacc.y"
          {
              vaMessageError("system variable ", (yyvsp[-1]._lexval));
          }
#line 3240 "vaYacc.cpp"
    break;

  case 152: /* R_analogcode_atomic: ';'  */
#line 1297 "vaYacc.y"
          {
              //vaMessageError("");
              (yyval._yaccval) = new yaccVal;
          }
#line 3249 "vaYacc.cpp"
    break;

  case 153: /* R_analogcode_block: R_d_block  */
#line 1304 "vaYacc.y"
          {
            (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 3257 "vaYacc.cpp"
    break;

  case 154: /* R_analogcode_block: R_analogcode_block_atevent R_d_block  */
#line 1308 "vaYacc.y"
          {
            (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 3265 "vaYacc.cpp"
    break;

  case 155: /* R_analogcode_block_atevent: '@' '(' tk_ident '(' R_l_analysis ')' ')'  */
#line 1314 "vaYacc.y"
          {
              vaMessageError("@ control not supported\n",(yyvsp[-4]._lexval));
          }
#line 3273 "vaYacc.cpp"
    break;

  case 156: /* R_analogcode_block_atevent: '@' tk_ident  */
#line 1318 "vaYacc.y"
          {
              string tmp = (yyvsp[0]._lexval)->_str;
              //vaMessageError("@ control not supported\n",$2);
          }
#line 3282 "vaYacc.cpp"
    break;

  case 157: /* R_analogcode_block_atevent: '@' '(' tk_ident ')'  */
#line 1323 "vaYacc.y"
          {
              // @(initial_step) 等事件块：内联展开（块内语句无条件顺序执行）。
              // initial_step 语义为实例初始化，通常只做幂等的参数派生计算，
              // DC/瞬态每次 eval 重算结果一致。其他事件类型（cross/above 等）
              // 本编译器不支持，但块语句仍保留以便后续扩展。
              string tmp = (yyvsp[-1]._lexval)->_str;
          }
#line 3294 "vaYacc.cpp"
    break;

  case 158: /* R_l_analysis: R_s_analysis  */
#line 1333 "vaYacc.y"
          {
          }
#line 3301 "vaYacc.cpp"
    break;

  case 159: /* R_l_analysis: R_l_analysis ',' R_s_analysis  */
#line 1336 "vaYacc.y"
          {
          }
#line 3308 "vaYacc.cpp"
    break;

  case 160: /* R_s_analysis: tk_anystring  */
#line 1341 "vaYacc.y"
          {
          }
#line 3315 "vaYacc.cpp"
    break;

  case 161: /* R_d_block: R_d_block_begin tk_end  */
#line 1346 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
          }
#line 3323 "vaYacc.cpp"
    break;

  case 162: /* R_d_block: R_d_block_begin ':' tk_ident tk_end  */
#line 1350 "vaYacc.y"
          {
            (yyval._yaccval) = new yaccVal;
          }
#line 3331 "vaYacc.cpp"
    break;

  case 163: /* R_d_block: R_d_block_begin R_l_blockitem tk_end  */
#line 1354 "vaYacc.y"
          {
            (yyval._yaccval) = (yyvsp[-1]._yaccval);
          }
#line 3339 "vaYacc.cpp"
    break;

  case 164: /* $@2: %empty  */
#line 1358 "vaYacc.y"
          {
            // 进入命名块：建立局部作用域（块内 real 声明用唯一名，引用映射）
            gBlockNameStack.push_back((yyvsp[0]._lexval)->_str);
            gBlockLocalStack.push_back(map<string,string>());
          }
#line 3349 "vaYacc.cpp"
    break;

  case 165: /* R_d_block: R_d_block_begin ':' tk_ident $@2 R_l_blockitem tk_end  */
#line 1364 "vaYacc.y"
          {
            gBlockNameStack.pop_back();
            gBlockLocalStack.pop_back();
            (yyval._yaccval) = (yyvsp[-1]._yaccval);
          }
#line 3359 "vaYacc.cpp"
    break;

  case 166: /* R_d_block_begin: R_d_attribute_0 tk_begin  */
#line 1372 "vaYacc.y"
          {
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
          }
#line 3369 "vaYacc.cpp"
    break;

  case 167: /* R_l_blockitem: R_analogcode  */
#line 1380 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 3377 "vaYacc.cpp"
    break;

  case 168: /* R_l_blockitem: R_l_blockitem R_analogcode  */
#line 1384 "vaYacc.y"
          {
	    yaccVal * t1, *t2, *t3;
              (yyval._yaccval) = (yyvsp[-1]._yaccval);
	      t1 = (yyval._yaccval), t2 = (yyvsp[-1]._yaccval), t3 = (yyvsp[0]._yaccval);

	      if((yyvsp[0]._yaccval) != NULL && (yyvsp[0]._yaccval)->_state.size() != 0)
		{
		  list<statement>::iterator iter = (yyvsp[0]._yaccval)->_state.begin();
		  while(iter != (yyvsp[0]._yaccval)->_state.end()){
		    (yyval._yaccval)->_state.push_back(*iter);
		    ++iter;
		  }
		}

	      delete (yyvsp[0]._yaccval);
          }
#line 3398 "vaYacc.cpp"
    break;

  case 169: /* R_d_blockvariable: tk_integer R_l_blockvariable ';'  */
#line 1404 "vaYacc.y"
          {
	    (yyval._yaccval) = new yaccVal;
	    (yyval._yaccval)->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
#line 3409 "vaYacc.cpp"
    break;

  case 170: /* R_d_blockvariable: tk_real R_l_blockvariable ';'  */
#line 1411 "vaYacc.y"
          {
	    (yyval._yaccval) = new yaccVal;
	    (yyval._yaccval)->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
#line 3420 "vaYacc.cpp"
    break;

  case 171: /* R_d_blockvariable: tk_string R_l_blockvariable ';'  */
#line 1418 "vaYacc.y"
          {
	    (yyval._yaccval) = new yaccVal;
	    (yyval._yaccval)->_str = "";
	    blockvariable(gVariableList);
	    gVariableList.clear();
          }
#line 3431 "vaYacc.cpp"
    break;

  case 172: /* R_l_blockvariable: R_s_blockvariable  */
#line 1427 "vaYacc.y"
          {
          }
#line 3438 "vaYacc.cpp"
    break;

  case 173: /* R_l_blockvariable: R_l_blockvariable ',' R_s_blockvariable  */
#line 1430 "vaYacc.y"
          {
          }
#line 3445 "vaYacc.cpp"
    break;

  case 174: /* R_s_blockvariable: tk_ident  */
#line 1435 "vaYacc.y"
          {
              gVariableList.push_back((yyvsp[0]._lexval)->_str);
          }
#line 3453 "vaYacc.cpp"
    break;

  case 175: /* R_s_blockvariable: tk_ident '[' tk_number ':' tk_number ']'  */
#line 1439 "vaYacc.y"
          {
              vaMessageError("Array not support now.", (yyvsp[-5]._lexval));
          }
#line 3461 "vaYacc.cpp"
    break;

  case 176: /* R_d_contribution: R_contribution R_d_attribute_0 ';'  */
#line 1445 "vaYacc.y"
          {
              if(__attrList.size() != 0){
                __attrList.pop_back();
              }
              (yyval._yaccval) = (yyvsp[-2]._yaccval);
          }
#line 3472 "vaYacc.cpp"
    break;

  case 177: /* R_contribution: R_source '<' '+' R_s_expression  */
#line 1454 "vaYacc.y"
          {
              bitset<BIT_> tmp;
              statement mystat;
              mystat._describ = (((yyvsp[0]._yaccval)->_state).front())._describ;
              mystat._mode = 2;
              mystat._type = true;
              mystat._var = (((yyvsp[0]._yaccval)->_state).front())._var;
              mystat._param = (yyvsp[0]._yaccval)->_state.front()._param;
              if(gSource->_type == 0 || gSource->_type == 3){
                  // 噪声专用贡献（V(a,b) <+ white_noise(...)）：确定性分析下
                  // 无方程（不是 0V 源），整条跳过，不建伪网络。
                  if(mystat._describ == "0" && mystat._var.empty() && mystat._param.empty()){
                      (yyval._yaccval) = (yyvsp[-3]._yaccval);
                      delete (yyvsp[0]._yaccval);
                      gSource = NULL;
                  } else {
                  // ===== V(a,b) <+ expr / Temp 等电位贡献：解糖为 MNA 支路电流未知量 =====
                  // 伪网络 $br(pos,neg) 承载支路电流 Ibr：
                  //   KCL: f[pos] += Ibr, f[neg] -= Ibr
                  //   电压方程: f[brIdx] += (V(pos)-V(neg)) - expr
                  // expr 中的 I(a,b) 读取已被 access 规则映射为同一 Ibr。
                  int posNode = gSource->_pos;
                  int negNode = (gSource->_nodenum == 2) ? gSource->_neg : -1;
                  int brIdx = GetOrCreateBranchFlowNet(gModule, posNode, negNode);
                  string posName = gModule->_net[posNode]._name;
                  string negName = (negNode >= 0) ? gModule->_net[negNode]._name : "";
                  string brVar  = "V" + gModule->_net[brIdx]._name;
                  static int beqNum = 0;
                  string beqVar = "__beq" + int2string(beqNum++);

                  // 支路电压变量声明（若模型未曾读取）
                  bitset<BIT_> bitPos; bitPos[posNode] = 1;
                  gModule->_dervar["dV" + posName + "Dv" + int2string(posNode)] = posNode;
                  bitset<BIT_> bitNeg;
                  if(negNode >= 0){
                      bitNeg[negNode] = 1;
                      gModule->_dervar["dV" + negName + "Dv" + int2string(negNode)] = negNode;
                  }
                  bitset<BIT_> bitBr; bitBr[brIdx] = 1;
                  gModule->_dervar["d" + brVar + "Dv" + int2string(brIdx)] = brIdx;

                  // 依赖集合 = 支路两端电压 + RHS 依赖
                  bitset<BIT_> depBits = bitPos | bitNeg;
                  map<string, bitset<BIT_> >::iterator vit;
                  for(vit = mystat._var.begin(); vit != mystat._var.end(); ++vit)
                      depBits |= vit->second;

                  // (1) 赋值: __beq<N> = (V(pos) - V(neg)) - (expr);
                  statement beq;
                  beq._mode = 0;
                  beq._type = true;
                  if(negNode >= 0)
                      beq._describ = beqVar + " = (V" + posName + " - V" + negName + ") - (" + mystat._describ + ");";
                  else
                      beq._describ = beqVar + " = (V" + posName + ") - (" + mystat._describ + ");";
                  beq._var["V" + posName] = bitPos;
                  if(negNode >= 0) beq._var["V" + negName] = bitNeg;
                  for(vit = mystat._var.begin(); vit != mystat._var.end(); ++vit)
                      beq._var[vit->first] = vit->second;
                  beq._param = mystat._param;
                  // 模块变量与导数变量注册
                  variable beqv; beqv._name = beqVar; beqv._type = 2;
                  gModule->_variable.push_back(beqv);
                  for(int i = 0; i < BIT_; ++i)
                      if(depBits[i]) gModule->_tmpdervar["d" + beqVar + "Dv" + int2string(i)] = 1;

                  // (2) V 方程: I($br) <+ __beq<N>
                  statement veq;
                  veq._mode = 2;
                  veq._type = true;
                  veq._describ = beqVar;
                  veq._var[beqVar] = depBits;
                  veq._param = mystat._param;
                  source* srcVeq = new source;
                  srcVeq->_nodenum = 1;
                  srcVeq->_pos = brIdx;
                  srcVeq->_type = 1;
                  for(int i = 0; i < BIT_; ++i)
                      if(depBits[i]) gModule->_matstructrue[brIdx][i] = 1;
                  // 回退方程（Ibr=0）可能需要在未激活支路 stamp 对角元
                  gModule->_matstructrue[brIdx][brIdx] = 1;

                  // (3) KCL pos: I(pos) <+ Ibr
                  statement kclP;
                  kclP._mode = 2;
                  kclP._type = true;
                  kclP._describ = brVar;
                  kclP._var[brVar] = bitBr;
                  source* srcKclP = new source;
                  srcKclP->_nodenum = 1;
                  srcKclP->_pos = posNode;
                  srcKclP->_type = 1;
                  gModule->_matstructrue[posNode][brIdx] = 1;

                  (yyval._yaccval) = (yyvsp[-3]._yaccval);
                  ((yyval._yaccval)->_state).push_back(beq);
                  ((yyval._yaccval)->_state).push_back(veq);
                  ((yyval._yaccval)->_state).push_back(kclP);
                  gModule->_contribute.push_back(srcVeq);
                  gModule->_contribute.push_back(srcKclP);

                  // (4) KCL neg: I(neg) <+ -Ibr
                  if(negNode >= 0){
                      statement kclN;
                      kclN._mode = 2;
                      kclN._type = true;
                      kclN._describ = "(-" + brVar + ")";
                      kclN._var[brVar] = bitBr;
                      source* srcKclN = new source;
                      srcKclN->_nodenum = 1;
                      srcKclN->_pos = negNode;
                      srcKclN->_type = 1;
                      gModule->_matstructrue[negNode][brIdx] = 1;
                      ((yyval._yaccval)->_state).push_back(kclN);
                      gModule->_contribute.push_back(srcKclN);
                  }
                  delete (yyvsp[0]._yaccval);
                  gSource = NULL;
                  }  // end else (非噪声 V<+ 解糖)
              } else {
                  // ===== 电流/功率流贡献（原逻辑） =====
                  map<string, bitset<BIT_> >::iterator iter;
                  iter = mystat._var.begin();
                  while(iter != mystat._var.end()){
                      tmp |= iter->second;
                      ++iter;
                  }
                  for(int i=0; i<gModule->_net.size(); ++i){
                      if(tmp[i] != 0){
                          gModule->_matstructrue[gSource->_pos][i] = 1;
                          if(gSource->_nodenum == 2)
                              gModule->_matstructrue[gSource->_neg][i] = 1;
                      }
                  }
                  (yyval._yaccval) = (yyvsp[-3]._yaccval);
                  ((yyval._yaccval)->_state).push_back(mystat);
                  delete (yyvsp[0]._yaccval);
                  gModule->_contribute.push_back(gSource);
                  gSource = NULL;
              }
          }
#line 3618 "vaYacc.cpp"
    break;

  case 178: /* R_source: tk_ident '(' tk_ident ',' tk_ident ')'  */
#line 1598 "vaYacc.y"
          {
              int pos = -1, neg = -1;
              nature* tmp;
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = (yyvsp[-5]._lexval)->_str + "(" + (yyvsp[-3]._lexval)->_str + "," + (yyvsp[-1]._lexval)->_str + ")";
              string pname = (yyvsp[-3]._lexval)->_str, nname = (yyvsp[-1]._lexval)->_str;
              // branch 别名作为 source 实参 → 展开为 branch 节点
              map<string, branch>::iterator brIt = gModule->_branchAlias.find(pname);
              if(brIt != gModule->_branchAlias.end()){ pname = brIt->second._pnode; nname = brIt->second._nnode; }
              for(int i=0; i<gModule->_net.size(); ++i){
                  if(gModule->_net[i]._name == pname) pos = i;
                  else if(gModule->_net[i]._name == nname) neg = i;
              }
              if(pos == -1)
                  vaMessageError("first node not defined.", (yyvsp[-5]._lexval));
              if(neg == -1)
                  vaMessageError("second node not defined.", (yyvsp[-5]._lexval));
              tmp = IsInNature(__natureList, (yyvsp[-5]._lexval)->_str);
              if(tmp == NULL){
                  vaMessageError("Access not defined.", (yyvsp[-5]._lexval));
              } else {
                  gSource = new source;
                  gSource->_nodenum = 2;
                  gSource->_pos = pos;
                  gSource->_neg = neg;
                  if(tmp->_name == "Voltage"){
                      gSource->_type = 0;
                  } else if(tmp->_name == "Current"){
                      gSource->_type = 1;
                  } else if(tmp->_name == "Power")
		    {
		      gSource->_type = 2;
		    } else if(tmp->_name == "Temperature")
		    {
		      gSource->_type = 3;
		    } else {
                      vaMessageError("contrubite source must be Voltage or Current.", (yyvsp[-5]._lexval));
                  }
              }
          }
#line 3663 "vaYacc.cpp"
    break;

  case 179: /* R_source: tk_ident '(' tk_ident ')'  */
#line 1639 "vaYacc.y"
          {
              int pos = -1, neg = -1;
              nature* tmp;
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = (yyvsp[-3]._lexval)->_str + "(" + (yyvsp[-1]._lexval)->_str + ")";
              string pname = (yyvsp[-1]._lexval)->_str, nname;
              bool twoNodeBranch = false;
              // branch 别名（单节点 source 实参）→ branch 节点；
              // 双节点 branch（如 I(br_a_ci)）恢复 nodenum=2 的 KCL 对侧 stamp
              map<string, branch>::iterator brIt = gModule->_branchAlias.find(pname);
              if(brIt != gModule->_branchAlias.end()){
                  pname = brIt->second._pnode;
                  if(brIt->second._type == 2){ nname = brIt->second._nnode; twoNodeBranch = true; }
              }
              for(int i=0; i<gModule->_net.size(); ++i){
                  if(gModule->_net[i]._name == pname) pos = i;
                  if(twoNodeBranch && gModule->_net[i]._name == nname) neg = i;
              }
              if(pos == -1)
                  vaMessageError("Node not defined.", (yyvsp[-3]._lexval));
              if(twoNodeBranch && neg == -1)
                  vaMessageError("Node not defined.", (yyvsp[-3]._lexval));
              tmp = IsInNature(__natureList, (yyvsp[-3]._lexval)->_str);
              if(tmp == NULL){
                  vaMessageError("Access not defined.", (yyvsp[-3]._lexval));
              } else {
                  gSource = new source;
                  gSource->_nodenum = twoNodeBranch ? 2 : 1;
                  gSource->_pos = pos;
                  if(twoNodeBranch) gSource->_neg = neg;
                  if(tmp->_name == "Voltage"){
                      gSource->_type = 0;
                  } else if(tmp->_name == "Current"){
                      gSource->_type = 1;
                  }
		   else if(tmp->_name == "Power")
		    {
		      gSource->_type = 2;
		    } else if(tmp->_name == "Temperature")
		    {
		      gSource->_type = 3;
		    } else{
                      vaMessageError("contrubite source must be Voltage or Current.", (yyvsp[-3]._lexval));
                  }
              }
          }
#line 3714 "vaYacc.cpp"
    break;

  case 180: /* R_d_while: tk_while '(' R_s_expression ')' R_analogcode  */
#line 1688 "vaYacc.y"
          {
	    //              cout<<"Warning: while loop detected.\n";
	      (yyval._yaccval) = new yaccVal;
              statement mystat;
              mystat._describ = "while(" + (yyvsp[-2]._yaccval)->_state.front()._describ + "){";
              mystat._mode = 0;
              mystat._type = false;
              map<string, int>::iterator piter;
              piter = (yyvsp[-2]._yaccval)->_state.front()._param.begin();
              while(piter != (yyvsp[-2]._yaccval)->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              (yyval._yaccval)->_state.push_back(mystat);
              list<statement>::iterator iter;
              iter = (yyvsp[0]._yaccval)->_state.begin();
              while(iter != (yyvsp[0]._yaccval)->_state.end()){
                  if(iter->_var.size() != 0){
                      cout<<(++(iter->_var.begin()))->first<<(++(iter->_var.begin()))->second<<"\t"<<iter->_var.size()<<endl;
                      vaMessageError("The expression under \"for\" loop must indepent to Voltages.\n", (yyvsp[-4]._lexval));
                  }
                  //iter->_describ += ";";
                  (yyval._yaccval)->_state.push_back(*iter);
                  ++iter;
              }
              mystat._describ = "}";
              (yyval._yaccval)->_state.push_back(mystat);
              delete (yyvsp[-4]._lexval);
              delete (yyvsp[-2]._yaccval);
              delete (yyvsp[0]._yaccval);
          }
#line 3750 "vaYacc.cpp"
    break;

  case 181: /* R_d_for: tk_for '(' R_s_assignment ';' R_s_expression ';' R_s_assignment ')' R_analogcode  */
#line 1722 "vaYacc.y"
          {
              //cout<<"Warning: for loop detected.\n";
              (yyval._yaccval) = new yaccVal;
              statement mystat;
              mystat._describ = "for(" + (yyvsp[-6]._yaccval)->_state.front()._describ + "; " +
                  (yyvsp[-4]._yaccval)->_state.front()._describ + "; " + (yyvsp[-2]._yaccval)->_state.front()._describ + "){";
              mystat._param = (yyvsp[-6]._yaccval)->_state.front()._param;
              mystat._mode = 0;
              mystat._type = false;
              map<string, int>::iterator piter;
              piter = (yyvsp[-4]._yaccval)->_state.front()._param.begin();
              while(piter != (yyvsp[-4]._yaccval)->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              piter = (yyvsp[-2]._yaccval)->_state.front()._param.begin();
              while(piter != (yyvsp[-2]._yaccval)->_state.front()._param.end()){
                  mystat._param[piter->first] = piter->second;
                  ++piter;
              }
              (yyval._yaccval)->_state.push_back(mystat);
              list<statement>::iterator iter;
              iter = (yyvsp[0]._yaccval)->_state.begin();
              while(iter != (yyvsp[0]._yaccval)->_state.end()){
                  if(iter->_var.size() != 0){
                      cout<<(++(iter->_var.begin()))->first<<(++(iter->_var.begin()))->second<<"\t"<<iter->_var.size()<<endl;
                      vaMessageError("The expression under \"for\" loop must indepent to Voltages.\n", (yyvsp[-8]._lexval));
                  }
                  //iter->_describ += ";";
                  (yyval._yaccval)->_state.push_back(*iter);
                  ++iter;
              }
              mystat._describ = "}";
              (yyval._yaccval)->_state.push_back(mystat);
              delete (yyvsp[-8]._lexval);
              delete (yyvsp[-6]._yaccval);
              delete (yyvsp[-4]._yaccval);
              delete (yyvsp[-2]._yaccval);
              delete (yyvsp[0]._yaccval);
          }
#line 3795 "vaYacc.cpp"
    break;

  case 182: /* $@3: %empty  */
#line 1765 "vaYacc.y"
          {
            // 进入新 case：压栈（嵌套 case 互不干扰），flag 复位
            gCaseStack.push_back(new list<yaccVal*>());
            gCaseFlagStack.push_back(gCaseFlag);
            gCaseFlag = 0;
          }
#line 3806 "vaYacc.cpp"
    break;

  case 183: /* R_d_case: tk_case '(' R_s_expression ')' $@3 R_l_case_item tk_endcase  */
#line 1772 "vaYacc.y"
          {
	    // handle the cases here. calculate the derivations here.
	    list<yaccVal*>::iterator iter;
	    list<yaccVal*>* myCases = gCaseStack.back();
	    gCaseStack.pop_back();
	    gCaseFlag = gCaseFlagStack.back();
	    gCaseFlagStack.pop_back();
	    int numcases = myCases->size();

	    map<string, bitset<BIT_> >::iterator bit_iter;
	    vector<map<string, bitset<BIT_> > > inside;

	    SwitchBlockVariable(gModule, gOutsideZero, inside, numcases);

	    if(inside.size() != numcases)
	      {
		vaMessageError("Case syntax error.\n", (yyvsp[-6]._lexval));
	      }

	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    (yyval._yaccval) = new yaccVal;
	    mystat._describ = "switch(" + ((yyvsp[-4]._yaccval)->_state.front())._describ + "){";
	    mystat._param = (yyvsp[-4]._yaccval)->_state.front()._param;
	    (yyval._yaccval)->_state.push_back(mystat);
	    mystat._param.clear();

	    int caseno = 0;
	    list<statement>::iterator state_iter;
	    // all the cases
	    for(iter = myCases->begin(); iter != myCases->end(); ++iter)
	      {
		state_iter = (*iter)->_state.begin();
		while(state_iter != (*iter)->_state.end())
		  {
		    (yyval._yaccval)->_state.push_back(*state_iter);
		    state_iter++;
		  }

		bit_iter = inside[caseno].begin();
		mystat._mode = 4;
		while(bit_iter != inside[caseno].end())
		  {
		    mystat._describ = GetZeroDerivation(bit_iter->first, bit_iter->second);
		    (yyval._yaccval)->_state.push_back(mystat);
		    ++bit_iter;
		  }

		mystat._mode = 0;
		mystat._describ = "break;";
		(yyval._yaccval)->_state.push_back(mystat);
		
		++caseno;
	      }
	    

	    mystat._mode = 0;
	    mystat._describ = "}";
	    (yyval._yaccval)->_state.push_back(mystat);

	    // clear all the cases
	    for(iter = myCases->begin(); iter != myCases->end(); ++iter)
	      delete *iter;

	    myCases->clear();
	    delete myCases;

	    delete (yyvsp[-4]._yaccval);
          }
#line 3881 "vaYacc.cpp"
    break;

  case 184: /* R_l_case_item: R_s_case_item  */
#line 1845 "vaYacc.y"
          {
	    //    $$ = $1;
	    gCaseStack.back()->push_back((yyvsp[0]._yaccval));
          }
#line 3890 "vaYacc.cpp"
    break;

  case 185: /* R_l_case_item: R_l_case_item R_s_case_item  */
#line 1850 "vaYacc.y"
          {
	    //  ($$->_state).push_back(($2->_state).front());
	    //  delete $2;
	    gCaseStack.back()->push_back((yyvsp[0]._yaccval));
          }
#line 3900 "vaYacc.cpp"
    break;

  case 186: /* R_s_case_item: R_l_expression ':' R_analogcode  */
#line 1858 "vaYacc.y"
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    (yyval._yaccval) = new yaccVal;
	    mystat._describ = "case " + ((yyvsp[-2]._yaccval)->_state.front())._describ + ":";
	    mystat._param = (yyvsp[0]._yaccval)->_state.front()._param;
	    (yyval._yaccval)->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = (yyvsp[0]._yaccval)->_state.begin();
	    while(it != (yyvsp[0]._yaccval)->_state.end()) {
	      (yyval._yaccval)->_state.push_back(*it);
	      ++it;
	    }
	    
          }
#line 3933 "vaYacc.cpp"
    break;

  case 187: /* R_s_case_item: tk_default ':' R_analogcode  */
#line 1887 "vaYacc.y"
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    (yyval._yaccval) = new yaccVal;
	    mystat._describ = "default:";
	    mystat._param = (yyvsp[0]._yaccval)->_state.front()._param;
	    (yyval._yaccval)->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = (yyvsp[0]._yaccval)->_state.begin();
	    while(it != (yyvsp[0]._yaccval)->_state.end()) {
	      (yyval._yaccval)->_state.push_back(*it);
	      ++it;
	    }
          }
#line 3965 "vaYacc.cpp"
    break;

  case 188: /* R_s_case_item: tk_default R_analogcode  */
#line 1915 "vaYacc.y"
          {
	    if(gCaseFlag == 0)
	      {
		NewIfVariableBlock(gModule);
		gCaseFlag = 1;
	      }
	    else
	      {
		NewElseVariableBlock(gModule);
	      }
	    
	    // only insert the necessary code; leave the derivations to the full case handler
	    statement mystat;
	    mystat._mode = 0;
	    mystat._type = false;
	    (yyval._yaccval) = new yaccVal;
	    mystat._describ = "default:";
	    mystat._param = (yyvsp[0]._yaccval)->_state.front()._param;
	    (yyval._yaccval)->_state.push_back(mystat);
	    mystat._param.clear();

	    list<statement>::iterator it;
	    it = (yyvsp[0]._yaccval)->_state.begin();
	    while(it != (yyvsp[0]._yaccval)->_state.end()) {
	      (yyval._yaccval)->_state.push_back(*it);
	      ++it;
	    }
          }
#line 3998 "vaYacc.cpp"
    break;

  case 189: /* R_s_instance: R_instance_module_name '#' '(' R_l_instance_parameter ')' tk_ident '(' R_l_node ')' ';'  */
#line 1946 "vaYacc.y"
          {
          }
#line 4005 "vaYacc.cpp"
    break;

  case 190: /* R_instance_module_name: tk_ident  */
#line 1951 "vaYacc.y"
          {
              vaMessageError("instance module not support now.", (yyvsp[0]._lexval));
          }
#line 4013 "vaYacc.cpp"
    break;

  case 191: /* R_l_instance_parameter: R_s_instance_parameter  */
#line 1957 "vaYacc.y"
          {
          }
#line 4020 "vaYacc.cpp"
    break;

  case 192: /* R_l_instance_parameter: R_l_instance_parameter ',' R_s_instance_parameter  */
#line 1960 "vaYacc.y"
          {
          }
#line 4027 "vaYacc.cpp"
    break;

  case 193: /* R_s_instance_parameter: '_' tk_ident '(' R_s_expression ')'  */
#line 1965 "vaYacc.y"
          {
          }
#line 4034 "vaYacc.cpp"
    break;

  case 194: /* R_s_assignment: R_s_assignment_name '=' R_s_expression  */
#line 1970 "vaYacc.y"
          {
              string dvarname;
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              (yyval._yaccval)->_str = (yyvsp[-2]._yaccval)->_str;
              ((yyval._yaccval)->_state.front())._describ = (yyvsp[-2]._yaccval)->_str + " = " + ((yyval._yaccval)->_state.front())._describ;
              bitset<BIT_> tmpbit;
              map<string, bitset<BIT_> >::iterator iter;
              iter = (yyvsp[0]._yaccval)->_state.front()._var.begin();
              while(iter != (yyvsp[0]._yaccval)->_state.front()._var.end()){
                  tmpbit = tmpbit | iter->second;
                  ++iter;
              }
              ((yyval._yaccval)->_state.front())._mode = 0;
              if(tmpbit != 0){
                  (yyval._yaccval)->_state.front()._type = true;
                  for(int i=0; i<gModule->_net.size(); ++i){
                      dvarname = "d" + (yyvsp[-2]._yaccval)->_str + "Dv" + int2string(i);
                      if(tmpbit[i] != 0) gModule->_tmpdervar[dvarname] = 1;
                  }
                  //SetVariableType(gModule, $1->_str, tmpbit);
              } else {
                  (yyval._yaccval)->_state.front()._type = false;
              }
              SetVariableType(gModule, (yyvsp[-2]._yaccval)->_str, tmpbit);
              delete (yyvsp[-2]._yaccval);
          }
#line 4065 "vaYacc.cpp"
    break;

  case 195: /* R_s_assignment: R_d_attribute R_s_assignment_name '=' R_s_expression  */
#line 1997 "vaYacc.y"
          {
              __attrList.pop_back();
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              (yyval._yaccval)->_str = (yyvsp[-2]._yaccval)->_str;
              ((yyval._yaccval)->_state.front())._describ = (yyvsp[-2]._yaccval)->_str + " = " + ((yyval._yaccval)->_state.front())._describ;
              SetVariableType(gModule, (yyvsp[-3]._yaccval)->_str, (yyval._yaccval)->_type);
          }
#line 4077 "vaYacc.cpp"
    break;

  case 196: /* R_s_assignment: R_s_assignment_name '[' R_expression ']' '=' R_s_expression  */
#line 2005 "vaYacc.y"
          {
              vaMessageError("Array not support now.", (yyvsp[-5]._yaccval));
          }
#line 4085 "vaYacc.cpp"
    break;

  case 197: /* R_s_assignment_name: tk_ident  */
#line 2011 "vaYacc.y"
          {
              (yyval._yaccval) = new yaccVal;
              // 命名块局部变量 LHS 解析（delta → delta__b3）
              string blk = ResolveBlockLocal((yyvsp[0]._lexval)->_str);
              (yyval._yaccval)->_str = blk.empty() ? (yyvsp[0]._lexval)->_str : blk;
          }
#line 4096 "vaYacc.cpp"
    break;

  case 198: /* R_d_conditional: tk_if '(' R_s_expression ')' R_analogcode  */
#line 2020 "vaYacc.y"
          {
              statement mystat;
              mystat._mode = 0;
              mystat._type = false;
              (yyval._yaccval) = new yaccVal;
              mystat._describ = "if(" + ((yyvsp[-2]._yaccval)->_state.front())._describ + "){";
              mystat._param = (yyvsp[-2]._yaccval)->_state.front()._param;
              (yyval._yaccval)->_state.push_back(mystat);
              mystat._param.clear();
              list<statement>::iterator it;
              it = (yyvsp[0]._yaccval)->_state.begin();
              while(it != (yyvsp[0]._yaccval)->_state.end()){
                  (yyval._yaccval)->_state.push_back(*it);
                  ++it;
              }
              map<string, bitset<BIT_> >  inside;
              IfBlockVariable(gModule, gOutsideZero, inside);
              map<string, bitset<BIT_> >::iterator iter;
              mystat._mode = 4;
              iter = inside.begin();
              while(iter != inside.end()){
                mystat._describ = GetZeroDerivation(iter->first, iter->second);
                (yyval._yaccval)->_state.push_back(mystat);
                ++iter;
              }
              mystat._mode = 0;
              mystat._describ = "}";
              (yyval._yaccval)->_state.push_back(mystat);
              delete (yyvsp[-2]._yaccval);
              delete (yyvsp[0]._yaccval);
          }
#line 4132 "vaYacc.cpp"
    break;

  case 199: /* R_d_conditional: tk_if '(' R_s_expression ')' R_analogcode tk_else R_analogcode  */
#line 2052 "vaYacc.y"
          {

	    yaccVal *t1, *t2, *t3;
	    t1 = (yyvsp[-4]._yaccval); t2 = (yyvsp[-2]._yaccval); t3 = (yyvsp[0]._yaccval);
	    
            vector<map<string, bitset<BIT_> > > inside;
            map<string, bitset<BIT_> > insideif, insideelse;
            map<string, bitset<BIT_> >::iterator iter;
            SwitchBlockVariable(gModule, gOutsideZero, inside, 2);
            if(inside.size() != 2){
              vaMessageError("Error while deal with if-else statement.\n", (yyvsp[-6]._lexval));
            } else {
              insideif = inside[0];
              insideelse = inside[1];
            }
            statement mystat;
            mystat._mode = 0;
            mystat._type = false;
            (yyval._yaccval) = new yaccVal;
            mystat._describ = "if(" + ((yyvsp[-4]._yaccval)->_state.front())._describ + "){";
            mystat._param = (yyvsp[-4]._yaccval)->_state.front()._param;
            (yyval._yaccval)->_state.push_back(mystat);
            mystat._param.clear();
            mystat._mode = 4;
            list<statement>::iterator it;
            it = (yyvsp[-2]._yaccval)->_state.begin();
            while(it != (yyvsp[-2]._yaccval)->_state.end()){
              (yyval._yaccval)->_state.push_back(*it);
              ++it;
            }
            iter = insideif.begin();
            while(iter != insideif.end()){
              mystat._describ = GetZeroDerivation(iter->first, iter->second);
              (yyval._yaccval)->_state.push_back(mystat);
              ++iter;
            }
            mystat._describ = "} else {";
            mystat._mode = 0;
            (yyval._yaccval)->_state.push_back(mystat);
            mystat._mode = 4;
            it = (yyvsp[0]._yaccval)->_state.begin();
            while(it != (yyvsp[0]._yaccval)->_state.end()){
              (yyval._yaccval)->_state.push_back(*it);
              ++it;
            }
            iter = insideelse.begin();
            while(iter != insideelse.end()){
              mystat._describ = GetZeroDerivation(iter->first, iter->second);
              (yyval._yaccval)->_state.push_back(mystat);
              ++iter;
            }
            mystat._describ = "}";
            mystat._mode = 0;
            (yyval._yaccval)->_state.push_back(mystat);
            delete (yyvsp[-4]._yaccval);
            delete (yyvsp[-2]._yaccval);
            delete (yyvsp[0]._yaccval);
          }
#line 4195 "vaYacc.cpp"
    break;

  case 200: /* R_s_expression: R_expression  */
#line 2113 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 4203 "vaYacc.cpp"
    break;

  case 201: /* R_l_callfunction_expression: R_s_expression  */
#line 2119 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              (yyval._yaccval)->_num = 1;
          }
#line 4212 "vaYacc.cpp"
    break;

  case 202: /* R_l_callfunction_expression: R_l_callfunction_expression ',' R_s_expression  */
#line 2124 "vaYacc.y"
          {
              ((yyval._yaccval)->_state).push_back(((yyvsp[0]._yaccval)->_state).front());
              (yyval._yaccval)->_num += 1;
              delete (yyvsp[0]._yaccval);
          }
#line 4222 "vaYacc.cpp"
    break;

  case 203: /* R_l_expression: R_s_function_expression  */
#line 2132 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              (yyval._yaccval)->_num = 1;
          }
#line 4231 "vaYacc.cpp"
    break;

  case 204: /* R_l_expression: R_l_expression ',' R_s_function_expression  */
#line 2137 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[-2]._yaccval);
              ((yyval._yaccval)->_state).push_back(((yyvsp[0]._yaccval)->_state).front());
              delete (yyvsp[0]._yaccval);
              (yyval._yaccval)->_num += 1;
          }
#line 4242 "vaYacc.cpp"
    break;

  case 205: /* R_s_function_expression: R_expression  */
#line 2146 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4250 "vaYacc.cpp"
    break;

  case 206: /* R_expression: R_e_conditional  */
#line 2152 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4258 "vaYacc.cpp"
    break;

  case 207: /* R_e_conditional: R_e_bitwise_equ  */
#line 2158 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4266 "vaYacc.cpp"
    break;

  case 208: /* R_e_conditional: R_e_bitwise_equ '?' R_e_bitwise_equ ':' R_e_bitwise_equ  */
#line 2162 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[-4]._yaccval);
              statement &tmp = ((yyval._yaccval)->_state).front();
              statement &tmp1 = ((yyvsp[-2]._yaccval)->_state).front();
              statement &tmp2 = ((yyvsp[0]._yaccval)->_state).front();
              tmp._describ += "?" + tmp1._describ + " : " + tmp2._describ;
              (yyval._yaccval)->_type = (yyvsp[0]._yaccval)->_type | (yyvsp[-2]._yaccval)->_type;
              map<string, bitset<BIT_> >::iterator iter;
              iter = tmp1._var.begin();
              (tmp._var).clear();
              while(iter != tmp1._var.end()){
                  tmp._var[iter->first] = iter->second;
                  ++iter;
              }
              iter = tmp2._var.begin();
              while(iter != tmp2._var.end()){
                  tmp._var[iter->first] = iter->second;
                  ++iter;
              }
              map<string, int>::iterator pit;
              pit = tmp1._param.begin();
              while(pit != tmp1._param.end()){
                  tmp._param[pit->first] = pit->second;
                  ++pit;
              }
              pit = tmp2._param.begin();
              while(pit != tmp2._param.end()){
                  tmp._param[pit->first] = pit->second;
                  ++pit;
              }
              delete (yyvsp[-2]._yaccval);
              delete (yyvsp[0]._yaccval);
          }
#line 4304 "vaYacc.cpp"
    break;

  case 209: /* R_e_bitwise_equ: R_e_bitwise_xor  */
#line 2200 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 4312 "vaYacc.cpp"
    break;

  case 210: /* R_e_bitwise_equ: R_e_bitwise_equ tk_bitwise_equr R_e_bitwise_xor  */
#line 2204 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "^~");
          }
#line 4320 "vaYacc.cpp"
    break;

  case 211: /* R_e_bitwise_equ: R_e_bitwise_equ '~' '^' R_e_bitwise_xor  */
#line 2208 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-3]._yaccval), (yyvsp[0]._yaccval), "~^");
          }
#line 4328 "vaYacc.cpp"
    break;

  case 212: /* R_e_bitwise_xor: R_e_bitwise_or  */
#line 2214 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4336 "vaYacc.cpp"
    break;

  case 213: /* R_e_bitwise_xor: R_e_bitwise_xor '^' R_e_bitwise_or  */
#line 2218 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "^");
          }
#line 4344 "vaYacc.cpp"
    break;

  case 214: /* R_e_bitwise_or: R_e_bitwise_and  */
#line 2224 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4352 "vaYacc.cpp"
    break;

  case 215: /* R_e_bitwise_or: R_e_bitwise_or '|' R_e_bitwise_and  */
#line 2228 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "|");
          }
#line 4360 "vaYacc.cpp"
    break;

  case 216: /* R_e_bitwise_and: R_e_logical_or  */
#line 2234 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4368 "vaYacc.cpp"
    break;

  case 217: /* R_e_bitwise_and: R_e_bitwise_and '&' R_e_logical_or  */
#line 2238 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "&");
          }
#line 4376 "vaYacc.cpp"
    break;

  case 218: /* R_e_logical_or: R_e_logical_and  */
#line 2244 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4384 "vaYacc.cpp"
    break;

  case 219: /* R_e_logical_or: R_e_logical_or tk_or R_e_logical_and  */
#line 2248 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "||");
          }
#line 4392 "vaYacc.cpp"
    break;

  case 220: /* R_e_logical_and: R_e_comp_equ  */
#line 2254 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4400 "vaYacc.cpp"
    break;

  case 221: /* R_e_logical_and: R_e_logical_and tk_and R_e_comp_equ  */
#line 2258 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "&&");
          }
#line 4408 "vaYacc.cpp"
    break;

  case 222: /* R_e_comp_equ: R_e_comp  */
#line 2264 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4416 "vaYacc.cpp"
    break;

  case 223: /* R_e_comp_equ: R_e_comp_equ '=' '=' R_e_comp  */
#line 2268 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-3]._yaccval), (yyvsp[0]._yaccval), "==");
          }
#line 4424 "vaYacc.cpp"
    break;

  case 224: /* R_e_comp_equ: R_e_comp_equ '!' '=' R_e_comp  */
#line 2272 "vaYacc.y"
          {
             R_e_bitwise((yyval._yaccval), (yyvsp[-3]._yaccval), (yyvsp[0]._yaccval), "!=");
          }
#line 4432 "vaYacc.cpp"
    break;

  case 225: /* R_e_comp: R_e_bitwise_shift  */
#line 2278 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4440 "vaYacc.cpp"
    break;

  case 226: /* R_e_comp: R_e_comp '<' R_e_bitwise_shift  */
#line 2282 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "<");
          }
#line 4448 "vaYacc.cpp"
    break;

  case 227: /* R_e_comp: R_e_comp '<' '=' R_e_bitwise_shift  */
#line 2286 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-3]._yaccval), (yyvsp[0]._yaccval), "<=");
          }
#line 4456 "vaYacc.cpp"
    break;

  case 228: /* R_e_comp: R_e_comp '>' R_e_bitwise_shift  */
#line 2290 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), ">");
          }
#line 4464 "vaYacc.cpp"
    break;

  case 229: /* R_e_comp: R_e_comp '>' '=' R_e_bitwise_shift  */
#line 2294 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-3]._yaccval), (yyvsp[0]._yaccval), ">=");
          }
#line 4472 "vaYacc.cpp"
    break;

  case 230: /* R_e_bitwise_shift: R_e_arithm_add  */
#line 2300 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4480 "vaYacc.cpp"
    break;

  case 231: /* R_e_bitwise_shift: R_e_bitwise_shift tk_op_shr R_e_arithm_add  */
#line 2304 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), ">>");
          }
#line 4488 "vaYacc.cpp"
    break;

  case 232: /* R_e_bitwise_shift: R_e_bitwise_shift tk_op_shl R_e_arithm_add  */
#line 2308 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "<<");
          }
#line 4496 "vaYacc.cpp"
    break;

  case 233: /* R_e_arithm_add: R_e_arithm_mult  */
#line 2314 "vaYacc.y"
          {
            (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4504 "vaYacc.cpp"
    break;

  case 234: /* R_e_arithm_add: R_e_arithm_add '+' R_e_arithm_mult  */
#line 2318 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "+");
          }
#line 4512 "vaYacc.cpp"
    break;

  case 235: /* R_e_arithm_add: R_e_arithm_add '-' R_e_arithm_mult  */
#line 2322 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "-");
          }
#line 4520 "vaYacc.cpp"
    break;

  case 236: /* R_e_arithm_mult: R_e_unary  */
#line 2328 "vaYacc.y"
          {
              (yyval._yaccval)=(yyvsp[0]._yaccval);
          }
#line 4528 "vaYacc.cpp"
    break;

  case 237: /* R_e_arithm_mult: R_e_arithm_mult '*' R_e_unary  */
#line 2332 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "*");
          }
#line 4536 "vaYacc.cpp"
    break;

  case 238: /* R_e_arithm_mult: R_e_arithm_mult '/' R_e_unary  */
#line 2336 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "/");
          }
#line 4544 "vaYacc.cpp"
    break;

  case 239: /* R_e_arithm_mult: R_e_arithm_mult '%' R_e_unary  */
#line 2340 "vaYacc.y"
          {
              R_e_bitwise((yyval._yaccval), (yyvsp[-2]._yaccval), (yyvsp[0]._yaccval), "%");
          }
#line 4552 "vaYacc.cpp"
    break;

  case 240: /* R_e_unary: R_e_atomic  */
#line 2346 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 4560 "vaYacc.cpp"
    break;

  case 241: /* R_e_unary: '+' R_e_unary  */
#line 2350 "vaYacc.y"
          {
              (yyval._yaccval) = (yyvsp[0]._yaccval);
          }
#line 4568 "vaYacc.cpp"
    break;

  case 242: /* R_e_unary: '-' R_e_unary  */
#line 2354 "vaYacc.y"
          {
              // 递归单目：支持 `- -x`（宏展开 `-`MACRO 产生的双负号）
              (yyval._yaccval) = (yyvsp[0]._yaccval);
              (yyval._yaccval)->_value = -((yyval._yaccval)->_value);
              (((yyval._yaccval)->_state).front())._describ = "(-" + (((yyval._yaccval)->_state).front())._describ + ")";
          }
#line 4579 "vaYacc.cpp"
    break;

  case 243: /* R_e_unary: '!' R_e_atomic  */
#line 2361 "vaYacc.y"
          {
	    (yyval._yaccval) = (yyvsp[0]._yaccval);
	    (((yyval._yaccval)->_state).front())._describ = "(!(" + (((yyval._yaccval)->_state).front())._describ + "))";
	    //              vaMessageError("Unsupport !", $2);
          }
#line 4589 "vaYacc.cpp"
    break;

  case 244: /* R_e_unary: '~' R_e_atomic  */
#line 2367 "vaYacc.y"
          {
              vaMessageError("Unsupport ~", (yyvsp[0]._yaccval));
          }
#line 4597 "vaYacc.cpp"
    break;

  case 245: /* R_e_atomic: tk_number  */
#line 2373 "vaYacc.y"
          {
              statement mystat;
              mystat._describ = (yyvsp[0]._lexval)->_str;
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_value = string2double((yyvsp[0]._lexval)->_str);
              ((yyval._yaccval)->_state).push_back(mystat);
          }
#line 4609 "vaYacc.cpp"
    break;

  case 246: /* R_e_atomic: tk_number tk_ident  */
#line 2381 "vaYacc.y"
          {
              string myunit;
              if(0) { }
              else if(((yyvsp[0]._lexval)->_str == "E")) myunit = "1e18";
              else if(((yyvsp[0]._lexval)->_str == "P")) myunit = "1e15";
              else if(((yyvsp[0]._lexval)->_str == "T")) myunit = "1e12";
              else if(((yyvsp[0]._lexval)->_str == "G")) myunit = "1e9";
              else if(((yyvsp[0]._lexval)->_str == "M")) myunit = "1e6";
              else if(((yyvsp[0]._lexval)->_str == "k")) myunit = "1e3";
              else if(((yyvsp[0]._lexval)->_str == "h")) myunit = "100";
              else if(((yyvsp[0]._lexval)->_str == "D")) myunit = "10";
              else if(((yyvsp[0]._lexval)->_str == "d")) myunit = "0.1";
              else if(((yyvsp[0]._lexval)->_str == "c")) myunit = "0.01";
              else if(((yyvsp[0]._lexval)->_str == "m")) myunit = "1e-3";
              else if(((yyvsp[0]._lexval)->_str == "u")) myunit = "1e-6";
              else if(((yyvsp[0]._lexval)->_str == "n")) myunit = "1e-9";
              else if(((yyvsp[0]._lexval)->_str == "A")) myunit = "1e-10";
              else if(((yyvsp[0]._lexval)->_str == "p")) myunit = "1e-12";
              else if(((yyvsp[0]._lexval)->_str == "f")) myunit = "1e-15";
              else if(((yyvsp[0]._lexval)->_str == "a")) myunit = "1e-18";
              else
                  vaMessageError("can not convert symbol to valid unit\n",(yyvsp[0]._lexval));
              statement mystat;
              mystat._describ = (yyvsp[-1]._lexval)->_str + "*" + myunit;
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_value = string2double((yyvsp[-1]._lexval)->_str) * string2double(myunit);
              ((yyval._yaccval)->_state).push_back(mystat);
          }
#line 4642 "vaYacc.cpp"
    break;

  case 247: /* R_e_atomic: tk_char  */
#line 2410 "vaYacc.y"
          {
            vaMessageError("%s: character are not handled\n",(yyvsp[0]._lexval));
          }
#line 4650 "vaYacc.cpp"
    break;

  case 248: /* R_e_atomic: tk_anystring  */
#line 2414 "vaYacc.y"
          {
              statement mystat;
              mystat._describ = "\"" + (yyvsp[0]._lexval)->_str + "\"";
              (yyval._yaccval) = new yaccVal;
              (yyval._yaccval)->_str = (yyvsp[0]._lexval)->_str;
              (yyval._yaccval)->_state.push_back(mystat);
          }
#line 4662 "vaYacc.cpp"
    break;

  case 249: /* R_e_atomic: tk_ident  */
#line 2422 "vaYacc.y"
          {
              (yyval._yaccval) = new yaccVal;
              statement mystat;
              parameter *mypar;
              int typ;
              bitset<BIT_> mytype;
              if(gAnalogfunction)
              {
                  // 函数体内标识符：先查形参/局部变量（电压无关），
                  // 再查模块变量与参数（如模型参数引用）
                  if(gAnalogfunction->_var.count((yyvsp[0]._lexval)->_str)){
                      mystat._describ = (yyvsp[0]._lexval)->_str;
                  } else if(IsModuleVariable(gModule, (yyvsp[0]._lexval)->_str)){
                      mystat._describ = (yyvsp[0]._lexval)->_str;
                      mytype = GetVariableType(gModule, (yyvsp[0]._lexval)->_str);
                      if(mytype != 0) (mystat._var)[(yyvsp[0]._lexval)->_str] = mytype;
                  } else if(mypar = IsInParam(gModule, (yyvsp[0]._lexval)->_str)) {
                      mystat._describ = (yyvsp[0]._lexval)->_str;
                      if(mypar->_type == 1) typ = 1;
                      else typ = 0;
                      mystat._param[(yyvsp[0]._lexval)->_str] = typ;
                  } else {
                      vaMessageError("identifier never declared",(yyvsp[0]._lexval));
                  }
              }
              else
              {
                  // 命名块局部变量优先（内层块遮蔽外层）
                  string blk = ResolveBlockLocal((yyvsp[0]._lexval)->_str);
                  if (!blk.empty()) {
                      mystat._describ = blk;
                      mytype = GetVariableType(gModule, blk);
                      if (mytype != 0) (mystat._var)[blk] = mytype;
                  } else if(IsModuleVariable(gModule, (yyvsp[0]._lexval)->_str)){
                      mystat._describ = (yyvsp[0]._lexval)->_str;
                      mytype = GetVariableType(gModule, (yyvsp[0]._lexval)->_str);
                      if(mytype != 0) (mystat._var)[(yyvsp[0]._lexval)->_str] = mytype;
                  } else if(mypar = IsInParam(gModule, (yyvsp[0]._lexval)->_str)) {
                      mystat._describ = (yyvsp[0]._lexval)->_str;
                      if(mypar->_type == 1) typ = 1;
                      else typ = 0;
                      mystat._param[(yyvsp[0]._lexval)->_str] = typ;
                  } else {
                      if(GetNameNum(gModule, (yyvsp[0]._lexval)->_str) != -1) mystat._describ = (yyvsp[0]._lexval)->_str;
                      else if(gModule->_branchAlias.count((yyvsp[0]._lexval)->_str)) mystat._describ = (yyvsp[0]._lexval)->_str;  // branch 别名: 由 access 规则展开
                      else vaMessageError("identifier never declared",(yyvsp[0]._lexval));
                  }
              }
              ((yyval._yaccval)->_state).push_back(mystat);
              (yyval._yaccval)->_type = mytype;
          }
#line 4718 "vaYacc.cpp"
    break;

  case 250: /* R_e_atomic: tk_dollar_ident  */
#line 2474 "vaYacc.y"
          {
              string mystr;
              mystr = GetDollarValue((yyvsp[0]._lexval)->_str);
              (yyval._yaccval) = new yaccVal;
              statement mystat;
              mystat._describ = mystr;
              ((yyval._yaccval)->_state).push_back(mystat);
          }
#line 4731 "vaYacc.cpp"
    break;

  case 251: /* R_e_atomic: tk_ident '[' R_expression ']'  */
#line 2483 "vaYacc.y"
          {
              vaMessageError("Array not support now.", (yyvsp[-3]._lexval));
          }
#line 4739 "vaYacc.cpp"
    break;

  case 252: /* R_e_atomic: tk_dollar_ident '(' R_l_expression ')'  */
#line 2487 "vaYacc.y"
          {
	    (yyval._yaccval) = new yaccVal;
	    statement mystat;
	    map<string, int>::iterator piter;
	    mystat._param = ((yyvsp[-1]._yaccval)->_state).front()._param;
	    if((yyvsp[-3]._lexval)->_str == "$param_given")
	      {
		// $param_given(NAME) → given_<name>_ 成员（.model 显式设置后置 1）
		string pname = ((yyvsp[-1]._yaccval)->_state).front()._describ;
		if(pname.size() >= 2 && pname.front() == '"' && pname.back() == '"')
		  pname = pname.substr(1, pname.size() - 2);
		mystat._describ = "given_" + pname + "_";
	      }
	    else if((yyvsp[-3]._lexval)->_str == "$strobe")
	      {
		mystat._describ = "printf(\"" + ((yyvsp[-1]._yaccval)->_state).front()._describ + "\")";		
		mystat._mode = 5;
	      }
	    else if((yyvsp[-3]._lexval)->_str == "$simparam")
	      {
		// $simparam("gmin", 1e-12) → 生成模型成员 simparam_<name>_，
		// 默认值取第二实参表达式（codegen 以成员初始化形式发出）。
		string spname = ((yyvsp[-1]._yaccval)->_state).front()._describ;
		// 去掉字符串字面量的引号
		if(spname.size() >= 2 && spname.front() == '"' && spname.back() == '"')
		  spname = spname.substr(1, spname.size() - 2);
		string dflt = "0.0";
		if(((yyvsp[-1]._yaccval)->_state).size() >= 2) dflt = ((yyvsp[-1]._yaccval)->_state).back()._describ;
		gModule->_simparamDflt[spname] = dflt;
		mystat._describ = "simparam_" + spname + "_";
	      }
	    else if((yyvsp[-3]._lexval)->_str == "$vt")
	      {
		// $vt(T) = k*T/q（带显式温度实参；无参 $vt 走 GetDollarValue→temp_）
		// Constants aligned to HSPICE/FineSim: KboQ = 8.617087e-5
		mystat._describ = "(1.38062E-23 * (" + ((yyvsp[-1]._yaccval)->_state).front()._describ + ") / 1.60219E-19)";
	      }
	    else
	      mystat._describ = "(0)";
	    SetVariableType(gModule, (yyvsp[-3]._lexval)->_str, 0);
	    ((yyval._yaccval)->_state).push_back(mystat);
	    
	    //              vaMessageError("DollarIdent function.", $1);
          }
#line 4788 "vaYacc.cpp"
    break;

  case 253: /* R_e_atomic: tk_ident '(' R_l_expression ')'  */
#line 2532 "vaYacc.y"
          {
              int pos, neg;
              list<statement>::iterator iter;
              bitset<BIT_> tmpbit;
              statement mystat;
              string tmp;
              if(IsInNature(__natureList, (yyvsp[-3]._lexval)->_str)){
                  if((yyvsp[-1]._yaccval)->_num == 1){
                      iter = (yyvsp[-1]._yaccval)->_state.begin();
                      string argName = (*iter)._describ;
                      map<string, branch>::iterator brIt = gModule->_branchAlias.find(argName);
                      if(brIt != gModule->_branchAlias.end() && brIt->second._type == 2){
                          // V(br)/Temp(br) 双节点 branch 别名 → 展开为 V(pnode, nnode)
                          string pnode = brIt->second._pnode;
                          string nnode = brIt->second._nnode;
                          pos = GetNameNum(gModule, pnode);
                          neg = GetNameNum(gModule, nnode);
                          if(pos == -1 || neg == -1)vaMessageError("Branch node not defined.", (yyvsp[-3]._lexval));
                          tmpbit[pos] = 1;
                          mystat._var[(yyvsp[-3]._lexval)->_str + pnode] = tmpbit;
                          tmp = "d" + (yyvsp[-3]._lexval)->_str + pnode + "Dv" + int2string(pos);
                          gModule->_dervar[tmp] = pos;
                          (yyval._yaccval) = new yaccVal;
                          mystat._describ = "(" + (yyvsp[-3]._lexval)->_str + pnode;
                          tmpbit = 0;
                          tmpbit[neg] = 1;
                          mystat._var[(yyvsp[-3]._lexval)->_str + nnode] = tmpbit;
                          tmp = "d" + (yyvsp[-3]._lexval)->_str + nnode + "Dv" + int2string(neg);
                          gModule->_dervar[tmp] = neg;
                          mystat._describ += " - " + (yyvsp[-3]._lexval)->_str + nnode + ")";
                          (yyval._yaccval)->_state.push_back(mystat);
                          ((yyval._yaccval)->_type)[pos] = 1;
                          ((yyval._yaccval)->_type)[neg] = 1;
                          delete (yyvsp[-1]._yaccval);
                      } else {
                          if(brIt != gModule->_branchAlias.end()) argName = brIt->second._pnode;  // 单节点 branch
                          pos = GetNameNum(gModule, argName);
                          if(pos == -1)vaMessageError("Acess must take a port num.", (yyvsp[-3]._lexval));
                          tmpbit[pos] = 1;
                          mystat._var[(yyvsp[-3]._lexval)->_str + argName] = tmpbit;
                          tmp = "d" + (yyvsp[-3]._lexval)->_str + argName + "Dv" + int2string(pos);
                          gModule->_dervar[tmp] = pos;
                          (yyval._yaccval) = new yaccVal;
                          mystat._describ = (yyvsp[-3]._lexval)->_str + argName;
                          (yyval._yaccval)->_state.push_back(mystat);
                          ((yyval._yaccval)->_type)[pos] = 1;
                          delete (yyvsp[-1]._yaccval);
                      }
                  }else if((yyvsp[-1]._yaccval)->_num == 2){
                      iter = (yyvsp[-1]._yaccval)->_state.begin();
                      pos = GetNameNum(gModule, (*iter)._describ);
                      if(pos == -1)vaMessageError("Acess must take port nums.", (yyvsp[-3]._lexval));
                      neg = GetNameNum(gModule, (*(++iter))._describ);
                      if(neg == -1)vaMessageError("Acess must take a port num.", (yyvsp[-3]._lexval));
                      nature* nat = IsInNature(__natureList, (yyvsp[-3]._lexval)->_str);
                      if(nat != NULL && nat->_name == "Current"){
                          // I(a,b) 读取 → 该 node pair 的 V<+ 支路电流未知量 Ibr
                          // （若对应 V(a,b) <+ 尚未出现，先建伪网络，
                          //   该支路最终必须有 V<+ 否则矩阵奇异）
                          int brIdx = GetOrCreateBranchFlowNet(gModule, pos, neg);
                          string brVar = "V" + gModule->_net[brIdx]._name;
                          tmpbit = 0;
                          tmpbit[brIdx] = 1;
                          gModule->_dervar["d" + brVar + "Dv" + int2string(brIdx)] = brIdx;
                          (yyval._yaccval) = new yaccVal;
                          mystat._var[brVar] = tmpbit;
                          mystat._describ = brVar;
                          (yyval._yaccval)->_state.push_back(mystat);
                          ((yyval._yaccval)->_type)[brIdx] = 1;
                      } else {
                      iter = (yyvsp[-1]._yaccval)->_state.begin();
                      tmpbit[pos] = 1;
                      tmp = "d" + (yyvsp[-3]._lexval)->_str + (*iter)._describ + "Dv" + int2string(pos);
                      gModule->_dervar[tmp] = pos;
                      mystat._var[(yyvsp[-3]._lexval)->_str + (*iter)._describ] = tmpbit;
                      (yyval._yaccval) = new yaccVal;
                      mystat._describ = "(" + (yyvsp[-3]._lexval)->_str + (*iter)._describ;
                      ++iter;
                      tmpbit = 0;
                      tmpbit[neg] = 1;
                      tmp = "d" + (yyvsp[-3]._lexval)->_str + (*iter)._describ + "Dv" + int2string(neg);
                      gModule->_dervar[tmp] = neg;
                      mystat._describ += " - " + (yyvsp[-3]._lexval)->_str + (*iter)._describ + ")";
                      mystat._var[(yyvsp[-3]._lexval)->_str + (*iter)._describ] = tmpbit;
                      (yyval._yaccval)->_state.push_back(mystat);
                      ((yyval._yaccval)->_type)[pos] = 1;
                      ((yyval._yaccval)->_type)[neg] = 1;
                      }
                      delete (yyvsp[-1]._yaccval);
                  }else{
                      vaMessageError("Too many ports of access.", (yyvsp[-3]._lexval));
                  }
              }else{
                  analogFun *af = FindAnalogFun(gModule, (yyvsp[-3]._lexval)->_str);
                  if(af == NULL){
                      vaMessageError("Undefined access of function: " + (yyvsp[-3]._lexval)->_str, (yyvsp[-3]._lexval));
                  }else{
                      if(af->_type == 0 || af->_type == 1 || af->_type == 2){
                          (yyval._yaccval) = (yyvsp[-1]._yaccval);
			  yaccVal * t = (yyvsp[-1]._yaccval);
                          if(af->_name == "ddt"){
                              map<string, bitset<BIT_> >::iterator mit;
                              mit = (yyval._yaccval)->_state.back()._var.begin();
                              while(mit != (yyval._yaccval)->_state.back()._var.end()){
                                  tmpbit |= mit->second;
                                  ++mit;
                              }
                              tmp = int2string(__modDdtNum);
                              SetVariableType(gModule, "DdtExp"+tmp, tmpbit);
                              SetVariableType(gModule, "DdtAns"+tmp, tmpbit);
                              mystat._describ = "DdtExp" + tmp + " = " + ((yyval._yaccval)->_state.back())._describ + ";";
                              mystat._var = (yyval._yaccval)->_state.back()._var;
                              mystat._param = (yyval._yaccval)->_state.back()._param;
                              mystat._mode = 0;
                              if(mystat._var.size() != 0) mystat._type = true;
                              gStateList.push_back(mystat);
			      //   mystat._describ = "stateVariable_.SetCurrentStateVariable(States::DdtVal" + tmp + ", DdtExp" + tmp + ");";
			      //  mystat._var.clear();
			      //  mystat._type = false;
			      // gStateList.push_back(mystat);
                              mystat._mode = 0;
			      //      mystat._describ = "DdtAns" + tmp + " = equation->DoDdt(stateVariable_, States::DdtVal" + tmp + ");";
			      mystat._describ = "DdtAns" + tmp + " = DdtExp" + tmp + ";";
                              gStateList.push_back(mystat);
                              for(int i=0; i<gModule->_net.size(); ++i){
                                  if(tmpbit[i] != 0){
                                      mystat._describ = "dDdtAns" + tmp + "Dv" + int2string(i) + " = " + "dDdtExp" + tmp + "Dv" + int2string(i) + " * _der0;";
                                      mystat._mode = 4;
                                      gModule->_tmpdervar["dDdtAns" + tmp + "Dv" + int2string(i)] = 1;
                                      gModule->_tmpdervar["dDdtExp" + tmp + "Dv" + int2string(i)] = 1;
                                      gStateList.push_back(mystat);
                                  }
                              }
                              ++__modDdtNum;
                              tmp = "DdtAns" + tmp;
                              ((yyval._yaccval)->_state.back())._describ = tmp;
                              ((yyval._yaccval)->_state.back())._var.clear();
                              tmpbit = GetVariableType(gModule, tmp);
                              if(tmpbit != 0)((yyval._yaccval)->_state.back())._var[tmp] = tmpbit;
                          } else if (af->_name == "ddx"){
                            // ddx(expr, V(node)): 仅用于 opvar 输出（cd/gd 等），
                            // 不影响 f/jac 仿真结果。暂以 0.0 近似（opvar 值不可比）。
                              (yyval._yaccval)->_state.clear();
                              mystat._describ = "0.0";
                              mystat._mode = 0;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else if (af->_name == "limexp"){
                            // limexp(x) → exp(x)：工作区内与 openvaf 一致；
                            // 极端饱和区（x 很大）openvaf 会限幅，此处不限（TODO）
                              ((yyval._yaccval)->_state.back())._describ = "exp(" + ((yyval._yaccval)->_state.back())._describ + ")";
                          } else if (af->_name == "analysis"){
                              (yyval._yaccval)->_state.clear();
                              mystat._describ = "1.0";
                              mystat._mode = 0;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else if (af->_name == "param_given"){
                              ((yyval._yaccval)->_state.back())._describ = "given_" + ((yyval._yaccval)->_state.back())._describ + "_";
                          } else if (af->_name == "port_connected"){
                              (yyval._yaccval)->_state.clear();
                              mystat._describ = "1.0";
                              mystat._mode = 0;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else if (af->_name == "ac_stim" || af->_name == "last_crossing" || af->_name == "timer" || af->_name == "above" || af->_name == "cross"){
                              (yyval._yaccval)->_state.clear();
                              mystat._describ = "0.0";
                              mystat._mode = 0;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else if (af->_name == "transition" || af->_name == "slew"){
                              // pass through first arg (already in $$)
                          } else if (af->_name == "white_noise" || af->_name == "flicker_noise"){
                              (yyval._yaccval)->_state.clear();
                              mystat._describ = "0";
                              mystat._mode = 0;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else if (af->_name == "ln") {
                              ((yyval._yaccval)->_state.back())._describ = "log(" + ((yyval._yaccval)->_state.back())._describ + ")";
                          } else if (af->_name == "log") {
                              ((yyval._yaccval)->_state.back())._describ = "log10(" + ((yyval._yaccval)->_state.back())._describ + ")";
                          } else if (af->_name == "abs") {
                              ((yyval._yaccval)->_state.back())._describ = "fabs(" + ((yyval._yaccval)->_state.back())._describ + ")";
                          } else if (af->_name == "pow" || af->_name == "max" || af->_name == "min") {
                              if((yyvsp[-1]._yaccval)->_num != 2) vaMessageError("pow must take 2 params.", (yyvsp[-3]._lexval));
                              ((yyval._yaccval)->_state.front())._describ = (yyvsp[-3]._lexval)->_str + "(" + ((yyval._yaccval)->_state.front())._describ + ", " + ((yyval._yaccval)->_state.back())._describ + ")";
                              // 合并第二实参的 _var/_param（否则其中的模型参数
                              // 不会替换为成员名、电压依赖跟踪也会丢失）
                              {
                                map<string, bitset<BIT_> >::iterator vit2 = ((yyval._yaccval)->_state.back())._var.begin();
                                while(vit2 != ((yyval._yaccval)->_state.back())._var.end()){
                                  ((yyval._yaccval)->_state.front())._var[vit2->first] = vit2->second;
                                  ++vit2;
                                }
                                map<string, int>::iterator pit2 = ((yyval._yaccval)->_state.back())._param.begin();
                                while(pit2 != ((yyval._yaccval)->_state.back())._param.end()){
                                  ((yyval._yaccval)->_state.front())._param[pit2->first] = pit2->second;
                                  ++pit2;
                                }
                              }
                              (yyval._yaccval)->_state.pop_back();
                          } else if (af->_type == 2) {
                              // ===== 用户 analog function 调用：内联展开 =====
                              // f(a1..an) → 形参替换为实参表达式、局部变量/返回值加
                              // 唯一后缀，函数体语句内联到 gStateList（随当前语句前发射）。
                              static int afInlineNum = 0;
                              string suffix = "__af" + int2string(afInlineNum++);
                              string retVar = af->_name + suffix;

                              // 收集实参（表达式文本 + 电压依赖 + 参数引用）
                              vector<string> argDesc;
                              vector<map<string, bitset<BIT_> > > argVar;
                              vector<map<string, int> > argParam;
                              for(list<statement>::iterator ait = (yyvsp[-1]._yaccval)->_state.begin();
                                  ait != (yyvsp[-1]._yaccval)->_state.end(); ++ait){
                                  argDesc.push_back(ait->_describ);
                                  argVar.push_back(ait->_var);
                                  argParam.push_back(ait->_param);
                              }
                              if(getenv("VA_DEBUG_AF")){
                                  fprintf(stderr, "[af] %s: interface=", af->_name.c_str());
                                  for(size_t _f = 0; _f < af->_interface.size(); ++_f)
                                      fprintf(stderr, "%s ", af->_interface[_f]._name.c_str());
                                  fprintf(stderr, "| args=");
                                  for(size_t _a = 0; _a < argDesc.size(); ++_a)
                                      fprintf(stderr, "[%s] ", argDesc[_a].c_str());
                                  fprintf(stderr, "| locals=");
                                  for(map<string, varType>::iterator _l = af->_var.begin(); _l != af->_var.end(); ++_l)
                                      fprintf(stderr, "%s ", _l->first.c_str());
                                  fprintf(stderr, "| bodysteps=%d\n", (int)af->_state._steps.size());
                                  for(list<statement>::iterator _b = af->_state._steps.begin(); _b != af->_state._steps.end(); ++_b)
                                      fprintf(stderr, "[af body] %s\n", _b->_describ.c_str());
                              }

                              // 形参索引
                              map<string, int> formalIdx;
                              for(size_t fi = 0; fi < af->_interface.size(); ++fi)
                                  formalIdx[af->_interface[fi]._name] = (int)fi;

                              // 局部变量（af->_var 中非形参）重命名并声明
                              map<string, string> lrename;
                              for(map<string, varType>::iterator lit = af->_var.begin();
                                  lit != af->_var.end(); ++lit){
                                  if(formalIdx.count(lit->first)) continue;
                                  lrename[lit->first] = lit->first + suffix;
                                  variable lv; lv._name = lit->first + suffix; lv._type = 2;
                                  gModule->_variable.push_back(lv);
                              }
                              variable rv; rv._name = retVar; rv._type = 2;
                              gModule->_variable.push_back(rv);

                              // 名称替换：形参→(实参表达式)、局部→加后缀、函数名→返回变量

                              // 内联函数体
                              bitset<BIT_> bodyDeps;
                              for(list<statement>::iterator fit = af->_state._steps.begin();
                                  fit != af->_state._steps.end(); ++fit){
                                  statement ns = *fit;
                                  ns._describ = AfSubstNames(fit->_describ, af, lrename, argDesc, retVar);
                                  // _var 重映射：形参→实参依赖、局部/函数名→重命名
                                  map<string, bitset<BIT_> > nvar;
                                  for(map<string, bitset<BIT_> >::iterator vit3 = fit->_var.begin();
                                      vit3 != fit->_var.end(); ++vit3){
                                      if(formalIdx.count(vit3->first)){
                                          int fi = formalIdx[vit3->first];
                                          if(fi < (int)argVar.size()){
                                              for(map<string, bitset<BIT_> >::iterator av = argVar[fi].begin();
                                                  av != argVar[fi].end(); ++av)
                                                  nvar[av->first] = av->second;
                                          }
                                      } else if(lrename.count(vit3->first)){
                                          nvar[lrename[vit3->first]] = vit3->second;
                                      } else if(vit3->first == af->_name){
                                          nvar[retVar] = vit3->second;
                                      } else {
                                          nvar[vit3->first] = vit3->second;
                                      }
                                  }
                                  ns._var = nvar;
                                  // 实参的模型参数引用传入内联语句（否则替换不成成员名）
                                  for(size_t _ai = 0; _ai < argParam.size(); ++_ai){
                                      for(map<string, int>::iterator ap = argParam[_ai].begin();
                                          ap != argParam[_ai].end(); ++ap)
                                          ns._param[ap->first] = ap->second;
                                  }
                                  bitset<BIT_> deps;
                                  for(map<string, bitset<BIT_> >::iterator vit4 = nvar.begin();
                                      vit4 != nvar.end(); ++vit4) deps |= vit4->second;
                                  bodyDeps |= deps;
                                  // LHS 导数临时变量注册
                                  size_t eqp = fit->_describ.find('=');
                                  if(eqp != string::npos){
                                      string lhs = fit->_describ.substr(0, eqp);
                                      while(!lhs.empty() && (lhs.back()==' '||lhs.back()=='\t')) lhs.pop_back();
                                      string lhsNew = lrename.count(lhs) ? lrename[lhs]
                                                        : (lhs == af->_name ? retVar : lhs);
                                      for(int i = 0; i < BIT_; ++i)
                                          if(deps[i]) gModule->_tmpdervar["d" + lhsNew + "Dv" + int2string(i)] = 1;
                                  }
                                  gStateList.push_back(ns);
                              }

                              // 调用点表达式 → 返回变量
                              (yyval._yaccval) = new yaccVal;
                              mystat._describ = retVar;
                              if(bodyDeps != 0) mystat._var[retVar] = bodyDeps;
                              ((yyval._yaccval)->_type) = bodyDeps;
                              (yyval._yaccval)->_state.push_back(mystat);
                          } else {
                              ((yyval._yaccval)->_state.back())._describ = (yyvsp[-3]._lexval)->_str + "(" + ((yyval._yaccval)->_state.back())._describ + ")";
                          }
                      }
                      else {
                          vaMessageError("Analog function not impl yet.", (yyvsp[-3]._lexval));
                      }
                  }
              }
          }
#line 5108 "vaYacc.cpp"
    break;

  case 254: /* R_e_atomic: '(' R_expression ')'  */
#line 2848 "vaYacc.y"
          {
            (yyval._yaccval) = (yyvsp[-1]._yaccval);
            (yyval._yaccval)->_state.front()._describ = "(" + (yyval._yaccval)->_state.front()._describ + ")";
          }
#line 5117 "vaYacc.cpp"
    break;


#line 5121 "vaYacc.cpp"

      default: break;
    }
  /* User semantic actions sometimes alter yychar, and that requires
     that yytoken be updated with the new translation.  We take the
     approach of translating immediately before every use of yytoken.
     One alternative is translating here after every semantic action,
     but that translation would be missed if the semantic action invokes
     YYABORT, YYACCEPT, or YYERROR immediately after altering yychar or
     if it invokes YYBACKUP.  In the case of YYABORT or YYACCEPT, an
     incorrect destructor might then be invoked immediately.  In the
     case of YYERROR or YYBACKUP, subsequent parser actions might lead
     to an incorrect destructor call or verbose syntax error message
     before the lookahead is translated.  */
  YY_SYMBOL_PRINT ("-> $$ =", YY_CAST (yysymbol_kind_t, yyr1[yyn]), &yyval, &yyloc);

  YYPOPSTACK (yylen);
  yylen = 0;

  *++yyvsp = yyval;

  /* Now 'shift' the result of the reduction.  Determine what state
     that goes to, based on the state we popped back to and the rule
     number reduced by.  */
  {
    const int yylhs = yyr1[yyn] - YYNTOKENS;
    const int yyi = yypgoto[yylhs] + *yyssp;
    yystate = (0 <= yyi && yyi <= YYLAST && yycheck[yyi] == *yyssp
               ? yytable[yyi]
               : yydefgoto[yylhs]);
  }

  goto yynewstate;


/*--------------------------------------.
| yyerrlab -- here on detecting error.  |
`--------------------------------------*/
yyerrlab:
  /* Make sure we have latest lookahead translation.  See comments at
     user semantic actions for why this is necessary.  */
  yytoken = yychar == YYEMPTY ? YYSYMBOL_YYEMPTY : YYTRANSLATE (yychar);
  /* If not already recovering from an error, report this error.  */
  if (!yyerrstatus)
    {
      ++yynerrs;
      yyerror (YY_("syntax error"));
    }

  if (yyerrstatus == 3)
    {
      /* If just tried and failed to reuse lookahead token after an
         error, discard it.  */

      if (yychar <= YYEOF)
        {
          /* Return failure if at end of input.  */
          if (yychar == YYEOF)
            YYABORT;
        }
      else
        {
          yydestruct ("Error: discarding",
                      yytoken, &yylval);
          yychar = YYEMPTY;
        }
    }

  /* Else will try to reuse lookahead token after shifting the error
     token.  */
  goto yyerrlab1;


/*---------------------------------------------------.
| yyerrorlab -- error raised explicitly by YYERROR.  |
`---------------------------------------------------*/
yyerrorlab:
  /* Pacify compilers when the user code never invokes YYERROR and the
     label yyerrorlab therefore never appears in user code.  */
  if (0)
    YYERROR;
  ++yynerrs;

  /* Do not reclaim the symbols of the rule whose action triggered
     this YYERROR.  */
  YYPOPSTACK (yylen);
  yylen = 0;
  YY_STACK_PRINT (yyss, yyssp);
  yystate = *yyssp;
  goto yyerrlab1;


/*-------------------------------------------------------------.
| yyerrlab1 -- common code for both syntax error and YYERROR.  |
`-------------------------------------------------------------*/
yyerrlab1:
  yyerrstatus = 3;      /* Each real token shifted decrements this.  */

  /* Pop stack until we find a state that shifts the error token.  */
  for (;;)
    {
      yyn = yypact[yystate];
      if (!yypact_value_is_default (yyn))
        {
          yyn += YYSYMBOL_YYerror;
          if (0 <= yyn && yyn <= YYLAST && yycheck[yyn] == YYSYMBOL_YYerror)
            {
              yyn = yytable[yyn];
              if (0 < yyn)
                break;
            }
        }

      /* Pop the current state because it cannot handle the error token.  */
      if (yyssp == yyss)
        YYABORT;


      yydestruct ("Error: popping",
                  YY_ACCESSING_SYMBOL (yystate), yyvsp);
      YYPOPSTACK (1);
      yystate = *yyssp;
      YY_STACK_PRINT (yyss, yyssp);
    }

  YY_IGNORE_MAYBE_UNINITIALIZED_BEGIN
  *++yyvsp = yylval;
  YY_IGNORE_MAYBE_UNINITIALIZED_END


  /* Shift the error token.  */
  YY_SYMBOL_PRINT ("Shifting", YY_ACCESSING_SYMBOL (yyn), yyvsp, yylsp);

  yystate = yyn;
  goto yynewstate;


/*-------------------------------------.
| yyacceptlab -- YYACCEPT comes here.  |
`-------------------------------------*/
yyacceptlab:
  yyresult = 0;
  goto yyreturnlab;


/*-----------------------------------.
| yyabortlab -- YYABORT comes here.  |
`-----------------------------------*/
yyabortlab:
  yyresult = 1;
  goto yyreturnlab;


/*-----------------------------------------------------------.
| yyexhaustedlab -- YYNOMEM (memory exhaustion) comes here.  |
`-----------------------------------------------------------*/
yyexhaustedlab:
  yyerror (YY_("memory exhausted"));
  yyresult = 2;
  goto yyreturnlab;


/*----------------------------------------------------------.
| yyreturnlab -- parsing is finished, clean up and return.  |
`----------------------------------------------------------*/
yyreturnlab:
  if (yychar != YYEMPTY)
    {
      /* Make sure we have latest lookahead translation.  See comments at
         user semantic actions for why this is necessary.  */
      yytoken = YYTRANSLATE (yychar);
      yydestruct ("Cleanup: discarding lookahead",
                  yytoken, &yylval);
    }
  /* Do not reclaim the symbols of the rule whose action triggered
     this YYABORT or YYACCEPT.  */
  YYPOPSTACK (yylen);
  YY_STACK_PRINT (yyss, yyssp);
  while (yyssp != yyss)
    {
      yydestruct ("Cleanup: popping",
                  YY_ACCESSING_SYMBOL (+*yyssp), yyvsp);
      YYPOPSTACK (1);
    }
#ifndef yyoverflow
  if (yyss != yyssa)
    YYSTACK_FREE (yyss);
#endif

  return yyresult;
}

#line 2853 "vaYacc.y"


void verilogerror(char *)
{
}

void adms_veriloga_setint_yydebug(const int val)
{
  yydebug=val;
}
