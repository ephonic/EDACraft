`timescale 1ns/1ps
module top;
logic [7:0] q;
logic [7:0] a,y;
always_comb begin q[7:4]=a[7:4];q[3:0]=a[3:0];y=q;end
initial begin
 #1;a=8'h56;
 #1;$display("TRACE union %b %b",q,y);a=8'bxz0101zx;
 #1;$display("TRACE union %b %b",q,y);$finish;
end
endmodule
