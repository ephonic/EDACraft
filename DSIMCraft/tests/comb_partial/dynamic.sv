`timescale 1ns/1ps
module top;
logic [15:0] a,q,seen;
logic [3:0] patch;
integer index;
always_comb begin q=a;q[index+:4]=patch;seen=q;end
initial begin
 a=16'h1234;index=4;patch=4'bxz01;
 #1;$display("TRACE dynamic %b %b",q,seen);
 index=14;patch=4'b0110;
 #1;$display("TRACE dynamic %b %b",q,seen);
 index=-2;
 #1;$display("TRACE dynamic %b %b",q,seen);
 index=32'bx;
 #1;$display("TRACE dynamic %b %b",q,seen);
 index=20;a=16'habcd;
 #1;$display("TRACE dynamic %b %b",q,seen);$finish;
end
endmodule
