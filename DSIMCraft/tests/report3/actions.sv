`timescale 1ns/1ps
module top;
  logic clk=0;int pass=0,fail=0,x=0;
  always #1 clk=~clk;
  assert property (@(posedge clk) x==0) begin pass++;pass++;end else begin fail++;fail++;end
  initial begin
    assert(0)else begin fail++;fail++;end
    #2;x=1;#2;
    $display("TRACE actions %0d %0d",pass,fail);$finish;
  end
endmodule
