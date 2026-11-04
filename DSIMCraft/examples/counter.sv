`timescale 1ns/1ps
module top;
  bit clk;
  int unsigned count;
  always #5 clk = ~clk;
  always @(posedge clk) count <= count + 1;
  initial begin
    repeat (4) @(negedge clk);
    if (count !== 4) $fatal(1, "counter mismatch");
    $display("DSIMCRAFT COUNTER PASS %0d", count);
    $finish;
  end
endmodule
