module dut(input c,d,output [3:0] y);
DFFP a(.C(c),.D(d),.Q(y[0]),.QN(y[1]));
DFFN b(.C(c),.D(d),.Q(y[2]),.QN(y[3]));
endmodule
