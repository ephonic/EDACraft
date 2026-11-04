`timescale 1ns/1ps
module top;
 int n=0;int done=0;
 function automatic int twice(input int x);return x*2;endfunction
 initial begin #1;n=7;#1;n=9;end
 final begin done=twice(n);$display("END scope=%m time=%0t n=%0d done=%0d %%m",$time,n,done);end
 always @(done) if(done) $display("SHOULD_NOT_WAKE");
endmodule
