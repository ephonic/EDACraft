`timescale 1ns/1ps
module top;event e;logic clk=0;integer q=0,bad=0,k=0;
initial begin for(k=0;k<3;k++)begin
 fork begin @e;q=q+1;end begin @(posedge clk);bad=bad+1;end join_any
 disable fork;
end #10;clk=1;#1;$display("TRACE events %0d %0d %0d %0t",q,bad,k,$time);
if(q!==3||bad!==0)$fatal(1,"cancelled event woke");$finish;end
initial begin #1;->e;#2;->e;#2;->e;end endmodule
