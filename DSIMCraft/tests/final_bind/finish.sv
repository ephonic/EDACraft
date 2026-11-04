`timescale 1ns/1ps
module top;
 int n=0;
 initial begin #1;n=4;#1;n<=9;$finish;end
 initial begin #20;n=99;end
 final begin n=n+1;$display("END scope=%m time=%0t n=%0d",$time,n);end
endmodule
