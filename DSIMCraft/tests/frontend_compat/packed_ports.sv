`timescale 1ns/1ps
module packed_child(input logic [1:0][7:0] a, output logic [1:0][7:0] y);
  assign y[0] = a[1] ^ 8'hff;
  assign y[1] = a[0] + 8'd1;
endmodule
module top;
  logic [1:0][7:0] a;
  wire [1:0][7:0] y;
  packed_child dut(a, y);
  initial begin
    a = 16'h12a5;
    #1;
    if (y !== 16'ha6ed || y[0][7] !== 1'b1) $fatal(1, "packed port");
    $display("TRACE packed a=%h y=%h byte=%h bit=%b", a, y, y[0], y[0][7]);
    $finish;
  end
endmodule
