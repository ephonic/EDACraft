`timescale 1ns/1ps
module top;
 logic [15:0] a[];
 bit [15:0] b[];
 logic [95:0] w[];
 integer i=0,k=4;
 logic [15:0] q=0;
 logic [95:0] wide=0;
 initial begin
  a=new[2];b=new[1];w=new[1];a[0]=16'h1234;a[1]=16'habcd;b[0]=16'hffff;w[0]=96'h123456789abcdef001234567;
  a[i][7:4]=4'hf;a[i][k+:4]+=1;a[1][11-:4]=4'h2;
  a[0][0]++;a[0][15]=1'bx;b[0][7:4]=4'bxz10;
  w[0][70+:12]=12'hdef;w[0][4]=1'bz;
  q=a[0];wide=w[0];
  $display("TRACE values %h %h %h %h %h %h",q,a[1],b[0],wide,a[0][k+:8],w[0][81:70]);
  k=14;a[0][k+:4]=4'b0101;k=3;a[1][k-:4]=4'b1010;
  $display("TRACE clipped %h %h %b %b",a[0],a[1],a[0][14+:4],a[1][3-:4]);
  k='x;a[0][k+:4]=4'hf;q=a[0];
  $display("TRACE invalid %h %b %b %b",q,a[0][k],a[10][2:0],b[10][2:0]);
  #1;$finish;
 end
endmodule
