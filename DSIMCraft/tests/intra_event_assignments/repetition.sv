`timescale 1ns/1ps
module top;event tick;logic clk=0,g=0;integer data=11,q=0,count=2,order=0,first=0,last=0,zero=0;
function integer length();order=order*10+1;return count;endfunction
function integer sample();order=order*10+2;return data;endfunction
function automatic logic allow();return g;endfunction
function automatic logic odd(input integer x);return ^x;endfunction
initial begin
q=repeat(length())@(posedge clk)sample();first=$time;
q=repeat(0)@(posedge clk)sample();zero=q;
q=repeat(-1)@(posedge clk)sample();
q=repeat(32'bx)@(posedge clk)sample();
q=repeat(1)@(tick iff allow())sample();
q=repeat(1)@(posedge odd(data))sample();last=$time;
$display("TRACE repetition %0d %0d %0d %0d %0d",q,zero,first,last,order);
if(q!==88||zero!==77||first!==3||last!==7||order!==1222222)$fatal(1,"repetition mismatch");$finish;end
initial begin
#1 clk=1;
#1 clk=0;count=0;data=77;
#1 clk=1;
#1 data=88;->tick;
#1 g=1;->>tick;
#1 data=0;
#1 data=1;end
endmodule
