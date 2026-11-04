`timescale 1ns/1ps
module counter #(parameter W=4)(input wire clk,input wire[W-1:0] seed,output logic[W-1:0] q);
  initial q=0;
  always @(posedge clk)q<=#1 q+seed;
endmodule
module top;
  logic[2:0] clk;logic[11:0] seed;wire[11:0] q;
  counter #(.W(4)) c[2:0](.clk(clk),.seed(seed),.q(q));
  initial begin
    clk=0;seed=12'h124;#1;clk=3'b101;#2;
    $display("TRACE state %h",q);if(q!==12'h104)$fatal(1,"first edge");
    clk=0;seed=12'h231;#1;clk=3'b110;#2;
    $display("TRACE state %h",q);if(q!==12'h334)$fatal(1,"independent state");
    clk=0;#1;clk=3'b001;#2;
    $display("TRACE state %h",q);if(q!==12'h335)$fatal(1,"last edge");
    $finish;
  end
endmodule
