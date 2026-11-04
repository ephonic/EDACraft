module top;integer local,protected;initial begin local=3;protected=5;$display("TRACE keywords %0d",local+protected);#1;$finish;end endmodule
