module top;logic[3:0] data[0:1];int observed;initial begin {<<4{data}}=12'habc;observed=1;$display("TRACE fixed left %h %h",data[0],data[1]);end endmodule
