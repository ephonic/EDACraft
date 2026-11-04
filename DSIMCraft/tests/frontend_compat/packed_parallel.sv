`timescale 1ns/1ps
module packed_worker(output wire [15:0] q);
  logic [1:0][7:0] data;
  integer lane;
  assign q=data;
  initial begin
    lane=0;data=16'h1200;
    repeat(3) begin #1;data[lane]++;end
  end
endmodule
module top;
  wire [15:0] one,two;
  packed_worker a(one),b(two);
endmodule
