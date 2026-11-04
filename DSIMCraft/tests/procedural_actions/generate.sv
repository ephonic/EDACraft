`timescale 1ns/1ps
module unit_test #(parameter W=8)(output reg [W-1:0] q=0);
genvar g;
generate for(g=0;g<2;g=g+1)begin:worker
 function [W-1:0] calc(input [W-1:0] a);
  reg [W-1:0] value;
  begin value=a;value+=W;if(a[0])return value;value^=3;return value;end
 endfunction
 task run(input [W-1:0] a);
  begin #1;if(g==0)begin q<=#1 calc(a);return;end return;end
 endtask
 initial begin run(1);#2;run(2);end
end endgenerate
endmodule
module top;
wire[7:0] a;wire[79:0] b;
unit_test #(8) u(a);unit_test #(80) v(b);
endmodule
