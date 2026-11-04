`timescale 1ns/1ps
module bridge(input clk,rst_n,input [7:0] a,output logic [7:0] q);
always @(posedge clk or negedge rst_n) if(!rst_n)q<=0;else q<=a;
endmodule
module top;
logic clk=0,rst_n=0;
logic [7:0] a=1,b=2;
wire [7:0] x,y;
bridge first(clk,rst_n,a,x);
bridge second(clk,rst_n,b,y);
always #1 clk=~clk;
always @(x,y) $display("TRACE ports %h %h",x,y);
initial begin
 #2;rst_n=1;a=3;b=5;
 #2;a<=8'hxx;b<=8'hzz;
 #2;rst_n<=0;a<=7;b<=9;
 #2;rst_n=1;
 #2;if(x!==7||y!==9)$fatal(1,"port batch values");
 #0.5;$display("TRACE done %h %h",x,y);$finish;
end
endmodule
