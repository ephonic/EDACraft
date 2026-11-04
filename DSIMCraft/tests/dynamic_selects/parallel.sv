`timescale 1ns/1ps
module worker(output logic[15:0] q=0);
 logic[15:0] a[];
 logic clk=0;
 integer n=0;
 initial repeat(6)#1 clk=~clk;
 initial begin
  a=new[1];a[0]=0;
  repeat(3)begin @(posedge clk);a[0][3:0]++;a[0][7:4]+=2;end
  q=a[0];
 end
endmodule
module top;
 wire[15:0] a,b;
 worker u(a),v(b);
endmodule
