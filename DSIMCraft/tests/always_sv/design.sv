`timescale 1ns/1ps
module stage(input logic clk, rst_n, en, input logic [7:0] d,
             output logic [7:0] q, held, mixed);
always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) q <= 0; else q <= d;
always_latch if (en) held = d;
always_comb mixed = (q ^ held) + 8'd1;
endmodule

module top;
logic clk, rst_n, en;
logic [7:0] d;
wire [7:0] q, held, mixed;
logic [7:0] constant_value;
logic [129:0] wide;
logic a, b, c;
logic [1:0] bits;
stage u(clk, rst_n, en, d, q, held, mixed);
initial begin
  clk=0;rst_n=0;en=0;d=0;
  #1;
  $display("TRACE startup constant=%h q=%h",constant_value,q);
  a=0;en=1;d=8'h12;
  #1;clk=1;
  #1;clk=0;en=0;d=8'h34;rst_n=1;a=1;
  #1;clk=1;
  #1;
  $display("TRACE held q=%h held=%h mixed=%h c=%b b=%b bits=%b",q,held,mixed,c,b,bits);
  en=1;d=8'bx1z00110;
  #1;
  $display("TRACE unknown held=%b mixed=%b wide=%b",held,mixed,wide);
  d=8'h57;clk=0;
  #1;clk=1;
  #1;
  $display("TRACE final q=%h held=%h mixed=%h c=%b b=%b bits=%b",q,held,mixed,c,b,bits);
end
always_comb constant_value=8'ha5;
always_comb wide={2'bxz,{16{d}}};
// b is read before being written: changing b must not retrigger this block.
always_comb begin c=b;b=a;end
always_ff @(posedge clk) bits[0]<=d[0];
always_ff @(posedge clk) bits[1]<=d[1];
endmodule
