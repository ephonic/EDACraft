module dut(input c,d,e,a,oe,output [5:0] y);
DFFE f(.C(c),.D(d),.E(e),.Q(y[0]),.QN(y[1]));
DFFOUT o(.C(c),.D(d),.A(a),.E(oe),.Q(y[2]),.QN(y[3]),.Y(y[4]),.TQ(y[5]));
endmodule
