/*verilog-ams lex file.*/
%{
#include <string>
#include <vector>
#include "vaParser.h"
#include "vaYacc.hpp"
//#define VADEBUG 1
#ifdef YYDEBUG
    extern int yydebug;
#endif

    using std::string;

    extern string __curFile;
    extern int    __curLine;
    extern int    __curPos;
    extern module *gModule;
    extern int    gCaseFlag;

    lexVal* lexvalNew(const char* str, string &file, int line, int pos)
    {
        lexVal* tmp = new lexVal;
        tmp->_str = string(str);
        tmp->_fileName = file;
        tmp->_line = line;
        return tmp;
    }
    void posUpdate(const int leng, const char* text)
    {
        __curPos += leng;
#ifdef VADEBUG
        printf("%s : %d : %d-%d token:\"%s\"\n", __curFile.c_str(), __curLine,
                __curPos-leng, __curPos, text);
#endif
    }
    void TKRETURN(const char* text, const int leng)
    {
        veriloglval._lexval = lexvalNew(text, __curFile, __curLine, __curPos);
        posUpdate(leng, text);
    }
    void TKSTRIPPEDRETURN(const char* text, const int leng)
    {
        string tmpstr = string(text+1, text+leng-1);
        veriloglval._lexval = lexvalNew(tmpstr.c_str(), __curFile, __curLine, __curPos);
        posUpdate(leng, text);
    }
    void VA_ERROR(string str, string file, int line, char* text)
    {
        cout<<"At file:"<<file<<", line:"<<line<<":"<<text;
        cout<<str<<endl;
    }
%}

whitespace0 [ \t\v\f]*
whitespace [ \t\v\f]+
newline    \r?\n
wn [ \t\v\f\r?\n]
wn0 [ \t\v\f\r?\n]*
wn1 [ \t\v\f\r?\n]+
ident      [A-Za-z_][A-Za-z0-9_]*
attribute  [A-Za-z_][A-Za-z0-9_:.]*
attributevalue {wn0}={wn0}{anystring}
escape     (\\([\'\"\\abfnrtv]))
anystring  \"([^\"]|{escape})*\"
b8_int     0[0-9]*
b10_uint   [1-9][0-9]*
b16_int    0[xX][0-9A-Fa-f]+
float      [0-9]*\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+\.?([eE][+-]?[0-9]+)?
char       \'[^\']*[\'\n]

%x insideAttribute 
%x insideAttributeBegin 
%x insideAttributeEqual 
%x insideAttributeValue 
%x insideAttributeEnd 
%x insidePragma 
%option nounput

%%

{newline} {
   ++__curLine;
   __curPos = 0;
}

^#{whitespace} {BEGIN(insidePragma);}
{whitespace} {posUpdate(yyleng, yytext);}


<insidePragma>{
{anystring} {
    __curFile = string(yytext+1, yytext+yyleng-1);
}
{b10_uint} {
    __curLine = str2int(yytext);
    __curPos = 0;
}
{newline} {
    BEGIN(INITIAL);
    __curPos = 0;
}
{whitespace} {
    posUpdate(yyleng, yytext);
}
. {
    VA_ERROR("Inside Error. unexpected character.", __curFile, __curLine, yytext);
}
}

{anystring} {
    char* ctmp = new char[yyleng-1];
    memcpy(ctmp, yytext+1, yyleng-2);
    ctmp[strlen(yytext)-2] = 0;
    TKRETURN(ctmp, yyleng-2);
    delete[] ctmp;
    return tk_anystring;
}

"(*"{wn0} {
    BEGIN(insideAttribute);
    posUpdate(yyleng, yytext);
    return tk_beginattribute;
}

<insideAttribute>{
"*)" {
    BEGIN(INITIAL);
    return tk_endattribute;
}
{attribute}{attributevalue} {BEGIN(insideAttributeBegin);yyless(0);}
. {
    char myyytext[1000];
    register int i=0;
    myyytext[i]=yytext[0];
    for(;;)
    {
        while((myyytext[i]!='*')&&(myyytext[i]!=EOF))
        {
            myyytext[++i]=yyinput();
        }
        if(myyytext[i]=='*')
        {
            while((myyytext[++i]=yyinput())=='*')
            ;
            if(myyytext[i]==')')
            {
              BEGIN(INITIAL);
              i-=2;
              while(myyytext[i]==' ')
                i--;
              myyytext[i+1]='\0';
              posUpdate(yyleng,yytext);

              veriloglval._lexval = lexvalNew(
                  myyytext,
                  __curFile,
                  __curLine,
                  __curPos
              );
              return tk_anytext;
            }
        }
        if(myyytext[i] == EOF)
        {
            printf("line %d, EOF found in attribute declaration.\n", __curLine);
            exit(-1);
        }
    }
}
}

<insideAttributeBegin>{
{attribute} {BEGIN(insideAttributeEqual);TKRETURN(yytext,yyleng);return tk_ident;}
. {
  //adms_message_fatal(("[%s:%i]: inside Verilog-ams attribute declaration unexpected character at [%s]\n",root()->_curfilename,root()->_curline,yytext))
}
}

<insideAttributeEqual>{
{wn0}={wn0} {BEGIN(insideAttributeValue);return '=';}
. {
  //adms_message_fatal(("[%s:%i]: inside Verilog-ams attribute declaration unexpected character at [%s]\n",root()->_curfilename,root()->_curline,yytext))
}
}
<insideAttributeValue>{
{anystring} {TKSTRIPPEDRETURN(yytext,yyleng);BEGIN(insideAttributeEnd);return tk_anystring;}
. {
  //adms_message_fatal(("[%s:%i]: inside Verilog-ams attribute declaration unexpected character at [%s]\n",root()->_curfilename,root()->_curline,yytext))
}
}

<insideAttributeEnd>{
{wn0}"*)" {BEGIN(INITIAL);TKRETURN(yytext,yyleng);return tk_endattribute;}
{wn1} {BEGIN(insideAttributeBegin); posUpdate(yyleng,yytext);}
{wn0},{wn0} {BEGIN(insideAttributeBegin);posUpdate(yyleng,yytext);}
{attribute}{attributevalue} {BEGIN(insideAttributeBegin);yyless(0);}
. {
  //adms_message_fatal(("[%s:%i]: inside Verilog-ams attribute declaration unexpected character at [%s]\n",root()->_curfilename,root()->_curline,yytext))
}
}


parameter {TKRETURN(yytext,yyleng); return tk_parameter;}
aliasparameter {TKRETURN(yytext,yyleng); return tk_aliasparameter;}
aliasparam {TKRETURN(yytext,yyleng); return tk_aliasparam;}
module {TKRETURN(yytext,yyleng); return tk_module;}
endmodule {TKRETURN(yytext,yyleng); return tk_endmodule;}
function {TKRETURN(yytext,yyleng); return tk_function;}
endfunction {TKRETURN(yytext,yyleng); return tk_endfunction;}
discipline {TKRETURN(yytext,yyleng); return tk_discipline;}
potential {TKRETURN(yytext,yyleng); return tk_potential;}
flow {TKRETURN(yytext,yyleng); return tk_flow;}
domain {TKRETURN(yytext,yyleng); return tk_domain;}
ground {TKRETURN(yytext,yyleng); return tk_ground;}
enddiscipline {TKRETURN(yytext,yyleng); return tk_enddiscipline;}
nature {TKRETURN(yytext,yyleng); return tk_nature;}
endnature {TKRETURN(yytext,yyleng); return tk_endnature;}
input {TKRETURN(yytext,yyleng); return tk_input;}
output {TKRETURN(yytext,yyleng); return tk_output;}
inout {TKRETURN(yytext,yyleng); return tk_inout;}
branch {TKRETURN(yytext,yyleng); return tk_branch;}
analog {TKRETURN(yytext,yyleng); return tk_analog;}
begin {TKRETURN(yytext,yyleng); return tk_begin;}
end {TKRETURN(yytext,yyleng); return tk_end;}
if {
    TKRETURN(yytext,yyleng);
    NewIfVariableBlock(gModule);
    return tk_if;
}
while {TKRETURN(yytext,yyleng); return tk_while;}
case {
    TKRETURN(yytext,yyleng);

    return tk_case;
}
endcase {
    TKRETURN(yytext,yyleng);
    gCaseFlag=0;
    return tk_endcase;
}
default {
    TKRETURN(yytext,yyleng);
    NewElseVariableBlock(gModule);
    return tk_default;
}
for {TKRETURN(yytext,yyleng); return tk_for;}
else {
    TKRETURN(yytext,yyleng);
    NewElseVariableBlock(gModule);
    return tk_else;
}
integer {TKRETURN(yytext,yyleng); return tk_integer;}
real {TKRETURN(yytext,yyleng); return tk_real;}
string {TKRETURN(yytext,yyleng); return tk_string;}
from {TKRETURN(yytext,yyleng); return tk_from;}
exclude {TKRETURN(yytext,yyleng); return tk_exclude;}
inf {TKRETURN(yytext,yyleng); return tk_inf;}
INF {TKRETURN(yytext,yyleng); return tk_inf;}

{ident} {TKRETURN(yytext,yyleng); return tk_ident;}

\>\> {TKRETURN(yytext,yyleng); return tk_op_shr;}
\<\< {TKRETURN(yytext,yyleng); return tk_op_shl;}
\&\& {TKRETURN(yytext,yyleng); return tk_and;}
\|\| {TKRETURN(yytext,yyleng); return tk_or;}
\^\~ {TKRETURN(yytext,yyleng); return tk_bitwise_equr;}

\${ident} {TKRETURN(yytext,yyleng); return tk_dollar_ident;}
{char} {TKSTRIPPEDRETURN(yytext,yyleng); return tk_char;}
{b8_int} {TKRETURN(yytext,yyleng); return tk_number;}
{b10_uint} {TKRETURN(yytext,yyleng); return tk_number;}
{b16_int} {TKRETURN(yytext,yyleng); return tk_number;}
{float} {TKRETURN(yytext,yyleng); return tk_number;}

. {posUpdate(yyleng,yytext);return yytext[0];}

%%

int yywrap (void) {return 1;}
