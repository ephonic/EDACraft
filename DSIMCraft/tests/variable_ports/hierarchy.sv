`timescale 1ns/1ps
module leaf #(parameter W=8)(input [W-1:0] d,output reg [W-1:0] q);
 always @(d)q<=d+1;
endmodule
module middle #(parameter W=8)(input [W-1:0] d,output logic [W-1:0] q);
 leaf #(W) u(d,q);
endmodule
module top;
 logic [7:0] d,q;
 logic [3:0] narrow_q;
 middle #(8) a(.d(d),.q(q));
 middle #(4) b(.d(d[3:0]),.q(narrow_q));
 initial begin
  d=8'h3e;
  #1 $display("TRACE hierarchy %h %h",q,narrow_q);
  if(q!==8'h3f||narrow_q!==4'hf)$fatal(1,"hierarchy first");
  d=8'hff;
  #1 $display("TRACE hierarchy %h %h",q,narrow_q);
  if(q!==0||narrow_q!==0)$fatal(1,"hierarchy wrap");
  d=8'h81;
  #1 $display("TRACE hierarchy %h %h",q,narrow_q);
  if(q!==8'h82||narrow_q!==2)$fatal(1,"hierarchy final");
  $finish;
 end
endmodule
