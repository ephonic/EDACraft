`timescale 1ns/1ps
module top;
reg clk=0,req=1,data=1;
integer passed=0,failed=0,covered=0,once=0,early_fail=0;
always #1 clk=~clk;
assert property(@(posedge clk) (req ##0 data[*254]) |-> data)passed++;else failed++;
cover property(@(posedge clk) (req ##0 data[*254]) |-> data)covered++;
assert property(@(posedge clk) (req ##0 data) |=> data)once++;
assert property(@(posedge clk) (req ##0 (!data)[*254]) |-> 0)else early_fail++;
initial begin #2;req=0;#512;
$display("TRACE antecedent-boundary %0d %0d %0d %0d %0d",passed,failed,covered,once,early_fail);
if(passed!=1||failed!=0||covered!=1||once!=1||early_fail!=0)$fatal(1,"antecedent boundary");$finish;end
endmodule
