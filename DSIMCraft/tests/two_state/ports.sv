`timescale 1ns/1ps
module typed(input bit[7:0] a,input byte b,input shortint s,input int i,input longint l,output bit[7:0] q,output byte r,output shortint t,output int u,output longint v);
always @* begin q=a;r=b/3;t=s/3;u=i/3;v=l/3;end
endmodule
module legacy(a,q);input int unsigned a;output longint unsigned q;always @* q=a;endmodule
module top;
reg[7:0] a=8'b1xz001zx,b=8'hfa;reg[15:0] s=16'hfff1;reg[31:0] i=32'hffffffeb;reg[63:0] l=64'hffffffffffffffdf;
wire[7:0]q;wire signed[7:0]r;wire signed[15:0]t;wire signed[31:0]u;wire signed[63:0]v;wire[63:0]w;
typed dut(a,b,s,i,l,q,r,t,u,v);legacy other(i,w);
initial begin
#1;$display("TRACE ports %h %0d %0d %0d %0d %h",q,r,t,u,v,w);
a=8'hxz;b=8'bx1z1;s=16'hxz00;i=32'hxz01;l=64'hxz01020304050607;
#1;$display("TRACE ports %h %0d %0d %0d %0d %h",q,r,t,u,v,w);
a=1;b=9;s=12;i=15;l=18;
#1;$display("TRACE ports %h %0d %0d %0d %0d %h",q,r,t,u,v,w);$finish;
end
endmodule
