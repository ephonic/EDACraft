`timescale 1ns/1ps
module top;
`ifdef FIXED_REFERENCE
 logic[15:0] a[1];bit[7:0] b[1];
`else
 logic[15:0] a[];bit[7:0] b[];
`endif
 logic[7:0] q=0;
 logic[15:0] observed=0;
 integer k=4;
 event e;
 initial begin
`ifndef FIXED_REFERENCE
  a=new[1];b=new[1];
`endif
  a[0]=16'h1234;b[0]=8'hff;
  {a[0][k+:4],b[0][3:0],q}<=#1 16'habcd;
  {a[0][3:0],a[0][7:4]}<=#1 8'h56;
  {a[0][15:12],q[3:0]}<=repeat(2)@(e)8'h78;
  k=8;
  #1;->e;#1;->e;#1;
  observed=a[0];$display("TRACE native packed %h %h %h",observed,b[0],q);
  #1;$finish;
 end
endmodule
