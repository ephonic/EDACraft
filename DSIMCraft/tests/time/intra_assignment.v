`timescale 10ns/1ns
module coarse(output reg [7:0] q);
  reg [7:0] source = 8'h11;
  initial begin #0.1; source=8'h22; end
  initial begin q = #0.15 source; $display("TRACE coarse t=%0t q=%h",$time,q); end
endmodule
`timescale 1ns/1ps
module top;
  reg [7:0] source = 8'h12;
  reg [7:0] q;
  reg [3:0] hi,lo;
  reg [255:0] wide_source = 256'h1111111111111111111111111111111111111111111111111111111111111111;
  reg [255:0] wide_result;
  wire [7:0] coarse_q;
  coarse c(coarse_q);
  initial begin
    #2; source=8'h34;
    wide_source=256'h2222222222222222222222222222222222222222222222222222222222222222;
    #6; source=8'h56;
    #2; wide_source=256'h3333333333333333333333333333333333333333333333333333333333333333;
    #4; source=8'hxz;
  end
  initial begin
    q = #5 source;
    $display("TRACE sampled t=%0t q=%h source=%h",$time,q,source);
    q = #0 source;
    $display("TRACE delta t=%0t q=%h",$time,q);
    {hi,lo} = #4 source;
    $display("TRACE parts t=%0t hi=%h lo=%h",$time,hi,lo);
    wide_result = #3 wide_source;
    $display("TRACE wide t=%0t q=%h",$time,wide_result);
    q = #2 source;
    $display("TRACE delayed t=%0t q=%h",$time,q);
    #1; q = #0 source;
    $display("TRACE unknown t=%0t q=%h",$time,q);
    q=0;
    repeat(3) begin q = #1 (q+8'd1); $display("TRACE repeat t=%0t q=%h",$time,q); end
    $finish;
  end
endmodule
