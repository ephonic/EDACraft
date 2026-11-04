`timescale 1ps/1ps
module top;
 int q[$]='{3};int map[int unsigned];int observed;
 initial begin
  map[-1]=3;observed=q[$];
  #2;map[-1]=9;q[$]=map[-1];observed=q[$];
  #1;map[0]=7;q[$+1]=map[0];observed=q[$];
  #2;$display("TRACE rollback %0d %0d %0d",observed,q.size(),map.num());$finish;
 end
endmodule
