`timescale 1ns/1ps
module top;
parameter logic[0:7] P=8'h96;parameter logic[-4:3] N=8'ha5;
integer i;
initial begin
 for(i=-2;i<10;i=i+1)begin #1;$display("TRACE PARAM %0d %b %b %b %b",i,P[i],P[i+:4],P[i-:4],N[i-4+:4]);end
 $display("TRACE FOLDED %h %h %h",P[0:3],N[-4:-1],P[0+:4]);$finish;
end
endmodule
