`timescale 1ns/1ps
module leaf(input wire a, output wire y);
  assign y = ~a;
endmodule
module matvec_tb;
  wire y;
  leaf dut(1'b0, y);
  initial begin
    #1;
    if (y !== 1'b1) $fatal(1, "implicit top");
    $display("TRACE inferred matvec_tb y=%b", y);
    $finish;
  end
endmodule
