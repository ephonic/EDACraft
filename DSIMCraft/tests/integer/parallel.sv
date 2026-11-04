`timescale 1ns/1ps
module lane #(parameter BASE=1)(output reg signed [31:0] q);
integer index;
reg [31:0] stimulus;
always_comb begin : calc
  integer temp;
  temp=$signed(stimulus)/3;
  q=temp-BASE;
end
initial begin : drive
  integer x;
  stimulus=0;
  for(index=0;index<5;index=index+1)begin
    x=BASE-index*7;
    #1 stimulus=x;
  end
end
endmodule
module top;
wire signed [31:0] a,b;
lane #(7) u(a);
lane #(31) v(b);
endmodule
