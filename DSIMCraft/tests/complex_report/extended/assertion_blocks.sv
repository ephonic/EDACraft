`timescale 1ns/1ps
module tb;
  reg clk=0,ok=0;
  integer failures=0,passes=0;
  always #5 clk=~clk;
  assert property(@(posedge clk)ok) begin passes=passes+1;end
    else begin failures=failures+1;failures=failures+1;end
  initial begin
    #6;ok=1;#10;
    if(failures!=2||passes!=1)$fatal(1,"assert action block");
    $display("TRACE assertion blocks %0d %0d",failures,passes);$finish;
  end
endmodule
