`timescale 1ns/1ps
module worker #(parameter ID=1)(output logic[63:0] q);
  bit[7:0] clean;
  initial begin
    q=0;clean=0;
    q<=#2 (64'h100+ID);
    clean<=8'bx1z01010;
    #1;q<=64'hzzzzzzzzzzzzzzzz;q<=#1 (64'h200+ID);
    #2;$display("TRACE whole %0d %h %h",ID,q,clean);
    #1;q<=#2 (64'h8000000000000000|ID);
    #4;$display("TRACE final %0d %h",ID,q);
  end
endmodule
module top;
  wire[63:0] one,two;
  worker #(1) u(one);
  worker #(2) v(two);
endmodule
