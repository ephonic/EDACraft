/**************************************************************************
*   @author  Panxiaoda zhgui
*   @date    Dec.1
***************************************************************************/

%{
#include "derivation.h"

#include <string.h>
#include <stdio.h>
using std::string;

#define CFREESD1(a)       free(a.self);free(a.deriv)
#define CFREESD2(a, b)    free(a.self);free(a.deriv);free(b.self);free(b.deriv)
#define SYMCOPY(des, ori) des.self = ori.self; des.deriv = ori.deriv

#define YYDEBUG 1

//	For Lex Functions.
int  derivlex_destroy (void);
int  derivlex         (void);
void deriverror      (char*);

int exprlnum = 0;
extern int __derindex;
extern string __selfResult;
extern string __derivResult;

%}

%union
{
  char *str;
  struct {
    char *self;
    char *deriv;
  } self_deriv;
}

%token <str> NUM
%token <str> VAR
%token <str> CMP
%token <str> CMP1

%token ADDONE MINONE
%token EOFF

%type <self_deriv> expral
%type <self_deriv> exprlist
%type <self_deriv> expr
%type <self_deriv> term
%type <self_deriv> unary
%type <self_deriv> atomic
%type <self_deriv> program
%type <self_deriv> assign
%type <self_deriv> all
%type <self_deriv> state

%%

all
  : program EOFF
   {
     return 0;
   }
  ;

program
  : program assign ';'
   {
     fprintf(stderr, "Wraning: More than one sentence found in a statement.\n");
   }
  | assign ';'
   {
     __selfResult = $1.self;
     __derivResult = $1.deriv;
     CFREESD1($1);
   }
  ;

assign
  : VAR '=' expral
   {
     asprintf(&($$.self), "%s = %s", $1, $3.self);
     asprintf(&($$.deriv), "d%sDv%d = %s", $1, __derindex, $3.deriv);
     CFREESD1($3);
     free($1);
   }
  | VAR '=' assign
   {
     fprintf(stderr, "Error: Inline assignments are prohibited.\n");
     return -1;
   }
  ;

expral
  : state '?' expr ':' expr
   {
     asprintf(&($$.self), "(%s ? %s : %s)", $1.self, $3.self, $5.self);
     if(GetType($3.deriv) == 0 && GetType($5.deriv) == 0)
       asprintf(&($$.deriv), "0");
     else asprintf(&($$.deriv), "(%s ? %s : %s)", $1.self, $3.deriv, $5.deriv);
     CFREESD2($3, $5);
     CFREESD1($1);
   }
  | expr
   {
     SYMCOPY($$, $1);
   }
  ;

exprlist
  : exprlist ',' expr
   {
     asprintf(&($$.self), "%s,%s", $1.self, $3.self);
     asprintf(&($$.deriv), "%s,%s", $1.deriv, $3.deriv);
     ++exprlnum;
     CFREESD2($1, $3);
   }
  | expr
   {
     SYMCOPY($$, $1);
     exprlnum = 1;
   }
  ;

state
  : expr CMP expr
   {
     asprintf(&($$.self), "(%s %s %s)", $1.self, $2, $3.self);
     $$.deriv = NULL;
     CFREESD2($1, $3);
     free($2);
   }
  | expr CMP1 expr
   {
     asprintf(&($$.self), "(%s %s %s)", $1.self, $2, $3.self);
     $$.deriv = NULL;
     CFREESD2($1, $3);
     free($2);
   }
  | '(' state ')'
   {
     $$.self = $2.self;
   }
  | expr
   {
     // 条件为纯表达式（如 (!(flag)) 无比较运算符）：不可微
     // $$.self 接管 $1.self 所有权（不能再 CFREESD1 释放，
     // 否则上层三目规则读到已释放内存 → 堆损坏）
     $$.self = $1.self;
     $$.deriv = NULL;
     free($1.deriv);
   }
  ;

expr
  : term
   {
     SYMCOPY($$, $1);
   }
  | expr '-' term
   {
     $$.self = GetExprAns('-', $1.self, $3.self);
     $$.deriv = GetExprAns('-', $1.deriv, $3.deriv);
     CFREESD2($1, $3);
   }
  | expr '+' term
   {
     $$.self = GetExprAns('+', $1.self, $3.self);
     $$.deriv = GetExprAns('+', $1.deriv, $3.deriv);
     CFREESD2($1, $3);
   }
  ;

term
  : unary
   {
     SYMCOPY($$, $1);
   }
  | term '*' unary
   {
     char *p1, *p2;
     $$.self = GetExprAns('*', $1.self, $3.self);
     p1 = GetExprAns('*', $1.self, $3.deriv);
     p2 = GetExprAns('*', $1.deriv, $3.self);
     $$.deriv = GetExprAns('+', p1, p2);
     free(p1);
     free(p2);
     CFREESD2($1, $3);
   }
  | term '/' unary
   {
     // should DO Optimize: a / b : 
     // tmp = a / b;
     // der = (da - tmp * db) / b = da/b - a*db/b^2
     char *p1, *p2;
     $$.self = GetExprAns('/', $1.self, $3.self);
     p1 = GetExprAns('*', $$.self, $3.deriv);
     p2 = GetExprAns('-', $1.deriv, p1);
     $$.deriv = GetExprAns('/', p2, $3.self);
     free(p1); free(p2);
     CFREESD2($1, $3);
   }
  ;


unary
  : atomic
   {
     SYMCOPY($$, $1);
   }
  | '+' atomic
   {
     SYMCOPY($$, $2);
   }
  | '-' atomic
   {
     asprintf(&($$.self), "(-%s)", $2.self);
     asprintf(&($$.deriv), "(-%s)", $2.deriv);
     CFREESD1($2);
   }
  | '!' atomic
   {
     // 逻辑非：只出现在条件表达式中，不可微，导数为 0
     asprintf(&($$.self), "(!%s)", $2.self);
     asprintf(&($$.deriv), "0");
     CFREESD1($2);
   }
  ;


atomic
  : VAR
   {
     $$.self = $1;
     if(VarCheckDependence($1, __derindex)){
       asprintf(&($$.deriv), "d%sDv%d", $1, __derindex);
     } else {
       asprintf(&($$.deriv), "0");
     }
   }
  | NUM
   {
     $$.self = $1;
     asprintf(&($$.deriv), "0");
   }
  | '(' expral ')'
   {
     if(CheckAtomic) {
       SYMCOPY($$, $2);
     } else {
       asprintf(&($$.self), "(%s)", $2.self);
       asprintf(&($$.deriv), "(%s)", $2.deriv);
       CFREESD1($2);
     }
   }
  | VAR '(' exprlist ')'
   {
     asprintf(&($$.self), "%s(%s)", $1, $3.self);
     $$.deriv = GetDerivFunction($1, $3.self, $3.deriv, exprlnum);
     if($$.deriv == NULL) {
       derivError("Function %s is Not Implement yet.\n", $1);
     }
     free($1);
     CFREESD1($3);
   }
  ;

%%

void deriverror(char *s) {
    fprintf(stderr, "%s\n", s);
}
