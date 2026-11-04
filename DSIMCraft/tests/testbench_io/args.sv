`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int n=777,r;logic[129:0] h;string text="initial",fmt;reg[31:0] packed_text;
 initial begin
  $display("TRACE TEST %0d %0d %0d %0d",$test$plusargs("mode"),$test$plusargs("mode=long"),$test$plusargs(""),$test$plusargs("missing"));
 r=$value$plusargs("n=%d",n); $display("TRACE DEC %0d %0d",r,n);
 r=$value$plusargs("bad=%d",n); $display("TRACE BAD %0d %h",r,n);
 r=$value$plusargs("absent=%d",n); $display("TRACE ABSENT %0d %h",r,n);
 r=$value$plusargs("h=%h",h); $display("TRACE HEX %0d %h",r,h);
 r=$value$plusargs("s=%s",text); $display("TRACE STR %0d <%s>",r,text);
 r=$value$plusargs("s=%s",packed_text); $display("TRACE PACK %0d <%s> %h",r,packed_text,packed_text);
 fmt="n=%d";r=$value$plusargs(fmt,n); $display("TRACE DYNAMIC %0d %0d",r,n);
 #2;$finish;
 end
endmodule
