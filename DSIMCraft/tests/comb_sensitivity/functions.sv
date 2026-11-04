`timescale 1ns/1ps
module top;
logic [5:0] q;
logic y;
function automatic logic getbit();return q[0];endfunction
function automatic logic update_bit();q[3]=getbit();return getbit();endfunction
always_comb begin q[2]=update_bit();y=getbit();$display("WAKE functions %0t %b %b",$time,q[3:2],y);end
initial begin
 #1;q[1:0]=0;q[5:4]=0;
 #1;$display("TRACE functions %b %b",q,y);
 q[1]=1;q[5:4]=3;
 #1;$display("TRACE functions %b %b",q,y);
 q[0]=1;
 #1;$display("TRACE functions %b %b",q,y);
 q[0]=1'bx;
 #1;$display("TRACE functions %b %b",q,y);
 q[0]=1'bz;
 #1;$display("TRACE functions %b %b",q,y);$finish;
end
endmodule
