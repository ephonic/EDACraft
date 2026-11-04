`timescale 1ns/1ps
module top;
reg clk=0,rst=1,en=0;integer q=17,prev=17,older=17,checks=0,errors=0,covered=0;
check: assert property(@(posedge clk) disable iff(rst) en |-> (($past(q)===prev)&&($past(q,2)===older))) checks=checks+1;else errors=errors+1;
hit: cover property(@(posedge clk) disable iff(rst) en |=> ($past(q)===prev)) covered=covered+1;
always @(posedge clk)begin prev<=q;older<=prev;end
initial begin
 repeat(2)begin #2;clk=1;#1;clk=0;q=q+3;end
 rst=0;
 repeat(2)begin #2;clk=1;#1;clk=0;q=q+3;end
 en=1;
 repeat(3)begin #2;clk=1;#1;clk=0;q=q+3;end
 rst=1;#1;rst=0;
 #2;clk=1;#1;clk=0;
 #1;$display("TRACE disabled %0d %0d %0d",checks,errors,covered);if(checks!=4||errors||covered!=2)$fatal(1,"FAIL disabled");$finish;
end
endmodule
