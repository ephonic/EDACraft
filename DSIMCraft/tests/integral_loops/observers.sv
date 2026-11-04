`timescale 1ns/1ps
module top;
 reg [7:0] q=0;integer i=0,changes=0;wire [7:0] next=q+1;
 always @(q)changes=changes+1;
 initial begin
  #1;for(i=0;i<19;i++)q=q+3;
  #1;$display("TRACE observed %h %h %0d",q,next,changes);
  force q=8'h51;
  for(i=0;i<7;i=i+1)q=q+1;
  $display("TRACE force %h %0d",q,i);release q;
  #1;$finish;
 end
endmodule
