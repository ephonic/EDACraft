module branch(input a,output y);INV u(.A(a),.Y(y));endmodule
module dut(input a,b,output y,z);
wire n;branch h(a,n);INV v(.A(n),.Y(y));
INV \literal/slash (.A(b),.Y(z));
endmodule
