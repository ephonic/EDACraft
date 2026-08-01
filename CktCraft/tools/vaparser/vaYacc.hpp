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

#ifndef YY_VERILOG_VAYACC_HPP_INCLUDED
# define YY_VERILOG_VAYACC_HPP_INCLUDED
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
    PREC_IF_THEN = 258,            /* PREC_IF_THEN  */
    tk_from = 259,                 /* tk_from  */
    tk_branch = 260,               /* tk_branch  */
    tk_number = 261,               /* tk_number  */
    tk_nature = 262,               /* tk_nature  */
    tk_aliasparameter = 263,       /* tk_aliasparameter  */
    tk_output = 264,               /* tk_output  */
    tk_anystring = 265,            /* tk_anystring  */
    tk_dollar_ident = 266,         /* tk_dollar_ident  */
    tk_or = 267,                   /* tk_or  */
    tk_aliasparam = 268,           /* tk_aliasparam  */
    tk_if = 269,                   /* tk_if  */
    tk_analog = 270,               /* tk_analog  */
    tk_parameter = 271,            /* tk_parameter  */
    tk_discipline = 272,           /* tk_discipline  */
    tk_char = 273,                 /* tk_char  */
    tk_anytext = 274,              /* tk_anytext  */
    tk_for = 275,                  /* tk_for  */
    tk_while = 276,                /* tk_while  */
    tk_real = 277,                 /* tk_real  */
    tk_op_shr = 278,               /* tk_op_shr  */
    tk_case = 279,                 /* tk_case  */
    tk_potential = 280,            /* tk_potential  */
    tk_endcase = 281,              /* tk_endcase  */
    tk_inf = 282,                  /* tk_inf  */
    tk_exclude = 283,              /* tk_exclude  */
    tk_ground = 284,               /* tk_ground  */
    tk_endmodule = 285,            /* tk_endmodule  */
    tk_begin = 286,                /* tk_begin  */
    tk_enddiscipline = 287,        /* tk_enddiscipline  */
    tk_domain = 288,               /* tk_domain  */
    tk_ident = 289,                /* tk_ident  */
    tk_op_shl = 290,               /* tk_op_shl  */
    tk_string = 291,               /* tk_string  */
    tk_integer = 292,              /* tk_integer  */
    tk_module = 293,               /* tk_module  */
    tk_endattribute = 294,         /* tk_endattribute  */
    tk_else = 295,                 /* tk_else  */
    tk_end = 296,                  /* tk_end  */
    tk_inout = 297,                /* tk_inout  */
    tk_and = 298,                  /* tk_and  */
    tk_bitwise_equr = 299,         /* tk_bitwise_equr  */
    tk_default = 300,              /* tk_default  */
    tk_function = 301,             /* tk_function  */
    tk_input = 302,                /* tk_input  */
    tk_beginattribute = 303,       /* tk_beginattribute  */
    tk_endnature = 304,            /* tk_endnature  */
    tk_endfunction = 305,          /* tk_endfunction  */
    tk_flow = 306                  /* tk_flow  */
  };
  typedef enum yytokentype yytoken_kind_t;
#endif
/* Token kinds.  */
#define YYEMPTY -2
#define YYEOF 0
#define YYerror 256
#define YYUNDEF 257
#define PREC_IF_THEN 258
#define tk_from 259
#define tk_branch 260
#define tk_number 261
#define tk_nature 262
#define tk_aliasparameter 263
#define tk_output 264
#define tk_anystring 265
#define tk_dollar_ident 266
#define tk_or 267
#define tk_aliasparam 268
#define tk_if 269
#define tk_analog 270
#define tk_parameter 271
#define tk_discipline 272
#define tk_char 273
#define tk_anytext 274
#define tk_for 275
#define tk_while 276
#define tk_real 277
#define tk_op_shr 278
#define tk_case 279
#define tk_potential 280
#define tk_endcase 281
#define tk_inf 282
#define tk_exclude 283
#define tk_ground 284
#define tk_endmodule 285
#define tk_begin 286
#define tk_enddiscipline 287
#define tk_domain 288
#define tk_ident 289
#define tk_op_shl 290
#define tk_string 291
#define tk_integer 292
#define tk_module 293
#define tk_endattribute 294
#define tk_else 295
#define tk_end 296
#define tk_inout 297
#define tk_and 298
#define tk_bitwise_equr 299
#define tk_default 300
#define tk_function 301
#define tk_input 302
#define tk_beginattribute 303
#define tk_endnature 304
#define tk_endfunction 305
#define tk_flow 306

/* Value type.  */
#if ! defined YYSTYPE && ! defined YYSTYPE_IS_DECLARED
union YYSTYPE
{
#line 72 "vaYacc.y"

  lexVal*  _lexval;
  yaccVal* _yaccval;

#line 174 "vaYacc.hpp"

};
typedef union YYSTYPE YYSTYPE;
# define YYSTYPE_IS_TRIVIAL 1
# define YYSTYPE_IS_DECLARED 1
#endif


extern YYSTYPE veriloglval;


int verilogparse (void);


#endif /* !YY_VERILOG_VAYACC_HPP_INCLUDED  */
