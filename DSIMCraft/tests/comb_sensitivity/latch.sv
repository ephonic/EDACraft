`timescale 1ns/1ps
module top;
logic [3:0] q;
logic gate;
always_latch if(gate)q[3:2]=q[1:0];
initial begin
 #1;gate=0;q[1:0]=0;
 #1;$display("TRACE latch %b",q);gate=1;
 #1;$display("TRACE latch %b",q);q[1:0]=1;
 #1;$display("TRACE latch %b",q);gate=0;q[1:0]=2;
 #1;$display("TRACE latch %b",q);gate=1;
 #1;$display("TRACE latch %b",q);q[1:0]=2'bxz;
 #1;$display("TRACE latch %b",q);$finish;
end
endmodule
