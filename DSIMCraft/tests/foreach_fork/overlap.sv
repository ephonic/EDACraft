`timescale 1ns/1ps
module top;
logic [3:1] data=0;
integer k=0,sum=0,done=0;
task walk();
 foreach(data[i])begin:body
  integer calls=0;
  #i;sum+=i;calls++;done++;
  if(calls!=done)$fatal(1,"static body storage must remain shared");
 end
endtask
initial begin
 for(k=0;k<4;k++)fork walk();join_none
 wait fork;
 $display("TRACE overlap %0d %0d",sum,done);
 if(sum!=24||done!=12)$fatal(1,"overlapping loop frames");
end
endmodule
