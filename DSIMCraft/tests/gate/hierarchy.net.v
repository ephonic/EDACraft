module leaf(input a,output y);
  wire n;
  INV inner(.A(a),.Y(n));
  INV outer(.A(n),.Y(y));
endmodule
module wrap(a,y);
  input a; output y;
  leaf deep(a,y);
endmodule
module dut(input a,output y,output constant,output floating);
  wrap u(.a(a),.y(y));
  assign constant = 1'b1;
  // Undriven output must remain Z.
endmodule
