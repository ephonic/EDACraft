`timescale 1ns/1ps
module top;
logic [7:0] src[2],q[2];
logic flag;logic[7:0] seen;
integer index,bit_index;
wire [7:0] first=q[0],second=q[1];
always_comb begin q=src;q[index][bit_index]=flag;seen=q[0]^q[1];end
initial begin
 src[0]=8'h12;src[1]=8'h34;index=0;bit_index=7;flag=1;
 #1;$display("TRACE arrays %b %b %b",first,second,seen);
 index=1;bit_index=0;flag=1'bz;
 #1;$display("TRACE arrays %b %b %b",first,second,seen);
 src[0]=8'b1010xz01;index=32'bx;
 #1;$display("TRACE arrays %b %b %b",first,second,seen);
 index=0;bit_index=32'bx;
 #1;$display("TRACE arrays %b %b %b",first,second,seen);$finish;
end
endmodule
