`timescale 1ns/1ps
module top;
int sum;byte counter;bit[7:0] bits;reg[7:0] four;integer index;integer seen;
initial begin
sum=0;bits=8'hff;four=8'hxz;
for(int i=0;i<4;i++)sum+=i;
for(byte j=-2;j<2;j++)sum+=j;
for(shortint unsigned k=0;k<3;k++)sum+=k;
for(longint m=0;m<2;m++)sum+=m;
$display("TRACE loops %0d %0d",sum,counter);
index=32'hx;seen=++bits[index];$display("TRACE increment %h %h",seen,bits);
{bits[7:4],four[3:0]}=8'bxz10xz01;$display("TRACE concat %h %h",bits,four);
bits<=#2 8'b1xz001zx;counter<=#1 8'b1xz001zx;#1;
$display("TRACE time1 %h %h",bits,counter);#2;$display("TRACE time3 %h %h",bits,counter);$finish;
end
endmodule
