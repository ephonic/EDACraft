`timescale 1ns/1ps
module top;logic clk=0;integer q=0,z=0,ordered_q=0,n=2,order=0,i=0;
function integer count();order=order*10+1;return n;endfunction
function integer value();order=order*10+2;n=1;return 17;endfunction
task automatic issue(input integer v);q<=repeat(v)@(posedge clk)v+10;endtask
initial begin
ordered_q<=repeat(count())@(posedge clk)value();
for(i=1;i<4;i++)issue(i);
z<=repeat(0)@(posedge clk)77;
#0;if(q!==0||z!==0)$fatal(1,"early NBA");
#2;$display("TRACE first %0d %0d %0d",q,z,order);if(ordered_q!==17||q!==11||z!==77||order!==21)$fatal(1,"first capture");
#2;$display("TRACE second %0d",q);if(q!==12)$fatal(1,"second capture");
#2;$display("TRACE third %0d",q);if(q!==13)$fatal(1,"third capture");$finish;end
initial begin #1 clk=1;#1 clk=0;#1 clk=1;#1 clk=0;#1 clk=1;end
endmodule
