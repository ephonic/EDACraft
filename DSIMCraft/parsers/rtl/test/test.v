

// This design checks different logical and shift operators on one
// bit signed/unsigned variables. Mainly logical and shifting
// operators are used here.

module test020(clk, in0, in1, in2, in3, in4, in5, in6, in7, out1, out2);

input clk;
input signed in0;
input in1;
input signed [0:0] in2;
input [0:0] in3;
input signed [1:1] in4;
input [1:1] in5;
input signed [11:11] in6;
input [11:11] in7;
output reg signed [2:2] out1, out2;

reg l1;
reg signed l2;
reg signed [0:0] l3;
reg signed [1:1] l4;

always @(negedge clk)
begin
	l1 = in1 && in2;
	l2 = (in4 || in5) && !in6;
	l3 = (in7 << 1) - (in7 >> 1);
	l4 = ((in3 <<< 1) || in2) + ((in5 >>> 1) && in6);

	out1 = l1 || !l2;
	out2 = !l1 + l2;
end

endmodule

