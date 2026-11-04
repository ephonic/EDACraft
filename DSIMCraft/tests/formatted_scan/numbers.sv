`timescale 1ns/1ps
module top;
`ifdef VCS_REFERENCE
 initial begin $dumpfile("wave.vcd");$dumpvars(0,top);end
`endif
 reg[127:0] a,b;int n;string word;
 task check(input string source,input string fmt);
  #1;a='1;b='1;n=$sscanf(source,fmt,a,b);
  $display("TRACE NUM <%s> <%s> %0d %h %h",source,fmt,n,a,b);
 endtask
 initial begin
  check(" -123456789012345678901234567890 17","%d%d");
  check("ABCDEF0123456789abcdef0123456789 1010xz?1","%h%b");
  check("7777777777777777 0x12","%o%h");
  check("xZ","%2d%c");check("z ?","%d%d");
  check("_12_3x","%d%c");check("12oops","%d%c");
  check("+12 -12","%d%d");check("+ab","%h%c");
  check("0b10","%b%c");check("8","%o%c");
  check("", "%d%d");check("oops","%d%d");check("-","%d%d");
  #1;n=$sscanf("  alpha,beta  Z","%5s,%*s %c",word,a);
  $display("TRACE TEXT %0d <%s> %h",n,word,a);
  #1;$finish;
 end
endmodule
