module dut(input c,d,r,output [15:0] q,output t);
DFFP g0(.C(c),.D(d),.Q(q[0]));
DFFP g1(.C(c),.D(q[0]),.Q(q[1]));
DFFP g2(.C(c),.D(q[1]),.Q(q[2]));
DFFP g3(.C(c),.D(q[2]),.Q(q[3]));
DFFP g4(.C(c),.D(q[3]),.Q(q[4]));
DFFP g5(.C(c),.D(q[4]),.Q(q[5]));
DFFP g6(.C(c),.D(q[5]),.Q(q[6]));
DFFP g7(.C(c),.D(q[6]),.Q(q[7]));
DFFP g8(.C(c),.D(q[7]),.Q(q[8]));
DFFP g9(.C(c),.D(q[8]),.Q(q[9]));
DFFP g10(.C(c),.D(q[9]),.Q(q[10]));
DFFP g11(.C(c),.D(q[10]),.Q(q[11]));
DFFP g12(.C(c),.D(q[11]),.Q(q[12]));
DFFP g13(.C(c),.D(q[12]),.Q(q[13]));
DFFP g14(.C(c),.D(q[13]),.Q(q[14]));
DFFP g15(.C(c),.D(q[14]),.Q(q[15]));
TFF tf(.C(c),.R(r),.Q(t));
endmodule
