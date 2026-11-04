`timescale 1ns/1ps
module top;logic clk=0,enable=0,valid=0;logic[3:0]data=0;integer clocks=0,edges=0;
function automatic logic permit(input logic x);logic temporary;temporary=x&&enable;return temporary;endfunction
function automatic logic odd(input logic[3:0]x);return ^x;endfunction
always @(posedge clk iff permit(valid))clocks++;
initial begin #0;forever begin @(posedge odd(data) iff permit(valid));edges++;end end
initial begin
#1 enable=1;valid=1;
#1 clk=1;data=1;
#1 clk=0;enable=0;data=3;
#1 clk=1;data=1;
#1 clk=0;enable=1;valid=0;data=0;
#1 clk=1;data=1;
#1 clk=0;valid=1;data=0;
#1 clk=1;data=1;
#1 $display("TRACE guard %0d %0d",clocks,edges);
if(clocks!==2||edges!==2)$fatal(1,"guard mismatch");$finish;
end
endmodule
