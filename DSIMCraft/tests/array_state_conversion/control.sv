`timescale 1ns/1ps
module top;
 logic[7:0] a[]=new[1];integer count=0,done=0,k=0,observed=0;
 task automatic work(inout bit[7:0] x[],input integer tag);
  logic[7:0] snapshot[]=x;bit[7:0] local_values[]=snapshot;
  local_values[0]+=tag;#2;x=local_values;count+=local_values[0];
 endtask
 initial begin
  a[0]=16;
  for(k=1;k<=3;k++)begin
   begin : cancelled
    fork work(a,99);begin #1;disable cancelled;end join
   end
   work(a,k);done++;observed=a[0];
  end
  $display("TRACE control %0d %0d %0d %h",count,done,observed,a[0]);
 end
endmodule
