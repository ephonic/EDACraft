`timescale 1ns/1ps
module top;
int passes,fails,hits,checks;
initial begin
 a_true:assert(1)passes++;else fails++;
 a_false:assert(0)passes++;else fails++;
 assert(1'bx)passes++;else fails++;
 assert(1'bz)passes++;else fails++;
 assert(4'bx100)passes++;else fails++;
 assume(0)passes++;else fails++;
 cover(0)hits++;
 cover(1'bx)hits++;
 c_true:cover(1)hits++;
 assert(++checks==1)passes++;else fails++;
 assert(0&&++checks)passes++;else fails++;
 cover(++checks==2)hits++;
 if(1)assert(0)else fails++;else passes+=100;
 assert(1);
 #1;$display("TRACE actions %0d %0d %0d %0d",passes,fails,hits,checks);$finish;
end
endmodule
