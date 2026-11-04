`timescale 1ns/1ps
module lane #(parameter BASE=3)(output reg signed [31:0] q);
initial begin : run
 integer sum;
 q=BASE;sum=0;
 for(int i=0;i<7;i++)begin
  #1;
  if(i==2)continue;
  if(i==6)break;
  sum=sum+BASE-i;
  q<=#1 sum;
 end
end
endmodule
module top;
wire signed [31:0] a,b;
lane #(3) u(a);
lane #(17) v(b);
endmodule
