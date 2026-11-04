`timescale 1ns/1ps
module top;
logic [5:0] q;
logic [3:0] w;
logic qread,wread;
always_comb begin
 q[3:2]=q[1:0];qread=q[0];
 $display("WAKE static %0t %b %b",$time,q[3:0],qread);
end
always_comb begin w[3:2]=w[1:0];wread=|w;end
initial begin
 #1;q[1:0]=0;q[5:4]=0;w[1:0]=0;
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);
 q[5:4]=3; // Not read: this change must not wake the first block.
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);
 q[1:0]=1;w[1:0]=1;
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);
 q[1:0]=2;w[1:0]=2;
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);
 q[1:0]=2'bxz;w[1:0]=2'bxz;
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);
 q[1:0]=2'bzx;w[1:0]=2'bzx;
 #1;$display("TRACE static %b %b %b %b",q,qread,w,wread);$finish;
end
endmodule
