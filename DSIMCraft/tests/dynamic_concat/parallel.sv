`timescale 1ns/1ps
module worker(output logic[15:0] q=0);
 logic[7:0] a[],b[];
 initial begin
  a=new[1];b=new[1];a[0]=0;b[0]=0;
  {a[0],b[0]}<=#2 16'h1234;
  #3;{a[0][3:0],b[0][3:0]}=8'hab;q={a[0],b[0]};
 end
endmodule
module top;
 wire[15:0] one,two;
 worker u(one),v(two);
endmodule
