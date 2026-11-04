`timescale 1ns/1ps
module top;
 reg clk=0,x=0,y=0;integer seen=-1;
 a: assert property(@(posedge clk) 1) begin x=1;y<=1;end
 always @(x) if(x) seen=y;
 initial begin #5;clk=1;#1;$display("TRACE reactive %0d %0d",seen,y);$finish;end
endmodule
