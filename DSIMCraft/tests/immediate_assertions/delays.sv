`timescale 1ns/1ps
module top;
reg clock=0;
int q,passes,fails;
always #1 clock=~clock;
always @(posedge clock)begin
 q<=q+1;
 assert(q>=0)passes++;else fails++;
end
initial begin
 #2;assert(q==1)passes++;else fails++;
 #2;cover(q==2)passes++;
 #2;assume(q==3)passes++;else fails++;
 $display("TRACE delays %0d %0d %0d",q,passes,fails);$finish;
end
endmodule
