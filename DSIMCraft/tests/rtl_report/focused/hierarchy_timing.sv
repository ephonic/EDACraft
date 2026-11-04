`timescale 1ns/1ps
module leaf #(parameter W=8,parameter INIT=1)(input logic clk);
 logic[W-1:0] hidden=INIT;
 logic signed[15:8] shifted=-8'sd2;
 always_ff @(posedge clk)hidden<=hidden+1;
endmodule
module branch(input logic clk);leaf #(.INIT(9)) inner(clk);endmodule
module top;
 logic clk=0;integer sel=1;logic[7:0] observed;logic bit_observed;
 leaf #(.INIT(3)) other(clk);
 branch nested(clk);
 leaf #(.INIT(1)) dut(clk);
 always #1 clk=~clk;
 always_comb observed=dut.hidden+other.hidden;
 always_comb bit_observed=dut.hidden[sel];
 initial begin
  #2;
  $display("TRACE hierarchy_timing %0d %0d %0d %0d %0d %0d %0d",dut.hidden,other.hidden,nested.inner.hidden,observed,bit_observed,$signed(dut.shifted),dut.INIT);
  @(posedge dut.hidden[1]);#0;
  $display("TRACE hierarchy_edge %0t %b",$time,dut.hidden[1]);
  #1;$finish;
 end
endmodule
