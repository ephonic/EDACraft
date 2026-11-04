`timescale 1ns/1ps
module top;integer q=0,r=0;
initial begin
fork begin #1;q<=11;end begin #1;r<=22;end join
$display("TRACE join %0d %0d",q,r);#0;$display("TRACE inactive %0d %0d",q,r);
#1;$display("TRACE settled %0d %0d",q,r);$finish;end
endmodule
