`timescale 1ns/1ps
module top;
logic [7:0] a=0,b=1,c=2;
wire [7:0] x=a,y=b,z=a,w=c,v=b;
wire [7:0] chain=x+y,chain2=chain^z;
logic [7:0] sampled=0;
always @(x,y,z,w,v) begin
 $display("TRACE outputs %h %h %h %h %h",x,y,z,w,v);
 sampled<=x^y^z^w^v;
end
always @(chain2) $display("TRACE chain %h",chain2);
initial begin
 #1;a=3;b=4;c=5;
 #1;a<=9;b<=10;c<=11;a<=12;
 #1;a=8'hxx;#0;b=8'hzz;#0;c=8'hx7;
 #1;c=7;b=6;a=5;
 #1;if(x!==5||y!==6||z!==5||w!==7||v!==6||sampled!==(5^6^5^7^6))$fatal(1,"masked batch values");
 $display("TRACE done %h %h %h %h %h %h",x,y,z,w,v,chain2);
end
endmodule
