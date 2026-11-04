`timescale 1ps/1ps
module top;
 reg raw=0,en=1;
 wire source,a,x,y;
 assign #2 source=raw;
 bufif1 #(1,2,3) b(a,source,en);
 dut d(a,x,y);
 initial begin
  #30;$display("TRACE combined raw=%b a=%b x=%b y=%b",raw,a,x,y);
  raw<=#1 1;#30;$display("TRACE combined raw=%b a=%b x=%b y=%b",raw,a,x,y);
  en=0;#30;$display("TRACE combined raw=%b a=%b x=%b y=%b",raw,a,x,y);
  en=1;raw<=#1 1'bx;#30;$display("TRACE combined raw=%b a=%b x=%b y=%b",raw,a,x,y);
  $finish;
 end
endmodule
