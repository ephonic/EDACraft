`timescale 1ns/1ps
module lane(output logic[15:0] out);
 logic[15:0] a[2];logic[15:0] d[];
 initial begin
  a[0]=16'h7600;a[1]=1;d=new[2];d[0]=1;d[1]=2;
  #1;a[1]=2;
  #1;out=a.sum()+d.xor()-2;
 end
endmodule
module top;
 wire[15:0] one,two;lane u(one),v(two);
endmodule
