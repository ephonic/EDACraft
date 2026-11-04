module top;bit[7:0] data[];bit[7:0] source[$];int observed;initial begin data=new[3];{>>{data}}={>>{source}};observed=data.size();$display("TRACE empty %0d",observed);end endmodule
