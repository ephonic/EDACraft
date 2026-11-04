`timescale 1ns/1ps
module top;
 reg [31:0] i,q;
 initial begin
  q=32'h87654321;
  for(i=0;i<10003;i=i+1)q=q*32'd1664525+32'd1013904223;
  $display("TRACE arithmetic %h %0d",q,i);#1;$finish;
 end
endmodule
