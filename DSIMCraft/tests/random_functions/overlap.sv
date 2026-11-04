`timescale 1ns/1ps
module top;
 integer issued=0,done=0,k=0;int unsigned answer[6];
 task automatic work();
  integer tag=issued++;
  int unsigned first,second,expected_first,expected_second;
  begin
   first=$urandom(123);#(7-tag);second=$urandom();
   expected_first=$urandom(123);expected_second=$urandom;
   if(first!==expected_first||second!==expected_second)$fatal(1,"overlapping thread stream");
   answer[tag]=first^second;done++;
  end
 endtask
 initial begin
  for(k=0;k<6;k++)fork work();join_none
  wait fork;
  if(issued!=6||done!=6)$fatal(1,"activation count");
  for(k=1;k<6;k++)if(answer[k]!==answer[0])$fatal(1,"thread stability");
  $display("TRACE random overlapping automatic activations pass");
 end
endmodule
