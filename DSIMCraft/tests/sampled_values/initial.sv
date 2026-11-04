`timescale 1ns/1ps
module top;
reg clk=0;logic q,proc,prev;bit two,tp;logic decl=1,dp=1;integer checks=0,errors=0;
check: assert property(@(negedge clk)
 ($past(q)===prev)&&($past(proc)===$past(q))&&($past(two)===tp)&&($past(decl)===dp)&&
 ($rose(q)==((q===1'b1)&&!(prev===1'b1)))&&($fell(q)==((q===1'b0)&&!(prev===1'b0)))) checks=checks+1;else errors=errors+1;
// Avoid an Active-region race with initial assignments at the static time-zero edge.
always @(negedge clk)if($time>0)begin prev<=q;tp<=two;dp<=decl;end
initial begin
 proc=1;q=1;two=1;decl=0;
 repeat(4)begin #2;clk=1;#1;clk=0;#1;q=~q;proc=~proc;two=~two;decl=~decl;end
 #1;$display("TRACE initial %0d %0d",checks,errors);if(checks!=5||errors)$fatal(1,"FAIL initial");$finish;
end
endmodule
