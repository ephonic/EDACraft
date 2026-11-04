`timescale 1ns/1ps
module lane #(parameter PERIOD=1)(output integer q=0);
integer i=0;
initial begin
 for(i=1;i<=4;i++)fork
  automatic integer saved=i;
  begin #PERIOD;q+=saved;end
 join_none
 wait fork;
end
endmodule
module top;
wire signed [31:0]a,b;
lane #(1)u(a);lane #(2)v(b);
endmodule
