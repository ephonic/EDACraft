`timescale 1ns/1ps
module lane(output logic[15:0] out);
 logic[15:0] a[2],d[];integer bias=0;
 initial begin
  a[0]=16'h7700;a[1]=1;d=new[2];d[0]=1;d[1]=2;
  #1;bias=1;
  #1;out=a.sum(x) with(16'(x+bias))+d.xor with(item)-3;
 end
endmodule
module top;
 wire[15:0] one,two;lane u(one),v(two);
endmodule
