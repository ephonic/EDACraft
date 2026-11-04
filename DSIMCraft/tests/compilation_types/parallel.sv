`timescale 1ps/1ps
typedef bit[7:0] Word;
module lane #(parameter N=1)(output Word value);
 initial begin
  value=N;#2;value=N+3;
 end
endmodule
module top;
 Word one,two;
 lane #(1) a(one);lane #(9) b(two);
endmodule
