`timescale 1ns/1ps
module top;
 reg clk=0,q=0,r=0;integer yes=0,no=0,edge_yes=0,edge_no=0;
 always @(posedge clk) q<=~q;
 a: assert property(@(posedge clk) !q) yes=yes+1;else no=no+1;
 b: assert property(@(negedge clk) r) edge_yes=edge_yes+1;else edge_no=edge_no+1;
 initial begin
  #5;clk=1;r=1;#5;clk=0;r=0;
  #5;clk=1;r=1;#5;clk=0;r=0;
  #5;clk=1;r=1;#5;clk=0;r=0;
  #5;clk=1;r=1;#5;clk=0;r=0;
  #1;$display("TRACE sampling %0d %0d %0d %0d",yes,no,edge_yes,edge_no);$finish;
 end
endmodule
