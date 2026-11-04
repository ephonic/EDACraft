`timescale 1ns/1ps
module top;
  reg [7:0] data=8'h12;
  wire [7:0] single=data;
  initial begin
    #1;force single=8'ha5;
    data=8'h34;#1;
    if(single!==8'ha5)$fatal(1,"forced");
    release single;#1;
    if(single!==8'h34)$fatal(1,"release driver history");
    $display("TRACE force %h",single);$finish;
  end
endmodule
