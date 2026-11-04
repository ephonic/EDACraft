// 8x8 unsigned multiplier
module mul8 (a, b, p);

input [7:0] a;
input [7:0] b;
output [15:0] p;

assign p = a * b;

endmodule
