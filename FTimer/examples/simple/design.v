module top (in1, out);
  input in1;
  output out;
  wire n1, n2, n3;

  INVx1 u1 (.A(in1), .Y(n1));
  BUFx1 u2 (.A(n1), .Y(n2));
  INVx1 u3 (.A(n2), .Y(n3));
  BUFx1 u4 (.A(n3), .Y(out));
endmodule
