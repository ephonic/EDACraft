`timescale 1ns/1ps
module top;
 reg clk=0,q=1;integer count=0;
 a: assert property(@(posedge clk) q) count=count+1;
 initial begin #5;clk=1;clk=0;clk=1;#1;$display("TRACE glitch %0d",count);$finish;end
endmodule
