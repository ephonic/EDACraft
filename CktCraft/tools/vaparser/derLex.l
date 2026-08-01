/**************************************************************************
*@author  Panxiaoda zhgui
*@date    Dec.1
***************************************************************************/

%{
#include "derivation.h"
#include "derYacc.hpp"
#include <stdlib.h>
#include <string.h>

extern int string_len;
extern char* string_ptr;

void deriverror(char *);

int myinput(char *buf, int max)
{
  if(string_len == 0) return 0;
  if(max > string_len) max = string_len;
  memcpy(buf, string_ptr, max);
  string_ptr += max;
  string_len -= max;
  return max;
}

#undef YY_INPUT
#define YY_INPUT(b, r, m) (r = myinput(b, m))


%}

integer  [0-9]+
number   [0-9]+\.[0-9]*([eE][+-]?[0-9]+)?|\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+([eE][+-]?[0-9]+)
variable [a-zA-Z\_][a-zA-Z0-9\_]*

%%

[ \t\n]              ;       // skip whitespace

{integer} {
  derivlval.str = (char*)malloc((yyleng+1)*sizeof(char));
  strcpy(derivlval.str, yytext);
  return NUM;
}

{number} {
  derivlval.str = (char*)malloc((yyleng+1)*sizeof(char));
  strcpy(derivlval.str, yytext);
  return NUM;
};

{variable} {
  derivlval.str = (char*)malloc((yyleng+1)*sizeof(char));
  strcpy(derivlval.str, yytext);
  return VAR;
}

"++" { return ADDONE; }
"--" { return MINONE; }
"==" { asprintf(&(derivlval.str), "=="); return CMP1;   }
"!=" { asprintf(&(derivlval.str), "!="); return CMP1;   }
">=" { asprintf(&(derivlval.str), ">="); return CMP;    }
"<=" { asprintf(&(derivlval.str), "<="); return CMP;    }
">"  { asprintf(&(derivlval.str), ">");  return CMP;    }
"<"  { asprintf(&(derivlval.str), "<");  return CMP;    }

<<EOF>> { return EOFF;}

.  { return yytext[0]; }

%%

int yywrap(void) {
    return 1;
}
