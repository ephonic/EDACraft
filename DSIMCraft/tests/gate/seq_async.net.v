module dut(input c,d,r,s,output [11:0] y);
DFFR a(.C(c),.D(d),.R(r),.Q(y[0]),.QN(y[1]));
DFFS b(.C(c),.D(d),.S(s),.Q(y[2]),.QN(y[3]));
DFFSR f(.C(c),.D(d),.R(r),.S(s),.Q(y[4]),.QN(y[5]));
DFFTN t(.C(c),.D(d),.R(r),.S(s),.Q(y[6]),.QN(y[7]));
LATCHR l(.G(c),.D(d),.R(r),.Q(y[8]),.QN(y[9]));
SRLATCH z(.R(r),.S(s),.Q(y[10]),.QN(y[11]));
endmodule
