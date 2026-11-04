`timescale 1ns/1ps
module top;integer q=0,k=0;initial begin for(k=0;k<3;k++)fork begin #3;q=q+1;end join_none wait fork;$display("TRACE overlap %0d",q);$finish;end endmodule
