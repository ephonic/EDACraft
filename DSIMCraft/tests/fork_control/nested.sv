`timescale 1ns/1ps
module top;integer q=0,r=0;
initial begin fork begin #2;q=1;fork begin #8;r=9;end join_none end join_none
wait fork;$display("TRACE direct %0d %0d %0t",q,r,$time);
disable fork;#10;$display("TRACE descendants %0d %0d %0t",q,r,$time);$finish;end endmodule
