module top;integer a=0;task incr;begin a=a+1;end endtask initial begin incr();$display("TRACE definition %0d",a);end endmodule
