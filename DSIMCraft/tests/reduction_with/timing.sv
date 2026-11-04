`timescale 1ns/1ps
module top;
 logic[7:0] a[2]='{1,2},d[];
 integer bias=1,comb,ds,nb,delayed;logic refresh=0;
 always_comb comb=a.sum with(int'(item)+bias);
 always_comb begin if(refresh)ds=d.sum with(int'(item)+bias);else ds=d.sum with(int'(item)+bias);end
 initial begin
  d=new[2];d[0]=4;d[1]=5;refresh=~refresh;
  nb<=#2 a.sum with(int'(item)+bias);delayed<=#2 d.product with(int'(item)+bias);
  #1;a[0]=10;d[0]=20;bias=2;refresh=~refresh;
  #2;$display("TRACE timing %0d %0d %0d %0d",comb,ds,nb,delayed);
  d=new[3](d);d[2]=7;a[1]=3;refresh=~refresh;
  #1;$display("TRACE resize %0d %0d",comb,ds);
  d.delete();refresh=~refresh;#1;$display("TRACE delete %0d",ds);
 end
endmodule
