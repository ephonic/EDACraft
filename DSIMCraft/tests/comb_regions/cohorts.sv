`timescale 1ns/1ps
module top;
logic [7:0] a=0,b=1;
wire [7:0] x=a+1,y=a^8'hff,z=a<<1;
wire [7:0] u=x+y,v=x-y;
wire [7:0] sum=a+b,difference=a-b,unknown=a^b;
always @(x) $display("TRACE x %h %h %h %h",x,y,z,sum);
always @(u) $display("TRACE u %h %h",u,v);
initial begin
 #1;a=1;#0;a=2;#1;a=8'hxx;#1;a=8'hzz;#1;a=3;b=2;
 #1;if(x!==4||y!==8'hfc||z!==6||sum!==5||difference!==1)$fatal(1,"cohort values");
 $display("TRACE done %h %h %h %h %h",x,y,z,u,v);
end
endmodule
