`timescale 1ns/1ps
module top;
reg [7:0] d,rhs,q,b;
reg [15:0] parts;
reg [64:0] wide;
initial begin
  d=3; rhs=8'h12; q=0; b=0; parts=0;
  q <= #(d+8'd1) rhs;
  {parts[15:12],parts[3:0]} <= #(d) 8'hab;
  b = #(d+8'd2) rhs;
  $display("TRACE sampled t=%0t b=%h rhs=%h q=%h parts=%h",$time,b,rhs,q,parts);
  d=2; #(d[1:0]);
  d=8'b0000x001; #d;
  $display("TRACE unknown t=%0t",$time);
  d=8'hzz; q <= #(d) 8'hcc;
  #1; $display("TRACE zero-nba t=%0t q=%h",$time,q);
  wide=65'h10000000000000002; #wide;
  $display("TRACE wide t=%0t",$time);
  wide={1'bx,64'd2}; #wide;
  wide={1'bz,64'd3}; #wide;
  #(1'bx); #(1'bz);
  $display("TRACE wide-unknown t=%0t",$time);
end
initial begin #1; rhs=8'h34; d=1; end
endmodule
