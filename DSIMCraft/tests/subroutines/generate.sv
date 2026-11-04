`timescale 1ns/1ps
module worker #(parameter W=8)(output reg [W-1:0] q=0);
function [W-1:0] calc(input [W-1:0] a);
 reg [W-1:0] temp;
 begin temp=a+W;calc=temp^3;end
endfunction
task run(input [W-1:0] a);
 begin #1;q<=#1 calc(a);end
endtask
initial begin run(1);run(3);end
endmodule
module top;
genvar g;
for(g=0;g<2;g=g+1)begin:lanes
 wire [g*72+8-1:0] q;
 worker #(g*72+8) u(q);
end
initial begin #6;$finish;end
endmodule
