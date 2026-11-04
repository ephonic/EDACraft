module top;bit[7:0] data[$:1];int observed;initial begin {>>{data}}=40'h123456789a;observed=data.size();$display("TRACE bounded %0d %h %h",observed,data[0],data[1]);end endmodule
