`timescale 1ps/1ps
module top;reg C,D,E;wire Z;dut d(C,D,E,Z);
initial begin C=0;D=0;E=1;#100;D=1;#2;C=1;#1;D=0;#2;C=0;#3;C=1;#7;C=0;#1;D=1;#10;C=1;#2;D=0;#6;C=0;#5;E=0;#10;D=1;#1;C=1;#10;E=1'bx;D=0;#1;C=0;#1;C=1;#10;$display("TRACE done c=%b d=%b",C,D);$finish;end endmodule
