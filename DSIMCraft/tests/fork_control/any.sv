`timescale 1ns/1ps
module top;integer a=0,b=0,k=0;
initial begin fork begin #2;a=1;end begin #5;b=1;end join_any
$display("TRACE any %0d %0d %0t",a,b,$time);wait fork;
$display("TRACE all %0d %0d %0t",a,b,$time);for(k=0;k<3;k++)begin fork begin #1;a=a+1;end join_none wait fork;end
$display("TRACE recycle %0d %0t",a,$time);#1;$finish;end endmodule
