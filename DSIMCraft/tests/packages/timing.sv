`timescale 1ns/1ps
package timed;
 parameter int STEP=3;
 function automatic integer advance(integer n);return n+STEP;endfunction
 task automatic update(integer n,output integer result);begin #1;result=advance(n);end endtask
endpackage
module top;
 import timed::*;
 integer n=0,other=0;logic clk=0;
 always #1 clk=~clk;
 always @(posedge clk)n<=advance(n);
 initial begin update(10,other);#3.5;if(n!=6||other!=13)$fatal(1,"package timing");$display("TRACE package timing %0d %0d",n,other);$finish;end
endmodule
