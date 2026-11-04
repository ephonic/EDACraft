`timescale 1ns/1ps
module source(input [7:0] d, output [7:0] y, output reg signed [7:0] q);
  assign y=d;
  always @(d) q<=d;
endmodule
module top;
  logic [7:0] d;
  logic [7:0] y;
  bit [7:0] b;
  logic signed [15:0] q;
  integer integer_q;
  wire [7:0] unused0,unused1,unused2;
  source a(d,y,q);
  source c(d,b,integer_q);
  initial begin
    d=8'h81;
    #1 $display("TRACE basic %h %h %h %h",y,b,q,integer_q);
    if(y!==8'h81||b!==8'h81||q!==16'hff81||integer_q!==32'hffffff81)$fatal(1,"basic sign");
    d=8'b10xz01z1;
    #1 $display("TRACE unknown %b %b %b",y,b,q);
    if(y!==8'b10xz01z1||b!==8'b10000101||q!==16'b1111111110xz01z1)$fatal(1,"basic unknown");
    d=8'h2a;
    #1 $display("TRACE final %h %h %h %h",y,b,q,integer_q);
    if(y!==42||b!==42||q!==42||integer_q!==42)$fatal(1,"basic final");
    $finish;
  end
endmodule
