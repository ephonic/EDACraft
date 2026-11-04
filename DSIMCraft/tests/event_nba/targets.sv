`timescale 1ns/1ps
module top;event e;logic clk=0;logic[31:0]q=0;logic[7:0]a=0,b=0;integer base=4,calls=0,stage=0;
function integer address();calls++;return base;endfunction
initial begin
q[address()+:8]<=@e 8'hbe;
{a[3:0],b[base+:4]}<=@(posedge clk)8'h12;
base=32'bx;q[address()+:8]<=@e 8'hff;
base=0;stage=1;
#5;$display("TRACE targets %0d %0d %0d %0d %0d",q,a,b,calls,stage);
if(q!==32'hbe0||a!==1||b!==32||calls!==2||stage!==1)$fatal(1,"target capture mismatch");$finish;end
initial begin #2 ->e;#1 clk=1;end
endmodule
