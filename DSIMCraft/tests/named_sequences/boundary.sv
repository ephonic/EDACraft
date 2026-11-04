`timescale 1ns/1ps
module top;
  reg clk=0,req=1,data=1;
  integer passed=0,failed=0,covered=0,once=0,early_fail=0;
  always #1 clk=~clk;
  ap:assert property(@(posedge clk) req |-> pair[*128]) passed++;else failed++;
  cp:cover property(@(posedge clk) req |-> pair[*128]) covered++;
  op:assert property(@(posedge clk) req |=> one()[*1]) once++;
  fp:assert property(@(posedge clk) req |-> bad[*128]) else early_fail++;
  sequence pair();data ##1 data;endsequence
  sequence one;data[*1];endsequence
  sequence bad;(!data) ##0 data;endsequence
  initial begin
    #2;req=0;
    #512;
    $display("TRACE named-seq-boundary %0d %0d %0d %0d %0d",passed,failed,covered,once,early_fail);
    if(passed!=1||failed!=0||covered!=1||once!=1||early_fail!=1)$fatal(1,"repeat boundary");
    $finish;
  end
endmodule
