`timescale 1ns/1ps
module top;
 logic[15:0] a[];
 logic[7:0] q=0;
 integer hits=0,bad=0;
 initial begin
  a=new[1];a[0]=0;
  #1;{a[0],q}=24'h123456;
  #1;{a[0],q}<=24'h789abc;
  #1;$display("TRACE observe %0d %0d %h %h",hits,bad,a[0],q);
  #1;$finish;
 end
 initial begin
  #0;
  repeat(2)begin
   @(a[0] or q);hits++;
   if((a[0]==16'h1234&&q!=8'h56)||(a[0]==16'h789a&&q!=8'hbc))bad++;
  end
 end
endmodule
