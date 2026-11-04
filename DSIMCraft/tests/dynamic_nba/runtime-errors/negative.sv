module top;integer a[];initial begin a=new[1];a[-1]<=#3 7;#4;$display("TRACE invalid target accepted");end endmodule
