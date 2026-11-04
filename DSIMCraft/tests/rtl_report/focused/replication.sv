module top;parameter W=4;logic[2:0]a;logic[7:0]b;initial begin a={(W-1){1'b1}};b={2*W{1'b1}};$display("TRACE replication %h %h",a,b);end endmodule
