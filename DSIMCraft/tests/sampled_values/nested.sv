`timescale 1ns/1ps
module top;
reg clk=0;integer q=11,p=11,pp=11,checks=0,errors=0;logic en=1;integer gp=11;
check: assert property(@(posedge clk)
 ($past($past(q))===pp)&&($past($sampled(q))===p)&&($sampled($past(q))===p)&&
 ($past(q,1,$sampled(en))===gp)&&($past(32'd7,3)===32'd7)) checks=checks+1;else errors=errors+1;
always @(posedge clk)begin p<=q;pp<=p;if(en)gp<=q;end
initial begin
 #1;q=20;
 repeat(7)begin #2;clk=1;#1;clk=0;q=q+5;en=~en;end
 #1;$display("TRACE nested %0d %0d",checks,errors);if(checks!=7||errors)$fatal(1,"FAIL nested");$finish;
end
endmodule
