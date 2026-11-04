`timescale 1ns/1ps
module worker #(parameter BASE=2)(output reg signed [31:0] q);
integer index;
initial begin : run
 q=BASE;
 for(index=0;index<8;index++)begin
  #1;
  if(index==1)continue;
  if(index==4)break;
  q=q+BASE+index;
 end
end
endmodule
module top;
genvar g;
for(g=0;g<2;g=g+1)begin : lanes
 wire signed [31:0] value;
 worker #(.BASE(g+2)) u(value);
end
initial begin #8 $finish;end
endmodule
