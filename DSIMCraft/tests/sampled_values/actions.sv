`timescale 1ns/1ps
module top;
reg clk=0,rst=1;integer q=5,seen=0,next_seen=0,checks=0,errors=0;
always @(posedge clk)begin q<=q+1;rst<=0;end
check: assert property(@(posedge clk) disable iff($sampled(rst)) $sampled(q)==q)
 begin seen=$sampled(q);next_seen<=$sampled(q+1);checks=checks+1;end else errors=errors+1;
initial begin
 repeat(5)begin #3;clk=1;#1;if(checks>0&&(seen!=q-1||next_seen!=q))errors=errors+1;clk=0;end
 #1;$display("TRACE actions %0d %0d %0d %0d",checks,errors,seen,next_seen);if(checks!=4||errors||seen!=9||next_seen!=10)$fatal(1,"FAIL actions");$finish;
end
endmodule
