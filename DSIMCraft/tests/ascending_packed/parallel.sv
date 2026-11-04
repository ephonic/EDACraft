`timescale 1ns/1ps
module leaf #(parameter integer INIT=1)(output logic[0:7] q);
integer i;
initial begin q=0;i=2;#1;q[i+:3]=INIT;#2;q[0:1]=2'b11;end
endmodule
module top(output wire[0:7] one,output wire[7:0] two);
leaf #(1) a(one);leaf #(2)b(two);
endmodule
