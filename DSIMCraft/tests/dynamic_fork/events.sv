`timescale 1ns/1ps
module top;
event e;
logic clk=0,enable=0,a=0,b=0;
integer i=0,q=0,r=0,t=0;
initial begin
 for(i=0;i<4;i++)fork begin @e;#1;q++;end begin @(posedge clk iff enable);#2;r++;end begin @(a^b);t++;end join_none
 a=1;#0;if(t!=0)$fatal(1,"pre-start expression change woke a branch");
 ->e;enable=1;clk=1;#1;b=1;
 wait fork;
 $display("TRACE events %0d %0d %0d %0t",q,r,t,$time);
 if(q!=4||r!=4||t!=4)$fatal(1,"lost cloned event wait");
 #1;$finish;
end
endmodule
