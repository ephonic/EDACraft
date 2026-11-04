`timescale 1ps/1ps
module top;
 class State;int value;endclass
 State p;
 int sampled;
 initial begin
  p=new;sampled=0;
  sampled<=@(p.value)99;
  #2;p.value=3;
  #1;$display("TRACE event_nba t=%0t sampled=%0d",$time,sampled);
  p=null;
  #1;$finish;
 end
endmodule
