`timescale 1ns/1ps
module top;
 reg clk=0,a=1,b=0;integer fail=0,yes=0,cov=0;
 always #5 clk=~clk;
 aa: assume property(@(posedge clk) a |-> b) yes=yes+1;else fail=fail+1;
 cc: cover property(@(posedge clk) b) cov=cov+1;
 initial begin
  #2;b=1'bx;#10;b=1'bz;#10;a=1'bx;#10;a=1'bz;#10;a=1;b=1;
  #10;$display("TRACE fourstate %0d %0d %0d",yes,fail,cov);$finish;
 end
endmodule
