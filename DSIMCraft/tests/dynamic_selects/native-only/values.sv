`timescale 1ns/1ps
module top;
`ifdef FIXED_REFERENCE
 logic [15:0] a[1];bit [15:0] b[1];logic [95:0] w[1];
`else
 logic [15:0] a[];bit [15:0] b[];logic [95:0] w[];
`endif
 logic [15:0] q=0,r=0;
 logic [95:0] wide=0;
 integer i=0,k=4;
 event e;
 initial begin
`ifndef FIXED_REFERENCE
  a=new[1];b=new[1];w=new[1];
`endif
  a[0]=0;b[0]=16'hffff;w[0]=0;
  a[i][0]<=1'b1;a[0][7:4]<=#0 4'hb;
  a[0][15:8]<=#1 8'hac;b[0][k+:4]<=#1 4'bxz10;
  w[0][69+:17]<=#1 17'h1abcd;
  a[0][3:1]<=repeat(2)@(e)3'b101;
  i=7;k=12;
  #1;->e;#1;->e;#1;
  q=a[0];r=b[0];wide=w[0];
  $display("TRACE native values %h %h %h",q,r,wide);
  #1;$finish;
 end
endmodule
