`timescale 1ns/1ps
module top;integer q=0;initial begin
wait fork;disable fork;fork join_any q=q+1;fork join_none q=q+1;
fork begin #1;disable fork;q=q+1;end begin #2;q=q+1;end join
wait fork;#1;$display("TRACE empty %0d %0t",q,$time);$finish;end endmodule
