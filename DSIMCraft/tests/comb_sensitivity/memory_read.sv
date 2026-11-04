`timescale 1ns/1ps
module top;
logic[7:0] m[2];
always_comb begin m[0][7:4]=m[m[0][0]][3:0];$display("WAKE memory_read %0t %b",$time,m[0]);end
initial begin
 #1;m[0][3:0]=0;m[1]=8'h36;
 #1;$display("TRACE memory_read %b %b",m[0],m[1]);m[0][3:0]=2;
 #1;$display("TRACE memory_read %b %b",m[0],m[1]);m[0][0]=1;
 #1;$display("TRACE memory_read %b %b",m[0],m[1]);m[1]=8'h39;
 #1;$display("TRACE memory_read %b %b",m[0],m[1]);m[0][3:0]=4'bxzxz;
 #1;$display("TRACE memory_read %b %b",m[0],m[1]);$finish;
end
endmodule
