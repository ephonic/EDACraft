`timescale 1ns/1ps
module top;
  reg clk=0;
  reg [7:0] data=0, comb;
  integer cycles=0, alternations=0;
  always #2 clk=~clk;
  always @(posedge clk) begin
    cycles<=cycles+1;
    data<=data+3;
  end
  always_comb comb=data ^ 8'h65;
  initial begin
    repeat(16) begin
      @(posedge clk);
      @(negedge clk);
      alternations=alternations+1;
    end
    #0;
    #1;
    $display("TRACE lists %0d %0d %02x %0d",cycles,data,comb,alternations);
    if(cycles!=16 || data!=48 || comb!=8'h55 || alternations!=16) $fatal(1,"lists");
    $finish;
  end
endmodule
