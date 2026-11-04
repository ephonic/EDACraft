`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 int n,a,b;reg[15:0]empty_packed=0;reg[63:0]packed_source="123 456";string s,fmt,empty="";
 initial begin
  #1;n=$sscanf("tag=17,% skip 23 end","tag=%2d,%% %*s %d end",a,b);$display("TRACE LIT %0d %0d %0d",n,a,b);
  #1;n=$sscanf("tag!17","tag=%d",a);$display("TRACE MISMATCH %0d %0d",n,a);
  #1;n=$sscanf(empty,"x");$display("TRACE LITEOF %0d",n);
  #1;n=$sscanf("","x");a=$sscanf(empty_packed," ");$display("TRACE PACKEMPTY %0d %0d",n,a);
  #1;n=$sscanf("12","%*d%d",a);$display("TRACE SUPEOF %0d %0d",n,a);
  #1;n=$sscanf("abc","%*c");$display("TRACE SUPONLY %0d",n);
  #1;fmt="%2d%d";n=$sscanf(packed_source,fmt,a,b);$display("TRACE PACKED %0d %0d %0d",n,a,b);
  #1;n=$sscanf("  \n\t", " \t\n");$display("TRACE SPACE %0d",n);
  #1;n=$sscanf("abcdef G","%3s%c",s,a);$display("TRACE WIDTH %0d <%s> %h",n,s,a);
  #1;$finish;
 end
endmodule
