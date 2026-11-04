`timescale 1ns/1ps
module lane #(parameter V=1)(output wire [1:0] result);
logic [3:0] q;
always_comb q[3:2]=q[1:0];
assign result=q[3:2];
initial begin #1;q[1:0]=0;#1;q[1:0]=V;#1;q[1:0]=2'bxz;#1;q[1:0]=V;end
endmodule
module top(output wire[1:0] one,two);
lane #(1)a(one);lane #(2)b(two);
endmodule
