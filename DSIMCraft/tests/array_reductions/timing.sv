`timescale 1ns/1ps
module top;
 logic[7:0] a[2]='{1,2};logic[7:0] d[];
 wire[7:0] combinational=a.sum();
 logic[7:0] dynamic_sum,nb,delayed,event_result;
 logic refresh=0;
 event sample;
 always_comb begin if(refresh)dynamic_sum=d.sum();else dynamic_sum=d.sum();end
 initial begin
  d=new[2];d[0]=4;d[1]=5;refresh=~refresh;
  nb<=#2 a.sum();delayed<=#2 d.sum();
  #1;a[0]=10;d[0]=20;refresh=~refresh;
  #2;$display("TRACE timing %h %h %h %h",combinational,dynamic_sum,nb,delayed);
  d=new[3](d);d[2]=7;a[1]=3;refresh=~refresh;
  #1;$display("TRACE resize %h %h",combinational,dynamic_sum);
  d.delete();refresh=~refresh;#1;$display("TRACE delete %h",dynamic_sum);
 end
 initial begin event_result=@(sample) a.product();end
 initial begin #2;->sample;end
endmodule
