`timescale 1ns/1ps
module tb;
 reg clk=0; reg [31:0] a=1,b=3; reg [31:0] q=0; integer n=0;
 wire [31:0] x=a+b;
 wire [31:0] y=x^32'h12345678;
 wire [31:0] z=y+q;
 always #5 clk=~clk;
 always @(posedge clk) begin q<=z; n<=n+1; end
 always @(negedge clk) begin a=a+1; b=b^a; end
 initial begin repeat(4) @(negedge clk); #1; $display("PROBE %h %h %h %0d",x,y,z,n); $finish; end
endmodule
