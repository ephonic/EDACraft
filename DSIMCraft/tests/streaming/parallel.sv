`timescale 1ns/1ps
module lane(output logic[15:0] out);
 logic[7:0] a[0:1];
 logic[15:0] value=16'h1234;
 initial begin
  {>>{a}}=value;
  #1;value=16'h0375;
  #1;{>>{a}}=value;
  #1;out={<<8{a}};
 end
endmodule
module top;
 wire[15:0] one,two;
 lane u(one),v(two);
endmodule
