module dut(input c,d,output [3:0] y);
LATCHP a(.G(c),.D(d),.Q(y[0]),.QN(y[1]));
LATCHN b(.G(c),.D(d),.Q(y[2]),.QN(y[3]));
endmodule
