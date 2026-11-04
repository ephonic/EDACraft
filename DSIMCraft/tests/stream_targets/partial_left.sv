module top;logic[3:0] data[];int observed;initial begin {<<4{data}}=10'b1010110011;observed=data.size();$display("TRACE partial left %0d %h %h %h",observed,data[0],data[1],data[2]);end endmodule
