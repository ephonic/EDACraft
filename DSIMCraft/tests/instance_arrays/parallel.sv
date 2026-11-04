`timescale 1ns/1ps
module array_worker(output wire[15:0] q);
  logic[15:0] state;
  assign q=state;
  initial begin state=16'h7300;repeat(3)begin #1;state++;end end
endmodule
module top;
  wire[15:0] one,two;
  array_worker u[1:0]({one,two});
endmodule
