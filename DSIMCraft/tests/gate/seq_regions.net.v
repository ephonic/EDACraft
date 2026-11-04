module dut(input c,d,a,oe,r,output [7:0] y);
DFFOUT f(.C(c),.D(d),.A(a),.E(oe),.Q(y[0]),.QN(y[1]),.Y(y[2]),.TQ(y[3]));
LATCHR l(.G(c),.D(d),.R(r),.Q(y[4]),.QN(y[5]));
DFFR z(.C(c),.D(d),.R(r),.Q(y[6]),.QN(y[7]));
endmodule
