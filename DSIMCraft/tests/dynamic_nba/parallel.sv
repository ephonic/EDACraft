`timescale 1ns/1ps
module worker(output integer result);
integer a[];logic clk=0;
initial begin
 a=new[2];a[0]=0;a[1]=0;
 a[0]<=#2 10;a[1]<=@(posedge clk)32;
 #1;clk=1;#2;result=a[0]+a[1];
end
endmodule
module top;
wire signed[31:0] one,two;
worker u(one),v(two);
endmodule
