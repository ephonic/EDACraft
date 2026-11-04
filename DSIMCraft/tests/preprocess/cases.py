"""Independent preprocessor fixtures. Expected traces are constants, not dsim output."""
CASES={
 'library_suffixes':dict(files={'lists/input.f':'+libext+.v+.sv\n../top.v\n','top.v':'module top; initial $display("TRACE suffixes=23"); endmodule\n'},args=['-F','lists/input.f'],iv_args=['top.v'],vcs_args=['-F','lists/input.f'],expected=['TRACE suffixes=23']),
 'strings':dict(files={'top.v':r'''module top;
initial begin $display("TRACE a"); $display("TRACE b");
 $display("TRACE quote=\"two\" slash=\\ literal=`NO_MACRO");
 /* `include "missing" */ $display("TRACE numeric=%02h",8'ha5); $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE a','TRACE b','TRACE quote="two" slash=\\ literal=`NO_MACRO','TRACE numeric=a5']),
 'functions':dict(files={'top.v':'''`define CONST 8'd5
`define ADD(a,b=8'd3) ((a)+(b))
`define TAKE(a,b) ((a)^(b))
`define CAT(a,b) a``b
`define STR(a) `"a`"
`define ZERO(v=8'd9) v
module top;
wire [7:0] `CAT(v,alue); assign value=`ADD(`CONST);
initial begin
 #1; $display("TRACE function=%0d concat=%h zero=%0d",value,`TAKE({4'hf,4'h0},8'h0f),`ZERO());
 $display(`STR(TRACE quoted=hello)); $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE function=8 concat=ff zero=9','TRACE quoted=hello']),
 'conditionals':dict(files={'top.v':'''`define OUTER
`ifdef NEVER
`include "absent.vh"
`BAD_UNDEFINED syntax invalid %
`elsif OUTER
 `ifndef INNER
  `define PICK 8'd13
 `else
  `define PICK 8'd2
 `endif
`else
 `define PICK 8'd1
`endif
`undef OUTER
`ifdef OUTER
 `define WRONG
`endif
`ifdef WRONG
 nonsense
`endif
module top; initial begin $display("TRACE picked=%0d",`PICK); $finish; end endmodule
'''},args=['top.v'],expected=['TRACE picked=13']),
 'includes':dict(files={'top.v':'''`include "settings.vh"
`include "settings.vh"
`define FILE "value.vh"
`include `FILE
module top; reg [7:0] q; initial begin q=`VAL; $display("TRACE includes=%0d",q); $finish; end endmodule
''','inc/settings.vh':'''`ifndef SETTINGS_GUARD
`define SETTINGS_GUARD
`include "nested.vh"
`endif
''','inc/nested.vh':"`define SEED 8'd17\n",'inc/value.vh':'`define VAL `SEED\n','inc2/value.vh':"`define VAL 8'd99\n"},args=['+incdir+inc+inc2','top.v'],iv_args=['-Iinc','-Iinc2','top.v'],expected=['TRACE includes=17']),
 'filelists':dict(files={'lists/root.f':'''// relative to this -F file
+incdir+../inc
+define+LIST_FLAG+AMOUNT=8'd6
-F sub/child.f
"../top space.v"
''','lists/sub/child.f':'../../child.v\n','child.v':'''`define GLOBAL 8'd4
module child(input [7:0] a,output [7:0] y); assign y=a+`GLOBAL; endmodule
''','inc/defs.vh':'''`ifdef LIST_FLAG
`define PORT_VALUE `AMOUNT
`else
`define PORT_VALUE 8'd99
`endif
''','top space.v':'''`include "defs.vh"
module top; wire [7:0] y; child u(`PORT_VALUE,y);
initial begin #1; $display("TRACE lists=%0d",y); $finish; end endmodule
'''},args=['-F','lists/root.f'],vcs_args=['-F','lists/root.f'],iv_args=['-Iinc','-DLIST_FLAG',"-DAMOUNT=8'd6",'child.v','top space.v'],expected=['TRACE lists=10']),
 'cwd_filelist':dict(files={'lists/root.f':'''# paths in -f are cwd-relative
-f lists/inner.f
+define+CMD=8'd12
''','lists/inner.f':'top.v\n','top.v':'''module top; initial begin $display("TRACE cwd=%0d",`CMD); $finish; end endmodule
'''},args=['-f','lists/root.f'],iv_args=["-DCMD=8'd12",'top.v'],expected=['TRACE cwd=12']),
 'flags':dict(files={'top.v':'''`ifdef REMOVED
invalid skipped syntax
`endif
`define LOCAL `VALUE
module top; initial begin $display("TRACE flags=%0d",`LOCAL); $finish; end endmodule
'''},args=['-DREMOVED','-UREMOVED','-D',"VALUE=8'd21",'top.v'],vcs_args=["+define+VALUE=8'd21",'top.v'],iv_args=["-DVALUE=8'd21",'top.v'],expected=['TRACE flags=21']),
 'continued':dict(files={'top.v':'''`define UPDATE(a) \\
 a <= a + 8'd3; \\
 a[7:4] <= 4'ha;
module top; reg [7:0] q;
initial begin q=0; #1; `UPDATE(q)
 #0; $display("TRACE before=%h",q); #1;
 $display("TRACE after=%h",q); $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE before=00','TRACE after=a3']),
 'builtins':dict(files={'top.v':'''`include "inc/location.vh"
module top; initial begin
 $display("TRACE line=%0d",`__LINE__);
 `REPORT
 $finish;
end endmodule
''','inc/location.vh':'''`define REPORT $display("TRACE call_line=%0d",`__LINE__);
'''},args=['top.v'],expected=['TRACE line=3','TRACE call_line=4']),
}

def materialize(root,name):
    case=CASES[name]
    for filename,text in case['files'].items():
        p=root/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    return case

def trace(text):return [s for s in text.splitlines() if s.startswith('TRACE ')]

CASES['inline']=dict(files={'top.v':'''`define X
module top; initial begin
`ifdef X $display("TRACE inline=yes"); `else $display("TRACE inline=no"); `endif
$finish; end endmodule
'''},args=['top.v'],expected=['TRACE inline=yes'])
CASES['macro_quotes']=dict(files={'top.v':'''`define TEXT(a) `"a`"
`define V hello
module top; initial begin $display(`TEXT(TRACE macro=`V)); $finish; end endmodule
'''},args=['top.v'],expected=['TRACE macro=hello'])
CASES['escaped']=dict(files={'top.v':r'''module top;
wire [7:0] \`specify ; assign \`specify =8'd23;
initial begin #1; $display("TRACE escaped=%0d",\`specify ); $finish; end endmodule
'''},args=['top.v'],iv_failure='macro specify undefined',expected=['TRACE escaped=23'])

CASES['include_conditional']=dict(files={'top.v':'`define ENABLE\n`include "open.vh"\n`define PICK 8\'d42\n`endif\nmodule top; initial begin $display("TRACE conditional_include=%0d",`PICK); $finish; end endmodule\n','open.vh':'`ifdef ENABLE\n'},args=['top.v'],expected=['TRACE conditional_include=42'])

# UVM-style macro bodies: // comments end physically, while a final
# backslash keeps the definition open for the following code line.
CASES['comment_continuation']=dict(files={'top.v':r'''`define DECL(SFX,BASE=5) \
  int field``SFX = BASE; // ignored `MISSING " /* \
  int other``SFX = BASE+1; // second comment \
  int last``SFX = BASE+2;
module top;
  `DECL(_a)
  `DECL(_b,10)
  initial begin
    $display("TRACE comments=%0d,%0d,%0d %0d,%0d,%0d",field_a,other_a,last_a,field_b,other_b,last_b);
    $finish;
  end
endmodule
'''},args=['top.v'],expected=['TRACE comments=5,6,7 10,11,12'])

CASES['comments_crlf']=dict(files={'top.v':r'''// Outside a definition this backslash does not continue code: \
`define VALUE 9
`define STEP(a) \
  a = a + 1; // hidden `MISSING \
  a = a + 2;
module top;
int n;
initial begin
 n=`VALUE;
 `STEP(n)
 $display("TRACE crlf=%0d line=%0d",n,`__LINE__);
 $finish;
end
endmodule
// final comment with no newline \
'''.replace('\n','\r\n').rstrip('\r\n')},args=['top.v'],vcs_failure='Error-[SE] Syntax error',vcs_difference='CRLF after a continued // comment: native normalizes physical line endings; VCS W-2024.09 rejects line 5',expected=['TRACE crlf=12 line=11'])

CASES['expanded_conditionals']=dict(files={'top.v':r'''`define FIRST
`define THIRD
`define VALUE 19
`define CHOOSE(flag) \
 `ifdef flag \
  `ifdef FIRST $display("TRACE chosen=%0d",`VALUE); \
  `else $display(`"unreachable `MISSING`"); `endif \
 `elsif SECOND `UNDEFINED_MACRO(garbage) \
 `else $display("TRACE fallback"); `endif
`define INNER \
 `ifdef FIRST $display("TRACE inner"); `else `MISSING `endif
`define OUTER \
 `ifndef FIRST `MISSING \
 `elsif THIRD `INNER \
 `else `MISSING `endif
module top;initial begin
 `CHOOSE(THIRD)
 `OUTER
 $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE chosen=19','TRACE inner'])

CASES['expanded_boundaries']=dict(files={'top.v':r'''`define YES
`define OPEN `ifdef YES
`define CLOSE `endif
module top;initial begin
 `OPEN
 $display("TRACE opened");
 `else `MISSING
 `endif
 `ifdef NO
 `MISSING
 `elsif YES
 $display("TRACE closed");
 `CLOSE
 $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE opened','TRACE closed'])

CASES['pasted_quotes']=dict(files={'top.v':r'''`define NAME(SFX) `"TRACE type=packet_``SFX`"
`define LABEL block
`define NESTED(SFX) `"TRACE nested=`LABEL``SFX`"
`define PLAIN(SFX) "TRACE literal=SFX``kept"
module top;initial begin
 $display(`NAME(7));
 $display(`NESTED(_tag));
 $display(`PLAIN(unused));
 $finish;
end endmodule
'''},args=['top.v'],expected=['TRACE type=packet_7','TRACE nested=block_tag','TRACE literal=unusedkept'])
