module dut(input a,b,output z,y);
  C u(.A(a),.B(b),.Z(z),.Y(y));
  C v(.A(b),.B(a),.Z(),.Y());
endmodule
