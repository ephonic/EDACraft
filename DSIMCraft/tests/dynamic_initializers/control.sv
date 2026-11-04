`timescale 1ns/1ps
module top;
 integer count=0,done=0,k=0;
 task automatic work(input integer tag);
  integer values[]=new[tag];
  assert(values.size()==tag);values[0]=tag;
  #2;count+=values[0]+values.size();
 endtask
 initial begin
  for(k=1;k<=6;k++)begin
   begin : cancelled
    fork work(9);begin #1;disable cancelled;end join
   end
   work(k);done++;
  end
  $display("TRACE control %0d %0d",count,done);
 end
endmodule
