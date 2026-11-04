`timescale 1ns/1ps
module top;event e,other;logic[129:0]g=0;logic clk=0;integer qualified=0,mixed=0;
always @(e iff g)qualified++;
always @(e iff g or other iff !g or posedge clk iff g)mixed++;
initial begin
#1 ->e;g=1;#0;
#1 g=1;->e;g=0;#0;
#1 g=1;->e;->e;#0;
#1 g=0;->e;g=1;->e;g=0;#0;
#1 ->other;#0;
#1 g=130'bx;->e;->other;#0;
#1 g=0;g[129]=1;->e;#0;
#1 g[0]=1'bz;->e;#0;
#1 g=0;clk=1;#0;
#1 g=1;clk=0;#0;clk=1;#0;
#1 $display("TRACE occurrence %0d %0d",qualified,mixed);
if(qualified!==4||mixed!==6)$fatal(1,"occurrence mismatch");$finish;end
endmodule
