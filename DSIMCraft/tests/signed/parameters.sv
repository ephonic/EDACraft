`timescale 1ns/1ps
module lane #(parameter signed [7:0] P=-3)(output signed [129:0] q,output [3:0] mode);
 localparam signed [64:0] BIG=-65'sd3;
 localparam signed [79:0] NEG=-80'sh3;
 reg signed [129:0] saved=BIG;
 assign q=P+BIG+NEG;
 generate if(BIG<0)begin: negative assign mode=4'd9;end
 else begin: positive assign mode=0;end endgenerate
 initial begin #1 saved<=#1 P;end
endmodule
module top;
 wire signed [129:0] a,b;
 wire [3:0] ma,mb;
 lane u(a,ma);
 lane #(.P(-5)) v(b,mb);
 initial begin #3 $display("TRACE params %0d %0d %h %h",a,b,ma,mb);end
endmodule
