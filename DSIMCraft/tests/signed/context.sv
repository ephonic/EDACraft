`timescale 1ns/1ps
module top;
 reg signed [3:0] a,b;
 reg signed [7:0] s;
 reg [7:0] u;
 reg [2:0] c;
 reg [7:0] count,chosen;
 wire [15:0] x0=(a+b)+u,x1=(a>>>1)+u,x2=(a<b)+u,x3=$signed(a+b)+u;
 wire signed [15:0] y0=a+b,y1=-a,y2=a>>>1,y3=(a+b)>>>1;
 wire [15:0] z0=c?a:s,z1=c?a:u,z2=$signed({a}),z3={a},z4={2{a}};
 wire signed [15:0] q0=a/b,r0=a%b;
 initial begin
  a=-7;b=2;s=-1;u=0;c=0;count=0;chosen=0;
  repeat(-1)count=count+1;
  repeat(4'shf)count=count+1;
  case(a) -7:chosen=1;default:chosen=2;endcase
  #1 $display("TRACE context %h %h %h %h %h %h %h %h",x0,x1,x2,x3,y0,y1,y2,y3);
  $display("TRACE branches %h %h %h %h %h %0d %0d count=%0d chosen=%0d",z0,z1,z2,z3,z4,q0,r0,count,chosen);
  c='x;b=-2;
  #1 $display("TRACE mux %b %b",z0,z1);
  a=4'shx;
  #1 $display("TRACE signx %b %b",y0,z2);
 end
endmodule
