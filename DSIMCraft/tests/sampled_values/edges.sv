`timescale 1ns/1ps
module top;
reg clk=0;logic [3:0] q=4'bxxxz,old=4'bxxxz;integer checks=0,errors=0;
check: assert property(@(posedge clk)
 ($rose(q)==((q[0]===1'b1)&&!(old[0]===1'b1)))&&
 ($fell(q)==((q[0]===1'b0)&&!(old[0]===1'b0)))&&
 ($stable(q)==(q===old))&&($changed(q)==(q!==old))) checks=checks+1;else errors=errors+1;
always @(posedge clk) old<=q;
task tick;begin #2;clk=1;#1;clk=0;end endtask
initial begin
 tick;q=4'bzzz1;tick;q=4'bxxx1;tick;q=4'b0000;tick;q=4'b111x;tick;q=4'b0000;tick;
 q=4'b111z;tick;q=4'b0001;tick;tick;
 #1;$display("TRACE edges %0d %0d",checks,errors);if(checks!=9||errors)$fatal(1,"FAIL edges");$finish;
end
endmodule
