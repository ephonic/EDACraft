`timescale 1ns/1ps
module top;integer q=0,r=0,late=0,x=0;
initial begin fork begin r=q;#2;r=r+1;end join_none
fork begin #3;x=1;end join_none
q=7;$display("TRACE before %0d %0d",q,r);#0;$display("TRACE after %0d %0d",q,r);
wait fork;$display("TRACE done %0d %0d %0d %0t",q,r,x,$time);#2;
$display("TRACE lifetime %0d",late);$finish;end
initial begin fork begin #3;late=9;end join_none end endmodule
