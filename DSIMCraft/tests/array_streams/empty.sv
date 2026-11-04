module top;byte q[$],result[$];logic[15:0] value=16'hffff;int observed;initial begin result={>>{q}};value={>>{q}};observed=result.size();$display("TRACE empty %0d %h",observed,value);end endmodule
