`timescale 1ns/1ps
module top;
logic [7:0] d,q,seen;
logic en,flag;
always_latch if(en)begin q=d;q[7]=flag;seen=q;end
initial begin
 en=0;d=8'h12;flag=0;
 #1;$display("TRACE latch %b %b",q,seen);
 en=1;
 #1;$display("TRACE latch %b %b",q,seen);
 en=0;d=8'h63;flag=1;
 #1;$display("TRACE latch %b %b",q,seen);
 en=1;
 #1;$display("TRACE latch %b %b",q,seen);
 flag=1'bx;
 #1;$display("TRACE latch %b %b",q,seen);$finish;
end
endmodule
