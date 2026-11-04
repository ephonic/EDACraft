`timescale 1ns/1ps
module top;event e;logic clk=0;logic[31:0]q=0;logic[7:0]a=0,b=0;logic[15:0]data=16'hbeef;
integer base=0,calls=0,stage=0;
function integer address();calls++;return base;endfunction
initial begin
q[address()+:8]=@e data;stage=1;
{a[3:0],b[address()+:4]}=@(posedge clk)data;stage=2;
q[address()+:8]=@(negedge clk)data;stage=3;
#1 $display("TRACE targets %0d %0d %0d %0d %0d",q,a,b,calls,stage);
if(q!==32'hef00||a!==3||b!==64||calls!==3||stage!==3)$fatal(1,"target mismatch");$finish;end
initial begin
#1 base=8;data=16'h1234;
#1 ->e;
#1 base=0;data=16'h5678;
#1 base=4;clk=1;
#1 data=16'hffff;
#1 base=32'bx;clk=0;end
endmodule
