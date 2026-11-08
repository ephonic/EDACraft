module top(input clk, a, b, output y, z);
 wire d, q, cclk;
 DFF regout(.CK(cclk),.D(d),.Q(q));
 BUF outbuf(.A(q),.Y(y));
 XOR2 logicgate(.A(a),.B(b),.Y(d));
 BUF leakbuf(.A(a),.Y(z));
 BUF unused_output(.A(a));
 BUF clkbuf(.A(clk),.Y(cclk));
endmodule
