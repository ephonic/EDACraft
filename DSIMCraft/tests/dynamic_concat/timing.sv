`timescale 1ns/1ps
module top;
 logic[15:0] a[];
 logic[7:0] q=0,r=0;
 integer i=0,k=0;
 logic[15:0] observed=0;
 event e;
 initial begin
  a=new[2];a[0]=16'h1234;a[1]=16'habcd;
  {a[i],q}<=#2 24'h56789a;
  i=1;
  #1;a[0][3:0]=4'hf;
  #2;observed=a[0];$display("TRACE delay %h %h %h",observed,a[1],q);
  {a[i],r}<=@(e)24'h765432;
  #1;a=new[3](a);i=0;->e;
  #1;observed=a[1];$display("TRACE event %h %h",observed,r);
  {a[0],q}<=#2 24'hffff71;
  #1;a=a;
  #2;observed=a[0];$display("TRACE replaced %h %h",observed,q);
  fork
   begin {a[i][k+:4],q}=#2 12'hbcd;end
   begin #1;i=2;k=8;a[2]=0;end
  join
  observed=a[2];$display("TRACE blocking %h %h",observed,q);
  #1;$finish;
 end
endmodule
