`timescale 1ns/1ps
module child #(parameter N=1)(output int q);
function longint f(input byte x);begin return x+N;end endfunction
initial begin q=f(8'b1xz001zx);#1;q+=N;end
endmodule
module top;
genvar g;generate for(g=0;g<2;g=g+1)begin:lanes
wire signed[31:0]q;child #(g+1)u(q);
initial begin #2;$display("TRACE lane %0d %0d",g,q);end
end endgenerate
initial begin #3;$finish;end
endmodule
