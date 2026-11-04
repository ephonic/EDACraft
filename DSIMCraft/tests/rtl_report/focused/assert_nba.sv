module top;integer x=0;initial begin assert(0) else x<=1;#1;$display("TRACE assert %0d",x);end endmodule
