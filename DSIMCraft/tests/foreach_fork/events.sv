`timescale 1ns/1ps
module top;
logic [3:1] data=0;
integer k=0,q=0,done=0;
task watch_indices();
 foreach(data[i])begin
  if(i>1)fork begin @(i);q+=i;done++;end join_none
  #1;
 end
 wait fork;
endtask
initial begin
 for(k=0;k<4;k++)fork watch_indices();join_none
 wait fork;
 $display("TRACE events %0d %0d",q,done);
 if(q!=12||done!=8)$fatal(1,"index-frame event rebinding");
end
endmodule
