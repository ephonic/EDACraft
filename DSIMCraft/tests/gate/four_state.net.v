module dut(a,y,bus);
  input [6:4] a;
  output [7:0] y;
  inout bus;
  AND2 g0(.A(a[6]),.B(a[5]),.Y(y[0]));
  INV g1(.Y(y[1]),.A(a[6]));
  COMPLEX g2(.C(a[4]),.RESULT(y[2]),.B(a[5]),.A(a[6]));
  XOR2 g3(.A(a[6]),.B(a[5]),.Y(y[3]));
  HALF g4(.SUM(y[4]),.A(a[6]),.CARRY(y[5]),.B(a[5]));
  assign y[6] = 1'bx;
  assign y[7] = 1'bz;
  TBUF tri_gate(.E(a[4]),.Y(bus),.A(a[6]));
  // Missing pins are unconnected, rather than assigned invented values.
  AND2 unused(.A(a[6]),.Y());
endmodule
