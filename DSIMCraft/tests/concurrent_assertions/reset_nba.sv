`timescale 1ns/1ps
module top;
 reg clk=0,rst=1,b=0;integer pass=0,fail=0;
 always #5 clk=~clk;
 always @(posedge clk) rst<=0;
 a: assert property(@(posedge clk) disable iff(rst) b) pass=pass+1;else fail=fail+1;
 initial begin #12;b=1;#10;$display("TRACE reset_nba %0d %0d",pass,fail);$finish;end
endmodule
