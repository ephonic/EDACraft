module BUF_X1(input A, output Y);
endmodule
module top(input a, output y);
  BUF_X1 u0 (.A(a), .Y(y));
endmodule
