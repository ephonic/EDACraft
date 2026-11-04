`timescale 1ps/1ps
module top;
 real one,two;
 initial begin one=0.5;#2;one=1.25;#2;one=2.5;end
 initial begin two=-1.5;#1;two=0.25;#2;two=0.5;end
endmodule
