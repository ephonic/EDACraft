`timescale 1ns/1ps
module top;
int seen;
initial begin
 a_bad:assert(0);
 assume(1'bx);
 assert(0)else;
 cover(0);
 $info("info value %0d",3);
 $warning("warning value %h",8'hf0);
 $error("error value %b",4'bxz01);
 seen=1;#1;$display("TRACE defaults %0d",seen);$finish;
end
endmodule
