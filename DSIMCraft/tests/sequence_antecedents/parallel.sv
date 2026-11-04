`timescale 1ns/1ps
module lane #(parameter PERIOD=5,EDGES=20)(output integer passed=0);
reg clk=0,a=1;integer failed=0;
initial repeat(EDGES) #(PERIOD)clk=~clk;
sequence prefix;a ##2 a;endsequence
assert property(@(posedge clk) prefix |=> a)passed++;else failed++;
endmodule
module top;
wire [31:0] one,two;
lane #(5,20)a(one);lane #(7,14)b(two);
endmodule
