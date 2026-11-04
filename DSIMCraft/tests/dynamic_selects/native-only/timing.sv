`timescale 1ns/1ps
module top;
 logic [15:0] a[],b[],c[];
 integer i=0,k=4;
 logic [15:0] qa=0,qb=0,qc=0;
 event e;
 initial begin
  a=new[2];b=new[1];a[0]=16'h1234;a[1]=16'h5678;b[0]=16'h0;
  a[i][k+:4]<=#2 4'ha;
  a[0][11:8]<=#2 4'hb;
  b[0][k+:4]<=#2 4'hc;
  c[0][k+:4]<=@(e) 4'hd;
  i=1;k=8;a[0][3:0]=4'he;
  #1;b=new[2](b);c=new[1];c[0]=16'h1357;a[0][15:12]=4'hf;
  ->e;
  #2;qa=a[0];qb=b[0];qc=c[0];
  $display("TRACE nba %h %h %h %h",qa,a[1],qb,qc);
  i=0;k=0;
  fork
   begin a[i][k+:4]=#2 4'h9;end
   begin #1;i=1;k=12;end
  join
  qa=a[0];
  $display("TRACE blocking %h %h",qa,a[1]);
  #1;$finish;
 end
endmodule
