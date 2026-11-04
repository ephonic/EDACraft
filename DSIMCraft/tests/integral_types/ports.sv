`timescale 1ns/1ps
module typed(input integer x,input integer unsigned y,input time t,
 output integer z,output integer unsigned u,output time stamp,output reg signed[63:0] signstamp);
always @* begin z=x/3;u=y/3;stamp=t+1;signstamp=x;end
endmodule
module nonansi(x,t,z,u);
 input integer x;
 input signed[63:0] t;
 output reg signed[63:0] z;
 output integer unsigned u;
 always @* begin z=t+x;u=x;end
endmodule
module top;
integer x=-9;
integer unsigned y=32'hffffffff;
time t=64'h123456789abcdef0;
wire signed[31:0]z;wire[31:0]u;wire[63:0]stamp;wire signed[63:0]signstamp,z2;wire[31:0]u2;
typed a(x,y,t,z,u,stamp,signstamp);
nonansi b(x,t,z2,u2);
initial begin
 #1;$display("TRACE ports %0d %0d %h %0d %h %h",z,u,stamp,signstamp,z2,u2);
 x=12;y=99;t=64'h8000000000000000;
 #1;$display("TRACE ports %0d %0d %h %0d %h %h",z,u,stamp,signstamp,z2,u2);
 x=32'bx;t=64'bz;
 #1;$display("TRACE unknown %h %h %h %h",z,u2,z2,stamp);$finish;
end
endmodule
