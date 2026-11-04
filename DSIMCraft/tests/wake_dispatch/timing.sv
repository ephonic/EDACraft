`timescale 1ns/1ps
module tb;
  reg [7:0] q=0, r=0;
  reg clk=0;
  integer n=0;
  always #1 clk=~clk;
  always @(posedge clk) begin q<=q+1; r<=#0.25 q; end
  initial begin
    #0.001;
    repeat(3) begin
      #2;
      $display("TRACE before %0t %0d %0d",$time,q,r);
      #0; q=q+2;
      $display("TRACE inactive %0t %0d %0d",$time,q,r);
    end
    #2;
    $display("TRACE done %0t %0d %0d",$time,q,r);
    $finish;
  end
  initial begin #2.001; repeat(3) begin n=n+1; #2; end end
endmodule
