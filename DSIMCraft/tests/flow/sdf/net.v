`timescale 1ps/1ps
module dut(input a,output x,y);wire n;S src(.A(a),.Z(n));D fast(.A(n),.Z(x));D slow(.A(n),.Z(y));endmodule
