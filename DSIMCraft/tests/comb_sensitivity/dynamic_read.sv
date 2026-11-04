`timescale 1ns/1ps
module top;
logic[7:0] q;
logic[3:0] y;
integer i;
always_comb begin q[7:4]=q[i+:4];y=q[i+:4];$display("WAKE dynamic_read %0t %b %b",$time,q,y);end
initial begin
 #1;i=0;q[3:0]=1;
 #1;$display("TRACE dynamic_read %b %b",q,y);i=4;
 #1;$display("TRACE dynamic_read %b %b",q,y);q[3:0]=2;
 #1;$display("TRACE dynamic_read %b %b",q,y);i=8;
 #1;$display("TRACE dynamic_read %b %b",q,y);i=0;
 #1;$display("TRACE dynamic_read %b %b",q,y);$finish;
end
endmodule
