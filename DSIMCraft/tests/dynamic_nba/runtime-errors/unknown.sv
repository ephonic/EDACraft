module top;integer a[];initial begin a=new[1];a[32'bx]<=#3 7;#4;$display("TRACE invalid target accepted");end endmodule
