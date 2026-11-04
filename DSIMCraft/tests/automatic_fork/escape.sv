`timescale 1ns/1ps
module top;integer q=0;task automatic work(input integer n);fork begin #2;q=n;end join_none endtask initial begin work(7);#3;$display("TRACE escape %0d",q);$finish;end endmodule
