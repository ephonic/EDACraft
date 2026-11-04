`timescale 1ns/1ps
module top;
 logic [7:0] q=8'hxx,z=8'hzz;integer i=0,j=0;
 initial begin
  for(i=0;i<4;i++)q=q+8'd1;
  for(j=0;j<4;j++)z=z^8'h55;
  $display("TRACE fourstate %h %h %0d %0d",q,z,i,j);
  i=0;while(1'bx)i=i+1;
  $display("TRACE unknown_condition %0d",i);#1;$finish;
 end
endmodule
