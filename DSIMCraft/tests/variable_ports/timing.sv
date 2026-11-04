`timescale 1ns/1ps
module flop(input clk,input [7:0] d,output logic [7:0] q);
 always @(posedge clk)q<=#2 d;
endmodule
module top;
 logic clk;
 logic [7:0] d,q;
 integer changes;
 flop a(clk,d,q);
 always @(q)changes=changes+1;
 initial begin
  clk=0;d=8'h31;changes=0;
  #1 clk=1;
  #1 d=8'h92;
  #2 $display("TRACE timing %h %d",q,changes);
  if(q!==8'h31||changes!==1)$fatal(1,"timing first");
  clk=0;
  #1 clk=1;
  #3 $display("TRACE timing %h %d",q,changes);
  if(q!==8'h92||changes!==2)$fatal(1,"timing final");
  $finish;
 end
endmodule
