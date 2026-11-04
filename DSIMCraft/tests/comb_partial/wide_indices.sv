`timescale 1ns/1ps
module top;
logic[15:0] a,u,seen_u;
logic[-1:-16] n;
logic[129:0] wide;
logic[3:0] patch,read_wide,read_negative;
logic signed[127:0] big;
logic[127:0] unsigned_big;
integer index;
always_comb begin
 wide={2'bxz,{8{a}}};wide[big+:4]=patch;read_wide=wide[big+:4];
 n=a;n[index+:4]=patch;read_negative=n[index+:4];
 u=a;u[unsigned_big+:4]=patch;seen_u=u;
end
initial begin
 a=16'h1234;patch=4'b0110;big=-2;index=-17;unsigned_big=128'h00000000000000010000000000000100;
 #1;$display("TRACE indices %b %b %b %b %b %b",wide,read_wide,n,read_negative,u,seen_u);
 big=128;index=-2;unsigned_big=14;
 #1;$display("TRACE indices %b %b %b %b %b %b",wide,read_wide,n,read_negative,u,seen_u);
 big=128'h00000000000000008000000000000100;index=-2147483648;unsigned_big=128'h00000000000000008000000000000100;
 #1;$display("TRACE indices %b %b %b %b %b %b",wide,read_wide,n,read_negative,u,seen_u);
 big=128'hffffffffffffffff7fffffffffffff00;index=2147483647;unsigned_big=128'bx;
 #1;$display("TRACE indices %b %b %b %b %b %b",wide,read_wide,n,read_negative,u,seen_u);$finish;
end
endmodule
