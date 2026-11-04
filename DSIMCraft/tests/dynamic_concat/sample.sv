`timescale 1ns/1ps
module top;
 logic[15:0] a[],b[];
 logic[7:0] fixed_words[2];
 logic[7:0] q=0;
 logic[15:0] out_a=0,out_b=0;
 integer i=0,k=4;
 initial begin
  a=new[2];b=new[1];a[0]=16'h1234;a[1]=16'h5678;b[0]=16'h9abc;fixed_words[0]=0;fixed_words[1]=0;
  {a[0],b[0],q}=40'h123456789a;
  $display("TRACE whole %h %h %h",a[0],b[0],q);
  {a[i][k+:4],fixed_words[i],q[3:0],b[0][7:0]}=24'habcdef;
  {a[0][7:0],a[0][11:4]}=16'h1234;
  out_a=a[0];out_b=b[0];
  $display("TRACE mixed %h %h %h %h",out_a,out_b,q,fixed_words[0]);
  i=8;{a[i],q}=24'hffff73;
  {a[i],fixed_words[i],q}=32'h12345673;
  {a[0],a[0]}=32'h12345678;
  out_a=a[0];
  $display("TRACE overlap %h %h",out_a,q);
  #1;$finish;
 end
endmodule
