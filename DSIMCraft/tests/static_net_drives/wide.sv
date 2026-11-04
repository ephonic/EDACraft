`timescale 1ns/1ps
module top;
  reg [127:0] data;
  wire [127:0] single=data;
  initial begin
    data=128'hx123_z456_1234_5678_abcd_0123_4567_89ab;#1;
    if(single!==data)$fatal(1,"wide");
    $display("TRACE wide %h",single);$finish;
  end
endmodule
