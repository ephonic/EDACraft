`timescale 1ns/1ps
module top;
 reg clk=0,a=1,b=0,rst=0;integer pass=0,fail=0;
 always #5 clk=~clk;
 a1: assert property(@(posedge clk) disable iff(rst) a |=> b) pass=pass+1;else fail=fail+1;
 initial begin
  #7;rst=1;#1;rst=0;
  #9;rst=1;#1;rst=0;
  #10;b=1;#10;rst=1;#10;rst=0;b=0;
  #10;$display("TRACE disable %0d %0d",pass,fail);$finish;
 end
endmodule
