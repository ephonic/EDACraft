`timescale 1ns/1ps
module child #(parameter int N=32'hxz000003,parameter byte signed START=-2,parameter int DELAY=1)(output reg signed[31:0]q);
localparam int COUNT=N;
localparam bit ENABLE=COUNT>0;
genvar g;generate if(ENABLE)begin:active
wire[COUNT-1:0] flags;
for(g=0;g<COUNT;g=g+1)begin:lane
 localparam int INDEX=g;
 assign flags[g]=(INDEX<COUNT);
end
initial begin q=START;repeat(COUNT)begin #DELAY;q<=q+1;end end
end else begin:off initial q=-99;end endgenerate
endmodule
module top;
wire signed[31:0]a,b;child u(a);child #(.N(2),.START(8'b1xz001zx),.DELAY(2))v(b);
initial begin #6;$display("TRACE generate %0d %0d",a,b);$finish;end
endmodule
