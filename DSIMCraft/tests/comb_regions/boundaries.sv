`timescale 1ns/1ps
module top;
logic [7:0] a=0,b=0;
wire [7:0] x=a+b,y=a-b,z=a^b;
wire [7:0] u=x+y,v=x-y;
logic [7:0] sampled=0;
always @(x)begin
 $display("TRACE wake %h %h %h %h",x,y,z,sampled);
 sampled<=x;
end
initial begin
 #1;a<=1;b<=2;a<=3;
 #1;if(x!==5||y!==1||z!==1||sampled!==5)$fatal(1,"NBA boundary");
 a=7;#0;b=4;#0;a=8'hx7;
 #1;a<=9;b<=5;
 #1;if(x!==14||y!==4||sampled!==14)$fatal(1,"settled boundary");
 $display("TRACE boundary %h %h %h %h %h",x,y,z,u,v);
end
endmodule
