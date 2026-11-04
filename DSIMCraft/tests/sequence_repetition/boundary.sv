`timescale 1ns/1ps
module top;
  reg clk=0,req=1,data=1;
  integer passed=0,failed=0,covered=0,once=0,early_fail=0;
  always #1 clk=~clk;
  ap:assert property(@(posedge clk) req |-> data[*256]) passed++;else failed++;
  cp:cover property(@(posedge clk) req |-> data[*256]) covered++;
  op:assert property(@(posedge clk) req |=> data[*1]) once++;
  fp:assert property(@(posedge clk) req |-> (!data)[*256]) else early_fail++;
  initial begin
    #2;req=0;
    #512;
    $display("TRACE repeat-boundary %0d %0d %0d %0d %0d",passed,failed,covered,once,early_fail);
    if(passed!=1||failed!=0||covered!=1||once!=1||early_fail!=1)$fatal(1,"repeat boundary");
    $finish;
  end
endmodule
