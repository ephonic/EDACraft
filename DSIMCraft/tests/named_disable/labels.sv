`timescale 1ns/1ps
module top;integer a=0;
initial begin : main
 fork : jobs
  begin : one #1;a=7;end : one
 join : jobs
 $display("TRACE labels %0d %0t",a,$time);$finish;
end : main
endmodule
